# Session 2026-05-02 — Output Buffer (UniCell-Edge Model)

## Summary

Added the UniCell-edge output buffer to the cell, array, and Verilog.
This was architecturally significant — required fixing bus semantics, feedback
loop behaviour, and updating tests across the entire suite.

## What Was Done

### Feature: Output Buffer (GS_OUT_POSEDGE, bit 26)

**gate_states.py**
- Added `GS_OUT_POSEDGE = 1 << 26` (0x04000000)
- Updated bit layout comment: bits 27-28 remain reserved
- Full doc block explaining posedge vs negedge release, compiler implications

**unicell.py**
- Added `out_posedge: bool` field (bit 26 decoded in gate_state parser)
- Added `_output_buf: Optional[tuple]` — holds computed result for one tick
- `tick()` now calls `_buf()` instead of returning directly
- `_buf()` loads `_output_buf` AND returns the tuple (for test/debug observability)
  - Exception: `loop_mode / latch_mode / storage_mode` cells bypass the buffer
    (feedback cells need immediate bus visibility for loop convergence)
- Added `drain_output_buf()` — called by array Phase 0 each tick

**unicell_array.py**

Bus model changes (the core of the work):
- Phase 0: builds `fresh_bus` from `_injected` + `_carry` + this-tick buffer drains
  - `_injected`: externally-written values (controller.start(), test harnesses) — one tick only
  - `_carry`: output-buffer drains that persist one extra tick for feed-forward chains
  - Feedback cell writes go into both `self.bus` AND `_carry` (overwrite, not OR)
- Phase 2: feedback/loop cells write directly to `self.bus` + `_carry` (bypassing buffer)
- Phase 4: bus is NOT cleared — Phase 0 rebuilds it fresh each tick
- Added `tick_drain()` — convenience method: compute tick + drain tick, used in tests
- `run()` now waits for `_output_buf` to drain before declaring completion
- `_armed` set tracking unchanged — only load/feedback distinction matters

**fpga/verilog/unicell.v**
- Added `GS_OUT_POSEDGE` localparams
- Added `out_buf_valid`, `out_buf_data`, `out_buf_addr`, `out_buf_posedge` registers
- Posedge always block: drains `out_buf` if `out_buf_posedge=1`
- Negedge always block: drains `out_buf` if `out_buf_posedge=0` (default);
  also handles GS_LATCH_IN re-evaluation → loads into output buffer
- Compute result now loads `out_buf` instead of driving output directly

**controller.py**
- `run()`: after `active==0`, drains pending output buffers (one extra tick if needed)
- `run()`: pre-run cleanup now also clears `_carry` entries for region cells
  (prevents stale values from leaking into second runs of the same region)
- `start()`: writes to `array._injected` instead of `array.bus` directly

**branch.py**
- `load_row()`: clears `_carry` and `_injected` in addition to `bus.clear()`
  (internal BranchPoint intermediate addresses were corrupting next dispatch)

### Tests Updated

All 40 runnable test files pass (2,238 tests). Changes by category:

**Direct bus injection** (`arr.bus[x] = v` → `arr._injected[x] = v`):
- test_addr_latch, test_array, test_bridge_integration, test_ecc,
  test_freeze, test_pond_restart

**Single tick → tick_drain** where result needed immediately:
- test_addr_latch (array extended_addresses, normal cell bus check)
- test_array (chain, parallelism, address isolation)
- test_freeze (multiple branch/thaw/stage checks)
- test_while (run() helper drain after active==0)

**Cycle count updates** (output buffer adds +1 cycle per cell in feed-forward chains):
- test_bridge_integration: cycle 1→2, cycle 4→5, updated run_ticks counts

**"Bus empty" → "active==0"** for freeze checks:
- test_freeze, test_branch (bus now holds last driven values, not empty)

**Stale carry clearing** between repeated dispatches:
- test_branch (dispatch() helper, DataTable, After update)

## Architecture Notes

### Bus Semantics (new model)
The bus is rebuilt fresh each tick from three sources:
1. `_carry` — output-buffer drains from previous tick (feed-forward persistence)
2. `_injected` — external controller/test injections (one tick only, then cleared)
3. This tick's output-buffer drains (added to `_carry` for next tick)

Feedback/loop cells write directly to bus + carry (overwrite, not OR).
This solves the wired-OR accumulation problem for feedback loops.

### Output Buffer Bypass for Feedback Cells
`loop_mode`, `latch_mode`, `storage_mode` cells bypass `_output_buf` entirely.
They need immediate bus visibility for loop convergence. The one-cycle delay
applies only to one-shot feed-forward cells.

### Compiler TODO (recorded in MIGRATION_TODO.md)
`lower_to_cell_map_v2()` must set `GS_OUT_POSEDGE` on cells whose output
feeds the A (posedge) input of the next cell. Cells feeding B (negedge) inputs
leave bit 26 clear. Default: set `GS_OUT_POSEDGE` on all cells until per-edge
routing is implemented.

## Test Status
- **2,238 tests passing, 0 failures**
- Pre-existing non-runners (unchanged): test_display_pond (pygame), test_llvm_frontend, test_llvm_ir_mapper (IndexError pre-dates this session), test_ecc (all skipped, ECC not active)

## Git
- Tag at start: v2.1
- Branch: main
- Commit: [pushed end of session]

---

## Session continuation — Latch model + test_helpers (2026-05-02 evening)

### unicell-latch/ — latch model built

**unicell.py changes:**
- Added `_input_latch` and `_output_latch` registers to `__init__`
- `receive()` now stores to `_input_latch` (and `self.data` for compat)
- `tick()` completely replaced with latch model:
  - Checks `_input_latch` (falls back to `self.data` for standalone tests)
  - Fires gate tree → stores result in `_output_latch`
  - Returns result for observability
- Added `drain_output_latch()` — called by array Phase 1 each tick

**unicell_array.py tick() rewritten — 3 phases:**
- Phase 1: drain `_output_latch` from all cells → fresh `new_bus` (no carry, no stale values)
- Phase 2: deliver bus → input latches of armed cells
- Phase 3: fire cells with `_input_latch` data → `_output_latch`
- `run()` updated to wait for output latches to drain before completion

**test_helpers.py created:**
- `CELL_LATENCY = 2` — single source of truth for timing
- `chain_latency(n)`, `parallel_latency(n)` — compute expected cycle counts
- `run_ticks(arr, n)`, `run_to_result(arr, *addrs)`, `run_chain(arr, addr)`

**Test status:** 2,087 passing, 65 failing
- All failures are cycle-count / tick_drain pattern — mechanical to fix
- All OS layer, pond, compiler, FP tiles pass outright

### unicell-edge/ — test_helpers.py added
- Same structure as latch helpers, `CELL_LATENCY = 2`
- Ready for tests to import — backport of cycle constants to edge
- Existing edge tests not yet updated to use helpers (next session)

### Next session
- Fix remaining 65 latch test failures (tick_drain + cycle counts)
- Update latch tests to use `chain_latency()` from test_helpers
- Write `fpga/verilog/unicell_latch.v`
- Backport test_helpers usage to unicell-edge tests
