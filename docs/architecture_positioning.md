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

---

## Silicon Scaling — UniCell on 1cm² Die

Projections for a native UniCell die at various process nodes.
All figures assume sparse/idle workloads at 50MHz baseline.

| Process Node | Max UniCells (practical) | Power per cell (µW) | Total power (W sparse) |
|-------------|--------------------------|---------------------|------------------------|
| 130nm       | ~40,000                  | 4–12                | 0.14 – 0.54            |
| 65nm        | ~100,000                 | 1.5–5               | 0.14 – 0.65            |
| 28nm        | ~280,000                 | 0.6–2               | 0.17 – 0.78            |
| 7nm         | ~700,000                 | 0.2–0.8             | 0.18 – 0.96            |
| 5nm         | ~900,000                 | 0.15–0.5            | 0.20 – 0.85            |
| 3nm         | ~1.2 million             | 0.1–0.4             | 0.20 – 1.12            |
| 3nm 4L 3D   | ~5 million               | 0.12–0.5            | 0.96 – 5.5             |

*Source: Grok analysis, April 2026. PCIe card (4-layer 3D): ~20M cells across 4 dies.*

### The throughput reality

50MHz understates actual throughput because all armed cells fire simultaneously.
This is not instructions-per-second — it is parallel cell firings per tick.

```
130nm die, 50MHz:   50MHz × 40,000 cells  =   2 trillion ops/second
130nm die, 200MHz:  200MHz × 40,000 cells =   8 trillion ops/second
3nm 3D PCIe card:   50MHz × 20,000,000   =   1 quadrillion ops/second
```

In a conventional processor at 50MHz: 50 million instructions per second.
Sequential. One result per tick.

In UniCell at 50MHz: every armed cell fires every tick simultaneously.
Idle cells consume near-zero power. Energy scales with actual computation,
not peak capacity. This is why the power numbers are so low.

The correct metric is **simultaneous cell firings per second** — a measure
that conventional architectures cannot meaningfully express.

Even the iCEBreaker at 12MHz with 64 cells:
```
12MHz × 64 cells = 768 million parallel cell operations per tick
```

### The pathway to silicon

Each step is a proof point for the next:

```
iCEBreaker (now)     ~64 cells     Prove v2 two-input architecture in silicon
Small FPGA cluster   ~1,000 cells  Prove pond model at scale
Tiny Tapeout 130nm   ~40,000 cells First native silicon (group tapeout, ~£300/tile)
Custom 28nm          ~280,000 cells Commercial pilot
3nm 3D PCIe card     ~20M cells    Production
```

Tiny Tapeout (tinytapeout.com) runs group tapeouts on SKY130 (130nm open PDK).
A small UniCell array would fit comfortably in their tile size. This is the
accessible bridge between FPGA proof and custom silicon.

---

## Use Case Scenarios

The following are starting points for community exploration. Each scenario
runs on the VM today. Hardware targets are noted for when silicon is available.

*These are stubs — contributions welcome.*

### 1. Spatial operating system (the founding use case)
Everything is a pond. Files, processes, peripherals, network connections —
all managed as ponds with Shore table entries, Ward health monitoring,
bridge access control, and live migration. The same OS runs on VM, FPGA,
and ASIC without modification.

**VM status:** Working. Shore, Ward, ShoreKeeper, Companion all implemented.
**Target hardware:** iCEBreaker (proof), 3nm card (production OS workload).

### 2. Neural simulation (LIF neuron clusters)
Leaky integrate-and-fire neurons as UniCell ponds. ~6-8 cells per neuron in v2.
A neural pond sits alongside OS ponds — same Shore table, same migration,
same access control. The substrate does not distinguish compute types.

```
iCEBreaker:     6-8 neurons
Mid FPGA:       800-1000 neurons
3nm 3D card:    60-80 million neurons
```

**VM status:** Architecture defined. Cell layout documented. Implementation pending.
**Reference:** docs/lif_neuron_reference.v (v1 Verilog), docs/architecture_positioning.md

### 3. Cellular automata / spatial simulation
Conway's Game of Life, reaction-diffusion systems, physical simulation.
Each cell maps naturally to a UniCell with neighbourhood inputs via the bus.
Massive arrays run in parallel — no sequential scan, every cell updates simultaneously.

**VM status:** Straightforward to implement. Community contribution opportunity.
**Potential:** Real-time physics simulation at scales impossible on conventional hardware.

### 4. Cryptographic primitives
AES, SHA, elliptic curve operations implemented as cell maps.
The NOR-universal cell fabric can implement any boolean function.
Pipelined at cell depth — throughput scales linearly with cell count.

**VM status:** Compiler can generate cell maps from Python implementations.
**Target:** Hardware security module use case.

### 5. Signal processing / DSP
FIR/IIR filters, FFT, convolution. Fixed-point arithmetic via Kogge-Stone
adder tiles (548 cells, depth 12). Parallel filter banks with one pond per channel.

**VM status:** INT32 arithmetic tiles available. Pipeline depth known.
**Potential:** Software-defined radio, audio processing, sensor fusion.

### 6. Graph algorithms
Breadth-first search, shortest path, PageRank. The pond model maps naturally
to graph partitioning — each pond handles a subgraph, bridges handle edges
between partitions. Migration moves hot subgraphs to available compute.

**VM status:** Architectural fit is strong. Implementation is a community opportunity.

### 7. Database / search acceleration
The collection search heuristic (Shore table → collection index → pond query)
is already implemented. Extension to full relational algebra or graph database
operations is a natural next step.

**VM status:** Collection search working. Full DB acceleration is future work.

### 8. Machine learning inference
Once neural simulation is proven, inference on trained models follows.
Weights as pond state, activations as bus values, layers as pond pipelines.
Not training (that needs backprop) but inference maps well to the architecture.

**VM status:** Requires neural pond implementation first.
**Potential:** Ultra-low-power edge inference. No GPU required.

### 9. Adaptive / liquid computing
Runtime reconfiguration of gate_state allows cells to adapt their function
based on feedback. The v2 gate tree has 12 meaningful configurations —
a much richer adaptation space than v1's effective 2.

**VM status:** Runtime reconfiguration is architecturally supported.
Reference Verilog available (docs/lif_neuron_reference.v).
Full implementation pending review and port to v2.

### 10. Emergent computation
With millions of cells running simple local rules, complex global behaviour
emerges. Ant colony optimisation, genetic algorithms, swarm intelligence —
all expressible as cell programs with no central coordinator.

**VM status:** The substrate supports it. Use cases are open research questions.
**This is the frontier — the community defines what goes here.**

---

*Contributions: raise a GitHub issue or submit a PR adding a scenario.*
*The VM runs today. No hardware needed to start.*
