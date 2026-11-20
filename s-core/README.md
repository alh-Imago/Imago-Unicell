# S-Core

A prototype of a **modular, interrupt-free RISC core whose datapath width is a dial.** One RV32I binary runs unchanged at 1, 2, 4, 8, 16 or 32 bits per cycle: "fusing slices" changes the speed, never the result.

**Current line (2026-11-16): a pool of 1-bit RV32I cores with one shared code store, a shared data RAM, a code library, regions and (v12) a status read-out, on a Tang Nano 20K, with a command line and a browser window to drive it.** The runtime-width array described further down (`sc_sys.v` ... `sc_sys_v4.v`) is the simulation history; the hardware path is `sc_sys_v5`..`v12` with `uc_core_v2s` / `uc_core_v2t` (fixed 1-bit cores, `W=1`). Live numbers are always in [`latest.md`](latest.md).

**Second target (2026-11): a Kintex-7 XC7K480T card (YPCB-00338-1P1), built with the open openXC7 flow, reached over JTAG (no PCIe).** The same pool runs there with up to 16 slices, the far RAM is the card's DDR3 (UberDDR3, GPL-3.0, channel 0) or block RAM, and the telemetry job set runs 24 of 24 correct on the card (S=4 and S=16 builds; DDR3 build proven). Build files, link and measurements are in `k7/` (see `k7/README.md`, `k7/ddr3_gpl3/README.md`) and `latest.md`. Dispatcher versions `sc_sys_v13` / `v14` (shorter paths for a higher clock at S=16) belong to this line.

| version | file | what it adds | board |
|---|---|---|---|
| v5 | `sc_sys_v5.v` | pool of fixed 1-bit cores (`uc_core_v2s`), v4 scheduler | block-RAM memories failed on silicon (see v6) |
| v6 | `sc_sys_v6.v` | register file and data memory in 32-bit-wide block RAM (the only block-RAM shape that works on this board), falling-edge RAM inputs | 10/10 tasks ok |
| v7 | `sc_sys_v7.v` | HOLD input: tasks are queued, then released together (host commands `H` / `G`) | 10/10 ok, all 8 slices used |
| v8 | `sc_sys_v8.v`, `uc_core_v2t.v` | ONE shared code store for all slices: turn-taking port, next-instruction fetch-ahead, core stalled via `ce` | 10/10 ok, about 1% slower, smaller |
| v9 | `sc_sys_v9.v`, `uc_core_v2u.v` | REGIONS: per program class a code region (base, length in words of the shared store) and a data limit; a fetch outside the region or a load/store beyond the limit ends the task as a trap and a wild store does not land (host command `B`) | on the board (see `latest.md` for the runs) |
| v10 | `sc_sys_v10.v`, `uc_core_v2v.v` | SHARED DATA RAM: one block RAM every slice can reach, in addition to each slice's private memory; per program class a window {base, length} into it (data word index 2^14 and up = byte address 0x10000); a load waits for its word (about 2 clocks at S=1, 8 at S=8, ~1.7% on a load-heavy loop), a store is posted; the host reads and writes it (`M` `L` `X` `Z`) | 15/15 tasks and 81/81 shared words on the board (6 slices) |
| v11 | `sc_sys_v11.v` | CODE LIBRARY window: one window of the shared code store that every class may execute (host `Y`); library code runs under the caller's limits. With `sclink.py` (library + classes + stack placement) | 13/13 tasks on the board (6 slices) |
| v12 | `sc_sys_v12.v`, `fpga/host_bridge_v6.v` | READ-OUT only (no change to scheduling or checks): status `T` (queues, what each core runs), per-core usage `U` (clocks allocated per slice, so load per core), trap cause and address `E` (code region / private limit / shared window / no window) | on the board; places on the Tang at S=6 (14,923 LUT4, 48.9 MHz) |

How a v8 slice gets its instructions: a free-running slot counter lets slice 0, 1, ... S-1 load its 32-bit fetch register from the shared store in turn (one clock per slot, no arbitration). While a core runs, its slice fetches the next sequential word, so straight-line code never waits; a taken branch waits at most S-1 clocks. The shared store is read-only to the cores (they cannot load from or store to code), and from v9 on, a task cannot run outside the code region the host gave its program class, nor touch data beyond its data limit (details in `latest.md`); classes with no region get the whole store and all physical data words.

This is separate from the UniCell cell grid. The aim is to see whether a sea of identical narrow slices can be fused into wider cores (or split into many narrow ones) while still running ordinary compiled software. Branch: `S-Core_go`. Status and numbers are in [`latest.md`](latest.md).

## The idea

- **One ISA at every width.** The datapath width W and the instruction width (32) are separate things. A 1-bit core takes 32 cycles on a 32-bit add; a 32-bit core takes 1. The compiler sees RV32I either way.
- **Everything is streamed one W-bit digit per cycle**, least significant first (shift-left runs most significant first so it can work in place). The register file and data memory are W-wide RAMs addressed `{register, digit}`. There is one W-bit adder with a carry flop; the pc goes through it too.
- **No interrupts.** The core only runs its own instruction stream. (The task queue and dispatcher are built. The event table and dedicated I/O cores are still design ideas, not built.)
- **Width is chosen at task start, not mid-task.** Changing width mid-task would mean re-slicing register state spread across slices, so the plan is to allocate a width per task from a descriptor.

## Runtime fusion in the pool (v16, v17; 2026-11-19, ledger #1378 to #1386)

A task submitted with width `lw > 0` (job file field `"lw"`, `scblocks.py --lw N`) gets an aligned group of 2**lw free slices; the leader (lowest slice) is run by a **fusion unit** (`uc_unitw4/8/16.v`: a controller plus lanes with whole-word RAM access) that takes over the leader's RAMs, fetch register and region checks for the length of the task. Other slices in the block carry on with their own jobs. With no free unit (or `FZ = 0`) the task runs at 1 bit exactly as before.

| version | file | what it adds |
|---|---|---|
| v16 | `sc_sys_v16.v` (generated by `make_sys_v16.py`) | ONE fusion unit per block (`FZ`, `ULW` = log2 of its lanes); only even slices can lead; the shared data window works for fused tasks |
| v17 | `sc_sys_v17.v` (generated by `make_sys_v17.py`) | `NU` units per block, the lowest free unit is bound to each fused task |

Measured on the Kintex card, 24-job telemetry set, clocks vs width 0: 2x4 slices with a 4-lane unit 1.85x (lw 1), 3.3x (lw 2); 2x8 slices with an 8-lane unit 1.84x, 3.09x, 5.78x (lw 3); the unit costs about 1,350 LUT (4 lanes) and 2,100 LUT (8 lanes) per block; routed 94.04 MHz (2x4) and 85.48 MHz (2x8). Mixing narrow and wide jobs did not beat widening every job on these sets. Two units per block: all-lw-2 3.57x instead of 3.09x on the 2x8. **Automatic width** is an optional mode: `"lw": "auto"` in the job file or `scblocks.py --lw auto --unit-lw N` (every job gets the widest width the unit and the block allow; explicit widths are never changed; `--auto-min-cost` keeps cheap jobs narrow). Details and the open points: [`latest.md`](latest.md), `FUSION_PLAN.md`, ledger #1378 to #1386.

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
| `fpga/far_copy.v`, `fpga/host_bridge_v7.v`, `fpga/sc_top_pool13.v`, `fpga/tb_top_far.v`, `test_farram_sim.py`, `run_farram_board.py` | stage 2 of the far RAM: copy engine between the cores' RAM / code store and the SDRAM, with a protected window; `--pool 9`; proven on the card |
| `jobio.py`, `jobio/` (lib_io.s, vsum.s, vscale.s, vstress.s), `test_jobio_sim.py`, `run_jobio_board.py`, `test_runner_standin.py` | stage 3 step 1: the job input / result convention (8-word header in each job's window), gathering results into one block of far RAM, and a shared-RAM stress job; proven on the card |
| `batch.py`, `batch_demo.py`, `test_batch_sim.py`, `run_batch_board.py` | stage 3 step 2: batch script (4-word steps in far RAM: load code/data, submit, wait, save, jump, end), its host-side executors and a two-phase demo chain that replaces the code store; proven on the card (one run) |
| `fpga/batch_seq.v`, `fpga/host_bridge_v8.v`, `fpga/sc_top_pool14.v`, `fpga/tb_top_seq.v`, `test_seq_sim.py`, `run_seq_board.py` | stage 3 step 3: the batch sequencer as hardware (state machine reading the step format from far RAM; host commands J start, A status; board version 11; build `--pool 10`, 4 slices); proven on the card at 4 slices (one run) |
| `jobcomp.py`, `scbatch.py`, `test_jobcomp_sim.py` | the job compiler (any number of jobs packed into chained batches, results in task order, status of every job saved) and its front end (job file in, verified results out) |
| `fpga/batch_seq_v2.v`, `fpga/host_bridge_v9.v`, `fpga/sc_top_pool15.v`, `fpga/tb_top_seq2.v` | the sequencer with clock counters and live progress (board version 12, build `--pool 11`, 4 slices); counters and own programs proven on the card at 4 slices (one run each) |
| `score_shell_v1.py`, `SHELL.md`, `test_score_shell_v1.py` | an interactive shell for the job files: type jobs in, save/open, plan, run on the card, compare; Tab completion and live colours; `SHELL.md` lists the commands (ledger #1420) |
| `jobmaker_v2.py`, `test_jobmaker_v2.py` | `make` with more steps: min max (clamp), gt lt eq ne (1 or 0), rol ror sra, mul (a number by shifts and adds, or `arg` by a loop), diff, prefix, and `pair OP` (two arrays); v1 kept, byte-identical code for v1 recipes (ledger #1428) |
| `bigjobs_v1.py`, `test_bigjobs_v1.py` | `addbig KIND DATA`: data longer than one job holds is cut into pieces, run as ordinary jobs and the answers combined and checked against the whole (ledger #1428) |
| `scwin_v2.py`, `test_scwin_v2.py` | the browser window for the Kintex card: the shell as a prompt in the page (live colours and Tab built in, no extra package), panels for the live cores (slices, fused groups, queues, sequencer), the jobs with answers and MATCH, the batch plan and the last run; `python3 scwin_v2.py` (with the openocd wrapper for the card); `scwin.py` (Tang, serial) is unchanged; `scblocks.run` got an optional `monitor` hook (ledger #1425) |
| `bigrun_v1.py`, `test_bigrun_v1.py`, `window_run_medium_v1.score`, `window_run_big_v1.score` | a long test run for the window, so the live cores panel has something to show (the 41-job demo ends in 12.6 ms, before the first poll, #1437): 100 or 500 jobs of one made kind (`wb_heavy7`: seven `mul arg` steps then a sum, about 700 instructions per data word), widths 0, 0, 1, 2, 0, five jobs to a batch. MEASURED on the card (20 Nov, #1440, #1443): medium 100 of 100 correct, 42,813,283 clocks (0.856 s); big 500 of 500 correct, 214,066,400 clocks (4.28 s, five times the medium to within 15 clocks), the same on a second run; the host's estimate was 4.0 % low for both (it has not been fitted to `mul arg`). Run: `nix shell nixpkgs#openocd --command python3 scwin_v2.py -f window_run_big_v1.score`. `python3 bigrun_v1.py --batches N -o FILE` makes another size (far RAM holds about 110 batches). |
| `WRITEUP_v1.md`, `made_demo2_v1.score` | the write-up before the larger build (what is measured, read from the RTL, reasoned; limits; checklist; commands) and the second card test of `make` (big constants, shifts by arg, all endings, widths 0 to 3; ledger #1424) |
| `jobmaker_v1.py`, `programs/made/`, `test_jobmaker_v1.py`, `made_demo_v1.score` | `make NAME STEP... [then ENDING]` in the shell builds a new job kind from a recipe (`make bump add 5 xor arg shl 1 then sum`): it writes the RV32I program and the Python answer, checks both on the interpreter (12 runs, random data and arg), and keeps the kind for later sessions; `code KIND` shows the program (ledger #1422) |
| `LADDER.md` | a ladder of commands from one job on the card to a program of your own, with `ladder_*.json` and `ladder_show.py` (ledger #1419) |
| `PROGRAMS.md` | a plain guide to writing your own program: the five parts, the rules of the core, `vmax` line by line, `vmin` and `vxor` made from it (ledger #1418) |
| `progs.py`, `jobiss.py`, `programs/`, `jobs_own_example.json`, `test_progs.py`, `test_ownprog_sim.py` | your own programs as job kinds: registry with checks, a reference interpreter that traps like the board, a template, two examples |
| `sccli.py`, `cli_demo/`, `test_cli_sim.py` | the command line scheduler: load a system file of named programs, send it, `run NAME COUNT`, `hold`/`go`, `wait`, `jobs`, shared RAM `peek`/`poke`, `counters`; tested against the simulated board |
| `violation_cases.py`, `test_violations_sim.py`, `run_violations_board.py` | the violation test: six kinds of violation (and good programs, mixed and all at once) on every slice, with guard words in the shared RAM; simulation passes S=1..8 and fails when any protection is switched off |
| `sclink.py`, `link_cases.py`, `test_link_sim.py`, `run_link_board.py` | the small linker (library + classes + stack placement + windows, produces the host commands) and the v11 tests: recursive fib on private and shared stacks, library calls from nine classes, stack overrun / jump into another class / library past its caller's window all trap |
| `host_sc.py`, `run_board.py`, `run_regions_board.py` | PC side for the real board: protocol codec (`V W P Q C R H G B M L X Y Z`), the board test script (`--regions` gives every program an exact region), and the regions test (traps, wild store, recovery) |
| `region_cases.py`, `test_regions_sim.py` | the twelve region test programs and their whole-board simulation test (`python3 test_regions_sim.py`; `NOREGION=1` is the negative control) |
| `k7/`, `fpga/jtag_link_v2.v`, `fpga/sc_top_k7_v*.v`, `jtagport.py`, `ddr3test.py` | Kintex-7 card: JTAG host link, builds (`make_sizes_v*.py` for S=4/8/16, `stage*.sh`), DDR3 far RAM in `k7/ddr3_gpl3/`, size and RAM-scaling results; `sc_sys_v13.v` / `sc_sys_v14.v` (+ `fit_search_tree.v`, `test_fit_equiv.py`) are the shorter-path dispatchers |
| `fpga/sc_block.v`, `fpga/far_arb.v`, `fpga/host_bridge_v11.v`, `fpga/sc_top_k7_v8.v` (generated by `fpga/make_top_multiblock_v1.py`), `fpga/tb_k7mb.v`, `test_mb_harness.py`, `test_mb_sim.py`, `k7/make_mb_v1.py`, `k7/stage_mb.sh` | MULTI-BLOCK Kintex top (simulation only so far): NB blocks, each a dispatcher + slices + shared RAM + code store + copy engine + batch sequencer in one box (`sc_block`), one host bridge whose new `O` command selects the block, one arbiter for the single far RAM. See ledger #1347 |
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
Tang Nano 20K (Sipeed) and a Kintex-7 XC7K480T card. The Kintex card has no PCIe side, so JTAG is the only way in: programs and results would go through the Xilinx JTAG user register. On the Tang Nano the onboard USB bridge (UART) is the natural route. On the Kintex, the JTAG host link and loader now exist and run on the card (`k7/`, `jtagport.py`); on the Tang the UART bridge is in use.

## Limits (be aware)

Word loads and stores only (no `lb`/`lh`/`sb`/`sh`), aligned only; `ebreak`/`ecall` halt; anything else illegal traps. No multiply, no CSRs, no interrupts. Loads and stores reach each core's private data memory and a window of the shared data RAM (v10), never the code store. From v9 a task is confined to its class's code region and data limits (a violation traps), but there are no per-task page tables or user/supervisor modes. Area figures for v1/v2 exclude the register file and memories. Block RAM: only the 32-bit-wide single-port shape works on this board (see `latest.md`, v6).

## Priority dispatcher v3
`sc_sys_v3.v` adds the request table, task table (start/end/slot), priority queues and best-fit placement; see `latest.md` and `matrix_v3.txt`. Run with `python3 sched_tests_v3.py` (needs Verilator).

`LONGEST=1` adds the duration-profile store and longest-first bulk buckets (see `latest.md`, `matrix_v3_longest.txt`).

## FPGA build (v4)
`sc_sys_v4.v` plus `fpga/` is the single-set Tang Nano 20K build (UART host path, pins, build script). See `fpga/README.md` and `latest.md`.

## Card setup: width calibration (`sc_calibrate_v1.py`, ledger #1397, #1398)
Measures how a given card build speeds up jobs at each width and stores the result as a profile in `profiles/`. Run it once after building or loading a bitstream (inside `nix shell nixpkgs#openocd`; the board does not report the unit width or unit count, so you give them):

    python3 sc_calibrate_v1.py run --name mycard --blocks 2 --unit-lw 3 --units 3        (add --quick for a shorter sweep)
    python3 sc_calibrate_v1.py show profiles/mycard.json                                  the numbers and the best width for 1..2xS jobs per batch
    python3 sc_calibrate_v1.py fit --from-text raw.txt --name x --slices 8 --blocks 2 --unit-lw 3 --units 3     fit a saved raw file, no card

For a batch of identical jobs on one block, the best width follows slices against jobs (8 slices: 1 job -> lw 3, 2 -> lw 2, 8 -> lw 0 on the measured 2x8 build), not the job length. `scblocks.py jtag jobs.json --lw auto --profile mycard` uses it: every batch gets the width the profile gives for that many jobs (optional; without `--profile`, `--lw auto` is the simple rule). `sh profile_compare_v1.sh NAME UNIT_LW UNITS WMAX` calibrates the loaded build and compares fixed widths, the simple rule and the profile (ledger #1401). The `run` mode has not yet been run on a card; the fit has (example: `profiles/example_2x8_nu3.json`). Test: `python3 test_calibrate_v1.py`.

### Width from the length of each job (`lengthest_v1.py`, ledger #1411; optional, an estimate)
`scblocks.py ... --lw auto --profile mycard --estimate` chooses a width for EACH job of a batch: the host counts the instructions of every job with the reference interpreter (no board), turns that into clocks (clocks per instruction fitted from the profile's single-job runs, divided by the profile's speed-up for the width), models the dispatcher and picks the widths with the shortest modelled batch (long jobs wide, short ones narrow). A mix of widths is kept only if it is modelled at least 10% faster than the best single width (`--estimate-margin`). Jobs that say a width themselves keep it. Other kinds than crc32 are assumed to run like crc32 until `sh cpi_run_v1.sh | tee cpi_run.txt` is run on the card and `python3 lengthest_v1.py fit-kinds --profile mycard --raw cpi_run.txt` stores their own clocks per instruction in the profile. How far the estimate was right on the card: ledger #1411. **Measure warm:** the pool keeps learned job durations across a reset (cleared only by a reload of the bitstream) and orders its queue by them, so the first run of a batch after a load is slower (all lw2 on `jobs_order_test2.json`: 48,26x clocks, then 35,49x); repeat a run and compare the later ones (ledger #1415, #1417). Test: `python3 test_lengthest_v1.py`.

How jobs, batches, scripts and widths are stored: `BATCH_FORMAT.md` (ledger #1404).
