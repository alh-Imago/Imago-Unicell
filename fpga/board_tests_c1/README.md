# C1: how fast does an ESP32 interrupt handler answer, and does it wobble? (ledger #1211)
The Tang is only the stopwatch. Nothing from the UniCell design is in these bitstreams. Built and simulated; NOT yet run on the card.

## Wiring (remove the T2/T3 jumpers first; common GND is already there)
| From | To | What |
|---|---|---|
| Tang pin 86 | ESP32 IO16 | random-timed edges to be answered |
| ESP32 IO17 | Tang pin 72 | the answer (the interrupt handler copies IO16 to IO17) |
| Tang pin 53 | ESP32 IO21 | "storm" edges every 26-76 us (only in the c1_storm build) |
Both boards are 3.3 V. IO16/17/21 are the pins the wiring reference lists for the PIR/tilt/ultrasonic sensors: unplug those.

## ESP32 side
Open `esp32/unicell_c1_interrupts/unicell_c1_interrupts.ino` in the Arduino IDE, upload, open the Serial Monitor (115200, Newline). It prints one line a second. Commands: `l1` compute loop on (default), `l0` loop off, `w<N>` storm work in microseconds (default 6), `i` setup. Please copy its status lines for each run.

## Runs (4 in all, each needs a Tang power-cycle per bitstream; the script asks)
1. ESP32 compute loop ON (default): `sudo LABEL=loopON ./run_c1_v1.sh`  -> c1_quiet, then c1_storm
2. type `l0` in the Serial Monitor, then: `sudo LABEL=loopOFF ./run_c1_v1.sh`
Results: `board_results_<LABEL>.txt` (min, max, average, spread of answer time for rising and falling edges, and a histogram), and the raw files.
`res=L` means the ESP32 did not answer the slow test edges: check wires and that the sketch is running; nothing is measured then.

## What is measured
Clocks of the Tang's 27 MHz clock (37.04 ns) from the Tang's edge to the answer, seen through a 2-flip-flop synchroniser (up to 2 clocks added). Time-outs (no answer within 2 ms) are counted separately.
The handler is the ordinary Arduino `attachInterrupt()` kind, kept in IRAM. Simulation (a stand-in that answers after exactly 1.5 us) reads 43 clocks both ways; the real ESP32 is not simulated.

## C2 (separate sketch, no wiring)
`esp32/unicell_c2_threads_v2/unicell_c2_threads_v2.ino` (v1 in the same folder is the first version: do not use it, it loops on the watchdog): the same job as 1, 2, 4, 8 threads on the ESP32 alone, one core and both cores; prints wall time and the watched job's time (min/avg/max). The ESP32 compared with itself.
I could not compile the sketches for the ESP32 here (only a syntax check on a host with stand-in headers): if the Arduino IDE shows an error, paste it and I will fix it.

## Correction (ledger #1216)
The storm period stated above (26-76 us) and in the sketch header is wrong: the Tang adds 0 to 2,047 clocks to a minimum of 700, so each storm edge comes 26 to 102 us after the last (average 64 us, about 15,670 edges a second). The ESP32 counted about 15,650 a second.
