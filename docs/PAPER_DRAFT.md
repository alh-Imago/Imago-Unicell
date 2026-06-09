# Imago UniCell: A NOR-Universal Reconfigurable Fabric with Two-Arrival Firing and Wired-OR Arbitration

**Alan Littleover**  
Imago UniCell Project  
`github.com/alh-Imago/Imago-Unicell`

*Draft — June 2026*

---

## Abstract

We describe Imago UniCell, a parallel compute fabric built from a single universal cell type. Each cell implements any of twelve Boolean functions via a NOR gate tree configured by a 32-bit `gate_state` word. Cells communicate through a shared wired-OR bus where physics performs arbitration without software overhead. Computation proceeds through a two-arrival firing model: the first bus arrival stores into the cell's A register; the second triggers the gate tree. The fabric is reconfigurable at runtime by writing new `gate_state` values over the same bus.

We present the architecture, the compilation pipeline from Python source to cell maps, silicon validation results on iCEBreaker (iCE40UP5K), and a browser-accessible compute server enabling network-transparent access to the fabric. The tile library provides 86 pre-verified building blocks including a 17-tile MathTrix Internal Float (MIF) family for parallel stencil computation. All code and hardware descriptions are open source.

---

## 1. Introduction

Conventional parallel hardware — multi-core CPUs, GPUs, FPGAs — separates computation from communication. Arithmetic units perform operations; memory buses and interconnect networks move data between them. The fundamental bottleneck is this separation: as compute density increases, data movement cost dominates.

UniCell takes a different approach: computation and communication are the same physical event. When a cell fires, it writes its output to the shared bus. Every other cell whose input address matches that bus address simultaneously receives the value. There is no routing, no arbitration, no memory hierarchy. The bus IS the interconnect and the computation IS the communication.

This is enabled by three architectural decisions that emerged from a single constraint: every logic function must be expressible as one cell, one cycle, from NOR gates.

**NOR universality.** NOR gates are functionally complete. Any Boolean function can be expressed as a tree of NOR gates. We encode the specific NOR topology for the desired function in a 10-bit field of the 32-bit `gate_state` word. This gives twelve standard functions (AND, OR, XOR, NOT, NAND, XNOR, NOR, PASS, PASS_B and variants) without any instruction decoder.

**Wired-OR bus.** When multiple cells write to the same bus address simultaneously, the electrical result is the bitwise OR of all values. This performs fan-in aggregation without software overhead. For binary values, wired-OR is equivalent to NOR-then-invert — directly useful for the gate tree inputs. At scale, DDR is the bottleneck, not the fabric; cell registers are faster than CPU L1 cache with zero contention.

**Two-arrival firing.** Each cell has two input channels, A and B. The first bus arrival stores into the A register and sets an armed flag; the second arrival triggers the gate tree evaluation and emits the result. This implements a natural synchronisation primitive: the cell does not fire until both its operands have arrived. No explicit synchronisation instructions are needed. The topology of the cell map encodes the data dependencies.

These three decisions together produce a substrate where programs are expressed as fabric topology rather than sequential instruction streams. The compile target is a cell map — a set of `(gate_state, input_address, output_address)` triples. The same cell map runs identically on the Python VM, on an iCEBreaker FPGA, and on any future implementation of the architecture.

---

## 2. Cell Architecture

### 2.1 The Cell

Each UniCell cell has the following state:

```
gate_state    : 32-bit configuration word
input_address : 32-bit bus address this cell listens on (B channel)
output_address: 32-bit bus address this cell writes to
a_data        : 32-bit stored value (A channel, set on first arrival)
a_arrived     : 1-bit flag (set when A has been stored)
```

On each bus cycle, the cell checks whether a value has been written to `input_address`. If `a_arrived` is False, the arriving value is stored in `a_data` and `a_arrived` is set — no output. If `a_arrived` is True, the gate tree evaluates `f(a_data, bus_value)` where `f` is determined by `gate_state[9:0]`, and the result is written to `output_address`.

The twelve standard gate functions (topology codes `0x00`–`0x24`) are:

| Code | Function | NOR expression |
|------|----------|---------------|
| `0x00` | PASS | output A unchanged |
| `0x01` | NOT_A | NOR(A, A) |
| `0x02` | NOT_B | NOR(B, B) |
| `0x07` | AND | NOR(NOR(A,A), NOR(B,B)) |
| `0x24` | OR | NOR(NOR(A,B), NOR(A,B)) |
| `0x1F` | NAND | NOR(NOR(NOR(A,A),NOR(B,B)), NOR(NOR(A,A),NOR(B,B))) |
| `0x04` | NOR | NOR(A, B) directly |
| `0x1B` | XOR | 4-NOR tree |
| `0x04` | XNOR | 5-NOR tree |
| `0x2C` | PASS_B | output B unchanged |

All functions reduce to NOR trees of depth at most 4. This is the key constraint: any cell is implementable in any NOR-based technology.

### 2.2 Mode Flags

Bits 10–31 of `gate_state` encode mode flags stored in a separate `cmd_latch` register:

| Bits | Flag | Effect |
|------|------|--------|
| 26 | `latch_in` | A register retains value after firing; cell fires on every subsequent arrival |
| 27 | `one_shot` | Cell fires once then disarms; further arrivals ignored |
| 28 | `invert_out` | Output is bitwise NOT before emission (`& 1` — single-bit inversion) |
| 29 | `loop_back` | Output fed back as next A value (implements running accumulator) |
| 30 | `preload_sel` | A value loaded at configure time from the command bus |
| 19 | `shift_in_en` | Input shifted left N nibbles before gate evaluation |
| 20 | `shift_out_en` | Output shifted right N nibbles before emission |

These flags allow single cells to implement SR latches (`latch_in`), one-shot triggers (`one_shot`), running accumulators (`loop_back`), and constant injection (`preload_sel`) without additional circuitry.

### 2.3 Preloaded-A Pattern

The `preload_sel` flag enables a compile-time optimisation. When a cell's A input is a constant (known at compile time), the constant is loaded into `a_data` during the configure transaction, and `a_arrived` is pre-set. The cell then fires on every single B arrival without waiting for a two-arrival sequence. This eliminates entire software preload sequences and reduces the cell count for constant-operand operations to zero additional cells.

The compiler uses this pattern extensively for tiling AND gates with one constant operand, building MUX selectors, and encoding comparison constants.

---

## 3. Compilation Pipeline

### 3.1 Overview

The compilation pipeline transforms Python source code into a cell map:

```
Python source
     ↓  (AST parse + type check)
IR graph (SSA, typed nodes)
     ↓  (tile placement)
Tile records (CellMapRecord list)
     ↓  (forward simulation)
Preload table (a_data values per cell)
     ↓  (controller load)
Running fabric
```

### 3.2 IR Graph

The IR graph is an SSA (Static Single Assignment) form with strict type discipline. Each node represents one operation. The INT32 compiler (`compiler_int32.py`) enforces that all values in a function are of type `int32`; type ambiguity is rejected at the compiler boundary, not deferred to runtime.

IR nodes map to one of:
- **INPUT**: an external value arriving on the bus (function parameters)
- **TILE**: a pre-built tile placed by the tile library
- **PASS**: identity relay (for depth alignment)

### 3.3 Tile Placement

Tiles are pre-verified cell networks with named input and output ports. The tile placer (`TilePlacer`) maps tile-relative template addresses to actual bus addresses in the array. Each tile placement produces a set of `CellMapRecord` triples and a preload table entry for each AND cell whose A input is known at compile time.

The tile library contains 86 tiles including:
- Integer arithmetic (INT32_ADD, INT32_SUB, INT32_MUX, comparisons, shifts)
- Floating point (FP32_ADD, FP32_MUL)
- MIF family for stencil computation (17 tiles)
- Counters, latches, signal generators

### 3.4 Forward Simulation

After placement, the compiler performs a forward simulation of the entire cell map using the known input values. This computes the `a_data` preload value for every cell in the map. At runtime, these preloaded values are loaded during the configure transaction. The fabric then executes without software-side timing coordination: cells fire as their inputs arrive, in parallel, at the rate determined by the bus cycle time.

### 3.5 MUX Selector — Resolved Timing Challenge

The if/else MUX tile (`INT32_MUX`) required careful resolution of a timing constraint. The selector signal from a comparison tile (e.g., `INT32_LT_S`, pipeline depth 16) arrives later than the data from an arithmetic tile (e.g., `INT32_SUB`, pipeline depth 12). The MUX's internal AND cells preload the selector value from the forward simulation, so the selector's runtime value is encoded as `a_data` at configure time. When data arrives from the arithmetic tile, the AND fires with the correct preloaded selector — no runtime timing coordination needed.

The challenge arose when the forward simulation was run before all IR nodes had computed their values. The fix: all zero-comparisons (`a < 0`, `a >= 0`, etc.) are now expressed as tile-space comparisons rather than IR nodes, ensuring their results are available in tile-record order during the forward simulation.

---

## 4. Silicon Validation

### 4.1 Hardware Platform

We validated the architecture on an iCEBreaker v1.0e (Lattice iCE40UP5K-SG48). The iCEBreaker was chosen for its open-source toolchain (Yosys + nextpnr-ice40 + iceprog) and documented silicon behaviour.

The Verilog implementation (`unicell_v3.v`) uses 3,780 ICESTORM_LC (71% utilisation) at 24 MHz synthesised from the internal oscillator. The UART bridge (`uart_bridge.v`) exposes the cell array to a host Python process at 115,200 baud.

The current bitstream implements 4 cells (`NUM_CELLS=4`). This limit arises from the 16-bit data bus packing in the UART bridge: each 32-bit cell value is split into two 16-bit transactions, and timing constraints at 24 MHz bound the practical cell count to 4 in this configuration. Validation of larger cell counts requires the Arria 10 GX660 (pending external programmer).

### 4.2 Validated Functionality

The `test_sanity.py` suite (31 tests) confirms the following on silicon:

| # | Test | Result |
|---|------|--------|
| 1 | Two-arrival model — fires on second arrival only | ✓ |
| 2–7 | NOT, AND, OR, XOR, PASS, NOR gate functions | ✓ |
| 8 | `latch_in` — stores first arrival, fires on every subsequent | ✓ |
| 9 | `one_shot` — fires once then disarms | ✓ |
| 10 | `invert_out` — output bitwise NOT before emission | ✓ |
| 11 | `preload_sel` — A loaded from command bus at configure time | ✓ |
| 12 | `shift_out_en` — output shifted right N nibbles | ✓ |
| 13 | `CMD_ARRAY_RESET` — authenticated system-wide reset | ✓ |
| 14–31 | Boundary values, combined modes, edge cases | ✓ |

The `shift_in_en` flag (input shift) could not be validated on the iCEBreaker due to the 16-bit data bus constraint. Validation is deferred to the Arria 10.

### 4.3 Verilog Ground Truth

The Verilog source is the ground truth for the architecture. All Python VM behaviour is derived from it, not the other way around. Key design decisions documented in `unicell_v3.v`:

- `CMD_ARRAY_RESET` is system-wide only by design. Per-cell reset would expose the physical `CELL_ID` on the bus, causing collisions. Authentication via a 16-bit token prevents accidental resets.
- The preload mechanism (`preload_sel`) writes directly to `a_data` and sets `a_arrived` in a single command transaction, eliminating the need for a separate preload bus cycle.
- `cmd_bus` bits are transient per-transaction; `cmd_latch` bits are persistent cell configuration. These are distinct registers.

---

## 5. Tile Library and MIF Format

### 5.1 Tile Library

The tile library (`fp_tiles.py`) provides pre-verified cell networks as composable building blocks. Each tile has a verified pipeline depth (exact ticks from input to output) and cell count measured from the instantiated network, not estimated. The library is the only source of tile metadata — documentation, the composer, and the compiler all read from it directly.

Selected tile specifications:

| Tile | Cells | Depth | Implementation |
|------|-------|-------|----------------|
| INT32_ADD | 482 | 10 | Kogge-Stone parallel prefix adder |
| INT32_SUB | 517 | 12 | NOT(B) + Kogge-Stone + carry-in=1 |
| INT32_LT_S | 523 | 16 | Sign XOR + unsigned compare |
| INT32_MUX | 128 | 3 | NOT(sel) + AND(sel,A) + AND(NOT(sel),B) + OR |
| FP32_ADD | 1,253 | 85 | IEEE-754 single (no denormals) |
| MIF_MUL | 3,066 | 89 | MIF multiply |
| MIF_DIV | 4,789 | 1,177 | MIF divide (Newton-Raphson) |

### 5.2 MathTrix Internal Float

MIF (MathTrix Internal Float) is a compact floating-point format designed for parallel stencil computation. Standard IEEE-754 encodes sign, exponent, and mantissa in a single 32-bit word, which requires significant unpacking circuitry for arithmetic. MIF instead stores the mantissa and exponent as separate values in a cell pair, reducing the per-operation gate count for addition and multiplication at the cost of boundary conversion overhead.

The boundary cost is paid once per grid point (at region entry and exit via `MIF_UNPACK` and `MIF_PACK`), while all stencil arithmetic runs in MIF format throughout. For a 2D diffusion stencil with five neighbours and an alpha-weighted update, the boundary cost is amortised over five arithmetic operations per cell per timestep.

The MIF family provides 17 tiles: `UNPACK`, `PACK`, `ADD`, `SUB`, `MUL`, `DIV`, `SQRT`, `MADD` (fused multiply-add), `ABS` (zero cells — sign bit clear), `NEG`, `MIN`, `MAX`, `CMP_EQ`, `CMP_LT`, `CMP_GT`, `CMP_LE`, `CMP_GE`.

---

## 6. Network-Transparent Compute Server

### 6.1 Architecture

The UniCell compute server (`unicell_server.py`) exposes the fabric via a REST API. Any device with a browser can submit jobs without installing software:

```
Browser (tablet, phone, laptop)
        ↓  HTTP / REST
Local server (Python, Flask)
        ↓
Compiler + TileLibrary
        ↓
Fabric (VM / iCEBreaker / Arria 10)
```

The server backend is selected per-request. The VM backend (always available) runs the forward simulation as a pure Python interpreter. Hardware backends communicate via UART bridge (`fpga_bridge.py`) using the same serial port interface for all card types. Backend switching does not require API changes or client awareness.

### 6.2 Model Library

The model library provides two entry points:

**System models** — 10 built-in MathTrix models (1D/2D Laplacian, Gray-Scott reaction-diffusion, 2D wave equation, Ising spin lattice, N-body gravity, Boids flocking, PageRank, continuous Conway, fast marching) defined in `unicell_model_library.py`. These are immutable at runtime.

**User models** — JSON files in the `models/` directory. Any user can create a domain-specific model by specifying parameters and (optionally) a base model to inherit its runner. New domains (BioTrix, ChemTrix) appear automatically in the browser frontend without server restart.

### 6.3 Deployment Variants

**Full server** (`unicell_server.py`): Compiler, tile library, all models, VM runners, browser model browser. Intended for research, education, and development.

**Deployed server** (`unicell_deployed.py`): ~300 lines. Reads the Pond Translation Table (PTT) output only — no compiler, no tile library. Intended for production embedded deployment (SCADA, ECU, security module). The PTT provides a structured name → value mapping that the deployed server serialises as JSON. The client never sees cells, gate states, or topology.

This three-tier separation (Workbench for development, full server for research, deployed server for production) maps cleanly to the three deployment contexts: developer machine, university lab rack, embedded system.

---

## 7. Pond Translation Table and OS Layer

The PTT (Pond Translation Table) is the contract between the fabric and the outside world. Each PTT entry maps a named port to a set of bus addresses and records the last value seen at those addresses. The deployed server reads `last_tick_value` from each entry and serves it over HTTP. The client does not know whether the values came from a VM, an iCEBreaker, or an Arria 10.

The full OS layer (Pond, Bridge, Ward, Shore, COMPANION) provides isolation, security, and health monitoring. Each Pond has its own address space; Bridges mediate inter-Pond communication with configurable access control. The Ward health monitor detects stall, spike, and anomaly conditions per Pond. The Shore registry provides name → address lookup. COMPANION is a permanent OS anchor that cannot be destroyed.

These components are fully implemented and validated in the Python VM. Hardware deployment of the OS layer at full scale awaits the Arria 10 bring-up.

---

## 8. Related Work

UniCell does not fit neatly into existing categories, which we view as a strength rather than a positioning challenge.

**Neuromorphic hardware** (Intel Loihi, IBM TrueNorth): these are designed specifically for spiking neural networks and use event-driven computation. UniCell's two-arrival model is event-driven in the same sense, but the architecture is general-purpose: the same cells implement integer arithmetic, floating-point stencils, sorting networks, and graph algorithms, not just neural spike propagation.

**Systolic arrays** (Google TPU, MIT Eyeriss): data flows through a fixed 2D mesh of processing elements in lockstep. UniCell's wired-OR bus creates a different topology: any cell can communicate with any other cell without routing through intermediate nodes. The price is bus bandwidth; the benefit is arbitrary connectivity patterns expressible as topology.

**Reconfigurable computing / FPGA**: commercial FPGAs are reconfigurable at the LUT level but this reconfigurability is exploited at design time, not runtime. UniCell cells are reconfigured at runtime — a cell can change from AND to OR to NOT to XOR between program loads without reprogramming the FPGA fabric. The `gate_state` register is written by the host CPU over the same bus used for data.

**Dataflow architectures** (MIT RAW, TRIPS, Wave Computing): dataflow machines execute computations when their operands arrive, similar to the two-arrival model. UniCell differs in the physical mechanism: the wired-OR bus means that fan-in aggregation is performed by physics (OR of electrical signals) rather than by a network of routers. This eliminates the routing overhead that limits scalable dataflow implementations.

**Cellular automata / spatial computing**: the connection to cellular automata is conceptual — UniCell cells fire based on local state and local inputs, and complex behaviour emerges from local rules. Unlike CA, the connectivity is not restricted to a spatial neighbourhood and the update rule is not fixed across all cells.

We are not aware of any published architecture that combines NOR universality, wired-OR arbitration, and runtime reconfigurability in a single cell type with a unified bus.

---

## 9. Discussion

### 9.1 What the Constraint Buys

The founding constraint — every logic function must be one cell, one cycle, from NOR gates — ruled out instruction sets, decoders, ALUs, separate memory banks, and type registers. Each of these exclusions turned out to be generative:

- No instruction decoder → gate_state IS the program, directly written by the compiler
- No memory hierarchy → cell registers faster than CPU L1 cache, zero contention
- No type registers → two bits of gate_state carry the type through silicon, OS, and program file
- No routing network → wired-OR bus makes fan-in free; physics performs arbitration

The constraint is not a limitation. It is the source of the properties that make the architecture useful.

### 9.2 Three Primitives

Every parallel computation on UniCell reduces to three primitives:

1. **Hold state** — `latch_in` flag, cell retains its last value
2. **Aggregate neighbours** — wired-OR bus, fan-in without coordination
3. **Apply threshold** — gate tree, any Boolean function of two inputs

This is sufficient for reaction-diffusion, spin lattices, N-body gravity, graph diffusion, and sorting networks. We conjecture it is sufficient for any embarrassingly parallel computation.

### 9.3 Commons Silicon

The architecture is designed to be a shared resource rather than a proprietary accelerator. The `.icm` program format is open and portable. The Verilog source is open. The compiler, tile library, and server are all open source. The deployment model (browser client → REST API → fabric) does not require any proprietary SDK or driver installed on the client.

We call this "commons silicon" — a fabric accessible over the network, owned by the organisation that operates it, open to inspection by anyone with a browser. This is in contrast to GPU cloud compute where the hardware is rented, the driver stack is proprietary, and the programming model is controlled by the vendor.

---

## 10. Current Status and Future Work

**Current status (June 2026):**
- Python VM: fully functional, all compilation paths tested
- Tile library: 86 tiles, 133/133 compiler tests, 236/236 tile tests
- Silicon: 31/31 tests passing on iCEBreaker (iCE40UP5K)
- Server: REST API, browser frontend, VM and hardware backends
- Arria 10 GX660 (Mustang-F100): card enumerated on PCIe; bring-up blocked pending external JTAG programmer

**Near-term:**
- Arria 10 bring-up — first bitstream, UART bridge validation, scale test
- `shift_in_en` silicon validation
- Open-source release

**Future:**
- 64-bit addressing (upper 32 bits via `GS_ADDR_LATCH` for cross-pond bridge addressing)
- LLVM frontend — C, C++, Rust → cells via IR mapper
- UniCell Security Module — fabric topology as root of trust, rolling auth on randomised reboot
- Wasserstein transport demo — geometric unmixing mapped to UniCell fabric (personal goal: demonstration of the three-primitive thesis on a non-trivial research problem)
- University lab deployment — 8 × Arria 10 GX rack, shared via browser portal

---

## 11. Conclusion

We have described a compute fabric built from a single universal cell type, validated on silicon, and made network-accessible via a browser frontend. The architecture's key properties — NOR universality, wired-OR arbitration, two-arrival firing, runtime reconfigurability — emerge from a single constraint enforced at the founding: every logic function must be one cell, one cycle.

The same constraint that feels limiting turns out to be generative. The absence of routing networks, instruction decoders, and memory hierarchies is not a poverty of features but a discipline that forces all complexity into the cell map topology. Programs are topology, not sequences.

The fabric is open source, the program format is portable, and the server is accessible from any browser. We believe this combination — architectural simplicity, silicon validation, open access — is the correct path toward compute that is genuinely shared rather than merely available.

---

## 10b. Format-Typed Symbolic Computation

The MIF tile family, described in Section 5, embeds an implicit design
pattern: a domain-specific internal representation that is more efficient
for computation than the external format, with boundary tiles mediating
the translation. This pattern has been generalised into a `FormatDefinition`
system that any frontend can use.

### The Pattern

A format definition answers five questions about a domain:

1. **Alphabet** — what symbols exist? (A/T/G/C for DNA; H/He/.../Og for chemistry)
2. **Packing** — how are symbols stored compactly in cells?
3. **Boundary** — how do external data and internal cells translate?
4. **Operations** — what computations are valid within this representation?
5. **Constants** — what fixed values does this domain need?

MIF was the first instance: IEEE-754 floats split into two cells
(control cell for exponent+flags, mantissa cell for significand).
The split means exponent arithmetic never touches the mantissa cell —
a structural optimisation that emerges from the format definition,
not from the tile implementation.

### Physical Constants as Preloaded Cells

In UniCell, constants are not special. A physical constant (speed of light,
Boltzmann constant, Avogadro number) is simply a cell whose `a_data` is
loaded at configure time via the preloaded-A pattern. The cell's output
address is the constant's identity. When the cell fires, it emits the
constant value with zero latency — no memory fetch, no broadcast.

The `SI_Physics` format definition declares 17 physical constants
(CODATA 2018 values). Any model that declares `format = "SI_Physics"`
inherits these constants. They are reconfigurable at runtime without
recompiling the cell map — updating a constant is a single configure
transaction on one cell.

This pattern applies equally to market data (Finance_Currency format
declares risk-free rate, basis points, settlement conventions) and
domain-specific lookup tables (Chemistry_Element format declares
atomic masses, valence electrons, periodic group).

### Domains Defined

The format registry currently contains 9 formats across 6 domains:

| Domain | Formats | Bits/symbol | Application |
|--------|---------|-------------|-------------|
| MathTrix | MIF | 32 (2 cells) | Floating-point stencil computation |
| BioTrix | DNA_4Base, RNA_4Base, Amino20 | 2, 2, 5 | Genomics, proteomics |
| ChemTrix | Chemistry_Element | 8 | Periodic table, molecular groups |
| PhysTrix | SI_Physics | 4 (dim vector) | Dimensional analysis, constants |
| FinTrix | Finance_Currency | 8 | Instruments, rates, conversion |
| General | BCD_Decimal, FixedPoint_Q8_24 | 4, 32 | Decimal arithmetic, fixed-point |

### The Broader Claim

Any domain with a finite alphabet, defined operations, and fixed constants
can be expressed as a UniCell format definition and run on the fabric.
The cells are unchanged. The bus is unchanged. The NOR gate is unchanged.
The format is the domain-specific type system that sits above the universal
compute primitive.

This is not a claim about specific tiles — those are domain work, to be
built as needed. It is a claim about the substrate: that the three-primitive
architecture (hold state / aggregate neighbours / apply threshold) plus the
preloaded-A constant injection mechanism is sufficient to host any
structured symbolic computation domain.

---

## 10c. Format Bridging — Cross-Domain Computation in a Single Run

The format definition system (Section 10b) raises a natural question:
if multiple format domains run on the same substrate, can a computation
span domain boundaries within a single cell map?

The answer is yes — and the mechanism is already implicit in the
architecture. It requires only one new concept: the **bridge tile**.

### The Bridge Tile

A bridge tile is a cell map that accepts data in one format and emits
data in another. It sits on the same bus, runs in the same tick cycle,
and is placed by the compiler like any other tile. The cells do not know
they are performing a translation — they fire on arrival and emit their
outputs. The semantic meaning of the translation lives in the bridge
tile's declaration, not in the hardware.

The pattern already exists in the format registry:
`FixedPoint_Q8_24` declares `FIXED_TO_MIF` and `FIXED_FROM_MIF` as valid
tiles. Those are bridge tiles — they cross from fixed-point to MIF format
and back. The concept was present before the name.

### Semantically Valid Bridges

Not all format pairs have meaningful bridges. The bridge tile carries a
**semantic contract** that the compiler evaluates at design time:

```
Chemistry → Physics:  atomic_number → atomic_mass (kg)
                      via preloaded LUT — trivial unit assignment
Chemistry → Biology:  concentration → membrane_potential
                      via Nernst equation — well-defined physics
Physics → Biology:    temperature (K) → metabolic_rate
                      via Arrhenius equation — established biochemistry
```

Each bridge declares its output SI dimension vector. The compiler checks
dimensional consistency before the cell map is placed. A bridge that
produces dimensionless output feeding a tile that expects mass `[0,1,0,0,0,0,0]`
is caught at design time — before the fabric runs.

### The Financial Oddity

A bridge from Finance to Biology has no general semantic meaning. A bond
yield is not a DNA concentration. The compiler assigns such bridges a low
`semantic_confidence` score and issues a design-time warning. The user
must explicitly declare the mapping and accept responsibility for its
meaning. The system does not silently coerce across incompatible domains.

This is the correct behaviour: the substrate is domain-indifferent, but
the format system is not. The cell fires regardless. The bridge contract
catches the error before it reaches silicon.

### Cross-Domain Pipeline

A complete cross-domain computation runs as a single cell map:

```
[ChemTrix: molecular formula]
        ↓  CHEM_MASS (atomic number → mass in kg)
[SI_Physics: mass value]
        ↓  SI_MUL (multiply by Avogadro)
[SI_Physics: molar mass]
        ↓  SI_TO_BIO (concentration bridge via Nernst)
[BioTrix: membrane potential]
        ↓  BIO_THRESHOLD (action potential trigger)
[1-bit result]
```

Each format boundary is crossed by a bridge tile. The substrate runs
the entire pipeline in one pass — chemistry to physics to biology to
signal, in a single tick sequence, on a single wired-OR bus.

### Implementation Path

The bridge system requires:
1. `BridgeTile` base class with semantic contract fields
2. `FormatRegistry.find_bridge(source, target)` — bridge discovery
3. Compiler auto-placement when adjacent tile formats differ
4. Design-time dimensional analysis via SI unit vector propagation

None of these require new hardware. The bridge is a tile. The semantic
contract is metadata. The dimensional check is a compiler pass.
The substrate is already capable.

---

## References

*To be completed for journal submission. Key citations:*

1. Kogge, P. M. & Stone, H. S. (1973). A parallel algorithm for the efficient solution of a general class of recurrence equations. *IEEE Transactions on Computers*, 22(8), 786–793. [Kogge-Stone adder used in INT32_ADD]

2. Heule, M. J. H. et al. (2016). Solving and verifying the Boolean Pythagorean Triples problem via Cube-and-Conquer. *SAT 2016*. [SAT solving as parallel computation — connections to two-arrival model]

3. Reynolds, C. W. (1987). Flocks, herds and schools: A distributed behavioral model. *SIGGRAPH '87*. [Boids algorithm implemented in MathTrix]

4. Turing, A. M. (1952). The chemical basis of morphogenesis. *Philosophical Transactions of the Royal Society B*, 237(641), 37–72. [Gray-Scott reaction-diffusion in MathTrix]

5. Negrut, D. et al. (2014). Parallel computing in multibody system dynamics: Why, when, and how. *J. Comput. Nonlinear Dynam.*, 9(4). [N-body parallel computation — connections to UniCell bus aggregation]

---

## Appendix A: Cell Map Record Format

Each cell is described by a `CellMapRecord`:

```python
@dataclass
class CellMapRecord:
    gate_state:     int    # 32-bit configuration
    input_address:  int    # 32-bit bus address (B channel)
    output_address: int    # 32-bit bus address (output)
    initial_value:  int    # preloaded a_data (0 if not preloaded)
```

The `.icm` format serialises a list of these records as JSON alongside port declarations (named input/output addresses) and metadata. An `.icm` file is self-contained: it carries all information needed to load the program into any UniCell implementation.

## Appendix B: Command Bus Protocol

The UART bridge uses a 9-byte frame format (host → FPGA):

```
0x01  [cmd_bus 4 bytes BE]  [cmd_data 4 bytes BE]
```

Response (FPGA → host):

```
0x10  [address 2 bytes BE]  [data 4 bytes BE]
```

Key opcodes (cmd_bus high byte):

| Opcode | Name | Effect |
|--------|------|--------|
| 0x00 | CMD_CONFIGURE | Set gate_state for addressed cell |
| 0x01 | CMD_SET_INPUT | Set input_address for addressed cell |
| 0x02 | CMD_SET_OUTPUT | Set output_address for addressed cell |
| 0x06 | CMD_INJECT | Write value to bus at specified address |
| 0x07 | CMD_READ | Read current output value of addressed cell |
| 0x08 | CMD_ARRAY_RESET | Authenticated system-wide reset |
| 0x09 | CMD_BOOT_COMMIT | Assign logical address to cell |
| 0x0A | CMD_RECONFIGURE | Change topology of already-configured cell |

## Appendix C: Test Suite Commands

```bash
# VM tests (no hardware required)
PYTHONPATH=. python tests/vm/test_compiler_int32.py   # 133 tests
PYTHONPATH=. python tests/vm/test_fp_tiles.py         # 236 tests

# Silicon tests (requires iCEBreaker connected via UART)
python tests/fpga/test_sanity.py /dev/ttyUSB0         # 31 tests

# Start compute server
python unicell_server.py --host 0.0.0.0 --port 5000
# Open http://localhost:5000 in any browser
```
