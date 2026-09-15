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

## Real, honest status

Another real design question feeding the same prerequisite `#736`
already named -- a VIX-compatible ICM format needs to exist before
either selection mode means anything, and this note narrows what that
format's own real shape should be, without deciding it. No RTL, no
format spec, no code. The central open question (per-instance
overrides) is the right next thing to work through, ideally against a
real, concrete example (a compiled CORDIC pipeline's own actual
record shape) rather than in the abstract.
