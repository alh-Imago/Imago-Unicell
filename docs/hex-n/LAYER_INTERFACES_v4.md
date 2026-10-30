# Hex-N as one nested unit: layer interfaces v4 (30 Oct 2026)

Clone in spirit of `LAYER_INTERFACES_v3.md` (left untouched). Reason for v4: Alan's change of frame (30 Oct 2026, 22:08 and 22:12). The layers were tested and built as separate parts, but they are parts of ONE unit. The outside is layer 1; each layer sits inside the one before it; the neural helper is the heart. The unit is repeatable. The lower limit for the design is to EQUAL the simple designs it is compared with; fitting on the Tang itself would be good but is not the limit.

Status words: BUILT = RTL passing in simulation (some also run on a card); MODEL = Python only; IDEA = written down only. Every figure below is copied from a row of `HEXN_DESIGN.md` (row time in brackets). Nothing was re-measured for this file. "Untested" means exactly that.

## 1. The picture

```
 world --> [ layer 1: counted detectors, one bank per sensor ]  (skin: meets the sensor wires)
              [ layer 2: history and paths per sensor ]
                 [ layer 3: the same over several sensors together ]
                    [ layer 4: looks ahead, sets goals ]
                       [ helper: judge / key maker / fallback ]  (heart)
   feedback flows OUTWARD at every step; the memory tier runs through the layers as shared storage
```

Each layer takes cleaned input from the layer outside it and gives its result inward. Each layer should also send something back outward. Most of those return paths already exist in the design (layer 4 to layer 3, layer 3 reward to layer 2, layer 2 verdict). The one at the skin (layer 2 to layer 1) does not.

## 2. Each layer, with the same four questions

| | Takes from outside | Gives inward | Feedback outward | Simplest version | Status and evidence |
|---|---|---|---|---|---|
| **1 Detectors** (skin) | coded sensor wires (12 to 20 per bank) | a class number (or NONE), held stable by a hold counter; bursts of 0 to 7 clocks per class | none today. Candidate: layer 2's verdict as the agree/disagree bit (untested) | the counted detector: lane weights counted in one pass, threshold counted, no search; exact-match mode for codes (weights wired from the code) | BUILT, on the Tang and the Kintex card. Minimal detector `hexn_det_v2` 150 / 224 / 268 LUT4 + 35 / 39 / 39 ALU at 12 / 18 / 20 wires [21 Oct]. Held-out accuracy 82 to 86% of the template-rule ceiling at 12 to 20 wires, 8 classes [21 Oct]; light and pot recordings 1.000 [27 Oct]. 19 detectors at 18 wires without feedback on the Tang: 15,730 of 20,736 LUT4, 75.9% [22 Oct] |
| **2 History and paths, per sensor** | each held class | predicted next event with counts and context length; verdict (ok, contradiction, novel, start) | reward values into its store (MODEL only) | store v5: address index plus dense heap, 4-bit events, history and dwell | BUILT. Core v9 with store v5 ran on the Tang and passed: 285 frames, 61 answers checked, 15 rewards [27 Oct 18:25]. Build 12,828 of 20,736 LUT4 (62%), 14 of 46 BSRAM [27 Oct, row 500] |
| **3 History and paths, across sensors** | the stable class of each channel, aligned into moments | ranked possible next moments with weights; confidence report (proposed, `v3` section 2); the choice | reward; contradicted counts | the same store, keyed by the tuple of channel classes | MODEL only (`tools/hexn_layer3_v1.py`); no RTL; hardware plan in `LAYER3_HW_v1.md`. Candidate stage and contradicted counts helped early, not later [14:50]. A planning copy refreshed every 1 to 10 games plays as well as the live one at depth 4 [staleness, 30 Oct] |
| **4 Strategist** | the situation, layer 3's predictions and confidence | a suggestion on its own channel into layer 3; forced win/block played directly | the suggestion channel itself (goal event into layer 3) | expectimax tree with a path-probability cutoff and free plies at confidence .8 | MODEL only (Connect Four, draughts stage 3a/4). Against a plain search of the same style, the plain search was better in Connect Four [21:20] and in the first draughts result [22:50]. The learned model can hurt: against a noisy opponent an empty model beat the learned one at depth 4 (0.98 against 0.71 to 0.74) [stale_v3] |
| **Helper** (heart) | both layers' state; positions | judge to layer 4; similarity and suggestions to layer 3 on their own channel | the end-of-game reward shows how far to follow it | position judge: small network, 127 inputs, 64 hidden units, about 8,000 weights | IDEA for key maker and fallback. The judge is MODEL: wins against lookahead(2) with 20% random moves, hand score against judge: depth 2 0.58 / 0.56 against 0.67 / 0.71; depth 3 0.73 / 0.71 against 0.77 / 0.83; depth 4 0.74 / 0.74 against 0.76 / 0.88 (two halves of 6 seeds x 60 games) [17:45]. The judge at depth 3 matched or beat the hand score at depth 4 with about a sixth of the positions. Limits: one opponent family, Connect Four only, teacher is a search of the hand score, cost per leaf not measured, float activations |
| **Memory tier** (shared, through the layers) | PUT / GET / FLUSH / COUNTERS / LEVEL commands | value or not found | none | three levels of key/value store | BUILT and proven on the Kintex card against the reference model: 2,000,000 steps, 0 wrong, 17 of 17 counters equal [30 Oct]. Not joined to the core. On the Tang the levels would be BSRAM, SDRAM, SD card (`LAYER3_HW_v1.md`); SDRAM test block 538 LUT4 [27 Oct] |

## 3. What today's detector models add to the nested view

All Python, 25 seeds, random patterns, detector model about 0.08 optimistic at 8 classes (see the 22:10 and 22:40 rows).

- **Layer 1 can learn a little while running, with a LOCAL rule.** Only the winning detector's counters move (lane on +1, lane off -1). Trained on 2 samples per class it went from 0.64 to 0.78 (16 per class, frozen: 0.87); with drifting patterns 0.41 to 0.62; steady patterns unchanged. Not helped: a rise in noise. The counted rule applied online with its own answers as labels collapsed (0.875 to about 0.13).
- **The feedback bit itself added little.** The same rule with no bit at all gave 0.76 and 0.61; a perfect bit added 0.02 to 0.07. So the nested frame's natural source for the bit (layer 2's verdict) is worth trying, but it is not what carries the gain.
- **The board trainer cannot do this today.** Its COUNT command applies the counted rule to all K detectors and needs a true label. The local rule would be a new command in a new trainer version, and a way to switch it off in exact-match mode (untested together).
- **Splitting wires into sides helps only for tasks made of independent parts.** Reading each side's winner (no second ring) was smaller and a little better than the single bank on such tasks, and worse on plain tasks. That is layer 3's moment-building, so no new layer is needed for it.
- **A frozen layer 1 shows slow drift to layer 2 as contradictions;** an adapting layer 1 would hide it. This is reasoning, not a measurement.

## 4. Repeatable unit, and fitting on the Tang (facts only)

- The Tang Nano 20K has 20,736 LUT4 slots and 46 BSRAM. Two recorded builds: 19 detectors at 18 wires without feedback, 15,730 LUT4 [22 Oct]; core v9 with the layer 2 store, 12,828 LUT4 [27 Oct]. They are different designs and cannot be added.
- Layers 3 and 4 and the helper have no RTL, so there is NO fit figure for the whole unit. Layer 3's tables would go in BSRAM / SDRAM; the cost of the search and the judge is not measured.
- Open question for Alan (section 6): what is copied per unit and what is shared. The memory tier is the large part; copying it per unit multiplies the biggest cost.
- I cannot say from the record whether repeatability helps or hinders; it depends on that choice.

## 5. How the unit would be compared with the simple designs

Alan's rule: equal is the lower limit; smaller or on the Tang is better. Each comparison below says what is done and what is not.

| Simple design | Compared? | Result |
|---|---|---|
| Cheap filter on one steady sensor (persist, EMA, alpha-beta) | Done [21:00] | Hex-N not better |
| Plain minimax in Connect Four | Done [21:20] | plain search better |
| Plain alpha-beta in draughts | Stage 1 to 4 done [22:50] | first result: plain search better |
| Nearest-pattern / simple trained classifier against the counted detector (same samples) | NOT done | the counted detector is close to nearest-pattern, so an equal result is likely; untested |
| Detector bank (own cell) against the connected cluster | Done [20 to 21 Oct] | bank far better (0.63 to 0.84 against 0.45) |
| Coupled sensors / discrete events against a plain filter | NOT done | the one case where history showed some evidence |

Suggested measures for each future comparison: accuracy (or wins), logic size, and what the simple design cannot do. Only the first two have been used so far.

## 6. Open decisions (for Alan)

1. **Is the unit's heart the helper, as a judge only, or also the key maker and fallback?** The judge is the only part of the stack with a measured gain against the hand score (section 2).
2. **Should layer 1 learn while running (the local rule), and if so is layer 2's verdict the signal?** Needs a new trainer command; the gain without the bit was most of the gain.
3. **What is repeated and what is shared in the unit** (especially the memory tier).
4. **Which comparison first:** the missing classifier baseline, or the coupled-sensor case.
5. Items still open from `v3` (section 6) and `DOUBLE_LAYER3_v1.md` (section 6).

## 7. NOT built

Everything marked MODEL or IDEA has no RTL. Also not built: a trainer command for the local rule, the layer 2 to layer 1 feedback path, the layer 3 and 4 and helper hardware, the join of the memory tier to the core, the output stage, any whole-unit build or fit figure.
