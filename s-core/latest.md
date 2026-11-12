# S-Core: current state (as of 2026-11-12). Width-selectable digit-serial RV32I core: v1, v2, a runtime-width core and a 32-slice array with a dispatcher working in simulation; not yet on a board. Newest first.

## v4: FPGA build for the Tang Nano 20K (S=1 confirmed on the board 2026-11-12; S=2 not yet run)

**Board result (Alan, 2026-11-12):** S=1 bitstream, `run_board.py /dev/ttyUSB1`: `RESULT PASS`, 12/12 tasks ok, launch_err 0; durations match the simulation (sort 74195 clocks). The first serial port (ttyUSB0) is the JTAG channel and returns 2 stray bytes: use ttyUSB1.

Files: `sc_sys_v4.v`, `uc_core_fp.v`, `tb_sys4.v`, `fpga/` (UART, host bridge, top, pins, build script, README), `host_sc.py`, `run_board.py`, `test_board_sim.py`, `v4_regress.txt`. Read `fpga/README.md` first.

**Built:** v3's scheduler with a clock-enabled core (one core step = 2 clocks, so every memory read is synchronous), bit-packed register file and data memory (1 Kbit register file per slice instead of 1024 x 32), a private instruction memory per slice loaded through one broadcast port, a UART byte protocol (link check, load code, submit, task-table read, counters, reset) and a Tang Nano 20K top level using the pins in `docs/man/tang-nano-20k.cst`.

**Measured:**
- Simulation: v4 passes the v3 gate in 12 policy/seed combinations; makespan = 2.00 x v3 (1.998 to 2.000), as expected for the 2-clock step. Whole-board test through the UART pins passes for S=1 (1 bit/cycle), S=2 (both widths, two tasks side by side) and S=8, at a fast and at the real 115200-baud divider. 16 data words per slice are enough for the test kernels, 8 are not.
- Place-and-route (native yosys 0.33 `synth_gowin -nowidelut` + nextpnr-himbaechel, GW2AR-LV18QN88C8/I7, seed 1, 27 MHz): **S=1** 11,755/20,736 LUT4 (57%), 344/648 LUT-RAM, **54.6 MHz** routed. **S=2** (64 code words) 17,575 LUT4 (85%), 505/648 LUT-RAM (78%), **57.0 MHz** routed. S=2 with 128 code words does not place. The committed `build_tang.sh` was run from a clean copy and reproduced the S=1 result.
- A timing bug was found and fixed on the way: the watcher's 256-line priority encoder synthesised as a ~20-LUT chain (13 MHz). Rewritten as a tree (same choice, identical makespan 105372 and all events logged): 54-57 MHz.
- Cost split: the runtime-width core alone is about 2,800 LUT4; each extra slice about 4,100 LUT4 with its memories; scheduler plus host bridge about 3,300 LUT4.

**What it means:** `uc_core_rw` is a simulation model (32-bit masked buses). It cannot be replicated 8-32 times on the Tang; at most two slices fit. This build proves the scheduler, queues, profile and host path on a real chip, not the 32-slice array. The array needs the real fusable 1-bit slice, or narrow cores, in place of one masked 32-bit core per slice. The Kintex-7 480T has roughly 15x the logic, so the same model might reach a few tens of slices there; that is an extrapolation, not a measurement.

**Not verified:** the S=2 bitstream has not been run on the board; pins are from the MAN file (chip-database checked, not schematic) but worked in the S=1 run. The YoWASP yosys 0.69 crashes (stack exhausted) on this design in the abc9 step; the native yosys is used.


## v3b: duration-profile store, longest-first bulk queue (simulation)

Files: `sc_sys_v3.v` (parameter `LONGEST`, `PROF`), `tb_sys3.v`, `sched_tests_v3.py`, `matrix_v3_longest.txt`.

**Built:** a dedicated profile RAM (512 x 25 bits: 64 program classes x 8 widths). The submitter gives a program-class id (`h_prog`); at completion the dispatcher writes the measured duration (end minus start from the task table) into the profile, averaging with the old value. At submit, the predicted duration picks one of 8 bulk buckets (about log2 of cycles; unknown goes to the top bucket so it is run and learned first). The dispatcher takes the highest non-empty bucket: no queue scan and no sorting. Critical tasks stay FIFO. LONGEST=0 is the old behaviour.

**Measured (12 cases: batch/staggered x uniform/mixed widths x 3 seeds; profile learned on a different workload):**
- Makespan vs FIFO bulk: better in 11 of 12 cases, worse in 1 (batch, mixed widths, seed 7: +12.7%). Mean change -6.0% for batch and -4.9% for staggered; best single case -19.3%. Per-row numbers in `matrix_v3_longest.txt`.
- Critical latency: unchanged within noise (critical class is untouched).
- Cold start (empty profile): identical to FIFO in a batch, since every task is submitted before any has finished; staggered arrivals learn online and gain a little.
- Prediction error is large (15% to 75% mean) because task size varies 2-5x inside one program class. A size hint from the submitter would be the next step.

**An earlier version keyed the profile on the code address; that was wrong (each task has its own address, so it only worked as a per-task memory and collided). Replaced by the class id.**

**Caveats:** 3 seeds; bucket resolution is a factor of 2; the prof RAM is cleared at reset only in simulation; not synthesised.


## v3: request table, task table, priority dispatcher (simulation, Verilator)

Files: `sc_sys_v3.v`, `tb_sys3.v`, `sched_tests_v3.py`, `matrix_v3.txt`.

**Built:** a 16x16 request table (set-only producers, clear-only watcher, set wins a same-cycle clear). Lines 0-63 mean "core with leader slice n finished"; lines 64-255 are peripheral lines whose payload is written first and logged once. A task table stores arrival, start, end, a0, trap, state and the slice the task ran on. There are two queues (critical, bulk), a wake-on-event dispatcher (no idle polling), best-fit placement, a GUARD/MAXPASS starvation guard, and waste counters.

**Measured:**
- Gate: all tasks complete, none trap, every a0 matches the ISS, `launch_err` = 0. Events logged exactly once with the right payload, served within 8 cycles (4 configs x 4 seeds, 40 events each).
- Regression: with PRIO=0, BESTFIT=0 it matches the v2 strict FIFO within 0.04%.
- Priority: critical-task latency falls by about 2x to 2.4x (batch) and 1.1x to 1.6x (staggered), at the cost of makespan, +4% to +9% in batch runs (full table in `matrix_v3.txt`).
- Best-fit: no effect when widths are uniform (aligned groups cannot fragment). With mixed widths 1..16 it changed 10-11 of 48 placements on 2 of 3 seeds, and cut makespan by up to 2.1% (batch) and 10.8% (staggered, seed 3). On one batch seed (7, PRIO=0) it was worse: worst wait 34023 -> 42137. So it is not a guaranteed win.
- Earlier worry (identical results with BESTFIT 0/1) was checked: uniform widths give identical placements; mixed widths do not. The code path is live.

**Not measured / caveats:** 3 seeds only, so the best-fit gain is indicative. Waste breakdown counters exist but are not tabulated here. Not synthesised for area. The 16x16 table is not yet attached to real I/O cores.


## Read this first (most recent)

**Dispatcher policies (12 Nov) -- overtaking and a reserved region give small gains; priority-aware dispatch is the missing lever.**
- `sc_sys_v2.v` (old `sc_sys.v` untouched): look-ahead overtaking (`LA`, with a `MAXPASS` anti-starvation limit), a reserved region for critical tasks (`RESERVE`), a critical flag per task. With `LA=1`, `RESERVE=0` it reproduces the earlier makespans exactly.
- Mean of 5 workloads of 48 tasks, every run through the correctness gate. Critical 8 / bulk 4 wide, strict FIFO versus reserve 8 + overtake 16: critical latency 22809 -> 21264 (batch, -7%) and 14978 -> 12593 (staggered, -16%), makespan unchanged.
- Reserving 16 of 32 slices hurt badly (makespan +25-30%, utilisation 63-66%). Reserve without overtaking also hurt slightly.
- Biggest effect was rescuing a bad width choice (critical 32 wide / bulk 1): 382901 -> 208775 cycles, still 21% utilisation. The anti-starvation limit kept worst-case waits within a few percent of strict FIFO.
- Submitting critical tasks first (host side, last entry) beat every dispatcher setting here for critical latency (about 6500 versus 12000-23000, different workload set, batch only). Next candidate: priority-aware dispatch (two queues, critical served first), which also covers staggered arrivals.
- Not the 16x16 request table: the queue here is for task submission by the host. The event table with its watcher core (hardware events, I/O cores) is still design-only.

**Array + dispatcher (12 Nov) -- width chosen per task works; critical tasks get ~3.7x lower latency at about the same total time.**
- `uc_core_rw.v`: width chosen at task start. 276/276 regression runs match the reference; cycles equal v2 (+1 start cycle).
- `sc_sys.v`: 32 slices, a core instance per slice, private regfile and data memory per instance, shared code image, submission and completion queues, and a dedicated dispatcher FSM (one-cycle aligned-group search, launches 3 cycles apart, strict FIFO). No interrupts; the host polls the completion queue.
- Correctness gate: every task completed, none trapped, every a0 equal to the reference simulator's. Passed in every run (random widths and arrival times, and all policy runs).
- Mean of 5 workloads of 48 tasks (makespan / critical latency / bulk latency, cycles): fixed W=32 66441 / 38259 / 33783; fixed W=8 43844 / 24078 / 21757; fixed W=4 longest-first 37306 / 29868 / 28039; critical W=8 + bulk W=4, critical first 44378 / 6496 / 26001.
- Reading: fixed wide is the worst for throughput; width-per-task buys low latency for the critical class at ~1% makespan and ~19% worse bulk latency; best raw makespan came from a fixed narrow width with long tasks first. One workload family, one dispatcher policy.
- Strict FIFO is fragile: a wide task among narrow ones can leave the pool mostly idle (9% utilisation seen). Backfill or reserved regions are the obvious next policies.
- Note: at W=32 a core costs 128 slice-cycles per instruction versus 66 at W=1 (fixed fetch/setup passes), so per-slice throughput is better narrow.
- Verilator is needed for the array runs (about 100x faster than iverilog here: 0.4 s versus 88 s for the same workload).
- Not built: loader/readout over JTAG or UART, real memory banking, any area figure for the array.

**v2 (12 Nov) -- pc, immediate and address register held as digit shift registers: 9-45% fewer LUTs, identical behaviour.**
- Measured first: knocking out blocks of v1 at W=1 showed the indexed 32-bit register access cost ~270 of 469 LUT4 (pc write ~91, address write ~75, imm read ~46, pc read ~34, imm decode ~27).
- `uc_core_v2.v`: pc rotates/inserts one digit per cycle, address register is insert-only, immediate is loaded at setup and rotated. v1 left untouched.
- 276/276 runs match the reference; cycle counts identical to v1.
- iCE40 LUT4 v1 -> v2: W=1 469->326, W=4 478->383, W=8 547->484, W=16 740->677, W=32 1258->1108. Xilinx LUT6: W=1 342->239, W=8 608->405, W=32 1616->890. Flops rise by 32 (the immediate ring).
- The W=1 floor is still ~326 LUT4, well above SERV; the rest is decode, immediate formation, control and the shift/compare logic (not yet broken down).
- Gowin (Tang Nano) counts from yosys 0.33 are unreliable and not recorded; measure with the Gowin tool.
- Harness bug found and fixed: the testbench filename buffer was 32 characters and silently truncated longer output names.
- Targets stated by Alan: Tang Nano 20K (Sipeed) and Kintex-7 XC7K480T with no PCIe side, so JTAG only. A loader/readout path is needed for each (Xilinx JTAG user register; Tang Nano UART).

**First prototype (12 Nov) -- one RV32I binary runs correctly at W = 1, 2, 4, 8, 16, 32 bits per cycle.**
- Correctness: 276 runs (6 directed programs and 40 random programs, each at all 6 widths) match an independent reference simulator on final registers, data memory, pc and instruction count. A planted bug in the signed-compare logic was caught by the suite (5 failures), so it can fail.
- Cycles per instruction (random programs, average): W=1 69.8, W=2 36.0, W=4 19.1, W=8 10.6, W=16 6.4, W=32 4.3. Model: ALU and branch 2N+2, load/store 3N+2, N = 32/W.
- Area (yosys, iCE40 4-LUT, core logic only): W=1 469 LUT4, W=2 476, W=4 478, W=8 547, W=16 740, W=32 1258; flops about 118-122 at every width.

**What the numbers say (measured, not guessed):**
- Width buys a lot of speed (about 16x from 1 to 32 bits) for little area (about 2.7x). Best LUTs x CPI is at W=8 to 16.
- The narrow end is not small: about 470 LUTs even at W=1 (SERV is about 125 on 7-series, taken from its project page, not measured here).
- Marginal cost of widening is roughly 24-32 LUTs per added bit between W=8 and W=32, so a 512-slice array extrapolates to more than the 10k LUTs first assumed. That is an extrapolation, not a measurement.

**Hypothesis, not yet tested:** the floor comes from `pc`, `ir` and the address register being 32-bit registers read and written through variable-index muxes. Turning them into digit shift registers should cut it.

**Simplifications in this prototype:** instruction fetch is a whole word in one cycle; word loads/stores only, aligned; no fetch/execute overlap; register file and memories not counted in area.

## Decisions so far
- One ISA (RV32I) at every width; width is a datapath property, not an ISA property.
- Width is allocated at task start, not changed mid-task (re-slicing live state is disruptive).
- No interrupts. Task queue and dispatcher are built (simulation); the 16x16 event table and I/O cores are designed on paper only.
- Scheduling is done by a dedicated hardware dispatcher, not by a compute core, so no task ever runs scheduling code.

## Next (options, not started)
1. Overlap the pc update with execute (needs a small second adder or serial incrementer); break down the remaining ~326-LUT floor.
2. (done in simulation, see top entry) Task descriptor and width allocator. Backfill and reserved regions tried (top entry); next: priority-aware dispatch, software scheduler variant.
3. Event table (16x16) plus dedicated I/O cores, with the set/clear race handled (clear before reading the payload, or a per-source FIFO).
