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

**Real, resolved, not open anymore:** what holds a genuine multi-word
32-bit command SEQUENCE is a real chain of `ram_shell_v1` instances in
FLOWING mode (`fixed_mode=0`), not `fixed_mode=1` -- checked directly
against the RTL and corrects an earlier wrong guess in this same
discussion (fixed_mode was floated as a candidate; it genuinely can't
chain, since `ready_out`/`capture_now` are both hard-gated `!fixed_mode`,
so a fixed-mode cell never becomes ready to receive and never drains).
Flowing mode is exactly `#638`'s own proven `RAM_RELAY`, chained N
times: `capture_now` requires `!data_valid`, `data_valid` clears the
instant `offer_draining` fires, and THAT is what frees the cell's own
`ready_out` for the cell behind it to push forward -- the entire
chain advances through ordinary, already-proven ready/ack backpressure,
zero new RTL. "Preloaded" vs. "computed by another mechanism" is not a
real distinction at this level -- both are just whatever fills the
tail end of the chain via ordinary dataflow; the same backpressure
rules apply regardless of the source.

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

## Real, resolved: one shared toggle primitive, not two separate patterns -- and mode governs the START mechanism, not just the reaction

**Superseding this note's own earlier framing above** (which had
separate, independently-set activate/deactivate patterns, and a
trigger-mode pattern captured live from the trigger word's own bits):
a live follow-up pass simplified this further, and it's real, not
speculative -- confirmed workable, not just simpler on paper.

**Real, confirmed: this is NOT any existing core's behavior.** RAM
captures once and holds forever, never comparing again.
`adder_cell_v4` captures once and fires once, resetting after. What
this core needs is different from both: ONE held pattern register,
config-set (same `cfg_data`/`PROG_ID` mechanism as any other field --
explicitly NOT set via this cell's own trigger/programmer mechanism,
which would be circular), reset-default `0000` (confirmed matches
`compare_cell_v4.v`'s own `threshold` register exactly -- an
un-configured cell genuinely toggles on the first `0000` it sees,
real and expected, not an oversight). Recognition is direction-
agnostic -- match from ANY of the 4 real directions (OR-combined, the
same "any real neighbor" idiom `freeze_in` already uses on the shells,
`#639`), not a configured watch-direction. Only the ACTION the match
produces needs a direction (see drive-direction, below).

**Real, resolved: the core circuit is `if (match) state <= !state;`
-- a genuine toggle, not two independent compare-and-set paths.** This
sidesteps a real hazard a naive two-value design would have (an
activate pattern equal to the deactivate pattern would race, since
both conditions would fire on the same value) -- with one shared
toggle pattern, "equal" isn't even a distinguishable case, it's just
"flip on this value," unambiguous by construction, one field instead
of two.

**Real, resolved: mode select governs where the FIRST transition's
source comes from, not just what the match produces** -- this is a
real structural difference between the two modes, not merely a
different output action on an otherwise-identical circuit:
- **Trigger mode:** genuinely symmetric. It's the outermost gate in
  the whole pipeline -- nothing upstream is already gating anything
  for it -- so it has to detect its OWN start via the comparator: a
  real toggle match, both directions, same mechanism, same pattern.
  Polarity (below) sets which state it rests in.
  - Rest state 0 (normally frozen): first match -> unfreeze the
    buffer direction (real start-of-burst). Second match, same
    pattern -> refreeze (real end-of-burst / terminal-marker
    detection, cascading the free full-chain stall, see below).
- **Programmer mode:** the toggle side is genuinely OFF/circumvented,
  not merely unused -- it's downstream of trigger mode's own gating,
  so by the time any real data reaches it, trigger mode has already
  decided the buffer should be flowing. Real, simpler start: the
  first real arrival while idle IS the start (freeze the target,
  assert `program_in`, begin relaying) -- no pattern match needed to
  know whether to start, only that something arrived. The comparator
  IS still genuinely needed here, but only for the STOP side: match
  against the toggle pattern (config-fixed to the target's own real
  `PROG_ID_COMPLETE` value, `4'd15`/`3'd7`) identifies which relayed
  word is the terminating one -- one-shot, one direction, not a toggle.

## Real, resolved: the full bit budget

| Field | Bits | Real notes |
|---|---|---|
| Mode select (trigger / programmer) | 1 | Also governs start-mechanism, not just reaction (above) |
| Polarity (rest-frozen / rest-open) | 1 | Meaningful in trigger mode; programmer mode always rests idle-awaiting-arrival |
| Drive direction | 3 | Where the ACTION lands (freeze/unfreeze target in trigger mode; program+freeze target in programmer mode) -- same shape as `branch_cell_v4.v`'s own `upstream_dir` |
| Toggle pattern (single, shared) | 4 | Sized to the wider of the two real known `PROG_ID_COMPLETE` values; capped here deliberately, not left open-ended |
| **Total** | **9** | |

+20 if the addon-chain question (below) ever resolves yes; current
instinct is no, since this core never produces a dataflow value for
the addon chain to act on. Comfortably fits the smaller, 64-bit
`cfg_data` shape six of the eight existing cores already use (not
nano/branch's wider 128/80-bit layout), with a 3-bit `PROG_ID` (well
under the 8-slot budget for real fields + `COMPLETE`).

**Real, deliberate scope limit, stated explicitly rather than left
implicit:** the toggle pattern is config-time-only in this first
build -- set via the ordinary `cfg_data`/`PROG_ID` mechanism, same as
any other field, reused across many trigger cycles once set. Neither
of the two uses actually being designed (trigger mode, programmer
mode) needs to change this value mid-operation; both set it once and
reuse it indefinitely. Live reconfiguration while the cell is actively
watching (without pausing it via ordinary `program_in`, which would
create a real, momentary blind spot) is a genuinely separate, real
capability -- deferred, not attempted here, matching how the
addon-chain question and `#628`'s own 256-address dynamic targeting
were both set aside rather than solved speculatively.

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
1. First real arrival from the buffer while idle: freeze the target,
   assert `program_in`, begin relaying -- no comparator match needed
   to start (the toggle side is genuinely off in this mode, see
   above); trigger mode has already done the gating upstream.
2. Relay buffer data -> target's `prog_data_in_x`/`prog_arrived_in_x`,
   pacing each word off the real `prog_ack_out_x` (word N acked ->
   send word N+1) -- free, already-existing infrastructure, no new
   flow-control logic needed for pacing.
3. The shared comparator (toggle pattern fixed at config time to the
   target's own real `COMPLETE` value) identifies WHICH relayed word
   is the terminating one -- one-shot match, not a toggle.
4. Only once THAT specific word is confirmed via `prog_ack_out` (not
   merely sent) does programmer mode declare the burst genuinely done
   -- combining "I recognized this as the last word" with "the target
   genuinely received it," not either alone.
5. Only then: drop `program_in`, release the target's freeze (via the
   freeze-drive primitive below).

**Trigger mode's own completion detection stays simpler and doesn't
need this same ack-anchoring**, because the link it watches (buffer ->
programmer) is deliberately UNFROZEN for the whole burst by design --
trigger mode is a pure, passive observer on that link, not itself
awaiting confirmation of something it sent. Content-comparison alone
(no ack gating) is sufficient there.

## Real, resolved: freezing the head cell alone stalls the entire buffer chain -- no per-cell mechanism needed

A genuine, free consequence of the SAME backpressure mechanism that
makes the buffer chain (above) advance in the first place, not a
second mechanism running alongside it. Confirmed directly against the
RTL: `ready_out = effective_armed && !data_valid && !fixed_mode &&
!effective_freeze` -- freezing the head cell drops its own `ready_out`
to 0. The cell behind it can't offer into a target whose `ready_out`
is 0 (`any_fire` requires `targets_all_ready`), so ITS `data_valid`
never drains, so ITS OWN `ready_out` drops too -- cascading a full
stall down the entire chain from a single freeze at the head. Real,
confirmed: this is a continuous assignment, not registered -- the
moment `freeze_in` changes, `ready_out` follows COMBINATIONALLY the
same cycle, so a freeze asserted the instant the terminal marker is
recognized takes effect immediately (same cycle) or one cycle later
if the trigger cell's own freeze-drive output is registered rather
than combinational -- a real, open, low-stakes implementation choice
for the freeze-drive block itself, not something that affects
correctness either way.

**Real, confirmed: an already-in-flight offer is not corrupted by a
freeze landing mid-handshake.** `fire_x` is driven off the registered
`pending_ack`, not a freshly-evaluated `want_to_offer` each cycle -- a
freeze asserted the same cycle the terminal marker's own offer is
still completing its ack does not interrupt that specific offer. The
freeze only blocks the NEXT offer from starting, which is exactly the
timing wanted: the terminal marker itself still gets through cleanly,
and nothing after it does.

**Real, resolved, full end-to-end picture:** trigger mode and
programmer mode both watch the SAME buffer stream (multicast, real,
free -- see above) for the SAME terminal marker. On match: trigger
mode freezes the head cell, which cascades a full, free stall through
the whole chain via the mechanism above -- no coordination needed with
programmer mode, and no per-cell freeze logic needed anywhere in the
chain itself. Programmer mode, independently, confirms via
`prog_ack_out` (real, freeze-safe, see above) and releases the
target's freeze. Same event, two independent, correct reactions from
watching one wire -- nothing new required beyond the freeze-drive
block and the shared comparator both modes already need.

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
precedent), 9 real config bits total, with:
- A fixed, config-time drive direction (matching `branch_cell_v4.v`'s
  own `upstream_dir`).
- Polarity (trigger mode's own rest state; not meaningful in
  programmer mode).
- One shared toggle-pattern register, direction-agnostic recognition,
  config-set only (`0000` reset default, matching `compare_cell_v4.v`'s
  own `threshold`).
- Mode-dependent start: genuine symmetric toggle in trigger mode
  (nothing upstream gates it); plain first-arrival in programmer mode
  (trigger mode has already gated it).
- Real, new freeze-DRIVE output logic (neither mode currently exists
  anywhere in the family).
- Real, new programming-channel-DRIVE output logic (programmer mode
  only): relaying ordinary buffer data onto `prog_data_in_x`, paced by
  the real, already-existing, freeze-safe `prog_ack_out_x`.

## Not yet done, stated plainly

No RTL written. The buffer question is now resolved (real `ram_
shell_v1` chain, flowing mode, composition only) -- the real next step
is building the shared capture-compare + freeze-drive block itself
(common to both modes), the one remaining piece with no existing real
implementation anywhere in the family.
