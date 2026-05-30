# Compound Opcodes & Command Word Extension
**Design note — May 2026**
**Status: Architectural decision, implementation pending**

---

## Summary

A conversation exploring opcode space led to several significant architectural discoveries,
all fitting within the existing 32-bit command word with zero bus width changes.

---

## Command Word Layout (v2.3 — unified 32-bit cmd_bus)

```
cmd_bus [31:0]  — unified command word:
  [7:0]   opcode        8-bit command code (256 opcodes)
  [8]     gate_enable   0=broadcast, 1=filter by gate_set
  [16:9]  gate_set      8-bit group tag
  [18:17] preload_sel   transient preload: 00=none 01=0x00000000 10=0xFFFFFFFF
  [20:19] shift_sel     bit19=shift_in_en, bit20=shift_out_en
  [28:21] auth_token    8-bit, matched against stored auth_mask
  [31:29] spare

cmd_data [31:0] — payload (meaning depends on opcode):
  CMD_BOOT_COMMIT:    [15:0]=logical_addr [23:16]=auth_mask [31:24]=group_tag
  CMD_RECONFIGURE:    [31:0]=full cmd_latch word
  address ops:        [15:0]=address
  shift ops:          [3:0]=nibble shift count
```

Auth token is now in `cmd_bus[28:21]` (not cmd_data). This means every
command carries auth, not just address-change opcodes. Gate_set allows
group-targeted commands without per-cell addressing.

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


## CMD_PRELOAD → preload_sel (v2.3)

**Original design: CMD_PRELOAD (0x0F) + CMD_PRELOAD_HI (0x16)**

Loaded `a_data` in one or two transactions. Both opcodes are **deprecated in v2.3**
and kept only for iCEBreaker compatibility with existing Verilog.

**v2.3 replacement: preload_sel bits in cmd_bus[18:17]**

A two-bit transient modifier carried on every command word:

```
00 = no preload
01 = load 0x00000000 into a_data, set a_arrived=1  (AND tree false side)
10 = load 0xFFFFFFFF into a_data, set a_arrived=1  (NOT/XOR/XNOR constant)
```

Applied after opcode logic, if auth passes. Independent of opcode — any
command can carry a preload. One transaction instead of one or two.

**Common patterns (v2.3):**
- NOT cell:            `build_cmd_bus(CMD_NOP, preload_sel=PRELOAD_ONES)`
- AND tree false side: `build_cmd_bus(CMD_NOP, preload_sel=PRELOAD_ZERO)`

**Python:** `fpga_bridge.preload_cell(cell_addr, 0xFFFFFFFF)` uses `preload_sel`
in v2.3 mode and falls back to the two-step CMD_PRELOAD sequence in v2.2 mode.

Only `0x00000000` and `0xFFFFFFFF` are supported on v2.3 silicon. These cover
all standard gate tree constants. Arbitrary values require the Python VM path
or a full CMD_RECONFIGURE.
