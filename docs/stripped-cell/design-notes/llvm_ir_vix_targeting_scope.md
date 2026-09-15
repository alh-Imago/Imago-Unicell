# The LLVM IR side, scoped for real before Alan gets back (Alan/Claude, 2026-09-15)

*Per Alan's own direct ask before heading out: look at the LLVM side
and see what's needed there -- item 1 on `#744`'s own roadmap, named
"a whole other session by itself." Checked the actual, current code
throughout rather than assumed from the existing scope documents alone
-- several real, previously-unstated facts surfaced. Nothing built.*

## The real, current, confirmed end-to-end pipeline

Traced directly, not assumed: **both** the LLVM IR frontend
(`nano/llvm_ir_frontend_v1.py`) and the DSL frontend compile down to
the SAME shared, frontend-agnostic `ProgramIR` (`nano/program_ir_v1.py`
-- deliberately pulled out of the DSL parser specifically so a second
frontend, like LLVM, could plug in without duplicating logic). That IR
is then handed to `nano/dsl_compiler_v1.py`'s own `compile_program_ir()`
-- one, single, shared backend, not two separate ones -- which
resolves each placement against a real tile from `nano/super_tile_
library_v1.py`, places it, and emits the result.

**Confirmed directly, not assumed from a docstring:** `compile_
program_ir()`'s own real return type is `v3.IcmV3File | v4.IcmV4File`.
`super_tile_library_v1.py`'s own header states its purpose explicitly:
"a tile here is a placement recipe for `icm_v3.IcmV3Record`s." **The
entire pipeline, both frontends, one shared backend, is scoped to the
OLD lineage's flat ICM format only.** Nothing anywhere in this stack
touches VIX Carrier, the `_v4c` core family, or the hierarchical ICM
format (`#737`-`#742`) at all -- a real, complete gap, not a partial
one.

## Three real, separate pieces of work -- confirmed distinct, not one job

**1. New tiles for the VIX/`_v4c` core family.** `super_tile_library_
v1.py` only defines tiles for the old lineage's 9 core names (`nano`,
`ram`, `adder`, `accumulator`, `comparator`, `latch`, `sequencer`,
`branch`, plus `subtractor` as a fixed-config variant of `adder`).
`mul` and `priority` (`#724`-`#731`) have no tile at all, not even a
stub. **A real, positive finding, checked directly, worth building
on:** every `SuperTileSpec` already carries a real `target` field with
three existing values (`"universal" | "super-only" | "nano-full"`,
confirmed in the dataclass itself and used for real, live dispatch
logic -- "only `target='universal'` tiles can be placed on a plain
Unicell-n grid"). **Adding a fourth value (`"vix"`, or similar) is a
natural, already-anticipated extension of a mechanism that already
exists, not a new kind of mechanism.** The real, separate work per
tile is still substantial, though: each `_v4c` core's own real port/
field shape needs checking against the actual RTL the same way the
existing tiles' own header comments show real, hard-won facts were
confirmed (the adder's shared `in_a`/`in_b` field, nano's missing "in"
port) rather than assumed -- `#734`'s own real finding that `project_
assemble_v1.py`'s own `CORE_REGISTRY` describes the OLD lineage only,
not `_v4c`, is the exact same gap showing up here a second time.

**2. The backend's own real emit path.** `compile_program_ir()` needs
a genuinely new code path to produce the hierarchical ICM format
(patterns + design map + diff, `#737`-`#741`) instead of (or alongside)
`IcmV3Record`s. **Real, honest, sequencing-critical finding: this
piece is currently BLOCKED, not just unstarted.** `#736`'s own named
prerequisite still stands -- there is no formal, written spec for the
hierarchical ICM format, only a real, working prototype
(`nano/examples/hierarchical_icm_prototype_loader.py`, explicitly
built to test the DESIGN, not to be production code, per its own
docstring and `#740`-`#742`'s own repeated, honest framing). A real
backend emit path can't be built against a format that isn't pinned
down yet -- formalizing the format (turning `#737`-`#742`'s own three
real, tested examples into an actual written spec) is real,
prerequisite work for this item specifically, not a parallel task.

**3. The frontend's own real language-coverage gaps -- confirmed
genuinely orthogonal to items 1 and 2, not blocked by or blocking
them.** `llvm_ir_frontend_completion_scope.md`'s own existing Tier A/
B/C inventory (bitwise ops, general DAG data flow, general branching,
bounded loop unrolling, floating point, real addressed memory, function
calls) is entirely about WHAT LLVM constructs can be expressed at all
-- checked directly, "vix"/"VIX" appears nowhere in that document.
**A frontend that could target VIX perfectly would still only express
the same narrow set of real programs it does today** (a single
function, one straight-line block or one narrow 3-block counting
loop, fixed compile-time arguments) unless Tier A/B/C work also
happens. These are two real, separate axes of incompleteness --
*what can be said* and *what it compiles to* -- worth keeping
distinct rather than treating "finish the LLVM side" as one
undifferentiated task.

## Real, honest sequencing, given what's actually blocked

1. **Formalize the hierarchical ICM format spec** (real, prerequisite
   work for item 2, drawing directly on `#737`-`#742`'s own three
   real, tested examples rather than starting from the abstract design
   notes alone -- the small relay chain, the parallel reduction tree,
   and the CORDIC pipeline between them already exercise patterns,
   `(row,col,face)` links, per-instance overrides, and the advisory
   check under real, different conditions).
2. **Build the backend's own new emit path** against that spec, once
   it exists -- can begin in parallel with item 3 below, since the two
   don't depend on each other.
3. **Add VIX/`_v4c` tiles**, extending `super_tile_library_v1.py`'s
   own already-existing `target` mechanism with a new value -- can
   start any time, independent of items 1/2 above, since tile
   definitions are data the backend resolves against, not backend
   logic itself; genuinely useful even before the backend can emit the
   hierarchical format, if a resolve/place dry-run against the new
   tiles is worth doing early to catch problems in the tile
   definitions themselves.
4. **Frontend language-coverage work** (`llvm_ir_frontend_completion_
   scope.md`'s own already-tiered inventory) proceeds entirely
   independently of 1-3 -- real, useful, orthogonal work whenever
   picked up, on the OLD lineage or the new one, without waiting on
   any of the above.

## Real, honest status

A scoping pass, not a build plan. No RTL, no tile code, no backend
changes, no format spec written. The real, most load-bearing finding:
item 2 (the backend's own hierarchical-ICM emit path) cannot start
until the format itself is pinned down in writing -- that's the one
genuine, hard dependency in this whole roadmap item; everything else
(tiles, frontend language coverage) can proceed independently of it
and of each other.
