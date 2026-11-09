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

## 17. Layer 2's prediction as a judge input, on data with sequences (Alan 7 Nov 23:04; simulation, 5 seeds, noise 0.20, certain-labels rule on)
Data now has sequences: when a sensor changes class it goes to a fixed successor 90% of the time (`--seq 0.9`). The layer 2 stand-in now PREDICTS (`l2_next`): per sensor, from the current class and how long it has lasted, it learns online which class follows, from the detected stream only. Two ways in to the judge: `replace` (the predicted next class takes the sensor's slot; judge layout unchanged) and `both` (current and predicted, 16 slots; the present scorer has 8, so this would be a new layout).
Final accuracy, mean of 5 seeds (B minus its own A in brackets):
- Sequence data, certain labels, no layer 2: B 0.742 (+0.058); replace: 0.743 (+0.058); both: 0.746 (+0.053).
- No-sequence data: certain labels 0.749 (+0.031); with `both` 0.753 (+0.034). Repeat check of the earlier +0.031 reproduces.
Reading: layer 2's prediction adds nothing measurable here (differences of 0.001 to 0.004 are inside the seed spread).
Why, measured on the same data (3 seeds, 3,000 words, dwell 6): the next word's event equals the present word's event 89% of the time when read from the TRUE classes, but only 70% when read from the DETECTED classes at noise 0.2 (83% at noise 0.1). So only about 11% of events change from one word to the next (little for history to predict), while the gap between 0.89 and what the judge reaches (about 0.72 to 0.75) is mostly the layer 1 detector's errors in the current word. On this task the headroom is in cleaning the present classes, not in predicting the next one.
Tried so far for cleaning: the hold counter (inputs; hurt, section 15) and layer 2 "fill" (hurt, section 16). Not tried: a vote over the last few words (majority, not "n identical in a row"), which keeps a class where a strict hold drops it. Also not tried: data where the sequence itself carries the event (for example an event that follows a particular pair of classes), which is where predicting should count.
Caveats: stand-in layer 2 (order-1 with age), one task, event timing random in the test data.

## 18. Cleaning the present classes: majority vote, carry-forward, and the real hold counter (Alan 7 Nov 23:16; simulation, 8 seeds paired, noise 0.20, certain-labels rule on, ~2,000 live words)
All figures: final accuracy on unseen words. Baseline = certain labels alone: A (teacher only) 0.706, B 0.745.
- **Majority vote over the last n words** (tie goes to the present word's class if it leads, else the most recent; "no class" abstains), on inputs and labels, B minus baseline: n=2 +0.050 (B 0.794, every seed positive); n=3 +0.020 (B 0.764); n=4 +0.016 (0.761). On the 5-seed run, inputs only: A falls with n (0.692, 0.671, 0.646, 0.609, 0.582 for n=3 to 7), and B ends 0.758, 0.733, 0.706, 0.670, 0.640. Longer windows lag behind real changes (dwell is 6 to 12 words).
- **Odd versus even (Alan's note):** odd did better in the pairs compared (3 over 4, 5 over 6 in B), but longer windows are also worse, so the two effects are mixed; the clean comparison would need the same effective lag. Not shown either way.
- **What n=2 really is:** with two words the vote only acts when the present word is "no class": it uses the previous word's class. That is carry-forward by one word, and it is where the whole gain comes from (the code test `majority(det,2) == carry(det,1)` holds for the filled words).
- **Carry-forward** (`carry`: where the detector gives no class, repeat that sensor's last class if seen at most k words ago; a class the detector did give is never changed), certain labels on, B minus baseline: k=1 +0.050 (A 0.746, B 0.794), k=2 +0.047, **k=3 +0.054 (A 0.754, B 0.799)**, k=6 +0.048. Inputs only (k=2) +0.044 (B 0.789). Insensitive to k from 1 to 6. It raises the teacher-only judge A as well (0.706 to about 0.75). Adding a 3-word vote on top hurts (+0.009, B 0.754).
- **The real layer 1 hold counter, modelled as built** (`hold_real`, using `hold_ref`, the reference the v9 core was checked against on the card: the held class stays until a different value, or "no class", has been seen n words in a row), inputs and labels, B minus baseline: n=2 -0.023 (A 0.641, B 0.722); n=3 -0.101; n=4 -0.154; n=5 -0.191 (A 0.500, B 0.554). Inputs only n=3: -0.144. It makes things clearly worse here, more so as n grows. Likely cause (a reading, not verified here): it also holds on to wrong classes and takes n words to follow a real change, against dwell 6 to 12, while carry-forward only fills the gaps and passes every given class straight through.
- **CORRECTION to section 15:** the "hold counter" tried there was `hold_det`, which blanks a class until it has been seen n times in a row. That is not how the built hold counter behaves, so section 15's hold figures do not describe the real one. Section 18's `hold_real` is the real behaviour and also hurts, for the reasons above; the conclusion that the hold counter does not help on this task stands, but it now rests on the right model.
- Reading: the one cleaning step that helps is the cheap one, carry the last class over short "no class" gaps (about +5 points, on top of the +3 to +4 from certain labels). The hold counter as built would not give that gain on this task. Caveats: one task, test data (persistence with random timing), noise 0.2 only, carry-forward is a host-side model and not in any RTL; whether the card's detector produces "no class" as often as this test's does is not checked. The v9 detector gave 82.8% match to its model on the card at dwell 6 [card, Nov 6].

## 19. Carry-forward applied in the detector-to-judge tool, and tested (Alan 8 Nov 00:13: "apply and test the carry forward")
- **Applied:** `tools/hexn_kxlayer1_judge_v2.py`, a clone of the card-proven v1 (v1 untouched, per the clone-and-increment rule) with `--carry K` (off by default) and `--noise`. The detector phase and the saved classes file are unchanged; carry-forward is applied on the host at the judge stage, filling a sensor's "no class" with its last class if seen at most K words ago. Host side only; nothing in RTL, nothing needs a new bitstream.
- **Tests:** 3 in `tests/vm/test_hexn_kxlayer1_judge_v2.py`, all pass. Two fast (v2 gives the same data, weights and reference results as v1; carry changes only the no-class slots and the word the judge sees). One slow end to end in simulation (detector in iverilog behind the JTAG bridge, base with the judge): 4 words, dwell 6, noise 0.30, carry 3: 0 differ from the model, 5 no-class slots filled, 3 still empty, 4 words scored, 0 differ from the reference, PASS. That shows the pipeline carries the filled classes through the real judge hardware model correctly; it is 4 words, so it is a plumbing check and not a measure of benefit.
- **How often there is no class [sim, model equal to the card's detector at 0 differ]:** noise 0.10 (the card run's setting): 6.9% no class, 0.8% wrong, 92.3% right (card v2 run: 93.8% right); noise 0.20: 21.2% no class, 6.6% wrong; noise 0.30: 42.6% no class, 15.4% wrong. So carry-forward has most to fill when the detector is noisy.
- **Benefit at the card's noise level [sim, 8 seeds paired, certain labels on]:** noise 0.10: teacher-only A 0.758 to 0.783, self-corrected B 0.820 to 0.861 (+0.041, sd 0.005, every seed positive, smallest +0.035). Together with section 18 (noise 0.20: +0.054) the gain holds at both noise levels.
- **Not done:** carry-forward on the card itself (the host step needs no card change, but the detector-to-judge run with `--carry` has not been run on the Kintex); training real judge weights with it in the loop; recorded real sensor data. Do not use `--carry` with `--dwell 1` (a new random class every step): it would only copy stale classes.

## 20. Carry-forward on the card (Alan 8 Nov 00:55 to 01:08)
Both phases ran on the Kintex card. Phase 1 (core v2 detector, hex7, dwell 6, noise 0.10, 40 words x 8 sensors): 0 differ from the detector model, 290 of 320 right (90.6%), 25 with no class. Phase 2 (base `arr_base_b3_noram`, `--carry 3`): all 25 no-class slots filled, 315 of 320 right (98.4%), judge 40 words 0 differ from the reference, 681 scans, 0 bad captures. Both numbers equal what the model predicted before the run [card, equal to sim].
Scope: the carry step is host-side; what the card shows is the real detector's classes and the real judge scoring the carried words correctly. The 7.8-point rise is on synthetic data where each class lasts 6 to 12 steps; whether real sensors persist like that is open. The self-teaching effect with carry-forward (section 18, +0.04 to +0.05) is simulation and has not been run on the card. The judge weights in this run are still the random test weights, not trained ones.
Next in line: train real judge weights from the (carried) classes with the teacher data, then run the teacher-versus-self experiment's winning settings (certain labels plus carry-forward) as the agreed method.

## 21. Carry-forward and the hold counter on the REAL recorded sensor data (Alan 8 Nov 01:09: "there was a record of real sensor data somewhere")
Found: `docs/hex-n/data/esp_run_20261027_*` (ESP32 at 200 per second: light lamp-on / light-off / daylight, pot sweep, thermistor finger and run 2, IR remote), already run through layer 1 in `tools/hexn_replay_v1.py` (27 Oct). New: `tools/hexn_replay_carry_v1.py` (reuses that replay unchanged, adds carry-forward and the built hold counter on each sensor's class stream; 3 tests pass). Python model only; K and N are in samples. Held-out part, 'no class' counted as wrong:
| stream | rule | right | no class | output changes (reference) | longest wrong run |
|---|---|---|---|---|---|
| light | none / carry 1 to 20 | 1.000 | 0% | 5 (5) | 0 |
| light | hold 3 / 10 / 20 | 0.994 / 0.973 / 0.943 | 0% | 5 | 2 / 9 / 19 |
| pot | none / carry 1 to 20 | 1.000 | 0% | 9 (9) | 0 |
| pot | hold 3 / 10 / 20 | 0.996 / 0.981 / 0.960 | 0% | 9 | 2 / 9 / 19 |
| thermistor raw | none / carry (any) | 0.954 | 0% | 186 (3) | 16 |
| thermistor raw | hold 3 / 10 / 20 | 0.961 / 0.977 / 1.000 | 0% | 22 / 8 / 3 | 44 / 30 / 0 |
| thermistor, 9-sample median | none / carry | 0.966 | 0% | 26 (3) | 42 |
| thermistor, 9-sample median | hold 3 / 10 / 20 | 0.967 / 0.978 / 0.985 | 0% | 16 / 8 / 5 | 42 |
Reading:
1. **Carry-forward does nothing on these three sensors** because the banks never answered "no class" on this data (0%). Their errors are chatter between valid neighbouring classes at the thermistor's band edges, which carry-forward does not touch.
2. **The built hold counter is the right tool for that**: on the thermistor it takes 186 output changes down to 3 (the real number) at N=20 (about 150 ms). On light and pot, which are already steady, it only adds delay and costs accuracy, so those two should use no hold (or 1 to 3). This matches the 27 Oct finding; here with the median-in-front shown worse than hold alone.
3. **So the two cleaners fix different faults.** Carry-forward fills gaps ("no class"); the hold counter removes chatter between classes. My synthetic test data had mostly gaps (and a large share of wrong classes at higher noise), which is why carry-forward won there and the hold counter lost; real analog sensors here show the opposite pattern. Section 18's conclusion that the hold counter "hurts" holds for that synthetic data, not for these recordings.
4. **Where "no class" does occur in the real recordings:** the IR remote with the exact-match bank (damaged frames answer "unknown"). The 27 Oct layer 2 row found "hold 1, ignoring unknown answers" the best there, which is carry-forward in effect. Not re-run here.
Caveats: the thermistor 1.000 at N=20 is partly an artefact (the three real changes lie in the training half, so the held-out half contains none; noted on 27 Oct); sensors were recorded separately; the light files are three steady recordings joined end to end; the pot reference is its own bands; the card's detector gave 5.3% "no class" on the synthetic 6 Nov data, so how often a real bank returns no class on live sensors is still unknown.
Consequence for the pipeline: do not apply one cleaner to all sensors. Per sensor: thermistor (slow continuous, band edges) gets hold about 20; light and pot get none; sensors whose bank can answer "no class" or "unknown" (IR exact-match; a noisy bank) get carry-forward. The `--carry` option of the judge tool is a per-run setting, not per sensor yet.

## 22. The cleaner belongs to the sensor type: part of the judge's set-up (Alan 8 Nov 01:27)
**Alan's design point:** per-sensor cleaning is important and is in part the judge's design: it matches data to known sensor types and loads the appropriate design for the input. That becomes part of the set-up. For unknown sensors the system can possibly try both options as part of its choice.
This is the same shape as the weight library (section 8): a library of known designs keyed by sensor type, a match, and a fallback search when nothing fits. Here the "design" is the sensor's cleaner (and, later, its coding and bank settings); today only the cleaner is modelled.
**Built (host side, model only; nothing on the card, no RTL):**
- `tools/hexn_sensor_profiles_v1.py`: cleaner specs `none`, `carryK`, `holdN`, chains like `carry3+hold10`; a table of known types from the recordings (light none, pot none, thermistor hold20, ir carry1 [ir taken from the 27 Oct layer 2 finding, not re-run]); `choose_taught` (known answers: best held-out accuracy, then fewer changes, then the lighter cleaner); `choose_blind` (no teacher; a PROPOSED rule, below); `clean_columns` (each sensor column by its own cleaner).
- `tools/hexn_kxlayer1_judge_v3.py` (clone of v2; v1 and v2 untouched): `--clean SPEC` = one cleaner for all sensors, eight comma-separated, `auto` (blind choice per sensor), or `known:type,...` (a type per sensor, `unknown` to choose blind). `--carry K` kept and means `--clean carryK`. Applied at the judge stage on the host, as in v2.
- Tests: `tests/vm/test_hexn_sensor_profiles_v1.py` (6), `tests/vm/test_hexn_kxlayer1_judge_v3.py` (2 fast + 1 slow end to end).
**Blind rule (proposed; for an unknown sensor, from its class stream alone):** (1) if at least 1% of steps have no class, start with carry3, else none; (2) a hold N (3, 10 or 20) is allowed only if at least half the steps lie in runs of at least 10 x N steps (the delay then costs at most a tenth of a run); (3) if the largest allowed hold removes at least half of the output changes, use the smallest allowed hold within 1.5 times those changes, else no hold.
**What it picks [model]:** on the real recordings: light none, pot none, thermistor raw hold20, thermistor with median hold20, equal to the known table. On the synthetic judge streams (classes last 6 to 12 steps): carry3 and no hold, at noise 0.10 / 0.20 / 0.30 and 40 or 400 words.
**Two earlier versions of the rule were wrong, kept here because they matter:** (a) with no run-length condition it chose carry3+hold10 or hold20 on the synthetic streams, where section 18 showed holds hurt: it was removing "chatter" by deleting real changes; (b) a version that measured run lengths after the hold still chose hold20 on 400-word synthetic streams, because a hold that never lets the class change makes long runs. The final version measures run lengths on the stream before the hold: synthetic 0.00 at every N, real light 1.00, pot 0.95 to 1.00, thermistor 0.76 to 0.98.
**Caveats:** the 1%, the half, the factor 10 and the 1.5 are guesses chosen with these streams in view; the separation (0.00 against 0.76 or more) is clean but rests on two kinds of stream only. The rule sees only the class stream, not what the sensor is. It has not been tried on IR frames, on noisier real sensors, or with a teacher present to check it. Whether a blind pick should instead try each candidate on the judge's own score (the "try both" idea, with the judge's answer as the test) is open and is the natural next experiment.
**Open:** how a sensor's type is known (declared in the set-up, or recognised from the signal: step sizes, rails, flicker); extending the profile to the coding (thresholds) and bank settings, not only the cleaner; per-sensor profiles for the eight judge slots in the final layout.

## 23. Try-both: the system chooses a design on blind data (Alan 8 Nov 16:27: "apply the try-both method first, the step to allowing the system to make choices on blind data"; simulation, 6 seeds per condition)
Tool: `tools/hexn_trycleaners_v1.py` (3 tests pass). Each candidate DESIGN = a cleaner plus judge weights taught (known answers) with that cleaner in front. All five are tried on the same unseen stream and the system keeps the best by a BLIND score: how often the design's prediction for word t agrees with the self label for word t, counted only where that label is certain. The self label is read from the RAW detected classes of word t+1 and is the same for every candidate (labelling from each candidate's own cleaned stream would let a long hold win by making the stream constant). The truth score (accuracy against the real event) is used only to check the choice. Candidates: none, carry3, hold3, carry3+hold3, hold10.
Results (truth accuracy of carry3 / none; blind pick; best by truth; regret = best truth accuracy minus the blind pick's, mean over seeds):
| classes last | noise | carry3 | none | blind pick | best by truth | per-seed picks matching | mean regret (max) |
|---|---|---|---|---|---|---|---|
| 6 to 12 | 0.10 | 0.783 | 0.773 | carry3 | carry3 | 6 of 6 | 0.000 (0.000) |
| 6 to 12 | 0.20 | 0.750 | 0.723 | carry3 | carry3 | 4 of 6 | 0.004 (0.015) |
| 6 to 12 | 0.30 | 0.665 | 0.625 | carry3 | carry3 | 4 of 6 | 0.011 (0.051) |
| 40 to 80 | 0.10 | 0.760 | 0.748 | carry3 | carry3 | 6 of 6 | 0.000 (0.000) |
| 40 to 80 | 0.20 | 0.736 | 0.712 | carry3 | carry3 | 5 of 6 | 0.001 (0.003) |
| 40 to 80 | 0.30 | 0.681 | 0.636 | carry3+hold3 | carry3 | 2 of 6 | 0.054 (0.108) |
Reading:
- Pooled over seeds, the blind pick equals the best by truth in 5 of 6 conditions; per seed, 27 of 36 picks match. Where it misses, the loss is small except in the noisiest, long-class condition (mean 0.054, worst seed 0.108).
- The blind score tracks the truth score closely (the two columns rise and fall together), so the "agree with your own certain labels" test is a usable signal for choosing a design.
- Holds (hold3, hold10) lose in every condition here, including with long-lasting classes: this synthetic detector's errors are mostly "no class" gaps, which carry-forward fixes and a hold does not. So this test never has a case where the right answer is a hold. It shows the choice works when carry-forward is the answer; it does NOT show it would pick a hold when a hold is right (the real thermistor, section 21). That needs a stream with chatter between valid classes.
- At high noise the blind score tilts toward the hold designs (it rewards agreement with a noisy raw-derived label, and a hold stabilises the cleaned input), which is the likely cause of the one bad condition; not isolated.
Open: a test stream where a hold is the right answer (edge chatter like the thermistor) to check the system picks it; fewer than 6 seeds per condition is thin; the five candidates are my list; the cost of trying every design (weights per cleaner stored in the library) is not counted; how the choice is made when several sensors are unknown at once (jointly, or one at a time).

## 24. Try-both where a hold is the right answer: the real thermistor (Alan 8 Nov 16:43; model only, single-sensor streams)
**Alan's question: "the feedback comes from the design picked, is that correct?"** Answer, as built: in the CHOOSING step, no. The self label there is read from the RAW detected classes and is the same for every candidate (section 23), because a label taken from each candidate's own cleaned stream lets a long hold win by making the stream constant. AFTER a design is chosen, yes: the running self-teaching loop (sections 14 and 18) takes its labels from the chosen design's own cleaned stream, with the certain-labels rule. So the picked design supplies the feedback when it runs; it does not mark its own homework when it is being chosen. Possible middle option, not tried: label from one fixed reference cleaner (for example carry3) for every candidate.
Tool: `tools/hexn_trychatter_v1.py` (3 tests pass). Candidates are cleaners only (none, carry3, hold3, hold10, hold20, carry3+hold10, carry3+hold20). Streams: real light, pot, thermistor raw and thermistor with 9-sample median (27 Oct recordings), plus one synthetic sensor (classes last 6 to 12 steps; noise 0.10, 0.20, 0.30). Blind scores, none uses the reference: AGREE (cleaned class at t equals the raw class at t+1); COST(c) = c x output changes + steps where the cleaned class differs from a given raw class.
Picks (best by truth | AGREE | COST c=1 | c=3 | c=10 | GUARD+c=10):
- light: none | none | none | none | none | none
- pot: none | none | none | none | none | none
- thermistor raw: hold20 | hold3 | hold3 | hold3 | **hold20** | **hold20**
- thermistor median: hold20 | none | none | none | hold10 | hold10
- synthetic 0.10: carry3 | carry3 | carry3 | carry3 | **hold20 (truth 0.193)** | carry3
- synthetic 0.20: carry3 | carry3 | carry3 | **hold10 (0.193)** | **hold10** | carry3
- synthetic 0.30: carry3 | carry3 | carry3 | **carry3+hold10 (0.062)** | **carry3+hold10** | carry3
Reading:
1. **AGREE cannot see chatter.** On the thermistor it prefers the lightly held or the unheld stream (a stream that copies the raw one agrees best with the raw one). It is right where carry-forward is the answer, and wrong where a hold is.
2. **COST works for the thermistor only at a high price per change (c=10), and then it picks long holds on the synthetic streams, where they are disastrous (truth 0.19 to 0.06): it removes "chatter" by deleting real changes.** No single c is right for both kinds of stream.
3. **COST with the run-length guard (a hold is allowed only if at least half the steps lie in runs of 10 x N or more) picks the right kind of cleaner on all seven streams:** none for light and pot, hold20 for the raw thermistor (truth 1.000), hold10 for the median-filtered thermistor (truth 0.978; best was hold20 at 0.985), carry3 for all three synthetic noise levels.
4. So a blind try-both CAN pick a hold when a hold is right, but only with the guard; the guard is the same condition that was found necessary for the profile rule (section 22). The system must know how long a class normally lasts compared with the hold it is testing.
**Caveats:** the guard and c=10 were fixed after seeing the cost-only failures, with these seven streams in view, so this is a fit to them and not an independent test; seven streams, two kinds of fault; the thermistor's 1.000 at hold20 is partly an artefact (the three real changes lie in the training half); no judge in this test (cleaner only), so it does not combine with the weight-taught candidate designs of section 23; the guard's half and the factor 10 are guesses.
**Next:** put the guard and the cost into the weight-taught try-both (section 23) and test on a mixed set of sensors (some needing carry, some a hold); fresh recordings of other sensors would be the independent test.

## 25. Per-sensor try-both in the judge, on a mixed set of sensors (Alan 8 Nov 16:57: "process that side first"; simulation, 5 seeds, noise 0.20)
Tool: `tools/hexn_mixedsensors_v1.py` (2 tests pass). Eight sensors for the judge: sensors 0 to 3 are GAP sensors (the detector's raw answers: "no class" gaps and some wrong classes; carry-forward is the right fix); sensors 4 to 7 are CHATTER sensors (never "no class"; flip between the old and new class for 8 steps either side of every real change, plus 1% single-step wrong classes; a hold is the right fix, as with the real thermistor). Classes last 100 to 200 steps. Each strategy gives one cleaner per sensor; the judge weights are taught (known answers, 1,500-word teacher streams) with those cleaners in front; all are scored on a separate held-out stream (2,500 words).
**First run discarded (flaw, kept on record):** it scored every strategy on the same stream on which the "blind judge" strategy had chosen its cleaners and weights, and used 400-word teacher streams with few class changes. "Blind judge" then looked best (0.80 against 0.67 for no cleaning) because it was selecting on the test stream. The tool now scores on a held-out stream. Those first figures are not results.
**Judge accuracy on the held-out stream, mean of 5 seeds (min / max):**
- no cleaner 0.779 (0.728 / 0.844); carry3 on every sensor 0.793 (0.743 / 0.873); hold10 on every sensor 0.619 (0.531 / 0.741)
- **oracle** (per sensor, the cleaner with the best single-sensor accuracy against the true classes) 0.795 (0.737 / 0.860)
- **blind cost** (per sensor, from its own raw stream: cost c = 10 among the cleaners the run-length guard allows, section 24) **0.793** (0.757 / 0.882)
- **blind judge** (each cleaner tried with its own taught weights, scored by agreement with a self label read from the raw classes, one pass over the sensors) 0.755 (0.709 / 0.798)
**Picks:** blind cost gave carry3 only to all 20 of the gap sensor cases and a hold to all 20 of the chatter sensor cases (the right kind every time; the oracle gave carry3 only to 8 of 20 gap cases and a hold to 19 of 20 chatter cases). Blind judge gave carry3 only to 5 of 20 and a hold to 3 of 20.
**Reading:**
1. **The blind cost-plus-guard rule works as a per-sensor chooser:** it matches the oracle (0.793 against 0.795) and picks the right kind of cleaner on every sensor. This is the first evidence that a per-sensor profile can be chosen on blind data and holds up in the judge.
2. **It gains nothing over simply carrying forward everywhere (0.793) in this set.** The chatter sensors are noisy only near class changes, which are rare when classes last 100 to 200 steps, so cleaning them barely moves the judge. The oracle ties it too. The benefit of a per-sensor hold would show where chatter is a larger share of the stream (the real thermistor).
3. **The weight-taught blind judge choice failed here** (0.755, below no cleaning at 0.779). Likely cause (a reading, not verified): agreement with a label read from the raw classes rewards copying the noisy raw input, as the agreement score did on the single thermistor stream (section 24). So the cost-plus-guard rule, not the judge-agreement score, is the one to build on.
4. **A hold of 10 on every sensor is clearly harmful (0.619).** Reason (not verified): the built hold counter changes only after N identical answers in a row; at noise 0.20 about 28% of the answers are "no class" or wrong, so ten in a row of the new class is rare and the held class stays on the old one after a real change. So the hold counter's usefulness depends on how reliable the bank is, not only on how long classes last; the run-length guard does not check for this.
**Caveats:** one noise level (0.20), 5 seeds; the chatter and gap sensor kinds are my construction; the guard and c = 10 were fixed in section 24 with other streams in view; per-sensor choices were made one sensor at a time with the others fixed (blind judge) or independently (cost); not on the card.
**Next:** a guard for hold reliability (how often the bank gives the same answer N times in a row); chatter that is a bigger share of the stream; fresh recordings of other sensors as the independent test.

## 26. The hold reliability check: not needed, the run-length guard already covers it (Alan 8 Nov 18:14: "carry on"; simulation, 3 seeds, noise 0.20)
Section 25 suggested a new guard so the system would not pick a hold on a sensor whose answers are too unreliable for the hold to follow a real change. Checked before building it.
**Cause of the harmful hold (section 25, point 4) verified.** On the gap sensors, counting real class changes after which the cleaned class equals the new true class at some step within 30 steps: no cleaner 97 of 98 (99%), carry3 97 of 98 (99%), hold3 92 of 98 (94%), carry3+hold10 87 of 98 (89%), **hold10 38 of 98 (39%)**. A hold of 10 on a stream with about 28% "no class" or wrong answers rarely sees ten identical new answers in a row, so it stays on the old class.
**The existing guard (section 22 and 24: a hold N is allowed only if at least half the steps lie in runs of at least 10 x N identical answers, measured before the hold) already blocks it.** Share of sensor streams on which it allows a cleaner: gap sensors: none 1.00, carry3 1.00, hold3 0.00, hold10 0.00, carry3+hold10 0.00; chatter sensors: none 1.00, carry3 1.00, hold3 1.00, hold10 0.58, carry3+hold10 0.58. A stream too unreliable for a hold to follow cannot have long runs of identical answers, so the run test is the stronger condition and includes reliability. The harmful "hold10 on every sensor" of section 25 was a fixed strategy that bypassed the guard; the rule itself never chose it. No new check built. Test added (gap sensors: holds blocked, carry allowed; chatter sensors: hold3 allowed).
**Caveat:** hold10 is allowed on only 58% of the chatter streams, close to the 0.5 line, so the guard's half is doing real work there and is a guess; and these are my constructed sensors.

## 27. The neural cell: Alan's notes on how a real neuron works (Alan 8 Nov 18:22; IDEAS, nothing built; the design is "a bit more radical" and will be tuned when we get to it)
**Alan's notes [Alan]:** a real neural cell is not simple. The connections in and out can number in the thousands. The outputs can be modified by exciters and inhibiters, or both. Some are slow acting, others fast. There are a lot of variables. There can even be a difference between the in side and the out side, the dendrites and the axons.
**General biology behind that, from Claude's general knowledge and NOT checked against a source here:** a cortical neuron receives of the order of thousands of synapses (some cell types far more); a synapse is mostly excitatory or inhibitory, set by the transmitter the sending cell uses; fast synaptic receptors act in milliseconds, slower ones (and modulator chemicals such as dopamine or serotonin) act over hundreds of milliseconds to seconds and change how strongly other inputs count rather than adding to the sum; synaptic strengths change with use, over short times (facilitation, depression) and long times (learning); dendrites do some processing of their own, in local branches, before the cell body sums the result; the axon carries the output spike and can send it to many targets, each with its own strength.
**First sort of the variables against the Hex-N design (a proposal to react to, not a decision):**
| Real-neuron feature | What it does for the computation | In Hex-N today | Candidate |
|---|---|---|---|
| Thousands of inputs and outputs | Fan-in and fan-out far beyond six faces | Six faces with lanes [file]; the detector counts up to 18 wires per bank [file] | Weights held in memory instead of wires; links the scale question (section 9) |
| Exciting, inhibiting, off | Signed contribution of each input | Lane weights +1, -1 or off in the layer 1 detector [file]; signed weights in the batch judge [file] | Already there for the detector and judge |
| Fast and slow acting | Different time constants on the same input | A hold counter and a leak-or-clear choice, the latter an open decision [file] | Two accumulators with different leak, or a slow trace beside the fast sum |
| Modulators that scale other inputs | A gain on the sum, not another term in it | Nothing | A modulation input that multiplies or shifts the threshold; perhaps the strategist layer's job |
| Strengths that change with use | Learning, short and long | Weights loaded from the host; self-teaching loop in simulation only (sections 8 to 18) | Short-term trace on the cell, long-term weights kept on the host (as agreed) |
| Dendrite versus axon difference | Input side groups and nonlinearity; output side fan-out with per-target strength | Faces do not talk to each other (open decision, `HEXN_DESIGN.md` 2a) | Input groups with a local sum before the cell total; per-target output weight |
**Points to settle when we get there [open]:** which of these change what the system can compute, and which are biological detail to leave out; whether the cell keeps one weight set format so the training scheme (section 10) is not redone; how many connections per cell and where their weights live; whether time constants belong in the cell or in the layer structure above it.

## 28. Fire level, leak, and the weight on each connection (Alan 8 Nov 18:27; IDEAS, nothing built)
**Alan's points [Alan]:**
1. **Fire level and leak are settled in his mind:** an accumulator reaches a point and the cell triggers; the leak simply lowers the value over time. Easy. (This is the sum, threshold and graded burst of section 1; the leak-or-clear choice stays on the open list of section 5 until he rules.)
2. **Inputs and outputs are limited,** which is why the earlier question mattered: are the values binary or actual values? If binary, an input has to be a collection of wires; if a value, it is one value per channel.
3. **How much actually gets passed in** is affected by the output of the cell before. The cell before has to fire (that works); but each OUT has its own set of weights, so every receiving cell gets the signal modified, per out.
**What the files already say about 2 [file]:** layer 1 inputs are single-bit wires (a 12-bit reading is coded onto several on/off wires, `tools/hexn_encode_v1.py`), so a value reaches the detector as a collection of bits. The detector's OUTPUT is already a graded value: a class number and a burst of 0 to 7 clocks (`LAYER_INTERFACES_v4.md`), i.e. a count of pulses on one wire.
**Reading of 3, for Alan to confirm [Claude's reading]:** the weight belongs to the CONNECTION (sender to receiver), not to the cell. One sender's output reaches many receivers; each receiver multiplies what arrives by its own weight for that sender before adding it to its accumulator. Seen from the sender that is "a different weight per out"; seen from the receiver it is "a weight per input". They are the same table, stored at either end. This is what the files already have: the detector's lane weights (+1, -1, off) and the batch judge's weight table indexed by sensor and class bin. What would be new is the sender's output being a graded value that the weight scales.
**Design consequences if that reading holds [proposals, untested]:**
- **Storage:** the connection table is senders x receivers weights; with thousands of connections it lives in memory and lists only the non-zero entries, not in wires. Links to the scale question (section 9) and to the weight library (section 8): a weight set is a table of connections.
- **Values on few wires:** a graded value sent as a pulse count over time on one wire (as the detector's burst already does) trades time for wires, so the number of in and out points need not grow with the number of connections; the receiver turns the pulse count times the weight into a number added to the accumulator.
- **Modulation falls out of the same picture:** a connection whose weight is itself set by another cell's output (a product of two signals) is the modulator of section 27; it needs no extra kind of cell, only a second signal reaching the weight.
- **Training scheme unchanged:** a weight set stays a table of numbers per connection, so the teacher/live rules and the weight library of sections 8 to 10 apply as agreed.
**Open:** is the sender's output a graded value, or fire / no fire only? Weight at the receiver (natural for summing) or per sender-receiver pair stored with the sender? How many connections per cell and how the pulse count is windowed? How time constants (the leak) interact with a pulse count that arrives over several clocks?

## 29. A frequency-and-level signal instead of discrete pulses (Alan 8 Nov 18:31; IDEA, nothing built; "radical")
**Alan's idea [Alan]:** so far the cells use discrete pulses. Can the FPGA make an FM-type signal to carry the data, with the receiver able to damp or amplify it? It would be digital, but the information would be in the frequency and the level (amplitude), giving two levels of modification.
**Claude's reading, in plain terms [proposal, untested]:** yes, an FPGA can produce it, as a digital stream, in either of two forms.
- **Pulse spacing and count (cheap, close to what exists):** the detector's burst of 0 to 7 clocks already carries a count; adding a chosen spacing between pulses gives a second number on the same wire. The receiver measures both: count (the "level") and spacing (the "frequency").
- **A true multi-bit waveform (costly):** a counter-driven oscillator at a chosen rate, multiplied by a level number each clock, giving samples; the receiver filters for a rate and multiplies by its own gain.
**What the two levels of modification would mean:** (1) gain: the receiver damps or amplifies the level by its weight, which is the weight-on-the-connection of section 28; (2) tuning: the receiver accepts only a band of frequencies, so several senders can share one wire and each receiver picks its own. That second one is new, and it speaks to the limited-in-and-out-points problem: connections separated by frequency instead of by separate wires.
**Honest limits [reasoned, not measured here]:**
- Sharing a wire by frequency does not create capacity. A wire clocked at rate f can carry a limited amount of information per window; separating senders by frequency or by time slot costs about the same. Frequency tuning is attractive for how the receiver picks its inputs, not because it carries more.
- In real hardware (and in a real neuron's dendrite) many signals add on a wire for free. On an FPGA they do not: every addition is an adder or a counter, and a shared digital wire cannot add, only combine. So the sum of many frequency-tagged signals needs real logic per receiver.
- To tell M frequencies apart a receiver needs a window of at least about M clocks, which adds delay.
**Link to biology (general knowledge, not checked against a source):** neurons do carry intensity as a firing rate, synaptic strength scales what arrives, and some neurons respond preferentially to input at certain rhythms (resonator, or resonate-and-fire, models are a known class). So frequency and level as two controls is not alien to the thing being copied.
**Open:** is the second control wanted for selection (tuning), for carrying a second number, or both? Cheapest first test would be in simulation: one shared wire, a few senders at different pulse spacings and counts, receivers with a gain and a tuned band; measure how many senders can be told apart and what the receiver costs in logic. Not started; Alan to say whether to.

## 30. The idea in logic terms: a cell id on a shared bus (Alan 8 Nov 18:35; IDEA, nothing built)
**Alan's restatement [Alan]:** in logic terms the frequency idea is a cell id, but a shared one. A packet with an id runs down a single bus; each cell with the matching id picks it up and acts on it. Still digital, but shared. The receiving cell says "I have this data, I will only take in 50% of its value into the accumulator system".
**Claude's reading [proposal, untested]:** this is the right digital form of section 29 and it keeps both of his controls:
- **Level** = the value carried in the packet (instead of a pulse count).
- **Frequency** = how often packets with that id are sent (the rate).
- **Tuning** = the id match: a receiver takes only the ids it has an entry for.
- **Gain** = the receiver's weight for that id, applied before the value goes into the accumulator ("50%" is a weight of 0.5, a shift by one bit; a weight of a power of two needs no multiplier; other weights need a multiplier or shift-and-add).
**Known practice (general knowledge, not checked against a source here):** sending spikes as address packets over a shared bus is the standard way neuromorphic chips do it (address-event representation); two common layouts are broadcast-and-match (every cell sees every packet) and a routing table that looks up a sender and delivers to its list of receivers with their weights.
**What it means for this design:**
- It is the connection table of section 28 with a delivery mechanism: the table maps (sender id) to (weight) at the receiver, or (receiver, weight) at a router.
- **Broadcast-and-match** is simple and local, but every cell checks every packet, so the cost is cells x packets; it suits a few hundred cells at a packet per clock, not thousands.
- **A routing table** needs memory but scales better and fits the "weights live in memory" proposal and the weight library (sections 8 and 10).
- **Limits:** one packet at a time on a bus, so a busy moment queues or drops packets (arbitration); timing is carried by arrival time instead of a pulse's place in the stream; the packet rate is a hard ceiling on events per second.
- The training scheme is unchanged (a weight set is still a table of numbers per connection), and the existing byte-command base controller already works in this style on the host side.
**Open:** broadcast-and-match or routing table? Is the weight allowed to be any number or only powers of two (cheap, and 1, 1/2, 1/4 is already close to the detector's +1, -1, off)? Signed (inhibitory) packets, or a sign in the weight? What happens when two packets arrive together? What is the id width, and how many ids per cell?

## 31. Layers of small buses, and the feedback matrix (Alan 8 Nov 18:39; IDEA, nothing built)
**Alan's picture [Alan]:** the output bus is a line linking cells; put 10 or 20 cells on that line, so a bus of multiple outputs is cheap; take the outputs of those cells and repeat. A single input creates a flow through, a map. Yes, only one packet is on the wire at a time, but once past the first layer there are 10 separate signals for the second layer, and so on. Then there is feedback: cross connections to other cells. One signal is not enough to fire a cell, it needs an accumulation. But the feedback matrix has to be fluid as well, and that is not easy.
**Claude's reading [proposals and reasoning, nothing measured]:**
- **Small buses fix the cost problem of broadcast-and-match (section 30).** A packet is only seen by the 10 to 20 cells on its own bus, so the matching cost is per bus, not cells x packets across the whole system. Many small buses run side by side, so total throughput is the number of buses times the packet rate of one. By arithmetic only: 1,000 cells in groups of 20 is 50 buses; at one packet per clock each, 50 events per clock in total.
- **Fan-out is cheap, fan-in is the limit.** On a broadcast bus every matching cell takes the same packet in the same clock, so one packet can update many accumulators at once; the limit is how many packets can arrive at one bus per clock (one).
- **Accumulation is what keeps the traffic sparse.** If one signal is not enough to fire a cell, a cell sends a packet only when its total crosses the threshold, so most of the time most buses are quiet. One packet at a time is workable because activity is sparse, as in the neuromorphic practice noted in section 30 (general knowledge, not checked here).
- **Where it can jam:** several cells on a bus firing in the same clock all want the next bus; that needs a small queue per bus (or accepting dropped packets). A cell whose output must reach several buses is sent as several packets.
- **It matches the layer structure we already have:** layer 1 (detectors), layer 2 (history), layer 3 (across sensors), layer 4 (strategist) with return paths (`LAYER_INTERFACES_v4.md`). In this picture each layer is a group of buses and cells; the feedback in that document would be packets sent back to an earlier layer's bus.
- **Feedback is the hard part, as Alan says.** Loops can run away or ring; stability needs the things the real cell has, a leak, a refractory period (a cell cannot fire again at once), and inhibitory connections. Training a feedback matrix that changes over time is much harder than the feedforward weight sets tested so far (sections 10 to 18, all feedforward and on a single judge). The agreed scheme can carry over (teacher sets a saved baseline; live adjustments are small and bounded within a drift ceiling of the saved set; promotion after confirmed hits), but that is untested for feedback.
**Open:** group size (10 to 20) and number of layers; queue depth per bus and what is dropped when full; refractory period and leak per cell; whether feedback packets share the forward buses or have their own; how a changing feedback matrix is kept stable and who is allowed to change it.
**A natural small test, if Alan wants it:** simulate three layers of leaky accumulating cells on small shared buses with queues; one input stream through; measure delay, dropped packets and how many cells fire; then add a feedback connection and see when it runs away. Not started.

## 32. The map the judge recalls, and the first bus-network simulation (8 Nov 2026)

**Alan's end model (18:43):** the pattern of activity as it runs through the layers is a *map*. The judge keeps maps and says "I have seen this before, this is the map, this is the result". Fuzzy: "I have seen something similar, it matches these two maps; let us see where they cross and extrapolate." Alan notes this is a leap ahead of where we are, and it is the end model, not the next step.

**What was built (toy, host-side Python, not hardware):** `tools/hexn_busnet_v1.py` with `tests/vm/test_hexn_busnet_v1.py` (4 tests). 3 layers, each 4 small buses of 16 cells (64 per layer); 48 input ids; each cell listens to 10 random sources with weight 1 or 2 (20% inhibitory); one packet per bus per clock, queue depth 8; accumulator, leak of 1 every 4 clocks, threshold 3, refractory 3 clocks. The tests first failed twice; both were test mistakes (the leak at clock 0, and a second random cell also listening to id 0), not the tool, and were fixed in the tests. The first run was too quiet (almost nothing reached layer 2), so threshold, leak and queue depth were swept once (k 10/16/24, threshold 3/4/6, leak 2/4/8) and a regime where activity flows through all three layers was chosen as the default. **That choice was made with the results in view of firing counts only, not of the recall results below**, but it is still a tuned toy.

**Results (one network seed; patterns and noise vary):**
- **Flow:** one clean pattern fires about 25 to 28 of 64 cells in each layer; the first layer 3 fire comes 9 clocks after the first input; 462 packets, none dropped, longest queue 8 (the full depth, so close to dropping).
- **Recall of the map:** 8 patterns; stored map = layer 2 and 3 cells firing in at least 3 of 5 noisy runs (35 to 63 cells of 128). With noisy test runs (10% spikes dropped, 3-clock jitter, 6 stray spikes) the nearest stored map (Jaccard overlap) was the right one in **132 of 160 (82%)**, chance 12.5%. Mean overlap was 0.52 with the right map and 0.37 with wrong ones, so the gap is real but not wide.
- **Mixtures (half of A, half of B):** the two best-matching maps were exactly A and B in only **10 of 100** runs. 78% of the mixture's firing cells lie inside A or B, but the maps are so large (about half of all cells) that almost anything overlaps. So "matches these two maps, find where they cross" does **not** work with this dense a map; it would need sparser maps (higher threshold plus inhibition, or a map taken only from the cells that fire early or most strongly) and a better score than plain overlap. Not tried.
- **Feedback** (layer 3 to layer 1, 4 links per layer 1 cell, activity measured 60 to 100 clocks, long after the input stopped at about clock 40): weight +1 stays silent (but drops 49 packets); **weight +2 and +3 sustain activity by themselves** (7 and 11 packets per clock, 73 and 110 cells still firing, +3 dropping 611 packets), i.e. runaway. A longer refractory (8) reduces but does not stop it. Leak every clock, or 50% inhibitory feedback, stop it completely. **Not yet tested:** whether those stabilised settings still pass useful signal with feedback on (they may simply be too damped), and whether feedback improves recall at all.

**Honest limits:** one seed of the wiring; random wiring, not trained; no weights learned; the Jaccard score is simple; nothing here says how the hardware would behave, how many clocks or cells it costs, or that real sensor data would map the same way. It shows only that (a) small buses with queues carry the flow with no drops in this regime, (b) activity maps are repeatable enough to recognise a stored pattern much better than chance, (c) fuzzy two-map matching needs sparser maps, (d) feedback runs away at modest weight unless leak or inhibition is strong.
**Next, if Alan wants:** sparser maps and re-test of the mixture case; check recall with the stabilised feedback on; repeat over several wiring seeds so the figures have a spread.

## 33. Sparser maps, the two-map test again, and the map-feedback that trains the cells (8 Nov 2026)

**Alan (18:55):** make the maps sparser and retest the two maps crossing; the runaway will be an issue; and he had forgotten the **feedback from a correct map, which is the part that used to train the cells themselves** (in the layer system: when the result is known to be right, the map that produced it is fed back to adjust the cells so that the same input gives the same map more reliably).

**Run:** `tools/hexn_busnet_sparse_v1.py` (+ 3 tests; `hexn_busnet_v1.py` untouched). 4 network settings x 3 map kinds (all cells that fired in layers 2 and 3; only cells firing at least twice; only the first 12 to fire) x 2 scores (plain overlap; overlap that discounts cells shared by many stored maps). One wiring seed, 8 patterns, 160 single tests, 100 mixture tests per row.

**Result:** sparsening alone does **not** fix the two-map case.
- Mixture hits (exactly A and B are the two best maps), out of 100: dense default map 10; best row **27** (threshold 3, 40% inhibitory cells, first-12-to-fire map, plain overlap); most rows 2 to 17. Chance for picking the right pair among 8 is about 3.6 in 100, so the best rows are above chance but far from useful.
- Single-pattern recall got worse as maps got smaller: 132/160 for the dense map down to 104 for the first-12 map at the default setting; 20 to 77/160 where inhibition or threshold left only 0 to 2 cells in a map (a map that is nearly empty cannot be matched). The discounting score was worse than plain overlap on single recall and only helped a little on mixtures.
- Reading (not proven): the wiring is random, so a cell's firing says little about *which* input caused it; sparser maps just carry less of what little there is. Making the maps recognisable and separable is the job of Alan's map-feedback, i.e. training, which this toy has none of.

**Runaway (section 32 result stands):** weight +2 and +3 feedback kept the network firing after the input stopped; leak on every clock or 50% inhibition stopped it. Still to check with training: that the stabilised setting passes a useful signal.

**Map-feedback as a training step (design note, not built):** when the teacher (or the certain-label rule from section 14) says which result is right, the stored map for that result is the target. Compare the map the input just produced with the target: strengthen the weights from the packets that were seen into the target-map cells that failed to fire, weaken them into cells that fired but are not in the target. Small bounded steps within the drift ceiling of the saved weights, and the saved library entered through teacher mode only, exactly as agreed in sections 10 to 12. It fits the scheme already settled, so the weight training scheme does not have to be redone for the neural cell.
**Next if Alan wants:** build that training step in the toy and repeat the single-recall, mixture and feedback tests over several wiring seeds.

## 34. Map feedback built in the toy: it trains the cells (8 Nov 2026)

**Alan (18:59):** start on building the map feedback. Built as `tools/hexn_busnet_train_v1.py` + 4 tests (`hexn_busnet_v1.py` untouched).

**Method (as the design note in section 33):** teacher mode gives each of the 8 patterns a target map: 5 chosen cells in layer 2 and 5 in layer 3, different for every pattern (so the targets are separable by construction). Each training step runs one noisy example of a known pattern. A target cell that did not fire gets every weight from an active source raised by 1; a cell that fired but is not in the target gets those weights lowered by 1. Weights stay within a drift ceiling of the starting wiring (3, or 6 in two runs) and within plus or minus 4. Only existing connections change and only layers 2 and 3 are trained (layer 1 is not). Test noise differs from training noise. Five wiring seeds; 800 single tests and 500 mixture tests per row. Chance is 100 of 800 for single recall and about 18 of 500 for the mixture hit.

| training (epochs of 8 patterns, ceiling) | single recall | mixture A+B exact |
|---|---|---|
| none | 93/800 (12%) | 22/500 (4%) |
| 40, ceiling 3 | 463/800 (58%) | 73/500 (15%) |
| 100, ceiling 3 | 575/800 (72%) | 100/500 (20%) |
| 40, ceiling 6 | 582/800 (73%) | 82/500 (16%) |
| 100, ceiling 6 | 597/800 (75%) | 90/500 (18%) |

**Reading:** the map feedback does train the cells. Untrained, the map says nothing about the pattern (at chance); trained, recall of a single pattern from a noisy run rises to 58 to 75%. The two-map case improves from chance to about 4 to 5 times chance but stays poor (15 to 20% exact pairs). The mean overlap with the right target is still only about 0.2 in the first 40-epoch run, so the trained maps are not close to the target maps, just nearer to them than to the others.

**Cautions:**
- The targets were handed out disjoint by the teacher, which is the easy case; naturally formed maps overlap.
- Only 4 variants were tried and all were scored on the same test noise, so the best row is slightly flattered.
- The first run used a mismatched "active inputs" list in the training step; this was corrected and the figures were identical, as expected, because only layers 2 and 3 are trained and their sources are cells, not inputs. No effect, but noted.
- Not done: feedback links (runaway) with trained cells, whether the stabilised settings still recall, a self-fed target (certain-label rule instead of a teacher), training layer 1, and whether the ceiling of the saved weights holds up over long live use.
**Next if Alan wants:** the same training with the feedback links switched on in the stabilised settings, and a version where the target map comes from the network's own earlier confident runs rather than a teacher.

## 35. Stabilising the feedback, with training; and prior art (8 Nov 2026)

**Alan (19:05):** stabilise the feedbacks; he is sure there is a path through, and equally sure the design is not novel, so there must be earlier work.

**Run:** `tools/hexn_busnet_fb_v1.py` (+2 tests). Feedback links layer 3 to layer 1 (4 per layer 1 cell, weight +2). For each stabiliser, the net is measured untrained ("before") and after map-feedback training done *with the feedback links present* (40 epochs, ceiling 6, 5 wiring seeds). "Afterglow" = cells firing in clocks 60 to 100, after the input ended (about clock 40). Averages of 8 noisy runs per pattern.

| setting | untrained afterglow (cells) | single recall before to after training | mixture exact after | dropped packets per run after |
|---|---|---|---|---|
| no feedback | 0.1 | 12% to 73% | 16% | 56 |
| feedback +2, nothing added | **51** | 14% to 71% | 21% | 58 |
| + leak every clock | 0 | 12% to **36%** | 8% | 3 |
| + leak every clock, threshold 2 | 0 | 14% to 52% | 11% | 5 |
| + 50% of feedback links inhibitory | 1.8 | 14% to **74%** | 22% | 50 |
| + 50% inhibitory, refractory 6 | 0.6 | 17% to 75% | 21% | 35 |
| leak every 2 clocks, refractory 8 | 0 | 12% to 68% | 16% | 5 |

**Findings:**
1. **There is a path.** Making about half the feedback links inhibitory removes the runaway (51 cells down to under 2) and keeps recall as good as no feedback (74%). Adding a longer refractory period lowers the dropped packets (50 to 35). Leak on every clock also stops it but starves the network (recall 36%): too blunt. Leak every 2 clocks with a refractory of 8 also works (68%) and drops very few packets.
2. **Training itself damps the runaway.** After training, even plain +2 feedback shows no afterglow. The training step counts every cell that fires and is not in the target as an error, and the afterglow cells are such cells, so their weights are pushed down. This is a useful property but it is learned for these patterns; it is not a guarantee for inputs the network was never trained on, so the structural stabilisers (inhibitory share, refractory period) should stay as the safety net. Not tested on unseen patterns.
3. **Feedback did not help recall in this test.** Single recall with feedback (68 to 75%) is the same as with none (73%); the mixture score moves between 8 and 22% with noise. So these feedback links cost wiring and traffic without a measured benefit here. They may matter for what Alan wants them for (sequences, holding a state, filling in a missing part of a map), none of which this test asks of them.
4. **Dropped packets are high** (50 to 60 per run of 100 clocks) in the dense settings; queues of depth 8 overflow on noisy input. Settings with fewer firing cells drop almost none. Queue depth or sparser firing is an open sizing question.

**Prior art (Alan's suspicion is right).** Nothing here is new as a family of ideas; what this project adds is the choice of parts and the supervised map training in this form.
- Shared bus carrying a source id with the receiver filtering on it: *address-event representation* (AER), the standard communication scheme in neuromorphic chips since the 1990s. Leaky accumulate-and-fire cells with a refractory period: the leaky integrate-and-fire neuron. FPGA spiking networks on shared buses with queues are a well-published area (a web search returned FPGA SNN papers, e.g. [Spiking Neural Networks on FPGAs](https://ese.washu.edu/documents/Spiking-Neural-Networks-on-FPGAs.pdf) and [a SNN versus CNN FPGA comparison](https://arxiv.org/pdf/2306.12742), which I have not read in detail, so I cite them only as examples of the area, not for any specific result).
- The pattern of activity as a recalled memory is close to *attractor networks* and *Hopfield-style associative memory*; reading out a trained pattern of activity from a fixed random network is *reservoir computing* (liquid state machines). Excitation balanced by inhibition to prevent runaway is the standard answer in cortical models. Training by comparing the network's activity with a target and adjusting the weights of the cells that were wrong is in the family of delta-rule and supervised spike-timing methods.
- Inside this repository: `archeology/shared/docs/software/TYPED_NEURAL.md` (typed leaky integrate-and-fire neurons in series on the cell fabric) and `VISION.md` (neural ponds, Hebbian updating by an observing cluster) already hold neural ideas, and per the working rule they should be read before any of this becomes hardware.
I have not done a literature review; the names above are from general knowledge plus the one search, and a proper check of what is published on, in particular, fuzzy matching of two stored activity maps is still to do.

**Cautions:** one training setup, teacher targets disjoint, toy random wiring, simulation only.
**Next if Alan wants:** read `TYPED_NEURAL.md` and `VISION.md` and compare with section 31 to 35; test the trained, stabilised network on patterns it was not trained on; try a task where feedback should matter (a pattern with a missing part, a sequence).

## 36. The archive read against this design; unseen inputs and missing parts (8 Nov 2026)

**Alan (19:19):** yes to the next steps in section 35.

**Archive read (`TYPED_NEURAL.md`, `VISION.md`, read in full or in the relevant parts).**
- `TYPED_NEURAL.md`: one leaky integrate-and-fire neuron built from 5 to ~12 cells (membrane store, integrator, comparator, spike, refractory); weight, decay and threshold are preloaded values, and "training" is a configure transaction rewriting those values with no recompile. The spike travels on the cell fabric's bus, one neuron per cluster.
- `VISION.md`: neural ponds sharing the tick cycle with OS ponds; a learning rule is "another cell cluster that observes spike activity and updates gate configurations" (Hebbian, STDP, neuromodulation named, none built there).
- **What the archive does not have, and sections 27 to 35 add:** several cells sharing one bus with the receiver filtering on a source id (address-event style) so fan-out is cheap; layers made of small buses with queues; an activity map recalled by the judge; and a supervised map-feedback rule. What it already has that matches: the leaky accumulator and refractory period, and "training = rewrite preloaded weights without recompile", which is exactly how the bounded weight steps and the drift ceiling of sections 10 to 12 would be applied. So the new design reuses the archived neuron's behaviour but changes how cells are connected and who owns the weights. Per the working rule, that cluster neuron should be the starting point for the cell itself, and the shared-bus version should be compared against it for cost before anything is built.

**Run:** `tools/hexn_busnet_gen_v1.py` (+2 tests). Three networks trained with the teacher-target map feedback (40 epochs, ceiling 6, 5 wiring seeds, 400 tests per cell): no feedback, plain +2 feedback, +2 feedback with 50% inhibitory links and refractory 6.

| network (trained) | spikes dropped 10% (as trained) | 30% | 50% | 70% | jitter 8 clocks | afterglow, trained patterns | afterglow, 8 new patterns |
|---|---|---|---|---|---|---|---|
| no feedback | 73% | 62% | 51% | 37% | 69% | 0.0 | 0.0 |
| feedback +2 plain | 77% | 65% | 51% | 39% | 70% | 0.0 | 0.0 |
| feedback +2, 50% inhibitory, refr 6 | 77% | 66% | 58% | 36% | 68% | 0.0 | 0.0 |

**Findings:**
1. **No runaway on unseen patterns after training**, even with plain feedback. Not because the net went silent: a separate check (3 seeds) showed the mean map after training is 8 to 9 cells for both trained and new patterns, against 58 to 77 cells untrained. So training made the whole network sparse, not only for the patterns taught, and the runaway disappeared with it. This is the 3-seed check only and the new patterns get maps of the right size but they are not meaningful maps (no target exists for them).
2. **Missing parts:** recall degrades gently as spikes are removed (73% at 10% dropped, 37% at 70% dropped, chance 12.5%), and heavy timing jitter costs only about 4 points. This is for patterns the network was trained on.
3. **Feedback helped little:** +2 to +4 points at low drop, +7 points for the inhibitory version at 50% dropped; with 400 tests per cell the noise is about 2 to 3 points, so only the 50% result is plausibly real and I would not rely on it. No evidence yet that these feedback links fill in missing parts of a map.
4. Untested: a feedback design aimed at completion (for example feedback weights trained to the target map instead of fixed random +2); a sequence task; different wiring sizes.

**Cautions:** toy, random wiring, teacher targets disjoint, one training recipe.
**Next if Alan wants:** train the feedback weights themselves toward the target map and repeat the completion test; or compare the cost of the shared-bus cell against the archive's cluster neuron in cells and clocks before going further.

## 37. Training the feedback weights, and pruning like a growing child (8 Nov 2026)

**Alan (19:47):** training the weights is good, and this is becoming what happens as a child grows: it starts with a very large number of connections and high plasticity; once paths for certain things are established they are pruned, keeping the most efficient shapes, weights and maps, the fully learned paths.

**Built:** `tools/hexn_busnet_prune_v1.py` (+4 tests; earlier tools untouched). Training now covers layers 1, 2 and 3 including the feedback links into layer 1. The correct map = the teacher's 10 target cells in layers 2 and 3 plus the layer 1 cells that fire for the clean pattern (a clean teacher presentation). Pruning: a consolidation pass counts, for every connection, how often its source was active when its cell fired inside the correct map; each cell then keeps only its most-used connections (ties by larger weight) and the bus delivery tables are rebuilt. 5 wiring seeds, 400 tests per cell.

**A. Training the feedback weights (lean net, 60 epochs):**

| | spikes dropped 10% | 30% | 50% | 70% |
|---|---|---|---|---|
| feedback weights trained | 80% | 74% | 65% | 47% |
| feedback weights frozen at the random start | 76% | 70% | 63% | 42% |
| no feedback links (layers 1 to 3 trained) | 61% | 59% | 56% | 42% |

Training the feedback weights is the best of the three at every drop level, by about 2 to 5 points over frozen, which is near the noise (about 2 to 3 points), so suggestive not proven. Against no feedback the gain is larger at low drop (80 vs 61) but that net also has 4 fewer connections per layer 1 cell, so it is not a clean comparison. Compared with section 36 (feedback fixed, layer 1 untrained: 77/66/58/36) the trained version is better, mostly at high drop (47 vs 36 at 70%), which also includes training layer 1, so I cannot say how much comes from the feedback weights alone.

**B. Rich then prune, against lean from the start (same final connections per cell: 14 on layer 1 including feedback, 10 on layers 2 and 3; same total epochs):**

| network | connections | 10% | 30% | 50% | 70% | dropped packets per run |
|---|---|---|---|---|---|---|
| rich (k=24 plus 8 feedback), trained, not pruned | 5120 | 48% | 42% | 44% | 31% | 283 |
| rich, pruned in one step and retrained | 2176 | 41% | 39% | 35% | 27% | 207 |
| lean from the start | 2176 | 75% | 69% | 64% | 42% | 75 |
| (gradual, 2 stages, 60 epochs) rich pruned | 2176 | 43% | 44% | 37% | 28% | 211 |
| (gradual) lean | 2176 | 80% | 74% | 65% | 47% | 69 |
| (100 epochs first) rich pruned / lean | 2176 | 38% / 79% | 37% / 69% | 31% / 62% | 25% / 48% | 218 / 74 |

**Result: in this toy the child-like route (many connections first, then prune) is clearly worse than starting lean, and pruning does not repair it.** Longer training and gradual pruning did not change that. A larger queue (depth 64) removed the lean net's dropped packets but left the rich net's recall about the same (46% unpruned, 39% pruned, 76% lean), so queue overflow is not the explanation. I do not know the cause. Candidates, none tested: with 24 sources per cell the first activity is so dense that the training signal (raise missed target cells, lower wrong firers) is swamped; the usefulness count taken from a poorly trained net picks the wrong connections to keep; the training rule has no mechanism that makes useful connections stand out before pruning.

**What this does and does not say about Alan's picture.** It does not show pruning is a bad idea. It shows that this training rule, on this task, with random wiring, learns better on a small wiring than on a large one that is then cut down. The biological and machine-learning versions of the idea (weights that start large and get pruned; keeping a small subnetwork that trained well) work when the large network learns the task well first; here it learned worse. A fair test of the idea needs a rich network that learns at least as well as the lean one, for example a lower learning rate or a different rule for the dense start, and a pruning rule that uses something other than the correct-map count. Pruning also has a use that this test does not measure: removing cells and connections that never matter, for cost. From general knowledge, network pruning and the lottery-ticket idea are established areas in machine learning; I have not looked at them for this note.

**Cautions:** toy, random wiring, teacher targets disjoint, one training recipe, simulation only.
**Next if Alan wants:** find out why the rich net trains worse (map sizes during training, how many weights hit the bounds), try a gentler dense start (smaller weights, lower learning rate in the early phase), and try pruning by weight size rather than by use.

## 38. Why the rich net trained worse; the threshold; pruning again (8 Nov 2026)

**Alan (20:05):** yes to the next steps in section 37. Tool: `tools/hexn_busnet_prune2_v1.py` (+3 tests; earlier tools untouched).

**Diagnosis (3 wiring seeds).** The rich net (24 sources per cell, threshold 3) starts with about 120 of 128 layer 2 and 3 cells firing, and 93% of the target cells are among them only because nearly everything fires. The training rule (raise missed target cells, lower every wrong firer) then sees about 110 wrong firers against about 10 missed, over-suppresses to maps of about 11 cells, and ends up hitting only 33% of the target cells. So the rich net did not fail to learn; the rule was dominated by its "lower" half because the start was far too active. Raising the starting threshold fixes the start: rich at threshold 5 starts at 80 cells and ends at 9 cells hitting 62% of target cells (lean at threshold 3: 7.5 cells, 35%).

**A correction to how far the earlier numbers can be trusted.** The threshold of 3 was chosen in section 32 only to get activity flowing through all layers; it was never tuned for recall. Tuning the lean net's threshold (5 seeds, 50 epochs, same task):

| lean net threshold | 10% dropped | 30% | 50% | 70% | dropped packets per run |
|---|---|---|---|---|---|
| 2 | 46% | 47% | 36% | 28% | 276 |
| 3 (used in sections 32 to 37) | 75% | 69% | 64% | 42% | 75 |
| 4 | **92%** | 87% | 73% | 50% | 14 |
| 5 | 95% | 87% | 65% | 34% | 3 |

So every lean-net figure in sections 33 to 37 (and the comparisons made with them) was taken at a poor setting, and the "lean beats rich" result of section 37 mostly measured the threshold, not the wiring size. Section 37's result stands as measured but should be read with this. The conclusions about stabilised feedback (section 35) and the feedback benefit (36, 37) were all at threshold 3 and are untested at 4.

**Pruning again, with a fair start (5 seeds, 400 tests per cell, 50 epochs in all, same final connections 2176 vs rich 5120):**

| network | 10% dropped | 30% | 50% | 70% | dropped packets |
|---|---|---|---|---|---|
| rich, threshold 5, trained, not pruned (5120 connections) | 92% | 87% | 81% | 61% | 144 |
| rich threshold 5, pruned by USE, threshold back to 3 | 42% | 46% | 37% | 30% | 148 |
| rich threshold 5, pruned by WEIGHT size, threshold back to 3 | 81% | 75% | 64% | 47% | 157 |
| rich threshold 5, pruned by weight, threshold 4 | 89% | 84% | 79% | 51% | 113 |
| rich threshold 5, pruned by weight, threshold kept at 5 | 93% | 87% | 78% | 50% | 85 |
| lean, threshold 4, same epochs (2176 connections) | 92% | 87% | 73% | 50% | 14 |
| rich threshold 7, pruned by weight, threshold 4 | 89% | 84% | 73% | 55% | 149 |

**Findings:**
1. **Pruning by use failed badly; pruning by weight size worked.** The use count (how often a connection's source was active when its cell fired in the correct map) is a poor guide in this setup, while the trained weight itself is a good one.
2. **The child-like route works but is not better than starting lean at the same connection count.** Rich at threshold 5 pruned by weight to 2176 connections (threshold kept at 5): 93/87/78/50 against lean at threshold 4: 92/87/73/50. Equal within noise, perhaps 5 points better at 50% dropped.
3. **The unpruned dense net is the best on heavy missing parts** (81% at 50% dropped and 61% at 70%, against 73% and 50%) but it uses 2.35 times the connections and drops about ten times as many packets (144 against 14 per run). Pruning gives up part of that robustness (61% down to 50% at 70% dropped) to cut connections and traffic. That fits Alan's picture as a trade-off between a plastic, robust phase and an efficient final shape.
4. **The firing threshold is the most sensitive setting found so far**, more than wiring size, feedback or pruning. It must be treated as a trained or homeostatic quantity, not a constant (the biology analogue is a cell adjusting its own firing level to keep activity in a target range). The pruned net did best when the threshold stayed matched to its starting activity (5), which suggests it should adapt rather than be reset.

**Cautions:** toy, random wiring, teacher targets disjoint, one training recipe; the choice of which variants to run was made with the earlier test numbers in view, and all are scored on the same test noise; dropped packets are still high for the dense nets.
**Next if Alan wants:** an automatic threshold (each cell adjusts its own level to hold its firing rate near a target), then repeat the feedback tests of sections 35 to 37 at the corrected setting; try pruning in more stages with the threshold adapting between them.

## 39. Cells that set their own firing level (8 Nov 2026)

**Alan (20:17):** yes to the self-adjusting threshold. Tool: `tools/hexn_busnet_homeo_v1.py` (+4 tests; earlier tools untouched).

**Method.** Each cell has its own threshold. After every training epoch the network is run on the patterns and each cell's firing rate (share of runs in which it fired) is compared with a target for its layer (layer 1: 0.40, layer 2: 0.08, layer 3: 0.05). A cell well above target raises its threshold by 1, a cell well below lowers it by 1 (limits 2 to 9). The target rates were set after measuring the tuned fixed-threshold network (average rates 0.39, 0.08 and 0.03), so they are not independent of the answer; the question tested is whether the result stops depending on the starting threshold. 50 epochs, 5 wiring seeds, 400 tests per cell, map feedback training of layers 1 to 3 as in section 37, 50% inhibitory feedback links, refractory 6.

| net, start threshold | fixed: 10% / 30% / 50% / 70% dropped | homeostatic: 10% / 30% / 50% / 70% | mean final thresholds L1 / L2 / L3 (homeostatic) |
|---|---|---|---|
| lean, 2 | 43 / 38 / 31 / 27 | 76 / 69 / 60 / 35 | 7.5 / 4.8 / 2.6 |
| lean, 3 | 77 / 72 / 64 / 42 | 91 / 86 / 66 / 38 | 5.8 / 5.1 / 2.7 |
| lean, 5 | 95 / 89 / 67 / 33 | 89 / 82 / 59 / 33 | 4.0 / 4.7 / 2.7 |
| lean, 7 | 82 / 68 / 44 / 21 | 77 / 68 / 52 / 36 | 3.1 / 3.6 / 2.5 |
| rich, 3 | 53 / 53 / 44 / 32 | 89 / 85 / 75 / 58 | 7.3 / 5.3 / 3.8 |
| rich, 5 | 90 / 87 / 78 / 58 | **96 / 95 / 83 / 57** | 7.2 / 5.6 / 4.1 |
| rich, 7 | 91 / 88 / 80 / 57 | 93 / 91 / 82 / 56 | 7.9 / 5.6 / 4.2 |

**Findings:**
1. **The self-adjusting threshold removes most of the dependence on the starting threshold.** Spread of the 10% result across starting thresholds: lean, fixed 43 to 95, homeostatic 76 to 91; rich, fixed 53 to 91, homeostatic 89 to 96. A badly chosen start (threshold 2 for the lean net, 3 for the rich net) is rescued (43 to 76 and 53 to 89).
2. **For the rich net the final thresholds converge to nearly the same values from every start** (layer 1 about 7.2 to 7.9, layer 2 5.3 to 5.6, layer 3 3.8 to 4.2). For the lean net they do not fully converge (layer 1 ends between 3.1 and 7.5): the rule moves a threshold by at most 1 per epoch and has not finished in 50 epochs from the far starts.
3. **It does not beat the best hand-picked fixed value for the lean net** (fixed 5: 95 / 89 / 67 / 33 against homeostatic from 5: 89 / 82 / 59 / 33). For the rich net it does: the best single row so far is rich from 5 with homeostasis, 96 / 95 / 83 / 57, against the best fixed 91 / 88 / 80 / 57; the gain is within a few points of noise at 70% dropped and real-looking at 10 to 50%.
4. **Dropped packets are unchanged for the rich net** (about 100 to 140 per run; lean net 4 to 70). That cost of the dense net remains.

**What this means for the design.** The firing level can be a property each cell adjusts for itself with a simple rule, so it need not be tuned by hand, and a wrong initial value is largely corrected. It adds one stored number per cell (the threshold) and a rate counter per cell, plus a slow periodic update, which is a hardware cost not yet counted.

**Cautions:** toy; the target rates were chosen with the answer in view; same test noise throughout; threshold update only during training here (not tested while running live); the feedback and pruning results of sections 35 to 38 have not been repeated with this rule; random wiring; teacher targets disjoint.
**Next if Alan wants:** repeat the pruning test (section 38) and the feedback test (sections 35 to 36) with the homeostatic threshold; try target rates that are not taken from the tuned net; test a threshold that keeps adapting during live use.

## 40. Pruning with the self-adjusting threshold (8 Nov 2026)

**Alan (20:32):** the self-adjusting threshold looks good; the next step from section 39 was to repeat the pruning test with it. Tool: `tools/hexn_busnet_homeoprune_v1.py` (+1 test; earlier tools untouched).

**Method.** Dense net (24 sources per cell plus 8 feedback links on layer 1), trained 40 epochs with the self-adjusting threshold, pruned by weight size to the lean connection count (14 / 10 / 10 per cell, 2176 in all), then retrained 10 epochs either with the threshold rule still running or with the thresholds frozen. Compared with the lean net trained 50 epochs with the same rule and the same start threshold. 5 wiring seeds, 400 tests per cell. Recall with 10 / 30 / 50 / 70% of spikes dropped.

| start threshold | network | connections | 10% | 30% | 50% | 70% | dropped packets per run |
|---|---|---|---|---|---|---|---|
| 5 | dense, trained, not pruned | 5120 | 97 | 95 | 87 | 55 | 97 |
| 5 | dense, pruned, retrained **with** homeostasis | 2176 | 95 | 90 | 75 | 44 | 58 |
| 5 | dense, pruned, retrained thresholds frozen | 2176 | 89 | 82 | 68 | 37 | 60 |
| 5 | lean, homeostatic | 2176 | 89 | 82 | 59 | 33 | 4 |
| 3 | dense, trained, not pruned | 5120 | 90 | 87 | 77 | 56 | 137 |
| 3 | dense, pruned, retrained with homeostasis | 2176 | 91 | 84 | 71 | 44 | 89 |
| 3 | dense, pruned, retrained thresholds frozen | 2176 | 89 | 86 | 68 | 42 | 90 |
| 3 | lean, homeostatic | 2176 | 91 | 86 | 66 | 38 | 18 |

**Findings:**
1. **Letting the threshold keep adapting after pruning matters.** From start 5: with the rule running 95 / 90 / 75 / 44, with thresholds frozen 89 / 82 / 68 / 37 (6 to 8 points better). From start 3 the difference is small (91 against 89 at 10%, mixed elsewhere).
2. **With that, the child-like route (dense, then prune) beats the lean start at the same connection count in the start 5 runs** (95 / 90 / 75 / 44 against 89 / 82 / 59 / 33, 6 to 16 points), and is equal or slightly better in the start 3 runs (91 / 84 / 71 / 44 against 91 / 86 / 66 / 38). So the section 38 result "equal to lean" improves to "equal or better" once the thresholds adapt.
3. **The unpruned dense net is still the most accurate** (97 / 95 / 87 / 55 at start 5), with 2.35 times the connections. Pruning keeps about 90% of its accuracy at low drop and about 80% at 70% dropped, for 42% of the connections and 60% of the dropped packets.
4. **Dropped packets** remain much higher for the pruned dense net (58 to 89 per run) than for the lean net (4 to 18): pruning cut connections but the surviving traffic of the dense-trained net is still heavy. This is a queue sizing question for the design.

**Cautions:** toy; target firing rates were chosen with the answer in view (section 39); 400 tests per cell gives about 2 to 3 points of noise, so the start 3 differences are not significant, the start 5 ones at 50 and 70% probably are; the lean net got the same epochs but its start threshold was not tuned per row; teacher targets disjoint; random wiring; no hardware cost counted.
**Next if Alan wants:** find why the pruned net keeps heavy traffic (map sizes and fan-out after pruning) and whether pruning cells, not only connections, reduces it; repeat the feedback tests (sections 35 to 36) with the self-adjusting threshold; target rates not taken from the tuned net.

## 41. Where the dropped packets come from, and what fixes them (8 Nov 2026)

**Alan (20:42):** carry on; every step so far has improved the design. (Not every step: sections 32, 33 and 37 were negative or null results and are recorded as such. The improvements came after those showed what was wrong.)

**Where the drops are** (`tools/hexn_busnet_traffic_diag_v1.py`, seed 1, start threshold 5, packets per run): the lean net fires 31 layer 1 cells, accepts 154 / 114 / 22 packets into the layer 1 / 2 / 3 buses and drops 5 / 0 / 0. The pruned dense net fires 60 layer 1 cells (twice as many), accepts 155 / 176 / 20 and drops 3 / **49** / 0. So the drops are at the **layer 2 buses**, caused by heavy layer 1 firing: each bus serves one packet per clock and its queue (depth 8) overflows in bursts.

**Lever 1: lower the layer 1 target firing rate** (`hexn_busnet_traffic_v1.py`, `_thmax_v1.py`; pruned dense net with homeostasis, 5 seeds, start threshold 5; recall at 10 / 30 / 50 / 70% dropped; dropped packets per run):

| layer 1 target rate, threshold cap | recall | dropped |
|---|---|---|
| 0.40, cap 9 (as before) | 95 / 90 / 75 / 44 | 58 |
| 0.25, cap 9 | 95 / 87 / 72 / 39 | 53 |
| 0.15, cap 9 | 98 / 91 / 76 / 40 | 56 |
| 0.08, cap 9 | 96 / 87 / 72 / 33 | 51 |
| 0.40, cap 16 | 96 / 88 / 62 / 34 | 34 |
| 0.25, cap 16 | 95 / 85 / 56 / 22 | 28 |
| 0.15, cap 16 | 95 / 84 / 51 / 20 | 25 |

Lowering the target barely helps while the threshold cap of 9 binds (the layer 1 thresholds sat at 8.7 to 8.8). With the cap raised the drops fall to 25 to 34, but the recall with many spikes missing falls with it (50% dropped: 75 down to 51 to 62). **Fewer packets is bought with robustness, not free.**

**Lever 2: deeper queues** (`hexn_busnet_traffic_queue_v1.py`; networks trained at the stated depth; target rate 0.40, cap 9):

| queue depth | pruned dense with homeostasis: recall | dropped | lean: recall | dropped |
|---|---|---|---|---|
| 8 (as before) | 95 / 90 / 75 / 44 | 58 | 89 / 82 / 59 / 33 | 4 |
| 32 | 95 / 92 / 74 / 39 | 9.5 | 91 / 81 / 59 / 32 | 0 |
| 128 | 97 / 94 / 68 / 38 | 0 | 91 / 81 / 59 / 32 | 0 |

A deeper queue removes the drops (depth 32 leaves under 10 per run; depth 128 none) and recall is about the same (95 / 92 / 74 / 39 against 95 / 90 / 75 / 44), slightly lower at 50 and 70% dropped at depth 128. So the dropped packets were mostly harmless to accuracy here; the cheaper remedy is queue depth, not weakening the firing.

**Reading for the design:** the pruned dense net needs a queue of about 32 per bus (against 8 for the lean net) to avoid loss, at a cost of queue memory per bus. Not measured: the extra delay a deeper queue adds (a queued packet waits), the memory cost of depth 32 buses on the card, and whether adding more buses per layer (more service per clock) is cheaper than deeper queues.

**Cautions:** toy; one set of runs per setting; the layer 1 and layer 2 target rates were chosen with the answer in view (section 39); the differences of a few points are within the noise of about 2 to 3 points.
**Next if Alan wants:** measure delay against queue depth; try more buses per layer instead of deeper queues; repeat the feedback tests (sections 35 and 36) with the self-adjusting threshold; try target rates that are not taken from the tuned net.

## 42. Delay against queue depth and number of buses (8 Nov 2026)

**Alan (20:56):** apply and test (the open items of section 41: delay of deeper queues, and more buses per layer instead). Tool: `tools/hexn_busnet_shape_v1.py` (+2 tests; earlier tools untouched).

**Setup.** Pruned dense net with the self-adjusting threshold (pipeline of section 40, start threshold 5, 5 wiring seeds). Each layer keeps 64 cells, split into 4, 8 or 16 buses; queue depth 4 to 32. Queue slots = 3 layers x buses x depth, a memory proxy only. Delay = clocks from the first input event to the first layer 3 fire, and to the clock by which 90% of the cells in the final layer 2 and 3 map have fired (8 patterns x 3 noisy runs). Recall with 10 / 30 / 50 / 70% of spikes dropped; dropped = packets lost per 100-clock run.

| buses per layer x cells | queue depth | slots | recall | dropped | delay to first layer 3 fire | delay to 90% of map |
|---|---|---|---|---|---|---|
| 4 x 16 (as before) | 8 | 96 | 95 / 90 / 75 / 44 | 58 | 22.8 | 37.6 |
| 4 x 16 | 32 | 384 | 95 / 92 / 74 / 39 | 9.5 | 29.2 | 52.1 |
| 8 x 8 | 8 | 192 | 91 / 86 / 66 / 38 | 68 | 21.4 | 36.0 |
| 8 x 8 | 16 | 384 | 96 / 93 / 75 / 36 | 39 | 27.6 | 42.1 |
| 16 x 4 | 8 | 384 | 97 / 93 / 70 / 37 | 31 | 21.3 | 35.6 |
| 16 x 4 | 4 | 192 | 96 / 90 / 67 / 36 | 81 | 22.4 | 32.4 |

**Findings:**
1. **Deeper queues cost delay.** Going from depth 8 to 32 on 4 buses cuts drops from 58 to 9.5 but adds about 6 clocks to the first layer 3 fire and about 14 clocks to the 90% point (37.6 to 52.1), because packets wait in line.
2. **More buses cost no delay.** With 16 buses of 4 cells at depth 8 the delay stays at 21 and 36 clocks, and drops fall to 31 (from 58) at the same number of slots (384) as the depth-32 case (which has 9.5 drops). So at equal memory, many shallow buses give lower delay but more drops than few deep buses.
3. **Accuracy hardly depends on any of this.** The low-drop columns stay at 91 to 97% in every row, and the high-drop columns move by a few points only (66 to 75% at 50% dropped), about the noise. The drops cost little accuracy here (consistent with section 41); the real differences are delay, memory and the number of buses.
4. **Not measured:** the physical cost of more buses (each is a shared wire with its own id match at every cell on it, and each source now feeds more buses, which should raise total packets pushed; that count was not recorded here); the cost per queue slot on the card; how much delay the application can accept (a single judge pass versus a stream).

**Choice depends on what the design needs.** If delay matters (a quick decision from a stream), many small buses with a shallow queue; if every packet must arrive and delay is acceptable, fewer buses with a deep queue. A middle option, 8 buses at depth 16, gave 96 / 93 / 75 / 36 with 39 drops and 28 / 42 clocks.

**Cautions:** toy; one pipeline, same test noise, differences of a few points within noise; delay in simulated clocks only, not card time; target rates chosen with the answer in view (section 39).
**Next if Alan wants:** count packets pushed per run for each shape; repeat the feedback tests with the self-adjusting threshold; try the same shapes on the lean net; a first cost estimate (cells, buses, queue memory) for the card from this configuration.

## 43. First cost estimate for the Kintex card, and what it says about scale (8 Nov 2026)

**Alan (21:32):** the cost estimate is the next step, and it would also give a sense of possible scale.

**What was built.** `sub/verilog/hexn_bnet_bus_v1.v` is one shared bus as logic: a queue of source ids (a full queue drops and counts), a weight table with one row per source id (4-bit signed weight for each cell on the bus, 0 = no connection), and the leaky accumulating cells with their own thresholds, refractory period and an 8-bit fire counter for the host (the rate the self-adjusting threshold needs). **It is cross-checked against the Python model:** `tests/vm/test_hexn_bnet_bus_v1.py` runs the module in iverilog and the Python bus on the same stimulus (6 seeds, 160 clocks, dense runs included) and the fire pattern of every cell matches clock for clock; the test fails, not skips, without iverilog, and a deliberately wrong refractory period in the testbench makes it fail (checked). The first version of the test did not catch that (it never made a cell fire twice in a row); it was strengthened before I trusted it. Drops cannot be tested at module level (one push per clock never overflows the queue), so the drop counter is checked only by being equal to the model's (0).

**Synthesis (yosys `synth_xilinx`, a synthesis count only: no placement, routing or timing), one bus:**

| bus | LUT | flip-flops | RAMB36 | LUTRAM | CARRY4 |
|---|---|---|---|---|---|
| 16 cells, 128 table rows (layer 1), queue 8 | 604 | 379 | 1 | 2 | 119 |
| 16 cells, 64 rows (layers 2, 3), queue 8 | 607 | 443 | 0 | 23 | 119 |
| 16 cells, 64 rows, queue 32 | 609 | 449 | 0 | 23 | 122 |
| 8 cells, 64 rows, queue 8 | 311 | 235 | 0 | 12 | 63 |
| 4 cells, 64 rows, queue 8 | 161 | 131 | 0 | 7 | 35 |

So a cell with its share of bus logic costs about 38 LUT sites and 24 to 28 flip-flops. The queue depth is almost free in logic (32 against 8: +2 LUT per bus), because it maps to small distributed memory; its price in the model is delay (section 42), not area. Small tables (64 rows) were put by yosys into distributed RAM, not block RAM.

**The 3 x 64 cell network of sections 41 and 42, assembled from those buses:** 7,300 to 8,200 LUT sites (1.2 to 1.4% of the chip's 597,200), 5,000 to 6,300 flip-flops, 0 to 4 RAMB36 (of 955) depending on shape. Shape changes the total by under 15%: 4 buses of 16 cells is 7,272 LUT, 16 buses of 4 cells is 8,048. **So the area argument does not decide between few deep buses and many shallow ones; delay, drops and the merger problem below do.** About 70 copies of this size would fit by LUT alone.

**Scale (dense tables, 16 cells per bus, one block RAM per 512 rows per bus):**

| cells per layer | all cells | RAMB36 (of about 945 free) | LUT (share of free) |
|---|---|---|---|
| 64 | 192 | 12 (1%) | 7,248 (1%) |
| 512 | 1,536 | 128 (14%) | 57,984 (10%) |
| 1,024 | 3,072 | 448 (47%) | 115,968 (20%) |
| 1,536 | 4,608 | 960 (102%) | 173,952 (30%) |
| 2,048 | 6,144 | 1,664 (176%) | 231,936 (40%) |

**With dense tables the limit is block RAM, at about 1,500 cells per layer (about 4,500 cells in three layers)**, while LUTs would allow roughly 2,500 per layer. The table is a full matrix (every source against every cell on the bus, 4 bits each) although each cell uses only 10 to 14 connections, so most of it is empty; storing only the used connections would extend the limit but needs a different read structure (a source may hit several cells) and was **not modelled**. This is a first-order sense of scale, not a design.

**What is NOT in these numbers, and matters:**
1. **The merger.** The module takes one push per clock per bus; the Python model delivers several. Measured on the trained nets (3 layers, 100 clocks, 24 runs): in the lean net 34% of busy bus-clocks receive more than one packet, at most 5; in the pruned dense net 45%, at most 9 (layer 2 buses). The hardware needs a merge stage (or per-source sub-queues with an arbiter) in front of every bus, which costs area and adds delay, and **its effect on accuracy was not simulated**. This is the largest open cost.
2. The wiring between layers (every fired cell goes to every bus that listens; up to 16 buses in the many-bus shapes) and routing congestion.
3. Loading and reading the tables, thresholds and fire counters over the JTAG link (the weights and the homeostat run on the host), and the clock: no timing was run, so no clock rate is claimed.
4. With a registered table read (needed for block RAM) every bus adds one clock of delay per layer.
5. The accumulator range: the Python model lets it fall without limit (seen down to -46 in the lean net and -86 in the dense net). The module saturates at -32. Testing a floor in the model (`tools/hexn_busnet_floor_v1.py`, pruned dense net with homeostasis, 5 seeds; recall at 10 / 30 / 50 / 70% dropped): floor -32 gives 95 / 90 / 75 / 44, identical to no floor; floor -8 gives 92 / 88 / 72 / 45; floor -4 gives 87 / 76 / 66 / 37. So 6 bits is safe, 5 bits (floor -16) is probably safe and untested, and 4 bits would cost accuracy.

**Reading for the design.** The network we have been testing is small for this card (about 1% of the logic, under 1% of block RAM at the tested size); it will not be the limit. The limits will be the merge stage, the table storage at larger sizes and delay. The next thing to cost is the merger, and then a placed and routed build to get a clock rate.

**Cautions:** synthesis counts only, from yosys not Vivado; the cell and bus follow the Python model, not a finished design; the merger, wiring and host path are missing; scale figures assume dense tables and a straight multiplication of one bus.
**Next if Alan wants:** design and cost the merger and simulate its effect on accuracy and delay; a placed and routed build of one layer on the card toolchain for a clock estimate; a sparse table structure to see how far the scale limit moves.


## 44. The merged design: serialiser, merger, buses, cells, feedback and map matcher as one netlist (8 Nov 2026)

Alan 22:08: design the merger with the other parts in mind, all in one design. Written up in `HEXN_NEURAL_BUS_DESIGN_v1.md`. Simulation and synthesis only; nothing ran on the card.

**What was built.** A source serialiser (a pending bit per source, a rotating pointer, merged events counted), per-(target bus, source group) sub-queues, a round-robin arbiter that lets one packet per bus per clock through, then the bus (table and cells) with feedback from layer 3 to layer 1. Python model `tools/hexn_busnet_hw_v1.py`; RTL `hexn_bnet_ser_v1.v`, `_tbus_v1.v`, `_net_v1.v`, `_bus_v2.v`, and a map recorder/matcher `hexn_bnet_map_v1.v`.

**Check.** The whole network in iverilog matches the Python merger model clock for clock (small shape, 4 seeds, 240 clocks, fire vectors and lost counts); the test fails on a wrong queue depth and a wrong arbiter pointer (mutation-checked). The map matcher matches an independent exact-fraction top-2 check (8 seeds). The lost-packet counters are now kept side by side and read through a selector (the earlier adder-tree sum did not change the DSP count).

**Accuracy and delay** (Python merger model, 5 seeds; recall at 10 / 30 / 50 / 70% of spikes dropped; sub-queue depth per source group):
| shape | recall | sub-queue drops | delay (two points) |
|---|---|---|---|
| 4x16 ideal reference (no merger) | 95/90/75/44 | 58.4 | 22.8 / 37.6 |
| 4x16 merger, ideal weights carried over, depth 8 | 96/92/74/42 | 8.0 | 24.5 / 41.9 |
| 4x16 trained inside the merger, depth 8 | 98/94/77/44 | 9.9 | 26.4 / 45.2 |
| depth 32 | 96/91/76/42 | 0.0 | 29.8 / 47.1 |
| depth 4 | 95/93/77/45 | 34.7 | 21.7 / 40.6 |
| 2 ports | 99/94/71/35 | 0.2 | 23.1 / 35.4 |
| 8x8 depth 8 (ideal 91/86/66/38) | 97/91/72/38 | 0.6 (ideal 68.0) | 23.0 / 42.3 |
| 16x4 depth 8 (ideal 97/93/70/37) | 97/91/72/38 | 0.0 (ideal 31.4) | 21.4 / 34.4 |
Reading: one packet per bus per clock costs no accuracy in this toy and the sub-queues cut drops; delay rises about 4 to 9 clocks for 4x16; 16 shallow buses keep the delay near the ideal.

**Whole-netlist synthesis** (yosys synth_xilinx, 3x64 cells, 48 inputs; % of 597,200 LUT):
| shape | LUT | FF | LUTRAM | DSP |
|---|---|---|---|---|
| 4x16, depth 8, feedback | 19,398 (3.25%) | 8,154 | 352 | 52 |
| 4x16, depth 32, feedback | 24,285 (4.07%) | 13,650 | 352 | 104 |
| 4x16, depth 8, no feedback | 15,822 (2.65%) | 7,022 | 272 | 36 |
| 8x8, depth 8, feedback | 51,002 (8.54%) | 14,318 | 352 | 200 |
| 16x4 | not obtained: yosys (YoWASP) crashed on this shape; not retried | | | |
| map matcher, 128-bit maps, 16 or 64 stored | 779 | 175-181 | 22-43 | 4 |
No block RAM in any row (tables map to LUT memory at this size). Whole-network LUT is about 2.6 times the bus-only 7.3-8.2K of section 43: the merger and serialisers are most of the difference, and some may be coding style. Why 8x8 costs about 2.6 times 4x16 is not understood and not examined. The DSP use is unexplained (the loss-counter sum was removed and the count stayed at 52); it may come from the cell multiply or accumulate coding and has not been traced.

**Cautions:** one combinational chain per hop, so no clock rate can be claimed and the real card needs pipelining, which adds delay the Python model does not yet include; synthesis counts only (not Vivado); accuracy numbers are the toy's; feedback still shows no measured benefit.
**Next if Alan wants:** a placed-and-routed build of one layer on the card toolchain for a clock rate; pipeline the netlist and update the model for the extra clocks; find out why 8x8 and the DSP use are so large.


## 45. First placed-and-routed build of the merged network (Tang Nano 20K, 9 Nov 2026)

Alan 23:18: "yes we can go for a build". The workspace has no Vivado and no Kintex place-and-route, so the Kintex clock rate was NOT obtained. The only place-and-route available is the Gowin flow for the Tang Nano 20K (GW2AR-18, 20,736 LUT4), a different and smaller chip, so this is a yardstick, not the card's speed. Tools: `sub/verilog/hexn_bnet_pnr_v1.v` (wrapper: all inputs from one shift register, all outputs folded to one bit, so the timing is the network's own path) and `tools/hexn_bnet_pnr_v1.sh G PER NIN FB SQL [MHz]`. Native yosys synth_gowin, YoWASP nextpnr-himbaechel, seed 1, one run per shape.

| shape (3 layers) | result |
|---|---|
| 2 buses of 8 cells (24 cells), 16 input lines, sub-queue 4, feedback | fits: 12,376 LUT4 (59%), 2,225 FF (14%), 64 of 648 RAM16SDP4; max clock 47.5 MHz after the optimiser (43.4 MHz on the first pass); misses a 100 MHz target, passes 27 MHz |
| 2 buses of 16 cells (48 cells), 32 input lines | does NOT fit: 27,750 LUT4 (133%) at synthesis |
| 4 buses of 8 cells (same 48 cells) | not run: same cell count, expected not to fit |

**Reading.** The single-clock-per-hop netlist reaches about 47 MHz on this chip, which is the long combinational chain showing. The model's delays are in clocks, so a slow clock is not wrong for the toy, but it needs pipelining before any claim about speed or real-time use. On the Gowin each cell costs about 500 LUT4 (12.4K / 24), far more than the roughly 38 per cell of the bus-only count (section 43) or the 19.4K LUT for 192 cells of section 44; the Gowin has no LUT6 and the tables here use distributed RAM, so the Gowin number is not comparable with the Xilinx synthesis counts. Where the long path runs (serialiser, merger, table read or cell) was not looked at.

**Cautions:** one seed, one run per shape; target clocks only 27 and 100 MHz; different chip; no board test; the Kintex figure is still unknown and needs Vivado on Alan's side or on the card's toolchain.
**Next if Alan wants:** read the critical path from the report and pipeline the stage that causes it, update the Python model for the extra clocks; package a Vivado kit (RTL, constraints, script) for a real Kintex number.


## 46. The slow line, and the first pipeline stages (9 Nov 2026)

Alan 00:05: test the slow line first, then add pipeline stages; the card build follows, and the detector layer, batch judge and neural block come before layers 2, 3 or 4. Same Tang Nano 20K yardstick as section 45 (shape: 3 layers of 2 buses of 8 cells, 16 input lines, sub-queue 4, feedback; one run per placer seed; the "Max frequency" lines are the optimiser's estimate then the routed figure, the routed figure is quoted).

**The slow line (v1, 47.5 MHz, 21 ns: 13.2 logic, 7.9 routing).** Read from the place-and-route report: it runs from the input serialiser's rotating pointer, through the "first pending source at or after the pointer" search, through the sub-queue write, to the 16-bit loss counter (`dropped`). So the whole hop was one path, and the loss counter was its last link.

**Changes (clones, v1 files untouched):** `hexn_bnet_net_v2.v` registers every serialiser output (valid, index) before the merger, so each hop takes one clock more; `hexn_bnet_ser_v2.v` and `hexn_bnet_tbus_v2.v` count lost packets through registers (the counters read four clocks late; only the host reads them). Python: `tools/hexn_busnet_hw_v2.py` (`HWNetP`, same CLI as v1). Test `tests/vm/test_hexn_bnet_net_v2.py` (+ testbench): clock-for-clock fire vectors and loss count (compared at the clock the counters have reached) against `HWNetP`, 4 seeds; run against the unpipelined v1 netlist it fails at clock 1, so the one-clock-per-hop change is checked.

**Timing steps** (routed estimate, seed 1): v1 47.5 MHz; pipeline register after the serialisers only 79.7 MHz (then the loss counter became the slowest line); counter with one register 65 MHz (the counting of events itself became the slowest line); counter in three register stages **74-77 MHz** (seed 1 77.4, seed 2 74.4). Seed-to-seed variation was up to about 10 MHz on the same netlist, so treat these as +/-10 MHz. LUT4 use unchanged at about 12.4K (59%).
**The slowest line now** is the serialiser's own pointer-to-pointer step (rotating search, then update of the pointer): it is the design itself, not a counter, and speeding it up means changing how the next source is chosen. Not done.

**Accuracy and delay with the extra clock per hop** (`python3 tools/hexn_busnet_hw_v2.py 1 16 8 G PER`, 5 seeds, sub-queue 8, recall at 10/30/50/70% dropped, delay to first layer-3 fire / 90% of the map):
| shape | unpipelined merger (section 44) | pipelined |
|---|---|---|
| 4 x 16 | 98/94/77/44, 26.4 / 45.2 | 98/94/74/45, 32.3 / 49.5 |
| 16 x 4 | 97/91/72/38, 21.4 / 34.4 | 98/90/69/33, 25.5 / 39.0 |
Recall holds at low drop rates and falls a few points at the heavy-drop end for 16 x 4; delay rises about 4 to 6 clocks. The ideal references are unchanged (4x16: 95/90/75/44; 16x4: 97/93/70/37).

**Cautions:** Tang Nano 20K figures, not the Kintex card (no Vivado here); one netlist shape (the only one that fits); +/-10 MHz placer noise, two seeds; the pipeline is only after the serialisers (the table read and cell update are still in one clock and were not the limit in these runs); the model's accuracy numbers are the toy's.
**Next:** the Kintex build, then the detector layer, the batch judge and the neural block on the base, then layers 2 and 3 (or 4) if needed (Alan's order); a faster next-source choice if the clock matters.


## 47. First Kintex build of the merged network (openXC7 flow, 9 Nov 2026)

Alan ran `fpga/ypcb/hexn_bnet/run_bnet.sh 2:8:16:2` on his OptiPlex (YPCB-00338-1P1, XC7K480T, 50 MHz target, openXC7 yosys and nextpnr-xilinx). Shape: 3 layers of 2 buses of 8 cells, 16 input lines, sub-queue 4, feedback, the pipelined netlist (`_v2`). First attempt stopped in one second at `always_comb` (the flow reads plain Verilog); `prebuild.py` now rewrites it for the card build only (ledger row 9 Nov 15:10). Second attempt: exit 0, bitstream produced, run time about 2.5 minutes (14:55:17 to 14:57:48).

**Result (nextpnr estimate, not silicon):** max clock 72.54 MHz after placement and 84.25 MHz after routing (the two lines the tool prints; I take the second as the routed figure, as on the Tang runs), passing the 50 MHz target. For comparison the Tang Nano 20K figure for the same shape was about 75 MHz plus or minus 10 (section 46), so the card is in the same range for this shape.

**Not yet known:** the logic, flip-flop and DSP use on the card (the summary's grep did not match the openXC7 log wording; the lines can be read from `/mnt/hdd/hexn_builds/bnet_2x8_n16_q2.log`), and the two larger shapes (4:16:48:3 and 8:8:48:3), which are the ones the design point of section 44 is about. This build is driven by an LFSR and checks size and clock only; function is covered by the iverilog cross-check. One run, one seed; the clock on silicon has not been measured.


### 47a. Logic use of the first Kintex build (read from the build logs, 9 Nov 2026 15:05)

Shape 2:8:16:2 (48 cells in all), nextpnr-xilinx on the XC7K480T: **7,313 LUT sites of 597,200 (1%)**, 2,071 flip-flops (0%), 479 CARRY4, **28 DSP48E1** of 1,920 (1%), 0 block RAM (RAMB18, RAMB36). The yosys cell counts agree: 1,169 LUT2, 877 LUT3, 447 LUT4, 812 LUT5, 456 LUT6, 1,975 FDRE, 96 FDSE, 474 CARRY4, 28 DSP48E1. The tables map to LUT memory, as in the section 44 synthesis. The DSP blocks are still unexplained (28 for 48 cells here; 52 in the section 44 4x16 count); not traced. Cause of the 7.3K here against the Tang's 12.4K LUT4 for the same shape is the different cell types (LUT6 against LUT4), not a design difference. The 4:16:48:3 and 8:8:48:3 shapes are still to be built. `run_bnet.sh` was changed to print these lines from the build's own nextpnr and yosys logs.


### 47b. The two larger Kintex builds, and a correction to the percentages of section 44 (9 Nov 2026 16:05)

Alan ran `run_bnet.sh 4:16:48:3 8:8:48:3` (50 MHz target, openXC7). Logic use is from the build's nextpnr log (Alan pasted it); clocks are the two "Max frequency" lines the summary printed (after placement, after routing; nextpnr estimates, not silicon).

| shape (3 layers) | build time | LUT sites (of 597,200) | FF | CARRY4 | DSP48E1 | block RAM | clock |
|---|---|---|---|---|---|---|---|
| 2 buses x 8 cells (48 cells), 16 lines | 2.5 min | 7,313 (1.2%) | 2,071 | 479 | 28 | 0 | 72.5 / 84.3 MHz, passes 50 |
| 4 buses x 16 cells (192 cells), 48 lines | 20 min | 34,777 (5.8%) | 9,081 | 2,027 | 52 | 0 | 54.6 / 58.1 MHz, passes 50 |
| 8 buses x 8 cells (192 cells), 48 lines | 32 min | 70,994 (11.9%) | 15,419 | 2,843 | 200 | 0 | 49.4 MHz, FAILS 50 by 0.6 MHz; no bitstream |

**Correction to section 44.** There the 4x16 cost was given as 19.4K LUT (3.25% of 597,200). That divided a yosys LUT6 count by the nextpnr site count, two different measures (the card notes already say to use the nextpnr figure). On the card the same 4x16 design takes **34,777 sites, 5.8%**, about 1.8 times the figure written in section 44. The 8x8 shape takes 71.0K (11.9%), not 8.5%. The ranking stands: 8x8 costs about twice 4x16. The DSP counts match the yosys counts (52 and 200), so those were right.

**Reading.** All three shapes fit easily; none uses block RAM. The 4x16 shape (the design point of section 44) passes 50 MHz with about 8 MHz to spare on the estimate, and 58 MHz is lower than the 84 MHz of the small shape, so clock falls as the network grows. 8x8 misses 50 MHz narrowly. DSP use grows about 3.8 times from 4x16 to 8x8 with the same number of cells, so it scales with the number of buses, not cells. A guess, not tested: the index arithmetic of the merger (position times width) is being mapped to multipliers.

**Cautions:** nextpnr estimates, one run per shape, LFSR-driven test (size and clock only); the bitstreams have not been loaded on the card; no pipelining beyond the register after the serialisers; 8x8 failed by a small margin and a different seed or a small pipeline change could pass it.
**Next if Alan wants:** replace the index multiplications with shifts and adders (a cheap test of the DSP guess); load the 4x16 bitstream on the card as a smoke test; the Kintex column for sections 44 and 46 can now use these numbers.


## 48. The DSP blocks traced and removed (9 Nov 2026)

**Cause.** Yosys names each DSP block after the expression it came from. All of them (52 in the 4x16 shape, 200 in 8x8, 28 in 2x8) come from line 30 of `hexn_bnet_tbus_v2.v`: in the arbiter, `cntv[jj*(SQL+1) ...]` and `srow[jj*IDW ...]` / `headv[jj*IDW ...]`, a variable position `jj` times a constant width, repeated once per unrolled search step. The guess of section 47b (index arithmetic in the merger) was right.
**Change (clones, v2 untouched):** `hexn_bnet_tbus_v3.v` and `hexn_bnet_net_v3.v` write the slice as a compare against each constant position, so no multiplier is made. Same behaviour: `tests/vm/test_hexn_bnet_net_v3.py` (the section 46 cross-check against `HWNetP`, 4 seeds) passes.
**Local synthesis, 4x16 (yosys, plain Verilog):** 0 DSP48E1 (v2: 52), 18,067 LUT (yosys LUT6 count), 8,916 FF, 2,114 CARRY4. The 8x8 number was not obtained here (run stopped).
**Kintex effect not yet known:** the card flow has not built v3. The kit now defaults to v3 (`HEXN_NETV=v2` for the old one). The two things to learn from a rebuild are the logic use in nextpnr terms and whether the clock moves; 8x8 missed 50 MHz by 0.6 MHz with the DSP blocks in the path.


## 49. Matching per layer against the combined map (9 Nov 2026)

Alan 16:52: the matcher per layer. `tools/hexn_busnet_layermatch_v1.py` (python3 tools/hexn_busnet_layermatch_v1.py 4 16): the pruned dense network with homeostasis (as the ideal model of section 44), 4 buses x 16 cells, 5 seeds, the same noisy test patterns as before (10 per pattern); the live map is compared with the stored maps in five ways. Recall at 10 / 30 / 50 / 70% of events dropped:

| matcher | recall |
|---|---|
| combined layer 2 + 3 map (every earlier section) | 95 / 90 / 75 / 44 |
| layer 2 map only | 97 / 92 / 76 / 46 |
| layer 3 map only | 78 / 65 / 50 / 25 |
| two per-layer matchers, scores added | 93 / 88 / 74 / 43 |
| two per-layer matchers must agree | 77 / 64 / 46 / 21 |

**Reading.** In this toy the layer 2 map carries the pattern and matches as well as the combined map (slightly better, 1 to 2 points, within what 5 seeds can show); layer 3 alone is clearly worse, and adding or requiring agreement does not help. So a matcher per layer gives no accuracy gain here; what it gives is information about each layer (layer 3 is the weaker one in this network), and a layer tile can still carry its own small matcher for the stacking design of the tile spec section 8. Why layer 3 is worse was not examined (the target maps, the feedback loop and the afterglow are all candidates).
**Cautions:** toy patterns; target maps chosen by me (5 cells per layer per pattern); 5 seeds, 10 tests each; the first row reproduces the earlier reference figures (95/90/75/44), so the run matches the earlier tools.


## 50. Matching per layer on a 5-layer network (9 Nov 2026)

Alan 16:59: does "layer 2 alone does best" follow if the model has 5 layers: only the middle, or every second layer? `tools/hexn_busnet_layers5_v1.py` (python3 tools/hexn_busnet_layers5_v1.py 5 4 16): 5 layers of 4 buses x 16 cells, same training as section 49 (dense start, homeostat, prune to 10 sources per cell, retrain), 5 seeds, 10 tests per pattern. The earlier model code assumed 3 layers in a few places; the tool patches those at run time (target maps in layers 2 to 5, 200-clock runs, firing-rate targets of 0.05 for layers 4 and 5, which is a GUESS and not tuned). Recall at 10 / 30 / 50 / 70% of events dropped:

| matcher | recall |
|---|---|
| layer 2 | 83 / 81 / 68 / 40 |
| layer 3 | 63 / 58 / 45 / 27 |
| layer 4 | 46 / 44 / 34 / 20 |
| layer 5 | 42 / 35 / 26 / 19 |
| all layers together | 79 / 76 / 64 / 39 |
| layers 2 + 4 | 80 / 79 / 66 / 40 |
| layers 3 + 5 | 61 / 57 / 43 / 27 |

Cells fired per run by layer (average of 5 seeds, 8 patterns): layer 1 43, layer 2 4, layer 3 2, layer 4 2, layer 5 1.

**Reading.** The rule is neither "only the middle" nor "every second layer". Recall falls steadily with depth: layer 2, the first layer after the input, is best, and each later layer is worse. Combining layers does not beat layer 2 alone (every second layer, 2 + 4, ties it). The reason shown by the fire counts is that the signal thins out with depth: layer 2 fires about 4 cells per run, layer 5 about 1, against 5 target cells per layer per pattern, so a deep layer gives the matcher little to match.
**Caution, important:** this is the model as it stands, not tuned for depth. The homeostat targets for layers 4 and 5 are my guess, the sources per cell were pruned to 10 as for the early layers, and nothing was adjusted to keep activity alive at depth. So it shows that stacking layers as they are fades the signal; it does NOT show that deeper layers cannot be made useful. Overall recall also falls from the 3-layer figures (layer 2: 97 / 92 / 76 / 46 in section 49), another sign of the untuned setup. One run per setting, toy patterns.
**For the stacking idea:** the tile only helps if a deeper tile keeps the signal. The first thing to test is what keeps activity alive across layers (more sources per cell, higher starting weights, or a lower threshold in deep layers) before building more layers in hardware.


## 51. How small the firing becomes with depth, with the feedback on and off (9 Nov 2026)

Alan 17:07: look first at how small the firing becomes, and whether the feedback affects keeping signals alive. `tools/hexn_busnet_depth_diag_v1.py` (python3 tools/hexn_busnet_depth_diag_v1.py 5): 5 layers of 4 buses x 16 cells (64 per layer), 3 seeds, clean runs of the 8 patterns, measurement only. Feedback ON is last layer to layer 1, half inhibitory, as in earlier sections; OFF has no feedback links. Cells fired per run (silent runs in brackets, as % of runs with no cell fired in that layer):

| feedback | stage | layer 1 | layer 2 | layer 3 | layer 4 | layer 5 |
|---|---|---|---|---|---|---|
| ON | untrained | 47.1 | 44.6 | 47.3 | 49.4 | 50.8 |
| ON | trained dense | 43.4 | 5.8 (4%) | 3.0 (21%) | 2.5 (27%) | 1.6 (50%) |
| ON | pruned, retrained | 43.2 | 3.9 (4%) | 2.3 (17%) | 2.1 (21%) | 1.5 (44%) |
| OFF | untrained | 50.3 | 46.0 | 48.3 | 51.4 | 49.5 |
| OFF | trained dense | 47.0 | 5.2 (0%) | 3.1 (8%) | 2.4 (27%) | 2.0 (40%) |
| OFF | pruned, retrained | 47.0 | 3.8 (2%) | 2.4 (15%) | 1.9 (35%) | 1.3 (56%) |

Mean threshold per layer after pruning and retraining (ON; OFF is within 0.4): 7.9, 4.8, 3.2, 2.4, 2.2 for layers 1 to 5. The floor is 2 (TH_MIN).

**Reading.**
- Untrained, the network is flooded: about 45 to 51 of the 64 cells fire in every layer. Training removes that, and the cut is very large (layer 2 from about 45 to about 4 to 6 cells). Deeper layers end at 1.3 to 3 cells per run, and by layer 5 between 40% and 56% of the runs have no firing in that layer at all.
- Pruning reduces the firing again: layer 2 falls about a third (5.8 to 3.9, ON), the deeper layers less. The silent share in layer 5 went 50 to 44% (ON) but 40 to 56% (OFF), so there is no consistent pruning effect on silence in 3 seeds.
- Feedback ON against OFF: no clear difference in the deeper layers at this size (layer 5: 1.5 against 1.3 cells, 44% against 56% silent, but the order flips between stages). The feedback does not appear to be what starves the deep layers. It does hold layer 1 slightly lower (43 against 47 cells). Three seeds, so differences of this size are not established.
- The thresholds in layers 4 and 5 are already at the floor (about 2.1 to 2.4 against a limit of 2), so the homeostat has no more room to raise their firing by lowering thresholds. The shortage is in how much input reaches the deep layers.
- Part of this is by my choice: the firing-rate targets (0.08 for layer 2, 0.05 for later layers) mean about 5 and 3 cells per run in a 64-cell layer, and the deep-layer values were a guess in section 50.
**Cautions:** model only; 3 seeds; untuned for depth; the loss of firing is the toy network under my training rules (target maps of 5 cells per layer), not a general fact about layered networks.
**Candidates to keep activity alive (not tried):** a lower threshold floor in deep layers; higher firing-rate targets for deep layers; more sources per cell or stronger starting weights in layers 4 and 5; a separate feedback test on those fixes.


## 52. Is the pruning too harsh? A sweep of the kept sources per cell (9 Nov 2026)

Alan 17:15. `tools/hexn_busnet_prunelevel_v1.py` (python3 tools/hexn_busnet_prunelevel_v1.py): 3 layers of 4 buses x 16 cells, 5 seeds, 10 tests per pattern per drop level. One dense network per seed (24 sources per cell, 8 feedback links), trained 40 epochs with the homeostat; each level is pruned by weight size from a copy of it and retrained 10 epochs. Layer 1 keeps 4 more than the others (the feedback links), as the lean net did. Recall at 10 / 30 / 50 / 70% of events dropped:

| sources per cell | connections | combined layer 2 + 3 | layer 2 only | cells fired, layer 2 / 3 |
|---|---|---|---|---|
| unpruned | 5,120 | 97 / 95 / 87 / 55 | 98 / 96 / 90 / 58 | 5.2 / 3.0 |
| 20 (layer 1: 24) | 4,096 | 97 / 94 / 89 / 54 | 98 / 96 / 90 / 54 | 4.9 / 2.9 |
| 14 (layer 1: 18) | 2,944 | 99 / 94 / 83 / 56 | 99 / 96 / 85 / 57 | 4.7 / 2.5 |
| **10 (layer 1: 14), used since section 37** | 2,176 | 95 / 90 / 75 / 44 | 97 / 92 / 76 / 46 | 3.7 / 2.0 |
| 6 (layer 1: 10) | 1,408 | 81 / 67 / 50 / 28 | 83 / 70 / 52 / 28 | 3.5 / 2.1 |
| 4 (layer 1: 8) | 1,024 | 67 / 55 / 36 / 24 | 64 / 52 / 37 / 25 | 2.5 / 1.9 |

**Reading.**
- Pruning to 10 sources per cell is on the harsh side. Keeping 14 holds recall close to the unpruned net (combined 99 / 94 / 83 / 56 against 97 / 95 / 87 / 55) with 57% of its connections; 10 gives up 8 points at 50% drop and 12 at 70% (75 and 44 against 83 and 56). Going lower than 10 falls away fast (6: 50 and 28 at 50 and 70% drop).
- The knee for this network is between 10 and 14 sources per cell. The earlier choice of 10 was made for a small connection count, with the comparison against the unpruned net showing little loss at the gentler drop levels; at heavy drop it costs more than I wrote then.
- The thin firing is mostly NOT the pruning: the unpruned net fires only 5.2 cells in layer 2 and 3.0 in layer 3 per run. That is the training target and the homeostat rate targets (5 target cells per layer per pattern; rate targets 0.08 and 0.05), not the loss of connections. Pruning to 10 takes layer 2 from 5.2 to 3.7.
**Cautions:** model only; toy patterns; 5 seeds, so differences of a point or two are noise; one dense network per seed, so the levels are not independent trainings.
**Not yet answered:** whether the later layers need to be as large. Layers of unequal size need a model change (the model uses the same buses and cells in every layer). The layer must hold enough distinct target cells for the stored patterns (8 patterns x 5 cells = 40 of 64 now), so shrinking below that needs fewer cells per pattern or fewer patterns; this is a separate test.


## 53. Moving the working point from 10 to 14 sources per cell: does the layered firing change? (9 Nov 2026)

Alan 20:21: move the working point first and see if the layered fire rate changes. `tools/hexn_busnet_workpoint_v1.py LAYERS` (3 and 5 run, 5 seeds each; 5 layers patched as in section 50, deep-layer rate targets guessed): the same dense start, training, pruning and retraining as section 52; only the kept sources differ, K = 10 (layer 1: 14, the working point of sections 37 to 52) against K = 14 (layer 1: 18). The earlier tools are unchanged; the working point is chosen in this tool's call, not by editing `LEAN_KEEP`.

**3 layers (the design).** Recall at 10 / 30 / 50 / 70% dropped, combined map:
| | connections | recall | cells fired L1 / L2 / L3 | silent runs L2 / L3 | mean threshold L1 / L2 / L3 |
|---|---|---|---|---|---|
| K = 10 | 2,176 | 95 / 90 / 75 / 44 | 37.0 / 4.0 / 2.2 | 1% / 16% | 7.2 / 4.8 / 3.5 |
| K = 14 | 2,944 | 99 / 94 / 83 / 56 | 37.2 / 4.9 / 3.0 | 0% / 6% | 7.2 / 5.4 / 3.9 |
Layer 2 alone: 97 / 92 / 76 / 46 (K = 10), 99 / 96 / 85 / 57 (K = 14).

**5 layers (stretch, untuned for depth).**
| | connections | recall (combined) | cells fired L1 to L5 | silent runs L2 to L5 |
|---|---|---|---|---|
| K = 10 | 3,456 | 79 / 76 / 64 / 39 | 43.7 / 3.7 / 2.3 / 2.0 / 1.2 | 4 / 20 / 29 / 52 % |
| K = 14 | 4,736 | 87 / 78 / 72 / 42 | 43.9 / 4.8 / 2.7 / 2.0 / 1.5 | 0 / 12 / 29 / 44 % |
Layer 2 alone: 83 / 81 / 68 / 40 (K = 10), 91 / 81 / 76 / 45 (K = 14).

**Reading.**
- The layered fire rate does change, modestly, in the early layers: layer 2 fires about 0.9 more cells per run, layer 3 about 0.5 to 0.8 more, and the silent share in layer 3 falls (16 to 6% in the 3-layer net, 20 to 12% in the 5-layer net). Layer 1 is unchanged.
- It does not change the picture at depth: layer 4 stays at 2.0 cells and 29% silent, layer 5 goes from 1.2 to 1.5 cells and 52 to 44% silent, thresholds there stay near the floor (2.4 to 2.6, and 2.2 to 2.3). So 14 helps the layers near the input and does not fix the thinning at depth.
- Recall improves at the 3-layer design by 4 to 12 points depending on drop level (the 70% drop figure goes 44 to 56) for 35% more connections (2,176 to 2,944). In the 5-layer net the gain is 3 to 8 points.
**Cautions:** model only; toy patterns; 5 seeds; K = 14 was chosen after seeing the sweep of section 52, on the same patterns and seeds, so its advantage over K = 10 is partly selection; the 5-layer figures use guessed rate targets.
**Working point:** 14 sources per cell (layer 1: 18) from here for new tests unless Alan decides otherwise; no earlier file was edited.


## 54. What keeps the deep layers alive? Five variants at the new working point (9 Nov 2026)

Alan 21:16 (driving; left to run). `tools/hexn_busnet_depthfix_v1.py VARIANT`: 5 layers of 4 buses x 16 cells, 14 sources per cell (section 53 working point), 4 seeds, 8 tests per pattern and drop level; one process per variant (the changes are module settings). Variants: **base** (nothing changed); **floor1** (threshold floor 1 instead of 2, all layers); **rates** (firing-rate targets of layers 3 to 5 raised from 0.05 to 0.08, the layer 2 value); **weights** (excitatory starting weights in layers 4 and 5 one higher); **all** (the three together). Layer 4 and 5 rate targets in the base were my guess (section 50).

Cells fired per run, silent runs (% of runs with nothing fired in that layer) and recall of a matcher on that layer alone, at 10 / 50 / 70% of events dropped:

| variant | cells fired L2 / L3 / L4 / L5 | silent L3 / L4 / L5 | recall L2 | recall L3 | recall L4 | recall L5 | all layers |
|---|---|---|---|---|---|---|---|
| base | 4.7 / 2.5 / 2.0 / 1.5 | 12 / 33 / 44 % | 91 / 78 / 46 | 63 / 51 / 27 | 51 / 41 / 21 | 38 / 28 / 20 | 87 / 73 / 44 |
| floor1 | 4.6 / 2.3 / 2.3 / 1.5 | 16 / 23 / 45 % | 90 / 75 / 46 | 69 / 52 / 26 | 47 / 37 / 23 | 38 / 29 / 17 | 81 / 73 / 42 |
| rates | 4.7 / 3.0 / 2.5 / 2.0 | 16 / 28 / 38 % | 89 / 81 / 44 | 73 / 61 / 32 | 64 / 51 / 26 | 52 / 43 / 23 | 87 / 76 / 44 |
| weights | 5.1 / 2.6 / 2.5 / 1.8 | 14 / 23 / 36 % | 96 / 81 / 48 | 70 / 49 / 24 | 56 / 43 / 19 | 39 / 29 / 18 | 89 / 73 / 44 |
| all | 4.7 / 3.2 / 3.0 / 2.8 | 9 / 12 / 23 % | 94 / 80 / 50 | 78 / 59 / 36 | 73 / 50 / 35 | 66 / 44 / 32 | 89 / 69 / 46 |

Mean threshold of layers 4 and 5: 2.5 / 2.3 (base), 1.6 / 1.3 (floor1 and all).

**Reading.**
- The rate targets matter most on their own: raising them for layers 3 to 5 lifts the deep layers' firing (layer 5 1.5 to 2.0 cells) and each deep layer's recall (layer 4 51 to 64 at 10% drop, layer 5 38 to 52). The floor alone and the starting weights alone do little.
- All three together keep the deep layers clearly more alive: layer 5 fires 2.8 cells (1.5 in the base), is silent in 23% of runs (44% in the base), and its matcher recalls 66 / 44 / 32 against 38 / 28 / 20. The deep layers still stay below layer 2 (94 / 80 / 50).
- The matcher on all layers together does NOT improve (89 / 69 / 46 against 87 / 73 / 44): keeping the deep layers alive makes each of them more informative on its own but adds nothing on top of layer 2 in this toy.
- The rate targets are the knob that decides how many cells fire per run (a target of 0.08 means about 5 cells in a 64-cell layer), so a part of this result is the setting working as set, not something the network found.
**Cautions:** model only; toy patterns; 4 seeds with 8 tests per setting, so differences of a few points are noise (layer 2 moving between 89 and 96 across variants that should not touch it shows how much); the variants were chosen after the findings of sections 50 to 53 on the same patterns.
**For the tile design:** a deep layer can be made to carry the pattern, but in this toy it does not add recall over layer 2, so the case for more layers has to come from a real task, not from this test.

## 55. First real data: the Heidelberg spoken digits (9 Nov 2026, Alan 22:07)

**Data.** SHD from zenkelab.org (train 8,156, test 2,264 recordings; 20 classes; 700 channels; spike times to about 1.1 s). Both files matched the published md5 sums. Used: the 10 English digits, 4,011 training and 1,079 test recordings. The test file holds speakers 4 and 5, who are never in training; they make up 870 of the 1,079 English test recordings, so the test is mostly unheard voices. The page states no licence or citation text; citation to be checked before any publication.

**Front end** (`tools/hexn_shd_frontend_v1.py`): 700 channels folded to NIN lines (neighbouring channels share a line); 1 s cut into time steps; in each step only the TOPN busiest lines (count divided by the line's average) send one event. A plain template classifier on the same folded data gives the ceiling the front end allows (chance 10%):

| lines | steps | top per step | events per recording | template accuracy |
|---|---|---|---|---|
| 48 | 40 | 1 / 2 / 4 | 20 / 36 / 68 | 58.7 / 65.2 / 77.0 % |
| 48 | 40 | 6 / 8 | 100 / 133 | 84.7 / 84.0 % |
| 48 | 20 | 8 | 82 | 85.7 % |
| 96 | 40 | 1 / 2 / 4 | 13 / 24 / 48 | 42.4 / 50.1 / 62.0 % |
| 24 | 40 | 4 | 82 | 84.0 % |

More events help up to about 100; 96 lines at the same event count did worse than 48 (events spread thinner).

**Network** (`tools/hexn_busnet_shd_v1.py`): the section 53 network (3 layers of 4x16, dense start then 14 sources per cell, homeostat), 20 steps of 2 clocks (the 40-clock window of the toy), teacher maps of 5 cells per layer per digit, 40 epochs of 2 training recordings per digit, 3 seeds, 300 test recordings (30 per digit):

| events per recording | template (same test set) | network combined map, dense | network combined map, 14 per cell | layer 1 cells fired (of 64) | packets dropped |
|---|---|---|---|---|---|
| 25 (top 2) | 68.7 % | 12.6 % | 16.0 % | 41 to 44 | 28 to 32 % |
| 45 (top 4) | 77.0 % | 13.3 % | 14.3 % | 49 | 42 to 45 % |
| 45, threshold cap 9 -> 30 | 77.0 % | 13.0 % | 19.0 % | 41 to 48 | 29 to 34 % |
| 82 (top 8), 30 epochs | 86.3 % | 10.4 % | 12.2 % | 49 to 50 | 55 to 56 % |

**Reading.**
- **The network as built does not recognise these recordings yet.** Recall is 10 to 19% against 10% chance, while a template on the same folded data reaches 69 to 86%. So the information is in the events and the network is not using it; this is a failure of the network setup, not of the data.
- Layer 1 is saturated on real input (41 to 50 of 64 cells fire on every recording, target about 26), and 28 to 56% of packets are dropped. Layer 1 therefore does not separate the digits. Raising the homeostat's threshold limit did not fix it.
- **Not verified, only hypotheses:** (a) the toy patterns were 12 fixed lines repeated, so a random sparse layer 1 could pick them out; speech spreads events over all lines and over time, and a random layer 1 with a leaky accumulator has nothing to lock onto; (b) the one-packet-per-bus-per-clock limit is overloaded at these event counts; (c) the layer 1 teacher (cells that fire for half of a digit's recordings) is weak because layer 1 fires for everything. None of these was tested.
- 96 lines was NOT run through the network (the template result at equal event count was worse than 48), so the question of whether more input lines revives the deep layers is still open.
**Cautions:** model only; 3 seeds; 300 test recordings; one front-end setting per row; network settings (epochs, teacher size, rate targets) are those of the toy and were not tuned for speech; the template baseline is a reference, not a design.
**Next options:** make layer 1 selective first (more time structure: delays or per-line history; or a front end that gives onset events), test layer 1 alone against the template, then add layers; or place blocks side by side, each taking a band of lines, so that each block sees fewer lines and a cleaner pattern (Alan's block-next-to-block idea, tile spec parallel tiles).

## 56. Blocks side by side on the spoken digits (9 Nov 2026, Alan 22:22)

**Test** (`tools/hexn_busnet_shd_blocks_v1.py`): the 48 lines are cut into NB bands; each band has its own 3-layer network (4 buses x 16 cells, same training, homeostat and pruning as section 55; cells listen to k = min(24, lines in the block) sources while dense); each block makes its own map; the join adds the Jaccard overlaps of the blocks' maps with each digit's teacher map and takes the largest sum. Same 300 test recordings as section 55 (243 from the two unheard speakers), 2 seeds, 30 epochs, chance 10%. The template column is a plain classifier on the same lines and events, as a reference.

| blocks x lines | top per step per block | events per recording | template | joined recall, dense | joined recall, 14 per cell | one block alone | layer 1 cells fired per block (of 64) |
|---|---|---|---|---|---|---|---|
| 1 x 48 | 4 | 45 | 77.0 % | 11.3 % | 10.8 % | 10.8 to 11.3 % | 49 to 51 |
| 2 x 24 | 4 | 84 | 77.7 % | 10.0 % | 10.2 % | 10.4 to 10.6 % | 61 to 62 |
| 2 x 24 | 2 | 47 | 69.7 % | 10.7 % | 10.7 % | 10.0 to 10.2 % | 61 |
| 3 x 16 | 1 | 35 | 68.0 % | 10.0 % | 11.8 % | 11.2 to 11.4 % | 47 to 48 |
| 4 x 12 | 1 | 45 | 75.0 % | 10.8 % | 10.3 % | 9.9 to 10.6 % | 44 to 45 |

**Reading.**
- **Side-by-side blocks did not change the result.** Every setting is at chance (10 to 12%), joined or alone, at every block count tried, while the template on the same events reaches 68 to 78%. Adding the join over several blocks added nothing because no single block carries anything to join.
- Layer 1 stays saturated in every block (44 to 62 of 64 cells fire on every recording; 61 to 62 of 64 with the 24-line blocks). So the fault is upstream of the blocks: layer 1 is not selective on speech, and cutting its input into bands does not make it so. This agrees with section 55, where the cause was left as untested hypotheses.
- Not tested here: 5 or more blocks, blocks of different depth, a join other than summed overlap, any change to layer 1, the teacher, the rate targets or the time structure of the input.
**Cautions:** model only; 2 seeds; 300 test recordings; the networks use settings tuned on the toy patterns and not retuned per block; a null result at these settings does not show that blocks cannot help once layer 1 works.
**Next:** make layer 1 selective on speech on its own (layer 1 alone against the template), then retry layers and blocks on top of it.

## 57. Can layer 1 be fixed on its own? (9 Nov 2026, Alan 22:35, option 1)

**Layer 1 alone** (`tools/hexn_busnet_shd_l1_v1.py`; one layer of 4x16 cells, no feedback, random wiring, NO training, fixed threshold; 45 events per recording; 400 training and 300 test recordings; nearest-centroid classifier on the vector of fire counts; 2 seeds; template on the raw events 77.0%, chance 10%). Cells fired per recording / accuracy %:

| sources per cell K | TH 3 | TH 6 | TH 10 | TH 16 | TH 24 | TH 36 |
|---|---|---|---|---|---|---|
| 4 | 15.6 / 45.0 | 3.7 / 32.2 | 1.0 / 17.7 | 0.1 / 9.8 | 0 / 10.0 | 0 / 10.0 |
| 8 | 28.3 / 48.0 | 8.6 / 38.2 | 2.1 / 25.2 | 0.3 / 12.5 | 0 / 10.0 | 0 / 10.0 |
| 14 | 42.8 / 48.0 | 21.0 / 44.2 | 7.8 / 35.5 | 1.6 / 18.0 | 0.2 / 11.0 | 0 / 10.0 |
| 24 | 55.8 / 49.2 | 41.5 / 48.7 | 24.9 / 45.8 | 9.1 / 35.7 | 1.7 / 23.2 | 0.1 / 10.3 |

**Layer by layer in the full network** (1 seed, K=14 working point, 40 epochs; nearest-centroid on each layer's fire counts, 300 test recordings):

| state | layer 1 | layer 2 | layer 3 |
|---|---|---|---|
| untrained | 49.0 % (41 cells fired) | 28.3 % (34) | 22.3 % (41) |
| trained, dense | 49.3 % (48) | 28.7 % (6.5) | 22.0 % (3.3) |
| trained, pruned to 14 | 50.7 % (48) | 22.0 % (4.4) | 17.7 % (2.1) |

**Layer 1 rate target** (homeostat target 0.40 changed to 0.25 and 0.12; 2 seeds, 40 epochs): layer 1 still fires 47.6 to 48.2 cells; teacher-map recall 12.3 to 14.8 % (combined) against 10 % chance.

**Reading.**
- **Layer 1 is not empty.** With random wiring and no training its fire pattern alone separates the digits at 45 to 49% (chance 10%). Sparser settings lose accuracy (K=14: 48.0% at 43 cells fired, 35.5% at 8). So "make layer 1 sparse" is not free: in this toy sparsity costs information.
- **The information thins on the way up.** About 49% in layer 1, 22 to 29% in layer 2, 18 to 22% in layer 3, before and after training. The teacher-map training makes layers 2 and 3 sparse (3 to 7 cells fired) but does not make them separate the digits better. Pruning to 14 lowered layers 2 and 3.
- **The rate target did not move layer 1** (still 47 to 48 cells fired), so the homeostat is not what holds layer 1 down or up here; the cause was not found. Training of the layer 1 targets and the starting weights are untested suspects.
- **No fix found in the net's own layer 1 within these tests.** A better-than-chance start exists (about 49%), but nothing tried carries it up to layers 2 and 3 or to the teacher-map recall.
**Cautions:** model only; 1 to 2 seeds; the classifier here (nearest centroid on counts) is not the matcher the design uses (Jaccard against teacher maps); one front-end setting (48 lines, top 4 per step).
**Decision (Alan 22:35):** option 1 first, then option 2 if no fix. No fix found, so next is option 2: the existing detector bank in front of the net block (counted detectors giving stable classes), scoped before building.

## 58. The counted detector bank, widened, on the spoken digits (9 Nov 2026, Alan 22:44)

**What was modelled** (`tools/hexn_det_shd_v1.py`, Python only, no RTL): the detector of `tools/hexn_det_v4_model_v1.py` and `hexn_ring_v1.py` in its own arithmetic: one detector per class (10 digits); lane weights +1 / -1 / 0 by the counted rule (lane on: own class +9, other classes -1, saturating at +-31; weight +1 at count >= T, -1 at <= -T, T = min(16, S/2)); total = 10 x (sum of weight x wire), signed; threshold per detector = midpoint of the mean own-class and other-class training totals; answer = largest margin. **Widened**: the built detector hears 12 to 20 wires; here a recording is the folded event matrix (lines x time steps) laid out as 480 to 1,920 wires, with an accumulator wide enough for it. All 1,079 English test recordings (870 from the two speakers never in training; 4,011 training). Chance 10%.

| front end (lines x steps, top per step) | wires | detector, 16 training per digit: all / unheard | detector, all ~400 per digit: all / unheard | accumulator bits needed (with sign) | template reference |
|---|---|---|---|---|---|
| 48 x 20, top 4 | 960 | 68.7 / 71.3 | 76.5 / 79.3 | 11 | 78.0 |
| 48 x 20, top 8 | 960 | 80.0 / 82.9 | 81.7 / 85.1 | 11 to 12 | 85.7 |
| 48 x 40, top 4 | 1,920 | 68.6 / 71.1 | 77.6 / 80.2 | 11 | 77.0 |
| 48 x 10, top 8 | 480 | 76.0 / 78.3 | 80.6 / 83.6 | 11 | 86.3 |
| 96 x 20, top 8 | 1,920 | 67.0 / 68.6 | 79.3 / 81.1 | 11 | 77.7 |

**Reading.**
- **The detector, widened, recognises the digits at about template level** (77 to 82% with all the training, 79 to 85% on the unheard speakers) against 10 to 19% for the net block's teacher-map recall in sections 55 to 57. With only 16 training recordings per digit it still reaches 69 to 80%.
- **What the widening needs:** 480 to 1,920 wires instead of 12 to 20, and an accumulator of 11 to 12 bits including the sign instead of 8 (the built v4 has AW 8; the range note in `hexn_det_v4.v` already says the total must fit). Nothing else in the rule changed.
- **Bands change nothing in accuracy** (4 bands joined by adding margins gave exactly the single-bank answers, as the sum of per-band totals and per-band midpoint thresholds equals the whole-bank total and threshold; this is arithmetic, not a finding). Bands only cut the wires each detector hears (240 instead of 960).
- 96 lines did better than 48 only when all the training was used (79.3 against 77.6 at equal wires), and worse with 16 per digit.
- **Size, as extrapolation only:** the file's figure is 29 + 13 LUT4 per lane from synthesis at 12 to 20 lanes. At 960 lanes per detector and 10 detectors that is about 125,000 LUT4. This extends the figure about 50 times beyond where it was measured; it is NOT a synthesis result, and weights that are loaded at run time and lanes shared in time could change it. It would not fit the Tang (20,736 LUT4); the Kintex card has 597,200 sites.
**Cautions:** model only; one training order; the front end (fold and top-N per step) is my own and not the real sensor path; the template reference uses the same events. This tests the detector on its own. The detector feeding the net block has NOT been tested.
**What this does and does not show:** the existing detector design, widened, handles this data. It does not show that the net block adds anything on top of it; the next step is to decide what the net block takes from the detector (open question for Alan, below).
**Open (Alan):** what the detector hands to the net block. Candidates: (a) the 10 margins per band as events on lines; (b) detectors on short time windows (local sub-patterns) as layer 1 of the net; (c) detector margins quantised to bins 0 to 11 into the batch judge, as in the existing picture.

## 59. Short-window detectors as layer 1 of the net block (9 Nov 2026, Alan 22:50, option 2)

**Build** (`tools/hexn_det_net_v1.py`, Python model only): the folded recording (48 lines x 20 steps, top 8 per step) is cut into W windows; each window has its own detector bank (10 detectors, counted rule, section 58) hearing that window's wires, trained with the recording's digit as the label of every window. A window sends an event for each of its TOP best detectors with a margin above zero (input line = window x 10 + digit, at the window's clock). The bus network (3 layers of 4x16, section 53 training and pruning) takes these W x 10 lines. Detectors trained on one half of the training recordings, the network on the other half. Same 300 test recordings as before (243 from unheard speakers), 2 seeds, 40 epochs, cells start at threshold 3.

| windows x steps | top per window | events per recording | detectors summed | window-winner vote | net recall, dense (combined / layer 2) | net recall, 14 per cell (combined / layer 2) | cells fired L1 / L2 / L3 (14 per cell) | packets dropped (14 per cell) |
|---|---|---|---|---|---|---|---|---|
| 5 x 4 | 2 | 9.4 | 85.7 | 57.0 | 32.0 / 34.3 | **35.2 / 38.5** | 18.7 / 3.9 / 2.3 | 0.8 % |
| 4 x 5 | 3 | 10.3 | 85.7 | 55.0 | 28.3 / 28.5 | 34.5 / 35.0 | 29.5 / 4.4 / 2.6 | 11.1 % |
| 5 x 4 | 3 | 12.8 | 85.7 | 57.0 | 27.0 / 29.5 | 27.5 / 28.7 | 26.6 / 4.7 / 1.8 | 4.3 % |
| 5 x 4 | 5 | 15.7 | 85.7 | 57.0 | 22.7 / 23.5 | 29.3 / 29.2 | 30.8 / 4.8 / 2.4 | 12.1 % |
| 10 x 2 | 3 | 24.3 | 86.0 | 51.0 | 21.0 / 22.0 | 27.8 / 27.3 | 26.0 / 5.5 / 2.7 | 0.4 % |
| 10 x 2 | 5 | 30.9 | 86.0 | 51.0 | 21.0 / 23.3 | 23.2 / 24.3 | 28.1 / 5.0 / 3.2 | 1.2 % |
| 10 x 2 | 1 | 9.0 | 86.0 | 51.0 | 10.2 / 10.2 | 10.0 / 10.0 | 0 / 0 / 0 | 0 % |

**Reading.**
- **The detector in front helps the net block a lot:** teacher-map recall rises from 10 to 19% (sections 55 to 57, raw folded input) to 28 to 38% at the best settings (chance 10%). Layer 1 is no longer saturated at 41 to 50 of 64 cells (19 to 31 cells fired) and packet loss at the best setting falls from 28 to 56% to 0.8%.
- **The net block still does far worse than the detectors it sits on:** 35 to 38% against 86% for the same windows summed, and 51 to 57% for a plain vote of the windows' winners. The sequence of winner events carries less than the margins do, and the teacher-map recall loses more still. Nothing here shows that the net block adds recognition on top of the detector; in this test it removes much of it.
- **More events did not help** (recall falls from 35 to 23 as top 2 goes to top 5 at 5 windows; the dropped-packet share rises to 12 to 19% in some rows). The one row with 9 events on 100 lines (10 windows, top 1) starved the network: no cell fired at the starting threshold of 3.
- Not tested: graded margins (weights from margin size), a teacher other than the 5-cells-per-layer maps, more seeds, feedback on and off, 96 lines.
**Cautions:** model only; 2 seeds; 300 test recordings; weak labels (the digit as the label of every window); my own front end; the net block kept the toy's settings (apart from the starting threshold of 3); the best row was picked from seven.
**Where this leaves the join:** the detector bank works on speech (section 58) and makes the net block usable (this section), but the net block's map recall is the weak link, not the input. The question for Alan is what the net block is for in this chain: if it is to recognise, the detectors alone already do better; if it is to hold maps, history or paths over the detectors' outputs (layer 2 and 3 of the nested picture), that needs a test of that job, not of teacher-map recall.

## 60. Sequence test: predict the next window's winner (9 Nov 2026, Alan 22:59)

**Test** (`tools/hexn_det_net_seq_v1.py`, Python model only): the same 5 window detectors as section 59 (top 2 events per window). After the first p windows (p = 1 to 4) predict the winning digit of window p (the detector with the largest margin there). The bus network (teacher map per target digit, section 55 training, 40 epochs, 2 seeds) sees only the events of windows 0 to p-1. Reference predictors are count tables built on the same training half, as a layer 2 history store would: (U) most common winner at that position, no history; (R) repeat the last winner; (B) bigram, given position and last winner; (T) trigram, given position and the last two. 1,200 test items (the same 300 test recordings x 4 prefixes). Chance 10%.

**Check before reading:** window 4 (the last fifth of the second) is nearly empty: 88% of recordings have no events in it (mean 0.6 events on, against 26 to 29 in windows 0 and 1), and its winner is digit 1 in 3,537 of 4,011 training recordings, which is a default, not a prediction. So p = 4 items are degenerate (U scores 85.3% there) and are left out of the main figures below. The cause (recordings end before about 0.8 s) was checked by counting events; it was not checked against the audio.

| predictor | p = 1 | p = 2 | p = 3 | mean of p = 1 to 3 | all four positions (incl. degenerate p = 4) |
|---|---|---|---|---|---|
| U: position only, no history | 6.7 | 14.0 | 21.3 | 14.0 | 31.8 |
| R: repeat the last winner | 39.0 | 32.7 | 22.7 | 31.5 | 28.1 |
| B: bigram (position, last winner) | 34.3 | 32.7 | 35.7 | 34.2 | 48.1 |
| T: trigram (position, last two) | 34.3 | 36.0 | 33.3 | 34.5 | 47.5 |
| bus network, dense | 13.7 | 15.5 | 10.2 | 13.1 | 13.8 |
| bus network, 14 per cell | 15.3 | 14.8 | 11.5 | 13.9 | 14.0 |

**Reading.**
- **History helps, and a count table gets it.** Bigram and trigram count tables predict the next window's winner at about 34% on the informative positions against 14% with no history, so the sequence carries information (a digit's early windows say something about its later ones).
- **The bus network did not learn it:** 13 to 14% on the informative positions, the same as the no-history guess (14.0) and below repeat-last (31.5) and the count tables (34). With these settings the network's map does not hold the history that a layer 2 style count store holds.
- The target labels are the detectors' own window winners, which are noisy (a window-winner vote is right on the digit 51 to 57% of the time, section 59), so a ceiling well below 100% applies to every row.
**Cautions:** model only; 2 seeds; 300 test recordings; training prefixes per target digit very uneven (266 to 2,422); weak window labels; the bus network kept the toy's settings and the teacher-map readout; the network was not tuned for this job; one window layout (5 windows, top 2).
**Where this leaves the layers:** on this data the working pieces are the detector bank (section 58) and a counting history store (this section), which matches the earlier nested picture (layer 1 detectors, layer 2 history and paths per sensor, layer 4 predictive work on top of that). The bus network's role in that chain is the part that has not shown a gain in sections 55 to 60. Open for Alan: stop testing the bus network on this data and build the chain from the detector and the count store, or test the network on a job that suits its parallel, event-driven form.
