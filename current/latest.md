# Current State (as of 2026-08-15, session close — see `archeology/sessions/archive-2026-08-15.md` for the full narrative, `points.md` #301-317 for the complete numbered ledger)

## What's real and confirmed right now

**`#298`'s sentinel self-test bug is fully resolved.** Root-caused as
TWO distinct, fully deterministic bugs (not one intermittent case as
originally reported) -- a config-race in `S_CFGWAIT` (`#306`) and a
separate test-stimulus flaw where a fixed collect-count stopped
guaranteeing correctness once the varying-`feed_target` mechanism
pushed past 10 (`#307`). Both fixed in `top_sentinel_discrete_test_
v2.v`. Sim-confirmed clean to 34,000+ passes, and now real-Quartus-
confirmed too: Flow Successful, `clk_div` 272.26 MHz, no failing paths
(`#308`).

**The first real ADDONs exist anywhere in the nano line.**
`shift_lane_addon_v1.v`, `nibble_mask_addon_v1.v`, `invert_addon_v1.v`
(`#311`) -- faithfully ported from `unicell64_v3.v`'s own proven shift/
lane/nibble-mask/invert mechanisms, sim-verified with hand-computed and
independently cross-checked expected values, full existing regression
suite re-confirmed clean afterward. A real correction was caught before
building: lane-cut is coupled to shift-OUT only, not an independent
mechanism as earlier framing implied.

**A real A/B cost-comparison build exists and has real Quartus data.**
`top_stripped_zone50_addons_v1.v` (`#312`) wires the three addons into
every cell of the proven 50-cell zone topology, deliberately at the
same scale as `#148`'s own baseline to avoid `#228`'s pruning trap.
Alan's real build: Flow Successful, 21,037 ALM, 8,463 registers,
`clk_div` 94.73 MHz -- comfortably over the real 25 MHz requirement
(`#316`). **NOT yet compared against a clean baseline delta** -- `#149`'s
own original zone50 figure predates the SDC-discipline fix by 5 days
and doesn't match any other trusted per-cell reference in this
project's history, so it was flagged as untrustworthy rather than used
anyway. A fresh, same-session rebuild of the plain baseline is the
next concrete step.

**The FULL cell's remaining mechanisms have been fully, ground-truth
audited against the nano line** (`#309`), closing the long-queued
"Cell Mechanics Deep Dive." Sorted into already-ported, genuine
candidates (shift/lane/nibble-mask/invert, now built; `latch_in`/
`latch_A_dis`, not yet started), suspect/unverified (`dtype`/
`priority`/`trace`/`breakpoint` -- three of these were already flagged
by `current/PLAN.md`'s own queue as never once exercised), and
structurally-incompatible (bus-addressed boot/config, `CMD_ARRAY_
RESET`, `one_shot`/`loop_back` -- already solved differently by the
accumulator's own design).

**The "super carrier shell" / fat-unicell direction has a real,
measured cost picture now, not just a concept.** Alan's own key
refinement: cores are mutually exclusive (config-time selectable, one
active at a time), so the shared core-config latch only needs sizing
to the WIDEST single core's requirement -- a union, not a struct.
Measured directly from every real core's own `cfg_data` usage: **42
bits (RAM, widest)**, not the naive 124-bit sum of all six (`#315`).
Real total: shell/routing(13) + core-union(42) + core-selector(~3,
must stay genuinely extensible per `#317`) + addon(20, `#313`) = **~78
bits total** -- leaner than the FULL cell's own 128-bit total width,
while covering strictly MORE real capability than the FULL cell ever
had (heterogeneous selectable cores never existed in any prior
generation at all, confirmed via a full three-generation trace, `#314`).

**A real, pre-existing gap found in the `.icm` file format itself**
(`#314`): the current format (`docs/shared/ICM_FORMAT.md`, `gate_
states.py`) is grounded in the OLDEST cell generation (`unicell.v`
Protocol v2.3, iCEBreaker era) -- never updated for the FULL fat
unicell's (`unicell64_v3.v`, Protocol v3.1) own real capability
expansion. This predates the current session entirely. Building a real
core-type-selector field for `.icm` records is genuinely new work, not
a restoration of anything that existed before.

**A real thread-recovery gap was found and named directly:** a prior
conversation had reasoned through the fat-unicell/shift-lane/dev-tool
material in real depth, ended with an explicit "yes please note it,"
but only part of it (the MAN-file thread) actually reached `points.md`
before that conversation closed. Recovered and logged properly
(`#303`-`#305`). Worth a closing gut-check on any future exploratory
session: confirm everything marked to-be-logged is actually logged
before the conversation ends.

## What's real but NOT yet resolved -- the honest open items

1. **`top_stripped_zone50_v1` needs a fresh, same-session rebuild** --
   the only trustworthy way to get a real ALM/Fmax delta for the
   addon cost, since `#149`'s own original baseline predates the
   SDC-discipline fix and is flagged as unreliable for comparison.
2. **The super carrier shell itself is unbuilt** -- `#315`'s 42-bit
   union-sized core-config accounting and `#317`'s extensibility
   requirement are real design constraints now, but no RTL exists for
   a cell physically containing multiple selectable cores yet.
3. **`latch_in`/`latch_A_dis`** (`#310`'s core-shaped pair, changes the
   cell's own capture/firing state rather than just the data path) --
   completely unstarted, a separate, harder design question from the
   addon-shaped four.
4. **The RAM-side address-arbitration/retry-loop mechanism** (`#301`/
   `#302`) -- real architectural direction, explicitly flagged as
   needing real testing before trust, several open questions
   (retry-loop depth, priority-tier semantics, stale-vs-current
   delivery, multi-chain out>in traffic asymmetry) genuinely
   unresolved.
5. **`sentinel_counter_v1.v`/`v2.v` still not wired into any real
   chain** -- carried forward unchanged from prior sessions.
6. **`shared_bram_arbiter_v1.v` still not wired into the full tree
   system** -- carried forward unchanged.
7. **The two long-queued Quartus diagnostic experiments** (duplication
   flags, aggressive optimization mode) -- still not started.
8. **No software/loader path exists for any new cell type** --
   carried forward unchanged.

## Also queued, not yet started (carried forward from prior sessions)

The `#210` programming-delivery architecture decision. The VM core
rebuild (`#216`/`#217`). The BRAM+DSP hybrid integration (`#220`). The
longer-horizon FPGA dev-tool vision (`#305`) -- design cores/wrappers
at a higher level, compile down to real Verilog, explicitly separate
from and downstream of the near-term hardware sequence.

## Next session, agreed order (2026-08-15)

1. Fresh, same-session rebuild of the plain `top_stripped_zone50_v1`
   baseline -- compute the real, trustworthy addon-cost delta.
2. Build the super carrier shell itself -- core-type selector (kept
   genuinely extensible, `#317`), the union-sized 42-bit core-config
   latch (`#315`), wired alongside the existing addon layer (`#311`/
   `#313`).
