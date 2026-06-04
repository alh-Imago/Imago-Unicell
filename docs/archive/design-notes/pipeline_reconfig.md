# Pipeline Reconfiguration — Streaming Execution Model

## Concept

The fabric reconfigures in-flight as data flows through. If the pipeline
is long enough, reconfiguration of trailing cells overlaps with execution
in leading cells. Data and instructions flow simultaneously — meeting at
each stage.

---

## How It Works

```
Time →

Stage 1:  [CONFIG_A]        → [DATA_1 executing]  → [DATA_2 executing]
Stage 2:  [loading CONFIG_B] → [CONFIG_A]          → [DATA_1 executing]
Stage 3:  [DDR fetch]        → [loading CONFIG_B]  → [CONFIG_A]
```

- Data flows forward through the pipeline
- Configuration flows behind it, loading the next operation
- By the time DATA_2 reaches Stage 1, CONFIG_B is already loaded
- No stall — execution and reconfiguration fully overlap

---

## The Data Tile as Instruction Carrier

The data tile carries its own reconfiguration instructions. Data and
program are unified — the arriving data word tells the cell what to
become next, then is processed by the current configuration.

Dissolves the Von Neumann separation of data and program at the cell level.
The instruction IS the data flowing through.

---

## Branches

Branches require a one-cell buffer to maintain timing while the
decision propagates:

```
[COMPARE cell] → [BUFFER cell] → [reconfigure based on result]
                      ↑
               holds data for 1 tick while branch
               decision propagates to next stage
```

Buffer cell is just PASS topology — delays data by one clock cycle,
giving the branch decision time to reach the reconfiguration logic
before data arrives at the next stage.

---

## RAM-Backed Instruction Table (Card Implementation)

For space-constrained systems, the full program lives in DDR3, not fabric:

```
DDR3 (instruction table)
    ↓ stream next config
Fabric pipeline (N cells deep)
    ↑ data flowing through
Result → DDR3 / PCIe output
```

- **Fabric**: only needs cells for pipeline depth, not full program
- **DDR3**: holds arbitrarily large instruction sequence
- **DDR3 as program counter**: streams configs to fabric continuously

For Kintex-7 with DDR3 ~25GB/s and 200 cells:
- Each cell reconfiguration = 32 bytes
- 200 cells × 32 bytes = 6400 bytes per full reconfiguration  
- DDR3 can stream ~4 million full reconfigurations per second
- Data throughput: 200 cells × 100MHz = 20 billion ops/second

---

## Compact Execution for Constrained Systems

**Tier 2 product** (1-2 ponds, security module, vehicle ECU):
- Small cell count (32-64 cells)
- Full program in small flash/RAM
- Pipeline streams through it continuously
- A 32-cell pipeline at 100MHz with 1000-step program executes
  full program in 10µs, then loops — sufficient for most control loops,
  auth checks, sensor processing

---

## Relationship to Existing Architecture

- **Preloaded-A pattern**: already streams A values before execution —
  pipeline reconfig generalises this to full reconfiguration
- **Data tile**: already exists — adds instruction-carrier role
- **CMD_BOOT_COMMIT**: already the reconfiguration mechanism — pipeline
  just automates the timing
- **DDR3**: natural next step after PCIe bring-up

---

## Key Properties

- **No stall**: reconfiguration and execution fully overlap
- **Compact**: cell count = pipeline depth, not program length
- **Unified**: data and instructions are the same stream  
- **Deterministic**: timing is structural, not scheduled

*Noted: 2026-06-03, during Kintex-7 bring-up*
