# UniCell — Internal Structure & Register Model

*Last updated: 2026-05-14 (revised — command latch simplified)*

---

## Overview

Each UniCell has three completely separate hardware sections:

```
┌─────────────────────────────────────────────────────────┐
│                        UniCell                          │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │             COMMAND LATCH (32 bits)              │  │
│  │         (cell identity — config only)            │  │
│  │                                                  │  │
│  │  bits  0-10:  NOR topology        (11 bits)      │  │
│  │  bits 11-21:  auth_mask           (11 bits)      │  │
│  │  bit   22:    start_flag          ( 1 bit )      │  │
│  │  bits 23-31:  reserved            ( 9 bits)      │  │
│  └───────────────────┬──────────────────────────────┘  │
│          ↑           │                                  │
│   CMD_RECONFIGURE    │ topology drives                  │
│   (auth checked)     ↓ NOR tree                         │
│                 ┌────────────┐                          │
│  ┌──────────┐   │            │   ┌──────────┐           │
│  │  INPUT   │──▶│  NOR TREE  │──▶│  OUTPUT  │           │
│  │  PORT    │   │            │   │  PORT    │           │
│  │  +LATCH  │   └────────────┘   │  +LATCH  │           │
│  └────┬─────┘                    └────┬─────┘           │
│       │ own address latch             │ own address      │
│       │ validates incoming data       │ latch drives     │
│       │ via command bus key           │ output writes    │
└───────┼──────────────────────────────┼──────────────────┘
        │                              │
   DATA BUS IN                    DATA BUS OUT
   (Bus 2 — data only)            (Bus 2 — data only)
```

**The key insight:** each port owns its own address latch. The input port
knows what address it listens on. The output port knows where it writes.
These are local to the port — not stored in the central command latch.

The command bus carries the key (auth token) that validates whether
incoming data on the data line is accepted by the appropriate latch.
Data lands in the right latch because the port recognises its own address
AND the command bus confirms the write is valid.

---

## The Command Latch — 32 bits, fixed width

The command latch holds only what defines the cell's permanent identity.
Everything else is either port-local state or a runtime command.

```
bits  0-10:  NOR topology     (11 bits)
             The cell's gate wiring — fixed at config time.
             Determines what computation the cell performs.
             0x000 = GS_PASS, 0x001 = GS_NOT, others per gate_states.py

bits 11-21:  auth_mask         (11 bits)
             Card-wide auth token. Write-once at boot.
             Validates CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE.
             WRITE-ONLY — no read path anywhere in hardware.
             Silent rejection on mismatch.

bit   22:    start_flag        (1 bit)
             Armed (1) = cell is live, processes data each tick.
             Disarmed (0) = cell ignores data bus.
             Set by CMD_RECONFIGURE completion.
             Cleared by CMD_FREEZE or natural disarm (one-shot).

bits 23-31:  reserved          (9 bits)
             Expansion space. Do not assign without reviewing
             impact on all three Verilog variants first.
```

**Total: 32 bits.** Fixed width retained for expansion headroom.

---

## What Moved Out of the Command Latch

### Input and output addresses — now port-local

Each port owns its own address latch. The input port stores the address
it listens on. The output port stores the address it writes to.

These are loaded by runtime commands on the command bus:
- `CMD_SET_INPUT_ADDR`  — writes to input port's own address latch
- `CMD_SET_OUTPUT_ADDR` — writes to output port's own address latch

Not auth-gated (user+system can set them). The port validates incoming
data by matching bus_addr against its own stored address.

### Mode flags — now runtime commands

GS_ flags that were previously stored in the command latch are now
runtime commands on the command bus. Applied when needed, not persisted.

```
Was stored, now runtime:
  GS_ONE_SHOT      → default cell behaviour (fires once, disarms)
                     No flag needed — it's what cells do naturally.
  GS_LATCH         → CMD_SET_LATCH_MODE on command bus
  GS_SYNC_WAIT     → CMD_SET_SYNC_WAIT on command bus
  GS_LOOP_BACK     → routing — handled at output port level
  GS_BROADCAST     → routing — handled at output port level
  GS_INVERT_OUT    → CMD_SET_INVERT on command bus
  GS_PRIORITY      → scheduler directive, not cell config
  GS_TRACE         → Ward directive, not cell config
  GS_BREAKPOINT    → Ward directive, not cell config
  GS_OUT_POSEDGE   → timing directive at port level
```

This frees up significant space in the command latch and makes the
cell core much leaner. Mode changes don't require a full CMD_RECONFIGURE.

---

## The Three Ports

### 1. Command Bus Port (Bus 1 — input only)

```
cmd_bus[31:0]   — command + auth token + flags
cmd_valid       — valid this cycle
```

Listens every cycle. Auth-gated commands silently dropped on mismatch.

Full Bus 1 bit map:
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
             10-15 = reserved for runtime mode commands (see above)

bits  4-14:  auth token (11 bits, card-wide)
bit   15:    address mode (0=PTT-relative, 1=raw)
bits 16-17:  scope (LOCAL only — EXTENDED retired)
bits 18-21:  handshake / ACK-REQ (bridge cells only)
bits 22-28:  sequence tag (7 bits, bridge transactions)
bits 29-31:  reserved
```

### 2. Data Input Port (Bus 2/3 — input)

```
bus_addr[31:0]  — target address (Bus 3)
bus_data[31:0]  — data payload (Bus 2)
bus_valid       — valid this cycle
```

Port has its own address latch (set by CMD_SET_INPUT_ADDR).
On each cycle: if bus_addr matches own address AND bus_valid → accept
data into input latch. Command bus key confirms the write is valid.

During CMD_RECONFIGURE: bus_data carries config words → command latch.
This is the ONLY time bus_data routes to the command latch.
All other times bus_data → input latch only.

### 3. Data Output Port (Bus 2 — output)

```
out_addr[31:0]  — destination (from port's own address latch)
out_data[31:0]  — computed result
out_valid       — cell fired this cycle
```

Port has its own address latch (set by CMD_SET_OUTPUT_ADDR).
Drives out_addr from its own latch when the cell fires.

---

## CMD_RECONFIGURE Sequence

The only path to the command latch.

**Word sequence (bus_data, one word per cycle):**
```
Word 0:  auth_mask [10:0]   — first RECONFIGURE only (auth_mask == 0)
Word 1:  NOR topology [10:0] → cmd_latch bits 0-10
```

That's it — two words (one on first boot). The addresses are set
separately via CMD_SET_INPUT_ADDR and CMD_SET_OUTPUT_ADDR.

After Word 1: start_flag set (bit 22 of command latch) → cell armed.

**Bootstrap rule:**
- auth_mask == 0 → first RECONFIGURE accepted unconditionally
- Sets auth_mask, then loads topology
- After this: all system commands require matching token
- auth_mask cannot be changed until power cycle

---

## Security Isolation

```
WHO CAN WRITE TO:     cmd latch   input latch   output latch   port addr latches
──────────────────────────────────────────────────────────────────────────────
CMD_RECONFIGURE(auth)    YES          NO             NO              NO
CMD_SET_*_ADDR            NO          NO             NO             YES
Normal bus write           NO         YES             NO              NO
NOR computation            NO          NO            YES              NO
──────────────────────────────────────────────────────────────────────────────
```

A user process writing data cannot reach the command latch or the port
address latches. The worst it can do is write to the input latch —
producing a wrong computation result, which Ward detects.

Only BIOS-Plus holds the card auth token. Only BIOS-Plus can issue
CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE.

---

## Impact on Verilog

The simplified command latch means the Verilog changes are smaller
than previously estimated. Key things to check on iCEBreaker / Kintex-7:

- [ ] Command latch narrows to 32 bits (topology 11b + auth 11b + start 1b + reserved 9b)
- [ ] Input port gets its own address register (was bus_addr comparison inline)
- [ ] Output port gets its own address register (was directly from config)
- [ ] CMD_SET_INPUT_ADDR and CMD_SET_OUTPUT_ADDR write to port registers
- [ ] CMD_RECONFIGURE now only loads 2 words (auth_mask + topology)
- [ ] GS_ mode flags that were in gate_state: audit which are needed as
      runtime commands on cmd_bus codes 10-15 vs which can be dropped
- [ ] Re-run on iCEBreaker to validate before Kintex-7 port

*Note: gate_states.py, compiler, and ICM loader will also need updating
to reflect that addresses are set via CMD_SET_*_ADDR not CMD_RECONFIGURE.
This flows through a significant part of the stack — do methodically.*

---

## Address Space (for port address latches)

```
0x00000000 to 0xEFFFFFFF   Local cell space  (~3.76B)
0xF0000000 to 0xFFFFFFFF   Shore index zone  (~268M)
```

Top nibble 0xF → Shore intercepts and resolves to physical destination.
Transparent to the cell and its port address latches.

---

*Supersedes docs/archive/02_Core_Architecture.md register layout section.*
*The archive doc is retained for historical reference only.*
