# Model 2: the detector system and the speech chain

Base document, written 12 Nov 2026 for Alan. It gathers what is already recorded; nothing was re-measured for it. Every figure is copied from the source named beside it. Tags: **[card]** measured on a board with Alan's run; **[sim]** simulation; **[model]** Python only; **[estimate]** a tool's estimate (place-and-route clock and size figures are estimates, never silicon timing).

## 1. What it is

The part of Hex-N that is proven on real data and on real hardware. A detector counts how well what arrives fits a taught pattern and names the best-fitting class. It started as layer 1 of the layered model (Model 1) on a handful of sensor wires, and was widened in November 2026 into the **speech chain**, which recognises spoken digits on the Kintex card.

## 2. The counted detector: how it is built and how it works

- **A detector** has one weight per input wire: +1 (should be on), -1 (should be off) or 0 (does not matter). It adds the weights of the wires that are on and compares the total with a threshold. A bank holds one detector per class; the largest total above its threshold wins, otherwise the answer is "no class".
- **Teaching is counting, not searching.** One pass over labelled examples: for each wire that is on, the count for the example's own class goes up and the counts for the other classes go down a little; the counts are clipped; a count above a level becomes +1, below the negative level -1, between them 0. The threshold is the midpoint between the detector's average total on its own class and on the others. (`tools/hexn_det_shd_v1.py`, direction doc section 58.)
- **No multipliers.** Weights are three-valued, so the hardware only adds and subtracts.

**On the Tang Nano 20K (the original, 12 to 20 wires per bank):**

| Fact | Figure | Source |
|---|---|---|
| Minimal detector size | 150 / 224 / 268 LUT4 at 12 / 18 / 20 wires | `LAYER_INTERFACES_v4.md` (21 Oct) |
| Held-out accuracy, 8 classes | 82 to 86% of the template-rule ceiling | same |
| Recorded light and potentiometer data | 1.000 | same (27 Oct) |
| 7-detector bank, board against simulation | 5,250 of 5,250 test samples equal [card] | `README_OLD_v1.md`, `HEXN_DESIGN.md` section 4a |
| 19 detectors at 18 wires on the Tang | 15,730 of 20,736 LUT4 (75.9%) | `LAYER_INTERFACES_v4.md` (22 Oct) |

The detectors, the batch judge and an ESP32 front end make up the **open unit** on the Tang, confirmed on the board stage by stage (`OPEN_UNIT_v1.md`, `FRONT_END_UNIT_v1.md`).

**Cleaning the class stream** (direction doc sections 18 to 26, models and recorded sensor data): carry-forward fills short "no class" gaps; a hold counter steadies a chattering sensor; which one is right belongs to the sensor type, and a try-both method lets the system pick on unlabelled data.

## 3. The speech chain: how it is built

**Data.** The Heidelberg spoken digits (SHD): the ten English digits, 4,011 training and 1,079 test recordings; 870 of the test recordings are from two speakers never heard in training (section 55).

**Front end (on the PC, `tools/hexn_shd_frontend_v1.py`).** The recording's 700 channels are folded onto 48 lines; one second is cut into 20 time steps; in each step the 8 busiest lines send one event. A recording becomes about 83 events.

**The chain (`rtl/hexn_speech_chain_v1.v`, model `tools/hexn_chain_hw_v1.py`):**
1. **Window detectors.** The 20 steps are cut into 5 windows of 4 steps. Each window has 10 detectors, one per digit, over 192 wires (4 steps x 48 lines). The detectors are event-driven: each event reads one word of weights for all ten detectors and adds it to ten accumulators (960 weight words in all).
2. **Count tables.** At the end of a window the best detector gives the window's class (or none). Tables of counts, made from training recordings, say how likely each class is at that position after the previous class, for each digit (605 words).
3. **Decision.** Each digit's score = its path through the tables + its summed detector margins (shifted, no multiplier). The best score is the answer; an early-stop flag is raised when the best digit leads the second by a set gap.

**Behind the base controller on the Kintex card** (`sub/verilog/hexn_base_ctl_v6.v`, generator `tools/hexn_kxbase_v6.py`): the chain sits beside the two pattern arrays, the batch judge and the stores, reached over JTAG. Commands `k` (write one setting), `e` (send events), `u` (read a result), and for the on-chip event memory `w` (fill), `g` (replay at the chain's own speed), `v` (read results). Nothing about the speech task is in the bitstream: settings and recordings come from the PC (`tools/hexn_chain_host_v1.py`, `_v2.py`, `_v3.py`).

## 4. Results

**On the card [card] (11 Nov 2026, direction doc sections 71 to 85):**

| Test | Result |
|---|---|
| Kit with 300 recordings baked in, exact count read over JTAG | 262 of 300 (87.3%), equal to the Python reference and the simulation |
| The same 300 with settings and events sent from the PC, command by command | 262 of 300; 4.0 s; 74 recordings per second over JTAG |
| The same 300 replayed from the on-chip event memory, three times | 262 of 300 each time; **86,079 clocks counted on the chip, equal to the simulation to the clock** |
| The whole test set, 1,079 recordings, three batches | **936 right (86.7%)**; every digit's count equal to the reference; 309,050 clocks (286 per recording) |
| Link | 0 bad captures and 0 resends in every run |

Computed from the clock count at the board's nominal 50 MHz (not separately timed): about 174,000 recordings per second, against 74 per second over JTAG.

**Sizes and clock [estimate, nextpnr on the XC7K480T of 597,200 sites]:**

| Design | LUT sites | Flip-flops | Clock estimate after routing |
|---|---|---|---|
| Speech kit alone | 2,861 (0.5%) | 1,213 | 185.56 MHz |
| Base v6: two pattern arrays, batch judge, stores, chain, event memory | 23,346 (3.9%) | 16,187 | 90.68 MHz |

All ran at the 50 MHz board clock. The chain's real clock limit has not been measured.

**How good the answers are [model, equal to the card]:**

| Fact | Figure | Source |
|---|---|---|
| Right after window 1 / 2 / 3 / 4 / 5 (300 recordings) | 68.7 / 85.0 / 87.3 / 87.0 / 85.3% | section 63 |
| With events dropped at random: 0 and 10% / 30% / 50% / 70% | 87.3 / 80.7 / 68.7 / 44.0% | section 63 |
| Per digit, whole test set | 0: 98/103, 1: 68/108, 2: 96/105, 3: 76/102, 4: 96/116, 5: 91/110, 6: 105/109, 7: 102/109, 8: 111/114, 9: 93/103 | section 85 |
| The largest single confusion | "one" answered as "nine": 36 of its 40 errors | section 93 |
| Wrong answers where the right digit was second best | 94 of 143 (66%) | section 93 |
| On its own training recordings | 3,129 of 4,011 (78.0%) | section 93 |

## 5. What was tried to lift it, and did not work

| Attempt | Result | Source |
|---|---|---|
| A memory of whole recordings (window codes) on top of the chain | 79 to 81% against the chain's 86.7%; both wrong on 117 of the 143 errors | section 99 |
| A second look between the top two digits | repaired 18, spoiled 21 | section 99 |
| Several templates per digit and window (2 to 6) | training set up to 85.8%, test set DOWN to 76.6 to 83.5% | section 100 |
| The neural bus network on the same data | 10 to 19% against 10% chance | section 55 |

Reading (Alan, 12 Nov): the detector does not only clean the data, it processes it, so the work is done before anything above it sees it. The untested candidates for a higher score are the front end (how sound becomes events) and the way templates are made.

## 6. Limits

- The front end runs on the PC; there is no live sound path into the card. Input is JTAG only; a real data port needs another card and PC (ledger, 11 Nov 19:04).
- One dataset, one front-end setting, one split of the training data.
- German digits in the same files have no detectors.

## 7. Where the detail is

`HEXN_SPEECH_CHAIN_KINTEX_v1.md` (placement note with every update), `HEXN_KINTEX_BASE_PICTURE_v1.md` (the base), kits `fpga/ypcb/hexn_speech/`, `hexn_speech2/`, `hexn_arr/`; direction doc sections 55 to 63, 70 to 76, 81 to 85, 93, 99, 100; tests `tests/vm/test_hexn_speech_chain_v1.py`, `test_hexn_base_v5_chain_v1.py`, `test_hexn_base_v6_evram_v1.py`, `test_hexn_chain_host_v3.py`.
