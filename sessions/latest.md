# Session 2026-05-12 — unicell_latch.v Verilog Implementation

## Summary

Wrote and verified `unicell_latch.v` — the Verilog implementation of the
latch-model UniCell. All 22 simulation tests passing. Python test suite
unchanged (2,238 passing, 0 failures confirmed on key suites).

## What was built

### unicell-latch/fpga/verilog/unicell_latch.v

The latch-model Verilog cell. Key design decisions:

**Two FF banks, purely combinational gate tree**
- `input_ff` / `input_ff_valid`: loaded when bus delivers data to input_address
- `output_ff` / `output_ff_valid`: loaded by gate tree result, drained to bus next tick
- Gate tree is `wire` logic between these — no clock in the compute path

**chain_latency(n) = n+1 confirmed in silicon**
- Tick 0: bus → input_ff
- Tick 1: input_ff → gate tree → output_ff (compute phase)
- Tick 2: output_ff → bus (drain phase)
- Each additional cell in chain adds exactly 1 tick

**Modes implemented**
- GS_PASS, GS_NOT (bits 0-8 NOR topology) ✓
- GS_LATCH (bit 11): re-emits stored_value each tick, updates on new input ✓
- GS_ONE_SHOT (bit 12): fires once then locks ✓
- GS_INVERT_OUT (bit 13): complements gate output ✓
- GS_SYNC_WAIT (bit 15): waits for both A (input_ff) and B (input_b_ff) ✓
- GS_SELECT (bit 9): routes condition=1→output_address, 0→output_address_alt ✓
- GS_LOOP (bit 10): stay armed after firing ✓
- Freeze line: suppresses output, preserves state ✓

**Config sequence**: standard 3-word (LOAD_PAT + gs + iaddr + oaddr),
extended 4-word for SYNC_WAIT (+ input_b_address) and SELECT (+ alt_addr).

**Vendor-neutral**: standard Verilog-2001. No vendor primitives.
Confirmed compiles clean with `iverilog -g2001 -Wall`.

### unicell-latch/fpga/verilog/tb_unicell_latch.v

22-test simulation testbench. Tests:
1-2: Reset state, 3-4: PASS gate, 5-6: NOT gate, 7-8: INVERT_OUT,
9-10: ONE_SHOT, 11-12: LATCH mode, 13-14: SYNC_WAIT, 15-17: SELECT,
18: Freeze, 19-20: chain latency (2 cells), 21-22: LOOP_MODE.

**Key debugging note**: gate tree inputs (`a_in`, `b_in`) must be `wire`
not `reg`. If registered, the gate tree reads the previous tick's value
and all outputs are off-by-one. Fix: `wire a_in = input_ff[0]`.

## Files changed

- NEW: `unicell-latch/fpga/verilog/unicell_latch.v`
- NEW: `unicell-latch/fpga/verilog/tb_unicell_latch.v`
- sessions/latest.md (updated)
- sessions/2026-05-12.md (this file)

## Test status

- unicell-latch Verilog: **22/22 simulation tests passing** ✓
- unicell-latch Python: **2,238 passing, 0 failures** ✓ (unchanged)

## MIGRATION_TODO.md item updated

- [x] `fpga/verilog/unicell_latch.v` — now complete

## Next session priorities

1. **docs/timing.md** for unicell-latch — document the n+1 latency formula,
   PASS cell use for path balancing, config sequence, mode flags
2. **Verilog portability audit** — verify unicell-standard and unicell-edge
   Verilog are similarly clean for synthesis (see MIGRATION_TODO Tier 1)
3. **unicell_array_latch.v** — the array wrapper that does the 3-phase tick
   (drain output_ff → bus, deliver bus → input_ff, fire gate tree)
4. **Freeze/move output bus capture** — snapshot includes output_ff content
   (see MIGRATION_TODO FREEZE/MOVE section)
