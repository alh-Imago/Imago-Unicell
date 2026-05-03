# Session 2026-05-12 (continued 2) — Freeze/Move + Timing Docs + ASIC Top + Yosys

## Summary

Worked through the full priority list from the previous push. All four items done.
Python tests: 64 passing in test_freeze.py (was 47), all other suites unchanged.
Zero regressions.

## What was done

### 1. Freeze/Move — output_latch captured in snapshot

**The gap:** A cell mid-pipeline (gate tree fired, result in _output_latch,
not yet drained to bus) would lose its in-flight result on a naive freeze+migrate.
The downstream cell would miss the value entirely.

**The fix — three files:**

`unicell-latch/unicell.py` — `snapshot()` now includes `"output_latch"` key:
- Captures `_output_latch` content (a result tuple or None)
- Also already captured `_input_latch` (pending input) — now fully round-tripped

`unicell-latch/controller.py` — `restore_snapshot()` now restores both latches:
- `cell._input_latch = state.get("input_latch")` — pending input survives migration
- `cell._output_latch = state.get("output_latch")` — in-flight result survives
- On thaw, first drain tick drives the restored result — no pipeline bubble

**17 new tests in test_freeze.py (47 → 64, all passing):**
- Output latch captured in snapshot (NOT(0)=1 in flight at freeze time) ✓
- restore_snapshot restores output_latch correctly ✓
- First tick after restore+thaw drives result to bus ✓
- Idle cell (output_latch=None) snapshots and restores without spurious output ✓
- Input_latch (pending input) captured and restored, gate fires correctly after thaw ✓

### 2. unicell-edge/docs/timing.md (new)

Timing model documentation for the edge variant:
- Two-edge compute cycle (posedge A, negedge compute+B)
- chain_latency(n) = n full cycles
- Output buffer (out_buf) — the edge model's _output_latch equivalent
- GS_OUT_POSEDGE (bit 26) — release on posedge to avoid collision
- Two-input natural operation vs SYNC_WAIT in latch model
- GS_LATCH_IN counter pattern
- Comparison table: Standard / Latch / Edge
- Synthesis note on negedge FFs

### 3. top_asic.v — all three variants (new)

Clean, parameterised ASIC-facing top-level for each variant:

`unicell-standard/fpga/verilog/top_asic.v`
`unicell-edge/fpga/verilog/top_asic.v`
`unicell-latch/fpga/verilog/top_asic.v`

All three: standard Verilog-2001, no vendor primitives, parameterised
(NUM_CELLS, CLK_FREQ, BAUD_RATE). Board constraints isolated here only.

Latch top_asic.v notes:
- Instantiates unicell_array_latch (not unicell_array)
- start_flags_in tied to all-ones for bring-up (TODO: connect to bridge)
- BASE_ADDRESS parameter exposed
- Tiny Tapeout 130nm area estimates included
- TODO note for uart_bridge SET_FLAGS extension

All three compile clean: iverilog -g2001 0 errors.

### 4. Yosys lint

`unicell_latch.v` — CLEAN. Zero warnings, zero errors, zero inferred latches.
Gate tree correctly inferred as combinational, all FFs correctly registered.

`unicell-standard/unicell.v`, `unicell-edge/unicell.v` — PRE-EXISTING ISSUE:
"multiple conflicting drivers" for out_data/out_addr/out_valid. Root cause:
both posedge and negedge always blocks write the same output regs.
This is a pre-existing structural issue in these variants (not a regression).
Fix: split into posedge-only and negedge-only output registers.
Logged for next session — does not affect simulation correctness.

## Test status

- unicell-latch Python: **2,255 passing** (test_freeze: 64, others unchanged) ✓
- unicell_latch.v Verilog: 22/22 simulation tests ✓
- Yosys lint unicell_latch.v: CLEAN ✓

## MIGRATION_TODO.md items completed

- [x] Freeze/move output register capture (FREEZE/MOVE section)
- [x] docs/timing.md for unicell-edge
- [x] top_asic.v for all three variants
- [x] Yosys lint on unicell_latch.v

## Next session priorities

1. **Fix standard/edge yosys multiple-driver warnings** — split posedge/negedge
   output registers so each always block has a single driver.
   Pure RTL cleanup, no functional change, no Python impact.

2. **uart_bridge SET_FLAGS extension** — extend uart_bridge.v with a command
   to drive start_flags_in on the latch array directly (currently the latch
   top_asic.v ties all flags high for bring-up).

3. **fpga_bringup.py** — bring-up sequence script:
   LED blink → UART loopback → NOT gate → AND → bridge pair.
   Testable against VM now; plug-and-run when iCEBreaker arrives.

4. **LIF neuron v2** — port lif_neuron_reference.v from v1 cell to latch model.
   6-8 cells per neuron, uses _input_latch and SYNC_WAIT.
   Testable in VM; runs on iCEBreaker at 4-5 neurons at 32 cells.
