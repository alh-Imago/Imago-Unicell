# hexn_speech: the speech chain on the Kintex card (self-checking replay)

What it is: `rtl/hexn_speech_chain_v1.v` (window detectors, count/log-probability store, decision) plus a ROM holding the 300 test recordings of the Heidelberg spoken digits as folded events and their labels. The top (`hexn_speech.v`) feeds the recordings to the chain, and after the third window compares the chain's digit with the label.

LEDs: `led[0]` heartbeat, `led[1]` replay finished, `led[2]` PASS (finished and at least 5/6 of the recordings right). The model (and the iverilog simulation of this very kit, `tests/vm/test_hexn_speech_kit_v1.py`) gives 262 of 300 right (87.3%), so a working chain passes. Nothing is read back over JTAG: the LEDs are the whole result. Simulation takes 68,357 clocks (about 1.4 ms at 50 MHz).

Data: `data/` holds the trained chain and the recordings (written by `tools/hexn_chain_kitdata_v1.py` from the SHD files, which are NOT in the repo). `prebuild.py` writes them into the Verilog as initial values, because the card flow's yosys could not be relied on to find data files (an absolute path failed in the yosys used for the checks here).

Build (same machine, shell and rules as the bnet kit; ONE build at a time; no sudo):
```
git -C ~/hexn-wt pull origin Hex-N
cd ~/ypcb-00338-1p1
ln -sfn ~/hexn-wt/fpga/ypcb/hexn_speech designs/hexn_speech
bash ~/hexn-wt/fpga/ypcb/hexn_speech/run_speech.sh
```
Expect: a few minutes to tens of minutes. The summary prints the nextpnr clock estimate (50 MHz target) and use of the chip. Then load the bitstream the way you loaded the bnet and sweep builds and look at the LEDs.

Caveats: yosys (not nextpnr) estimate for the kit design is about 1,740 LUTs, 886 flip-flops, 15 RAMB36 and 0 DSP; the nextpnr site count is the number to use. The chain is a SIZE, CLOCK and pass/fail test; it is not yet joined to the base controller (no JTAG commands, no run-time loading from the host in this kit).
