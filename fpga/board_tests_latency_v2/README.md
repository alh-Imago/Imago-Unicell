# T2 latency test, v2 (ledger #1207)
Clone of board_tests_latency (v1, whose first card run timed out on every edge, #1207). New: a pre-check first.
Wiring: ONE jumper, Tang pin 86 -> pin 72 (4th pin from the end of the right header). Nothing else on pin 72 (take the tilt switch out). Pin 71 empty.
Run: `sudo ./run_groups_latency_v2.sh` (power-cycle the Tang when asked, one bitstream per power-up).
Result line: `pre=00000010` means pin 72 followed pin 86 all 16 times; then the latency numbers follow. `res=L` means the loop-back was not seen and nothing was measured.
LEDs: 0 heartbeat, 1 pass, 2 fail/loop-back not seen, 3 done, 4 level sent on pin 86, 5 level seen on pin 72 (4 and 5 should blink together while it runs the pre-check). Active low.
Simulation only so far: B = 8 clocks constant; no card numbers yet.
