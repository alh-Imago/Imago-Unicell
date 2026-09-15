# CORDIC, revisited: what `mul` and `priority` actually unlock (Alan/Claude, 2026-09-15)

*A real, direct follow-up to `points.md` #513 (2026-08-25), written
before `mul` or `priority` existed. That note already established the
core result: CORDIC — the standard technique for computing sin/cos/
tan/arctan/sqrt/exp/log from iterative shift, add/subtract, and a
sign-based rotation decision — maps almost entirely onto primitives
this project already had (`shift_lane_addon_v1.v`, the adder core,
the branch cell). This note doesn't repeat that mapping; it asks the
narrower, honest question Alan raised directly: given `mul` and
`priority` are now real, built, verified cores (`#724`/`#730`), what
do they specifically change about that picture? Two real, concrete
answers below — one for each core — plus what's still genuinely open.*

## Real, honest framing before the two answers

CORDIC never *needed* multiplication — that was the whole historical
point of the algorithm, decades before hardware multipliers were
cheap. So `mul` doesn't unlock CORDIC's own core iteration at all; the
shift/add/branch loop `#513` already scoped stays exactly as it was.
What `mul` and `priority` unlock is everything *around* that loop —
the parts `#513` correctly left as real, open costs rather than
solved problems.

## `mul`'s real contribution: two genuine, separate wins, not one

**1. Gain correction becomes a direct multiply instead of a decomposed
shift-add sequence.** CORDIC's own rotation-mode iterations introduce
a fixed, well-known gain factor (K≈1.6467 for circular mode) that has
to be corrected somewhere — the standard real technique is multiplying
the final result by 1/K (≈0.6072, a fixed constant). Without a real
multiply core, that correction has to be built the same way any
constant multiply is built from shift-add primitives alone — a real,
working technique, but one that adds its own stages (and its own
cells) on top of the CORDIC loop itself. With `mul` now real and
available, that correction is a single, direct multiply-by-constant
step. This doesn't change whether CORDIC works; it changes how many
real cells the gain-correction step costs, which matters directly
given this architecture's own hard, real per-card cell ceiling
(~200-250 cells at the currently-accepted Fmax).

**2. Integer exponentiation's own real technique gets dramatically
cheaper, not just simpler.** `#513` already named repeated squaring as
the real technique for integer exponentiation, explicitly noting it
was "structurally the same shape as `#506`'s own multiply-via-
repeated-addition, just squaring instead of adding" — because at that
time, a REAL squaring step meant repeated addition, itself an
iterative sub-process. With `mul` now a real, single-cycle-latency,
purely combinational core, each squaring step in that repeated-
squaring chain becomes one real `mul` call instead of its own
multi-cycle repeated-addition loop. The algorithm's own real shape
(repeated squaring) is unchanged; what changes is the real cost of
each step inside it — a genuine, direct unlock, not a restatement.

**3. A real, honest, NOT-yet-resolved possibility, named plainly as
speculative:** higher-radix CORDIC variants exist that trade "more
iterations, each doing pure shift-add" for "fewer iterations, each
doing slightly more work, including a small multiply." Whether that
tradeoff is actually worth it HERE depends on real numbers this note
doesn't have — the real per-iteration cell cost of a higher-radix
stage versus the real cell cost saved by needing fewer of them. Worth
naming as a real question a future pass could answer with actual
measurement (matching `#514`'s own real-numbers-over-guesses
discipline), not something this note claims to have resolved.

## `priority`'s real contribution: it makes the LOOP topology genuinely shareable, closing a real gap `#513` left open

**The real gap, stated precisely:** `#513`'s own loop-vs-chain choice
described the LOOP option as "cheap, slow per-value, real cells not
tied up permanently" — clearly implying the loop is meant to be
REUSED across multiple, separate computations over time, not built
fresh for each one. But `#513` never addressed what happens when
MULTIPLE, DIFFERENT vectors want to use that same shared loop at
close to the same time. Every core's own arrival logic in this family
OR-combines simultaneous arrivals from different directions —
correct and safe when only one direction is ever actually enabled at
once, but genuinely wrong (data corruption, not just contention) if
two DIFFERENT real vectors' worth of data tried to enter the same
shared loop simultaneously. Without a real arbitration mechanism, a
shared CORDIC loop would need either an external, software-level
scheduler (not a real, hardware-native mechanism) or careful,
manual timing discipline preventing simultaneous injection — a real,
fragile constraint on how the loop could actually be used.

**The real fix, a direct, literal application of what `priority`
already does, not a stretch:** placed at the loop's own real entry
point, `priority` arbitrates which of several competing vectors gets
injected into the shared iteration hardware next. Both of its real
modes map onto real, different CORDIC use cases:
- **Strict priority** — some vectors are genuinely more urgent (a
  real-time control loop's own angle computation should never wait
  behind a batch job's).
- **Weighted round-robin** — several streams of comparable importance
  share the loop fairly, each getting proportional turns rather than
  one monopolizing it and starving the others (`#730`'s own real,
  worked example — a 3:1 configured weight giving an exact 6:2,
  genuinely interleaved service pattern — is directly the shape this
  needs).

**A real, honest, new consequence worth naming directly: this creates
a genuine THIRD topology option, not just a safety fix for the
existing one.** `#513`'s own choice was binary — an occasional-use
loop (cheap, single-user) or a sustained-stream pipeline (N cells,
one per iteration, full throughput). A `priority`-arbitrated SHARED
loop is a real, different point on that spectrum: several concurrent
users, fewer cells than N separate loops would cost, less throughput
than a dedicated pipeline sized for peak load but real, fair service
to every stream using it. Whether this is ever the RIGHT choice for a
given real workload is exactly the kind of question `#514`'s own
still-queued decision chart was scoped to eventually answer with real
numbers — this note adds a real third option to that decision, it
doesn't resolve which one wins for any given case.

## Real, honest, open questions — nothing here is resolved or scoped into build steps

- **The atan lookup table CORDIC's own rotation mode needs at every
  iteration has no identified real mechanism in this family yet.**
  `sequencer_cell_v4`'s own real value-cycling (`#513`'s own family
  didn't have this core yet either) is a plausible candidate worth
  real investigation later, but its own real 4-value limit is almost
  certainly too small for the ~16-32 entries a reasonable-precision
  CORDIC table would want — genuinely unresolved, not assumed solved
  by a core that happens to sound relevant.
- **No real cell-count or timing comparison exists between the three
  topology options** (dedicated loop, dedicated pipeline, shared
  `priority`-arbitrated loop) for any actual target precision or
  throughput requirement. All of this stays qualitative until
  something in this shape is actually built and measured — the same
  standard `#509`/`#514` already hold every other claim in this
  project to.
- **Whether a `priority`-arbitrated shared loop can genuinely sustain
  the SAME iteration-count-per-vector guarantee a dedicated loop gives**
  (i.e., does arbitration ever introduce a partial-iteration hazard —
  a vector's own state getting overwritten mid-sequence by another's
  injection) is a real, structural question that needs actual design
  work, not assumed safe by analogy to `priority`'s own simpler,
  single-value arbitration use case tested so far.
- **Higher-radix CORDIC's own real viability** (named above under
  `mul`) is speculative, not scoped.

**Real, honest status: a design possibility sharpened by two new real
primitives, not a build plan.** Nothing here is built, nothing is
scoped into concrete RTL steps. The real value of this note is
narrowing `#513`'s own two-way choice into three real options and
naming precisely which NEW primitive unlocks which NEW cost-reduction
— leaving the actual build, measurement, and topology decision for
whenever this is picked up for real.
