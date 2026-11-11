# hexn_speech2: the speech kit with an exact-count readout (11 Nov 2026)

Clone of `fpga/ypcb/hexn_speech` (left untouched, and its data folder is read from there, nothing is copied). Same chain, same replay of the 300 recordings, same three LEDs (heartbeat, finished, PASS). New: a read-only 64-bit JTAG register (BSCANE2 USER2, IR 0x03) that gives the exact counts, so the card can show 262 and not only "at least 5/6".

Register (bit 0 shifted out first): [8:0] correct, [17:9] total scored, [26:18] recordings started, [27] done, [28] pass, [31:29] 0, [63:32] 0x53504348 ("SPCH"). The counts stop changing when done = 1, so a read after that is exact. Nothing can be written to the card through it.

## Status
Simulated only (`tests/vm/test_hexn_speech2_kit_v1.py`: the register read through the BSCANE2 model after the replay gives magic SPCH, done 1, pass 1, total 300, recordings 300, correct 262; a read while the replay runs shows done 0). NOT built on the card flow yet, NOT run on the card. nextpnr size and clock unknown (expect close to the v1 kit: 2,861 LUT sites, 185 MHz; this is an expectation, not a result).

## Build and run (openXC7 shell, as the v1 kit)
```
git -C ~/hexn-wt pull origin Hex-N
cd ~/ypcb-00338-1p1 && ln -sfn ~/hexn-wt/fpga/ypcb/hexn_speech2 designs/hexn_speech2
bash ~/hexn-wt/fpga/ypcb/hexn_speech2/run_speech2.sh
```
## Load and read (ordinary terminal; load again if the printout does not end with done 1)
```
~/openFPGALoader/build/openFPGALoader -c digilent_hs2 /mnt/hdd/hexn_builds/speech2/hexn_speech2.bit
cd ~/ypcb-00338-1p1 && nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_REPO=$HOME/hexn-wt python3 ~/hexn-wt/fpga/ypcb/hexn_speech2/check.py
```
`check.py` stops other programs that hold the cable (it kills hw_server/openocd as the other Hex-N check scripts do), reads the register until done, prints the counts and says PASS if they equal the model's (300 scored, 262 correct). `check.py --decode HEX` decodes a value without the card.
