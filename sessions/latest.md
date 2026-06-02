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

