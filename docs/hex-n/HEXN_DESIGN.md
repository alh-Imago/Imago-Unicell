# Hex-N: a silicon neural cell that learns (design document, 20 Oct 2026)

**Status in one line:** a working cell model and a Verilog prototype, a training method that works in simulation, and first size measurements. Nothing has been routed or run on a card yet. This is a separate project on its own branch (`Hex-N`); it is not meant to be merged into `main`.

This document is written for Alan (the author, not a programmer): ideas first, numbers where they were measured, and a plain line on what is not known.

## 1. What it is, and how it relates to UniCell

Hex-N is an attempt to build the silicon version of a nerve cell, and then a substrate made of many of them.

It shares its roots with Imago UniCell: "topology is computation", cells that are wired to their neighbours point to point, no central processor, and the habit of building from small proven pieces. It differs in what a cell is. A UniCell compute cell is a small register file with NOR gates, and its programme is a wiring. A Hex-N cell is closer to a neuron: it adds up what arrives, compares the total with a threshold, and fires a graded burst. Its programme is also a pattern, but the pattern is trained and not written.

| | UniCell | Hex-N |
|---|---|---|
| Cell | register file plus NOR gates | six-faced summing cell with lanes |
| Programme | a wiring, written | a pattern of settings, trained |
| Result | deterministic, known in a fixed number of clocks | deterministic, produced by the trained pattern |
| Timing | clocked dataflow | windows of two phases (forward, then feedback) |

Both are deterministic. Hex-N has no true randomness at run time; any random choice in training comes from a seeded circuit that can be replayed exactly.

## 2. The cell as it exists

A cell has six faces. Each face has a number of **lanes** (4 in the prototype; the original specification had 16, the first bring-up scoped 8). A lane is one wire whose direction is shared in time: it never carries flow both ways at once.

Per lane the settings are: active or not, a direction code, and a gate code. Per face there is a threshold. One shared value (the bias) raises every threshold.

**Direction codes:** receive only, send only, receive-then-send, send-then-receive.

**Gate codes** (applied on the sending side):
- ALL-THREE ("AND"): fire only if input arrived, the threshold was reached and feedback agreed.
- CHOOSE ("OR"): of several equal paths, the lowest-numbered one fires.
- STEER ("XOR"): steer to an even or odd lane depending on whether input arrived.
- NEGATIVE ("NOT"): a receiving lane subtracts instead of adds.

**One window.** A window has a forward phase (flow goes forward and is summed) and a feedback phase (flow comes back and is summed separately). At the end of the window the face works out: did the total reach the threshold; by how much (capped at 6); did any input arrive; did the feedback agree. In the next window a lane that passes its gate sends a burst of 1 + margin clocks, so stronger input produces a stronger signal downstream. That is the graded output.

**Where the cell's memory is today.** The only memory is those four results, held for one window. Everything else clears at each phase. The shared 16-bit bias is a fixed setting, not a memory.

Files: `rtl/hexn_cell_v1.v` (Verilog), `tests/test_hexn_cell_v1.py` (an independent cycle-accurate Python model; the RTL matches it on 60 random configurations). The model rests on seven assumptions, marked A1 to A7 in the RTL and listed in `walkthrough-v0.2.md`; they are guesses made to build the prototype, not decisions, and only Alan can settle them.

## 2a. Finding (20 Oct, measured): the faces of a cell do not talk to each other

In the prototype each face works alone: its output depends only on what that same face received, on its own threshold and on the shared bias. Changing the input on faces 0 to 2 never changed the output on faces 3 to 5 (0 of 100 random cells). Information moves between cells only along the wires, from a face to the matching face of a neighbour; inside a cell it does not move at all. So today a Hex-N cell is six independent face-neurons that happen to share a bias, not one neuron with six faces of dendrites.

This may or may not be intended. If it is, a recognition task needs a layout where each face sees its own inputs and outputs and a network is built by wiring faces together. If it is not, the cell needs a mixing step (for example one shared accumulator, or a crossbar between faces), which is a design change that would raise its size. Decision for Alan.

## 3. How it learns

The method, as Alan specified it:

1. **Train in the VM.** The pattern (which lanes, directions, gates, thresholds) is found by search in simulation.
2. **Freeze it.** The trained pattern becomes the programmed cell, as a UniCell wiring would.
3. **Optionally mutate in silicon.** If the cell can change its own settings and score the result, it can retrain in place.

The search used is not gradient training (the settings are discrete). It is: start from a working cell, change 1 to 3 settings at a time, keep the change if the score is not worse, otherwise undo it. A random starting point is replaced by the best of 100 random trials.

**What the score is.** For every lane and every window, the number of clocks the lane was high is compared with the goal's. 1,000 means identical bursts, 0 means no overlap. Forward and feedback phases are scored separately and combined (half and half works best).

**On-chip learning needs only small parts** (tested in the VM, not yet in RTL): a 32-bit random-number circuit (replayable), a spare copy of the last good settings, and one teacher reward. The reward needs about **4 bits** per trial; with 3 bits it is a little worse, and below that it fails. A teacher that only says "better or not" (1 bit) works as well as the 4-bit reward when the "not worse" rule is used.

## 4. What has been measured (all in the VM unless stated)

Single cell, 30 seeds, 1,500 tries each. "Random guessing" is the best of the same number of random settings. Scores are 0 to 1,000.

| Step | Mutated score | Beat random guessing |
|---|---|---|
| Exact-bit score, keep-or-undo (v1) | about 600 | about half of seeds |
| Graded burst score (v2) | 627 | 18 of 30 |
| Plus warm start and 1 to 3 changes per try (v5) | 808 to 828 (three runs) | 27 to 29 of 30 |

Run-to-run noise in a mean of 30 is roughly 30 to 60 points; earlier conclusions drawn from small differences were not reliable.

**Networks: no valid result yet.** Two earlier network tests (`hexn_network_v7.py`, `hexn_network_v8.py`, a line of 1 to 8 cells) reported that learning faded from 4 cells. That is **withdrawn**: in the cell as built, information never crosses from one face to another inside a cell (section 2a), so in those line networks the external input never reached the cell whose output was scored (checked: its output did not change at all when the input changed, in 0 of 40 networks at 2, 4 and 8 cells). The 1-cell rows were valid. The network question is open and needs a proper test (section 2a).

**Memory of older input.** When the right output depends on input from earlier windows, a plain cell loses score steadily: delay 0 scores 833, delay 1 641, delay 2 524, delay 3 443. Adding a small writable memory (a shift register of "input arrived", with trained taps that the AND and XOR gates can read) lifts delay 4 from 390 (none) to 475 (4 bits), 563 (8 bits) and 480 (16 bits). The same memory costs score when it is not needed (delay 0: 761 without, 615 to 677 with). A live-input AND was tried and cannot change anything in this cell as built, so it is not a result. The 8-bit memory could share the existing 16-bit latch (8 memory, 8 bias), which needs no extra storage. More sweep results (other delays) will be added here when they are complete.

**Size (synthesis estimate, one cell, 6-bit accumulator, no place and route, settings excluded):**

| Lanes per face | Gowin LUTs (Tang Nano 20K) | Xilinx 7-series LUTs (Kintex) |
|---|---|---|
| 1 | 450 | 359 |
| 2 | 600 | 407 |
| 3 | 968 | 539 |
| 4 | 1,280 | 677 |
| 8 | 2,719 | 1,186 |

Flip-flops stay at 117. The settings (82 bits at 1 lane, 172 at 4, 292 at 8) are inputs in this prototype and would add storage. Tool: `tools/hexn_size_v1.sh`, yosys 0.33. The learning-versus-lanes result is still running and will be added.

## 4a. Pattern recognition and the hex cluster (20 Oct 2026, VM only; all numbers from the files named)

**Cell v2 (Alan's choice):** all six faces feed one decision (one shared forward total, one feedback total, one threshold); the earlier cell (v1) was six independent faces. Model `tools/hexn_cell_v2_model.py`, RTL `rtl/hexn_cell_v2.v` (checked against the model by `tests/test_hexn_cell_v2.py`), size tables `tools/hexn_size_v2.sh`.

**Task:** four classes of 12 on/off wires, noise = chance each wire is flipped, chance level 0.25, "template rule" ceiling about 0.90 at noise 0.15 (0.72 at 0.25). A single detector cell per class reaches about 0.68; one cluster of 7 cells (radius 1) with one shared reward reached 0.45 (random best 0.42, `hexn_cluster_v15.py`).

**What was tried, one change at a time on the same seeds (v18 to v20).** Accept rule fixed in advance (`tools/hexn_ladder_compare_v1.py`): the mean paired difference must be at least 2 standard errors and the new arm must win on more seeds than it loses.

| Change | Result | Verdict |
|---|---|---|
| Local reward per output group instead of one reward (v16) | 0.25 at 600 tries, 0.29 at 2,000 (global reward: 0.45) | worse |
| Outputs that never vary with the input get no credit (v18 reward) | 0.199 (25 seeds) | baseline for the ladder |
| Threshold offset, clamped, driven by firing (v18, M=2, run 3) | 0.227 vs 0.199 | no difference shown |
| Grow from one-in-one-out cells, with stuck-lane pruning (v17) | 0.00 to 0.26 depending on arm | no help |
| Feedback also pushes the offset (first form) | identical on all 25 seeds | VOID: its vote could never oppose the firing vote |
| Feedback agreement cancels the push (v19 fbagree) | 0.170 vs 0.227 | leans worse, not accepted |
| Offset decay | 0.247 vs 0.227 | no difference shown |
| **Readout score: reward also counts "my group fires strictly more than the others"** | **0.312 vs 0.199 (+0.112, 3.6x its error, 19 wins 5 losses)** | **accepted** |
| Aimed mutations (shared output cells) | 0.309 vs 0.312 | no difference shown |
| Per-face weights 1 to 3, trained, fixed at run time | 0.329 vs 0.312 | no difference shown |
| **Each output group served by its own cell (`--ownout`)** | **0.385 vs 0.315 over 50 seeds (+0.070, 3.35x, 31 wins 16 losses); the last 25 seeds alone also pass** | **accepted** |
| Aimed mutations again, now with one cell per output group | 0.366 vs 0.376 (25 seeds) | no difference shown |
| Longer search, 2,000 tries instead of 600 (15 seeds only) | 0.418 vs 0.366 (+0.052, 1.6x its error, 8 wins 4 losses) | no difference shown; leans better, would need more seeds |
| Graded readout term: how much the right group leads in burst clocks (Alan's idea, 21 Oct) | 0.348 vs 0.376 (25 seeds; 6 wins 11 losses) | no difference shown; leans worse |
| Panic shake: after 60 tries without strict improvement, change 8 to 12 settings at once (Alan's "keep the openness") | 0.378 vs 0.376 (25 seeds) | no difference shown; with 600 tries the shake fires only a few times, so a longer search would be a fairer test |
| **Decision-table cell** (`hexn_cell_v3_model.py`, `hexn_cluster_v21.py`; 64-entry table of output levels indexed by which faces had input; 768 bits per cell; Alan's idea, 21 Oct) | 0.421 vs 0.385 over 50 seeds (+0.036, 1.4x its error, 29 wins 21 losses); sd 0.107 vs 0.134; worst 0.22 vs 0.01; seeds under 0.20: 0 vs 3; best 0.73 | no difference shown on the mean. The spread looks better (0 failures in 50 against 3) but on the second 25 seeds alone the summing cell also had none, so the consistency gain is not established. Not yet sized in logic. |
| Per-lane weights, a 2-bit weight on each of the 24 lanes, trained and fixed at run time (Alan, 21 Oct) | 0.340 vs 0.376 (25 seeds; 7 wins 15 losses; sd 0.121 vs 0.155, only 1 seed at 0.50 or more vs 6) | no difference shown; leans worse |

**Why the layout change mattered.** A diagnostic (`tools/hexn_diag_v1.py`) on models trained on clean data showed each one learned only 1 to 3 of the 4 classes. In the original layout output groups 1 and 2 were driven by the same cell and groups 2 and 3 by another; a v2 cell makes one decision, so those groups could not differ.

**Frozen model (train, freeze, then add noise), `tools/hexn_cluster_v20.py`, 12 seeds, run on Alan's machine and here.** Trained on clean data the frozen model scores 0.417 / 0.382 / 0.323 / 0.273 at test noise 0 / 0.05 / 0.15 / 0.25 (ceiling 1.00 / 0.98 / 0.89 / 0.70). Trained at noise 0.15: 0.375 / 0.352 / 0.292 / 0.274, no better. Letting the threshold offset adapt during the test stream made it **worse** at every level (by 0.139 to 0.072), losing on 8 to 11 of 12 seeds. This tests one form of run-time adaptation; it does not show adaptation in general cannot help.

**Where it stands.** Best cluster so far 0.385 (0.418 on 15 seeds with 2,000 tries, not accepted), against 0.68 for four separate detectors and about 0.90 for the ceiling. The gap is not closed. Two mistakes of mine are on record: the first feedback test was void (see above), and the earlier network tests (section 4) were withdrawn.

## 5. Open questions

1. A1 to A7 (how strongly each lane counts, which way the bias acts, what "graded" means, and so on).
2. Should the accumulator leak slowly or clear at the end of each window? Not decided; the biggest gap against a real neuron.
3. How many bits of memory, and should it be a plain shift register or something richer (a counter, context tags)?
4. Credit assignment in a network: not yet measured (the earlier test was void, see section 4). Needs a layout in which input can actually reach the output, which depends on the answer to section 2a.
5. Where the goal and teacher live in hardware (an external teacher such as the ESP32, a reference held in the cell, or neighbours scoring each other).
6. A real routing question for clusters: several routes, and different results depending on the input, so a route has to remember the input. Wire weights alone cannot do this; the memory above is one answer, a ring of cells holding a value is another (untested).
7. Real hardware: stacked-die chips could carry a third dimension in future (a note on the 3D thread in UniCell; nothing here depends on it).

## 6. Targets

Tang Nano 20K (Gowin) and a Kintex card, both on hand. Nothing has been placed yet; the next hardware step is a few cells with settings storage, fitted by place-and-route on Alan's tools.

## 7. Files (branch `Hex-N`)

`docs/hex-n/` (this document, the older notes, link protocol), `rtl/hexn_cell_v1.v`, `tests/test_hexn_cell_v1.py`, and `tools/hexn_*.py` (experiments v1 to v20, plus `hexn_diag_v1.py`, `hexn_ladder_compare_v1.py`, `hexn_ladder_run_v1.py`, `hexn_run_frozen_v1.sh`;  v7, v8 and v12 rest on a faulty layout and are kept as a record, each a new file; see the header of each for the question it asks), `tools/hexn_size_v1.sh`, `tools/hexn_state_sweep_v1.sh`, `tools/hexn_state_summary_v1.py`.
