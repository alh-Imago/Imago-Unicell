# sub/ -- the "v4s" (stripped) cell family

Real design direction from a live conversation with Alan (2026-09-29 evening into
morning), building directly on that session's own measured findings (`points.md
#886`/`#889`/`#890`/`#891`). Recorded here as the standing scope note for this
folder; see `points.md #898` for the full narrative and the first real measured
result.

## The idea, in one line

Strip each cell back to its bare compute function -- no addon chain, no 4-way
cardinal routing, no backward ack/flow-control -- accepting a fixed, ASIC-like
datapath in exchange for a dramatic area cut, specifically because this project's
smallest real hardware target (the Tang Nano 20K) cannot host the general,
fully-reconfigurable cell at any useful scale (`#886`/`#887`/`#889` all measured
this independently). This is a deliberate trade of UniCell's general "topology is
computation, reconfigurable at runtime" property for a fixed-at-build-time
datapath, made specifically because this small card cannot afford the general
version -- not a claim that the general architecture is wrong.

Alan's own framing for why the earlier design was expensive: not just topology as
program, but a bus-contention-avoiding, mask/ack-arbitrated design -- computing
through *control*. The stripped family is an attempt at computing through
*physics*: a wire that only ever goes one place doesn't need a decoder to pick
where it goes.

## What's gone, and why (see individual cell file headers for full detail)

- **The addon chain** (shift_lane/nibble_mask/invert): `#886` measured
  `shift_lane_addon_v2` alone at ~2,600 LUT4 -- bigger than a whole `adder_full`
  core (2,348). Gone entirely from the compute cells; shift and nibble-mask become
  their own dedicated cell types instead of a chain every cell pays for whether it
  uses it or not.
- **4-way cardinal routing** (N/S/E/W, upstream/downstream masks): collapses to
  fixed, dedicated ports per operand (e.g. `in_a`/`in_b` for a binary cell). "No
  cardinality" removes the runtime *decision* of which direction data comes
  from/goes to; it does not reduce a function's real arity below what it needs.
- **Backward ack/ready (flow control)**: removed entirely. This is what makes the
  family genuinely timing-agnostic -- no cell can ever be told to wait. The real
  consequence, named directly by Alan: every cell's latency must be a KNOWN, FIXED
  number of cycles at build time, and any two paths that CONVERGE on a later cell
  must arrive latency-matched, or a fresh value on one side silently combines with
  a stale one on the other. Not a new problem for this project -- `#762`-`#765`'s
  timing model and `dsp_latency_v1`'s latency-padding mechanism already exist to
  solve exactly this; they have simply never been pointed at this family yet. That
  padding work is the real next step this family creates a need for.
- **freeze_in**: removed as a direct consequence of the above -- a per-cell pause
  would silently break every latency guarantee downstream of it. A future global
  pause, if wanted, must be a single synchronized clock-enable across the whole
  chain at once, never per-cell -- a separate design question.
- **Live per-direction reprogramming**: removed for this first cut (no cardinal
  direction left to receive a reprogramming word from). Boot-load config
  (`cfg_valid`/`cfg_data`) only. A future shared reprogramming bus for this family
  is a separate, undecided question.

## The "timing line"

A single FORWARD valid bit riding alongside data out, asserted for exactly one
cycle when the data is a genuinely new result. Not ack's replacement -- carries no
backward information, never stalls anything upstream.

## Planned cell types

- **Plain compute core** (adder built first; compare, and others to follow) --
  fixed operand-count in, one out, one timing line.
- **Shift core** -- the extracted shift_lane function as its own cell.
- **Nibble-mask core** -- the extracted nibble_mask function as its own cell.
- **Router/split cell** -- a FIXED physical junction (path set once at
  configuration time, no runtime decision) for the rare case a cell's single
  output genuinely needs to reach more than one place. Deliberately NOT an
  arbitrated/masked router -- if it evaluates anything at runtime, it is just the
  old cardinal decode logic wearing a new name, and the whole point is lost.
- **branch's split**: `branch` today does compare AND route in one cell, and
  `#889` measured it as the single most expensive type found all session (9 cells
  = 34.6% of the whole chip). Splits into a plain **compare** cell (A, B in; one
  flag out; no routing decision at all) and a small **select** cell (the flag plus
  already-present candidate values in; one passed through) -- concentrating the
  one unavoidable runtime decision into one small, purpose-built cell instead of
  every cell carrying a slice of it.
- **nano -- the one real exception.** Every other stripped cell is fixed-role,
  single-shot-per-cycle. Nano's real job (proven load-bearing by the actual fold
  work, `#880`) needs one operand held across many invocations while a second,
  genuinely different operand streams past on every firing -- two structurally
  different roles, not "the same port, sometimes early." The original design
  solved this by arrival-order tracking on a shared wire (`hold_in`, `a_arrived`),
  which is itself a small piece of control state -- exactly what a
  fully-timing-agnostic design removes. So nano cannot fit the uniform
  A-in/B-in/out/timing-line shape the rest of the family gets: it needs a
  dedicated hold-in port (loaded rarely, held across cycles), a dedicated flow-in
  port (new every cycle), and an explicit "load the hold value now" signal, since
  there is no more arrival-order trick to lean on.

## Naming convention

`<function>_cell_v4s.v` -- "v4s" for "v4, stripped," parallel to the existing
`_v4`/`_v4c` (carrier) lineage. Testbenches: `tb_<function>_cell_v4s.v`.

## First real result

`adder_cell_v4s`: **66 LUT4** (measured via the same free-port synthesis-only
methodology as `#886`'s `adder_full` figure), against **2,348 for `adder_full`** --
a 97.2% reduction. See `points.md #898` for the full write-up, including a real
testbench race condition found and fixed along the way (not an RTL bug).

## A second, bigger insight: build-time-fixed vs. runtime-loaded config (`#899`)

Alan's own idea, chasing why `shift_cell_v4s` (the runtime-configurable
extraction of `shift_lane_addon_v2`, amount and direction loaded via `cfg_data`)
still measured a real 3,261 LUT4 despite every other cut: limit each shift cell
to a small range and chain them for larger totals. Measuring it directly found
something sharper than "limit the range" -- the coarse shift mux ALONE (with
`lane_cut` removed entirely) was still 1,686 LUT4, more than half the total, and
none of that cost is the actual data movement (each case is real, free rewiring)
-- it is the SELECT logic: with `shift_amt` a live runtime signal, the
synthesiser must build real 5-bit comparators and a genuine 9-way mux tree,
because it can never know at build time which case will be chosen.

**`shift_stage_v4s.v`: the same shift, with the amount and direction as real
Verilog PARAMETERS (fixed at synthesis time) instead of `cfg_data` fields.**
Measured: **26 LUT4** for a real amount (8, right), 34 for passthrough (0) --
against runtime-configurable `shift_cell_v4s`'s 3,261. A **99.2% reduction**.
Chaining two stages (left-by-8 then left-by-4) was simulated and confirmed to
compose exactly (`1 << 8 << 4 == 1 << 12`, matching the original sparse table's
own supported amount), with a real, known, fixed 2-cycle latency for the chain --
exactly the number the family's latency-matching work needs.

**Why this is bigger than one cell type.** This is "physics, not control" pushed
one level deeper than routing: not just no runtime ROUTING decision, no runtime
FUNCTION-SELECTION decision either. A cell whose behaviour is fixed the moment
it is BUILT, not the moment it is CONFIGURED, costs almost nothing beyond its
own control logic -- the function itself becomes free wiring. This likely
generalises to `compare`'s threshold, `mask`'s pattern, and others: any v4s
cell's config field is a candidate for this same treatment, IF the deployment
can accept "changing this cell's behaviour means rebuilding it," not just
reloading it. That is a genuine, real trade-off (flexibility vs. cost, the
ROM-vs-RAM distinction `ram_cell_v4s` already has explicitly), not something to
apply everywhere without deciding it deliberately -- `shift_cell_v4s`
(runtime-configurable) and `shift_stage_v4s` (build-time-fixed, chainable) are
BOTH kept, for exactly this reason: which one is right depends on whether a
given deployment needs to change shift amounts without a rebuild.

## Real, measured results so far

| Cell | LUT4 | Notes |
|---|---|---|
| `adder_cell_v4s` | 66 | vs `adder_full` 2,348 -- 97.2% reduction |
| `compare_cell_v4s` | 26 | value vs. static threshold, signed comparison |
| `accumulator_cell_v4s` | 303 | two dedicated event ports (inc/dec) replace direction-as-meaning |
| `latch_cell_v4s` | 4 | three dedicated pulses (set/clear/toggle), CLEAR>SET>TOGGLE kept |
| `sequencer_cell_v4s` | 85 | `advance_in` forward pulse replaces "ack completed" as the trigger |
| `ram_cell_v4s` | small | flowing vs. fixed(ROM) mode, both simulated |
| `router_cell_v4s` | 35 | genuinely fixed fan-out, zero runtime decision |
| `mask_cell_v4s` | 66 | direct extraction of `nibble_mask_addon_v1`, unchanged |
| `mul_cell_v4s` | 4,277 | vs `mul_full` 7,015 -- only 39% reduction, and correctly so, see below |
| `shift_cell_v4s` | 3,261 | runtime-configurable amount/direction -- expensive, see below |
| `shift_stage_v4s` | 26 | SAME function, amount/direction fixed at build time -- see `#899` |

All simulated with real testbenches before any synthesis was attempted; two real
testbench bugs found and fixed along the way (a `cfg_valid` clear-timing race, and
manually-packed `cfg_data` field-width miscounts) -- not RTL bugs.

**`mul`'s smaller reduction is itself an honest, useful data point, not a
disappointment.** Every other cell's big cuts came from removing genuine overhead
-- the addon chain, the mask/ack control plane -- costs that had nothing to do
with the cell's actual function. `mul`'s cost was never mostly that: its real
32x32 array multiplier (32 partial products, summed) is honest, unavoidable
computation, the same amount of real work regardless of what wraps around it.
Stripping control-plane fat can't shrink work that was never fat to begin with --
`adder`'s 97.2% and `mul`'s 39% are both the SAME stripping applied faithfully;
they differ because the two cells' real costs were made of different things.

## Status

Ten cell functions proven (adder, compare, accumulator, latch, sequencer, ram,
router, mask, mul, shift/shift_stage), all simulated, all measured. Not yet on
real hardware. Still to do: `branch` (architecturally in tension with the
family, needs a real design conversation, not a mechanical strip), `nano` (the
confirmed two-input-role exception), and `command` (structurally at odds with
"no live reprogramming," since reprogramming is its whole purpose). The
latency-padding work this family depends on the moment more than one stage is
chained has not been started.

## A stated design rule (Alan's own, confirmed across every cell built so far)

However many genuinely distinct roles a function needs -- operands, or
independent events, or triggers -- that's how many dedicated ports it gets.
Never a runtime decision about which port means what. `adder`/`mul`'s `in_a`/
`in_b`; `accumulator`'s `inc_pulse`/`dec_pulse`; `latch`'s three pulses;
`router`'s fixed per-output enables -- all the same rule, applied to whatever
the function actually needs, not a fixed template forced onto every cell.
