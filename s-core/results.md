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

## Runtime-width core and the array (`uc_core_rw.v`, `sc_sys.v`)
`uc_core_rw.v` chooses its width when a task starts (`lw_in` = log2 bits per cycle). Same 276-run regression
as v1/v2: 276/276 match the reference, cycle counts equal v2's plus 1 cycle for the start handshake.
It is a behavioural simulation model (32-bit buses masked to the current width), not an area-optimised design.

`sc_sys.v`: 32 slices, a core instance per slice (startable at widths that divide its slice number), private
register file and data memory per instance, shared read-only code image, submission queue, completion queue,
and a dedicated dispatcher (hardware FSM). No interrupts: a core runs to EBREAK and goes idle; the host polls
the completion queue (task id, a0, start/end cycle, width, trap flag).

Dispatcher: pops a descriptor, finds the lowest aligned free group in one cycle, marks it busy, pulses start.
Back-to-back launches are 3 cycles apart (measured). Strict FIFO: a head task that does not fit waits.

Correctness gate: a run passes only if every task completed, none trapped, and every task's a0 equals the
reference simulator's. All runs below passed it.

### Scheduling experiment (S=32, 48 tasks, mean of 5 workloads, everything submitted at t=0)
Tasks: sum, fib, crc, gcd, multiply, bubble-sort kernels (30 to 1500+ instructions); 25% flagged critical.

| policy                         | makespan (cycles) | slice utilisation | critical latency | bulk latency |
|--------------------------------|-------------------|-------------------|------------------|--------------|
| all W=32, natural order        | 66441             | 100%              | 38259            | 33783        |
| all W=8, natural order         | 43844             | 94%               | 24078            | 21757        |
| all W=4, longest first         | 37306             | 99%               | 29868            | 28039        |
| critical W=8 / bulk W=4, critical first | 44378    | 86%               | 6496             | 26001        |
| critical W=16 / bulk W=4, critical first | 46353   | 86%               | 7631             | 28042        |

What it shows (this workload family only, one dispatcher policy):
- A narrower core costs more cycles per instruction but many more run at once: a fixed 32-wide core is the
  slowest overall (4 cycles/instr but one task at a time; also the fixed fetch/setup cycles are 128 slice-cycles
  per instruction at W=32 versus 66 at W=1).
- Giving critical tasks W=8 and bulk tasks W=4 with critical tasks submitted first gives about 3.7x lower
  critical latency than fixed W=8 for about the same makespan (+1%), at the price of about 19% higher bulk latency.
- With strict FIFO, submission order matters a lot. Wide tasks submitted among narrow ones make the queue head
  wait for a big free group: critical 32 / bulk 1 in natural order had 9% utilisation and a 468k-cycle makespan.
- Longest-first with a fixed narrow width gave the best makespan (about 15% better than fixed W=8 natural order).

Tools: `sched_tests.py` (needs Verilator; about 100x faster than iverilog for the 32-core system).
