# Hex-N cell internals — 6x8 bring-up unit, v0.1

Status: scoping, resolved through direct design discussion (2026-09-29). No RTL yet.
This records what was decided and why, so it isn't lost to chat history before RTL starts.

## Why 6x8, not 6x16

The original spec (6 faces x 16 lines/face = 96 lines/cell) cannot be a standalone,
fully-instrumented bring-up unit on the Tang Nano 20K: the board has only 66 I/O
pins total (confirmed against the real Apicula chip database, not an estimate), and
96 raw lines already exceeds that before spending a single pin on clock, reset, or
the BL616 programming link.

6x8 (48 lines/cell) fits with room to spare (66 - 48 = 18 pins for clock/programming/
status), at the cost of narrower per-face channel count (see below). 6x4 was the
more conservative fallback if 6x8's margin proves too tight in practice.

This sizing question applies specifically to a **single, fully-instrumented bring-up
cell** — every line broken out to a real pin so it can be individually driven/observed
during initial calibration. A later multi-cell substrate, where most connections are
cell-to-cell on the same die (not through package pins), faces a completely different
and far less restrictive budget — that budget is LUT4, not pin count, and scales with
the array's *boundary*, not each cell's total line count.

## The channel-pair model (this session's main resolution)

Each face's 8 physical lines are not 8 independent lines — they are **4 channels**,
each channel one in/out pair bound to one specific neighbour connection point:

- An `out` on this cell's channel feeds the matching `in` on the neighbour's paired
  channel, and vice versa — never a shared bidirectional wire (this is the existing,
  already-decided fix for the bus-contention problems the original UniCell "full fat"
  cell design hit).
- This is *why* lines are paired at all: AND/OR/XOR need two operands, and each
  channel's own in/out pair supplies them naturally. NOT is unary and doesn't need
  the second operand, but uses the same channel shape for uniformity.

**Per-face weight/firing decision:** popcount of how many of the face's 4 channels
currently have an active, asserted `in` value. Range 0-4, so the per-face accumulator
and per-face threshold register are each only **3 bits** wide (not the 4 bits a naive
0-8 reading of "8 lines" would suggest — the channel-pair halving matters here).

**Per-channel output:** `out = GATE_select[channel](face_fire_decision, that_channel's
_own_in_value)` — the face's collective fire decision combined with that specific
channel's own current input, gate chosen independently per channel (2 bits: AND / OR
/ XOR / NOT). This is what makes per-channel gate selection meaningful rather than
redundant (a gate combining only the fire decision with itself would make every
channel on a face identical).

**Consequence: direction is now implicit, not a free per-line bit.** Since a channel
is structurally an in/out pair, "direction" isn't an independent runtime choice per
physical lane the way the original spec described it — it's which half of the pair a
given lane plays, fixed by channel-slot rather than a separate config bit. Still
configurable once at pattern-load time (the same physical lane can be the in-half in
one trained pattern and the out-half in another), but this drops per-line config from
4 bits (gate-select 2 + direction 1 + active 1) to **3 bits** (gate-select 2 + active
1), since direction no longer needs its own bit. Not yet re-verified against the
original 4-bit-per-line total elsewhere in the docs — flagged for whoever writes the
real config field map next.

## The feedback-loop hazard, and the fix (also resolved this session)

A channel is bidirectional between two neighbouring cells: this cell's output on that
channel depends on this cell's own input on it, which is the neighbour's output on
their matching channel, which depends on the neighbour's own input — which is this
cell's output. A real combinational loop, not just a modelling nuisance: wired without
a clock edge between the two directions, this either fails to synthesise cleanly or
causes real oscillation/metastability on actual silicon.

**Fix: the whole cell updates synchronously, once per timer window, not
combinationally.** In-lines are sampled at the start of a window; the fire decision
and new out-values are computed from that sample; the new out-values are only
presented to neighbours at the *next* window boundary. An output this window is a
function of inputs from *last* window, never the current instant. This costs nothing
new in hardware — the design already has a timer-gated window for the threshold
check; it now also does double duty as the thing that breaks the loop into safe,
discrete steps and keeps the whole mesh's updates in lockstep.

## The 16-bit memory latch: one shared, trained bias value (resolved this session)

Originally ambiguous (a candidate for the gate's second operand, before the
channel-pair model above settled that question differently). Resolved: it is **a
single, shared, per-cell bias value**, generated during VM training and loaded onto
the deployed cell alongside the threshold (i.e. via the same eventual `PATTERN_PUSH`
loading mechanism the ESP32-BL616 link protocol already anticipates) — not split six
ways across faces, not read/written at runtime by the cell itself.

Its purpose is a **tuning value, not a fixed constant**: if a deployed unit turns out
to be overloaded (firing too readily, presumably contributing to runaway or
excessive mesh activity), this bias can be *retrained and reloaded* to make the whole
cell less excitable across all six faces at once, without touching per-face
thresholds or per-channel gate/active configuration individually. A cheap, global
damping knob, separate from and cheaper to adjust than the rest of the trained state.

Exact application to the per-face comparison (e.g. `effective_popcount = popcount -
bias`, or something else) is not yet decided — this session settled *what the value
is for*, not the precise arithmetic. Flagged as the next open question when RTL work
starts.

## Still open (not resolved this session, listed so they aren't lost either)

- Exact arithmetic combining the shared bias with each face's popcount/threshold
  comparison.
- Whether the per-line config bit width correction above (4 -> 3 bits/line) has been
  reconciled against the original 4x96-bit-latch total described elsewhere, or
  whether that total needs restating for the channel-pair model.
- Real RTL for any of this — still scoping stage, unchanged from the branch's
  existing status note.
