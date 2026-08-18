# The Composer — real scope, per the #385 reframing

*Captured 2026-08-17 (day 3), given limited session time remaining --
a real scoping pass, not a build. Item 8 of `#370`'s own priority
list, last on purpose.*

## The real premise, now, not the original one

`#370` raised real doubt about the Composer's ORIGINAL premise
("create models") -- it needs pre-made models and full system
understanding to be useful for that. `#371` reintroduced it anyway,
positioned last. `#385` found a genuinely different, additional reason
for it to exist: **a visual, human-in-the-loop tool for PLACING and
ROUTING an already-compiled model**, not for authoring one from
scratch. This note scopes THAT premise, not the original one -- the
DSL/frontends already own program authoring (`docs/stripped-cell/
UNICELL_S_DSL_MANUAL.md`), and do it well.

**Why this premise is real, not speculative:** the underlying
placement/connection problem is CONFIRMED NP-complete (`#385`,
Numberlink). No algorithm guarantees an optimal answer as connection
count grows. Humans are genuinely good at this class of puzzle in
practice, despite its proven worst-case hardness. A visual tool that
lets a person see the grid, see what needs to connect to what, and
route it by eye is a real, useful complement to an automated heuristic
search (`loader_v1.py`'s own anchor-first-BFS-style approach) — not
a replacement for the loader, a partner to it.

## What's genuinely reusable from the old (archived) composer, and why

Checked directly against the archived tool
(`archeology/onion/old_composer_tool.onion`), not assumed from memory.
**The VISUAL PARADIGM is real and reusable; the DATA MODEL underneath
it is not** (confirmed old, `format_version: 2`, "32-bit gate_state
control" -- the same old, incompatible architecture archived
throughout `#364`-`#367`):

- Canvas-based cell placement, pan/zoom, box-select, multi-select.
- Drag-from-output-port, release-on-input-port linking gesture.
- A library panel for dropping pre-built pieces onto the canvas.

None of the underlying data (cell types, port semantics, `.icm`
format) carries over -- only the interaction PATTERN.

## What already exists to build ON, not duplicate

- **`nano/workbench_v1.py`** already renders a real, live grid from
  `VMSession.describe()`'s own JSON, and already has real region
  loading/placement (`#363`/`#375`/`#377`). The Composer's own
  rendering could be a real EXTENSION of the workbench's existing grid
  view, not a separate renderer built from scratch.
- **`nano/loader_v1.py`**'s own `bind_shape()`/`find_auto_placement()`/
  `find_dsp_aware_placement()` already do the AUTOMATED half of
  placement. The Composer's real job is the human-assisted half --
  proposing a placement, letting a person see and adjust it, not
  replacing the automated search.
- **`vm_introspection_v1.py`/`VMSession`** already provide the real
  "compile, place, check validity, inspect" loop (`#359`/`#385`) any
  interactive tool would need underneath it.

## A real, minimal first scope, not the full vision

Given the size of what's already been designed this session
(`#381`/`#382`'s own header/collector/command mechanism, the DSP
interface work, the connection-point problem itself), a REAL first
Composer pass should be genuinely small:

1. Render the CURRENT grid state (reuse the workbench's own real
   rendering -- don't rebuild it).
2. Let a person see where the loader's own automated placement landed,
   and visually confirm/adjust it BEFORE committing -- not open-ended
   free-form design, a real, bounded "review and correct" role.
3. Defer actual drag-to-place/drag-to-route interaction to a later
   pass -- start with VISUALIZING the placement problem clearly, since
   that alone is real, useful, and much smaller than a full editor.

## Real, honest, explicitly NOT scoped here

- Model AUTHORING (the Composer's original, doubted premise) --
  explicitly not this note's concern; the DSL/frontends already do
  this.
- Any new core/cell type creation -- unrelated to placement/routing.
- A full drag-and-drop routing editor -- real, larger future work once
  the minimal "view and confirm" pass proves useful.
- Any RTL, any hardware target -- this is a software/VM-side tool only.

## Not yet done, stated plainly

No code exists for any of this yet. This is a real scoping pass only,
matching the same discipline as every other `*_scope.md` note in this
directory (`workbench_scope.md`, `super_tile_library_scope.md`,
`unicell_s_dsl_and_compiler_scope.md`) -- define the real boundary
before writing anything, not after.
