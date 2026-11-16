# S-Core

A prototype of a **modular, interrupt-free RISC core whose datapath width is a dial.** One RV32I binary runs unchanged at 1, 2, 4, 8, 16 or 32 bits per cycle: "fusing slices" changes the speed, never the result.

**Current line (2026-11-16): a pool of 1-bit RV32I cores with one shared code store, a shared data RAM, a code library, regions and (v12) a status read-out, on a Tang Nano 20K, with a command line and a browser window to drive it.** The runtime-width array described further down (`sc_sys.v` ... `sc_sys_v4.v`) is the simulation history; the hardware path is `sc_sys_v5`..`v12` with `uc_core_v2s` / `uc_core_v2t` (fixed 1-bit cores, `W=1`). Live numbers are always in [`latest.md`](latest.md).

| version | file | what it adds | board |
|---|---|---|---|
| v5 | `sc_sys_v5.v` | pool of fixed 1-bit cores (`uc_core_v2s`), v4 scheduler | block-RAM memories failed on silicon (see v6) |
| v6 | `sc_sys_v6.v` | register file and data memory in 32-bit-wide block RAM (the only block-RAM shape that works on this board), falling-edge RAM inputs | 10/10 tasks ok |
| v7 | `sc_sys_v7.v` | HOLD input: tasks are queued, then released together (host commands `H` / `G`) | 10/10 ok, all 8 slices used |
| v8 | `sc_sys_v8.v`, `uc_core_v2t.v` | ONE shared code store for all slices: turn-taking port, next-instruction fetch-ahead, core stalled via `ce` | 10/10 ok, about 1% slower, smaller |
| v9 | `sc_sys_v9.v`, `uc_core_v2u.v` | REGIONS: per program class a code region (base, length in words of the shared store) and a data limit; a fetch outside the region or a load/store beyond the limit ends the task as a trap and a wild store does not land (host command `B`) | simulation; build sizes in `latest.md`; not yet on the board |
| v10 | `sc_sys_v10.v`, `uc_core_v2v.v` | SHARED DATA RAM: one block RAM every slice can reach, in addition to each slice's private memory; per program class a window {base, length} into it (data word index 2^14 and up = byte address 0x10000); a load waits for its word (about 2 clocks at S=1, 8 at S=8, ~1.7% on a load-heavy loop), a store is posted; the host reads and writes it (`M` `L` `X` `Z`) | 15/15 tasks and 81/81 shared words on the board (6 slices) |
| v11 | `sc_sys_v11.v` | CODE LIBRARY window: one window of the shared code store that every class may execute (host `Y`); library code runs under the caller's limits. With `sclink.py` (library + classes + stack placement) | 13/13 tasks on the board (6 slices) |
| v12 | `sc_sys_v12.v`, `fpga/host_bridge_v6.v` | READ-OUT only (no change to scheduling or checks): status `T` (queues, what each core runs), per-core usage `U` (clocks allocated per slice, so load per core), trap cause and address `E` (code region / private limit / shared window / no window) | simulation; places on the Tang at S=6 (14,923 LUT4, 48.9 MHz); not yet on the board |

How a v8 slice gets its instructions: a free-running slot counter lets slice 0, 1, ... S-1 load its 32-bit fetch register from the shared store in turn (one clock per slot, no arbitration). While a core runs, its slice fetches the next sequential word, so straight-line code never waits; a taken branch waits at most S-1 clocks. The shared store is read-only to the cores (they cannot load from or store to code), and from v9 on, a task cannot run outside the code region the host gave its program class, nor touch data beyond its data limit (details in `latest.md`); classes with no region get the whole store and all physical data words.

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
| `sc_sys_v5.v` .. `sc_sys_v8.v`, `uc_core_v2s.v`, `uc_core_v2t.v` | the pool designs described above (clone-and-increment: each version is a new file, older ones are kept as proven) |
| `tb_sys5.v` .. `tb_sys8.v`, `sched_tests_v3.py` | system testbenches and the scheduler gate (`v5`..`v8` flags in `build`/`run3`) |
| `sc_sys_v10.v`, `sc_sys_v11.v`, `uc_core_v2v.v`, `tb_sys10.v` | shared data RAM (v10) and code library window (v11); `tb_sys10.v` is the stress testbench (host reads the RAM nonstop while slices run) |
| `shared_cases.py`, `test_shared_sim.py`, `test_shared_stress.py`, `run_shared_board.py` | the v10 tests: eight-plus tasks on windows of the shared RAM, producer/consumer, window guards, clamping; the stress test; the board script |
| `sc_sys_v12.v`, `fpga/host_bridge_v6.v`, `fpga/sc_top_pool12.v`, `status_cases.py`, `test_status_sim.py`, `run_status_board.py` | v12: status (T), per-core usage (U) and trap cause + address (E) read-out; `--pool 8`, version 9 |
| `scwin.py`, `test_scwin_sim.py` | the browser window: commands, data into the shared RAM, Run, live core view, jobs and result words back; tested by driving it against the simulated board |
| `fpga/sdram_ctl.v`, `fpga/sdt_selftest.v`, `fpga/sdt_bridge.v`, `fpga/sc_top_sdt.v`, `fpga/sdram_model.v`, `fpga/build_sdt.sh`, `sdt_host.py`, `run_sdram_test.py`, `test_sdram_sim.py` | stage 1 of the far RAM: the onboard 8 MB SDRAM controller and a memory test (separate build; 8 MB test passes on the card) |
| `fpga/far_copy.v`, `fpga/host_bridge_v7.v`, `fpga/sc_top_pool13.v`, `fpga/tb_top_far.v`, `test_farram_sim.py`, `run_farram_board.py` | stage 2 of the far RAM: copy engine between the cores' RAM / code store and the SDRAM, with a protected window; `--pool 9`; simulation only so far |
| `jobio.py`, `jobio/` (lib_io.s, vsum.s, vscale.s, vstress.s), `test_jobio_sim.py`, `run_jobio_board.py`, `test_runner_standin.py` | stage 3 step 1: the job input / result convention (8-word header in each job's window), gathering results into one block of far RAM, and a shared-RAM stress job; simulation only so far |
| `sccli.py`, `cli_demo/`, `test_cli_sim.py` | the command line scheduler: load a system file of named programs, send it, `run NAME COUNT`, `hold`/`go`, `wait`, `jobs`, shared RAM `peek`/`poke`, `counters`; tested against the simulated board |
| `violation_cases.py`, `test_violations_sim.py`, `run_violations_board.py` | the violation test: six kinds of violation (and good programs, mixed and all at once) on every slice, with guard words in the shared RAM; simulation passes S=1..8 and fails when any protection is switched off |
| `sclink.py`, `link_cases.py`, `test_link_sim.py`, `run_link_board.py` | the small linker (library + classes + stack placement + windows, produces the host commands) and the v11 tests: recursive fib on private and shared stacks, library calls from nine classes, stack overrun / jump into another class / library past its caller's window all trap |
| `host_sc.py`, `run_board.py`, `run_regions_board.py` | PC side for the real board: protocol codec (`V W P Q C R H G B M L X Y Z`), the board test script (`--regions` gives every program an exact region), and the regions test (traps, wild store, recovery) |
| `region_cases.py`, `test_regions_sim.py` | the twelve region test programs and their whole-board simulation test (`python3 test_regions_sim.py`; `NOREGION=1` is the negative control) |
| `fpga/` | Tang Nano 20K build: top levels `sc_top_pool*.v`, UART host bridge, `build_tang.sh`, block-RAM probe designs; see `fpga/README.md` |

## The array and the dispatcher

`sc_sys.v` holds 32 slices. A task asks for a width (1, 2, 4, 8, 16 or 32 slices); a **dedicated dispatcher** (a small hardware state machine, so no compute core ever runs scheduling code) finds an aligned free group, starts a core of that width, and frees the slices when the task ends. Tasks wait in a submission queue; finished tasks are reported in a completion queue that the host polls. No interrupts, no preemption: a task runs to completion.

## Quick start: drive the board (v11 or v12 design)

Build and load a design (v12 shown; `--pool 7` is v11, which has no live core view):
```
cd s-core/fpga && source ~/gowin-env/bin/activate
./build_tang.sh --out pool12_6 --pool 8 --slices 6 --code 128 --data 16 --queue 16
# unplug and replug the Tang (about 5 s), then:
openFPGALoader -b tangnano20k pool12_6/sc_top_pool12.fs
# unplug and replug again if the next command says it cannot find the board or /dev/ttyUSB1
```
Then, from `s-core/`:

| you want | run |
|---|---|
| **the window** (load commands and data, run, see the cores live, read results back) | `python3 scwin.py /dev/ttyUSB1` and open http://localhost:8765 |
| the command line | `python3 sccli.py /dev/ttyUSB1` (`help` lists the commands; `-f cli_demo/demo.sccli -q` runs the demo) |
| check the v12 read-out on the silicon | `python3 run_status_board.py /dev/ttyUSB1` |
| check every violation kind on every core | `python3 run_violations_board.py /dev/ttyUSB1` |
| earlier board checks | `run_shared_board.py`, `run_link_board.py` (see the file list) |

**The window** (`scwin.py`) runs a small page on your own PC. Box 1 holds the scheduler commands (`load`, `send`, `run NAME COUNT`, `hold`, `go`, `wait` ...), box 2 holds data for the shared RAM (`address value value ...`, written straight after `send`), box 3 says which RAM words to read back. Press **Run**: the data goes into the RAM, the commands are carried out, the result words are read back, and the job table shows each job's answer, core and clocks, or why it was stopped. While it runs the **Cores** panel shows every core (idle or running, which program and job, its load), and the queues. The programs themselves come from a system file (`cli_demo/demo.scs` is an example; format at the top of `sccli.py`). Data reaches the cores through the shared RAM, so a program reads its inputs from its window and leaves its results there.

## Build and run on the Tang Nano 20K (current design, v8)
```
cd s-core/fpga
source ~/gowin-env/bin/activate            # open flow: yosys, nextpnr-himbaechel, gowin_pack, openFPGALoader
./build_tang.sh --out pool8_8 --slices 8 --code 64 --data 16 --queue 16     # named options, any order; --help lists them
# (old positional form still works:  POOL=4 ./build_tang.sh pool8_8 8 64 16 16)
# unplug and replug the Tang (about 5 s), then load:
openFPGALoader -b tangnano20k pool8_8/sc_top_pool8.fs
cd .. && python3 run_board.py /dev/ttyUSB1 --lw 0        # run twice: the second run uses the learned duration profile
```
Build settings (`--slices`, `--code`, `--data`, `--queue`, `--fine`, `--pool`, `--seed`) are fixed when the bitstream is built and are saved in `build_info.txt` next to it; the board reports slices, code words and data words to the host (`V` command), and `run_board.py` adapts. `run_board.py --base N` loads the test programs at code address N (use a high value to test the upper part of a big code store). Power-cycle the board before loading a different design: it sometimes keeps running the previous one.

## Run it (simulation)

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

Word loads and stores only (no `lb`/`lh`/`sb`/`sh`), aligned only; `ebreak`/`ecall` halt; anything else illegal traps. No multiply, no CSRs, no interrupts. Loads and stores reach only each core's own small private data memory, not the code store. No protection between tasks yet. Area figures for v1/v2 exclude the register file and memories. Block RAM: only the 32-bit-wide single-port shape works on this board (see `latest.md`, v6).

## Priority dispatcher v3
`sc_sys_v3.v` adds the request table, task table (start/end/slot), priority queues and best-fit placement; see `latest.md` and `matrix_v3.txt`. Run with `python3 sched_tests_v3.py` (needs Verilator).

`LONGEST=1` adds the duration-profile store and longest-first bulk buckets (see `latest.md`, `matrix_v3_longest.txt`).

## FPGA build (v4)
`sc_sys_v4.v` plus `fpga/` is the single-set Tang Nano 20K build (UART host path, pins, build script). See `fpga/README.md` and `latest.md`.
