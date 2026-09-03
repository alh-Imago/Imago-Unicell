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

## Addendum 2 (2026-09-03): real prior art for exactly this problem already exists, in the old full-cell compiler -- not to be reinvented

Alan's own direct point, confirmed by checking, not assumed: the old
full-cell system's tile library (`fp_tiles.TileLibrary`, cited above,
source itself archived away per this project's own "concept survives,
code doesn't" discipline, but its real design documentation survives
in `archeology/shared/docs/software/COMPILER_TILE_CONFIG.md`) wasn't
just "known-good logic to assemble from" -- its real, concrete use was
premade artifacts that were ALREADY fully placed, timed, and verified,
so composing them meant inheriting solved timing for free rather than
re-deriving it per program.

**Direct, striking confirmation of `Addendum 1`'s own real conclusion
above, found in that old documentation, not rediscovered independently
this time:** the old placer had a NAMED, SYSTEMATIC rule for the exact
same collision `#611` found by tracing VM ticks by hand: "Group cells
so no two cells of the same dataflow DEPTH share a cluster (they would
fire the same cycle -> local wired-OR bus collision)." Not a hazard to
rediscover per program -- a real, general placement invariant, checked
automatically.

**A real, purpose-built primitive for exactly the "relay path length
must be engineered, not just present" problem `Addendum 1` named as
open:** a "TRANSIT PATH" -- dedicated relay cells for long-range
connections, with a formal, documented safety condition (suppress-
local on exit, a unique address per pass-through cluster, a free bus
cycle there). Not improvised per-program the way `#611`'s own west-
path relay was built -- a general, reusable primitive with its own
correctness contract, verified once.

**A real, mandatory verification gate before anything reached RTL, not
"compile and hope":** "Validate the result in the event-driven sim
(two-arrival firing + one-transaction-per-cluster-per-cycle +
simultaneous multicast) BEFORE generating RTL." The library's own
tiles had already been pushed through this gauntlet and archived as
done -- composing them meant inheriting that timing correctness, not
re-earning it.

**Real, honest implication for whenever general DAG routing is
actually built:** study `COMPILER_TILE_CONFIG.md`'s own real placer
rules (dataflow-depth grouping, cluster embeddability, the transit
primitive's safety condition) FIRST, as real, working prior art for
this exact problem. Real, confirmed correction to an earlier, over-
hedged version of this note: the cell model's own ADDRESSING
granularity differs (the old full-cell substrate was more finely,
loosely addressable; Unicell-S's coarser one-core-per-cell model packs
more function per physical location) -- but the underlying CELL is
confirmed the SAME, not just similar, per this project's own
documented design lineage. `unicell_automaton_v1.py`'s own header
states plainly that its same-cycle multi-direction OR-combine
behavior "recreates the FULL cell's free wired-OR N-way reduction on
these dedicated point-to-point wires" (`#153`) -- a DELIBERATE
re-creation of the old full-cell's own real wire-level physics, not an
independent rediscovery or a coincidental resemblance. The exact
hazard `#611` found by tracing VM ticks by hand (simultaneous arrivals
OR-combining) is consequently the SAME real physical behavior the old
placer's own "no two cells of the same dataflow depth share a cluster"
rule was written to avoid. Given the underlying wire-level cell physics
are confirmed identical, not merely analogous, the old placer's own
timing-closure discipline (depth-based grouping, the transit
primitive, the mandatory pre-RTL simulation gate) is the RIGHT real
starting reference for general DAG routing, not just a plausible one --
the real, open, honest question is how it maps onto Unicell-S's own
coarser addressing granularity (a "cluster" of finely-addressed full
cells versus a single coarser super-cell holding one active core), not
whether the underlying timing rules themselves still apply. Not scoped
further here -- a real, concrete next-look item for whenever general
routing is picked up, not a green light to start building it now.

## Addendum 3 (2026-09-03): a real, working LLVM IR frontend already existed -- extracted and read directly, per Alan's own "history hunt" request

`archeology/shared/docs/software/LLVM.md` (a real, dedicated design
doc) and `archeology/onion/old_llvm_frontend.onion` (a real, archived
source bundle) confirm the old full-cell system had a genuine, tested
LLVM IR frontend: `llvm_frontend.py` + `llvm_ir_mapper.py`, 31KB each,
using `llvmlite` -- the exact same library `#611` independently chose
today. Extracted and read directly via the now-initialized Onion
submodule (`tools/onion`, `git submodule update --init --recursive` +
a fresh C-extension build, per this project's own established
per-session ritual), not assumed from the design doc's own claims
alone.

**Real, honest scope comparison against today's `#611` slice:** the
old mapper supported a genuinely richer subset --
`add`/`sub`/`and`/`or`/`xor`, all six real `icmp` predicates (not just
equality), `select`, real CONDITIONAL BRANCHES, and real `phi` NODES
(loop-carrying values) -- everything `#611` explicitly deferred as
"real control flow, not attempted here." `LLVM.md` also documents real
float support (`fadd`/`fmul`/`fcmp`) and gives real, measured tile
sizes (e.g. `INT32_ADD`: Kogge-Stone, 482 cells, depth 10) -- concrete
evidence this wasn't a toy, it targeted real, sized, verified hardware
tiles.

**The real architectural fact this discovery surfaces, checked
directly against `TilePlacer`'s own real code, not assumed:**
`TilePlacer.place()`'s own docstring states plainly it "places a tile
into an address space by remapping its internal wire addresses to a
fresh region of the BUS." The old mapper's own `_lower_phi()`/
`_lower_br()` work by writing to and reading from abstract BUS
ADDRESSES -- a `phi` node's predecessors just write to a shared
address, a branch's `GS_SELECT` cell routes between two addresses.
**This is precisely why phi/branches were tractable there and remain
genuinely open here:** a bus-addressed model sidesteps physical
adjacency entirely -- any cell can reference any other cell's output
by address, with no relay-path timing to engineer at all. Unicell-S
has no bus, by deliberate design (`Addendum 2`'s own confirmed "same
cell" wired-OR mesh) -- every real timing hazard `#611` hit (OR-
collision, live-source contamination, arrival-order dependence) exists
SPECIFICALLY BECAUSE there is no bus to sidestep it with. The old
mapper's own bus-addressed approach does NOT directly transfer to
Unicell-S's own real architecture -- confirmed by reading the actual
code, not assumed from the design doc's surface-level operation table.

**What DOES transfer, real and useful, kept distinct from what
doesn't:** the mapper's own FRONTEND STRUCTURE -- walking LLVM IR
instruction by instruction, resolving SSA values through an
environment, dispatching by opcode to a per-construct lowering method,
handling all six `icmp` predicates via sign-bit extraction on a
subtractor tile -- is real, concrete, valuable reference for extending
`#611`'s own frontend into a richer LLVM IR subset later, independent
of the bus-vs-mesh question. A real, honest, additional finding: the
old mapper's own `_lower_load()`/`_lower_store()` exist, but checked
directly, are narrow -- a fixed, static stack-address alias (via a
single `GS_PASS` cell), not general indexed/addressed memory (no
array indexing, no pointer arithmetic) -- `LLVM.md`'s own "no memory
model... only pure arithmetic functions" claim holds up against the
real code, this isn't a case of the design doc understating a more
complete implementation.

**Real, honest scope: nothing built or ported here.** This is a real,
completed research pass, per Alan's own direct request -- the two
archives read and understood, the real distinction between "logical/
bus-addressed compiler structure" (transfers as a pattern) and
"physical cardinal-mesh timing closure" (needs the SEPARATE prior art
in `Addendum 2`, not this one) now stated precisely rather than left
to guess at. The old mapper's own frontend-structure patterns remain a
real, concrete reference for whenever `#611`'s own subset is extended
toward `icmp`/`select`/`phi`/`br` -- not attempted in this entry.

## Addendum 4 (2026-09-03): two real, verified leads for `eq`/`ne` and `select`, per Alan's own direct pointers -- confirmed against real code, not built yet

`#613` closed the four inequality `icmp` predicates but honestly
deferred `eq`/`ne` (no AND primitive) and `select` (the `branch` tile
doesn't fit). Alan pointed at two real mechanisms; both confirmed
directly against the actual RTL/tile code before being recorded here.

**`eq`/`ne`: nano already has a real, built-in AND.** Checked directly
against `unicell_gate_core.py` -- nano's real `topology` field selects
among 12 real NOR-decomposed boolean functions, including
`TOPO_AND = 0x007` (alongside `OR`/`NAND`/`NOR`/`XOR`/`XNOR`/etc.).
`super_tile_library_v1.py`'s own already-registered `nano_gate` tile
already exposes `topology` as a real, required param -- **no new tile
registration needed at all.** The real, concrete shape for `icmp eq`:
two `comparator` evaluations (`A>=B` and `B>=A`, both `#613`'s own
already-proven mechanism) AND'd together via one `nano_gate` cell with
`topology=TOPO_AND`; `ne` is the same composition negated (or, since
nano's own topology table includes `TOPO_NAND`/`TOPO_XNOR` directly,
possibly a single-cell answer rather than AND-then-invert -- a real,
concrete design question for whenever this is picked up, not resolved
here). **Real, open sub-question, not yet checked:** nano_gate's own
real two-arrival timing semantics (`nano_gate`'s own tile description:
"accepts input from ANY physically wired neighbor -- no upstream_mask
on this core at all") haven't been traced the way `#611` traced the
adder's -- whether the SAME OR-combine/continuously-live-contamination
hazards apply here, or a genuinely different real timing story, needs
real, direct tracing before trusting it, same discipline `#611` itself
established.

**`select`: the command cell (`cell_command_v1.v`) is a real, different,
heavier mechanism worth exploring properly, not a rushed fit.** Its
own real header comment explicitly names "a comparator's live match
result" as an example trigger -- confirming this isn't a stretch.
Real, honest distinction from a simple mux, stated plainly: this
DYNAMICALLY REPROGRAMS a target cell's own real behavior (a genuine
multi-cycle, 96-bit `program_in` transfer, `#123`'s own real design),
triggered by a condition -- not an instant per-value selection between
two already-computed results. Whether that's the right shape for
LLVM's own `select` semantics (which wants ONE value chosen from two,
not a cell's future behavior changed) is a real, open design question
-- staging cost, real timing, and whether it's even the right
conceptual fit (reprogram vs. route) all need real, direct
investigation before building anything, per Alan's own honest framing
("it can be a bit more in the staging, but it may help").

**Real, honest scope: nothing built here either.** Both leads are
real and verified against actual code (`TOPO_AND` genuinely exists and
is already exposed via `nano_gate`'s own param; the command cell's own
real trigger mechanism genuinely names a comparator match as an
example use) -- but neither has been traced through an actual VM run
the way every other real claim in `#611`-`#613` was. Real, concrete
next steps, in order of how close each is to `#613`'s own already-
proven pattern: (1) trace `nano_gate`'s own real two-arrival timing
directly (mirroring `#611`'s own tick-by-tick method) before trusting
an AND composition; (2) once that's solid, build `icmp eq`/`ne`; (3)
investigate the command cell's own real fit for `select` separately,
including its real staging/timing cost, before committing to it as
the right mechanism.

## Addendum 5 (2026-09-03): nano's own targeted reconfiguration is real and already built -- but doesn't reach the super-cell cores this frontend actually uses

Alan's own real memory, checked directly rather than assumed: the old
full-cell system used a rich, 256-opcode command bus (`cmd_bus[31:0]`,
`unicell64_v3.v`) with many dedicated, narrow opcodes for targeting
JUST PART of a cell's configuration (e.g. `CMD_TOPO_COMMAND_EMIT`
setting a single bit, topology presets avoiding a full reconfigure)
rather than always reloading everything.

**Real, precise finding: this capability wasn't simply lost -- it
survives, differently encoded, but ONLY on the nano core.** Checked
directly against `unicell_stripped_v1.v`'s own real `program_in`
protocol: each programming word is self-describing (`{3-bit ID,
16-bit data}`), covering 7 real, individually-addressable fields
(`PROG_ID_TOPOLOGY`/`ROUTING_MASK`/`CARDINAL_EDGE`/`PATTERN_LOW`/
`EQUAL`/`HIGH`/`DYN_ROUTE_EN`), plus a `COMPLETE` marker that can
commit-and-stay-cold for a genuine staged "pause, send more fields,
then arm" sequence -- the RTL's own comment calls this "a scalpel, not
a hammer." Confirmed the VM already models this faithfully
(`unicell_automaton_v1.py`'s own `CACell`, matching the RTL's real
`PROG_ID` table exactly) -- genuinely usable today, not a proposal.

**Real, precise limitation, checked directly against
`unicell_super_v3.v`, not assumed:** the super-cell shell's own
`cfg_valid` commits the entire 80-bit `SUPER_LATCH` ATOMICALLY, all at
once -- genuinely one full pass, no partial targeting. `program_in`
does exist at the shell level, but is wired ONLY to the nano sub-core
inside the shell -- NOT to the other seven real cores (`ram`/`adder`/
`accumulator`/`comparator`/`latch`/`sequencer`/`branch`), exactly the
ones this LLVM frontend and every Tier-0 tile actually use.

**Real, honest implication, directly relevant to `Addendum 4`'s own
`select`-via-command-cell lead:** today, even changing ONE field on an
adder or comparator requires reloading the whole 80-bit latch --
there is no cheaper, targeted path for the cores this frontend cares
about, only for nano. Whether a real, `PROG_ID`-style selective
mechanism could be extended to the super-cell's other cores is a real,
concrete, unexplored architectural question that would directly affect
the real staging cost of any reconfiguration-based approach to
`select` -- not scoped or attempted here, a real, separate design
question for whenever the `select` lead from `Addendum 4` is picked up
seriously.
