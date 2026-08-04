# Imago UniCell — Project Progress

A running log of significant milestones across all sessions.

---

## Architecture & Theory

- **2023-2024** — Core concept developed: NOR-universal reconfigurable cell,
  computation fabric-native rather than Von Neumann sequential. Wired-OR bus
  arbitration through physics. Gate state is a register; computation happens
  in place without data movement.

- **Two-arrival model** established: first arrival stores in `a_data`, second
  arrival triggers gate computation. Eliminates need for delay cells.
  `sync_wait` flag repurposed to implement naturally.

- **Preloaded-A pattern** adopted: Python forward simulation pre-computes A
  values, writes directly into op cells before execution. B injected as single
  trigger wave. Validated on comparator, generalised to all compiled functions.

---

## Python VM & Compiler Stack

- **IR + compiler pipeline** complete: full IR, compiler, INT32 operations,
  MUX, branching.

- **Kogge-Stone adder**: 19 cells (packed shift-chain) vs 12,931-cell
  ripple-carry. 682× improvement.

- **INT32 operations**: ADD/SUB/EQ/NEQ/LT/GT/LTE/GTE all passing.
  AND/OR/NOT, MUX 4/4.

- **Zero-compare fast path** (2026-06-02): OR-reduction tree, 32-34 cells
  vs 523 for LT_S tile. All 6 ops + commuted forms.

- **load(A)/run(B) API**: compile once, run many times with different B.
  All 8 ops, 100 random pairs each.

- **Test suite**: 28/28 suite runner, 101 compiler_int32 tests.

---

## FPGA — iCEBreaker (iCE40UP5K)

- **4-cell hardware validation** at 12 MHz. Bitstream obtained via iceprog.
  Two-arrival model confirmed on silicon.

- **unicell_v3.v**: `one_shot`/`loop_back` bits (30-31), `bus_hit`
  pre-registered for fan-out prep.

---

## FPGA — Kintex-7 XC7K480T (YPCB-00338-1P1)

- **Hardware acquired**: XC7K480T-2FFG1156I, PCIe x8, 18× DDR3 ECC,
  512Mb BPI flash.

- **Vivado project retargeted** from Virtex-7 to correct xc7k480tffg1156-2.

- **First successful synthesis** (2026-06-02): 200 cells (4 zones × 50),
  ~20% LUT utilisation, 0 errors.

- **First fully routed implementation** (2026-06-02): 0 failed nets,
  WNS = -2.594ns at 125MHz. Timing violation from cmd_bus fanout.

- **Bitstream flashed to BPI flash** (2026-06-02). Card boots from flash. ✅

- **PCIe enumeration** (2026-06-02): `01:00.0 Xilinx Corporation Device 7028`,
  Gen2 x8 link. ✅

- **XDMA driver loaded** (2026-06-02): `/dev/xdma0_user`,
  `/dev/xdma0_control` present. ✅

- **Bridge write/read confirmed** (2026-06-02): 0xA5A5A5A5 round-trip
  via `/dev/xdma0_user`. Bridge is alive. ✅

- **Reset issue identified** (2026-06-02): `SYS_RSTN` on R28 (SW2 button)
  floating/low, holding XDMA in reset. Cycle counter stuck at 0.
  Fix: remove SYS_RSTN from sys_rst_n, use only pcie_perstn.
  Re-synthesis in progress.

---

## Software Tools

- **unicell_xdma.py**: MMIO tool for XDMA BAR0 (pread/pwrite, no ioctl).
  Commands: info, reset, dump, peek, poke.

- **unicell_tool.py**: original tool (ioctl-based, for future unicell.ko driver).

---

## Documentation

- **docs/benchmarks/README.md**: 8 target benchmark papers covering major
  parallel computing domains. MathTrix demo library (9 problems).
  Researcher outreach strategy.

- **docs/math_frontend_design.md**: MathTrix mathematical frontend design.
  Pattern library, float/complex support via pairs/triplets, UI design.

- **docs/BRANCH_DECISION_TREE.md**: PTT dispatch model, branch architecture.

---

## Next Milestones

- [x] PCIe enumeration confirmed — Gen2 x8, XDMA driver, BAR0 bridge working ✅
- [ ] **Card failed** — timing violation stressed PCIe interface, new card ordered (~6 weeks)
- [ ] Cycle counter running (pending timing closure on new card)
- [ ] First live cell configuration and fire on hardware
- [ ] Connect Python VM compiler output to hardware via DMA
- [ ] cmd_bus pipeline register timing closure at 125MHz
- [ ] DDR3 MIG integration (staging area for large datasets)
- [ ] MathTrix frontend — first pattern (Laplacian stencil / Ising model)
- [ ] Scale cell count beyond 200
- [ ] Researcher demo package (personalised per benchmark paper)

---

*Last updated: 2026-06-03*
