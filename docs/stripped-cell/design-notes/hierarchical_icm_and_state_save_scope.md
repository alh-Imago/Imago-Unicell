# A hierarchical ICM: named repeating structures, and the separate question of saved state (Alan/Claude, 2026-09-15)

*A direct, real extension of `#736`'s own named prerequisite -- "a
VIX-compatible ICM format needs to exist before Mode B means anything"
-- prompted by Alan's own follow-up: compiled LLVM IR output will
genuinely have repeating structures, and the flat, one-record-per-cell
format doesn't capture that at all. Two genuinely separate real
questions here, kept separate on purpose: (1) how the STATIC PROGRAM
STRUCTURE should represent repetition, and (2) how a SAVED RUNTIME
SNAPSHOT should relate to that structure. Nothing built.*

## Real motivation, checked against what actually produces repetition

This is a genuinely well-grounded concern, not a hypothetical --
loop unrolling and repeated inlined patterns are exactly what a real
compiler backend produces, and this project already has a concrete,
real example of the shape involved: `#733`'s own CORDIC design
possibility is precisely "the same N-cell stage, repeated N times."
Today's flat `IcmV3File` would represent that as N × (cells per
stage) individual, fully-spelled-out records, with the repeated
SHAPE itself present nowhere in the file -- only inferable by a reader
noticing the pattern by eye.

## Real, important distinction to make before designing anything: this is not (only) a compression problem

**Worth naming directly, since it changes what "solving" this even
means:** this project already has a real, working, generic solution
to "repeated byte patterns bloat a file" -- `tools/onion`'s own real,
built LZ77 and Huffman implementations. Running Onion over a flat ICM
file would genuinely shrink it, today, with zero format changes.
**But that's not actually what Alan's own proposal is asking for.**
Generic compression finds repeated BYTES; it doesn't give a human or a
tool a name for "this is a CORDIC stage," doesn't let a compiler
regenerate just one structure's own definition without touching every
instance, and doesn't make the file's own real shape legible by
reading it. The two are complementary, not competing -- a hierarchical,
named-structure ICM could still be Onion-compressed afterward for raw
size, same as any other file. This note is about the SEMANTIC,
structural question, not the size question.

## The real design questions a "header, structure map, then full map" format actually raises

**1. Are instances of a named structure ever byte-identical, or do
they need real, per-instance overrides?** This is the single most
important open question, and the honest answer is almost certainly
"they need overrides." A real N-stage CORDIC pipeline's own middle
stages might be identical, but the FIRST stage needs external input
wiring where the others have an upstream neighbor, and the LAST needs
external output wiring the others don't. A structure format that only
supports pure, verbatim repetition doesn't match real compiler output;
one that supports per-instance parameter overrides (row/col placement
at minimum, likely also which cardinal direction is "external" for
edge instances) is a real, bigger design than a pure template stamp.

**2. How does a structure declare its own external connection points?**
The same real problem Verilog module ports solve. This project already
has the right building block for the answer: a structure's own "ports"
are naturally just "which of its own internal cells' cardinal
directions are exposed to whatever's outside the structure" -- the
existing `upstream_mask`/`downstream_mask` convention every core
already speaks, one level up. Real, undecided: whether a structure
needs its OWN, separate port-naming layer, or whether "port N of
structure X" can just mean "the north face of the cell at relative
position (r,c) within X," addressed directly rather than through an
extra layer of naming.

**3. Does nesting go more than one level deep?** A structure containing
other named structures (real, recursive composability) is more
powerful than a flat "structure = list of raw cells" -- but genuinely
harder to load correctly, and it's honestly unclear whether real
compiler output needs more than one level. Worth resolving with a real
example from an actual compiled program shape, not decided
abstractly here.

**4. The real, direct precedent already in this codebase, worth
reusing rather than re-inventing:** `minimum_shell_version()`
(`#736`'s own finding) already demonstrates the right pattern for
deriving a real SUMMARY from records -- scan the actual placed cells,
compute what's needed. A structure-aware format's own "header listing
structures used and their counts" is the same kind of derived summary,
one level up: scan structure INSTANCES instead of raw cells. This
doesn't have to be a hand-maintained field that can go stale (`#734`'s
own real lesson) -- it can be computed from the structure-instance
list itself, the same way `minimum_shell_version()` is computed rather
than stored.

## The real, separate question: how does a runtime snapshot relate to this?

**The genuinely important thing to get right here: program STRUCTURE
and runtime STATE are two different, orthogonal concerns, and keeping
them separate is the simpler choice, not the more complex one.** A
named structure is, by its own definition, a SHARED template used by
multiple instances -- attaching one specific run's own current latch
values directly into that shared definition doesn't make sense, since
different instances of the same structure will hold different real
values at any given moment. The values have to live somewhere else,
addressed per real cell, not baked into the shared shape they're an
instance of.

**Alan's own second option -- the original structure file, unchanged,
plus a separate diff file holding only the runtime values that
differ -- is the right one, and it's checked directly against what
this format already has, not just a preference:** `IcmV3Record.cell_id`
already exists today as a real, stable, per-cell identifier,
independent of row/col or which structure (if any) a cell belongs to.
A diff file keyed by `cell_id` -> current value works cleanly whether
the underlying structure file is flat (today) or hierarchical (this
note's own proposal) -- the ONE real requirement is that `cell_id`
stays a genuinely stable, unique identifier for every real cell,
including cells that live inside a named structure instance, not just
top-level loose cells. That's a real, necessary property to preserve
through any redesign, not an incidental detail.

**Real, honest reasons this is the right choice, not just the
simpler-sounding one:**
- The structure file never needs regenerating just because a
  simulation ran for a while -- it's the real, unchanging program.
- Multiple independent runs of the SAME program produce multiple,
  small diff files, not multiple copies of the whole structure.
- A loader that already knows how to apply "cell_id -> value" doesn't
  care whether the structure underneath is flat or hierarchical --
  the diff mechanism and the structure-representation question are
  genuinely independent, which is real, direct evidence this is the
  right separation of concerns, not just a simpler-sounding one.

**Real, honest complexity this doesn't remove, stated directly:** the
loader DOES have to be able to resolve "cell_id X, wherever it actually
lives in a possibly-nested structure hierarchy" back to a real, live
cell to apply a diff value to -- a real, necessary piece of work
either way, not avoided by choosing the diff approach, just isolated
to one well-defined operation (`cell_id` lookup) rather than smeared
across "how do I even represent state inside a template."

## Real, honest, open questions -- not resolved here

- **Per-instance override shape** (question 1 above) is the real,
  central unresolved design question -- everything else is
  comparatively mechanical once this is answered.
- **Whether `cell_id` needs a real, structured naming convention**
  once cells live inside possibly-nested structure instances (e.g.
  `cordic_pipeline_3.stage_7.adder` vs. a flat, opaque string) --
  matters directly for how easy the diff file is to read/write by
  hand, not just by tooling.
- **Whether the loader needs to materialize the FULL flat cell list in
  memory regardless of the file's own hierarchical representation**
  (likely yes, for the VM at least, since `SuperGrid`/`VixCarrierGrid`
  already model a flat grid) -- meaning the hierarchical format's own
  real value is at the FILE level (human/tooling legibility, compiler
  generation convenience), not necessarily a runtime representation
  change. Worth stating plainly rather than implying the VM itself
  needs restructuring too.
- **Onion's own real role, if any, stays genuinely orthogonal** -- a
  real, separate, later decision about whether to compress the
  resulting file for storage/transfer, not something this format
  redesign needs to accommodate directly.

## Real, honest status (superseded by the concrete shape below, kept for its own real history)

Another real design question feeding the same prerequisite `#736`
already named -- a VIX-compatible ICM format needs to exist before
either selection mode means anything, and this note narrows what that
format's own real shape should be, without deciding it. No RTL, no
format spec, no code. The central open question (per-instance
overrides) is the right next thing to work through, ideally against a
real, concrete example (a compiled CORDIC pipeline's own actual
record shape) rather than in the abstract.

## Alan's own concrete shape (2026-09-15), and the real question it resolves

**A real, direct answer to this note's own central open question, not
a new one: every real cell shape becomes a pattern, even one used
exactly once.** This removes the per-instance-override problem
entirely, rather than solving it -- there is no shared template with
per-instance variation to design, because a pipeline's first stage,
middle stages, and last stage simply become three real, separate
patterns (say, `pattern_1`, `pattern_2` used 30 times, `pattern_3`),
each internally fixed and exact. The real cost of this simplicity is
honest and worth naming: a design with many genuinely distinct shapes
produces many real pattern entries, some used only once -- but that's
still a real, structural improvement over today's fully flat format,
since even a single-use "pattern" is a named, legible unit instead of
an anonymous cluster of records, and any shape that DOES repeat still
collapses to one real definition plus N cheap references.

**Alan's own real, four-part shape, worked through directly:**

```
Header
    Cores used
    Cell Count

Pattern 1
    Layout by cell type (pattern map)
Pattern 2
    Layout by cell type (pattern map)
...

Design Map
    Location start (0,0)   {relative offsets}
        Pattern 1 > N > Pattern 2
                  > S > Pattern 45
                  > W > Data entry point
                  > E > BLANK
...

Diff Section
    Cell ID  Latch(0)  &01100110000111
...
```

**Real, direct mapping onto what's already established, confirmed
before sketching JSON:** the Design Map's own N/S/E/W links between
pattern INSTANCES is the same real cardinal-adjacency model every
single cell in this whole architecture already uses, one level up --
not a new addressing scheme, a genuine reuse of the project's own
central idea ("topology is computation") at the pattern-instance
level instead of the cell level. The header's own "cores used"/"cell
count" stays a real, DERIVED summary (matching `minimum_shell_
version()`'s own precedent, `#736`) rather than a hand-maintained
field -- computed by walking the pattern definitions and the design
map's own instance list, not written by hand and left to go stale.

**A real, concrete JSON sketch, illustrative not final, to make this
tangible enough to find real problems in:**

```json
{
  "format_version": "icm-v4-hierarchical",
  "header": {
    "cores_used": ["ram", "adder", "mul"],
    "cell_count": 47
  },
  "patterns": {
    "pattern_1": {
      "cells": [
        {"cell_id": "c001", "rel_row": 0, "rel_col": 0,
         "core": "ram", "core_config": {"...": "..."}, "io_name": "data_in"}
      ]
    },
    "pattern_2": {
      "cells": [
        {"cell_id": "c010", "rel_row": 0, "rel_col": 0,
         "core": "adder", "core_config": {"...": "..."}},
        {"cell_id": "c011", "rel_row": 0, "rel_col": 1,
         "core": "mul", "core_config": {"...": "..."}}
      ]
    }
  },
  "design_map": {
    "origin": {"row": 0, "col": 0},
    "root_instance": "inst_1",
    "instances": {
      "inst_1": {"pattern": "pattern_1",
                  "links": {"N": "inst_2", "S": "inst_45", "W": null, "E": "BLANK"}},
      "inst_2": {"pattern": "pattern_2", "links": {"S": "inst_1"}}
    }
  },
  "diff": {
    "c010": {"latch_0": "0b01100110000111"}
  }
}
```

**Real, honest questions this concrete shape surfaces, sharper than
the abstract version could:**
- **Which cell, inside a multi-cell pattern, does a cardinal link
  actually attach to?** `"Pattern 1 > N > Pattern 2"` is clear when a
  pattern is one cell; `pattern_2` above has two. A real link needs to
  name which of `pattern_2`'s own internal cells sits at the real,
  physical boundary the link crosses -- either an explicit per-pattern
  port declaration (a real, small addition: `"ports": {"S": "c010"}`
  inside the pattern definition itself) or a convention (e.g. "the
  cell at the pattern's own geometric edge facing that direction"),
  checked against real, actual multi-cell pattern shapes before
  picking one.
- **Are "Data entry point" and "BLANK" real, first-class instances of
  something, or a genuinely different, third kind of link target?**
  Given "even one cell becomes a pattern," a real, single, named
  external entry point plausibly IS just another one-cell pattern
  (`io_name` already exists on a per-cell basis, per the current
  format) -- but "BLANK" (no connection at all in that direction) is
  categorically different, a real absence rather than a reference to
  anything. Worth keeping these conceptually distinct in the eventual
  spec: a link is either a real pattern-instance reference, or
  genuinely null, not a third kind of magic string doing double duty.
- **Are the Design Map's own offsets relative to the immediately-
  linked pattern, or all relative to the one real, global origin?**
  Alan's own "(0,0) {locations given as relative offsets}" reads as
  the former -- each pattern instance's own real position is computed
  from whatever it's linked FROM, not restated in absolute grid
  coordinates. Real, genuine benefit if so: the whole design can be
  moved to a different real starting position by changing exactly one
  value, without touching every instance -- worth confirming directly
  before committing to it, since it changes how a loader has to walk
  the structure (a real, necessary graph traversal from the root
  outward, not a flat pass over independent absolute coordinates).

**Real, honest status, updated (superseded again below):** the central
open question from this note's own earlier draft (per-instance
overrides) is genuinely resolved by Alan's own "every shape is its own
pattern" rule -- a real step forward, not just a restatement. What
remains open is narrower and more concrete: pattern-internal port/link
attachment for multi-cell patterns, the real distinction between a
null link and an external-entry-point link, and confirming relative-
vs-absolute placement semantics. Still no RTL, no format spec, no
code -- but the real shape is close enough now that the next useful
step is probably trying this JSON shape against one real, actual
compiled example (the CORDIC pipeline this whole line of notes keeps
returning to) rather than refining it further in the abstract.

## A real, important clarification (2026-09-15) that simplifies the loader's own job significantly

**The two open questions above (per-cell link attachment, `NC` vs. an
entry point) are genuinely resolved by Alan's own direct follow-up,**
using exactly the (row, col, face) precision this note's own JSON
sketch was missing:

```
Pattern 45 (0,1,N) > Pattern 1 (2,1,S)
Pattern 42 (2,1,S) > NC
```

Read directly: Pattern 45's own cell at its local (0,1), specifically
its north face, connects to Pattern 1's own cell at its local (2,1),
its south face. `NC` ("not connected" -- borrowed directly and
deliberately from real, standard hardware/schematic notation, not
invented) replaces "BLANK" as the genuinely different, categorical
case: a real absence of any link, not a reference to anything.

**The real, important clarification underneath this, confirmed
directly rather than assumed, and it changes what kind of mechanism
this whole layer actually is:** the connection notation and the
placement list (`at (0,0) Load Pattern 1`, etc.) are NOT what makes
cells actually connect. The real, authoritative wiring mechanism is
exactly the one that already exists today and needs no reinvention --
each cell's own `core_config` bits (`upstream_mask`/`downstream_mask`,
or nano's own `routing_mask`/`cardinal_edge`). **This layer's own real
job is human-readable documentation and machine-checkable
cross-referencing** -- confirming that a given placement's own real,
configured connection bits actually agree with what the design says
should be connected, catching a real mismatch (a cell placed as if it
connects north, but its own real `upstream_mask` doesn't actually
listen north) rather than driving the connection itself.

**This is directly, precisely the same real pattern this project
already trusts elsewhere, not a new kind of mechanism:**
`tools/project_assemble_v1.py`'s own `discover_instantiated_modules()`/
`check_dependency_compatibility()` (`#590`) already does exactly this
shape of thing -- a real, useful, best-effort ADVISORY check, never
the authoritative source of truth, which stays the actual RTL/config
bits either way. The same real, honest framing applies here directly:
this connection notation is a real, valuable sanity check a loader (or
a separate validator) can run, catching likely mistakes before they
become silent, wrong behavior -- but the cell's own real `core_config`
bits remain what actually determines behavior, exactly as today.

**Real, honest consequence, worth stating plainly: this genuinely
simplifies the loader's own job, removing a real complexity concern
raised (then withdrawn) earlier in this same conversation.** A loader
does NOT need to solve a real, potentially-ambiguous constraint/graph-
layout problem to derive placement from the connection graph -- the
placement list (`at (X,Y), Load Pattern N`) gives real, direct
coordinates already; the connection notation is there to CHECK those
coordinates and the actual configured `core_config` bits agree, not to
COMPUTE anything. A mismatch is a real, catchable, advisory warning
(matching `#590`'s own real, established warning shape: never a hard
block, since the real compile/RTL remains authoritative either way),
not a silent failure and not something requiring a real solver.

## Real, honest status (superseded below -- the design was actually tried)

The design's own real shape is now settled enough to be genuinely
useful: patterns (even single-use ones) as the one, uniform unit;
explicit `(row,col,face)` addressing for real, precise cross-checking
of connections; `NC` for a genuine absence, distinct from a reference;
direct, explicit placement coordinates (not solver-derived); and the
whole connection layer understood correctly as advisory, human/
tooling-facing documentation, not the authoritative wiring mechanism
(which stays exactly what it already is today, per-cell `core_config`
bits). Still no RTL, no format spec, no code. The real next step
remains the same: try this shape against one real, concrete compiled
example before writing anything resembling a spec.

## Real, actual result of trying it (2026-09-15) -- a small, real example, ported through a real prototype loader, into the real, existing VM

**A real, small, concrete example built** (`nano/examples/small_relay_
chain.icm-hier.json`): a linear, 8-cell chain -- a single-use `entry`
pattern, a real 2-cell `relay` pattern used three times (specifically
to exercise multi-cell port attachment, `#739`'s own central question),
and a single-use `exit` pattern. Real `ram` cores throughout (flowing
mode), the only core type needed to test the format's own real
mechanics without needing to also stand up new core semantics.

**A real, small prototype loader written** (`nano/examples/
hierarchical_icm_prototype_loader.py`) -- flattens the hierarchical
document into real `IcmV3Record` objects (direct placement, no
solving, matching `#739`'s own clarification exactly), runs the real
advisory connection check described above, then hands the flattened
records to the real, existing `VixCarrierGrid` to actually execute.
Reused the real VM's own existing, already-proven API throughout
(`IcmV3Record`, `VixCarrierGrid.inject()`/`.tick()`) -- nothing new
built in the VM itself, confirming this note's own earlier prediction
that the hierarchical format's real value sits at the file level, not
as a VM runtime change.

**What actually came out, run directly, not assumed:**
```
Flattened 8 real cells from 3 patterns (5 placements).

Advisory connection check: all declared connections agree with the
real, configured core_config bits.

Real VM grid built: 8 cells at [(0,0)...(0,7)]

Injecting 0x2A at the real 'input' cell (0,0)...
Tick 8: real 'output' cell now holds 0x2A (valid=True)

Real diff-section snapshot (cell_id -> current value): {'exit_1.exit_c0': '0x2A'}
```
The injected value propagated correctly through all 8 real cells in 8
real ticks (one hop per tick, exactly as a flowing-mode relay chain
should behave) -- the whole pipeline (hierarchical JSON -> flattened
records -> real VM execution) worked end to end on the first real,
complete attempt.

**A real, deliberate negative test, not just a happy-path run:** broke
`relay`'s own pattern DEFINITION directly (cleared one cell's own
`downstream_mask`), then re-ran the advisory check. It correctly
flagged all three real, affected connections (`relay_1`, `relay_2`,
`relay_3` -- every instance using the now-broken shared pattern), not
just one. This is real, concrete, positive evidence for the whole
point of pattern-based reuse: a real mistake in one shared definition
is caught consistently everywhere it's used, rather than needing
independent discovery in N separate, flat places.

**Real, honest limits of this prototype, stated directly:** this
loader is deliberately minimal -- no `NC` handling, no io_name-based
external injection beyond the one hardcoded example, no nested
patterns, no diff-file loading (only a snapshot demonstrated, not a
real round-trip save/restore). It exists to test the DESIGN's own real
shape against a real VM, not as a draft of the real, eventual loader.

**Real, honest status: the design has now been tried against a real,
working example, not just reasoned about.** Every real mechanic
discussed across `#737`-`#739` -- patterns (including single-use ones),
multi-cell port attachment, direct (non-solved) placement, the
advisory connection check (both confirming a correct design and
catching a real, deliberate break), and a `cell_id`-keyed diff
snapshot -- worked, on the first complete attempt, against the real,
existing VM. Still no RTL, no format spec, no production loader. The
real next step: a genuinely bigger example (the CORDIC pipeline this
whole line of notes has pointed toward) to find whatever this small,
deliberately simple case was too small to surface.
