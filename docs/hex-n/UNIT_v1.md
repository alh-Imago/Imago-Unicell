# Hex-N unit v1: the whole unit with every component in (31 Oct 2026)

New file. `LAYER_INTERFACES_v4.md` (30 Oct) stays untouched; this file is the next step of it: the same nested unit, now with the parts that were built or measured on 31 Oct, a block-by-block size table and a stated fit on the Tang Nano 20K.

Status words (as in v4): **BUILT** = RTL passing in simulation (some also run on a card); **MODEL** = Python only; **DESIGNED** = specified here from model rules, no RTL; **ESTIMATE** = a number I derived, not a measurement. Every figure is copied from a ledger row of `HEXN_DESIGN.md` (time in brackets) or from a measurement made for this file (marked **[this file]**). Resource figures are yosys counts, not place-and-route, unless said.

## 1. The picture

```
 world (sensors / game)
    |
 [ L1  counted detectors ]--- counts x1..x6, parity ------------------------------+
    | classes (one feed per sensor)                                                |
 [ L2  history per feed: one store per feed ] (A: opponent / sensor events          |
    |   predicted next, verdict, SURPRISE flag)                                     v
    |                                                                 [ NEURAL  judge + learning rule ]
 [ L3  history across feeds: moments, snapshots,                       7 counts -> 8 weights -> tanh
    |   weighted possible next moments, hit rate ]                         ^    |
    |                                                                      |    | position value (leaf)
 [ L4  strategist: expectimax with path-probability cutoff ]---------------+----+
    |   blend by confidence x hit rate x L2 gate; its search value = the TEACHER
    |
 [ PLAYER DETECTOR ] -> [ SELECTOR: which approach this opponent gets ]      (section 5, being measured)
    |
 choice out (column / action)

 DATA flows inward (L1 -> L2 -> L3 -> L4).  CONFIDENCE flows the other way and sideways:
   L2 surprise -> L4 (gate) ; L3 hit rate -> L4 (blend weight) ; L4 right/wrong -> L3 (hit rate) ;
   L4 search value -> NEURAL (teaching target) ; NEURAL value -> L4 (leaf) ; detector -> selector.
 TRAINING MODULE = L2 + L3 + L4 acting together as the teacher of the NEURAL; the neural reads only L1.
```

## 2. Components: what each is, what state it is in, what it costs

Sizes are Gowin (Tang Nano 20K family) from yosys unless stated. "slot" = LUT4 + ALU cell, the unit nextpnr counts against the 20,736 of the board. 46 BSRAM on the board.

| # | Block | Job in the unit | State | Size | Source |
|---|---|---|---|---|---|
| 1 | L1 counted detectors | turn the sensor wires (or the game position) into small counts | BUILT (sensors); the game's line counters are MODEL | minimal detector: 150 / 224 / 268 LUT4 + 35 / 39 / 39 ALU at 12 / 18 / 20 wires, per detector | [21 Oct] |
| 2 | NEURAL: 8-weight judge + whole-number learning rule | value of a situation from the L1 counts; learns from the teacher | **BUILT (simulation, bit-true to the Python integer model, 2,400 commands, WB 14 and 10)** | **477 LUT + 180 ALU = 657 slots, 273 FF, 5 MULT18X18, no BSRAM** (WB 10 gives the same within 1%; weights 16 bit, accumulator 28 bit as synthesised; Q10 needs 10-bit weights and a 13-bit accumulator, so the registers can shrink) | **[this file]** `rtl/hexn_neural_v1.v`, `hexn_tanh512_v1.v` |
| 3 | L2 store, one per feed (2 feeds) | history per feed: predicted next event, verdict, surprise | BUILT (store v6, LRU, simulation; v5 on the card) | per store: **1,472 LUT + 572 ALU = 2,044 slots, 1,101 FF, 14 BSRAM + 46 RAM16SDP4 at the default (1,024 index slots, 512 rows)**; the configuration used in the tests (IB 8, RB 7) maps to 4 BSRAM + 74 RAM16SDP4 and 988 FF with the same 572 ALU **[this file]**, so the logic does not shrink, only the memory | [04:10, 31 Oct], [this file] |
| 4 | L3 across feeds | moments, snapshots, weighted possible next moments, hit rate | MODEL; DESIGNED in `LAYER3_HW_v1.md` | ESTIMATE: one more store v6 (2,044 slots, 4 to 14 BSRAM) for the path memory + moment builder (counter and latch per channel, tiny) + two ID tables (`hexn_snapid_v1.py`, 512 slots each, about 1 BSRAM each) + a read that ranks all followers of a context (new, not sized) | [27 Oct], [07:30, 31 Oct] |
| 5 | L4 strategist | search: expectimax, path cutoff, blend; its value is the teaching target | MODEL (Connect Four, draughts) | NOT SIZED. Measured work per decision in the tests: 250 to 1,850 search nodes (depth 3 to 4); each leaf = one neural evaluation (12 clocks serial). See 4. for where it can live | [09:40, 10:30, 31 Oct] |
| 6 | Player detector + selector | tell the opponent's style from L2/L3/L1 signals and pick the approach | being measured (section 5) | ESTIMATE: 4 to 6 counters and 2 comparators, well under 200 slots | this file |
| 7 | Memory tier | shared key/value store behind the layers | BUILT on the Kintex card (2,000,000 steps, 0 wrong); not joined to the core | Tang: levels would be BSRAM, SDRAM, SD (SDRAM test block 538 LUT4) | [30 Oct], [27 Oct] |

## 3. Fit on the Tang Nano 20K (20,736 slots, 46 BSRAM)

| Configuration | Slots | BSRAM | Status |
|---|---|---|---|
| Sensor side only: 8 detectors at 18 wires (8 x (224 + 39)) | about 2,100 | 0 | from [21 Oct] unit sizes; the 19-detector build with its lattice was 15,730 slots, so the lattice (wiring between detectors), not the detector, is what grows |
| Neural | 657 | 0 | measured |
| 2 x L2 store v6 (tests' memory size IB 8 / RB 7) | 4,088 | 8 | measured logic, memory from the yosys stat |
| L3 (estimate: store v6 + ID tables + moment builder) | about 2,400 | about 6 | ESTIMATE |
| Detector + selector | under 200 | 0 | ESTIMATE |
| **Fabric total (L1 8 detectors, neural, 2 x L2, L3, detector)** | **about 9,500** | **about 14** | **about 46% of the logic, 30% of BSRAM, if the 19-detector lattice overhead is NOT repeated; ESTIMATE where marked, not placed and routed, no timing** |
| L4 | 0 on the fabric | 0 | proposed: runs on the ESP32/BL616 beside the FPGA (4. below); NOT built |

Reading: the parts that can be built fit with room to spare; the fit is not proven until L3 exists and the lot is placed and routed. At the default store size (14 BSRAM each) three stores would take 42 of 46 BSRAM, so the test-size memory (IB 8) is the working choice. The Tang has 46 BSRAM; the Kintex card has far more.

## 4. Where the strategist (L4) lives, and why it matters

The search is a loop with a stack, 250 to 1,850 nodes per decision, each leaf a 7-multiply evaluation. That is trivial for a small processor and awkward in fabric. Two placements, choose one (open decision):
- **A. Co-processor (proposed):** L4 on the board's ESP32/BL616 (the link already exists, `esp32-bl616-link-protocol-v0.1.md`). The fabric holds L1, L2, L3, the neural's weights and its learning rule; L4 asks the fabric for the L3 ranking and the neural value per leaf (or holds an identical integer copy of the 8 weights and evaluates leaves itself, which the bit-true model makes safe).
- **B. All in fabric:** a small sequencer with a stack and the neural as its leaf unit; the neural is already the right shape (serial, one multiplier). Size unknown; this is the larger build.

For the sensor-control direction decided on 30 Oct (20:10) L4 reduces to a goal setter and no search is needed, so placement A costs nothing there.

## 5. Evidence, and what it does and does not support

All Connect Four, Python, 600-game runs, mean of games 301 to 600. Opponent names as in the ledger.

(see section 8, filled from the 31 Oct rows)

## 6. Step of the unit, in order (one decision)

1. L1 turns the position/sensors into counts. 2. The opponent's last event goes into its L2 store (read first for the verdict, then observed); L3 takes the moment and updates its hit rate. 3. L4 searches: at each opponent node it takes the L3 ranking, weights it by hit rate and halves that when L2 reported a surprise; leaves are scored by the neural. 4. The chosen action goes out; the unit stores the position and the search value. 5. After the next move (or the end) each stored position is taught to the neural: target = the next search value (the result at the end), one whole-number step per position.

## 7. NOT built (so nobody reads this as a finished unit)

L3 hardware; L4 hardware or firmware; the join of the memory tier to the core; any layer 1 hardware for the game's line counters (the sensor detectors exist, but the neural has only ever been tested on game counts, not on sensor class counts); the player detector and selector; a placed-and-routed build of the whole; any timing figure.
