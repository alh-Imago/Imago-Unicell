# Compound Opcodes & Command Word Extension
**Design note — May 2026**
**Status: Architectural decision, implementation pending**

---

## Summary

A conversation exploring opcode space led to several significant architectural discoveries,
all fitting within the existing 32-bit command word with zero bus width changes.

---

## Command Word Layout (revised understanding)

```
cmd_bus  [7:0]   = opcode (256 codes, ~243 free)
cmd_data [31:0]:
  [31:24] = auth_token    (8-bit, only consumed by address ops)
  [23:16] = spare
  [15:8]  = nibble mask   (8 bits = 8 nibbles of 32-bit word)
  [8]     = mask_enable   (0=full word, 1=use nibble mask)
  [7:0]   = opcode mirror / spare
```

Auth is only consumed by address-change opcodes (CMD_SET_INPUT_ADDR,
CMD_SET_OUTPUT_ADDR, CMD_SET_LOGICAL). All other opcodes leave [31:24] free.

**Hot path (compute/reconfigure):** full 24 bits available, auth irrelevant
**Config path (address changes):** auth consumed, slow, infrequent, protected

---

## Nibble Mask Extension

Every existing opcode automatically gets a masked variant via bit [8]:

```
mask_enable = 0  →  operate on all 32 bits (existing behaviour, unchanged)
mask_enable = 1  →  apply nibble mask in [15:8]
```

Nibble mask bits:
```
bit 0 → nibble 0  bits [3:0]
bit 1 → nibble 1  bits [7:4]
bit 2 → nibble 2  bits [11:8]
bit 3 → nibble 3  bits [15:12]
bit 4 → nibble 4  bits [19:16]
bit 5 → nibble 5  bits [23:20]
bit 6 → nibble 6  bits [27:24]
bit 7 → nibble 7  bits [31:28]
```

This extends ALL opcodes to masked variants with zero new opcodes — one modifier
bit multiplies the entire opcode table. Particularly powerful for:
- Partial word memory updates (read-modify-write replaced by single masked command)
- Lane-specific gate operations (apply AND to upper two nibbles, leave lower intact)
- Byte/halfword granularity without separate addressing

---

## Topology Preset Opcodes (range 48–63)

Instead of sending a full CMD_RECONFIGURE with carefully assembled topology bits,
a single preset opcode configures the cell for a known gate function:

| Code | Name | Topology | Notes |
|------|------|----------|-------|
| 48 | CMD_TOPO_PASS_COLD | 0x000 | configure, disarmed |
| 49 | CMD_TOPO_PASS | 0x000 | configure + arm |
| 50 | CMD_TOPO_NOT_COLD | 0x001 | configure, disarmed, latch_in=1 |
| 51 | CMD_TOPO_NOT | 0x001 | configure + arm, latch_in=1 |
| 52 | CMD_TOPO_NOR_COLD | 0x004 | configure, disarmed |
| 53 | CMD_TOPO_NOR | 0x004 | configure + arm |
| 54 | CMD_TOPO_NAND_COLD | 0x027 | configure, disarmed |
| 55 | CMD_TOPO_NAND | 0x027 | configure + arm |
| 56 | CMD_TOPO_AND_COLD | 0x007 | configure, disarmed |
| 57 | CMD_TOPO_AND | 0x007 | configure + arm |
| 58 | CMD_TOPO_OR_COLD | 0x024 | configure, disarmed |
| 59 | CMD_TOPO_OR | 0x024 | configure + arm |
| 60 | CMD_TOPO_XOR_COLD | 0x0BC | configure, disarmed |
| 61 | CMD_TOPO_XOR | 0x0BC | configure + arm |
| 62 | CMD_TOPO_XNOR_COLD | 0x03C | configure, disarmed |
| 63 | CMD_TOPO_XNOR | 0x03C | configure + arm |

**Pattern:** cold always even, armed always odd.
**Python:** `CMD_TOPO_BASE + (gate_type * 2) + armed`

Single-input gates (PASS, NOT) automatically get `latch_in=1` since B is irrelevant.

Each preset internally executes (like CMD_MEM_CALL pattern):
1. Write topology bits for gate type
2. Set edge_mode, latch_in, one_shot as appropriate
3. Armed variant: set start_flag=1

---

## Cell State Control Opcodes (range 16–31)

| Code | Name | Action |
|------|------|--------|
| 16 | CMD_CLEAR_ARRIVED | clear a_arrived, a_data — reset input state only |
| 17 | CMD_RESET_CELL | clear a_arrived + a_data + one_shot_fired, rearm |
| 18 | CMD_SWAP_AB | a_data ← bus_data, set a_arrived (pipeline reuse) |
| 19 | CMD_CAPTURE_REARM | fire output + rearm one_shot in same cycle |
| 20 | CMD_SET_TOPO | write topology bits only, no full reconfigure |
| 21 | CMD_SET_INVERT | toggle invert_out without reconfigure |

CMD_RESET_CELL is the "panic clear" — single command replaces CLEAR + CONFIG sequence.

---

## NOR Gate Tree — Complete Topology Table

From unicell.v (silicon validated):

| Gate | Topology bits [9:0] | Hex | Gates used |
|------|---------------------|-----|-----------|
| PASS(A) | 0000000000 | 0x000 | bypass |
| PASS(B) | 0000101100 | 0x02C | bypass |
| NOT(A) | 0000000001 | 0x001 | g0 |
| NOT(B) | 0000000010 | 0x002 | g1 |
| NOR(A,B) | 0000000100 | 0x004 | g4 |
| AND(A,B) | 0000000111 | 0x007 | g0+g1+g2 |
| OR(A,B) | 0000100100 | 0x024 | g4+g5 |
| NAND(A,B) | 0000100111 | 0x027 | g0+g1+g2+g3 |
| XNOR(A,B) | 0000111100 | 0x03C | g4+g6+g7+g8 |
| XOR(A,B) | 0010111100 | 0x0BC | g4+g6+g7+g8+g9 |
| ZERO | 0000110000 | 0x030 | g4+g5 forced |
| ONE | 0010110000 | 0x0B0 | forced high |

Topology bits are dependency-encoded — AND requires g0+g1+g2 (bits 0,1,2) because
g2 depends on g0 and g1. Cannot skip dependencies.

---

## Latch Axis as Functional Switch

Disabling input latches changes the effective gate function:

| Latch A | Latch B | Effective function |
|---------|---------|-------------------|
| on | on | normal two-arrival gate |
| off | on | PASS(B) — live value straight through |
| on | off | PASS(A) — stored value rebroadcast |
| off | off | dead cell |

Latch state and topology are independent axes — NOR with latch A disabled becomes
NOT(B) without needing the NOT topology. Multiplies effective function space.

---

## Declarative Programming Model

The compound opcode + nibble mask architecture shifts Python from imperative to
declarative style:

```python
# Current imperative style
cell.freeze()
cell.set_topology(AND_BITS)
cell.set_gate_state(AND_GATES)
cell.release()

# Declarative style with presets
cell.configure(CMD_TOPO_AND, mask=0b00110000)  # AND on upper two nibbles
```

Benefits:
- fp_tiles.py and compiler output becomes self-documenting
- Barrier to contribution drops significantly
- Trace logs readable without decoder
- IR-to-cell mapping approaches 1:1 for common ops

---

## Depth as the New Constraint

Key insight from this session:

> "Depth is the new constraint, time never was"

Traditional architectures optimise for time (clock cycles, latency, bandwidth).
Imago sidesteps time — the free-running parallel tree fires when ready.

The constraint becomes **depth** — dependency chain length through the cell graph.
This maps to problem complexity naturally: shallow problems get shallow solutions.
The architecture reflects the computation rather than fighting it.

---

## Implementation Notes

- All fits in existing 32-bit command word — zero bus width changes
- ROM-style preset table: localparam block in Verilog, zero runtime cost
- Preset opcodes follow CMD_MEM_CALL pattern (already established)
- Nibble mask logic: output assembly mux + one register, low cost
- No new FSM states needed — just more case branches
- Auth isolation guaranteed: [31:24] only consumed by address opcodes

---

## Partial Word Memory Updates

The nibble mask makes read-modify-write obsolete for cell-managed memory:

**Before:** read word → mask in Python → write full word back (3 bus cycles)
**After:** CMD with mask_enable=1 + nibble_mask = update selected nibbles (1 bus cycle)

Significant capability for any cell acting as a memory/register location.

---

## References (for future paper)

- Cellular automata (Conway, Wolfram) — emergent computation from simple rules
- Dataflow architectures — cells firing on data availability
- NOR universality — theoretical foundation
- Systolic arrays — parallel compute fabric analogy
- Reservoir computing / neuromorphic — emergent computation analogies
- BBC Micro nibble packing (1982) — constraint-driven elegance, same DNA


## CMD_PRELOAD (0x0F) + CMD_PRELOAD_HI (0x16)

**Added: 2026-05-29**

Implements the preloaded-A pattern on silicon. Loads a 32-bit value into
`a_data` and sets `a_arrived=True`. Cell fires immediately on first B arrival.

| Opcode | Code | Payload | Effect |
|--------|------|---------|--------|
| CMD_PRELOAD | 0x0F | cmd_data[23:0] | a_data[23:0] = payload, a_arrived = 1 |
| CMD_PRELOAD_HI | 0x16 | cmd_data[15:0] | a_data[31:16] = payload |

**Common patterns:**
- NOT cell: CMD_PRELOAD(0xFFFFFF) + CMD_PRELOAD_HI(0xFFFF) → a_data=0xFFFFFFFF
- AND tree false branch: CMD_PRELOAD(0) → a_data=0x00000000
- Arbitrary value: CMD_PRELOAD(lo24) + CMD_PRELOAD_HI(hi16)

**Python:** `fpga_bridge.preload_cell(cell_addr, a_data)` handles the 1 or 2
command sequence automatically based on whether upper bits are non-zero.

Both opcodes require auth and the cell should be frozen during configuration.
