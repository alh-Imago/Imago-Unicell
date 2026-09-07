# Promoting specialist modules to real cores or addons — and where the 13 reserved bits actually came from

*Captured 2026-08-20, following a real question from Alan: several
specialist modules got built this session (`#279` onward) OUTSIDE the
super carrier shell's own core/addon system — worth asking whether any
belong INSIDE it, given `core_select` has real spare room. Also
captures the answer to a second question Alan raised about his own
past decision: why 13 bits, specifically, ended up reserved in
`SUPER_LATCH`. Not a build — a real assessment and a real historical
answer, recorded before either is lost.*

## The real bit budget, checked precisely, not assumed

From `unicell_super_v1.v`'s own header (`SUPER_LATCH[79:0]`):

```
[4:0]    core_select   -- 5 bits, 6 of 32 values used (0-5) -> 26 SPARE
[46:5]   core_config   -- 42 bits, a UNION reused per core_select
[66:47]  addon_config  -- 20 bits, 100% USED (9+10+1 by the 3 real addons)
[79:67]  reserved      -- 13 bits, genuine, untouched headroom
```

**The real, load-bearing distinction for everything below:** cores
(`core_select`) are MUTUALLY EXCLUSIVE -- exactly one active per cell.
Addons are wired "core-independent, on the periphery" (confirmed
directly in the RTL, `#311`) -- ALWAYS active, regardless of which
core is selected, sitting on the shared output path. A module's own
real behavior determines which of these two extension points (if
either) it actually fits -- promoting something into the wrong one
doesn't just waste effort, it can genuinely break the module's own
purpose (see sentinel, below).

## Module-by-module assessment

**`sentinel_counter_v1` — the strongest candidate, but as an ADDON,
and it needs genuinely new room, not a drop-in.** Its whole job is
watching a cell's own `arrived_X`/`ack_in_X` activity WHILE some other
core (accumulator, in every real use this session) is simultaneously
doing real work in the SAME cell. Making it a CORE is a structural
mismatch, not a detail to iron out later -- a core can never coexist
with the thing it's meant to monitor, since only one core is ever
active per cell. The addon mechanism's own "always active regardless
of core_select" property is exactly what sentinel needs -- but the 3
existing addons all transform OUTPUT DATA on the way out
(`nibble_mask`/`shift_lane`/`invert`, chained on `data_out_X`);
sentinel would need to tap INPUT-side events (arrivals, acks) and
produce a CONTROL signal (freeze), not a data transform. That's a
genuinely new addon SHAPE, not a fourth entry in the existing chain.
`addon_config` is completely full (20/20 bits) -- this would need to
draw from the 13 reserved bits, a real, deliberate use of that
headroom, not a free plug-in.

**`cell_command_sequencer_v1` — a genuine new CORE candidate, not an
addon.** None of the 6 existing cores do "cycle through a short,
fixed, host-configured list of values in order" as an ordinary data
output -- a real, distinct primitive, not overlapping territory
already covered by accumulator/adder/compare/latch/RAM/nano. It
currently emits through its own separate programming-channel ports
(`program_out`/`prog_data_out`/`prog_arrived_out`) rather than
ordinary cardinal ports -- promoting it means genuinely redesigning
its output side to emit through `data_out_X`/`fire_X` like every other
core, real work, but the underlying idea is a clean fit. Plenty of
`core_select` room (slot 6 of 31 spare).

**`addr_counter_v1` — probably not worth its own core.** Mostly
redundant with what `accumulator_cell_v1` already does (event-driven
counting via arrivals). Its one genuinely distinct feature -- wrapping
at a configured bound instead of free signed overflow -- reads more
like a config bit on the accumulator (a real "wrap mode") than a
justification for a whole new core.

**`bram_controller_v1`/`v2` — should explicitly stay OUT of both
systems.** Its entire reason for existing is being ONE shared resource
multiple chains arbitrate for -- the real hardware constraint (2
physical BRAM ports) `#412` built the whole shared-BRAM redesign
around. Giving every cell its own core-select slot for it would
directly undercut that constraint, not honor it -- a real
architectural reason to leave this one alone, not an oversight.

## Where the 13 reserved bits actually came from — a real, traceable answer, not a guess

Alan asked to work out why 13 bits, specifically, ended up reserved.
The real answer is already in the ledger (`#320`), and it's more
interesting than "chose a round number and left slack": those 13 bits
are the EXACT SIZE of a real category that got CORRECTED OUT of the
design during the SAME session `SUPER_LATCH` was built, not chosen as
a target from the start.

`#315`'s own first-pass categorization split out "shell routing"
(`ready` + `routing_mask` + `cardinal_edge`, 13 bits) as a category
assumed to be universal -- present the same way regardless of which
core a cell was running. Checking every core's own real `cfg_data`
layout directly against its RTL (not assumed) showed this was wrong:
those three fields are NANO-SPECIFIC. Every other core (RAM, adder,
accumulator, comparator, latch) has its own `downstream_mask`/
`upstream_mask` fields instead, already counted inside that core's own
part of the 42-bit `core_config` union. Once "shell routing" was
correctly recognized as belonging to nano alone rather than to every
core, the 13 bits it would have occupied as a separate universal
category had nowhere left to go -- and rather than repurpose them
into something else on the spot, they were left as genuine headroom
when the whole latch was rounded up to a clean 80 bits.

**So the real, precise answer:** 13 is not an arbitrary or
symbolically chosen number -- it's the literal size of nano's own
`ready`+`routing_mask`+`cardinal_edge` fields, discovered to be
non-universal partway through building `SUPER_LATCH`, and deliberately
left unclaimed rather than folded back into the union once that
correction was made. The "nice round 80-bit figure" decision and the
specific 13-bit size are two separate real decisions that happened to
land together in the same design pass.

## Status

Not started -- a real assessment and a real historical answer,
recorded for whenever promotion work (sentinel-as-addon in particular)
is actually taken up. Sentinel-as-addon is the most valuable of the
real candidates and also the hardest, since it needs a genuinely new
addon shape (input/control-tap) the existing three don't provide any
precedent for.

## A useful external framing, worth keeping precisely separate from the speculation it arrived alongside

Alan brought a long AI-assisted conversation (Copilot) that wandered
into large-scale, ungrounded speculation (photonic clusters, 10^10
cells, "the vision was right all along") -- checked directly rather
than taken at face value, and most of it doesn't hold up: the two real
science/engineering items it cited (Caltech's real, published
germano-silicate waveguide work; Synopsys's real 3D PCIe 6.0 PHY test
chip) are genuine, but the conversation's OWN numbers were already
inflated on top of them (it claimed "512 GT/s aggregate" for the
Synopsys chip; the real, reported figure is 128 GB/s aggregate across
8 lanes at 64 GT/s -- a real, checkable error sitting inside what
read as precise, authoritative figures). The "100 channels" framing
came from a separate, unverified claim bolted onto the real Caltech
result, not from the Caltech paper itself. The billion-cell scaling
was arithmetic (100^5), not a design -- no real treatment of photonic
multiplexing complexity, power/thermal budgets, yield, or
electronic/optical handoff at that density. None of that is being
carried forward.

**The one genuinely useful thing in the whole conversation, correctly
identified by Alan as the relevant part over the inflated claims:** an
external, independent articulation of the carrier shell as a real
hardware ABI -- "fixed cardinal connectivity, fixed arrival/ack
semantics, fixed addon chain, one config surface (`SUPER_LATCH`); any
core that obeys the carrier's own rules just works." This isn't a new
finding -- it's a clean restatement of what this project has already
built (`unicell_super_v1.v`'s own real design, `#320` onward) -- but
it's a genuinely good, quotable framing worth keeping for how this
gets described going forward, precisely BECAUSE it came from
independently reasoning about the finished shell rather than from
inside the project's own accumulated context.

**One concrete addition to the promotion-candidate list above, worth
recording alongside `cell_command_sequencer_v1`:** a PCIe-ingress core
-- a real core that takes host-side PCIe traffic and presents it
through the ordinary `data_out_X`/`fire_X` cardinal ports like any
other core, rather than PCIe being treated as a special, carrier-level
concern. Not scoped or started -- but a real, small, useful idea
distinct from the speculation it arrived wrapped in.

## Addendum (2026-09-03): nano's own real shift capability -- confirmed lost, and a real, precise reason to give it back, per Alan's own direct point

**Real, status update, 2026-09-07 — read this first:** Alan's own
precise design call reframed this from "nano's own independent shift"
into a shared-addon upgrade benefiting all 8 cores at once: a genuine
2-bit fine shift (0-3) layered in front of the existing 9-tap coarse
shifter closes every gap between taps for free (no two adjacent taps
are more than 4 apart). This is now REAL, sim-verified RTL, wired into
all 8 shells (`unicell_super_v1.v`-`v8.v`), with a full downstream
checklist (compiler, VM, workbench, Composer, LLVM, and the VIX
Carrier's own separate rollout) tracked in `shift_fine_addon_rollout.
md`. The real proposal below is preserved as the original scoping
record, not because it's still an open question.

Alan's own real correction, prompted by this session's own LLVM-
frontend work narrowing focus onto the 8 already-built super-cell
cores: recent work risked treating that set as closed, when a real,
substantial, already-explored thread (`#303`-`#311`, the FULL cell's
own shift/lane mechanism, and `shift_lane_addon_v1.v` -- the first
real addon this project ever built) sits right here, underused.

**The real, current state, checked directly, not assumed:**
`shift_lane_addon_v1.v` is real, already built, and FAITHFULLY ported
from the FULL cell's own real, in-use logic (`#303`) -- a SPARSE,
FIXED-PATTERN shifter (exactly 9 discrete amounts, `{1,2,4,8,12,16,
20,24,28}`; any other amount silently passes through unshifted, a
real, deliberate "constant shift is free rewiring" tradeoff, not a
missing feature), placement-flexible (before or after the active
core's own data work, resolving the real position-sensitivity concern
`#179`'s own follow-up first raised), with lane-cut coupled only to
the shift-OUT direction. It lives entirely in `addon_config` (9 of the
addon budget's own 20 bits, already 100% allocated across the 3 real
addons) -- meaning it wraps whichever core is active, nano included,
when nano runs AS ONE OF THE 8 CORES inside a super-cell shell.

**But nano's own STANDALONE RTL (`unicell_stripped_v1.v`) has
genuinely ZERO shift capability of its own** -- confirmed directly, a
real grep for "shift" turns up nothing relevant. Whatever shift nano
gets today comes entirely from the shared, single, sparse addon every
other core also shares -- nothing nano-specific, nothing finer-grained.

**Alan's own real proposal, precise, not yet built:** give nano back a
genuine, INDEPENDENT shift capability of its own (distinct from, in
addition to, the existing shared addon) -- so that when nano
specifically is active, its own shift and the shell's own
`shift_lane_addon_v1` could LAYER, giving genuinely finer-grained
control than the single, sparse, 9-discrete-amount addon provides
alone. Real, honest first step named plainly: even nano's own shift
capability EXPOSED ALONE (independent of any layering) would be worth
real testing on its own merits, not conditional on the layering idea
panning out.

**Real, direct connection to gaps already found this same session, not
a speculative tie-in:** LLVM IR's own `shl`/`lshr`/`ashr` instructions
-- not yet even considered for `#611`-`#613`'s own frontend -- would
have a real, natural home in whatever shift mechanism results here.
And the same earlier thread that first surfaced the shift/lane
mechanism (`#303`-era) already flagged it as the real missing step
toward eventual multiply support (shift-and-add) -- `LLVM.md`'s own
archived note (`#612`) named `mul` as "too large for most FPGA
targets... planned for a future session," and a real shift mechanism
is a genuine, concrete piece of that future path, not a separate idea.

**Real, honest scope: nothing built here.** The 13 genuinely reserved
`SUPER_LATCH` bits (confirmed above, `addon_config`'s own 20 bits
already 100% allocated) are the real, available headroom a second,
nano-specific shift mechanism would need to draw from -- a real,
concrete design constraint to work within, not resolved here. A real,
precise proposal captured so it survives intact, matching every other
`*_scope.md`/design-note's own discipline in this directory -- not
started this session, given low usage.

## Update (2026-09-07): a genuinely better shape found, sim-verified real RTL built — not nano-specific, a shared-addon upgrade benefiting all 8 cores at once

**The real reframe, per Alan's own direct design call:** rather than
build nano its own SEPARATE, independent shift mechanism, add a small,
GENERAL 2-bit "fine" shift stage (0-3) immediately in front of the
existing `shift_lane_addon_v1` in the shared addon chain. Confirmed
directly, by construction: the union of `{coarse_tap + 0,1,2,3}` for
every one of the 9 real coarse taps (`{1,2,4,8,12,16,20,24,28}`, plus
the implicit 0) covers the ENTIRE 0-31 range with zero gaps, since no
two adjacent taps are ever more than 4 apart. Two bits, not five —
genuinely cheaper than a general barrel shifter, and it benefits every
one of the 8 cores at once (since `addon_config` is core-independent),
not just nano.

**The real problem this creates, caught and fixed, per Alan's own
direct point ("it has to hit before the lane mechanism, and carry that
value through to it, or it will fail"):** `shift_lane_addon_v1`'s own
`lane_cut` boundary-crossing math is computed from `shift_amt` alone.
Once a fine pre-shift moves the data by 0-3 bits before the coarse
stage ever sees it, `lane_cut`'s window is wrong by up to 3 bits unless
it's recomputed from the TOTAL real shift (coarse + fine), not the
coarse portion alone.

**Real RTL built and sim-verified, matching the "clone, don't modify a
proven file" rule exactly:**
- `shift_fine_addon_v1.v` — a genuine general 2-bit shifter (no
  unsupported-amount case, unlike its sparse coarse sibling), same
  direction convention, forwarding the REAL fine shift that actually
  happened (`shift_amount_out`, forced to 0 when `shift_en=0`,
  regardless of the configured value) downstream.
- `shift_lane_addon_v2.v` — cloned from `v1` (left completely
  untouched, its own testbench still passes bit-for-bit, unmodified);
  the ONLY change is a new `shift_fine_in[1:0]` input folded into
  `lane_cut`'s own `lane_s` computation (`shift_amt + shift_fine_in`,
  max 31, still exactly 5 bits).

**Real, full verification, four testbenches, all passing:**
`tb_shift_fine_addon_v1.v` (12 checks, the fine stage standalone,
both directions, all 4 real amounts); `tb_shift_lane_addon_v2.v` (a
full regression of `v1`'s own proven testbench with `shift_fine_in=0`
— bit-identical, confirmed — plus new, directly-simulated-not-hand-
derived cases proving the `lane_cut` window genuinely tracks the total
shift); `tb_shift_chain_v1.v` — the real, end-to-end proof of the
whole claim: both addons chained together, swept across every real
`(coarse, fine)` combination in both directions, each result checked
against a plain behavioral shift by the true total amount — 74/74
checks passing, confirming genuine, gap-free 0-31 coverage, not just
asserted by construction.

**One real bug found and fixed in the testbench itself while building
this, not the RTL:** the integration testbench's own direction sweep
used a 1-bit `reg` as a `for`-loop counter (`direction`), which wraps
silently past 1 back to 0 — a real infinite loop, caught by a hung
simulation, not a logic error in the design under test. Fixed with a
separate `integer` loop variable.

**Real, honest scope: sim-verified only, not yet wired into any
shell.** Per Alan's own explicit request ("Yes sim verify..."), this
stops at standalone RTL + testbenches. Wiring `shift_fine_addon_v1` +
`shift_lane_addon_v2` into `unicell_super_v1.v` through `v8.v` (in
place of the lone `shift_lane_addon_v1` instance each currently has),
allocating the real `shift_fine[1:0]` config bits from the 13
genuinely-reserved `SUPER_LATCH[79:67]` bits, and updating `icm_v3.py`'s
own field tables to match, are real, separate, deliberately unstarted
next steps.
