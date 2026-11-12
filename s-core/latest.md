# S-Core: current state (as of 2026-11-12). Width-selectable digit-serial RV32I core, first prototype working in simulation; not yet put on a board. Newest first.

## Read this first (most recent)

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
- No interrupts. Events, I/O cores and the task queue are designed on paper only.

## Next (options, not started)
1. Convert `pc`, `ir`, `addr` to digit shift registers; overlap the pc update with execute; re-measure.
2. Task descriptor and width allocator (carve a core at task start, release at end).
3. Event table (16x16) plus dedicated I/O cores, with the set/clear race handled (clear before reading the payload, or a per-source FIFO).
