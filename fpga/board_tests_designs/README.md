# Tang Nano 20K: designs built from an ICM on the standard line (ledger #1124)

Power the card up cold, then `sudo ./run_all.sh` (or `run_all.bat`); results land in `board_results.txt` / `.csv`. LED1 = PASS, LED2 = FAIL, LED3 = finished, LED0 = heartbeat. Power it OFF between sessions.

| test | what | LUT4 | FF | Fmax MHz |
|---|---|---|---|---|
| `std_tree4` | 4-input sum tree built from the ICM (-s std): 6 vectors of 4 words (negatives, and one sum that wraps around 32 bits) give the 6 sums in order | 2109 | 978 | 124.8 |
| `std_gen_ring` | looped CORDIC ring on standalone shells with the ring control GENERATED from the ICM (offset 8, reference 12): exactly 20 results, quiet, one release gives one more | 5191 | 3329 | 120.7 |

`std_tree4`: 6 sums expected (e=0006), n0=0000 and st=3 are fixed (no release phase). `std_gen_ring`: e=0015 (21 = 20 then one after the release), n0=0014, st=3 as for std_ring.

Honest limits: simulated (UART text decoded) and timing-closed at 27 MHz; not yet on the card. The expected words are computed here (sums) or from the model (CORDIC).
