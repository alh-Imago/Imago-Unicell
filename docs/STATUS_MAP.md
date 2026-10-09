# Status map -- what is LIVE, EXPERIMENTAL, or ARCHIVED (9 Oct 2026, ledger #1036 addendum 19)

Nothing in this repo is deleted (standing rule: never remove a proven design; superseded work is kept and labelled). This page says, for each part, which of three states it is in.
It was built from evidence (what the tests run, what imports what, what was last touched, what has run on a board), not from memory, and where the evidence did not settle it the part is marked **RULING NEEDED**.

| State | Meaning |
|---|---|
| **LIVE** | In the current line, covered by tests that pass, and (where it is hardware) either proven on a board or clearly labelled as sim-only. Safe to build on. |
| **EXPERIMENTAL** | Works in simulation or as a prototype, but is unproven on hardware, unmeasured, on a side branch, or deliberately a trial. Do not build on it without checking. |
| **ARCHIVED** | Belongs to a superseded line. Kept byte-for-byte for reference; its commands will not run as written. |

## The lines, at a glance

| Line | State | Where | One-line status |
|---|---|---|---|
| Small unit (Tang Nano 20K + SD + ESP32) | **LIVE** (on hardware) | `fpga/verilog/{sd_unit,sd_stream,sd_spi,spi_bridge,playout,capture}_v1.v`, `tools/sd_unit_top_v1.py`, `fpga/build/unit_cordic_v1/`, `tools/esp32/`, `quickstart.py` | CORDIC design confirmed on the board (SPI results, SD round trip). |
| Flex / sub cell families (the current cells) | **LIVE** | `sub/verilog/`, `tools/flexsub_*`, `tools/project_assemble_v1.py` | Generated and simulated; the CORDIC unit built from them runs on the Tang. |
| Compiler / composer / tile libraries | **LIVE** | `nano/` (DSL, Python AST, LLVM IR frontends, composer page, tile libraries) | Tested; composer opens via `quickstart.py --composer`. |
| Arria 10 / Carrier line (VIX Carrier cores, super shells, Quartus projects, ISSP scripts) | **RULING NEEDED** | `fpga/verilog/` (361 files), `fpga/quartus/`, `fpga/*.tcl` | Real and heavily referenced by tests, but this is the older card; the Tang line has superseded it for day-to-day work. See "Rulings needed". |
| Full-cell line (addressed-bus cell, old VM/compiler/OS stack, Trix family) | **ARCHIVED** | `archeology/` (incl. `archeology/onion/`), `tests/vm/legacy_full_cell/` | Superseded; kept. SensorTrix is the example: its format is reused (live feed), its tiles are not. |
| Hex-N (hex-cell neural substrate) | **EXPERIMENTAL** | branch `Hex-N` (`docs/hex-n/`, `rtl/hexn_cell_v1.v`) | Behavioural RTL + cycle-accurate model only; large (about 1,300 LUT per small cell); not on hardware. Not for main. |

## Small unit parts

| Part | State | Evidence / limit |
|---|---|---|
| CORDIC unit bitstream | LIVE | On the board: six reference answers; SD round trip matched. |
| Reduction tree, relay chain designs | EXPERIMENTAL | Pass in simulation through the real unit top; fit on the part (measured); no bitstream built, nothing on hardware. |
| SPI bridge, playout, capture, SD streamer | LIVE | Hardware-proven for the CORDIC path. |
| S1 reset button | EXPERIMENTAL | Simulated and in the rebuilt bitstream; button not yet pressed on the board. |
| ESP32 bridge sketch (`unicell_unit_bridge`) | LIVE | Used on the board. |
| ESP32 web sketch (WiFi page, file card, live sensors, `sensors.h`) | EXPERIMENTAL | Syntax-checked against stubs only; never compiled for or run on an ESP32. |
| SensorTrix live feed | EXPERIMENTAL | Simulation test passes (`tests/vm/test_unit_live_feed_v1.py`); no sensor attached. |
| SunFounder kit readers (thermistor, ultrasonic, DHT11, ...) | EXPERIMENTAL | Written, not wired; thermistor circuit is an assumption. |
| ESP32 JTAG loader | EXPERIMENTAL (proposal only) | Not built; needs a spare Tang. |
| Wasserstein-2 engine (`tools/ot_w2_v1.py`) | EXPERIMENTAL | Does not fit the Nano 20K even at n=2; needs a bigger part. |

## Tools with no importer and no test (candidates for a label or an archive)

Found by searching every script for references. These are command-line demos or measurement scripts, so "no importer" is normal, but none is covered by a test:
`nano/experimental_3d_chaos_run_v1.py`, `nano/experimental_3d_crossing_demo_v1.py`, `tools/chaos_topology_v1.py`, `tools/flow_demo_v1.py`, `tools/lif_demo_v1.py`, `tools/measure_cell_width_v1.py`, `tools/measure_flag_across_families_v1.py`, `tools/measure_flag_pnr_v1.py`, `tools/placement_extract_v1.py`.
Suggested labels: the two `experimental_3d_*` and `chaos_topology` are EXPERIMENTAL by name and date (28 Aug and 18 Aug); `flow_demo` / `lif_demo` are demos of LIVE-line generators (keep, label demo); the three `measure_*` are one-off measurements whose results are in the ledger (keep, label measurement); `placement_extract` is an older Quartus-era tool (RULING NEEDED).

## Verilog references (how many files anything points at)

| Folder | Files | Referenced by code/scripts | Only by other Verilog | Unreferenced |
|---|---|---|---|---|
| `fpga/verilog` | 361 | 183 | 73 | 105 |
| `sub/verilog` | 74 | 33 | 31 | 10 |
| `archeology/full-cell` | 78 | 25 | 15 | 38 |
| `experimental/shared_buffer_v1` | 16 | 16 | 0 | 0 |
| `tests/fpga` | 22 | 6 | 1 | 15 |
| `fpga/board_tests` | 12 | 0 | 10 | 2 |

"Unreferenced" means no script, test or build file names it, not that it is wrong; the 105 in `fpga/verilog` are mostly older core versions (`*_v1` ... `v3`) kept next to their successors, which is the "clone, don't modify" rule at work. They are the main candidates for moving into an archive, and that move is a ruling, not something to do silently.

## Test evidence behind the LIVE labels (9 Oct 2026)

- The 20 flex/sub script suites (`tests/test_*.py`, each run as a plain script as the README says): **20 of 20 pass** (this session).
- The small-unit suites (`tests/vm/test_unit_*`, `test_spi_bridge`, `test_sd_unit_top`, live feed): pass.
- The full VM suite (`python3 -m pytest tests/vm`): started this session and had passed everything it reached (about a third of it, stopped at first failure) when it was left running; several hardware-simulation tests take minutes each, so the full run takes hours. **Not yet finished, so not claimed.**
- Do **not** run `pytest tests` over the whole folder: the flex/sub files are scripts that exit on import, which makes pytest report 26 collection errors. That is the runner, not a defect in the tests (the same 26 appear on main and on the Hex-N branch).

## Rulings needed from Alan

1. **Arria 10 / Carrier line in `fpga/`**: keep as LIVE reference, mark EXPERIMENTAL (card stalled), or move to an archive folder?
2. **The 105 unreferenced files in `fpga/verilog`**: archive them (keeping the cores that are referenced), or leave and label?
3. **`placement_extract_v1.py`, `chaos_topology_v1.py`, `experimental_3d_*`**: label as above, or archive?
4. **`fpga/board_tests/`** (twelve diagnostic tops): keep as LIVE bring-up tools or archive?

## How to keep this page true
When a part changes state (an EXPERIMENTAL part runs on a board, a LIVE part is superseded), change its row here in the same commit as the ledger entry. The table at the top of `current/latest.md` should point here.
