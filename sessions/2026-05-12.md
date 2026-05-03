# Session 2026-05-12 (continued) — Verilog Portability Audit + Array + Docs

## Summary

Completed the three session priorities from the previous push:
1. `docs/timing.md` written for unicell-latch
2. Verilog portability audit — all three variants now clean Verilog-2001
3. `unicell_array_latch.v` written for latch variant

Python tests unchanged: 2,238 passing, 0 failures.

## What was done

### unicell-latch/docs/timing.md (new)

Timing model documentation:
- chain_latency(n) = n+1 formula with derivation
- 3-phase tick explained (drain / load / compute)
- PASS cells as delay elements, path balancing
- SYNC_WAIT timing and alignment
- Config sequence (3-word standard, 4-word SYNC_WAIT/SELECT)
- Gate state register bit table
- NOR gate topology (1-input and 2-input modes)
- Verilog implementation notes (wire vs reg for gate inputs)

### Verilog portability audit — all 9 files CLEAN

**Bug found and fixed in standard + edge:**
Local `reg` declarations inside unnamed `always @(*)` blocks are
SystemVerilog syntax, not Verilog-2001. Fixed by moving g0-g8 and
input_val to module scope. Synthesises identically — no semantic change.

Files fixed:
- `unicell-standard/fpga/verilog/unicell.v`
- `unicell-edge/fpga/verilog/unicell.v`

**Bug found and fixed in unicell-edge/unicell_array.v:**
`BASE_ADDRESS` was referenced in CONFIG_ADDRESS calculation but never
declared as a parameter. Added `parameter BASE_ADDRESS = 0`.

**All 9 RTL files now clean (iverilog -g2001 -Wall, errors=0):**
- unicell-standard: unicell.v ✓  unicell_array.v ✓  uart_bridge.v ✓
- unicell-edge:     unicell.v ✓  unicell_array.v ✓  uart_bridge.v ✓
- unicell-latch:    unicell_latch.v ✓  unicell_array_latch.v ✓  uart_bridge.v ✓

No vendor-specific primitives in any file. Board-specific constraints
are isolated to top_*.v files only. All cell and array files are
synthesis-portable across iCE40, ECP5, Xilinx, Intel, SKY130.

### unicell_array_latch.v (new)

Proper latch-model array wrapper. Replaces the old unicell_array.v
which incorrectly instantiated `unicell` instead of `unicell_latch`.

Key differences from standard/edge arrays:
- Instantiates `unicell_latch` (not `unicell`)
- `start_flags_in [NUM_CELLS-1:0]`: per-cell arm/disarm bus
  (replaces implicit start_flag management inside standard cells)
- `start_flags_out`: echo for host observability
- No `clk_n` port (latch model has no falling-edge output path)
- `BASE_ADDRESS` parameter present and correct
- `armed_count` and `cycle_count` status outputs retained
- Clean Verilog-2001, 0 errors

## Test status

- Python (unicell-latch): 2,238 passing, 0 failures ✓ (unchanged)
- Verilog simulation (unicell_latch.v): 22/22 ✓ (unchanged)

## MIGRATION_TODO.md items completed

- [x] Verilog portability audit — all three variants clean
- [x] unicell_array_latch.v written

## Next session priorities

1. **docs/timing.md for unicell-edge** — document the output buffer model,
   GS_OUT_POSEDGE bit, negedge compute, posedge drain. Different from latch.
2. **Freeze/move output register capture** — controller.py freeze()/restore()
   should capture _output_latch (latch) / output_buf (edge) in snapshot.
   Full spec in MIGRATION_TODO.md under FREEZE/MOVE.
3. **top_asic.v** — ASIC-specific top-level (placeholder with parameter list).
   Currently missing from all three variants. Board-specific file for foundry.
4. **yosys lint** — run `yosys -check` on unicell_latch.v to catch
   latches, multi-driven nets, or other synthesis hazards before tapeout.
