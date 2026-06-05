# Session Log — 2026-06-05

## Status at session end
Last commit: 38fb9a1
Suite: 199/199 fp_tiles, 101/101 compiler_int32

## Silicon confirmed today (iCEBreaker)
tests/fpga/test_sanity.py — 31/31 passing

All confirmed on silicon:
- Two-arrival model
- NOT, AND, OR, XOR, PASS, NOR gates (32-bit)
- latch_in, one_shot, invert_out
- preload_sel (v2.3)
- shift_out_en (v2.3)
- CMD_ARRAY_RESET, CMD_BOOT_COMMIT, CMD_RECONFIGURE

## Also done today
- RShift/LShift/SAR compiler support added
- 1D Laplacian MathTrix demo working
- shift_in_en deferred to Arria 10 (16-bit bus limitation)

## Next session
1. Arria 10 card arrives — Quartus project setup
2. Validate shift_in_en on Arria 10
3. Multi-param compiler bug
