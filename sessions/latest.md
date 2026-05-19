# Session 2026-05-17

## Summary

A session of foundational corrections. Three independent bugs found and fixed,
all at the Verilog/VM level. The architecture is now on solid ground.

---

## Work completed

### 1. Composer CSS fix
Missing CSS definitions from the ports tab (added in commit 207190f but CSS
never written). Ports panel was invisible — buttons unstyled, IN/OUT badges
missing, port rows unformatted.
Fixed: `--muted`, `.fb`, `.fb:hover`, `.port-row`, `.port-badge`, `.port-badge.in/.out`
Commit: `c176041`

### 2. FPGA Verilog cleanup
Retired all v1.2 Verilog variants:
- `unicell-edge/fpga/` — entire directory (Claudette v1.2, LOAD_PATTERN)
- `unicell-latch/fpga/` — entire directory (Claudette v1.2, LOAD_PATTERN)
- Root stale tops: basys3, icestick, orangecrab, tinyfpga_bx, ulx3s (v1.1)
- `top_debug.v`, `uart_hello.v`, `unicell_array_stub.v` — bring-up one-shots, done
- `apply_fpga_v1.2.bat` — v1.2 patcher, retired

Canonical build confirmed:
```
yosys -p "synth_ice40 -top top -json top_icebreaker.json" \
  verilog/top_icebreaker.v verilog/unicell_array.v \
  verilog/unicell.v verilog/uart_bridge.v
```
Commit: `aac0cc1`

### 3. Python vs Verilog full audit
44 Python files carrying stale references to retired architecture:
- `input_b_address` / `receive_b()` — 24 files
- `FUNCTION_LOAD_PATTERN` config protocol — 8 files
- `GS_SELECT` / SELECT cells — 6 files
- Old bit positions throughout `gate_states.py`
- CMD codes wrong in `command_interface.py`, `fpga_bridge.py`, `icm_loader.py`

Full audit saved: `sessions/2026-05-17-python-audit.md`
Commits: `ccf9054`, `b3a2c6f`

### 4. Python migration — layers 1-3 (PARTIAL, halted at gate tree discovery)
- `gate_states.py` — complete rewrite, all bit positions corrected
- `unicell.py` — rewrite to two-arrival model, configure() replaces LOAD_PATTERN
- `unicell_array.py` — B-input phase removed, configure_cell() added

**Migration halted** when gate tree bug discovered (see below).

### 5. CRITICAL: gate tree was 1-bit, not 32-bit

**The bug:** `unicell.v` gate tree operated on `bus_data[0]` / `a_data[0]` only.
Output was `{31'h0, computed_output}` — one bit zero-padded.

**Why it wasn't caught:** The VM was written to model the intended 32-bit
architecture. The Verilog was wrong. They were silently modelling different things.
All existing silicon tests (test_ring_2.py, test_ring_22.py) used only 1-bit
values (data=0 or data=1) so the bug was invisible.

**The fix:** Widen gate tree to `wire [31:0]`. Introduce `second_val [31:0]`
for B input. `computed_output` becomes `reg [31:0]`. Output assignments
changed from `{31'h0, computed_output}` to `computed_output` throughout.

**Secondary bugs found during testing:**
1. Gate tree wiring was wrong for OR/XOR/XNOR/NOR/NAND — previous tree
   was not a valid NOR-only implementation. Derived correct tree algebraically:
   ```
   g0 = NOR(A,A)   = NOT(A)
   g1 = NOR(B,B)   = NOT(B)
   g2 = NOR(g0,g1) = AND(A,B)
   g3 = NOR(g2,g2) = NAND(A,B)
   g4 = NOR(A,B)   = NOR(A,B)
   g5 = NOR(g4,g4) = OR(A,B)
   g6 = NOR(A,g4)
   g7 = NOR(B,g4)
   g8 = NOR(g6,g7) = XNOR(A,B)
   g9 = NOR(g8,g8) = XOR(A,B)
   ```
2. Topology case statement was one-hot only — OR/XOR/XNOR are multi-bit
   topology values and fell through to PASS(A). Replaced with if-else chain.
3. `loop_back`: was updating `data_reg` but not `a_data`. `input_val` uses
   `a_data` when `bus_hit && a_arrived`, so fed-back value was invisible.
   Fix: `a_data <= computed_output` on fire when `loop_back=1`.
4. `latch_in` overwrite: first tx of send_twice fires immediately with stale
   `a_data`. Fix: `a_data <= bus_data` on latch_in fire. Test updated to
   read last event not first.

**Confirmed on silicon:** 15/15 tests passing in `test_32bit_gate.py`.
Commits: `532b8fe`, `335bbea`, `55df45d`, `c13324c`

### 6. Address width clarification
VM keeps full 32-bit addresses throughout. iCEBreaker Verilog narrows to
16-bit for timing only (iCE40 4-input LUTs can't close timing at 24 MHz
with 32-bit address comparison at 8 cells). This is a hardware constraint,
not an architectural one. Kintex-7 uses 6-input LUTs — full 32-bit from day 1.
ICM format will carry `address_width` field (16 or 32). VM ignores it.

---

## iCEBreaker sizing — current numbers

| Parameter | Value | Notes |
|---|---|---|
| Clock | 12 MHz | Reduced from 24 MHz for 32-bit gate tree timing |
| Max achievable | 20.26 MHz | Routing bottleneck (9.45 ns), logic only 2.26 ns |
| Cells fitted | 4 | At 79% LC utilisation (4220/5280) |
| LC per cell | ~880 | (4220 - ~700 fixed) / 4 ≈ 880 per cell |
| Timing margin | 8 MHz | 20.26 MHz max vs 12 MHz target |

**Cell count ceiling on iCEBreaker:**
- Fixed overhead (UART bridge, top, array controller): ~700 LCs
- Remaining: 5280 - 700 = 4580 LCs available for cells
- Per cell: ~880 LCs
- Theoretical max: 4580 / 880 ≈ **5 cells**
- Practical max: **4 cells** (routing congestion degrades before LC limit)

**Why only 4 cells:** The 32-bit gate tree is wide parallel logic. iCE40
4-input LUTs require long carry chains for 32-bit operations. Routing
congestion hits before the LC count ceiling. At 6 cells: 108% utilisation.
At 4 cells: 79% utilisation, timing closes comfortably.

**This is a validation platform, not a production target.** The iCEBreaker
proves the architecture works. Kintex-7 has 6-input LUTs, dedicated carry
chains, and far more routing resources — expect 50-100 cells easily.

---

## Key architectural finding: 32-bit comparator in one cell

XNOR(A,B) across 32 bits in a single cell:
- A == B → output = 0xFFFFFFFF
- A != B → output = bitmask of agreeing bits (0 where bits differ)
- A == B exactly → single XNOR cell sufficient

XOR(A,B) for inequality: non-zero result = bits that differ.

Confirmed on silicon: `XNOR(0xDEADBEEF, 0xDEADBEEF) = 0xFFFFFFFF` ✓

**Ordered comparison (>, <) still needs multi-cell.** A single NOR cell
cannot determine magnitude — only equality/inequality. The INT32 comparison
tiles in `fp_tiles.py` (subtract + sign bit check) remain necessary for
ordered comparisons.

---

## Silicon test files

Two real-silicon test files committed from session exploration:
- `fpga/test_ring_2.py` — ring oscillator, one_shot observer, edge-mode chain
- `fpga/test_ring_22.py` — 8-cell stateful sequence lock, streaming pipeline

These were written against the 1-bit silicon and still work because they
use only data=0/1. They demonstrate edge_mode, latch_in, one_shot, and
multi-cell cascades. Worth revisiting with 32-bit word payloads now that
the gate tree is correct.

Validation test:
- `fpga/test_32bit_gate.py` — 15/15 passing on silicon

---

## What was NOT completed (continue next session)

Python migration halted at layer 3. Remaining in order:
```
4.  command_interface.py  — CMD code remap, remove SCOPE_EXTENDED
5.  controller.py         — remove input_b_address, storage_mode
6.  program_image.py      — ICM format: remove inB/alt/stor, add address_width
7.  ir.py                 — remove GS_SYNC_WAIT, input_b_address from emissions
8.  fp_tiles.py           — NORBuilder cleanup, remove B-input parameter
9.  compiler.py           — remove SELECT/LOOP_MODE/storage_mode patterns
10. compiler_int32.py     — remove input_b_address from tile placements
11. branch.py             — BLOCKED: needs branch design decision (SELECT retired)
12. fpga/fpga_bridge.py   — CMD code update
13. fpga/icm_loader.py    — CMD code update, remove inB, add address_width
14. All tests             — audit and fix
```

Branch design decision still needed before branch.py can be updated.
Options: two-cell branch, PTT-based, or 1-bit MUX tile.

---

## Errors made this session (record for reference)

1. **Stated gate tree was 1-bit** early in session — correct observation but
   should have been flagged as a critical architectural issue immediately
   rather than noted in passing. Caught later during testing.

2. **Initial Python gate tree fix** used `av = a & 1` / `bv = b & 1` —
   carried the 1-bit assumption into the VM. Corrected after silicon validation.

3. **gate tree wiring** in Verilog — first attempt had wrong connections for
   OR/XOR/XNOR. Required algebraic derivation to get correct NOR-only tree.

4. **Topology case statement** — initially one-hot, missed that OR/XOR/XNOR
   are multi-bit topology values. Fell through to PASS(A) silently.

5. **loop_back target** — updated `data_reg` instead of `a_data`. `input_val`
   uses `a_data` on bus_hit, so fed-back value was never seen.

6. **latch_in overwrite test** — read first event instead of last. latch_in
   fires twice on overwrite: once with stale a_data, once with new value.

---

## Architectural pattern: preloaded a_data

Discovered during test_ring_22.py exploration. The two-arrival latch in each
cell can act as an implicit register — a_data persists between the preload
and the comparison, and survives CMD_RECONFIGURE (topology can change without
losing the stored value).

### Patterns

**Preloaded comparator (single cell)**
```
send_twice(addr, secret)    # preload: stores secret in a_data
# ... time passes, cell stays armed ...
send_twice(addr, attempt)   # XNOR(secret, attempt) fires
# output = 0xFFFFFFFF on exact match, bitmask of agreeing bits otherwise
```
Previously required a multi-cell chain. Now one XNOR cell.

**Preloaded mask**
```
send_twice(addr, mask)      # preload: store bitmask in a_data
send_twice(addr, word)      # AND(mask, word) fires — isolates fields
```
Extracts bit fields from packed words without a tile. One AND cell.

**Preloaded threshold / change detector**
```
send_twice(addr, baseline)  # preload: store reference state
send_twice(addr, current)   # XOR(baseline, current) fires
# output = bitmask of bits that changed
```
Sensor/register change detection in one XOR cell.

**Sequence lock (refined)**
The test_ring_22 sequence lock used NOT+edge chains (3-4 cells per key bit).
With XNOR preload: one cell per key position. Preload each cell with its
expected value, then send the attempt — all cells fire simultaneously,
outputs can be AND-reduced to a single unlock signal.

### Key property
`a_data` survives CMD_RECONFIGURE. Topology can be changed (e.g. XNOR → AND)
without losing the preloaded reference value. The stored value only clears
if a new first arrival is delivered or the cell is reset (rst=1).

This means a cell can be repurposed mid-program while retaining its data —
useful for compiler optimisations where the same cell serves multiple roles
in sequence.

### Compiler implication
The INT32 comparison tiles in fp_tiles.py (subtract + sign bit) are still
needed for ordered comparison (>, <, >=, <=). But equality (==, !=) can now
be a single XNOR/XOR cell with a preloaded reference. The compiler should
emit preloaded XNOR for equality checks rather than the full subtract tile.
Flag for when compiler work resumes.

---

## Python migration — layers completed this session

```
1.  gate_states.py       ✅  commit dc8f8d6
2.  unicell.py           ✅  commit 357d024 / c13324c (gate tree fix)
3.  unicell_array.py     ✅  commit a2e56e0
4.  command_interface.py ✅  commit 5d8efb6
5.  controller.py        ✅  commit ca86b64
6.  program_image.py     ✅  commit bf47ebe
7.  ir.py                ✅  commit 811f494
8.  fp_tiles.py          ✅  commit 9eede17
9.  compiler.py          ✅  commit 2e2ec47 (while loop blocked, marked)
10. fpga/fpga_bridge.py  ✅  commit c435c55
11. fpga/icm_loader.py   ✅  commit c435c55
```

## Remaining for next session

```
12. branch.py            BLOCKED — branch design decision needed
                         Options: two-cell branch, PTT, 1-bit MUX tile
13. compiler_int32.py    — remove input_b_address from tile placements
14. All tests            — audit and fix (many reference retired features)
    - test_select.py     retire
    - test_addr_latch.py retire
    - test_while.py      blocked on branch
    - test_branch.py     blocked on branch
    - test_gate_state_32.py rewrite
    - test_ecc.py        update
    - test_compiler_v2.py update
    - others — audit pass needed
```

---

## Branch design — confirmed 2026-05-17

Two compiler modes for branching (both confirmed as viable):

### Mode 1: Compiled tree (small decisions)
Both branches fully compiled into cells simultaneously.
AND-gate masks each branch: true branch gets AND(condition, input),
false branch gets AND(NOT(condition), input). Both exist in silicon,
only one fires. Cost: proportional to branch size × 2.
Good for: inlined if/else, ternary expressions, small decisions.

### Mode 2: Program tile (dynamic dispatch)
A tile containing a table of {condition_value → (addresses, data)}.
Before the comparison fires, the tile preloads branch target addresses
into two pointer cells. When the condition fires, the correct pointer
cell emits the target address as its output value, activating the
correct preloaded primitive model.

**Branch point implementation — 3 cells:**

```
NOT cell:   NOT(condition)      → inverted_cond
cell_true:  AND + latch_in
              a_data preloaded  = true_target_address  (by tile, before decision)
              trigger           = condition
              output            → branch_router address

cell_false: AND + latch_in
              a_data preloaded  = false_target_address (by tile, before decision)
              trigger           = inverted_cond
              output            → branch_router address (same — wired-OR)
```

The branch_router address receives whichever AND cell fires (only one
can — gates are complementary). The value at branch_router IS the
target address. That value activates the correct primitive model.

**Why wired-OR is safe here:**
Only one of cell_true / cell_false can fire per decision — the gates
are NOT(x) and x, mutually exclusive. Bus OR is therefore unambiguous.

**Preloading:**
The program tile preloads a_data into both pointer cells BEFORE the
condition data arrives. This uses the preloaded comparator pattern
confirmed on silicon (2026-05-17) — first arrival sets a_data,
second arrival triggers the gate. Tile writes target addresses as
first arrivals to each pointer cell's input_address.

**While loops:**
Body is a Pond region. Condition fires CMD_RELEASE/CMD_FREEZE via PTT
to arm/disarm the body region for the next iteration. Loop_back on the
condition cell feeds the result back for re-evaluation.

**What this means for branch.py:**
- GS_SELECT is retired — do not use
- LOOP_MODE is retired — do not use
- New pattern: NOT + AND(latch_in) + AND(latch_in) = 3 cells per branch
- Compiler option 1: emit full AND-gated tree (static)
- Compiler option 2: emit program tile with pointer cells (dynamic)
- branch.py needs rewriting around this pattern
- compiler_int32.py: remove input_b_address from tile placements

**Next session starts here:**
  branch.py        — rewrite around 3-cell branch pattern
  compiler_int32.py — remove input_b_address
  Tests            — audit pass

---

## Two-arrival model — end-to-end wiring (2026-05-18 continuation)

### Problem
The two-arrival model requires each cell to receive the same input address
value twice: first arrival stores in a_data, second arrival triggers fire.
In a compiled program, different inputs (A and B for binary ops) need to
both arrive at the cell's single input_address.

### Solution: Relay cells (PASS_B | GS_LATCH_IN)
For binary ops where B comes from a separate source address (src_b):
- Emit a relay cell: GS_PASS_B|GS_LATCH_IN, listens on src_b, outputs to src_a
- Pre-arm relay in load_map (a_arrived=True) so it fires on single B arrival
- Relay forwards B to src_a as the second arrival trigger
- relay_targets: exclude src_a AND src_b from _pending_inputs re-injection

For single-input ops (NOT, standalone):
- Controller re-injects value on cycle 1 (_pending_inputs) as second arrival

### What works
- High-level compiler (ImagoCompiler): AND/OR/NOT all correct
- Chain propagation (NOT→PASS→PASS): correct via relay pre-arming
- 661 core tests: all passing

### Open issue: INT32 / fp_tiles relay timing
The fp_tiles NORBuilder._emit_v2 also emits relay cells. The Kogge-Stone
INT32 adder uses fp_tiles for all binary ops — emitting relay cells doubles
the cell count (~966 vs 483) and disrupts carry chain timing.

Root cause: relay cells should only be emitted at the INPUT BOUNDARY
(cells receiving user-injected values). Internal chain cells in the KS
adder receive their inputs naturally from upstream computed values which
arrive sequentially — no relay needed. The fp_tiles approach doesn't
distinguish boundary vs internal cells.

Fix needed next session:
- fp_tiles._emit_v2: don't emit relay for internal chain cells
- Option: add a parameter `relay_b=True/False` to _emit_v2 so callers
  that know they're at the input boundary can request relay emission
- run_int32_function: inject a_bits and b_bits to same addresses per bit
  position (alternative — eliminates need for relay in fp_tiles entirely)

---

## Preloaded-A pattern for INT32 adder (2026-05-19)

### Problem
Two-arrival model in fp_tiles: relay cells, carry persistence, and shared
input_address all conspired to prevent correct KS adder operation.

### Solution: Preloaded-A pattern (suggested by Alan)
Mirrors the preloaded comparator pattern confirmed on silicon (2026-05-17).

- A is NOT routed through the network. A values are computed via a Python
  forward simulation of the KS tree at run time, then written directly into
  each op cell's a_data (via region.preloaded_a, restored by start()).
- B is the single trigger wave. Injected once, propagates through the
  network. Each op cell fires immediately when B arrives (a_arrived=True).
- Wire cells use GS_PASS|GS_LATCH_IN — fire on single arrival, forward B.
- No relay cells. No carry timing issues. Clean and simple.

### Changes
- fp_tiles.py: _emit_v2 — records preload_map[out] = in_a source addr,
  emits op cell listening on in_b (B wave). No relay cells emitted.
- fp_tiles.py: wire() — uses GS_PASS|GS_LATCH_IN (single-arrival forward).
- fp_tiles.py: Tile class — preload_map field added.
- fp_tiles.py: _build_int32_add — threads preload_map into Tile return.
- fp_tiles.py: TilePlacer.place() — remaps preload_map, returns 5-tuple.
- compiler_int32.py: _tile_preloads accumulated per place() call.
- compiler_int32.py: run_int32_function — Python forward sim evaluates
  KS tree, known_preloads written to region.preloaded_a, only B injected.
- controller.py: start() — restores preloaded_a into a_data after reset.

### Results
INT32 addition: 11/11 tests passing including overflow, negative, large values.
Core tests: 19/19 passing.

### Note for silicon validation
The preloaded-A mechanism sets a_data directly in the VM. On real hardware
(iCEBreaker), this maps to CMD_SET_INPUT_ADDR + send_twice(addr, A) before
the B wave is injected. Confirmed pattern from test_ring_22.py / 2026-05-17.
The new card (arriving 2026-05-20) will be the first real test.

---

## run_compiled_function + MUX + ir.py relay fix (2026-05-19 cont.)

### Problem
test_compiler_v2.py MUX tests failing (None). Multi-level cell chains
(NOT + AND + AND + OR) broken by relay carry interference.

### Solution: run_compiled_function with two-pass preloaded-A sim

New function `run_compiled_function(src, fn, operands)` in compiler.py:

**Two-pass forward simulation:**
- Pass 1: compute all op cell outputs given inputs
- Pass 2: set preload[out] = first_arrival[in] for each op cell
  - Only preload cells whose A-input is a USER INPUT address
  - Intermediate cells (both inputs from upstream ops) use natural two-arrival

**Injection rules:**
- A-side (sim_map keys): skip direct injection — already in a_data
- Relay destinations: skip direct injection — relay delivers correct B
- Everything else: inject normally

**Relay one_shot:** relay cells fire once per run and disarm, preventing
carry-persisted upstream values from re-triggering them.

**preloaded_one_shot flag:** preloaded cells are one_shot in
run_compiled_function (prevents carry re-fires in shallow chains),
but NOT one_shot in run_int32_function (KS tree needs carry propagation).

**ir.py:** smart relay routing — leaf ops (both inputs user-injected) use
second_inputs_map scheduling; intermediate ops (B from upstream) use relay.

**controller.py start():**
- Relay cells: pre-armed + one_shot reset
- Preloaded-A cells: a_data restored + a_arrived=True + one_shot if region requests
- initial_value cells: NOT cells use double-injection (ir.py), no initial_value

**unicell_array.py carry suppression:**
- Relay cells: no carry (prevents repeated delivery)
- one_shot_fired cells: no carry (output served, no repeat needed)

### Results
- AND/OR/NOT: 8/8 + 2/2 passing
- MUX (4-cell chain): 4/4 passing  
- IfExp MUX: 2/2 passing
- INT32 ADD: 9/9 passing
- core tests: 19/19 passing
- compiler_v2 tests: all passing

### Mode 2 hook
second_inputs_map on compiler: {src_a → src_b} for leaf binary ops.
BranchPoint.build() is Mode 2 (PTT dispatch) — unchanged, ready.
run_compiled_function is Mode 1 (compiled tree) — working.
