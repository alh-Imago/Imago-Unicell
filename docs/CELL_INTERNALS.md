# UniCell — Internal Structure & Register Model

*Last updated: 2026-05-17 (v2 command latch, NOR(A,B) two-input model confirmed on silicon)*

---

## Fundamental Operating Model

**Every UniCell is a two-input NOR gate. It always requires two data arrivals before firing.**

```
First arrival  (input A) → stored in a_data latch, a_arrived flag set — NO output
Second arrival (input B) → triggers NOR(A, B) computation → output fires
```

This is not optional — it is the base behaviour of every cell regardless of topology.

**NOT(A) = NOR(A, A):** both inputs are the same value. Send A twice to the same
input address. The compiler achieves this with a Y-formation — the wire splits into
two paths of equal depth, both arriving at the same cell address.

**Chains are always Y-shaped**, never linear. A linear chain `cell0 → cell1` cannot
work because cell1 only ever receives one input. Real computation graphs are trees
of converging Y-formations.

**sync_wait** (cmd_latch[10]) is now accurately named — it describes the fundamental
two-arrival model. The bit is retained for potential future use (e.g. requiring two
cell-to-cell arrivals before firing, vs one cell + one host arrival).

**Validated on iCEBreaker silicon, 2026-05-17:**
- NOR(A,B) two-arrival model confirmed correct
- NOT(A)=NOR(A,A): send same value twice, correct output
- Y-formation chain: cell0 output = cell1 input A, host sends input B, cell1 fires

---

## Overview

Each UniCell has three completely separate hardware sections:

```
┌─────────────────────────────────────────────────────────┐
│                        UniCell                          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         COMMAND LATCH (32 bits — one word)       │  │
│  │                                                  │  │
│  │  bits  0-10:  NOR topology        (11 bits)      │  │
│  │  bits 11-21:  auth_mask           (11 bits)      │  │
│  │  bit   22:    start_flag          ( 1 bit )      │  │
│  │  bits 23-24:  type                ( 2 bits)      │  │
│  │  bits 25-26:  cell type           ( 2 bits)      │  │
│  │  bit   27:    priority            ( 1 bit )      │  │
│  │  bit   28:    trace               ( 1 bit )      │  │
│  │  bit   29:    breakpoint          ( 1 bit )      │  │
│  │  bits 30-31:  reserved            ( 2 bits)      │  │
│  └───────────────────┬──────────────────────────────┘  │
│          ↑           │                                  │
│   CMD_RECONFIGURE    │ topology drives NOR tree         │
│   (auth checked)     │ type/variant/flags inform Ward   │
│   one word load      ↓ and array controller             │
│                 ┌────────────┐                          │
│  ┌──────────┐   │            │   ┌──────────┐           │
│  │  INPUT   │──▶│  NOR TREE  │──▶│  OUTPUT  │           │
│  │  PORT    │   │            │   │  PORT    │           │
│  │  +LATCH  │   └────────────┘   │  +LATCH  │           │
│  └────┬─────┘                    └────┬─────┘           │
│  own address latch               own address latch      │
└───────┼──────────────────────────┼────────────────────-─┘
        │                          │
   DATA BUS IN                DATA BUS OUT
```

---

## Command Latch — Full 32-bit Map

One word defines the complete cell identity. Load it, the cell is live.

```
bits  9-0:   topology         (10 bits)
             Gate wiring — fixed at config time.
             0x000 = GS_PASS  (identity)
             0x001 = GS_NOT   (invert)
             Others: see gate_states.py

bit   10:    cell_type        (1 bit — repurposed from sync_wait)
             0 = STANDARD/LATCH — fires on data arrival (level triggered)
                 Two arrivals: first loads a_data, second triggers gate tree
                 latch_in=1 → single arrival, a_arrived stays set (memory/counter)
             1 = EDGE — fires on data edge transition
                 invert_out=0 → POSEDGE: fires on 0→1 transition
                 invert_out=1 → NEGEDGE: fires on 1→0 transition
                 Compares current bus_data[0] to prev_data[0] stored in data_reg
                 Single arrival fires when edge detected
             Note: was named sync_wait — renamed as two-arrival is now the default

bits 11-21:  auth_mask        (11 bits)
             Card-wide security token.
             WRITE-ONLY — no read path anywhere in hardware.
             Set once at boot, cannot change until power cycle.
             Silent rejection on CMD mismatch.

bit   22:    start_flag       (1 bit)
             0 = disarmed (ignores data bus)
             1 = armed    (live, processes each tick)
             Set on CMD_RECONFIGURE completion.
             Cleared by CMD_FREEZE or one-shot disarm.

bits 23-24:  type             (2 bits)
             00 = NUMERIC     unsigned integer (default)
             01 = SIGNED      two's complement, primary+complement pair
             10 = ALPHA       8-bit character / string byte
             11 = DATETIME    Unix timestamp, primary+complement pair
             Readable by Ward and bridge without consulting PTT.
             Flows from compiler → command latch → silicon.

bits 25-26:  cell type        (2 bits)
             00 = standard    combinatorial, fires and disarms
             01 = latch       holds output between ticks
             10 = posedge     edge-triggered, rising edge
             11 = negedge     edge-triggered, falling edge
             Decoded once at RECONFIGURE — static, not on data path.
             Informs array controller scheduling on mixed arrays.
             Future: single parameterised Verilog module — type bits
             select behaviour internally, three variants collapse to one.

bit   27:    priority         (1 bit)
             0 = normal scheduling
             1 = scheduled first each tick (high priority path)
             Persistent — high priority cells are always high priority.

bit   28:    trace            (1 bit)
             0 = silent
             1 = record to Ward trace buffer on every fire
             Persistent across reconfigurations — debug sessions survive.

bit   29:    breakpoint       (1 bit)
             0 = normal
             1 = halt array on fire (Ward breakpoint)
             Persistent — breakpoint survives until explicitly cleared.

bits 30-31:  reserved         (2 bits)
             HARD RESERVED. Do not assign.
             Cannot be recovered after tape-out.
```

---

## Why One Word Matters

The entire cell identity fits in a single 32-bit bus transaction:
- Array controller reads cell state in one cycle
- Ward health checks require no multi-word reads
- Bridge depth decisions use type field directly — no PTT lookup
- ICM files store one config word + address pair per cell — very compact
- CMD_RECONFIGURE is 2 words total: auth_mask (boot only) + this word

Everything the system needs to know about a cell lives in one place.

---

## The Three Ports

### 1. Command Bus Port (Bus 1 — input only)

```
cmd_bus[31:0]   — full command bus word
cmd_valid       — valid this cycle
```

```
bits  0-3:   command code
             0  = CMD_NOP
             1  = CMD_DATA_WRITE        user+system
             2  = CMD_SET_INPUT_ADDR    user+system
             3  = CMD_SET_OUTPUT_ADDR   user+system
             4  = CMD_RECONFIGURE       system only (auth required)
             5  = CMD_FREEZE            system only (auth required)
             6  = CMD_RELEASE           system only (auth required)
             7  = CMD_COPY_DATA_TO_OUT  user+system
             8  = CMD_COPY_DATA_TO_IN   user+system
             9  = CMD_PING              anyone
             10-15 = runtime mode commands (GS_ flags, TBD)

bits  4-14:  auth token     (11 bits, card-wide)
bit   15:    address mode   (0=PTT-relative, 1=raw — host always sets 1)
bits 26-16:  cell_id        (11 bits) — target cell for CMD_SET_INPUT_ADDR,
             CMD_SET_OUTPUT_ADDR, and CMD_RECONFIGURE. Cell only accepts if
             cmd_bus[26:16] == CELL_ID. Use 0x7FF as broadcast sentinel
             (FREEZE, RELEASE, PING reach all cells).
bits 16-17:  scope          (LOCAL only)
bits 18-21:  handshake      (bridge cells only)
bits 22-28:  sequence count (7 bits) ┐ 10-bit soft ECC
bits 29-31:  identifier     (3 bits) ┘ → Hamming later, same XOR cell
```

### 2. Data Input Port (Bus 2/3)

Port owns its own address latch (set by CMD_SET_INPUT_ADDR).
Accepts data when bus_addr matches own address AND cmd_valid confirms.
During CMD_RECONFIGURE: bus_data routes to command latch only.
All other times: bus_data → input latch only.

### 3. Data Output Port (Bus 2)

Port owns its own address latch (set by CMD_SET_OUTPUT_ADDR).
Drives out_addr from own latch when cell fires.

---

## CMD_RECONFIGURE Sequence

```
Word 0:  auth_mask [10:0]      FIRST BOOT ONLY (auth_mask == 0)
Word 1:  full 32-bit config    → command latch (topology + all flags)
```

After Word 1: start_flag set → cell armed, live next tick.

Bootstrap: auth_mask == 0 → first RECONFIGURE accepted unconditionally.
After set: all system commands require matching token. One-time write.

---

## GS_SYNC_WAIT — No second address needed

A SYNC_WAIT cell waits for two sequential data arrivals at its own
input_address before firing. It does not need to know where the second
input comes from — it simply counts arrivals:

```
Arrival 1:  data lands in input latch A — cell holds, does not fire
Arrival 2:  data lands in input latch B — cell fires, NOR tree runs
            result written to output_address
            both latches cleared, cell re-arms
```

The sequence count on the command bus (bits 22-28) maintains alignment —
the sender tags each packet in a multi-word transaction with its position.
The SYNC_WAIT cell just waits for count 1 then count 2, in order.

**What this removes:**
- No input_b_address register in the command latch
- No pass-through cells needed to route the second input
- No second CMD_SET_INPUT_B_ADDR command
- Alignment is natural — sequence count enforces order

The cell is self-contained. Two arrivals at one address, in sequence,
is all it needs. The sender handles the routing, not the cell.

---

## Security Isolation

```
WHO CAN WRITE TO:     cmd latch   input latch   output latch   port latches
─────────────────────────────────────────────────────────────────────────────
CMD_RECONFIGURE(auth)    YES          NO             NO              NO
CMD_SET_*_ADDR            NO          NO             NO             YES
Normal bus write           NO         YES             NO              NO
NOR computation            NO          NO            YES              NO
─────────────────────────────────────────────────────────────────────────────
```

---

## Address Space

```
0x00000000 - 0xEFFFFFFF   Local cell space  (~3.76B)
0xF0000000 - 0xFFFFFFFF   Shore index zone  (~268M — logical, not physical)
```

**iCEBreaker test array uses 16-bit addresses (input_address/output_address narrowed
to 16 bits) to reduce comparison LUT chain depth and pass timing at 24 MHz with 8
cells. This is a test array constraint only — not an architectural limit.**

Full 32-bit address validation plan:
- Test 1 (current): 8 cells, 16-bit addresses, 24 MHz — functional bring-up
- Test 2 (pending): 2-3 cells, 32-bit addresses, timing check — validates full
  address space before Kintex-7 scale-up

The Kintex-7 uses 6-input LUTs (vs iCE40 4-input), so a 32-bit comparison fits
in 3 LUTs instead of 5. The timing constraint should not apply there.

---

*Supersedes docs/archive/02_Core_Architecture.md register layout.*
*Archive retained for historical reference only.*

---

## Ground Truth Declaration (2026-05-17)

**The Verilog is now the ground truth for the UniCell model.**

```
ONE input_address
ONE a_data latch — holds first arrival
Second arrival at same address → triggers gate tree on a_data → output fires
```

The VM's input_b_address and receive_b() were pre-silicon convenience abstractions.
They are now superseded. The VM will be updated to match the silicon model:
  - Two arrivals at one address (not one arrival at two addresses)
  - input_b_address removed from CellMapRecord
  - receive_b() removed from UniCell VM class
  - Compiler updated: one input_address per cell, timing handled by Y-formation

Silicon → VM → Compiler → everything else.
Not the other way around.

---

## Special Cell Modes — Memory and Counter

Derived from unicell_latch_split.v and unicell-latch/unicell.py.

### Memory Cell (storage_mode / latch_in)

Normal cell: `a_arrived` cleared after firing — ready for next pair.
Memory cell: `a_arrived` NOT cleared — `a_data` persists between firings.

```
cmd_latch[26] latch_in = 1   — keep a_data after firing
cmd_latch[10] sync_wait = 1  — (default, no change needed)
```

Every incoming trigger arrival re-fires the gate tree on the same `a_data`.
`a_data` only updates when a new FIRST arrival comes in (i.e. when `a_arrived=0`).
Effectively: cell remembers its last input and re-emits computed result on each tick.

### Counter Cell

```
cmd_latch[26] latch_in  = 1  — keep a_data (the increment step)
cmd_latch[31] loop_back = 1  — feed computed output back as next a_data
```

Operation:
1. Load increment value into `a_data` via first arrival (e.g. 1)
2. `a_arrived` stays set (latch_in=1)
3. Each subsequent trigger arrival: gate tree adds trigger value to `a_data`
   (using NOR arithmetic — g2=AND(A,B) builds addition)
4. Result feeds back via loop_back → becomes new `a_data` for next trigger
5. Count accumulates each tick

The 16-bit split (unicell_latch_split.v):
- Lower 16 bits: running count
- Upper 16 bits: increment step (held constant)
- 2x clock (48 MHz) processes lower then upper half in one 24 MHz cycle

For the standard model Verilog (current iCEBreaker):
- Full 32-bit operation, single clock
- latch_in + loop_back flags implement counter behaviour
- No 2x clock needed — gate tree is purely combinational

---

## Multi-Pond Architecture — Mixed Cell Types (future, Kintex-7)

A single system can host multiple ponds with different cell models:

**Latch pond** (edge_mode=0):
- Standard two-arrival model
- General computation, most programs
- Normal throughput

**Edge pond** (edge_mode=1):
- Single-arrival on data transition
- Time-critical paths, interrupt-like behaviour
- Higher throughput, lower latency

**Bridge as model adapter:**
- Edge pond output → bridge → latch-compatible two-packet format → latch pond
- Host always sees latch model — edge pond detail is invisible above bridge
- Bridge normalises: one edge event → two arrival packets at destination address

**iCEBreaker test (future):**
- 4 cells latch + 4 cells edge = 2 ponds on one device
- SB_GB limit (8 total) is the constraint — tight but feasible
- Validates inter-pond bridge conversion on real hardware

**Kintex-7 target:**
- Multiple pond pairs, each with independent bridge
- Intensive computation → edge pond
- Normal computation → latch pond
- PTT manages routing between ponds

---

## Memory Cell — Correct Model (from unicell-latch/unicell.py)

The VM implements memory (storage_mode / latch_mode) as:

```
When new data arrives at input_address:
  computed = gate_tree(input_data)
  _stored_value = computed
  _input_latch = None  ← cleared immediately

Every tick (regardless of new data):
  emit _stored_value to output_address
```

**Key points:**
- `_stored_value` persists between ticks — no loopback needed
- Re-emission is unconditional — fires every tick to output_address
- Update is gated — only when new input arrives
- Gate tree runs on the INPUT, not the stored value
- `output_address` is the read address — different from `input_address`

**Write:** send new value to `input_address` → gate tree computes → stored → re-emitted
**Read:** any tap cell listening on `output_address` sees current value as A every tick

**Verilog implementation note:**
Current Verilog uses `latch_in=1` + `loop_back=1` as approximation.
Correct implementation needs a dedicated `stored_value` register that:
- Updates when `new_data` fires (from gate tree output)
- Re-emits to output_address every tick via `latch_reemit` path
- Does NOT need to loop through the bus — internal register suffices
This is cleaner than the loopback approach and matches the VM exactly.

## Memory Access Pattern — Three-Cell Minimum

Reading a memory cell's stored value requires a minimum of three cells:

```
Memory cell:   in=X  out=Y  latch_mode=1
               New data arrives at X → gate tree → stored → re-emits to Y every tick
               Y is the read address — continuously broadcasts current value

Tap cell:      in=Y  out=Z
               A = stored value (arrives from memory cell every tick)
               B = trigger (second arrival at Y from trigger cell)
               Computes NOR(stored_value, B) → result at Z

Trigger cell:  out=Y
               Provides B — the second arrival at Y that fires the tap cell
```

**Key properties:**
- Memory re-emits every tick — tap cell's A input is always fresh
- Multiple tap cells can share Y — multiple simultaneous readers
- Reading IS computing — no separate read operation
- One tick latency between memory update and tap output
- Trigger cell is often an existing upstream cell — compiler should reuse

**Update (write to memory):**
- Send new value to X (memory cell's input_address)
- Gate tree runs on new value → stored_value updated
- Next tick: new value re-emitted to Y automatically
- Write cost: one arrival at X (latch_mode = single arrival fires)
EOF
