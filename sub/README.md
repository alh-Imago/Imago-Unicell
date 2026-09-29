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

## Status

Scoping and first cell proven (adder). Not yet on real hardware. The
latency-padding work this family creates a real need for has not been started.
