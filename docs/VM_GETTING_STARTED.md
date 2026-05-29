# Getting Started with Imago UniCell

*Last updated 2026-05-29. Install the VM, run your first example, compile your first function, and open the
workbench — in under five minutes.*

See [INDEX.md](INDEX.md) for the full document map.
See [RUNNING.md](RUNNING.md) for the complete API and CLI reference.

---

## 1 — Install

```bash
pip install imago-vm
```

That's the whole runtime: the VM, the compiler, the CLI, the workbench, and all
bundled examples.

**Optional extras**

```bash
pip install llvmlite   # C / C++ / Rust frontend (LLVM IR → UniCell)
pip install pyserial   # FPGA hardware upload over JTAG/UART
```

Check what's installed:

```bash
imago info
```

---

## 2 — Run a bundled example

```bash
# See what's available
imago examples

# Run the NOT gate: a=1 → result=0
imago run not_gate a=1

# Run the 32-bit integer adder: 5 + 3 = 8
imago run adder_int32 a=5 b=3
```

`imago run` loads the `.icm` file, arms the cell network, supplies inputs, runs
one tick, and prints results. The `[CONTROLLER]` log lines are normal — suppress
them with `IMAGO_VERBOSE=0`:

```bash
IMAGO_VERBOSE=0 imago run adder_int32 a=5 b=3
# Loaded 'adder_int32' — 483 cells
# Inputs:  ['a', 'b']
# Outputs: ['result']
#
# Result:
#   result = 8
```

---

## 3 — Compile your first function

Write a plain Python function — no imports, no special types needed for boolean
logic:

```python
# myfile.py

def xor(a, b):
    return (a or b) and not (a and b)
```

Compile it:

```bash
IMAGO_VERBOSE=0 imago compile myfile.py xor
# Compiling 'xor'...
# OK — 4 cells
# Inputs:  ['a', 'b']
# Outputs: ['output']
```

Four cells. One cycle. Before saving, the CLI scans the function and prompts
you to confirm or rename each port — press Enter to keep the discovered name,
or type a new one. Port names become the keys in the `.icm` header and any
PTT (Pond Task Table) entries.

Save the result as a portable `.icm` file:

```bash
IMAGO_VERBOSE=0 imago compile myfile.py xor --save xor.icm
```

Run it back immediately:

```bash
IMAGO_VERBOSE=0 imago run xor.icm a=1 b=0
# Result:
#   output = 1
```

---

## 4 — 32-bit integer arithmetic

Boolean functions use single-bit cells. For 32-bit integer arithmetic, annotate
your function with `int32` and use the `--int32` flag:

```python
# add32.py
from compiler_int32 import int32

def add(a: int32, b: int32) -> int32:
    return a + b
```

```bash
IMAGO_VERBOSE=0 imago compile add32.py add --int32 --save add.icm
# Compiling 'add'  [INT32]...
# OK — 483 cells
# Inputs:  ['a', 'b']
# Outputs: ['output']
```

483 cells, depth 2 (Kogge-Stone parallel prefix adder). The same `.icm` runs
on the VM, on an iCEBreaker FPGA, and on a Kintex-7 — no recompilation.

---

## 5 — Python API

```python
import imago
imago.set_verbose(False)          # suppress [CONTROLLER] log lines

# Run a bundled example
result = imago.run_icm('composer/examples/not_gate.icm', {'a': 1})
print(result)    # {'result': 0}

# Compile and run a function directly
vm = imago.compile_function('''
def xor(a, b):
    return (a or b) and not (a and b)
''', 'xor')

print(vm.run(a=1, b=0))    # {'output': 1}
print(vm.run(a=1, b=1))    # {'output': 0}
print(vm.status())          # cells, inputs, outputs, ...
```

`compile_function` returns a `VM` instance already loaded with the compiled
program. Call `.run(**inputs)` as many times as you like — the VM resets
between calls.

---

## 6 — Open the workbench

The workbench is a browser-based visual designer for building programs from
cells and models without writing code.

```bash
imago-workbench
# → http://localhost:7420
```

In the workbench you can:

- Place cells and wire them on the canvas
- Declare named input and output ports in the **ports** tab
- Load and connect bundled models (INT32_ADD, LIF neuron, etc.) from the **models** tab
- Simulate the network tick-by-tick
- Export to `.icm` (File → Export ICM)
- Import any `.icm` file to inspect or extend it

See [RUNNING.md](RUNNING.md) for the full workbench reference, including port
declarations and the Composer tab workflow.

---

## What's next

| Goal | Where to look |
|---|---|
| Understand the cell model and OS | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Full CLI and API reference | [RUNNING.md](RUNNING.md) |
| `.icm` file format | [ICM_FORMAT.md](ICM_FORMAT.md) |
| Build a spiking neural network | [NEURAL_POND_TUTORIAL.md](NEURAL_POND_TUTORIAL.md) |
| Save programs to your user library | [LIBRARY.md](LIBRARY.md) |
| Upload to FPGA hardware | [RUNNING.md](RUNNING.md) — FPGA section |
| Browse all docs | [INDEX.md](INDEX.md) |
