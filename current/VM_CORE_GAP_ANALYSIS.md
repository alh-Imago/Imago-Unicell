# VM Core Gap Analysis — root-level Python vs. the nano cell, vs. #216's requirements

*Written while waiting on the FPGA timing work (`#206`-`#215`) to settle,
per Alan's request: map what already exists, find the holes, before
`core/` gets built. Not a design document itself — `#216` is the design;
this is the "what's actually there" survey that informs it.*

## Method

Every root-level `.py` file's top docstring pulled via `ast.get_docstring`
(77 files total), then grepped for which cell format each one actually
targets: the OLD full-cell markers (`gate_state`, `CellMapRecord`,
`unicell64`) vs. any mention of the stripped/nano cell at all.

**Headline result: zero of the 77 root files mention the stripped/nano
cell. 35 of the 77 explicitly target the old full-cell format.** This
matches and sharpens the standing `current/PLAN.md` note ("compiler.py
targets the old full-cell `CellMapRecord` format") with a hard number
rather than a general impression.

## What actually exists for the nano cell today

Two files only, both in `nano/`, not root:

- **`nano/unicell_automaton_v1.py`** (584 lines) — `CACell` (single cell)
  + `CAGrid` (grid of cells, fixed physical neighbors only, no addressing/
  bus). This is a genuinely live, currently-accurate simulation core, not
  stale prior art — confirmed directly: `program_word()`'s docstring cites
  `points.md #123/#140/#156` and its field-ID table matches
  `unicell_stripped_v1.v`'s real `PROG_ID` table exactly (checked
  side-by-side, same 3-bit-ID/16-bit-data scheme `#211` confirmed against
  the RTL this session). `CAGrid.tick()` advances one cycle, combining
  same-cell simultaneous arrivals (`#153`'s OR-combine); `run_to_
  quiescence()` runs until settled; `inject()`/`confirm_read()` handle
  boundary I/O.
- **`nano/unicell_gate_core.py`** (93 lines) — the NOR-tree gate
  computation and topology decode table, extracted because it's verified
  BYTE-IDENTICAL between the full cell and the stripped cell (checked
  against both `.v` files directly, not assumed). Genuinely shared, not
  nano-specific, but lives here since it's what the nano side currently
  imports.

So the honest starting point is better than "nothing" — there's a real,
RTL-tracking simulation core for a single grid, already correctly
modeling the current programming format. What's NOT there is everything
`#216` asked for beyond bare simulation.

## Root-level capability inventory, by category

*(35/77 files target the old full-cell format; the rest are either
cell-format-agnostic infrastructure or genuinely reusable as patterns,
noted below.)*

**Core VM / cell-simulation layer (old-format):** `unicell.py`,
`unicell_array.py` (`UniCellArray`, `BusSegment`, `BusConflictError` —
the old addressed-bus model, doesn't apply to nano's bus-less design at
all), `controller.py`, `compiler.py`, `compiler_int32.py`, `gate_states.py`,
`cell_format.py`, `command_interface.py`, `sequencer.py`, `packet_spec.py`,
`program_image.py`, `program_builder.py`, `vm_image.py`, `model_library.py`,
`ir.py`, `fp_tiles.py` (93 classes/functions — the floating-point macro
tile library, sizeable and would need real porting work, not a small
shim).

**OS/Pond layer (Companion/Ward/Shore ecosystem — format-agnostic in
principle, but built and tested only against the old cell):**
`companion.py`, `pond.py`, `pond_ptt.py`, `pond_types.py`, `shore.py`,
`shore_core.py`, `shore_v2.py`, `shorekeeper.py`, `ward.py`, `ward_core.py`,
`sentinel_core.py`, `device_bridge.py`, `workspace.py`, `run_companion.py`,
`multi_dimm.py`, `uniflex_fs.py`, `fs_search.py`, `display_pond.py`,
`compiler_pond.py`, `unicell_deployed.py`, `unicell_server.py`.

**Domain/Trix demo applications (old-format, but the DOMAIN LOGIC itself
is format-independent — these are the 55 community model files referenced
in memory):** `gol.py`, `sort.py`, `postcode_sort.py`, `branch.py`,
`cast.py`, the `mathtrix_*_mif.py` family (9 files — boids, conway,
fast-marching, gray-scott, ising, laplacian 1d/2d, nbody, pagerank, wave),
`flowtrix_cost.py`/`flowtrix_cylinder.py`/`flowtrix_lbm_mif.py`,
`neurotrix_lif.py`/`neurotrix_lif_mif.py`, `miditrix_lif.py`,
`nettrix_runner.py`, `optitrix_runner.py`, `sensortrix_runner.py`.

**LLVM/frontend:** `llvm_frontend.py`, `llvm_ir_mapper.py`.

**Old hardware bridge (iCEBreaker/UART era, predates current Quartus/
JTAG workflow):** `fpga_bridge.py`, `fpga_bringup.py`.

**Misc/support (likely genuinely reusable as-is or near-as-is):**
`imago_log.py`, `conftest.py`, `pipeline_queue.py`, `packed_adder_cells.py`,
`packed_shift_adder.py`.

**Two files worth calling out specifically as reusable PATTERNS (not
reusable CODE — both target the old format, but the architecture is
exactly what `#216` needs):**

- **`gpu_array.py`** — "GPU Stage 1: CuPy/NumPy unified array backend."
  Already solves `#216` requirement 3 (dual CPU/GPU execution) for the
  OLD cell: vectorises the per-cell tick loop, CuPy on GPU, NumPy
  fallback on CPU, same code path either way. The array-of-registers
  layout (`gate_state`, `input_address` as parallel arrays) won't
  transfer directly to the nano cell's very different field layout, but
  the vectorisation STRATEGY is exactly the one to reuse.
- **`companion.py`'s `attach_ai(model_path)`** — a real, working
  AI-attach precedent already in the codebase (referenced in
  `current/PLAN.md`'s own much older note about Composer/compiler/VM
  each needing an AI-interaction port). Narrower in scope than `#216`
  asks for (a specific Ward-escalation classifier hook, not a general
  port), but it's proof the pattern already has a working shape here,
  not something to invent from nothing.

## The actual holes, mapped directly against #216's 8 requirements

1. **Root definition from RTL** — PARTIAL. `unicell_automaton_v1.py`
   correctly tracks the RTL today, verified by hand each time (comments
   citing specific points.md entries), not generated/read from a file.
   No mechanical link from `unicell_stripped_v1.v` to the Python model —
   if the RTL changes, nothing catches the drift automatically.
2. **Grid construction** — DONE. `CAGrid` already does this correctly for
   the nano cell.
3. **Dual CPU/GPU execution** — MISSING for the nano cell. `gpu_array.py`
   proves the pattern works but targets the wrong cell entirely.
4. **Cell-design-aware/parameterized** — MISSING. `CACell`/`CAGrid` are
   hardcoded to today's specific field layout, not parameterized against
   a loadable definition.
5. **JSON introspection API** — MISSING entirely. No `to_dict`/`json`
   anywhere in either nano file.
6. **AI-interaction port** — MISSING on the nano/VM side specifically;
   `companion.py`'s `attach_ai()` is real prior art but lives in the OS
   layer, not the VM core, and is narrower in scope.
7. **Timing-awareness for the workbench** — PARTIAL. `CAGrid.tick_count`
   exists as a bare counter; no real-world-equivalent timing (ns/tick,
   clock-frequency emulation) and no user-facing speed control at all.
8. **No compiler/model-loading bridge** — MISSING, and this is the
   biggest one: there is currently no way to load a compiled program
   into `CAGrid` at all. Everything today goes through manual
   `inject()`/`program_word()` calls — no `.icm`-equivalent ingestion
   path for the nano cell, matching the standing `current/PLAN.md` note
   exactly ("no working pipeline exists from the 55 community model
   files to the current nano cell").

## Not a recommendation, just the map

This is deliberately just an inventory, not a build plan — `#216` already
covers the intended shape of `core/`. The one thing worth flagging
explicitly: `fp_tiles.py` (93 defined names) and the Trix domain-model
family are real, sizeable existing logic whose actual computational
content is likely cell-format-independent even though today's plumbing
isn't — worth keeping in mind as "port the logic, not the plumbing" when
that phase starts, rather than being written off as dead weight just
because they currently import old-format modules.
