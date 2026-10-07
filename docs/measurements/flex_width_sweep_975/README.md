# Flex cell cost vs width (ledger #975, extended #976)

Measured by `tools/flex_width_sweep_v1.py` (yosys `synth_gowin`, synthesis only -- no place-and-route, no timing, nothing run on a board). Raw numbers: `costs.json`; they are also carried in the Tang Nano 20K MAN file under `cell_costs`. Regenerate this file with `python3 tools/flex_width_sweep_v1.py --readme-only`.

Each cell was built at widths 4, 8, 16, 18, 24, 32: the **single cell** alone (every configuration port a real input -- the honest per-cell cost) in the card's default `-nowidelut` flow and in the historical wide-LUT flow, and a **3x3 array** (nine cells in the generated assembler top). The adder, multiplier and DSP multiplier were also built **with their second output port** (`SECOND_PORT=1`).

## Single cell, LUT4 (default `-nowidelut` flow)

| cell | W4 | W8 | W16 | W18 | W24 | W32 | fit LUT4 vs W | max error |
|---|---|---|---|---|---|---|---|---|
| accumulator | 63 | 77 | 88 | 93 | 110 | 133 | 2.39W +53.3 | 4.5 |
| adder | 9 | 13 | 21 | 23 | 29 | 37 | 1.00W +5.0 | 0.0 |
| branch | 43 | 64 | 111 | 122 | 156 | 200 | 5.64W +20.1 | 1.2 |
| compare | 9 | 11 | 17 | 19 | 22 | 28 | 0.68W +6.0 | 0.6 |
| latch | 8 | 8 | 8 | 8 | 8 | 8 | 8 (flat) | 0.0 |
| mask | 9 | 13 | 21 | 23 | 29 | 37 | 1.00W +5.0 | 0.0 |
| merge | 21 | 25 | 33 | 35 | 41 | 49 | 1.00W +17.0 | 0.0 |
| mul | 16 | 70 | 313 | 394 | 728 | 1332 | 1.41W^2 -3.94W +10.2 | 4.1 |
| mul_dsp | 5 | 5 | 5 | 5 | 5 | 5 | 5 (flat) | 0.0 |
| nano | 61 | 89 | 145 | 159 | 201 | 257 | 7.00W +33.0 | 0.0 |
| priority | 206 | 218 | 242 | 248 | 266 | 291 | 3.03W +193.7 | 0.4 |
| ram | 10 | 14 | 22 | 24 | 30 | 38 | 1.00W +6.0 | 0.0 |
| router | 10 | 10 | 10 | 10 | 10 | 10 | 10 (flat) | 0.0 |
| sequencer | 21 | 36 | 36 | 36 | 36 | 36 | 36 (saturates from W8; no useful fit) | - |
| shift_stage | 5 | 5 | 5 | 5 | 5 | 5 | 5 (flat) | 0.0 |

## With the second output port built (`SECOND_PORT=1`), LUT4 / DFF

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| adder (port off -> on) | 9/7 -> 13/10 | 13/11 -> 17/14 | 21/19 -> 25/22 | 23/21 -> 27/24 | 29/27 -> 33/30 | 37/35 -> 41/38 |
| mul (port off -> on) | 16/6 -> 31/12 | 70/10 -> 152/20 | 313/18 -> 645/36 | 394/20 -> 829/40 | 728/26 -> 1504/52 | 1332/34 -> 2695/68 |
| mul_dsp (port off -> on) | 5/6 -> 8/12 | 5/10 -> 8/20 | 5/18 -> 8/36 | 5/20 -> 8/40 | 5/26 -> 8/52 | 5/34 -> 8/68 |

## Build-parameter variants (ledger #1021/#1022), LUT4 / DFF

| cell variant | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| ram oneshot (default -> variant) | 10/7 -> 10/7 | 14/11 -> 14/11 | 22/19 -> 22/19 | 24/21 -> 24/21 | 30/27 -> 30/27 | 38/35 -> 38/35 |
| ram hold (default -> variant) | 10/7 -> 12/8 | 14/11 -> 16/12 | 22/19 -> 24/20 | 24/21 -> 26/22 | 30/27 -> 32/28 | 38/35 -> 40/36 |

The ram's one-shot preload (`OFFER_PRELOAD`) costs nothing measurable; HOLD adds about two LUT4 and one flip-flop at every width. The priority cell is a single measured cell (all three modes in one build): about 3W + 194 LUT4, 155 ALU, W + 62 flip-flops.

## Single cell, flip-flops (DFF)

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| accumulator | 31 | 43 | 59 | 63 | 75 | 91 |
| adder | 7 | 11 | 19 | 21 | 27 | 35 |
| branch | 27 | 39 | 63 | 69 | 87 | 111 |
| compare | 7 | 11 | 19 | 21 | 27 | 35 |
| latch | 4 | 4 | 4 | 4 | 4 | 4 |
| mask | 11 | 19 | 27 | 27 | 35 | 43 |
| merge | 9 | 13 | 21 | 23 | 29 | 37 |
| mul | 6 | 10 | 18 | 20 | 26 | 34 |
| mul_dsp | 6 | 10 | 18 | 20 | 26 | 34 |
| nano | 20 | 28 | 44 | 48 | 60 | 76 |
| priority | 66 | 70 | 78 | 80 | 86 | 94 |
| ram | 7 | 11 | 19 | 21 | 27 | 35 |
| router | 9 | 13 | 21 | 23 | 29 | 37 |
| sequencer | 26 | 46 | 46 | 46 | 46 | 46 |
| shift_stage | 6 | 10 | 18 | 20 | 26 | 34 |

ALU (carry-chain) cells, `mul_dsp` DSP blocks and the wide-LUT and 3x3 numbers are in `costs.json`.

## How to read this

- **Use the single-cell nowidelut numbers to project.** They are smooth in W and the fits hold to a few LUTs.
- **The wide-LUT flow is not smooth** (the mapper changes its mind between widths), so do not extrapolate from it; the nowidelut flow is the card's default (`synthesis.nowidelut.default`).
- **The 3x3 array is not nine times the single cell.** The generated top pins each cell's configuration, so constant-config logic folds away. It tells you what a hard-wired cluster costs, not a runtime-configurable one.
- **The second port is a build parameter** set from the compiler's ICM flag (adder `carry_mode`, multiplier `wide_mode`): a cell the compiler did not flag is built without it and carries no cost for it.
- **W-independent cells:** latch, router, shift_stage and mul_dsp (plus one DSP block) cost the same LUTs at every width and only add flip-flops. The sequencer saturates at 8 bits and FlexGrid refuses it below 8.
- Not covered: place-and-route or timing.

## On the Tang Nano 20K (20,736 LUT4)

Whole cells that fit if the device held nothing else (single-cell nowidelut cost, ignoring routing and the 15,552 flip-flop limit):

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| accumulator | 329 | 269 | 235 | 222 | 188 | 155 |
| adder | 2304 | 1595 | 987 | 901 | 715 | 560 |
| branch | 482 | 324 | 186 | 169 | 132 | 103 |
| compare | 2304 | 1885 | 1219 | 1091 | 942 | 740 |
| latch | 2592 | 2592 | 2592 | 2592 | 2592 | 2592 |
| mask | 2304 | 1595 | 987 | 901 | 715 | 560 |
| merge | 987 | 829 | 628 | 592 | 505 | 423 |
| mul | 1296 | 296 | 66 | 52 | 28 | 15 |
| mul_dsp | 4147 | 4147 | 4147 | 4147 | 4147 | 4147 |
| nano | 339 | 232 | 143 | 130 | 103 | 80 |
| priority | 100 | 95 | 85 | 83 | 77 | 71 |
| ram | 2073 | 1481 | 942 | 864 | 691 | 545 |
| router | 2073 | 2073 | 2073 | 2073 | 2073 | 2073 |
| sequencer | 987 | 576 | 576 | 576 | 576 | 576 |
| shift_stage | 4147 | 4147 | 4147 | 4147 | 4147 | 4147 |
