# The RAM interface block — a real, tested mechanism for multi-chain memory access

*Captured 2026-08-17 (day 3), following directly from `#301`/`#302`
(the original stalled-chain/shared-addressing problem) and `#381`
(the first concrete design of this mechanism). This note consolidates
the full design, the real test results, and the honest open questions
into one place — Alan's own instruction: "we need both the dd4
connection, bigger space, and the interface block, both need to be
tested in the card, so yes make lots of notes."*

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

## Real, honest size/cost estimate — CAVEATED, NOT MEASURED

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
