# S-Core on the Tang Nano 20K (single set, v4)

This folder is the first path from the simulated S-Core scheduler to real hardware. Everything here is tested in
simulation and through the open-source place-and-route tools; **nothing has been run on a board yet.**

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
`Q tid(2)` task table (22 bytes) · `C` counters (56 bytes; read after the run) · `R` reset the array (profile kept).
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

## What this says about the design (important)
`uc_core_rw` is a *simulation model*: it works on 32-bit buses and masks them to the chosen width. As hardware it costs
about 2,800 LUT4 per core, and each extra slice about 4,100 LUT4 once its memories and shifters are included, against
about 470 LUT4 for the fixed 1-bit core measured earlier. The scheduler and host bridge are about 3,300 LUT4 on top.
So this model cannot be replicated 8, 16 or 32 times on this chip. What the build proves is the scheduler path on
silicon (table, queues, profile, UART). The 32-slice array needs the real fusable 1-bit slice with a fusion network,
or at least the narrow-datapath cores, instead of one masked 32-bit core per slice.

## First run on the board (2026-11-12, Alan)
S=1 bitstream loaded to SRAM on a Tang Nano 20K; `run_board.py /dev/ttyUSB1` passed: 12 of 12 tasks `ok`, launch_err 0. Task durations equal the simulation's (e.g. sort 74195 clocks, sum 24165-24166), so pins, UART and clock are confirmed on silicon.

S=2 bitstream (`run_board.py /dev/ttyUSB1 --lw 0`, 64 code words): 10 of 10 tasks `ok`, launch_err 0, tasks placed on slot 0 and slot 1 (two cores running side by side on silicon). waste_tail 99,567 slice-cycles: one slot idle at the end of the batch (profile was empty on that run).

## Not verified
Pins are from the MAN file (checked against the chip database, not the schematic). The 54.6 MHz figure is the placer's estimate, not a measurement on silicon (the design ran correctly at 27 MHz).
