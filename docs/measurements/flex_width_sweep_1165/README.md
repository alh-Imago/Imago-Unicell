# Flex cell cost vs width (ledger #975, extended #976)

Measured by `tools/flex_width_sweep_v1.py` (yosys `synth_gowin`, synthesis only -- no place-and-route, no timing, nothing run on a board). Raw numbers: `costs.json`; they are also carried in the Tang Nano 20K MAN file under `cell_costs`. Regenerate this file with `python3 tools/flex_width_sweep_v1.py --readme-only`.

Each cell was built at widths 4, 8, 16, 18, 24, 32: the **single cell** alone (every configuration port a real input -- the honest per-cell cost) in the card's default `-nowidelut` flow and in the historical wide-LUT flow, and a **3x3 array** (nine cells in the generated assembler top). The adder, multiplier and DSP multiplier were also built **with their second output port** (`SECOND_PORT=1`).

## Single cell, LUT4 (default `-nowidelut` flow)

| cell | W4 | W8 | W16 | W18 | W24 | W32 | fit LUT4 vs W | max error |
|---|---|---|---|---|---|---|---|---|
| accumulator | 25 | 43 | 54 | 57 | 69 | 85 | 1.99W +21.6 | 5.4 |
| adder | 9 | 13 | 21 | 23 | 29 | 37 | 1.00W +5.0 | 0.0 |
| branch | 44 | 72 | 127 | 143 | 177 | 235 | 6.77W +17.9 | 3.4 |
| compare | 6 | 6 | 6 | 6 | 6 | 6 | 6 (flat) | 0.0 |
| corner | 14 | 14 | 14 | 14 | 14 | 14 | 14 (flat) | 0.0 |
| cross | 14 | 14 | 14 | 14 | 14 | 14 | 14 (flat) | 0.0 |
| div | 39 | 64 | 116 | 127 | 163 | 213 | 6.21W +14.8 | 1.9 |
| latch | 8 | 8 | 8 | 8 | 8 | 8 | 8 (flat) | 0.0 |
| mask | 9 | 13 | 21 | 23 | 29 | 37 | 1.00W +5.0 | 0.0 |
| merge | 22 | 27 | 35 | 35 | 41 | 49 | 0.94W +18.9 | 1.1 |
| mul | 5 | 5 | 5 | 5 | 5 | 5 | -0.00W^2 +0.00W +5.0 | 0.0 |
| mul_dsp | 5 | 5 | 5 | 5 | 5 | 5 | 5 (flat) | 0.0 |
| nano | 87 | 115 | 191 | 232 | 276 | 407 | 11.24W +26.9 | 20.7 |
| priority | 179 | 190 | 217 | 224 | 238 | 262 | 2.98W +167.7 | 2.7 |
| ram | 10 | 14 | 22 | 24 | 30 | 38 | 1.00W +6.0 | 0.0 |
| router | 9 | 9 | 9 | 9 | 9 | 9 | 9 (flat) | 0.0 |
| sequencer | 31 | 36 | 36 | 36 | 36 | 52 | 36 (saturates from W8; no useful fit) | - |
| shift_stage | 5 | 5 | 5 | 5 | 5 | 5 | 5 (flat) | 0.0 |

## With the second output port built (`SECOND_PORT=1`), LUT4 / DFF

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| adder (port off -> on) | 9/7 -> 13/10 | 13/11 -> 17/14 | 21/19 -> 25/22 | 23/21 -> 27/24 | 29/27 -> 33/30 | 37/35 -> 41/38 |
| mul (port off -> on) | 5/6 -> 8/12 | 5/10 -> 8/20 | 5/18 -> 8/36 | 5/20 -> 8/40 | 5/26 -> 8/52 | 5/34 -> 8/68 |
| mul_dsp (port off -> on) | 5/6 -> 8/12 | 5/10 -> 8/20 | 5/18 -> 8/36 | 5/20 -> 8/40 | 5/26 -> 8/52 | 5/34 -> 8/68 |

## Build-parameter variants (ledger #1021/#1022), LUT4 / DFF

| cell variant | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| ram oneshot (default -> variant) | 10/7 -> 11/7 | 14/11 -> 15/11 | 22/19 -> 23/19 | 24/21 -> 25/21 | 30/27 -> 31/27 | 38/35 -> 39/35 |
| ram hold (default -> variant) | 10/7 -> 12/8 | 14/11 -> 16/12 | 22/19 -> 24/20 | 24/21 -> 26/22 | 30/27 -> 32/28 | 38/35 -> 40/36 |

The ram's one-shot preload (`OFFER_PRELOAD`) costs nothing measurable; HOLD adds about two LUT4 and one flip-flop at every width. The priority cell is a single measured cell (all three modes in one build): about 3W + 194 LUT4, 155 ALU, W + 62 flip-flops.

## Single cell, flip-flops (DFF)

| cell | W4 | W8 | W16 | W18 | W24 | W32 |
|---|---|---|---|---|---|---|
| accumulator | 31 | 43 | 59 | 63 | 75 | 91 |
| adder | 7 | 11 | 19 | 21 | 27 | 35 |
| branch | 27 | 39 | 63 | 69 | 87 | 111 |
| compare | 7 | 11 | 19 | 21 | 27 | 35 |
| corner | 21 | 37 | 69 | 77 | 101 | 133 |
| cross | 21 | 37 | 69 | 77 | 101 | 133 |
| div | 23 | 40 | 73 | 81 | 105 | 138 |
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

## Flow variants (ledger #1165), LUT4 / ALU / DFF / MULT at the widest and the card-typical width

| cell | flow | W18 | W32 |
|---|---|---|---|
| accumulator | default (-nowidelut) | 57/61/63/0 | 85/103/91/0 |
| accumulator | -nodsp (no DSP inference) | 57/61/63/0 | 85/103/91/0 |
| accumulator | -family gw2a (the card's chip) | 57/61/63/0 | 85/103/91/0 |
| adder | default (-nowidelut) | 23/18/21/0 | 37/32/35/0 |
| adder | -nodsp (no DSP inference) | 23/18/21/0 | 37/32/35/0 |
| adder | -family gw2a (the card's chip) | 23/18/21/0 | 37/32/35/0 |
| branch | default (-nowidelut) | 143/35/69/0 | 235/63/111/0 |
| branch | -nodsp (no DSP inference) | 143/35/69/0 | 235/63/111/0 |
| branch | -family gw2a (the card's chip) | 143/35/69/0 | 235/63/111/0 |
| compare | default (-nowidelut) | 6/17/21/0 | 6/31/35/0 |
| compare | -nodsp (no DSP inference) | 6/17/21/0 | 6/31/35/0 |
| compare | -family gw2a (the card's chip) | 6/17/21/0 | 6/31/35/0 |
| corner | default (-nowidelut) | 14/0/77/0 | 14/0/133/0 |
| corner | -nodsp (no DSP inference) | 14/0/77/0 | 14/0/133/0 |
| corner | -family gw2a (the card's chip) | 14/0/77/0 | 14/0/133/0 |
| cross | default (-nowidelut) | 14/0/77/0 | 14/0/133/0 |
| cross | -nodsp (no DSP inference) | 14/0/77/0 | 14/0/133/0 |
| cross | -family gw2a (the card's chip) | 14/0/77/0 | 14/0/133/0 |
| div | default (-nowidelut) | 127/29/81/0 | 213/45/138/0 |
| div | -nodsp (no DSP inference) | 127/29/81/0 | 213/45/138/0 |
| div | -family gw2a (the card's chip) | 127/29/81/0 | 213/45/138/0 |
| latch | default (-nowidelut) | 8/0/4/0 | 8/0/4/0 |
| latch | -nodsp (no DSP inference) | 8/0/4/0 | 8/0/4/0 |
| latch | -family gw2a (the card's chip) | 8/0/4/0 | 8/0/4/0 |
| mask | default (-nowidelut) | 23/0/27/0 | 37/0/43/0 |
| mask | -nodsp (no DSP inference) | 23/0/27/0 | 37/0/43/0 |
| mask | -family gw2a (the card's chip) | 23/0/27/0 | 37/0/43/0 |
| merge | default (-nowidelut) | 35/0/23/0 | 49/0/37/0 |
| merge | -nodsp (no DSP inference) | 35/0/23/0 | 49/0/37/0 |
| merge | -family gw2a (the card's chip) | 35/0/23/0 | 49/0/37/0 |
| mul | default (-nowidelut) | 5/0/20/1 | 5/0/34/1 |
| mul | -nodsp (no DSP inference) | 387/18/20/0 | 1274/32/34/0 |
| mul | -family gw2a (the card's chip) | 5/0/20/1 | 5/0/34/1 |
| mul_dsp | default (-nowidelut) | 5/0/20/1 | 5/0/34/1 |
| mul_dsp | -nodsp (no DSP inference) | 5/0/20/1 | 5/0/34/1 |
| mul_dsp | -family gw2a (the card's chip) | 5/0/20/1 | 5/0/34/1 |
| nano | default (-nowidelut) | 232/0/48/0 | 407/0/76/0 |
| nano | -nodsp (no DSP inference) | 232/0/48/0 | 407/0/76/0 |
| nano | -family gw2a (the card's chip) | 232/0/48/0 | 407/0/76/0 |
| priority | default (-nowidelut) | 224/122/80/0 | 262/122/94/0 |
| priority | -nodsp (no DSP inference) | 224/122/80/0 | 262/122/94/0 |
| priority | -family gw2a (the card's chip) | 224/122/80/0 | 262/122/94/0 |
| ram | default (-nowidelut) | 24/0/21/0 | 38/0/35/0 |
| ram | -nodsp (no DSP inference) | 24/0/21/0 | 38/0/35/0 |
| ram | -family gw2a (the card's chip) | 24/0/21/0 | 38/0/35/0 |
| router | default (-nowidelut) | 9/0/23/0 | 9/0/37/0 |
| router | -nodsp (no DSP inference) | 9/0/23/0 | 9/0/37/0 |
| router | -family gw2a (the card's chip) | 9/0/23/0 | 9/0/37/0 |
| sequencer | default (-nowidelut) | 36/0/46/0 | 52/0/46/0 |
| sequencer | -nodsp (no DSP inference) | 36/0/46/0 | 52/0/46/0 |
| sequencer | -family gw2a (the card's chip) | 36/0/46/0 | 52/0/46/0 |
| shift_stage | default (-nowidelut) | 5/0/20/0 | 5/0/34/0 |
| shift_stage | -nodsp (no DSP inference) | 5/0/20/0 | 5/0/34/0 |
| shift_stage | -family gw2a (the card's chip) | 5/0/20/0 | 5/0/34/0 |

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
| accumulator | 829 | 482 | 384 | 363 | 300 | 243 |
| adder | 2304 | 1595 | 987 | 901 | 715 | 560 |
| branch | 471 | 288 | 163 | 145 | 117 | 88 |
| compare | 3456 | 3456 | 3456 | 3456 | 3456 | 3456 |
| corner | 1481 | 1481 | 1481 | 1481 | 1481 | 1481 |
| cross | 1481 | 1481 | 1481 | 1481 | 1481 | 1481 |
| div | 531 | 324 | 178 | 163 | 127 | 97 |
| latch | 2592 | 2592 | 2592 | 2592 | 2592 | 2592 |
| mask | 2304 | 1595 | 987 | 901 | 715 | 560 |
| merge | 942 | 768 | 592 | 592 | 505 | 423 |
| mul | 4147 | 4147 | 4147 | 4147 | 4147 | 4147 |
| mul_dsp | 4147 | 4147 | 4147 | 4147 | 4147 | 4147 |
| nano | 238 | 180 | 108 | 89 | 75 | 50 |
| priority | 115 | 109 | 95 | 92 | 87 | 79 |
| ram | 2073 | 1481 | 942 | 864 | 691 | 545 |
| router | 2304 | 2304 | 2304 | 2304 | 2304 | 2304 |
| sequencer | 668 | 576 | 576 | 576 | 576 | 398 |
| shift_stage | 4147 | 4147 | 4147 | 4147 | 4147 | 4147 |
