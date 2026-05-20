# Session Log — 2026-05-19 (full day)

## Status at session start
Last commit: INT32 adder preloaded-A pattern, 11/11 ADD tests passing.
New iCEBreaker card arriving 2026-05-20.

---

## What was done

### 1. INT32 adder — preloaded-A pattern (morning)
Established the correct architecture for binary op cells:
- A is computed via Python forward simulation of the KS tree at runtime
- Written into each op cell's a_data via region.preloaded_a before run starts
- B is the single trigger wave — propagates through the network
- Each cell fires immediately when B arrives (a_arrived=True, a_data preloaded)
- Wire cells use GS_PASS|GS_LATCH_IN for single-arrival propagation
Confirmed: same as preloaded comparator pattern validated on silicon (2026-05-17)
Result: INT32 ADD 11/11 passing

### 2. Mode 1 branch: run_compiled_function (morning/afternoon)
New function run_compiled_function() in compiler.py:
- Two-pass forward simulation: Pass 1 computes outputs, Pass 2 sets preloads
- Only preloads cells whose A-input is a user-input address
- Intermediate cells (both inputs from upstream ops) use natural two-arrival
- Injection rules: skip A-side (preloaded), skip relay destinations
- preloaded_one_shot flag: one_shot for shallow chains, off for KS tree
- ir.py: smart relay routing — leaf ops use second_inputs_map, intermediate use relay
- Relay cells: one_shot to prevent carry re-fires
Result: AND/OR/NOT/MUX all passing, IfExp MUX passing

### 3. BranchPoint API fix
- Rebuilt branch.py to match current architecture (no SELECT/output_address_alt)
- build(ctrl, name) — allocates ptt_addr internally
- 1-cell layout: XNOR + latch_in (preloaded-A, silicon-confirmed)
- dispatch() injects marker at addr_true or addr_false for observability
- Mode 2 hook clearly documented
- test_branch.py rewritten: 56/56 tests passing

### 4. INT32 SUB/EQ/NEQ/Lt/Gt/LtE/GtE/min/max (afternoon)
Root causes fixed (all related to preloaded-A not being wired through):
1. place() dropped initial_value from CellMapRecord — NOT cells lost preload
2. All tile builders missing preload_map in Tile return
3. _eval_gate NOT used 32-bit complement not single-bit
4. Comparison tile placers not accumulating _tile_preloads
5. carry-in must be injected as live trigger, not preloaded
6. Both A and B injected as triggers; a_vals added to relay_targets
7. Bit reconstruction uses & 1 (handles 0xFFFFFFFF=1, 0xFFFFFFFE=0)
8. _pad_int32_to_depth used GS_PASS (two-arrival) → GS_PASS|GS_LATCH_IN
9. make_int32_mux missing preload_map
Result: 81/82 INT32 tests (1 non-critical depth-uniformity structural check)

### 5. File scan and tidy (end of day)
- All .py files scanned for retired gate state references
- place() 5-tuple updated in: compiler.py, test files
- list_tiles() guarded against legacy tiles with retired gate states
- bits_to_int reconstruction fixed in test_tile_library.py
- Pre-existing failures documented (not regressions):
  test_gate_state_32.py, test_new_tiles.py, test_compiler_tile_library.py

### 6. Subdirectory retirement
- unicell-edge/ — REMOVED (edge-triggered variant, superseded by two-arrival)
- unicell-latch/ — REMOVED (latch variant, superseded by current model)
- unicell-standard/ — REMOVED (historical archive only)
- Promoted from unicell-latch: fpga_bridge.py, fpga_bringup.py
  Updated LOOP_MODE → GS_LATCH_IN, GS_SYNC_WAIT removed (now default)
- Deferred: composer/, lif_neuron_v2.py, load(A)/run(B) API separation
  All recorded in MIGRATION_TODO.md

---

## Test status at session end
- Core tests (test_array.py, test_compiler.py): 19/19 ✅
- Compiler v2 (test_compiler_v2.py): all passing ✅
- Branch (test_branch.py): 56/56 ✅
- INT32 (test_compiler_int32.py): 81/82 ✅ (1 structural depth check)
- Counter tiles: 83/86 (3 SHIFT_8 pre-existing failures)
- Branch 56/56

## What's ready for the card (2026-05-20)
- fpga_bridge.py — UART host interface for iCEBreaker
- fpga_bringup.py — 6-step bring-up sequence (sim + hardware modes)
  Run: python3 fpga_bringup.py --sim (no hardware needed to test flow)
  Run: python3 fpga_bringup.py --port /dev/ttyUSB0 (hardware)
- Preloaded-A pattern validated in software, matches silicon-confirmed comparator

## Architecture notes
The two-arrival model IS the unified model. The old edge/latch split was
exploring different FPGA timing approaches. The current model:
- First arrival at input_address → stored in a_data, a_arrived=True
- Second arrival → fires gate(a_data, new_value)
- Preloaded-A: a_data set at load time, any arrival fires immediately
This maps cleanly to the hardware send_twice() preload pattern.

---

# Session Log — 2026-05-20

## Hardware arrived
- iCEBreaker confirmed working (from previous session)
- Kintex-7 dual XC7K480T PCIe card arrived (YZCA-00338-104)
- Xilinx Platform USB Cable arrived
- Board files found: github.com/TiferKing/ypcb_00338_1p1_hack
- Vivado bring-up pending PCIe riser cable (arriving next day)

## Composer fixes
- Fixed buttons not working: duplicate buildLib() closing block caused silent
  JS syntax error — all onclick handlers unattached
- Added touch support: tap to select, drag to pan, pinch to zoom on canvas
- canvas: touch-action:none, slightly larger button tap targets
- addCell(): resize() if W=0, then fitView() — new cells always visible on mobile

## fpga_bridge/bringup fixes
- 6/6 sim steps now passing (was stuck at step 2)
- Key fixes: write_config()→configure_cell(), _injected not .bus,
  GS_PASS_B|GS_LATCH_IN for single-arrival relay, pre-arm relay cells in configure()

## Silicon results — sequence lock (test_ring_22.py)

### Key discoveries during bring-up:
1. NUM_CELLS=4 not 16 (spec says 16 — rebuild needed)
2. ENABLE_LATCH_IN=0 — latch_in bit compiled out on iCEBreaker
3. freeze() drops data writes — freeze is config-only (bus_hit = !frozen)
4. 16-bit address matching only (bus_addr[15:0])
5. XNOR mismatch = 0xFFFFFFFE not 0 — check != 0xFFFFFFFF not == 0

### Final result (4-cell XNOR lock):
- Wrong code [0,0,0]: c0=0xFFFFFFFE (mismatch) c1=0xFFFFFFFF c2=0xFFFFFFFE → BLOCKED ✅
- Correct code [1,0,1]: c0=0xFFFFFFFF c1=0xFFFFFFFF c2=0xFFFFFFFF → UNLOCKED ✅
- addr99 = 0xFFFFFFFF on correct code only
- **Preloaded spatial memory confirmed on silicon**

## Documentation
- docs/RESULTS.md created — comprehensive silicon validation record
- docs/ARCHITECTURE.md updated — retired three-variant section, updated Kintex-7 status
- README.md updated — removed stale cell simplification warning, current state correct
- MIGRATION_TODO.md — Kintex-7 board details and rebuild instructions added

## Kintex-7 board notes (YZCA-00338-104)
- Dual XC7K480T, ~10 DDR3 chips on rear (estimated 5-10GB)
- PCIe form factor, Xilinx JTAG 14-pin header
- Board files: TiferKing/ypcb_00338_1p1_hack (Vivado board repository)
- WARNING: JTAG header is NOT a power connector (Meta AI gave dangerous advice)
  Pin 1 = VREF (3.3V ref), standard Xilinx 14-pin JTAG
