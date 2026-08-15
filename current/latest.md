# Current State (as of 2026-08-13, session close — see `archeology/sessions/archive-2026-08-13.md` for the full blow-by-blow narrative, `points.md` #248-298 for the complete numbered ledger)

## What's real and confirmed right now

**The distribution system (mux tree, combiner tree, full shared-data
arithmetic) is proven complete, end to end, in simulation.** `#273`'s
own topology (3 starter chains, B genuinely shared across two real
joins, both mux tree levels + both combiner tree levels) passes clean.
Real Quartus data exists for the assembled system (`top_full_tree_
system_v1.v`): **275 ALM, 192.09 MHz, 655,360 real M20K bits confirmed
inferred** — after fixing THREE separate constant-propagation/synthesis
traps found via real Quartus builds, not predicted (`#283`/`#284`/
`#286`). `bram_controller_v2.v` (registered read address) is now the
standard memory core going forward — `v1` has a known hierarchy-depth
RAM-inference failure at 3+ levels deep.

**The sentinel system (`#279`'s design) is real, built, and hardware-
confirmed for the first time this session (`#291`).** Both of `#257`'s
originally-open questions (farthest-point addressing, the empty/full
status signal) are resolved with one coherent freeze/flag mechanism.
`sentinel_counter_v1.v`/`v2.v` are proven in simulation; `sentinel_
issp_bridge_v1.v` gives real JTAG access to the whole thing, confirmed
live on the actual Arria 10 (`Unicell-Q-sentinel-issp-test-v1`).

**The sentinel's own discrete-cell decomposition is proven equivalent
to the monolithic module** — `accumulator_cell_v1.v` (hold-and-refire,
direction-tagged, the free sign-bit tap for `diff<0`), `compare_cell_
v1.v` (stateless threshold check), `latch_cell_v1.v` (the sticky-latch
piece that closes the one honest gap the decomposition initially had).
All three are genuine new CORES per `#253`'s SHELL/CORE model, not a
new architectural category.

**A fourth architectural category is now formally named: HOST-
INTERFACE** (`#293`) — no cardinal ports, bridges the fabric to
something outside it (JTAG today). Real, recurring, hardware-confirmed
— but baked into the bitstream at synthesis time, no runtime toggle,
"used sparingly" per Alan's own framing.

**Real DSP/M20K floorplan data exists for `10AX066H2F34E2SG`**
(`#274`-`#277`): 8 DSP columns, 11 M20K columns, confirmed completely
disjoint. The Chip Planner GUI method itself is written up as reusable
documentation in `docs/shared/TOOLCHAIN_SETUP.md`, not just a one-off
finding.

**A living cross-cutting reference now exists for every core/wrapper
built so far:** `docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md` —
what's standalone-Quartus-proven vs. aggregate-only vs. sim-only,
updated as things get proven further.

## What's real but NOT yet resolved — the honest open items

1. **RESOLVED 2026-08-14 (`points.md` #306/#307):** `#298`'s remaining
   self-test bug was actually TWO distinct bugs, neither an
   intermittent single case as originally reported. A config-race
   (`S_CFGWAIT` sampling stale `cfg_step` as a level, landing the
   genuine config pulse on top of the first feed of every pass,
   deterministic every time, not just pass 3) and a separate
   test-stimulus flaw (fixed collect-count of 3 stopped guaranteeing
   the accumulator landed below the comparator's threshold once
   feed_target grew past 10 — every cell was behaving correctly, the
   TEST was wrong). Both fixed in `top_sentinel_discrete_test_v2.v`;
   `v1` retained unmodified as the historical bug record. Confirmed
   clean out to 34,000+ passes via a purpose-built debug trace, plus a
   new keepable regression testbench (`tb_top_sentinel_discrete_
   test_v2.v`, public-interface-only). The underlying cells themselves
   were never touched and remain fully proven. **`v2` is ready for a
   real Quartus build — the next concrete step, not yet done.**
2. **`sentinel_counter_v1.v`/`v2.v` are not yet wired into any real
   chain** — `out_wrap_pulse`/`feed_pulse`/`collect_pulse` remain
   unconnected to real chain events; the mechanism is proven standalone
   and over real JTAG, not yet integrated end-to-end with a running
   model.
3. **A real cross-instance shared-memory write-then-read** — OUT and IN
   sides of the distribution system still use separate `bram_
   controller_v2.v` instances (`shared_bram_arbiter_v1.v` exists and is
   proven standalone, `#282`, but not yet wired into the full tree
   system to replace the two-memory design).
4. **The DSP bus-contention question from `#270`** — real column data
   now exists, but nobody has reasoned through the contention question
   using it yet.
5. **A real 3-level tree** — both the mux tree and combiner tree are
   only proven at 2 levels; the design supports up to 3.
6. **No software/loader path exists for any of the new cell types** —
   every `cfg_valid`/`cfg_data` load has been driven by testbench-only
   stand-ins. No real `loader_fsm_v3.v` integration, and the compiler/
   VM software side still only understands the old full-cell format.
7. **Addon headroom work** (`#229`'s own plan) and the two long-queued
   Quartus experiments (`#206`'s OPTIMIZATION_MODE, `#200`'s
   duplication-flags diagnostic) — both genuinely meaningful now
   against real, confirmed baselines, neither started.

## A real design principle worth carrying forward

**Cumulative per-hop latency in any discrete-cell chain** (`#296`,
Alan's own generalization): every cell hop costs at least 1 real cycle,
minimum, and total observable delay is the SUM across the whole chain
— confirmed by direct measurement (`#295`'s own `drain_to_settled`
fix), not assumed. Worth remembering for anything built from multiple
cardinal-connected cells: a discrete system is EVENTUALLY, CORRECTLY
consistent, not cycle-exact with a monolithic reference — that's how
real hardware pipelines behave, not a defect.

## Also queued, not yet started (carried forward from prior sessions)

The `#210` programming-delivery architecture decision (single-hop/
addressed vs. accepted broadcast). The VM core rebuild (`#216`/`#217`,
gap analysis at `current/VM_CORE_GAP_ANALYSIS.md`) — still deliberately
not started while RTL settles. The BRAM+DSP hybrid integration
(`#220`) — the RAM-cell chain is its planned front door, per `#232`.
