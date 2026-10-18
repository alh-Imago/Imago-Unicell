# T2: how long from an input pin changing to the result changing (ledger #1206)

Built by `tools/board_direct_latency_v1.py`. Two bitstreams, `groups/lat_idle.fs` (nothing else running) and `groups/lat_busy.fs` (24 free-running 32-bit lanes of logic switching every clock; their folded output is printed as `chk=` so the build cannot drop them).

**Wiring (one jumper):** Tang pin **86** (right header) to Tang pin **72** (input 1). Take the hand jumper off 72. Nothing is used on pin 71. Leave the ESP32 link wires unplugged or plugged, it does not matter (nothing reads them).

**What the chip does:** it raises pin 86 at a random moment, waits for the direct-mode unit's result to change, holds for a random time, lowers the pin, waits for the result to go back, and repeats 2,048 times. A counter on the 27 MHz clock times each wait. The direct-mode unit is the same RTL as `unit_tree_direct_v1` (sampling once per millisecond).

**Numbers printed (clocks; 1 clock = 37.04 ns), for rising and falling edges:**
- `rA`, `fA`: edge to result. Includes the wait for the next 1 ms sample, so a spread of up to 27,000 clocks is expected (it is the sampling window).
- `rB`, `fB`: from the last sample tick to the result: the part the design adds. The pass test is min = max here, and the same in the busy build as in the idle one.
Simulation (checked before the build): B = 8 clocks, constant, idle and busy.

**Run (Linux):** `sudo ./run_groups_latency_v1.sh` (power the Tang off and on before each load, as for the other board tests). Results land in `board_results.txt`. A missing or loose jumper shows as time-outs and `res=F`.
