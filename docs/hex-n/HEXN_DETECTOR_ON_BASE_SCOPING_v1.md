# Layer 1 detector back on the Kintex base: scoping (v1, 5 Nov 2026)

Step one of the core line in `HEXN_DIRECTION_SCOPING_v1.md` (Alan 22:59: start at the base, the detector system, then the batch judge, then the neural cell design). Scoping only: nothing built yet. Tags: [file] read in a file, [card] seen on the card, [arith] arithmetic from file figures, not a measurement, [open] undecided or unchecked.

## 1. What already exists
- Layer 1 is BUILT on the Tang and on the Kintex card [file: LAYER_INTERFACES_v4 section 2]. It takes coded sensor wires (12 to 20 per bank) and gives a class number (or NONE), held stable by a hold counter.
- On the Kintex card, hex19 (19 detectors, 18 wires each) passed the built-in self-test over JTAG (342 counters, 342 weights, 19 sums, 19 thresholds, 76 answers and bursts per set, 24 divider tests) and the leaky-cell test (0 of 9,120 frames differing) [file: ledger rows 256 and 260, Oct 2026]. Bigger builds placed up to 128 cells at 73 MHz as reported by nextpnr, not run on the card [file: row 262].
- The detector core is a byte-command device behind its own JTAG byte bridge: `rtl/hexn_core_v1.v` (later versions v2 to v9 exist) and `rtl/hexn_jtag_bridge_v1.v`, whose BSCANE2 chain is a parameter (default USER1) [file]. The base host tools select their chain with `HEXN_CHAIN` (used as 2 in the card tests) [file], so the two bridges look able to live in one chip on different chains [open: not tried].
- The batch judge reads words of layer-1 bins: eight sensors, one 4-bit class (0 to 11) each [file: SCORER_v1]. So the link is: one detector bank per sensor gives a class; eight classes pack into one judge word.

## 2. What is not known [open]
- Which core version is the current layer 1 (the card runs were `hexn_core_v1` on the Kintex; `core_v9` with store v5 ran on the Tang). Needs checking against the newest ledger rows before choosing.
- Whether the detector's class output is available as a signal inside the chip in the form the judge word needs (the core is built around byte commands and an `ans_class` signal).

## 3. Ways to join them
- **A. Same chip, host in the middle.** Load the detector core on its own chain next to the base. The host runs a sample through the detector, reads the class, packs eight classes into a judge word and sends it to the base. No new RTL, quickest to try, but the class travels over JTAG both ways, so JTAG (about 5,500 scans per second measured) stays the limit.
- **B. On chip.** The base controller drives the detector core as another target (like the arrays), takes `ans_class` for each sensor and feeds the packed word straight into the batch judge. New controller version (v5), simulation first. Raw sensor bits go in over JTAG, only the judge's answer comes out.
- **Banks:** the judge expects eight sensors. Eight parallel banks cost, by [arith] from the October placed figures (about 10,100 LUT for hex19 with one cell, about 450 LUT per extra detector), roughly 8 x 8,500 = about 68,000 LUT for the detectors alone, against 298,600 on the chip and about 19,100 for the base now. One bank time-shared across the eight sensors (settings reloaded per sensor) is far smaller but eight times slower per word. Alan to choose.

## 4. Proposed order
1. Check the newest detector core and its ledger rows; settle the output signal. 
2. Try A on the card (no new RTL) to show detector -> judge end to end with real class words.
3. Build B in simulation, then on the card, once the shape (banks, time-sharing) is chosen.
4. Then the neural cell design.

## 5. Questions for Alan
1. A first (quick, host-linked) or straight to B (on chip)?
2. Eight banks or one time-shared bank?
3. What feeds the sensors for now: recorded test vectors from the host?
