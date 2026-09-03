# The command core — real design notes toward a 9th core (CONCEPT, review before building)

*Captured 2026-09-04, from a real, live design discussion following
`#626`'s own removal of command-cell functionality from `nano`
(`is_command_cell`/`cmd_in`/`cmd_out`, both confirmed real but
non-functional stubs before removal). Nothing built here -- a real
design note, matching every other `*_scope.md`/design-note's own
discipline of capturing shape before committing to RTL.*

## The real, existing starting point -- not built from nothing

Two real, already-built modules exist and inform this directly:
- **`cell_command_v1.v`** -- minimal `trigger_in`→`program_out` pulse
  extender. Real, but already RULED OUT per its own header (`#392`):
  shares data through ordinary `data_in` ports, doesn't match the
  real, dedicated `PROG_ID`-word interface every `v4` core now uses.
- **`cell_command_sequencer_v1.v`** -- real, working, but narrow:
  compile-time-fixed values, hardwired to one target field
  (`PROG_ID_CARDINAL_EDGE` only). Its own real 4-state machine
  (`IDLE → SEND_FIELD → SEND_COMPLETE → WAIT_DONE`, advancing only
  once `program_done_in` confirms real completion) is solid, reusable
  prior art for the SHAPE of the new work, not the scope of it.

## Real point 1: directional freeze has to move from shell to core

Every real `v4` core today has ONE shared `freeze_in` wire, tied
uniformly across all four cardinal directions (`effective_freeze =
freeze_in || ...`, confirmed directly against the RTL, `#618`-`#626`).
The command core genuinely can't work that way -- it needs to freeze
only the ONE direction its target sits on, leaving the other three
untouched. Real, necessary consequence: the command core needs FOUR
separate freeze lines (one per cardinal direction) as its own real
core-level logic, not the single shared shell-level wire every other
core uses.

## Real point 2: four real approaches to knowing when it's safe to act, converging on two

1. **Ack-line sensing** -- watch both ack lines on the target
   direction: both idle = empty; toggling = real traffic, leave it;
   both stuck high = a real stall. Real, honest caveat found directly
   from this session's own hard-won lessons (`#621`/`#623`/`#625`):
   this only gives a clean, universal "empty" signal for ONE-SHOT
   cores (`adder`/`ram`/`comparator`/`branch`). CONTINUOUSLY-LIVE cores
   (`accumulator`/`latch`/`sequencer`) never settle to a stable
   both-idle state in normal operation -- they keep cycling by design.
   Ack-sensing would need a different real interpretation per target
   core TYPE, not one universal rule.
2. **Direct freeze-line visibility** -- if the command cell can see
   the target is already frozen, it knows definitively the target is
   quiescent. Real, honest cost: needs the command cell's own logic to
   span two real cycles.
3. **Explicit state-output lines** -- add a real pair of status wires
   to every core, reporting active/busy state directly, resolving
   point 1's own real ambiguity by construction rather than inference.
   A real, more invasive change (every core gains new real output
   ports), not scoped further here.
4. **No sensing at all** -- freeze the target direction unconditionally
   and inject regardless of prior state. Simplest, blunt, real
   fallback if the others prove too costly.

**Real, working synthesis, not yet decided as final:** point 1's own
directional freeze and point 2's approach 2 combine naturally --
cycle 1, the command cell asserts its own directional freeze on the
target; cycle 2, once any in-flight capture/offer has had a chance to
settle, the command cell can trust the target is genuinely quiescent
and proceed. This makes the directional-freeze mechanism the actual
tool that CREATES safety, not a separate concern from sensing it.

## Real point 3: addressing in the existing spare bits, confirmed real room exists

The real 32-bit `prog_data` word: the busiest real cores (`branch`/
`nano`, 4-bit `PROG_ID`) use `id[23:20]` + `word[19:0]` = 24 bits,
leaving `[31:24]` genuinely free (8 bits) -- confirmed directly against
the RTL, not assumed. Every 3-bit-ID core has even more room (9 bits
free at `[31:23]`). **`[31:24]` is the real, safe, uniform space** to
carry a target-address field across every core in the family without
widening anything.

Real, concrete design: an 8-bit target address (256 real distinct
cells) genuinely fits, and every core ALREADY carries a real, unused-
for-this-purpose `CELL_ID` parameter (16 bits, currently just a debug
tag) -- reusing its own low 8 bits as a real, comparable address is a
clean, low-cost way to give this real meaning, not inventing new
infrastructure. The real mechanism this enables is structurally the
same shape as `nano`'s own real relay-vs-consume classification
(`cardinal_edge`, `#626`) -- applied to the PROGRAMMING channel instead
of ordinary data: a command word flows through, each cell checks "is
this address mine?", and either consumes or relays. Real, honest
flag, matching this session's own repeated lesson: this needs careful,
deliberate timing design before being trusted (the same class of
subtlety that produced `#619`'s real split-write bug and `#624`'s real
testbench misconception) -- not attempted here.

## Real point 4: stage-then-release, using existing decision cores as the trigger

The command core stores a real, staged payload (target address +
direction + the `PROG_ID`/word sequence to apply) and HOLDS it, firing
only once a separate, real "release" signal arrives -- decoupling
STAGING from FIRING entirely. Real, genuinely clean architectural
choice: the release trigger doesn't need bespoke decision logic inside
the command core at all -- it's just whatever a real, already-proven
`comparator`/`branch`/`latch` cell already produces, wired in directly.
The command core's own real job narrows to "store and wait," not
"decide when" -- a direct, real application of this project's own Lego
philosophy (composition over monolithic cores, `#498`).

**Real, open sub-question, not resolved here:** does the SAME 32-bit
bus word need to also carry the real target DIRECTION (up to 6-way,
per the real headroom convention every core's own mask fields already
have)? Computed directly: an 8-bit address + a 24-bit `(ID,word)`
payload already fills the full 32 bits, leaving no room for a separate
direction field in the same word. The cleaner real answer, consistent
with how every other real field in this family already works
(`branch`'s own `upstream_dir`, `adder`'s `upstream_mask`): direction
is the command core's OWN real, separate config field (set via
`cfg_valid`/`PROG_ID`, matching every other core's real convention),
not something re-specified per transaction on the bus. Keeps the
32-bit word's own real budget clean (8-bit address + 24-bit payload)
without cramming two genuinely different concerns into one word.

## Real, honest open question, not resolved here

**Does the shared 3-addon chain even apply to this core?** The command
core is control-plane, not data-plane -- it doesn't compute or offer a
dataflow value the way every other real core does. Whether
`nibble_mask`/`shift`/`lane`/`invert` have any real meaning here is a
genuinely open, honest question (matching `sequencer`'s own real
finding, `#625`, that not every real shell feature has equal surface
on every core) -- not assumed either way.

## Not yet done, stated plainly

No RTL written, no port list finalized, no decision made between the
sensing approaches in point 2 or the addressing/direction split in
point 3/4. A real, live design discussion captured precisely so it
survives intact, not a locked spec -- the real next step is picking
one sensing approach and one addressing shape to prototype, not
building all of this at once.
