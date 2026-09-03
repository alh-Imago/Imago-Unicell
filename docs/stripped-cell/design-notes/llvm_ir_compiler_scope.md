# LLVM IR → Unicell-S compiler backend — real scope (CONCEPT, review before building)

*Captured 2026-09-02, per `points.md #547` (2026-08-31)'s own real,
long-standing intent, and `#603` (2026-09-02)'s own real observation
that this session's new VM-mirror + simulated-Walker infrastructure
(`#601`/`#602`) now gives it somewhere real to be built AND TESTED.
Same discipline as `composer_scope.md`/`workbench_scope.md`/
`unicell_s_dsl_and_compiler_scope.md`: this is a proposal to review and
correct, not a locked spec. Nothing below is built. Per Alan's own
explicit request at session pause -- run a scope now, not code, so
there's a clean stopping point rather than a half-finished build.*

## The real premise, recapped from `#547` (not re-derived here)

Every program, in any language, on any real processor, eventually
bottoms out at machine code against some real instruction set. The
real question `#547` asked: could Unicell-S's own DSL/tile system
serve as a genuine compilation TARGET for real programs generally, not
just hand-written DSL source?

Two real, mature, genuinely different fields answer "translate
compiled code onto different hardware," and only one applies:
**binary translation** (QEMU, Rosetta 2) needs a shared shape --
program counter, register file, addressed memory -- that Unicell-S
deliberately has none of. **High-Level Synthesis** (Xilinx/AMD Vitis
HLS, Intel's HLS Compiler) is the real field this belongs to instead:
sequential code in, spatial dataflow hardware out -- genuinely still
hard after decades of real investment, and the well-known limits are
exactly the parts of real programs with no natural spatial shape
(unbounded loops, recursion, dynamic allocation).

`#547`'s own concrete refinement: target **LLVM IR**, not raw machine
code or a full source language directly. LLVM IR is closer to SSA/
dataflow form than machine code (registers not yet allocated, control
flow not yet linearized into jumps) -- not coincidentally why Vitis
HLS is itself LLVM-based internally. And Alan's own added refinement:
rather than synthesizing novel hardware per IR construct (the
genuinely hard, still-open part of real HLS research), pattern-match
against this project's own ALREADY-PROVEN tile library -- "recognize
which known, verified pattern matches this piece of IR, instantiate
it" rather than "invent correct hardware from scratch."

## What already exists to build on -- and one real, honest correction to what that prior art actually covers

**The shared-IR, multi-frontend architecture is real and proven,
`#344`/`#348`.** Three structurally different frontends -- the DSL's
own grammar, a real Python-AST walk, and a real `pycparser`-based C
frontend -- all compile down to the same `program_ir_v1.ProgramIR` and
produce byte-identical output. A fourth frontend (LLVM IR) plugging
into the same `ProgramIR` is architecturally the same move already
made three times, not a new pattern.

**A real, honest correction, checked directly before writing this
note, not assumed from the frontend count alone:** none of those three
existing frontends compile GENERAL PROGRAMS. Checked directly against
`c_frontend_v1.py`'s own header -- its entire real grammar is
`place(name, tile, row, col)` / `field(name, key, value)` calls inside
one `void PROGRAM_NAME(void)` function. It uses C's own SYNTAX as a
container for the exact same declarative placement recipe the DSL and
Python-AST frontends already express -- no expressions, no arithmetic,
no control flow, no variables in any general-programming sense. All
three existing frontends are real, working, and genuinely
language-agnostic in the sense `#547`/the long-range note meant -- but
"language-agnostic" so far has only ever meant "agnostic about which
SYNTAX declares the same placement recipe," not "compiles arbitrary
imperative programs." `ProgramIR` itself is deliberately thin: a flat
list of placements, each a name + tile reference + row/col + fields --
confirmed directly against `program_ir_v1.py`'s own header, which
states plainly it carries nothing about expressions or control flow.
**This is the real, load-bearing fact this whole scope note has to be
honest about: the "actual programming" gap `general_purpose_
programming_long_range_note.md` already named (2026-08-16) has not
been closed by anything built since, including this session's own new
infrastructure.** LLVM IR is exactly the kind of input that's FULL of
that gap's own hardest content (SSA variables, `phi` nodes, branches,
loops) -- this backend can't sidestep those open questions the way the
existing three frontends implicitly did by never having them at all.

**What this session's own new infrastructure genuinely does add, real
and concrete:** `VMSession.from_man()` (`#601`) means a candidate
lowering can be loaded into a session that genuinely, checkably
corresponds to a real card's own real N-cell layout, not a
free-floating guess. The simulated Walker (`#602`) means that loaded
design's own actual realized topology can be independently discovered
and verified against what the lowering intended, rather than trusted
on faith. Real, useful for the one question below that's actually
answerable by running something -- not a solution to the open
questions themselves.

## The real, load-bearing open questions, restated precisely (not resolved here)

Unchanged from `general_purpose_programming_long_range_note.md`
(2026-08-16), because nothing built since has touched them:

- **What does an LLVM IR *value* (an SSA register) map to** on a
  substrate where a "variable" is a specific physical cell, not an
  addressable slot? A real, concrete, tractable-sounding first answer:
  one SSA value -> one placed cell holding it, decided once at compile
  time (a real register-allocation-shaped problem, not solved here).
- **What does an LLVM `br`/loop construct compile to** with no program
  counter? Compile-time loop unrolling is the obvious first answer for
  a genuinely BOUNDED loop -- and LLVM already has real, mature
  unrolling passes (`opt -loop-unroll`) that could do this BEFORE this
  project's own compiler ever sees the IR, meaning the frontend itself
  might never need to handle a loop construct at all for a real first
  version. Data-dependent or unbounded loops remain the same real,
  possibly-architectural dead end the long-range note already named --
  not attempted here.
- **What does an LLVM `phi` node mean spatially?** The old full-cell
  compiler's own real answer to `if`/`else` -- evaluate both branches,
  MUX-select the output -- is real prior art directly relevant here
  (`compiler_int32.py`, cited in the long-range note): a `phi` node is
  exactly a MUX over predecessor-block values, and Unicell-S already
  has real muxing via routing. This one open question looks genuinely
  tractable, unlike the loop/memory questions above.
- **Real addressed memory** (an LLVM `alloca`/`load`/`store` to a
  dynamically-computed address) has no real answer anywhere in this
  project yet, full-cell or Unicell-S. Out of scope for a first real
  pass, stated plainly rather than glossed over.

## A real, concrete, bounded first target, not "solve general programs"

`#547`'s own refinement already named the honest, tractable version:
**a genuinely bounded, well-behaved program subset** -- static loop
bounds (or no loops at all, post-unrolling), no recursion, no dynamic
allocation. This is not a hypothetical shape invented for this note --
it's exactly the real, already-standing FlowTrix/LBM demo's own
computational structure (fixed lattice sites, purely local collision
arithmetic, one-hop streaming that the fabric's own topology already
provides for free, no dynamic control flow at each site at all). A
real LLVM IR backend's first real target should be code that already
looks like that -- not a general C compiler pointed at Unicell-S, a
backend for the specific, bounded shape this project's own real demos
already need.

## A real, honest pipeline sketch, marking what's new versus reused

```
source language (C, Rust, etc.)
    -> real, existing compiler front half (clang/rustc/etc,
       EXTERNAL tooling, not this project's own concern)
    -> LLVM IR, already unrolled/optimized (opt -O2 -loop-unroll, etc.)
    -> [NEW, genuinely unsolved] SSA-VALUE-TO-CELL ALLOCATION PASS --
       decide which physical (row,col) each live SSA value occupies;
       the real, hard, novel part this note doesn't resolve
    -> [NEW] PATTERN MATCHER -- recognize known, already-verified
       tile-library shapes (arithmetic ops -> adder/comparator/etc,
       phi -> a real MUX composition, per Alan's own real refinement)
    -> program_ir_v1.ProgramIR   [REUSED, unchanged -- the same real
       shared IR every existing frontend already targets]
    -> dsl_compiler_v1's own real resolve/place/emit backend
       [REUSED, unchanged] -> IcmV3File
    -> VMSession.from_man() + simulated Walker (#601/#602)
       [REUSED, this session's own real new infrastructure] --
       load the lowering against a REAL card's real layout, discover
       its own actual realized topology, verify it matches intent,
       all before any real hardware is involved
```

Everything below the IR line is real and already built. Everything
above it -- the two `[NEW]` stages -- is the actual, unsolved content
of this whole idea. Real, honest scale check: this is where the
genuine, novel engineering effort lives, not in wiring a fourth
frontend into an already-proven multi-frontend architecture.

## Real, practical tooling check, done now rather than assumed later

Confirmed directly in this environment, matching `c_frontend_v1.py`'s
own "confirmed already installed, not assumed" precedent, this time
the inverse finding: `llvmlite` (the real, standard Python binding for
consuming LLVM IR) is **NOT currently installed** here, and no
`clang`/`llvm-as`/`opt` binaries are available either. `pycparser` (the
existing C frontend's own real dependency) IS already installed. A
real, concrete, small first step whenever this is picked up: confirm
`pip install llvmlite` (or an equivalent pure-Python `.ll`-text parser,
avoiding a full LLVM toolchain dependency) is actually viable in this
environment before any real parsing code is written -- the same
"confirm the dependency is real before committing to the approach"
discipline the C frontend's own header already modeled.

## A real, low-risk suggested first step, matching this project's own "smallest test first" discipline

Don't design the SSA-allocation pass or the pattern matcher in the
abstract. Take ONE small, already-unrolled, real LLVM IR snippet
(hand-written or produced by `clang -S -emit-llvm -O2` from a trivial
C function doing a handful of adds/compares, no loops, no memory) and
hand-trace what pattern-matching it against the real, existing Tier-0
tile library would actually look like -- on paper or in a throwaway
script, before writing any real frontend/parser code. If that trace
reveals the SSA-value-to-cell allocation question is genuinely
tractable for straight-line code, that's the real, concrete green
light to start building the pattern matcher for real; if it reveals a
new, unforeseen blocker, that's found cheaply, before any real
investment.

## Real, honest, explicitly NOT scoped here

- Real, unbounded or data-dependent loops, recursion, dynamic memory
  allocation -- the same real, possibly-architectural open questions
  `general_purpose_programming_long_range_note.md` already named,
  restated, not solved.
- The separate "FPGA design-side" idea (generating bespoke, per-program
  synthesizable Verilog rather than configuring the fixed, already-
  synthesized shell) -- a genuinely different long-range thread, per
  that same note's own real distinction; this backend targets
  `ProgramIR`/ICM configuration only, same as every existing frontend.
- Any TRIX-system domain-typing awareness -- a real, separate, later
  concern per the long-range note's own fourth section.
- Any real card-capacity/ALM-budget enforcement beyond `#601`'s own
  already-real topology checking -- per-cell ALM cost isn't settled
  enough across shell versions to build a hard budget gate on top of
  this yet, same real boundary `#601` itself already drew.

## Not yet done, stated plainly

No parser, no SSA-allocation pass, no pattern matcher, no code at all
-- a real scoping pass only, matching every other `*_scope.md` note in
this directory. The real, load-bearing open questions above (variable
mapping, loop handling, `phi`-as-MUX) are the right place to start
whenever this is picked up for real -- in isolation, via the small,
concrete experiment above, not a ground-up design effort.

## Addendum (2026-09-03, `points.md #611`): the real, novel content is TIMING, confirmed by building it, not just theorized

`#611` built the real, restricted first slice this note recommended
(one function, one block, `add`/`sub`, a linear chain) -- and getting
it CORRECT, not just compiling, required discovering three real,
previously-undocumented facts about the two-arrival firing model, each
found by tracing actual VM ticks:

1. **Simultaneous arrivals bitwise-OR together**, not captured as
   separate operands -- two neighbors offering on the same tick
   collide into one combined value.
2. **A continuously-live source keeps re-contaminating even behind a
   single-shot "shielding" relay** -- once the relay drains and
   re-opens (its own real, documented behavior), it recaptures from
   the still-live source behind it and re-delivers, racing against
   whatever the real second operand should have been. The robust fix
   was one-time `VMSession.inject()` delivery instead of a
   permanently-broadcasting constant.
3. **A given layout's own arrival order is a fixed physical fact, not
   a semantic label** -- `in_a`/`in_b` don't mean anything until you
   know which one actually arrives first in THIS layout, and getting
   it wrong silently reverses non-commutative operations like
   subtraction.

**The real, sharpened conclusion this proves, not just asserts:** the
genuinely hard, novel content of this whole idea is less "which tile
matches this IR instruction" and more **compile-time TIMING analysis**
-- deciding not just where each value lives, but exactly when it will
physically arrive relative to every other value it needs to combine
with, and deliberately engineering that timing (relay-path padding,
one-time delivery, operand-order accounting) rather than assuming
correct placement is enough. For the linear-chain case, this was
tractable by hand, once traced. **A real DAG makes this materially
harder, not just bigger:** every point where two independently-
computed values converge on the same consumer needs its own real
timing analysis, and relay paths of different lengths converging on
one cell need deliberate padding so arrivals aren't accidentally
simultaneous OR accidentally out of the intended order. This is closer
to real hardware timing closure / scheduling than to ordinary software
compilation -- the SSA-allocation pass this note already named as
"genuinely unsolved" is now confirmed, by direct evidence, to really
be a **placement-AND-TIMING** allocation problem, not placement alone.
Worth remembering precisely when general DAG routing is picked up
next: the real design question isn't just "which relay cells route
value X to consumer Y," it's "which relay path LENGTH gets X to Y at
EXACTLY the tick the rest of the schedule requires."
