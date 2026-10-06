# Flex cell cost vs width (ledger #975)

Measured by `tools/flex_width_sweep_v1.py` (yosys `synth_gowin`, synthesis only -- no place-and-route, no timing, nothing run on a board). Raw numbers: `costs.json`; they are also carried in the Tang Nano 20K MAN file under `cell_costs`.

Each cell was built three ways at widths 4, 8, 16, 18, 24, 32: the **single cell** alone (every configuration port a real input -- the honest per-cell cost) in the card's default `-nowidelut` flow, the same in the historical wide-LUT flow, and a **3x3 array** (nine cells in the generated assembler top).

## Single cell, LUT4 (default `-nowidelut` flow)

| cell | W4 | W8 | W16 | W18 | W24 | W32 | fit LUT4 vs W | max error |
|---|---|---|---|---|---|---|---|---|
| accumulator | 63 | 77 | 88 | 93 | 110 | 133 | 2.39W +53.3 | 4.5 |
| adder | 13 | 17 | 25 | 27 | 33 | 41 | 1.00W +9.0 | 0.0 |
| branch | 43 | 64 | 111 | 122 | 156 | 200 | 5.64W +20.1 | 1.2 |
| compare | 9 | 11 | 17 | 19 | 22 | 28 | 0.68W +6.0 | 0.6 |
| latch | 8 | 8 | 8 | 8 | 8 | 8 | 8 (flat) | 0.0 |
| mask | 9 | 13 | 21 | 23 | 29 | 37 | 1.00W +5.0 | 0.0 |
| mul | 31 | 152 | 645 | 829 | 1504 | 2695 | 2.73W^2 -2.98W -0.6 | 5.2 |
| mul_dsp | 8 | 8 | 8 | 8 | 8 | 8 | 8 (flat) | 0.0 |
| nano | 61 | 89 | 145 | 159 | 201 | 257 | 7.00W +33.0 | 0.0 |
| ram | 10 | 14 | 22 | 24 | 30 | 38 | 1.00W +6.0 | 0.0 |
| router | 10 | 10 | 10 | 10 | 10 | 10 | 10 (flat) | 0.0 |
| sequencer | 21 | 36 | 36 | 36 | 36 | 36 | 36 (saturates from W8; no useful fit) | - |
| shift_stage | 5 | 5 | 5 | 5 | 5 | 5 | 5 (flat) | 0.0 |

## Single cell, flip-flops (DFF)

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| accumulator | 31 | 43 | 59 | 63 | 75 | 91 |
| adder | 10 | 14 | 22 | 24 | 30 | 38 |
| branch | 27 | 39 | 63 | 69 | 87 | 111 |
| compare | 7 | 11 | 19 | 21 | 27 | 35 |
| latch | 4 | 4 | 4 | 4 | 4 | 4 |
| mask | 11 | 19 | 27 | 27 | 35 | 43 |
| mul | 12 | 20 | 36 | 40 | 52 | 68 |
| mul_dsp | 12 | 20 | 36 | 40 | 52 | 68 |
| nano | 20 | 28 | 44 | 48 | 60 | 76 |
| ram | 7 | 11 | 19 | 21 | 27 | 35 |
| router | 9 | 13 | 21 | 23 | 29 | 37 |
| sequencer | 26 | 46 | 46 | 46 | 46 | 46 |
| shift_stage | 6 | 10 | 18 | 20 | 26 | 34 |

ALU (carry-chain) cells, `mul_dsp` DSP blocks and the wide-LUT and 3x3 numbers are in `costs.json`.

## How to read this

- **Use the single-cell nowidelut numbers to project.** They are smooth in W and the fits hold to a few LUTs (adder exactly W+9, nano exactly 7W+33, mask W+5, ram W+6; the LUT multiplier is quadratic, about 2.7 W^2).
- **The wide-LUT flow is not smooth** (compare: 50 / 86 / 110 / 28 LUT4 at W16 / 18 / 24 / 32; branch 239 at W16 but 201 at W18). The mapper changes its mind between widths, so do not extrapolate from it; the nowidelut flow is the card's default (`synthesis.nowidelut.default`).
- **The 3x3 array is not nine times the single cell.** The generated top pins each cell's configuration, so constant-config logic folds away: nine adders cost less than two single adders. It tells you what a hard-wired cluster costs, not a runtime-configurable one. Cells whose configuration the harness leaves live (nano, branch, accumulator, mask, ram) come out near nine times the single cell plus a small harness.
- **W-independent cells:** latch (8 LUT4), router (10), shift_stage (5) cost the same LUTs at every width and only add flip-flops. The sequencer saturates at 8 bits (36 LUT4 above) and FlexGrid refuses it below 8.
- **mul_dsp** is 8 LUT4 plus one MULT36X36 at every width (the multiply is in the DSP block); its width limit is 36.
- Costs are of the cells as they stand with the #974 second output ports (adder carry, multiplier high word) present and unused, and the #971-#973 changes (nano armed gate, comparator threshold port, accumulator below 16 bits).
- Not covered: the merge cell (no assembler shape yet), cells with the second ports switched on, place-and-route or timing.

## On the Tang Nano 20K (20,736 LUT4)

Whole cells that fit if the device held nothing else (single-cell nowidelut cost, ignoring routing and the DFF limit of 15,552):

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| accumulator | 329 | 269 | 235 | 222 | 188 | 155 |
| adder | 1595 | 1219 | 829 | 768 | 628 | 505 |
| branch | 482 | 324 | 186 | 169 | 132 | 103 |
| compare | 2304 | 1885 | 1219 | 1091 | 942 | 740 |
| latch | 2592 | 2592 | 2592 | 2592 | 2592 | 2592 |
| mask | 2304 | 1595 | 987 | 901 | 715 | 560 |
| mul | 668 | 136 | 32 | 25 | 13 | 7 |
| mul_dsp | 2592 | 2592 | 2592 | 2592 | 2592 | 2592 |
| nano | 339 | 232 | 143 | 130 | 103 | 80 |
| ram | 2073 | 1481 | 942 | 864 | 691 | 545 |
| router | 2073 | 2073 | 2073 | 2073 | 2073 | 2073 |
| sequencer | 987 | 576 | 576 | 576 | 576 | 576 |
| shift_stage | 4147 | 4147 | 4147 | 4147 | 4147 | 4147 |
