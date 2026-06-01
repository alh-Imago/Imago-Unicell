# Session Log — 2026-06-02

## Status at session end
Last commit: 48cdc44 — 2x2 zone grid: 4 zones × 50 cells, 4 bridge lanes, ~20% LUT
Kintex-7 implementation running overnight (routing phase 4, expected WNS ~-0.6ns)
Suite: **28/28** (101 compiler_int32 tests)

---

## What happened

### Zero-compare fast path (earlier in session)
- See previous session notes — committed as 3e248d1

### Kintex-7 FPGA bring-up
- PCIe enumeration confirmed — JTAG cable was interfering, unplug JTAG to enumerate
- Retargeted Vivado project from Virtex-7 to correct xc7k480tffg1156-2
- Built and iterated through several zone grid configurations:

#### Run 1: 16-zone 2×8 grid, 28 cells/zone (top_xdma_unicell_zones.v)
- Multiple-driver DRC — clamped index trick caused zone 7 east output to drive
  same wire as zone 0. Fixed with unique scratch wires.
- Pblock coordinates wrong (estimated X0-X479, actual X0-X92)
- Disabled Pblocks, let free-place run to get real die coordinates
- Result: WNS=-3.038, routed successfully, floorplan showed real die layout
- Real die: X0-X92, Y0-Y377 (93 cols × 378 rows)

#### Run 2: 16-zone 2×8 grid, 24 cells/zone, calibrated Pblocks
- UTLZ errors — each zone needs ~13K LUTs but regions only have ~9K
- Die has BRAM/DSP columns breaking up SLICE grid unevenly
- Failed at place_design DRC

#### Run 3: 2×2 grid, 4 zones × 50 cells, 4 bridge lanes (current)
- 200 cells total, ~20% LUT utilisation
- Pblock DRC clean — 0 errors ✅
- Synthesis: 0 errors, ~120K LUTs, 12 mins
- phys_opt: WNS improved from -4.346 → -2.628
- Dont Touch: 130 (cmd_bus fanout across Pblock boundaries)
- Routing running overnight — expected WNS ~-0.6ns based on prior runs
- Hold violations appeared: WHS=-0.485 (same root cause as setup)

### Known fix for next run
- Add per-zone cmd_bus pipeline registers in Verilog
- One register stage at each zone input before fanout to 50 cells
- Eliminates cross-boundary fanout, fixes both setup and hold violations
- Should close timing at 125MHz (original target was 25MHz!)

### Side conversations / ideas noted
- UniCell Security Module: fabric topology as root of trust, rolling auth
  on randomised reboots, biometric phone+NFC token (saved to memory)
- Routing fabric in UniCell: cells as switch nodes, address-matched
  propagation, physics-based arbitration — traffic management, network
  switching applications
- Tri-state transistors / mutable transistors as future silicon direction
  — third state could unify computation and configuration in same device

---

## Next session

### Immediate
1. Check overnight routing result — WNS and hold status
2. If timing violated: add per-zone cmd_bus pipeline registers
3. If timing closed: write bitstream, flash card, test PCIe enumeration

### Pblock coordinates (confirmed from free-placement run)
- Die: X0-X92, Y0-Y377
- Z00: SLICE_X0Y189:SLICE_X45Y377   (top-left)
- Z01: SLICE_X46Y189:SLICE_X92Y377  (top-right)
- Z02: SLICE_X0Y0:SLICE_X45Y188     (bottom-left)
- Z03: SLICE_X46Y0:SLICE_X92Y188    (bottom-right)

### Still open
- Per-zone cmd_bus pipeline register fix
- Scale test after timing closure — how far can cell count grow?
- Python unicell_tool.py test via PCIe once bitstream working
- iCEBreaker SYNC_WAIT hardware test
- Branch/decision tree (deferred)
