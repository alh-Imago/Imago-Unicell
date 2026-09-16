# Free-format design targets, core selection, and real project workspaces (Alan/Claude, 2026-09-16)

*Per Alan's own direct proposal: on the real, existing MAN-creation
page, a checkbox moving it from a real card to a free-format design,
using cell count rather than ALM/LUTs as the size metric, with a
per-core selection (defaulting to all, deselectable) that everything
downstream — the workbench, the Composer — then works from. This adds
a real, new layer of complexity: persistent, folder-based "projects,"
storing project-specific work while still reaching back to shared
components and libraries. A scoping pass only, nothing built.*

## The real, existing starting point, checked directly before proposing anything

**`nano/frontend_v1.py`'s own `page_man()` is the real page Alan is
referring to** — a real, working HTML form (`points.md #557`) that
calls `tools/man_generate_v1.py`'s own `build_man()` directly. Checked
directly: it currently REQUIRES `card_id`, `part`, `alm_total`,
`dsp_total`, `clk_pin`, `led0_pin`, `led1_pin` — exactly the same real
fields `#745` already named as the one, narrow, remaining obstacle to
generating an "arbitrary size" MAN file: "a real, deliberate choice
for a human hand-authoring a REAL card's own file... a genuine, minor
obstacle to generating an 'arbitrary size' MAN file directly from the
command line." **Alan's own checkbox proposal is precisely the real,
concrete UI fix `#745` already predicted would be needed** — not a new
idea layered on top, the actual, specific mechanism that gap was
always going to need.

**A real, important naming collision found and worth stating
directly, so it doesn't get assumed away later:** `nano/frontend_
v1.py` already has a method called `create_project()` — checked
directly, it's a real, one-shot, thin wrapper around `project_
assemble_v1.assemble()`, generating a single Quartus output folder for
one specific build. **This is NOT the same real thing as the
persistent, multi-session project workspace Alan is now proposing** —
the existing name is already taken by something narrower. Whatever
this new concept is called in the real, eventual build, it needs its
own real name, distinct from the existing `create_project`.

## Part 1: the checkbox — free-format vs. card, cell count vs. ALM/LUT

**The real, concrete UI change:** a checkbox on `page_man()` toggling
between two real modes:
- **Card mode (unchanged, today's real behavior):** the existing,
  full form — a specific, real device, with `alm_total`/`dsp_total`
  and real pin assignments, exactly as `#557` already built it.
- **Free-format mode:** hides/disables the card-specific fields
  (`part`, `dsp_total`, `clk_pin`, `led0_pin`, `led1_pin`) and replaces
  `alm_total` with a real, direct **cell count** field instead. This
  matches `#741`'s own already-established, honest precedent exactly:
  `check_against_man()`'s own real scope is deliberately "a cell-count
  sanity check, NOT a precise ALM estimate," since real, measured
  per-core ALM costs don't exist for every core type yet (`mul`/
  `priority` have none at all). Free-format mode using cell count
  directly, rather than pretending to derive an ALM-equivalent
  estimate it can't honestly make, is the SAME real, deliberate
  honesty this project's own checking code already commits to
  elsewhere — not a new standard, applying the existing one to a new
  surface.

**Real, direct implementation path, already proven to work end to
end:** `#745` already confirmed `build_man(card_id=..., alm_total=N,
...everything else None)` produces a real, valid, loadable MAN file,
verified directly against `load_man()`/`check_against_man()` with zero
changes needed anywhere else. A real "free-format" checkbox on
`page_man()` is a thin, front-end-only translation of that already-
proven call shape — no new backend mechanism, a real UI convenience
for something the underlying code already does correctly.

## Part 2: per-core selection — the real, direct connection to VIXb and the tile library

**Alan's own proposal: a checkbox per real core type, defaulting to
all selected, deselectable.** This is the real, concrete FRONTEND for
exactly what `#735`/`#736` already scoped and left as real, open
design work — the "carrier build system" idea (`#726`'s own original
note, `#735`'s own real Option B recommendation): select which cores a
design needs, build a carrier sized to that set. All-selected-by-
default is the real, "fully loaded" case (today's actual, existing,
already-verified `unicell_vix_carrier_v1.v`, holding all 11 real
cores); deselecting some is the real "trimmed" case `#735`/`#736`
already discussed at length but never built a generator for.

**Real, honest, load-bearing dependency, not glossed over:** this
checkbox's own real, useful behavior — actually producing a smaller,
correctly-wired carrier when cores are deselected — depends entirely
on `#735`'s own still-unbuilt generator (Option B: a Python-side RTL
generator, not yet written). Without that generator existing, "which
cores are selected" can be recorded (a real, useful piece of project
metadata on its own, feeding `check_known_gotchas()`-style validation
and the pattern-library work from `#752`) but can't yet change what
carrier RTL actually gets built or simulated. **A real, honest
sequencing fact:** this checkbox is buildable and useful today as a
real, recorded SELECTION; it only becomes a real, functional TRIMMING
mechanism once `#735`'s own generator exists.

**A real, new field the MAN schema doesn't have at all today,
confirmed by checking `man_generate_v1.py` directly:** nothing in the
current schema records which cores are available/selected. A real
`cores_selected` (or similar) field would need to be added — a small,
concrete, well-scoped schema extension, not a large one, but a real
one nonetheless.

## Part 3: "everything else... works off of that" — the real, load-bearing implication

**Alan's own direct framing: once created, the workbench (already
does) and the Composer (etc.) all work off the same, single project
definition.** Checked what this actually requires: the workbench's own
`load_man()`/`check_against_man()` machinery (`#734`/`#741`) already
treats a MAN file as a real, authoritative description of the target
— extending it to also carry `cores_selected` means every consumer
(workbench, Composer, the tile library resolve/place step, the
pattern-library escalation ladder from `#752`) has ONE real, shared
place to read "what does this design's own target actually support"
from, rather than each tool needing its own, separately-maintained
notion of it. This is the same real, single-source-of-truth discipline
`#734`'s own real lesson (a stale, hand-maintained dependency list)
already taught this project the hard way — applied here to a genuinely
new kind of fact (core availability) before it has the chance to go
stale the same way.

## Part 4: real projects — a genuinely new, additional layer of complexity, named honestly

**Alan's own direct point: this adds real complexity, moving into "the
realms of projects"** — a new folder per project, storing project-
specific work inside it, while still reaching back to shared
components and libraries. This is a real, additional, separate design
question from Parts 1-3 above, not a natural, free consequence of
them — worth scoping as its own real thing.

**What would live IN a project's own folder, a real, first-pass
list, not exhaustive:** the project's own MAN file (card or free-
format, with its own real `cores_selected`); any real, hierarchical
ICM structure files (`icm_vix_v1.IcmVixFile`, `#747`) the project's
own designs use; any real, saved diff/state files (`#747`'s own
`save_state`/`load_state` mechanism) capturing a particular run's own
current values; whatever the Composer's own eventual real output
format turns out to be, once it exists.

**What must stay SHARED, not duplicated per project, per Alan's own
direct point ("reaching back to the shared components and library"):**
the tile libraries (`super_tile_library_v1.py`, `vix_tile_library_
v1.py`) — one real, project-independent registry of known-good
placement recipes, not copied into every project folder; the pattern
library from `#752`, once it exists — the whole point of that
mechanism is a shared, growing corpus, which duplicating per project
would directly undermine; the core RTL itself (`fpga/verilog/`) — one
real, shared source of truth for what a `_v4c` core actually is,
never project-local.

**The real, genuinely open design question this creates, not resolved
here:** HOW does a project's own folder "reach back" to shared
components mechanically? Two real, honest options, not decided
between here:
- A real, relative or absolute PATH reference stored in the project's
  own metadata (simple, but fragile if the shared library's own
  location ever moves relative to a given project).
  - A real, versioned reference (which real version/commit of the
    shared tile library or pattern library this project was built
    against) — more robust, but real, additional bookkeeping the
    simpler path-only approach doesn't need.
- Real, honest, unresolved: whether a project should be allowed to
  pin a specific shared-library version at all, or whether it should
  always resolve against whatever the shared library's own current
  state is (simpler, but means a shared-library change could silently
  change what an existing project's own design resolves to later).

## Real, honest, open questions overall — not resolved here

- **The existing `create_project()` naming collision** needs a real,
  deliberate resolution before any of this is built — reusing the name
  for a fundamentally different, broader concept would be genuinely
  confusing, not just cosmetically awkward.
- **The free-format checkbox (Part 1) is real, small, and buildable
  today**, with zero new backend mechanism needed — the most
  immediately actionable piece of this whole note.
- **The core-selection checkbox (Part 2) is buildable as a real,
  recorded selection today**, but only becomes functionally meaningful
  once `#735`'s own carrier generator exists — a real, honest
  sequencing dependency, not a blocker to building the UI/schema piece
  now if that's useful on its own.
- **The real "project" folder structure (Part 4) is the most
  substantial, least-scoped piece here** — a real, separate design
  pass of its own is warranted before building anything, given how
  many real, existing pieces (MAN files, ICM structures, saved states,
  shared libraries) it would need to organize coherently.

## Real, honest status

A scoping pass, connecting Alan's own new proposal directly to real,
already-existing code (`page_man()`, `create_project()`) and real,
already-scoped prior work (`#735`/`#736`'s carrier build system,
`#741`/`#745`'s own MAN-file honesty precedent, `#747`'s own ICM/state
mechanisms, `#752`'s own pattern library). No RTL, no schema changes,
no UI code, no project-folder structure built. The real, most
immediately actionable next step, if picked up: the free-format
checkbox alone (Part 1) — small, well-understood, and useful on its
own even before the core-selection and project-workspace pieces are
resolved.
