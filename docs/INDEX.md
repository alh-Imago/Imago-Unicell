# Imago UniCell — Documentation Index

Complete searchable reference. Use Ctrl+F to find any topic.

---

## Getting Started

→ **[docs/EXAMPLES.md](EXAMPLES.md)** — all runnable examples with copy-paste commands

→ **[docs/LIBRARY.md](LIBRARY.md)** — user library: keeping and sharing `.icm` programs


| Topic | Where |
|-------|-------|
| Install the VM (`pip install imago-vm`) | [RUNNING.md § Setup](RUNNING.md) |
| Run a bundled example | [RUNNING.md § Python VM](RUNNING.md) |
| Launch the workbench UI | [RUNNING.md § Workbench](RUNNING.md) |
| Compile your first function | [RUNNING.md § Compile from source](RUNNING.md) |
| Load a `.icm` file | [RUNNING.md § Loading an ICM](RUNNING.md) |
| Full workflow: Composer → VM → FPGA | [RUNNING.md](RUNNING.md) |

---

## Architecture

| Topic | Where |
|-------|-------|
| The founding idea (NOR universality, wired-OR bus) | [ARCHITECTURE.md § Foundations](ARCHITECTURE.md) |
| Cell model — gate_state, 12 functions, one cycle | [ARCHITECTURE.md § The Cell](ARCHITECTURE.md) |
| Wired-OR bus — no arbitration, NOR for free | [ARCHITECTURE.md § The Bus](ARCHITECTURE.md) |
| Two-input cell (A↑ posedge, B↓ negedge) | [ARCHITECTURE.md § Edge model](ARCHITECTURE.md) |
| Type system — bits 27-28, complement cells | [ARCHITECTURE.md § Type system](ARCHITECTURE.md) |
| Typed computing substrate (vs CPU/FPGA) | [ARCHITECTURE.md § Significance](ARCHITECTURE.md) |
| Compile pipeline (source → IR → cells) | [ARCHITECTURE.md § Compiler](ARCHITECTURE.md) |
| Portability — same `.icm` on VM, FPGA, ASIC | [ARCHITECTURE.md § Portability](ARCHITECTURE.md) |
| Three variants (standard, latch, edge) | [ARCHITECTURE.md § Variants](ARCHITECTURE.md) |
| Design principle: the constraint is the point | [ARCHITECTURE.md § Principle](ARCHITECTURE.md) |

---

## OS Layer

| Topic | Where |
|-------|-------|
| Pond — isolated compute environment | [ARCHITECTURE.md § Pond](ARCHITECTURE.md) |
| Bridge — INBOUND / OUTBOUND / MONITOR / LOG | [ARCHITECTURE.md § Bridge](ARCHITECTURE.md) |
| Ward — health monitor, stall/spike/anomaly | [ARCHITECTURE.md § Ward](ARCHITECTURE.md) |
| Shore — name → address registry | [ARCHITECTURE.md § Shore](ARCHITECTURE.md) |
| ShoreKeeper — query engine, PTT scheduling | [ARCHITECTURE.md § Shore](ARCHITECTURE.md) |
| COMPANION — permanent OS anchor | [ARCHITECTURE.md § COMPANION](ARCHITECTURE.md) |
| PTT — Pond Translation Table | [ARCHITECTURE.md § PTT](ARCHITECTURE.md) |
| WORKSPACE pond — user's desk | [ARCHITECTURE.md § WORKSPACE](ARCHITECTURE.md) |
| Pond types (PROCESS, WORKSPACE, LIBRARY…) | [ARCHITECTURE.md § Pond](ARCHITECTURE.md) |
| Ward health states and thresholds | [ARCHITECTURE.md § Ward](ARCHITECTURE.md) |
| Live migration (FREEZE → THAW) | [ARCHITECTURE.md § Pond](ARCHITECTURE.md) |
| Security levels (OPEN / PRIVATE / HIDDEN) | [ARCHITECTURE.md § Pond](ARCHITECTURE.md) |

---

## Programs and the `.icm` Format

| Topic | Where |
|-------|-------|
| `.icm` file structure | [ICM_FORMAT.md](ICM_FORMAT.md) |
| `inputs` / `outputs` — named port declarations | [ICM_FORMAT.md § Ports](ICM_FORMAT.md) |
| `input_types` / `output_types` — type declarations | [ICM_FORMAT.md § Types](ICM_FORMAT.md) |
| `input_shapes` — array/matrix ports (reserved) | [ICM_FORMAT.md § Shapes](ICM_FORMAT.md) |
| `records` — cell configurations | [ICM_FORMAT.md § Records](ICM_FORMAT.md) |
| `models` — tile library references | [ICM_FORMAT.md § Models](ICM_FORMAT.md) |
| `record_hash` — integrity verification | [ICM_FORMAT.md § Hash](ICM_FORMAT.md) |
| `vm_only` — FPGA budget flag | [ICM_FORMAT.md § Target](ICM_FORMAT.md) |
| Port name prompt (CLI confirm/rename) | [RUNNING.md § Port names](RUNNING.md) |

---

## Tile Library

| Tile | Cells | Depth | Notes |
|------|-------|-------|-------|
| INT32_ADD | 482 | 2 | Kogge-Stone parallel prefix |
| INT32_SUB | 517 | 12 | KS + NOT(b) + carry-in=1 |
| INT32_LT_U | 518 | 14 | Unsigned a<b — NOT(carry_out of SUB) |
| INT32_LT_S | 523 | 16 | Signed a<b — sign XOR + unsigned_lt |
| INT32_MIN | 317 | 66 | Unsigned min(a,b) — LT_U + MUX |
| INT32_MAX | 317 | 66 | Unsigned max(a,b) — LT_U + MUX |
| INT32_CAS | 711 | 17 | Compare-and-swap (min,max) — sort primitive |
| INT32_EQ | 95 | 7 | XNOR + AND tree |
| INT32_MUX | 128 | 3 | 32-bit 2:1 mux |
| INT32_NOT/AND/OR/XOR | 32 | 1 | Bitwise, one cell per bit |
| FP32_ADD | 1,253 | 85 | Simplified (no denormals) |
| FP32_MUL | 3,066 | 89 | Simplified (no denormals) |
| FP32_CMP_EQ | 95 | 7 | Bit-exact equality |
| COUNTER_DECREMENT_N | ~√N·2 | ~√N | N-bit decrement + zero detect |
| SR_LATCH | 6 | 2 | Cross-coupled NOR |

Full tile reference: [fp_tiles.py](../fp_tiles.py)

---

## Data Types

| Topic | Where |
|-------|-------|
| Type bits 27-28 in gate_state | [ARCHITECTURE.md § Type system](ARCHITECTURE.md) |
| GS_TYPE_NUMERIC (00) | [gate_states.py](../gate_states.py) |
| GS_TYPE_SIGNED (01) — complement cell pair | [gate_states.py](../gate_states.py) |
| GS_TYPE_ALPHA (10) — character bytes | [gate_states.py](../gate_states.py) |
| GS_TYPE_DATETIME (11) — Unix timestamp | [gate_states.py](../gate_states.py) |
| Complement cell model (64-bit word) | [ARCHITECTURE.md § Types](ARCHITECTURE.md) |
| Type annotations in source (`a: signed`) | [RUNNING.md § Types](RUNNING.md) |
| Future: INT64, FP64, signed comparator | [MIGRATION_TODO.md](../MIGRATION_TODO.md) |
| Future: array/matrix inputs (`input_shapes`) | [ICM_FORMAT.md § Shapes](ICM_FORMAT.md) |

---

## Compiler

| Topic | Where |
|-------|-------|
| Single-bit compiler (`compiler.py`) | [ARCHITECTURE.md § Compiler](ARCHITECTURE.md) |
| INT32 compiler (`compiler_int32.py`) | [RUNNING.md § INT32](RUNNING.md) |
| LLVM IR mapper (C/C++/Rust → cells) | [ARCHITECTURE.md § LLVM](ARCHITECTURE.md) |
| `scan_function()` — pre-compile port scan | [RUNNING.md § Port names](RUNNING.md) |
| `port_names=` — rename ports before `.icm` | [RUNNING.md § Port names](RUNNING.md) |
| `compile_function()` API | [RUNNING.md § Python API](RUNNING.md) |
| Known values / constant auto-injection | [ARCHITECTURE.md § Compiler](ARCHITECTURE.md) |
| MUX: `if cond: return a / return b` | compiler.py |
| MUX: `a if cond else b` (IfExp) | compiler.py |
| GS_OUT_POSEDGE on all emitted cells | [gate_states.py](../gate_states.py) |

---

## WORKSPACE Pond

| Topic | Where |
|-------|-------|
| What the WORKSPACE pond is | [ARCHITECTURE.md § WORKSPACE](ARCHITECTURE.md) |
| Shell commands (`ws load`, `ws set`, `ws run`…) | [RUNNING.md § Shell](RUNNING.md) |
| Named input/output values | [RUNNING.md § WORKSPACE](RUNNING.md) |
| Programming space (multi-file editor) | [RUNNING.md § Programming space](RUNNING.md) |
| Session file system | [RUNNING.md § File system](RUNNING.md) |
| Search across workspace | [RUNNING.md § Search](RUNNING.md) |

---

## Composer (Visual Design Tool)

| Topic | Where |
|-------|-------|
| Open Composer (no install) | [RUNNING.md § Composer](RUNNING.md) |
| Place cells and wire them | [RUNNING.md § Composer](RUNNING.md) |
| Drop model macros from library | [RUNNING.md § Composer](RUNNING.md) |
| Ports tab — declare named inputs/outputs | [RUNNING.md § Composer ports](RUNNING.md) |
| Port type selector (numeric/signed/alpha/datetime) | composer/unicell_composer.html |
| FPGA target selector and cell budget | [RUNNING.md § Composer](RUNNING.md) |
| vmOnly warning — model too large for FPGA | [RUNNING.md § Composer](RUNNING.md) |
| Export `.icm` | [RUNNING.md § Composer](RUNNING.md) |

---

## FPGA and Hardware

| Topic | Where |
|-------|-------|
| Supported boards | [RUNNING.md § FPGA](RUNNING.md) |
| Build and flash (iCEBreaker) | [RUNNING.md § FPGA](RUNNING.md) |
| Load `.icm` onto FPGA (`icm_loader.py`) | [RUNNING.md § ICM loader](RUNNING.md) |
| FPGA bridge protocol (UART, 13-byte packets) | [RUNNING.md § Protocol](RUNNING.md) |
| Python FPGA bridge API | [RUNNING.md § Python FPGA API](RUNNING.md) |
| Bring-up sequence (6 stages) | [RUNNING.md § Bring-up](RUNNING.md) |
| Variant selection for FPGA | [RUNNING.md § Variants](RUNNING.md) |
| FPGA workbench (PTT-only mode, Jul 2026) | [MIGRATION_TODO.md](../MIGRATION_TODO.md) |
| Verilog files | fpga/verilog/ |

---

## Neural Ponds

| Topic | Where |
|-------|-------|
| 5-cell LIF neuron (latch model) | [neural_pond_design.md](neural_pond_design.md) |
| 10-cell Izhikevich neuron | [neural_pond_design.md](neural_pond_design.md) |
| Scale: iCEBreaker 12 LIF / Kintex-7 300 | [neural_pond_design.md](neural_pond_design.md) |
| UniCell vs neuromorphic chips | [neural_pond_design.md](neural_pond_design.md) |
| Why the latch model suits neural ponds | [neural_pond_design.md](neural_pond_design.md) |
| Loading a LIF pond in Python | [neural_pond_design.md](neural_pond_design.md) |
| Step-by-step LIF tutorial + `lif_neuron.icm` | [NEURAL_POND_TUTORIAL.md](NEURAL_POND_TUTORIAL.md) |

---

## Three Variants

| Variant | Location | Use |
|---------|----------|-----|
| Standard | `/` (root) | Development, simulation, VM |
| Latch | `unicell-latch/` | Large FPGA, timing closure |
| Edge | `unicell-edge/` | iCEBreaker, tight timing |

All variants share `.icm` format. No shared code — each is self-contained.

---

## Repository Map

```
README.md               — short overview + quick start
MIGRATION_TODO.md       — open work and architecture decisions
SESSION_START.md        — session assistant briefing
sessions/               — dated session logs

# Core VM (standard variant)
unicell.py              — UniCell v2 model
unicell_array.py        — array tick loop, wired-OR bus
gate_states.py          — all gate_state bit definitions (authoritative)
ir.py                   — IR graph → CellMapRecord lowering
compiler.py             — single-bit function compiler
compiler_int32.py       — 32-bit integer compiler
fp_tiles.py             — tile library (INT32, FP32, counters, SR latch)
controller.py           — region lifecycle, load/run/halt/freeze
imago_log.py            — centralised logging (set_level, set_handler)
workspace.py            — WORKSPACE pond (named values, fs, prog space)
pond.py                 — Pond, Bridge, Ward
shore_v2.py             — Shore registry
shorekeeper.py          — ShoreKeeper query engine
workbench.py            — browser workbench UI (http://localhost:7420)
run_companion.py        — launch full OS session

# Package
imago/
  __init__.py           — public API (VM, run_icm, compile_function)
  cli.py                — CLI entry points (imago, imago-workbench)
  examples/             — bundled .icm programs
pyproject.toml          — pip install imago-vm

# FPGA
fpga/
  fpga_bridge.py        — UART host bridge
  icm_loader.py         — load .icm onto FPGA
  verilog/              — Verilog-2001 (all families)

# Composer
composer/
  unicell_composer.html — open in browser, no install

# Variants
unicell-latch/          — Latch model (self-contained)
unicell-edge/           — Edge model (self-contained)

# Docs
docs/
  INDEX.md              — this file
  EXAMPLES.md           — all runnable examples with commands
  LIBRARY.md            — user library (sharing and reusing programs)
  ARCHITECTURE.md       — full architecture document
  ICM_FORMAT.md         — .icm format specification
  RUNNING.md            — workflow guide
  VERILOG_SPEC.md       — silicon bring-up, timing issues, parity table
  NEURAL_POND_TUTORIAL.md — step-by-step tutorial + lif_neuron.icm
  neural_pond_design.md — LIF + Izhikevich neuron design
  LLVM.md               — LLVM / open-source language portability
  VISION.md             — what this is trying to become
  addressing_note.md    — 32-bit address space, future 64-bit path
  archive/              — v1.1 historical docs (superseded)
    README.md           — what each archived file is replaced by
    00_PRIMER.md … 10_*.md — 14 v1.1 files, retained for reference
  diagrams/             — Mermaid architecture diagrams (7 files)
unicell-latch/docs/timing.md — latch model timing and path balancing
```

---

## Silicon Validation (May 2026)

All three variants validated on iCEBreaker v1.0e (iCE40UP5K sg48):

| Test | Standard | Latch | Edge |
|------|----------|-------|------|
| NOT gate | ✓ | ✓ | ✓ |
| Two-input NAND | ✓ | ✓ | ✓ |
| Bridge pair | ✓ | ✓ | ✓ |
| 8-cell scale | ✓ | ✓ | ✓ |

3,780 ICESTORM_LC (71%), 24 MHz. Wired-OR bus correct in silicon.

---

## Glossary

| Term | Meaning |
|------|---------|
| Cell | The universal compute unit. One gate_state word, one input address, one output address. One cycle to evaluate. |
| gate_state | 32-bit configuration word. Bits 0-8: NOR topology. Bits 11-26: mode flags. Bits 27-28: type. Bits 29-31: debug. |
| Wired-OR bus | Shared address space. Two cells writing the same address → OR of values. No arbitration. |
| Pond | Isolated compute environment with address space, bridges, Ward health monitor. |
| Bridge | Cell cluster connecting Ponds. INBOUND / OUTBOUND / MONITOR / LOG. |
| Ward | Per-Pond health monitor. Detects stall, spike, anomaly, silence. |
| Shore | Name → address registry. Lean index, view_mask access control. |
| COMPANION | Permanent OS anchor. HIDDEN, single instance, cannot be destroyed. |
| PTT | Pond Translation Table. Named ports with bus addresses and type bits. |
| WORKSPACE | User's session Pond. Holds named values, session fs, programming space. |
| `.icm` | Portable program file. JSON. Runs on VM, FPGA, ASIC unchanged. |
| Tile | Pre-built verified cell network (INT32_ADD, FP32_MUL, etc.). |
| Complement cell | The cell at primary_addr+1. Together form a 64-bit typed word. |
| Depth | Pipeline depth: exact number of ticks from input to output. Structural, not statistical. |
| GS_TYPE_SIGNED | Bits 27-28 = 01. Cell produces signed two's complement value (primary + complement). |
| GS_TYPE_DATETIME | Bits 27-28 = 11. Cell produces Unix timestamp (primary = seconds, complement = subsecond). |
