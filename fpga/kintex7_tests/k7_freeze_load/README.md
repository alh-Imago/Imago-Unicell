# k7_freeze_v3 -- freeze, SAVE and LOAD the Tang tree on the Kintex card over JTAG (ledger #1250)

Clone of the hidden-state kit (k7_freeze_dbg). New: the cells can be **written** (load-capable debug cells), the driver restores its own state, and the freeze is
**cycle-exact** (the earlier kits froze one clock late: the cells were one clock ahead of the driver's count, and a release did not remove that skew).

* **Save** = read the frozen grid (all registers of all 13 cells, plus the driver's count and bookkeeping): `freeze_save.sh T` writes `saved_T.txt`.
* **Load** = write those registers back into the cells and restore the driver: `freeze_load.sh saved_T.txt` (the grid stays frozen), `freeze_load.sh saved_T.txt run` (then release).
* **Round-trip test on the card:** `freeze_saveload_test.sh 346 1400` = freeze at 346 and save; run to 1400 (a different state); load the saved state; read it back (must be identical); release;
  the run must finish with the Tang's results (signature 7FEF5298, last word 7FFFFEAA, last result at count 1562). The script checks all of this and prints PASS / FAIL.

## Do this (same flow as before; a different folder and bitstream)
1. Copy this folder into `demo-projects`. In the openXC7 Nix shell: `make`, then `make program JTAG_LINK="-c ft232"`.  Red LED off, yellow blinking, green on = ready.
2. From a **plain terminal**, in this folder, one command per line:
   * `nix shell nixpkgs#openocd --command sh freeze_read.sh`   (expects magic 46525A33 "FRZ3")
   * `nix shell nixpkgs#openocd --command sh freeze_at.sh 346`
   * `nix shell nixpkgs#openocd --command sh freeze_release.sh`
   * `nix shell nixpkgs#openocd --command sh freeze_saveload_test.sh 346 1400`   (the main test; try 60, 700, 1000 as well)
   * `nix shell nixpkgs#openocd --command sh freeze_sweep.sh 0 1700 1`   (every count, about 2 minutes; sweep.csv)
3. Send back the output / csv files.

## Checked in simulation (not on the card)
`make sim`: the frozen state, visible and hidden, equals the free-running state AT count T at 24 counts (cycle-exact); freeze + release gives the free run's results AND the
same clock for the last result; save, disturb, load, release does the same at four counts; a deliberately corrupted loaded register changes the results (negative control).
