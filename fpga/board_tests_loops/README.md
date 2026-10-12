# Tang Nano 20K: the ring-controlled loops on the card (ledger #1118)

Each `<name>.fs` is a self-checking bitstream. Run `./run_all.sh` (Linux, needs `openFPGALoader`, root or the dialout group) or `run_all.bat` (Windows, needs `pip install pyserial`); the results land in `board_results.txt` / `.csv`. LED1 on = PASS, LED2 on = FAIL, LED3 on = finished, LED0 = heartbeat (active low). Bitstreams go to SRAM only. Same tooling and serial settings as the #1023 package (`fpga/board_tests/`); the board stops answering after about 5 loads in a row, so `run_all.sh` asks for a replug every 4.

## What each loop test does

z0 is injected once. The ring must give exactly **20** results, each equal to the model's word, stay quiet, and (flex and sub) show `ring_stopped`. One **release** is then given: flex and sub run another **20** (a release opens a new window of N) and stop again, std gives exactly **one more** (the 21st). `mixed_pipe` is a pipeline, not a loop: 8 words through flex, bridge, SUB, bridge, flex, each x + 1239, with random exit stalls.

## The line

`UCT <name> res=P|F n=<results> e=<expected, hex: 0028 = 40 for flex and sub, 0015 = 21 for std> bad=<wrong or extra> to=<timeout> n0=<results when the release was given: 0014 = 20> st=<bit1 stopped at release, bit0 stopped at the end: 3 = both> last=<cycle of the last result> sig=<checksum> w=<first 8 words>` (all hex). `std_ring` has no stop flag on a pin, so its `st` only means 'quiet after exactly 20'.

## The tests

| test | what it proves | LUT4 | FF | Fmax (MHz, 27 needed) |
|---|---|---|---|---|
| `flex_ring` | looped CORDIC ring in generated flex RTL: stops after exactly 20 results; one release lets it run 20 more and stop again | 3153 | 2301 | 139.2 |
| `sub_ring` | looped CORDIC ring in generated SUB RTL (fixed 1-clock cells): stops after exactly 20 results; one release lets it run 20 more and stop again | 2887 | 2125 | 134.6 |
| `std_ring` | looped CORDIC ring on standalone v4 shells (counter + branch + join-gate in the ring): stops after exactly 20 results; one release gives exactly one more | 4986 | 3181 | 119.2 |
| `mixed_pipe` | flex -> bridge -> SUB -> bridge -> flex pipeline, x + 1239 (random exit stalls) | 1770 | 1018 | 119.9 |

## Honest limits

- Each passed in simulation (UART text decoded) and closed timing at 27 MHz in place-and-route; none has been on the board yet.
- 27 MHz only (no PLL): a correctness test on silicon, not a speed test. Fmax is nextpnr's static figure.
- The expected words are the model's (`looped_cordic_v1.model`); the generated RTL and the grids were proven equal to it in simulation (#1110, #1111, #1116, #1117).
- Only 20 + 1 results are checked; the long-run behaviour (hundreds of steps) was checked in simulation, not here.

## If a test prints nothing (ledger #1119)
The first run (23:35) showed `flex_ring` with 41621 bytes received but no line accepted: the parsers of the first package rejected the loop tests' extra `n0=`/`st=` fields (fixed in this package). The other three received 0 bytes. Try one at a time with a replug between: unplug the USB cable, plug it back in, wait 20 s, then `sudo env ONLY="mixed_pipe" ./run_all.sh /dev/ttyUSB1`. If it is still silent, keep the `raw/` folder (`raw/<name>.bin`, `.loader.txt`, `.ports`) and send it.
