# What each cell type needs to have six faces (N, S, E, W, U, D)

*Audit of 23 Oct 2026. Paper analysis of the real RTL and code: **no 3D RTL exists and nothing here was simulated in 3D.** The number of stacked layers is a free variable (a stack can be 2 or 20 high), so the question is not "how thin" but "what must a cell itself carry to have all six faces". Everything below was read from the named files or measured by the scripts named; the last section lists what was NOT checked.*

> **Scope (Alan, 23 Oct 2026): this is an exploration, not a design under way.** There is no card that could run any of it, nothing 3D exists in RTL, and the one 3D layout (the NOR adder) was placed by a hand-derived stage-tile formula with only the end cells and long nets searched automatically; an automatic simulated-annealing placement was tried first (#1036 addendum 50) and never produced a routable layout. Read the decisions at the end as a menu of what six faces would cost, not as a to-do list.

## The short answer

A cell touches direction in **three places**. Each cell type was checked for all three:

1. **Ports** (the physical faces).
2. **Direction fields** (which faces a cell listens on / sends to).
3. **Face-indexed logic** (selects, ack vectors, tie-break order, the programming channel).

The cell families differ a lot:

| Family | Files | Direction in the cell | Six faces mean |
|---|---|---|---|
| **Flex / sub** (the active line, Tang Nano) | `sub/verilog/*_v4sa.v`, `*_v4s.v` | **None.** Cells have generic lanes (data, valid, ack). Which neighbour a lane meets is decided by the netlist, not the cell. | No cell change, except **corner, cross, priority**. The change is in the ICM masks, the assembler, the layout tool and the VM. |
| **Standard** (carrier / super shells, Arria 10 line) | `fpga/verilog/*_cell_v4c.v`, shells, `unicell_vix_carrier_v1d.v` | **Everywhere.** Four named faces on every core and on the carrier. | Every one of the 15 cores, its shell and the carrier. |

## Flex / sub family: only three cells know about faces

Checked by listing every module's ports in `sub/verilog` (a throwaway scan, not saved): the only cells with face-named ports are

| Cell | Why it is face-aware | What six faces needs |
|---|---|---|
| `corner`, `cross` | four independent one-word slices, one per face a word enters by; `partner(face)` is a hard-coded 4-entry table (cross: N-S, E-W; corner: N-E/S-W or N-W/S-E) | **six slices.** Cross gains the U-D pair (three straight-through pairs). Corner is the real design question: with six faces a "turn" is no longer one bit (`TURN`); a pairing of six faces into three pairs has 15 possibilities, so the partner map needs to be a configured table, not two parameters. |
| `priority` | four inputs named `in_n/s/e/w`, four per-face ranks, tie-break "a fixed N>S>E>W order", weighted round-robin credits one per face | two more inputs, two more ranks, two more credit counters; the tie-break order extends U, D (so every existing four-face design keeps its result). |

Every other flex cell (nano, ram, mask, shift, compare, sequencer, accumulator, latch, merge, router, adder, mul, div, branch) has 2 to 4 lanes in and out and **no face in its RTL**. A six-face grid does not change them. What it removes is the 2D cost of having more than four neighbours (the toy adder shows 44 cells against 80).

One thing to keep in mind: a face carries a lane in and a lane out, so "faces needed" is the number of *distinct neighbours*, which is at most the number of lanes. Priority (4 in + 1 out) and the two-output cells (adder, mul, div, branch: 2 in + 2 out) are the ones that can need four or more neighbours.

Also order-sensitive: `merge` (A = the first set upstream bit in N,S,E,W order) and the two-operand cells (the first arrival is A) rely on face order only to break ties; adding U and D after W keeps every existing result.

## Standard family: the core-by-core table (v4c RTL)

Measured from the RTL (`fpga/verilog/*_v4c.v`, `mul_cell_v5c.v`):

* **Direction registers are already 6 bits wide** in every core ("N/S/E/W real + 2 reserved"), and `branch` has a 3-bit direction and 6-bit routes. **Nothing reads bit 4 or bit 5 of any of them**, so this is headroom, not a half-built feature. (Nano ties its top two bits to `2'b00`.)
* **Ack vectors are 4 bits** (`pending_ack`, `ack_in_vec`) in every core except nano, whose `pending_ack` is 6 bits with the top two always zero.
* **Select logic is four copies**: `sel_n/s/e/w = arrived_x && mask[0..3]`, and the data path ORs four buses.
* **The programming channel is four faces in all 15 cores** (checked: every file has the `prog_sel_n/s/e/w` chain with a fixed N>S>E>W priority and four `prog_data_in_*` buses). Programming reaches a cell through a neighbour, so in a stack a cell must be programmable from U and D as well.
* **Ports**: every core and every shell has `arrived/fire/ack/ready/data` per face, four times.

| Core | Direction fields today | Specific work for six faces |
|---|---|---|
| nano (`nano_gate_v4c`) | `routing_mask` 6, `cardinal_edge` 6, `pending_ack` 6; the three 4-bit routing patterns | Already the closest: widen the three patterns, add `sel_u/d`, use ack bits 4-5. Its "ready" is broadcast on all four faces. |
| ram | down 6, up 6 | selects and ack vector |
| adder, mul, div | down, up, second-down 6 each | same; second word leaves by its own mask |
| accumulator | inc_dir, dec_dir, down | same |
| comparator | down, up | same |
| latch | set, clear, toggle, down | four masks |
| sequencer | down | one mask |
| branch | `upstream_dir` 3-bit **encoded** (0-3 used), three 6-bit routes | the encoded direction already holds 0-5; the compare of `== 3'd0..3` extends; routes widen their active use |
| priority | masks 6, ranks 2x4, `sequence_0..3` 2-bit | ranks and credits per face; sequence entries become 3-bit (a six-turn order needs six entries) |
| merge | up, down | A/B order by face index |
| cross, corner | 4 slices | six slices and the partner table (see above) |
| command | `drive_dir` 3-bit (0-3 used) | freeze / program drive outputs for U and D; `drive_dir` already holds 4-5 |

## The ICM v3 file format is the one real squeeze

`nano/icm_v3.py`'s `core_config` is a **42-bit union** shared by all cores. Re-run `python3 experimental/three_d/cell_face_budget_v1.py`:

| core | uses | with six faces | verdict |
|---|---|---|---|
| nano | 41 | 47 | over by 5 |
| ram | 42 | 46 | over by 4 |
| accumulator | 37 | 43 | over by 1 |
| comparator | 40 | 44 | over by 2 |
| branch | 42 | 49 | **over by 7** |
| priority | 29 | 41 (47 if a full six-turn order is allowed) | fits (tight) |
| adder, mul, div | 25 | 31 | fits |
| latch | 16 | 24 | fits |
| sequencer | 38 | 40 | fits |
| cross, corner, merge | 8-10 | 12-14 | fits |

So **five cores do not fit the 42-bit union with six faces**; the worst needs 49. This is a limit of the *file layout*, not of the cells: the standalone v4c cores take 64-, 80- or 128-bit config words, and the VIX carrier's `core_config` is 128 bits. The old 80-bit SUPER_LATCH has 11 reserved bits `[79:69]`, enough for the worst case (7), but using them moves every field after them (the carrier shells and the ICM encoder/decoder would change together). The 3D toy's own header (#520) already said branch was at the edge of the 42 bits (41 then; 42 today, since `rolling_mode` was added) for the same reason.

## Wires per face (the cost of two more faces)

Counted from the port lists:

| Where | Wires per face | Four faces | Six faces |
|---|---|---|---|
| flex lane (one link, `WIDTH` = 32) | 34 (data 32, valid, ack) | n/a (per link) | n/a |
| `unicell_super_v3` shell | 102 | 408 | 612 |
| `unicell_vix_carrier_v1d` | 141 (four 32-bit buses: data in/out and programming in/out) | 564 | 846 |

For a real stacked chip the two vertical faces are the through-silicon connections, so these counts matter. The flex lane is far cheaper than the carrier face, because the carrier face carries a programming bus both ways.

## Software that hard-codes four directions

49 non-archived Python files in `nano/` and `tools/` name four directions (delta tables, opposite-face tables, direction-bit maps), including `icm_v3.py`, `unicell_super_automaton_v1.py`, `flex_grid_v1/v2.py`, `flex_layout_v1.py`, `design_map_v1/v2.py`, `walker_card_v1/v2.py`, and every `flexsub_icm_*` generator. (Found by searching for the direction tables, not by reading each file; some may need no change.)

## What was NOT checked

* The per-core **shells** (`*_shell_v1c.v`) and carrier internals beyond their port lists and the header of `v1d`.
* The Flex-Sub assembler / ICM generators: found by name only; not read for how a mask becomes a link.
* Timing and area of six-face cells (nothing built).
* Whether `priority`'s weighted round-robin keeps its fairness with six requesters (a behaviour question, not a width one).
* The standard-VM's treatment of simultaneous arrivals on U/D (the VM would need the same extension).
* The `sub` (v4s) family was checked by port list only (same result as flex: only corner and cross carry faces).

## Decisions only Alan can make

1. **Which family first?** Flex/sub needs almost no cell change (three cells) and the most tool change; the standard family needs all 15 cores plus shells.
2. **Corner in 3D:** keep it as a fixed set of turn tiles, or make the partner table configurable?
3. **Fixed-order extension:** U and D after W everywhere (keeps all four-face designs identical) — recommended unless there is a reason to put them first.
4. **ICM format:** a v4 with per-core widths, or use the 11 reserved bits.
5. **Programming a stack:** the programming channel enters through faces, so it needs vertical entry; decide whether a stack is programmed layer by layer or through the vertical faces.
