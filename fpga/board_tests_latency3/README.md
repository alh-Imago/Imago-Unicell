# T3: two inputs, one timed while the other changes (ledger #1209)
Wiring: TWO jumpers on the right header, far end: Tang pin 86 -> pin 72, and pin 53 -> pin 71. Nothing else on 72 or 71 (tilt switch out).
Run: `sudo ./run_groups_latency3_v1.sh` (power-cycle the Tang when asked, one bitstream per power-up). Needs about 25 s per build after loading.
The chip drives both pins itself. Each event picks a new state of the two inputs (the number of active sensors always changes). One input changing = series s; both changing a random 0..2.4 ms apart = series d (time taken from the first edge to the final correct result).
Result line: `pre=`/`p1=` = how often pin 72 / pin 71 followed in the slow pre-check (must be 00000010 = 16 each, else `res=L` and nothing is measured); `bad=` = results wrong after a hold; `nd=` = number of two-input events.
LEDs: 0 heartbeat, 1 pass, 2 fail or loop-back not seen, 3 done, 4 level out on pin 86, 5 level seen on pin 72. Active low.
Simulation only so far: B = 8 clocks constant in both series. No card numbers yet.
