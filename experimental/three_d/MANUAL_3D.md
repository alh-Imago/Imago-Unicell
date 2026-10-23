# Imago UniCell 3D Kit — manual

*Version of 23 Oct 2026 (ledger #1310–#1314). This kit is **separate from the main UniCell tools**: its own composer, its own placer, its own file formats. It does not need, and is not connected to, the main Composer, the workbench or the front panel.*

## 1. What this is, and what it is not

The kit explores one idea: what if a cell had **six** neighbours — north, south, east, west, **up and down** — so that a design can be built in layers, the way a stacked chip is? It lets you **draw** such a design, **run** it, **place it automatically**, and **save it in a file format** meant for six-face cells.

**It is an exploration, not a product.** Be clear about this before relying on anything here:

* **There is no 3D hardware, no 3D RTL and no card to run any of this on.** Everything runs in software, in a small *toy model* of the six-face grid (`experimental_3d_nor_v2.py`): a cell passes a word on, or combines two words with a gate, one cell per tick.
* The number of layers is **free** (a stack can be 2 or 20 high). The cells themselves have to carry all six faces.
* The three file formats in this kit (design, netlist, ICM-3D) are **read only by this kit**. Nothing else — no assembler, no generator, no FPGA flow — reads them.
* Timing in the toy (one tick per cell) is **not** hardware timing.

## 2. Quick start

You need **Python 3.12 or newer** (tested on 3.13; nothing outside the standard library). From the folder that holds this manual:

    python3 run_composer.py

The 3D Composer opens in your browser at **http://127.0.0.1:7422**. (`--port 7430` changes the port, `--no-browser` stops it opening a window, `--example adder_auto` starts with an example loaded.) Stop it with Ctrl+C.

First things to try, in the page:

1. **Open an example…** → *NOR adder, 44 cells, 3 layers*.
2. Drag the **Depth** slider: the layer you are on is shown in full, everything on other layers fades.
3. Drag in the **3D view** to rotate; press **Top**, **Front**, **Side**, **3/4**.
4. In the **Run / step** panel give A and B some numbers, choose **watch** `E`, press **Start**, then **Run to end**: E holds A + B.

To check the whole kit works: `python3 run_tests.py` (needs `pytest`: `pip install pytest`).

## 3. The ideas, in plain words

* **Six faces.** Every cell has N, S, E, W, U, D. A cell sends a word out of the faces you switch on; a neighbour receives it through its opposite face.
* **Layers.** Up/down moves to the next layer. Layer 0 is the bottom. The board is rows × columns × layers.
* **Two kinds of cell.**
  * **Relay** — passes the word on, optionally **shifted** left or right by 0–31 bits. In ICM-3D terms a relay is a **ram cell in flowing (pass-through) mode**: one word in, one or more faces out (Alan, 23 Oct 2026; read from `ram_cell_v4sa.v`). The shift is the add-on.
  * **Gate** — waits for **two** words, then outputs AND, OR, XOR, NOR, NAND or XNOR of them. In ICM-3D a gate is a **nano** cell with the toy's topology code.
* **Joins.** A "join" is just a face switched on towards a neighbour. Cells that are not neighbours are joined by a chain of relay cells laid between them.
* **Entries and exits.** An **entry** is a cell that sends but receives nothing: you give it a word to start. An **exit** is a cell that receives but sends nothing: you read the answer there.
* **Ticks.** In each tick every cell that has a word passes it on; it arrives next tick. A gate fires when its second word arrives. There is no flow control: one set of words at a time.
* **Nothing crosses by accident.** A cell sends only through the faces switched on, so two wires can pass side by side or one over the other without touching. The only rule: two wires never share a cell.

## 4. The 3D Composer

### The page

* **Floor plan** (left): one layer, editable. The layers above (▲n) and below (▼n) are drawn faded behind it. A gold triangle on a tile means it sends up or down; a hollow gold triangle means it receives from there.
* **3D view** (right): the whole stack in perspective. The current layer's sheet is outlined in copper; its cells are drawn solid and labelled, other layers are faded.
* **Depth slider** (and the ▼ ▲ buttons, or the `[` and `]` keys): chooses the current layer. The **others** menu sets how strongly other layers fade (hidden · very faint · faint · visible); layers further from the current one fade more. **layer gap** spreads the layers apart in the 3D view. **show** switches between plan + 3D, plan only and 3D only.
* **3D view controls:** drag to rotate; shift-drag or right-drag to pan; mouse wheel to zoom; **3/4 · Top · Front · Side** presets; **Spin** turns it slowly. Click a cell to select it.

### Tools

| Tool | What it does |
|---|---|
| **Select** | click a cell to select it and edit it in the *Selected* panel |
| **Place** | pick Relay or a gate in the palette, then click an empty square of the current layer |
| **Join** | click a source cell, then a target cell. Neighbours get a face; otherwise a shortest chain of relay cells is laid through free squares. The box *joins may route through other layers* chooses whether the chain may leave the current layer |
| **Delete** | click a cell (or select it and press Delete) |

### The Selected panel

Name, kind (relay/gate), gate type, shift bits and direction (relay only), and **six face buttons** N S E W U D — a face can be switched on only where a neighbouring cell exists. It also shows what the cell receives from, and a **Delete cell** button.

### Board and layers

Set **rows** and **cols**; **+ layer top** / **+ layer bottom** add an empty layer (adding underneath moves everything up one, so neighbours stay neighbours); **− top** / **− bottom** remove an empty end layer. A change that would cut off a cell is refused. **Undo** (or Ctrl+Z) takes back the last edit.

### Run / step

Give each entry a word (decimal or `0x` hex), choose a **watch** cell, press **Start**. **Step** advances one tick, **+10** ten, **Run to end** until nothing moves (a loop is cut off after 2000 ticks). Cells holding words are outlined green; cells that fired this tick copper; the watch cell shows its word and the tick it first appeared. Any edit stops the run. **Check** (when the design says what it should compute) runs 100 random tests: for the adder against real addition, for an auto-placed design against its netlist.

### Problems panel

Warns about: a face that points at no cell; a gate without two inputs; a loop (a word would go round for ever); a cell not joined to anything. Click a line to jump to it.

### Files

| Button | Does |
|---|---|
| **Save design** / **Open file…** | the composer's own `imago-3d-design` file (JSON) |
| **Save ICM-3D** / **Save ICM-3D binary** | the ICM-3D v2 file (section 6); refused if any face points at nothing |
| **Open file…** | reads a design, an ICM-3D JSON or an ICM-3D binary (decided by what is inside, not the name) |
| **Auto-place netlist…** | choose a netlist file (section 5); *layers* sets how many layers the placer may use |

The **examples** menu has the NOR adder (hand-laid, 44 cells), the same adder **placed automatically**, two wires crossing on two layers, and one gate fed from two layers.

## 5. The automatic placer

`experimental/three_d/placer3d_v1.py` takes a **netlist** and lays it out by itself.

    python3 experimental/three_d/placer3d_v1.py --example adder --layers 3 --out adder.3d.json
    python3 experimental/three_d/placer3d_v1.py --netlist my_net.json --layers 2 --seed 3 --out my.3d.json

Open the result with **Open file…** in the composer.

### The netlist file

    {"format": "imago-3d-netlist", "version": 1,
     "cells": [{"name": "A", "kind": "relay"},
               {"name": "G", "kind": "gate", "gate": "XOR"},
               {"name": "S", "kind": "relay", "shift": 4, "left": true}, ...],
     "nets": [["A", "G"], ["B", "G"], ["G", "S"]]}

A net `["A", "G"]` means *A's output goes to G*. Rules the placer checks and states plainly if broken: no loops; a gate has exactly two inputs; a relay at most one; a cell's inputs plus outputs at most six (add a fan-out relay yourself); every cell joined to something; names unique.

### How it works

1. **Spread** the cells on a lattice by simulated annealing (short wires, and no cell walled in by cells it is not joined to).
2. **Route** every net as a chain of relay cells, by negotiated congestion (nets may share squares at first; sharing gets dearer each round until none do).
3. **Close the gaps** between rows, columns and layers while it still routes, and delete planes that hold only straight-through relays.
4. **Verify by running**: every exit must give the same word as direct evaluation of the netlist, for 64 random input sets. A layout that fails is never returned.

Several layouts are found (`keep`) and the smallest is returned; different `--seed`s give different layouts.

### What it achieves (measured)

For the NOR adder (35 netlist cells), 3 layers allowed: **80 cells in all** from the default three layouts (seed 1), **72** if eight are tried, **62** with 4 layers allowed. The hand-placed adder is **44 cells** in 22 ticks; the automatic ones settle in about 40 ticks. So the placer is **correct but not compact** — about 1.4 to 1.8 times the hand layout. With **one layer** the adder cannot be placed (wires must cross) and the placer says so.

## 6. ICM-3D v2 — the file format

A standalone file format for six-face designs in the flex family. Full specification: the next section of this manual (*ICM-3D v2 specification*). In short: one record per cell — its square, its core (`ram` pass-through or `nano` gate with a topology code), its shift add-on, and two 6-bit face masks (`out_mask`: faces it sends to; `in_mask`: faces it receives from; bit order N S E W **U D**). A reader recomputes every `in_mask` from the neighbours and refuses the file if it disagrees. JSON form (with names) and a compact binary with a checksum (the 44-cell adder is 367 bytes).

    python3 experimental/three_d/icm3d_v2.py convert design.3d.json out.icm3d.json
    python3 experimental/three_d/icm3d_v2.py convert design.3d.json out.icm3d
    python3 experimental/three_d/icm3d_v2.py convert out.icm3d back.3d.json
    python3 experimental/three_d/icm3d_v2.py show out.icm3d

`icm3d_v1.py` (the first version, with a toy relay) is kept as it was written; v1 and v2 files refuse each other.

## 7. The three file formats

| Format | Made by | Read by | Contains |
|---|---|---|---|
| `imago-3d-design` v1 (JSON) | composer **Save design**, placer `--out` | composer | cells, positions, faces, names, board size, description |
| `imago-3d-netlist` v1 (JSON) | you (or a tool) | placer, composer **Auto-place** | cells and nets, no positions |
| `icm-3d` v2 (JSON or binary `I3D2`) | composer, `icm3d_v2.py` | composer, `icm3d_v2.py` | cells as hardware-style records |

## 8. Checks

`python3 run_tests.py` runs 55 tests: edit refusals and undo, routing, layer changes, file round trips and damaged files, the stepper against the toy model's own run, the adder against real addition (and the check failing when a gate is broken), the placer's refusals and its verification (also tested to bite: a changed gate and a cut wire are caught), ICM-3D consistency rules and damaged binaries, and the live server.

## 9. Limits — what is not done

* No 3D hardware, RTL, assembler pass or card (section 1).
* ICM-3D covers **only `nano` gates and `ram` pass-throughs**. The other cores (adder, mul, div, accumulator, comparator, latch, sequencer, branch, priority, cross, corner, merge, the other ram modes) have no record; their six-face widths are in the cell audit (last section). The `sub` family is not defined.
* The `ram` record is not a full ram configuration (no preload word; fixed mode off). How one ram offers a word to several consumers is the flex glue's job, not a ram setting. A real ram holds a word for two cycles; the toy passes one cell per tick. The polarity of the add-on's direction bit against "shift left" was not checked.
* The nano topology codes are copied from the toy model, not re-checked against the RTL here.
* The placer handles feed-forward netlists only, does not insert fan-out relays, and is not minimal.
* The composer's Join router is a plain shortest-path search; it can fail on a dense design. Placing is in the floor plan only. Touch pinch-zoom is untested.
* In the downloaded kit, the cell-audit's numbers come from the full project (`cell_face_budget_v1.py` there); the script is not in the kit.

## 10. Troubleshooting

| Problem | What to do |
|---|---|
| "Address already in use" | another copy is running: `python3 run_composer.py --port 7430` |
| The browser does not open | `--no-browser`, then open http://127.0.0.1:7422 yourself |
| The page looks plain (different font) | the page asks Google Fonts for its font; offline it falls back to system fonts, everything still works |
| "no routable layout found" | allow more layers (`--layers 4`), try another `--seed`, or the netlist needs a crossing and you allowed one layer |
| "in_mask does not match" opening an ICM-3D file | the file was edited by hand or damaged; the reader refuses it on purpose |
| An older ICM-3D file will not open | it is v1; the kit reads v2. Re-save from the design file |
