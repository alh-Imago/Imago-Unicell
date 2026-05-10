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
| Silicon validated | iCEBreaker (iCE40UP5K), all three variants, May 2026 |
| Tests passing | 2,329 (standard variant) · 7,190 across all variants |
| Package | `pip install imago-vm` |
| Hardware inbound | Kintex-7 XC7K480T (ETA Jul 2026) |

**Tiers complete:** v1 retirement · OS v2 migration · architecture refinements ·
VM package · type system

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

## Full Documentation

→ **[docs/INDEX.md](docs/INDEX.md)** — complete searchable index

Key documents:

| | |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | The full architecture — cell model, bus, OS, type system, portability |
| [docs/RUNNING.md](docs/RUNNING.md) | Workflow: Composer → VM → FPGA |
| [docs/ICM_FORMAT.md](docs/ICM_FORMAT.md) | `.icm` file format specification |
| [docs/neural_pond_design.md](docs/neural_pond_design.md) | LIF and Izhikevich neurons in UniCell |
| [MIGRATION_TODO.md](MIGRATION_TODO.md) | Open work and architecture decisions |
| [fpga/README_FPGA.md](fpga/README_FPGA.md) | FPGA bring-up guide |
