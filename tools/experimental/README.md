# tools/experimental -- one-off, demo and measurement scripts

Moved here on 9 Oct 2026 (ledger #1036 addendum 20) from `tools/` and `nano/`. They are kept, runnable and labelled, but none has a test of its own, so treat them as **experimental**: check before building on them.

| Script | Kind | Note |
|---|---|---|
| `chaos_topology_v1.py` | experimental | random-topology exploration |
| `experimental_3d_chaos_run_v1.py`, `experimental_3d_crossing_demo_v1.py` | experimental | 3D toy grid; the grid itself (`nano/experimental_3d_grid_v1.py`) stays in `nano/`; its gate-and-shift extension is `nano/experimental_3d_nor_v2.py` (addendum 50) |
| `flow_demo_v1.py`, `lif_demo_v1.py` | demo | show the flow and LIF generators (`tools/flow_flex_v1.py`, `tools/lif_flex_v1.py`, which stay live) working |
| `measure_cell_width_v1.py`, `measure_flag_across_families_v1.py`, `measure_flag_pnr_v1.py` | measurement | the results are in the ledger; re-run to reproduce |
| `placement_extract_v1.py` | experimental | Quartus (Arria 10) placement extractor |

Run from anywhere: each script finds the repo root from its own location (checked for path errors on the day they moved; the long ones were not run to completion).
Older ledger entries and `docs/manual.html` still name the old paths; that is history, not a fault.
