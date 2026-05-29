# Subfolder Audit
**Created: 2026-05-29**

Each folder audited file by file. Same approach as root FILE_AUDIT.md.
Tick off as validated/fixed. Note tests needed alongside each file.

---

## `fpga/` — FPGA bridge, loader, Verilog

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `fpga_bridge.py` | 2026-05-28 | [x] | Updated this session — configure_cell(), preload_cell() wired |
| `icm_loader.py` | 2026-05-28 | [x] | Updated this session — init field → preload_cell() |
| `ping_test.py` | 2026-05-14 | [x] | VALIDATED 2026-05-29. CMD codes match unicell.v. Raw UART protocol intentional. No changes needed. |
| `verilog/unicell.v` | 2026-05-28 | [x] | Updated this session — CMD_PRELOAD, bus_hit_r, dbg fix |
| `verilog/unicell_array.v` | 2026-05-28 | [x] | Updated this session — CMD_PRELOAD in runtime targeted |
| `verilog/tb_unicell_v2.v` | 2026-05-28 | [x] | Updated this session — tests [17][18][19] added |
| `verilog/top_icebreaker.v` | 2026-05-23 | [x] | VALIDATED 2026-05-29. Compiles clean (SB_HFOSC is iCE40 primitive, expected). No changes needed. |
| `verilog/top_kintex7.v` | 2026-05-23 | [x] | VALIDATED 2026-05-29. Compiles clean with uart_bridge. Only pre-existing width warnings. No changes needed. |
| `verilog/top_arty_a7.v` | 2026-04-24 | [~] | Deferred — oldest file, low priority, not active target. |
| `verilog/uart_bridge.v` | 2026-05-25 | [x] | VALIDATED 2026-05-29. Passes opcodes through transparently — no clash with CMD_PRELOAD (0x0F). |
| `verilog/blink_test.v` | 2026-05-05 | [x] | Sanity test only — self-contained, no API dependencies. |
| `README_FPGA.md` | 2026-05-11 | [ ] | Deferred — update after iCEBreaker live bring-up |

**Tests needed:** `tests/fpga/` folder — currently empty, needs bring-up scripts

---

## `imago/` — CLI and library entry points

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `__init__.py` | 2026-05-11 | [x] | VALIDATED 2026-05-29. VM/run_icm/compile_function all work. workspace.py fixes flow through correctly. |
| `cli.py` | 2026-05-11 | [x] | VALIDATED 2026-05-29. run/compile/examples/info all work. Positional input syntax confirmed. |
| `library.py` | 2026-05-11 | [x] | VALIDATED 2026-05-29. add/scan/get/remove cycle works. ICM format v2 loads correctly. |

**Tests needed:** basic CLI smoke test

---

## `pcie/` — PCIe / XDMA bridge (blocked on hardware)

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `top_xdma_unicell.v` | 2026-05-26 | [ ] | Most recent — check after Optiplex test |
| `axi_unicell_bridge.v` | 2026-05-24 | [ ] | AXI bridge — check after Optiplex test |
| `unicell_xdma.py` | 2026-05-24 | [ ] | XDMA Python driver — blocked on PCIe enumeration |
| `unicell_tool.py` | 2026-05-23 | [ ] | Tool CLI — blocked on PCIe enumeration |
| `litepcie_unicell_top.py` | 2026-05-23 | [ ] | LitePCIe top — blocked |
| `platform_ypcb003381p1.py` | 2026-05-23 | [ ] | Platform config — check XDC still matches |

**All blocked on PCIe enumeration on Optiplex 9020.**

---

## `composer/` — Standalone HTML design tool

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `unicell_composer.html` | 2026-05-28 | [x] | Updated this session — semantic display, pond vis, tree, link highlight |
| `models/INDEX.md` | 2026-05-11 | [ ] | Model index — update cell counts/depths against current tiles |
| `README.md` | 2026-05-06 | [ ] | Stale — update after workbench features land |

**Tests needed:** open in browser, load adder32.icm, verify pan/zoom/tree/pond

---

## `docs/` — Architecture and reference docs

### Current (need review against recent changes)
| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `ICM_FORMAT.md` | 2026-05-28 | [x] | Updated this session — format v2, gate_state table |
| `ARCHITECTURE.md` | 2026-05-20 | [x] | UPDATED 2026-05-29. gate_state bit table corrected (GS_SYNC_WAIT retired, GS_LATCH_IN/ONE_SHOT/LOOP_BACK correct). Gate function table updated. Cell count 482→589. |
| `CELL_INTERNALS.md` | 2026-05-20 | [ ] | Check gate_state bit table matches current layout |
| `COMPOUND_OPCODES.md` | 2026-05-25 | [x] | UPDATED 2026-05-29. CMD_PRELOAD (0x0F) and CMD_PRELOAD_HI (0x16) section added. |
| `FPGA_HARDWARE.md` | 2026-05-25 | [ ] | Check bring-up findings, PCIe status |
| `RESULTS.md` | 2026-05-26 | [x] | UPDATED 2026-05-29. Latest results added: 161/161 fp_tiles, 21/30 suite, 589 cells KS. |
| `INDEX.md` | 2026-05-24 | [ ] | Check links still valid |
| `ADDER_REFERENCE_MODEL.md` | 2026-05-18 | [x] | UPDATED 2026-05-29. Cell count 482→589. |
| `KS_ADDER_UNICELL.md` | 2026-05-18 | [x] | UPDATED 2026-05-29. Cell count 482→589. |
| `BRANCH_DECISION_TREE.md` | 2026-05-18 | [ ] | Check against current BranchPoint API |
| `RUNNING.md` | 2026-05-11 | [ ] | Check install/run instructions still work |
| `LIBRARY.md` | 2026-05-11 | [x] | UPDATED 2026-05-29. INT32_MIN_U/MAX_U added. |
| `EXAMPLES.md` | 2026-05-10 | [ ] | Oldest current doc — check examples still run |
| `LLVM.md` | 2026-05-10 | [ ] | Check llvmlite install note |
| `VERILOG_SPEC.md` | 2026-05-10 | [x] | UPDATED 2026-05-29. GS_SYNC_WAIT marked retired/implemented. Two-arrival is default. CMD_PRELOAD (0x0F) documented. |

### Likely stable (lower priority)
| File | Status | Notes |
|------|--------|-------|
| `NEURAL_POND_TUTORIAL.md` | [ ] | Tutorial — check against pond API |
| `VM_GETTING_STARTED.md` | [ ] | Check VAR_TRUE=0xFFFFFFFF in examples |
| `VISION.md` | [ ] | Stable — unlikely to need changes |
| `addressing_note.md` | [ ] | Internal note — review |
| `DOC_AUDIT.md` | [ ] | Existing doc audit — superseded by this file? |

### Archive (docs/archive/) — 2026-05-11, low priority
| Status | Notes |
|--------|-------|
| [ ] | 10 architecture docs — historical reference, probably fine as-is |
| [ ] | COMMAND_REFERENCE.md — likely stale, check against current opcodes |

### Diagrams (docs/diagrams/) — 2026-05-11
| Status | Notes |
|--------|-------|
| [ ] | 7 diagram markdown files — check against current architecture |

---

## `hardware/` — Hardware notes

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `YPCB_00338_bringup_findings.md` | 2026-05-26 | [ ] | Update after Optiplex test |

---

## `tests/` — Test suites

### `tests/vm/` — VM simulator tests (main suite)
See TEST_AUDIT.md for full breakdown.

| Summary | Count |
|---------|-------|
| Passing | 21 |
| Failing (Category E) | 6 |
| Archived to legacy/ | 8 |
| Skip (no pygame) | 1 |

**Remaining 6 failures all need ProgramBuilder preloaded-A update.**

### `tests/fpga/` — Hardware tests
| File | Status | Notes |
|------|--------|-------|
| (empty) | [ ] | Needs bring-up test scripts after iCEBreaker live |

### `tests/vm/legacy/` — Archived v1 tests
| Status | Notes |
|--------|-------|
| Archived | 8 files — kept for reference, not run |

---

## Progress summary

| Folder | Total files | Done | Partial | Pending | Blocked |
|--------|------------|------|---------|---------|---------|
| `fpga/` | 12 | 5 | 0 | 6 | 1 |
| `imago/` | 3 | 0 | 0 | 3 | 0 |
| `pcie/` | 6 | 0 | 0 | 0 | 6 |
| `composer/` | 3 | 1 | 0 | 2 | 0 |
| `docs/` | ~40 | 1 | 0 | ~39 | 0 |
| `hardware/` | 1 | 0 | 0 | 1 | 0 |
| `tests/vm/` | 36 | 21 | 0 | 6 | 0 |

