# UniCell — Internal Structure & Register Model

## Overview

Each UniCell has three completely separate hardware sections:

```
┌─────────────────────────────────────────────────────────┐
│                        UniCell                          │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              COMMAND LATCH                      │   │
│  │  (full cell config — write-once per boot)       │   │
│  │                                                 │   │
│  │  gate_state        32 bits                      │   │
│  │  input_address     32 bits                      │   │
│  │  output_address    32 bits                      │   │
│  │  auth_mask         11 bits  (HIDDEN, write-only)│   │
│  │  start_flag         1 bit   (armed/disarmed)    │   │
│  │                   ───────                       │   │
│  │  Total:           108 bits                      │   │
│  └────────────────────┬────────────────────────────┘   │
│           ↑           │                                 │
│    CMD_RECONFIGURE    │ gate_state controls             │
│    (auth checked)     ↓ NOR topology + mode flags       │
│                  ┌────────────┐                         │
│  ┌─────────┐     │            │     ┌─────────┐         │
│  │  INPUT  │────▶│  NOR TREE  │────▶│ OUTPUT  │         │
│  │  LATCH  │     │            │     │  LATCH  │         │
│  └────┬────┘     └────────────┘     └────┬────┘         │
│       │                                  │              │
│  input_address                    output_address        │
│  (from command latch)             (from command latch)  │
└───────┼──────────────────────────────────┼──────────────┘
        │                                  │
   DATA BUS IN                        DATA BUS OUT
   (Bus 2 — data only)                (Bus 2 — data only)
```

The command latch is **never reachable from the data bus**. Normal data
traffic flows only through the input/output latches. The command latch
can only be written via an auth-checked CMD_RECONFIGURE on the command bus.

---

## The Three Ports

### 1. Command Bus Port (Bus 1 — input only)

```
cmd_bus[31:0]   — command code, auth token, address mode, scope, handshake
cmd_valid       — command bus has valid data this cycle
```

The cell listens to the command bus every cycle. System commands
(CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE) are silently ignored unless
the auth token in bits 4-14 matches the cell's auth_mask.

The command bus **never carries data values**. It carries only control.

Full bit map:
```
bits  0-3:   command code
             0 = CMD_NOP
             1 = CMD_DATA_WRITE       (user+system)
             2 = CMD_SET_INPUT_ADDR   (user+system)
             3 = CMD_SET_OUTPUT_ADDR  (user+system)
             4 = CMD_RECONFIGURE      (system only — auth required)
             5 = CMD_FREEZE           (system only — auth required)
             6 = CMD_RELEASE          (system only — auth required)
             7 = CMD_COPY_DATA_TO_OUT (user+system)
             8 = CMD_COPY_DATA_TO_IN  (user+system)
             9 = CMD_PING             (anyone)
             10-15 = reserved

bits  4-14:  auth token (11 bits)
             Card-wide. Same for all cells on this card.
             Checked only on CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE.
             Silent rejection on mismatch.

bit   15:    address mode
             0 = PTT-relative (user space default)
             1 = raw system address (BIOS-Plus / system only)

bits 16-17:  scope
             00 = LOCAL
             01 = reserved (SHORE routing now implicit in address)
             10 = reserved (EXTENDED scope retired)
             11 = reserved

bits 18-21:  handshake / ACK-REQ
             0x0 = NONE    0x1 = ACK     0x2 = NAK    0x3 = BUSY
             0x4 = REQUEST 0x5 = GRANT   0x6 = DENY   0x7 = RETRY
             0x8-0xF = reserved
             Only meaningful on bridge cells. Ignored on compute cells.

bits 22-28:  sequence tag (7 bits)
             Bridge transaction packet sequence number (0..127).
             Set by sender for each packet in a bridge transaction.
             Checked at INBOUND bridge. 0 = not a bridge packet.
             Pre-ECC: carries sequence number.
             Post-ECC: carries Hamming syndrome (same check cell, stronger).

bits 29-31:  reserved — do not assign

bits 32-63:  retired — 64-bit bus extension removed. All buses are 32-bit.
```

### 2. Data Input Port (Bus 2 / Bus 3 — input)

```
bus_addr[31:0]  — target cell address (Bus 3)
bus_data[31:0]  — data payload (Bus 2)
bus_valid       — bus has valid data this cycle
```

Normal data traffic. The cell accepts data written to its `input_address`.
The data lands in the **input latch** — it never touches the command latch.

During a CMD_RECONFIGURE sequence, the config words also arrive on bus_data.
The cell's command latch loads from bus_data ONLY when:
  - A valid CMD_RECONFIGURE was seen on the command bus this cycle
  - The auth token matched (or auth_mask is 0 — bootstrap only)

Outside of a CMD_RECONFIGURE sequence, bus_data writes go to the input latch
only. There is no path from bus_data to the command latch during normal operation.

### 3. Data Output Port (Bus 2 — output)

```
out_addr[31:0]  — destination address (from command latch output_address)
out_data[31:0]  — computed result
out_valid       — cell has fired this cycle
```

The cell writes to `output_address` when it fires. The destination is taken
from the command latch — the cell program cannot change its own output address.

---

## The Command Latch — Full Register Map

The command latch holds the complete cell identity. It is loaded once per
boot (or once per reconfiguration) and cannot be changed by data traffic.

```
Register         Width   Description
─────────────────────────────────────────────────────────────────────
gate_state       32 bit  NOR topology (bits 0-10) + mode flags (bits 11-31)
input_address    32 bit  Where this cell reads its input data from
output_address   32 bit  Where this cell writes its output data to
auth_mask        11 bit  Card auth token — WRITE-ONLY, never readable
start_flag        1 bit  Armed (1) / disarmed (0)
─────────────────────────────────────────────────────────────────────
Total:          108 bit
```

### gate_state field detail

```
bits  0-10:  NOR topology (11 bits)
             Configures up to 9 NOR gates in a fixed tree.
             0x000 = GS_PASS (identity — output = input)
             0x001 = GS_NOT  (invert)
             Other patterns: see gate_states.py for full list.

bit   11:    GS_LATCH
             Hold output in latch each tick (loop variable / counter pattern).

bit   12:    GS_ONE_SHOT
             Disarm after first firing. Cell fires once then goes silent.

bit   13:    GS_INVERT_OUT
             Invert the output signal before writing to output_address.

bit   14:    GS_BROADCAST
             Write result to all cells in a range at output_address.

bit   15:    GS_SYNC_WAIT
             Wait for two sequential arrivals before firing (async merge).
             Requires input_b_address (second input source).

bit   16:    GS_LOOP_BACK
             Feed output back as next input (feedback loop).

bits 17-19:  LOOP_BACK_SRC   — source gate selector (3 bits)
bits 20-22:  LOOP_BACK_DST   — destination gate selector (3 bits)

bit   23:    reserved        — GS_ADDR_LATCH retired (64-bit addressing removed)

bits 24-28:  reserved

bit   29:    GS_PRIORITY
             Cell is scheduled first each tick (high priority path).

bit   30:    GS_TRACE
             Record to trace buffer on every fire (debug).

bit   31:    GS_BREAKPOINT
             Halt the entire array on fire (debug / Ward breakpoint).
```

---

## CMD_RECONFIGURE Sequence

This is the only way to write to the command latch.

### Prerequisites
- Valid CMD_RECONFIGURE on command bus (bits 0-3 = 4)
- Auth token in cmd_bus[14:4] must match cell's auth_mask
- Exception: if auth_mask == 0 (boot state), first RECONFIGURE is accepted
  unconditionally and sets auth_mask from the first data word

### Word sequence (arrives on bus_data, one word per cycle)

```
Cycle  Word         Content
──────────────────────────────────────────────────────────────
  0    auth_mask    bus_data[10:0] → auth_mask register
                   ONLY sent on first RECONFIGURE (auth_mask == 0)
                   On subsequent RECONFIGUREs this word is skipped.

  1    gate_state   bus_data[31:0] → command latch gate_state

  2    input_addr   bus_data[31:0] → command latch input_address

  3    output_addr  bus_data[31:0] → command latch output_address

  4    input_b_addr bus_data[31:0] → command latch input_b_address
                   GS_SYNC_WAIT cells only. Skipped otherwise.
```

After the final word is loaded, start_flag is set to 1 (armed).
The cell is live from the next tick.

### Security properties of CMD_RECONFIGURE

- Auth mismatch → entire sequence silently dropped. No words loaded.
- auth_mask is set exactly once. Subsequent RECONFIGUREs cannot change it.
- auth_mask is not readable via any bus command. No debug output for this field.
- The command latch is invisible to the data bus at all times.

---

## Data Flow During Normal Operation

Once armed, the cell operates on data only. The command latch is static.

```
Each tick:
  1. Bus controller writes data to input_address on bus_addr/bus_data
  2. Cell detects its input_address on bus_addr → captures bus_data
     into INPUT LATCH
  3. NOR tree runs combinatorially on INPUT LATCH value
     (gate topology from command latch gate_state[10:0])
  4. Mode flags applied (GS_LATCH, GS_ONE_SHOT, GS_INVERT_OUT etc.)
     (mode flags from command latch gate_state[11:31])
  5. Result written to OUTPUT LATCH
  6. Cell asserts out_valid, drives out_addr (= command latch output_address)
     and out_data (= OUTPUT LATCH value) onto the output bus
  7. If GS_ONE_SHOT: start_flag cleared → cell disarmed
```

At no point in this sequence does the NOR computation or data traffic
have any path to the command latch. The input/output latches and the
command latch are physically separate register banks.

---

## Security Isolation Model

```
WHO CAN WRITE TO:        command latch    input latch    output latch
─────────────────────────────────────────────────────────────────────
CMD_RECONFIGURE (auth)        YES              NO             NO
Normal bus write (data)        NO             YES             NO
NOR computation                NO              NO            YES
─────────────────────────────────────────────────────────────────────
```

A user process writing data to a cell's input_address has absolutely no
path to the command latch. It cannot change the cell's gate topology, its
output address, or its auth_mask — regardless of what values it writes.

An attacker who can write arbitrary values to arbitrary bus addresses
cannot reconfigure a cell without the card auth token. The worst they
can do is write garbage to a cell's input latch — which produces a
wrong computation result, detectable by Ward.

CMD_FREEZE and CMD_RELEASE also require the auth token. A user process
cannot freeze or release a cell — only BIOS-Plus holds the card token.

---

## Address Space Note

All addresses (input_address, output_address) are 32-bit.

```
0x00000000 to 0xEFFFFFFF   Local cell space  (~3.76B addresses)
0xF0000000 to 0xFFFFFFFF   Shore index zone  (~268M indexes)
```

A cell whose output_address is in the Shore index zone (top nibble = 0xF)
will have its output intercepted by the Shore and routed to the resolved
physical destination. The cell program does not need to know whether its
output goes to a local cell or crosses a card boundary.

---

## What Is NOT in the Command Latch

For completeness — things that are sometimes confused with command latch fields:

- **ECC syndrome** — not stored in command latch. Checked at bus receive time.
  The 7 ECC bits ride on the data bus packet (bus_data bits 32-38, reserved
  until Hamming SECDED is implemented). Not a cell register.

- **PTT entries** — not per-cell. PTT is a pond-level structure, not stored
  in individual cells. Cells use addresses, not names.

- **Pond type / access flags** — not per-cell. These are PondBridge registers,
  enforced at the pond boundary, not inside the cell.

- **Trace buffer** — not in the command latch. GS_TRACE flag causes the cell
  to write a record to a shared trace buffer managed by Ward. The buffer
  itself is external to the cell.

---

*This document supersedes the register layout section of
docs/archive/02_Core_Architecture.md. The archive doc has stale field
widths (64-bit addresses, _config_upper, GS_ADDR_LATCH) that are retired.*

*Last updated: 2026-05-14*
