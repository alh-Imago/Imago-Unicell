# S-Core

A prototype of a **modular, interrupt-free RISC core whose datapath width is a dial.** One RV32I binary runs unchanged at 1, 2, 4, 8, 16 or 32 bits per cycle: "fusing slices" changes the speed, never the result.

This is separate from the UniCell cell grid. The aim is to see whether a sea of identical narrow slices can be fused into wider cores (or split into many narrow ones) while still running ordinary compiled software. Branch: `S-Core_go`. Status and numbers are in [`latest.md`](latest.md).

## The idea

- **One ISA at every width.** The datapath width W and the instruction width (32) are separate things. A 1-bit core takes 32 cycles on a 32-bit add; a 32-bit core takes 1. The compiler sees RV32I either way.
- **Everything is streamed one W-bit digit per cycle**, least significant first (shift-left runs most significant first so it can work in place). The register file and data memory are W-wide RAMs addressed `{register, digit}`. There is one W-bit adder with a carry flop; the pc goes through it too.
- **No interrupts.** The core only runs its own instruction stream. (The event table, dedicated I/O cores and task queue are design ideas, not built yet.)
- **Width is chosen at task start, not mid-task.** Changing width mid-task would mean re-slicing register state spread across slices, so the plan is to allocate a width per task from a descriptor.

## Files

| file | what it is |
|---|---|
| `uc_core.v` | the core, v1 (parameter `W`), no RAM inside |
| `uc_core_v2.v` | v2: pc / immediate / address as digit shift registers, smaller, same behaviour |
| `tb.v` | testbench: RAM models, runs a hex program, dumps registers, memory, cycles |
| `runtests.py` | mini assembler, independent RV32I reference simulator, random program generator, runner |
| `synth_all.sh` | area script (iCE40 and Xilinx counts via yosys) |
| `uc_core_rw.v`, `tb_rw.v` | runtime-width core (width given at task start) and its testbench |
| `sc_sys.v`, `tb_sys.v` | the array: 32 slices, queues and the dedicated dispatcher; system testbench |
| `sched_tests.py` | task kernels, correctness gate and the scheduling experiments |
| `sc_sys_v2.v`, `tb_sys_v2.v`, `sched_tests_v2.py` | v2 of the array: look-ahead overtaking, reserved region, critical flag (v1 files kept) |
| `dispatch_tests.py` | dispatcher policy matrix (strict FIFO, overtaking, reserved region) |
| `results.md` | measured cycles per instruction and iCE40 area per width |
| `latest.md` | current state of this line |

## The array and the dispatcher

`sc_sys.v` holds 32 slices. A task asks for a width (1, 2, 4, 8, 16 or 32 slices); a **dedicated dispatcher** (a small hardware state machine, so no compute core ever runs scheduling code) finds an aligned free group, starts a core of that width, and frees the slices when the task ends. Tasks wait in a submission queue; finished tasks are reported in a completion queue that the host polls. No interrupts, no preemption: a task runs to completion.

## Run it

Needs `iverilog` (and `yosys` for area, `verilator` for the array experiments):

```
cd s-core
python3 -I runtests.py                       # all programs, all widths (v1)
python3 -I runtests.py --core uc_core_v2     # same tests on v2
python3 -I runtests.py --widths 4 32 --random 10
python3 sched_tests.py                       # array: correctness gate + scheduling experiments
yosys -p "read_verilog -sv uc_core.v; chparam -set W 4 uc_core; hierarchy -top uc_core; synth_ice40 -top uc_core; stat"
```

The runner compiles one simulator per width, runs every program on the hardware model and on the reference simulator, and compares final registers, data memory, pc and instruction count.

## Targets
Tang Nano 20K (Sipeed) and a Kintex-7 XC7K480T card. The Kintex card has no PCIe side, so JTAG is the only way in: programs and results would go through the Xilinx JTAG user register. On the Tang Nano the onboard USB bridge (UART) is the natural route. Neither loader exists yet.

## Limits (be aware)

Word loads and stores only (no `lb`/`lh`/`sb`/`sh`), aligned only; `ebreak`/`ecall` halt; anything else illegal traps. Instruction fetch is one 32-bit read. No fetch/execute overlap. Area figures exclude the register file and memories.

## Priority dispatcher v3
`sc_sys_v3.v` adds the request table, task table (start/end/slot), priority queues and best-fit placement; see `latest.md` and `matrix_v3.txt`. Run with `python3 sched_tests_v3.py` (needs Verilator).
