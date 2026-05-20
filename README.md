# Imago UniCell

A compute architecture built from one cell type. Every logic function — AND, OR,
XOR, NOR, NAND, NOT, MUX, SELECT — is one cell, one cycle. Programs are portable
`.icm` files that run identically on a Python VM, an iCEBreaker FPGA, a Kintex-7,
or a future ASIC without modification.

---

## The Constraint That Shapes Everything

NOR is universal — any Boolean function can be expressed in NOR alone. The UniCell
takes that further: a single cell contains a 9-input NOR gate tree and selects
which function to perform via a 32-bit `gate_state` configuration word. One cell,
one cycle, 12 possible logic functions.

Cells share a **wired-OR bus**. Two cells writing the same address produce OR of
their outputs — naturally, in hardware, with no arbitration. This is the bus
equivalent of NOR universality.

Everything — programs, OS services, neural clusters, filesystem entries — is built
from this one cell type. The constraint is the point.

---

## Current State

| | |
|---|---|
| Silicon validated | iCEBreaker (iCE40UP5K) — 15/15 gate ops confirmed May 2026 |
| Tests passing | 19/19 core · 56/56 branch · 81/82 INT32 |
| Package | `pip install imago-vm` |
| Hardware in hand | Kintex-7 XC7K480T ×2 — bring-up pending (riser cable) |

**Confirmed:** two-arrival model validated on silicon · preloaded-A pattern
confirmed · XNOR comparator · sequence lock proven · INT32 arithmetic complete

---

## Silicon Results

iCEBreaker validated May 2026. See [`docs/RESULTS.md`](docs/RESULTS.md) for
the full record. Kintex-7 (dual XC7K480T) in hand — bring-up pending PCIe
riser cable.

---

## Quick Start

```bash
pip install imago-vm

# Run a bundled example
imago run not_gate a=1
imago run adder_int32 a=5 b=3

# Compile your own function
imago compile myfile.py my_function --save my_function.icm

# Launch the workbench (browser UI)
imago-workbench
# → http://localhost:7420
```

```python
import imago
imago.set_verbose(False)

# Load and run
vm = imago.VM()
vm.load_example("adder_int32")
print(vm.run(a=100, b=200))   # {"result": 300}

# Compile from source
vm2 = imago.compile_function(
    "def add(a: signed, b: signed) -> signed:\n    return a and b",
    "add"
)
print(vm2.run(a=1, b=1))
```

---

## The Type System

Every cell carries a 2-bit type declaration in its `gate_state` word:

| Bits 27-28 | Type | Notes |
|------------|------|-------|
| `00` | NUMERIC | unsigned integer, default |
| `01` | SIGNED | two's complement, primary + complement cell pair |
| `10` | ALPHA | 8-bit character / string byte |
| `11` | DATETIME | Unix timestamp, primary + complement cell pair |

Type annotations in source flow all the way through: compiler → cell configuration
→ PTT entries → `.icm` header → WORKSPACE → Ward health monitoring. The cell knows
what it holds. The system knows what it's moving.

This is not a convention. It is in the silicon.

---

## Tile Library

Pre-built verified cell networks. Each tile is a drop-in building block:

| Tile | Cells | Notes |
|------|-------|-------|
| `INT32_ADD` | 482 | Kogge-Stone 32-bit adder, depth 2 |
| `INT32_SUB` | 517 | 32-bit subtractor, depth 12 |
| `INT32_LT_U` | 518 | Unsigned `a < b` — one NOT on the carry-out |
| `INT32_LT_S` | 523 | Signed `a < b` — handles all sign combinations |
| `INT32_MIN` | 317 | Unsigned `min(a,b)` |
| `INT32_MAX` | 317 | Unsigned `max(a,b)` |
| `INT32_CAS` | 711 | Compare-and-swap `(min,max)` — sort network primitive |
| `INT32_EQ` | 95 | 32-bit equality, depth 7 |
| `INT32_MUX` | 128 | 32-bit 2:1 multiplexer |
| `FP32_ADD` | 1,253 | 32-bit float add |
| `FP32_MUL` | 3,066 | 32-bit float multiply |

Full reference: [fp_tiles.py](fp_tiles.py) · [docs/INDEX.md § Tile Library](docs/INDEX.md)

---

## Full Documentation

→ **[docs/INDEX.md](docs/INDEX.md)** — complete searchable index

Key documents:

| | |
|---|---|
| [docs/VM_GETTING_STARTED.md](docs/VM_GETTING_STARTED.md) | New user guide — install to first run (< 5 min) |
| [docs/EXAMPLES.md](docs/EXAMPLES.md) | All runnable examples with commands |
| [docs/LIBRARY.md](docs/LIBRARY.md) | User library — keeping and sharing `.icm` programs |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | The full architecture — cell model, bus, OS, type system, portability |
| [docs/RUNNING.md](docs/RUNNING.md) | Workflow: Composer → VM → FPGA |
| [docs/ICM_FORMAT.md](docs/ICM_FORMAT.md) | `.icm` file format specification |
| [docs/neural_pond_design.md](docs/neural_pond_design.md) | LIF and Izhikevich neurons in UniCell |
| [MIGRATION_TODO.md](MIGRATION_TODO.md) | Open work and architecture decisions |
| [fpga/README_FPGA.md](fpga/README_FPGA.md) | FPGA bring-up guide |
