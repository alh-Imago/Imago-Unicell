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
