# Imago UniCell — Claudette v1.1
## Complete Development Documentation

---

# PART 1 — DEVELOPMENT HISTORY

## Origin and Design Philosophy

The Imago UniCell project began with a single constraint: every logic function must be built from NOR gates. NOR is universal — any Boolean function can be expressed in NOR alone. The question was whether a practical computing architecture could emerge from that constraint rather than fighting it.

The answer turned out to be yes, but the architecture it produced is unlike conventional processors in almost every respect.

**The fundamental insight:** rather than having a processor fetch and execute instructions, have cells evaluate themselves. A cell knows its gate topology, its input address, and its output address. When data arrives at its input address, it fires, computes, and writes to its output address. No fetch cycle. No decode. No program counter. The computation is the wiring.

This means programs are not sequences of instructions — they are networks of cells. Compiling a function means constructing a cell network where data flows through it and the correct result emerges at the output address after a known number of clock ticks. The pipeline depth is the compile-time-known latency of the computation.

---

## Phase 1 — Cell and Array (Weeks 1–2)

### UniCell

The first working cell was a single NOR gate with a configurable topology register. The initial design had an 11-bit gate_state (bits 0–10 for NOR fanin topology), then expanded to a **32-bit gate_state** to accommodate mode flags, security fields, and loop control without breaking the existing 11-bit NOR topology in bits 0–10.

**Final 5-register cell architecture (129 bits total per cell):**

```
Config register (32 bits, Command 3 / system only):
  bits  0-10:  NOR topology (fanin configuration — unchanged from original)
  bits 11-14:  ECC config
  bits 15-26:  Auth mask (12-bit card token — set at boot, HIDDEN in ShoreKeeper)
  bits 27-31:  Reserved

Mode register (32 bits):
  bit  11:  GS_LATCH       — store output each tick
  bit  12:  GS_ONE_SHOT    — disarm after first firing
  bit  13:  GS_INVERT_OUT  — invert output signal
  bit  14:  GS_BROADCAST   — write to address range
  bit  15:  GS_SYNC_WAIT   — wait for two sequential arrivals
  bit  16:  GS_LOOP_BACK   — feedback output to input
  bits 17-19: LOOP_BACK_SRC
  bits 20-22: LOOP_BACK_DST
  bit  23:  GS_ADDR_LATCH  — extended 64-bit address latch (bridge cells only)
  bit  24:  GS_FALL_EDGE   — assert output on falling clock edge (default: rising)
  bits 25-28: reserved for future use
  bit  29:  GS_PRIORITY    — scheduled first each tick
  bit  30:  GS_TRACE       — record to trace buffer on fire
  bit  31:  GS_BREAKPOINT  — halt array on fire

Input address register  (32 bits)
Output address register (32 bits)
Data register           (32 bits)
Start flag              (1 bit)  — armed / disarmed
```

**Key design choices:**

The cell has exactly one input address. This was the most debated decision early on. It seems to prevent two-input operations, but the wired-OR bus solves this: two cells writing to the same bus address have their outputs OR'd together. A downstream cell reading that address sees the combined result. Two-input NOR emerges from one-input cells plus bus topology — the cell stays simple, the topology does the work.

The `start_flag` acts as the armed/disarmed control. A disarmed cell ignores all bus traffic. This is the fundamental compute control primitive — arming and disarming cells is how the OS starts and stops computation.

**The timing insight:** everything in the architecture is a timing problem. If cell A and cell B both write to address X, but A fires on tick 7 and B fires on tick 12, the downstream cell reading X will fire twice with wrong partial results. `pad_to_depth` was introduced to insert PASS cells on the shorter path so both signals arrive simultaneously. The entire compiler pipeline depth tracking exists to solve this one problem correctly.

**Edge separation refinement (Claudette v1.2):** The primary bus collision solution is now clock-edge separation rather than PASS pad cells. When two values target the same address in the same clock cycle, the compiler assigns one to the rising edge (default) and one to the falling edge (`GS_FALL_EDGE | GS_LATCH`), separating them within the cycle without inserting dummy cells. This reduces cell count across all compiled programs.

Edge assignment is structural and automatic — never user-visible:
- Cell output values → rising edge (data is already on its way)
- Program table / literal injections → falling edge (scheduled, arrives after cell outputs settle)
- Cell-to-cell conflicts in trees → compiler assigns the deeper/later cell `GS_FALL_EDGE`; flagged in compile stats as `edge_resolved`

`pad_to_depth` is retained for depth gaps > 1 tick, where edge separation (one half-cycle) is insufficient. At 12MHz the half-cycle window is ~41ns, sufficient for iCE40 routing. `GS_LATCH` must be set on the sending cell so the held value is stable across both edges.

### UniCellArray

The array introduces the bus — a shared dict mapping address to (value, tick). All cells read from and write to this single shared medium. The tick counter prevents stale reads.

The `_armed` set tracks which cells are currently active. This set is the heartbeat of the system — when it empties, computation is complete.

---

## Phase 2 — Tile Library (Weeks 2–4)

### NOR primitives and gate construction

NOT, AND, OR, XOR, XNOR — all constructed from NOR trees. The NORBuilder abstraction handles depth tracking automatically: every node records its depth from the input, and `pad_to_depth` equalises paths before wiring. Where depth gaps are ≤ 1 tick, edge separation replaces pad cells entirely — the compiler assigns `GS_FALL_EDGE | GS_LATCH` to one input of each wired-OR combiner, separating the two signals within the same clock cycle without consuming extra cells.

**Critical finding:** SYNC_WAIT was designed to replace pad_to_depth, allowing a cell to wait for two sequential arrivals before firing. This works for genuinely asynchronous merges, but fails for the common case where two paths are equalised to arrive simultaneously — the wired-OR bus merges simultaneous arrivals into one packet, and SYNC_WAIT waits forever for a second that never comes. SYNC_WAIT was retained as an explicit primitive for async merges only. NOR2 reverted to pad_to_depth.

### Integer arithmetic tiles

**INT32_ADD (ripple carry):** depth 194, 12,931 cells. The carry chain propagates bit by bit — correct but slow.

**INT32_ADD_CLA (carry-lookahead):** depth 58, 3,219 cells. The CLA computes all carries in parallel. This was the first major optimisation — a 3× depth reduction by changing the carry architecture. The CLA became the default for compiler-generated addition.

**INT32_SUB:** implemented as ADD with the second operand complemented (two's complement: subtract B = add NOT(B) + 1).

**INT32_EQ, INT32_MUX:** equality via XNOR-tree, multiplexer via AND/OR selection.

**INT32_MAX, INT32_MIN:** built from a subtractor plus sign-bit MUX. 26,077 cells, depth 202 — correct but expensive. A CLA-based variant is planned.

### Counter tiles

**COUNTER_SHIFT_N:** a PASS chain of N cells. Produces N sequential one-hot pulses. Depth = N. Used for small fixed-range for loops (n ≤ 32).

**COUNTER_RIPPLE_8/16/32:** a ripple counter with tick input, limit comparison, done signal, and value output. Used for variable-range loops and large fixed-range loops (n > 32).

**COUNTER_DECREMENT_8/16/32:** counts down to zero. Used for while-loop iterations with a known bound.

### Bitwise logic tiles

INT32_NOT (32 cells, depth 1), INT32_AND (160 cells, depth 3), INT32_OR (128 cells, depth 3), INT32_XOR (576 cells, depth 7). All implemented as parallel bitwise operations — the simplest tiles in the library and the fastest.

### Parity and LFSR

PARITY_32: 558 cells, depth 35. XOR tree folding 32 bits to 1.

LFSR_16: 185 cells, depth 10. Galois LFSR with polynomial x^16+x^15+x^13+x^4+1 (maximal length, period 65,535). Used for pseudo-random number generation without a CPU.

---

## Phase 3 — Compiler (Weeks 3–6)

### IR and graph

The compiler works in two passes: first build an IR graph from the Python AST, then lower the IR to CellMapRecords. The IR captures data dependencies; the lowering assigns addresses and wires cells.

The IR graph uses a simple node model: each node has a list of input node IDs and produces one output address. Constants are input nodes with a fixed address. Operations are nodes that consume inputs and produce an output.

### Arithmetic lowering

Integer arithmetic compiles via the tile library. An `a + b` expression becomes an INT32_ADD_CLA tile instance placed at a fresh base address. The compiler tracks which tile instances are in use and ensures they don't overlap.

**Int32Value type:** a 32-bit integer aware type in the compiler. When an operation involves an Int32Value on one side and a Python int literal on the other, the literal is automatically coerced to Int32. This eliminates the need for explicit casts in most programs.

**AugAssign (+=, -=, &=, |=, ^=):** compiled by treating `x += y` as `x = x + y` and updating the variable binding in scope.

**Chained comparisons (a < b < c):** desugared to `(a < b) AND (b < c)` with b evaluated once.

### Control flow

**if/else:** compiled using GS_SELECT cells. The condition drives a SELECT cell that routes the true or false branch to the result address. Both branches are compiled fully; only the selected one propagates.

**while loop:** uses a loop-back storage cell. The variable lives in a storage cell that re-emits its value every tick. The condition chain evaluates it; GS_SELECT routes either the loop body result (feeding back to the storage cell) or the exit value. The storage cell model was the key insight — the variable persists between iterations by continuously re-emitting.

**for loop (SHIFT path, n ≤ 32):** COUNTER_SHIFT_N produces N sequential one-hot step outputs. The body is compiled once; each step gates it via AND. For loops with accumulators need a storage cell (pending improvement).

**for loop (RIPPLE path, n > 32 or variable):** COUNTER_RIPPLE_8 drives iteration. The tick address is exposed in the input_map so the caller can start the loop. The done signal terminates.

**ast.Pass:** no-op statement, compiles to None (no cells allocated).

---

## Phase 4 — OS Layer: Claudette v1.0 (Weeks 4–10)

### Naming

The current version of the Imago spatial computing OS is Claudette v1.2. v1.1 introduced the 64-bit config register, three-tier object model, 3×64-bit command bus, GS_ADDR_LATCH bridge primitive, and Shore proxy retirement. v1.2 introduces clock-edge separation (`GS_FALL_EDGE`, bit 24) as the primary bus collision resolution mechanism, reducing compiled cell counts by eliminating PASS pad cells wherever depth gaps are ≤ 1 tick. The compiler now emits `edge_resolved` statistics alongside `pad_cells`. The name appears in three places: the `companion.py` constants (`OS_NAME`, `OS_VERSION`, `OS_FULL_NAME`), the workbench `ver` command output, and every VM image header as `os_name`/`os_version` stamps. New VM images are stamped `os_version: 1.2`. v1.0/v1.1 images load correctly — the gate_state extension is backward-compatible.

### Pond

The Pond is the fundamental OS resource unit — a named, bounded pool of cells with bridge-gated access. Ponds replaced flat memory allocation as the model for all resource management.

Every Pond has at minimum two bridges: INBOUND and OUTBOUND. Bridges are single cells that gate all access. The PondBridge access model evolved through several iterations:

- V1: whitelist-only (known identities admitted by name)
- V2: whitelist + security level (OPEN/PRIVATE/HIDDEN)
- V3: whitelist + mask check (bidirectional 32-bit process mask)

The current model does the mask check first (O(1)) before the whitelist check. A mask mismatch makes the Pond invisible — absent, not denied. This is the core security property: the system cannot leak information about resources that the querying process has no mask overlap with.

### Security Model — Nine Layers

The security model is built on a single primitive applied at every layer: a 32-bit bitmask AND operation. There are no ACL tables, no permission inheritance calculations, no per-object configuration at runtime. Security is enforced by the same `(process_mask & resource_mask) != 0` check from the hardware cell up to the filesystem view.

#### Layer 1 — Hardware: Cell Auth Token

The BIOS-Plus chip generates a 12-bit random auth token at power-on from its hardware RNG. This token is distributed to every cell on the card during the boot sequence via Command 3 (RECONFIGURE). The token is stored in the cell's config register (bits 15-26) and is write-only — once set, it cannot be read back by any bus operation.

**Enforcement:** Any subsequent Command 3 transaction carries the auth token in Bus 1 bits 4-14. The cell silently rejects the command if the presented token does not match the stored value. Silent rejection is deliberate — no error signal means an attacker cannot probe for the correct token by watching responses.

**Scope:** This is a card-level secret. All cells on a given card share the same token. A program running on one card cannot reconfigure cells on another card without that card's token.

#### Layer 2 — Data: Salt Key Encryption

The BIOS-Plus chip generates a 64-bit salt key at power-on from the same entropy source as the auth token. The salt key never leaves the BIOS chip — it is not stored in the NOR cell array, not accessible via any bus address, and is destroyed if the BIOS chip is physically tampered with (tamper-evident fusing).

**Uses:**
- **Hidden Pond encryption:** A SHOREKEEPER-type Pond can be encrypted at rest using the salt key. The data is unreadable without the card's BIOS chip. A snapshot of a hidden Pond taken off-card is meaningless.
- **Licensed software:** Tile programs and user libraries can be encrypted against a card's salt key before delivery. The program runs only on the card it was licensed for — the salt key is the hardware binding. This is hardware DRM without a separate DRM system.

**Relationship to auth token:** Both derive from the same RNG entropy pool at boot. The auth token protects cell reconfiguration (command-level). The salt key protects data and intellectual property (content-level). They are independent secrets derived from the same source.

#### Layer 3 — Addressing: PTT Hidden Process Mask

Every process has a hidden `process_mask` (32-bit) stored in its Process Translation Table entry. The mask is set by COMPANION at process creation and is never readable by the process itself — it exists in a hidden PTT field alongside `bubble_id` (containment zone) and thermal fields.

**Mask layout (32 bits):**
```
bits  0-7:   tenant ID (which user/organisation owns this process)
bits  8-15:  role flags (admin, user, service, etc.)
bits 16-23:  feature flags (which capabilities are enabled)
bits 24-31:  reserved
```

**Enforcement:** Mask is inherited — every object a process creates (Ponds, bridges, files) inherits the creator's mask. There is no escalation path through object creation. A process with bits 0-7 set to tenant 3 can only create objects that also belong to tenant 3.

#### Layer 4 — Discovery: Mask-Filtered Cast/Ripple

Cast and Ripple queries are the discovery mechanism — they let processes find resources by type, name, or attribute. Every bridge has a 32-bit `access_mask`. Before a Stone can touch a Pond, the check `(process_mask & bridge.access_mask) != 0` is evaluated.

**The critical property:** a failing mask check causes the Pond to be **absent from results**, not denied. There is no "permission denied" response. From the querying process's perspective, a Pond it cannot reach simply does not exist. This prevents information leakage — a process cannot even discover that a resource exists if it lacks the correct mask bits.

This is enforced at the `_touch_pond()` level before the owner announcement, meaning even the Pond owner does not learn about the query if the mask check fails.

#### Layer 5 — Bridge Access: Bidirectional Mask Check

Every bridge has a 32-bit `access_mask` checked in both directions:

- **Inbound:** when data enters the Pond, `(process_mask & bridge.access_mask) != 0`
- **Outbound:** when data leaves the Pond, the same check applies

A single mask per bridge — no lists, no rules, no lookup tables. O(1) per check regardless of how many processes exist or how large the system grows. The mask check is performed before the whitelist check — if the mask fails, the check short-circuits and no log entry is written.

**Why bidirectional:** An inbound-only check prevents unauthorised writes but allows a low-privilege process to receive data it shouldn't see on the outbound path. The bidirectional check ensures that a process cannot use a bridge as a covert channel to receive data from a higher-privilege Pond.

#### Layer 6 — Identity Inheritance: Mask Lineage

Every object a process creates inherits the creator's process_mask. The full inheritance chain:

```
User account (mask set at account creation)
  → Session (inherits user mask)
    → COMPANION instance (inherits session mask)
      → Pond (inherits COMPANION mask)
        → Bridge (inherits Pond mask)
          → FS Pond (inherits Bridge mask)
            → File (inherits FS Pond mask)
```

There is no way for a process to create an object with a higher mask than its own. A user with tenant-3 bits set cannot create a Pond visible to tenant-1. No escalation through object creation — the mask lineage is monotonically non-increasing from creator to created object.

#### Layer 7 — Session Provisioning: Template Pond Cloning

When a user joins the system, COMPANION does not give them access to a shared namespace. Instead, it clones a Template Pond matched to the user's mask pattern and gives them their own private copy.

**Template Ponds** are pre-configured environments stored in the ShoreKeeper's hidden table (`template_ponds`), keyed by mask pattern. A user with an admin mask gets an admin-configured environment. A user with a tenant-3 user mask gets a tenant-3 user environment. Templates are defined by the system operator and are invisible to users.

**The effect:** two users with the same mask pattern get identical environments but completely separate address spaces. User A's Ponds are never visible to User B — they share the same template but inhabit different clones. Resource caps are enforced by COMPANION via Ward monitoring of the cloned environment.

#### Layer 8 — Filesystem: Mask-Shaped Views

The filesystem is implemented as a collection of FS Ponds. Each path entry is a bridge. Directory listings are filtered by the caller's process_mask: if `(process_mask & bridge.access_mask) == 0`, the path is absent from the listing — not permission-denied, not visible.

**The consequence:** two users with different masks see different directory structures. A user without the admin flag does not see `/system/` paths. A tenant-3 user does not see tenant-1 paths. The filesystem is a mask-shaped view of the same underlying structure.

This also means that adding a file to a protected directory cannot accidentally expose it to unprivileged users — the bridge mask on the directory entry controls who can see it was ever added.

#### Layer 9 — Card Boundary: ShoreKeeper Validation

All cross-card traffic is validated by the ShoreKeeper at the source card before transmission and by the ShoreKeeper at the destination card on receipt. Both checks:

1. **Auth check:** source card's auth token must be known to the destination ShoreKeeper
2. **Mask check:** `(process_mask & bridge.access_mask) != 0` in both directions
3. **PTT translation:** PTT-relative addresses translated to raw addresses per card

The cross-card bus carries only pre-validated data and aggregated heartbeat summaries. Individual cell states, PTT hidden fields, auth tokens, salt keys, and individual Ward heartbeats never cross card boundaries.

**Why both ends validate:** The source ShoreKeeper prevents malformed or unauthorised data from entering the cross-card bus. The destination ShoreKeeper validates that the data is appropriate for the destination Pond's current state. Neither ShoreKeeper trusts the other blindly — the auth check at the destination ensures the source card is legitimate.

#### Security at scale

The nine-layer model has a key scaling property: the cost of security enforcement does not increase with system size. A system with 1 million Ponds and 100,000 users has the same per-operation security cost as a system with 10 Ponds and 5 users:

```
Layer 1 — auth token:    1 comparison per command
Layer 3 — process mask:  1 lookup per operation
Layer 4 — cast filter:   1 AND per discovered item
Layer 5 — bridge check:  1 AND per bridge transit
Layer 6 — inheritance:   0 cost (mask copied at creation)
Layer 9 — card boundary: 1 AND per hop
```

No security operation is O(n) in the number of users, processes, or resources. This is a fundamental design requirement for a system intended to run at billion-cell scale.

### Shore

The Shore registry maps resource names to addresses and metadata. ShoreV2 extended the basic registry with Ward state tracking, connection suspension/restoration for hot migration, and hidden table support for COMPANION-only entries.

### Ward

The Ward is the health monitor for a single Pond. It tracks emission history, detects stall and silence conditions, and escalates to COMPANION when thresholds are crossed. The Ward state machine: IDLE → HEALTHY → DEGRADED → STALLED/SILENT → ISOLATED.

**Thermal tracking** was added to Ward: each Ward tracks `thermal_load`, `thermal_limit`, `thermal_trend`, and `thermal_zone`. The simulation model: armed cells contribute 0.001 units/tick, idle cells 0.0001 (leakage), exponential decay factor 0.999. States: NOMINAL (<100%), THROTTLE (≥100%), FREEZE (≥120%), MIGRATE (≥150%). On real hardware, simulated load is replaced by thermal telemetry bus data with no change to Ward logic.

**Dissolve contract** (CONDITIONAL ponds): `set_dissolve_contract(condition, action)` stores a lifecycle contract hidden from the Pond. `evaluate_dissolve(context)` checks the condition and fires the action once when met. Five condition types: TIME, RETURN, COMPLETE, EXTERNAL, COMPOUND (ANY/ALL). Three actions: DISSOLVE, FREEZE, CHECKPOINT.

### COMPANION

The COMPANION Pond is the OS anchor — permanent, HIDDEN, always running. It manages the rule engine (stall → restart → isolate), key issuance and revocation, and the escalation hierarchy. COMPANION's `_execute_action()` was extended to actually call `pond.restart()` when ACTION_RESTART is decided, with automatic fallback to ISOLATE if restart fails.

### Cast / Ripple

The Cast engine provides distributed resource discovery. A Stone thrown into the registry touches Ponds according to visibility rules. Results return as a ReturnWave.

Process mask filtering was added as security layer 4: `(process_mask & bridge.access_mask) != 0` — otherwise the Pond is absent from results. The mask is carried in the Stone and checked in `_touch_pond()` before the owner announcement. This means a process with the wrong mask never learns the Pond exists.

### ShoreKeeper and HyperShore

The federated monitoring architecture emerged from the need to keep cross-card buses clean. Instead of every cell reporting health data to a central registry, each card runs a ShoreKeeper — a SHOREKEEPER-type Pond that aggregates all Ward states into a single heartbeat packet sent upstream every N ticks.

```
Cell → Local Ward → ShoreKeeper (per card) → HyperShore (master card)
```

**Design principle:** the cross-card bus carries only pre-validated Pond data and aggregated heartbeat summaries. Raw cell states, individual Ward data, auth tokens, and PTT hidden fields never cross card boundaries.

HyperShore maintains the global registry of all cards, tracks thermal balance across the system, and provides `hottest_card()` / `coolest_card()` for thermal-driven migration decisions.

---

## Phase 5 — VM Image, Migration, Command Interface (Weeks 6–8)

### Three-bus command interface

The CommandInterface was added as Option C of the architecture migration — a translation layer that converts the three-bus command protocol to existing cell operations. Cells, tiles, and the compiler are unchanged; OS-level code uses CommandInterface.

```
Bus 1 (Command & Control):
  bits  0-3:   command code (0-15)
  bits  4-14:  auth token field (11 bits — carries the 12-bit card token,
               11 usable bits; upper bit checked via stored mask)
  bit  15:     address mode (0=PTT-relative, 1=raw system address)
  bits 16-17:  scope (00=LOCAL 32-bit, 01=SHORE 48-bit, 10=EXTENDED 64-bit)
  bits 18-21:  handshake field — ACK/REQ signalling on bridge cells only
               0x0=NONE 0x1=ACK 0x2=NAK 0x3=BUSY 0x4=REQUEST
               0x5=GRANT 0x6=DENY 0x7=RETRY 0x8-0xF=reserved
  bits 22-31:  reserved for future use

Bus 2 (Data Payload):   32-bit value
Bus 3 (Target Address): cell address (raw or PTT-relative)
```

The handshake field (bits 18-21) is bridge-level only — ignored on compute cells. It travels with the command on Bus 1 at no extra cost. The scope field (bits 16-17) implicitly identifies the handshake level: LOCAL = pond-to-pond, SHORE = card-to-card, EXTENDED = system-to-system. The Ward monitors bridge handshake state — persistent BUSY or high NAK/DENY rates surface as PTT health concerns automatically.

Commands 3 (RECONFIGURE), 4 (FREEZE), 5 (RELEASE) are system-only and require the auth token on Bus 1. Silent rejection on mismatch — no error signal to the caller, no acknowledgement that the command was received.

### VM image

The VM image format evolved through three versions:

- **v1:** basic array snapshot (cell gate_state and addresses)
- **v2:** added Shore registry, Companion key state
- **v3:** added 32-bit gate_state field, OS name/version stamp, PTT/PondManager snapshot

Every v3 image header contains `os_name: Claudette`, `os_version: 1.1`, `gate_state_bits: 32`. Old v1/v2 images load correctly because bits 0–10 are unchanged — the NOR topology encoding is backwards-compatible.

### Migration

`pond.migrate()` implements hot migration in two modes:

**FREEZE_BODY:** internal cells frozen, bridges stay registered. Connected Ponds keep running — data flows to the old address briefly and then resumes at the new address. Shore suspends connections, relocate() updates addresses, Shore restores connections. Duration: ~95 array ticks.

**FREEZE_FULL:** everything stops, all bridges frozen, complete snapshot.

---

## Phase 6 — GPU Backend, Program Image, User Library (Weeks 9–10)

### GPU Stage 1

The `GPUArrayBackend` replaces the per-cell Python loop with a vectorised NumPy/CuPy operation. Auto-detects GPU or falls back to NumPy. The CPU/GPU split:

- **VRAM:** cell array (gate_state, addresses, flags) — GPU owns between ticks
- **RAM:** bus buffer (address → value) — CPU owns, fed to GPU

Hardware target: NVIDIA GTX 970, 4GB GDDR5, compute 5.2 (Maxwell). Benchmark: 1.8M cells/sec on NumPy CPU; estimated ~180M cells/sec on 970 GTX at full vectorisation.

Stage 2 (planned): persistent VRAM state, vectorised bus gather, CPU only receives capture values.

### Program Image with Named Ranges

`ProgramImage` is a self-describing executable unit with a four-section layout:

```
MANIFEST HEADER   — program_id, name, Claudette version stamp, cell count
MODELS NEEDED     — tile names required to run
NAMED RANGES      — the CPU/GPU reference layer
PROGRAM SCRIPTS   — compiled CellMapRecord list
```

Named ranges classify every address in the program: INPUT (caller supplies), OUTPUT (caller reads), ACCUMULATOR (loop variable with storage), LOOP_TICK, LOOP_LIMIT, SCRATCH. The named range table is the contract between CPU and GPU — CPU uses `bus_address` by name, GPU uses `vram_offset` as direct index into the cell array.

### User Tile Library

User-designed tiles can be added to Claudette without modifying core files. A user tile file is identified by the marker `# LIBRARY MODEL` in the first 10 lines. The system:

1. Scans `~/.claudette/user_tiles/` at startup
2. Validates imports via AST (only fp_tiles, gate_states, controller, math permitted)
3. Executes tile builder functions in a restricted namespace
4. Measures depth and cell count automatically
5. Registers tiles in the CombinedLibrary alongside core tiles

User tiles take precedence over core tiles with the same name. Bad imports are rejected before any code executes — the AST check runs first.

### Mouse, Audio and Video Device Bridges

`device_bridge.py` was extended with four new device types:

**MouseBridge** — fully implemented. Reads pygame mouse events in a background thread at 200Hz. Packs each event into a 32-bit word: event type (move/button_down/button_up/wheel) in the top byte, button mask and delta X/Y in the lower bytes, written to `OUT_ADDR` at `base_address=0x00C10000`. Full position readable via `MS_CMD_GET_X` / `MS_CMD_GET_Y`. If pygame is not available it runs as a connected stub returning no events.

**AudioBridge (stub)** — command set defined (`AU_CMD_OPEN`, `AU_CMD_WRITE`, `AU_CMD_FLUSH`, `AU_CMD_SET_GAIN` etc.) but no simulation implementation. The reasoning is deliberate: a 44,100 Hz sample rate requires a new sample every 22 microseconds — a deadline Python cannot reliably meet alongside the cell array sim. When real silicon arrives, a USB audio device appears as a PERIPHERAL Pond and the AudioBridge forwards samples to the USB driver. The tile library already has `AUDIO_IN_HANDLER` and `AUDIO_OUT_HANDLER` peripheral stubs (2,800 cells, depth 24, 4 lanes for stereo).

**VideoBridge (stub)** — command set defined (`VD_CMD_OPEN`, `VD_CMD_READ` etc.) but no simulation implementation. Video OUTPUT is already handled by DisplayPond — the cell array writes pixel values to display cell addresses. Video DECODE (H.264, AV1) requires dedicated tiles (DCT, motion compensation) that do not yet exist. Raw RGB24 input maps directly to DisplayPond addresses and will work once timing constraints are solved on real hardware. The `DISPLAY_HANDLER` tile (18,600 cells, depth 32, 8 outbound lanes for pixel stream) handles the output side.

**MOUSE_HANDLER tile** added to the tile library: 960 cells, depth 12, 2 outbound lanes (packed event word + position).

---

## Phase 7 — LLVM Frontend and IR Mapper (Week 10)

### LLVM Frontend

`llvm_frontend.py` accepts LLVM IR text (`.ll` format) and validates it against the supported instruction subset. Uses llvmlite for parsing. Returns a `FrontendResult` containing `LLVMFunction` parse trees.

**Supported:** add, sub, and, or, xor, icmp (eq/ne/slt/sgt/sle/sge), phi, br (conditional/unconditional), ret, alloca, load, store, permitted intrinsics (ctpop, bswap, ctlz, cttz).

**Rejected with clear errors:** getelementptr, exceptions (invoke/resume), vector/SIMD, i64/float/double, extern calls.

The full LLVM pipeline:
```
clang -S -emit-llvm -O1 file.c -o file.ll
LLVMFrontend.parse(ll_source)  →  LLVMFunction parse tree
LLVMIRMapper.lower(fn)         →  ProgramImage
program.run(inputs={...})      →  result dict
```

### LLVM IR Mapper

`llvm_ir_mapper.py` lowers `LLVMFunction` parse trees to `ProgramImage`. Mapping strategy:

- Arithmetic instructions → tile placement (same tiles as Python compiler)
- icmp eq/ne → INT32_EQ tile ± NOT
- icmp slt/sgt/sle/sge → INT32_SUB sign bit extraction
- phi nodes → LATCH+LOOP_MODE storage cells (same model as while-loop variables)
- Conditional br → GS_SELECT routing
- Unconditional br → direct address flow
- alloca/load/store → address slots + PASS cells

Blocks processed in reverse-post-order (RPO). Phi nodes pre-allocated in pass 1 before instruction lowering in pass 2.

---

# PART 2 — FILE REFERENCE

## Core Simulation Layer

| File | Purpose |
|------|---------|
| `unicell.py` | UniCell — single NOR-gate cell with 32-bit gate_state, 5 registers (config, mode, input_address, output_address, data + start_flag = 129 bits total), mode flags, loop-back, trace, breakpoint |
| `unicell_array.py` | UniCellArray — array of cells sharing a bus dict. tick() advances all armed cells. Segments for isolation, trace buffer, breakpoint halt |
| `gate_states.py` | All gate_state constants: GS_NOT, GS_PASS, GS_SELECT, LOOP_MODE, GS_LATCH, GS_ONE_SHOT, GS_INVERT_OUT, GS_BROADCAST, GS_SYNC_WAIT, GS_LOOP_BACK, GS_PRIORITY, GS_TRACE, GS_BREAKPOINT. Config register layout: bits 0-10 NOR topology, 11-14 ECC, 15-26 auth mask |
| `controller.py` | ImagoController — loads CellMapRecord lists into the array, manages regions, provides run() with capture address support, freeze/thaw regions |
| `ecc.py` | Error-correcting code — Hamming-based ECC, single-bit error correction, double-bit detection |
| `multi_dimm.py` | Multi-card array support — multiple UniCellArrays with cross-array bus routing |

## Tile Library

| File | Purpose |
|------|---------|
| `fp_tiles.py` | Full tile library — NORBuilder (depth-tracking NOR construction), TileAddressAllocator, 40 built-in tiles including INT32_ADD/SUB/EQ/MUX, INT32_ADD_CLA, INT32_NOT/AND/OR/XOR/MAX/MIN, COUNTER_SHIFT/RIPPLE/DECREMENT, SR_LATCH, RING_OSC, PULSE_GEN, DELAY_4/8/16, PARITY_32, LFSR_16, FP32 tiles, peripheral stubs (KEYBOARD_HANDLER, MOUSE_HANDLER, SENSOR_HANDLER, AUDIO_IN/OUT_HANDLER, DISPLAY_HANDLER, NETWORK_HANDLER), TileLibrary registry, TilePlacer |
| `user_library.py` | User tile library — scans LIBRARY MODEL files, AST import sandbox (permitted: fp_tiles, gate_states, controller, math), restricted exec namespace, cell count and depth measured automatically, CombinedLibrary for unified lookup with user tiles taking precedence |

## Compiler

| File | Purpose |
|------|---------|
| `compiler.py` | ImagoCompiler — compiles Python function AST to CellMapRecord list. Handles: integers, booleans, assignment, augmented assignment (+=/-=), if/else, while, for (SHIFT and RIPPLE paths), return, ast.Pass, chained comparisons |
| `compiler_int32.py` | Int32 compiler extension — lowers Int32Value operations through tile library, AugAssign override, literal coercion, sign bit placement |
| `ir.py` | Intermediate representation — IRNode, IRGraph, IRAllocator (address allocation), lower_to_cell_map() |
| `branch.py` | Branch and select tile construction — GS_SELECT cell wiring for if/else |
| `llvm_frontend.py` | LLVM IR frontend — parses .ll text via llvmlite, validates supported instruction subset, emits LLVMFunction parse trees with CFG and phi node incoming values |
| `llvm_ir_mapper.py` | LLVM IR mapper — lowers LLVMFunction to ProgramImage. Tile placement for arithmetic, sign-bit icmp, phi→storage cells, br→GS_SELECT, RPO block ordering |

## OS Layer — Claudette v1.1

| File | Purpose |
|------|---------|
| `companion.py` | COMPANION OS anchor — OS_NAME=Claudette, OS_VERSION=1.1, OS_FULL_NAME, OS_DESCRIPTION constants, rule engine, action executor, key issuance/revocation, ACTION_RESTART wired to pond.restart() with ISOLATE fallback |
| `pond.py` | Pond class — resource pool with bridge-gated access. Security levels (OPEN/PRIVATE/HIDDEN), whitelist, bidirectional access_mask, visit log, migrate(), restart(), checkpoint(), freeze_pond(), token space, PTT attachment. PondManager |
| `pond_types.py` | Pond type registry — all built-in types (PROCESS, WORKSPACE, FILE, PERIPHERAL, LIBRARY, BOOT, COMPANION, DEVICE, SHORE, FS, CONDITIONAL, SHOREKEEPER, HYPERSHORE), dissolve constants |
| `pond_ptt.py` | Pond Process Translation Table — maps process IDs to cell addresses, hidden fields (process_mask, bubble_id, thermal fields), PTT serialisation |
| `ward.py` | Ward health monitor — emission tracking, stall/silence detection, state machine (IDLE/HEALTHY/DEGRADED/STALLED/SILENT/ISOLATED), thermal tracking (load/limit/trend/zone/state with NOMINAL/THROTTLE/FREEZE/MIGRATE thresholds), dissolve contract (5 condition types, 3 actions) |
| `shore_v2.py` | ShoreV2 registry — ShoreEntry, register/lookup/update/suspend_connections/restore_connections, hidden table support |
| `shorekeeper.py` | ShoreKeeper (per-card Ward collective + boundary authority) — heartbeat aggregation, thermal rollup, armed cell counting, escalation callbacks. HyperShore (global registry) — multi-card health, hottest/coolest card, escalation routing |
| `cast.py` | Cast/Ripple discovery engine — Stone, ReturnWave, RippleResult, ripple_cast() with process_mask filtering (absent ≠ denied), skipping_stone() |
| `command_interface.py` | Three-bus command protocol — 12-bit auth token enforcement, Commands 0-8, PTT-relative and raw addressing, boot_all_cells() for BIOS dead-cell-check pass |

## Program Execution

| File | Purpose |
|------|---------|
| `program_image.py` | ProgramImage — four-section format (MANIFEST HEADER / MODELS NEEDED / NAMED RANGES / PROGRAM SCRIPTS). NamedRange with bus_address (CPU) and vram_offset (GPU). run() via CPU controller, run_gpu() via GPU backend, serialise/restore |
| `vm_image.py` | VM image v3 — OS stamp (os_name=Claudette, os_version=1.1), gate_state_bits=32, PTT/PondManager snapshot, Shore/COMPANION serialisation, gzip support. Backwards-compatible with v1/v2 images |
| `gpu_array.py` | GPU array backend — GPUArrayBackend with CuPy (GPU) or NumPy (CPU fallback). Packed cell array (5×uint32 per cell), vectorised tick(), load_from_unicell_array(), benchmark() |

## Filesystem and Search

| File | Purpose |
|------|---------|
| `uniflex_fs.py` | UniFlex filesystem — Pond-based file storage with token addressing |
| `fs_search.py` | File search index — heuristic text search, SearchIndex, SearchPond integration |

## Hardware Interface

| File | Purpose |
|------|---------|
| `device_bridge.py` | Hardware device bridge — connects physical hardware to the cell array via bridge cells. KeyboardBridge (stdin → bus 0x00C00000), MouseBridge (pygame events → bus 0x00C10000), AudioBridge (stub — USB audio, no sim), VideoBridge (stub — capture/decode, no sim) |
| `visualiser.py` | Array state visualiser — renders cell activity to terminal or browser |
| `workbench.py` | CLI workbench — browser-based terminal for interacting with a running Claudette system. `ver` command shows Claudette v1.1 header |

## Miscellaneous

| File | Purpose |
|------|---------|
| `sequencer.py` | Program sequencer — manages ordered execution of compiled programs |
| `pipeline_queue.py` | Pipeline queue — buffers data between pipeline stages |
| `packet_spec.py` | Packet format specification for cross-bridge data |
| `model_library.py` | Model registry — tracks loaded tile models and their instances |
| `program_builder.py` | High-level program builder API |
| `run_companion.py` | Standalone COMPANION runner |
| `apollo_guidance.py` | Apollo Guidance Computer simulation — demonstration program |

---

# PART 3 — TEST RESULT SHEET

## Claudette v1.1 — Test Results
### Run date: April 2026 | 45 suites | 2586 tests | 0 failures

| Suite | Tests | Pass | Fail | Coverage |
|-------|-------|------|------|----------|
| test_array.py | 21 | 21 | 0 | UniCellArray tick, bus, segments, armed set |
| test_branch.py | 61 | 61 | 0 | GS_SELECT, if/else routing, branch tiles |
| test_bridge_anomaly.py | 60 | 60 | 0 | Routing anomaly detection, rejection tracking |
| test_bridge_integration.py | 55 | 55 | 0 | Inbound/Outbound bridge integration, visit log |
| test_cast.py | 54 | 54 | 0 | Cast/Ripple, Stone, process_mask filtering, skipping stone |
| test_cla.py | 44 | 44 | 0 | Carry-lookahead adder correctness and depth |
| test_command_interface.py | 47 | 47 | 0 | 3-bus protocol, 12-bit auth enforcement, boot sequence |
| test_compiler.py | 35 | 35 | 0 | Python AST → CellMapRecord, basic constructs |
| test_compiler_int32.py | 58 | 58 | 0 | Int32Value, AugAssign, chained comparisons, literal coercion |
| test_compiler_tile_library.py | 38 | 38 | 0 | Compiler tile integration, tile selection |
| test_conditional_pond.py | 41 | 41 | 0 | CONDITIONAL pond, Ward dissolve contract, all 5 conditions, 3 actions |
| test_controller.py | 26 | 26 | 0 | Region loading, run(), capture addresses, freeze/thaw |
| test_counter_tiles.py | 86 | 86 | 0 | SHIFT/RIPPLE/DECREMENT counters, all widths |
| test_device_bridge.py | 34 | 34 | 0 | Hardware device bridge, register mapping |
| test_ecc.py | 54 | 54 | 0 | ECC encode/decode, single-bit correction, double-bit detection |
| test_for_loop.py | 21 | 21 | 0 | For loop SHIFT path (n≤32), RIPPLE path (n>32/variable), ast.Pass |
| test_fp_tiles.py | 134 | 134 | 0 | Full tile library build and metadata check (40 tiles inc. MOUSE_HANDLER) |
| test_freeze.py | 47 | 47 | 0 | Region freeze/thaw, partial freeze, breakpoint halt |
| test_fs_search.py | 43 | 43 | 0 | File search index, heuristic matching, SearchPond |
| test_gate_state_32.py | 73 | 73 | 0 | 32-bit gate_state constants, all mode flags, config register layout |
| test_gpu_array.py | 35 | 35 | 0 | GPUArrayBackend, tick kernel, NumPy/CuPy detection, benchmark |
| test_llvm_frontend.py | 77 | 77 | 0 | LLVM IR parse, CFG construction, icmp predicates, phi nodes, rejection |
| test_llvm_ir_mapper.py | 86 | 86 | 0 | LLVM → tiles, icmp sign-bit, phi→storage cells, multi-function, alloca |
| test_migration.py | 33 | 33 | 0 | FREEZE_BODY, FREEZE_FULL, VM save+restore, post-migrate snapshot |
| test_multi_dimm.py | 36 | 36 | 0 | Multi-card array, cross-array routing |
| test_new_tiles.py | 57 | 57 | 0 | INT32_NOT/AND/OR/XOR/MAX/MIN, DELAY, PARITY_32, LFSR_16 functional |
| test_pond.py | 163 | 163 | 0 | Full Pond lifecycle, whitelist, token space, bridges |
| test_pond_ptt.py | 75 | 75 | 0 | PTT, hidden fields, process_mask, bubble_id |
| test_pond_region_scope.py | 42 | 42 | 0 | Region-scoped cell grants, scope validation |
| test_pond_restart.py | 44 | 44 | 0 | restart(), checkpoint(), freeze_pond(), bidirectional access_mask |
| test_pond_types.py | 64 | 64 | 0 | Type registry, CONDITIONAL/SHOREKEEPER/HYPERSHORE types |
| test_program_builder.py | 28 | 28 | 0 | High-level program builder API |
| test_program_image.py | 66 | 66 | 0 | Named ranges, manifest, run(), GPU load, round-trip serialise |
| test_select.py | 43 | 43 | 0 | SELECT cell, branch routing, priority |
| test_shore.py | 49 | 49 | 0 | Shore v1 registry, lookup, update |
| test_shore_v2.py | 114 | 114 | 0 | ShoreV2 full feature set, hidden tables, connection management |
| test_shorekeeper.py | 47 | 47 | 0 | ShoreKeeper heartbeat, HyperShore global health, thermal, escalation |
| test_tile_library.py | 66 | 66 | 0 | TileLibrary registry, metadata, placer |
| test_uniflex.py | 75 | 75 | 0 | UniFlex filesystem, token addressing, file operations |
| test_user_library.py | 54 | 54 | 0 | LIBRARY MODEL scan, import sandbox, CombinedLibrary, user override |
| test_vm_image.py | 54 | 54 | 0 | VM image v3, OS stamp, PTT snapshot, save/restore, gzip |
| test_ward.py | 83 | 83 | 0 | Ward state machine, thermal tracking, dissolve contract, escalation |
| test_while.py | 39 | 39 | 0 | While loop compilation, storage cell, loop variable persistence |
| **TOTAL** | **2586** | **2586** | **0** | **45 suites — 100% pass rate** |

---

# PART 4 — CLI COMMAND REFERENCE

## Workbench Shell — Claudette v1.1

The workbench is accessed via browser at `http://localhost:<port>` after calling `workbench.serve()`, or programmatically via `workbench.handle_command(cmd)`. Commands are case-insensitive. Arguments separated by spaces.

---

### System Information

| Command | Aliases | Description |
|---------|---------|-------------|
| `ver` | `version`, `status` | Display Claudette v1.1 header, array usage, region count, cycle count, Shore/Companion/Device/Search status |
| `help` | `?`, `h` | Display full command reference |
| `cls` | `clear` | Clear the terminal output |

**Example:**
```
> ver
Claudette v1.1
Imago UniCell Workbench
────────────────────────────────
Array:     247/65536 cells
Regions:   3
Cycles:    1204
Shore:     online
Companion: online
```

---

### Array and Regions

| Command | Aliases | Flags / Args | Description |
|---------|---------|--------------|-------------|
| `ps` | `regions` | — | List all loaded regions with ID, name, cell count, armed state |
| `df` | `array` | — | Array usage: cells used/total, armed count, segment breakdown, bus utilisation |
| `kill <region>` | — | `<region>`: region ID or name | Free a region and deallocate its cells |
| `freeze <region>` | — | `<region>`: region ID or name | Snapshot and halt a region (cells stop, values preserved) |

**Example:**
```
> ps
Region 0  'and_prog'     5 cells   armed
Region 1  'loop_test'    6 cells   idle
Region 2  'companion'    12 cells  armed
```

---

### Shore Registry

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `ls` | `dir` | `[TYPE]` optional filter | List Shore registry entries. TYPE filters by resource type (POND, BRIDGE, TILE, FILE, etc.) |
| `cat <n>` | `inspect <n>` | `<n>`: entry name or index | Inspect full details of a Shore entry: addresses, Ward state, metadata, connections |

**Flags for `ls`:**
- `ls POND` — show only Pond entries
- `ls BRIDGE` — show only Bridge entries
- `ls FILE` — show only File entries
- `ls` (no arg) — show all entries

**Example:**
```
> ls
  [1] workspace_alice    POND    0x00200000  HEALTHY
  [2] inbox              POND    0x00210000  HEALTHY
  [3] workspace_alice_IN BRIDGE  0x00200010  HEALTHY
> cat workspace_alice
  Name:    workspace_alice
  Type:    POND
  Address: 0x00200000
  Ward:    HEALTHY (idle 0 cycles)
  Owner:   alice
  Bridges: INBOUND @ 0x00200010, OUTBOUND @ 0x00200020
```

---

### Ward Monitoring

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `ward <n>` | — | `<n>`: Pond name or index | Show Ward state for one Pond: state, emission history, anomaly count, thermal summary |
| `ward --all` | — | `--all` flag | Show Ward states for all registered Ponds in a compact table |
| `escalate <n> <state>` | — | `<n>` Pond name, `<state>` ward state string | Manually trigger a Ward state transition and COMPANION escalation. Used for testing the rule engine |

**Ward states:** IDLE, HEALTHY, DEGRADED, STALLED, SILENT, ISOLATED

**Thermal states:** NOMINAL, THROTTLE (≥100% of limit), FREEZE (≥120%), MIGRATE (≥150%)

**Example:**
```
> ward workspace_alice
  Pond:         workspace_alice
  State:        HEALTHY
  Cycles:       1204
  Emissions:    avg 4.2/cycle  peak 12
  Thermal:      load=0.034  limit=100.0  state=NOMINAL  zone=block_0
  Anomalies:    0
```

---

### Search

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `search <query>` | `find`, `grep` | `<query>`: text to search | Heuristic search across all indexed files and Pond names. Returns ranked results |

---

### Devices

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `devices` | `dev` | — | List all registered device bridges with name, type, direction, and connection status |

**Example:**
```
> devices
  keyboard    KEYBOARD   inbound   connected   0x00C00000
  mouse       MOUSE      inbound   connected   0x00C10000
  storage     STORAGE    inbound   connected   0x00D00000
  audio       AUDIO      outbound  stub        0x00C20000
  video       VIDEO      inbound   stub        0x00C30000
```
Audio and video show as `stub` — no simulation implementation.
On real hardware they connect to USB devices.

---

### Tile and Model Library

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `tile` | — | — | List all available tiles (core + user) with cell count and pipeline depth. User tiles marked `[USER]` |
| `tile <n>` | — | `<n>`: tile name | Inspect tile: operation, cell count, depth, input/output port counts, notes |
| `model` | — | — | List all loaded model instances |
| `model <n>` | — | `<n>`: model name | Inspect a model instance |

**Example:**
```
> tile
  INT32_ADD_CLA    3219 cells  depth  58
  INT32_AND         160 cells  depth   3
  INT32_NOT          32 cells  depth   1
  COUNTER_RIPPLE_8  924 cells  depth   4
  LFSR_16           185 cells  depth  10
  PASSTHROUGH_4       8 cells  depth   2   [USER]
```

---

### Cast / Discovery

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `cast` | — | `[key=value ...]` optional query | Cast a Stone into the registry. Results filtered by caller's process_mask — invisible Ponds absent, not denied |

**Query keys:** `pond_type`, `name_contains`, `security_level`, `ward_state`, `has_tile`, `ptt_active_min`, `ptt_faulted`, `search_query`

---

### VM Image

| Command | Aliases | Flags / Args | Description |
|---------|---------|-------------|-------------|
| `image save <path>` | — | `<path>`: .img or .img.gz | Save complete system snapshot: array, Shore, Companion, PTT, OS stamp |
| `image info` | — | — | Display current system state summary without saving |

---

## Gate State Flags Reference

| Constant | Bit | Description |
|----------|-----|-------------|
| `GS_NOT` | topology=1 | Invert input |
| `GS_PASS` | topology=0 | Pass input unchanged |
| `GS_SELECT` | topology=2 | Route A or B based on condition |
| `LOOP_MODE` | bit 9 | Cell loops back output to input |
| `GS_LATCH` | bit 11 | Store output in data register each tick |
| `GS_ONE_SHOT` | bit 12 | Disarm after first firing |
| `GS_INVERT_OUT` | bit 13 | Invert output signal |
| `GS_BROADCAST` | bit 14 | Write to address range |
| `GS_SYNC_WAIT` | bit 15 | Wait for two sequential arrivals (async merges only) |
| `GS_LOOP_BACK` | bit 16 | Feedback output to input address |
| `LOOP_BACK_SRC` | bits 17-19 | Loop-back source selector |
| `LOOP_BACK_DST` | bits 20-22 | Loop-back destination selector |
| `GS_PRIORITY` | bit 29 | High-priority cell (scheduled first) |
| `GS_TRACE` | bit 30 | Record to trace buffer on fire |
| `GS_BREAKPOINT` | bit 31 | Halt array on fire |

---

## Cell Register Layout (161 bits per cell)

### Config Register (64-bit, Command 3 / system only)

```
Lower 32 bits (CMD_RECONFIGURE + scope=LOCAL):
  bits  0-10:  NOR topology      (fanin — 11 bits, unchanged from v1)
  bits 11-14:  ECC configuration
  bits 15-26:  Auth mask          (12-bit card token stored at boot — HIDDEN)
  bits 27-31:  Reserved

Upper 32 bits / _config_upper (CMD_RECONFIGURE + scope=EXTENDED):
  bits 32-63:  Extended forwarding address upper half
               Active only when GS_ADDR_LATCH (bit 23) set
               full_addr = (_config_upper << 32) | output_address
               Enables 64-bit addressing: large files, cross-card routing
               ZERO connection to data bus or NOR compute path
               Same command bus wire — config register extended to 64 bits
```

### Mode Register (32-bit)

```
bit  11:  GS_LATCH        — store output in data register each tick
bit  12:  GS_ONE_SHOT     — disarm after first firing
bit  13:  GS_INVERT_OUT   — invert output signal
bit  14:  GS_BROADCAST    — write to address range
bit  15:  GS_SYNC_WAIT    — wait for two sequential arrivals (async merges only)
bit  16:  GS_LOOP_BACK    — feedback output to input address
bits 17-19: LOOP_BACK_SRC
bits 20-22: LOOP_BACK_DST
bit  23:  GS_ADDR_LATCH   — bridge: upper config = upper 32 of 64-bit forwarding address
                            cell fires 4-tuple; stored in array._extended_addresses
bits 24-28: reserved
bit  29:  GS_PRIORITY     — scheduled first each tick
bit  30:  GS_TRACE        — record to trace buffer on fire
bit  31:  GS_BREAKPOINT   — halt array on fire
```

### Other Registers

```
Input address register:   32 bits
Output address register:  32 bits  (lower 32 of 64-bit address when addr_latch set)
Data register:            32 bits  (NOR compute only — never used for addressing)
Start flag:                1 bit   (armed=1, disarmed=0)

Total per cell: 64 + 32 + 32 + 32 + 32 + 1 = 161 bits (≈21 bytes)
```

### Config sequence for addr_latch bridge cells

```
Field 0: gate_state       (lower config — GS_ADDR_LATCH bit 23 set)
Field 1: input_address    (32-bit local listen address)
Field 2: output_address   (lower 32 of 64-bit forwarding address)
         stays open when addr_latch is set
Field 4: _config_upper    (upper 32 — CMD_RECONFIGURE + scope=EXTENDED)

Normal compute cells close at Field 2. Zero overhead for 99% of cells.
Bridge cells with addr_latch stay open until Field 4.
```

### Simulation scaling at 161 bits/cell (GPU backend)

The 21 bytes/cell figure is the **software simulation cost** — how much
GPU VRAM the `GPUArrayBackend` numpy model needs per cell. This is not
a hardware requirement. On real silicon each cell's registers live in
the transistors themselves; no external memory is needed to hold cell state.

```
970 GTX (3.5 GB usable VRAM for simulation):
  3.5 × 10⁹ bytes / 21 bytes = ~167 million cells modelled per GPU card

For silicon targets see Part 5 — Silicon Hardware Reference.
For the object model and PTT hierarchy see the Object Model section above.
```


---

## Object Model — Everything is an Object

Claudette uses a three-level object hierarchy instead of a flat address
space. Every resource — cell, Pond, bridge, program, file, display,
session — is an object with a 32-bit local ID. Objects contain other
objects. Bridges navigate between levels.

### Core principle

```
Old model:  32-bit address → physical cell location
            Breaks at 4.29B cells (12-layer card has 30.24B)

New model:  32-bit object ID → object in THIS scope
            Bridge navigates to next scope if not found locally
            Each level has its own independent 32-bit ID space
            Scales without limit — you reference the container,
            the container knows where its contents are
```

### The three PTT levels

```
┌─────────────────────────────────────────────────────────────────┐
│  EXTENDED PTT  (32-bit IDs)                                     │
│  Objects beyond this card — remote cards, global services       │
│  Managed by: HyperShore / HyperCompanion                        │
│  Lookup: cross-card bus, milliseconds                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  SHORE PTT  (32-bit IDs)                                  │  │
│  │  Objects visible to this card — cross-stack Ponds,        │  │
│  │  bridges, shared resources, sessions                      │  │
│  │  Managed by: ShoreKeeper                                  │  │
│  │  Lookup: on-card, microseconds                            │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  LOCAL PTT  (32-bit IDs)                            │  │  │
│  │  │  Objects owned by this stack — cells, local Ponds,  │  │  │
│  │  │  programs, tiles, local bridges                     │  │  │
│  │  │  Managed by: local Ward / die ShoreKeeper           │  │  │
│  │  │  Lookup: on-die SRAM, nanoseconds                   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Object types at each level

| Object | Level | Contains |
|--------|-------|----------|
| Cell | Local | Registers (gate_state, addresses, data, flag) |
| Tile instance | Local | Cell objects × N |
| Program | Local | Tile instances + named ranges |
| Local Pond | Local | Cell objects + bridge objects |
| Bridge | Shore | Pond reference + routing entry |
| Session | Shore | Local Pond references + mask |
| File | Shore | Cell address range (content) |
| Display | Shore | Cell address range (pixel map) |
| Remote card | Extended | Shore PTT reference |
| Global service | Extended | Cross-card bridge chain |

### Bridge as navigator

The bridge does not need to know the physical address of the
destination — it holds a 32-bit object reference at the appropriate
scope level. Navigation is:

```
Request for object X:
  1. Check Local PTT     — found? return immediately  (nanoseconds)
  2. Miss → Shore PTT    — found? route via card bus   (microseconds)
  3. Miss → Extended PTT — found? route cross-card     (milliseconds)
  4. Miss → object does not exist in accessible scope

Each hop is one 32-bit lookup + one mask check.
The caller never knows which level answered.
```

### Object containment hierarchy

```
Extended Object
  └── Card Object (Shore PTT)
        └── Stack Object (Shore PTT)
              └── Pond Object (Local PTT)
                    ├── Bridge Object    (Local PTT)
                    ├── Cell Object × N  (Local PTT)
                    └── Program Object   (Local PTT)
                          └── Tile × M   (Local PTT)
```

A Pond has a 32-bit local ID. It contains thousands of cells.
You reference the Pond. The Pond knows where its cells are.
The 12-layer card's 30.24B cells are never directly addressed —
they live inside objects that are directly addressed.

### PTT entry counts at 12-layer scale

```
32-bit address space:    4,294,967,296 IDs available per level
Stacks per card:         112
IDs per stack (local):   38,347,922  (~38.3M local object IDs)

At 36 bytes per PTT entry:
  1%  allocated:   383K entries,  14 MB  — comfortably on-die
  10% allocated:  3.8M entries,  138 MB  — manageable
  Full range:     38.3M entries, 1.38 GB — needs two-level cache

Hot PTT (on-die SRAM, 20% of ShoreKeeper die at 3nm):
  ~1.7M entries — active objects, fast nanosecond lookup

Cold PTT (off-die storage):
  Remaining entries — inactive objects, paged in on demand
  Eviction: Ward IDLE state → candidate for cold PTT
  Same principle as CPU L1/L2 cache

Effective simultaneous active objects per card:
  1.7M hot entries × 112 stacks = 190M concurrent active objects
```

### Security maps directly to scope

```
process_mask bits  0-7:   tenant  — LOCAL PTT scope membership
process_mask bits  8-15:  role    — SHORE PTT visibility
process_mask bits 16-23:  feature — EXTENDED PTT reachability
process_mask bits 24-31:  reserved

At each level: (process_mask & object_mask) != 0
  → object visible in this scope

Invisible at any level = nonexistent at that level.
A process cannot discover an object it lacks mask bits for —
at any of the three scopes.
```

### Cast/Ripple as object traversal

```
Cast a Stone →
  Search Local PTT   (same stack — nanoseconds)    nearest first
  Miss →
  Search Shore PTT   (same card — microseconds)
  Miss →
  Search Extended PTT (cross-card — milliseconds)  furthest last

Return first match at nearest scope.
The Stone never needs a physical address —
it navigates by object ID and mask at each level.
```

### The filesystem parallel

```
Unix:   inode → directory → mount point    (everything is a file)
Imago:  cell  → pond      → card           (everything is an object)

A directory IS a file that contains file references.
A Pond IS an object that contains object references.
The bridge IS the directory entry — it points to the next object.
```

---

## Three-Bus Command Reference

| Command | Code | Privilege | Description |
|---------|------|-----------|-------------|
| DATA_WRITE | 0 | User+System | Write value to cell data latch |
| SET_INPUT_ADDR | 1 | User+System | Set cell input address register |
| SET_OUTPUT_ADDR | 2 | User+System | Set cell output address register |
| RECONFIGURE | 3 | **System only** | Reconfigure cell — requires 12-bit auth token in Bus 1 bits 4-14 |
| FREEZE | 4 | **System only** | Clear start_flag (disarm cell) |
| RELEASE | 5 | **System only** | Set start_flag (arm cell) |
| COPY_DATA_TO_OUT | 6 | User+System | Copy data latch to output address register |
| COPY_DATA_TO_IN | 7 | User+System | Copy data latch to input address register |
| PING | 8 | Anyone | Return cell address if alive, None if dead/absent |

**Bus 1 layout:**
```
bits  0-3:   command code
bits  4-14:  auth token (11 bits — carries the 12-bit card token)
bit  15:     address mode (0=PTT-relative, 1=raw system address)
bits 16-31:  reserved flags
```

---

## User Tile File Format

```python
# LIBRARY MODEL                    ← required marker (first 10 lines)
# User: your_name                  ← optional author tag
# Description: what it does        ← optional description

from fp_tiles import TileAddressAllocator, NORBuilder, Tile, TileMetadata
# from gate_states import ...  also permitted
# from controller import CellMapRecord  also permitted
# NO other imports permitted — checked via AST before any code runs

def make_your_tile_name(base_address=0x10000):
    """Every make_* function is auto-discovered and registered."""
    alloc = TileAddressAllocator(base_address)
    b     = NORBuilder(alloc)
    # ... build using b.NOT(), b.AND2(), b.OR2(), b.XOR2() etc ...
    return Tile(
        records  = b.records,
        in_a     = [...],     # input bit addresses
        in_b     = [...],     # second operand (or [])
        out      = [...],     # output bit addresses
        metadata = TileMetadata(
            operation      = "YOUR_TILE_NAME",   # name used in compiler
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes          = "Description.",
        )
    )
```

Place in `~/.claudette/user_tiles/`. Available immediately after `user_lib.scan()`.
User tiles override core tiles with the same operation name.


---

# PART 5 — SILICON HARDWARE REFERENCE

## MIDAS Chip — Design Baseline

The MIDAS (Modular Imago Die Architecture System) chip is the physical
silicon implementation of the Imago UniCell architecture. The design
is based on the MIDAS diagrams produced during development:

```
Process node:       3nm (TSMC N3 class — ~300M transistors/mm²)
Die footprint:      10mm × 10mm  (1cm square)
Transistors/cell:   1,000  (allows full 5-register cell with ECC and
                            auth mask, mode flags, and NOR topology)
Die utilisation:    75%  (25% reserved for routing, power grid, I/O ring,
                          edge keep-out zones)
```

### Single-layer die cell count

```
Transistor density:   300,000,000 / mm²
Transistors per cell:       1,000
Cells per mm²:            300,000
Usable die area:          75 mm²  (75% of 100 mm²)
──────────────────────────────────────────────────
Cells per die (1 layer):  22,500,000  (22.5M)
65k blocks per die:              343
```

Note: the MIDAS development diagrams referenced 115,000 blocks per die.
That figure assumed approximately 36 transistors per cell (minimum NOR
gate count) rather than 1,000. At 1,000 transistors per cell the correct
figure is 343 blocks per die for a single-layer die. The 115,000 figure
remains a valid long-term target at a future sub-1nm node or with a
minimum-transistor cell design.

---

## MIDAS Chip Package — Ball Grid Array (BGA)

### Package choice: BGA

The MIDAS die is packaged as a **Ball Grid Array (BGA)**. BGA is the
correct choice for this application for several reasons:

The command bus is 3 × 64 bits = 192 signal lines. Add clock, freeze,
power, and ground and the total pin count exceeds anything a QFP or
LGA package can handle cleanly in a 1cm² footprint. BGA distributes
the balls across the entire underside of the package — a 1cm² die
with 0.5mm ball pitch on a 10×10 grid gives 100 balls in the
footprint alone, and a 1.2cm² package body with 0.4mm pitch gives
up to ~900 balls — well above what the bus requires.

BGA also suits the PCIe card layout directly: the 10mm × 10mm die
positions each have a 10mm gap on all sides. The BGA package sits
flush on the PCB. The cooling block sits directly on top of the
package lid. No leads, no pins to bend, no clearance issues.

### Minimum pin allocation

```
Command Bus:
  Bus 1 (Command + Control):  64 signal lines
  Bus 2 (Data Payload):       64 signal lines
  Bus 3 (Target Address):     64 signal lines
  ─────────────────────────────────────────────
  Command bus total:         192 signal lines

Control signals:
  CLK       (1)  — system clock (differential pair = 2 pins)
  CLK_N     (1)  — differential clock complement
  FREEZE    (1)  — global halt signal (hardware freeze, auth-protected)
  RESET_N   (1)  — active-low reset

Power and ground:
  VDD       (minimum 8) — core power (multiple for current distribution)
  VDDIO     (minimum 4) — I/O power (command bus buffers)
  VSS       (minimum 12)— ground (distributed for return current)

BIOS-Plus interface:
  BIOS_CLK  (1)  — BIOS chip clock
  BIOS_DATA (1)  — BIOS chip serial data (auth token + salt key delivery)
  BIOS_CS_N (1)  — BIOS chip select

Thermal:
  THERM_OUT (1)  — thermal alert (open-drain, wired-OR across stack)
  THERM_ID  (2)  — 2-bit zone ID (which of 4 row zones this die is in)

─────────────────────────────────────────────────────────────────
Minimum signal pins:          192 + 4 + 3 + 3  = 202 signal pins
Power/ground pins:             8  + 4 + 12      =  24 power pins
─────────────────────────────────────────────────────────────────
Minimum total ball count:     226 balls
```

### Recommended BGA specification

```
Package body:      12mm × 12mm  (2mm clearance around 10mm die)
Ball pitch:         0.8mm
Ball grid:         14 × 14 = 196 balls minimum
                   (depopulate corners for fiducial marks)
Practical layout:  15 × 15 = 225 balls — covers all signals with
                   spare capacity for decoupling and future expansion

Ball diameter:     0.45mm (standard 0.8mm pitch ball)
Package height:    ~1.2mm above PCB (within the 10mm cooling gap)
Thermal interface: exposed die paddle on lid for direct cooler contact

Inter-die routing: BGA balls on underside connect to PCB trace layer
                   Signal traces run in the 10mm gap between die positions
                   Command bus traces are wider (64-bit) than data bus
                   traces (32-bit) — physically separate on PCB layers
```

### Bus-to-BGA ball assignment (recommended grouping)

```
Ball region        Signals                     Count
─────────────────────────────────────────────────────
Top rows (1-3):    Bus 1 bits 0-63             64
Middle-top (4-6):  Bus 2 bits 0-63             64
Middle-bot (7-9):  Bus 3 bits 0-63             64
Bottom rows (10-12): CLK/CLK_N, FREEZE,        26
                   RESET_N, BIOS interface,
                   THERM signals
Distributed:       VDD, VDDIO, VSS             24
─────────────────────────────────────────────────────
Total:             242 balls  (15×15 grid,
                               spare balls for decoupling)
```

### Data path isolation on PCB

The BGA ball assignment deliberately separates command bus balls (top
of package) from control and power balls (bottom). On the PCB the
command bus traces are routed on dedicated inner layers — they never
share a layer with power planes or data-adjacent signals. The critical
safety constraint from the architecture is maintained at the PCB level:

```
Layer 1 (top copper):  Die pad, thermal interface
Layer 2:               Bus 1 signal traces (command + control)
Layer 3:               Bus 2 signal traces (data payload)
Layer 4:               Bus 3 signal traces (target address)
Layer 5:               Ground plane
Layer 6:               Power planes (VDD, VDDIO)
Layer 7:               Ground plane
Layer 8 (bottom):      PCIe edge connector traces, inter-die routing
```

Bus 2 (data) and Bus 3 (address) are on separate PCB layers.
There is no connection between them at the PCB level.
The scope decoder in the command bus is the only point where
the two paths interact — and only to select which register to write.

---

## PCIe Card Layout

### Physical dimensions

Standard full-height, full-length PCIe card:

```
Card dimensions:    312mm × 111mm
Usable area:        280mm × 90mm
  (after edge connector, bracket, keep-out zones)

Die footprint:      10mm × 10mm
Gap between dies:   10mm  (generous — see cooling section)
Pitch:              20mm  (die + gap)

Dies across:        280mm ÷ 20mm = 14
Dies high:           90mm ÷ 20mm =  4  (10mm margin at top = heatsink rail)
Dies per side:      14 × 4 = 56
```

### Card layout diagram

```
  ┌─ 280mm usable ──────────────────────────────────────────────────────┐
  │  ← 20mm →                                                           │ ↑
  │  [die][ gap ][die][ gap ][die][ gap ][die][ gap ]...×14             │ 10mm margin
  │  [ gap between rows ]                                               │ (heatsink rail)
  │  [die][ gap ][die][ gap ][die][ gap ][die][ gap ]...×14             │
  │  [ gap between rows ]                                               │ 90mm usable
  │  [die][ gap ][die][ gap ][die][ gap ][die][ gap ]...×14             │
  │  [ gap between rows ]                                               │
  │  [die][ gap ][die][ gap ][die][ gap ][die][ gap ]...×14             │ ↓
  ├─────────────────────────────────────────────────────────────────────┤
  │  PCIe edge connector                                                │
  └─────────────────────────────────────────────────────────────────────┘
     14 columns × 4 rows = 56 die positions per face
```

---

## 3D Die Stacking

The 10mm gap between die positions exists primarily to accommodate
3D-stacked die groups and their cooling infrastructure. Each die
position holds a vertical stack of 1 to 12 identical dies connected
by Through-Silicon Vias (TSVs).

### Stack geometry

```
Each die layer:     50 μm thick  (thinned wafer)
Bonding layer:      10 μm  (TSV bonding and underfill)
Layer pitch:        60 μm per layer

Stack heights:
  1 layer:    0.06mm
  4 layers:   0.24mm
  8 layers:   0.48mm
  12 layers:  0.72mm

Available gap:      10mm
Unused after 12L:   9.28mm  → cooling headroom
```

### Cell count scaling table

| Layers | Cells/die | Blocks/die | Cells/side (56) | Cells/card (×2) | Sim VRAM † | vs Brain |
|--------|-----------|------------|-----------------|-----------------|------------|----------|
| 1  | 22.5M | 343 | 1.26B | 2.52B | 43 GB | 0.03× |
| 2  | 45.0M | 686 | 2.52B | 5.04B | 86 GB | 0.06× |
| 3  | 67.5M | 1,029 | 3.78B | 7.56B | 128 GB | 0.09× |
| 4  | 90.0M | 1,372 | 5.04B | 10.08B | 171 GB | 0.12× |
| 5  | 112.5M | 1,716 | 6.30B | 12.60B | 214 GB | 0.15× |
| 6  | 135.0M | 2,059 | 7.56B | 15.12B | 257 GB | 0.18× |
| 7  | 157.5M | 2,402 | 8.82B | 17.64B | 300 GB | 0.21× |
| **8** | **180.0M** | **2,746** | **10.08B** | **20.16B** | **343 GB** | **0.23×** |
| 9  | 202.5M | 3,089 | 11.34B | 22.68B | 385 GB | 0.26× |
| 10 | 225.0M | 3,432 | 12.60B | 25.20B | 428 GB | 0.29× |
| 11 | 247.5M | 3,775 | 13.86B | 27.72B | 471 GB | 0.32× |
| **12** | **270.0M** | **4,119** | **15.12B** | **30.24B** | **514 GB** | **0.35×** |

† **Sim VRAM is the software simulation cost only — not a hardware requirement.**
The cell array is self-contained silicon: each cell's registers live in the
transistors themselves. The real card needs only megabytes of external storage
(VM image flash, BIOS-Plus chip). The Sim VRAM figure is how much GPU memory
the `GPUArrayBackend` numpy simulation would require to model this card in software.

**Bold rows are primary targets.** 8 layers is the practical engineering
target — mature 3D stacking, manageable thermal load. 12 layers is the
ambitious target — requires the full cooling jacket described below.

**The Pebble tier crossover:**
At 12 layers, one PCIe card holds 30.24 billion cells — exceeding the
24 billion cell Pebble tier target with 6.24 billion cells to spare.
The Pebble tier was the original architecture goal. One card gets there.

---

## Thermal Management — Double-Sided Water Cooling Jacket

### Why water cooling is mandatory

At 8–12 layers each die position is a 3D stack of up to 12 active silicon
layers in a 10mm × 10mm footprint. Heat has nowhere to go vertically —
it must be extracted laterally through the gap between die groups.

```
Estimated thermal load:
  Single layer die:   ~1-2W per die  (at moderate utilisation)
  8-layer stack:      ~8-16W per position
  12-layer stack:     ~12-24W per position
  56 positions/side:  672W–1,344W per side
  Both sides:         1,344W–2,688W total

Standard GPU TDP:     300–600W
This card at 12L:     ~1,500W typical operating — air cooling impossible
```

### Cooling gap utilisation

The 10mm gap between die positions — which appears wasteful at first —
is the thermal infrastructure. At 12 layers the stack is only 0.72mm
tall, leaving 9.28mm:

```
Gap cross-section (10mm available, 0.72mm used by stack):

  ┌─────────────── 10mm gap ───────────────┐
  │ [die stack 0.72mm] │ 9.28mm available  │
  │                    ├───────────────────┤
  │                    │ 2.5mm microchannel │ ← liquid cooling
  │                    │ copper block       │
  │                    ├───────────────────┤
  │                    │ 1.0mm vapour       │ ← heat spreading
  │                    │ chamber layer      │
  │                    ├───────────────────┤
  │                    │ 0.2mm TIM          │ ← thermal interface
  │                    ├───────────────────┤
  │                    │ 1.5mm PCB routing  │ ← inter-die bus traces
  │                    ├───────────────────┤
  │                    │ 4.08mm spare       │ ← future headroom
  └────────────────────────────────────────┘
```

### Double-sided water cooling jacket design

Because the card has active die stacks on **both faces**, a standard
single-sided cooler is insufficient. The card requires a water cooling
jacket that clamps both faces simultaneously:

```
         WATER IN ──────────────────────────────── WATER OUT
                                │                │
    ┌───────────────────────────┼────────────────┼──────────────┐
    │  TOP COOLING PLATE        │                │              │
    │  (aluminium/copper)       │                │              │
    │  microchannel array  ─────┘                └─────         │
    ├──────────────────────────────────────────────────────────┤
    │  FACE A  [die][gap][die][gap][die]...×56 positions        │
    ├──────────────────────────────────────────────────────────┤
    │  PCB substrate  (signal layers, power planes)             │
    ├──────────────────────────────────────────────────────────┤
    │  FACE B  [die][gap][die][gap][die]...×56 positions        │
    ├──────────────────────────────────────────────────────────┤
    │  BOTTOM COOLING PLATE                                     │
    │  (aluminium/copper)       ┐                ┌─────         │
    │  microchannel array  ─────┘                └─────         │
    └──────────────────────────────────────────────────────────┘
         WATER IN ──────────────────────────────── WATER OUT
```

Each face has its own independent cooling loop. This allows:
- **Thermal balancing:** if Face A is running hotter, its loop flow rate
  increases independently of Face B
- **Failure isolation:** one loop failing does not immediately kill the card
- **Maintenance:** loops can be purged independently

### Microchannel routing

The microchannels run parallel to the 14-column direction (long axis).
Each channel serves one row of 14 die positions:

```
     ← 280mm →
  ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐  ← Row 1 channel
  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │
  ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  ← Row 2 channel
  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │
  ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  ← Row 3 channel
  │  │  │  │  │  │  │  │  │  │  │  │  │  │  │
  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘  ← Row 4 channel

  4 channels per face × 2 faces = 8 independent thermal zones
  Each zone maps to one ShoreKeeper thermal zone (row_0 through row_3)
```

The 4 row channels map naturally to the 4-row die layout. Each ShoreKeeper
thermal zone corresponds to one physical cooling channel — when Ward reports
a thermal zone as THROTTLE or MIGRATE, the cooling system knows exactly
which channel to increase flow on.

### ShoreKeeper thermal hierarchy maps to physical layout

```
Physical layer:         Monitoring layer:
  Die (one stack)    →    Ward (per Pond)
  Column of 14 dies  →    (bus segment)
  Row of 14 dies     →    Zone ShoreKeeper (4 per face, maps to cooling channel)
  Full face (56 dies)→    ShoreKeeper (one per face)
  Both faces         →    HyperShore (one per card)
  Multi-card system  →    HyperCompanion
```

The thermal data path mirrors the cooling infrastructure:
Ward → Zone ShoreKeeper → cooling flow controller (same channel)
without routing through HyperShore unless cross-zone migration is needed.

---

## Display System Integration

### Peripheral device address map

```
Base address    Device          Bridge class      Status
──────────────────────────────────────────────────────────
0x00C00000      Keyboard        KeyboardBridge    implemented
0x00C10000      Mouse           MouseBridge       implemented
0x00C20000      Audio output    AudioBridge       stub
0x00C30000      Video capture   VideoBridge       stub
0x00D00000      Storage         StorageBridge     implemented
0x00E00000      Network         NetworkBridge     implemented
0x00F00000      Display (start) DisplayPond       implemented
```

Mouse events arrive as 32-bit packed words at `OUT_ADDR = base + 0x40`:
```
bits 31-24:  event type  (0=move, 1=btn_down, 2=btn_up, 3=wheel)
bits 23-16:  button mask / wheel delta
bits 15-8:   X delta (move) or position high byte (button)
bits  7-0:   Y delta (move) or position high byte (button)
```
Full position readable via `MS_CMD_GET_X` (0x22) / `MS_CMD_GET_Y` (0x23).

Audio and video are stub-only. On real silicon: USB audio/video devices
appear as PERIPHERAL Ponds. The tile library has `AUDIO_IN_HANDLER`,
`AUDIO_OUT_HANDLER`, and `DISPLAY_HANDLER` stubs ready for them.

---

### Host window via pygame

The `DisplayPond` class opens a native host OS window via pygame/SDL2.
On a desktop the window has a title bar, close button, and is resizable.
In a container environment it runs headless (SDL_VIDEODRIVER=offscreen).
On real silicon the pygame backend is replaced by a display controller
driver — the DisplayPond and delta update code are identical.

```python
from display_pond import DisplayPond, DisplayConfig, PixelFormat
from unicell_array import UniCellArray

arr = UniCellArray(cell_count=100_000)
cfg = DisplayConfig(
    width        = 320,
    height       = 200,
    pixel_format = PixelFormat.RGB24,
    base_address = 0x00F00000,
    title        = "Claudette v1.1",
    scale        = 3)      # 3× upscale → 960×600 window on desktop

dp = DisplayPond("main_display", arr, "system", cfg)

with dp:
    while dp.is_open:
        # Normal cell computation writes to display addresses
        dp.tick()          # only fired cells update pixels
```

### Pixel formats and cell budget

| Format | Cells/pixel | 320×200 | 1080p | 4K | 8K |
|--------|-------------|---------|-------|-----|-----|
| MONO1 | 1 | 64K | 2.1M | 8.3M | 33.2M |
| GREY8 | 1 | 64K | 2.1M | 8.3M | 33.2M |
| IDX8 (palette) | 1 | 64K | 2.1M | 8.3M | 33.2M |
| RGB16 | 2 | 128K | 4.1M | 16.6M | 66.4M |
| RGB24 | 3 | 192K | 6.2M | 24.9M | 99.5M |
| RGBA32 | 4 | 256K | 8.3M | 33.2M | 132.7M |

### Display budget on silicon

At 12-layer stack (30.24B cells per card):
*(Cell counts only — the silicon card requires no external VRAM.)*

```
One 4K RGBA32 display:   33.2M cells =  0.11% of card
One 8K GREY8  display:   33.2M cells =  0.11% of card
One 8K RGBA32 display:  132.7M cells =  0.44% of card

Simultaneous 4K RGBA32:  911 displays before using 100% of card
  (in practice you would allocate far less than 100% to display)
```

### Delta rendering — only changed cells update

The DisplayPond intersects the array's fired-cell set with the display
address range each frame. Only cells that wrote a new value to the bus
since the last frame update their pixel:

```
Typical frame (5-10% of pixels changing):
  Full 4K RGBA32:  33M cells total
  Changed cells:   ~330K–660K per frame
  Update cost:     O(changed) not O(total)

At 60fps:
  16.67ms per frame
  GPU can run thousands of ticks in that window
  Display update is a set intersection — essentially free
```

### The Apollo Guidance Computer demo

The `apollo_guidance.py` simulation outputs to both terminal and display
simultaneously. No rewrite needed — the terminal ASCII DSKY is unchanged.
Pass a `DisplayPond` to `run_simulation()` and the pixel DSKY opens
alongside:

```python
from apollo_guidance import run_simulation
from display_pond import DisplayPond, DisplayConfig, PixelFormat
from unicell_array import UniCellArray

arr = UniCellArray(cell_count=100)
arr.enforce_emission_limits = False
cfg = DisplayConfig(
    width=320, height=200,
    pixel_format=PixelFormat.RGB24,
    base_address=0x00F00000,
    title="AGC DSKY — Apollo 11",
    scale=3)                    # 960×600 window

dp = DisplayPond("dsky", arr, "system", cfg)

run_simulation(
    use_array    = True,        # NOR-gate array arithmetic
    speed        = 1.0,         # real-time (2s per guidance cycle)
    display_pond = dp)          # pixel display alongside terminal
```

The DSKY renders: amber register rows with value bars, throttle and fuel
bars, a vertical trajectory visualiser, and alarm state — all driven by
the same NOR-gate arithmetic computing the actual guidance solution.
Each guidance cycle updates only the pixels that changed.

---

## Realistic Cell Counts vs MIDAS Diagram

| Source | Blocks/die | Cells/die | Basis |
|--------|-----------|-----------|-------|
| MIDAS diagram | 115,000 | 7.54B | ~36T/cell (minimum NOR count) |
| Calculated (3nm, 1000T/cell) | 343 | 22.5M | Realistic cell complexity |
| Future target (sub-1nm) | ~115,000 | 7.54B | MIDAS figure becomes achievable |

The MIDAS figure is not wrong — it is a future target. At 1,000 transistors
per cell the minimum transistor count (~36) gives about 28× more cells per
die than the 1,000T figure. The 115,000 block figure corresponds to a
minimum-transistor cell design at 3nm, which trades cell richness (no ECC,
no auth mask, no mode flags) for raw cell count. The production MIDAS cell
at 1,000 transistors is the correct target for Claudette v1.1 with full
security and mode flag support.

