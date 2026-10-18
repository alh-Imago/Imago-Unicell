# P1 -- how short a pulse does the ESP32's interrupt handler notice? (ledger #1227)

The mirror of T4 (fpga/board_tests_pulse), for the ESP32. The Tang sends pulses of 12 widths on pin 86 -> ESP32 IO16: 100 us, 50 us, 20 us, 10 us, 5 us, 2 us, 1 us, 600 ns, 300 ns, 150 ns, 75 ns, 37 ns (2700 ... 1 clocks of 37 ns), 512 of each. The ESP32's handler (a RISING-edge interrupt) toggles its answer pin IO17 -> Tang pin 72 every time it runs; a pulse is caught if the answer pin has changed 185 us after the pulse. Two builds: pe_quiet and pe_storm (the C1 storm from pin 53 -> IO21 as well, the ESP32 doing storm work in each storm interrupt).

Wiring: exactly as C1 (Tang 86 -> IO16, IO17 -> Tang 72, Tang 53 -> IO21, GND-GND). Nothing else in those ESP32 pins (PIR, tilt, ultrasonic out).
ESP32: flash `esp32/unicell_pulse_v1/unicell_pulse_v1.ino`. Serial Monitor 115200, Newline. Send `l1` (or `l0`), `w6` (or `w20`), then `z` before each run; then CLOSE the Serial Monitor.
Run: `sudo LABEL=a ESPPORT=auto sh ./run_pulse_esp32_v1.sh` (unplug/replug the Tang's USB each time it asks). About 15 s per build once loaded.
Send back `board_results_<label>.txt` and the `raw` folder (zipped).
Result `L` = the 8 slow pre-check pulses were not all answered (check the wires). Simulation (6 pulses per width, with a stand-in that toggles 1.5 us after every rising edge): all pulses caught in both builds, so any miss on the card comes from the ESP32 side or the wiring, not from the generator.
Builds: pe_quiet 1,400 LUT4, Fmax 131.1 MHz; pe_storm 1,509 LUT4, Fmax 132.8 MHz.
