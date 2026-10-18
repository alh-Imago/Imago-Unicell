# C1 v2: cumulative interrupt counts, and a cleaner stopwatch (ledger #1217)
Same three wires as C1 (see ../board_tests_c1/README.md): Tang 86 -> ESP32 IO16, ESP32 IO17 -> Tang 72, Tang 53 -> ESP32 IO21, GND-GND. Built and simulated; NOT yet run on the card.

## What is new
* ESP32 sketch `esp32/unicell_c1_interrupts_v2/unicell_c1_interrupts_v2.ino`: every status line now also shows `evT=` and `stormT=`, running totals that never lose an edge while a line is being printed. `z` zeroes them.
* Tang stopwatch: an edge with no answer within 2 ms no longer makes the next edge read as a 1-clock answer. Unanswered rising/falling edges are counted apart (`tor=`, `tof=`), edges that could not be timed because of one are counted in `inv=`, and the timed counts (`nr=`, `nf=`) give correct averages. In simulation, an edge the stand-in never answers gives tof=1, inv=1 and no 1-clock artifact.
* The storm period is 26 to 102 us (mean 64 us), about 15,670 a second. (The 26-76 us in the earlier files was wrong, ledger #1216.)

## Runs (the same four as before)
1. Upload the v2 sketch. Close the Arduino Serial Monitor before each run (the script needs the port), or just do not use the script's ESP32 recording and copy the lines by hand.
2. Find the ESP32's port: `ls /dev/ttyUSB* /dev/ttyACM*` with the ESP32 plugged in (the Tang uses /dev/ttyUSB1 by default).
3. Compute loop ON (default): `sudo ESPPORT=/dev/ttyUSB0 LABEL=on ./run_c1_v2.sh`   (use your ESP32 port)
4. Compute loop OFF: open the Serial Monitor, type `l0`, close it, then `sudo ESPPORT=/dev/ttyUSB0 LABEL=off ./run_c1_v2.sh`
Results: `board_results_<LABEL>.txt`. With ESPPORT set it also compares the ESP32's interrupt count with the edges the Tang sent: if an edge was unanswered and the counts differ by about that much, the interrupt was missed; if they match, it ran but the answer was late or wrong.
