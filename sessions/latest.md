# Latest Session — 2026-05-11 (session 2)

## Tests
2,381 passing / 6 failing (all pre-existing deprecated)
test_compiler_int32.py: 80/80

## Latest commit
6cc5678 — compiler_int32: wire Lt/Gt/LtE/GtE → INT32_LT_U; min/max → INT32_LT_S + INT32_MUX

## What was done
- Lt/Gt/LtE/GtE now route to INT32_LT_U tile (was broken — returned None)
- min(a,b)/max(a,b) compile via INT32_LT_S + INT32_MUX
  - INT32_LT_S handles signed overflow correctly (XOR sign bits first)
  - INT32_MUX selects the correct operand based on 1-bit comparison result
- New methods: _place_int32_lt_tile, _place_int32_lt_s_tile,
  _place_int32_mux_tile, _place_int32_minmax_tile, _compile_call_typed
- 22 new tests in test_compiler_int32.py

## Key insight from Alan
Signed comparisons with large values require the INT32_LT_S tile which
uses XOR of sign bits before subtraction to avoid overflow — not the
simpler sign-bit-of-subtract approach which overflows when signs differ.

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026

## Next session priorities
1. sort.py: n=16 INT32 sort testing
2. Composer: simulation limitations note (SYNC_WAIT/LOOP_MODE)
3. Hardware support matrix (inB/stor/init per FPGA target)
