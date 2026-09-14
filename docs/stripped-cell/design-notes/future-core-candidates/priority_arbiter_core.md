# Priority-arbiter core — a real candidate, not yet built (Alan, 2026-09-08)

## Real, resolved decision (2026-09-08): a separate core, not a shell function

Checked directly, not assumed: every existing core's own arrival logic
(`upstream_val = (sel_n?data_in_n:0)|(sel_s?...)|...`) is baked into
each core's own RTL file, and every existing core's own cardinal ports
are symmetric by convention (any of N/S/E/W can be upstream or
downstream, per instance). A shell-level version of this would mean
ripping out and replacing that logic inside every one of the 10 real
cores, for a benefit only some designs would ever use -- a much
bigger, riskier change than the addon chain's own shell-level move
ever was (that was pure OUTPUT transformation, inserted cleanly after
an already-existing mux; this is INPUT handling, genuinely different
in kind). Real, honest conclusion: this becomes its own core, its own
cell -- the "new carrier function, or a modification to existing
cores" question this note originally left open is resolved.

## Real refinements to the original idea, from Alan's own direct
## follow-up, each correcting or sharpening the original framing

- **Uses the same real `upstream_mask`/`downstream_mask` convention
  every other core already has, not a bespoke addressing scheme.**
  The core needs to be aware of whatever real connections the shell
  has configured for it, the same way every other core already is --
  not a foreign, incompatible port model layered on top.
- **A real, documented expectation, not a hardware-enforced check:**
  at least TWO real input directions need to be enabled via
  `upstream_mask`, or there's genuinely no point using this core --
  with only one real input, it degrades to a plain relay carrying
  more complexity than it needs. Named plainly for whoever configures
  it, the same way no other core validates its own config either.
- **Priority order must be a real, configurable field, NOT a fixed
  value.** A hardcoded "west always wins" would force every design
  using this core to physically route its own priority signal to one
  specific side regardless of what's actually convenient for that
  design's own layout -- a real planning trap, not a minor
  inconvenience. Instead: each of the four real cardinal directions
  gets its own small, configurable rank field (2 bits is enough for 4
  real ranks) -- priority becomes a genuine per-instance
  configuration, like every other field on every other core, not a
  constraint baked into the floorplan.
- **The real output side needs nothing new at all.** A normal
  `downstream_mask`, exactly like every other core already has -- no
  priority semantics attached to output, only to which of the
  (multiple) real, competing inputs gets taken first.

**A real, updated `cfg_data` field shape, following directly from the
above (not yet built, a real starting point for whenever this is
picked up):**
```
[5:0]   upstream_mask     — SAME real convention as every other core
[11:6]  downstream_mask   — SAME real convention, no priority attached
[13:12] priority_rank_n   — 0 = highest priority, 3 = lowest
[15:14] priority_rank_s
[17:16] priority_rank_e
[19:18] priority_rank_w
```
Real, honest scope for the actual arbitration logic this implies: a
genuine priority encoder over whichever directions are BOTH enabled
(`upstream_mask`) AND currently arrived, selecting the arrived
direction with the lowest configured rank -- not a fixed two-input
compare, a real N-way (up to 4) configurable-priority selector.

## Real, second refinement (2026-09-08): strict priority alone starves
## lower-ranked ports under sustained load — a real, separate
## scheduling mode added, not a replacement

**The real problem, caught directly, not theoretical:** with pure
strict priority, if the highest-ranked enabled direction has
continuous data, the other enabled directions never get serviced at
all — not "less often," genuinely never, for as long as the top-
ranked input keeps arriving. A real design relying on this core for
more than an occasional tie-break would need very careful traffic
planning to avoid starving its own lower-priority inputs completely.

**The real fix: a second, selectable scheduling mode, not a
replacement for strict priority** — some real designs genuinely want
"this input always wins when present" (the original, simpler
behavior); others need real, weighted fairness. Both are real,
legitimate needs, so both stay available via one new, real
`scheduling_mode` bit:

- `scheduling_mode = 0`: strict priority (the original design, above,
  unchanged).
- `scheduling_mode = 1`: weighted round-robin, reusing the SAME
  `priority_rank_*` fields as real, configurable WEIGHTS instead of
  absolute ranks (0 is genuinely the lowest possible weight here, not
  "highest priority" — real, different meaning depending on mode, the
  same field, no new field needed for weights specifically).

**The real, concrete mechanism, a genuine credit accumulator (the
same real technique real network schedulers use for weighted
fairness, not an invented one):** one real, internal credit register
per direction (`credit_n/s/e/w`, 8 bits — internal scheduler state,
NOT part of `cfg_data`, not user-visible or configurable directly).
Every real arbitration cycle:
- Every direction that's a genuine candidate (enabled AND arrived)
  gets its own configured weight ADDED to its own credit.
- The candidate with the HIGHEST current credit wins (ties broken by
  the same fixed N>S>E>W order as strict mode).
- The WINNING direction's own credit resets to 0; every other
  candidate's own credit keeps accumulating.

**Real, honest, worked-through consequence of this mechanism, checked
by hand before committing to it:** a port with 3x another's weight
wins roughly 3 times for every 1 the other wins, and — because credit
accumulates steadily every cycle rather than in a lump sum — the real
service pattern comes out genuinely interleaved (something like
A,A,A,B,A,A,A,B for a real 3:1 weight ratio), not clustered into "all
of A's turns, then all of B's."

**A real, honest limitation, stated plainly rather than oversold:**
this produces a proportionally FAIR pattern matching the configured
weight ratio, not an exact, pre-specified sequence a user might write
down by hand (e.g. Alan's own illustrative "1,2,1,2,1,3" example for
three weighted inputs). Building a core that reproduces an arbitrary,
exact, user-specified sequence would need a real sequence table/
generator — a genuinely bigger, different kind of core — not
attempted here. The credit-accumulator approach gets the real, stated
goal (no starvation, weight-proportional service) with a small,
bounded, purely-additive hardware cost instead.

**A real, updated `cfg_data` field shape, adding exactly one new bit:**
```
[5:0]   upstream_mask     — SAME real convention as every other core
[11:6]  downstream_mask   — SAME real convention, no priority attached
[13:12] priority_rank_n   — strict mode: 0=highest,3=lowest. RR mode:
[15:14] priority_rank_s     relative weight, 0=lowest possible weight
[17:16] priority_rank_e
[19:18] priority_rank_w
[20]    scheduling_mode   — 0=strict priority, 1=weighted round-robin
[40:21] addon_config      — 20 bits, shifted by 1 bit from the first
                            draft to make room for scheduling_mode
[63:41] reserved
```



A cell with (at least) two real, distinct INPUT roles, not the usual
symmetric cardinal wiring every existing core uses — a strict priority
order between them, not a merge:

- If data is present on the priority input (west, in Alan's own
  framing), take it. Data waiting on the other input (north) is
  genuinely held back — not lost, not combined, just waits its turn.
- Only once the priority input is empty does the cell take from the
  second input.
- Output goes to a known, fixed direction (east, in Alan's own
  framing) — meaning this core has a genuinely fixed IN/IN/OUT role
  per port, not the current uniform "any direction can be upstream or
  downstream depending on configuration" model every existing core
  shares.

Alan's own real framing of the tradeoff: this means some chains would
have to wait their turn rather than proceed immediately — a real,
deliberate cost, not an oversight.

**Real, honest note (2026-09-08): the fixed-role framing above is
superseded by the refinements section above it** — the real, current
design uses configurable ranks over the normal symmetric port
convention, not fixed west/north/east roles. Kept here for its own
real history, not as the current plan.

## Confirmed directly before writing anything else: nothing like this
## exists in the current lineage

Checked the real RTL for every cardinal-port core (`ram_cell_v3.v`,
`branch_cell_v3.v`, `adder_cell_v1.v`, `latch_cell_v3.v`,
`compare_cell_v3.v`) directly, not assumed from memory. Every single
one uses the identical real pattern:

```verilog
wire [31:0] upstream_val = (sel_n ? data_in_n : 0) |
                           (sel_s ? data_in_s : 0) |
                           (sel_e ? data_in_e : 0) |
                           (sel_w ? data_in_w : 0);
```

A bitwise OR across every simultaneously-arrived, matched direction —
not a priority chain. This is the exact, confirmed mechanism behind
the real "adder OR-merges simultaneous arrivals" bug found this same
session (`points.md #686`), and the reason so much of today's own
work (the DAG relay's trigger-chain-length engineering, `ashr`'s own
stagger cells, the shared-producer daisy-chain's strict ordering
requirement) exists at all — every one of those is careful TIMING
built to avoid two things landing on the same tick, because nothing
in the hardware itself resolves that collision by rule.

**So this is a genuinely new mechanism, not a repurposing of anything
already built** — worth being clear about, since it would have been
easy to assume some existing core already did this and build on that
assumption.

## The real, honest case for building it

If this held true across the fabric, a large fraction of today's own
hop-count/ordering engineering becomes unnecessary — correctness would
come from the arbitration RULE itself (west always wins, north always
waits), not from getting relay-path lengths exactly right. That is a
real, substantial simplification if it holds, not a minor convenience.

## Real, open questions Alan raised — status as of 2026-09-08

- **New carrier function, or a modification to existing cores?**
  RESOLVED (2026-09-08, see above): a separate core. The structural
  mismatch (input-arrival logic baked into each core's own RTL, plus
  the port-role question below) settles this for real.
- **Universal, or scoped to one core?** RESOLVED (2026-09-08): scoped
  to its own, separate core -- a universal shell-level change would
  touch every core's own timing-critical arrival path for a benefit
  most designs would never use.
- **Fixed IN/IN/OUT roles need real, new port semantics.** RESOLVED
  DIFFERENTLY than first framed (2026-09-08): not fixed roles at all
  -- the real, current design (see refinements section above) uses
  the SAME symmetric `upstream_mask`/`downstream_mask` convention
  every other core has, with a real, per-direction configurable
  priority RANK instead of a hardcoded role. This is a genuine
  improvement on the original framing, not just a resolution of it --
  a fixed-role core would have forced every design using it into a
  specific physical layout; a configurable-rank one doesn't.

## A real, honest timing concern worth naming before this goes further

Not confirmed either way, but worth flagging directly, matching the
same real concern this directory's own README already raised about
the bitwise divider: a genuine priority CHAIN (check west, then
fall through to north) is a longer real combinational path per tick
than the current flat OR-combine every core uses today. This
architecture's entire premise is wire-delay-based timing with a real,
hard per-hop budget (the super carrier shell's own real number,
200.76 MHz, `#322`). Whether a real priority-chain implementation
fits inside that budget, or needs its own extra tick, is a real,
unanswered question — not something to discover after building it.

## Status

Real, resolved design decisions (2026-09-08): a separate core (not a
shell function), using the standard `upstream_mask`/`downstream_mask`
convention with a real, per-direction configurable priority rank
instead of fixed roles -- see the refinements section above for the
real, updated `cfg_data` field shape this implies.

Still genuinely open, not attempted here: the real timing question
(does a configurable, up-to-4-way priority encoder fit the real
200.76 MHz budget, `#322`, any better or worse than the original
two-input framing did -- not yet checked either way) and the actual
RTL itself. No RTL, no VM model, no `core_select` assignment yet. A
real candidate for a real scoping-then-build-then-test pass whenever
there's time to do it properly -- the design itself is now settled
enough to start that pass from, which it wasn't before today.
