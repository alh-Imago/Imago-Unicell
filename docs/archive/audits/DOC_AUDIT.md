# Documentation Consistency Audit
**Ground truth: `fpga/verilog/unicell.v` (silicon validated) and `docs/CELL_INTERNALS.md`**
**Updated: 2026-05-30 — v2.3 protocol**

> **Historical note:** This document tracks the audit trail from v1 → v2.2 → v2.3.
> Current canonical reference: `docs/CELL_INTERNALS.md` (rewritten for v2.3).

---

## Architectural Changes — v2.2 → v2.3 (2026-05-30)

| Change | v2.2 | v2.3 (Current) |
|--------|------|----------------|
| cmd_bus width | 8-bit (opcode only) | **32-bit unified word** |
| auth_token position | cmd_data[31:24] | **cmd_bus[28:21]** |
| auth_mask in RECONFIGURE | cmd_data[31:24] | **cmd_data[30:23]** |
| Preload mechanism | CMD_PRELOAD + CMD_PRELOAD_HI (2 transactions) | **preload_sel bits cmd_bus[18:17] (1 transaction)** |
| Shift mechanism | not implemented | **shift_sel bits cmd_bus[20:19], amount in cmd_data[3:0]** |
| Group targeting | cmd_addr per-cell | **gate_enable + gate_set in cmd_bus[16:8]** |
| Boot sequence | 4 packets (RECONFIGURE+SET_LOGICAL+SET_OUTPUT_ADDR+RELEASE) | **2 packets (CMD_BOOT_COMMIT+CMD_RECONFIGURE)** |
| latch_in bit | cmd_latch[25] (misread as ctype bit 0) | **cmd_latch[26] (corrected)** |
| invert_out bit | merged into ctype field | **cmd_latch[25] (separate, independent)** |
| GS_LATCH_IN value | 0x02000000 (wrong) | **0x04000000 (corrected)** |
| LOOP_MODE constant | 0 (bug) | **0x80000000 = GS_LOOP_BACK (fixed)** |
| GS_FALL_EDGE | missing | **0x02000400 = GS_EDGE_MODE\|GS_INVERT_OUT_BIT (added)** |
| UART packet size | 8 bytes | **9 bytes (pending uart_bridge.v update; v2.2 shim active)** |

## Files Updated for v2.3 (2026-05-30)

| File | Status |
|------|--------|
| `fpga/verilog/unicell.v` | ✅ Updated — v2.3 cmd_bus, CMD_BOOT_COMMIT, preload_sel, shift_sel |
| `fpga/verilog/unicell_array.v` | ✅ Updated — cmd_bus widened to 32-bit |
| `gate_states.py` | ✅ Updated — bit positions corrected, GS_FALL_EDGE added, LOOP_MODE fixed |
| `unicell.py` | ✅ Updated — latch_in/invert_out read from correct bits |
| `command_interface.py` | ✅ Updated — v2.3 build_cmd_bus, CMD_BOOT_COMMIT, preload_sel |
| `fpga/fpga_bridge.py` | ✅ Updated — v2.3 + v2.2 legacy shim, preload_sel, boot_commit |
| `docs/CELL_INTERNALS.md` | ✅ Rewritten — v2.3 ground truth reference |
| `docs/FPGA_HARDWARE.md` | ✅ Updated — v2.3 protocol, boot sequence, preload_sel |
| `docs/VERILOG_SPEC.md` | ✅ Updated — gate_state parity table corrected |
| `docs/COMPOUND_OPCODES.md` | ✅ Updated — cmd_bus layout, CMD_PRELOAD→preload_sel |
| `docs/ARCHITECTURE.md` | ✅ Updated — preload references |
| `docs/PRELOAD_MODEL.md` | ✅ Updated — preload_sel references |

## Pending (v2.3 bring-up)

| Item | Notes |
|------|-------|
| `fpga/verilog/uart_bridge.v` | Needs v2.3 9-byte packet format (currently v2.2 8-byte) |
| `fpga/verilog/top_icebreaker.v` | May need cmd_bus width update after uart_bridge.v |
| iCEBreaker SYNC_WAIT test | First hardware test with v2.3 Verilog |
| CMD_BOOT_COMMIT silicon test | First boot using new 2-transaction sequence |

---

## Architectural Changes — v1 → v2.2 (historical)

### ✅ CORRECT — No changes needed
| File | Status | Notes |
|------|--------|-------|
| `docs/FPGA_HARDWARE.md` | ✅ Ground truth | Written this session, fully current |
| `docs/INDEX.md` | ✅ Current | FPGA section updated this session |
| `START.md` | ✅ Current | Build commands correct |
| `fpga/verilog/unicell.v` | ✅ Silicon validated | Ground truth Verilog |
| `fpga/verilog/unicell_array.v` | ✅ Current | Updated this session |
| `fpga/verilog/uart_bridge.v` | ✅ Current | Updated this session |
| `fpga/verilog/top_icebreaker.v` | ✅ Current | Updated this session |
| `fpga/verilog/top_kintex7.v` | ✅ Current | Updated this session |
| `fpga/fpga_bridge.py` | ✅ Current | Updated this session |
| `fpga/test_sync_wait.py` | ✅ Current | 16/16 passing |
| `fpga/test_new_opcodes.py` | ✅ Current | 26/29 passing |
| `pcie/axi_unicell_bridge.v` | ✅ Current | Written this session |
| `pcie/top_xdma_unicell.v` | ✅ Current | Updated this session |
| `pcie/unicell_xdma.py` | ✅ Current | Written this session |
| `docs/BRANCH_DECISION_TREE.md` | ✅ Acceptable | sync_wait terminology used as label, semantics correct |
| `docs/VISION.md` | ✅ Stable | Architectural vision, not protocol-specific |
| `docs/ADDER_REFERENCE_MODEL.md` | ✅ Stable | Logic model, not protocol-specific |
| `docs/KS_ADDER_UNICELL.md` | ✅ Stable | Algorithm description, not protocol-specific |
| `docs/RESULTS.md` | ✅ Stable | Historical results, not protocol-specific |
| `docs/LLVM.md` | ✅ Stable | Compiler backend, not affected by protocol |
| `docs/archive/*` | ✅ Archived | Intentionally historical |

---

### ❌ NEEDS UPDATE — Specific issues

#### `docs/CELL_INTERNALS.md`
| Line | Issue | Fix |
|------|-------|-----|
| 56 | `bits 21:11 auth_mask 11-bit` | → `bits 18:11 auth_mask 8-bit` |
| 128 | `Auth token in cmd_bus[14:4]` | → `Auth token in cmd_data[31:24] (8-bit)` |
| 415 | `Opcode 0x01 — DATA WRITE (13 bytes total)` | → `8 bytes total` |
| 417 | `[1:4] cmd_word 32-bit command word` | → `[1] opcode(8-bit), [2:3] addr(16-bit), [4:7] data(32-bit)` |
| 421 | `Opcode 0x02 — STATUS READ (9 bytes total)` | → `7 bytes total` |
| 444 | `cmd_bus Word (bridge → cell array, 32 bits)` | → `8-bit opcode only` |
| 482 | `bits 14:4 auth_token 11-bit` | → `cmd_data[31:24] auth_token 8-bit` |
| 492 | `bits 26:16 cell_id 11-bit` | → `cmd_addr[15:0] cell physical/logical ID 16-bit` |
| 501 | `11 bits plus...` | → update to 8-bit auth, 16-bit addr |
| 539 | `(auth_mask & 0x7FF) << 11` | → `(auth_mask & 0xFF) << 24` in cmd_data |
| Throughout | `input_b_address` references | → remove, two-arrival is default |
| Throughout | `sync_wait` as flag | → note it is default behaviour, no flag needed |

#### `docs/VERILOG_SPEC.md`
| Line | Issue | Fix |
|------|-------|-----|
| 14 | `13-byte packets` | → `8-byte TX, 7-byte RX` |
| 133 | `LOAD_PATTERN` | → remove, replaced by CMD_RECONFIGURE |
| 146 | `LOAD_PATTERN` in code example | → remove |
| 233 | `input_b_address` | → remove from register list |
| 247 | `input_b_address` in bus logic | → remove |
| 258 | `5. input_b_address` in config sequence | → remove |
| 262 | Old config sequence | → update to 4-packet boot sequence |
| Throughout | Old cmd_bus 32-bit format | → update to 8-bit opcode |

#### `docs/ARCHITECTURE.md`
| Line | Issue | Fix |
|------|-------|-----|
| 82 | `negedge: B arrives at input_b_address` | → remove, use two-arrival model description |
| 666 | `13-byte packets` | → `8-byte TX, 7-byte RX` |
| Throughout | Old auth/cmd_bus references | → update to v2.1 protocol |

#### `docs/RUNNING.md`
| Line | Issue | Fix |
|------|-------|-----|
| 90 | `Two-input cells add "inB"` | → remove inB, explain two-arrival model |
| 141 | `input_b_address=r.get("inB")` | → remove |
| 420 | `inB` in config description | → remove |
| 470 | `13-byte packets` | → `8-byte TX, 7-byte RX` |

#### `docs/ICM_FORMAT.md`
| Line | Issue | Fix |
|------|-------|-----|
| 35 | `"inB": null` in example | → remove inB field |
| 140 | `inB` field description | → remove or mark deprecated |
| 199 | `"inB": null` in example | → remove |
| 213 | `"inB": 4097` in example | → remove |
| 346 | `inB and init not yet implemented` | → update status |
| Throughout | `gs` field bit layout | → update to new cmd_latch layout |

#### `docs/NEURAL_POND_TUTORIAL.md`
| Line | Issue | Fix |
|------|-------|-----|
| 117, 122, 202 | `input_b_address=` | → remove, explain two-arrival model |

#### `docs/neural_pond_design.md`
| Line | Issue | Fix |
|------|-------|-----|
| 327, 332 | `input_b_address=` | → remove |

#### `docs/diagrams/diagram_cell_internal.md`
| Issue | Fix |
|-------|-----|
| `FUNCTION_LOAD_PATTERN` | → update to CMD_RECONFIGURE flow |

#### `docs/diagrams/diagram_boot_sequence.md`
| Issue | Fix |
|-------|-----|
| Likely shows old boot sequence | → update to 4-packet sequence |

---

## Priority Order for Updates

**Priority 1 — Most likely to confuse a developer:**
1. `CELL_INTERNALS.md` — core reference, heavily stale
2. `VERILOG_SPEC.md` — protocol spec, wrong frame sizes and LOAD_PATTERN
3. `RUNNING.md` — user guide, wrong packet sizes and inB references

**Priority 2 — Architecture docs:**
4. `ARCHITECTURE.md` — input_b and packet size references
5. `ICM_FORMAT.md` — inB field needs removing/deprecating

**Priority 3 — Tutorials (lower urgency, input_b only):**
6. `NEURAL_POND_TUTORIAL.md`
7. `neural_pond_design.md`
8. `diagrams/diagram_cell_internal.md`
9. `diagrams/diagram_boot_sequence.md`

---

## Key Facts for All Updates (from unicell.v ground truth)

### cmd_latch[31:0] current layout
```
[9:0]   topology    (NOR gate selection, one-hot)
[10]    edge_mode   (0=standard, 1=edge)
[18:11] auth_mask   (8-bit, zeroed before ICM serialisation)
[19]    output_set  (1=output address configured)
[22]    start_flag  (1=armed)
[24:23] dtype       (00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME)
[25]    invert_out
[26]    latch_in    (hold a_arrived after firing)
[27]    priority
[28]    trace
[29]    breakpoint
[30]    one_shot    (fire once then disarm)
[31]    loop_back   (output feeds back as next a_data)
```

### UART frame format (current)
```
TX (host→FPGA): 8 bytes
  [0]   0x01 (UART_INJECT)
  [1]   opcode (8-bit)
  [2:3] addr (16-bit big-endian)
  [4:7] data (32-bit big-endian, auth[31:24]+payload[23:0])

RX fired (FPGA→host): 7 bytes
  [0]   0x10
  [1:2] out_addr (16-bit)
  [3:6] out_data (32-bit)

RX status (FPGA→host): 7 bytes
  [0]   0x11
  [1:2] armed_count (16-bit)
  [3:6] cycle_count (32-bit)
```

### Removed features
- `input_b_address` — removed from unicell.v, two-arrival is default
- `LOAD_PATTERN` — removed, replaced by CMD_RECONFIGURE
- `sync_wait` flag — removed from cmd_latch, two-arrival is default behaviour

### New features (not in any old docs)
- `physical_mode` register — boot=1, cleared by CMD_SET_LOGICAL
- `output_set` register — 0 until CMD_SET_OUTPUT_ADDR or RECONFIGURE
- CMD_SET_LOGICAL (0x0E) — switches physical→logical addressing
- CMD_LATCH_IN_ON/OFF (0x0A/0x0B)
- CMD_MEM_CALL (0x0C)
- CMD_REARM (0x0D)
- 4-packet boot sequence
