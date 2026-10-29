# Hex-N crib sheet: commands for the Tang Nano 20K and the Kintex card

Written 29 Oct 2026 from Alan's own shell history and the repo scripts. Items marked (unconfirmed) have not been run in this form. Update by adding rows, not by silently changing old ones. Words used: "SD card" is the card in the Tang's slot; "Tang board" and "Kintex card" are the boards.

## 0. Always first: get the latest files
    git -C ~/hexn-wt pull origin Hex-N
(The sandbox pushes to the branch `Hex-N`; the OptiPlex has the checkout `~/hexn-wt`.)

---
## 1. TANG NANO 20K

Bitstreams (`.fs` files) are built in the sandbox by Claude and handed over; Alan loads them. The open flow (yosys, nextpnr-himbaechel, gowin_pack) needs nothing from Alan.

### Load (SRAM only: gone at power-off, the flash is not touched)
    openFPGALoader -b tangnano20k FILE.fs
Write to flash instead (stays after power-off; this replaces what is on the flash, e.g. the LiteX image): add `-f`.
Factory flash backup, read-only (not run yet): `openFPGALoader -b tangnano20k --dump-flash --file-size 1048576 backup.bin`
(unconfirmed) `openFPGALoader -b tangnano20k -r` resets the board; whether it reloads LiteX from flash is not known.

### Serial port (the test boards report here)
Port: `/dev/ttyUSB1`, 115200 8N1 (the second USB serial port of the BL616). Port numbers can change; `ls /dev/ttyUSB*`.

### Card-log test v5 (the SD card tier test; SD card region test)
Bitstreams: `hexn_tang_cardtest_v5.fs` (read-only probe, refuses a non-empty region), `..._erase.fs` (opt-in: wipes its own region first), `..._stage1.fs` and `..._stage2.fs` (the two halves of the power-cut test).
Run and judge one capture (about 5 s):
    stty -F /dev/ttyUSB1 115200 raw
    timeout 5 cat /dev/ttyUSB1 > cap.txt
    python3 tools/hexn_tang_cardtest_check_v5.py cap.txt          # stage 1 half or normal run
    python3 tools/hexn_tang_cardtest_check_v5.py --stage 1 cap.txt   # for the second half (stage 2 bitstream)
Verdicts: PASS, REFUSED (region not empty), CARD ERROR, FAIL, NO REPORT. Keep each raw capture (cap.txt, rename it) when something looks odd.
Power-cut test: load stage 1, capture and check, cut power, load stage 2 with the SAME SD card, capture and check with `--stage 1`.
Rule: an SD card may be reformatted at any time, but the region the test uses must be empty unless the erase build is used.

### Core on the Tang (training scripts etc.)
    sudo sh tools/hexn_tang_run_v4.sh BITSTREAM.fs SCRIPT.txt /dev/ttyUSB1 --cells 7 --wires 18 --aw 7
Memory (save and recall) test: `sudo sh tools/hexn_tang_mem_run_v1.sh BITSTREAM.fs /dev/ttyUSB1`
Bist: `sudo sh tools/hexn_tang_bist_run_v1.sh ...` (the script header lists its arguments).

### Build (done in the sandbox by Claude; for reference)
- Core v9: `sh tools/hexn_tang_build_v18.sh` (output `/tmp/hexn_tang/v18/hexn_tang18_core_v9.fs`)
- Card-log tier test: `sh tools/hexn_tang_cardtest_build_v5.sh` (options by environment: `ERASE=1`, `STAGE=1`, `FINAL_SAVE=1`, `SD_BASE=n`)
- Tier SDRAM test: `sh tools/hexn_tang_tiertest_build_v1.sh`
- Measured size of the cardtest build: about 7.1k LUT4, 3.4k FF, clock 95 to 103 MHz against 27 MHz.

---
## 2. KINTEX CARD (YPCB-00338-1P1, XC7K480T), on the OptiPlex

### Every time, in this order (from `~/ypcb-00338-1p1`)
    cd ~/ypcb-00338-1p1
    git -C ~/hexn-wt pull origin Hex-N
    nix develop github:openxc7/toolchain-nix        # opens the toolchain shell (may download for a few minutes); the prompt changes
    export CHIPDB=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin
Do NOT use `sudo` for builds. The disk for builds must be mounted: `mountpoint /mnt/hdd` (if not: `sudo mount /dev/sda1 /mnt/hdd`).

### One-time links for a design (example: hexn_tier)
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_tier designs/hexn_tier
    mkdir -p /mnt/hdd/hexn_builds/tier_hex7
    ln -sfn /mnt/hdd/hexn_builds/tier_hex7 designs/hexn_tier/build_tier_hex7
(Run the `mkdir` BEFORE the build, or the build stops with "File exists".)

### Build lines (inside the toolchain shell)
Memory tier + Hex-N core (core v9 by default; add `HEXN_CORE=v2` in front for the older core):
    HEXN_REPO=$HOME/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=7 BUILD=build_tier_hex7 THREADS=4 FPGA_HOST=$(hostname -s) ./fpga build designs/hexn_tier ypcb_00338_1p1_ddr3 2>&1 | tee /mnt/hdd/hexn_builds/tier_hex7.log
Tier sizes by environment (defaults 24 24 10 17 14 17): `TIER_KW TIER_VW TIER_FB TIER_BMB TIER_RAMB TIER_SB`.
DDR3 probe + Hex-N (the joint design, line 668 of the history): same line with `BUILD=build_joint_hex7`, `designs/hexn_joint`, log `joint_hex7.log`.
DDR3 latency probe only: `BUILD=build_lat THREADS=4 FPGA_HOST=$(hostname -s) ./fpga build designs/hexn_ram ypcb_00338_1p1_ddr3 2>&1 | tee /mnt/hdd/hexn_builds/ram_lat.log`
Older Hex-N-only design: `designs/hexn_u2` (see history line 598).
After a build: `grep -E "Max frequency|Device utilisation|SLICE_LUTX|FDRE|critical path" /mnt/hdd/hexn_builds/tier_hex7.log | tail` and `ls /mnt/hdd/hexn_builds/tier_hex7/*.bit`.

### Load the bitstream (`.bit`)
    ~/openFPGALoader/build/openFPGALoader -c digilent_hs2 designs/hexn_tier/build_tier_hex7/<name>.bit
(`ls` the build folder for the real name.) Load first, then test, in the order below.

### Tests (each one in its own command; these use `nix shell nixpkgs#openocd`, not the toolchain shell)
JTAG chains: USER1 = ypcb DDR3 register, USER2 = Hex-N core (`HEXN_CHAIN=2`), USER3 = memory tier (`HEXN_CHAIN=3`, set by the script).
1. Hex-N core BIST (right after a load): `nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_bist_v1.py --cells 7 --wires 18 --aw 7`
2. DDR3 calibration: `nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/fpga/ypcb/hexn_ram/run_with_openocd.py designs/uberddr3/check.py`
3. DDR3 latency (only for hexn_ram / hexn_joint builds): `... run_with_openocd.py ~/hexn-wt/fpga/ypcb/hexn_ram/memlat.py --len 10`
4. Memory tier: `nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/tools/hexn_tier7_card_v1.py --steps 2000 --dump tier_dump.json` (prints INFO, compares with the Python model, saves a dump of every level; `--info` only reads the sizes)
5. Training scripts on the core: `... env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_run_v3.py tools/<test>.py docs/hex-n/frontend/example_sensors_script_v1.txt ...`

### Rules and gotchas seen
- Builds run in the toolchain shell with CHIPDB exported; tests run via `nix shell nixpkgs#openocd`. Mixing them gives "can't open file /share/nextpnr/..." (build outside the toolchain shell).
- The Kintex card is powered externally; PCIe is dead; JTAG is the only link. No SD socket.
- Only one program can use the JTAG cable at a time (OpenOCD stops other users).
- Everything in the combined design runs on the 83.33 MHz DDR3 controller clock; the flow's timing check only tests 50 MHz.
- Keep logs on `/mnt/hdd/hexn_builds/`.

### hexn_tier2 (tier with CLEAR, 29 Oct 2026; not built yet when written)
One-time links, then build (about 45 min: synth 6 min, place and route 27 min), inside the toolchain shell with CHIPDB exported:
    cd ~/hexn-wt && git pull && cd ~/ypcb-00338-1p1
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_tier2 designs/hexn_tier2
    mkdir -p /mnt/hdd/hexn_builds/tier2_hex7
    ln -sfn /mnt/hdd/hexn_builds/tier2_hex7 designs/hexn_tier2/build_tier2_hex7
    HEXN_REPO=$HOME/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=7 BUILD=build_tier2_hex7 THREADS=4 FPGA_HOST=$(hostname -s) ./fpga build designs/hexn_tier2 ypcb_00338_1p1_ddr3 2>&1 | tee /mnt/hdd/hexn_builds/tier2_hex7.log
Load: `~/openFPGALoader/build/openFPGALoader -c digilent_hs2 designs/hexn_tier2/build_tier2_hex7/ypcb_00338_1p1_ddr3.bit`
Test (CLEAR is sent first by itself, no reload needed between runs): `nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/tools/hexn_tier7_card_v2.py --steps 20000 --keys 100000`
