# Python vs Verilog Audit — 2026-05-17

Ground truth: `fpga/verilog/unicell.v` (silicon-validated, iCEBreaker 2026-05-17).
This document maps every divergence between the current Python stack and that Verilog.
Work order follows the dependency graph: gate_states → unicell → array → ICM/image → compiler stack.

---

## Summary of divergences

| Category | What Python has | What Verilog has | Action |
|---|---|---|---|
| Config protocol | FUNCTION_LOAD_PATTERN (0xA5A5A5A5) on data bus | CMD_RECONFIGURE on separate cmd_bus | Remove LOAD_PATTERN entirely |
| Two-input model | input_b_address + receive_b() | One input_address, two arrivals at same address | Remove input_b_address, receive_b() |
| cmd_latch bit map | gate_state with old bit positions | Confirmed 32-bit cmd_latch | Remap all GS_ constants |
| SELECT cell | GS_SELECT (bit 9), output_address_alt | Not in Verilog — retired | Retire SELECT and output_address_alt |
| LOOP_MODE | bit 10 — stay armed | Not in Verilog — loop_back (bit 31) exists instead | Retire LOOP_MODE |
| GS_LATCH (bit 11) | latch_mode flag | latch_in (bit 26) — different bit, different semantics | Remap |
| GS_ONE_SHOT (bit 12) | one_shot flag | one_shot (bit 30) — different bit position | Remap |
| GS_INVERT_OUT (bit 13) | invert_out flag | invert_out (bit 25) — different bit position | Remap |
| GS_BROADCAST (bit 14) | broadcast flag | Not in Verilog | Retire |
| GS_SYNC_WAIT (bit 15) | sync_wait, waiting for two inputs | bit 10 — cell_type/edge_mode repurposing | Retire as explicit flag; two-arrival is default |
| GS_LOOP_BACK (bit 16) + src/dst (17-22) | loop_back_en + src/dst fields | loop_back (bit 31) — simplified | Remap, remove src/dst |
| GS_ADDR_LATCH (bit 23) | addr_latch, _config_upper, SCOPE_EXTENDED | Not in Verilog — 32-bit address space only | Retire entirely |
| GS_FALL_EDGE (bit 24) | fall_edge flag | Not in Verilog — odd_phase handles this internally | Retire |
| GS_LATCH_IN (bit 25) | latch_in flag | latch_in (bit 26) — one bit shifted | Remap |
| GS_OUT_POSEDGE (bit 26) | out_posedge flag | Not a cell flag — odd_phase is internal | Retire |
| GS_TYPE bits (27-28) | GS_TYPE_SHIFT=27, two bits | dtype (bits 23-24) — shifted two bits lower | Remap |
| priority (bit 29) | GS_PRIORITY=1<<29 | priority (bit 27) — shifted | Remap |
| trace (bit 30) | GS_TRACE=1<<30 | trace (bit 28) — shifted | Remap |
| breakpoint (bit 31) | GS_BREAKPOINT=1<<31 | breakpoint (bit 29) — shifted | Remap |
| storage_mode | Separate bool on cell | Encoded in latch_in + topology | Retire storage_mode |
| ECC format | "39-bit packet" with bits 32-38 | 32-bit data bus, ECC on cmd_bus bits 22-31 | Retire 39-bit ECC model |
| 64-bit addresses | SCOPE_EXTENDED, _config_upper | Retired — 32-bit + Shore index only | Retire |
| Command codes | CMD_DATA_WRITE=0 through CMD_PING=8 | CMD_NOP=0, codes differ (SET_INPUT=2, SET_OUTPUT=3, RECONFIG=4) | Remap |

---

## File-by-file changes required

### 1. gate_states.py — COMPLETE REWRITE

The entire bit layout is wrong. Every constant needs moving.

**Confirmed Verilog cmd_latch bit map:**
```
bits  9-0:   topology      (10 bits, one-hot NOR gate)
bit   10:    edge_mode     (0=STANDARD/LATCH, 1=EDGE cell) — was sync_wait
bits 21-11:  auth_mask     (11 bits, write-only, not in Python gate_state)
bit   22:    start_flag    (1 bit, set by CMD_RECONFIGURE)
bits 24-23:  dtype         (2 bits: 00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME)
bits 26-25:  cell_type     (2 bits: 00=standard 01=latch 10=posedge 11=negedge)
bit   27:    priority      (1 bit)
bit   28:    trace         (1 bit)
bit   29:    breakpoint    (1 bit)
bit   30:    one_shot      (1 bit)
bit   31:    loop_back     (1 bit)
bits 30-31:  HARD RESERVED in CELL_INTERNALS — conflict noted, Verilog wins
```

**What changes:**
- Remove: GS_SELECT (bit 9), LOOP_MODE (bit 10), GS_LATCH (bit 11),
  GS_ONE_SHOT (bit 12), GS_INVERT_OUT (bit 13), GS_BROADCAST (bit 14),
  GS_SYNC_WAIT (bit 15), GS_LOOP_BACK (bit 16), LOOP_BACK_SRC/DST bits (17-22),
  GS_ADDR_LATCH (bit 23), GS_FALL_EDGE (bit 24), GS_LATCH_IN (bit 25),
  GS_OUT_POSEDGE (bit 26), GS_TYPE_SHIFT=27, GS_PRIORITY=1<<29,
  GS_TRACE=1<<30, GS_BREAKPOINT=1<<31
- Remove: GS_TABLE_VAL, GS_COUNTER, GS_SENTRY (composites using retired flags)
- Remove: GS_LOOP_BACK_DEFAULT, gs_loop_back(), gs_extract_loop_back()
- Add: GS_EDGE_MODE = 1 << 10
- Add: GS_DTYPE_SHIFT = 23, GS_DTYPE_MASK = 0b11 << 23
- Add: GS_DTYPE_NUMERIC=0, GS_DTYPE_SIGNED=1<<23, GS_DTYPE_ALPHA=2<<23, GS_DTYPE_DATETIME=3<<23
- Add: GS_CELL_TYPE_SHIFT = 25, GS_CELL_TYPE_STANDARD=0, GS_CELL_TYPE_LATCH=1<<25,
       GS_CELL_TYPE_POSEDGE=2<<25, GS_CELL_TYPE_NEGEDGE=3<<25
- Add: GS_PRIORITY = 1 << 27
- Add: GS_TRACE = 1 << 28
- Add: GS_BREAKPOINT = 1 << 29
- Add: GS_ONE_SHOT = 1 << 30
- Add: GS_LOOP_BACK = 1 << 31
- Add: GS_LATCH_IN = 1 << 26 (was bit 25)
- Add: GS_INVERT_OUT = 1 << 25 (was bit 13)
- Remove: GS_AND_V2 etc composites using GS_SYNC_WAIT — all two-input ops use
  only topology bits (two arrivals is now the default, no flag needed)
- Update: OPERATION_TABLE to remove GS_SYNC_WAIT from all binary ops
- Update: GS_NOR = 0b000000100 (unchanged), GS_AND_V2 = 0b000000111 (unchanged topology, no GS_SYNC_WAIT)

**New composites:**
```python
GS_LATCH_CELL  = GS_CELL_TYPE_LATCH   # latch_in behaviour via cell_type
GS_STORAGE     = GS_CELL_TYPE_LATCH   # PASS topology + latch cell type
GS_LOOP_MEM    = GS_CELL_TYPE_LATCH | GS_LOOP_BACK  # loop_back + latch
```

---

### 2. unicell.py — MAJOR REWRITE

**Remove entirely:**
- `FUNCTION_LOAD_PATTERN = 0xA5A5A5A5`
- `input_b_address` field
- `receive_b()` method
- `_sync_buf` field (v1 SYNC_WAIT compat)
- `_input_b` field
- `output_address_alt` field (SELECT cells retired)
- `latch_mode` bool (replaced by cell_type bits)
- `addr_latch` bool + `_config_upper` int (64-bit addressing retired)
- `broadcast` bool (GS_BROADCAST retired)
- `sync_wait` bool (two-arrival is now default, no flag)
- `loop_back_en`, `loop_back_src`, `loop_back_dst` (simplified to one bit)
- `fall_edge` bool (odd_phase is internal to Verilog, not a Python flag)
- `out_posedge` bool (not a cell flag in Verilog)
- `storage_mode` bool + `_stored_value` (replaced by latch_in + cell_type)
- `_config_mode`, `_config_step` (LOAD_PATTERN config protocol retired)
- `_b_address` field
- Old `receive()` method with LOAD_PATTERN detection
- `_execute_nor_gates()` (v1 deprecated single-input path)
- All SELECT cell routing in `tick()`
- 64-bit addr_latch path in `tick()`

**Update:**
- `__init__`: new cmd_latch-aligned fields:
  - `edge_mode: bool` (bit 10)
  - `dtype: int` (bits 23-24, 0-3)
  - `cell_type: int` (bits 25-26: 0=standard, 1=latch, 2=posedge, 3=negedge)
  - `invert_out: bool` (bit 25 — NOTE: same bit as cell_type LSB; Verilog uses bits 25-26 for cell_type and bit 25 separately for invert_out on EDGE cells. Resolve: invert_out is derived from cell_type==negedge, not a separate flag)
  - `latch_in: bool` (bit 26)
  - `one_shot: bool` (bit 30)
  - `loop_back: bool` (bit 31)
  - `a_data: int` (first arrival storage — matches Verilog a_data register)
  - `a_arrived: bool` (matches Verilog a_arrived flag)
  - `armed: bool` (matches start_flag + !frozen)
- `configure(cmd_latch_word, input_addr, output_addr)`: replaces receive() config path
  - Unpacks all fields from single 32-bit cmd_latch word (auth_mask bits zeroed in Python)
  - Sets input_address and output_address from separate SET_ADDR commands
- `tick()`: rewritten to two-arrival model:
  - First arrival at input_address → stores in a_data, sets a_arrived, NO output
  - Second arrival at input_address → fires gate tree on a_data, clears a_arrived
  - latch_in=1: a_arrived NOT cleared after fire → single arrival fires (memory mode)
  - edge_mode=1: fires on transition of bus_data[0] vs prev_data — single arrival
  - loop_back=1: computed output fed back to a_data for next trigger
  - one_shot=1: clears start_flag (armed) after first fire
  - invert_out=1 (cell_type bits encode negedge): flip output[0] before emit
- `_execute_nor_gates_v2(a, b)`: keep but note — in silicon a_data is always A,
  second arrival triggers but its value is the B input. Python must match:
  first stored in a_data, second arrival value is b in the gate tree.

**New methods:**
- `receive(value)`: single method, one input_address. Implements two-arrival model:
  - If a_arrived=False: store value in a_data, set a_arrived, return None
  - If a_arrived=True: return value for gate tree as (a_data, value)
- `configure_from_word(cmd_latch: int)`: unpack 32-bit word into all fields

---

### 3. unicell_array.py — SIGNIFICANT CHANGES

**Remove:**
- FUNCTION_LOAD_PATTERN import
- `write_config()` method (LOAD_PATTERN protocol)
- `input_map_b` dict (B-address routing for input_b_address)
- Phase-2 B-input delivery loop
- `storage_mode` parameter in write_config

**Update:**
- `tick()`: single input map — all cells at input_address get each bus value
  - First delivery → a_arrived set, no fire
  - Second delivery → fire
  - Remove separate B-input phase entirely
- `configure_cell(cell, cmd_latch, input_addr, output_addr)`: new method replacing write_config
- Bridge registry access check: remove input_b_address from registered addresses

---

### 4. command_interface.py — MODERATE CHANGES

**Command code remapping** (Python → Verilog):
```
Old Python → New (matches Verilog)
CMD_DATA_WRITE=0       → 1 (CMD_DATA_WRITE, user+system — but in Verilog this is bus_valid, not cmd_valid)
CMD_SET_INPUT_ADDR=1   → 2
CMD_SET_OUTPUT_ADDR=2  → 3
CMD_RECONFIGURE=3      → 4
CMD_FREEZE=4           → 5
CMD_RELEASE=5          → 6
CMD_COPY_DATA_TO_OUT=6 → retire (not in Verilog)
CMD_COPY_DATA_TO_IN=7  → retire (not in Verilog)
CMD_PING=8             → 9
```

**Remove:**
- `_SCOPE_EXTENDED`, `_SCOPE_SHORE` (only LOCAL remains)
- `_config_upper` path in `reconfigure()`
- 64-bit address routing
- LOAD_PATTERN emission path in `reconfigure()`
- `scope` parameter (always LOCAL)

**Update:**
- `build_bus1()`: remove scope/EXTENDED path; keep cmd code, auth, cell_id targeting
- Add `cell_id` field to bus1 word (bits 26-16): target cell for RECONFIGURE/SET_ADDR
- `reconfigure()`: emits `cmd_latch_word` (32-bit) as single cmd_data payload
  - Auth token goes in cmd_bus bits 14-4
  - Cell_id goes in cmd_bus bits 26-16
  - No more multi-step config sequence via LOAD_PATTERN

**cmd_bus bit layout (from silicon):**
```python
# bits  3-0:  command code
# bits 14-4:  auth token (11 bits)
# bit   15:   raw_addr (host always sets 1)
# bits 26-16: cell_id (11 bits, 0x7FF = broadcast)
# bits 31-27: reserved
```

---

### 5. controller.py — MODERATE CHANGES

**CellMapRecord:**
- Remove: `input_b_address`, `output_address_alt`, `storage_mode`
- Keep: `gate_state` (renamed to `cmd_latch` eventually), `input_address`, `output_address`, `initial_value`
- Add: no new fields (cmd_latch word contains everything)

**load_map():**
- Remove: input_b_address routing, output_address_alt, storage_mode handling
- Update: configure each cell using `configure_from_word(cmd_latch)` + set addresses

**write_config():** retire entirely — replaced by configure_cell()

---

### 6. program_image.py — MINOR CHANGES

**ICM record format:**
- Remove: `"inB"` field (input_b_address)
- Remove: `"alt"` field (output_address_alt)
- Remove: `"stor"` field (storage_mode)
- Keep: `"gs"` field (rename to `"cl"` for cmd_latch eventually, but keep `"gs"` for compat)
- Add: `"format_version": 2` field to ICM header
- Keep: `"in"`, `"out"`, `"init"` fields unchanged

**on load:**
- Warn if `"inB"` field present (retired), ignore it
- Warn if `"alt"` field present (retired), ignore it

---

### 7. ir.py — SIGNIFICANT CHANGES

**Remove:**
- `GS_SYNC_WAIT` from all binary op gate_states (AND, OR, XOR, NAND, XNOR, NOR)
- `GS_OUT_POSEDGE` from all emitted cells
- `input_b_address` field on all CellMapRecord emissions
- PASS pad cells for OR depth alignment (SYNC_WAIT was handling this — now two-arrival handles it naturally)
- `LOOP_MODE` from all emitted gate states

**Update:**
- `lower_to_cell_map_v2()`: binary ops just use topology bits, no flags needed
- OR path: single cell, two arrivals at same address from Y-formation — remove pad cells
- All CellMapRecord emissions: remove input_b_address= kwarg

---

### 8. fp_tiles.py — SIGNIFICANT CHANGES

**Every NORBuilder.two_input() call:**
- Remove `GS_SYNC_WAIT` from all binary op topology constants
- Remove `GS_OUT_POSEDGE` from all emitted cells
- Remove `GS_FALL_EDGE` from all emitted cells
- Remove `input_b_address=in_b` from all CellMapRecord constructor calls

**NORBuilder class:**
- `two_input(gs, in_a, in_b, out)` → `two_input(gs, in_addr, out)`:
  - Both A and B arrive at same `in_addr`
  - Compiler must emit Y-formation (two upstream cells both writing to `in_addr`)
  - NORBuilder no longer needs `in_b` parameter
- Remove GS_FALL_EDGE import and usage

---

### 9. branch.py — SIGNIFICANT CHANGES

SELECT cell pattern is the main casualty.

**Remove:**
- `GS_SELECT` import and all usage
- `output_address_alt` from all CellMapRecord calls
- `LOOP_MODE` from all gate states

**SELECT replacement (needs design):**
Branch comparator currently uses: storage cell → XNOR chain → AND → SELECT(LOOP_MODE).
SELECT cell reads condition and routes to true/false address.
Without SELECT: the branch must be expressed differently.
Options:
  a. Two-cell branch: condition cell → fires to one of two downstream addresses
     (compiler inserts one cell per branch that only arms when condition fires it)
  b. PTT-based: condition result → PTT → COMPANION → sets start_flag on correct branch
     (slower but already works for pond-level branching)
  c. MUX cell: use the INT32_MUX tile logic at 1-bit width

**For the next session:** flag branch.py as blocked pending branch design decision.
The branch.py pattern is the most architecturally significant retirement.
Mark tests for branch/while/select as EXPECTED FAIL during migration.

---

### 10. compiler.py and compiler_int32.py — MODERATE CHANGES

**Remove:**
- `GS_SELECT` import and branch compilation using SELECT cells
- `LOOP_MODE` from storage/loop variable cell states
- `storage_mode=True` from all CellMapRecord() calls

**Update:**
- Loop variable cells: use `GS_CELL_TYPE_LATCH` (cell_type=latch) instead of storage_mode
- Y-formation routing: compiler must ensure binary op cells receive two arrivals
  at the same address — emit two upstream cells both writing to the same address
  with matched depth
- `_place_int32_lt_tile()` etc: remove input_b_address from CellMapRecord

---

### 11. fpga/fpga_bridge.py — MINOR CHANGES

Already partially updated (comments reference retired fields). Full check:
- Remove input_b_address from config sequence emission
- Update CMD codes to match Verilog (SET_INPUT=2, SET_OUTPUT=3, RECONFIG=4, FREEZE=5, RELEASE=6, PING=9)
- Remove LOAD_PATTERN emission

---

### 12. fpga/icm_loader.py — MINOR CHANGES

- Remove inB field handling (already warns, just remove the warning and the code)
- Update CMD codes to match Verilog

---

### 13. Tests — significant audit needed

Files expected to fail during migration:
- `test_select.py` — SELECT cells retired
- `test_addr_latch.py` — GS_ADDR_LATCH retired
- `test_while.py` — uses SELECT for branch
- `test_branch.py` — uses SELECT for branch
- `test_ecc.py` — ECC format changes (39-bit retired)
- `test_gate_state_32.py` — all bit positions wrong
- `test_compiler_v2.py` — GS_SYNC_WAIT in binary ops

Files that should pass after unicell.py/gate_states.py update:
- `test_array.py`, `test_pond.py`, `test_controller.py`, `test_compiler.py`
- All PTT/Ward/Shore tests (pond.py not directly affected)

---

## Execution order

Strict dependency order. Each step must pass tests before the next starts.

```
1. gate_states.py       — remap all constants to confirmed Verilog bit positions
2. unicell.py           — rewrite to two-arrival model, new cmd_latch fields
3. unicell_array.py     — remove B-input phase, update configure path
4. command_interface.py — remap CMD codes, remove SCOPE_EXTENDED
5. controller.py        — CellMapRecord cleanup, remove storage_mode
6. program_image.py     — ICM format cleanup (remove inB/alt/stor)
7. ir.py                — remove GS_SYNC_WAIT/GS_OUT_POSEDGE/input_b_address
8. fp_tiles.py          — NORBuilder cleanup
9. compiler.py          — remove SELECT/LOOP_MODE/storage_mode patterns
10. compiler_int32.py   — remove input_b_address from tile placements
11. branch.py           — BLOCKED: needs branch design decision
12. fpga/fpga_bridge.py — CMD code update
13. fpga/icm_loader.py  — CMD code update, remove inB
14. All tests           — audit and fix
```

## Affected test files (full list)

Tests that reference retired features and need updating or retiring:
```
test_select.py          — GS_SELECT retired — test must retire or redesign
test_addr_latch.py      — GS_ADDR_LATCH retired — test retires
test_while.py           — SELECT-based branch — blocked on branch design
test_branch.py          — SELECT-based branch — blocked on branch design
test_gate_state_32.py   — all bit positions wrong — needs full rewrite
test_compiler_v2.py     — GS_SYNC_WAIT in binary ops — update
test_ecc.py             — 39-bit ECC format — update to cmd_bus ECC
test_freeze.py          — may use storage_mode — check
test_compiler.py        — storage_mode in loop cells — update
test_handshake.py       — handshake bits may have moved — check
```

Tests expected to pass without changes (pond/OS layer):
```
test_pond.py, test_pond_ptt.py, test_pond_restart.py, test_shore_v2.py,
test_shorekeeper.py, test_ward.py, test_pond_connect.py,
test_workspace_pond.py, test_pond_bootstrap.py, test_ptt_sentry.py
```

---

*Session: 2026-05-17. Ground truth: fpga/verilog/unicell.v.*
*Next: start with gate_states.py rewrite — all other changes depend on it.*
