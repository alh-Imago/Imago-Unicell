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

**The real design question above, now given a real, concrete answer,
per Alan's own direct follow-up (2026-09-16) — not fully settled, but
genuinely resolved in shape, not left open the way it was above.**

**The real, load-bearing fact this answer rests on: the workbench
always runs from a known, fixed point inside a git clone.** A user
who clones the repository and starts the workbench gives it a real,
concrete anchor — `nano/workbench_v1.py`'s own real, running location
— from which every shared component's own real path is already a
short, stable, KNOWN relative hop, confirmed directly rather than
assumed: `../fpga/verilog` (core RTL), `../docs/stripped-cell` (design
notes, `CELL_GOTCHAS.md`), `super_tile_library_v1.py`/`vix_tile_
library_v1.py` (both already siblings of the workbench itself). This
is already the same real pattern this whole project's own test suite
already uses (`os.path.join(os.path.dirname(__file__), "..", ...)`
throughout) — Alan's own proposal formalizes an already-proven pattern
into a real, first-class mechanism, not a new one.

**The real, concrete mechanism, per Alan's own direct proposal:**
- **A real path-tree file** — a real, structured manifest recording
  where each real, shared component lives, relative to the workbench's
  own location, not duplicated as scattered, independent path
  constants across every consumer. If the repo's own real structure
  ever changes (a directory renamed or moved), this ONE file gets
  edited once, rather than every individual reference needing to be
  found and fixed independently — the same real, single-source-of-
  truth discipline `#734`'s own stale-dependency-list lesson already
  taught this project, applied here to filesystem layout instead of a
  dependency list.
- **A real path-picker/folder-creation UI added to the frontend** —
  letting a user either CREATE a new project (name it, choose or
  accept a real, default location) or OPEN an existing one (point at
  a real, existing project folder). Real, honest, worth naming
  directly: since the workbench is an HTTP-based frontend, not a
  native desktop application, a real "path picker" here almost
  certainly means a real, validated TEXT field (a real path the
  server-side process can check exists/is writable), not a native
  OS-level file-browser dialog — a real, small but genuine UI-
  architecture constraint worth stating plainly rather than assuming
  a native-app-style picker is available.
- **The path-tree file itself stays editable**, per Alan's own direct
  point — if a user's own real setup ever DOES move something (a
  relocated clone, a reorganized shared-library location), the one
  real file recording relative paths can be corrected directly,
  rather than the whole mechanism breaking silently.

**Real, honest, still-open pieces, even with the shape now resolved:**
whether the path-tree file lives once, globally, per-workbench-
instance (the more natural reading of "relative to the workbench," and
the simpler real design), or could ever need to be genuinely per-
project (not indicated by anything Alan's said, but worth naming as a
real, deliberately-excluded alternative rather than silently assumed
away); the real, exact schema the path-tree file itself would use;
and the still-real, separate question `#754`'s own original note
already named and this doesn't resolve — whether a project should ever
pin a specific SHARED-LIBRARY VERSION (not just its real location) —
Alan's own proposal answers "where do I find it," not "which version
of it," and the two are genuinely different real questions.

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

**Update, 2026-09-16, per Alan's own direct follow-up:** Part 4's own
real, open "how does a project reach shared components" question is
now resolved in SHAPE, not just named — a real path-tree file,
relative to the workbench's own known, fixed location inside a git
clone (the same real pattern this project's own test suite already
uses throughout, formalized rather than invented), plus a real path-
picker/folder-creation UI for creating or opening a project. Real,
narrower open pieces remain (the exact schema, whether the path-tree
file is global-per-workbench or ever per-project, and the real,
separate, still-unresolved question of pinning a shared-library
VERSION rather than just its location) — see the updated Part 4
above for the real, full detail.

**A real, separate, worthwhile observation, made directly by Alan and
recorded here rather than lost:** the eventual user manual for
everything this session's own work (and the sessions before it) has
accumulated — the hierarchical ICM format, the tile libraries, the
priority core, the DAG-convergence/pattern-library mechanism, MAN/
project workflows, the Composer — is genuinely going to be a
substantial volume of real documentation work in its own right. Not
scoped or attempted here; a real, honest acknowledgment that this is
real, additional work still ahead, distinct from any of the building
this note or its siblings describe.
