# Model 3: the neural bus network (cells on shared buses)

Base document, written 12 Nov 2026 for Alan. It gathers what is already recorded; nothing was re-measured for it. Every figure is copied from the source named beside it (section numbers are sections of `HEXN_DIRECTION_SCOPING_v1.md`). Tags: **[sim]** Python model; **[rtl]** logic checked against the Python model in simulation; **[estimate]** a tool's place-and-route figure, never silicon timing; **[card]** done on the board with Alan's run.

## 1. What it is

Alan's neuron-like cell (sections 27 to 31, 8 Nov 2026): a cell gathers small signed pushes from the cells it listens to, leaks a little all the time, fires when it passes its own level, then rests. The cells sit in layers on small shared buses. What the network produces is not a single answer wire but a **map**: the set of cells that fired during a run. A matcher compares the live map with stored maps and names the nearest one, or the nearest two.

It works well on made-up test patterns and has been built and loaded on the Kintex card as logic. On real speech its maps carried no usable information (section 6).

## 2. How it is built

**The cell (hardware form, `sub/verilog/hexn_bnet_bus_v2.v`):** a 6-bit signed accumulator; a 4-bit signed weight for each source it listens to, read from the bus's shared table; its own 4-bit threshold; a rest (refractory) counter; a leak of 1 on a shared tick while the accumulator is positive; an 8-bit fire counter. No multipliers.

**The bus.** A bus carries ONE packet per clock: the number of a source that fired. Every cell on the bus looks that number up in the table and adds its weight for it. A layer is a few buses (4 buses of 16 cells, or 8 of 8); the model has 3 layers, 64 cells each, 192 cells, fed by 48 input lines.

**Between layers (`hexn_bnet_ser_v1`, `hexn_bnet_tbus_v5`):** a serialiser per group of sources sends one waiting source per clock in rotation; in front of each bus a merger holds a small queue per feeding group and a round-robin arbiter passes one packet per clock. A full queue drops the packet and counts it. Layer 3 also feeds back into layer 1.

**The map and the matcher (`hexn_bnet_map_v1`):** records which layer 2 and 3 cells fired; compares with each stored map, one per clock, by overlap (shared cells over all cells, done without division) and keeps the best two.

**Training is on the PC; the chip only holds numbers and counts fires.** The steps, each of which was tested (sections 34 to 40):

| Step | What it does | Evidence [sim] |
|---|---|---|
| Map feedback (teacher) | Each pattern is given a target map (5 cells per layer). A target cell that did not fire has its weights from active sources raised by 1; a cell that fired outside the target has them lowered. Weights stay within a ceiling of the starting wiring | Untrained recall 12% (chance); trained 58 to 75% (section 34) |
| Self-set threshold | After each round, a cell firing more often than its layer's target rate raises its threshold by 1, less often lowers it | Removes most of the dependence on the starting threshold: recall at 10% dropped ranged 43 to 95% with fixed thresholds across starts, 76 to 91% self-set (lean net); best row 96 / 95 / 83 / 57 (section 39) |
| Start dense, then prune | Train with 24 sources per cell, keep the largest weights down to 14 / 10 / 10 per cell (2,176 connections), retrain with the thresholds still adapting | Pruned: 95 / 90 / 75 / 44 with 42% of the connections; unpruned dense: 97 / 95 / 87 / 55; lean from the start: 89 / 82 / 59 / 33 (section 40) |

(Recall figures are percent right with 10 / 30 / 50 / 70% of the input events dropped; 8 patterns; chance 12.5%.)

## 3. How it works, in plain terms

1. An input event on one of the 48 lines is sent as a packet on the layer 1 buses.
2. Every cell that listens to that line gets a small push up or down. Pushes that arrive close together add up; a slow trickle leaks away.
3. A cell that passes its own level fires: its number goes out as a packet to the next layer, and it rests for a few clocks.
4. After the run, the cells that fired in layers 2 and 3 are the map. The matcher says which stored map it is nearest to.

## 4. Results on the test patterns [sim]

| Fact | Figure | Source |
|---|---|---|
| Recall of the stored pattern, working design (pruned, self-set thresholds), combined layer 2 + 3 map | 95 / 90 / 75 / 44 | sections 40, 49 |
| Layer 2 map alone / layer 3 map alone | 97 / 92 / 76 / 46 and 78 / 65 / 50 / 25 | section 49 |
| Five layers: layer 2 / 3 / 4 / 5 | 83/81/68/40, 63/58/45/27, 46/44/34/20, 42/35/26/19 | section 50 |
| Cells firing per run by layer, 5-layer net | 43, 4, 2, 2, 1 | section 50 |
| Mixture of two patterns: the two best maps are exactly the two | 10 of 100 untrained (dense maps); 15 to 20% after training | sections 32, 34 |
| Feedback (layer 3 to layer 1) | Runs away at weight +2 or more unless half the links are inhibitory or the leak is every clock; no measured benefit to recall | sections 32, 35 |
| Competition between cells (a firing cell holds its neighbours down) | Never better: mildest form unchanged on layer 2; first-to-fire across a layer 78 / 71 / 62 / 38; trained with it 55 / 51 / 47 / 32 | section 96 |

**What the results say.** Depth does not help: the first layer after the input carries the pattern and each deeper layer is worse, because fewer and fewer cells fire. A pattern is a set of cells that must fire together, so making cells compete hurts. The map is good at one thing: recognising a known pattern from a damaged version of it.

## 5. In hardware

| Build | LUT sites (of 597,200) | Flip-flops | Clock after routing | State | Source |
|---|---|---|---|---|---|
| Tang Nano 20K, 24 cells | 12,376 LUT4 of 20,736 (59%) | 2,225 | 47.5 MHz | [estimate]; 48 cells do not fit | section 45 |
| Kintex, 2 buses x 8 cells (48 cells), v2 | 7,313 (1.2%) | 2,071 | 84.3 MHz | [estimate] | section 47 |
| Kintex, 4 buses x 16 cells (192 cells), v2 | 34,777 (5.8%) | 9,081 | 58.1 MHz | [estimate]; **loaded on the card, runs** [card] | sections 47b, 71 |
| Kintex, 8 buses x 8 cells (192 cells), v2 | 70,994 (11.9%), 200 multiplier blocks | 15,419 | 49.4 MHz, fails 50 | [estimate] | section 47b |
| Kintex, 8 x 8, v5 (no multipliers, register after the arbiter) | 43,741 (7.3%) | 15,595 | **65.6 MHz, passes 50** | [estimate]; **loaded on the card, runs** [card] | section 72 |

- The logic is checked clock for clock against the Python model in simulation (`tests/vm/test_hexn_bnet_net_v3.py`, `_v4.py`, `_v5.py`) [rtl].
- "Loaded, runs" means the design configured and its heartbeat counter ran at the 50 MHz board clock. The test wrapper drives the network from a random source and folds its outputs to one light, so the card runs say nothing about whether the network computed correctly.
- v5 adds one clock of delay per hop; the recall results above were not re-run with that extra clock (section 72).
- No controller commands exist for the network, and no PC program to load weights into it: it is not joined to the base (`HEXN_NEURAL_BUS_DESIGN_v1.md` section 4, proposal).
- One tile of four such blocks would be about 175,000 sites, 29% of the chip, by multiplying the 8 x 8 v5 build by four; not built (Alan's question of 12 Nov 08:45).

## 6. On real data [sim]

Spoken digits (section 55; same data and front end as Model 2): **recall 10 to 19% against 10% chance**, while a plain template on the same events reaches 69 to 86%. Layer 1 fires 41 to 50 of its 64 cells on every recording and 28 to 56% of packets are dropped, so layer 1 does not separate the digits. What was tried after that:

| Attempt | Result | Source |
|---|---|---|
| Blocks side by side, each on a band of lines | Every setting at chance (10 to 12%) | section 56 |
| Layer 1 looked at alone | Untrained layer 1 separates the digits at 45 to 49%, but the information thins on the way up: 22 to 29% in layer 2, 18 to 22% in layer 3 | section 57 |
| Detectors in front as layer 1 | Recall rises to 28 to 38%, still far below the detectors it sits on (86%) | section 59 |

As a novelty detector and on damaged recordings it was also at chance on this data (section 66: 0.505 where 0.5 is chance; detectors 0.723).

The reasons were not established. Three guesses are recorded in section 55 and none was tested: the test patterns were a few fixed lines, which random wiring can pick out, where speech spreads over all lines and over time; one packet per bus per clock is overloaded at speech event rates; the layer 1 teacher is weak because layer 1 fires for everything.

## 7. Limits and open points

- Proven only on made-up patterns with target maps handed out by a teacher (the easy case: targets do not overlap).
- No learning on the chip.
- Not compared against a plain lookup of the same test patterns (section 66 says so), so "better than a table" is not shown.
- Parked by Alan on 11 Nov 2026 unless a new application turns up (section 92). The parts that grew out of it, the stored maps beside the cells and everything above them, are Model 4.

## 8. Where the detail is

`HEXN_NEURAL_BUS_DESIGN_v1.md` (the merged design, part by part), `HEXN_TILE_SPEC_v1.md`, direction doc sections 27 to 57, 65 to 69, 72, 96; tools `tools/hexn_busnet_v1.py`, `hexn_busnet_train_v1.py`, `hexn_busnet_homeo_v1.py`, `hexn_busnet_prune_v1.py`, `hexn_busnet_hw_v3.py`, `hexn_busnet_compete_v1.py`; logic `sub/verilog/hexn_bnet_*.v`; card kit `fpga/ypcb/hexn_bnet/`.
