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

**Networks.** A line of cells, one reward for the whole line, same 1,500 tries: 1 cell 883, 2 cells 731, 4 cells 612, 8 cells 695 (random guessing about 600). Learning fades from 4 cells at this budget. Whether more tries or a per-cell teacher signal fixes it is not yet tested.

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

## 5. Open questions

1. A1 to A7 (how strongly each lane counts, which way the bias acts, what "graded" means, and so on).
2. Should the accumulator leak slowly or clear at the end of each window? Not decided; the biggest gap against a real neuron.
3. How many bits of memory, and should it be a plain shift register or something richer (a counter, context tags)?
4. Credit assignment in a network: with one reward for the whole network learning fades from 4 cells; a per-cell teacher signal is the next test.
5. Where the goal and teacher live in hardware (an external teacher such as the ESP32, a reference held in the cell, or neighbours scoring each other).
6. A real routing question for clusters: several routes, and different results depending on the input, so a route has to remember the input. Wire weights alone cannot do this; the memory above is one answer, a ring of cells holding a value is another (untested).
7. Real hardware: stacked-die chips could carry a third dimension in future (a note on the 3D thread in UniCell; nothing here depends on it).

## 6. Targets

Tang Nano 20K (Gowin) and a Kintex card, both on hand. Nothing has been placed yet; the next hardware step is a few cells with settings storage, fitted by place-and-route on Alan's tools.

## 7. Files (branch `Hex-N`)

`docs/hex-n/` (this document, the older notes, link protocol), `rtl/hexn_cell_v1.v`, `tests/test_hexn_cell_v1.py`, and `tools/hexn_*.py` (experiments v1 to v11, each a new file; see the header of each for the question it asks), `tools/hexn_size_v1.sh`, `tools/hexn_state_sweep_v1.sh`, `tools/hexn_state_summary_v1.py`.
