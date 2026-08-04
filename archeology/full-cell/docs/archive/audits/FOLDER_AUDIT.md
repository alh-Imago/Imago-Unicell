# Subfolder Audit
**Updated: 2026-05-31 — v2.3 protocol session**

---

## `fpga/` — FPGA bridge, loader, Verilog

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `fpga_bridge.py` | 2026-05-31 | [x] | **v2.3** build_cmd_bus(), preload_sel, CMD_BOOT_COMMIT, 9-byte packets. v2.2 legacy shims for iCEBreaker compat. |
| `icm_loader.py` | 2026-05-28 | [x] | Updated previous session — init field → preload_cell() |
| `ping_test.py` | 2026-05-29 | [x] | VALIDATED. CMD codes match. Raw UART intentional. |
| `verilog/unicell.v` | 2026-05-31 | [x] | **v2.3** 32-bit cmd_bus, CMD_BOOT_COMMIT, preload_sel, shift barrel, BOOT/RUN states. |
| `verilog/unicell_array.v` | 2026-05-31 | [x] | **v2.3** cmd_bus widened. |
| `verilog/uart_bridge.v` | 2026-05-31 | [x] | **v2.3** 9-byte frame, cpu_bus[31:0] output. |
| `verilog/top_icebreaker.v` | 2026-05-31 | [x] | **v2.3** cpu_bus wiring, cmd_valid checks opcode field. |
| `verilog/top_kintex7.v` | 2026-05-29 | [x] | VALIDATED. Compiles clean. |
| `verilog/tb_unicell_v2.v` | 2026-05-28 | [x] | Updated previous session. |
| `verilog/top_arty_a7.v` | 2026-04-24 | [~] | Deferred — not active target. |
| `verilog/blink_test.v` | 2026-05-05 | [x] | Self-contained sanity test. |
| `README_FPGA.md` | 2026-05-11 | [ ] | Deferred — update after iCEBreaker live bring-up. |

**Next:** SYNC_WAIT test on iCEBreaker with v2.3 bitstream. CMD_BOOT_COMMIT first silicon test.

---

## `imago/` — CLI and library entry points

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `__init__.py` | 2026-05-29 | [x] | VALIDATED. |
| `cli.py` | 2026-05-29 | [x] | VALIDATED. |
| `library.py` | 2026-05-29 | [x] | VALIDATED. |
| `examples/lif_neuron.icm` | 2026-05-31 | [x] | **FIXED** v2.3 gs values. |
| `examples/lif_cascade.icm` | 2026-05-28 | [ ] | Needs gs review. |

---

## `composer/` — HTML composer and ICM examples

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `unicell_composer.html` | 2026-05-31 | [x] | **v2.3** GS bits corrected (latch_in bit26, invert_out bit25). PRESETS fixed. 20+ new models. Enhanced tree panel with tile sub-tree display. |
| `examples/lif_neuron.icm` | 2026-05-31 | [x] | **FIXED** v2.3 gs values. |
| `examples/lif_cascade.icm` | 2026-05-28 | [ ] | Needs gs review. |
| `models/INDEX.md` | 2026-05-28 | [ ] | Update when model count stabilises. |

---

## `docs/` — Architecture and reference docs

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `CELL_INTERNALS.md` | 2026-05-31 | [x] | Rewritten for v2.3. Ground truth reference. |
| `FPGA_HARDWARE.md` | 2026-05-31 | [x] | Full v2.3 rewrite. |
| `VERILOG_SPEC.md` | 2026-05-31 | [x] | Gate_state parity table v2.3. |
| `COMPOUND_OPCODES.md` | 2026-05-31 | [x] | cmd_bus layout + preload_sel. |
| `ARCHITECTURE.md` | 2026-05-31 | [x] | Preload references updated. |
| `PRELOAD_MODEL.md` | 2026-05-31 | [x] | preload_sel noted. |
| `DOC_AUDIT.md` | 2026-05-31 | [x] | v2.2→v2.3 change table. |
| `neural_pond_design.md` | 2026-05-31 | [x] | LIF gs values corrected. |
| `BRANCH_DECISION_TREE.md` | 2026-05-29 | [x] | Protocol version note added. |
| `RESULTS.md` | 2026-05-29 | [x] | Silicon results current. |
| `RUNNING.md` | 2026-05-29 | [x] | Current. |
| `VM_GETTING_STARTED.md` | 2026-05-29 | [x] | Current. |
| `lif_neuron_reference.v` | 2026-05-29 | [ ] | Reference Verilog — gs values may need review. |

---

## `tests/` — Test suite

| Folder | Status | Notes |
|--------|--------|-------|
| `tests/vm/` | [x] | 48/48 passing (session end). |
| `tests/fpga/` | [ ] | v2.2 format — update alongside uart_bridge.v hardware bring-up. |
| `tests/vm/legacy/` | [ ] | tick() API removed — pre-existing failures, deferred. |
