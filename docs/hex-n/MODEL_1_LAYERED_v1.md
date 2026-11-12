# Model 1: the layered model (layers 1 to 4, the helper and the batch judge)

Base document, written 12 Nov 2026 for Alan. It gathers what is already recorded; nothing was re-measured for it. Every figure is copied from the source named beside it. Status words: **BUILT** = logic that passes in simulation (where it also ran on a board, that is said); **MODEL** = Python only; **IDEA** = written down only.

## 1. What it is

The first Hex-N model: one unit made of layers nested inside each other. The outside layer meets the sensor wires; each layer hands a cleaner, smaller answer inward; the innermost parts look ahead and judge. It is the model that played Connect Four and draughts, and its layer 4 is the part that does inference: imagining what may happen next and choosing.

```
 world --> [ layer 1: counted detectors, one bank per sensor ]
              [ layer 2: history and paths, per sensor ]
                 [ layer 3: the same, across several sensors ]
                    [ layer 4: looks ahead, sets goals ]
                       [ helper: a small network that judges positions ]
   beside them: the batch judge (scores layer 1's output with weights worked out on the PC)
   through them: the memory tier (shared key/value storage)
```

Source for the picture and the table below: `LAYER_INTERFACES_v4.md` (30 Oct 2026), which copies each figure from a dated row of the ledger `HEXN_DESIGN.md`.

## 2. The layers: what each does, how it is built, where it stands

| Layer | What it does | How it is built | State |
|---|---|---|---|
| **1 Detectors** | Turns coded sensor wires (12 to 20 per bank) into a class number or "no class", held steady by a hold counter | The counted detector: each wire's weight is counted in one pass over examples (+1, 0 or -1), a threshold is counted, no search | **BUILT**, run on the Tang Nano 20K and the Kintex card. See Model 2 |
| **2 History, per sensor** | Remembers what followed what for one sensor; predicts the next event; says ok, contradiction, novel or start | A store of event histories with counts (store v5: address index plus dense heap, 4-bit events) | **BUILT**. Core v9 with store v5 ran on the Tang and passed (285 frames, 61 answers checked, 15 rewards, 27 Oct). 12,828 of 20,736 LUT4 (62%), 14 of 46 block RAMs |
| **3 History, across sensors** | The same, keyed by the classes of several sensors at one moment; gives ranked possible next moments with weights | The same store idea with a tuple of classes as the key | **MODEL** (`tools/hexn_layer3_v1.py`); hardware plan in `LAYER3_HW_v1.md`, no logic written |
| **4 Strategist** | Grows a tree of imagined futures from layer 3's predictions, prunes unlikely paths, suggests a move | Expectimax search with a path-probability cutoff; blends its learned model with worst-case play by confidence | **MODEL** (Connect Four, draughts) |
| **Helper** | Judges a position when the search has to stop | A small network: 127 inputs, 64 hidden units, about 8,000 weights | Judge: **MODEL**. Other roles (key maker, fallback): **IDEA** |
| **Batch judge** | Scores 8 sensor readings (bins 0 to 11) with two tables of 128 weights and a bias; gives a prediction bit and two scores | `fpga/verilog/hexn_scorer_v3.v`; weights worked out on the PC and loaded | **BUILT**, runs on the Tang and in the Kintex base |
| **Memory tier** | Shared key/value storage on three levels | PUT / GET / FLUSH commands | **BUILT**, proven on the Kintex card against the reference model: 2,000,000 steps, 0 wrong (30 Oct). Not joined to the layers |

## 3. How it works, in plain terms

1. A sensor reading is coded onto a handful of wires. Layer 1's detectors each hold a pattern of "this wire should be on, this one off, this one does not matter"; the detector whose pattern fits best names the class.
2. Layer 2 keeps count of which class followed which, for each sensor, so it can say what usually comes next and notice when something does not fit.
3. Layer 3 does the same for several sensors taken together (a "moment").
4. Layer 4 uses those counts as a model of the world: it imagines several steps ahead, weighs each path by how likely layer 3 says it is, and picks a move. When it is unsure of its model it falls back to assuming the worst case.
5. The helper is a small trained network that says how good a position looks, so the search can stop earlier.

## 4. Results

**Games (all Python models; the game is the test bed, nothing ran on a board).**

| Test | Result | Source |
|---|---|---|
| Connect Four, Hex-N search against a plain search of the same style | The plain search was better | ledger 30 Oct 21:20; `LAYER_INTERFACES_v4.md` |
| Draughts, first result | The plain search was better | ledger 30 Oct 22:50 |
| Draughts, confidence weighted by layer 3's hit rate | The Hex-N search EQUALS the plain search at depth 3 and 4 (.47 against .48, .72 against .70). No gain from learning shown, as positions seldom recur. About 5 times the time per move in Python | ledger 31 Oct 09:40 |
| Connect Four against opponents with habits | The learned model predicts about 60% of replies and still LOWERS the score by 0.04 to 0.18 against worst-case play: acting on a prediction that is wrong 40% of the time costs more than it earns | ledger 31 Oct 10:30 |
| Helper as position judge, Connect Four | With the judge, depth 3 matched or beat the hand score at depth 4 with about a sixth of the positions (depth 3: 0.77 / 0.83 against 0.73 / 0.71) | ledger 30 Oct 17:45 |

**Against simple designs** (Alan's rule: equal is the lower limit). Cheap filter on one steady sensor: Hex-N not better. Plain minimax in Connect Four: plain search better. Plain alpha-beta in draughts: equal at depth 3 and 4 with the hit-rate blend. (`LAYER_INTERFACES_v4.md` section 5 and the 31 Oct rows.)

**Layer 4 on real speech (10 Nov, direction doc section 62).** Used to predict the next window of a spoken digit and to decide early: prediction 46.6% against 43.6% for the count table alone (upper bound with the true digit known 49.1%); deciding early worked but no better than layer 1's own margin rule. Isolated digits give a strategist nothing to choose between.

## 5. Limits and open points

- Layers 3 and 4 and the helper have no hardware, so there is no size or speed figure for the whole unit.
- Learning is on the PC. Nothing changes its own weights on the chip (the layer 1 local rule and the neural judge `rtl/hexn_neural_v1.v` are simulated only).
- The games showed the cost of trusting a learned model that is often wrong; the hit-rate blend makes the model safe, not better.
- The direction decided on 30 Oct 2026: Hex-N is a sensor-control device; the neural side came off the critical path; games stay as the test bed.

## 6. Where the detail is

`LAYER_INTERFACES_v4.md` (the nested unit), `HEXN_HELPER_AND_JUDGE_DEFINED_v1.md` (helper and judge), `LAYER3_HW_v1.md` (layer 3 hardware plan), `SCORER_v1.md` (batch judge), `HEXN_DESIGN.md` rows of 29 to 31 Oct 2026 (games), direction doc sections 8 to 26 (teaching the batch judge, cleaning the class streams) and 60 to 62 (layer 4 on speech).
