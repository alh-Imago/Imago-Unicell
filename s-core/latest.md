# S-Core: current state (as of 2026-11-12). Width-selectable digit-serial RV32I core: v1, v2, a runtime-width core and a 32-slice array with a dispatcher working in simulation; not yet on a board. Newest first.

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
