# AI training buckets — real scope, per the #676 audit

*Captured 2026-09-07, per Alan's own direct request following the
`#676` orphaned-work audit ("scope both out into docs, so we know
where we are"). A real scoping pass only, matching this project's own
established discipline — define the real boundary before writing any
code, not after.*

**Updated 2026-09-07, same day, per Alan's own follow-up direct
request:** partition the buckets by area from the start (see "Real
structural decision" below) — added before any code existed, per this
same note's own "define the boundary before writing anything" rule.

## Where this comes from

`#510` (2026-08-25): a real, new roadmap item — "a real, structured
knowledge substrate teaching a future AI system the composition method
(`#509`) and the real, proven patterns already discovered, not just
'what does each cell do.'" `#511` clarified it as the already-
anticipated "layer 2" of `vm_ai_port_v1.py`'s own docstring. `#604`
(2026-09-02) later connected it to a second, genuinely different axis:
a card-decoupled virtual substrate (no real hardware ceiling) as a
richer generation space for the same idea, in both 2D and 3D. Nothing
was ever built or scoped into concrete steps on either axis — this
note is the first real attempt at that.

## The real, already-existing two-layer distinction (not this note's
own invention — `vm_ai_port_v1.py`'s own docstring, written 2026-08-**)

1. **Layer 1 — the port itself.** A clean, structured interface any
   driver (AI, script, human) can drive the VM through: compile (DSL
   or Python-AST) → real ICM v3 → running `SuperGrid` → real JSON
   introspection. Already real, already built, needs no changes for
   training buckets.
2. **Layer 2 — actually attaching a reasoning model to make decisions
   through that interface.** Explicitly named as separate, later, and
   optional. Training buckets are squarely LAYER 2's own concern —
   this note does not scope attaching or training any actual model,
   only the DATA a future layer 2 would need.

## Real structural decision, per Alan's own direct request, 2026-09-07: partition by area, not one monolithic bucket

Alan's own framing: split the training buckets into sections/areas so
that adding a new area is just a new bucket, and updating something
only means touching the one bucket it actually belongs to — not a
single combined corpus that has to be regenerated (or reasoned about)
as one unit every time anything changes.

**The real, existing seam this maps onto, not an invented one:**
`nano/tile_source_registry_v1.py` already lets a tile library
self-register (`register_tile_source(TileSource(...))`) — `#485`/`#487`
built this specifically so a new tile source can be added without
editing a central list. Walking THIS registry, rather than hand-listing
tile names in the exporter, means the bucket-per-area principle costs
zero new machinery: a new tile that registers itself is automatically
a new, separate bucket the next time the exporter runs, and an
existing tile's own updated behavior only ever regenerates its own
one file.

**Real, concrete area boundaries, each mapping onto something that
already exists as its own real unit in the code, not a fresh
taxonomy:**

1. **`tiles/`** — one bucket file per entry in `tile_source_registry_
   v1.py`'s own self-registering tile sources (Tier-0 primitives via
   `super_tile_library_v1.py`, plus DSP-wrapper tiles via `dsp_
   wrapper_tile_library_v1.py` — both genuinely self-register into the
   SAME generic registry today, confirmed directly). **Real correction
   made while building the first slice, 2026-09-07:** Tier-1 COMPOSED
   tiles (`sentinel`, `dual_threshold_monitor`, `twin_sentinel`,
   `dsp_add_and_hold`) do NOT live in this registry — `composed_tile_
   library_v1.py` is a genuinely separate library, confirmed directly
   against `tile_source_registry_v1.py`'s own docstring ("Tier-1
   composed tiles... remain super-tile-only sub-cells for now"). This
   was wrongly stated as already-unified in this note's own first
   draft; corrected once actually checked, not left silently wrong. A
   second, related correction: the loop tiles (`nano_loop_var`/`nano_
   loop_ctrl`) are NOT Tier-1 examples either, despite this note's own
   earlier draft implying they might be — confirmed directly, they're
   real Tier-0 entries in `super_tile_library_v1.py` (single-cell,
   `target="universal"`), already covered by `tiles/`. **Real Tier-1
   export is now built — see "Status" below.**
2. **`demos/`** — one bucket file per entry in `workbench_v1.py`'s own
   `DEMOS` dict. Genuinely different from `tiles/`: a demo is a
   complete, wired, runnable PROGRAM (possibly combining several
   tiles plus `expose()` wiring), not a single composable unit — worth
   keeping separate even where the same name appears in both (e.g.
   `sentinel` is both a tile and a demo).
3. **`frontend_compositions/`** — a real, honest, smaller area for
   constructions that exist only as inline code inside a compiler
   frontend, NOT as registered tiles — `select` and `icmp eq`/`ne` in
   `llvm_ir_frontend_v1.py` specifically, confirmed by direct check to
   have zero entries in the tile registry. This area needs a small,
   explicit list (it can't self-register the way `tiles/` does) until
   or unless each one is promoted to a real tile — which is already a
   standing, separate roadmap item. **A real, useful side effect worth
   naming:** promoting a frontend composition to a registered tile
   doesn't just serve the compiler — it also moves that pattern from
   this small, manually-tracked area into the self-registering
   `tiles/` area for free, one more real reason (beyond the compiler's
   own reuse) to do that promotion.
4. **A top-level lineage split, not yet needed but ready when it is:**
   everything above targets the OLD core lineage (the one with real
   DSL/tile-registry reachability today). The newer VIX Carrier/
   command-core generation (`CORES_AND_WRAPPERS_REFERENCE.md`'s own
   dedicated section) has no compiler or tile-registry reachability
   yet, so it genuinely has nothing to export today — but the moment
   it does, it becomes a new top-level lineage folder (e.g. `vix_
   carrier/tiles/`, `vix_carrier/demos/`), added alongside the
   existing one, touching nothing already built.

**What this buys, concretely, matching Alan's own stated reason for
asking:** a new tile/demo/composition never requires touching an
exporter's own hardcoded list (for `tiles/`, since it's registry-
driven) or, at worst, a small, isolated addition to one area's own
list (`frontend_compositions/`) — never a change to how any OTHER
area's buckets are produced. Updating one core's own behavior (a new
field, a fixed bug) only ever needs that one tile's own bucket file
regenerated, not the whole corpus re-verified.

## The real, open question this note exists to answer: what IS a
"training bucket," concretely

`#510`'s own framing ("the composition method... not just what does
each cell do") points at teaching PATTERNS, not just facts — but
"pattern" is still underspecified. Four real, genuinely different
shapes a bucket could take, not mutually exclusive:

**(a) Input/output behavior examples.** A fixed topology + config,
paired with its real observed behavior (a VM trace over N ticks given
a stated set of injections). Teaches cause-and-effect on THIS
substrate specifically.

**(b) Natural-language-to-DSL pairs.** A stated goal ("count injected
pulses and flag when they exceed a threshold") paired with the real
DSL source that implements it (e.g. `sentinel`) and its trace. Teaches
translation from intent to a real, working program — closer to a
conventional instruction-tuning shape.

**(c) A pattern-to-implementation reference corpus.** "Need a MUX →
here is `select`'s real 4-cell nano-gate composition, here is why it
works, here is the hop-count constraint that makes it correct." Closer
to a retrieval/reference corpus than training data in the strict
sense — teaches the COMPOSITION METHOD `#510` explicitly named, most
directly of the four.

**(d) Bulk synthetic generation.** Large volumes of valid, randomly or
systematically generated topologies (2D and, per `#604`'s own later
extension, 3D) plus their VM-computed behavior, at a scale no real
card's own physical ceiling could provide. Teaches general substrate
mechanics from volume rather than curated examples.

**This note does not pick one.** (c) is the most directly buildable
today, entirely from already-existing, already-tested code, with zero
new mechanism. (a)/(b) need a real decision about scale and curation
effort. (d) is real, separate, larger work — it depends on `#604`'s own
still-unbuilt card-decoupled virtual substrate generator, not just an
export step.

## What already exists to build on, not duplicate

- **`nano/workbench_v1.py`'s own `DEMOS` dict** (`#363`) — 6 real,
  working, hand-described programs (`simple_ram`, `adder_pair`,
  `sentinel`, `dual_threshold_monitor`, `twin_sentinel`,
  `python_ast_example`), each already carrying a name, a plain-
  language description, and real DSL/Python source. This is already,
  structurally, a tiny hand-curated proto-bucket in shape (b) — it
  just isn't exported anywhere outside the workbench's own `/demos`
  endpoint.
- **`nano/super_tile_library_v1.py`'s own Tier-0 + composed tile
  catalog** — `sentinel`, `dual_threshold_monitor`, `twin_sentinel`,
  the `select`/`icmp eq` LLVM-frontend compositions, the wired-OR MUX
  construction, etc. Each is a real, named, already-understood
  pattern-to-cells recipe — the direct, already-built raw material for
  shape (c), currently living as Python code and docstrings, not as a
  portable, model-consumable corpus.
- **`vm_ai_port_v1.VMSession`** — compile → run → introspect in one
  object; the real mechanism any exporter would drive to produce a
  genuine, verified VM trace for a bucket entry, rather than a
  hand-written or assumed one.
- **`nano/experimental_3d_grid_v1.py`** (`#520`) — real, honest prior
  art for `#604`'s own 3D extension: an already-built, deliberately
  separate, VM-only 6-cardinal toy model, explicitly not grounded in
  any real RTL. The natural (not novelty-for-its-own-sake) starting
  point if the 3D generation axis is ever picked up.

## A real, minimal first slice (not built), matching every other
`*_scope.md`'s own "smallest real step, not the full vision" discipline

Build a real EXPORTER, not a generator — and, per the area-partition
decision above, one that writes ONE FILE PER BUCKET, not one combined
corpus: walk `super_tile_library_v1.py`'s own tile registry (the
`tiles/` area, registry-driven, no hardcoded list) and `workbench_v1.
py`'s own `DEMOS` dict (the `demos/` area), and for each individual
entry emit its own canonical, model-consumable record — name,
plain-language description, real DSL source, the resulting ICM
record(s), and a real example VM trace (a fixed injection sequence run
through an actual `VMSession`, with the tick-by-tick observed output,
not an assumed one) — as its own file. This is shape (c)-plus-(b): it
reuses 100% already-existing, already-tested code, adds no new
mechanism, and produces a real, concrete first set of buckets — one
per tile, one per demo — instead of an abstract roadmap line or a
single monolithic file. It also gives a real, early answer to a
question every one of the four shapes above would eventually need
anyway: what does ONE record actually look like on disk (a JSON
schema), before deciding how many thousand of them to generate.

## Explicitly, honestly NOT scoped here

- **Actually attaching or training any model** (layer 2, per
  `vm_ai_port_v1.py`'s own docstring) — genuinely separate, later,
  optional work; this note only scopes the data such a layer would
  eventually consume.
- **`#604`'s own card-decoupled virtual substrate generator** — real,
  separate, larger work, a true prerequisite for shape (d)
  specifically, not for the pattern-library export slice above. Not
  started here.
- **The 3D extension** — real prior art exists (`#520`), but building
  on it is its own, separate decision, not implied by this note.
- **Any claim about which of shapes (a)-(d) is "correct"** — a real
  product/architecture decision for whoever eventually attaches layer
  2, not decidable from the VM side alone.

## Status

**Updated 2026-09-07, real code now exists — the first slice from
above is built:** `nano/training_bucket_export_v1.py` (`points.md
#681`) implements the `tiles/`/`demos/` exporter exactly as scoped,
including the real per-tile/per-demo file layout `#680` decided. 14
real tests, `tests/vm/test_training_bucket_export_v1.py`, all passing,
zero regressions (606 total). Genuinely still NOT built at that point:
Tier-1 composed-tile export (see the real correction above), a real
DSP-wrapper trace (metadata-only today, honestly), any bulk/3D
generation axis (`#604`), and anything in layer 2 (attaching a real
model).

**Updated again 2026-09-07, same day, per Alan's own direct request to
continue: Tier-1 composed-tile export is now real and built** (`points.
md #682`), in its own separate `tiles_composed/` bucket area (a
genuinely different registry/resolution mechanism from Tier-0's
`tiles/`, kept separate on purpose). Handles real nested composition
correctly (`twin_sentinel`'s own nested sentinels, confirmed via an
actually-executed multi-cell trace reaching identical real state on
both branches), real fan-out (`dual_threshold_monitor`), and correctly,
honestly detects when a composed tile transitively touches a
non-`super_records` bucket (`dsp_add_and_hold`'s own real DSP-wrapper
subcell) and falls back to static-metadata-only rather than faking a
trace. 13 more real tests (27 total in the file), 619 passed + 1
skipped overall, zero regressions.

**Genuinely still NOT built:** a real DSP-wrapper execution model (so
`dsp_add_and_hold` could get a real trace too, not just metadata), any
bulk/3D generation axis (`#604`), and anything in layer 2 (attaching a
real model to consume any of this).
