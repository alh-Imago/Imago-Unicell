# points.md Status Audit — 2026-08-16

**Covers entries #1-#330. For #331-#592 (everything since, including
the whole current session's real hardware work), see
[`POINTS_STATUS_AUDIT_2.md`](POINTS_STATUS_AUDIT_2.md), added
2026-09-02.**

**Purpose: a genuine sweep through all 330 numbered entries, organized
by architectural era, flagging what's complete, what's architecturally
superseded, and — the most valuable part — specific items that are
still real and relevant but had drifted disconnected from current
active work. This document does not edit `points.md` itself (the
ledger stays append-only, historical record intact); it's a curated
map on top of it.**

**Method:** every entry title read in full (330 of them), grouped into
five architectural eras by what they actually describe, cross-checked
against `current/latest.md`/`current/START.md`'s own "open items"
lists, and spot-checked in full where the title alone was ambiguous or
where a real cross-era connection looked plausible.

---

## Era 1: Pre-fork FULL-cell / pentacross exploration (#1–#106)

**Status: mostly architecturally superseded — the specific mechanisms
described (pentacross lattice tiling, cluster-mesh bus routing,
address-decode relay cells, the cellular-automaton hybrid-card
concept) were never carried into the nano/stripped line. `#107`
explicitly marks the pivot: "two closing architectural principles...
established as first-principles for the project going forward."**

This is NOT wasted work — it's the real reasoning trail that led to
the pivot, and several ideas from this era WERE carried forward
conceptually even though their specific mechanism died with pentacross:

- **`#37`'s "cell IS the memory cell" concept** (loop_back + latch_in +
  MEM_CALL) — the specific pentacross-era mechanism is dead, but the
  underlying idea was explicitly cross-referenced and confirmed fully
  realized on the stripped cell at `#119`. Not orphaned — already
  properly closed within this same era's own later work.
- **`#124`'s photonic-interconnect direction** — carried forward
  explicitly at `#219` and `#299`. Still on record as a real, long-
  horizon, speculative direction. Not orphaned.
- **`#43`'s "lane-split-to-cardinals mode" parked idea** — worth a
  second look now that shift/lane addons are real (`#303`/`#311`).
  Not confirmed connected, but similar enough in shape to be worth
  Alan's own eyes rather than assumed dead outright.

**Safe to treat as closed/historical, no live thread:** the pentacross
tiling math (#3, #38, #47), the cluster-mesh bus-vs-crossbar analysis
(#2, #6, #7, #12, #14, #15, #24, #32), MathTrix-specific questions
(#13), the substrate-map/composer-frontend concept as originally
scoped (#19–#21), the N-dimensional bridge-cell reconfiguration idea
(#48), and the full cellular-automaton/hybrid-card exploration (#70,
#74–#86) — all superseded by the stripped-cell architecture that
replaced it. Real, useful reasoning trail; not live work.

**Genuinely orphaned, no later reference found:** `#10` ("Host-
triggerable control register, not started"), `#45` ("a larger,
dedicated 'lab' AI role for substrate exploration" — a tooling/meta
idea, distinct from the RTL work, never picked up again). Neither is
architecturally urgent, but worth a conscious decision (still wanted,
or formally drop) rather than sitting in limbo.

---

## Era 2: Stripped-cell core buildout (#107–#179)

**Status: foundational and complete. This IS the genesis of the
current active architecture — not stale, not superseded, just
finished. The wrapper, command-cell, freeze, hold/feedback, ready-flag,
and 25/50/750-cell scale campaigns all directly underpin everything
built this session.** No cleanup needed here; this era did its job.

One item worth surfacing because it connects directly to real work
from TODAY:

- **`#171` "Modular/composable cell builds + capability-aware .icm"**
  (2026-08-04, explicitly "concept-stage, deliberately not
  implemented") — this is the SAME document (`docs/shared/design-
  notes/modular_cell_builds_and_capability_aware_icm.md`) that got
  read and referenced during this session's own `#320` design work.
  Not orphaned — already properly picked back up, just worth noting
  the thread is real and continuous across 12 days.

---

## Era 3: The 750-cell timing investigation (#180–#241)

**Status: resolved as a whole arc, closed cleanly at `#241` (the SDC-
discipline discovery) and `#228` (the pruning-trap correction). Most
INDIVIDUAL entries in the middle of this arc are tested-and-rejected
hypotheses — real, valuable as a record of what was ruled out, but
each one individually is a dead end, not a live thread.**

Rejected hypotheses, safe to treat as closed with no further action:
resource-sharing/duplication theory (#199–#201, #207), packing-density
theory (#201, #207), Quartus GUI stale-file-list risk (#212, resolved
by re-confirming the right RTL was actually built), device speed-grade
mixup (#225–#227, confirmed a one-off build mistake not a repo error),
and the programming-channel-decode-cost hypothesis (#209–#210,
returned a real negative result).

**The one item from this arc worth flagging as still genuinely open:**
`#206`/`#200`'s two queued Quartus diagnostic experiments
(`ROUTER_REGISTER_DUPLICATION`/`ROUTER_LCELL_INSERTION_AND_LOGIC_
DUPLICATION`/`ALLOW_REGISTER_DUPLICATION` off, and `OPTIMIZATION_
MODE "Aggressive Performance"`) — already correctly carried in
`current/START.md`'s own NEXT list, still not run. Correctly tracked,
not lost.

---

## Era 4: RAM / BRAM / DSP distribution system (#230–#297)

**Status: mostly complete and directly ancestral to this session's own
work — the RAM cell, adder, comparator, latch, mux/combiner tree,
sentinel system. Many pieces silicon-confirmed. This IS where the
SHELL/CORE/ADDON model (`#253`) and the ICM-portability regression
(`#263`) that this whole session's `#304`–`#324` arc addressed both
originate.**

**Two real, specific connections found that were disconnected from
current work until this audit — the actual valuable finds Alan asked
for:**

1. **`#230` (2026-08-08) already adopted the Tang Nano 20K**, with
   the same price point (~£33), the same ESP32-pairing idea, AND —
   critically — it already confirmed a full open-source toolchain
   exists for this exact board (Yosys + nextpnr-himbaechel + Apicula +
   openFPGALoader, with real working projects already found built
   against it). This session's `#326`–`#330` thread treated the Tang
   Nano idea as fresh and left the cross-vendor-toolchain question
   as "genuinely untested" — when `#230` had already done real
   research confirming an open chain exists. **This should have been
   found and built on before `#326` was written, not after.** Worth a
   proper connecting entry (see below).

2. **`#213`/`#214` (2026-08-08) already proposed the addon-timing-
   manifest concept** this session's `#311`–`#319` actually delivered
   real data for — including floating "~200 MHz" as a candidate
   no-addon Fmax floor, explicitly flagged as "not yet fixed, just a
   plausible number." This session's real measurements (`#308`:
   272.26 MHz, `#322`: 200.76 MHz, `#319`'s baseline: 137.8 MHz) land
   close enough to that 8-day-old guess to be worth Alan knowing about
   directly. `#214`'s own "addon manifest carries a timing field
   alongside size" proposal is now directly buildable using `#319`'s
   real 238.5%-Fmax-impact figure as the first real entry in it.

3. **`#232`/`#233` (2026-08-09)** already named the exact tension
   this session's `#314` traced fully: "the RAM cell is a divergence
   from one uniform cell type, and the hybrid version may require
   accepting that as a real compromise." `#263` (2026-08-10) then
   formally named the consequence (ICM portability collapse), and
   this session's `#304`–`#324` arc resolved it. Not orphaned — the
   throughline is real and continuous, just worth having named
   explicitly end-to-end in one place.

**Genuinely still open from this era, already correctly tracked in
`current/START.md`:** the RAM-side address-arbitration/retry-loop
mechanism (`#301`/`#302`), wiring the sentinel into a real chain,
wiring `shared_bram_arbiter_v1.v` into the full tree system, a real
3-level tree (only 2 proven), and the DSP bus-contention question
(`#270`) — flagged once, never revisited. Worth confirming this last
one is still wanted before it goes unaddressed indefinitely.

---

## Era 5: This session (#298–#330)

All current, all live — no audit needed, this is where the project
actually is right now.

---

## Summary: what this audit actually changes

**Nothing in `points.md` itself.** The value here is connective, not
corrective — three real, specific threads (Tang Nano tooling, the
addon-timing-manifest proposal, and the RAM-divergence-to-ICM-collapse
throughline) that were sitting disconnected across the ledger, now
named explicitly in one place so the next time any of them comes up,
the full history is immediately available rather than needing to be
rediscovered.

**Two small, genuinely orphaned items worth a conscious decision**
(`#10`, `#45`) — not urgent, but worth Alan saying "still wanted" or
"formally drop" rather than leaving indefinitely ambiguous.

**Nothing found that contradicts or invalidates current architecture.**
The eras are cleanly separable — pentacross-era material is safely
historical, stripped-cell-era material is foundational and complete,
and the RAM/BRAM/sentinel era flows directly and traceably into this
session's own work. The ledger, for its size, is in genuinely good
shape.
