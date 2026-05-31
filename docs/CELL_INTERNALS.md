# UniCell — Internal Structure & Register Model

*Ground truth: `fpga/verilog/unicell.v` Protocol v2.3. Last updated 2026-05-30.*
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

## Two States — BOOT and RUN

Every cell starts in **BOOT state** at power-on. A single `CMD_BOOT_COMMIT`
transaction moves it to **RUN state** permanently (until reset).

```
BOOT state:
  cell exposes baked-in CELL_ID on input_address (reset value of the register)
  boot controller finds it by CELL_ID
  sends CMD_BOOT_COMMIT:
    cmd_data[15:0]  = logical input_address
    cmd_data[23:16] = auth_mask to store in cmd_latch[18:11]
    cmd_data[31:24] = group_tag (for gate_set filtering)
  cell stores all three, clears physical_mode → RUN state

RUN state:
  cell responds to logical input_address only
  CELL_ID register fully repurposed — physical address gone
  all further commands require auth_token match
```

The boot transaction is auth-exempt (cell has no auth_mask yet). After
`CMD_BOOT_COMMIT` all commands require the auth_token field in cmd_bus[28:21].

---

## Command Bus — 32-bit Unified Word (v2.3)

The command bus is a single 32-bit word broadcast to all cells each cycle.
Cells filter by `gate_set` (if gate_enable=1) and by `auth_token`.

```
cmd_bus[31:0] layout:

bits  7:0   opcode        8-bit operation code (256 opcodes)
bit   8     gate_enable   0 = broadcast to all cells
                          1 = filter by gate_set (only matching group fires)
bits 16:9   gate_set      8-bit group tag (256 groups)
                          cell accepts command only if gate_set == its group_tag
                          set at boot via CMD_BOOT_COMMIT cmd_data[31:24]
bits 18:17  preload_sel   A-LATCH CONSTANT LOADER — table-driven, like topology presets.
                          Selector bits transmitted, constants held in cell decode table.
                          No value travels on the bus — cmd_data remains free for payload.
                          Applied after opcode logic, if auth_ok. Cell grabs the constant
                          from its internal table and loads it straight into the A latch.
                          00 = no preload
                          01 = load 0x00000000  (AND tree false side, NOR constant)
                          10 = load 0xFFFFFFFF  (NOT/XOR/XNOR constant)
                          11 = spare            (reserved — future: 0x7FFFFFFF, 0x80000000)
                          Sets a_arrived=1. Cell waits for one B arrival to fire.
                          Replaces CMD_PRELOAD + CMD_PRELOAD_HI (2 transactions, value
                          on bus) with a single bit-field, zero payload cost.
bits 20:19  shift_sel     TRANSIENT per-transaction shift modifier
                          bit 19 = shift_in_en:  shift bus_data before gate tree
                          bit 20 = shift_out_en: shift computed_output before emit
                          shift amount in cmd_data[3:0] (nibble count, 0-7)
                          shift_in  = left shift  by N×4 bits
                          shift_out = right shift by N×4 bits
bits 28:21  auth_token    8-bit token matched against stored auth_mask
                          silent reject on mismatch
                          boot bypass: auth_mask==0 → CMD_BOOT_COMMIT accepted
bits 31:29  spare         reserved, must be zero
```

`cmd_data[31:0]` carries the payload:
- `SET_INPUT_ADDR` / `SET_OUTPUT_ADDR`: `cmd_data[15:0]` = address
- `CMD_RECONFIGURE`: `cmd_data[31:0]` = full cmd_latch word (see below)
- `CMD_BOOT_COMMIT`: `cmd_data[15:0]` = logical addr, `[23:16]` = auth_mask, `[31:24]` = group_tag
- shift ops: `cmd_data[3:0]` = nibble shift count

---

## Command Latch — 32 bits (cell internal state)

One word defines the complete cell identity. Loaded by `CMD_RECONFIGURE`.
**This is NOT the command bus** — it is the cell's internal register.

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
             0x030 = ZERO            always 0x00000000
             0x0B0 = ONE             always 0xFFFFFFFF

bit   10    edge_mode     0 = STANDARD (two-arrival, default)
                          1 = EDGE (transition detection on bus_data[0])

bits 18:11  auth_mask     8-bit security token. Write-once at boot.
                          Stored by CMD_BOOT_COMMIT or CMD_RECONFIGURE.
                          Silent rejection on cmd_bus auth_token mismatch.
                          WRITE-ONLY — zeroed in debug output and ICM files.

bit   19    output_set    1 = output address configured, cell may fire
                          0 = cell cannot fire (prevents bus pollution at boot)
                          Set by CMD_RECONFIGURE or CMD_SET_OUTPUT_ADDR.

bit   20    latch_A_dis   1 = disable A latch store
                          Effect: live bus_data flows straight through (PASS(B))

bit   21    latch_B_dis   1 = disable B arrival trigger
                          Effect: stored a_data rebroadcast on any arrival (PASS(A))

Latch disable truth table:
  latch_A_dis=0, latch_B_dis=0 — normal two-arrival gate (default)
  latch_A_dis=1, latch_B_dis=0 — PASS(B): live value straight through
  latch_A_dis=0, latch_B_dis=1 — PASS(A): stored value rebroadcast on trigger
  latch_A_dis=1, latch_B_dis=1 — dead cell: nothing fires

bit   22    start_flag    1 = armed (live, processes data bus)
                          0 = disarmed (ignores data bus)
                          Set by CMD_RECONFIGURE. Cleared by CMD_FREEZE or one_shot.

bits 24:23  dtype         00 = NUMERIC   unsigned integer (default)
                          01 = SIGNED    two's complement
                          10 = ALPHA     8-bit character
                          11 = DATETIME  Unix timestamp
                          Metadata for Ward/bridge — gate tree unaffected.

bit   25    invert_out    1 = invert computed output at drain time
                          (EDGE mode: selects negedge when edge_mode=1)

bit   26    latch_in      1 = hold a_arrived set after firing
                          single arrival fires on next tick (memory/counter mode)
                          requires ENABLE_LATCH_IN=1 at synthesis

bit   27    priority      1 = schedule this cell first each tick

bit   28    trace         1 = log every fire to Ward trace buffer

bit   29    breakpoint    1 = halt array on fire

bit   30    one_shot      1 = fire once then clear start_flag (disarm)

bit   31    loop_back     1 = feed computed output back into a_data
                          implements counters, accumulators, recurrent state
```

**No reserved bits.** All 32 bits assigned. preload_sel and shift_sel
are command bus transient modifiers — they consume NO cmd_latch bits.

### CMD_RECONFIGURE payload mapping (cmd_data → cmd_latch)

```
cmd_data[9:0]   → cmd_latch[9:0]    topology
cmd_data[10]    → cmd_latch[10]     edge_mode
cmd_data[11]    → cmd_latch[22]     start_flag
cmd_data[12]    → cmd_latch[20]     latch_A_dis
cmd_data[13]    → cmd_latch[21]     latch_B_dis
cmd_data[15:14] → cmd_latch[24:23]  dtype
cmd_data[16]    → cmd_latch[25]     invert_out
cmd_data[17]    → cmd_latch[26]     latch_in
cmd_data[18]    → cmd_latch[27]     priority
cmd_data[19]    → cmd_latch[28]     trace
cmd_data[20]    → cmd_latch[29]     breakpoint
cmd_data[21]    → cmd_latch[30]     one_shot
cmd_data[22]    → cmd_latch[31]     loop_back
cmd_data[30:23] → cmd_latch[18:11]  auth_mask
```

---

## Opcode Table

```
0x00  CMD_NOP              no operation
0x01  CMD_DATA_WRITE       inject data onto bus (no auth needed)
0x02  CMD_SET_INPUT_ADDR   cmd_data[15:0] → input_address (auth)
0x03  CMD_SET_OUTPUT_ADDR  cmd_data[15:0] → output_address, output_set=1 (auth)
0x04  CMD_RECONFIGURE      cmd_data[31:0] → cmd_latch (auth)
0x05  CMD_FREEZE           disarm cell, suppress output (auth)
0x06  CMD_RELEASE          re-arm cell (auth)
0x07  CMD_BOOT_COMMIT      BOOT STATE ONLY — no auth required
                           cmd_data[15:0]  = logical input_address
                           cmd_data[23:16] = auth_mask → cmd_latch[18:11]
                           cmd_data[31:24] = group_tag (for gate_set)
                           clears physical_mode → RUN state
0x09  CMD_PING             no-op response
0x0A  CMD_LATCH_IN_ON      set latch_in bit (auth)
0x0B  CMD_LATCH_IN_OFF     clear latch_in, reset a_arrived (auth)
0x0C  CMD_MEM_CALL         latch_in+one_shot+rearm atomically (auth)
0x0D  CMD_REARM            rearm one-shot, clear a_arrived (auth)
0x0E  CMD_SET_LOGICAL      set logical addr, clear physical_mode (auth) [legacy]
0x0F  CMD_PRELOAD          DEPRECATED — use preload_sel bits 18:17 on cmd_bus
0x10  CMD_CLEAR_ARRIVED    clear a_arrived + a_data (auth)
0x11  CMD_RESET_CELL       clear arrived+data+one_shot_fired, rearm (auth)
0x12  CMD_SWAP_AB          load a_data from cmd_data[12:0], set a_arrived (auth)
0x13  CMD_CAPTURE_REARM    fire output + rearm one_shot (auth)
0x14  CMD_SET_TOPO         write topology bits only (auth)
0x15  CMD_SET_INVERT       toggle invert_out (auth)
0x16  CMD_PRELOAD_HI       DEPRECATED — use preload_sel bits 18:17 on cmd_bus

Topology presets (cold=even opcode, armed=odd opcode):
0x30/31  CMD_TOPO_PASS_A   topology=0x000, latch_in=1
0x32/33  CMD_TOPO_NOT_A    topology=0x001, latch_in=1
0x34/35  CMD_TOPO_NOR      topology=0x004
0x36/37  CMD_TOPO_AND      topology=0x007
0x38/39  CMD_TOPO_OR       topology=0x024
0x3A/3B  CMD_TOPO_NAND     topology=0x027
0x3C/3D  CMD_TOPO_PASS_B   topology=0x02C
0x3E/3F  CMD_TOPO_XNOR     topology=0x03C
0x40/41  CMD_TOPO_XOR      topology=0x0BC
0x42/43  CMD_TOPO_ZERO     topology=0x030, latch_in=1
0x44/45  CMD_TOPO_ONE      topology=0x0B0, latch_in=1
```

---

## Gate Tree (NOR topology)

The 9-gate NOR tree all topology values draw from:

```
g0 = NOR(A,A)   = NOT(A)
g1 = NOR(B,B)   = NOT(B)
g2 = NOR(g0,g1) = AND(A,B)
g3 = NOR(g2,g2) = NAND(A,B)
g4 = NOR(A,B)
g5 = NOR(g4,g4) = OR(A,B)
g6 = NOR(A,g4)
g7 = NOR(B,g4)
g8 = NOR(g6,g7) = XNOR(A,B)
g9 = NOR(g8,g8) = XOR(A,B)
```

A = `a_data` (first arrival, stored). B = live `bus_data` (second arrival).
All operations are 32-bit wide — gate tree operates bitwise across full word.
`invert_out` (cmd_latch[25]) inverts output at drain time, not on data path.

### preload_sel — A-latch constant loader (cmd_bus[18:17])

Works identically to topology preset opcodes (0x30–0x45): selector bits
transmitted, constants held in the cell's internal decode table. No constant
value ever travels on the command bus. cmd_data remains free for the actual
command payload.

```
preload_sel 00 → no preload (A latch unchanged)
preload_sel 01 → a_data = 0x00000000, a_arrived = 1
preload_sel 10 → a_data = 0xFFFFFFFF, a_arrived = 1
preload_sel 11 → spare
```

The constant loads straight into the A latch. Cell then waits for one B
arrival to fire — identical to a normal first-arrival store, but sourced
from the internal table rather than the bus.

```verilog
// Silicon (unicell.v) — pure table lookup, no bus data involved:
if (auth_ok && preload_sel != 2'b00) begin
    a_data    <= (preload_sel == 2'b10) ? 32'hFFFFFFFF : 32'h00000000;
    a_arrived <= 1'b1;
end
```

This replaces CMD_PRELOAD + CMD_PRELOAD_HI (2 transactions, value on bus)
with a single 2-bit field, zero payload cost, value cannot be corrupted
in transit.

### Shift modifiers (cmd_bus transient)

When `shift_in_en=1` (cmd_bus[19]), `bus_data` is shifted left by
`cmd_data[3:0]` × 4 bits before entering the gate tree.

When `shift_out_en=1` (cmd_bus[20]), `computed_output` is shifted right by
`cmd_data[3:0]` × 4 bits before loading into the output buffer.

Shift amount is nibble-aligned (0-7 nibbles = 0-28 bits). Non-nibble-aligned
shifts require up to 3 extra cells for residual bits.

---

## STANDARD Mode — Two-Arrival Detail

```verilog
// First arrival: store A
if (bus_hit && !a_arrived && !edge_mode && !latch_A_dis) begin
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

`latch_in=1` (cmd_latch[26]): `a_arrived` stays set after firing,
`a_data` updates to new arrival. Every subsequent single arrival fires.
Requires `ENABLE_LATCH_IN=1` at synthesis (compiled out on iCEBreaker build).

---

## EDGE Mode — Transition Detection

```
edge_mode=1 (cmd_latch[10]):
  Cell monitors bus_data[0] each cycle when bus_hit is true.
  prev_data register holds last seen bit 0.

  posedge (invert_out=0): fires when prev_data=0 AND bus_data[0]=1
  negedge (invert_out=1): fires when prev_data=1 AND bus_data[0]=0

  On edge detected:
    Full 32-bit bus_data enters gate tree (not just bit 0)
  No two-arrival requirement — single transition fires.
```

---

## Output Timing — odd_phase / negedge emulation

iCE40 does not support negedge flip-flops. The cell uses an `odd_phase`
toggle to emulate half-cycle granularity:

```
Even phase: gate tree fires, result loads into out_buf
Odd phase:  out_buf drains to out_addr/out_data/out_valid
```

One extra half-cycle between fire and output. Does not affect correctness.

---

## one_shot and loop_back

**one_shot (cmd_latch[30]):**
```
Fire → computed_output → out_buf → bus
     → one_shot_fired = 1
     → start_flag = 0    (cell disarms)
Cell ignores all further bus traffic until CMD_REARM or CMD_RESET_CELL.
```

**loop_back (cmd_latch[31]):**
```
Fire → computed_output → out_buf → bus
                       → a_data  (fed back internally)
Next arrival: a_data = previous computed_output
Implements: counters, accumulators, recurrent state
```

`loop_back` and `latch_in` combinations:
- `latch_in=1, loop_back=0`: a_data updates to new arrival each fire
- `latch_in=0, loop_back=1`: a_data updates to computed output each fire
- `latch_in=1, loop_back=1`: a_data gets computed_output AND a_arrived stays set

---

## Address Space

### Physical vs Logical Address

```
Physical address:  CELL_ID parameter — baked in at synthesis.
                   Reset value of input_address register.
                   Used ONLY during BOOT state.
                   Gone after CMD_BOOT_COMMIT.

Logical address:   input_address register — assigned by CMD_BOOT_COMMIT.
                   Fully mutable at runtime via CMD_SET_INPUT_ADDR.
                   This is what the cell responds to for all data traffic.
```

The same 16-bit register serves both purposes at different times.
No extra silicon — CELL_ID is just the reset value.

### Cell address space (32-bit logical)

```
0x00000000 - 0xEFFFFFFF   Cell computation space     (~3.76B addresses)
0xF0000000 - 0xFFFBFFFF   OS / Shore reserved        (~16M addresses)
0xFFFC0000 - 0xFFFFFFFF   Extended addressing zone   (~262K addresses)
                           Shore intercepts, translates to 64-bit global
```

iCEBreaker uses 16-bit addresses (timing concession). Kintex-7 uses full 32-bit.

---

## Silicon Status (iCEBreaker, May 2026)

| Feature            | Status        | Notes                              |
|--------------------|---------------|------------------------------------|
| STANDARD two-arrival | ✅ Confirmed | 15/15 gate tests                   |
| EDGE posedge/negedge | ✅ Confirmed | test_32bit_gate step 10            |
| loop_back          | ✅ Confirmed  | NOT oscillator test                |
| one_shot           | ✅ Confirmed  | sequence lock cell 7               |
| latch_in           | ⚠️ Compiled out | ENABLE_LATCH_IN=0 on iCEBreaker  |
| invert_out         | ✅ Confirmed  | test_32bit_gate step 9             |
| gate_set filtering | ⏳ Pending    | v2.3 feature, not yet tested       |
| preload_sel        | ⏳ Pending    | v2.3 feature, replaces CMD_PRELOAD |
| shift_in/out       | ⏳ Pending    | v2.3 feature, nibble-aligned       |
| CMD_BOOT_COMMIT    | ⏳ Pending    | v2.3 boot sequence                 |
| 32-bit addresses   | ⏳ Pending    | 16-bit only in current build       |
| 32-bit gate ops    | ✅ Confirmed  | All ops full 32-bit width          |
