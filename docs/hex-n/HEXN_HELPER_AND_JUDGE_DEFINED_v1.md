# The helper and the batch judge: what each does, where its data comes from, where it goes, where it fits

Draft v1, 5 Nov 2026 (evening), written from Alan's account (20:50 to 20:59) and from our own files. **For Alan to correct.** Every line is tagged **[file]** (read from our files, with the file named), **[Alan]** (his statement, not checked against every row) or **[open]** (nobody has defined it yet). Nothing here is new hardware; it fixes words so the next steps can be built on them.

## 1. The picture (Alan, 20:56)
```
 world → layer 1 (counted detectors, bins 0..11) ─┬→ helper layers 2 to 4 (history, combine, choose)
                                                  └→ batch judge (scores the same layer-1 output)
 hex cell arrays: the additional layer now being worked on                                   [Alan]
```
The file `docs/hex-n/LAYER_INTERFACES_v4.md` draws the layers as nested (each inside the one before, the helper as the heart); the batch scorer's header says it scores "layer-1 bin words", so it takes layer 1's output. [file]

## 2. The batch judge (hexn_scorer_v3)
| | |
|---|---|
| **Job** | Decide between two classes for one set of layer-1 bins. [file: `SCORER_v1.md`] |
| **Data in** | One 32-bit word = eight sensors' bins, each 0 to 11, produced by layer 1. Weights come in as LOAD words (class, address = sensor and bin, signed 8-bit) and one BIAS word. On the Tang the words came from the ESP32 over SPI. On the Kintex base they come from the host, from the data RAM, or in AFTER mode from the selected array's output words (each nibble clamped to 11). [file] |
| **Weights** | Two tables of 128 whole-number weights plus a bias. They are rounded log-likelihoods worked out on the HOST from data (the table refresh), then loaded. [file: `SCORER_v1.md`, `hexn-weights-save-load.md`] |
| **Learning** | In batches on the host, outside the chip. Nothing on the chip changes the weights while it scores. [file] |
| **Data out** | One result word: decision bit, class-1 score, class-0 score. On the Tang: back to the ESP32 over SPI. On the Kintex base: a record in the results RAM, and the decision bit picks the library slot that `Z` loads. [file] |
| **Saved as** | A weight set in the weight store (257 words, judge's own format), optionally tied to a library slot. Simulation only so far. [file] |
| **Where it fits** | Beside the helper layers, reading layer 1's output [Alan, with the scorer's header]. **What consumes its decision in the layered system is [open].** |
| **Status** | Ran on the Tang board (1 Nov) and on the Kintex card (5 Nov). [file] |

## 3. The helper (heart of the nested unit) and its neural judge
| | |
|---|---|
| **Job** | In `LAYER_INTERFACES_v4.md`: a judge that scores a position or situation, plus the ideas of key maker and fallback. The judge's score goes to layer 4; similarity and suggestions go to layer 3 on their own channel. [file] |
| **Two forms** | (a) the position judge: 127 inputs, 64 hidden units, about 8,000 weights: Python only. (b) the layer-1 judge: 7 inputs (counts of pure lines: 1, 2, 3 counters for each side, and parity), linear or 7-16-1: Python, and in whole numbers as `rtl/hexn_neural_v1.v` (7 inputs of 6 bits, 8 weights of 16 bits, one multiplier, tanh table): simulated, in no top-level design. [file] |
| **Data in** | Both layers' state and positions (form a); counts from layer 1 (form b). [file] |
| **Learning** | On the chip in the RTL form: evaluate, then learn from a teacher value (error times gain, weights nudged). The teacher in the Python tests was layer 4's search plus layer 3's history (the 'training module', 31 Oct). [file] |
| **Data out** | Judge score to layer 4; similarity and suggestions to layer 3; the end-of-game reward comes back to show how far to follow it. [file] |
| **Where it fits** | Inside the helper layers, below layer 4. On 30 Oct (20:10) it was moved off the critical path for the sensor-control direction (archived, not deleted). [file] |
| **Status** | MODEL plus RTL in simulation. Not on any card. Not in the Kintex base. [file] |

## 4. What is NOT defined yet (needs Alan)
1. **What reads the batch judge's decision** in the layered picture (layer 3, layer 4, an output stage, or only the host). [open]
2. **How hex array output becomes bins** for the batch judge, or counts for the neural judge: the base only clamps array output nibbles to 11. [open]
3. **Whether both judges stay**, or the batch judge takes over part of the neural judge's job (Alan said 'replaced in part'; no row records the decision). [open]
4. **Teacher source** for the neural judge on a run: a label stored with the data, the batch judge's own decision, or a rule. [open]
5. **Which of the two judges the weight store and the job list should serve first.** The store serves the batch judge today; the neural judge needs a small read-out walker (8 words per set). [open]
6. **How the hex arrays map onto the layer numbering.** [open]

## 5. Not claimed
No hardware path exists between layer 1, the helper layers and the Kintex base. The batch judge's learning is on the host; the neural judge's learning has only been simulated. The 'replaced in part' statement and the 'combined and removed' statement for layers 2 to 4 are Alan's account; the files show the layers combined into a Python module and the neural side moved off the critical path, and no row records a removal or a replacement.
