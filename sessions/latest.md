# Latest Session — 2026-05-11 (session 3)

## Tests
2,381 passing / 6 failing (all pre-existing deprecated)
test_compiler_int32.py: 80/80

## Latest commit
TBD — sort.py n=16 INT32 verified; hardware matrix doc; Composer sim note

## What was done
- compiler_int32.py: Lt/Gt/LtE/GtE → INT32_LT_U; min/max → INT32_LT_S + INT32_MUX
- MIGRATION_TODO: signed int32 pattern documented for future reference
- Composer sim panel: amber warning box for SYNC_WAIT/tile/LOOP_MODE limitations
- fpga/README_FPGA.md: hardware support matrix (gs/in/out/inB/stor/init per layer)
- fpga/icm_loader.py: warns on inB and init fields not supported in silicon
- sort.py n=16 INT32: 62,000 cells, ✓ correct, ~10s VM runtime
  Fuzz: 10×n=4, 5×n=8, 3×n=16 — all correct

## Signed int32 pattern (important for future work)
Use INT32_LT_S (not sign-bit-of-subtract) for signed comparisons.
Sign-bit-of-subtract overflows when operand signs differ.
INT32_LT_S: XOR sign bits first; if differ, negative is smaller (no arithmetic);
if same, unsigned LT is safe. 523 cells, depth 16.

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026
- inB/SYNC_WAIT: implement in Verilog after JTAG arrives
- init pre-load: implement in UART protocol after JTAG arrives

## Next session priorities
1. postcode_sort.py: use INT32 sort for real Haversine distances
2. Composer: add INT32_LT_U/S, MIN, MAX, CAS to model library
3. model_library.py: register new tiles with accurate figures
