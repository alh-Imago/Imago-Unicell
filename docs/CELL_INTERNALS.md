# UniCell — Internal Structure & Register Model

*Ground truth: `fpga/verilog/unicell.v`. Last updated 2026-05-20.*
*If this doc and the Verilog disagree, the Verilog wins.*

---

## Fundamental Operating Model

Every UniCell is a NOR gate tree. It requires **two data arrivals** at the
same `input_address` before it fires — unless configured as an edge cell
(which fires on a bus transition instead).

```
STANDARD mode (edge_mode=0):
  First arrival  → stored in a_data, a_arrived=True  — NO output
  Second arrival → fires gate(a_data, bus_data)      — output to output_address

EDGE mode (edge_mode=1):
  Monitors bus_data[0] each cycle
  posedge (invert_out=0): fires on 0→1 transition on bit 0
  negedge (invert_out=1): fires on 1→0 transition on bit 0
  Full 32-bit bus_data passes through the gate tree when edge detected
  Single arrival fires — no two-arrival requirement
```

Validated on iCEBreaker silicon, May 2026.

---

## Command Latch — 32 bits (ground truth from unicell.v)

One word defines the complete cell identity.

```
bits  9:0   topology      NOR gate selection (10 bits, one-hot)
             0x000 = PASS(A)         identity
             0x001 = NOT(A)          invert A
             0x002 = NOT(B)          invert B
             0x004 = NOR(A,B)        baseline NOR
             0x007 = AND(A,B)
             0x024 = OR(A,B)
             0x027 = NAND(A,B)
             0x03C = XNOR(A,B)
             0x02C = PASS(B)         pass trigger value
             0x0BC = XOR(A,B)
             0x030 = ZERO            always 0
             0x0B0 = ONE             always 0xFFFFFFFF

bit   10    edge_mode     0 = STANDARD (two-arrival)
                          1 = EDGE (transition detection on bus_data[0])
                          Note: was named sync_wait in early docs.
                          The two-arrival model is now the default —
                          this bit selects the ALTERNATIVE (edge) mode.

bits 21:11  auth_mask     11-bit security token. Write-once at boot.
                          Silent rejection on CMD mismatch.
                          WRITE-ONLY — zeroed in debug output.

bit   22    start_flag    1 = armed (live, processes data bus)
                          0 = disarmed (ignores data bus)
                          Set by CMD_RECONFIGURE. Cleared by CMD_FREEZE
                          or one_shot disarm.

bits 24:23  dtype         00 = NUMERIC   unsigned integer (default)
                          01 = SIGNED    two's complement
                          10 = ALPHA     8-bit character
                          11 = DATETIME  Unix timestamp
                          Readable by Ward/bridge without PTT lookup.

bits 26:25  ctype         Cell type (stored, informs scheduler)
                          00 = STANDARD  combinatorial
                          01 = LATCH     holds output
                          10 = POSEDGE   edge-triggered rising
                          11 = NEGEDGE   edge-triggered falling

bit   27    priority      0 = normal scheduling
                          1 = scheduled first each tick

bit   28    trace         0 = silent
                          1 = log every fire to Ward trace buffer

bit   29    breakpoint    0 = normal
                          1 = halt array on fire

bit   30    one_shot      0 = normal — re-arms after firing
                          1 = fire once, then clear start_flag (disarm)

bit   31    loop_back     0 = normal
                          1 = feed computed output back into a_data
                            (for counters, accumulators)

bits 31:30  NOTE: one_shot (bit 30) and loop_back (bit 31) are NOT
                  reserved. Earlier versions of this doc incorrectly
                  listed them as reserved. They are active features.
```

**No reserved bits.** All 32 bits are assigned. The earlier "bits 30-31
reserved" entry in ARCHITECTURE.md was wrong and has been removed.

---

## Why One Word Matters

The entire cell identity fits in a single 32-bit bus transaction:
- Array controller reads cell state in one cycle
- Ward health checks require no multi-word reads
- Bridge depth decisions use dtype field directly — no PTT lookup
- `.icm` files store one config word + address pair per cell
- CMD_RECONFIGURE loads it in one word

---

## Command Bus Codes

```
bits [3:0] of cmd_bus:

0  CMD_NOP              — no operation
2  CMD_SET_INPUT_ADDR   — cmd_data[15:0] → input_address
3  CMD_SET_OUTPUT_ADDR  — cmd_data[15:0] → output_address
4  CMD_RECONFIGURE      — cmd_data[31:0] → cmd_latch, arms cell
5  CMD_FREEZE           — disarm, suppress output (auth required)
6  CMD_RELEASE          — re-arm (auth required)
9  CMD_PING             — accepted, no response in baseline
```

Auth token in cmd_bus[14:4]. Boot bypass: if stored auth_mask == 0,
first CMD_RECONFIGURE accepted unconditionally and sets the mask.

---

## STANDARD Mode — Two-Arrival Detail

```verilog
// First arrival: store A
if (bus_hit && !a_arrived && !edge_mode) begin
    a_data    <= bus_data;
    a_arrived <= 1'b1;
end

// Second arrival: fire
wire new_data = bus_hit && a_arrived;   // (simplified)
if (new_data) begin
    out_buf_data  <= computed_output;   // gate(a_data, bus_data)
    a_arrived     <= 1'b0;              // reset for next pair
end
```

`latch_in=1` (bit 26) changes the fire handler: `a_arrived` stays True
after firing and `a_data` updates to the new arrival. So every subsequent
single arrival fires the gate. This requires `ENABLE_LATCH_IN=1` to be
set at synthesis time — it is compiled out on the current iCEBreaker build.

---

## EDGE Mode — Transition Detection

```
edge_mode=1 (bit 10):

  Cell monitors bus_data[0] each cycle when bus_hit is true.
  prev_data register holds last seen bit 0.

  posedge (invert_out=0): fires when prev_data=0 AND bus_data[0]=1
  negedge (invert_out=1): fires when prev_data=1 AND bus_data[0]=0

  On edge detected:
    Full 32-bit bus_data enters gate tree (not just bit 0)
    This lets an edge cell detect a strobe on bit 0 while
    propagating a full 32-bit payload through the gate tree.

  No two-arrival requirement — single transition fires.
  No a_data / a_arrived used.
```

The essential difference from STANDARD: timing is determined by the
**direction of change** on bit 0, not by counting arrivals. Useful for
interrupt-like behaviour and precise timing control.

---

## Gate Tree (NOR topology)

The 9-gate tree that all topology values draw from:

```
g0 = NOR(A,A)  = NOT(A)
g1 = NOR(B,B)  = NOT(B)
g2 = NOR(g0,g1) = AND(A,B)
g3 = NOR(g2,g2) = NAND(A,B)
g4 = NOR(A,B)
g5 = NOR(g4,g4) = OR(A,B)
g6 = NOR(A,g4)
g7 = NOR(B,g4)
g8 = NOR(g6,g7) = XNOR(A,B)
g9 = NOR(g8,g8) = XOR(A,B)
```

A = `a_data` (first arrival stored), B = live `bus_data` (second arrival).
For single-input ops: compiler ensures A == B (send same value twice).
`invert_out` (bit 25) inverts the output at drain time — not on the
data path — so it does not affect timing.

---

## Output Timing — odd_phase / negedge emulation

iCE40 does not support negedge flip-flops. The cell uses an `odd_phase`
toggle to emulate half-cycle granularity:

```
Even phase: gate tree fires, result loads into out_buf
Odd phase:  out_buf drains to out_addr/out_data/out_valid
```

One extra half-cycle between fire and output. Does not affect correctness.
Kintex-7 (6-input LUTs, better timing) may not need this.

---

## Address Space

**Architecture spec:** 32-bit address space (`bus_addr[31:0]`).

**Current iCEBreaker bitstream:** 16-bit matching only.
`input_address` and `output_address` are `reg [15:0]`.
Bus hit uses `bus_addr[15:0] == input_address`.

This is a timing concession for 24 MHz on iCE40 4-input LUTs —
a 32-bit comparator needs 5 LUTs on iCE40 vs 3 on Kintex-7 (6-input LUTs).

**Logical address map (architectural intent):**

```
0x00000000 - 0xEFFFFFFF   Cell computation space  (~3.76B addresses)
0xF0000000 - 0xFFEFFFFF   OS reserved             (~15M addresses)
0xFFF00000 - 0xFFFFFFFF   Shore / PTT bus range   (~1M addresses)
```

The division is logical — enforced by the OS layer (Pond, Shore, Ward),
not by hardware. Any cell can write any address. Security is at the bridge.

**Mechanism for actual use:** Ponds are allocated a base address and a
region size by PondManager. All cell addresses within a Pond are offset
from that base. The UART bridge adds the base automatically. Shore maps
pond names to base addresses. The address space is flat — hierarchy is
a software abstraction above a flat bus.

Full 32-bit address validation is pending. Plan:
- Test 1 (current): 16-bit, 4 cells, 24 MHz — functional bring-up ✅
- Test 2 (pending): 32-bit, 2-3 cells, timing check on iCEBreaker
- Test 3: Kintex-7 full 32-bit at 200 MHz

---

## one_shot and loop_back

**one_shot (bit 30):**
```
Fire → computed_output → out_buf → bus
     → one_shot_fired = 1
     → start_flag = 0    (cell disarms)
Cell ignores all further bus traffic until CMD_RECONFIGURE.
```

**loop_back (bit 31):**
```
Fire → computed_output → out_buf → bus
                       → a_data  (fed back internally)
Next arrival: a_data = previous computed_output
Implements: counters, accumulators, recurrent state
```

`loop_back` and `latch_in` can coexist:
- `latch_in=1, loop_back=0`: a_data updates to new arrival each fire
- `latch_in=0, loop_back=1`: a_data updates to computed output each fire
- `latch_in=1, loop_back=1`: both — a_data gets computed_output AND a_arrived stays set

---

## Memory — NOTE: Needs Rethinking

The current memory model (latch_in + loop_back) has an open question:

**The problem:** Latch re-emission (`latch_reemit`) fires to `output_address`
every cycle — but the bus is shared. If no other cell is listening on that
address with a fresh first-arrival slot, the re-emission is wasted. If another
cell IS listening, it gets an unsolicited second arrival and fires spuriously.

**The constraint:** There are no free bits on the bus. Every bus transaction
at an address is seen by all cells listening on that address. There is no
"this is a re-emission" flag on the bus — it looks identical to a host write.

**What this means for memory:**
- A memory cell that re-emits every cycle will spuriously trigger any
  downstream cell that has stored a first arrival at the re-emission address
- Reliable memory requires careful address discipline or a dedicated
  "memory read" protocol (trigger cell sends a read request)
- The three-cell pattern (memory + tap + trigger) may need a 4th cell
  to isolate the memory re-emission from the trigger pathway

**TODO:** Revisit the memory cell model. The correct implementation may
require a different approach at the hardware level — possibly a dedicated
`mem_out_address` separate from the bus, or a re-emission inhibit flag
that prevents re-emission from looking like a host write to downstream cells.
Recorded here for the next architecture session.

---

## Silicon Status (iCEBreaker, May 2026)

| Feature | Status | Notes |
|---------|--------|-------|
| STANDARD two-arrival | ✅ Confirmed | 15/15 gate tests |
| EDGE posedge/negedge | ✅ Confirmed | test_32bit_gate step 10 |
| loop_back | ✅ Confirmed | NOT oscillator test |
| one_shot | ✅ Confirmed | sequence lock cell 7 |
| latch_in | ⚠️ Compiled out | ENABLE_LATCH_IN=0 on iCEBreaker |
| invert_out | ✅ Confirmed | test_32bit_gate step 9 |
| 32-bit addresses | ⏳ Pending | 16-bit only in current build |
| 32-bit gate ops | ✅ Confirmed | All ops full 32-bit width |


---

## Full Command Bus Specification

The command bus has two layers: the **UART packet** (host to bridge) and
the **cmd_bus word** (bridge to cell array). The bridge translates one into
the other.

---

### Layer 1 — UART Packet (host → bridge)

Single-byte opcode followed by payload. All multi-byte fields are big-endian.

```
Opcode 0x01 — DATA WRITE (13 bytes total)
  [0]      0x01              opcode
  [1:4]    cmd_word          32-bit command word (see cmd_bus format below)
  [5:8]    addr              32-bit target address
  [9:12]   data              32-bit data value

Opcode 0x02 — STATUS READ (9 bytes total)
  [0]      0x02              opcode
  [1:8]    (payload)         status request

Opcode 0x03 — ARRAY RESET (1 byte)
  [0]      0x03              assert array_rst for one cycle

Opcode 0x04 — STATUS (1 byte, bridge responds)
  [0]      0x04

Opcode 0x06 — FREEZE (1 byte)
  [0]      0x06              assert array_freeze — data bus inactive

Opcode 0x07 — THAW / RELEASE (1 byte)
  [0]      0x07              deassert array_freeze — array live

Note: freeze (0x06) and thaw (0x07) are UART-level array-wide controls.
They are NOT the same as CMD_FREEZE (code 5) / CMD_RELEASE (code 6) which
operate at the per-cell command bus level.
```

---

### Layer 2 — cmd_bus Word (bridge → cell array, 32 bits)

Built by the Python `mk_cmd()` function. Passed as `cpu_cmd` from bridge
to array. All cells see every cmd_bus word — they filter by `cell_id`.

```
bits  3:0   command code     Cell operation to perform
             0  = CMD_NOP
             1  = CMD_DATA   (data write — goes to data bus not cmd bus)
             2  = CMD_SET_INPUT_ADDR   — cmd_data[15:0] → input_address
             3  = CMD_SET_OUTPUT_ADDR  — cmd_data[15:0] → output_address
             4  = CMD_RECONFIGURE      — cmd_data[31:0] → cmd_latch
             5  = CMD_FREEZE           — disarm this cell
             6  = CMD_RELEASE          — re-arm this cell
             9  = CMD_PING

bits 14:4   auth_token       11-bit security token
             Must match cell's stored auth_mask to execute system commands
             (CMD_RECONFIGURE, CMD_FREEZE, CMD_RELEASE).
             Boot bypass: if cell's auth_mask == 0, first RECONFIGURE
             accepted unconditionally and sets the mask permanently.

bit  15     address_mode     Always 1 from host (raw address mode).
             0 = PTT-relative (reserved for future OS use)
             1 = raw bus address

bits 26:16  cell_id          11-bit target cell identifier
             Commands SET_INPUT_ADDR, SET_OUTPUT_ADDR, RECONFIGURE
             are only accepted by the cell whose CELL_ID matches.
             Use 0x7FF as broadcast sentinel:
             FREEZE, RELEASE, PING reach all cells.
             DATA (code 1) is not a cell command — it goes on the data bus.

bits 31:27  (unused in current baseline)
```

**Python mk_cmd() for reference:**
```python
BROADCAST = 0x7FF

def mk_cmd(code, auth=0, cell_id=BROADCAST):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15) | ((cell_id & 0x7FF) << 16)

# Examples:
CMD_DATA            = mk_cmd(1)              # data write, broadcast
CMD_SET_INPUT_ADDR  = mk_cmd(2, AUTH, cell)  # targeted to cell N
CMD_SET_OUTPUT_ADDR = mk_cmd(3, AUTH, cell)
CMD_RECONFIGURE     = mk_cmd(4, AUTH, cell)
```

---

### Layer 3 — Configure Sequence (3 commands per cell)

To configure one cell (input addr, output addr, topology + flags):

```python
tx(mk_cmd(2, AUTH, cell_id), 0, in_addr)    # SET_INPUT_ADDR
tx(mk_cmd(3, AUTH, cell_id), 0, out_addr)   # SET_OUTPUT_ADDR
tx(mk_cmd(4, AUTH, cell_id), 0, cfg_word)   # RECONFIGURE (cmd_latch)
```

`cfg_word` is the full 32-bit command latch word. Built by `mk_cfg()`:

```python
def mk_cfg(topo, auth_mask=0, one_shot=0, latch_in=0,
           invert_out=0, edge_mode=0, loop_back=0):
    w  = (topo & 0x3FF)            # bits  9:0  topology
    w |= (0 if not edge_mode else 1) << 10   # bit  10  edge_mode
    w |= (auth_mask & 0x7FF) << 11 # bits 21:11 auth_mask
    w |= 1 << 22                   # bit  22  start_flag (arm on configure)
    # bits 24:23 dtype — set separately if needed
    w |= (1 if invert_out else 0) << 25  # bit 25 invert_out
    w |= (1 if latch_in   else 0) << 26  # bit 26 latch_in
    # bit 27 priority, 28 trace, 29 breakpoint — set separately if needed
    w |= (1 if one_shot   else 0) << 30  # bit 30 one_shot
    w |= (1 if loop_back  else 0) << 31  # bit 31 loop_back
    return w
```

CMD_RECONFIGURE also:
- Sets `start_flag` (arms the cell)
- Clears `one_shot_fired`
- Clears `a_arrived`
- Clears `frozen`

---

### Data Write vs Command Write

The distinction matters:

```
Data write:   tx(CMD_DATA, address, value)
              Goes on the DATA bus (bus_addr=address, bus_data=value)
              Seen by any cell whose input_address matches
              Subject to freeze (bus_hit = !frozen && ...)

Command write: tx(mk_cmd(4, AUTH, cell_id), 0, cfg_word)
               Goes on the COMMAND bus (cmd_bus=cmd_word, cmd_data=cfg_word)
               Only accepted by the cell matching cell_id
               NOT subject to freeze — config commands always land
```

This is why **preload data writes must happen while thawed** — they go on
the data bus which is blocked by freeze. Configuration commands land
regardless of freeze state.
