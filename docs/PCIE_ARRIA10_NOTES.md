# PCIe on the Arria 10 (Mustang-F100-A10) — Construction Notes & Blocker

**Status as of 2026-07-09: BLOCKED on one missing board fact.** Everything else is
understood and captured below. Nothing here needs re-deriving when the blocker lifts.

---

## 1. The blocker, stated precisely

**Which transceiver block(s) on the `10AX066H2F34E2SG` does IEI route to the PCIe
edge connector, and which block-specific REFCLK pin pair carries the host's 100 MHz
PCIe reference clock?**

That is the whole blocker. Two numbers (a refclk pin pair, and a lane/bank mapping).

Why it cannot be inferred:
- The **Intel PCIe hard IP** knows the *device*. It does not know the *board*.
- The **Arria 10 handbook** (683553 / 683461) is a *device* document. Its pin tables
  are per-package, and it contains no board wiring.
- The **Intel example design** targets `10AX115S1F45I1SG` on the *Arria 10 GX FPGA
  Development Kit* — different die, different package (F45 vs F34), different board.
  Its pins are actively misleading.
- The **A10 GX Transceiver Signal Integrity Dev Kit UG** targets `10AX115F1932C` —
  again a different die/package, and that board has **no PCIe edge connector at all**
  (QSFP/SFP+/CFP2/SMA/backplane only). Its "PCIe Group" label in the transceiver
  usage figure refers to internal block grouping, not an edge connector.

A wrong `refclk` pin does not error. The link simply never trains and the card never
appears on the bus — the `PIN_E23` failure class, with worse diagnostics.

**Where the answer would live:** the IEI Mustang-F100-A10 user manual; an IEI BSP or
reference design (OpenVINO-era cards sometimes shipped one); or the card schematic.
As of this writing, none located.

### Structural constraint that narrows it (from the A10 handbooks)
- Transceiver REFCLK inputs are **dedicated pins per transceiver block**:
  `REFCLK_GXBL_1C..1H` (left side) and `REFCLK_GXBR_4C..4H` (right side).
- Transceiver channels are organised in **blocks of 6** (`CH0..CH5`).
- A **Gen2 x8** link needs 8 lanes, so it **spans two adjacent blocks**. This
  meaningfully restricts which bank pairs IEI could have used.

---

## 2. What IS established (verified, not assumed)

### The IP configures cleanly for our exact part
Platform Designer instantiates `altera_pcie_a10_hip` and reports:
```
device_family    = Arria 10
part_trait_device = 10AX066H2F34E2SG      <- our part
Gen2 (5.0 Gbps) x8, 128-bit
```

### Correct settings (already selected in `pcie_test_1.qsys`)
| Parameter | Value |
|---|---|
| `interface_type_hwtcl` | `Avalon-MM` (not AXI — the repo's Xilinx work is irrelevant here) |
| `port_type_hwtcl` | `Native endpoint` |
| `pll_refclk_freq_hwtcl` | `100 MHz` |
| Hard IP mode | Gen2 x8, 128-bit, **250 MHz** `coreclkout_hip` |
| `bar0_address_width_hwtcl` | `16` → BAR0 = **64 KB** |
| `bar2_address_width_hwtcl` | `8` → BAR2 = 256 B |

BAR0 at 64 KB = 2,048 cells at 32 bytes/cell. Ample.

### The four exports (from Intel's own example generation script)
These clear the "must be exported, or connected to a matching conduit" errors:
```tcl
add_interface          refclk clock end
set_interface_property refclk EXPORT_OF DUT.refclk
add_interface          pcie_rstn conduit end
set_interface_property pcie_rstn EXPORT_OF DUT.npor
add_interface          xcvr conduit end
set_interface_property xcvr EXPORT_OF DUT.hip_serial
add_interface          pipe_sim_only conduit end
set_interface_property pipe_sim_only EXPORT_OF DUT.hip_pipe
```
Plus `hip_ctrl` must be exported, and `rxm_irq` connected to `cra_irq`
(`add_connection DUT.rxm_irq DUT.cra_irq`) to satisfy the interrupt message.

**`refclk` must NOT be connected to an internal `clk_0` source.** It is the host's
100 MHz reference arriving on a dedicated transceiver pin. (A `clk_0` at 50 MHz
produces the "requires 100000000Hz, but source has frequency of 50000000Hz" error.)
`coreclkout_hip` is an *output* — the IP gives you 250 MHz; feeding it back to
`refclk` would be circular.

### Interface roles (mental model)
- **`rxm_bar0`, `rxm_bar2`** — Avalon-MM **masters**. They reach *into* your design.
  The host writing BAR0 becomes a master transaction on your Avalon bus.
- **`txs`, `cra`** — Avalon-MM **slaves**; the IP's own registers.
- **`coreclkout_hip`** — clock *output*, already clocking every Avalon port.
- Masters reach in; slaves get reached.

### Connection topology (adapted from the example)
The example hangs an on-chip memory off BAR0:
```tcl
add_connection DUT.rxm_bar0 MEM.s1
add_connection DUT.rxm_bar0 DUT.cra
add_connection DUT.rxm_bar2 MEM.s1
```
**In our design, `rxm_bar0` drives the UniCell command bridge instead of `MEM`.**
That bridge is the one component we write. Everything else is IP configuration.

Also drop `add_instance DK altpcie_devkit` — it exists to drive the dev kit's board
pins and is irrelevant to a custom card.

### `apps_type_hwtcl = 3` ("Target only")
Correct starting point: the card only responds to host reads/writes, no
card-initiated DMA. Exactly what a control-plane bridge needs.

---

## 3. The bridge we would write

An **Avalon-MM slave** wrapping the UniCell command path. Avalon-MM's handshake
(`write`/`read`/`address`/`writedata`/`readdata`/`waitrequest`) is simpler than
AXI-Lite's.

**CRITICAL:** derive its encodings from `docs/V3_COMMAND_CONTRACT.md`, **not** from
`pcie/axi_unicell_bridge.v`. That file is Xilinx AXI-Lite *and* encodes the retired
**8-bit auth at `axi_wdata[23:16]`**. The live RTL uses **11-bit auth at
`cmd_bus[29:19]`**. A bridge built from the old file would silently refuse every
config command — precisely the failure that consumed the 2026-07-08 session.

The old bridge's *conceptual* content survives (BAR0 memory map: cell x 32 bytes;
CMD_WRITE / DATA_WRITE / OUT_READ / STATUS). Its bus interface and command encodings
do not.

### Clocking decision (open)
`coreclkout_hip` is 250 MHz. The fabric currently runs at 25 MHz (CLK_100M / 4).
Either clock-cross into the fabric domain, or reconsider the divider. Not yet decided.

---

## 4. Consequence for the card

Without the pinout, **the PCIe half of the Mustang-F100-A10 is unusable to us**. The
card remains fully functional over JTAG/ISSP (which is how the entire substrate was
brought up and how transit was proven on silicon), but:

- No high-bandwidth host path for streaming ICMs or reading results.
- The FlowTrix / LBM plan's DDR-streaming + temporal-blocking approach, which assumed
  a fast host link, needs rethinking or deferral.
- Iteration stays JTAG-speed. (This is what made the 2026-07-08 debugging slow.)

**This does not block the roadmap.** Stage 1 (adder RTL), Stage 3 (model migration),
Stage 4 (compiler), Stage 5 (composer) are all unaffected. DSP integration (#25/#26)
has a clear runway — chain length (27), bridge shape, and the configurable-latency
story are all sourced from Intel's device handbook, which *does* apply to our part.

**Sequencing therefore stands as decided: DSP first.** PCIe is a single missing datum
away, not a design problem. Park it; pursue the pinout via IEI support in the
background.

---

## 5. Note on the MAN file (#23)

This whole episode is the MAN-file argument made concrete. The facts that block us —
the PCIe refclk pin, the transceiver lane mapping — are *card properties*, sitting
alongside `PIN_E23` (the fabric clock, whose absence killed the clock and cost a
build cycle) and the DSP latency table. They are exactly what a MAN file exists to
hold. A card without a MAN file cannot be fully targeted, and that is not a
limitation of the design — it is the design correctly identifying missing input.
