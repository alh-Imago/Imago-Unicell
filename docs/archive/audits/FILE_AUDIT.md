# Stale Root File Audit
**Updated: 2026-05-31 — v2.3 protocol session**

Tracks files by dependency order (foundations first).
Check off each item as updated and tested.

---

## Tier 0 — Verilog / hardware

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `fpga/verilog/unicell.v` | 2026-05-31 | [x] | **v2.3** cmd_bus widened to 32-bit unified word. CMD_BOOT_COMMIT added. preload_sel (bits 18:17), shift_in/out (bits 20:19), gate_enable+gate_set (bits 16:8), auth_token (bits 28:21). Shift barrel added to data path. Both BOOT and RUN states. |
| `fpga/verilog/unicell_array.v` | 2026-05-31 | [x] | **v2.3** cmd_bus widened to 32-bit. cmd_code wire updated. |
| `fpga/verilog/uart_bridge.v` | 2026-05-31 | [x] | **v2.3** 9-byte UART_INJECT frame. cpu_bus[31:0] replaces cpu_cmd+cpu_addr. Frame decoder updated. |
| `fpga/verilog/top_icebreaker.v` | 2026-05-31 | [x] | **v2.3** cpu_bus[31:0] wiring. cmd_valid_w checks cpu_bus[7:0]. |
| `fpga/fpga_bridge.py` | 2026-05-31 | [x] | **v2.3** + v2.2 legacy shims. build_cmd_bus(), preload_sel, CMD_BOOT_COMMIT, 9-byte packets with protocol_v22 flag for iCEBreaker compat. |

---

## Tier 1 — Foundations (no internal deps)

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `gate_states.py` | 2026-05-31 | [x] | **FIXED** GS_LATCH_IN bit 25→26 (0x02000000→0x04000000). GS_INVERT_OUT_BIT added at bit 25. GS_FALL_EDGE = edge+negedge. LOOP_MODE=0 bug fixed → GS_LOOP_BACK. Auth_mask 11-bit→8-bit. |
| `model_library.py` | 2026-05-31 | [x] | **EXPANDED** All stale figures corrected (TileLibrary verified). 18 new models added. 54 total. v2.3 notes on shift/preload/accumulator. |
| `llvm_frontend.py` | 2026-05-09 | [x] | VALIDATED. No changes needed. |
| `shore.py` | 2026-04-17 | [x] | VALIDATED. No changes needed. |

---

## Tier 2 — Core runtime

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `unicell.py` | 2026-05-31 | [x] | **FIXED** latch_in reads bit 26, invert_out reads bit 25. gate_states imports added. |
| `command_interface.py` | 2026-05-31 | [x] | **REWRITTEN v2.3** build_cmd_bus, CMD_BOOT_COMMIT, preload_sel, gate_set, shift_sel, boot_cell(), full docs. |
| `pipeline_queue.py` | 2026-05-10 | [ ] | Deferred — no active callers. |
| `workspace.py` | 2026-05-29 | [x] | FIXED _run_via_compiler() fast path. |
| `fs_search.py` | 2026-05-29 | [x] | VALIDATED. No changes needed. |

---

## Tier 3 — Application layer

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `gol.py` | 2026-05-31 | [x] | **FIXED** Removed retired GS_SYNC_WAIT, GS_OUT_POSEDGE, input_b_address. Two-arrival is default. |
| `postcode_sort.py` | 2026-05-31 | [x] | **FIXED** Cell count 775→711 (INT32_CAS verified). Header estimates corrected. |
| `display_pond.py` | 2026-05-10 | [ ] | Deferred — low priority. |
| `companion.py` | 2026-05-29 | [x] | VALIDATED. No changes needed. (companion-side updates deferred until base stable) |
| `llvm_ir_mapper.py` | 2026-05-10 | [ ] | Deferred. |

---

## Examples / ICM files

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `composer/examples/lif_neuron.icm` | 2026-05-31 | [x] | **FIXED** All gs values corrected for v2.3. C0: 0x84000000, C3: 0x40000000, C4: 0x04000000. Hash recalculated. |
| `imago/examples/lif_neuron.icm` | 2026-05-31 | [x] | **FIXED** Same corrections. |
| `composer/examples/lif_cascade.icm` | 2026-05-28 | [ ] | Needs gs review — not yet checked. |
| `imago/examples/lif_cascade.icm` | 2026-05-28 | [ ] | Needs gs review. |

---

## Docs updated this session

| File | Status | Notes |
|------|--------|-------|
| `docs/CELL_INTERNALS.md` | [x] | Rewritten for v2.3 — ground truth reference |
| `docs/FPGA_HARDWARE.md` | [x] | Full rewrite — v2.3 protocol, boot sequence, preload_sel, shift_sel |
| `docs/VERILOG_SPEC.md` | [x] | Gate_state parity table corrected to v2.3 bit positions |
| `docs/COMPOUND_OPCODES.md` | [x] | cmd_bus layout updated, CMD_PRELOAD→preload_sel |
| `docs/ARCHITECTURE.md` | [x] | Preload references updated |
| `docs/PRELOAD_MODEL.md` | [x] | preload_sel references added |
| `docs/DOC_AUDIT.md` | [x] | v2.2→v2.3 change table, files-updated tracker |
| `docs/neural_pond_design.md` | [x] | LIF cell table corrected for v2.3 gs values |
| `composer/unicell_composer.html` | [x] | GS bits corrected, 20+ new models, tree panel enhanced |
