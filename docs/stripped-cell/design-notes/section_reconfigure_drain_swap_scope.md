# Section-wide reconfigure, drain/swap/reload, and iterative folding (CONCEPT, review before building)

*Captured 2026-09-26, from a real, live design discussion that grew
directly out of fp32 ADD's own static-vs-reconfigure question
(`#840`/`#841`). Nothing built here — a real design note, matching
every other `*_scope.md`'s own discipline of capturing shape before
committing to RTL. Logged in the ledger as `#843`; this file is the
proper write-up that entry's own real queue called for.*

## Real point 1: static structure wins for anything meant to stream

`unicell_vix_carrier_v1d.v` (`#841`) gave the carrier a real, proven
way to live-reprogram its own shared addon block at runtime. The
question that followed: should fp32 ADD use that mechanism for its
data-dependent stages (the alignment shift, the overflow-driven
normalize shift), or should it use static structure instead (a
log-depth mux tree for alignment; a branch-and-pad topology for
normalize, `#544`'s equal-hop-count rule satisfied with plain
flowing-mode RAM cells as delay padding — the same "delay cells are
extra relay hops" principle already proven for DSP-wrapper latency,
`#822`)?

The real, decisive fact: **freeze is not per-cell, it is
pipeline-wide.** A `v1d`-style reconfigure pauses the WHOLE substrate
while it happens, not just the cell being touched. A static structure
pays its cost once, at build time, and then runs at full throughput —
values flowing through back-to-back, no gap. A live-reconfigure
structure pays a real pause on every operation whose data-dependent
decision requires a different setting than the last one used.

**Settled, independent of unmeasured depth/cell numbers:** for
anything meant to be a real, reusable, streaming arithmetic tile —
which fp32 ADD is — static structure is the right choice on
architectural grounds alone. `v1d`-style live reconfigure remains the
right tool for genuinely rare or occasional retuning (nudging a shift
amount once in a while), not for gating a per-value decision inside a
stream. Whichever strategy is chosen should be applied consistently to
BOTH of ADD's data-dependent stages (alignment and normalize) — a
design that's static for one and reconfigure-based for the other would
be an incoherent mix without a real reason for the difference.

## Real point 2: live reconfiguration is a deeper power than it first looks

Worth naming precisely, separate from the throughput cost above: an
ordinary per-field PROG_ID reconfiguration (flipping `subtract_mode`,
say) still leaves a core being fundamentally the same thing — "an
adder that now subtracts instead." Live-reprogramming the ADDON CHAIN
itself is a step beyond that — the same physical structure can become
a genuinely different transform in place (pure passthrough one moment,
a masked-and-shifted transform the next), with no rebuild, no new
cells laid down, nothing torn down. Closer in spirit to the carrier's
own core-select philosophy (one physical position, many identities),
but applied one level deeper — to a chain's behaviour, not to which
core occupies a slot.

This is real, genuine capability, not merely a workaround for the
throughput cost in point 1 — which is why it's worth its own real use
case (points 3-6 below) rather than being set aside just because it
loses the static-vs-reconfigure argument for a single streaming tile.

## Real point 3: amortizing the pause across a whole section, not one cell

If the live-reconfigure pause is unavoidable for some real use (see
points 5-6), the next real question is whether it has to be paid once
per cell touched, or once per RECONFIGURE EVENT regardless of how much
is being touched.

**The real mechanism, built from pieces that already exist:** a LINE
of command cells, each in programmer mode, each wired 1:1 to its own
target (not necessarily identical targets, and not necessarily
identical relay payloads — each can carry whatever that specific
position needs). If every command cell in the line starts its own
freeze→relay→ack→unfreeze sequence on the SAME cycle, the whole
section's pause is one pipeline-wide stall, not N of them.

**The real, still-open mechanism question:** what guarantees they all
start on the identical cycle, rather than merely close together?
Trigger mode's own real, existing design — watching a shared signal,
direction-agnostic, OR-combined — is the natural answer: if every
command cell in the line watches the SAME broadcast signal, they cross
from idle to active together BY CONSTRUCTION, not by hoping timing
happens to line up. This points directly at `#835`/`#836`'s own
paired-cell/command-bus idea as the natural carrier for that shared
trigger, rather than inventing a second broadcast mechanism alongside
it — a real, concrete use case for that idea, not just a hypothetical
one.

## Real point 4: the in-flight hazard, and the drain/swap/reload resolution

A genuine hazard falls out of point 3 immediately: if the section being
reconfigured has any values still mid-flight across the cells being
touched, freezing them all together is safe (nothing progresses,
nothing corrupts) — but the moment they unfreeze together, whatever
was mid-flight resumes against a now-different downstream
configuration. Two very different guarantees are possible here:
tolerate live in-flight state across the reconfigure, or require the
section to be genuinely drained first. The first is a much harder
correctness problem; the second is the one this design commits to.

**The real resolution: drain to a checkpoint before reconfiguring, so
there is never any in-flight data to reason about.** A genuine
two-branch pattern:

1. **Branch A live and processing.** Branch B is being reconfigured
   off to the side — safe regardless of B's own state, since B isn't
   in A's data path yet.
2. **A's output feeds a checkpoint** (a RAM cell or cells), not B
   directly.
3. **Swap:** the newly-reconfigured B takes over, fed FROM that
   checkpoint — a real reload through the new chain, not a resumption
   of old in-flight state.
4. **A becomes the next branch available to reconfigure**, and the
   cycle repeats — a genuine ping-pong between the two branches, not a
   one-shot swap.

**The real, still-open piece: knowing when a drain is genuinely
complete, not merely paused.** This needs some real drain-completion
signal. `#257`'s own empty/full status-signal concept (part of its
real host stall/refill lifecycle design) is the obvious real fit for
this role — but per the honest correction below, that concept is
UNBUILT. Building it for real (or designing an alternative) is real,
necessary prerequisite work, not something this design can assume
already exists.

## Real point 5: overlapping the reconfigure with the flow

The genuinely elegant closing piece: the SAME drain-completion signal
that hands the checkpoint to the branch taking over can ALSO fire the
trigger (point 3) that starts reconfiguring the branch that just
emptied — one signal, two real jobs, for free. By the time fresh data
has finished flowing through whichever branch is currently live, the
branch that drained has already finished becoming something new. The
reconfigure latency hides behind the handoff instead of sitting in the
critical path at all.

This is what makes points 3-5 together a real, coherent answer to
point 1's own cost — not by avoiding the pipeline-wide pause, but by
making sure it never has to be waited for on the critical path.

## Real point 6: iterative folding — a genuinely different use mode

Everything above optimizes latency for a fixed design being
reconfigured. A real, separate use mode this same mechanism opens:
rather than laying out every stage of a multi-stage algorithm as
separate, permanent hardware, fold the WHOLE algorithm through a
small, fixed footprint of cells, one stage at a time, self-triggering
its own reconfiguration between passes via the mechanism in points 3-5.

This is real, compact area-for-time trading — a genuine answer to
doing significant computation on a small board (the Tang Nano 20K's
own real constraint) without needing every algorithmic stage to exist
in silicon simultaneously.

## Honest citation correction

Mid-discussion, Claude asserted the drain/checkpoint pattern in point
4 was already proven precedent from a "hybrid-DSP" design entry
("freeze → system quiesces → hard blocks settle → save cell states").
Checked directly against the real ledger before this file was written:
**no such entry exists.** The general freeze/quiesce mechanism itself
IS real and proven throughout (every core's own `freeze_in`). The
specific host stall/refill lifecycle and empty/full status signal this
design leans on for point 4 is `#257`'s own real, referenced design —
but it is explicitly and repeatedly flagged in later entries as NOT
YET MODELLED, NOT YET PLACED. This design rests on that honest
footing: a real, referenced, UNBUILT concept, not existing working
infrastructure being reused.

## Real, honest scope

Nothing in this file is built. No RTL, no VM code, no cell counts, no
tick counts. Every real number this design would need — branch depth,
RAM padding count, actual reconfigure-cycle cost, whether trigger
mode's shared-signal watch genuinely produces same-cycle activation
across multiple command cells rather than merely close cycles — is
unmeasured. This is a captured, coherent SHAPE, not a scoped
implementation plan.

## Real queue

1. Resolve the drain-completion-signal question — build `#257`'s
   empty/full concept for real, or design an alternative — before any
   of points 3-5 can be simulated at all.
2. Confirm trigger mode's shared-signal watch genuinely produces
   same-cycle activation across multiple command cells (a real,
   targeted testbench question, not assumed from the mode's existing
   single-target proof, `#644`).
3. Measure the real static-vs-reconfigure numbers (point 1) for BOTH
   of ADD's data-dependent stages — alignment and normalize — applying
   whichever strategy wins consistently to both.
4. fp32 ADD itself, once point 3's decision is made.
5. VM-level model of `v1d`'s own new addon-addressing mechanism
   (`#841`) — needed before any of this can be prototyped in Python
   ahead of real RTL.
6. If points 1-2 resolve favourably, a real design pass on points 3-6
   as an actual buildable mechanism (not just a captured shape) —
   likely its own follow-up scope note once real numbers exist.
