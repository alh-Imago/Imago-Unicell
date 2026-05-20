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
bits  0-8:   NOR gate topology (9-input tree, selects the logic function)
bits  9-10:  ECC configuration
bits 11:     GS_LATCH        — store output each tick
bits 12:     GS_ONE_SHOT     — disarm after first firing
bits 13:     GS_INVERT_OUT   — invert output signal (deprecated in v2)
bits 14:     GS_BROADCAST    — write to address range
bits 15:     GS_SYNC_WAIT    — wait for A and B before firing
bits 16:     GS_LOOP_BACK    — feedback output to input address
bits 17-19:  LOOP_BACK_SRC   — source gate selector (3 bits)
bits 20-22:  LOOP_BACK_DST   — destination gate selector (3 bits)
bits 23:     GS_ADDR_LATCH   — extended 64-bit address mode (bridge cells only)
bits 24:     GS_FALL_EDGE    — assert output on falling clock edge
bits 25:     GS_LATCH_IN     — input-side latch, re-fires on down tick
bits 26:     GS_OUT_POSEDGE  — output buffer releases on rising edge
bits 27-28:  GS_TYPE         — cell output type (00=numeric, 01=signed,
                                                  10=alpha, 11=datetime)
bits 29:     GS_PRIORITY     — jump segment emission queue
bits 30:     GS_TRACE        — log every firing to debug buffer
bits 31:     GS_BREAKPOINT   — halt array when this cell fires
```

### Gate functions (v2, all one cell one cycle)

| Function | gate_state | Notes |
|----------|------------|-------|
| NOT | GS_NOT (bit 0) | single-input |
| PASS | 0x00000000 | wire / delay cell |
| AND | GS_AND_V2 \| GS_SYNC_WAIT | A↑ posedge, B↓ negedge |
| OR | GS_OR_V2 \| GS_SYNC_WAIT | A↑ posedge, B↓ negedge |
| XOR | GS_XOR_V2 \| GS_SYNC_WAIT | A↑ posedge, B↓ negedge |
| NAND | GS_NAND_V2 \| GS_SYNC_WAIT | A↑ posedge, B↓ negedge |
| XNOR | GS_XNOR_V2 \| GS_SYNC_WAIT | A↑ posedge, B↓ negedge |
| NOR | GS_NOR_V2 | via wired-OR bus |
| SELECT | GS_SELECT | conditional routing |
| LATCH | GS_LATCH | state hold |
| LOOP | GS_LOOP_BACK | feedback path |
| ONE_SHOT | GS_ONE_SHOT | fires once then disarms |

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

## Address Space

### Cell view — 32 bits

Every cell uses 32-bit addressing throughout its lifetime. This does not
change at any scale.

```
0x00000000 - 0xEFFFFFFF   Cell computation space     (~3.76B addresses)
0xF0000000 - 0xFFFBFFFF   OS / Shore reserved        (~16M addresses)
0xFFFC0000 - 0xFFFFFFFF   Extended addressing zone   (~262K addresses)
                           Shore intercepts and translates to 64-bit global
                           Last ~300K reserved for inter-card identity space
```

### 64-bit global addressing — card boundary

When a cell address reaches `0xFFFC0000+`, Shore intercepts and translates
to a full 64-bit external address using the hierarchical address structure:

```
bits 63:40   card_id    24 bits   16,777,216 cards
bits 39:32   die_id      8 bits   256 dies per card (160 max + headroom)
bits 31:16   block_id   16 bits   65,536 blocks per die
bits 15:0    cell_id    16 bits   65,536 cells per block
```

The 64-bit hierarchy is **invisible below Shore**. Cells, blocks, and dies
all operate in 32-bit local address space. Only Shore and the inter-card
routing fabric see the full 64-bit address.

### Address layers

```
Cell / block:   32 bits — local bus, fast, no routing overhead
Card internal:  48 bits — die + block + cell (card strips own card_id)
Inter-card:     64 bits — full hierarchy, Shore translates transparently
```

### Scale — full 128-bit address space

```
bits 127:64  backplane_id   64 bits  rack / region / datacenter / ...
bits  63:40  card_id        24 bits  16,777,216 cards per backplane
bits  39:32  die_id          8 bits  256 dies per card
bits  31:16  block_id       16 bits  65,536 blocks per die
bits  15:0   cell_id        16 bits  65,536 cells per block
```

Each layer strips its own prefix and passes the remainder down.
Cell always sees 16 bits. Block always sees 32 bits. Nothing below
the backplane layer changes regardless of global scale.

**Uniqueness constraint:** no two nodes at the same level may share
the same ID within their parent scope. Enforced by sequential bootstrap
allocation at each level — no global coordination needed.

### Manufacturing

Every cell, block, and die is **identical**. Identity comes from position,
not from anything baked into silicon. Only `card_id` varies at manufacture
— a 24-bit serial number, a solved problem.

Bootstrap is hierarchical:
- Card controller assigns `die_id` to each die (up to 256)
- Die controller assigns `block_id` to each block (up to 65,536)
- Block controller assigns `cell_id` (logical) to each cell sequentially

The local bus within a block is 16-bit only — cells never see the upper
48 bits. The block boundary is the bus boundary.

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
tile library. Maps `a + b` to an `INT32_ADD` tile (482 cells, Kogge-Stone
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
