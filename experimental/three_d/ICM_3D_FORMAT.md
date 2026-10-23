# ICM-3D v2 — a file format for six-face (3D) designs, flex family

*23 Oct 2026. **v2 supersedes v1** (#1314): v1 had a toy `relay` pseudo-core; per Alan a relay is a **ram cell in flowing (pass-through) mode**, and v2 says so. `icm3d_v1.py` is kept as it was. **Exploration only** (see the scope note in `README.md`): there is no 3D RTL, no assembler pass and no card. The format is read and written only by `icm3d_v2.py` and the 3D Composer, and describes designs in the toy grid `experimental_3d_nor_v2.py`.*

## Why a separate format

ICM v3's `core_config` is a 42-bit union shared by all cores; with six faces five cores overflow it (branch needs 49, nano 47, ram 46, comparator 44, accumulator 43 — `CELL_AUDIT_6_FACE.md`, re-run `cell_face_budget_v1.py`). Rather than move fields inside the 80-bit SUPER_LATCH, ICM-3D is a **new standalone format with its own per-core records** (Alan's choice, 23 Oct 2026). ICM v3 is untouched, and an ICM v3 reader will refuse an ICM-3D file (different `format`, different magic).

Family chosen first: **flex/sub** (Alan, 23 Oct 2026). In that family a cell has generic lanes and the wiring is the netlist, so the format needs one thing per cell beyond the core: which of the six faces it sends to and receives from.

## What a record says

| field | meaning |
|---|---|
| `pos` `[row, col, layer]` | the grid square; layer 0 is the bottom, U goes to a higher layer |
| `core` | `nano` (a gate) or `ram` (a pass-through, see below) |
| `topology` | nano only: the toy's nano topology code — AND `0x007`, OR `0x024`, XOR `0x0BC`, NOR `0x004`, NAND `0x027`, XNOR `0x03C` (copied from the toy model; **not re-checked against the RTL** here) |
| `shift`, `shift_left` | the shift add-on, 0–31 bits (on a `ram` pass-through only; a gate has none in this model) |
| `out_mask` | 6 bits, faces the cell sends to: bit 0 N, 1 S, 2 E, 3 W, **4 U, 5 D** (U, D after W, so a four-face design keeps its four low bits) |
| `in_mask` | 6 bits, faces it receives from; **derived** from the neighbours' `out_mask`s and stored anyway |

**The consistency rule:** a reader recomputes every `in_mask` from the neighbours' `out_mask`s and refuses the file if any differs. It also refuses: two cells on a square, a square outside the board, a face sending into an empty square, a gate without exactly two inputs, an unknown topology, a shift on a gate, a mask wider than six bits. A design with a dangling face cannot be exported (the composer shows it as a warning; the format has no dangling faces).

**What a relay is (Alan, 23 Oct 2026):** a `ram` core in its flowing mode — `fixed_mode` 0, no preload — one word in, any of the six faces out. Read from `sub/verilog/ram_cell_v4sa.v` (flowing mode: capture on `valid_in`, offer until `ack_in`) and `icm_v3.CORE_FIELD_TABLES` (ram: `downstream_mask`, `upstream_mask`, `fixed_mode`, `load_data_valid`, `init_data`). The shift is not a ram field: it is the **add-on** (`addon_config`: `shift_en`, `shift_amt`, `direction`), whose bit polarity for `shift_left` was not checked here. Not simulated in 3D, and the toy's one-tick-per-cell timing is not the ram's (it holds a word for two cycles).

## Two forms

* **JSON** — human readable; also carries cell `name`s, a `description` and `meta`.
* **Binary** — little-endian. Header `<4s B B B B B H>`: magic `I3D2`, version (2), family (1 = flex), rows, cols, layers, cell count. Then one 64-bit record per cell, then a CRC-32 of everything before it. No names.

Record bits (LSB first): `row[0:6] col[6:12] layer[12:17] core[17:19] gate_index[19:22] shift[22:27] shift_left[27] out_mask[28:34] in_mask[34:40] reserved[40:64]`. `core`: 0 ram (flowing), 1 nano. `gate_index`: 0 AND, 1 OR, 2 XOR, 3 NOR, 4 NAND, 5 XNOR. **Reserved bits must be zero**; a reader that finds one set refuses (a newer format). Limits: 63 × 63 × 31 squares, 65,535 cells. The 44-cell adder is 367 bytes.

## Use

    python3 experimental/three_d/icm3d_v2.py convert design.3d.json out.icm3d.json   # composer design -> ICM-3D JSON
    python3 experimental/three_d/icm3d_v2.py convert design.3d.json out.icm3d        # -> binary
    python3 experimental/three_d/icm3d_v2.py convert out.icm3d back.3d.json          # back to a composer design
    python3 experimental/three_d/icm3d_v2.py show out.icm3d

The 3D Composer has **Save ICM-3D** and **Save ICM-3D binary** buttons, and **Open file…** reads either form.

## Not done

* No core other than `nano` gates and `ram` pass-throughs: the other ram modes (fixed, preloaded), adder, mul, accumulator, comparator, latch, sequencer, branch, priority, cross, corner, merge and div have no ICM-3D record yet. Their six-face widths are in `CELL_AUDIT_6_FACE.md`; each would need a per-core record layout of its own.
* The `sub` (v4s) family: only `flex` is defined (`family` 1).
* The binary does not carry names, so a name-based check (the adder's "A", "B", "E") needs the names put back.
* No generator, assembler or RTL reads this.
