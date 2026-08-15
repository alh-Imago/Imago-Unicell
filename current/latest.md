# Current State (as of 2026-08-15, session close -- see `archeology/sessions/archive-2026-08-15.md` for the full narrative, `points.md` #301-324 for the complete numbered ledger)

## THE MILESTONE (read this first)

**The architectural risk that could have ended this project's scaling
ambitions is retired, with real measurement behind it, not just a
plan.** The original bus-based architecture had a genuine scalability
ceiling (contention) that `#153` moved away from via cardinal point-
to-point wiring -- necessary, but it made core type a synthesis-time-
fixed property (`#253`), which broke ICM/multimodel portability
(`#263`). That regression sat open until today. `#304` through `#323`
closed it for real: `unicell_super_v1.v` -- one cell, all 6 real cores
(nano, RAM, adder, accumulator, comparator, latch) physically present,
individually selectable via an 80-bit `SUPER_LATCH`, mutually
exclusive -- built, sim-verified, and real-Quartus-confirmed. The
actual isolation/selection cost is 25.9 ALM, smaller than any single
one of the bigger cores it holds together (`#323`). This is strictly
MORE capability than the FULL cell ever had (heterogeneous selectable
cores never existed in any prior generation, `#314`), on an
architecture that doesn't carry the original bus-contention flaw, with
real expansion room built in from the start (`#317`). See `#324` for
the full framing.

**Consequence: the VM, the ICM file format, and the compiler's job are
now genuinely well-scoped, not open-ended.** `SUPER_LATCH[79:0]` is a
real, stable, measured target to build against -- the ICM format's own
missing core-type-selector field (`#314`'s named gap) has an exact
shape to fill now. None of that work has started yet.

## What's real and confirmed right now

**The super carrier shell exists and works.** `unicell_super_v1.v`
(`#320`) holds all 6 cores, individually selectable, sim-verified
correct and isolated across every one. `top_unicell_super_test_v1.v`
(`#321`) is a real, synthesizable self-test — Quartus-confirmed: 213
ALM, 257 registers, `clk_div` 200.76 MHz (8.03x margin over the real 25
MHz target, the best of any build this session) (`#322`). Real per-
entity breakdown (`#323`): six cores combined = 116.5 ALM, the
selection/isolation mechanism itself = only 25.9 ALM, the self-test
FSM = 69.9 ALM (larger than the mechanism it tests). A real, separate
finding: adder's actual math costs 8.0 ALM, its own handshake wrapper
costs 21.0 ALM — protocol overhead dominating computation.

**Two real architectural questions answered precisely against RTL,
not assumed** (`#318`): RAM's mechanism can't fold into the shell
because the shell's own `ready_out` is a static config flag while RAM
needs a dynamic state-tracking signal that doesn't exist there yet.
The BRAM controller's 40-bit interface is fully contained to its own
connection with the physical M20K primitive — the rest of the system
stays 32-bit throughout, zero DSP involvement (confirmed disjoint
hardware resources).

**A real, trustworthy addon-cost delta finally exists** (`#319`) — a
fresh, same-session rebuild of the plain `top_stripped_zone50_v1`
baseline (6,214 ALM, 137.8 MHz) against the addon-augmented build
(`#316`'s 21,037 ALM, 94.73 MHz): the three addons cost **238.5% more
ALM per cell** than the base cell they sit on top of — a real,
substantial, honestly-reported cost. This supersedes `#149`'s own
flagged-unreliable original baseline entirely.

**Everything from the earlier part of today's session remains
current** — `#298`'s bug fully resolved (`#306`-`#308`), the first
real ADDONs built and cost-measured (`#311`-`#313`), the FULL cell
audit closing the long-queued deep-dive (`#309`-`#310`), the three-
generation ICM history traced (`#314`), and the union-sized core-
config accounting (`#315`, `#317`).

## What's real but NOT yet resolved -- the honest open items

1. **No ICM v3 format exists yet** incorporating a real core-type-
   selector field. This is the concrete next step per `#324`'s own
   framing — the format has a clear target to build against now.
2. **No VM logic exists yet** that interprets `core_select`/`core_
   config`/`addon_config` and dispatches accordingly.
3. **No compiler path exists yet** that lowers a higher-level cell/
   core description down to real `SUPER_LATCH` bits.
4. **The register-count side of `#323`'s own entity report doesn't
   fully add up** — `unicell_super_v1`'s own reported register count
   (4, excluding children) seems too low given the 80-bit `super_
   latch`. Flagged honestly as unresolved, not guessed at.
5. **`unicell_super_v1.v`'s nano selection is genuinely incomplete** —
   command-cell mode, feedback, and the dynamic-reprogramming channel
   are all tied to safe defaults, out of scope for this first build.
6. **`latch_in`/`latch_A_dis`** (`#310`'s core-shaped pair) remain
   completely absent from every core, including the super cell.
7. **The RAM-side address-arbitration/retry-loop mechanism** (`#301`/
   `#302`) — real direction, explicitly needs testing before trust.
8. **`sentinel_counter_v1.v`/`v2.v` still not wired into any real
   chain**; **`shared_bram_arbiter_v1.v` still not wired into the full
   tree system** — both carried forward unchanged.
9. **The two long-queued Quartus diagnostic experiments** (duplication
   flags, aggressive optimization mode) — still not started.

## Also queued, not yet started (carried forward from prior sessions)

The `#210` programming-delivery architecture decision. The VM core
rebuild (`#216`/`#217`) — now directly relevant to item 2 above. The
BRAM+DSP hybrid integration (`#220`). The longer-horizon FPGA dev-tool
vision (`#305`).

## Next session, the real work per Alan's own framing (2026-08-15)

1. Design and build a real ICM v3 format with a core-type-selector
   field, targeting `unicell_super_v1.v`'s own real `SUPER_LATCH[79:0]`
   layout directly.
2. VM logic to interpret and dispatch on `core_select`/`core_config`/
   `addon_config`.
3. A compiler path from higher-level cell/core description down to
   real `SUPER_LATCH` bits.
4. Whenever convenient: resolve `#323`'s own register-count discrepancy
   via Chip Planner, and consider a real host/JTAG-wrapped version of
   the super cell for a fully clean comparison against `#319`'s
   baseline.
