# Imago UniCell — Architecture

*Current as of v2, May 2026. See [INDEX.md](INDEX.md) for the full document map.*

---

## Foundations

### The Constraint

NOR is universal. Any Boolean function can be expressed using only NOR gates.
This is a theorem, not a design choice. The Imago UniCell project asked: what
computing architecture emerges if you take that constraint seriously, all the
way down?

The answer is a single cell type. One cell can become AND, OR, XOR, NAND,
XNOR, NOR, NOT, PASS, MUX, SELECT, LATCH, or LOOP — selected by a 32-bit
configuration word called `gate_state`. One cell, one clock cycle, one result.

There is no CPU, no ALU, no instruction set, no registers, no program counter.
Programs are cell networks — wirings — through which data flows and results
emerge at known addresses after a deterministic number of ticks. Compiling a
function means constructing a network where the correct answer falls out the
other end.

**The constraint is the point.** It forced every decision: the bus, the OS,
the type system, the portability story. Relaxing it would produce a faster
design for some workloads and a worse design overall.

---

## The Cell

### gate_state — 32 bits

```
bits  0-9:   topology        — NOR gate tree selection (10 bits)
bit  10:     GS_EDGE_MODE    — fire on 0→1 data transition (edge trigger)
bits 11-22:  (reserved)
bits 23-24:  GS_DTYPE        — 00=NUMERIC, 01=SIGNED, 10=ALPHA, 11=DATETIME
bit  25:     GS_LATCH_IN     — a_arrived held after fire (single-arrival mode)
             Used for: relay cells, NOT cells, sentry cells
bits 26-27:  GS_OUT_POSEDGE/NEGEDGE — output edge type
bit  28:     GS_PRIORITY     — priority cell (Ward scheduling)
bit  29:     GS_TRACE        — log every firing to debug buffer
bit  30:     GS_BREAKPOINT   — halt array when this cell fires
bit  31:     GS_ONE_SHOT     — disarm after first firing (self-clearing)
bit  32:     GS_LOOP_BACK    — feed output back to own input each tick

Note: GS_SYNC_WAIT (old bit 15) is RETIRED. Two-arrival is now the default
for all cells. A stores on first arrival, B triggers fire on second arrival.
For single-arrival (NOT, relay): set GS_LATCH_IN. For preloaded-A pattern:
use preload_sel bits in cmd_bus (v2.3) or CMD_PRELOAD (v2.2 legacy iCEBreaker).
```

### Gate functions (v2, all one cell one cycle)

| Function | gate_state | Notes |
|----------|------------|-------|
| NOT | GS_NOT (bit 0) | single-input |
| PASS | 0x00000000 | wire / delay cell |
| AND | GS_AND | two-arrival: A stored, B triggers |
| OR | GS_OR | two-arrival: A stored, B triggers |
| XOR | GS_XOR | two-arrival: A stored, B triggers |
| NAND | GS_NAND | two-arrival: A stored, B triggers |
| XNOR | GS_XNOR | two-arrival: A stored, B triggers |
| NOR | GS_NOR | two-arrival: A stored, B triggers |
| RELAY | GS_PASS_B \| GS_LATCH_IN | routes B to A-side of downstream |
| COUNTER | GS_LOOP_BACK \| GS_LATCH_IN | feedback path with latch |
| ONE_SHOT | GS_ONE_SHOT | fires once then disarms |
| PRELOADED | any \| preload_sel | A pre-loaded via preload_sel (v2.3) or CMD_PRELOAD (v2.2), fires on first B |

### The two-input model (v2)

Two-input gates (AND, OR, XOR, NAND, XNOR) receive inputs on two different
clock edges within the same cycle:

```
posedge:  A arrives at input_address    → stored in input register
negedge:  B arrives at input_b_address  → gate tree fires
                                           result → output buffer
posedge+1: output buffer → bus          (if GS_OUT_POSEDGE set)
```

This gives the downstream cell a full half-cycle of settling time between
receiving A (posedge) and B (negedge). No timing violations. No pad cells
needed between stages of different depth. The compiler sets `GS_OUT_POSEDGE`
on all emitted cells by default.

---

## The Bus

The wired-OR bus is the architecture. Every cell writes to its `output_address`.
When two cells write the same address in the same tick, the result is OR of
their values — naturally, in hardware, with no arbitration, no collision, no
error.

This is not an approximation or a simplification. It is exact. Two NOT cells
sharing an output address produce NAND. One cell writing 0 and another writing
1 produce 1. The bus is the computing surface.

**Consequences:**

- Fan-in is free. Any number of cells can write to the same address. The bus
  ORs them all.
- Fan-out is free. Any number of cells can read from the same address. They
  all see the same value.
- NOR is free. Put a NOT cell after a wired-OR to get NOR of all writers.
  This is why the architecture is NOR-universal without multi-cell chains.

---

## Design Scale

The architecture is dimensioned for a target far above any bring-up board, and
that target is what makes every addressing and boot decision below mandatory
rather than stylistic:

| Level  | Holds                | Approx. cell count |
|--------|----------------------|--------------------|
| Block  | ~65,000 cells        | ~6.5e4             |
| Die    | ~115,000 blocks      | ~7.5e9             |
| Card   | 150 dies             | ~1.1e12            |
| Server | 8 cards              | ~9e12              |

Consequences that drive the rest of this document:

- **Flat local address, hierarchy above the cell.** A global coordinate cannot
  live in ~1e13 cells. Each cell holds only its local flat address; block → die →
  card → server each strip their own prefix on the way down. The cell latch never
  grows with scale — this is why richness lives in the layers above the cell, not
  in more cell bits.
- **Defects are certain, not rare.** At billions of cells per die, yield demands
  the substrate be mapped around dead cells. The boot walk health-checks every
  cell and records failures in a bad-cell table; the block base must be
  relocatable so the controller assigns ranges and routes around damage. No cell
  is ever hand-placed.
- **Bridges are dumb wire; the address is the route.** No routing fabric can make
  decisions across ~1e13 endpoints. Destination address carries the routing,
  resolved hierarchically; Shore translates across boundaries.
- **The serial boot walk is acceptable.** It is a one-time bring-up cost
  amortised across an astronomical number of compute elements.

The 448-cell FPGA bring-up is a proof of this structure at 1/20,000,000,000 scale.

---

## Address Space

### Cell view — 32-bit space, 16-bit local

A cell's address **space** is 32 bits, but its **local matching is 16 bits**. These are
not in conflict — they are the two halves of a deliberate partition:

```
bits 31:16   block_id   high 16 — INTER-block: the BRIDGE's field
bits 15:0    cell_id    low 16  — INTRA-block: the cell's own bus (direct, fast)
```

- **Low 16 = cell_id.** The cell matches here (`addr_match` compares 16 bits), and the
  block-local bus carries only these 16 bits. A 256×256 block is exactly 65,536 cells =
  exactly 16 bits, so the low half names every cell on the block bus with none to spare
  and none wasted. This is the fast path: intra-block references never leave the bus,
  never touch a bridge.
- **High 16 = block_id — the bridge's field.** The cell does not use the upper 16 for
  local traffic (they are constant — its own block — for everything inside the block).
  They exist in the 32-bit *space* so that a reference whose high 16 differs from the
  emitter's block is, by definition, a **cross-block** reference — and that is exactly
  what the bridge catches. The upper 16 are not wasted and not a cell burden; they are
  the addressing field the bridge reads, sitting in the same word, invisible below it.

So "32-bit throughout" means the cell's *reference space* is 32 bits; its *local
identity and local matching* are 16 bits, with the parent (block_id) **implied by which
block's bus the cell physically sits on**. The cell never carries its block_id for
local work — location carries it.

This partition is what gives a **pond its two scales**:
- **Fits in one block** — every reference is low-16, intra-block, no bridge touched,
  pure local-bus speed. The high 16 are constant (the block's id) and never matter.
- **Spans two or more blocks** — the same pond, same offsets, placed across a boundary.
  Intra-block references stay local; references whose high 16 cross a block boundary are
  caught by the bridge (their block_id ≠ the emitter's), resolved **once**, and flat
  thereafter. The pond's internal description does not change — placement decides which
  references happen to cross, and the bridge handles those transparently. This is how a
  pond grows past 65k cells without changing the cell or the pond.

### Shore-side expansion — 32-bit local to 128-bit global via bridge blocks

The cell and block live in the 32-bit die-local space. **Everything above 32 bits is
Shore-side**, reached by climbing the hierarchy through **multiple bridge blocks**, each
adding its level's offset:

```
32-bit  die-local      block_id | cell_id        — cells, blocks (local bus)
40-bit  on-card        + die_id                  — inter-die bridge
44-bit  in-backplane   + card_id                 — inter-card bridge
128-bit global         + backplane_id (84 bits)  — Shore / inter-card routing
```

Each level is an offset within its parent (cell-in-block, block-in-die, die-in-card,
card-in-backplane), and each boundary is a bridge that adds/strips exactly its level's
field — paid once per connection (lookup-once), never per hop. A reference climbs only
as far as it must: most stay at 32-bit die-local; only genuinely remote references walk
up through the bridge blocks to the full 128-bit identity, and once resolved they
collapse back to a local handle.

The physical scale fits this cleanly. At ~22–32 blocks per 1 cm² die (3nm, no 3D), the
inter-block bridge mesh per die is a tractable ~22–32-node fabric — block_id's 16 bits
have vast headroom over the handful physically present, and the same headroom holds at
each level up. The partition that keeps the cell at 16 bits is the same one that lets
the system scale to 128-bit global identity: the cell never changes; the bridge blocks
do the climbing.

### Off-die redirect — the cell's 32-bit ceiling

On-die, a reference is resolved by the **block_id field** (high 16): same block = local
bus, different block = inter-block bridge. But a cell cannot *name* an off-die location —
that needs die_id/card_id/global bits it does not have in 32 bits. So off-die uses an
**escape range**, not a field: any address past the on-die ceiling (`0xFFFC0000+`) is by
definition not a local block|cell — it is a Shore escape. The cell never decides "this
is remote"; the range decides, and Shore intercepts it and resolves to the full location
via the lookup-once bridge. The range decides; the cell does not.

So the cell's 32-bit space has two mechanisms, not one: the **block_id field** routes
*on-die* (cross-block via bridge), and the **top escape range** routes *off-die* (via
Shore). The die_id/card_id/backplane structure above (see "Shore-side expansion") is
**invisible below Shore** — cells, blocks and dies all operate in 32-bit local space;
only Shore and the inter-card fabric see the full 128-bit address.

### Lookup-once bridge — paying the hierarchy a single time

When a cell first references an off-die address, Shore (and its companion) holds a
table of lookup entries; the extra high-address bits index into it. On that first
reference Shore:

1. takes the high bits as an index into the lookup table,
2. **creates a bridge** to the resolved remote location, and
3. **sets the cell's internal address to the resolved local one.**

After that, the bridge exists and is directly addressable by the cell like any
local destination — subsequent traffic is just a bus address, no re-resolution.
The expensive 128-bit hierarchical lookup happens **exactly once per connection**,
at bind time; from then on it is flat local-bus speed. This is what makes
cross-die / cross-card / cross-server references affordable at scale: the
hierarchy is paid once and collapses to a local address forever after.

### Address layers

```
Cell / block:      32 bits — local bus, fast, no routing overhead
On-card:           40 bits — die + block + cell (card strips its own card_id)
Within-backplane:  44 bits — card + die + block + cell
Global:           128 bits — full hierarchy, Shore translates once via the
                             lookup-once bridge, then it is local thereafter
```

### Scale — full 128-bit address space

```
bits 127:44  backplane_id   84 bits  server / rack / region / datacenter / ...
bits  43:40  card_id         4 bits  16 cards per backplane (slot)
bits  39:32  die_id          8 bits  256 dies per card
bits  31:16  block_id       16 bits  65,536 blocks per die
bits  15:0   cell_id        16 bits  65,536 cells per block
```

`cell_id + block_id` = the 32-bit on-die address every cell sees. `die_id`
(etched) extends it to 40 bits on-card; `card_id` (slot) to 44 bits within a
backplane; `backplane_id` carries the remaining 84 bits of global identity.

The **backplane_id is a code held in the boot ROM image** — fixed per backplane,
the equivalent of the hardware ID code every node carries in present-day comms.
It is read once at boot and is the server/region/global identity for everything
on that backplane.

Each layer strips its own prefix and passes the remainder down.
Cell always sees 16 bits. Block always sees 32 bits. Nothing below
the backplane layer changes regardless of global scale.

**Uniqueness constraint:** no two nodes at the same level may share
the same ID within their parent scope — guaranteed by physical identity
(etched die, slotted card) and boot-ROM backplane code, with no global
coordination needed.

### Relocatable models — root + offset (position-independent)

The address layers above are the *physical* hierarchy — where silicon is. A **model**
(a configured circuit, a pond, a saved artifact) sits *within* that space at a chosen
position, and this is a separate axis: a model was always designed to be
**position-independent**. Everything a model addresses is an **offset from its root**.

```
effective address = model_root + offset
```

The model's internal description (its ICM, its saved state) is written entirely in
offsets, relative to 0. **Placing** the model = choosing a `model_root`. This is the
property that makes the fabric fluid:
- a model can be **shifted across the substrate** — same offsets, new root;
- a **save reloads into a different space** — the saved offsets are root-agnostic, so
  a checkpoint taken at one root restores at any other;
- **multiple models coexist** on one fabric — each placed at a non-overlapping root,
  none assuming it owns address 0;
- live migration (Ward) is a root change, not a rewrite.

So a model carries the mechanism to say *"this is my root; I sit there, and everything
I do is relative to it."* The root is a physical address in the hierarchy above; the
offsets are the model's own internal coordinates.

**The root is scale-relative.** "Address 0" is taken at whatever scale the model lives
in — a block-sized model roots at a block-local zero, a card-spanning model at a
card-local zero, a system-spanning one at a system zero. The records never name the
scale; they say "+N from my root," and the scale is decided at **placement**, not baked
into the artifact. This is the foundation of the pond system: a **pond is a rooted
region**, and everything inside it is relative to the pond's zero, whatever physical
span that zero sits at. The absolute address a cell ends up with is "directly relative
to the scale of the substrate" the pond was placed into.

**The work lives in the loader and saver — the cell stays absolute and dumb.** The cell
holds two absolute addresses (in/out) and knows nothing about roots or offsets. The
relativity exists in exactly two places, the boundary between "model as portable
artifact" and "cells placed on substrate":
- **Save:** read the cells, pick a zero-point (root), record each cell's two addresses
  as `address − root`. The artifact is pure offsets; the root is the implied origin,
  not stored in the records.
- **Load:** given a placement root, emit `root + offset` as each `CMD_LOAD_AT` target.
  The fabric receives absolute addresses, exactly as today.
- **Move (Ward):** read out as offsets (relative to old root), write back at
  `new_root + offset`. Live migration is save-then-load with a different root — no
  migration machinery in the cell, the same offset arithmetic.

So relocation, reload-into-different-space, and live migration collapse into **one
mechanism**: offsets live in the artifact, the loader/saver do the root arithmetic, the
cell is always absolute. Every bit of cleverness is in software (CPU-side, easy to
change); the thing etched into billions of cells carries nothing extra.

**The bridge is the relative↔absolute seam.** Outside a bridge, addresses are absolute
(direct, full-hierarchy). Inside, they are relative to the local root. The lookup-once
bridge (above) already "sets the cell's internal address to the resolved local one" —
that *is* this seam: it resolves an outside-absolute reference to an inside-local one.
So a bridge can **move** — the pond it fronts can relocate — and nothing inside changes,
because inside is always relative to the root; only the bridge's notion of where its
zero sits updates. Relative on the inside, absolute on the outside, the bridge is the
boundary, and the cell is absolute throughout because by the time an address reaches it,
it has already been resolved to the cell's local scale.

**Record-format note (decide at first loader):** offsets need a width. Block-local
offsets (16-bit cell_id) keep records narrow and are fine for intra-block models (the
22-cell packed adder fits easily); full on-die offsets (32-bit block+cell) let a model
span blocks at wider records. Pick block-local for the first loader, but reserve format
room to widen so a cross-block model later is not a format break.

**Where the absolute is formed (mechanism vs policy — keep separate):**
- The transport (target latch, `CMD_LOAD_AT`) holds a **resolved** absolute address and
  is deliberately dumb about how it was composed.
- *Now:* **direct addressing** — root = 0, the loader streams absolute targets.
- *Going forward:* the **loader/saver form the absolute** (`root + offset`) in software;
  the fabric and cell never see an offset. The loader must **never bake in absolute as
  the only mode** — it always streams *resolved* addresses, and root choice (placement,
  pond base) stacks above it without touching the transport.

**Host allocation (hosted, multi-model):** on a self-hosting fabric, allocation is
intrinsic (the boot walk tracks live cells). **Hosted**, the host keeps a used/free map
per loaded model and assigns each model a root within a free window before generating
its ICM. This is a bookkeeping layer *above* the loader — the loader still just fires
`(target, config)` pairs; the host decides which roots are legal. Deferred, but the
flat-offset ICM is what makes it drop in cleanly later.

### Manufacturing

Every cell, block, and die is **identical silicon**. Identity at the lower levels
comes from position, not from anything unique baked into the cell/block. The
upper-level identities are fixed physically or in firmware:

```
die_id        8 bits   ETCHED at manufacture — no two dies of the same number
                       on one card. Intrinsic to the silicon.
card_id       4 bits   SLOT — the card's position in the backplane.
backplane_id 84 bits   BOOT ROM image — a fixed code, the equivalent of the
                       hardware ID code every node carries in current comms.
```

Because die is etched, card is slotted, and backplane is a ROM code, the global
address is unambiguous with **no central allocator** — identity is intrinsic at
every level above the block.

Bootstrap is hierarchical, and only the within-block / within-die levels are
*assigned* (the etched/slotted/ROM levels above are already fixed):
- Card controller reads each die's etched `die_id`
- Die controller assigns `block_id` to each block (up to 65,536)
- Block controller assigns `cell_id` (logical) to each cell sequentially,
  health-checking as it walks and skipping cells held in the bad-cell table

The local bus within a block is 16-bit only — cells never see the upper
112 bits. The block boundary is the bus boundary.

### Physical vs Logical Address — the bootstrap handoff

```
Physical:  CELL_ID parameter — position in the block, set at synthesis
           or bootstrap. Immutable. Used only during bootstrap.
           Default input_address = CELL_ID at power-on.

Logical:   input_address register — assigned during bootstrap via
           SET_INPUT_ADDR. Fully mutable at any point during runtime.
```

The physical address exists only long enough to receive the logical one.
After bootstrap the cell responds to its logical address only and has
no knowledge of its physical position.

At runtime a cell can be moved to any logical address:
```
freeze → SET_INPUT_ADDR(new_address) → thaw
```

The physical substrate is fixed. The logical topology is completely fluid.
Ponds, arrays, and computation graphs can be restructured at runtime
without any hardware change.

### Physical address — no extra silicon

The physical address is simply the reset value of the `input_address`
register that already exists:

```verilog
reg [15:0] input_address = CELL_ID[15:0];  // already in unicell.v
```

No extra silicon. No extra bits. CELL_ID is a hardwired constant
(tied-high/tied-low metal, determined by position) feeding the reset
value of a register that was always there. After bootstrap assigns the
logical address, the register is 100% available for logical use.
The physical address costs nothing and leaves nothing behind.

### Current iCEBreaker

The iCEBreaker build uses 16-bit address matching (`bus_addr[15:0]`) as a
timing concession for 24 MHz on iCE40 4-input LUTs. This is not an
architectural limit — it sits cleanly within the 32-bit cell model.
Full 32-bit validation is planned for Kintex-7.

---

## Command-Emit Cells — The Fabric Commands Itself (v3.0)

A cell, when it fires, drives the **data** bus: `out_addr`, `out_data`,
`out_valid`. Nothing in the fabric drives the **command** bus — that has one
external source at cold boot. But Shore, the program-tile system, and every
controller are themselves built from cells. So without a way for a cell to issue
a command, nothing in-fabric can command anything: "the controller generates the
commands" is circular, because the controller is cells.

A **command-emit cell** closes this. It is an ordinary cell flagged by a single bit,
`cmd_latch[10]` (`is_command_cell` — a one-bit tap, no comparator; this bit reuses the
slot the removed `edge_mode` once held). The flag is set by `CMD_TOPO_COMMAND_EMIT`
(opcode 0x46 cold / 0x47 armed) or by a `RECONFIGURE`/`CMD_LOAD_AT` whose `cmd_data[10]`
is set. (Earlier drafts flagged it by a reserved topology `0x3C0`, which forced a
10-bit comparator into all 448 cells — removed; the bit tap is free.) When a command
cell fires it drives its stored command word (`a_data`) onto the command bus and its
`output_address` as the target, instead of computing a gate result onto the data bus:

```
normal cell fire:   out_bus     <- (output_address, gate(A,B))
command cell fire:  command_bus <- (a_data as cmd_bus, output_address as target)
```

Three properties make this safe and on-model:

- **The cell stays dumb — it is not an ALU.** It holds no program flow and decides
  nothing. The command's content (opcode, gating, auth) is assembled as ordinary
  data by upstream cells; the *ordering* is the fabric topology, not a program
  counter. A command-emit cell is a conduit, not an interpreter.
- **The trigger is the data wave.** The emit fires on the cell's second arrival,
  whose value is ignored — it is only a trigger. By placing the emit cell so its
  trigger is the same wave that feeds the cell it commands, the command lands in
  sync with the data. Ordering solves itself through placement.
- **Auth is intrinsic.** The emitted command is authed by the emit cell's own
  stored `auth_mask` — nothing is transmitted in. A target only accepts a command
  it is authed for, exactly as with a controller command.

Command-emit is **sparse and local**: most of a model is plain dataflow that just
flows; only the parts needing a transient command (e.g. a shift cell that must be
told its span) have an emit cell beside them, usually commanding the next cell.

What it unlocks, directly: self-triggering pipelines (a stage tells the next to
run when data lands), event-driven control (emit only when a condition holds),
local micro-schedulers and counters, distributed state machines (a state per cell,
transitions as emits), and data-dependent reconfiguration (emit `SET_OUTPUT_ADDR`
/ `RECONFIGURE` to rewire on the fly). Cells become local reflex agents, not
operators — without any cell gaining a program counter.

**Open design surface** (mechanism proven in sim; these are the next decisions):
command-bus **arbitration** in the zone (multiple emitters + the boot pin need the
same `cpu>n>s>e>w` discipline the data bus has); and **auth lockdown** for who may
hold the command-emit flag, since that is the highest privilege in the fabric. The
**payload-vs-target** question is now resolved — see the invariant below.

---

## Addressing & Command Authority — INVARIANT (read before touching command/auth/targeting)

This is settled architecture, not an open question. It has been re-litigated once and
must not be again. If a proposal conflicts with any clause here, the proposal is wrong.

**1. One comparator gates everything.** A cell has exactly one address comparator
(`addr_match` = physical CELL_ID in boot, logical `input_address` in run). It gates
BOTH lanes. On a cycle where the address matches, the cell looks at both busses:
the **data lane** loads/fires as normal; the **command lane**, if `auth_ok`, acts
(reconfigure / address-load), else is ignored. There is no second targeting mechanism.
Targeting *is* addressing.

**2. The target rides the ADDRESS LANE, at full width — never the command word.** A
command reaches a cell by putting that cell's address on `bus_addr` (driven by the
host, or by a command-emit cell's `output_address`), exactly as data is addressed.
The address is the cell's identity and is full-width (16-bit now, 32/128-bit later);
it must never be packed into spare command-bus bits. Doing so does not scale past a
toy zone and opens a path around the auth machinery. **Anti-pattern, permanently
rejected:** `cmd_bus[..]=target_addr`. (Built and reverted; do not reintroduce.)

**3. Auth is WRITE-ONCE at boot; the route then closes.** The data-bus route into a
cell's `auth_mask` is open ONLY in `physical_mode`. When the cell leaves boot
(`physical_mode -> 0`) that route closes permanently. After boot, nothing can set or
change a cell's auth. A fresh cell (`auth_mask == 0`) is `auth_boot` — it accepts its
first config, which sets its auth; thereafter commands need the matching token.

**4. Post-boot, the only authority over a configured cell is an auth-verified OPCODE.**
The data bus carries values, never config. Reconfiguration is opcode-only and
auth-verified. The single post-boot data-path special case is a verified address-load
opcode: "authorised — take the value off the DATA bus into the in/out address latch"
(auth in the command word, address value on the data lane, full width).

**The three properties that follow, and must be preserved:**
- *Identity unforgeable* — address is the comparator, set at boot.
- *Authority unstealable* — auth is write-once, its route closes after boot.
- *Action unsmuggleable* — reconfigure is opcode-only + auth-verified; no side door.

A running fabric cannot be reprogrammed without the boot-established auth code, and
that code is itself unreachable after boot. Per-cell targeting "opens up" precisely
*because* of this: once commands are addressed via the full-width address lane and
gated by the cell's own comparator, any cell is individually addressable — and the
security model stays intact.

**Implementation status (keep honest):**
- `CMD_LOAD_AT` (opcode 23) implements clauses 1–4: addr_match-gated, target on the
  address lane, config in `cmd_data`, auth-verified, auth-write boot-only. Proven in
  sim (per-cell config + auth reject/accept); regressions green.
- DONE (SILICON, 2026-06-28): `SET_INPUT_ADDR` (opcode 2) and `SET_OUTPUT_ADDR` (opcode 3)
  are now **addr_match-gated in the cell** (Option A), the same one-comparator mechanism as
  `CMD_LOAD_AT` — clauses 1/4 for in/out wiring. Target rides the address lane via the
  `SET_TARGET` latch (top routes `load_target` into `cpu_addr_w` for opcodes 2/3/23);
  the new address value rides `cmd_data`. The array no longer carries a parallel
  physical-ID comparator for op 2 (dropped from `cmd_is_boot_targeted`); ops 2/3
  broadcast and the cell self-gates. `SET_LOGICAL` (opcode 14) stays array-targeted for
  the boot walk. Per-cell load is now a full record: `SET_TARGET; SET_INPUT; SET_OUTPUT;
  CMD_LOAD_AT`. Proven on the GX660 die (fpga/icm_wired3.tcl, probe selector 3):
  cell0 read back topo=0x0BC, in=0x40, out=0x50 — the address rode the lane to the cell,
  addr_match self-gated, and the held target survived between SET_TARGET and the
  SET_INPUT/SET_OUTPUT pulses (the registered-bus skew that only shows on silicon did not
  bite). 0x50 is the wired-OR fan-in address (cell0+cell1 → one output), a wiring shape the
  physical-default chain cannot express — so arbitrary topology + arbitrary wiring are both
  now silicon-confirmed loadable. Ledger limit: cell0 is the probe-visible cell; cell1/cell2
  distinct in/out (cell2 out=0x51 vs cell0/1 out=0x50, which disproves broadcast) are
  oracle- and sim-verified, not directly read on the die — same read-scope as zone_target.
  The addressing invariant (one comparator, target on the address lane, never the command
  word) is therefore a measured property of the fabric, not only a doc claim; the rejected
  `cmd_bus`-target anti-pattern is proven unnecessary.
- TODO: legacy broadcast `CMD_RECONFIGURE` still writes `auth_mask` in run mode — bring
  its auth-write under the same `physical_mode` gate so clause 3 holds everywhere.
- DONE (sim): TARGET LATCH in `top_arria10.v`. `SET_TARGET` (opcode 24, top-only — the
  cells ignore it) latches the target and holds it on the address lane; the following
  `CMD_LOAD_AT(config)` lands on the held target. Two-word ISSP pairs, no IP regen.
  Proven (tb_top_target.v): an ICM stream of `(SET_TARGET, LOAD_AT)` pairs configured
  three cells (XOR/AND/OR) heterogeneously through the real transport. cpu_addr for
  `CMD_LOAD_AT` reads the latch, not `cpu_data` — so target and config never collide.
  Silicon test ready (fpga/zone_target.tcl, reads cell-0 latch via probe selector 3);
  needs a reflash (top changed). Widen the 16-bit latch to the full hierarchical
  address later with zero cell impact.

---

## Ward — Live Cell Migration

The Ward's freeze-move-thaw capability is a first-class runtime operation,
not just a recovery mechanism. It is enabled directly by the physical/logical
address separation — the program sees stable logical addresses while the
Ward moves cells freely across the physical substrate.

### Operations

**Damage recovery:**
```
Cell fails → Ward detects (no response to ping)
           → freeze neighbours
           → remap logical address to healthy cell
           → thaw — computation resumes, program unchanged
```

**Thermal management:**
```
Hot spot detected → Ward identifies overloaded block
                  → migrates cells to cooler region
                  → logical addresses follow the cells
                  → computation continues, topology unchanged
```

**Load spreading** — Ward can distribute computation across the physical
substrate dynamically. The program sees a completely stable logical address
space and never knows cells moved.

**Workspace Pond grow/shrink:**
```
Pond needs more space → Ward allocates fresh cells
                      → assigns logical addresses in pond's range
                      → pond grows transparently, no recompilation
Pond shrinks          → drain region, wait for in-flight completion
                      → reassign cells elsewhere
                      → live resize, no program change
```

### The move operation
```
1. freeze(source_cell)
2. read state: a_data, cmd_latch, input_address, output_address
3. configure(target_cell) with identical state
4. freeze(source_cell) permanently
5. thaw(target_cell)
```

One atomic logical hop. The bus sees one address. The physical cell
behind it changed. The rest of the system does not notice.

### Why this works
The logical address is the program's handle on a cell. The physical
address is discarded after bootstrap. There is no coupling between
logical identity and physical location — the Ward exploits this
deliberately and completely.

---

## One Unified Model

The repository has one implementation. The three-variant exploration
(Standard / Latch / Edge) concluded May 2026 when silicon bring-up confirmed
the two-arrival model as the canonical architecture. The subdirectories
`unicell-latch/`, `unicell-edge/`, and `unicell-standard/` have been retired.

**The two-arrival model:**

```
First arrival  at input_address → stored in a_data, a_arrived=True — NO output
Second arrival at input_address → fires gate(a_data, incoming) → output
```

This is the only cell model. All compiler, simulator, and hardware paths
use it. Validated on iCEBreaker silicon May 2026.

**Tests:** 19/19 core · 56/56 branch · 81/82 INT32 · all passing 2026-05-19.
iCEBreaker silicon: 15/15 gate operations confirmed. See `docs/RESULTS.md`.

---

## The Type System

### Two bits that change everything

Bits 27-28 of every cell's `gate_state` declare the semantic type of its
output:

```
00  GS_TYPE_NUMERIC   — unsigned integer (default)
01  GS_TYPE_SIGNED    — two's complement signed
10  GS_TYPE_ALPHA     — 8-bit character / string byte
11  GS_TYPE_DATETIME  — Unix timestamp
```

These bits travel with the cell through its entire lifecycle: configuration,
PTT registration, `.icm` serialisation, Ward monitoring, WORKSPACE injection.

### Complement cells

Typed values wider than 32 bits use a **complement cell** at `primary_addr + 1`:

```
SIGNED:    primary  = bits 0-31  (low word, two's complement)
           complement = bits 32-63 (high word, sign extension)
           Together: int64 in two's complement

DATETIME:  primary  = Unix seconds (signed int32, fits in 32 bits to year 2038;
                      use int64 pair for full range)
           complement = subsecond (bits 0-29: nanoseconds 0-999999999)
                       + tz_offset (bits 30-31: quarter-hours, -48..+56)

ALPHA:     primary  = character N (bits 0-7 = ASCII/UTF-8 byte)
           complement = character N+1
           String: sequence of cell pairs, terminated by primary=0x00
```

The compiler allocates complement cells automatically when it sees a type
annotation:

```python
def add_signed(a: signed, b: signed) -> signed:
    ...
# Compiler allocates: a (primary), _a_hi (complement), b, _b_hi, result, _result_hi
```

### What this means

A CPU has typed registers by convention. The type lives in the programmer's
head and the compiler's symbol table. The hardware shuffles bits with no
awareness of what they mean.

Here, the type is in the silicon. The gate_state word travels with the cell
through configuration, through the PTT, through the `.icm` file, through Ward
health monitoring. When a SIGNED cell fires, everything downstream knows it is
looking at the low half of a 64-bit signed value and the complement cell is at
`addr+1`.

**Ward can monitor types.** A Bridge carrying DATETIME values that starts
receiving NUMERIC values is a type violation. Ward flags it without the program
checking.

**Shore can index by type.** "All SIGNED output ports in this pond" is a PTT
scan on type bits — not a metadata lookup.

**Migration preserves type.** When a pond freezes and migrates to a different
substrate, cell configurations move with it. Types move with them. No
unmarshalling step where type information can be lost.

**The `.icm` is a typed program.** Not just cell configurations but a declared
contract. Any loader — VM, FPGA, future ASIC — knows exactly what it receives
before the first cell fires.

This is the shift from "logic fabric" to "typed computing substrate." Two bits
and the discipline to thread them all the way through.

---

## Compiler

### Two paths

**Single-bit compiler (`compiler.py`):** Python AST → IR graph →
`CellMapRecord` list. Handles logic, conditionals, while loops, for loops,
function calls. Constant auto-injection via `known_values`. Type annotation
support (`:signed`, `:datetime`, `:alpha`).

**INT32 compiler (`compiler_int32.py`):** 32-bit integer arithmetic via the
tile library. Maps `a + b` to an `INT32_ADD` tile (482 cells, Kogge-Stone adder, depth 10
depth 2), `a - b` to `INT32_SUB` (517 cells, depth 12), `a < b` to
`INT32_LT_U` (518 cells, unsigned) or `INT32_LT_S` (523 cells, signed), etc.

### scan_function — pre-compile port discovery

Before compiling, `scan_function(source, fn_name)` reads the AST without
emitting cells and returns:

```python
{
  "inputs":      ["a", "b"],
  "input_types": {"a": "signed", "b": "datetime"},
  "output":      "result",
  "return_type": "signed",
  "loop_vars":   [],
}
```

The CLI uses this to prompt the user to confirm or rename ports before the
`.icm` is written. The confirmed names become the PTT entries for the program.

### LLVM path

Any language with an LLVM frontend (C, C++, Rust, Swift, Zig) compiles to
`.icm` via `llvm_ir_mapper.py`:

```
C / C++ / Rust  →  clang  →  LLVM IR  →  llvm_ir_mapper.py  →  .icm
```

Requires `pip install llvmlite`. Graceful fallback if not installed.

---

## OS Layer

### Pond

Every program runs inside a Pond: an isolated address space with a security
level (OPEN / PRIVATE / HIDDEN), inbound/outbound bridge lanes, Ward health
monitoring, and live migration support.

```
Pond
├── address space  (base_address + region_size)
├── PTT            (named ports → bus addresses + type bits)
├── bridges        INBOUND (data arrives)
│                  OUTBOUND (results leave)
│                  MONITOR (emission counting, anomaly detection)
│                  LOG (audit trail)
└── Ward           (health monitor)
```

Ponds can be frozen mid-computation and migrated to a different substrate
(FREEZE → move → THAW) without stopping computation or losing state.

**Security levels:**

| Level | Behaviour |
|-------|-----------|
| `OPEN` | Any identity admitted; no whitelist check. Development default. |
| `PRIVATE` | Only whitelisted identities admitted. All program ponds spawned by the OS default to PRIVATE. |
| `HIDDEN` | Not discoverable via Shore. Only whitelisted identities admitted. Used by COMPANION and system ponds. |

Access is enforced at the bridge via `check_access(identity_id)`. On silicon
this becomes a gate_state mask check in hardware — zero software overhead.

### PondManager

`PondManager` is the OS-level factory for all Pond lifecycle operations. It
owns the shared `UniCellArray` and all active Ponds.

```python
from pond import PondManager
from unicell_array import UniCellArray

array = UniCellArray(cell_count=8192)
mgr   = PondManager(array)
```

Key methods:

| Method | What it does |
|--------|-------------|
| `spawn_workspace(owner_id, name)` | Create a PRIVATE WORKSPACE Pond for a user session |
| `spawn_pond_from_icm(icm, owner_id)` | Create a PRIVATE PROCESS Pond from a `.icm` dict; register all ports in PTT; wire sentry cluster |
| `connect(workspace, program)` | Wire bus addresses and grant whitelist access both ways |
| `create_pond(name, owner_id, ...)` | Low-level: create a bare Pond of any type |
| `destroy_pond(pond_id, requester_id)` | Free cells, remove from registry |

### Bridge security model

Each Pond has an INBOUND and OUTBOUND bridge — clusters of cells at known
`external_address` values registered with Shore. The bridge is the only entry
and exit point for data.

**Whitelist:** PRIVATE and HIDDEN ponds maintain a `{identity_id: AccessGrant}`
dict. `grant_access(identity_id)` adds an entry; `revoke_access()` removes it.
The owner is always admitted regardless of whitelist.

**`connect(workspace, program)` wires two ponds together:**

```
workspace OUTBOUND external_address → program  INBOUND external_address
program   OUTBOUND external_address → workspace INBOUND external_address
```

This is a direct bus address assignment — when the workspace fires its
OUTBOUND cells at the program's INBOUND address, the program sees the value
on the next tick. One tick end-to-end, zero routing overhead. `connect()` also
grants whitelist access both ways, so only these two ponds can exchange data.

**Multi-program workspace:** a single WORKSPACE pond can connect to N program
ponds simultaneously. Each program has distinct INBOUND addresses; all route
their OUTBOUND to the same workspace INBOUND address. The wired-OR bus handles
fan-in naturally.

```
WORKSPACE (PRIVATE, INCREMENTAL PTT)
  OUTBOUND → prog_A INBOUND   (inputs to A)
  OUTBOUND → prog_B INBOUND   (inputs to B, different address)
  INBOUND  ← prog_A OUTBOUND  (A's results)
  INBOUND  ← prog_B OUTBOUND  (B's results, OR'd on the bus)
```

### PTT — Pond Translation Table

Every Pond has a PTT: a structured table of named entries mapping port names
to bus addresses and type bits. The PTT is the OS-level view of a program's
interface. Shore indexes PTT entries. The WORKSPACE queries PTT entries by
name to inject inputs and read outputs.

**Entry types after `spawn_pond_from_icm`:**

| Type | Label example | Status | What it tracks |
|------|--------------|--------|----------------|
| `BRIDGE_INBOUND` | `INBOUND_bridge` | ACTIVE | Always-on infrastructure |
| `BRIDGE_OUTBOUND` | `OUTBOUND_bridge` | ACTIVE | Always-on infrastructure |
| `TILE_IN` | `adder.a` | IDLE→WAITING | Input port — did the user supply a value? |
| `TILE_IN` | `adder.b` | IDLE→WAITING | One entry per named input |
| `PRIMITIVE` | `adder.result` | IDLE→ACTIVE | Output port — is the tile computing? |

`TILE_IN` entries let the Ward distinguish "pond waiting for user input" from
"pond actively computing". Without them, a pond that has never received an
input looks identical to one mid-run. The WORKSPACE model depends on this:
`ws set a=5` should transition `adder.a` IDLE → WAITING so the Ward knows the
pond has been engaged.

```
PTT[0]: BRIDGE_INBOUND  — INBOUND_bridge        ACTIVE  (always)
PTT[1]: BRIDGE_OUTBOUND — OUTBOUND_bridge        ACTIVE  (always)
PTT[2]: TILE_IN         — adder.a               IDLE    ← waiting for ws set a=...
PTT[3]: TILE_IN         — adder.b               IDLE    ← waiting for ws set b=...
PTT[4]: PRIMITIVE       — adder.result  sentry  IDLE    ← will go ACTIVE when tile fires
```

### Sentry cluster

Each `PRIMITIVE` PTT entry has a **sentry cell** — a LOOP_MODE cell that
watches the tile's primary input address and writes a keep-alive tick to
the PTT bus range (`0xFFE00000+`) every cycle once the tile has been
invoked.

The Ward calls `ptt.check_staleness()` each tick. If a PRIMITIVE entry that
is ACTIVE has not received a sentry tick within its `staleness_threshold`
(typically 5 seconds), it transitions to FAULTED and the Ward escalates to
COMPANION.

**Wiring** (handled automatically by `spawn_pond_from_icm` via
`controller.load_map(ptt=...)`):

1. `ptt.register_sentry(idx)` — assigns a dedicated PTT bus address to the entry
2. `load_map(ptt=pond._ptt)` — sets `cell._ptt_ref = ptt` on every loaded cell so
   sentry output interception fires; patches placeholder sentry address
   (`PTT_BUS_BASE`) to the correct per-entry address
3. On each tick, sentry cell output is intercepted in `unicell.py` before reaching
   the bus: `ptt.bus_tick(sentry_addr, value)` → status transitions

### Ward

Per-Pond health monitor. Detects:

- **STALL** — consecutive zero-emission cycles beyond `stall_threshold`
- **SPIKE** — burst emission beyond declared bridge bandwidth
- **ANOMALY** — rejection rate above `anomaly_threshold` in rolling window
- **SILENT** — no emission at all (device disconnect for DEVICE ponds)

Thresholds come from `PondTypeSpec` — each pond type has tuned values:
DEVICE ponds flag silence in 15 cycles, PROCESS ponds tolerate 100, FILE
ponds tolerate 200. Ward escalates to COMPANION on repeated failures.

### Shore

The lean registry. Maps Pond names to addresses via a `view_mask` access
control layer. Query by PTT cell word. No directory tree — search is an
index query. Shore is a HIDDEN SHORE-type Pond living in the cell fabric
it indexes.

### COMPANION

The permanent OS anchor. One instance per session. HIDDEN security level.
Cannot be destroyed without `heritage=True`. Manages: rule engine (receives
Ward escalations, decides RESTART/ISOLATE/MIGRATE), key issuance, template
Pond cloning, region allocation.

### WORKSPACE Pond

The user's desk. Every interactive session has one WORKSPACE pond (type
WORKSPACE, security PRIVATE) that bridges to program ponds via `connect()`.

Current state (2026-05-11): `PondManager.spawn_workspace()` and `connect()`
create the correct Pond structure with Ward, PTT, and bridge wiring. The
`WorkspacePond` class in `workspace.py` is a standalone controller wrapper
used by the workbench — it does not yet use the Pond architecture. Full
integration is tracked in `MIGRATION_TODO.md § WORKSPACE POND`.

When fully integrated, the lifecycle will be:

```python
# User logs in
ws = mgr.spawn_workspace(owner_id="user_alice")

# User loads a program
program = mgr.spawn_pond_from_icm(icm, owner_id="user_alice")
conn    = mgr.connect(ws, program)

# User sets inputs — TILE_IN entries transition IDLE→WAITING
ws.set("a", 5)
ws.set("b", 3)

# User runs — ws OUTBOUND fires to prog INBOUND; prog OUTBOUND returns to ws INBOUND
result = ws.run(conn)   # {"result": 8}

# Program pond PTT: PRIMITIVE entry transitions IDLE→WAITING→ACTIVE→COMPLETING→IDLE
# Workspace PTT:    connected program entry tracks same lifecycle
```

The user only ever sees names. The bus addresses, bridge wiring, PTT
transitions, and Ward health monitoring are invisible below the `ws.set` /
`ws.run` / `ws.get` surface.

---

## Portability

The same `.icm` file runs on every target without modification:

| Target | Cells | Clock | Status |
|--------|-------|-------|--------|
| Python VM | Unlimited | Software | Available (`pip install imago-vm`) |
| iCEBreaker (iCE40UP5K) | 32–64 | 24 MHz | Validated May 2026 |
| iCEstick (iCE40HX1K) | 8–16 | ~20 MHz | Supported |
| Basys 3 / Arty A7 | 256 | ~100 MHz | Supported |
| OrangeCrab (ECP5) | 256 | ~80 MHz | Supported |
| Kintex-7 XC7K480T ×2 | 600–1,500+ | 200+ MHz | In hand — bring-up pending (riser cable) |
| Future ASIC | Millions | GHz | Same `.icm` files |

Programs written today run on silicon that does not exist yet. The community
can develop and test on the VM — programs are almost silicon-ready when
hardware arrives.

The Verilog is Verilog-2001 clean and synthesises on any family. The UART
bridge protocol is 13-byte packets at 115200 baud — simple enough to
re-implement on any MCU.

---

## Design Principle

Every time a feature needed more gate_state bits — a type system, an edge
model, address extension — the constraint held. The cell didn't grow.

The instinct to add more bits leads to the CPU path: wider buses, wider
routing, more silicon, more heat, more failure modes. The NOR fabric stays
lean precisely because the cell doesn't grow.

What the type system showed is that you don't need more hardware bits to carry
more information — you need better discipline about what existing bits mean.
Two previously-reserved bits became a type system that flows through the entire
stack. The cell didn't change. The architecture got richer.

If an idea feels like it needs more bits in the gate_state word, that is a
signal it belongs above the cell layer — in the PTT, the `.icm` header, the
Shore registry, the WORKSPACE type_map. The cell stays simple. Richness lives
in the layers above it.
