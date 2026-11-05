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
