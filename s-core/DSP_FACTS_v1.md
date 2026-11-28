# DSP blocks and the cost of multiply: facts so far (ledger #1573, 27 Nov 2026)

Purpose: the numbers the maths-side decision (S_CORE_TODO.md section G) needs. Nothing here is a design. Each line says where it comes from.

## 1. What a multiply costs today (measured on the host reference core, not on the card)
Program `programs/vgain.s` (the only registered example that multiplies; it does shift-and-add by hand). Instructions per output word, from `jobiss.reference` on one job per gain:

| gain (multiplier) | instructions per word (whole loop) |
|---|---|
| 0 | 11 |
| 1 | 18 |
| 2 | 24 |
| 3 | 25 |
| 128 | 60 |
| 255 | 67 |

The loop overhead outside the multiply is 10 instructions, so one 8-bit shift-and-add multiply costs 6 instructions per bit of the gain plus 1 per set bit plus 1: 57 instructions for gain 255 (matches the table: 67 - 10). A 32-bit multiplier would cost about 6 x 32 + 32 + 1 = 225 instructions (worked out from the same loop, NOT run).

## 2. Clocks per instruction (from card runs, with an important caveat)
`profiles/example_2x8_nu3_v2.cpi.txt` has card clocks at lw 0 (one block) for four example jobs; dividing by the reference core's instruction count for the same job (`jobs_cpi_*.json`):

| job | instructions | card clocks | clocks per instruction |
|---|---|---|---|
| vgain (60 words, gain 63) | 3,219 | 438,109 | 136 |
| vsum (100 words) | 635 | 93,582 | 147 |
| vmax (60 words) | 402 | 59,300 | 148 |
| vprefix (60 words) | 517 | 79,166 | 153 |

Caveats: that profile is the OLD 2-block, 8-slice build (19 Nov), not the hk 8 x 32 build; the clocks include start-up and the library I/O, so the figure is an upper bound per instruction for short jobs; the ratio depends on the slice count (a unit gets one instruction per S clocks, #1516). Treat 130 to 150 as the order of size at lw 0, not as a constant. Fusing (lw 1 to 3) divides it by up to about 6 (profile speedups 1.9, 3.6, 6.3 for lw 1 to 3).

## 3. What that means (arithmetic on the figures above, not a measurement)
An 8-bit shift-and-add multiply at lw 0 is about 57 x 136 = 7,750 clocks, about 0.15 ms at 50 MHz. A hardware `mul` instruction would itself cost one instruction slot (about 136 clocks at lw 0) plus the unit's own latency, so for an 8-bit multiply the gain would be roughly 50 times at lw 0, and the same order for a 32-bit one (about 225 instructions) times larger. Fused cores shrink both sides alike. This is the size of the prize, to be confirmed by a real run before any build.

## 4. DSP blocks per target card (vendor documents; not yet checked against our reports)
- Tang Nano 20K, GW2AR-18: 48 multipliers of 18 x 18 (Gowin product page; Sipeed datasheet says the block also supports 9 x 9 and 36 x 36 with a 54-bit accumulator).
- Kintex-7: DSP48E1 slices, each a 25 x 18 multiplier with 48-bit accumulator and pre-adder (Xilinx DS180); the Kintex-7 family maximum is 1,920 slices. The XC7K480T is the largest Kintex-7 part; I did not see its own row of the device table, so the exact count for our part is still to be read from DS180 table 6 or the Vivado report.
- Arria 10 GX 660 (10AX066, the Arria 10 line's part): 1,687 variable-precision DSP blocks, each configurable as two 18 x 19 multipliers (3,374 multipliers) or one 27 x 27 (Intel Arria 10 Device Overview).
- Arria 10 10AX115 also appears in the repo; its count was not looked up.
Consequence for the design (to check, not yet checked): none of these is a 32 x 32 multiplier. A 32-bit multiply on a DSP needs several blocks or several passes of one block, so a pool-wide unit should be built from a number of blocks that the board profile says is available, with the shift-and-add routine as the fallback.

## 5. What our builds use today
Every Kintex build in `k7/sizes_result_2026-11-17.txt` (S = 4, 8, 16) reports exactly 1 DSP48E1, unchanged with size, so nothing in the cores uses a DSP; the one block is unexplained (no multiply operator found in `sc_sys_v22.v` by a quick search; possibly the host link or inferred by the tool). To find out where it comes from.

## 6. Prior art in this repo (not yet read in full)
`docs/gowin_sizing_1036.md` (decision of 2026-10-08: DSP preferred on FPGA, logic multiplier the fallback), `nano/card_fit_v1.py` (DSP facts read per card from its manifest; an op that wants a DSP and finds none must not degrade silently), `nano/dsp_latency_v1.py` (the DSP's latency modelled as elapsed time; a two-arrival core waits however long). The Onion archive was not searched.

## 7. Measured on the card (ledger #1575, Alan's run of batches/mul_cost.score, hk8s32u32n1i1024, one block, 27 Nov 16:50)
All twelve runs correct. Block-0 clocks, two repeats each (they agree within 0.1 %):

| job | lw 0 | lw 5 |
|---|---|---|
| A: 40 words, gain 255 | 379,841 / 379,838 | 26,165 / 26,187 |
| B: 80 words, gain 255 | 753,247 / 753,229 | 51,397 / 51,398 |
| C: 80 words, gain 1 | 215,636 / 215,624 | 18,110 / 18,122 |

`mul_cost_calc_v1.py` on the means: lw 0 = 139.3 clocks per instruction (from B-A) and 137.1 (from B-C); lw 5 = 9.4 and 8.5. One 8-bit shift-and-add multiply (57 instructions): about 7,940 clocks = 0.16 ms at lw 0, and about 540 clocks = 0.011 ms at lw 5. Fixed start-up inside a run (job A minus 40 words at the marginal rate): about 6,400 clocks at lw 0 and about 950 at lw 5.
The 136 to 153 of section 2 (old 2 x 8 build) is confirmed on the hk build at lw 0. Fusing 32 lanes makes the multiply-heavy jobs 14.5 and 14.7 times faster (A, B); the light job C only 11.9 times (more of it is start-up and I/O).

## 8. 32-bit multiply measured on the card (ledger #1577, batches/mul32_cost.score run twice by Alan, 27 Nov 16:57; hk8s32u32n1i1024, one block)
All 32 runs correct (16 per batch run). Mean block-0 clocks over the four repeats of each condition (the two batch runs agree within 7 clocks at lw 0 and 17 at lw 5):

| job | lw 0 | lw 5 |
|---|---|---|
| A: 40 words, arg 0xFFFFFFFF | 1,296,180 | 85,023 |
| B: 80 words, arg 0xFFFFFFFF | 2,586,058 | 169,145 |
| C: 80 words, arg 1 | 205,260 | 15,544 |
| D: 80 words, arg 255 | 742,850 | 51,378 |

`mul32_cost_calc_v1.py`: clocks per instruction 137.8, 137.1, 137.1 (B-A, B-C, B-D) at lw 0 and 9.0, 8.8, 8.8 at lw 5. **One 32-bit shift-and-add multiply (224 instructions): about 30,900 clocks = 0.62 ms at lw 0; about 2,010 clocks = 0.040 ms at lw 5** (the prediction of 31,000 at lw 0 held). One whole word of the job: about 32,250 clocks (lw 0), 2,100 (lw 5). The 255 multiplier on the same program costs 742,850 clocks for 80 words at lw 0, within 1.4 % of vgain's 753,238 (the two programs differ only in the `>> 8` and the mask). A 32-bit multiply costs 4.0 times an 8-bit one. Fusing 32 lanes: 15.3 times faster for the 32-bit multiply, 14.5 for the 255 case, 13.2 for the light job. A hardware multiply instruction would take one instruction slot, so it would be about 224 times cheaper than this routine at both widths (138 clocks at lw 0, 9 at lw 5), plus the unit's own latency.

## 9. The XC7K480T's DSP count and the one unexplained DSP block (ledger #1589, 28 Nov 2026)

- **DSP count of our part:** the XC7K480T has **1,920 DSP48E1 slices** (AMD 7 series product selection guide, the Kintex-7 table row for XC7K480T; the same figure as the family maximum). The multiply unit of #1584 takes 3 per block: 8 blocks = 24, 1.25 % of the chip. (A web-source figure; not yet seen in a Vivado report of our own.)
- **The block that every Kintex build has:** it is the multiplication `40 * ((i - 8) >> 3)` in `fpga/blk_rd_v2.v` (status readout, line 90 in the "U" reply: it picks block i's 40-bit record out of the status vector); line 55 of the same file has the same constant multiply for `cur_bs`, which the tool merges into the same block. **Evidence:** yosys `synth_xilinx -family xc7` on blk_rd_v2.v alone gives 1 DSP48E1; with `40 * x` replaced by `(x << 5) + (x << 3)` it gives 0. So the cores use no DSP; this one is the host readout path, harmless but it also means "1 DSP" in the older reports is not a core.
- Whether Vivado puts the same multiply in a DSP block was not looked at (all numbers here are from yosys). The file is a proven file and was not changed; a corrected clone could remove the block, but nothing needs it.
