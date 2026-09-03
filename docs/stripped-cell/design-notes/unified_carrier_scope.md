# The unified carrier — one rich shell, one core-slot or many (CONCEPT, review before building)

*Captured 2026-09-03, per Alan's own direct proposal and his own
5-point breakdown, both reproduced precisely below. Same discipline as
`composer_scope.md`/`llvm_ir_compiler_scope.md`: a proposal to review
and correct, not a locked spec. Nothing below is built.*

## Alan's own 5-point breakdown, the real source of truth for this note

1. Each cell has two effective parts: (a) the actual CORE function,
   (b) the SHELL that wraps around it.
2. Make the shell consistent, so every core gets the SAME shell
   functionality -- programming, shift, nibble mask, lanes, the shift
   functions, the command functions, 6-way cardinality, with ack all
   around.
3. The super carrier has the SAME features, just now can take
   multiple cores (not just 1) and has the select option.
4. Each core, placed into EITHER shell (the single-core shell or the
   carrier), is just that core's own function wrapped in the SAME,
   entire shell.
5. The only extra part -- possibly already solved -- is a single bit
   in the core stating whether it's active or not: permanently on in
   the single-core case, programmable (select-driven) in the carrier.

## The real, current asymmetry this fixes, checked directly against the RTL, not assumed

**Nano (`unicell_stripped_v1.v`) is genuinely richer than every other
real core today, confirmed directly, not from memory:**
- A real, WORKING second channel: `program_in`/`prog_data_in_*`/
  `prog_arrived_in_*`/`prog_ack_out_*` (4-directional, its own real
  ack), carrying the real `PROG_ID`-tagged targeted/staged
  reconfiguration protocol (`#123`/`#140`, confirmed real and VM-
  modeled, `#615`).
- A real, working `is_command_cell` mode (`cmd_latch[10]`, the old
  full-cell's own `COMMAND_EMIT` precedent) -- a cell that continuously
  re-emits its held value, real infrastructure for driving another
  cell's `program_in` externally (`cell_command_v1.v`).
- A real, honest THIRD port set that ISN'T built yet, worth being
  precise about rather than conflating with the two real ones above:
  `cmd_in_n/s/e/w`/`cmd_out_n/s/e/w` are real, reserved PORTS
  (`#84`), but genuinely unwired -- `cmd_out_n` etc. are tied to
  `32'h0` in the current RTL. A real placeholder, not a working
  channel.
- `routing_mask`/`cardinal_edge` fields that are genuinely 6 bits wide
  in the real RTL -- real headroom for a 6th/7th cardinal direction,
  even though only 4 are physically wired today (the real prerequisite
  `#604` already named for any future 3D work).
- `shift_lane_addon_v1.v` (`#303`-`#311`, real, already built) --
  though this one is genuinely a SHELL-level addon already, not
  nano-internal; it wraps whichever core is selected inside a super
  shell, nano included. Nano's own real gap here (`#616`) is that its
  STANDALONE RTL has no shift of its own at all, separate from the
  shared addon.

**Every other real core (`adder_cell_v1.v` checked directly as the
representative case) has a genuinely simpler, single-channel shell:**
one `cfg_valid`/`cfg_data` word, committed atomically, no targeting,
no command-cell hook, 4-bit (not 6-bit) direction fields, no addon
wiring of its own (addons currently only exist at the SUPER shell
level, `unicell_super_v3.v`, not on the standalone single-core files).

**This is real, un-planned duplication and asymmetry, not a
deliberate design choice, confirmed by checking rather than assuming:**
each standalone core file hand-rolls its own shell from scratch
(`adder_cell_v1.v`'s own cardinal ports and handshake are a real,
separate reimplementation of the same shape nano already has, not a
shared module) -- and nano's own extra richness never got generalized
outward when the other 6 cores were built.

## The real, proposed unification, restated precisely against real module boundaries

**One shell design, not two.** Today, "standalone single-core cell"
and "super carrier shell" are architecturally DIFFERENT files with
different capabilities (`adder_cell_v1.v` vs. `unicell_super_v3.v`).
Alan's own real proposal collapses this: there is ONE real shell
design -- call it the CARRIER for now, pending a real name -- that
provides the full, unified feature set (programming/`PROG_ID`
targeting, command-cell support, shift, nibble mask, lane-cut, 6-way
cardinal field width, full ack on every real channel) around
WHATEVER core(s) it holds. The carrier is PARAMETERIZED by how many
core-slots it has (`N=1` for what's the standalone case today, `N=8`
for what's the super shell today) -- not two designs, one design with
a real, honest slot count.

**The `active` bit, per point 5 -- the real, minimal difference
between the two configurations.** A single, real, per-core-slot bit,
exposed the same way regardless of `N`: tied permanently high when
`N=1` (there's only ever one real core, always the active one, no
`core_select` decode needed at all); driven by the real, already-
existing `incoming_select == SEL_X` decode (`unicell_super_v3.v`'s own
real, working pattern, confirmed directly -- `cfg_valid_adder =
cfg_valid && (incoming_select == SEL_ADDER)`, real prior art for
exactly this bit, not a new mechanism) when `N>1`. Real, honest
confirmation of point 5's own "may have solved already" -- the
MECHANISM (select-gated `cfg_valid`) is real and already proven; what's
missing is making it a real, explicit, uniform PORT every core-slot
carries, present (and simply tied high) even in the `N=1` case, so the
core+shell combination is IDENTICAL RTL in both configurations, not
two separate integrations of the same core into two differently-shaped
shells.

## Real, honest scope questions, not resolved here

- **Real, measurable cost, not assumed.** Giving all 7 non-nano cores
  nano's own full channel set (programming, ack-everywhere, 6-bit
  fields) will cost real ALM -- by how much is unmeasured. This
  project's own standing discipline (`#524`-`#526`, every real addon/
  core measured as a real delta against a real baseline) applies
  directly here, not skipped because the design is elegant.
- **The `cmd_in`/`cmd_out` channel itself remains genuinely unbuilt**
  (`#84`) -- unifying the shell around nano's own CURRENTLY REAL
  capabilities does not, by itself, finish that separate, older,
  still-open thread. Worth naming so it isn't silently assumed solved
  by this work.
  6-bit-wide cardinal fields is a real, useful, low-cost step (pure
  field-width headroom, same real principle nano's own fields already
  prove) -- but PHYSICALLY wiring 2 more real cardinal directions
  (actual U/D ports, actual routing logic) is `#604`'s own separate,
  larger, not-yet-started thread. This scope note only proposes
  giving every core's own FIELD ENCODING the same real headroom nano's
  already has, not building real 6-directional wiring.
- **Real naming, not decided.** "Carrier" is used provisionally above
  to avoid colliding with the existing, real, differently-scoped
  "super carrier shell" name -- a real naming decision for whenever
  this is built, not resolved here.

## A real, low-risk suggested first step, matching this project's own "smallest test first" discipline

Don't rebuild all 7 non-nano cores at once. Per this project's own
established "clone, measure, don't assume" method: pick ONE real core
-- `adder` is the natural choice, being the simplest and already the
one this session's own LLVM frontend (`#611`-`#613`) depends on --
and build a real, single, `N=1`-configured carrier around it,
including the full unified feature set (programming/`PROG_ID`,
command-cell support, 6-bit field width, the `active` bit tied high).
Confirm it behaves identically to today's `adder_cell_v1.v` for
ordinary operation (sim-verified, matching the project's own real
regression discipline), measure the real ALM/Fmax cost of the added
richness against the current, simpler `adder_cell_v1.v` baseline, and
only then generalize the same real template to the remaining 6 cores
and to the `N=8` carrier case.

## Not yet done, stated plainly

No RTL written, no module designed in detail, no real port list
finalized -- a real scoping pass only, matching every other
`*_scope.md` note in this directory. The real, concrete next step is
the single-core, `adder`-based experiment above, not a ground-up
redesign of all 8 cores or the existing super shell at once.
