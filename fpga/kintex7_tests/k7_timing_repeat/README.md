# k7_timing_repeat -- does the Kintex card give the same clock count every time? (prepared, not yet run on the card)

For Paper 2, "Before submission", item 1. **No new hardware design**: the tests use the k7_freeze_load (v3) bitstream and any ICM runner design already built for the card. Everything is read
over JTAG (USER1); nothing needs pins or PCIe. These scripts have been checked against made-up logs and the v3 kit's own simulation (PASS); they have **not** been run on the card or with openocd.

What they can and cannot show: the card's own clock count from restart to the last result, repeated. The restart and the reads come from the PC over JTAG, so this checks that **repeat runs
and a freeze/release give identical counts on this chip**. It does not test an outside event arriving during a run (the card has no pins to give one), and it is not a throughput test.

## Run order (one command per line)
1. Build and load (openXC7 nix shell, `nix develop ~/toolchain-nix`; skip if the v3 kit is already loaded; LEDs yellow blinking, green on, red off):
   * `sh fpga/kintex7_tests/k7_timing_repeat/build_load.sh`        (set `DEMO=...` if your demo-projects folder is elsewhere)
2. Plain terminal, from `fpga/kintex7_tests/k7_timing_repeat`:
   * `nix shell nixpkgs#openocd --command sh repeat_free.sh 2000`    TEST A: 2,000 restarts, last-result clock each time (expect 6 results, signature 7FEF5298, last word 7FFFFEAA, clock 1562 every time; these are the Tang figures of #1251)
   * `nix shell nixpkgs#openocd --command sh repeat_freeze.sh 50`    TEST B: freeze at 60 346 700 1000 1400, 50 times each, release; the clock must not move
   * `nix shell nixpkgs#openocd --command sh runner_repeat.sh ../../../PATH/TO/runner_folder 500`    TEST C: the same vectors 500 times on an ICM runner design already loaded (needs that design's bitstream on the card, not v3)
3. Send back `results/*.log` (and `results_repeat/*.log` in the runner folder) and the PASS/FAIL summary the scripts print.

Each summary also checks that the run number goes up by one at every restart, so a PASS cannot come from reading one old run again.
