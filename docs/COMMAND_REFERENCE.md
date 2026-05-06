# Imago UniCell — Command Reference
## iCEBreaker Bring-up Guide

**Connection:** COM4, 115200 baud, 8N1, no flow control  
**Cells available:** 8 (addresses 0x0000 to 0x0007)  
**Run:** `python fpga\fpga_bridge.py --port COM4`

---

## Quick Start

```bash
# Connect and check status
python fpga\fpga_bridge.py --port COM4

# Run built-in demo (NOT gate + NAND)
python fpga\fpga_bridge.py --port COM4 --demo

# Reset the array
python fpga\fpga_bridge.py --port COM4 --reset
```

---

## Python Session (interactive)

```python
import sys
sys.path.insert(0, 'fpga')
from fpga_bridge import FPGABridge
import time

b = FPGABridge('COM4')
b.connect()

# --- your commands here ---

b.disconnect()
```

---

## Gate States (GS_*)

These are the values to pass as `gate_state` when configuring a cell.

| Name       | Value        | Function                        |
|------------|-------------|----------------------------------|
| GS_NOT     | 0x00000001  | NOT(input) = NOR(in, in)        |
| GS_PASSTHROUGH | 0x00000200 | Pass input through unchanged  |
| GS_NOR     | *see below* | NOR(A, B) — needs two inputs    |

### All gate outputs (gate_state selects which NOR gate output):

The cell has 9 NOR gates internally. Set exactly ONE bit in bits [8:0]:

```
gate_state[8:0]   Output selected
000000001 (0x001) g0 = NOR(in, in)       = NOT(in)
000000010 (0x002) g1 = NOR(in, in)       = NOT(in)  [duplicate]
000000100 (0x004) g2 = NOR(g0, g1)       = AND(in, in) = in
000001000 (0x008) g3 = NOR(g2, in)       = NOT(in OR in) = NOT(in)
000010000 (0x010) g4 = NOR(g2, in)       = NOT(in)
000100000 (0x020) g5 = NOR(g3, g4)       = in NOR in = NOT(in)... 
001000000 (0x040) g6 = NOR(g5, in)
010000000 (0x080) g7 = NOR(g6, g5)
100000000 (0x100) g8 = NOR(g7, 0)        = NOT(g7)
```

**For bring-up, use GS_NOT = 0x00000001** — this is the confirmed working gate.

---

## Configuring a Cell

```python
# configure_cell(cell_addr, gate_state, input_addr, output_addr)
# cell_addr:   0x0000 to 0x0007 (which cell to configure)
# gate_state:  which gate to use (see above)
# input_addr:  bus address this cell listens to
# output_addr: bus address this cell writes to

GS_NOT = 0x00000001

# Configure cell 0 as NOT gate
# Listens on 0x1000, outputs to 0x2000
b.configure_cell(0x0000, GS_NOT, 0x1000, 0x2000)

# Configure cell 1 as NOT gate  
# Listens on 0x1001, outputs to 0x2001
b.configure_cell(0x0001, GS_NOT, 0x1001, 0x2001)
```

---

## Injecting Data (triggering cells)

```python
# inject(addr, data)
# addr: bus address to write to
# data: 32-bit value (cells use bit 0 for logic)

# Send 0 to address 0x1000
b.inject(0x1000, 0)

# Send 1 to address 0x1000
b.inject(0x1000, 1)
```

---

## Reading Output

```python
# wait_for_fire(timeout=2.0)
# Returns (addr, data) tuple or None on timeout

result = b.wait_for_fire(timeout=2.0)
if result:
    addr, data = result
    print(f"Cell fired: addr=0x{addr:04X} data={data & 1}")
else:
    print("No output received")
```

---

## Status Query

```python
status = b.get_status()
print(f"Armed cells: {status['armed']}")
print(f"Cycle count: {status['cycles']}")
```

---

## Complete Examples

### NOT Gate

```python
GS_NOT = 0x00000001
b.configure_cell(0x0000, GS_NOT, 0x1000, 0x2000)

for input_val in [0, 1]:
    b.inject(0x1000, input_val)
    result = b.wait_for_fire()
    output = result[1] & 1 if result else '?'
    print(f"NOT({input_val}) = {output}")
```

### NAND via Wired-OR (two NOT cells, shared output address)

```python
GS_NOT = 0x00000001
# Both cells output to SAME address — wired-OR combines their outputs
b.configure_cell(0x0002, GS_NOT, 0x1100, 0x3000)
b.configure_cell(0x0003, GS_NOT, 0x1200, 0x3000)

for a, b_val in [(0,0),(0,1),(1,0),(1,1)]:
    b.inject(0x1100, a)
    b.inject(0x1200, b_val)
    time.sleep(0.05)
    r1 = b.wait_for_fire(timeout=1.0)
    r2 = b.wait_for_fire(timeout=1.0)
    # Collect both outputs — OR them together
    outputs = []
    if r1: outputs.append(r1[1] & 1)
    if r2: outputs.append(r2[1] & 1)
    result = max(outputs) if outputs else '?'
    print(f"NAND({a},{b_val}) = {result}")
```

### NOR via Wired-OR (two NOT-NOT chains)

```python
# NOR(A,B) = NOT(A OR B)
# Build: A -> NOT -> wire_or_bus -> NOT -> output
# But with wired-OR: NOT(A) AND NOT(B) = NOR(A,B) by De Morgan
GS_NOT = 0x00000001

# Cell 0: NOT(A) -> 0x4000
b.configure_cell(0x0004, GS_NOT, 0x1000, 0x4000)
# Cell 1: NOT(B) -> 0x4000 (same address as cell 0 — wired-OR)
b.configure_cell(0x0005, GS_NOT, 0x2000, 0x4000)

# Note: wired-OR gives OR of NOT(A) and NOT(B)
# That equals NAND(A,B), not NOR
# For true NOR, chain: A->NOT->addr1, B->NOT->addr1, addr1->NOT->output
```

### Chained NOT (double negation = buffer)

```python
GS_NOT = 0x00000001
# Cell 0: NOT(input) -> intermediate address
b.configure_cell(0x0000, GS_NOT, 0x1000, 0x5000)
# Cell 1: NOT(intermediate) -> output
b.configure_cell(0x0001, GS_NOT, 0x5000, 0x6000)

b.inject(0x1000, 1)
r1 = b.wait_for_fire()  # cell 0 fires: NOT(1) = 0
r2 = b.wait_for_fire()  # cell 1 fires: NOT(0) = 1
print(f"Double NOT(1) = {r2[1] & 1 if r2 else '?'}")  # should be 1
```

---

## Address Space Guidelines

Use these ranges to keep things organised:

```
0x0000 - 0x0007   Cell CONFIG_ADDRESS (do not use as data addresses)
0x1000 - 0x1FFF   Primary inputs (inject here to trigger cells)
0x2000 - 0x2FFF   Primary outputs (single cell outputs)
0x3000 - 0x3FFF   Wired-OR outputs (multiple cells share)
0x4000 - 0x4FFF   Intermediate / chained signals
0x5000 - 0x5FFF   Secondary intermediate signals
```

---

## Available Cells

With 8 cells (addresses 0x0000–0x0007) you can build:

- Up to 8 independent NOT gates
- Up to 4 NAND gates (2 cells each)
- Up to 2 chains of 4 (e.g. 4-input logic)
- Any combination of the above

All 8 cells operate in **parallel** — they all evaluate simultaneously
every clock cycle (~12MHz). There is no time-sharing.

---

## Reset

```python
# Reset array (clears all cell state, requires reconfiguration)
b.reset()
time.sleep(0.1)
# Now reconfigure cells as needed
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| No UCOK on connect | Board not running | Power cycle, re-flash |
| Armed cells = 0 after configure | Wrong cell address | Check cell_addr is 0x0000-0x0007 |
| No output after inject | Wrong input_addr | Must match what you configured |
| Output always 1 | input_val stale | Confirmed fixed in current build |
| Corrupt responses | Baud rate drift | Reconnect, or power cycle board |

