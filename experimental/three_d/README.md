# experimental/three_d -- the 3D toy grids (VM only)

Gathered here on 20 Oct 2026 (ledger #1308). The files were **moved, not changed**; the old paths hold small pointer stubs, so existing imports and commands still work.

## What is real and what is a model

| | |
|---|---|
| **Real hardware** | None of this. The chips built so far have four face ports (north, south, east, west). Some cores carry 3D address masks, and the 6-bit direction masks in the cores leave room for up and down, but no 3D wiring exists in any RTL, and no 3D design has run on a card. |
| **Model (VM only)** | A toy grid with six neighbours per cell (north, south, east, west, up, down) in Python. It shows what a stacked-chip layout *could* do: wires crossing over each other through the third direction, and a NOR-built adder laid out in the six-neighbour grid. |
| **Why it is kept** | Stacked chips are a possible future design route. These files let the idea be explored without touching the real design. Any result here is a statement about the model only. |

**Exploration only (Alan, 23 Oct 2026).** There is no card to run any of this on. The 3D adder layout was not found by an automatic placer: its stage tile is placed by a hand-derived formula, only the end cells and long nets are searched, and an automatic annealing placement was tried first and never became routable (#1036 addendum 50). `CELL_AUDIT_6_FACE.md` (and `cell_face_budget_v1.py`) set out, cell type by cell type, what six faces would cost; it is a paper audit (#1310).

## Files

| File | What it is | Old path (now a pointer) |
|---|---|---|
| `experimental_3d_grid_v1.py` | the toy 3D grid (`Grid3D`, `ToyCell3D`), ledger #520 | `nano/experimental_3d_grid_v1.py` |
| `experimental_3d_nor_v2.py` | six-neighbour grid with gate and shift cells (ledger #1036 addendum 50) | `nano/experimental_3d_nor_v2.py` |
| `experimental_3d_chaos_run_v1.py` | a 5x5x5 random grid run | `tools/experimental/experimental_3d_chaos_run_v1.py` |
| `experimental_3d_crossing_demo_v1.py` | the wire-crossing test | `tools/experimental/experimental_3d_crossing_demo_v1.py` |
| `CELL_AUDIT_6_FACE.md`, `cell_face_budget_v1.py` | new (#1310): what each cell type needs for six faces, and the ICM v3 config-bit budget (re-runnable) | -- |
| `composer3d_v1.py`, `composer3d_v1.js` | new (#1312): a separate Composer for the six-face toy grid: floor plan, rotatable 3D view, depth slider (current layer shown, others faded); `python3 experimental/three_d/composer3d_v1.py` (port 7422) | `tests/vm/test_composer3d_v1.py` |
| `placer3d_v1.py` | new (#1313): an automatic placer and router for the six-face toy grid; any feed-forward netlist; every layout is proven by running it; `--example adder --layers 3` | `tests/vm/test_placer3d_v1.py` |
| `icm3d_v1.py` | #1313: ICM-3D v1 (toy relay pseudo-core); kept as written, superseded by v2 | `tests/vm/test_icm3d_v1.py` |
| `icm3d_v2.py`, `ICM_3D_FORMAT.md` | new (#1314): ICM-3D v2, a standalone six-face file format (flex family; JSON and binary); a relay is a ram cell in flowing mode; the composer saves and opens it | `tests/vm/test_icm3d_v2.py` |
| `MANUAL_3D.md`, `build_manual_3d_v1.py`, `manual3d.html` | new (#1315): the 3D kit's OWN manual (separate from `docs/manual.html`); rebuild the html with `python3 experimental/three_d/build_manual_3d_v1.py` after editing it, `ICM_3D_FORMAT.md` or `CELL_AUDIT_6_FACE.md`; also served at `/manual` by the composer | -- |
| `make_bundle_v1.py` | new (#1315): builds the separate download kit `dist/imago-3d-kit-<date>-<commit>.zip` (stdlib only, from a clean commit, unpacks and runs its own 55 tests as a check); `python3 experimental/three_d/make_bundle_v1.py` | -- |

The two demos find the grid file through `nano/` (the pointer), which works as before.

Tests that use these files: `tests/vm/test_nor_adder_3d_v1.py`, and the file-exists check in `tests/vm/test_unit_bringup_v1.py`. The adder layout tool is `tools/nor_adder_3d_v1.py` (stays in `tools/`).
