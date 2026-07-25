# PCIe on the Arria 10 (Mustang-F100-A10) — Construction Notes & Blocker

**Status as of 2026-07-09: BLOCKED on one missing board fact.** Everything else is
understood and captured below. Nothing here needs re-deriving when the blocker lifts.

**Superseded (2026-07-25): the refclk blocker below was resolved -- `PIN_AB28`
confirmed correct by a real Fitter run, full PCIe chain synthesized, fitted, and
timing-closed (58.62MHz, points.md #52).** See "## 6. Live bring-up debugging
log" at the end of this file for the full trail from a working compile through
to actual BAR read/write testing on real hardware -- a genuinely useful
reference for the next time any of this needs touching again.

---

## 0a. CONFIRMED ON THE ACTUAL DEVICE (2026-07-09)

The `.pin` file from a real Fitter run on `10AX066H2F34E2SG` (`output_files/
Unbicell64_sz_cross.pin`) **validates the BSDL F34 map pin-for-pin, all four banks.**

Because the design instantiates no transceivers, Quartus reports each unused
transceiver pin by its *termination requirement*, not its name:
`GXB_NC` (unused TX -> float) and `GXB_GND*` (unused RX and refclk -> tie to GND).
Per bank that is exactly **12 NC + 16 GND = 28**, matching 12 TX + 12 RX + 4 refclk.

Validation, all four banks (`1C`,`1D`,`1E`,`1F`): **GND set match = True, NC set
match = True.** Every pin number in the BSDL appears in the correct group on the
real GX die. The SX-vs-GX die difference does not affect the transceiver pin map.

### CONFIRMED refclk pins on 10AX066H2F34E2SG
| Refclk | p | n |
|---|---|---|
| `REFCLK_GXBL1C_CHT` | AD28 | AD27 |
| `REFCLK_GXBL1C_CHB` | AF28 | AF27 |
| `REFCLK_GXBL1D_CHT` | Y28 | Y27 |
| **`REFCLK_GXBL1D_CHB`** | **AB28** | **AB27** |
| `REFCLK_GXBL1E_CHT` | T28 | T27 |
| `REFCLK_GXBL1E_CHB` | V28 | V27 |
| `REFCLK_GXBL1F_CHT` | M28 | M27 |
| `REFCLK_GXBL1F_CHB` | P28 | P27 |

Eight pairs. That is the entire universe of possibilities on this package.

### What is PROVEN vs what is INFERRED
- **PROVEN**: these eight pairs are the device's refclk pins. Confirmed twice --
  by the Fitter's "24 unused RX/TX channels" warning, and now pin-for-pin by the
  `.pin` file.
- **INFERRED**: that IEI wired the edge connector's REFCLK to `1D_CHB`. Rests on
  AN 750 showing Quartus's *natural* x8 placement (banks 1D+1C, refclk `1D_B`) and
  the assumption IEI did not fight the tool. Reasonable, not certain.
- **SAFETY NET**: an ILLEGAL refclk assignment errors at compile. Only a LEGAL-but-
  WRONG one fails silently. Eight candidates, further pruned by HIP placement.

### First QSF line to try
```
set_location_assignment PIN_AB28 -to refclk
```
(Quartus normally wants only the `p` leg; it derives `n` from the differential
pair. Set the I/O standard per PCG-01017: HCSL if DC-coupled, else AC-couple.)

This was answered entirely from local build artifacts + one BSDL, with Intel's
pinout pages deleted. See points.md #28/#29 -- the `.pin` file IS the MAN file's
device half.

---

## 0. How the search was collapsed (2026-07-09)

A BSDL file for the **F34 package** (`10AS032HF34`, FBGA1152) reveals that this
package bonds out **only FOUR transceiver banks**: `GXBL1C`, `GXBL1D`, `GXBL1E`,
`GXBL1F`. **All left side. No `GXBR4x` at all.** 4 banks x 6 channels = **24**.

**Independently confirmed by our own Fitter**, which warned:
```
There are 24 unused RX channels in the design.
There are 24 unused TX channels in the design.
```
24 = 24. Two independent sources agree. (Earlier notes claiming banks C..J on both
sides described the FAMILY; this PACKAGE has four.)

### The only refclk pins that physically exist on F34
| Refclk | p | n |
|---|---|---|
| `REFCLK_GXBL1F_CHT` | M28 | M27 |
| `REFCLK_GXBL1F_CHB` | P28 | P27 |
| `REFCLK_GXBL1E_CHT` | T28 | T27 |
| `REFCLK_GXBL1E_CHB` | V28 | V27 |
| `REFCLK_GXBL1D_CHT` | Y28 | Y27 |
| **`REFCLK_GXBL1D_CHB`** | **AB28** | **AB27** |
| `REFCLK_GXBL1C_CHT` | AD28 | AD27 |
| `REFCLK_GXBL1C_CHB` | AF28 | AF27 |

### The search space, collapsed
Gen2 x8 = 8 lanes = **two ADJACENT 6-channel banks**. Only three pairings exist:
`1C+1D`, `1D+1E`, `1E+1F`. **Six combinations maximum**, and Quartus rejects illegal
refclk/HIP pairings before you flash.

Further: on Arria 10 you generally do NOT hand-assign `hip_serial` lanes -- the hard
IP's location determines them. **The real unknown is essentially just the refclk pin.**

### Strong first candidate
AN 750's table (dismissed above as a pinout source, correctly) is useful as evidence
of **Quartus's NATURAL PLACEMENT**: that was a real fit, and Quartus put PCIe Gen2 x8
on **1D (all six) + 1C (two)** with refclk **`REFCLK_GXBL1D_B`**. That is a DEVICE
tendency (where the HIP lands), not a board fact. If IEI let Quartus place naturally
-- the path of least resistance -- they would have got the same.

**=> Try `REFCLK_GXBL1D_CHB` first: `PIN_AB28` (p) / `PIN_AB27` (n).**

### The exact-part pinout is GONE from Intel -- but QUARTUS IS THE PINOUT FILE
Intel has partly removed the pages for this EOL model, including its pinout files.
The `10AS032HF34` BSDL is the only F34 document obtainable, and it is an Arria 10
**SX** (has an HPS) whereas ours is a **GX** -- different die, different
general-purpose I/O. Same package is the only commonality. That caveat is real.

**It does not matter.** The device database for `10AX066H2F34E2SG` ships *inside
Quartus*. The tool has the ball map; Intel pulling web pages does not remove it.

Three ways to confirm the refclk pins for the EXACT part, easiest first:
1. **Pin Planner -> All Pins / package view.** Look up **AB28**. If it reports
   `REFCLK_GXBL1D_CHBp`, the BSDL numbers transfer and the guessing is over.
2. **Filter Pin Planner by pin FUNCTION** for `REFCLK`. It enumerates every refclk
   pin on *our* device with locations -- the definitive eight-pair table, from the
   tool.
3. **Let the Fitter check it.** Export `refclk`, `set_location_assignment PIN_AB28
   -to refclk`, compile. An ILLEGAL refclk location for the HIP placement makes
   Quartus **error before flashing**. The tool prunes wrong answers for free.

(3) is the safety net. The dreaded build-flash-silence failure only occurs on a
LEGAL-but-WRONG pin. Quartus rejects every ILLEGAL one, and only 8 refclk pairs
exist, of which the HIP placement accepts a subset.

Independent corroboration that the bank structure transfers: our own Fitter reports
exactly **24 unused RX and 24 unused TX channels** on the real GX die -- matching the
BSDL's 4 banks x 6 channels. That is our device describing itself, not the SX
describing the GX.

### Other caveats before building
2. Set the refclk I/O standard appropriately -- per PCG-01017, PCIe permits
   DC-coupling on REFCLK only if the standard is **HCSL**; otherwise AC-couple.
3. A wrong refclk still fails silently (no link, no enumeration). But six candidates
   is a tractable afternoon, not a void.

**Status change: PCIe moves from "bounded search, or never" to "one pin, one strong
candidate, six worst-case tries."**

---

## 1. The blocker, stated precisely (superseded in part by §0 above)

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

### FALSE LEAD (2026-07-09) — do not use AN 750's table as a pinout
`fpga/quartus/683155_666704.pdf` is **AN 750: Using the Altera PDN Tool to Optimize
Your Power Delivery Network Design**. Its bank-allocation table shows PCIe Gen2 on
banks 1D (CH0-5) + 1C (CH4-5), with `REFCLK_GXBL1D_B = 100 MHz`. This looks exactly
like the answer. **It is not.** It is the app note's hypothetical EXAMPLE DESIGN,
built to stress the PDN tool: page 7 lists the per-bank current draw
(`VCCR_GXBL1C/1D/1E/1F`, `VCCR_GXBR4C..4F`) that this very table feeds. The
"Datarate 1/2/3" columns are what-if scenarios for current estimation, not wiring.
Tell-tales: the table pairs `GXBL1D_TX` with `GXBR4C_RX` (incoherent for a real
link, irrelevant for a current total), and mixes 12Gbps chip-to-chip + 10GbE + 1GbE
+ PCIe on one die -- a deliberate worst case, not an inference accelerator.

Assigning pins from it would build, fit, flash, and never enumerate.

**What it does legitimately confirm** (matching the handbook-derived inference):
- A PCIe **Gen2 x8 link spans two adjacent 6-channel banks** (6 + 2 here).
- The reference clock is a **bank-specific `REFCLK_GXBLxx_T` / `_B` pin at 100 MHz**.
- The GX660 has banks **1C-1F (left)** and **4C-4F (right)** -- eight total.

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

### PCIe is PARKED, not DEAD — and the search is bounded
Two facts keep this alive:
1. **The card enumerates on the host** under IEI's factory bitstream (visible in
   Windows). So the lanes ARE wired, the refclk IS connected, and the link provably
   trains. This is missing documentation about hardware that demonstrably works --
   not a hardware limitation.
2. **The search space is small.** Eight banks (1C-1F, 4C-4F); a Gen2 x8 link occupies
   two ADJACENT banks; each bank has a `_T`/`_B` refclk choice. That is a handful of
   plausible combinations, each testable by a build. Expensive (a full compile each)
   but finite -- and PCIe hard IP instances are themselves tied to specific banks,
   which narrows it further.

So if IEI never answers, a focused set of builds can find it. Worth an afternoon
someday; not worth blocking the roadmap now.

### EOL REALITY CHECK (2026-07-09) — revise the optimism downward
The Mustang-F100-A10 has reached **end of life**. No vendor support; a BSP or
schematic is unlikely to surface. Earlier framing ("one email to IEI away") was too
optimistic and is hereby corrected: **the pinout probably is not coming from IEI.**
That moves PCIe from "one datum away" to "bounded search, or never."

What EOL actually costs, stated plainly:
- **PCIe on THIS card**: probably gone, absent a successful bounded search.
- **Nothing else.** The substrate is proven on real gates with real JTAG readback.
  That proof does not evaporate because a board stopped shipping.
- **DSP is unaffected.** Chain length 27, bridge shape, latency structure are all
  *device* facts from Intel's Arria 10 handbook -- alive, maintained, and true of the
  die regardless of who sold the board.

**Why this is survivable, by construction.** The card is a development TARGET, not
the architecture. Everything built -- transit, routing_mask, CMD_ARRAY_RESET, the v3
command contract, pentacross placement, the map/binder/loader design -- is
card-agnostic. That is precisely what #19 and #23 exist for: card-specific facts
(pins, DSP latencies, refclk) live as DATA in the MAN file, outside the design. **An
EOL card becomes a stale MAN file, not a stranded project.**

Nothing on the near roadmap needs PCIe: Stage 1 (adder RTL), Stage 3 (migration),
Stage 4 (compiler), Stage 5 (composer) are all JTAG-sufficient. The FlowTrix/LBM
streaming plan does need bandwidth -- but that is stages away, and by then the honest
question is whether the NEXT card should be chosen for a *documented* PCIe path,
rather than whether this one can be coaxed.

**This card got the project to a silicon-proven substrate. That was its job, and it
did it.** Choose the successor for a writable MAN file; the architecture already
makes that a data change, not a rebuild.

### Useful facts from the Pin Connection Guidelines (683814, PCG-01017)
Not a pinout, but the naming grammar and electrical rules:
- Refclk pins: `REFCLK_GXB[L1,R4][C,D,E,F,G,H,I,J]_CH[B,T]p/n`. Banks run **C..J**
  (wider than the C..F seen in AN 750's example).
- Lanes: `GXB[L1,R4][C..J]_TX_CH[0:5]p/n` (and RX).
- `REFCLK_GXB` doubles as a dedicated clock input with fPLL for core clock
  generation, even when the transceiver channel is unused.
- **"In the PCI Express configuration, DC-coupling is allowed on the REFCLK if the
  selected REFCLK I/O standard is HCSL."** Otherwise the refclk pins must be
  AC-coupled.
- Unused refclk pins: tie individually to GND, or all together via one 10k to GND,
  with short traces. Unused TX pins: leave floating.

This is the *device* half of the puzzle's grammar. The missing half remains the
*board* fact: which bank IEI wired to the edge fingers.

---

## 5. Note on the MAN file (#23)

This whole episode is the MAN-file argument made concrete. The facts that block us —
the PCIe refclk pin, the transceiver lane mapping — are *card properties*, sitting
alongside `PIN_E23` (the fabric clock, whose absence killed the clock and cost a
build cycle) and the DSP latency table. They are exactly what a MAN file exists to
hold. A card without a MAN file cannot be fully targeted, and that is not a
limitation of the design — it is the design correctly identifying missing input.

---

## 6. Live bring-up debugging log (2026-07-24/25)

Full trail from "PCIe chain synthesizes and fits" through to actually testing
BAR0 read/write on real hardware -- not a clean success story, several real,
independent bugs found one at a time. Kept in full because every one of these
is the kind of thing that costs another afternoon if rediscovered from scratch.

### 6a. Windows driver install: Code 39, and the real cause

Symptom: `Alt_Test.exe` couldn't even open the device -- Device Manager showed
Code 39 ("Windows cannot load the device driver for this hardware... The
driver may be corrupted or missing"), plus an Application Control policy block.

**What did NOT fix it, in order tried:** Smart App Control off; `bcdedit /set
testsigning on` + reboot; disabling Secure Boot in BIOS (this DOES matter for
testsigning to take effect at all, but wasn't the actual root cause here).

**The real cause, found via the driver's own Device Manager error log entry**
(status `0xC0000494` = `STATUS_PNP_FUNCTION_DRIVER_REQUIRED`, per Microsoft's
own docs: "the INF does not specify an associated function driver service"):
Altera's own `altera_pcie_win_driver.inf` has a genuine packaging bug. The
`[ALTERA.NTamd64]` Models section maps the device to install-section name
`Altera_Device`, but every actual DDInstall section in the file (`.NT`,
`.NT.Services`, `.NT.CoInstallers`, `.NT.Wdf`, `.NT.HW`) is named `AltPCI_Inst`
instead. Windows found no matching install section at all -- including no
`AddService` directive, which is exactly what that status code means.

**Fix:** rename the five `AltPCI_Inst.*` section headers to `Altera_Device.*`
(leaving `[AltPCI.CopyFiles]`, `[AltPCI_Service]`, `[AltPCI_wdfsect]` etc. alone
-- those are referenced *by name* from inside the renamed sections and don't
need to match the Models-section basename). Since the edited `.inf` no longer
matches the signed `.cat` file's recorded hash, Test Mode being active is what
lets Windows install it anyway ("install this driver software anyway" prompt).
Install via Device Manager → Update Driver → point at the folder with the
corrected `.inf` alongside the original `.sys`/`.cat`/`WdfCoInstaller*.dll`.

If Code 39 ever needs re-diagnosing on a fresh machine: check the exact status
code in Device Manager's error log first (Event Viewer → Windows Logs →
System, or the device's own "Events" tab) rather than assuming it's a
signing/Secure Boot problem -- it very often isn't.

### 6b. PCIe Hard IP identity fields left at zero

Symptom: `Alt_Test.exe` could open the device and read config space, but
`Device ID`, `Revision ID`, `Subsystem Vendor/Device ID` all read `0x0000`, and
the BAR0 write/readback test failed (`0xFFFFFFFF`, though this specific
symptom turned out to have a second, independent cause -- see 6c).

**Cause:** in `pcie_a10_hip_0`'s own IP Catalog parameters (`pcie_a10_hip_0.qsys`),
`device_id_hwtcl`, `revision_id_hwtcl`, `subsystem_device_id_hwtcl`, and
`subsystem_vendor_id_hwtcl` were all left at their literal default of `0`.
Only `vendor_id_hwtcl` had ever been set (to `0x1172`, hence Vendor ID always
read correctly). This is a synthesis-time IP parameter, not a driver or
Windows-caching issue.

**Fix, in Platform Designer -> `pcie_a10_hip_0` -> Device Identification
Registers tab:** Device ID `0x2494`, Revision ID `0x1`, Subsystem Vendor ID
`0x180C`, Subsystem Device ID `0x660A` -- these exact values come from the
`.inf`'s own hardware ID string (`DEV_2494&SUBSYS_660A180C&REV_01`), which the
driver package was built expecting. Regenerate HDL, full recompile, reprogram,
**and reboot the host** -- see 6d for why a reboot was needed for this specific
change and not others.

### 6c. BAR0 type: 64-bit prefetchable vs 32-bit non-prefetchable

Even after 6b fixed the identity fields, BAR0 read/write still failed
identically (`0xFFFFFFFF`), and `Alt_Test.exe`'s own BAR0 readout showed the
allocated address itself looked wrong/unstable across runs.

**Cause:** the Hard IP's BAR0 was configured as **64-bit prefetchable memory**.
Two independent problems with that: (1) a 64-bit BAR can be mapped anywhere in
the full 64-bit space including above 4GB, and many desktop BIOSes only
actually route real address space up there if "Above 4G Decoding" is enabled
-- without it, config space enumerates fine but the BAR never gets a real,
routable address; (2) "prefetchable" tells the OS/root complex reads have no
side effects and can be spec ulatively cached/read-ahead, which is semantically
wrong for a live register interface whose reads reflect real-time fabric state.

**Fix, in Platform Designer -> `pcie_a10_hip_0` -> Base Address Registers ->
BAR0:** Type -> `32-bit non-prefetchable memory`, Size unchanged (4KB). After
this fix, `Alt_Test.exe` showed a genuine, stable, below-4GB BAR0 address
(`0xFC9FF000`) -- confirming this part of the fix took, even though the actual
read/write test still failed for the separate reason under investigation now
(see 6f). Regenerate, recompile, reprogram, reboot.

### 6d. When a reboot is actually needed vs. just a reprogram

**Rule, confirmed through several rounds of "did I need to reboot for this":**
a reboot (forcing Windows to re-walk PCI config space) is only needed when
something visible *in PCI config space itself* changes -- Vendor/Device/
Revision/Subsystem IDs, BAR count/size/type, capability structures. Those get
read once at boot and cached by the OS; JTAG-reprogramming the FPGA has no
mechanism to tell Windows "re-read me," so a stale cache persists until reboot
forces fresh enumeration.

**A reboot is NOT needed** for anything that doesn't change config space:
RTL/cell logic changes, `.sdc` changes, adding/changing SignalTap probes.
Windows already has the right BAR address/size cached and just keeps issuing
reads/writes to it; whatever's actually running on the FPGA behind that
address is free to change via a plain reprogram.

### 6e. Custom host-side BAR test tool, and a real bug in it

`Alt_Test.exe` turned out to be a fixed, built-in compliance self-test (reports
only PASS/FAIL against its own internal pattern) -- it cannot drive an
arbitrary command sequence to specific offsets. `AlteraPCILibraryDll.dll`
(shipped alongside it) exports the real API needed: `AltInitAPI`,
`AltPciOpenDevice`, `AltPciMapResource`, `AltPciReadAddr32`/`WriteAddr32`,
`AltPciUnmapResource`, etc. -- called via `LoadLibrary`/`GetProcAddress`
against the raw C++-decorated export names (no original header or import lib
needed, since only opaque handles get passed between calls). Full working test
program: `unicell_pcie_celltest.c`, replays the exact known-good
`icm64_readstate.tcl` configure+inject sequence (ARRAY_RESET through INJECT)
over live PCIe instead of JTAG.

**Real bug found and fixed:** `AltPciOpenDevice` and `AltPciMapResource`'s
mangled export names show a *single* pointer to the handle struct
(`PAUAltPciDeviceHandle@@`), not a pointer-to-pointer -- meaning the caller
must supply the address of an *already-allocated* struct for the DLL to fill
in, not a `void**` for the DLL to allocate and hand back. The first version of
the test program used bare pointer-sized variables as if they were the whole
struct's storage; the DLL then wrote real handle data past that tiny
allocation, corrupting adjacent memory and crashing the program shortly after
(silently -- no crash dialog, just an early return to the prompt). Fixed by
allocating generous (1KB) zeroed buffers for both handles and passing the raw
buffer addresses directly, without knowing the real (undocumented) struct
sizes. `AltPciReadAddr32`/`WriteAddr32`'s signatures were correctly typed from
the start (`PAI` there really is a plain `unsigned int*` out-param, not a
struct handle).

### 6f. SignalTap setup gotchas (all real, all cost real time)

1. **Changes made in the SignalTap GUI are not saved to disk automatically.**
   A first compile with a fully-configured `.stp` still showed "0 cells, 0
   bits" in the Instance Manager -- because the file was never actually saved
   (watch the title bar's `*` and make sure it clears) before the compile ran.
   Always `Ctrl+S` and confirm before recompiling.

2. **Node Finder's default Filter/Look-in scope can silently return zero
   matches for signals that genuinely exist.** Set Filter to `Design Entry
   (all names)` and Look in to the actual top-level module (with "Include
   subentities" checked) -- a narrower or stale scope produces "No matches"
   for a search that should hit dozens of nodes.

3. **Plain wires with no register on them get optimized away and won't appear
   under their source-file name.** Top-level port names like `rxm_write`,
   `avs_write`, `rx_st_valid` (straight pass-throughs with no logic) vanished
   entirely from Node Finder; the actual *registered* internal signals
   (`out_addr_r`, `out_data_r`, `cpu_valid`, `rx_st_valid_r`, `rx_st_bar_r`)
   survived and were taggable. When a signal search comes up empty, look for
   the registered version one layer in, not the port name.

4. **Clock *alias* wires can be optimized away even when the design partition
   they belong to has Netlist Type set to "Source File."** `w_coreclkout_hip`
   (the wrapper's own alias for the Hard IP's clock output) showed up red
   ("missing... pre-synthesis tap must be preserved... recompile with Source
   netlist type") even with that setting already correctly in place. Fix:
   use the real signal one level closer to the actual hardware instead of the
   alias -- `pcie_a10_hip_0:u_pcie_hip|coreclkout_hip` (the IP instance's own
   output port) resolved cleanly. A global clock buffer primitive (e.g.
   `u_global_buffer_coreclkout`, if the instance-port name still doesn't
   resolve) is an even safer bet, since real hardware clock buffers are
   essentially never optimized away.

5. **Signals in different clock domains need separate SignalTap instances**,
   each with its own Clock field set to the actual clock in that domain --
   don't try to mix a fast-domain signal into an instance clocked by the slow
   fabric clock or vice versa.

### 6g. Current status (2026-07-25)

Two SignalTap instances set up: one on the fabric-clock side
(`out_addr_r`/`out_data_r`/`cpu_valid`/`cpu_bus`, clocked by `div_cnt[1]`,
triggered on `cpu_valid`), one on the Hard-IP-clock side
(`rx_st_valid_r`/`rx_st_sop_r`/`rx_st_bar_r[5:0]`, clocked by
`pcie_a10_hip_0:u_pcie_hip|coreclkout_hip`, triggered on `rx_st_valid_r`).
`cpu_valid` never pulsed across a full 12-step configure+inject sequence
issued via `unicell_pcie_celltest.exe` in earlier captures. This second
instance is intended to answer, definitively: does a BAR0-tagged TLP even
arrive at the Hard-IP/`pio_bridge_0` boundary at all? If not, the fault is in
Hard IP TLP/BAR configuration. If it arrives correctly tagged but `cpu_valid`
still never fires, the fault is inside `pio_bridge_0`'s own internal decode --
IP-generated code, not something in this repo's own RTL. Not yet resolved as
of this writing; update this section once the capture comes back.
