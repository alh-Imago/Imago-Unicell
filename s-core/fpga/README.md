# S-Core on the Tang Nano 20K

This folder is the path from the simulated S-Core scheduler to real hardware. **Current design: v8 (pool of 1-bit cores, one shared code store), run on a real Tang Nano 20K on 2026-11-15.** The sections from "What is here" down describe the first single-set build (v4) and are kept as history; the section below is the current state. Live numbers: [`../latest.md`](../latest.md).

## Current designs (v6 - v8), at a glance
| `--pool` | top level | design | board result (8 slices, 64 code words, 16 data words) |
|---|---|---|---|
| 2 | `sc_top_pool6.v` | v6: block-RAM memories in the 32-bit-wide shape | 10/10 ok; only slots 0 and 1 used (tasks trickle in over the UART) |
| 3 | `sc_top_pool7.v` | v7: + HOLD (host `H` / `G`) | 10/10 ok, all 8 slots used; second run with the learned profile: batch 54,945 -> 48,602 clocks |
| 4 | `sc_top_pool8.v` | v8: + one shared code store | 10/10 ok, all 8 slots used; about 1% slower than v7; second run batch 55,592 -> 49,122 clocks |

Place-and-route (nextpnr, 8 slices): v7 13,706 LUT4 / 377 LUT-RAM blocks; v8 12,887 LUT4 / 153 LUT-RAM blocks, 54.3 MHz. v8 with 10 slices (14,921 LUT4) places and routes but has not been run on the board; 12 slices do not place (logic), 16 do not (block RAM: 3 blocks per slice). Code store size at 8 slices (all route and close timing; 64 and 256 words have run on the board, 512 has not): 64 words 12,887 LUT4 / 153 LUT-RAM blocks / 54.3 MHz; 256 words 13,928 / 249 / 53.9 MHz; 512 words 14,466 / 377 / 51.6 MHz. The 256-word build ran on the board with the programs at address 192: 10 of 10 ok on both runs (batch 55,594 then 49,129 clocks), same durations as the 64-word build. The cost is LUT-RAM (about 0.5 block per word) plus a wider read multiplexer, and it is paid once, not per slice.

| 5 | `sc_top_pool9.v` | v9: + regions (host `B`, version 6): code base/limit and data limit per program class | 8 slices: 10/10, identical timing; one slice: regions test 12/12 (traps, wild store blocked, recovery) |
| 6 | `sc_top_pool10.v` | v10: + a SHARED DATA RAM, one block RAM for all slices (`--shared N` words, power of 2, default 256), per-class windows (host `X`), host access (`M` write, `L` read, `Z` size); version 7 | board: `run_shared_board.py` 15/15 tasks, 81/81 words (6 slices) |
| 7 | `sc_top_pool11.v` | v11: + a code LIBRARY window every class may execute (host `Y`); version 8; use `../sclink.py` to build library + classes + stacks | board: `run_link_board.py` 13/13 tasks (6 slices) |
| 8 | `sc_top_pool12.v` | v12: + status `T`, per-core usage `U`, trap cause `E`; version 9; `--pool 8` | simulation: `test_status_sim.py`; board: `run_status_board.py` (not run yet) |
| 9 | `sc_top_sdt.v` | stage 1 of the onboard 8 MB SDRAM: controller + on-chip memory test + UART commands (`build_sdt.sh`); not the pool | simulation `test_sdram_sim.py` PASS; places at 27 MHz (2,391 LUT4); not yet on the card |

Build (named options; the old positional form still works) and run:
```
cd s-core/fpga && source ~/gowin-env/bin/activate
./build_tang.sh --out pool8_8 --slices 8 --code 64 --data 16 --queue 16        # ./build_tang.sh --help lists the options
# unplug and replug the board (about 5 s), then
openFPGALoader -b tangnano20k pool8_8/sc_top_pool8.fs
cd .. && python3 run_board.py /dev/ttyUSB1 --lw 0       # --nohold: do not use hold/go; --base N: load the programs at code address N
```
The shared data RAM (v10) and library (v11) tests, builds and scripts:
```
./build_tang.sh --pool 6 --slices 8 --code 128 --shared 256 --out pool10_8     # v10
openFPGALoader -b tangnano20k pool10_8/sc_top_pool10.fs
cd .. && python3 run_shared_board.py /dev/ttyUSB1                              # expects version 7; 15 tasks + 81 words checked
cd fpga && ./build_tang.sh --pool 7 --slices 8 --code 128 --shared 256 --out pool11_8     # v11
openFPGALoader -b tangnano20k pool11_8/sc_top_pool11.fs
cd .. && python3 run_link_board.py /dev/ttyUSB1                                # expects version 8; library + stacks, 13 tasks
```
`run_board.py --expect version=6,S=8,imem_words=64` (any subset of version, S, imem_words, dmem_words) stops early with a plain "WRONG DESIGN" message if the board is not running that design, which is how a load that did not take shows up; `--regions` and `run_regions_board.py` check the design version automatically. Run `run_board.py` twice without reloading: the second run has a duration prediction for every task, and the ordered batch is shorter. `run_board.py` flushes the serial port when it opens it (the board's factory demo prints text at power-up). If it prints `not an S-Core build`, rerun it once.

Rules learned on this board: power-cycle before loading a different design (it sometimes keeps running the previous one); only the 32-bit-wide single-port block RAM works (narrower shapes return wrong data on silicon even with no core); nextpnr does check hold time, so block-RAM inputs are re-registered on the falling clock edge; `gowin_pack -s` rewrites the `.cst`, so do not reuse that file for nextpnr.

## What is here
| File | What it is |
|---|---|
| `../sc_sys_v4.v` | The v3 scheduler (request table, task table, priority queues, best-fit, duration profile) with FPGA-friendly memories and a host port |
| `../uc_core_fp.v` | The proven `uc_core_rw` core with a clock-enable, so memories can have synchronous reads |
| `uart.v`, `host_bridge.v` | 8N1 UART and a small byte protocol (load code, submit task, read task table, read counters) |
| `sc_top_tang.v`, `sc_top_tang.cst` | Top level and pin file (pins from `docs/man/tang-nano-20k.cst`) |
| `build_tang.sh` | Synthesis, place-and-route, bitstream (same open flow as `tools/gowin_sizing/build_smoke_bitstream.sh`) |
| `tb_top_tang.v`, `../test_board_sim.py` | Whole-board simulation through the UART pins |
| `../host_sc.py`, `../run_board.py` | PC side: protocol codec, and a script that runs 12 tasks on the real board |

## Build and run at home
```
pip install yowasp-nextpnr-himbaechel-gowin apycula pyserial     # once; you also need a native yosys on the path
cd s-core/fpga
./build_tang.sh build 1 128 16 16          # outdir, S (slices), IMEM_WORDS, DMW, QD  -> build/sc_top_tang.fs
openFPGALoader -b tangnano20k build/sc_top_tang.fs                   # loads to SRAM (lost at power-off)
python3 ../run_board.py /dev/ttyUSB0       # Windows: COMx.  The BL616 offers two serial ports; use the SECOND one (/dev/ttyUSB1): the first is the JTAG channel and returns only two stray bytes.
# two-slice build:  ./build_tang.sh build2 2 64 16 16   then   python3 ../run_board.py <port> --lw 0
```
Use the native `yosys` (the repo's other builds do). The YoWASP yosys runs out of stack on this design.
Start with SRAM, as in the Tang getting-started note; do not write the flash first.

Expected output: a `board:` line (S=1, 128 and 16), then 12 task lines each ending `ok`, then `RESULT PASS`.
At S=1 every task runs at one bit per cycle, so the 12 tasks take a few tenths of a second.

## LEDs (active low, LED0 = pin 15)
LED0 heartbeat (about 1.6 Hz) · LED1 a core is running · LED2 UART receive · LED3 UART transmit ·
LED4 launch error (must stay off) · LED5 at least one task has finished.
If nothing blinks, the bitstream did not load. If LED0 blinks but `run_board.py` gets no answer, check the serial port
(it is the BL616 bridge, FPGA pins 69/70) and that no other program has it open.

## Protocol (all little-endian; one command at a time, wait for the reply before the next command)
`V` link check (8 bytes back) · `W addr(2) word(4)` write code · `P tid(2) code(2) lw(1) crit(1) prog(1)` submit ·
`Q tid(2)` task table (22 bytes) · `C` counters (56 bytes; read after the run) · `R` reset the array (profile kept) ·
`H` hold: accept and queue tasks but start none · `G` go: release the hold (both need a board that reports version 5 in the `V` reply; `host_bridge_v2.v`) ·
`M addr(2) word(4)` write a word of the shared data RAM · `L addr(2)` read one (4 bytes back) · `X prog(1) base(2) len(2)` shared window of class prog: words [base, base+len) of the shared RAM (seen by the program as data word index 2^14 + 0.., byte address 0x10000 +) · `Z` -> DSH(2) window_log2(1) addr_bits(1) (all version 7, `host_bridge_v4.v`; `X` is cleared by `R`, the RAM itself is not) · `Y base(2) len(2)` code library window (version 8, `host_bridge_v5.v`; cleared by `R`) ·
`B prog(1) cbase(2) clen(2) dlen(2)` set the region of program class prog: code words [cbase, cbase+clen) of the shared store, data words [0, dlen) (version 6, `host_bridge_v3.v`; entries are cleared by `R`, so send them after the reset and before the tasks).
Details are in the header of `host_bridge.v`.

## What was measured (not guessed)
Simulation (Verilator): the v4 design passes the same gate as v3 (all results equal the independent ISS, no launch
errors) for 12 policy/seed combinations; makespan is 2.00x v3 because a core step now takes 2 clocks (measured ratio
1.998 to 2.000). The whole-board test passes at both a fast and the real 115200-baud divider.
Data memory: 16 words per slice is enough for the test kernels, 8 is not; the board build uses 16.

Synthesis and place-and-route (native yosys 0.33 `synth_gowin -nowidelut`, then nextpnr-himbaechel for
`GW2AR-LV18QN88C8/I7`, seed 1, target 27 MHz). **S=1** (1 slice, 128 code words, 16 data words):
11,755 of 20,736 LUT4 (57%), 1,564 ALU, 4,191 DFF, 344 of 648 LUT-RAM blocks (53%). It routes and closes timing:
54.6 MHz achieved (target 27). nextpnr's final report file lists fewer LUT4/DFF (9,639 / 2,127) than the log line; the
larger log figure is used here to be safe.

**S=2** (2 slices, 64 code words, 16 data words; `./build_tang.sh build2 2 64 16 16`): 17,575 of 20,736 LUT4 (85%),
2,050 ALU, 5,499 DFF, 505 of 648 LUT-RAM blocks (78%). Routes and closes timing: 57.0 MHz achieved (target 27).
With 128 code words S=2 did **not** place (87% of LUTs and of LUT-RAM), so the instruction memory is the lever: 64 words
hold five of the six test kernels (60 words; `sort` needs 36 more). `run_board.py --lw 0` runs the two slices as two
separate 1-bit cores side by side; the default `--lw` uses both as one 2-bit core.
S=3 and above were not tried; by the per-slice cost below they will not fit.

## What this said about the design (v4 - history; resolved by the pool of 1-bit cores in v5-v8)
`uc_core_rw` is a *simulation model*: it works on 32-bit buses and masks them to the chosen width. As hardware it costs
about 2,800 LUT4 per core, and each extra slice about 4,100 LUT4 once its memories and shifters are included, against
about 470 LUT4 for the fixed 1-bit core measured earlier. The scheduler and host bridge are about 3,300 LUT4 on top.
So this model cannot be replicated 8, 16 or 32 times on this chip. What the build proves is the scheduler path on
silicon (table, queues, profile, UART). The 32-slice array needs the real fusable 1-bit slice with a fusion network,
or at least the narrow-datapath cores, instead of one masked 32-bit core per slice.

## First run on the board (2026-11-12, Alan) - v4, history
S=1 bitstream loaded to SRAM on a Tang Nano 20K; `run_board.py /dev/ttyUSB1` passed: 12 of 12 tasks `ok`, launch_err 0. Task durations equal the simulation's (e.g. sort 74195 clocks, sum 24165-24166), so pins, UART and clock are confirmed on silicon.

S=2 bitstream (`run_board.py /dev/ttyUSB1 --lw 0`, 64 code words): 10 of 10 tasks `ok`, launch_err 0, tasks placed on slot 0 and slot 1 (two cores running side by side on silicon). waste_tail 99,567 slice-cycles: one slot idle at the end of the batch (profile was empty on that run).

## Not verified
Pins are from the MAN file (checked against the chip database, not the schematic). The 54.6 MHz figure is the placer's estimate, not a measurement on silicon (the design ran correctly at 27 MHz).
