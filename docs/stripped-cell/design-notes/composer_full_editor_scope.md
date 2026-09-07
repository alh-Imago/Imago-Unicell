# The Composer's full editor — real scope, per the #676 audit

*Captured 2026-09-07, per Alan's own direct request following the
`#676` orphaned-work audit ("scope both out into docs, so we know
where we are"). A real scoping pass only, matching this project's own
established discipline (`composer_scope.md`, `workbench_scope.md`,
`command_core_scope.md`/`_v2.md`) — define the real boundary before
writing any code, not after.*

## Where this picks up from

`composer_scope.md` (2026-08-17, `#385`) already made the real,
foundational call: the Composer's job is PLACEMENT/ROUTING review of an
already-compiled model, not model authoring — the DSL/frontends own
that. It deliberately scoped a "real, minimal first pass" (render the
current grid, show where automated placement landed, let a person
confirm/adjust) and explicitly deferred "a full drag-and-drop routing
editor" as real, larger future work.

That first pass shipped (`#606`-`#609`), but it is NOT the drag-and-
drop editor `composer_scope.md` deferred — it's a different, smaller
thing that happened to satisfy Alan's own three stated requirements at
the time. **This note scopes the actual deferred item**, now that
`#676`'s audit confirmed it's still genuinely unbuilt.

## What actually exists today, checked directly, not assumed

There is no separate "Composer" page or tool. "Composer" today is a
real set of features extending `nano/workbench_v1.py` directly:

- **Shell/version compatibility awareness** (`shell_compat_v1.py`) —
  a hard rejection if a placed core type doesn't exist on the selected
  shell, derived live from the real `.v` files, never hand-copied.
- **Connection hints, never rejections** (`connection_check_v1.py`) —
  flags when a cell broadcasts toward a neighbor not configured to
  listen back, checked against real per-core direction-field mappings.
- **Configured-state/cardinal-direction visibility** — each cell's own
  grid-rendered box shows a real `out: .../in: ...` summary line.
- **Real ICM save/load** (`#607`), reusing the same grid.

All of this is genuinely useful and real, but it's REVIEW tooling
layered on the workbench's existing static grid render — there is no
canvas, no drag gesture, no library panel, anywhere in the current
code. `composer_scope.md`'s own real premise (a human visually
confirming/adjusting an already-computed placement) is still only
half-built: the CONFIRM half exists; the ADJUST half does not.

## What's genuinely reusable from the old, archived Composer

Re-confirmed against `archeology/onion/old_composer_tool.onion`
(`composer/unicell_composer.html`), the same source `composer_scope.md`
already checked once — the underlying DATA MODEL is still dead
(`format_version: 2`, 32-bit `gate_state`), but the VISUAL PARADIGM
remains real and worth reusing:

- Canvas-based cell placement, pan/zoom, box-select, multi-select.
- Drag-from-output-port, release-on-input-port linking gesture.
- A library panel for dropping pre-built pieces onto the canvas.
- The tool already loads raw `.icm`/JSON files client-side
  (`loadFile` → `FileReader.readAsText`, per `current/PLAN.md`'s own
  earlier notes) — a real precedent for a future palette/import flow,
  not just a placement canvas.

## The one real, unresolved architectural question, not answered here

The old system's links were graph edges between arbitrary named ports,
decoupled from physical position. The current system's connections are
CARDINAL and REQUIRE physical adjacency — a `ram` cell's `out: e`
field means, literally, "the cell directly east of me." This makes the
old "drag from an output port, release on an input port" gesture
ambiguous here in a way it wasn't in the old system, and this note
does not resolve it. Two real, different things the gesture could mean
in this architecture:

1. **Placement-only interpretation** (matches `composer_scope.md`'s
   own already-decided scope exactly): dragging a cell moves it in
   space; a "link" is just the visual confirmation that two cells
   already configured with matching directional fields are now
   physically adjacent. No new DSL/record semantics needed — this is
   a real, direct extension of what exists today (see below).
2. **Authoring interpretation**: dragging from one cell's port to
   another's actually SETS that connection — i.e., the editor writes
   `out`/`in`/`inc_dir`/etc. fields, not just arranges pre-authored
   ones. This is real model AUTHORING, which `composer_scope.md`
   explicitly ruled out of scope for the Composer ("the DSL/frontends
   already own this, and do it well").

**Recommendation, not a decision:** interpretation 1 is the one
consistent with the project's own already-stated scope; interpretation
2 would need Alan to explicitly reopen the authoring question first.
This note assumes interpretation 1 for the real, minimal next slice
below, but flags the choice plainly rather than picking silently.

## What already exists to build on, not duplicate

- `nano/workbench_v1.py`'s own live grid render (`renderState()`,
  existing `.cell` DOM elements per position) — the real starting
  point for a canvas/drag layer, not a from-scratch renderer.
- `nano/loader_v1.py`'s `bind_shape()`/`find_auto_placement()`/
  `find_dsp_aware_placement()` — the automated half of placement,
  already real and tested; a drag interaction only needs to let a
  person OVERRIDE its result, not replace the algorithm.
- `connection_check_v1.py`'s per-core direction-field map — already
  computed server-side for hints; the same data could drive which of
  a cell's four sides light up as valid drop targets while dragging.
- `super_tile_library_v1.py`'s own Tier-0/composed tile catalog — a
  real, already-populated list of named, placeable pieces (`sentinel`,
  `dual_threshold_monitor`, `twin_sentinel`, `select`, etc.) that is
  the natural, already-built data source for a library panel — no new
  registry needed, just a new client for an existing one.

## A real, minimal next increment (not built), matching interpretation 1

1. **Make existing grid cells draggable.** Mouse-down on a rendered
   cell, drag, drop on an empty grid position; snap to row/col. A new
   `move_cell(name_or_pos, new_row, new_col)` controller method reuses
   the exact collision-check logic `load_region()` already runs before
   writing records, rather than a new check.
2. **Visual port highlighting during drag**, reusing
   `connection_check_v1.py`'s data purely for display (matching
   `#606`'s own "display only, real gate stays server-side"
   discipline) — a neighbor cell's matching side highlights green when
   a drag would create a live connection, red when it would create a
   dangling/mismatched one, per the direction-field map already
   computed.
3. **A real library panel**, listing `super_tile_library_v1.py`'s own
   tile catalog by name + description (already present as
   `describe()`-style metadata); dragging an entry onto the grid calls
   the existing `place()`/`place_composed()` path, same as the DSL
   compiler already does — no new placement mechanism, a new client
   for the existing one.
4. **Defer pan/zoom/box-select/multi-select** to a later pass — the
   current grid is small enough (tens of cells, not hundreds) that
   these matter less than they did for the old system's larger, more
   free-form designs; worth reconsidering once real usage shows
   whether the grid genuinely outgrows the current fixed-size render.

## Explicitly, honestly NOT scoped here

- Model/topology AUTHORING from a blank canvas (interpretation 2
  above) — needs Alan's own explicit reopening of `composer_scope.md`'s
  own already-decided boundary, not assumed here.
- Any new core/cell type creation.
- Any RTL, any hardware target — software/VM-side only, unchanged from
  `composer_scope.md`.
- Answering whether the four-item increment above should be a new
  page, a new mode of the existing workbench grid, or a genuinely
  separate tool — a real, small product decision, not a technical one,
  left for whenever this is actually picked up.

## Status

No code exists for any of this yet. Design/scoping note only, per
Alan's own direct request, following the exact discipline every other
`*_scope.md` in this directory already uses.
