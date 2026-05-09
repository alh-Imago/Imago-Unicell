# Imago UniCell

A compute architecture built from a single, universal cell. Every logic function —
AND, OR, XOR, NOR, NAND, XNOR, MUX, SELECT, and more — is implemented by one cell
in one clock cycle. No multi-cell chains. No ripple. Programs written once run on any
target in the family: Python VM, iCEBreaker FPGA, larger FPGA, future ASIC.

---

## The Founding Idea

A NOR gate is universal: any digital function can be built from NOR gates alone. The
UniCell takes this further — instead of wiring many NOR gates together, a single cell
contains the full 9-input NOR gate tree and selects which function to perform via a
32-bit gate_state configuration word. One cell, one cycle, 12 possible logic outputs.

Cells share a **wired-OR bus**: two cells writing the same address produce OR of their
outputs — naturally, in hardware, with no arbitration. This is the bus equivalent of
NOR universality. It makes fan-in free.

Everything in the system — programs, OS services, filesystem entries, even neural ponds
— is built from this one cell type.

---

## Current Status

| Milestone | Status |
|-----------|--------|
| v2 two-input cell (A↑ B↓ gate tree) | ✅ Complete |
| All 12 gate functions verified by truth table | ✅ Complete |
| Kogge-Stone 32-bit adder (482 cells, depth 2) | ✅ Complete |
| FP32 ADD / MUL tiles | ✅ Complete (1,253 / 3,066 cells) |
| Pond OS layer (Ward, Shore, ShoreKeeper, Bridge) | ✅ Complete |
| Compiler (single-bit and INT32 paths) | ✅ Complete |
| LLVM IR mapper (C/C++/Rust → cells) | ✅ Complete |
| iCEBreaker silicon validation | ✅ **Passed May 2026** |
| All three variants validated on iCEBreaker | ✅ Complete |
| Test suite | ✅ 7,190 tests across all variants |
| Tier 1 v1 compatibility retirement | ✅ Complete |
| Tier 2 OS layer v2 migration | ✅ Complete |
| GS_OUT_POSEDGE on all compiler-emitted cells | ✅ Complete |
| Compiler constant auto-injection | ✅ Complete |
| Kintex-7 XC7K480T board | 🚚 In transit (ETA Jul 2026) |
| Standalone VM package | 🔜 Next |

**Main repo (standard variant): 2,329 tests passing.**

---

## Silicon Validation — May 2026

All three variants validated on a physical **iCEBreaker v1.0e** (iCE40UP5K sg48):

| Variant | NOT gate | NAND | Bridge pair | 8-cell scale |
|---------|----------|------|-------------|-------------|
| Standard | ✓ | ✓ | ✓ | ✓ |
| Latch | ✓ | ✓ | ✓ | ✓ |
| Edge | ✓ | ✓ | ✓ | ✓ |

All variants: 3,780 ICESTORM_LC (71%), 25–26 MHz at 24 MHz target. Wired-OR bus
correct in silicon, two-input NAND via shared output address confirmed, UART bridge
bidirectional. Architecture validated.

---

## Three Variants

This repository contains three independent implementations of the UniCell
architecture. Each is a complete, self-contained codebase: VM, compiler, OS layer,
tests, and FPGA Verilog. They share no code — a change to one variant stays in that
variant.

### Root `/` — Standard Model

The reference implementation. Cells fire immediately on data arrival and drive the
bus in the same tick. No latency registers. The development and simulation target:
fast, transparent, easiest to reason about.

**Use for:** algorithm development, compiler work, unit testing, the workbench VM.
**Tests:** 2,329 passing.

---

### `unicell-latch/` — Latch Model

Each cell has an **input latch** and an **output latch**. The clock controls flow only;
the gate tree runs combinatorially. Fixed 2-tick latency per cell, always. Timing skew
in large arrays is absorbed by the latches — no edge-sensitivity required.

```
Tick N:    Data arrives → stored in INPUT LATCH
Tick N+1:  Input latch → gate tree → result → OUTPUT LATCH
Tick N+2:  Output latch → bus
```

Path balancing is done topologically: insert a PASS cell anywhere to add exactly
2 ticks of delay. No timing constraints files needed.

**Use for:** large FPGA arrays, designs where timing closure is hard, long-term stable
target. **Tests:** 2,535 passing. iCEBreaker validated May 2026.

---

### `unicell-edge/` — Edge Model

The primary FPGA target. Cells are edge-triggered: **A input on rising edge, B input
on falling edge**, output buffer released on the next configurable edge
(`GS_OUT_POSEDGE`, bit 26). One cell handles true two-input logic — AND, OR, XOR —
natively, with A and B arriving in the same cycle at different edges.

```
posedge:   A arrives → stored in input register
negedge:   B arrives → gate tree fires → result → output buffer
posedge+1: output buffer → bus  (GS_OUT_POSEDGE=1, default)
```

**Use for:** iCEBreaker bring-up and validation, tight-timing FPGA designs.
**Tests:** 2,326 passing. iCEBreaker validated May 2026.

---

## Architecture

```
  Source (Python subset, LLVM IR, or visual Composer)
        │
        ▼
  ImagoCompiler / Int32Compiler / LLVM IR mapper
        │  produces CellMapRecord list
        ▼
  ImagoController  ←→  UniCellArray  ←→  physical bus (wired-OR)
        │
        ▼
  Pond OS layer
    ├── Pond         — isolated compute environment
    ├── Bridge       — INBOUND / OUTBOUND / MONITOR / LOG
    ├── Ward         — health monitor (stall, spike, anomaly)
    ├── Shore        — name → address registry
    ├── ShoreKeeper  — Shore query engine, PTT scheduling
    └── COMPANION    — permanent OS anchor (HIDDEN, single instance)
```

### Cell Gate Functions (v2)

Every function below costs exactly 1 cell (except MUX2):

| Function | gate_state | Notes |
|----------|------------|-------|
| NOT | GS_NOT | single-input |
| PASS | GS_PASS | wire / delay |
| AND | GS_AND_V2 \| GS_SYNC_WAIT | A↑ B↓ |
| OR | GS_OR_V2 \| GS_SYNC_WAIT | A↑ B↓ |
| XOR | GS_XOR_V2 \| GS_SYNC_WAIT | A↑ B↓ |
| NAND | GS_NAND_V2 \| GS_SYNC_WAIT | A↑ B↓ |
| XNOR | GS_XNOR_V2 \| GS_SYNC_WAIT | A↑ B↓ |
| NOR | GS_NOR_V2 | via wired-OR bus |
| SELECT | GS_SELECT | conditional routing |
| LATCH | GS_LATCH | state hold |
| LOOP | GS_LOOP_BACK | feedback path |
| MUX2 | NOT+AND+AND+OR | 4 cells |

### Tile Library

| Tile | Cells | Depth | Notes |
|------|-------|-------|-------|
| INT32_ADD | 482 | 2 | Kogge-Stone parallel prefix |
| INT32_SUB | 517 | 12 | Kogge-Stone + NOT(b) |
| INT32_EQ | 95 | 7 | XNOR + AND tree |
| INT32_MUX | 128 | 3 | 32-bit 2:1 multiplexer |
| INT32_NOT/AND/OR/XOR | 32 | 1 | Bitwise, one cell per bit |
| FP32_ADD | 1,253 | 85 | Simplified (no denormals) |
| FP32_MUL | 3,066 | 89 | Simplified (no denormals) |
| FP32_CMP_EQ | 95 | 7 | Bit-exact equality |

---

## Portability

The same `.icm` file runs on every target without modification:

| Target | Cells | Clock | Status |
|--------|-------|-------|--------|
| Python VM | Unlimited | Software | Available now |
| iCEBreaker (iCE40UP5K) | 32–64 | 24 MHz | Validated May 2026 |
| iCEstick (iCE40HX1K) | 8–16 | ~20 MHz | Supported |
| Basys 3 / Arty A7-35T | 256 | ~100 MHz | Supported |
| OrangeCrab (ECP5 25F) | 256 | ~80 MHz | Supported |
| Kintex-7 XC7K480T | 600–1,500 | 200+ MHz | In transit |
| Future ASIC | Millions | GHz | Same .icm files |

Programs written today run on silicon that does not exist yet.

---

## The LLVM Path

Any language with an LLVM frontend — C, C++, Rust, Swift, Zig — compiles to `.icm`
without a new backend:

```
C / C++ / Rust  →  LLVM IR  →  llvm_ir_mapper.py  →  .icm
```

Requires `pip install llvmlite`. If not installed, the LLVM frontend gracefully
disables itself with a clear error message.

---

## Repository Structure

```
README.md               — this file
MIGRATION_TODO.md       — open work and architecture decisions
SESSION_START.md        — quick-start prompt for new sessions
sessions/               — dated session logs

# Standard variant (root)
unicell.py              — UniCell v2 model
unicell_array.py        — array tick loop
gate_states.py          — gate_state bit definitions
ir.py                   — IR graph → CellMapRecord (v2 lowering)
compiler.py             — single-bit function compiler
compiler_int32.py       — 32-bit integer compiler
llvm_frontend.py        — LLVM bitcode → compiler IR
llvm_ir_mapper.py       — LLVM IR → tile placements
fp_tiles.py             — tile library (INT32, FP32, counters, SR latch)
controller.py           — region lifecycle, run/halt/freeze/thaw
pond.py                 — Pond, Bridge, Ward
shore.py / shore_v2.py  — Shore registry and lean index
shorekeeper.py          — ShoreKeeper query engine
workbench.py            — browser development UI (http://localhost:7420)
run_companion.py        — launch COMPANION OS session

# FPGA
fpga/
  fpga_bridge.py        — UART host bridge to physical array
  icm_loader.py         — load .icm file onto FPGA via UART
  verilog/              — Verilog-2001, synthesises on all families

# Composer
composer/
  unicell_composer.html — open in browser, no install needed
  examples/             — example .icm programs

# Variant directories
unicell-latch/          — Latch model (self-contained)
unicell-edge/           — Edge model (self-contained, primary FPGA target)

docs/
  RUNNING.md            — workflow guide: Composer → VM → FPGA
  00_PRIMER.md          — architecture primer
  01_Architecture_Overview.md
  02_Core_Architecture.md
  04_OS_and_Runtime.md
  COMMAND_REFERENCE.md
```

---

## Key Concepts

**Wired-OR bus.** Two cells writing the same output address produce OR of their values.
No arbitration. No collision. This matches the silicon bus exactly — the Python VM and
the FPGA produce identical results.

**Ponds.** Every program runs inside a Pond: an isolated address space with security
level (OPEN / PRIVATE / HIDDEN), inbound/outbound bridge lanes, Ward health monitoring,
and live migration support (FREEZE → move → THAW without stopping computation).

**Shore.** The lean registry. Maps Pond names to addresses via a view_mask access
control layer. Query by PTT cell word. No directory tree — search is an index query.

**Ward.** Per-Pond health monitor. Detects stall (consecutive zero-emission cycles),
spike (burst beyond declared bandwidth), and routing anomaly (high rejection rate).
Thresholds are tuned per pond type: a DEVICE Pond flags silence in 15 cycles; a FILE
Pond tolerates 200.

**GS_OUT_POSEDGE (bit 26).** When set, a cell's output buffer releases on the next
rising edge, giving the downstream cell a full half-cycle of settling time before its
B input arrives. Set on all compiler-emitted cells by default.

---

## Quick Start

```bash
git clone https://github.com/alh-Imago/Imago-Unicell.git
cd Imago-Unicell
pip install -r requirements.txt

# Launch the workbench VM (browser UI)
python3 workbench.py
# Open http://localhost:7420

# Run the OS session
python3 run_companion.py
```

See `docs/RUNNING.md` for the full workflow — Composer → VM → FPGA, including
Python commands to load `.icm` files into either target.
