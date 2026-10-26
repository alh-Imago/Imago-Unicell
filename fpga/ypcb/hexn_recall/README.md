# hexn_recall: the settings-recall build (prepared 26 Oct 2026; NOT built yet, nothing run on the card)

What it is: the Hex-N core with the settings loader (command 0x13 LOADDET) behind the JTAG bridge on USER2, nothing else (no DDR3). Same top level and pins as `hexn_sweep`. Design and test ladder: `docs/hex-n/CARD_SLICE_v1.md`.
Files used (all new clones; proven files untouched): core v4, lattice v18 (hex7), bank v19, `hexn_loader_v1`, plus the unchanged bridge, memory block, detector v3, glue, cell v5, training bank v9, settings store v2, divider.
Checked in the sandbox: the prebuild gathers the 12 files, the top level elaborates in yosys (BSCANE2 present), and the whole path passes the two simulation checks (`LOADSET CHECK PASS`, `KEY CHECK PASS`; see the design doc). NOT checked: a real build.

## 1. Build (one build, about 15 minutes expected: the joint 7-cell build took 153 s synthesis + 677 s place and route)
In the openXC7 nix shell from `~/ypcb-00338-1p1`, NO sudo, /mnt/hdd mounted, swap on:

    export CHIPDB=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin
    git -C ~/hexn-wt pull origin Hex-N
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_recall designs/hexn_recall
    bash ~/hexn-wt/fpga/ypcb/hexn_recall/run_recall.sh 7

(`run_recall.sh` stops with a message if CHIPDB, the design link or /mnt/hdd is missing.) It prints the clock and size lines and whether a bitstream exists. Log: `/mnt/hdd/hexn_builds/recall_7.log`. Paste the printed lines back.

## 2. Load (only one program owns the JTAG cable at a time)

    ls /mnt/hdd/hexn_builds/recall_7/*.bit
    ~/openFPGALoader/build/openFPGALoader -c digilent_hs2 /mnt/hdd/hexn_builds/recall_7/hexn_recall.bit

(use the file name `ls` shows).

## 3. Tests, in this order, from `~/ypcb-00338-1p1` (each must pass before the next)

    # a) self-test of the existing Hex-N parts (expect BIST PASS)
    nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_bist_v1.py --cells 7 --wires 18 --aw 7

    # b) settings recall: train set A, train set B, load A, B, A back and compare (expect LOADSET CHECK PASS)
    nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_run_v3.py tools/hexn_loadset_check_v1.py docs/hex-n/frontend/example_sensors_script_v1.txt --per 4 --tests 20

    # c) host-side key on the bank (expect KEY CHECK PASS)
    nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_run_v3.py tools/hexn_key_check_v1.py docs/hex-n/frontend/example_sensors_script_v1.txt

If the first command gets no answer, reload the bitstream and try again (this happened once before; a reload fixed it). Paste the output back.

## Reading the result
- The clock is what nextpnr reports, NOT a measurement on silicon.
- Compare size and clock with the base 7-cell figures in the design doc; the loader should add only a little (pre-mapping: about 1 percent more gate cells, 94 more flip-flops).
- If (a) passes and (b) fails, the loader or the core command is the suspect; if (a) fails, the build itself is.
