# Hex-N first card slice, spec v1 (26 Oct 2026) — DESIGN ONLY, nothing built

Status: a plan. Every statement about existing RTL was read from the files named; nothing here has been simulated or run. New files will be clones with new version numbers; proven files stay untouched.

## What the slice is for
Show on the card, with real size and timing, the base of the system: a detector bank trained from labelled examples (level 1), an ENGRAM stored from it (settings read out), a RECALL that writes the stored settings back, and a check that the recalled bank behaves exactly like the original. The host plays the teacher (supplies examples and labels) and does the key matching.

## Parts reused as they are
- Detector bank with its training bank (`hexn_trainbank_v6.v`), settings store as a shift chain (`hexn_cfgbank_v2.v`), run-time detectors, `hexn_bank_v18.v` or earlier base.
- Core command machine `hexn_core_v2.v` (training commands 0x02..0x05, run 0x06, DUMP 0x07), JTAG bridge on USER2, host tooling `tools/hexn_card_run_v2.py`.
- Joint DDR3 + Hex-N design is NOT needed for the slice (7-detector settings are 294 bits).

## New parts
1. **Bank v19** (clone of v18): a multiplexer in front of the settings store's write ports (`cw_we, cw_ad, cwp, cwn, ct_we, ct_k, ct_val`), second source = a loader. No change to the training bank.
2. **Loader** (new small module): receives stored bits and replays them in the order the shift chain needs: K x NB lane writes in ascending order (weight-plus, weight-minus pair per lane), then K thresholds in detector order.
3. **Core v4** (clone of v2): one new command LOADSET that takes the stored bytes from the bridge, drives the loader, and acknowledges when the chain is full. Must be refused or ignored while a training command is running.
4. **Host script**: store (DUMP to a file keyed by a name), recall (LOADSET from the file), key (probe responses), compare.

## Facts read from the RTL
- DUMP (core v2) sends per detector 3 bytes of plus-weights, 3 bytes of minus-weights, 1 byte threshold = 7 bytes; lane j = bit j. The file header comment (5 bytes per detector, 16-lane halves) is out of date against the code. 3 bytes cover up to 24 lanes, so 18 wires fit.
- The settings store clears only on reset; the training bank writes it only in its weight-write and threshold-write states. So one command at a time through the core is enough to keep a half-loaded chain from being disturbed; this is an argument from the structure, not a test.
- The design doc records the trained settings of all 19 detectors read back equal to Python on the Kintex card (leaky-cell test v2), so training and DUMP have run on the card (I have not re-read the script).

## Size (arithmetic)
7 detectors x 18 lanes x 2 bits + 7 x 6-bit thresholds = 294 bits (about 37 bytes, 3 bridge frames). 19 detectors: 798 bits (about 100 bytes, 8 frames).

## Test ladder (each step passes before the next)
1. Simulation: train, DUMP, reset, LOADSET, DUMP again: the two dumps are equal, and answers on 1,000 samples equal the original's (0 differ).
2. Simulation: load engram A, then engram B over it, then A again; answers always equal that engram's original.
3. Card, 7 detectors: same as 1 and 2 using the existing host tooling.
4. Host-side key: the response of the bank to a fixed probe set (which detectors fire) as the quick key; recall the right engram from damaged or noisy probes; compare with the model rates (hexn_engram_v2: 72-bit key, 40/40 clean).
5. Key in the memory block: the memory block holds 8 slots of 18 wires; a 72-bit key takes 4 slots, so decide key length against slots (open).
6. Report size and clock of the build against the sweep figures.

## Open points
- Bank training has run on the card; LOADSET has not been designed in RTL.
- Cell-network settings (the NC cells) use a different path (core commands 0x0E / 0x11); the slice covers the detector bank only. Whether the cell v5 matches the Python cell model is still unchecked.
- The goal teacher and level 2 are not part of this slice.
