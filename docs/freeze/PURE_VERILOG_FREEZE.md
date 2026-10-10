# Freeze, save and restore on a pure Verilog CORDIC (no cells)

Alan's question (10 Oct 2026, 17:16): can the freeze system be added to a basic Verilog design, "no cells, nothing else, just that", to see whether the pure CORDIC stands up to it? Ledger addendum 65. Tool `tools/freeze_pure_v1.py`, tests `tests/vm/test_freeze_pure_v1.py`, numbers in `docs/measurements/freeze_pure_v1.json`.

**Answer: yes, and it is easy.** Two new files in `fpga/baselines/cordic_z_v1/` (the originals are untouched): `cordic_z_pipe_frz_v1.v` (no back-pressure) and `cordic_z_hs_frz_v1.v` (valid/ack handshake). Each adds a `freeze` input (every register holds) and a `scan_en`/`scan_in`/`scan_out` chain that links all 132 state bits into one shift register. About 10 lines each.

## Test (simulation)
Design A runs two items. At every cut where an output was still to come (cuts 1 to 5; the pipeline is only 4 deep, so only 5 positions hold words in flight), the freeze is raised, the 132 bits are shifted out of A into a never-fed copy B (A's chain recirculates so A is restored), both are released together. **B gave the same values on the same cycles as A at all 5 cuts, for both designs, and A matched the Python model.** Loading zeros instead of A's bits broke all 5 cuts in both designs.

## Cost (system yosys `synth_gowin -nowidelut`; nextpnr in a small wrapper, 3 seeds, Tang Nano 20K part)
| design | LUT | ALU | DFF | placed LUT4 (wrapper included) |
|---|---|---|---|---|
| pipe | 48 | 123 | 132 | 172 to 202 |
| pipe + freeze + scan | 179 | 123 | 132 | 271 to 273 |
| hs | 56 | 123 | 132 | 158 to 175 |
| hs + freeze + scan | 192 | 123 | 132 | 257 to 260 |

The scan chain costs about **one LUT per state bit and no extra flip-flops**: +131 LUT for 132 bits (pipe), +136 (hs). Fmax in the wrapper did not drop (it came out higher, 320 to 340 MHz against 166 to 183 MHz); I did not investigate why, and it is probably an artefact of the wrapper and the arithmetic packing, so no claim is made about speed.

## What this does to the argument
- The freeze-and-restore idea is **not unique to UniCell**. A pure design gets it with a clock enable and a scan chain, written by hand per design. The earlier claim that a pure design "has no equivalent" was wrong as written; addendum 59 said "unless scan logic is added", and this shows the scan logic is small.
- What is left for UniCell is **uniformity and automation**: one scan structure could be added by the generator to every design built from cells, and the saved state would line up with the VM's state. This is an argument, not a measurement. Not tested: the same scan chain on the UniCell flex design (estimated at about one LUT per dynamic bit from the pure result; the capture list says up to 1,600 bits before optimisation), a timed comparison of the effort, or any benefit of the saved state being readable.
- Also not shown: anything on a board; a freeze held longer than a few cycles in a real system; the environment (the feed and the consumer) stopping with the freeze, which the pure designs assume (the pipe has no back-pressure, so a producer that does not stop loses items; the handshake version masks `in_ack` and `out_valid` while frozen).
