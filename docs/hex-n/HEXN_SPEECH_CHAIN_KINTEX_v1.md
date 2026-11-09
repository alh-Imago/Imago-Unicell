# The speech chain placed on the Kintex card (v1, 10 Nov 2026)

Alan 23:14: "place the full path into the kintex, then run some tests". Tags: **[sim]** simulation or model result, **[yosys]** local synthesis count (NOT the nextpnr site count), **[proposal]** not built, **[open]** undecided. Nothing here is a card result yet.

## 1. What is placed
```
 host front end (fold 700 channels to 48 lines, top 8 busiest lines per time step)   [host / sensor side, Python today]
   |  events: (step, line) -> one address per event
   v
 hexn_speech_chain_v1  (rtl/hexn_speech_chain_v1.v)
   layer 1  event-driven detector bank: 1 word read per event (10 detectors x 2-bit ternary weights), 10 accumulators; per window end: margin = acc - threshold, class = largest margin or NONE
   layer 2  count store as a log-probability table LP[digit][window][previous class][class]: 10 lookups-and-adds per window end
   layer 4 style decision: score = path score + shifted margin sum; argmax; gap between the two best margin sums -> stop flag
   |  per window end: class, predicted digit, gap, stop
   v
 host / base results RAM / batch judge   [proposal]
```
Everything is shifts, adds, compares and block RAM. **No multiplier, no DSP [yosys].**

## 2. What changed from the built counted detector (the widening)
1. **Wires to events.** The built detector (`hexn_det_v4.v`) holds 12 to 20 wires in parallel. Speech needs 192 per window (48 lines x 4 steps), and 960 over five windows. Instead of 192 parallel lanes, each event reads one word of weights (a RAM of 960 x 20 bits) and the 10 accumulators add it. Same sum as the parallel bank with PL = 1 (the built one multiplies by PL = 10, a scale only). [sim: bit-exact against the Python model]
2. **Accumulator.** 8 bits signed per window (at most 32 events x +-1); margin 9 bits; margin sum 16 bits; score 24 bits. The built v4 has AW 8.
3. **One bank, five windows.** The weights of window w are the w-th block of the RAM, so one set of adders serves all windows.
4. **New parts:** the store (605 x 80-bit words) and the decision (shifts, argmax, gap). Store v5 (`hexn_store_v5.v`, predicts the next event) is a different structure and is NOT used here; the table here is a plain RAM written by the host.
5. **Loading.** Weights, thresholds, store and shift codes are written through a config port (`cfg_sel` 0 to 3) or preloaded; both paths give the same outputs [sim].

## 3. Tests run [sim]
| test | result |
|---|---|
| RTL against the exact-arithmetic Python model, random weights, thresholds, store and event streams (40 recordings x 5 windows), config preloaded and config written through the port | identical in every window (class, predicted digit, gap, stop) in both modes; a mutated model disagrees (`tests/vm/test_hexn_speech_chain_v1.py`) |
| The 300 real test recordings through the simulated RTL | 1,500 of 1,500 windows identical to the model; accuracy after 1 / 2 / 3 / 4 / 5 windows 68.7 / 85.0 / 87.3 / 87.0 / 85.3 % (unheard speakers 72.0 / 89.3 / 88.9 / 88.9 / 87.2 %) |
| Early stop on the RTL's gap output | gap >= 10: 2.40 windows used, 86.3 %; gap >= 20: 3.49 windows, 86.0 % |
| Kit top (replay of the 300 recordings, compare after window 3), `tests/vm/test_hexn_speech_kit_v1.py` | 262 of 300 right, PASS led on, 68,357 clocks (about 1.4 ms at 50 MHz; 107,357 after the timing fix, section 64) |
| Robustness: events dropped at random from the 300 real recordings (model arithmetic), accuracy after 3 windows | 0 %: 87.3; 10 %: 87.3; 30 %: 80.7; 50 %: 68.7; 70 %: 44.0 (chance 10 %) |

## 4. Size [yosys, not nextpnr]
| target | design | LUTs | flip-flops | block RAM | DSP |
|---|---|---|---|---|---|
| Xilinx 7-series (`synth_xilinx`) | the chain module alone | 2,240 (LUT2 591, LUT3 529, LUT4 158, LUT5 535, LUT6 427) | 889 | 5 RAMB18 + 1 RAMB36 | 0 |
| Xilinx 7-series | the whole kit (chain + 300-recording ROM + replay) | about 1,740 | 886 | 15 RAMB36 | 0 |
| Gowin (`synth_gowin`, for the Tang Nano 20K) | the chain module alone | about 4,700 LUT1-4 (20,736 on the chip) | 966 | 7 BSRAM + 25 RAM16SDP4 | 0 |
The two LUT figures for the chain module differ because the kit's tie-offs and the flattening change what is kept; the nextpnr site count on the card flow (as for the bnet kit) is the number to use. No place and route was run for the Tang. The earlier yosys-versus-nextpnr mix-up (section 47b) is why these are not called site counts.

## 5. Where it joins the base (proposal, not built)
The Kintex base (controller v1 to v4, results RAM, batch judge) has no detector. The chain would be one more target of the controller, as the arrays are:
- **J-load:** write weights, thresholds, store, shift codes (the cfg port) from the host over the existing JTAG byte commands, or from the weight store (`O`, `F`).
- **J-events:** event words (address) and a window-end word from the host (or from RAM), one per command or in blocks.
- **J-result:** the per-window record (class, digit, gap, stop) into the results RAM, so the judge's decision bit and the library slot choice (`Z`) can use it.
- **[open]** where the fold and the top-8 selection live: on the host (today), or in logic on the card.
- **[open]** the batch judge takes bins 0 to 11 of eight sensors; the chain's output is a digit and a gap. Whether the judge scores the chain's margins (as bins) or the chain replaces the judge's job for this task is Alan's call.

## 6. Not done
No nextpnr place and route of the chain or the kit; no bitstream; no run on the card; no JTAG command set; the weights were trained on the host from the SHD recordings (not in the repo); one train and test split; 300 test recordings; the front end is my own fold, not the real sensor path.
