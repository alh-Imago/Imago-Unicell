# Imago UniCell — Claudette v1.1

**A NOR-universal spatial computing architecture. Every logic function is a NOR gate. No exceptions.**

The architecture that emerges from that constraint has no instruction fetch, no decode pipeline, no program counter, and no separation between compute and memory. Programs are cell networks — wirings — through which data flows and results emerge at known addresses after a deterministic number of clock ticks.

This repository contains a complete virtual machine implementation: cell array, compiler, operating system, security model, GPU backend, browser workbench, and 2,409 passing tests across 43 test suites.

---

## What is in here

```
unicell.py          — The cell: 192-bit register file + dedicated start flag
unicell_array.py    — The array: shared bus, wired-OR, armed set, ECC
gate_states.py      — All 12 gate state flags (32-bit config register)
compiler.py         — Python AST → spatial cell map or command table
compiler_int32.py   — 32-bit integer specialised compiler
sequencer.py        — Command table execution model, resource manifest
program_builder.py  — Multi-file dependency walker, global address map
llvm_frontend.py    — LLVM IR parser (requires llvmlite)
llvm_ir_mapper.py   — LLVM IR → tile operations
fp_tiles.py         — 40-tile library (INT32_ADD_CLA depth=58, FP32_MUL, ...)
model_library.py    — Composed models, user-editable, two-tier library
branch.py           — Runtime-volatile dispatch: BranchPoint + DataTable
pipeline_queue.py   — Reference shift register, out-of-order delivery
pond.py             — OS resource unit: bounded cell region, bridge-gated
ward.py             — Health monitor: emission tracking, thermal, dissolve contracts
shore_v2.py         — Card registry: HIDDEN Pond, ShoreTile stored in cells
shorekeeper.py      — Card boundary authority, heartbeat aggregation
companion.py        — OS anchor: rule engine, key issuance, COMPANION boot
cast.py             — Discovery: Pebble, Ripple, Skipping Stone
vm_image.py         — Snapshot, freeze, migrate, round-trip serialise
controller.py       — Cell map loader, region lifecycle, freeze/thaw
gpu_array.py        — CuPy GPU kernel / NumPy fallback
multi_dimm.py       — Multi-array controller, 64-bit address routing
uniflex_fs.py       — UniFlex: FAT32/NTFS/ext4/APFS as Storage Ponds
display_pond.py     — Framebuffer, delta renderer, thermal palette
device_bridge.py    — Keyboard, storage, network, console bridges
workbench.py        — Browser IDE: source editor, live cell grid, 12 demos
visualiser.py       — Live cell grid, click-to-inspect, step/run
run_companion.py    — Full system boot entry point
```

---

## Requirements

**Python 3.12+** required (uses `match` statements and type union syntax).

### Minimal — runs all core tests and the compiler

```bash
pip install pytest numpy llvmlite
```

### Full — adds GPU backend, display, and AI bridge

```bash
pip install pytest numpy llvmlite pygame
pip install cupy-cuda12x          # GPU backend (CUDA 12) — skip if no GPU
pip install torch transformers accelerate  # AI bridge — optional
```

### Run the test suite

```bash
cd Python
python3 -m pytest .
# or run individual suites directly:
python3 test_array.py
python3 test_compiler.py
python3 test_compiler_int32.py
```

Expected: **2,409 passed, 0 failed** across 43 test suites.

---

## Quick start

All examples run from the `Python/` directory.

### 1. The cell — raw NOR gate

```python
from unicell_array import UniCellArray
from gate_states import GS_NOT

arr = UniCellArray(cell_count=1000)

# Wire a NOT gate manually
c = arr.allocate_cell()
c.gate_state     = GS_NOT
c.input_address  = 0x0100
c.output_address = 0x0200
c.start_flag     = True
arr._armed.add(c.address)

# Inject input and tick
arr.bus[0x0100] = (1, arr._tick_count)
arr.tick()

print(arr.read_bus(0x0200))   # → 0
```

This is the entire primitive. One cell. 192 bits of register state plus a dedicated start flag line. The cell fires when data arrives at its input address, computes its NOR gate topology, and writes to its output address. No instruction. No decoder. The cell is the instruction.

### 2. Wired-OR — two-input NAND from two single-input cells

```python
from unicell_array import UniCellArray
from gate_states import GS_NOT

arr = UniCellArray(cell_count=1000)

# Two NOT cells sharing an output address
ca = arr.allocate_cell()
ca.gate_state = GS_NOT; ca.input_address = 0x0100; ca.output_address = 0x0300
ca.start_flag = True; arr._armed.add(ca.address)

cb = arr.allocate_cell()
cb.gate_state = GS_NOT; cb.input_address = 0x0101; cb.output_address = 0x0300
cb.start_flag = True; arr._armed.add(cb.address)

arr.bus[0x0100] = (0, arr._tick_count)   # NOT(0) = 1
arr.bus[0x0101] = (1, arr._tick_count)   # NOT(1) = 0
arr.tick()

print(arr.read_bus(0x0300))   # → 1  (NOT(0) OR NOT(1) = NAND(0,1) = 1)
```

When two cells write to the same address in the same tick their values are OR'd together. This is not a conflict — it is the mechanism for building multi-input operations from single-input cells. Two NOT cells sharing an output produce NAND by De Morgan's law. True NOR uses the `GS_NOR` internal topology flag within a single cell.

### 3. Controller — load a cell map and run

```python
from controller import ImagoController, CellMapRecord
from gate_states import GS_NOT

ctrl = ImagoController(cell_count=100_000)

# Build a two-stage NOT chain: NOT(NOT(1)) = 1
cell_map = [
    CellMapRecord(GS_NOT, 0x1000, 0x1001),   # stage 1
    CellMapRecord(GS_NOT, 0x1001, 0x2000),   # stage 2
]

region_id = ctrl.load_map(cell_map, 'double_not')
result = ctrl.run(region_id,
                  inputs={0x1000: 1},
                  capture_addresses=[0x2000])

print(result[0x2000])   # → 1
```

`load_map` allocates cells, sets gate topologies and addresses, and returns a region ID. `run` injects inputs, ticks until the armed set empties, captures the specified output addresses, and returns them. The pipeline depth — how many ticks from input to output — is a structural property of the wiring.

### 4. Freeze and thaw

```python
ctrl2 = ImagoController(cell_count=10_000)
rid = ctrl2.load_map([CellMapRecord(GS_NOT, 0x1000, 0x2000)], 'freeze_test')

ctrl2.start(rid, inputs={0x1000: 1})
print(f'Armed before freeze: {len(ctrl2.array._armed)}')   # → 1

ctrl2.freeze(region_id=rid)
print(f'Armed after freeze:  {len(ctrl2.array._armed)}')   # → 0

ctrl2.thaw(region_id=rid)
print(f'Armed after thaw:    {len(ctrl2.array._armed)}')   # → 1
```

Clearing the start flag suspends cells in place. Gate topology, stored values, and address configuration are fully preserved. Zero energy. Zero bus traffic. The rest of the array continues unaffected. Assert the flags again to resume from the exact suspended state.

### 5. Gate state flags

```python
from gate_states import (
    GS_PASS,       # identity — pass input unchanged
    GS_NOT,        # NOT(a) = NOR(a,a)
    GS_NOR,        # internal two-input NOR topology
    GS_SELECT,     # conditional router: routes data wave to one of two addresses
    LOOP_MODE,     # stay armed after firing — for loops and latches
    GS_LATCH,      # hold last result and re-emit every tick
    GS_ONE_SHOT,   # fire exactly once then lock permanently
    GS_INVERT_OUT, # flip output after gate computation
    GS_SYNC_WAIT,  # hold until two inputs have arrived before firing
    GS_LOOP_BACK,  # internal G8→G0 feedback: in-situ register
    GS_BROADCAST,  # fan output to all cells at output_address
    GS_TRACE,      # log every firing to debug buffer
)

# Flags compose with bitwise OR
from gate_states import GS_NOT, LOOP_MODE
loop_not = GS_NOT | LOOP_MODE   # NOT gate that stays armed
```

The config register is 32 bits. Bits 0–8 configure the NOR gate topology (9 gates in a fixed tree). Bits 9–31 are mode flags. The full 32-bit register is what gets stored in `CellMapRecord.gate_state`.

### 6. The int32 compiler

```python
from compiler_int32 import run_int32_function
from fp_tiles import TileLibrary

lib = TileLibrary()

result = run_int32_function(
    'def add(a: int32, b: int32) -> int32: return a + b',
    'add',
    {'a': 42, 'b': 17},
    tile_library=lib,
)
print(result)   # → 59
```

The compiler does not produce opcodes. It emits a cell network — a wiring diagram — and loads it into the controller. `run_int32_function` compiles, runs, and returns the result. The underlying cell map is available if you want to inspect it.

```python
from compiler_int32 import Int32Compiler

comp = Int32Compiler(tile_library=lib)
records, graph, input_bit_map, output_addrs, segments = comp.compile_int32_function(
    'def add(a: int32, b: int32) -> int32: return a + b', 'add'
)

print(f'{len(records)} cells emitted')
print(f'Pipeline depth: {max(len(segs) for segs in segments.values())} ticks')
print(graph.dump())   # prints the IR dependency graph
```

### 7. The general compiler — boolean logic and control flow

```python
from compiler import ImagoCompiler

comp = ImagoCompiler()

# Boolean or: 4 cells
records, graph, input_map, output_addrs = comp.compile_function(
    'def f(a, b):\n    return a or b',
    'f', ['a', 'b']
)
print(f'a or b: {len(records)} cells')
print(graph.dump())
```

```python
# While loop with LOOP_MODE and storage cells
records, graph, input_map, output_addrs = comp.compile_function(
    'def loop(x):\n    while x:\n        x = 0\n    return x',
    'loop', ['x']
)

# Include extra_records (storage and SELECT cells for the loop)
all_records = list(records) + list(comp._extra_records)

from controller import ImagoController
ctrl = ImagoController(cell_count=100_000)
rid = ctrl.load_map(all_records, 'while_loop')

# Manual tick loop — while loops use storage cells that re-emit each tick
ctrl.start(rid, inputs={input_map['x']: 1})
captured = {}
for _ in range(50):
    active = ctrl.array.tick()
    for addr, val in ctrl.array.bus.items():
        captured[addr] = val[0] if isinstance(val, tuple) else val
    if active == 0:
        break

print(f'loop(x=1) = {captured.get(output_addrs[0])}')   # → 0
```

### 8. The sequencer — command table execution model

The sequencer pre-allocates a pool of primitives once and drives them with a command table. Decision trees become lists. No dead cells.

```python
from sequencer import ProgramSequencer, CommandRow, ResourceManifest
from controller import ImagoController

ctrl = ImagoController(cell_count=100_000)
seq  = ProgramSequencer(ctrl)

# Declare what primitives are needed and maximum simultaneous instances
manifest = ResourceManifest(primitives={'NOT': 1})

# Build the command table
commands = [
    CommandRow(
        label       = 'step 0: NOT(1)',
        primitive   = 'NOT',
        variables   = {'a': 1},
        result_name = 'r0',
    ),
    CommandRow(
        label       = 'step 1: NOT(result of step 0)',
        primitive   = 'NOT',
        variables   = {'a': '@r0'},    # @name references a previous result
        result_name = 'r1',
    ),
]

seq.load_program(manifest, commands)
results = seq.run()

print(results)   # → {'r0': 0, 'r1': 1}
```

The `@name` reference syntax means a step can depend on a previous result. The sequencer waits until the referenced result is in the output table before executing the step.

### 9. The tile library

```python
from fp_tiles import TileLibrary

lib = TileLibrary()
tiles = lib.list_tiles()

print(f'{len(tiles)} tiles available')

# Show key tiles
for name in ['INT32_ADD_CLA', 'INT32_ADD', 'FP32_MUL', 'SR_LATCH']:
    t = next(t for t in tiles if t['name'] == name)
    print(f'  {name:20s}  pipeline_depth={t["pipeline_depth"]:4d}  cells={t["cell_count"]:7d}')
```

```
40 tiles available
  INT32_ADD_CLA        pipeline_depth=  58  cells=  6227
  INT32_ADD            pipeline_depth= 194  cells= 12931
  FP32_MUL             pipeline_depth= 451  cells=397740
  SR_LATCH             pipeline_depth=   2  cells=      8
```

Pipeline depth is a structural property of the cell network — not a measured runtime, not an approximation. It is the exact number of ticks from input to output, determined by the wiring. This is the governing metric for all timing and composition in the architecture.

### 10. ECC — single-bit correction, double-bit detection

```python
from unicell import _compute_ecc, _verify_ecc

val   = 0xDEADBEEF
check = _compute_ecc(val)

# Inject a single-bit error
flipped = val ^ (1 << 13)

corrected, was_corrected, double_detected = _verify_ecc(flipped, check)

print(f'Original:  0x{val:08X}')
print(f'Flipped:   0x{flipped:08X}')
print(f'Corrected: 0x{corrected:08X}  (match: {corrected == val})')
print(f'Fixed:     {was_corrected}')
```

ECC is per-cell. Enable it on a region with `arr.enable_ecc(addresses)`. All 32 single-bit positions are correctable. Double-bit errors are detected and reported.

### 11. Pond, Ward, and the OS

```python
from unicell_array import UniCellArray
from pond import Pond
from pond_types import PROCESS, OPEN

arr  = UniCellArray(cell_count=50_000)
pond = Pond(
    name         = 'compute_pond',
    array        = arr,
    owner_id     = 'user',
    pond_type    = PROCESS,
    base_address = 0x00300000,
    region_size  = 0x10000,
)

print(f'Pond:    {pond.pond_id}  bridges={len(pond.bridges)}')
print(f'Ward:    {pond.ward.state}')

# Simulate healthy activity then silence
for _ in range(5):  pond.ward.tick(emissions=200)
for _ in range(52): pond.ward.tick(emissions=0)

ws = pond.ward.status
print(f'After silence: {ws.state}  reason="{ws.anomaly_reason}"')
# → STALLED  reason="zero emissions for 52 cycles"
```

```python
# The mask primitive — visibility at every layer
bridge = pond.bridges[0]
print(f'Bridge access_mask: 0x{bridge.access_mask:08X}')

for process_mask, label in [
    (0xFFFFFFFF, 'full access'),
    (0x00000001, 'tenant bit 0'),
    (0x00000000, 'no bits set'),
]:
    visible = (process_mask & bridge.access_mask) != 0
    print(f'  0x{process_mask:08X} ({label}): visible={visible}')
```

A resource that fails the mask check is not denied — it is absent. No error. No log entry. No acknowledgement. From the querying process's perspective, the resource was never there.

### 12. Shore, Cast, and discovery

```python
import types, sys

# Stub packet_spec if not available
ps = types.ModuleType('packet_spec')
for attr in ['Packet','CapabilityDescriptor','FLAG_ANNOUNCE','FLAG_ROUTE_UPDATE',
             'FLAG_READY','FLAG_MOVING','FLAG_CAPABILITY','FLAG_ACK',
             'POND_TYPE_NAMES','WARD_STATE_NAMES','SECURITY_NAMES']:
    setattr(ps, attr, {} if attr.endswith('NAMES') else 0)
for attr in ['SECURITY_OPEN','SECURITY_PRIVATE','SECURITY_HIDDEN']:
    setattr(ps, attr, attr.split('_',1)[1])
sys.modules['packet_spec'] = ps

from unicell_array import UniCellArray
from shore_v2 import ShoreV2, ShoreEntry
from pond import Pond, PondManager
from pond_types import PROCESS, OPEN, HIDDEN
from cast import CastEngine, VIS_PUBLIC

arr  = UniCellArray(cell_count=200_000)
mgr  = PondManager(arr)

p1 = mgr.create_pond('compute_alice', 'alice', OPEN,   PROCESS, base_address=0x00300000)
p2 = mgr.create_pond('compute_bob',   'bob',   OPEN,   PROCESS, base_address=0x00400000)
p3 = mgr.create_pond('secret',        'sys',   HIDDEN, PROCESS, base_address=0x00500000)

engine = CastEngine(mgr)

# Ripple Cast — discovers all visible Ponds
wave = engine.ripple_cast('alice', visibility=VIS_PUBLIC, collect_all=True)
print(f'Ripple found {len(wave.results)} pond(s):')
for r in wave.results:
    print(f'  {r.pond_id}  hop={r.hop}  announced={r.announced_to_owner}')

# HIDDEN pond is absent — not denied, simply not visible
found_secret = any(r.pond_id == p3.pond_id for r in wave.results)
print(f'Secret pond found: {found_secret}')   # → False
```

### 13. Boot the full system

```bash
# Basic boot — array, Shore, COMPANION, device bridges
python3 run_companion.py

# Boot and run the demo
python3 run_companion.py --demo

# Interactive Ward simulator — type pond states and see COMPANION respond
python3 run_companion.py --interactive

# Boot with a larger array
python3 run_companion.py --cells 100000 --demo

# Save system state on exit
python3 run_companion.py --demo --save system.img.gz

# Restore from saved state
python3 run_companion.py --load system.img.gz

# Attach TinyLlama AI bridge (requires torch + transformers, downloads ~2.2GB)
python3 run_companion.py --ai

# Use Ollama instead (requires Ollama running locally)
ollama pull tinyllama
python3 run_companion.py --ollama
```

### 14. Open the workbench

```bash
python3 workbench.py
# Opens browser at http://localhost:7420
```

The workbench is a full browser-based development environment:

- **Source editor** — write Python, click Compile + Load, click Run
- **Live cell grid** — every cell is a coloured block; click any cell to see its full 192-bit state
- **12 built-in demos** — all gate types, loops, branches, tiles, the sequencer
- **Region manager** — list, highlight, free individual regions
- **Bus injection** — write any value to any address directly
- **Execution controls** — Step / Run / Pause, speed slider, cycle counter
- **Cell inspector** — gate_state, input/output addresses, stored value, start flag, ECC status
- **Array statistics** — armed cells, tick count, per-DIMM breakdown
- **JSON export** — full array state to file

### 15. Live cell visualiser

```bash
python3 visualiser.py
# Opens browser with a live 8×8 grid demo
```

Or embed in your own code:

```python
from visualiser import Visualiser
from controller import ImagoController

ctrl = ImagoController(cell_count=64)
# ... load a program ...
vis = Visualiser(ctrl.array, grid_cols=8)
vis.serve()   # opens browser and blocks until closed
```

Watch a data wave propagate through the cell network, tick by tick, spatially. Click any cell for full state. Step or run from the browser controls.

---

## Running the parallel demos

```bash
python3 claudette_parallel_demos.py
```

Eight demonstrations comparing UniCell against a modern von Neumann CPU — including honest cases where UniCell wins, where it loses, and why. The architecture is not universally faster. It is differently fast, in ways that make sense once you understand that depth — not clock speed — is the governing metric.

---

## Running the full test suite

```bash
cd Python

# All suites
for f in test_*.py; do python3 "$f"; done

# Individual suites
python3 test_array.py           # UniCellArray — tick, bus, armed set
python3 test_ecc.py             # SECDED Hamming — all 32 bit positions
python3 test_gate_state_32.py   # 32-bit config register, all 12 flags
python3 test_compiler.py        # Python AST → cell network
python3 test_compiler_int32.py  # 32-bit integer compiler
python3 test_while.py           # While loop compilation
python3 test_cla.py             # Carry-lookahead adder tile
python3 test_fp_tiles.py        # Full tile library
python3 test_pond.py            # Pond, bridges, mask
python3 test_ward.py            # Ward state machine
python3 test_shore_v2.py        # Shore registry
python3 test_cast.py            # Pebble, Ripple, Skipping Stone
python3 test_freeze.py          # Snapshot, freeze, migrate
python3 test_migration.py       # Live migration
python3 test_gpu_array.py       # GPU/NumPy backend
python3 test_llvm_frontend.py   # LLVM IR parser (requires llvmlite)
python3 test_llvm_ir_mapper.py  # LLVM IR → tiles
```

Expected across all 43 suites: **2,409 passed, 0 failed**.

---

## Architecture overview

```
Cell (192-bit register file + 1-bit start flag)
  ├── gate_state     32 bits  NOR topology (bits 0–8) + 12 mode flags
  ├── input_address  64 bits  where this cell listens
  ├── output_address 64 bits  where this cell writes (64-bit native)
  ├── data           32 bits  current value
  └── start flag      1 bit   dedicated hardware line — not on any bus

UniCellArray — shared bus, wired-OR, armed set, ECC
  └── All armed cells evaluate simultaneously, every tick

Tile library — 40 pre-verified cell networks, fixed pipeline depths
  └── INT32_ADD_CLA (depth=58), FP32_MUL (depth=451), SR_LATCH (depth=2)...

Two compiler models
  ├── Spatial map   — full cell-by-cell wiring, maximum parallelism
  └── Sequencer     — resource manifest + command table, no dead cells

Claudette OS
  ├── Pond          — bounded cell region, bridge-gated, mask-checked
  ├── Ward          — health monitor, dissolve contracts, thermal tracking
  ├── COMPANION     — OS anchor: rule engine, key issuance, migrations
  ├── Shore         — card registry (HIDDEN Pond, ShoreTile stored in cells)
  └── ShoreKeeper   — heartbeat aggregation, cross-card boundary authority

Addressing
  ├── Local (32-bit)   — within Pond, PTT-relative
  ├── Shore (48-bit)   — within card
  └── Extended (64-bit) — cross-card, native in address registers

Security
  └── (process_mask & resource_mask) != 0  → visible
      (process_mask & resource_mask) == 0  → absent (not denied — absent)
```

---

## Key concepts

**Depth, not clock speed.** The pipeline depth of a tile is a structural property of its wiring — the exact number of ticks from input to output. This is known at compile time, does not vary between runs, and governs all timing and composition decisions. Two programs are compared by their depth, not by clock frequency.

**Wired-OR.** When two cells write to the same address in the same tick, their values are OR'd. Two NOT cells sharing an output produce NAND (NOT(a) OR NOT(b) = NAND(a,b)). True NOR uses the `GS_NOR` internal topology within a single cell. Both are universally complete.

**Start flag.** A dedicated hardware line — not a register bit, not on any bus. Clearing it suspends a cell in place with full state preserved. Four architectural mechanisms from one line: configuration gating, branch routing, checkpoint freeze, debug pause.

**Cells as memory.** `GS_LATCH` holds a result and re-emits every tick. `storage_mode` persists a value until updated. `GS_LOOP_BACK` feeds output back to input for an in-situ register. There is no separate memory subsystem.

**The mask.** A single bitwise AND governs visibility at every layer from the raw cell config register through bridges, Ponds, discovery, filesystem, and cross-card traffic. A failing check makes a resource absent, not denied. The querying process cannot learn the resource exists.

---

## Silicon path

First tape-out target: **ChipFoundry chipIgnite** — SKY130 130nm, 15mm² user area, 112,500 cells, $14,950 for 100 QFN-packaged chips. The RISC-V management core included in the MPW maps to the CommandInterface role. The NOR cell array is the compute fabric.

At 3nm: 22.5M cells per 1cm² die. PCIe card (56 dies/face): 1.26B cells/side. 12-layer 3D stack: 30.24B cells/card.

---

## Status

| Component | Status |
|---|---|
| Cell, array, ECC, gate states | Complete — passing |
| Tile library (40 tiles) | Complete — passing |
| Spatial compiler (Python AST + LLVM) | Complete — passing |
| Sequencer / command table model | Complete — passing |
| Program builder (multi-file) | Complete — passing |
| Pipeline queue, BranchPoint | Complete — passing |
| Claudette OS (Pond, Ward, Shore, COMPANION) | Complete — passing |
| VM image (freeze, snapshot, migrate) | Complete — passing |
| Security model (9 layers, mask) | Complete — passing |
| GPU backend (CuPy / NumPy) | Complete — passing |
| Multi-DIMM controller | Complete — passing |
| UniFlex filesystem | Complete — passing |
| Workbench + Visualiser | Complete — passing |
| HyperShore / HyperCompanion | Designed — pre-silicon |
| MIDAS silicon (SKY130 chipIgnite) | Specified — pre-silicon |

**2,409 tests. 0 failures.**

---

## Contact

[Contact details]
