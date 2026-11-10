# hexn_speech: the speech chain on the Kintex card (self-checking replay)

What it is: `rtl/hexn_speech_chain_v1.v` (window detectors, count/log-probability store, decision) plus a ROM holding the 300 test recordings of the Heidelberg spoken digits as folded events and their labels. The top (`hexn_speech.v`) feeds the recordings to the chain, and after the third window compares the chain's digit with the label.

LEDs: `led[0]` heartbeat, `led[1]` replay finished, `led[2]` PASS (finished and at least 5/6 of the recordings right). The model (and the iverilog simulation of this very kit, `tests/vm/test_hexn_speech_kit_v1.py`) gives 262 of 300 right (87.3%), so a working chain passes. Nothing is read back over JTAG: the LEDs are the whole result. Simulation takes 107,357 clocks (about 2.1 ms at 50 MHz).

Data: `data/` holds the trained chain and the recordings (written by `tools/hexn_chain_kitdata_v1.py` from the SHD files, which are NOT in the repo). `prebuild.py` writes them into the Verilog as initial values, because the card flow's yosys could not be relied on to find data files (the sandboxed yosys used for the checks here only sees its own working folder, so a data file given by absolute path failed; whether the card flow has the same limit was not tested).

Build (same machine, shell and rules as the bnet kit; ONE build at a time; no sudo):
```
git -C ~/hexn-wt pull origin Hex-N
cd ~/ypcb-00338-1p1
ln -sfn ~/hexn-wt/fpga/ypcb/hexn_speech designs/hexn_speech
bash ~/hexn-wt/fpga/ypcb/hexn_speech/run_speech.sh
```
Expect: a few minutes to tens of minutes. The summary prints the nextpnr clock estimate (50 MHz target) and use of the chip. Then load the bitstream the way you loaded the bnet and sweep builds and look at the LEDs.

Caveats: yosys (not nextpnr) estimate for the kit design is about 1,740 LUTs, 886 flip-flops, 15 RAMB36 and 0 DSP; the nextpnr site count is the number to use. The chain is a SIZE, CLOCK and pass/fail test; it is not yet joined to the base controller (no JTAG commands, no run-time loading from the host in this kit).

## First card build (Alan, 9 Nov 2026 23:33 to 23:39)
Built in 6 minutes. nextpnr: 3,175 LUT sites (0.5%), 891 flip-flops, 264 CARRY4, 0 DSP, 15 RAMB36. **Timing FAILED: 32.37 MHz against the 50 MHz target, so the flow made no bitstream.** The critical path ran through a chain of 24-bit compares in the decision step (the argmax over ten scores in one clock). Fix in `rtl/hexn_speech_chain_v1.v` (10 Nov): every ten-way compare is now a scan of one candidate per clock, and the shift, the add, the store address and the store read are separate clocks. Results are unchanged (the RTL still equals the model bit for bit). The new clock has NOT been measured yet; please rebuild.

## Second card build, after the timing fix (Alan, 10 Nov 2026 01:24 to 01:29)
Built in 5 min 17 s, exit 0, **bitstream: yes**. nextpnr: **182.62 MHz after placement, 185.56 MHz after routing, PASS at the 50 MHz target** (estimates, not silicon). 2,861 LUT sites (0.5%; was 3,175), 1,213 flip-flops (was 891: the scan and pipeline registers), 236 CARRY4, 0 DSP, 15 RAMB36. Yosys cells: 694 LUT2, 196 LUT3, 152 LUT4, 337 LUT5, 276 LUT6, 1,207 FDRE, 6 FDSE. Not yet loaded on the card: the self-check LEDs (done, pass) have not been seen.

## On the card (Alan, 10 Nov 2026 01:33 to 01:37): PASS
Load: `~/openFPGALoader/build/openFPGALoader -c digilent_hs2 /mnt/hdd/hexn_builds/speech/hexn_speech.bit` (ordinary terminal, SRAM load). The first load did not start the design (loader status Done 0; all three LEDs lit, led[0] not blinking); loading the same file again worked: led[0] blinks, led[1] and led[2] on = finished and at least 5/6 right (simulation: 262 of 300). If the heartbeat does not blink, load again. The cause of the failed first load is not known.
