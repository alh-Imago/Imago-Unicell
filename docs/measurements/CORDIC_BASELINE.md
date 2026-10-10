# CORDIC baseline: the UniCell design against hand-written 32-bit hardware (ledger #1036 addendum 58)

**What was compared.** The UniCell flex CORDIC z-convergence example (`nano/examples/cordic_z_convergence.icm-hier.json`, 4 stages, 32-bit signed, 36 cells after the generator merges the zero sources; the one proven on the board in addendum 7) against hand-written Verilog for the SAME function: each stage does `z > 0 -> z - K, else z + K` with K = 45000, 26565, 14036, 7125 (note `z == 0` takes the add side, as the branch cell's `route_equal` does). Source: `fpga/baselines/cordic_z_v1/`; tool and numbers: `tools/cordic_baseline_v1.py`, `docs/measurements/cordic_baseline_v1.json`; tests: `tests/vm/test_cordic_baseline_v1.py`.

**Five designs.**
- `pipe` hand-written pipeline, one adder per stage, a valid bit, no back-pressure.
- `hs` the same with the UniCell flex handshake (each stage holds one item and waits for the next stage's ack). This is the fairest like-for-like.
- `iter` one adder reused for the four steps (a loop); one item at a time.
- `pipe_naive` the first way I wrote the pipeline: both z-K and z+K are computed and one is picked (two adders per stage). Kept to show the cost of coding style.
- `UniCell` the generated design.

**Correct.** In iverilog all five give the same answer on 316 inputs (edge cases such as 0, +-1, +-2^31, +-45000, plus 300 random, all checked against an independent Python model); a deliberately wrong constant is caught. Latency, in clock cycles from accepting an item to its result: pipe 4, hs 4, iter 5, pipe_naive 4, **UniCell 20**.

## Size and speed (Tang Nano 20K part GW2AR-18C)

Counts come from synthesis of the bare design (system yosys, `synth_gowin -nowidelut`, the same script the assembler writes). Speed comes from place-and-route (yowasp yosys + nextpnr-himbaechel-gowin) of each design inside the same small shell (a 32-bit shift register in, one folded bit out; the shell alone is 59 LUT4 and 33 flip-flops), target 400 MHz so the router keeps trying, three seeds, the range is shown.

| design | LUT | ALU (carry) | LUT + ALU | flip-flops | Fmax range (MHz) |
|---|---|---|---|---|---|
| iter | 68 | 42 | 110 | 35 | 270 to 278 |
| pipe | 48 | 123 | 171 | 132 | 169 to 180 |
| hs | 56 | 123 | 179 | 132 | 166 to 183 |
| pipe_naive | 127 | 374 | 501 | 132 | 216 to 238 |
| **UniCell** | 389 | 374 | **763** | **933** | 265 to 277 |

**Reading it.** Against the like-for-like `hs` pipeline the UniCell design uses about 4.3 times the logic (763 against 179) and about 7 times the flip-flops (933 against 132), and takes 5 times the cycles for one item (20 against 4). Against the naively coded pipeline it is 1.5 times the logic. It is NOT slower: its clock range is higher than the tuned hand-written pipelines, probably because every UniCell cell registers its output so no path is long (my explanation; the critical paths were not examined), while each hand-written stage does the sign test, the constant choice and the add in one clock. The hand-written pipelines would also reach higher clocks with one more register stage; that was not tried, so the Fmax column compares these particular codings, not the best possible hand design.

## What this does and does not show

- It is a measurement of one small design (four stages). Do not extend the ratios to other designs without measuring them.
- The UniCell design holds one item at a time here (the unit paces it that way), and the test feeds one item at a time, so **throughput was not measured**. A hand-written pipeline can take an item every cycle; whether the UniCell design can was not tested.
- Synthesis and place-and-route only. Nothing was run on a board for this comparison (the UniCell CORDIC was run on the board in addendum 7).
- **The advantage of changing a design without re-synthesis is not exercised here.** The generated flex RTL bakes each cell's configuration in as a constant at synthesis, so on the Tang this design is re-synthesised like any other. That advantage belongs to the VM, the carrier line and silicon, where cells are loaded as data.
- The Fmax figures are place-and-route estimates inside a shell, not timing closure of a full unit (the full unit reached 165.8 MHz in addendum 6, which includes the SD and SPI parts).
- No claim is made here about the other arguments for UniCell (determinism, freeze and reload, one description for every target); this only prices the generality of the cells on one example.
