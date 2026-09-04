# The command core — real design notes, round 2 (CONCEPT, review before building)

*Captured 2026-09-04, from a real, live follow-up design discussion,
after `#639`/`#640`'s own real cardinal control shells landed. This
note builds directly on `command_core_scope.md`'s own real open
questions -- several are resolved here, none are contradicted. Nothing
built here either -- same discipline as the first note: capture shape
before committing to RTL.*

## Real, resolved: one core type, two live instances

Not two separate core files. **One core, mode-selected**, deployed as
TWO simultaneously-active instances in a real topology -- the same
real pattern `ram_cell_v4.v`'s own `fixed_mode` bit already uses (one
file, genuinely different behavior selected at config time). This
gives the Lego-philosophy cleanliness of one RTL file while still
having two live cells doing two different jobs, matching the
diagram's own "Command Cell 1" / "Command Cell 2" separation.

**Real, confirmed: single fixed target per instance**, not `#628`'s
original 256-address runtime-targeting scheme. Direction is a real,
config-time field, same shape as `branch_cell_v4.v`'s own
`upstream_dir` -- simpler, and the right scope for a first real build.
This meaningfully narrows `#628`'s own point 3 (dynamic addressing is
real, later work, not this build).

## Real, resolved: buffer fan-out needs zero new RTL

Checked directly against the RTL, not assumed: `next_pending_ack =
downstream_mask[3:0] & ~ack_in_vec` (confirmed in `adder_cell_v4.v`,
same real pattern on every core in the family) -- every bit set in a
mask fires SIMULTANEOUSLY, same cycle, same value, real multicast
already built in. The "head buffer cell sends its data in two
directions at once" requirement is free: ANY existing core (a RAM
cell, most naturally) with a real 2-bit `downstream_mask` (toward the
programmer instance, toward the trigger instance) already does this,
today, no new core needed.

**Real, still open, not resolved here:** what holds a genuine
multi-word 32-bit command SEQUENCE. Neither `sequencer_cell_v4.v`
(4x8-bit, too narrow) nor a plain RAM cell (single static value, no
advance-to-next) cleanly provides this. Real candidates not yet
evaluated: several RAM cells physically chained with a real hand-off
signal between them (reusing the SAME freeze-drive primitive scoped
below), or a genuinely new small buffer core. Picking one is real,
separate, later work.

## Real, resolved: variable-length packets, chosen deliberately

Real, deliberate choice over the simpler fixed-count alternative
(`#628`'s own scope did not resolve this; this session did): variable-
length bursts, gated by recognizing a real stop-pattern in the data
stream, not a pre-declared word count. More complex cell design, real
payoff: no burst-length limit, and the SAME mechanism generalizes into
a real, standalone flow-control primitive usable anywhere a variable-
length burst needs gating, not just this command pipeline.

**Real, confirmed structural finding, checked against the RTL:**
`PROG_ID_COMPLETE` is genuinely unavoidable even in the simplest
possible single-field transaction -- `program_done_r` (the target's
own real "I'm done" signal) is set ONLY by `PROG_ID_COMPLETE`, nothing
else touches it (confirmed in `nano_gate_v4.v`'s own always block).
Every individual field write applies live and immediately the instant
it's processed; `COMPLETE` is not a "commit all staged fields" gate --
its real job is marking the cell ready again, signalling
`program_done`, and re-arming. So the real minimum transaction is
always at least two words (field write + `COMPLETE`), full stop,
regardless of which scheme is chosen. What variable-length buys is
letting MULTIPLE field writes ride in one continuous unfrozen burst
before the terminating `COMPLETE`, not avoiding `COMPLETE` itself.

**Real, narrow stop-pattern field, matching the actual known
requirement:** the only two real patterns that exist today are 3-4
bits wide (`3'd7`/`4'd15`, confirmed against every core's own
`PROG_ID_COMPLETE`). A narrow field (a handful of bits) is sufficient
and matches this project's own established convention of sizing
fields to the real confirmed requirement rather than over-reserving.
A wide/arbitrary stop-pattern field was considered and set aside --
it would force a two-word trigger protocol (direction word + pattern
word) for no real known use today.

## Real, resolved: a genuinely new shared primitive -- capture-once-then-continuously-compare

Real, confirmed: this is NOT any existing core's behavior. RAM
captures once and holds forever, never comparing again. `adder_cell_
v4` captures once and fires once, resetting after. What both trigger
mode and programmer mode need is different from both: capture a
pattern into a hold register ONCE, then continuously compare EVERY
subsequent arrival against that held value indefinitely, with no
reset between checks -- a persistent watch, not a one-shot. Real,
minimal internal shape (both modes, same circuit):
1. One capture register, loaded once from a trigger event.
2. A continuous equality compare against that held value on every
   subsequent real arrival from the watched direction.
3. Match -> real action (mode-dependent, see below).

**Real, resolved: the pattern SOURCE differs by mode, the comparator
circuit doesn't:**
- **Trigger mode:** pattern captured LIVE from the trigger word's own
  narrow field at runtime -- a genuinely configurable, per-transaction
  stop-pattern ("a configurable trigger releasing data as required, a
  flow control" -- Alan's own framing, and a real, valuable
  generalization beyond this specific command pipeline).
- **Programmer mode:** pattern is FIXED at config time to the real,
  known `PROG_ID_COMPLETE` value for whichever target type this
  instance points at (`4'd15` or `3'd7`).

This is what makes "one core, mode-selected" genuinely clean rather
than a forced unification: same internal circuit, only where the held
value comes from differs.

## Real, resolved: completion detection is ack-anchored, not content-only, and this was NOT optional

Real, confirmed directly against the RTL, settling what was left open
mid-discussion: ordinary `ack_out` is dead the instant a cell is
frozen. `ack_out_x` only ever fires from `consumed_now`
(`capture_now`/`can_fire`/etc.), and every one of those real paths is
gated by `!effective_freeze` (confirmed in `nano_gate_v4.v`). Freezing
the target for programming safety and expecting ordinary `ack_out` to
confirm anything during that same window are mutually exclusive --
this is exactly, precisely why the programming channel has its own
real, separate ack lines (`prog_ack_out_n/s/e/w`) in the first place.
Confirmed: `prog_ack_out_n = programming_active && prog_sel_n`, with
no freeze term anywhere in that formula -- real, freeze-safe by
construction, asserted every single cycle a word is genuinely
processed (a real per-word ack, same shape as every ordinary data
`ack_out`/`ack_in` handshake elsewhere in this project).

**Real, resolved mechanism for programmer mode, combining the shared
comparator with this freeze-safe ack:**
1. Relay buffer data -> target's `prog_data_in_x`/`prog_arrived_in_x`,
   pacing each word off the real `prog_ack_out_x` (word N acked ->
   send word N+1) -- free, already-existing infrastructure, no new
   flow-control logic needed for pacing.
2. The shared capture-and-compare primitive (pattern fixed to the
   target's own real `COMPLETE` value) identifies WHICH relayed word
   is the terminating one.
3. Only once THAT specific word is confirmed via `prog_ack_out` (not
   merely sent) does programmer mode declare the burst genuinely done
   -- combining "I recognized this as the last word" with "the target
   genuinely received it," not either alone.
4. Only then: drop `program_in`, release the target's freeze (via the
   freeze-drive primitive below).

**Trigger mode's own completion detection stays simpler and doesn't
need this same ack-anchoring**, because the link it watches (buffer ->
programmer) is deliberately UNFROZEN for the whole burst by design --
trigger mode is a pure, passive observer on that link, not itself
awaiting confirmation of something it sent. Content-comparison alone
(no ack gating) is sufficient there.

## Real, still standing from `command_core_scope.md`: freeze-output generation is new RTL, not composition

Unchanged from the first note's own real finding: no core in the
family currently DRIVES freeze, only receives it. Both modes need
this -- trigger mode drives freeze toward the buffer direction,
programmer mode drives freeze toward the target direction. This is
the one piece of genuinely new logic shared by both modes, alongside
the capture-and-compare primitive above. Worth building as one clean,
shared internal block inside the single core file, not duplicated per
mode.

**Real, also still new, not previously flagged as clearly:**
programmer mode driving `program_in`/relaying onto `prog_data_in_x`
outward is itself new -- no core currently drives the programming
channel, only receives it (matches trigger mode's own equivalent gap
on the freeze/buffer side).

## Real, honest summary of what this core actually needs to be, end to end

One core, mode-selected (matching `ram_cell_v4.v`'s own `fixed_mode`
precedent), with:
- A fixed, config-time target direction (matching `branch_cell_v4.v`'s
  own `upstream_dir`).
- The shared capture-and-compare primitive (live-captured pattern in
  trigger mode, config-fixed `COMPLETE` pattern in programmer mode).
- Real, new freeze-DRIVE output logic (neither mode currently exists
  anywhere in the family).
- Real, new programming-channel-DRIVE output logic (programmer mode
  only): relaying ordinary buffer data onto `prog_data_in_x`, paced by
  the real, already-existing, freeze-safe `prog_ack_out_x`.

## Not yet done, stated plainly

No RTL written. Genuinely open, not resolved here: what cell type (or
composition of existing cells) plays "buffer" for a real multi-word
sequence -- the one real gap from `command_core_scope.md`'s own scope
that this round of discussion didn't close. The real next step is
still picking a concrete port list and building the shared capture-
compare + freeze-drive block first (the common core of both modes),
not the buffer question, which can be deferred behind a simpler
fixed-count stand-in for early testing if needed.
