# T4 -- pulse width at the input pin (ledger #1224)

Question: how short can a pulse on an input pin be before the UniCell design (direct sensor mode) no longer sees it?

The Tang drives pulses of 12 widths (2 ms down to 1 us, 512 pulses each) on pin 86; the existing T2 jumper (pin 86 -> pin 72) feeds them into sensor input 1. The design samples that pin once per 1 ms (27,000 clocks). A pulse counts as *caught* if the design's result became non-zero at any time from the rising edge to 28,000 clocks after the falling edge. Before each pulse the Tang waits 60,000 clocks plus a random 0 to 131,071 clocks, so pulses land at random points between samples.
The expectation to be tested (not assumed): a sampler that looks once per 1 ms catches a pulse of width W with probability min(1, W / 27,000 clocks).

Wiring: only the T2 jumper, pin 86 -> pin 72, nothing else in pin 72 (tilt switch out). Nothing needed on the ESP32 side.
Run:  `sudo LABEL=a sh ./run_pulse_v1.sh`   (two builds: pls_idle, pls_busy with 24 free-running load lanes; unplug/replug the Tang's USB each time it asks). About a minute per build.
Send back `board_results_<label>.txt` and the `raw` folder (zipped).
Result `L` means the loop-back pre-check failed (check the jumper); `F` means the result was not zero before some pulse (stale=).

Simulation (6 pulses per width, short random gap): the 2 ms and 1 ms pulses were all caught in both builds; shorter widths are shown in the ledger. Builds: pls_idle 1,641 LUT4, Fmax 123.6 MHz; pls_busy 2,850 LUT4, Fmax 120.0 MHz; the busy build adds 800 flip-flops (24 lanes x 32 + 32), so its load was kept.
