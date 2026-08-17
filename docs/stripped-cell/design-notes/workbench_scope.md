# The Unicell-S workbench — design scope

*Captured 2026-08-16 (day 2), based on a real, line-level audit of the
old `workbench.py` (2711 lines) -- not a fresh design from nothing.
Per Alan's own instruction: check the old version first for what's
non-functional under the new system shape before designing anything.*

## What the audit found, precisely

**Genuinely dead** -- addressed-bus/`gate_state`-specific, no
equivalent concept in Unicell-S at all:
- `array_snapshot()`/`cell_state()`/`gate_details()` -- keys cells by
  integer address, decodes one `gate_state` word into NOR-topology
  opcodes with LATCH_IN/ONE_SHOT/LOOP_BACK bits packed in. Unicell-S
  has no single opcode word -- `core_select` (which of 6 cores) plus
  per-core fields that differ entirely by core (an accumulator has
  `inc_dir`/`dec_dir`, not a gate topology at all).
- `inject_bus(address_hex, value)` -- writes to `array.bus[addr]`.
  There is no bus.
- `configure(cell_count, num_dimms)` -- DIMM-partitioned pre-allocated
  address pools. Unicell-S programs are small, explicitly hand-placed
  grids, not huge address spaces.
- `compile_and_load()`/`_load_records()` -- the old `ImagoCompiler`,
  returns `input_map`/`output_addrs` (bus addresses).
- `load_demo()` and all six `_demo_*` implementations -- raw opcode
  cell allocation (`allocate_cell()`, `write_config()`, `GS_PASS`).
- `highlight_region()`/`free_region()` -- regions are address sets.
- `run_tests()` -- the old 14-suite list, every target stale.
- `attach_os()`/Shore-Ward-Companion shell commands -- a different,
  unrelated subsystem, not built for Unicell-S at all.
- The embedded JS's own field bindings (`c.address_hex`,
  `c.gate_state_hex`, `pondColorForAddr()`, etc.) throughout the UI.

**Genuinely reusable** -- addressing-agnostic infrastructure or
pattern, not code to port as-is:
- The tick/step/run/pause *concept* -- actually a CLEANER fit on the
  new VM, since `SuperGrid.tick()` already returns the active-cell set
  directly, no scanning needed.
- `start_server()`/`stop_server()` -- plain `http.server`/threading,
  serves whatever JSON it's handed, genuinely generic.
- The general UI *pattern* (a rendered cell grid, click-for-details,
  run/step/pause controls) -- reusable as a layout idea only.

**Already built, not starting from zero:** the replacement DATA LAYER
for the dead parts above already exists from earlier this session --
`vm_introspection_v1.py` (`#354`) is the real `array_snapshot()`
equivalent; `vm_ai_port_v1.py`'s `VMSession` (`#359`) already covers
compile/step/inject/deliver/describe in one clean, tested object. A new
workbench is mostly server + UI wiring on top of already-tested VM
logic, not new VM logic.

## Proposed architecture for the first real slice

A thin HTTP layer directly over `VMSession`, nothing more for v1:

```
GET  /              -> serves the HTML/JS page
GET  /state          -> VMSession.describe(), as JSON
POST /compile         -> {"source": "...", "language": "dsl"|"python"}
                          compiles, replaces the current session,
                          returns diagnostics + initial state
POST /step             -> {"n": 1} -- advances n ticks, returns new state
POST /deliver            -> {"row", "col", "direction", "value", "injected"}
                             drives one cell directly
POST /inject               -> {"row", "col", "value"} -- boundary injection
```

Row/col-keyed JSON throughout (matching `vm_introspection_v1.py`'s own
shape exactly), never an address anywhere.

## Suggested first, low-risk step

Build the server + API first, tested end to end with real HTTP calls
against a real running session (compile the proven `sentinel` program,
confirm state, step it, drive it, confirm the accumulator/comparator/
latch state matches the same real behavior already proven in
`points.md #340`) -- before spending time on visual polish. A minimal,
functional HTML page comes after the API is proven correct, not before.
