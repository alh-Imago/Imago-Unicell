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

### 6g. Session log: 2026-07-25 (superseded, kept for the reasoning trail)

Ended the day believing the Data Link Layer never came up, on the grounds
that bit 13 of Link Status read 0.

**That inference was wrong.** DLL Link Active is only meaningful if the
endpoint advertises the capability, and Link Capabilities had bit 20 clear
(Data Link Layer Link Active Reporting Capable = 0). Bit 13 therefore reads
0 permanently regardless of link state. The IP's "Data link layer active
reporting" checkbox was noted as unchecked in the same session and then the
resulting zero bit was treated as independent evidence -- the same fact
counted twice.

The inference also runs the opposite way: config space reads are TLPs, and
TLPs cannot move before the link completes flow-control initialisation and
reaches DL_Active. Config space was working throughout. The data link layer
was up the whole time, and PERST#/refclk sequencing -- the leading
hypothesis at the end of that session -- was never the problem.

### 6h. Session log: 2026-07-26/27 -- two real root causes, one working
###      session, and a regression that has not been explained

A long day. Two genuine faults were found and fixed, one test path worked
end to end, and then stopped working, and the reason it stopped is still
open. Written up in full because the false leads are as instructive as the
findings.

**ROOT CAUSE 1: memory decode was never enabled.** Linux `lspci` showed
`Control: I/O- Mem- BusMaster-` and `Region 0 ... [disabled]`. With memory
decode off the endpoint ignores every memory transaction addressed to it,
the root complex gets no completion, and synthesises all-ones. That is
exactly the `0xFFFFFFFF` that had been read as "the FPGA isn't responding"
for days. It is a driver's job to set that bit; Intel's Windows driver
never does, and under Linux nothing had claimed the device. Fix on Linux:
`sudo setpci -s 08:00.0 COMMAND=0x0006`. From Windows the same thing is
possible via `AltPciWriteCfg` (see 6i).

Note for the record: `Command: 0x00000406` appeared in the very first
`Alt_Test.exe` dump of the whole investigation and was read as "memory
space + bus master enabled", which would have been fine. Whatever Windows
had set at that moment, the bit was clear later, and that early reading was
treated as settled rather than re-checked against the ongoing failure.

**ROOT CAUSE 2: the fabric's output pulse is unpollable.** With decode
enabled, reads returned real data (`0x0`, not all-ones) and writes landed
-- `CMD_DATA`/`CMD_BUS` read back `DEADBEEF`/`CAFEBABE` exactly, proving
address decode, byte lanes, and the whole host->fabric path. But
`STATUS_ADDR_VALID` still read 0. Reason: the output collector in
`top_arria10_zone1_v3.v` is an `always @(*)` block, so `out_valid` is
combinational and exactly one CLK cycle wide -- 40ns at 25MHz. A host
polling over PCIe arrives microseconds later and can never catch it. JTAG
got away with this because ISSP samples differently; a memory-mapped host
cannot. Fixed by adding sticky capture in `pcie_unicell_bridge.v`, latched
until explicitly cleared by writing to `REG_STATUS_ADDR_VALID`. Covered by
`tb_pcie_bridge_sticky.v`, which tests the case no existing testbench did:
a one-cycle pulse read 100 cycles later.

**A third fix, confirmed by evidence and then briefly reverted in error:**
the reset deadlock on `pld_core_ready`. `pio_bridge_0` drives that signal
(an output, per `pio_bridge_0.cmp`) but is itself held in reset by
`clr_st`, which the Hard IP won't release until `pld_core_ready` asserts.
Nothing starts. Symptoms: `reset_status` high, `rx_st_ready` low,
`rxstvalid` never asserting, while the link itself is healthy
(`ltssmstate = 0x0F` = L0). Driving `pld_core_ready` from
`w_serdes_pll_locked` -- outside the application reset domain, and Intel's
documented tie -- breaks the loop. The revert happened because a Windows
test returned all-ones and was read as the fix having failed; memory decode
was disabled in that test, so it would have returned all-ones regardless.
A worthless test was allowed to overturn a working result.

**Then it stopped working, and that is still open.** After the sticky latch
was added and the wrapper restored, the same procedure failed. `lspci`
comparison between the working session and afterwards shows the endpoint
advertising different capabilities:

| | working session | after |
|---|---|---|
| `LnkCap` speed | 8GT/s | 5GT/s |
| `LnkCap2` | 2.5-8GT/s | 2.5-5GT/s |
| `DevCap` MaxPayload | 256 bytes | 128 bytes |
| Secondary PCIe cap `[300]` | present | absent |

Those are static values from the IP configuration -- they do not change on
their own, and the BIOS cannot rewrite an endpoint's capability registers
(it can constrain negotiated speed in `LnkSta`, which is why the working
session showed 5GT/s negotiated against an 8GT/s capability, but that is a
different register). The Secondary PCIe capability only exists on
Gen3-capable endpoints, so its disappearance is the strongest single
indicator: the IP appears to have been regenerated as Gen2.

**Honest limit:** diffing the current `pcie_a10_hip_0.qsys` against
`fpga/ip-reference/` shows only the intended edits (BAR type, identity
fields) and reports payload 128 in both. So the on-disk config cannot
account for the working session advertising 256 bytes, and it is not
possible to establish from the available files *when* the IP changed. The
capabilities did change; the cause is inferred, not proven.

**First thing to check next session:** the IP editor's System Settings tab
-- link rate and maximum payload size. If they read Gen2/128, set them to
Gen3/256 to match what the working bitstream advertised, regenerate,
rebuild. If they already read Gen3/256, this explanation is wrong and the
regression is elsewhere.

**Also unresolved and worth doing regardless:** run `icm64_readstate.tcl`
over JTAG against the current bitstream. It exercises the fabric through a
path with nothing to do with PCIe. It was suggested twice during the day
and never actually run. If it fails, the problem is not PCIe at all and the
day's entire framing was wrong -- which is a five-minute test worth doing
before anything else.

### 6i. Practical mechanics learned the hard way

**Reprogramming over JTAG wipes the endpoint's config space**, because
config space is implemented in the reconfigured logic. That includes the
Command register *and* BAR0's base address. After a reprogram without a
reboot the card no longer decodes the address the host still thinks it
lives at, and every access reads all-ones -- indistinguishable from a dead
card. Either reboot so the BIOS reassigns, or write the values back
directly.

**Windows and Linux assign different BAR addresses.** On this machine
Windows chose `0xFC9FF000` and Linux `0xFC900000`. Hardcoding an address
observed under one and using it under the other overwrote a correct value
with a wrong one, and because config space persists until the next
reprogram, the bad value stayed put across several subsequent runs. The
test tool now takes the address as an argument and only writes it when the
caller supplies one. Get the real value from Device Manager (Resources tab)
or `lspci`. Do not guess it.

**Order matters when repairing config space.** `AltPciMapResource` reads
BAR0 to decide which physical address to map. Calling it before BAR0 is
valid produces a mapping that points at nothing, and fixing the BAR
afterwards does not repair a mapping already built. Correct order: open
device, fix Command register, fix BAR0, *then* map.

**`AlteraPCILibraryDll.dll` is 32-bit.** Building the test tool in an x64
Developer Command Prompt produces a 64-bit exe that cannot load it --
`LoadLibrary failed, error 193`. Use the **x86** Native Tools Command
Prompt.

**Status 0 from the DLL is not proof of anything reaching the wire.**
`AltPciWriteAddr32` returning 0 means the driver accepted the call.
SignalTap on `rxstvalid` showed no TLP arriving at the Hard IP across five
runs while every host write reported success. Trust the capture, not the
return code.

**Python's `mmap` slice assignment is not a 32-bit store.** It is a memcpy
and may split a word into byte writes. `pcie_unicell_bridge.v` ignores
`avs_byteenable` entirely, so each byte write clobbers the whole register
and only the last survives -- writing `0xDEADBEEF` lands as `0xDE000000`.
Use `ctypes` on a `c_uint32` array for genuine 32-bit accesses.

**Latent RTL bug, not yet fixed:** that `avs_byteenable` behaviour. Benign
for aligned 32-bit accesses, silently corrupting for anything partial.
Worth fixing.

**Also outstanding:** BAR2 is enabled in the Hard IP config (256 bytes,
64-bit prefetchable) and was never intended. Linux shows it at
`fffff00000`, effectively unassignable. Not implicated in any failure so
far, but it is a real misconfiguration and should be disabled.

### 6j. Tooling that now exists

- `pcie/unicell_pcie_test.py` -- Linux host test. Enables memory decode,
  verifies it stuck, probes the write path, runs the known-good sequence,
  decodes the result. Refuses to report all-ones as a fabric result.
- `pcie/unicell_pcie_celltest.c` -- Windows equivalent, via the Altera DLL.
  Reads and repairs Command register and BAR0 through `AltPciReadCfg`/
  `AltPciWriteCfg`. Being able to enable decode from Windows matters
  because SignalTap runs from Quartus over JTAG on Windows, so this is what
  makes it possible to drive the fabric and observe it simultaneously --
  impossible for most of this investigation.
- `pcie/tb_pcie_bridge_sticky.v` -- covers the one-cycle-pulse case.
- `fpga/ip-reference/` -- generated IP component and system files, checked
  in precisely so questions like "what did this parameter used to be" are
  answerable offline. Worth re-snapshotting after any IP regeneration; they
  go stale silently and one of them was already stale when needed.

---

## 7. The fault is NOT in PCIe (2026-07-27)

> **RULE: reboot after every reprogram, before any PCIe test.**
>
> JTAG reprogramming wipes the endpoint's config space -- BAR0's base
> address and the Command register both go to zero -- because config space is
> implemented in the reconfigured logic. It also drops the link, which
> retrains, but the root port above does not re-enumerate.
>
> The result is that the card decodes nothing, and every access returns
> `0xFFFFFFFF`: **a symptom indistinguishable from a dead card or a broken
> design.** This cost real time twice on 2026-07-26/27, including one case
> where a working change was reverted on the strength of a test that was
> invalid for exactly this reason.
>
> So: program, then reboot, then test. A full restart lets the BIOS
> enumerate cleanly and assign the BAR itself, which is the known-good
> state.
>
> The alternative -- restoring BAR0 by hand with `unicell_pcie_celltest.c`
> and an explicit address -- exists only so a test can run while SignalTap
> captures over JTAG, which a reboot would interrupt. Use it for that and
> nothing else, and read the address from Device Manager or `lspci` first.
> Never reuse an address from a previous boot: Windows and Linux assign
> different ones on the same machine.


**The pivotal finding, and it reframes all of section 6.** Running
`fpga/icm64_readstate.tcl` -- which drives the *identical* command sequence
over JTAG/ISSP, a completely separate path from PCIe -- fails in exactly the
same way:

```
cycle_count: 4042334226 -> 4044784369   OK (snapshot live, fabric clocking)
cmd_latch[31:0] = 0x00000000   (topology[9:0]=0x000  armed=0)
input_addr      = 0x0100
output_addr     = 0x0001
out_seen=0 out_addr=0x0000 out_data=0x00000000 out_count=0 armed_count=0
```

`SET_OUTPUT_ADDR 0x200` did not take (`output_addr` reads `0x0001`),
`RECONFIGURE` did not take (`cmd_latch` is zero, `armed=0`), nothing fired.
**The fabric is not accepting commands over ANY path.** The design is alive --
`cycle_count` ticks, so it is clocked and the snapshot readback works -- it
simply ignores commands.

Everything in section 6 was therefore chasing a symptom. That work was not
wasted (the driver INF bug, the IP identity fields, the BAR type, the
memory-decode discovery and the reset deadlock are all real and all needed
fixing) but none of it was why the sequence never produced a result.

### 7a. Where to look next

Both JTAG and PCIe reach the fabric through the same three-master arbiter in
`top_arria10_zone1_v3.v`:

```verilog
wire [31:0] cpu_bus  = j_valid ? j_bus  : (p_valid ? p_bus  : u_bus);
wire        cpu_valid = j_valid | p_valid | u_valid;
```

A common cause fits far better than two independent faults. The OR on
`cpu_valid` is the exposed part: if any master asserts spuriously, the fabric
sees a continuous stream of whatever that master has on its bus, and latched
state (`SET_TARGET`, and `cmd_latch` contents) gets trampled between
legitimate commands. That is precisely the observed symptom.

Candidates, cheapest first:

1. **`u_valid` from `uart_bridge`, driven by the `UART_RX` pin.** If that pin
   is unassigned or floating, the UART receiver will decode noise into
   spurious commands. Check for a pin assignment and a defined idle level.
   HYPOTHESIS ONLY -- not yet investigated.
2. **`p_valid` from `pcie_unicell_bridge`** -- checked and ruled out by
   inspection: `cpu_valid` there is a one-cycle pulse, resets to zero, and can
   only assert on `avs_write`.
3. **A regression.** `icm64_readstate.tcl` is believed to have passed
   previously. The commit that introduced the third master is `210d45e`
   ("Wire pcie_unicell_bridge into top_arria10_zone1_v3.v as a third cpu_bus
   master"). Rebuilding an earlier top level and re-running the script would
   settle whether this is a regression and bound where it entered.

### 7b. Method note

This took far too long to find because the JTAG path was assumed working and
never re-tested against the current bitstream. It is a known-good reference
that costs one script run. Running it FIRST would have shown immediately that
the problem was not PCIe-specific.

**Test the independent path before investigating the suspect one.**

### 7c. Loose ends found along the way

- **BAR2 is enabled and shouldn't be.** `pcie_a10_hip_0.qsys` has
  `bar2_address_width_hwtcl = 8`, 64-bit prefetchable. It appears in Windows
  Device Manager at `FFFFFFFFFF00`, an unassignable address. Disable it.
- **`avs_byteenable` is ignored** in `pcie_unicell_bridge.v` -- the write path
  assigns the whole register unconditionally. Harmless for aligned 32-bit
  access, silently corrupting for anything partial.
- **JTAG reprogramming wipes config space**, including BAR0's base address,
  because config space lives in the reconfigured logic. After a reprogram
  without a reboot the card decodes nothing until either a reboot or an
  explicit BAR restore. `unicell_pcie_celltest.c` can restore it, but the
  address must be passed in -- read it from Device Manager or `lspci`. Do not
  guess: a wrong address produces a symptom identical to a dead card, and it
  cost several runs here.
- **Windows and Linux assign different BAR addresses** on the same machine
  (`0xFC9FF000` vs `0xFC900000` observed). Always read the current value
  rather than reusing one from a previous boot.
- **The Windows DLL can write config space** (`AltPciWriteCfg`, export 19).
  That is what makes it possible to enable memory decode and run a test while
  SignalTap captures over JTAG -- driving and observing at the same time,
  which was impossible for most of this investigation.

### 7d. Candidate 1 (UART_RX floating) -- fixed at RTL level, awaiting silicon retest

Checked all four `.qsf` files in the repo's history
(`Unicell-Q.qsf`/`Unicell-Q64.qsf`/`Unicell-Q-zone1.qsf`/`Unicell-Q-zone1-v3.qsf`):
`UART_RX` has NEVER had a `set_location_assignment` or a pull-up/pull-down
assignment, in any build, ever. On silicon this is a floating input with no
defined idle level -- exactly the precondition needed for the RX state
machine (`uart_bridge.v`, state 0: `if (!uart_rx) ...`) to decode noise as a
start bit and eventually assemble a spurious `cpu_valid` pulse.

Caveat worth keeping honest: this has been unassigned in every build,
including ones that silicon-confirmed correctly (cardinals, `#32` wired-OR).
So this is not obviously introduced by the third (`p_valid`) master -- it may
be a latent hazard that simply never glitched during those shorter,
single-command tests, or the Fitter happened to park it on an electrically
quiet pin. Candidate 3 (the `210d45e` regression check) is NOT closed by
this finding; it stays open in parallel.

**Fix applied:** `top_arria10_zone1_v3.v`'s `uart_bridge` instance now ties
`uart_rx` to constant `1'b1` instead of the `UART_RX` port, removing the
floating input from the design by construction rather than relying on board
electrics. The `UART_RX` top-level port itself is left in place (unused) for
when real UART hardware exists -- reverting requires reconnecting it AND
adding a `.qsf` pin assignment with `WEAK_PULL_UP_RESISTOR ON`, not just
undoing this one line.

**Sim verification:** new standalone testbench `tb_uart_bridge_idle.v` drives
`uart_bridge` with `uart_rx=1'b1` for 200,000 cycles (several full sweeps of
the RX startup counter) and confirms `cpu_valid` and `array_rst` never
assert. PASS.

**Full mux regression (2026-07-28, completed):** the existing
`tb_top_arria10_pcie_silent.v` / `tb_top_arria10_pcie_mux.v` initially could
not run in this sandbox -- they need the real Quartus-generated
`pcie_a10_hip_0` / `pio_bridge_0` IP, which don't exist as plain-Verilog sim
models outside a Quartus/ModelSim install. Alan pulled the real generated
`pcie_a10_hip_0.v` (ACDS 25.1) from the live project and uploaded it; its
exact port list (names + widths, not guessed) was used to write
`tb_stub_pcie_a10_hip_0_sim_only.v`, a SIM-ONLY blackbox with every output
tied to constant 0 (including `coreclkout_hip`, so the PCIe-side clock
domain never toggles -- consistent with "no real Hard IP driving anything").
The repo's existing `fpga/ip-reference/pio_bridge_0.cmp` (VHDL component
declaration, already committed) supplied the same for
`tb_stub_pio_bridge_0_sim_only.v`. Both follow the same SIM-ONLY convention
as the pre-existing `tb_stub_issp_sim_only.v`.

With both stubs in place, both testbenches now elaborate and PASS:
- `tb_top_arria10_pcie_mux.v`: full UART/JTAG/PCIe arbitration priority
  behavior unchanged (all 9 checks pass) with the `uart_rx` tie-off in place.
- `tb_top_arria10_pcie_silent.v`: `p_valid` stays silent throughout --
  confirms the PCIe wiring remains a true no-op with the UART fix applied.

This closes the "couldn't re-run the full regression" gap noted earlier.
Note the honest limit of what this proves: these stubs model zero HIP
behavior, so this confirms *structural* non-interference (the UART fix
doesn't perturb the mux/arbiter), not real PCIe functional simulation --
that still requires actual silicon or Quartus/ModelSim's own IP sim flow.

**Next real test:** rebuild + reflash + `icm64_readstate.tcl` (reboot first,
per §7e/procedural rule). If commands are now accepted, candidate 1 was the
cause. If not, move to candidate 3 (checkout pre-`210d45e`, rebuild, rerun
the same script) to bound whether this is a regression at all.

### 7e. CONFIRMED (2026-07-28) -- candidate 1 was the cause, fabric accepts commands again

Rebuilt with the `uart_rx` tie-off (commit `1c5ea5e`), reflashed, rebooted,
ran `fpga/icm64_readstate.tcl`. Direct comparison against the 7/27 failing
run:

```
                    BEFORE (broken)          AFTER (fixed)
cmd_latch           0x00000000, armed=0      0x0440a02c, armed=1
output_addr         0x0001 (didn't take)     0x0200 (exactly as set)
out_seen/out_count  0 / 0                    1 / 1
out_data            --                       0x000000aa
armed_count         0                        25
```

`RECONFIGURE` landed, `SET_OUTPUT_ADDR 0x200` landed exactly, the cell
fired, output captured with matching address/data, `armed_count=25`
matches the known 25-cells/zone single-zone fit. `a_data` also carries the
`0xDA7A` debug-view marker correctly, so this isn't a readback artifact --
the fabric is genuinely executing commands again.

**Candidate 1 (floating `UART_RX`) confirmed as the cause.** The floating
pin was corrupting `cpu_valid` via the three-master OR exactly as
hypothesized in §7a. Candidate 3 (the `210d45e` regression check) is now
moot -- no need to bound it further since the actual fix works.

This closes the "fabric ignores commands over both JTAG and PCIe" finding
from 2026-07-27. Next step per PLAN.md Step 1: resume the live BAR
read/write test over PCIe now that the underlying fabric-acceptance bug is
gone -- replay the `icm64_readstate.tcl` command sequence over PCIe itself
(not just JTAG) to close Step 1 for real.

## 8. Testing roadmap for this stage (post-UART-fix, pre-Step-1-close)

One JTAG pass proves the fix works once. Before calling Step 1 closed, this
maps the sequence worth running -- ordered cheapest/most-informative first,
each gating whether the next is even needed. None of these require new RTL;
they're all re-runs of existing scripts/tools in different combinations.

### 8a. Repeatability on the known-good path (JTAG) -- do this first
Run `icm64_readstate.tcl` several times back-to-back, no reprogram between
runs. The fix is a hard tie to a constant (`1'b1`), not a probabilistic
pull-up, so this *should* be fully deterministic -- but "should be" is a
hypothesis, and confirming clean results across repeated runs is nearly
free and rules out "got lucky once." A single flaky run here would be a big
deal (would mean candidate 1 isn't the whole story), so this is worth
doing before touching PCIe at all.

**CLOSED (2026-07-28).** `icm64_readstate_loop.tcl` (25 iterations, one
JTAG session, no reprogram/reboot between): **25/25 passed, 0/25 failed.**
Fully deterministic, exactly as expected for a hard constant tie rather
than a probabilistic pull-up. No lingering doubt about "got lucky once."

### 8b. Broader opcode coverage (JTAG) -- still cheap, still no PCIe needed
`icm64_readstate.tcl` only exercises `RECONFIGURE` + `SET_OUTPUT_ADDR` +
readback -- three of `unicell64_v3.v`'s 56 opcodes. The floating pin could
plausibly have corrupted some command paths more than others (depends on
what garbage happened to land on `cpu_bus`), so a clean result on this one
script doesn't guarantee every opcode is healthy. Before declaring the
fabric fully trustworthy again, worth a quick pass on a few more that are
either already scripted or cheap to add:
  - `CMD_ARRAY_RESET` (opcode 8) -- already silicon-proven earlier, good
    regression check to confirm it's still clean post-fix.
  - freeze/release (UART's own 0x06/0x07, still relevant since they go
    through `array_freeze`, separate from `cpu_valid` but worth touching).
  - `DATA_WRITE` and `LOAD_AT` -- different from `RECONFIGURE`'s auth path,
    good coverage of the auth-gated vs non-auth-gated command split.
  - The `#37` loop_back+latch_in+MEM_CALL composition, if a script for it
    already exists -- it's the most "interesting" cell behavior on record
    and a good canary for anything subtly still wrong.
This can piggyback on the already-queued "systematic opcode/flag
combination audit" (PLAN.md, priority/trace/breakpoint flagged as first
unknowns) rather than being a separate effort.

### 8c. The actual Step 1 close -- PCIe BAR read/write replay
The real target. Replay the same `icm64_readstate.tcl`-equivalent command
sequence over PCIe instead of JTAG (Windows DLL / `AltPciWriteCfg` path, or
the Linux `setpci` + Python ctypes/mmap path -- whichever is faster to
stand up again). Mechanics that already cost time once, don't relearn them:
  - **Reboot before testing**, every time, after any reprogram -- config
    space including BAR0 gets wiped by JTAG reprogramming, and a wipe
    looks identical to "still broken."
  - **Enable memory decode** explicitly (Intel's Windows driver never does
    this automatically -- confirmed cause of the earlier false-negative
    BAR reads). `setpci -s <bus>:00.0 COMMAND=0x0006` on Linux, or the
    Windows DLL's `AltPciWriteCfg` equivalent.
  - **Read the current BAR0 address fresh** (Device Manager or `lspci`)
    rather than reusing a value from a previous boot -- Windows and Linux
    have been observed to assign different addresses on the same machine.
  - Config repair must happen BEFORE `MapResource`, not after.
  - If reads still fail here after all of the above, that's now a genuine
    PCIe-specific finding rather than a symptom of the fabric-acceptance
    bug -- the two are finally properly separated for the first time.

### 8d. Arbitration under real concurrent load (stretch, do if 8c passes)
`tb_top_arria10_pcie_mux.v` already sim-proves the priority order
(JTAG > PCIe > UART) with driven stimulus, but that's simulation with a
stub Hard IP -- it's never been exercised with two REAL masters live on
silicon at once. Once 8c confirms PCIe alone works, worth trying to drive
commands from JTAG and PCIe close together in time (even just
back-to-back scripts, not true simultaneity) to build confidence the
arbiter's real-silicon behavior matches what sim predicts, now that a
second master actually has something to say.

### 8e. Standing design rule (process fix, not a test, but belongs here)
Add to `ARCHITECTURE.md` or `START.md`'s discipline section: **any unused
top-level input pin must be tied to a defined constant or an explicit pull
in the .qsf, never left with no assignment at all.** This bug sat latent
since the UART bridge was first added, unnoticed because it was arguably
never really used or exercised before this stage. If a fourth bus master
or any other bridge gets added later, this rule is cheap insurance against
the same class of bug recurring silently.

### 8f. Not recommended right now
A "negative control" -- deliberately re-introducing a floating pin on a
spare unused I/O to confirm the corruption reappears -- would be the
strongest possible scientific confirmation, but the causal chain here is
already solid (mechanism identified in the RTL, confirmed absent in every
.qsf ever, before/after silicon comparison matches the hypothesis exactly)
and this would cost hardware time without adding real doubt-resolution.
Skip unless 8a-8c produce a genuinely confusing result that reopens the
question.

### 8g. CMD_FREEZE/CMD_RELEASE mid-loop test (2026-07-28, sim-verified)

Alan's framing reset the approach here: CMD_FREEZE was designed for
programming and error-state use, not mid-computation stalling -- the real
risk is a LOOP GROUP, where freezing at different phase offsets relative
to the loop's own trigger timing could reveal a corrupted or partial fire
that a simple single-shot test would never catch.

**First attempt (3-cell linear chain, A->B->C) was abandoned, not fixed.**
It hit a genuine testbench bug -- `bus_addr` for the downstream cells was
driven by BOTH an auto-forwarding always-block (chain wiring) AND the
command-targeting tasks, a multi-driver conflict that produced
unpredictable results (baseline propagation failed before freeze was even
tested). Rather than debug that further, dropped to the smaller test this
project's own discipline calls for.

**Second attempt (single self-looping cell, `loop_back`+`latch_in`) is
the right minimal test** -- no auto-forward wiring needed at all, since a
loop only has one bus_addr line. Configured as a running XOR accumulator:
each external trigger B_k computes `a_data_k = a_data_(k-1) XOR B_k`, easy
to predict by hand instead of needing multi-cell address-chain semantics.

**Found and fixed a real bug getting there:** `loop_back` lives at
`cmd_data[22]`, which falls inside `cmd_data[30:20]` -- the exact range
`CMD_LOAD_AT` also writes to `auth_mask` while a cell is still in
`physical_mode` (boot state). Setting `loop_back` in the same `LOAD_AT`
that's still in `physical_mode` silently corrupts `auth_mask` to a
non-zero value, which then breaks `auth_ok` (`auth_boot = auth_mask==0`)
for every later command including `CMD_FREEZE` -- diagnosed by adding
`dbg3.v`, a minimal isolated harness, and reading `auth_mask` directly
after arming (came out `0x004`, non-zero, explaining why `frozen` never
asserted). Fixed by issuing `CMD_BOOT_COMMIT` (cmd_data=0, keeps
auth_mask=0) between two `LOAD_AT`s -- first without `loop_back`, then a
second with it added once `physical_mode` is 0 and the auth-write branch
is inactive. **Worth a standing note for anyone hand-building `LOAD_AT`
payloads in physical_mode: any bit in `cmd_data[30:20]` is live-wired to
auth_mask, whether you meant it to be or not** -- this also applies to the
bank-2 methodology fields (`cmd_data[30:23]`), which share the same
danger zone.

**Result (`tb_freeze_loop_v3.v`): 19/19 checks PASS.** Two phase variants
tested:
  - Phase A: freeze issued well-separated (3+ cycles) before the next
    trigger attempt.
  - Phase B: freeze and the next trigger issued back-to-back, minimal
    gap -- the timing-adjacent case Alan specifically flagged.

Both phases show identical behavior: `a_data` (the loop_back accumulator
state) is bit-for-bit unchanged by an attempted trigger while frozen, no
spurious fire occurs, and after release the accumulator resumes correctly
from the pre-freeze value -- the dropped trigger contributes nothing, and
critically, doesn't corrupt anything either. No phase-dependent
corruption found in sim.

**Honest scope of what this proves:** this is RTL-level sim confirmation
under directly-driven stimulus timing, not real silicon under an actual
JTAG/PCIe command cadence (which has its own multi-cycle latencies, per
§7's whole saga). If freeze/release testing ever moves to actual hardware
(8b touched on this originally), the same phase-variation idea applies
there too -- vary how close together the freeze and the next real command
land, don't just test one timing.

## 9. §8c (PCIe BAR replay) run -- isolated to upstream of the FPGA, not an RTL bug (2026-07-28/29)

Attempted the actual Step 1 close (§8c): replay `icm64_readstate.tcl`'s
known-good sequence over PCIe via `unicell_pcie_celltest.exe`, after the
uart_rx fix was already confirmed clean on JTAG (25/25, §8a) and the
freeze/loop_back sim work (§8g) was done. Result: **BAR0 reads/writes
return `0xFFFFFFFF` on every attempt**, including a raw register probe
(`DEADBEEF`/`CAFEBABE` written, `FFFFFFFF` read back) that never even
reaches the fabric's command sequence.

**Ruled out, in order, each confirmed clean:**
- Memory decode: `Command register = 0x0406` -- bit 1 (Memory Space) and
  bit 2 (Bus Master) both already enabled.
- BAR0 address: `0xFC9FF000`, matches Device Manager exactly, no stale
  value from a previous boot.
- `pcie_hip_wrapper.v`'s `pld_core_ready` fix: Alan's compile-folder copy
  diffed byte-identical against the repo's fixed version
  (`pld_core_ready(w_serdes_pll_locked)`), so this isn't a stale-file
  regression of the earlier reset-deadlock fix.
- `pcie_a10_hip_0.qsys` IP parameters: also diffed byte-identical against
  the repo's archived reference -- BAR0 still `32-bit non-prefetchable`,
  device/revision/subsystem IDs still the real (non-zero) values, so the
  IP config didn't silently revert either.
- Link training: Alt_Test.exe reports `Lane Rate: 2` (Gen2, 5.0GT/s),
  `Link Width: 08` (full x8) -- identical to the originally-confirmed good
  link. Real, non-zero Device ID (`0x2494`), Subsystem Vendor/Device IDs
  (`0x180c`/`0x660a`) all present and correct in the full config-space
  dump.
- Fabric health (JTAG, same moment): `icm64_readstate.tcl` re-run
  independently during this same investigation -- `armed=1`,
  `output_addr=0x0200`, `out_seen=1`, `armed_count=25`, identical to the
  post-fix confirmed-good pattern. The fabric itself is not the problem.

**SignalTap capture (post-fit, `sync_rst`/`reset_status_hip`/`pll_locked`/
`ltssmstate`/`rx_st_*`/`rxstbardec1`/`rx_st_bar_hit_o`, run live during
`unicell_pcie_celltest.exe`):**
- `pll_locked=1`, `pcie_perst_n~input=1` (deasserted), `ltssmstate[3:0]`
  all high (an active/late LTSSM state, not stuck in early training),
  `txstready=1`, `rx_st_ready=1` -- the application interface genuinely
  is out of reset and ready to receive. The reset-deadlock theory that
  explained the ORIGINAL version of this symptom (07-26/27 session) is
  NOT what's happening this time -- that fix is holding.
- `rx_st_valid_r`, `rx_st_bar_hit_o`, `rxstvalid[0]`, and all six
  `rxstbardec1[5:0]` bits: **flat low for the entire capture window.**
  Not "decoding the wrong BAR" -- zero TLPs of any kind ever reached the
  Hard IP's own RX decode logic during the whole celltest run.

**Cross-check: ran Intel's own `Alt_Test.exe`** (not just the
project-authored celltest tool) against the same card/slot -- identical
config-space dump (same Lane Rate/Width, same IDs), and its own internal
BAR0 clear/write self-test fails the exact same way
(`Data == 0xffffffff`). Two independently-written tools, same failure, at
the same layer.

**Conclusion: this isolates to somewhere upstream of the FPGA entirely --
not an RTL bug, not a regression of anything fixed this session.** The
link negotiates, config space is fully readable, the application
interface is out of reset and ready, and still literally no memory TLP
ever arrives at the endpoint's decoder. That combination (link-layer
healthy, zero transaction-layer traffic, reproduced by a second
independent tool) points at something in the host/slot/BIOS, not the
bitstream:
  - **IOMMU/VT-d** -- most likely candidate. Link/config-space access can
    go through the root complex more directly; DMA/MMIO remapping for an
    unofficial device without a real driver is exactly the kind of thing
    that would silently drop memory TLPs while leaving config space and
    link training untouched.
  - **"Above 4G Decoding"** BIOS setting -- some chipsets route BAR
    memory differently for devices with non-standard capability
    structures depending on this.
  - **A different physical PCIe slot**, if available -- tests whether
    this is root-port/ACS-specific rather than device-specific.
  - Windows Device Manager, checked directly for any resource-conflict
    flag that wouldn't block `AltPciOpenDevice` but could still indicate
    a mapping problem.

**Practical implication for the project:** the fabric, the uart_rx fix,
and the freeze/loop_back sim work are all still trusted good -- nothing
here reopens any of that. PLAN.md Step 1's remaining item (live PCIe BAR
replay) is now blocked on a host/BIOS-level investigation, not further
RTL or bitstream work, until one of the above is tried and either clears
the symptom or further localizes it.
