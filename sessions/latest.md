# Session Log — 2026-06-02 (session 3 - long day)

## Status at session end
Last commit: d1cb01b — unicell_xdma.py MMIO tool
Suite: 28/28, 101 compiler_int32 tests

---

## Hardware Progress

### Kintex-7 PCIe Bring-up
- Card enumerates on PCIe: `01:00.0 Xilinx Corporation Device 7028` ✅
- PCIe link: Gen1 x8, 2.5GT/s ✅
- XDMA driver loaded: `/dev/xdma0_user`, `/dev/xdma0_control` ✅
- `unicell_xdma.py info` returns data from fabric ✅

### XDMA Configuration Issues Found (need re-synthesis)
1. **AXI-Lite BASEADDR = 0x1000** — bridge mapped at 0x1000-0x1FFF
   Our tool reads offset 0x00 which is BELOW the window → all zeros
   Fix: `set_property CONFIG.BASEADDR 0x00000000`
   Fix: `set_property CONFIG.HIGHADDR 0x0000FFFF`
2. **axilite_master_size already changed to 16KB** ✅
3. **cmd_bus pipeline register** added to unicell_zone.v ✅
   Should close 125MHz timing (WNS was -2.7ns without it)

### Re-synthesis in progress
Changes: BASEADDR/HIGHADDR fix + pipeline register + BAR size
After this run: bridge should respond with 0xDEADBEEF at default offset

---

## Routing History (today)
- Multiple failed runs: IBUFDS_GTE2 LOC missing, CONTAIN_ROUTING blocking nets,
  Pblock overutilisation, unrouted nets in z01 cells 9/10
- Final successful route: removed CONTAIN_ROUTING, 0 failed nets ✅
- WNS = -2.7ns at 125MHz (pipeline register fix should close this)
- Bitstream flashed to BPI flash, card boots from flash ✅

---

## Software Progress

### unicell_xdma.py
New MMIO tool using pread/pwrite directly on /dev/xdma0_user
Commands: info, reset, dump, peek, poke
No ioctl, no kernel module beyond xdma driver

### docs/benchmarks/README.md
8 target benchmark papers documented:
1. Fractional hyperbolic PDE (Macias-Diaz)
2. Type I error probability (Novoa-Munoz)
3. Calderon problem / complex parallel transport (Cekic)
4. Massively parallel SAT solving (Heule)
5. Parallel graph neural dynamics (PGNDL/D-METIS)
6. System reliability via algebraic inequalities (Todinov)
7. Dense linear algebra parallel programming (Dongarra et al)
8. Parallel multibody dynamics (Negrut et al)

### docs/math_frontend_design.md
Full design for MathTrix mathematical frontend:
- Architecture: SymPy → pattern library → existing compiler
- Pattern library: Laplacian stencil, inner product, threshold etc.
- Float support: pairs/triplets, no new hardware needed
- 9 demo problems (Gray-Scott, Ising, Wave, PageRank, etc.)
- UI design mirrors composer workflow
- Researcher outreach strategy documented

---

## Next Session

### Immediate (when re-synthesis finishes)
1. Flash new bitstream
2. Test `sudo python3 pcie/unicell_xdma.py info` → expect 0xDEADBEEF
3. If bridge responds: configure a cell, inject data, read output
4. That's the first live cell test on hardware

### After first live cell test
- Scale up cell count (currently 200, target 500+)
- Python unicell_xdma.py configure/inject/read commands
- Connect VM compiler output to hardware via DMA
- MathTrix frontend development

### XDMA IP settings confirmed
- BASEADDR: 0x00000000 (fixed)
- HIGHADDR: 0x0000FFFF (fixed)  
- axilite_master_size: 16KB
- bar_indicator: BAR_0 → /dev/xdma0_user
- Link: Gen1 x8


## Update — Reset issue found

Cycle counter stuck at 0 — XDMA `axi_aresetn` never asserts.
Root cause: `sys_rst_n = SYS_RSTN & pcie_perstn` — SYS_RSTN on pin R28
connected to SW2 button, which appears to be active-low or floating by default.

Fix committed (38852d9): removed SYS_RSTN from sys_rst_n, now just pcie_perstn.
Added PULLUP on SYS_RSTN in XDC as safety measure.

Evidence:
- Bridge write/read working (0xA5A5A5A5 round-trip confirmed) ✅
- All BAR0 status registers return 0 (bridge in reset)
- Cycle counter stays 0 regardless of SW2 state
- TiferKing reverse engineering page confirms SW2→R28→GPIO
- Their example XDC has no PULLUP on SYS_RSTN

Next: re-synthesise with SYS_RSTN removed from reset. Should be fast
(incremental flow, only one line changed in Verilog).

## Update — New bitstream broke PCIe enumeration

After flashing reset-fix bitstream (SYS_RSTN removed):
- Card stopped enumerating on PCIe — invisible to BIOS
- Green power LED on, red config error LED appeared briefly
- Readback confirmed flash programmed correctly
- Re-flashed with old top_xdma_unicell.mcs (27/05) — card recovered

**Root cause theory:** WNS = -2.594ns timing violation on PCIe paths.
PCIe link training requires very precise timing — a 2.6ns violation on
the PCIe core's internal paths could cause link training failure,
making the card invisible to the system.

**Fix for next run:**
1. Drop clock to 100MHz (change constraint from 8ns to 10ns period)
2. Pipeline register already in for cmd_bus fanout
3. Together should give clean timing closure with margin

Next session: re-synthesise at 100MHz, flash, confirm PCIe comes back,
then test cycle counter.
