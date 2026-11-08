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
