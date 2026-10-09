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
| Arria 10 / Carrier line (VIX Carrier cores, super shells, Quartus projects, ISSP scripts) | **LIVE target card** (bring-up stalled) | `fpga/verilog/`, `fpga/quartus/`, `fpga/*.tcl`, `hardware/` | Still a target card (Alan, 9 Oct 2026); the PCIe/BAR0 bring-up is stalled and Alan may have a simple fix. Older core versions and their Quartus projects / Tcl scripts are archived in `fpga/archive/arria10_super_line/` (reclaimable); v4, v4c, v4s, v4sa and the VIX carrier v1d stay. |
| Kintex-7 XC7K480T card | **LIVE target card** (PCIe dead, JTAG works) | `fpga/archive/kintex7_xc7k480t/` | Brought up in June 2026 (PCIe Gen2 x8, XDMA, BAR0 round trip proven on real silicon); the PCIe interface then failed, JTAG still works (Alan, 9 Oct 2026). Plan: use it stand-alone, powered via a 1x riser, programmed and tested over JTAG. Sits under `archive/` by Alan's choice for now. |
| Full-cell line (addressed-bus cell, old VM/compiler/OS stack, Trix family) | **ARCHIVED** | `archeology/` (incl. `archeology/onion/`), `tests/vm/legacy_full_cell/` | Superseded; kept. SensorTrix is the example: its format is reused (live feed), its tiles are not. |
| Hex-N (hex-cell neural substrate) | **EXPERIMENTAL** | branch `Hex-N` (`docs/hex-n/`, `rtl/hexn_cell_v1.v`) | Behavioural RTL + cycle-accurate model only; large (about 1,300 LUT per small cell); not on hardware. Not for main. |

## Small unit parts

| Part | State | Evidence / limit |
|---|---|---|
| CORDIC unit bitstream | LIVE | On the board: six reference answers; SD round trip matched. |
| Reduction tree, relay chain designs | LIVE (proven on the board) | Built 9 Oct 2026 (timing met at 27 MHz) and run on the Tang Nano 20K through the unit: relay passes words unchanged, tree sums four. Bitstreams in `fpga/build/unit_relay_v1/` and `unit_tree_v1/`. Rebuilt 9 Oct with the design ID register (register 10); simulated, not yet re-run on the board. |
| SPI bridge, playout, capture, SD streamer | LIVE | Hardware-proven for the CORDIC path. |
| S1 reset button | LIVE (proven on the board) | 9 Oct 2026 (Alan, counting LEDs from 1): fourth LED (guide's LED3, SD up) goes off while S1 is held and comes back on release, i.e. the unit restarts and the SD card re-initialises; first LED (LED0) keeps blinking. Not yet checked after a press: `id` and `status` from the ESP32. |
| ESP32 bridge sketch (`unicell_unit_bridge`) | LIVE | Used on the board. |
| ESP32 web sketch (WiFi page, file card, live sensors, `sensors.h`) | WiFi page + Run proven once; page broke on the next upload (Arduino IDE mangled the page JavaScript, fixed by moving it to page.h, awaiting re-upload); file card and live sensors EXPERIMENTAL | 9 Oct 2026 (Alan): joined WiFi, page loads; status panel shows unit link answering, SD ready, RSSI -52 dBm; Run through the design returns all six CORDIC reference answers (-404, 404, -2726, 821, -821, -2726). Live sensors and the web file card not yet tried. |
| SensorTrix live feed | LIVE (proven on the board: CORDIC, relay and 4-input tree) | 9 Oct 2026: sensors read by the ESP32 and fed live to the running unit. CORDIC: angle 43248 -> 3652 (= simulator). Relay: packed word returned unchanged (29712, loc 1 -> 1947205633). Tree: Run 1 2 3 4 -> 10, 10 20 30 40 -> 100, 100 200 300 400 -> 1000; live four-input sum amount 12600 (6151+304+6145+0), location 12 (3+2+3+4) = 825753612. Only two physical sensors wired (thermistor on two lanes, light; PIR open = 0). |
| SunFounder kit readers (thermistor, ultrasonic, DHT11, ...) | EXPERIMENTAL (potentiometer proven) | Potentiometer works on GPIO35 (first live reading 9 Oct 2026). Light sensor, thermistor, PIR, tilt, ultrasonic, DHT11 written, not wired; thermistor circuit is an assumption. |
| ESP32 JTAG loader | EXPERIMENTAL (proposal only) | Not built; needs a spare Tang. |
| Wasserstein-2 engine (`tools/ot_w2_v1.py`) | EXPERIMENTAL | Does not fit the Nano 20K even at n=2; needs a bigger part. |

## Scripts with no importer and no test: now labelled and in `tools/experimental/`

Nine scripts (the 3D chaos pair, `chaos_topology`, `flow_demo`, `lif_demo`, three `measure_*`, `placement_extract`) had nothing importing them and no test. They were moved, labelled and given a README at [`tools/experimental/`](../tools/experimental/README.md) on 9 Oct 2026.

## Verilog references (corrected)

An early count here said 105 of 361 files in `fpga/verilog` were unreferenced; that matched file names only and was wrong. Matching module names as well: of 123 top-level files, 25 are named by no script, test, build file or other Verilog -- 23 are testbenches (standalone by nature) and 2 were shells (`cross_shell_v1`, `merge_shell_v1`; `corner_shell_v1` joined them on a second pass). Older core versions are still named by Quartus projects; `fpga/verilog/VERSIONS.md` (made by `tools/verilog_versions_v1.py`) lists each one and what names it.

## Test evidence behind the LIVE labels (9 Oct 2026)

- The 20 flex/sub script suites (`tests/test_*.py`, each run as a plain script as the README says): **20 of 20 pass** (this session).
- The small-unit suites (`tests/vm/test_unit_*`, `test_spi_bridge`, `test_sd_unit_top`, live feed): pass.
- The full VM suite (`python3 -m pytest tests/vm`): started this session and had passed everything it reached (about a third of it, stopped at first failure) when it was left running; several hardware-simulation tests take minutes each, so the full run takes hours. **Not yet finished, so not claimed.**
- Do **not** run `pytest tests` over the whole folder: the flex/sub files are scripts that exit on import, which makes pytest report 26 collection errors. That is the runner, not a defect in the tests (the same 26 appear on main and on the Hex-N branch).

## Rulings made (Alan, 9 Oct 2026) and what was done

1. **Arria 10 and Kintex 480T are still target cards (the Kintex is the card whose PCIe died and JTAG works)**: both labelled LIVE target above.
2. **Older core versions should be archived**: keep v4, v4c, v4s, v4sa (plus unnumbered add-ons and the v5/v5c file); archive the rest and the Arria 10 scripts that use them. **Done (addendum 21)**: 293 files moved to `fpga/archive/arria10_super_line/` with a manifest and `tools/archive_move_v1.py --reclaim` to bring any back; paths rewritten; before/after checks identical (22 tests, 7 generated projects, flex/sub scripts, small-unit suites). Left in place: the `unicell_super_v1..v9` shells (the composer lists them), and carrier v1 (many testbenches use it; v1d is the latest). Earlier, the three unused shells went to `fpga/archive/older_cores/`. Quartus is not available here, so the archived projects were not compiled.
3. **The odd nine scripts**: labelled and moved to `tools/experimental/` (README there).
4. **`fpga/board_tests/`** (twelve diagnostic tops): left in place and still listed LIVE as bring-up tools. RULING STILL OPEN if Alan meant these when he said "the fpga test tools" go in a marked folder under tools.

## How to keep this page true
When a part changes state (an EXPERIMENTAL part runs on a board, a LIVE part is superseded), change its row here in the same commit as the ledger entry. The table at the top of `current/latest.md` should point here.
