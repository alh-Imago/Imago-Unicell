# div_cell_v4s (sub family, 32 bits, no ack): size and depth against bits-per-clock (ledger #1072)

Measured with `tools/div_cell_sweep_v1.py --family sub` (yosys `synth_gowin -nowidelut`, then nextpnr-himbaechel-gowin for GW2AR-LV18QN88C8/I7,
seed 1). Synthesis and place-and-route only, nothing run on a board. Raw numbers: `results.json` (older run, 2 seeds) and the table below (re-run
with the depth column). Wrapper alone: 78 LUT, 32 ALU, 158 DFF. "Cell" = wrapper-with-cell minus wrapper alone (an approximation).

| K (bits/clock) | latency (clocks) | cell LUT | cell ALU | cell DFF | gate depth (whole wrapper) | nextpnr Fmax MHz (NOT TRUSTED, see below) |
|--:|--:|--:|--:|--:|--:|--:|
| 1  | 32 | 247  | 23   | 89 | 25  | 388 |
| 2  | 16 | 343  | 61   | 89 | 39  | 401 |
| 4  | 8  | 535  | 137  | 89 | 70  | 410 |
| 8  | 4  | 918  | 289  | 89 | 132 | 428 |
| 32 | 1  | 3222 | 1198 | 89 | 504 | 433 |

(Wrapper alone has gate depth 18.) Latency is exact and is what the bench checks: ceil(32/K) clocks from the edge that takes valid_in.

## The Fmax column cannot be used
nextpnr reports a FASTER clock for K=32 than for K=1, although the K=32 chain is 20 times deeper. Its critical path at K=32 is only the boot/busy
control logic (2.3 ns, 2 logic stages); the 32-deep subtract-and-select chain does not appear as a timed path. A synthetic test (a plain chain of N
subtract-and-select steps between flip-flops, no divider) showed the same: N=1 reported 1501 MHz, N=32 reported 682 MHz. So for designs of this
shape, **this tool's Fmax does not follow the logic depth**. I have not found out why (not studied; do not assume a reason). No Fmax is claimed for the
divider cells from this method, flex or sub.

## What is usable
- LUT, ALU and DFF counts (read from yosys, not from the timing engine).
- Gate depth (`ltp -noff` after techmap, simple gates, relative only, not nanoseconds): 25 at K=1 up to 504 at K=32. The flex cell measured the same way
  gives 24 / 69 / 503 at K = 1 / 4 / 32, so the two cells have the same arithmetic depth, as they should.
- Observation, cause not established: looped K=1 costs 247 LUT here against about 122 in the #1070 flex table, so the sub cell is NOT smaller than
  the flex cell as built. The sub cell starts an operation straight from the inputs on the first clock (inputs and registers are selected by a
  multiplexer in front of the chain); that is a candidate reason, not a measured one. The two numbers also come from different wrappers, so no
  family-to-family area comparison is claimed.
- A real Fmax needs a different tool or a real board; K is chosen on area and latency until then.
