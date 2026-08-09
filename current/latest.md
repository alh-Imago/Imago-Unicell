# Current State (as of 2026-08-08 — see `archeology/sessions/archive-2026-08-08.md` for the full narrative)

Everything through 2026-08-08 (points.md #180-#229) has been moved to
`archeology/sessions/archive-2026-08-08.md`, most-recent-first within its
own sections, preserved as written. This file starts fresh as the fast
catch-up document, per its own stated purpose.

## WAITING ON YOU — RAM cell RTL draft (points.md #231-#235)

While you were out: a design-note thread on a "RAM cell" (minimal
latch-only cousin of the compute cell, chain direction fixed at config
time, ack-reuse as the pull-refill trigger, framed as the feeding-buffer
interface to real BRAM per `#232`) turned into a first RTL draft —
`fpga/verilog/ram_cell_v1.v` + two passing iverilog testbenches
(`#235`). **You specifically said you need to confirm the read/write
mechanism yourself before this is trusted — nothing past iverilog sim
has been done, no Quartus, no ALM cost, no `#229` ratio yet.** Read
`#231` through `#235` in order before touching this. cfg_data field
layout is a first proposal, not frozen.

## CRITICAL — read this before trusting any "X ALM/cell" figure (points.md #228)

**`#171`'s old "3.36 ALM/cell" isolated-25-cell baseline is INVALID.**
Confirmed directly: only 3 of that test's 25 nominal cell/command-cell
instances were ever genuinely live in its stimulus — the other 22 were
fully pruned by Quartus (absent entirely, not just small). "3.36
ALM/cell" was total design ALM (dominated by 25 live wrappers + top-level
glue) divided by a cell count where 88% of the cells contributed zero. It
never measured what one active cell costs.

**Use this instead:** cells known to be genuinely live, receiving real
ongoing cardinal traffic — the interior-row samples from `#209`
(750-cell) and `#224` (240-cell) both land at ~100-106 ALM/cell,
consistently, across two independent scales. That's the real reference
point going forward.

## Where things stand

**The 750-cell zone build (`top_stripped_zone750_v5`) is the active
reference build:** 89,818 ALM, 259.61 MHz, -2.852ns worst slack (`#198`).
Worst-path mechanisms found this session, all showing the same
placement-scatter signature (LAB-column spread far beyond what a
logically-adjacent connection should need) regardless of which specific
signal is involved: a cell-internal self-loop (`#207`), an ordinary
two-arrival compute write (`#211`), the wrapper's own JTAG/host daisy-
chain bus (`#221`), and a two-hop `cmd_latch[13]`/`ready_bit` cascade
recurring across multiple independent builds (`#227`). None of the five
hypotheses tested this session for the underlying per-cell-cost question
(programming-channel decode, placement congestion, resource-sharing QSF
flags, RTL drift, device speed grade) turned out to be the explanation —
see the CRITICAL section above for why the question itself needed
correcting.

**Real per-card capacity estimate (`#229`):** ~1500-1700 cells at an 80%
utilization ceiling, extrapolated from two real builds (240 cells at 11%,
750 cells at 36%). This is a ~7-8x downward revision from
`current/PLAN.md`'s original 16-zone/12,000-cell per-card target — not
yet fed back into the multi-card/lab-cage planning, flagged for whenever
that's revisited.

**Strategic shift on target speed (`#213`/`#214`):** stability over
maximum Fmax. Target a reliable, always-passing floor (Alan floated
~200 MHz, not fixed) rather than chasing the highest Fmax a minimal,
addon-free build happens to hit. Every future addon carries both a size
AND a timing cost in its manifest, explicitly not assumed additive
across combinations.

**Minimum-spec clarification (`#215`):** the base cell's floor already
includes everything designed and proven (hold/reemit/update/self-update/
freeze/cardinal programming) — these are baseline, not addons subject to
the size+timing manifest. That framework applies only to genuinely new
capability layered beyond this floor.

**Programming channel, confirmed correct (`#211`):** single self-
describing `{3-bit ID, 16-bit data}` word per field-write (`#140`'s
design), matches the RTL exactly. The channel's current DELIVERY
(broadcast to every cell in a row, not point-to-point) is a real,
still-open architecture question (`#210`) — options on the table:
genuinely single-hop/addressed delivery matching the project's cardinal
philosophy, or accept full broadcast as the load-bearing cost of genuine
any-cell-any-time reprogrammability. Not decided.

**VM core rebuild — mapped, not started (`#216`/`#217`):** zero of the 77
root-level Python files target the stripped/nano cell; 35 explicitly
target the old full-cell format. Two genuinely current files exist
(`nano/unicell_automaton_v1.py`, `unicell_gate_core.py`) — real, RTL-
tracking simulation core, not stale. Two reusable architecture patterns
found in the old-format files (`gpu_array.py`'s CPU/GPU backend,
`companion.py`'s `attach_ai()`). Full gap analysis at
`current/VM_CORE_GAP_ANALYSIS.md`. Deliberately not started — RTL still
settling, matching the project's own "substrate before models"
discipline.

## NEXT (agreed order, 2026-08-08 — this is what a fresh session picks up first)

1. **Drop the target clock to a level that reliably PASSES timing** — the
   real floor per `#213`/`#214`, not a chased maximum. This is the
   prerequisite for everything below.
2. **That floor becomes genuine headroom for future addons**, not a
   number that only holds for today's minimal feature set.
3. **Every future addon gets tested against a FULL-CARD build
   specifically**, not small-scale — `#224` already showed small-scale
   numbers don't necessarily predict behavior near real capacity.
4. **Build a real map of addon timing costs** from those full-card
   measurements — the size+timing manifest `#214` specified, with an
   explicit "measure at real scale" requirement.

**Also queued, not yet started:** the `#210` programming-delivery
architecture decision (single-hop/addressed vs. accepted broadcast);
the VM core rebuild (`#216`, once RTL is stable); the BRAM+DSP hybrid
integration (`#220`, design already substantially in `current/PLAN.md`);
feeding `#229`'s corrected capacity estimate back into the multi-card/
lab-cage planning.
