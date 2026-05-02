# Imago UniCell — Architecture Overview
## Claudette v1.1

---

## Origin and Design Philosophy

The Imago UniCell project began with a single constraint: every logic function must be built from NOR gates. NOR is universal — any Boolean function can be expressed in NOR alone. The question was whether a practical computing architecture could emerge from that constraint rather than fighting it.

The answer is yes, but the architecture it produces is unlike conventional processors in almost every respect. There is no instruction fetch, no decode pipeline, no program counter, and no separation between compute and memory. Instead, computation is the wiring — a network of cells where data flows through the network and the correct result emerges at the output address after a known number of clock ticks.

---

## The Fundamental Insight

**Cells evaluate themselves.**

A conventional processor fetches an instruction, decodes it, routes operands to an ALU, and writes a result. Every operation is orchestrated by a central sequencer. Claudette has no sequencer.

Each cell knows three things:
- Its gate topology (what NOR operation it performs)
- Its input address (where to listen on the bus)
- Its output address (where to write its result)

When data arrives at its input address, the cell fires, computes, and writes to its output address. No instruction needed. No decoder. No program counter. The cell IS the instruction — permanently wired.

Programs are not sequences of instructions. They are **networks of cells**. Compiling a function means constructing a cell network where data flows through it and the correct result emerges at the output address after a known pipeline depth.

```
Conventional processor:
  fetch → decode → execute → writeback
  (sequential, one operation per cycle)

Claudette:
  all armed cells evaluate simultaneously, every tick
  (massively parallel, O(armed cells) per tick)
```

**Depth, not clock speed.** The pipeline depth of any cell network is a structural property of its wiring — the exact number of ticks from input to output, known at compile time, invariant across runs. This is the governing metric for all timing, composition, and correctness in the architecture.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CLAUDETTE v1.1 ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  HYPERCOMPANION  (cross-card policy authority)               │    │
│  └──────────────────────────────┬──────────────────────────────┘    │
│                                 │                                     │
│  ┌──────────────────────────────▼──────────────────────────────┐    │
│  │  HYPERSHORE  (global registry, master card)                  │    │
│  └──────┬───────────────────────────────────────────┬──────────┘    │
│         │ card A                                     │ card B        │
│  ┌──────▼──────────────────────────────────────┐    │               │
│  │  SHOREKEEPER  (per-card boundary authority)  │    │               │
│  │    aggregates Ward heartbeats                │    │               │
│  │    validates cross-card traffic              │    │               │
│  └──────┬───────────────────────────────────────┘    │               │
│         │                                             │               │
│  ┌──────▼──────────────────────────────────────┐    │               │
│  │  SHORE V2  (card registry — HIDDEN Pond)     │    │               │
│  │    ShoreTile: registry stored in cells       │    │               │
│  │    scope: LOCAL / SHORE / EXTENDED           │    │               │
│  │    v1.1: directory + fallback only           │    │               │
│  └──────┬───────────────────────────────────────┘    │               │
│         │                                             │               │
│  ┌──────▼───────────────────┐  ┌────────────────┐   │               │
│  │  COMPANION  (OS anchor)  │  │  POND (n)       │   │               │
│  │    permanent, HIDDEN     │  │  ┌────────────┐ │   │               │
│  │    rule engine           │  │  │  BRIDGE IN  │ │   │               │
│  │    key issuance          │  │  ├────────────┤ │   │               │
│  └──────────────────────────┘  │  │  CELLS ×N  │ │   │               │
│                                │  ├────────────┤ │   │               │
│  ┌─────────────────────────┐   │  │  BRIDGE OUT│ │   │               │
│  │  WARD  (health monitor) │◄──┤  └────────────┘ │   │               │
│  │    emission tracking    │   │  PTT (address   │   │               │
│  │    thermal monitoring   │   │  translation +  │   │               │
│  │    dissolve contracts   │   │  health monitor)│   │               │
│  └─────────────────────────┘   └────────────────┘   │               │
│                                                       │               │
│  ┌──────────────────────────────────────────────┐   │               │
│  │  UNICELL ARRAY  (NOR gate fabric)             │   │               │
│  │    bus: shared dict {address → (value, tick)} │   │               │
│  │    cells fire in parallel each tick           │   │               │
│  │    _armed set = currently evaluating cells    │   │               │
│  └──────────────────────────────────────────────┘   │               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Cell Register Layout — 192 bits + 1 dedicated line

```
gate_state        32 bits   NOR topology (bits 0–8), mode flags (bits 9–31)
input_address     64 bits   Full 64-bit bus address this cell listens to
                            Lower 32 used for local/intra-Pond operation
                            Full 64 available when reaching beyond the Pond
output_address    64 bits   Full 64-bit forwarding address
                            Lower 32 for local operation
                            Bridge cells use full 64 to route natively
data              32 bits   NOR compute register
─────────────────────────
Register file:   192 bits

start flag         1 bit    DEDICATED HARDWARE LINE — not on any bus
                            Armed = participates each tick
                            Disarmed = present but silent
─────────────────────────
Total per cell:  193 bits
```

The start flag is the only signal that crosses from controller space into cell space outside the three buses. That physical separation is what enables four distinct architectural mechanisms from one line: configuration gating, branch routing, checkpoint freeze, and debug pause.

---

## The Wired-OR Property — Precisely Stated

When two cells write to the same bus address in the same tick their values are OR'd together. This is not a conflict — it is the mechanism for building multi-input operations from single-input cells.

**Precise statement:** two NOT cells sharing an output address produce `NOT(a) OR NOT(b) = NAND(a,b)` — NAND, not NOR, by De Morgan's law.

True NOR is implemented using the `GS_NOR` internal gate topology flag (bit 2) within a single cell, which applies the full two-input NOR computation internally before writing to the bus. Alternatively: NAND output fed into a NOT cell in the next stage produces NOR. Both NAND and NOR are universally complete — nothing is lost. The wired-OR mechanism is how multi-input operations are composed from single-input cells.

---

## 64-Bit Addressing — Native and Contextual

Both address registers are 64 bits wide in v1.1. The cell uses them contextually:

- **Local / intra-Pond** — lower 32 bits are sufficient. All PTT-relative addresses within a Pond fit in 32 bits. No overhead, no Shore involvement.
- **Cross-Pond / cross-card** — full 64 bits. A bridge cell carries the full 64-bit destination address natively in its output_address register. Cross-card forwarding is a single cell firing — Shore is completely out of the routing path.

Shore V2 is a directory and fallback service in v1.1, not a routing component. You consult it once to discover an address; after that the bridge routes directly.

---

## Key Concepts

### UniCell

The fundamental unit. A single NOR-gate cell with a 192-bit register file plus a dedicated start flag line. The cell has one input address and one output address. It is inherently unidirectional. Multiple cells can write to the same address — the bus combines them via wired-OR (producing NAND when two NOT cells share an address, true NOR from the GS_NOR topology flag).

### Tile

A pre-designed network of cells implementing one named operation — INT32_ADD_CLA, INT32_AND, COUNTER_RIPPLE_8, etc. The tile library contains 40 tiles. Every tile has a fixed pipeline depth — a structural property of its wiring, known at compile time. Tiles are the vocabulary of the compiler.

### Two Compiler Models

The compiler chooses between two execution models:
- **Spatial map** — full cell-by-cell wiring, every operation gets its own cells, all independent operations fire simultaneously. Best for dense computation.
- **Sequencer** — a resource manifest pre-allocates the maximum number of simultaneously needed primitives; a command table drives them. Decision trees become lists. No dead cells from untaken branches.

### Cell as Memory

There is no separate memory subsystem. Cells hold state directly:
- `GS_LATCH` (bit 11) — holds last result, re-emits every tick
- `storage_mode` — persists a value until updated by new input
- `GS_LOOP_BACK` (bit 16) — feeds output back to input: in-situ register

### Pond

The fundamental OS resource unit. A named, bounded pool of cells with bridge-gated access. Every Pond has at minimum two bridges: INBOUND and OUTBOUND. Data can only enter or leave through bridges. The bridge IS the security boundary — a single cell enforcing the mask check.

### PTT (Pond Translation Table)

Sits at offset 0 of every Pond. Serves three functions simultaneously: maps logical 11-bit indices to absolute cell addresses (address translation), provides a complete Pond manifest for Cast/Ripple discovery without array scanning, and gives the Ward a status column to watch for anomalies. One structure, three jobs.

### Ward

The health monitor for a single Pond. Tracks emission history, thermal load, and lifecycle state. State machine: IDLE → HEALTHY → DEGRADED → STALLED/SILENT → ISOLATED. Also manages dissolve contracts — programmable lifecycle conditions stored in the PTT (five condition types, three action types). The Ward does not poll; problems surface themselves.

### Shore

The card-level registry. HIDDEN Pond. Maps object names to addresses. Tracks connections between Ponds. Internal storage (ShoreTile) is itself implemented as a resizable hash table in the cell array — the registry that tracks cell resources is stored in cells. In v1.1, Shore is a directory and fallback, not a routing component.

### ShoreKeeper

The per-card boundary authority. Aggregates all Ward heartbeats into a single summary packet sent to HyperShore. Validates all cross-card traffic (auth + mask at both ends). Maps physical cooling channels to thermal zones.

### COMPANION

The OS anchor. Permanent, HIDDEN, single instance per card. Runs the rule engine: restart a stalled Pond, isolate a compromised one, migrate a thermally overloaded one. Issues and revokes auth keys. The only entity with authority to restart, isolate, or migrate Ponds.

### Discovery — Cast, PTT, Shore, Bridge

Finding and using any resource follows a single coherent path:
1. **Cast** (Pebble, Ripple, or Skipping Stone) — discovers Ponds visible to the caller's process_mask
2. **PTT manifest** from the RippleResult — complete inventory of every tile, bridge, and storage cell
3. **Shore** — resolves scope-qualified names to addresses when needed
4. **Bridge** — routes directly using its native 64-bit output address register

> Cast to discover. PTT to inventory. Shore to resolve. Bridge to route.

---

## How the Levels Fit Together

```
UniCell:        fires when data arrives at its input address
Tile:           a named group of cells implementing one operation
Program:        a set of tile instances wired together (spatial or sequencer)
Pond:           a bounded region of cells with bridge-gated, mask-checked access
PTT:            address translation + discovery manifest + Ward health index
Ward:           watches one Pond's health, thermal state, and lifecycle
Shore:          the card's address book — directory and fallback only in v1.1
ShoreKeeper:    aggregates Ward states, validates cross-card traffic
HyperShore:     the multi-card registry on the master card
COMPANION:      the OS decision-maker — responds to Ward escalations
```

Each level only knows about its own scope. A cell does not know it is in a Pond. A Pond does not know it is on a card. A ShoreKeeper does not know the contents of the Ponds it monitors — only their Ward states. Information flows upward only as aggregated summaries. This is what makes the architecture scale.

---

## Development History

| Phase | What was built | Key insight |
|-------|---------------|-------------|
| 1 — Cell & Array | UniCell, bus, armed set | One input address; wired-OR combines signals |
| 2 — Tile Library | NORBuilder, 40 tiles | pad_to_depth solves timing; CLA gives 3× speedup over ripple carry |
| 3 — Compiler | Python AST → cells | Programs are cell networks; depth is compile-time known |
| 4 — OS: Claudette v1.0 | Pond, Ward, Shore, COMPANION | Mask check makes absent = nonexistent; bridge IS the boundary |
| 5 — VM Image & Migration | Snapshot, FREEZE_BODY, command bus | Three-bus protocol with auth protects config from user code |
| 6 — GPU, Program Image, Sequencer | GPUArrayBackend, command table, resource manifest | Decision trees become lists; no dead cells |
| 7 — LLVM | Frontend + IR mapper | LLVM IR lowers to tiles via the same path as Python compiler |
| 8 — Pipeline Queue | Reference shift register, out-of-order delivery | Depth known → reference travels alongside data for free |
| v1.1 — 64-bit addressing | Both address registers widened to 64 bits | Bridge cells route natively; Shore becomes directory only |

---

## Vision and Scaling

```
First silicon (SKY130 130nm, chipIgnite):  112,500 cells  ($14,950, 100 chips)
Single die (3nm, 1 layer):                 22.5M cells,   343 blocks
PCIe card (56 dies/face):                  1.26B cells/side
12-layer 3D stack:                         30.24B cells/card
Multi-card:                                federation via ShoreKeeper / HyperShore
```

The MIDAS chip (Modular Imago Die Architecture System) is the planned silicon implementation — a 1cm² 3nm die in a 15×15 ball BGA package. The chipIgnite SKY130 route is available today — $14,950 for 100 QFN-packaged chips, with a RISC-V management core that maps naturally to the CommandInterface role.

---

*See companion documents:*
- `02_Core_Architecture.md` — cell layout, tiles, compiler, command bus
- `03_Security_Model.md` — 9-layer security, sandboxing, masks
- `04_OS_and_Runtime.md` — Claudette OS, Ponds, migration
- `05_Hardware_and_Scaling.md` — MIDAS chip, PCIe card, BGA
- `06_Testing_and_Validation.md` — test suites, results
- `07_CLI_and_User_Guide.md` — workbench, devices, commands
- `00_PRIMER.md` — quick start, worked examples, installation
