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
