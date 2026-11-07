# Hex-N: direction scoping (v1, 5 Nov 2026)

A living note. It records where the work is heading, what is core and what is a side route, and how far the build is from the core idea. It may grow or shrink. Tags: [file] read in a file, [card] seen on the Kintex card, [sim] simulation only, [open] undecided or unchecked, [Alan] said by Alan.

## 1. The core idea
From `HEXN_DESIGN.md` sections 1 to 3 [file]: Hex-N is the silicon version of a nerve cell and then a substrate of many. A cell has six faces with lanes, adds up what arrives, compares the total with a threshold and fires a graded burst. Its programme is a pattern that is trained, not written. Learning has three steps: train in the VM, freeze the pattern, optionally keep mutating in silicon.

## 2. Core line and side route [Alan, 5 Nov 22:53]
- **Core line:** the layer 1 counted detector, the layers above it (the helper / neural judge, the choice engine), the batch judge beside them, and the learning. The detector and the batch judge fit this schema well; the layer 1 detector was part of the initial thrust.
- **Side route:** the hex work cells were applied early, to see whether they could interface with the schema and use the space on the Kintex card. They are extra processing capacity (the pattern arrays), not the neuron.
- **Direction:** the original schema, with the Kintex space as the extra processing array.

## 3. Where the build stands against it
| Part | State |
|---|---|
| Layer 1 counted detector | Built and run on the Tang Nano 20K [file: ledger Oct 2026]. Not in the current Kintex base [Alan confirmed 19:49]. Earlier Kintex builds ran it with the memory tier. |
| Layers 2 to 4 (combined) | Not in the Kintex base [open: ledger says they were combined and later removed; not re-checked]. |
| Neural judge (helper) | `rtl/hexn_neural_v1.v`, simulated only, in no top level [sim]. |
| Batch judge | Built (Tang batch scorer); runs on the Kintex base [card]. Weights are worked out on the host, not learned on chip. Weight store with save, load and a cross-index to program slots: simulation only [sim]. |
| Pattern arrays (hex7, hex6) | On the Kintex card with a JTAG controller, results RAM with stop-and-flag, data RAM with run-from-RAM [card]. Six work types in use. |
| Merged work cell | `hexn_tile_wk_v1.v`, equal to the six old tiles in simulation; synthesis size only (about 656 LUT); not in the generator or any build [sim]. |
| Auto picker (data in, judge picks the program, data runs through it) | Agreed as the next build; slot choice by the judge works on the card, the sequencer is not built [card / open]. |
| Learning in silicon (step 3) | Not done. |

## 4. Gaps to the core idea
1. The detector and the upper layers are not on the Kintex base; there is no direct input path to the card other than JTAG, so raw data would not reach it anyway [Alan].
2. Learning is on the host: batch weights are computed there; nothing mutates on chip.
3. The neural judge has no home: inputs, teacher and role are undecided.
4. The work cells are serial word cores, not the summing cell of section 1.

## 5. Open decisions
- Faces of the neuron cell do not talk to each other (`HEXN_DESIGN.md` 2a): decision for Alan, not seen settled.
- Leak or clear, memory size, where the teacher lives (design doc section 5).
- Where the pattern arrays sit in the layers: after the helper and before the choice engine (a), after the choice engine (b), or extra processing after layer 1 (c). The base behaves as (c).
- Auto picker: how many programs; what happens when no result or an empty slot.
- Merged work cell: every core in every cell (as built) or a chosen subset; add SQ and LT or not.
- Work cell shape: the neuron-style cell versus the word cores for the arrays.

## 6. Next steps (proposals, not commitments)
1. Merged cell into the pattern generator; place and route it on the Kintex flow for real size and clock.
2. Auto picker sequencer (ctl v5) on the existing judge, weight store and data RAM.
3. Decide the neural judge's placement and what gets brought back onto the Kintex from layer 1 upward.

## 7. Note on the design document
The status line of `HEXN_DESIGN.md` (20 Oct: "nothing has been routed or run on a card") is out of date. The ledger is append-only, so it is corrected here and by a ledger row, not by editing it.

## 8. Weight library and the self-teaching loop (Alan, 7 Nov 21:33 to 21:39; IDEAS, nothing built)
- **Idea [Alan]:** as data arrives the judge loads a program and its weights. If no stored weight set fits, it searches the stored sets with a fuzzy match, loads the pre-completed ones, compares them, finds what they have in common and builds the new set from that (the stored things are weight sets, not paths).
- **Teacher placement [Alan]:** if a prediction from matching against the cross map turns out correct, that result feeds back into the system. Whether this sits in teacher mode or live mode is a real question. Prediction against the next observation gives labels for free (reality is the answer), which is the reward step of the Gemini list (`HEXN_GEMINI_SCOPING_NOTES_v1.md`, step 5) and the open question in `LAYER_INTERFACES_v4.md` (does layer 2's verdict teach layer 1).
- **What fits the base today [file]:** numbered weight sets saved from and loaded into the judge, a cross-index tying a set to a program slot (simulation only), the detector core's save-and-recall block with a best and second-best match (ran on the card in Oct), layer 2 history store (Tang), layer 3 (Python model only).
- **Proposed placement (Claude's proposal, untested):** teacher mode with known answers sets the baselines and is the only way sets enter the saved library; live mode adjusts a working copy only, in small bounded steps; a working copy is promoted to a saved set only after enough confirmed hits, the old set kept. Reason: a system that trusts its own correct guesses without limit can lock in a wrong habit. Learning stays on the host (training is hosted anyway); the card judges.
- **"Fit" measure [open]:** with a teacher, agreement of the judge's decisions with the right answers; without one, only a weak proxy such as the gap between the two class scores. "Common weights" is meaningful only between sets of the same layout (same sensors, same class meanings).

## 9. The question that follows: scale (Alan, 7 Nov 21:39; to be taken up once the model above is more settled)
Can it be scaled, and if so how and where? Not answered here. Figures already in the files, to start from (all as recorded, none re-measured today): about 450 LUT per extra detector and about 10,100 LUT for hex19 with one cell, 128 cells placed at 73 MHz (nextpnr estimate, not run on the card) [file, Oct]; eight parallel banks about 68,000 LUT by arithmetic against 298,600 on the chip [arith, 5 Nov]; the JTAG bridge about 5,500 scans per second, per-scan cost dominating, the card's PCIe link dead [card, 5 Nov and Oct]; the weight store 512 words per set in a 2,048-word block RAM [file]. Questions to settle then: what scales (detectors, sensors, stored sets, programs), where the limit sits (logic, memory, the JTAG link, the host), and whether it scales inside one card, across cards, or in the host.

## 10. Training scheme: settled in principle (Alan, 7 Nov 21:49: "that's fine, it follows established methods used today in the training of AI systems")
Settled before the neural cell design so the training is not redone if the cell changes. The scheme is separate from whatever cell runs the weights.
- **Input [file/card]:** the eight class bins per word from the layer 1 detector (card-proven, v2 and v9).
- **Output:** a numbered weight set in the batch judge's layout (512 words per set in the weight store [file]). A neural cell would load its own layout; the library, the search and the teacher/live rules stay the same.
- **Who trains:** the host. The card only judges [Alan, 5 Nov].
- **Teacher mode:** known answers set the baselines and are the only way a set enters the saved library [agreed].
- **Live mode:** adjusts a working copy only, in small bounded steps; promoted to a saved set after enough confirmed hits, old set kept [agreed]. The number for "confirmed hits" is [open], to be set when built.
- **Fuzzy search:** compares only sets of the same layout (same sensors, same class meanings) [Claude's proposal, accepted with the above; not separately ruled].
- **[open] Where the first right answers come from:** recorded runs with known outcomes, a hand-written rule, or the next observation only. Alan has not ruled; this decides what "fit" means.
- **Next build step:** train real weights from recorded detector classes in place of the random weights used in the end-to-end test. Neural cell design comes after.

## 11. The first right answers, and the test this is (Alan, 7 Nov 21:51)
- **Source of the first answers [Alan]:** the initial teaching system supplies a fairly broad set of data with known answers.
- **Then [Alan]:** the system's own feedback has to modify what the teacher gave it. This is a testing design: can the system, by itself, get to a similar point as the teacher-trained model?
- **So there are two judges to compare [Claude's reading of the above]:** (A) the reference, trained by the teacher only; (B) the same starting weights, then modified only by the system's own feedback (prediction against the next observation). The question is how close B ends up to A.
- **Consistent with section 10:** the teacher sets the baseline; B changes a working copy, never the saved teacher set, so A stays as the yardstick.
- **Possible data source [file]:** `make_data` in `tools/hexn_kxlayer1_judge_v1.py` makes words with known answers, with adjustable noise and dwell. Whether it is broad enough to be the teaching system is [open].
- **[open] What "a similar point" means:** a measure is needed before the test (for example agreement of B's decisions with A's, and with the known answers, on data neither saw). Also open: how broad the teacher's data is, how much the system may move the weights, and how long B runs.

## 12. Experiment design v0 (Alan, 7 Nov 21:54: "that's the start"; an experiment, to test and hone the real design)
Claude's first answers, accepted as the starting point. All are expected to change after the first runs.
1. **Closeness:** held-out words neither judge trained on. Score A (teacher only) and B (teacher start, then self-feedback) on: match to the known answer, agreement of B with A, and the two class scores word by word. "Similar" = B's accuracy within a margin of A's; margin chosen after seeing A's first result.
2. **Teacher data:** the existing generator (`make_data`) at several noise and dwell settings. Real recorded data later.
3. **Step limit:** B moves each weight one small step at a time with a ceiling on drift from the teacher value; both numbers set by early runs.
4. **Run length:** fixed number of words, compared with A at regular points to show converge, stall or drift.
Host side, simulation only; no card until the method shows something.

## 13. Experiment v0, first run (7 Nov 22:15; simulation, one seed, one run: a first look, not a result)
Tool: `tools/hexn_selftrain_v1.py` (3 tests pass). Task assumed by the tool, not ruled by Alan: predict an event in the next word (at least 4 of the 8 sensors in class 4 or above) from the detector's classes now; dwell 6 so the next word is partly predictable. Teacher data: noise 0.05, 0.10, 0.15; live and held-out data: noise 0.20 (shifted, so the live feedback has something to adapt to). Step 1, ceiling 24, 3,000 live words.
- A (teacher only): held-out accuracy 0.713 (training 0.795); the event is present 0.539 of the time, so A is only moderately above guessing the common answer.
- The self label (event read from the detector's classes) agrees with the true event 0.810 of the time, so B learns from labels that are wrong about one time in five.
- B (teacher start, self feedback): accuracy 0.673, 0.654, 0.701, 0.710, 0.716 at 500 to 2,500 words; agreement with A 0.89 falling to 0.82; reached the 24 ceiling by 1,000 words. It dipped early, recovered to A's level, and did not beat A.
- C (control, from zero, self labels only): accuracy 0.42 to 0.57, near the common-answer rate; did not get there in 3,000 words at this step.
- Reading: with a teacher start, self feedback holds A's level on shifted data but shows no gain here; with no teacher it did not get there. Not settled: one seed, one setting, a task with a modest ceiling, and the early dip needs explaining.

## 14. Improving the self feedback (Alan 7 Nov 21:58: "is there anything we can change in that?"; simulation, 5 seeds)
Cause found in the first run: the self label is wrong about one time in five, and plain B corrected itself on every mismatch, so it chased the detector's errors. Over five seeds plain B finishes on average 0.028 BELOW A (per seed -0.023, -0.048, +0.003, -0.023, -0.048); the single-seed first look (section 13) hid that it is a mild loss.
Change tried: update only when the self label is certain, using only what the system itself sees. A word's label counts as certain only if it would be the same whether each "no class" sensor were high or low (`confident` in the tool). Results, final accuracy minus A, mean of 5 seeds (3,000 live words, step 1):
- plain -0.028; batch of 10 corrections -0.022 (a delay, not a real vote; little help)
- certain labels only **+0.039** (every seed positive: +0.045 +0.025 +0.058 +0.042 +0.023); worst checkpoint +0.006 above A
- certain labels + batch 10: +0.034; certain labels + ceiling 8: +0.019 (a tighter ceiling holds it back)
Caveats: six variants were tried and the best reported; same detector templates in every seed; shifted-noise data only; one task. The gain is modest (about 4 points). Not yet tried: lower step, longer runs, other noise levels, labels needing agreement across words.

## 15. Self feedback: the untried changes, tried (Alan 7 Nov 22:08; simulation, 5 seeds each, noise 0.20 unless stated)
Figures are final accuracy minus A (teacher only), mean of 5 seeds. Note: "final" is the last checkpoint reached (about 2,000 words for the 3,000-word runs), so these sit a little below section 14's 2,500-word figures (+0.039 there, +0.031 here for the same setting).
- Certain-labels-only (the section 14 filter): +0.031; plain: -0.027. Still the main gain.
- Lower effective rate (a weight moves only after 2 or 4 net votes): +0.022, +0.014. Worse. The system is under-adapting, not over-adapting.
- Larger step 2: +0.020 (one seed -0.042). Drift ceiling 48: +0.030, no change from 24.
- Longer run, 9,000 words: certain-labels +0.034 (seeds +0.030 +0.047 +0.042 +0.053 +0.000); plain -0.028. The gain does not grow with length.
- Noise: at 0.10 certain-labels +0.054 (plain +0.024); at 0.30 certain-labels +0.034 (plain -0.008). Teacher-only accuracy there 0.765 and 0.595.
- Hold counter (layer 1) in the judge's inputs: teacher-only accuracy falls from 0.718 to 0.647 (hold 2) and 0.610 (hold 3), because held classes drop out as "no class" at this noise; self feedback adds +0.008 and +0.016 on those lower bases. Plain self feedback with hold 3 is -0.053.
- Hold counter on the labels only (inputs unheld): +0.012 (hold 2), +0.003 (hold 3). Worse than the certain-labels rule alone.
Reading: one change works, update only on certain labels, and it works at every noise level tried, with a modest gain (about 3 to 5 points). Nothing else tried added to it. The gain stops at about 4 points because the self label comes from the same detector the judge reads, so it cannot correct the detector's own errors. Open: a second source of evidence for the label (layer 2 history, or two sensors agreeing) is the next candidate; the hold counter as built does not provide it at this noise. Alan's note (22:08): the judge may need some of what was developed in the layer system; consistent with this, but only the hold counter has been tried so far.

## 16. Layer 2 as a second source of evidence: first try (Alan 7 Nov 22:36; simulation, 5 seeds, noise 0.20, ~2,000 live words)
Alan's point: each layer reached a certain point and plateaued by design; the improvement is in stacking them. Tried a layer 2 STAND-IN (`layer2` in the tool; per-sensor history of which class follows which, learned online from the detected stream, no teacher; a class is "ok" when it matches the prediction). It models the idea only, not the Tang store v5 (dense heap, context lengths). Two uses:
- **Labels** (unreliable classes become "unknown" for the certain-labels rule): B minus A +0.013, below the certain-labels rule alone (+0.031). Too many real changes are marked unknown.
- **Inputs** (a class that contradicts the history is replaced by the prediction, before the judge sees it): the teacher-only judge A falls from 0.718 to 0.673, plain self feedback -0.023; with certain labels B ends 0.735 (+0.062 over this lower A). In absolute accuracy that is below certain labels alone (0.749). Both together: 0.705.
- Reading: as modelled here, layer 2 does not add on top of certain-labels-only. The relative gain looks bigger only because A starts lower. I should not call it a layer 2 result: the stand-in is crude (it predicts mostly "same class again", which the judge's inputs already carry at dwell 6).
- Not tried: using layer 2's PREDICTED next classes as an extra input to the judge for the next-word event (the layer's real job); a longer context; the real store's verdicts; layer 3 across sensors (MODEL only). The test data has no structure across sensors or sequences beyond persistence, so history has little to find; data with real sequences is the fairer test of layer 2.
