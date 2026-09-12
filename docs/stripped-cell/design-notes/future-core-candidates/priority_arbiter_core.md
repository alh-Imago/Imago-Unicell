# Priority-arbiter core — a real candidate, not yet built (Alan, 2026-09-08)

## The real idea, as given

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

## Real, open questions Alan raised, not yet resolved here

- **New carrier function, or a modification to existing cores?**
  Alan's own framing: "a new carrier function... if there is space."
  Genuinely undecided whether this should be a brand new, distinct
  core type added alongside `ram`/`adder`/etc., or a variant/mode
  applied to an existing core. Real cost implications either way —
  a new core type means a new `core_select` value and its own real
  RTL from scratch; a mode on an existing core means touching
  already-proven, working RTL.
- **Universal, or scoped to one core?** Alan's own framing: "extend
  the ability across all cores simultaneously." Genuinely undecided
  whether this priority-input behavior should be a property every
  core in the shell gains, or something scoped to a specific new core
  used only where the priority behavior is actually needed. A
  universal change touches every core's own RTL; a scoped one is a
  smaller, more contained addition.
- **Fixed IN/IN/OUT roles need real, new port semantics.** Every
  existing core's own cardinal ports are symmetric by convention
  (any of N/S/E/W can be configured as upstream OR downstream,
  per-instance). This idea needs asymmetric, FIXED roles per port
  (west = priority in, north = secondary in, east = the only real
  out) — a genuinely different port model, not just a new field on
  the existing one. Worth real thought about whether the remaining
  two directions (south, and whichever of west/north isn't already a
  role) get any real role at all, or sit unused.

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

Design idea only. No RTL, no VM model, no scoping pass, no core_select
assignment. A real candidate for whenever there's real time to work
through the open questions above properly — not attempted here.
