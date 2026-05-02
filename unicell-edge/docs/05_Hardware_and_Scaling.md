# Imago UniCell — Hardware and Scaling
## Claudette v1.1 — MIDAS Silicon Reference

---

## MIDAS Chip — Design Baseline

MIDAS (Modular Imago Die Architecture System) is the planned silicon implementation of the Claudette v1.1 architecture.

### Single-layer die specification (3nm target)

```
Process node:         3nm (TSMC N3 class)
Die area:             10mm × 10mm = 100mm²
Die utilisation:      75% (25% reserved for routing, power grid, I/O ring)
Transistors/mm²:      ~300M at 3nm
Transistors/cell:     1,000 (full cell: config 64-bit, mode 32-bit,
                             input_address, output_address, data, start_flag)
Usable transistors:   300M × 75% = 225M per die
Cells per die:        225M / 1,000 = 225,000 cells  (≈ 3.4 × 65k blocks)
```

### Simulation cost vs silicon reality

The 192-bit + 1-bit start flag per-cell figure is the **software simulation cost** only — how much GPU VRAM the NumPy simulation model consumes. On real silicon, cell registers live in transistors. No external memory is needed to hold cell state. The silicon die carries its own state in the gate fabric.

### Cell count note

The MIDAS development diagrams referenced 115,000 blocks per die. That figure assumed ~36 transistors per cell (minimum NOR gate count). At 1,000 transistors per cell the correct figure is 343 blocks per die at 3nm. The 115,000 figure remains valid as a long-term target at a future sub-1nm node.

---

## BGA Package

### Why BGA

The command bus is 3 × 64 bits = 192 signal lines. With clock, freeze, power, and ground the total pin count exceeds what a QFP or LGA package can handle cleanly in a 1cm² footprint. BGA distributes balls across the entire underside — a 15×15 grid at 0.8mm pitch gives 225 balls in a 12mm body.

### Specification

```
Package body:      12mm × 12mm
Ball pitch:         0.8mm
Ball grid:         15 × 15 = 225 balls
Ball diameter:     0.45mm
Package height:    ~1.2mm above PCB
Thermal interface: exposed die paddle on lid for direct cooler contact
```

### Minimum ball allocation (226 required)

```
Bus 1 (Command + Control):  64 balls
Bus 2 (Data Payload):       64 balls
Bus 3 (Target Address):     64 balls
─────────────────────────────────────
Command bus total:          192 balls

Control signals:
  CLK, CLK_N (differential): 2
  FREEZE:                     1
  RESET_N:                    1

BIOS-Plus interface:
  BIOS_CLK, BIOS_DATA, BIOS_CS_N: 3

Thermal:
  THERM_OUT, THERM_ID[1:0]:  3

Power/ground:
  VDD (×8), VDDIO (×4), VSS (×12): 24
─────────────────────────────────────
Total:                      226 balls minimum
Recommended 15×15 grid:     225 balls (depopulate 2 corners for fiducials)
```

### Ball-to-bus grouping

```
Rows 1-3:   Bus 1 (Command + Control)   64 balls
Rows 4-6:   Bus 2 (Data Payload)        64 balls
Rows 7-9:   Bus 3 (Target Address)      64 balls
Rows 10-12: Control, BIOS, thermal      24 balls
Distributed: VDD, VDDIO, VSS            24 balls
```

### PCB layer stack

```
Layer 1 (top):  Die pad, thermal interface
Layer 2:        Bus 1 signal traces (command + control)
Layer 3:        Bus 2 signal traces (data payload)
Layer 4:        Bus 3 signal traces (target address)
Layer 5:        Ground plane
Layer 6:        Power planes (VDD, VDDIO)
Layer 7:        Ground plane
Layer 8 (bottom): PCIe connector, inter-die routing
```

Bus 2 (data) and Bus 3 (address) are on separate PCB layers with no physical connection. The scope decoder in the command bus is the only point where the paths interact — to select which register to write.

---

## PCIe Card Layout

### Physical dimensions

```
Form factor:  Full-height, full-length PCIe (FHFL)
Board:        312mm × 111mm
Thickness:    ~25mm (with cooling jacket installed)
Interface:    PCIe ×16 edge connector
```

### Die positions

```
56 positions per face (front and back), 14 columns × 4 rows
Position size:  10mm × 10mm
Gap between:    10mm (used for cooling infrastructure)
Total grid:     14 × 4 × 2 faces = 112 die positions per card
```

### Card layout diagram (one face)

```
  ┌────────────────────────────────────────────────────────┐
  │  [D][D][D][D][D][D][D][D][D][D][D][D][D][D]  row 0   │
  │  10mm gap — cooling channels + inter-die bus           │
  │  [D][D][D][D][D][D][D][D][D][D][D][D][D][D]  row 1   │
  │  10mm gap                                              │
  │  [D][D][D][D][D][D][D][D][D][D][D][D][D][D]  row 2   │
  │  10mm gap                                              │
  │  [D][D][D][D][D][D][D][D][D][D][D][D][D][D]  row 3   │
  │                                PCIe connector ────────►│
  └────────────────────────────────────────────────────────┘
  [D] = 10mm × 10mm die position (one MIDAS chip)
```

### Cell count scaling table

| Layers | Cells/die | Sim VRAM† | Cells/card |
|--------|-----------|-----------|------------|
| 1 | 225K | ~4.7 GB | 25.2M |
| 1 | 22.5M‡ | ~473 GB | 2.52B |
| 8 | 180M | ~3.8 TB | 20.16B |
| 12 | 270M | ~5.7 TB | 30.24B |

† Sim VRAM = GPU simulation cost only. NOT a hardware requirement.  
‡ 22.5M cells/die at 3nm (100mm², 75% utilisation, 1000T/cell)

A 12-layer card exceeds the Pebble tier target (24B cells) on a single PCIe card. Double-sided water cooling is mandatory from 8 layers upward.

---

## 3D Die Stacking

Dies are stacked vertically using Through-Silicon Vias (TSV). Each stack position holds 1-12 identical MIDAS dies. All dies in a stack share the same command bus column — they are peers, not master/slave.

### Stack geometry

```
Stack:    vertical column at one (row, col) position
          1-12 dies, each 10mm × 10mm × 0.7mm
          Total stack height: 12 × 0.7mm = 8.4mm
          Fits within the 10mm position gap

Inter-die bus: TSV columns carrying all three command buses
               between adjacent dies in the stack
               Each die in the stack is its own ShoreKeeper domain
```

---

## Thermal Management — Water Cooling Jacket

### Why mandatory above 8 layers

```
Power per die (estimate):   ~4W at 3nm, 100% activity
Dies per face:               56
Faces:                       2
8-layer stack power:        56 × 2 × 8 × 4W = 3,584W
12-layer stack power:       56 × 2 × 12 × 4W = 5,376W
```

Air cooling cannot remove 3-5kW from a 312mm PCIe card. Water cooling jacket is mandatory.

### Double-sided cooling jacket design

```
Two aluminium water blocks, one per card face
Sandwich: [front block] [PCB with dies] [rear block]
Total PCB+jacket thickness: ~25mm
Coolant flow: 4 independent channels per face (one per die row)
              16 channels total per card (8 per side)
```

### Four-channel layout per face

```
Channel 0 (row 0):  14 dies, top row
Channel 1 (row 1):  14 dies
Channel 2 (row 2):  14 dies
Channel 3 (row 3):  14 dies, bottom row

Each channel:  independent flow rate control
               inlet temperature sensor
               outlet temperature sensor
               flow rate sensor
```

### ShoreKeeper thermal zones

The 4 physical cooling channels map directly to 4 ShoreKeeper thermal zones:

```
zone_row_0 → channel 0
zone_row_1 → channel 1
zone_row_2 → channel 2
zone_row_3 → channel 3
```

When a Ward in zone_row_2 escalates with thermal_state=MIGRATE, the ShoreKeeper knows the Pond is physically in channel 2. It requests migration to a die in a cooler channel — without routing through HyperShore unless cross-zone migration is needed.

### Microchannel routing

```
Manifold (inlet):  coolant enters from card edge connector
Distribution:      splits to 4 parallel channels per face
Microchannel:      0.5mm channels directly over die positions
Collection:        merges back to single outlet at card edge
Outlet:            warm coolant returns to external chiller
```

---

## Proof-of-Concept Tape-out — ChipFoundry chipIgnite

A first silicon validation tape-out is possible today at 130nm on the SKY130 process via ChipFoundry (formerly Efabless). This is not the production MIDAS chip — it is proof that the architecture is correct on real silicon.

### Specification

```
Foundry:      ChipFoundry (UmbraLogic Technologies LLC)
Process:      SKY130 (Skywater 130nm)
Platform:     OpenFrame (~15mm² user area)
Cost:         $14,950 per tapeout
Delivery:     ~5 months after submission
Units:        100 QFN-packaged chips
IP:           fully private — no open-source requirement
```

### What you get on 15mm² at 130nm

```
Transistor density:   ~10M/mm²
Usable area:          15mm² × 75% = 11.25mm²
Transistors:          ~112.5M
Cells at 1000T each:  ~112,500 cells (≈1 × 65k block)
```

### Why this is enough for validation

112,500 NOR cells is sufficient to prove:
- NOR gate cells fire correctly at silicon speed (~100MHz+)
- Command bus auth token mechanism works in hardware
- PTT lookup operates at nanosecond latency
- COMPANION + Ward + Shore function correctly
- GS_ADDR_LATCH extended addressing works on real gates
- A simple compiled program (INT32_ADD_CLA) runs on silicon

### The RISC-V core

Every chipIgnite design includes a RISC-V management core. This maps naturally to the Claudette architecture:

```
RISC-V core:     CommandInterface role
                 Boot sequence and auth token distribution
                 COMPANION logic (rule engine)
                 ShoreKeeper aggregation

NOR cell array:  The compute fabric (112,500 cells)
                 Runs compiled Claudette programs
                 PTT-relative addressing enforced

Together:        Exactly the intended architecture —
                 management processor + NOR compute fabric
```

### Production pathway

```
Step 1: chipIgnite 130nm, 15mm², $14,950
        Prove the architecture. 100 chips.

Step 2: 28nm shuttle (~$100-400k)
        15M cells — real functional MIDAS card
        Full Pond hierarchy, multi-session

Step 3: 22nm / below
        22.5M cells — matches simulation baseline
        Full production MIDAS specification
```

---

## GPU Backend — Simulation Notes

The `GPUArrayBackend` replaces the per-cell Python loop with a vectorised NumPy/CuPy tick:

```python
backend = GPUArrayBackend(cell_count=1_000_000)
backend.load_from_controller(ctrl)
backend.tick()      # vectorised — all cells in parallel
ctrl.array = backend
```

Auto-detects CuPy (GPU) and falls back to NumPy (CPU) transparently.

### Simulation VRAM requirements (not hardware)

| Cell count | VRAM needed |
|------------|-------------|
| 1M cells | ~21 MB |
| 22.5M cells | ~473 MB |
| 100M cells | ~2.1 GB |
| 225M cells | ~4.7 GB |

A 970 GTX (3.5GB VRAM) can simulate ~167M cells. This is the simulation cost only — real silicon stores cell state in transistors with no external memory requirement.
