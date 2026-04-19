# Imago UniCell — Standalone Boot Sequence and Self-Hosting
## Claudette v1.1

---

## Overview

A standalone UniCell system — one with no external host CPU, no development machine, no external compiler — must be able to compile, modify, and extend itself entirely from within the fabric. This document specifies the boot sequence that achieves that, the core Ponds that must be present for self-hosted operation, and the path from the current VM implementation to a fully self-hosted boot image.

This document will expand as the boot image is developed and tested in the VM.

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

## VM Implementation Path

The current VM (`run_companion.py`) implements Tier 2 completely. The Tier 3 Core Ponds exist as Python modules but are not yet wrapped as persistent Ponds with bridges.

### Phase 1 — Compiler Pond wrapper (immediate)

Wrap `compiler.py` and `compiler_int32.py` as a persistent Pond:

```python
from companion import Companion
from compiler import ImagoCompiler
from compiler_int32 import Int32Compiler
from pond import Pond
from pond_types import LIBRARY, HIDDEN

class CompilerPond:
    """
    Wraps the ImagoCompiler as a persistent LIBRARY Pond.
    Accepts source via SOURCE_IN bridge.
    Returns CellMapRecord list via MAP_OUT bridge.
    Always armed. Always ready.
    """
    def __init__(self, array, shore, companion):
        self.pond = Pond(
            name         = 'compiler',
            array        = array,
            owner_id     = 'companion',
            pond_type    = LIBRARY,
            base_address = 0x00600000,
            region_size  = 0x10000,
        )
        self._compiler    = ImagoCompiler()
        self._int32       = Int32Compiler()
        self._jobs        = {}   # job_ref → result

    def compile(self, source: str, function_name: str,
                job_ref: str = None) -> str:
        """
        Submit a compile job. Returns job_ref.
        Result available via get_result(job_ref).
        """
        import uuid
        ref = job_ref or str(uuid.uuid4())[:8]
        # Compile — in VM this is synchronous
        # In silicon this would be a pipeline job
        records, graph, imap, oaddrs = self._compiler.compile_function(
            source, function_name,
            list(self._compiler._last_params or [])
        )
        self._jobs[ref] = {
            'records':  records,
            'input_map': imap,
            'output_addrs': oaddrs,
            'graph':    graph,
        }
        return ref

    def get_result(self, job_ref: str) -> dict:
        return self._jobs.get(job_ref)
```

### Phase 2 — Boot manifest

Add a boot manifest to `run_companion.py` that loads the Compiler Pond, Tile Library Pond, and Model Library Pond as persistent Ponds after the Tier 2 boot:

```python
def boot_core_ponds(arr, ctrl, shore, companion):
    """
    Load Tier 3 core Ponds — the self-hosted layer.
    Called after Tier 2 boot completes.
    """
    from compiler_pond import CompilerPond
    from sequencer_pond import SequencerPond   # to be written

    compiler_pond = CompilerPond(arr, shore, companion)
    shore.register(ShoreEntry(
        'compiler', 'LIBRARY', 0x00600000, 0x00600000,
        ward_state='HEALTHY'
    ))
    print("[BOOT] Compiler Pond armed")

    # ... tile library pond, model library pond, etc.

    print("[BOOT] Self-hosted layer ready")
    print("[BOOT] System fully self-hosting")
    return compiler_pond
```

### Phase 3 — Boot image serialisation

Once all Core Ponds are implemented and tested, snapshot the fully booted system as a VM image:

```python
python3 run_companion.py --boot-full --save core_boot.img.gz
```

This image is the Tier 3 boot image. A fresh system loads it at startup and is immediately self-hosted. No Python host needed — only the VM layer that simulates the cell array.

---

## Relationship to Existing Models

The self-hosting model extends rather than replaces the existing architecture:

| Current | Self-Hosted Extension |
|---|---|
| `TileLibrary()` Python object | Tile Library Pond — persistent, in fabric |
| `ModelLibrary()` Python object | Model Library Pond — persistent, in fabric |
| `ImagoCompiler()` Python object | Compiler Pond — persistent, always armed |
| `ProgramSequencer()` Python object | Sequencer Pond — persistent, always armed |
| `run_companion.py` boot | Tier 2 + Tier 3 boot sequence |
| VM image save/load | Core boot image + user environment image |

The existing Python implementations remain as the reference — they define the correct behaviour. The Pond wrappers are the self-hosted layer built on top of them.

---

## Next Steps

- [ ] Implement CompilerPond wrapper
- [ ] Implement SequencerPond wrapper
- [ ] Implement TileLibraryPond wrapper
- [ ] Implement ModelLibraryPond wrapper
- [ ] Add boot_core_ponds() to run_companion.py
- [ ] Test: submit source to CompilerPond, load result, run new Pond
- [ ] Test: parallel compilation — two variants simultaneously
- [ ] Test: self-modification — running Pond recompiles one of its components
- [ ] Snapshot core boot image
- [ ] Document silicon boot sequence for chipIgnite implementation

---

*This document will expand as each phase is implemented and tested.*

*Companion documents:*
- `01_Architecture_Overview.md` — cell model and OS layers
- `02_Core_Architecture.md` — compiler and tile library detail
- `04_OS_and_Runtime.md` — Pond lifecycle, Ward, COMPANION
- `06_Testing_and_Validation.md` — test suites covering existing components
