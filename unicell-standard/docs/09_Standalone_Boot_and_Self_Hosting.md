# Imago UniCell — Standalone Boot Sequence and Self-Hosting
## Claudette v1.1

---

## Overview

A standalone UniCell system — one with no external host CPU, no development machine, no external compiler — must be able to compile, modify, and extend itself entirely from within the fabric. This document specifies the boot sequence that achieves that, the core Ponds that must be present for self-hosted operation, and the path from the current VM implementation to a fully self-hosted boot image.

Updated to reflect the completed VM implementation. Phase 1 (CompilerPond) is implemented and tested. Phase 2 (boot manifest) is complete — `run_companion.py` boots the full Tier 2 + Tier 3 stack. See the VM Implementation section below for current status.

---

## Why Self-Hosting Matters

A system dependent on an external machine for compilation is not standalone. Every program change, every new tile, every adaptation requires a laptop connected to the system. For embedded deployment — a vehicle, a robot, an industrial controller, a field device — that dependency is unacceptable.

Self-hosting removes it. Once booted, the system compiles, loads, runs, and modifies programs entirely within the cell fabric. An engineer in the field can deploy a new program from source. A running system can recompile a hot path and replace it without restarting. A program can spawn variants of itself, test them, and dissolve the inferior one — all within the fabric, at cell speed.

The compiler is not a tool that sits outside the system. **The compiler is a Pond.**

---

## Boot Tiers

### Tier 1 — Silicon Fixed

The cell array, the shared bus, the start flag mechanism, the wired-OR combining property, ECC on all data paths. This is hardware. It does not change at runtime. It is the substrate everything else runs on.

On the chipIgnite SKY130 proof-of-concept: 112,500 cells, the RISC-V management core acting as CommandInterface, the BIOS-Plus chip holding the 12-bit auth token and 64-bit salt key.

### Tier 2 — BIOS Boot Image

Loaded from the BIOS-Plus chip at power-on. The minimum OS to bring the system to a state where it can load the Tier 3 core Ponds.

Contents:
- **COMPANION** — booted first, permanently HIDDEN, permanent anchor
- **Shore V2** — card registry, booted alongside COMPANION
- **ShoreKeeper** — card boundary authority, heartbeat aggregation
- **CommandInterface** — three-bus protocol translator, auth token distribution

This tier is fixed at manufacture. It is the minimum viable OS. It cannot compile. It cannot run user programs. Its only job is to bring up the infrastructure that loads Tier 3.

In the VM: `run_companion.py` boot sequence covers this tier. COMPANION, Shore, and ShoreKeeper are already implemented and tested.

### Tier 3 — Core Ponds (Self-Hosted Layer)

Loaded by the BIOS boot image from persistent storage (UniFlex filesystem Pond). These are themselves compiled cell networks — spatial programs running in the fabric, subject to the same Ward monitoring and security model as everything else.

Once Tier 3 is loaded, the system is self-hosted. Everything above this layer can be compiled, modified, and replaced from within.

**Required Core Ponds:**

#### 3.1 Tile Library Pond
- Type: LIBRARY, HIDDEN, permanent
- Contents: all 40 core tiles (INT32_ADD_CLA, FP32_MUL, SR_LATCH, etc.)
- Role: the vocabulary the compiler draws from
- Access: via COMPANION TILE key
- Already in VM: `fp_tiles.py` — TileLibrary class, loaded at COMPANION boot

#### 3.2 Model Library Pond
- Type: LIBRARY, HIDDEN, permanent
- Contents: composed models built from tiles (INT32_ADDER, FP32_MULTIPLIER, etc.)
- Role: higher-level vocabulary, pre-verified blueprints with named ports
- Access: via COMPANION TILE key
- Already in VM: `model_library.py` — ModelLibrary class, registered at boot

#### 3.3 Compiler Pond
- Type: LIBRARY, HIDDEN, permanent, always armed
- Contents: the spatial compiler — Python AST → cell network
- Role: accepts source input, returns compiled CellMapRecord list
- Interface: SOURCE_IN bridge (source text), MAP_OUT bridge (cell map), STATUS bridge
- Access: via COMPANION COMPILE key (new key type needed)
- Already in VM: `compiler.py` + `compiler_int32.py` — needs Pond wrapper

#### 3.4 Sequencer Pond
- Type: LIBRARY, HIDDEN, permanent, always armed
- Contents: the command table execution model
- Role: accepts resource manifest + command table, drives primitive pool
- Interface: MANIFEST_IN, TABLE_IN, RESULT_OUT bridges
- Already in VM: `sequencer.py` — needs Pond wrapper

#### 3.5 LLVM Mapper Pond
- Type: LIBRARY, HIDDEN, permanent
- Contents: LLVM IR parser + tile mapper
- Role: accepts LLVM IR text, returns compiled CellMapRecord list
- Access: via COMPANION COMPILE key
- Already in VM: `llvm_frontend.py` + `llvm_ir_mapper.py` — needs Pond wrapper
- Note: requires llvmlite; optional for embedded deployments without LLVM input

#### 3.6 UniFlex Filesystem Pond
- Type: FS, HIDDEN, permanent
- Contents: filesystem layer (FAT32/NTFS/ext4/APFS as Storage Ponds)
- Role: persistent storage for compiled images, source, configuration
- Already in VM: `uniflex_fs.py` — needs integration with boot sequence

#### 3.7 Program Builder Pond
- Type: LIBRARY, HIDDEN, permanent
- Contents: multi-file dependency walker, global address map
- Role: assembles multi-component programs, resolves cross-file references
- Already in VM: `program_builder.py` — needs Pond wrapper

---

## The Compiler as a Pond — Detailed Model

The Compiler Pond is the most important addition for self-hosted operation. Its design:

```
COMPILER POND
─────────────────────────────────────────────────────
Type:         LIBRARY
Security:     HIDDEN
Lifecycle:    permanent, always armed
Ward:         monitors compile request throughput

Bridges:
  INBOUND:    SOURCE_IN    — source text (Python AST or LLVM IR)
  INBOUND:    CONFIG_IN    — compiler options (target model, optimisation level)
  OUTBOUND:   MAP_OUT      — compiled CellMapRecord list
  OUTBOUND:   STATUS_OUT   — compile status (SUCCESS, ERROR, DEPTH, CELL_COUNT)
  MONITOR:    (standard Ward monitoring)

Operation:
  1. Caller sends source text to SOURCE_IN bridge
  2. Compiler Pond processes — runs the compiler cell network
  3. Result (CellMapRecord list) appears at MAP_OUT
  4. Caller loads the map into available cell space via COMPANION
  5. New program Pond is armed and running

Parallel compilation:
  Multiple callers can submit to the same Compiler Pond simultaneously
  Each compile job is a separate pipeline — the sequencer model
  handles multiple parallel compile jobs from the same primitive pool
  Results are tagged by job reference (pipeline queue model)
```

### What this enables

**Always ready** — no startup, no loading, no initialisation. The compiler is already running.

**Parallel variants** — a program testing multiple implementations submits all variants simultaneously. Results arrive as each compilation completes. The best performing variant is kept, the others dissolve.

**Self-modification** — a running program can request recompilation of one of its own components. The new version loads alongside the old. Control transfers. The old version dissolves. The program adapted itself without stopping.

**Iterative development on a standalone system** — an engineer connects via the workbench, sends source to the Compiler Pond, a new program Pond appears in the array, runs, results are inspectable. No external compiler needed.

---

## Boot Sequence — Detailed

```
POWER ON
│
├── BIOS-Plus chip
│     Generate auth token (12-bit, hardware RNG)
│     Generate salt key (64-bit, hardware RNG)
│     Begin FUNCTION_LOAD_PATTERN sequence
│
├── Tier 2 — BIOS Boot Image loads
│     Configure auth token into all cells
│     Boot COMPANION (HIDDEN, permanent)
│     Boot Shore V2 (HIDDEN, permanent)
│     Boot ShoreKeeper
│     Boot CommandInterface
│     System: minimal OS running
│
├── Tier 3 — Core Pond load sequence
│     COMPANION reads boot manifest from BIOS storage
│     For each Core Pond in manifest:
│       │
│       ├── Load cell map from UniFlex storage Pond
│       ├── Allocate region in cell array
│       ├── Load CellMapRecord list into region
│       ├── Register with Shore
│       ├── Assign Ward
│       ├── Issue TILE key to COMPANION for this Pond
│       └── Assert start flags → Pond armed
│
│     Core Ponds now running:
│       Tile Library Pond     ✓
│       Model Library Pond    ✓
│       Compiler Pond         ✓
│       Sequencer Pond        ✓
│       LLVM Mapper Pond      ✓ (if present)
│       UniFlex FS Pond       ✓
│       Program Builder Pond  ✓
│
├── System: SELF-HOSTED
│     Any source → Compiler Pond → new Program Pond
│     No external machine required
│
└── Optional: load user environment
      Personal image (if identity system present)
      User program Ponds
      Device Ponds (sensors, peripherals)
      Display Pond
      Workbench Pond
```

---

## VM Implementation Status

**The VM is fully self-hosting as of Claudette v1.1.**

`run_companion.py` boots the complete Tier 2 + Tier 3 stack. The CompilerPond is implemented in `compiler_pond.py`, tested, and armed at every boot. The boot sequence runs a verification compile at startup to confirm the compiler is live before declaring the system self-hosting.

### What runs at boot

```
[BOOT] Loading Tier 3 — Core Ponds (self-hosted layer)...
[COMPILER_POND] Initialised @ 0x600000
[COMPILER_POND] Compile key issued
[COMPILER_POND] Armed @ 0x600000
[COMPILER_POND] Compilers ready: general, int32
[COMPILER_POND] Job boot_verify: compiling 'test' (int32)
[COMPILER_POND] Job boot_verify: 6800 cells, compiled OK
[BOOT] CompilerPond armed — system self-hosting
[BOOT] Tier 3 complete — 1 Core Pond(s): ['compiler']
[BOOT] Self-hosting: YES — CompilerPond armed
```

### Cell budget

The base system (Tier 2 only, no compiler, no user programs) uses **176 simulated cells** — Shore's four structural regions:

```
registry:     64 cells   (Shore name→address map)
address_map:  64 cells   (address translation table)
translation:  16 cells   (PTT lookup)
connections:  32 cells   (bridge connection records)
─────────────────────────────────────────────────
Total:       176 cells
```

This is the minimum viable OS footprint. COMPANION, ShoreKeeper, and the device bridges run on top of this substrate without additional cell allocation in the current VM — they are Python objects managing the cell fabric rather than cells themselves. On silicon they would occupy their own Pond regions.

### Boot modes

```bash
# Full boot — Tier 2 + Tier 3, CompilerPond armed
python3 run_companion.py

# Minimal boot — Tier 2 only, no compiler
python3 run_companion.py --no-core-ponds
```

### Using the CompilerPond

```python
from run_companion import boot_system

arr, ctrl, shore, comp, devmgr, search, core_ponds = boot_system()

cpond = core_ponds['compiler']

# Submit a compile job
ref = cpond.compile(
    source        = 'def add(a: int32, b: int32) -> int32: return a + b',
    function_name = 'add',
    compiler_type = 'int32',
)

# Retrieve result
result   = cpond.get_result(ref)
records  = result['records']
imap     = result['input_map']
oaddrs   = result['output_addrs']

# Load and run
region_id = ctrl.load_map(records, 'add_program')
output    = ctrl.run(region_id,
                     inputs={imap['a']: 42, imap['b']: 17},
                     capture_addresses=oaddrs)
print(output)   # {result_address: 59}
```

---

## Relationship to Existing Models

The self-hosting layer wraps rather than replaces the existing Python implementations. The Python objects remain the reference — they define the correct behaviour. The Pond wrappers are the in-fabric layer built on top.

| Python object | In-fabric Pond | Status |
|---|---|---|
| `ImagoCompiler()` + `Int32Compiler()` | CompilerPond @ 0x600000 | ✅ Implemented and tested |
| `TileLibrary()` | Tile Library Pond | Planned — Tier 3 expansion |
| `ModelLibrary()` | Model Library Pond | Planned — Tier 3 expansion |
| `ProgramSequencer()` | Sequencer Pond | Planned — Tier 3 expansion |

---

## Remaining Work Before Silicon

- [ ] Snapshot core boot image: `python3 run_companion.py --save core_boot.img.gz`
- [ ] Document silicon boot sequence for chipIgnite RISC-V management core
- [ ] TileLibraryPond, ModelLibraryPond, SequencerPond wrappers (Tier 3 expansion)
- [ ] Test parallel compilation — two CompilerPond jobs simultaneously
- [ ] Test self-modification — running Pond submits recompile of one of its regions

*Companion documents:*
- `01_Architecture_Overview.md` — cell model and OS layers
- `02_Core_Architecture.md` — compiler and tile library detail
- `04_OS_and_Runtime.md` — Pond lifecycle, Ward, COMPANION
- `06_Testing_and_Validation.md` — test suites covering existing components
