# UniCell — Internal Structure & Register Model

*Last updated: 2026-05-14 (final 32-bit command latch)*

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
bits  0-10:  NOR topology     (11 bits)
             Gate wiring — fixed at config time.
             0x000 = GS_PASS  (identity)
             0x001 = GS_NOT   (invert)
             Others: see gate_states.py

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
bits 26-16:  cell_id        (11 bits) — target cell for CMD_SET_INPUT_ADDR and
             CMD_SET_OUTPUT_ADDR. Cell only accepts if cmd_bus[26:16] == CELL_ID.
             Ignored by other commands (auth/code based targeting).
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
