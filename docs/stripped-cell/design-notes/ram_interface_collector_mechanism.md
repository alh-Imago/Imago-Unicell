# The RAM interface block — a real, tested mechanism for multi-chain memory access

*Captured 2026-08-17 (day 3), following directly from `#301`/`#302`
(the original stalled-chain/shared-addressing problem) and `#381`
(the first concrete design of this mechanism). This note consolidates
the full design, the real test results, and the honest open questions
into one place — Alan's own instruction: "we need both the dd4
connection, bigger space, and the interface block, both need to be
tested in the card, so yes make lots of notes."*

## UPDATE (same day) — the mechanism is now real RTL, not just Python-VM-tested

Everything below this section was written when this mechanism existed
only as a Python behavioral-model simulation. **That's no longer true.**
`points.md` #390 (shell-level `program_in` channel), #395 (the real
command sequencer), #396 (the header role, proven via the existing
accumulator core), and #397 (the COMPLETE end-to-end system, 3 real
headers + collector + command + queue, wired as genuine separate
`unicell_super_v1` instances) took this from design to real, working,
`iverilog`-simulated RTL — a full 3-round cycle, every value verified
correct, correct wraparound confirmed. The Python-VM findings below
remain real and correct; they're just no longer the most current or
most rigorously verified layer.

**A real, important generalization confirmed by this RTL, not just
theorized:** the proven 3-header collector is the actual, physical
BUILDING BLOCK the whole hierarchical addressing scheme (`#381`'s own
27 = 3×3×3 tree) is built from. A collector has exactly 4 cardinal
ports — 3 available for input sources (one direction reserved for the
output toward the queue/next level), matching the `27 = 3×3×3`
branching factor precisely, not coincidentally. **If a real system
needs more than 3 sources, the answer isn't new RTL — it's real
repetition of this exact same, now-proven mechanism, composed
hierarchically**: a second-level collector's own 3 inputs can each be
fed by a first-level collector's own output, exactly matching the
3-level tree shape already on record. This mechanism is now the real,
concrete basis for any future BRAM/memory interface needing more than
3 chains, not a separate design problem to solve later.

## The goal, stated precisely

Any Unicell-S system that needs RAM access — whether on-chip M20K/BRAM
or (eventually) off-board DDR4 — needs a way to let MULTIPLE
independent chains share that memory resource without a shared,
globally-synchronizing controller, and without losing data when one
chain stalls. This is meant to become a STANDARD, reusable substrate
mechanism, baked into any system needing RAM access — not a bespoke,
per-use design (Alan's own framing).

## The full mechanism, as designed and NOW TESTED

1. Each chain has its own **header cell** — holds/increments its own
   read address, entirely locally, no shared counter across chains
   (`#301`'s option 3, the decentralized alternative to `#301`'s own
   original centralized-arbiter proposal).
2. A **collector cell** gathers each chain's data one at a time. Its
   cardinal INPUT selection is switched at runtime.
3. A **command cell** drives BOTH halves of the switching in lockstep:
   it reprograms the collector's own `cardinal_edge` to select the
   correct direction, AND triggers the matching source to reemit its
   held value, at the same step.
4. A **counter cell** tracks progress and tells the command cell when
   to advance to the next position.
5. The collected stream feeds a **queue** -- confirmed by Alan directly
   to be plain `ram_cell_v1.v` instances, nothing new needed there.
6. **Stall handling reuses the sentinel** (`#340`) -- on stall, a
   chain's own header simply stops advancing until clear. No cross-
   chain signaling, fully decentralized.

## Real test results — VERIFIED against the live, RTL-matched Python
## VM (`nano/unicell_automaton_v1.py`), not reasoned about abstractly

**Finding 1 — mixed consume/relay in the same tick is a real fault, not
graceful handling.** Confirmed directly: if multiple sources arrive
simultaneously while some directions are configured `consume` and
others `relay`, `error_frozen` trips and the whole delivery is
rejected. The RTL's own comment: *"a well-formed model never has this
by construction... if it happens anyway, genuine error, protective
freeze."* Real consequence: source-side gating (only the currently-
selected source ever attempts to send) is a HARD REQUIREMENT, not an
optimization.

**Finding 2 — the selected direction must be `relay`, not `consume`
(a real correction to the original assumption).** `consume` is the
ordinary two-arrival gate path — it needs a second "companion" input
before it computes/fires anything, which is the wrong behavior for a
collector that wants to forward each child's value individually.
`relay` gives immediate, single-value pass-through with no waiting.
Confirmed directly: a lone `relay`-mode arrival is accepted and
forwarded in the same step, no second input needed.

**Finding 3 — sources need `hold_in`+`a_reemit_in`, pre-loaded, to
correctly reemit ONLY when triggered.** A source cell configured this
way (value pre-loaded into `a_data`, `a_arrived=True`) reemits its HELD
value whenever ANY new arrival triggers it — the trigger's own content
is irrelevant, only its presence matters. This is the real, existing
primitive (`effective_hold`/`effective_reemit`, already in the live
RTL) needed for a source that stays silent until explicitly told to
speak.

**Finding 4 — the FULL composition works, tested across two complete
rounds, zero faults.** A real grid test: 3 source cells (N/S/E),
configured per Findings 2-3, triggered one at a time in lockstep with
the collector's own `cardinal_edge` switching (simulating the command
cell's real job). Result: every single step across BOTH rounds
delivered exactly the expected value, correctly wrapped back to the
first source for round 2, with zero faults throughout.

| Step | Expected | Collector offered | Fault? |
|---|---|---|---|
| r1-N | 111 | 111 | No |
| r1-S | 222 | 222 | No |
| r1-E | 333 | 333 | No |
| r2-N | 111 | 111 | No |
| r2-S | 222 | 222 | No |
| r2-E | 333 | 333 | No |

**What this test did NOT cover, stated honestly:** it used direct
injection as the trigger and read the collector's own `out_buffer`
directly, rather than modeling a real downstream RAM-cell queue (which
has different, write-oriented semantics not yet tested here). A real,
separate next step, not something this result claims to have covered.

## The 2-cycle programming-latency correction (from `#381`, restated)

A single-field reprogram (e.g. switching `cardinal_edge`) costs a real
MINIMUM of 2 cycles internally — the field-write word, then a separate,
required `COMPLETE` word that actually re-arms the cell — both inside
`programming_active`, which suspends all normal firing. This is the
INTERNAL cost only; real wire-transit delay between the command cell
and its target is additional and unmeasured.

**The staggering insight (also from `#381`):** `N = 1 + reconfigure_cost`
parallel chains keep a shared resource continuously busy with zero
aggregate idle time, since each chain's own reconfigure window is fully
hidden behind the others. For a hierarchical (not flat) collection
tree -- the real shape implied by the `27 = 3×3×3` addressing scheme --
whether the SAME staggering rule applies cleanly level-by-level, or
needs a different factor per level, is a real, open, harder question,
not yet resolved.

## The DDR4 / external RAM question

**Real, confirmed context:** the target board (IEI Mustang-F100-A10)
has a genuine 8 GB on-board DDR4 resource. `#147` did real throughput
analysis on it (measured, not assumed) -- concluded DDR4 itself is "a
buffer at best," not the bottleneck; a "wrapper" mechanism was the
actual throughput ceiling (~1.54 GB/s aggregate vs. DDR4's own much
higher native bandwidth and PCIe Gen3 x8's ~7.88 GB/s).

**A real, important caveat, checked before answering:** that "wrapper"
mechanism (`#146`, dated 2026-08-03) predates this session's full
architecture rebuild and very likely belongs to the OLD, now-archived
full-cell design -- not anything in the current Unicell-S/nano
substrate. **There is currently no built, current-architecture bridge
from this collection mechanism to actual DDR4.**

**Honest answer to "can this collector mechanism also interface DDR4":**
architecturally, yes in principle -- the mechanism's real job (gathering
addresses/data from multiple internal fabric chains into one ordered
stream) doesn't inherently care what consumes that stream downstream.
But reaching DDR4 for real needs a genuinely NEW downstream bridge
stage (a real DDR4 controller interface), not something that already
exists to plug into. A real, separate piece of design work -- "the DD4
connection, bigger space" is real, wanted work, explicitly not yet
started.

## Real, honest size/cost estimate — SUPERSEDED (2026-08-19) by a real Quartus measurement, `points.md` #407

**UPDATE (2026-08-19): the rough estimate below is now superseded by a
real, successful Quartus build of the flat 3-header case
(`top_collector_mechanism_v1`, `points.md` #403/#404/#406/#407).
Real, measured numbers: 274 ALM total, 235.96 MHz achieved against the
25 MHz requirement. Splits into a real SHARED cost (collector +
sequencer + queue ≈ 122.5 ALM, paid roughly once per collection point)
and a real PER-HEADER marginal cost (≈22.5–27.9 ALM, averaging
≈25.9 ALM/header) — a genuinely different, much smaller shape than the
flat "~180 ALM/chain" figure below assumed. The projection below is
kept for historical record, not as a current estimate.**

No RTL exists for this mechanism yet -- everything tested so far is at
the Python behavioral-model level. The following is a ROUGH estimate
assembled from real, Quartus-confirmed reference numbers already on
record, explicitly NOT a measurement of this specific mechanism:

- Base nano cell: 5.8 ALM/cell (25-cell baseline, `CELL_INTERNALS.md`)
- Command-cell wrapper addition: +163 ALM (confirmed, though for a
  specific prior 25-cell build -- may not transfer 1:1 to a single
  dedicated command cell in this new role)
- Rough estimate per chain (header + collector + counter, each
  ~1 nano-cell-class cost, plus one command cell): **~180 ALM/chain**
- At the 27-chain addressing maximum: **~4,860 ALM**, roughly 2% of
  the GX660's real total ALM budget (~251,680) -- a real but small
  fraction, though this whole figure is a placeholder pending an
  actual build.

**Alan's own framing on this, stated directly:** a full usage pattern
would be needed to determine the real cost precisely, but the PATTERN
itself (the mechanism described above) is now settled enough to build
against -- the estimate above is "enough for now," not a final number.

## Real, honest remaining work, stated plainly

1. No RTL exists for header/collector/command/counter yet -- Python
   behavioral-model tested only.
2. The real downstream queue (RAM-cell-based, write-oriented) has not
   been correctly modeled/tested yet.
3. The hierarchical (27-leaf, 3-level) staggering question remains
   genuinely open, not resolved by the flat 3-chain case.
4. A real DDR4 bridge for the current architecture does not exist and
   has not been designed.
5. A real Quartus-measured size for this mechanism does not exist --
   the ~180 ALM/chain figure is a rough, honestly-caveated estimate.
6. Both the DDR4 connection AND the interface block itself need real
   testing on actual hardware once built -- explicitly named by Alan as
   both being real, wanted next steps, not yet started.

## A real, precise gap: the super carrier shell's own bit LAYOUT is
## fully documented; its runtime ACCESS mechanism is not

Checked directly, not assumed either way. `docs/stripped-cell/
SUPER_CELL_INTERNALS.md` has a complete, cross-validated `core_config
[N:0]` field map for all 6 real cores -- bit positions and widths,
matched against real RTL test vectors AND mechanically re-extracted
from the RTL's own comments, with one honestly-flagged exception
(`addon_config` isn't covered by that same mechanical check, since it's
wired via direct port connections, a genuinely different RTL pattern).

**But the ONLY documented (and built) access mechanism for the shell is
the atomic, all-or-nothing register write** -- `if (cfg_valid)
super_latch <= cfg_data`, the whole 80 bits at once. Confirmed directly:
there is no incremental, field-by-field, runtime reprogramming path
for the shell at all. The standalone nano cell has exactly this
(`program_in`/`PROG_ID`, fully documented in `CELL_INTERNALS.md`) --
but `SUPER_CELL_INTERNALS.md` itself states plainly that nano's own
programming channel is "tied to inactive defaults" inside the shell,
genuinely out of scope, not an oversight.

**This is not a new gap -- it's the exact same one already tracked
since `#371`** (the command-cell wrapper's own exposure question), and
the same thing the whole header/collector/command mechanism above has
been depending on existing eventually. Looking at it from the
documentation side rather than the RTL side changes nothing about the
answer: it genuinely needs to be DESIGNED AND BUILT, not just written
up -- there is nothing to document yet because the mechanism itself
doesn't exist for the shell.

## The loader's own real, confirmed lack of connection-point awareness

Checked directly against `nano/loader_v1.py`'s own real code, not
assumed: `find_auto_placement()` and `find_dsp_aware_placement()` both
know only how to AVOID collision (and, for the DSP-aware mode, minimize
distance to a given column). Neither has any concept of "this needs to
land next to that." There is no code anywhere in the loader that knows
where a RAM header, a collector, or any other existing infrastructure
cell is -- confirmed by grep, not inferred from the design.

**A real option worth stating plainly, not assumed to be the only
path:** since each workbench region is already a fully independent,
self-contained unit (`#363`), the simplest and most architecturally
consistent answer may be that EACH region needing RAM access brings its
OWN complete header/collector/command/queue set, rather than trying to
share one memory interface across independently-loaded models. That
sidesteps most of the cross-region connection problem -- the loader
just needs to place a region's own infrastructure adjacent to its own
chains, a self-contained placement problem, not a cross-region one.

**The harder case that doesn't go away either way: multiple chains
WITHIN one region, all needing to reach the same collector/queue.**
That genuinely does need the loader to know where the collector sits
and place each chain's header within reach of it -- the same kind of
"connection point awareness" `dsp_columns` already established a
pattern for (`#377`), just applied to something the loader has never
had a concept of before.

**A real, sharpening observation, Alan's own: there are TWO points of
mutability, not one.** The header/collector side can move (that's what
the loader already places) -- but the RAM queue side is ALSO a chain
of plain RAM cells (`#382`), not one fixed dot. It can extend or
reroute to meet a header partway, not just sit still waiting to be
reached. A real degree of freedom a naive "connect fixed point A to
fixed point B" router wouldn't have.

## The connection problem is structurally Numberlink -- confirmed, not just an analogy

Verified directly, not assumed: Numberlink (also called Flow, Arukone,
Nanbarinku) -- the puzzle of connecting N pairs of same-labeled cells
on a grid with non-crossing paths -- is proven NP-complete, in BOTH
major rule variants (requiring full grid coverage and not requiring
it). Real, cited academic sources confirm this (Adcock/Demaine et al.,
"Zig-Zag Numberlink is NP-Complete," 2015; multiple independent
confirmations in the wider literature).

**Real, practical consequence, not just a computer-science curiosity:**
there is no known efficient algorithm that GUARANTEES an optimal,
non-crossing solution to this class of problem as the number of
connection pairs grows. This CONFIRMS (doesn't newly establish) that
the project's own existing design direction -- `#54`/`#220`'s
"anchor-first seeded graph embedding... grow outward BFS along
dataflow edges, cost = hops" -- was already the right KIND of approach:
a practical heuristic, not an attempted exact solver. Real FPGA place-
and-route tools face this exact same underlying hardness for general
net routing and solve it the same way, every day: heuristics that work
well in practice, not proofs of optimality.

**A real, honest, unresolved scaling question:** 27 simultaneous
connection points (the real addressing maximum, `#381`) is a
genuinely different scale of problem than the handful-of-pairs
instances most routing heuristics are tuned and tested against.
Whether anchor-first BFS actually holds up at that scale, or where it
starts breaking down, is a real, open question -- not yet tested,
stated honestly rather than assumed either way.

## Three real approaches to solving it, and a genuine reframing of the Composer's own purpose

Given the problem's own proven hardness, Alan's own real proposal:
this may be exactly where the AI and the VM need to be active
participants, not just passive tooling. Three distinct, real
approaches, not mutually exclusive:

1. **By hand** -- the user places things manually.
2. **AI + VM, as a real heuristic search loop.** The compiler already
   produces the ICM (the LOGICAL shape -- what connects to what); the
   VM's own real introspection (`vm_introspection_v1.py`, `#354`) and
   the AI-interaction port (`VMSession`, `#359`) already provide
   exactly the "compile, place, check validity, inspect" loop this
   would need -- not hypothetical infrastructure, something that
   already exists and works today. An AI agent could genuinely use
   this as a fast validity-checking oracle while iterating over
   candidate placements, the same practical heuristic-search pattern
   real EDA tools already use, just with an AI driving the search
   instead of a hand-written heuristic.
3. **A visual, human-in-the-loop tool -- a genuine reframing of the
   Composer's own purpose (`#20`), not just a restatement of its
   original one.** `#370`'s own real doubt about the Composer ("not
   sure if its relevant, it requires pre made models and full
   understanding of the system") was raised against its ORIGINAL
   conceived purpose -- creating models. This is a genuinely different,
   additional reason for it to exist: helping a human PLACE/ROUTE an
   already-compiled model by eye, leveraging the same real human
   visual-puzzle-solving strength that makes people surprisingly good
   at Numberlink-class problems in practice, despite their proven
   worst-case hardness. Worth carrying forward as a real update to the
   Composer's own premise question, not a new, separate idea -- the
   Composer may turn out to be needed for a reason genuinely different
   from the one that originally motivated it.

**Not yet done, stated plainly:** none of the three approaches has been
built or tried for this specific problem. This section captures a
real, three-way design option and a genuine reframing of an existing
open question (the Composer's own premise), not a decision or a build.

## `#301`'s stale-data hazard and `#302`'s write-side concern, precisely re-located against what's now actually real (`#399`)

**Neither is resolved by the now-proven RTL above -- both were re-read
in full and re-examined against it precisely, revealing they concern
two genuinely different, still-unbuilt stages of the overall pipeline,
not the header/collector/queue mechanism this note's own RTL section
proves.**

`#301`'s own stale-data hazard concerns a computed ADDRESS triggering a
REAL RAM READ, whose RESULT needs to reach a possibly-stalled
DOWNSTREAM CONSUMER, using a retry loop that holds the address (not the
data) while waiting. The hazard: something else writes to that RAM
location while the retry waits, so the eventual retry delivers
whatever's CURRENTLY there, not what was live when queued. **This is
the read-RESULT-delivery side of the pipeline -- `#397`'s own proven
mechanism is the address/value-SUPPLY side instead**, and never builds
or tests anything resembling a retry-loop-for-stalled-consumers at
all. That whole stage remains genuinely unbuilt.

**A real, genuine architectural advantage confirmed precisely, not
previously stated this exactly:** each header in the now-proven
mechanism exclusively owns and updates its own held value -- there is
no shared, externally-writable resource being queued-and-later-
revisited the way `#301`'s original centralized design queued a shared
RAM address. `#301`'s own specific hazard has no direct analogue for a
header's own local state, because nothing external can write to it.

**Where the hazard genuinely still lives, precisely located:** the
moment a header's collected value gets used as an address into an
actual, shared BRAM (matching this note's own earlier "the queue is
fed to the bram addressing mechanism to recall that data" framing) --
a stage the proven RTL does not build or test at all, it only proves
values correctly reaching the queue itself. Between a real BRAM read
completing and its result reaching a downstream consumer, `#301`'s own
hazard re-enters in essentially its original shape.

`#302`'s own write-side "out>in" concern is grounded in a real, already
-confirmed hardware topology (`#273`/`#286`) -- multiple WRITE sources
COMBINING via real joins before writing back to RAM, where join
combinations can scale faster than raw chain count. The now-proven
mechanism is purely READ-side (gathering, not combining, a genuine 1:1
correspondence between rounds and outputs) -- a fundamentally
different, write-side topology this note's own RTL doesn't touch or
make any claim about either way.

**The honest summary:** the proven mechanism is a real, necessary PART
of a complete RAM interface, not the whole system. Both `#301` and
`#302` remain exactly as open as their own original entries honestly
stated -- neither confused with this note's own real accomplishment,
nor claimed resolved by it.

## Real synthesis: `#408`'s later closure of `#301`/`#302` doesn't contradict the section above -- it tells us something useful about how the still-unbuilt stage should behave once built

**Read together, not in isolation, since a later session (`#408`) closed
what this note's own earlier section (immediately above) called
"genuinely still open" -- both are correct, about different things.**

`#408` established a real, standing design principle: every core built
in this project so far follows "offer stays stable until acked" --
nothing free-runs, nothing re-offers before its own prior offer is
genuinely consumed. Under that discipline, the SPECIFIC race `#301`
worried about (a fresh write landing on a RAM location while an
earlier read's own retry is still pending) cannot occur, because
whatever WOULD produce that fresh write is bound by the identical
backpressure discipline -- it cannot get ahead of a stalled consumer
any more than the read side can.

This does not un-open what the section above identified: the real
BRAM-read-result-delivery stage (address computed -> real read issued
-> result reaches a possibly-stalled downstream consumer) is still
genuinely unbuilt. What `#408` tells us is narrower and more useful
than "it's fine": IF that stage, whenever it gets built, follows the
SAME offer-holds-until-acked discipline every other core in this
project already follows -- which is the default, not an exception, for
everything built so far -- THEN `#301`'s own specific stale-data race
will not manifest in it either. `#408`'s closure is a real design
constraint to build that stage AGAINST, not proof it's already handled.

## `#410`-`#416`: the sentinel system wired to a real chain for the first time, and the real shared-BRAM redesign this forced

**A separate, later thread of work, connecting `#279`'s own FULL
SENTINEL SYSTEM (proven standalone at `#281`, explicitly flagged there
as needing real-chain integration next) to the gather mechanism this
note's own earlier sections prove.**

**`#410`: sentinel + gather, synthetic data, first real integration.**
3 real accumulator chains, each with its own `sentinel_counter_v1`
instance, each independently wrapping/freezing on its own local
block's completion without waiting on the others. A real integration
bug found and fixed here, diagnosed precisely by Alan, not discovered
independently in code: the counter's own freeze (stop counting,
immediate) and the accumulator's own freeze (stop OFFERING what it
already holds) are NOT the same signal. Conflating them stranded the
wrap-triggering final value -- captured correctly, but its own offer
never got a chance to complete, since the same signal that (correctly)
stopped the counter was also (incorrectly) blocking the accumulator
from ever offering what it had. Fixed by driving the accumulator's own
`freeze_in` from `results_ready_flag` (`out_frozen && diff==0`) instead
of `freeze_out` directly -- the counter freezes immediately; the
accumulator's own ability to offer freezes only once the final value's
delivery is CONFIRMED complete.

**`#412`: a fundamental correction, caught before more time was spent
on the wrong design.** Real BRAM has only 2 physical ports -- which is
WHY the entire header/collector/combiner architecture this whole note
documents was designed in the first place: 1 shared read port, 1
shared write port, arbitrated across every chain through mechanisms
already proven, not one separate memory per chain. An earlier attempt
(`#411`) gave each chain its own private BRAM, which never actually
exercised the real sharing constraint at all -- corrected before
building anything further on top of it.

**`#413`-`#415`: the real shared-BRAM redesign, built correctly per
`#412`'s own correction, reaching a clean pass.** ONE shared
`bram_controller_v1.v` instance serves all chains, arbitrated by
REUSING the exact round-robin gating that already decides whose turn
it is to offer to the collector -- no separate arbitration mechanism
needed, since only one chain is ever "current" at a time anyway.
`#409`'s own block-partitioned addressing became real for the first
time here: each chain's local counter offset by its own fixed block
base into the one shared address space. Several real, distinct bugs
were found and fixed along the way (a multiple-driver hazard, a
`read_owner` staleness bug where a response could be misrouted to the
wrong chain, a precise preload timing bug where the last write raced
its own op-reset and got issued as a stray read instead) -- see
`points.md` `#413`/`#414` for the full, precise account of each.

**The real, general principle this redesign surfaced, worth carrying
into ANY future round-robin-gated mechanism in this project, stated by
Alan and confirmed correct by testing before being built:** "the
sequence should be based on actual data in the latch... data in then
confirm, not ready and waiting confirm then capture." A chain's own
readiness (visible to whatever's arbitrating access to it) must be
gated on having ALREADY genuinely captured the data being asked for --
not merely "has captured something, ever," and not "is it nominally
this chain's scheduled turn." The fix that closed `#415`'s own last
real bug was exactly this: `h*_fresh`, a PER-ROUND freshness flag
(replacing an earlier, insufficient one-time `h*_primed` flag that
only protected a chain's very first visit), reset at the start of
every round and set only once that round's own real capture completes.
Confirmed as a genuinely recurring hazard, not a one-off: it surfaced
TWICE in this same redesign (once as a one-time priming issue, `#414`;
once in its full, general per-round form, `#415`) before being closed
correctly both times.

**`#416`: a real scale family (1/3/9/27 chains, each a genuinely
separate, standalone unit, not one module switched by a parameter) --
started, not complete.** The real architecture: every level shares the
SAME per-chain building block (address counter + accumulator +
sentinel + shared BRAM read), differing only in how many chains share
the one physical read port and how many arbitration levels are needed
to pick among them -- 0 for a single chain, 1 for 3 chains (`#415`,
proven), 2 for 9 (two groups of 3), 3 for 27 (matching `#402`'s own
proven VM shape exactly). Level 1 (fixed at `#425` -- the wrap/freeze
signal was being forwarded to the sentinel the instant the wrap-causing
read was ISSUED rather than once it genuinely completed, the same
class of bug already found and fixed twice below, this time in the
wrap path instead of the readiness path) and Level 3 (`#415`) both now
pass clean, deterministic, zero regression on each other. Levels 9 and
27 have not been started.

**Real, honest scope, stated plainly:** all of `#410`-`#425` is
synthetic-data proof at the RTL/sim level. No real BRAM read of
genuinely externally-sourced data has been built (each proof so far
preloads its own known values before reading them back). The real host
reload/JTAG round trip -- the actual point of the freeze/unfreeze
protocol -- has not been built; every unfreeze pulse so far comes from
the self-test FSM standing in for it.

**Real Quartus numbers now exist, closing a gap stated for several
entries (`#426`, 2026-08-22):** 347 ALM, 598 registers, 188.86 MHz on
the real 25MHz-target fabric clock (a 7.55x margin), 144 block memory
bits, 0 DSP/HSSI/PLL. Measured directly against `#407`'s own baseline
(274 ALM, 235.96 MHz, the flat collector mechanism WITHOUT sentinel or
shared-BRAM arbitration): **+73 ALM (26.6%), Fmax down 20.0%** -- a
real, measured, non-trivial cost for the sentinel + shared-BRAM read
arbitration, still comfortably clear of the real 25MHz requirement.
Per-instance breakdown worth keeping for future 9-way/27-way scaling
estimates: the 3 `sentinel_counter_v1` instances cost ~9 ALM each
(~27 combined); the ONE shared `bram_controller_v1` (`#412`'s own real
architectural correction) costs only ~12 ALM total, confirming that
correction was cheap to implement once done right; the collector's own
nano core (68.8 ALM) remains the single largest contributor, matching
`#407`'s own earlier finding.

**A real, stated gap: none of this exists in the Python VM.**
`nano/unicell_super_automaton_v1.py` (`SuperCell`/`SuperGrid`) has zero
representation of `sentinel_counter_v1` or the shared-BRAM arbitration
mechanism -- checked directly, not assumed. Every proof in `#410`-`#416`
exists only as real Verilog and iverilog simulation, with no VM-level
model to cross-check against or to extend the 27-leaf VM proof (`#402`)
with real freeze/sentinel behavior. Building that VM model, if wanted,
is real, separate, not-yet-scoped work -- not attempted here.
