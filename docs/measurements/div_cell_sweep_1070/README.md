# div_cell_v4sa: size and speed against bits-per-clock (ledger #1070)

Measured with `tools/div_cell_sweep_v1.py` (yosys `synth_gowin -nowidelut`, then nextpnr-himbaechel-gowin for the Tang Nano 20K part GW2AR-LV18QN88C8/I7,
2 seeds, target 400 MHz so the router keeps trying). Synthesis and place-and-route only, nothing run on a board. Raw numbers: `results.json`.

"Cell only" figures are the wrapper-with-cell minus the wrapper alone (an approximation: the wrapper's own LFSR/XOR logic is in both).
"Clocks" = the capture clock plus ceil(W/K) compute clocks (what the bench checks, exactly).

| W | K (bits/clock) | clocks | cell LUT | cell ALU | cell DFF | Fmax MHz (seed 1, seed 2) |
|--:|--:|--:|--:|--:|--:|--|
| 18 | 1 | 19 | 81 | 27 | 78 | 289.0, 316.8 |
| 18 | 2 | 10 | 115 | 44 | 77 | 298.5, 322.5 |
| 18 | 4 | 6 | 203 | 84 | 77 | 278.9, 307.3 |
| 18 | 8 | 4 | 360 | 159 | 76 | 295.0, 294.6 |
| 18 | 18 | 2 | 865 | 374 | 77 | 233.9, 233.8 |
| 32 | 1 | 33 | 122 | 29 | 121 | 261.6, 247.8 |
| 32 | 2 | 17 | 184 | 60 | 120 | 251.1, 221.8 |
| 32 | 4 | 9 | 310 | 124 | 119 | 252.0, 235.0 |
| 32 | 8 | 5 | 559 | 254 | 118 | 302.4, 333.1 |
| 32 | 32 | 2 | 2070 | 1040 | 116 | 225.8, (routing failed on seed 2) |

Reading it (what the numbers support, and what they do not):
- Area grows steeply with K (W=32: about 122 LUT looped, about 2,070 LUT fully chained, roughly 17 times) while the clock count falls from 33 to 2.
- Fmax moves much less than area. The spread between the two seeds is up to about 30 MHz, so differences under about 15% are noise; the pattern
  across K is not clean (K=8 at W=32 came out fastest) and should not be read as a trend. The fully chained W=32 form still reached about 226 MHz:
  its critical path is 28 logic stages in 4.43 ns (reported by nextpnr), consistent with the staggered carry chains of restoring division
  overlapping rather than adding. This was read from one run's report, not studied further.
- All of these Fmax figures are far above the 27 MHz board clock, so at that clock none of them is the limit; what K buys is fewer clocks, what it costs is area.
- The W=32, K=32 row has a single seed (the second seed failed to route, "Routing design failed", a placement-congestion result for a 2,100-LUT block, not a timing failure).
- Cell DFF is nearly the same for every K (state is the same registers); the wrapper's own registers are subtracted.
