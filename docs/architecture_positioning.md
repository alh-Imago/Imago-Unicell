# UniCell Architecture Positioning

## What UniCell Is

A universal reconfigurable NOR cell fabric. Each UniCell is a configurable
9-gate NOR tree that can become any logic function -- AND, OR, XOR, XNOR,
NOT, NOR, NAND -- in a single cell, single tick. Cells are organised into
ponds, connected via a wired-OR bus, managed by an OS layer (Shore, Ward,
ShoreKeeper, Companion).

The cell is the primitive. Everything else is built from cells.

## The Abstraction Stack

```
User programs (.icm files)
        ↓
Compiler (Python → cell records)
        ↓
Controller (load, start, run)
        ↓
Bus interface
        ↓
VM (unicell_array_v2.py)    OR    FPGA / ASIC (unicell_v2.v)
```

The same .icm program file runs unchanged on any target in the family.
Programs written today run on silicon that does not exist yet.

## Target Hardware Family

```
VM (laptop)         unlimited cells    software speed    no hardware needed
iCEBreaker FPGA     ~64 cells          real silicon      ~£40
Larger FPGA         thousands of cells real silicon
Custom ASIC 3nm 3D  ~500M cells        50MHz baseline    PCIe card
```

## Comparison with Neuromorphic Hardware (2026)

UniCell is not a neuromorphic chip. It is a universal reconfigurable fabric
that can run neural simulations as one workload among many -- simultaneously
with OS primitives, file search, and bridge routing in other ponds.

| Metric | UniCell (3nm 4L 3D PCIe card) | Intel Loihi 2 | IBM TrueNorth | BrainChip Akida |
|--------|-------------------------------|---------------|---------------|-----------------|
| Compute elements | ~500M UniCells (configurable NOR cells with state/addressing/loop) | ~1M neurons (Loihi 2); 1.15B in Hala Point | ~1M neurons, 256M synapses | ~1.2M neurons, up to 10B synapses |
| Connectivity | Shared wired-OR bus + per-cell addressing + GS_LOOP feedback | 120M synapses per chip | 256M synapses | High (event-driven) |
| Clock / style | 50MHz synchronous + dual-edge; data-driven firing | Asynchronous event-driven | Asynchronous / digital | Event-driven hybrid |
| Power (sparse) | 10–50W average per card | <1W to ~2.5W per chip | ~70mW | <1W (0.3–1W typical) |
| Energy efficiency | Extremely high in sparse regimes (near-zero when idle) | 15–100+ TOPS/W | Very high (~26 GSOPS at 65mW) | 100–500× lower than conventional AI |
| Best for | Massive parallel fine-grained logic, spatial/emergent simulation, reconfigurable pond computation, neural simulation as one workload | Spiking neural nets, sensorimotor control, low-latency edge AI | Pattern recognition, vision | Edge AI inference |

### Key differences

**Neuromorphic chips are fixed-function neural hardware.**
TrueNorth, Loihi, Akida are optimised specifically for spiking neural
networks. Excellent at that one thing.

**UniCell is universal reconfigurable fabric.**
The same card running LIF neurons in one pond is simultaneously running
the OS in another pond, handling file search in a third, routing bridge
traffic between them. No neuromorphic chip does this.

**Granularity is completely different.**
500M UniCells vs 1M neurons (Loihi 2) -- but UniCells are not neurons.
They are NOR gates that can become neurons, adders, comparators, OS
primitives, or anything else. The comparison understates the difference.

**The wired-OR bus is free in silicon.**
Multiple drivers on the same wire is just physics. No arbitration logic.
This is what makes massive sparse connectivity cheap.

## Neural Simulation in UniCell

A Leaky Integrate-and-Fire (LIF) neuron in a UniCell pond:

```
Cell A: membrane latch   (GS_LATCH_IN | LOOP_MODE) -- holds V
Cell B: leak             (GS_NOT_A | LOOP_MODE)    -- approximates V >> shift
Cell C: integrate        (GS_OR)                   -- V + synaptic input
Cell D: threshold compare (XNOR + AND mask)        -- V >= threshold
Cell E: spike output     (GS_ONE_SHOT)             -- fires once on threshold
Cell F: refractory latch                           -- blocks re-fire
```

~6-8 cells per neuron in v2 (was ~40-50 in v1 due to multi-cell logic chains).

On iCEBreaker (~64 cells): 6-8 LIF neurons.
On 10,000 cell array:      ~800-1000 neurons.
On 500M cell ASIC:         ~60-80 million neurons.

Same compiler, same .icm format, same OS layer managing the neural pond
alongside everything else.

## What Makes UniCell Different

The same substrate runs OS primitives and neural simulations simultaneously.
That is not something available from any conventional or neuromorphic
architecture.

A neural pond is just another pond:
- Listed in the Shore table like any other resource
- Monitored by Ward for health
- Migratable (freeze/copy/move/unfreeze) like any other pond
- Searchable via collection index (type:neural_pond)
- Accessible via the same bridge/view_mask access control

The architecture does not distinguish between compute types.
Everything is cells. Everything is ponds.

---
*Reference: Comparison data from Grok analysis, April 2026.*
*Neuromorphic figures: Intel Loihi 2, IBM TrueNorth/NorthPole, BrainChip Akida 2nd gen.*
*UniCell ASIC projections: 3nm 4-layer 3D stacking, PCIe card form factor.*
