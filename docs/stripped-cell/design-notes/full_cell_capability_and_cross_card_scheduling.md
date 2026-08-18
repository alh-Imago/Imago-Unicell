# The FULL cell's own capability with nano's communication layer, and cross-card scheduling

*Captured 2026-08-17 (day 3), a real, unplanned offshoot from the RAM
interface work. Alan's own framing: "here a complete off shoot."*

## Idea 1: keep the FULL cell's richer capability, swap its communication layer

**What "the full fat unicell" actually refers to, confirmed against
the real record (`points.md #314`), not assumed:** `unicell64_v3.v`
(Protocol v3.1) — a real, archived, older cell design with a 128-bit
config surface split across four named segments (core `cmd_latch
[31:0]`, methodology latch `[63:32]`, routing latch `[95:64]`, one
still-free segment). Genuinely different from both the standalone nano
cell and the current super carrier shell (Unicell-S).

**Its real, known problem, confirmed throughout this session's own
archival work:** its communication layer — an addressed bus, `cmd_bus`,
wired-OR, the whole shared-resource contention model — is what made it
architecturally incompatible with the current cardinal-only philosophy,
not necessarily its own richer core capability.

**Alan's proposal:** keep the FULL cell's own richer capability, but
give it nano's own proven, local, cardinal-only, ack-based
communication layer instead of its original addressed-bus one.

**Why this is architecturally coherent, not a random tangent:** it
applies the exact same SHELL/CORE separation this project already
proved works (`#253`) to material that was archived, not obsolete.
Separates "what it computes/configures" (FULL's own richer logic) from
"how it talks to neighbors" (the part that was actually broken) — and
the broken part goes away while the capability stays.

**A real, checked size comparison, not assumed to just fit:** FULL's
own 128-bit config surface is comparable in total size to nano's own
128-bit `cmd_latch` (confirmed directly, `CELL_INTERNALS.md`) — just
organized differently (dedicated methodology/routing segments vs.
nano's more compact field layout). The raw bit budget is plausible for
this swap; the internal reorganization work itself is real, unstarted
design work.

## Idea 2: counter-scheduled cross-zone/cross-card bursts (TDM)

**Alan's proposal:** each zone gets a guaranteed, non-contending turn
to send a data burst on a shared long-distance channel, scheduled by a
counter — e.g. 1 in every 16 cycles, a real, standard Time-Division
Multiplexing (TDM) scheme.

**Directly connects to an already-closed, real physical finding
(`#325`), not a competing proposal to it:** the IEI Mustang-F100-A10
has no external transceiver breakout at all — its only physical
connectors are the PCIe x8 edge connector, 12V power, and JTAG. Direct
card-to-card meshing via the Arria 10's own transceivers isn't
possible without invasive board rework. The already-decided real path
for genuine multi-card interconnect is PCIe peer-to-peer via a proper
switched backplane (or, longer-term, a network smart NIC).

**TDM scheduling is the LOGICAL layer that would ride on top of that
already-decided physical transport, not an alternative to it.**
Multiple zones sharing one physical channel (the PCIe/backplane link),
each getting a guaranteed, scheduled turn rather than arbitrary bus
contention — a real, well-established technique for exactly this
situation.

## The real self-check: does this reintroduce the bus wiring nano avoided?

A real, important question Alan raised directly against his own idea,
worth taking seriously rather than reassured away.

**Where the risk is genuinely real:** if every zone had a direct wire
straight to a central scheduling point, that would be a bus by another
name — TDM scheduling stops CONTENTION, but the wiring itself would
still be exactly what nano was built to avoid (long shared runs, many
taps, real routing congestion — the FULL cell's own real problems).

**Where it's genuinely avoidable, and Alan's own "set nodes" framing is
the right fix:** reuse the EXACT SAME header/collector/queue pattern
already designed and simulation-tested for the RAM interface
(`#381`/`#382`). That mechanism is already a chain of pure local
cardinal hops converging on a shared destination, zero bus wiring
anywhere in it. The same pattern applies here directly -- each zone
relays toward a meeting point through ordinary neighbor-to-neighbor
hops, not a direct wire to a central bus. No new wiring class gets
introduced; it's the same proven pattern, aimed at a different
destination.

**Where a genuinely shared, bus-like point is unavoidable, stated
precisely, not vaguely:** the physical card boundary itself. `#325`
already established this isn't a design choice -- this board has
exactly one PCIe edge connector, nothing else. Every zone that wants
to reach another card has to converge on that single physical resource
SOMEWHERE, regardless of how the wiring inside the card is arranged.
**This is where TDM scheduling actually belongs -- applied at that one,
real, unavoidable point, not distributed through the fabric.**

## The honest shape of the conclusion

The slowdown risk Alan raised is real, but LOCALIZED to exactly one
place -- the PCIe boundary crossing -- not spread across the design.
Everything on the way to that point can stay pure cardinal-only chain
relay, the same proven pattern as the RAM interface work, with its own
already-quantified real cost as the right precedent (`#381`'s own
2-cycle reconfigure overhead finding: "yes, coordination costs
something, and here's exactly what and where," not "assume it's
free").

## Real, honest, unstarted work, stated plainly

1. Idea 1 (FULL cell capability + nano communication layer) has no
   design work done on the actual field reorganization yet -- only the
   size-budget plausibility check above.
2. Idea 2's real TDM scheduling mechanism (the counter, the slot-width
   choice, how a zone knows its own turn) has not been designed.
3. The header/collector/queue reuse for cross-zone relay has not been
   adapted from its RAM-specific design (`#382`) to this different
   destination -- a real, separate adaptation, not assumed automatic.
4. Neither idea has any RTL, simulation, or measurement -- this note
   captures a real, coherent design direction and a real self-check
   resolved, not a decision to build either.
