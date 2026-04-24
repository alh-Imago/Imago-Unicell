# Imago UniCell — Claudette v1.1

**A NOR-universal spatial computing architecture. Every logic function is a NOR gate. No exceptions.**

The architecture that emerges from that constraint has no instruction fetch, no decode pipeline, no program counter, and no separation between compute and memory. Programs are cell networks — wirings — through which data flows and results emerge at known addresses after a deterministic number of clock ticks.

This is not a Von Neumann processor with parallelism added. It is not a GPU. It is not a quantum system. It is a different substrate — deterministic, room-temperature, buildable now — that sits in the space between the sequential model we have been optimising for fifty years and the physically fragile systems that may arrive in the future. When you add a card you add compute and memory simultaneously, in the same ratio, managed by the same OS, addressed by the same compiler. There is no boundary to coordinate across because there is no boundary.

This repository contains a complete virtual machine implementation: cell array, compiler, operating system, security model, GPU backend, browser workbench, and 2,586 passing tests across 45 test suites.

### How this system was built

This architecture was not designed top-down from a specification. It was grown from a single founding constraint — every logic function must be a NOR gate — and followed honestly wherever it led.

The OS emerged from the cell model. The security model emerged from the OS. The compiler emerged from the tile library. The sequencer emerged when the spatial compiler produced dead cells on complex branching. The pipeline queue emerged when deep primitives needed continuous feeding. The AI bridge emerged from COMPANION needing something to reason about ambiguous Ward states. The workbench arrived as an observation layer once the system was complex enough to need one.

None of it was bolted on. Each piece arrived when the system needed it, in the form the system naturally suggested. The result is an emergent architecture — one where the coherence comes from following the constraint rather than from enforcing a design.

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
compiler_pond.py    — CompilerPond: self-hosting compiler as a persistent Pond
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

Expected: **2,586 passed, 0 failed** across 45 test suites.

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

### 13. Device Ponds — sensors, peripherals, and everything else

A keyboard is a Pond. A mouse is a Pond. A display is a Pond. Any sensor or peripheral is a Pond. The discovery, connection, masking, and health monitoring model is identical to any other Pond — there is no separate device subsystem.

```python
from device_bridge import DeviceManager, KeyboardBridge, MouseBridge
from device_bridge import StorageBridge, NetworkBridge, ConsoleBridge

# Register devices — each becomes a DEVICE Pond visible to Shore/Cast
mgr = DeviceManager(controller=ctrl, shore=shore)
mgr.add(KeyboardBridge, base_address=0x00B00000, name='keyboard')
mgr.add(MouseBridge,    base_address=0x00C00000, name='mouse')
mgr.add(StorageBridge,  base_address=0x00D00000, name='storage')
mgr.add(NetworkBridge,  base_address=0x00E00000, name='network')
mgr.add(ConsoleBridge,  base_address=0x00F00000, name='console')

# Devices are now discoverable via Cast exactly like any other Pond
# Any program Pond can find and connect to any device at any time

# Each tick — devices write their state to bus addresses,
# any armed cell listening to those addresses receives it
mgr.tick(ctrl.array.bus)
```

There are no interrupts to the CPU. There is no polling loop at the application level. The keyboard places a keycode on the bus at its output address each tick a key is held. Any cell with its input address set to that bus address receives it automatically. When the device disconnects, the Ward detects the silence — zero emissions at the bridge input — transitions to SILENT state, and the dissolve contract cleans up the Pond. No dangling handles, no leaked resources, no OS intervention required.

The same model extends to any data source. A temperature sensor, a CAN bus node, a LIDAR unit, an IMU — each one is a DEVICE Pond with an output address. Whatever computation needs that data connects to that address. The format conversion, filtering, and routing happens in the cell network. The architecture does not distinguish between a keyboard and a CAN bus frame — both are Ponds producing data at addresses the system can listen to.

**Automotive ECU replacement** — a modern car has dozens of ECUs communicating over CAN, each managing a subsystem in isolation. A UniCell card replaces all of them: each sensor becomes a DEVICE Pond, each actuator becomes a DEVICE Pond, and the logic connecting sensor data to actuator commands is compiled cell networks. No inter-ECU protocol overhead, no polling arbitration, no interrupt priority conflicts. The data flows from the sensor Pond directly to the compute Pond directly to the actuator Pond, all on the same bus, all in parallel.

### 14. The AI bridge — COMPANION with a language model

The AI bridge predates the workbench. It was the first way of interacting with a running system — attaching a small language model to COMPANION's decision loop so that Ward escalations could be reasoned about rather than just rule-matched. The workbench arrived later as a richer observation layer, but the AI bridge remains a distinct and useful capability.

The flow is:

```
VM running → Ward escalates → COMPANION formats status as JSON
→ sends to AI model → AI responds with JSON action
→ COMPANION executes: RESTART / MIGRATE / ISOLATE / NOOP / ESCALATE
```

The AI reads structured system state and returns structured decisions. It is not driving the VM directly — it is extending COMPANION's rule engine for cases the hardcoded rules don't cover cleanly: a Pond that is DEGRADED but not yet STALLED, thermal trends that suggest migration before the threshold is crossed, compound conditions with no single obvious response.

```bash
# Via Ollama — easiest, no GPU required
ollama pull tinyllama
python3 run_companion.py --ollama --demo

# Via TinyLlama direct — requires torch
python3 run_companion.py --ai --cpu --demo

# Interactive Ward simulator with AI decisions
python3 run_companion.py --ollama --interactive
# Type: pond_7 STALLED
# AI responds with action JSON: {"action": "RESTART", "target": "pond_7", "reason": "..."}

# Boot, run demo, save system state
python3 run_companion.py --ollama --demo --save system.img.gz

# Restore from saved state
python3 run_companion.py --load system.img.gz
```

All outputs are JSON artifacts — structured, inspectable, suitable for logging or piping to other tools. The system was designed this way from the start: the VM produces structured state, the AI consumes structured state, the decisions are structured actions. Nothing opaque in the loop.



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

### 15. Open the workbench

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

**Observing the self-hosting boot from the workbench:**

Start the workbench alongside the full boot and watch in real time:
- Tier 2 Ponds appearing in the cell grid — COMPANION, Shore arming
- Tier 3 loading — the CompilerPond cells populating at 0x00600000
- A compile job running — the CompilerPond firing, a new Program Pond appearing in available space
- The compiled program executing — the data wave propagating spatially through the cell network tick by tick

Click any cell at any point to inspect its full state. Freeze the CompilerPond mid-compile. Watch the partial data wave in the program being compiled. This is the entire stack — compiler, OS, and program — observable simultaneously at the level of individual NOR gates.

> **VM vs Silicon note:** In the VM the workbench reads raw cell state directly from Python objects. On silicon this access does not exist — cell state is only readable via the command bus with the auth token, which user space never holds. A production workbench observes through PTT queries, Ward status, and Shore registry only. The VM workbench is a development tool; the production workbench is a PTT/Ward/Shore observer. Both show you what the system is doing — the VM version shows the internals too, which is intentional for development and enforced away on silicon by physics rather than policy.

### 16. Live cell visualiser

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

### 17. The self-hosting boot sequence

A standalone UniCell system compiles, loads, and runs programs entirely within the cell fabric. The compiler is not an external tool — it is a Pond.

```python
from compiler_pond import boot_compiler_pond

# Boot the compiler as a persistent Core Pond
cpond = boot_compiler_pond(arr, ctrl, shore, companion)

# Submit a compile job — returns immediately with a job reference
ref = cpond.compile(
    source        = 'def add(a: int32, b: int32) -> int32: return a + b',
    function_name = 'add',
    compiler_type = 'int32',
)

# Retrieve the result
result = cpond.get_result(ref)
print(f'{result.cell_count} cells emitted')   # 6800

# Compile, load, and run in one call
output = cpond.load_and_run(ref, inputs={'a': 42, 'b': 17})
print(output)   # {'result': 59}
```

The CompilerPond is always armed. It registers with Shore and is discoverable via Cast. Multiple jobs can be submitted simultaneously — each gets its own job reference and result. A running program can call the CompilerPond to recompile one of its own components while continuing to run, then switch to the new version when it is ready.

**The full boot sequence:**

```
Power on
│
├── BIOS-Plus chip
│     Generate auth token (12-bit hardware RNG)
│     Generate salt key  (64-bit hardware RNG)
│     Dead cell survey — build defect map
│     Allocate address space around defective cells
│     Distribute auth token to all live cells
│
├── Tier 2 — BIOS Boot Image
│     COMPANION (permanent OS anchor)
│     Shore V2  (card registry)
│     ShoreKeeper (boundary authority)
│     CommandInterface (three-bus protocol)
│
├── Tier 3 — Core Ponds (self-hosted layer)
│     COMPILER_POND         @ 0x00600000  — always armed
│     INT32_COMPILER_POND   @ 0x00610000  — always armed
│     LLVM_COMPILER_POND    @ 0x00620000  — optional
│     SEQUENCER_POND        @ 0x00630000  — always armed
│     TILE_LIBRARY_POND     @ 0x00640000  — always armed
│     MODEL_LIBRARY_POND    @ 0x00650000  — always armed
│     PROGRAM_BUILDER_POND  @ 0x00660000  — always armed
│
└── System self-hosting
      Any source → CompilerPond → new Program Pond
      No external machine required
```

See `09_Standalone_Boot_and_Self_Hosting.md` and `10_BIOS_Plus_Boot_Sequence.md` for the full specification.

---



```bash
python3 claudette_parallel_demos.py
```

Eight demonstrations comparing UniCell against a modern von Neumann CPU — including honest cases where UniCell wins, where it loses, and why. The architecture is not universally faster. It is differently fast, in ways that make sense once you understand that depth — not clock speed — is the governing metric.

---

## FPGA Implementation

A physical hardware implementation is available in the `fpga/` directory. The cell array runs on real silicon — each cell is a physical register file and NOR gate topology running at the FPGA clock frequency, with a real shared bus and real wired-OR combining. The OS layer runs on the host CPU via a UART bridge.

Supported boards: iCEBreaker (iCE40UP5K), IceStick, Basys 3, Arty A7, OrangeCrab (ECP5), ULX3S and others.

See `fpga/README_FPGA.md` for build instructions, supported boards, and a progression of experiments from a single NOT gate up to compiling Python and loading it onto silicon.

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

Expected across all 45 suites: **2,586 passed, 0 failed**.

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

**Emergent architecture.** The OS was not designed and then implemented on top of the cell model. It emerged from it. COMPANION exists because the cell model needed a rule engine. The Ward exists because Ponds needed health monitoring. The dissolve contracts exist because the Ward needed to manage planned lifecycle as well as faults. The sequencer exists because the spatial compiler produced dead cells on complex branching and the cell model suggested the solution. Each component is what the constraint produced when followed one step further — not a feature added to a design, but a consequence of the founding primitive.

**Everything is a Pond — including devices.** A keyboard is a DEVICE Pond. A mouse is a DEVICE Pond. A display is a DEVICE Pond. A temperature sensor, a CAN bus node, an accelerometer, a network interface — all Ponds. Each one sits behind bridges that enforce the mask check. Each one is registered with Shore and discoverable via Cast. Each one has a Ward watching its health.

The consequence of this is profound. Any program Pond can connect to any device Pond at any time through the same discovery and connection model used for everything else. There are no interrupts to the CPU. There is no polling loop. The device writes its data to its output address on the bus; any armed cell listening to that address receives it. When a device disconnects, the Ward detects the silence, transitions to SILENT state, and the dissolve contract cleans up the Pond automatically — no OS intervention, no dangling handles, no leaked resources.

This makes the architecture applicable anywhere data is produced or consumed: a PC, a car replacing multiple ECU systems, an IoT sensor array, a robotics platform, an industrial controller. The programming model does not change between these domains. A sensor sending temperature data and a keyboard sending keycodes are the same kind of thing — a Pond with an output address. Whatever needs that data connects to it. The architecture does not distinguish between device classes.

---

## Silicon path

First tape-out target: **ChipFoundry chipIgnite** — SKY130 130nm, 15mm² user area, 112,500 cells, $14,950 for 100 QFN-packaged chips. The RISC-V management core included in the MPW maps to the CommandInterface role. The NOR cell array is the compute fabric.

At 3nm: 22.5M cells per 1cm² die. PCIe card (56 dies/face): 1.26B cells/side. 12-layer 3D stack: 30.24B cells/card.

**Add a card — add compute and memory simultaneously.** Every cell is both compute and memory. There is no boundary between them to coordinate across. Adding a card adds both in the same ratio, under the same OS, with the same addressing model, managed by the same compiler output. The ShoreKeeper on the new card registers with HyperShore. The new cells are immediately addressable via the 64-bit extended address space. No cache coherence negotiation. No memory controller reconfiguration. No NUMA topology to reason about. The architecture scales linearly because the primitive scales linearly — you are adding more of the same thing, not adding a new kind of thing and then solving the coordination problem between them.

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
| AI bridge (COMPANION + TinyLlama / Ollama, JSON artifacts) | Complete — passing |
| CompilerPond — self-hosting compiler as persistent Pond | Complete — passing |
| BIOS-Plus boot sequence (Tier 1/2/3) | Specified — VM implementation in progress |
| HyperShore / HyperCompanion | Designed — pre-silicon |
| MIDAS silicon (SKY130 chipIgnite) | Specified — pre-silicon |

**2,586 tests. 0 failures.**

---

## Contact

[Contact details]
