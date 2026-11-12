# Width-selectable digit-serial RV32I core - first results

Files: `uc_core.v` (core), `tb.v` (RAM models + dump), `runtests.py` (assembler, reference RV32I simulator, runner).
Run: `python3 -I runtests.py` (needs iverilog). Area: `yosys -p "read_verilog -sv uc_core.v; chparam -set W 4 uc_core; hierarchy -top uc_core; synth_ice40 -top uc_core; stat"`.

## Correctness
276 runs (6 directed programs + 40 random programs, x 6 widths) all match an independent
reference simulator on final registers, data memory, pc and instruction count.
A planted bug in the signed-compare logic was caught (checked), so the suite can fail.

## Cycles per instruction (same binary at every width)
| program     | W=1   | W=2   | W=4   | W=8   | W=16 | W=32 |
|-------------|-------|-------|-------|-------|------|------|
| sum100      | 65.80 | 33.90 | 17.95 | 9.98  | 5.99 | 4.00 |
| bubblesort  | 77.01 | 39.58 | 20.86 | 11.51 | 6.83 | 4.49 |
| crc32       | 66.16 | 34.17 | 18.17 | 10.17 | 6.18 | 4.18 |
| random avg  | 69.83 | 35.99 | 19.08 | 10.60 | 6.38 | 4.27 |

Model: ALU/branch = 2N+2 cycles, load/store = 3N+2, shifts add a few, N = 32/W.

## Area (yosys, iCE40 4-LUT, core logic only - register file and memories excluded)
| W  | LUT4 | carry | flops | LUT x CPI (lower = better) |
|----|------|-------|-------|----------------------------|
| 1  | 469  | 41    | 122   | 32.7k |
| 2  | 476  | 52    | 121   | 17.1k |
| 4  | 478  | 50    | 120   | 9.1k  |
| 8  | 547  | 50    | 119   | 5.8k  |
| 16 | 740  | 53    | 118   | 4.7k  |
| 32 | 1258 | 55    | 118   | 5.4k  |

## Simplifications to keep in mind
- Instruction fetch is a whole 32-bit word in one cycle (not streamed).
- Word loads/stores only (no LB/LH/SB/SH), aligned only. EBREAK/ECALL halt.
- pc, ir and the address register are 32-bit flops read/written through variable-index muxes.
- No overlap of fetch / pc update with execute.

## v2: pc, immediate and address as digit shift registers (`uc_core_v2.v`)
Same behaviour and cycle counts as v1 (276/276 runs match the reference). Core logic only, RAMs excluded.

| W  | iCE40 LUT4 v1 -> v2 | Xilinx LUT6 v1 -> v2 | flops v1 -> v2 |
|----|---------------------|----------------------|----------------|
| 1  | 469 -> 326 (-30%)   | 342 -> 239 (-30%)    | 122 -> 154 |
| 4  | 478 -> 383 (-20%)   | 488 -> 329 (-33%)    | 120 -> 152 |
| 8  | 547 -> 484 (-12%)   | 608 -> 405 (-33%)    | 119 -> 151 |
| 16 | 740 -> 677 (-9%)    | 977 -> 668 (-32%)    | 118 -> 150 |
| 32 | 1258 -> 1108 (-12%) | 1616 -> 890 (-45%)   | 118 -> 150 |

Ablation on v1 (W=1, knocking out one block at a time, iCE40 LUT4): pc write path ~91, address register
write path ~75, immediate digit read ~46, pc digit read ~34, immediate decode ~27; together ~270 of 469.
The imm shift register was not measured separately from the pc and address changes.

Not reported: Gowin (Tang Nano) LUT counts. yosys 0.33's Gowin mapper gave inflated, unreliable numbers
(hundreds of LUT1 and mux cells); use the Gowin tool for those.

Tools: `synth_all.sh file module W` prints the iCE40 / Xilinx counts. `runtests.py --core uc_core_v2` tests v2.
