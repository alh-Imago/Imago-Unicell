# Gowin GW2A sizing, all cores incl. corner / cross / merge / mul v5 (ledger #1036)
Synthesis only (yosys `synth_gowin`, generic mapping, no place-and-route, no timing). Tang Nano 20K = 20,736 LUT4 / 15,552 FF.
Reproduce: `tools/gowin_sizing/size_cells.sh full|lean`, `tools/gowin_sizing/size_carrier.sh`.
"full" = cell with its own addon chain; "lean" = core alone (addon chain stubbed, a lower bound, not a working cell).

| core | full LUT4 | full FF | lean LUT4 | lean FF |
|---|---|---|---|---|
| ram (with HOLD) | 2422 | 100 | 387 | 80 |
| latch | 243 | 38 | 186 | 25 |
| accumulator | 2398 | 129 | 360 | 109 |
| compare | 575 | 61 | 484 | 48 |
| branch | 3036 | 140 | 718 | 120 |
| sequencer | 686 | 69 | 173 | 55 |
| command | 338 | 45 | 338 | 45 |
| adder (with carry word) | 2539 | 109 | 441 | 89 |
| nano_gate | 3898 | 113 | 1750 | 93 |
| mul v4 | 7015 | 100 | 5723 | 80 |
| mul v5 (high-word output) | 11601 | 139 | 10786 | 119 |
| priority | 3064 | 110 | 979 | 90 |
| corner | 202 | 139 | 202 | 139 |
| cross | 66 | 138 | 66 | 138 |
| merge | 2644 | 136 | 956 | 116 |

Full carrier position (every core shell, one shared addon chain): v1d 18,238 LUT4 / 1,294 FF (87.9% of LUT4); v1 18,246 / 1,292.

Notes: mul v5 costs about 5,000 LUT4 more than v4 (the second output word) -- worth checking whether the multiplier core can share logic. Corner/cross are tiny but FF-heavy (four one-word slices). One carrier position fills ~88% of a Nano 20K, so the Nano holds one position only.

## Why mul v5 is ~5,000 LUT4 bigger than v4 (checked)
The control logic for the second word is small. The difference is the multiplier itself: v4 only uses Product[31:0], so synthesis deletes the upper half of the partial-product array; v5 needs Product[63:32], so the whole 32x32 array stays.
Multiplier alone (yosys synth_gowin): full 64-bit product = 6739 LUT4 + 1698 smaller LUTs + 97 ALU; low 32 bits only = 3277 LUT4 + 966 smaller LUTs + 32 ALU. So the high half costs about as much again as the low half -- it is inherent to the array, not a v5 defect.
Caveat: the sizing scripts count LUT1-4 only; ALU (carry-chain) cells are not in the totals, so all figures under-count slightly.
Ways down (not done, need a decision): (1) use the Gowin DSP multiplier blocks on FPGA (the repo already has a DSP wrapper cell) -- near-zero LUTs, FPGA-only, not silicon; (2) a sequential shift-add multiplier -- ~100-200 LUTs but 32 ticks of latency instead of 0; (3) keep it, since mul is one core of fourteen per carrier position.

## Decision (Alan, 2026-10-08)
The Gowin DSP blocks are the preferred multiplier on FPGA (the flex and sub variants already work that way). The pure-logic mul core (v4/v5/v5c) is the FALLBACK / ASIC path and stays as it is. The full carrier position (~18.2k LUT4+, 88%+ of a Nano 20K) is not meant to fit the current Tang card; it is an ASIC design call, so no carrier change is made for size. A DSP-based carrier mul would mean a two-step carrier design (approached before) -- not started. Shift stays combined coarse+fine (limited core-config bus room).
