# The LLVM IR frontend — real completion scope, 2026-09-07

*Captured per Alan's own direct request: scope shift-opcode support
now that the hardware exists (`#683`/`#684`), then scope what it would
take to bring the whole frontend to real completeness, including what
"compiling itself" would actually mean. A scoping pass only — nothing
built here.*

## Part 1: `shl`/`lshr`/`ashr` — real, concrete, mostly buildable now

**Real status update, 2026-09-07, same day: `shl`/`lshr` are now
built and verified.** Everything below this note was the original
scoping; the real build followed it closely, with one real design
correction found empirically (see `points.md #690`): the addon chain
applies at OFFER time, not by mutating a cell's own stored register,
so the lowering needs a real second "sink" cell to capture the
shifted value into something directly readable, matching every other
opcode's own convention -- not just the single relay cell originally
imagined. `ashr` remains unsupported, exactly as scoped, with a real,
specific diagnostic naming the hardware gap rather than a generic
"unsupported opcode" message.

**The good news: the shift AMOUNT fits the frontend's existing
restriction perfectly.** LLVM's `shl`/`lshr`/`ashr` take the value to
shift and a shift amount; this frontend already requires an
instruction's own second operand to be a compile-time constant
(matching `add`/`sub`'s own real restriction) — a shift amount is
exactly that shape already, no new restriction needed.

**The real, missing link, confirmed directly, not assumed:** `place()`
(`super_tile_library_v1.py`) already accepts an `addon_config` dict —
the mechanism is real and callable today. But nothing between a
`PlaceIR`'s own `fields` and that call ever reaches it: `dsl_compiler_
v1.py`'s field-routing logic recognizes exactly two buckets, a tile's
declared ports and its declared params — there is no third "addon"
bucket, and no `SuperTileSpec` field for a tile to declare a fixed or
caller-supplied addon setting. This is the same real gap `shift_fine_
addon_rollout.md` (`#684`) already named for the compiler in general;
`shl`/`lshr` are the first real, concrete thing that needs it closed.

**Real, minimal design to close it:**
1. A new, reserved field-name convention — `"addon.<name>"` (e.g.
   `"addon.shift_amt"`, `"addon.shift_fine"`, `"addon.direction"`,
   `"addon.shift_en"`) — recognized generically in `dsl_compiler_v1.
   py`'s field-routing step, for ANY tile, not tied to a tile's own
   declared ports/params (matching the real RTL fact that `addon_
   config` is core-independent, on the periphery, per `#310`).
2. `compile_llvm_ir()` lowers `shl %x, N` (or `lshr`) to: place a
   `ram_flowing` relay cell in the chain (the exact same pattern
   already used for the "west0"/relay cells elsewhere), with `addon.
   shift_en=1`, `addon.direction` (0=left/`shl`, 1=right/`lshr`), and
   `addon.shift_amt`/`addon.shift_fine` computed by decomposing `N`
   (0-31) into the coarse+fine split: pick the largest real coarse tap
   `{0,1,2,4,8,12,16,20,24,28}` that's `<= N`, and `fine = N - coarse`
   — always 0-3, by construction (no gap between consecutive real taps
   exceeds 4).

**`ashr` is a REAL, separate gap, not just more compiler work.**
Confirmed directly against `shift_fine_addon_v1.v`'s own real
implementation: it performs a plain LOGICAL shift, zero-fill on both
directions — there is no sign-extension mechanism anywhere in the
addon chain. `lshr` is fully served by the existing hardware; `ashr`
is not, and building it would mean real, new RTL (a sign-aware variant
of the fine/coarse shifters, or a separate addon stage entirely) —
genuinely a hardware gap, not something the compiler side can work
around. Worth a conscious decision whenever this is picked up: build
the real hardware, or scope `ashr` as explicitly unsupported (a clear
diagnostic, same discipline as every other deferred opcode) until it
is.

**Real, honest estimate:** `shl`/`lshr` together are a small, well-
bounded piece of work — one new field-routing bucket (reusable for
anything else needing addon access later, e.g. `nibble_mask`/`invert`
support that would follow the identical pattern) plus one real
opcode-lowering case, no new hardware needed. `ashr` is blocked on a
real, separate hardware decision.

## Part 2: what "really complete" would mean — a real gap inventory,
tiered by what kind of work each one actually is

This deliberately builds on, and does not re-derive, `general_
purpose_programming_long_range_note.md`'s own already-real prior-art
findings (the old full-cell compiler's proven MUX-as-branch and
loop-unrolling answers) — this section organizes the CURRENT LLVM
frontend's own specific remaining gaps against that same real
prior art, tiered by how hard each one actually is.

### Tier A — mechanical, buildable now, no new architecture needed

- **Bitwise `and`/`or`/`xor`.** Confirmed trivial: `nano_gate` already
  supports AND/OR/XOR (and NAND/NOR/XNOR) as real, existing topology
  values — this is a smaller version of exactly what `select`/`icmp_
  eq` already proved out. The easiest real opcode addition available.
- **`shl`/`lshr`** — scoped above, Part 1.
- **`mul` by a compile-time constant.** Real, buildable via shift-and-
  add — decompose the constant into its set bits, shift the dynamic
  operand left by each set bit's position (now genuinely possible,
  Part 1), sum the results. The real catch: summing more than two
  partial products is a small, bounded instance of the NEXT tier's own
  problem (fan-in from multiple results, not a 2-operand chain) — a
  real, natural bridge between "mechanical" and "needs DAG routing,"
  not a clean Tier-A item on its own once a constant needs 3+ set bits.

### Tier B — real, hard, but with proven prior art to draw from

- **General DAG data flow** (an operand referencing an EARLIER, non-
  immediately-preceding result — e.g. `t3 = add t1, t2`). This
  frontend's own docstring already names this as "the actual hard,
  unsolved part" `#610` identified. Real, necessary building block for
  almost everything else in this tier and the multi-set-bit `mul` case
  above — relay-cell routing between non-adjacent cells, a genuine,
  nontrivial placement/routing problem, not a small addition.
- **General branching (`if`/`else` outside the one narrow loop
  shape).** Real, proven prior art exists and directly transfers: the
  old full-cell compiler's own answer was a spatial MUX — evaluate
  both branches unconditionally, then select the real output, exactly
  the same real mechanism `select` (`#686`) already builds and this
  frontend already lowers to. Extending from "select between two
  compile-time-resolved values" to "select between two live, computed
  sub-expressions" is real, incremental work on an already-proven
  idea, not a new one.
- **Bounded loop unrolling** (a `for`/`while` with a compile-time-
  known, fixed trip count, as opposed to the one narrow hardware-
  loop-ring shape already supported). Also real, proven prior art:
  the old compiler's own documented approach. Genuinely more
  mechanical than architecturally novel — repeat the lowering N times
  at compile time.
- **Nested loops / loops with more than one live variable.** Harder
  than the above — the existing 4-cell bounded-loop-ring hardware
  (`nano_loop_var`/`nano_loop_ctrl`/adder-or-subtractor/`ram_flowing`)
  was built and proven for exactly ONE induction variable; a second
  live loop variable or a nested loop needs a real, new topology
  question answered (does each loop variable get its own independent
  ring, wired to share a common exit signal? Does nesting mean
  physically nesting rings in space?) — not decided or attempted
  anywhere in this project yet.
- **Floating point** (moved here from Tier C, 2026-09-07 — see the
  real correction below). `math_frontend_design.md` has a real,
  worked-out design: float32/float64 via bit-manipulation chains on
  plain INT32 cells (5 cells for `FLOAT32_ADD`, 4 for `FLOAT32_MUL`,
  etc.), reusing the same paired-cell mechanism already built for
  signed 64-bit integers. A real, bounded, mechanical build once
  general `mul`/bitwise ops exist — not a new architectural question.

### Tier C — genuinely open architectural questions, not just
"more compiler work" (named, not resolved, in the long-range note
already)

- **Real addressed memory** (arrays, pointers, `load`/`store`,
  `getelementptr`). The long-range note's own real, load-bearing
  question stands unanswered: "what does a variable even mean" on a
  substrate where every cell is a fixed physical location, not an
  addressable slot? A real RAM core exists (`ram_flowing`/`ram_
  constant`), but neither offers anything like indexed addressing —
  this is a genuine, unsolved substrate-level question, not a backlog
  item.
- **Unbounded / data-dependent loops** (trip count not known at
  compile time). The long-range note already flags this as "may be a
  real architectural dead end for this kind of substrate, not just a
  hard compiler problem" — a no-program-counter, fixed-topology fabric
  has no obvious place to put a runtime-varying iteration count at all.
- **Function calls, especially recursion.** No call stack, no return
  address mechanism exists or has been designed. A non-recursive,
  always-inlined "function" is really just Tier B's own DAG-routing
  problem wearing a different name; genuine recursion runs straight
  into the same unbounded-loop question above.
- **Floating point.** **Correction, 2026-09-07: not actually
  unscoped.** `archeology/shared/docs/software/math_frontend_design.
  md` has a real, worked-out design -- float32/float64 via bit-
  manipulation chains on plain INT32 cells (5 cells for `FLOAT32_ADD`,
  4 for `FLOAT32_MUL`, etc.), reusing the SAME paired-cell mechanism
  already built for signed 64-bit integers (the two-arrival model
  naturally synchronizes a mantissa pair). Never built, but a real,
  bounded, Tier-A/B-shaped design, not a genuine architectural
  question -- moved out of Tier C on that basis.

## Part 2.5: the LaTeX-equation path — a real, concrete, reachable
target once Tier B lands, added 2026-09-07 per Alan's own direct
question

**Real prior art confirms this is architecturally sound, not just
plausible.** `archeology/shared/docs/software/math_frontend_design.md`
already scoped exactly this idea: `SymPy → Discretiser → Pattern
Matcher → Tiler → Wirer`, feeding the same real `compiler_int32`/IR
pipeline `llvm_ir_frontend_v1.py` directly descends from.
`trix_bridge_archaeology_refnotes.md` confirms this was MathTrix's
own real origin — the first Trix design, the one the whole family grew
out of.

**A concrete, satisfying connection to what's already built:** that
old design's own "Path to Implementation" names its main gaps as "MUL
tile (future), SHR tile (future)" — `SHR` is `lshr` (`#690`, built the
same day this note was updated). Its own 1D Laplacian stencil pattern
(`u_new[i] = u[i] + alpha*(u[i-1] - 2*u[i] + u[i+1])`, `alpha=1/4` as a
power-of-2 shift) is now genuinely, actually buildable.

**What's still needed, concretely, beyond `shl`/`lshr`:**
1. **General `mul`** (Tier A/B boundary above) — the other named gap.
2. **General DAG/tree routing** (Tier B) — the real gating item.
   Almost any real equation combines two independently-computed sub-
   expressions (`(a+b)*(c+d)`, `a*b + c*d`) — not an edge case, the
   common case.
3. **A real LaTeX parser** — genuinely new, currently unbuilt work,
   separate from backend lowering: turning `\frac{a+b}{c}` syntax into
   something the compiler can consume.
4. **Fixed-point scaling** — already solved on paper (Q16 format,
   `math_frontend_design.md`'s own real strategy), just needs building.

**Why this stays real and reachable, not Tier C:** a single equation
evaluation needs no loops or memory at all. Applying a stencil across
a grid of N points is compile-time-bounded unrolling (N known ahead of
time) — the same real, proven technique Tier B's own bounded-loop-
unrolling item already names. Genuinely open Tier C territory (real
integrals, unbounded summation, data-dependent iteration) would need
separate, further work, but ordinary algebraic equations and fixed-
size numerical stencils — exactly what the old design targeted — never
touch it.

## Part 3: "if it can get to a point it can compile itself" — what
this would actually mean, stated honestly rather than left ambiguous

**The literal reading doesn't hold up, and it's worth being direct
about why, not just deferring it as "future work."** `llvm_ir_
frontend_v1.py` is an ordinary Python program — it parses text, builds
data structures, recurses, allocates memory dynamically, calls
functions with returns. Every one of those is either genuinely
unsolved (real addressed memory, function calls/recursion) or a real,
architectural open question the project's own long-range note already
flags as possibly unanswerable on this substrate (unbounded,
data-dependent control flow — which any real parser or compiler
fundamentally needs, since it must handle inputs of unknown, varying
size and shape). This isn't "we haven't built it yet" the way `shl`
is — it's the same category as Tier C above: the substrate is
deliberately a CONFIGURATION architecture, not a general-purpose one
(`unified_carrier_scope.md`/`architecture.html` both already say this
plainly), and a self-hosting compiler is about as general-purpose a
program as exists. Chasing literal self-hosting would mean either
solving Tier C in full first, or discovering along the way that some
piece of it is a genuine dead end for a topology-is-computation
substrate — which would itself be a real, valuable, honest finding,
just not a near-term deliverable.

**A real, meaningful, MUCH more reachable version of the same idea,**
worth naming as an actual milestone instead: compile something with
real, nontrivial structural complexity comparable to a SMALL, FIXED
piece of a compiler's own core logic — a bounded expression evaluator
(parse a fixed-depth arithmetic expression into `add`/`sub`/`mul`
operations, no recursion, no variable-length input), or a small,
fixed-size state machine (a handful of states and transitions, unrolled
rather than driven by a real program counter). Both are genuinely
useful, real proof points that don't require solving memory or
unbounded control flow at all — they'd exercise Tier A/B (DAG routing,
branching-as-MUX, bounded unrolling) thoroughly, which is itself a
real, honest measure of how far the "narrow slice" from today has
actually grown. This is offered as a real, alternative milestone, not
a substitute answer to the literal question — the literal one stays
open, correctly flagged as Tier C, not quietly redefined away.

## Status

Design/scoping note only. Nothing built. Real, concrete next step
identified (Part 1: `shl`/`lshr` via a new "addon." field-routing
bucket) whenever picked up; Parts 2/3 are a map for prioritizing
everything past that, not a commitment to build all of it, or in any
particular order.
