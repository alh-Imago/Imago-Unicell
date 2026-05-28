# Session Log — 2026-05-28

## Status at session start
Last commit: Mode 1 branch, preloaded-A pattern, INT32 ADD 11/11.
New Kintex-7 card (YPCB-00338) arrived, PCIe bring-up in progress.

---

## What was done

### 1. Kintex-7 PCIe bring-up (morning)
Continued from previous session — FPGA booting from BPI flash, PCIe not enumerating.
- Diagnosed BIVC-1 bank voltage conflict (pcie_perstn LVCMOS33 vs SYS_CLK LVCMOS18 in same bank)
- Confirmed perst_n correct at LVCMOS18 — reverted attempted fix
- Tried Gen2/Gen1 speed settings — already at Gen1 (most conservative)
- Tried SMBus tape fix (B5/B6 pins) — no change
- Enabled Above 4G Decoding in BIOS — two LEDs lit (progress) but no enumeration
- Conclusion: B550M DS3H consumer platform incompatible with datacenter card
- Deferred — will test on Optiplex 9020 (Intel platform) at weekend
- FPGA itself confirmed healthy: DONE=1, EOS=1, PLL_LOCK=1, no errors

### 2. fp_tiles fixes — preloaded_a pipeline (afternoon)
Root cause: preload_map (address→address) was not being converted to concrete
a_data values (address→value) before loading into controller.
- Added `preloaded_a` parameter to `load_map()` in controller.py
- Added `compute_tile_preloads(tile, a_vals, b_vals)` utility in compiler_int32.py
  Forward-simulates tile records to compute concrete a_data from actual inputs
- Fixed `run_tile()` test helper: 32-bit word inputs (0/0xFFFFFFFF not 0/1)
- Fixed termination condition in run(): wait for `_carry` to clear (multi-layer trees)
- Fixed `one_shot` carry suppression: allow one carry after fire (`_one_shot_carried`)
- Fixed FP32_CMP_EQ: added `preload_map = getattr(bld, 'preload_map', {})`
Results: INT32_ADD 8/8, INT32_SUB 8/8, INT32_EQ 7/7, INT32_MUX 4/4,
         INT32_LT_U 6/6, INT32_LT_S 7/7, INT32_MIN 6/6, INT32_MAX 6/6,
         FP32_CMP_EQ 6/6, TilePlacer 6/6 — 161/161 total, 0 failures

### 3. ICM format v2 — unified across VM/Composer/FPGA
- docs/ICM_FORMAT.md: full rewrite with correct gate_state bit table
  GS_LATCH_IN (25), GS_ONE_SHOT (31), GS_LOOP_BACK (32), GS_EDGE_MODE (10)
  Two-arrival model and preloaded-A pattern documented
  Retired inB/alt/stor clearly marked
- composer/unicell_composer.html: updated presets, bit panel, ICM export/import
  No more inB/alt/stor emitted; format_version=2, address_width=32
- composer/examples/*.icm: all 11 files upgraded, stale gate_state bits stripped
- fpga/fpga_bridge.py: added configure_cell() (decodes full gate_state word) 
  and preload_cell() (preloaded-A pattern stub for silicon)
- fpga/icm_loader.py: wires init field to preload_cell()

### 4. IR lowering — preloaded-A pattern, eliminate relay cells
- lower_to_cell_map_v2(): binary ops now use 1 cell (was 2 with relay)
  Cell uses src_b as trigger, A from preload_map (depth-ordered)
  preload_map {out → A_src} returned in stats for callers
  ~40% cell reduction for typical multi-op expressions
- run_compiled_function(): single-pass forward sim using _ir_preload_map
  Removed relay_gs, relay_b, two-pass logic, _second_inputs
  Input values normalized to 32-bit words (0/0xFFFFFFFF)

### 5. load(A) / run(B) API separation
- LoadedInt32Function class: wraps compiled+preloaded region
  run(b_operands) reuses region, restores preloaded_a each call
- load_int32_function(source, fn, a_operands): compiles, forward-sims with A
  Note: KS adder needs both operands for optimal preload; API most useful
  for tiles where A is truly independent of B

### 6. Duplicate make_int32_min/max resolved
- Unsigned (KS subtractor, 615 cells, in_b=33): renamed to INT32_MIN_U / INT32_MAX_U
- Signed (ripple-borrow, 317 cells, in_b=32): kept as INT32_MIN / INT32_MAX
- All four registered in TileLibrary and TIER_MAP

### 7. Verilog: bus_hit_r pre-registered for Kintex-7
- Added `reg bus_hit_r` to unicell.v — registered copy of combinatorial bus_hit
- iCEBreaker unaffected; Kintex-7 swaps bus_hit → bus_hit_r for timing
- Syntax verified clean with iverilog

---

## Commits this session
- fix: preloaded_a pipeline — load_map param + compute_tile_preloads + test run_tile
- fix: EQ/AND-tree execution — one_shot carry, 32-bit word inputs, termination
- fix: FP32_CMP_EQ preload_map + INT32_SUB test cases
- test: INT32_LT_U, INT32_LT_S, INT32_MIN, INT32_MAX — all passing
- docs: update TODO.md — reflect current state
- feat: ICM format v2 — gate_state opcodes unified across VM/Composer/FPGA
- feat: IR lowering — preloaded-A pattern, eliminate relay cells
- feat: load(A)/run(B) API — LoadedInt32Function + load_int32_function
- fix: resolve duplicate make_int32_min/max — signed vs unsigned variants
- feat: pre-register bus_hit_r in unicell.v for Kintex-7 fan-out prep
- docs: update TODO — mark completed immediate items

---

## Test results at session end
161/161 fp_tiles tests passing, 0 failures

---

## Deferred to next session
- CMD_PRELOAD in unicell.v — wire preload_cell() stub in fpga_bridge.py
- Workbench testing
- PCIe on Optiplex 9020 (weekend)
- INT32_MIN/MAX signed overflow boundary fix

---

## Workbench enhancement notes (post-session)

Features to consider for next workbench session. Some only practical in frozen mode
(array frozen = static snapshot, no bus activity, safe to trace topology).

### Semantic cell behaviour display
Show human-readable interpretation of gate_state rather than raw hex.
e.g. "AND preloaded(a_data=0xF0)" or "XNOR latch_in comparator" instead of "0x0200003C".

### Linked-cell highlighting
Click a cell → highlight all cells it feeds (downstream) and all cells that feed it
(upstream). Currently cells shown as isolated pairs; need cross-cell address matching.

### Logic tree visualisation ← frozen mode only
Trace the full dependency tree from any cell back to its input roots and forward to
its output leaves. Render as a proper tree/DAG, not just address pairs.
Frozen mode required — in live mode bus activity makes topology ambiguous and
tracing would race against firing cells. Snapshot the array state first, then render.

### Pond visualisation
Show which cells belong to which pond/region. Colour-code by region_id.
Show pond boundaries, bridge cells, PTT sentry cells distinctly.
Useful for understanding compiled tile placement and multi-pond designs.
