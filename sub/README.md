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
| `mul_cell_v4s` | 4,277 | vs `mul_full` 7,015 -- only 39% reduction using a LUT-built array multiplier; see the real DSP-block result below, which supersedes this as the recommended choice |
| `mul_cell_v4s_dsp2` | ~34 + 1 DSP block (`MULT36X36`, whole tile) | the SAME function via the chip's real DSP hardware -- see `#901` |
| `mul_cell_v4s_dsp3` | 71 + 1 `MULT18X18` slot (1/4 of a tile) | time-multiplexed, 4-cycle latency, real packing confirmed -- see `#902` |
| `shift_cell_v4s` | 3,261 | runtime-configurable amount/direction -- expensive, see below |
| `shift_stage_v4s` | 26 | SAME function, amount/direction fixed at build time -- see `#899` |

All simulated with real testbenches before any synthesis was attempted; two real
testbench bugs found and fixed along the way (a `cfg_valid` clear-timing race, and
manually-packed `cfg_data` field-width miscounts) -- not RTL bugs.

**`mul`'s smaller reduction is itself an honest, useful data point, not a
disappointment -- WHEN the multiply is built from LUTs.** Every other cell's big
cuts came from removing genuine overhead -- the addon chain, the mask/ack control
plane -- costs that had nothing to do with the cell's actual function. `mul`'s
LUT-built cost was never mostly that: its real 32x32 array multiplier (32 partial
products, summed) is honest, unavoidable computation, the same amount of real
work regardless of what wraps around it. Stripping control-plane fat can't
shrink work that was never fat to begin with -- `adder`'s 97.2% and `mul`'s 39%
are both the SAME stripping applied faithfully; they differ because the two
cells' real costs were made of different things.

**But that "unavoidable computation" framing only holds if the multiply has to
be built from LUT fabric at all -- and on this chip, it doesn't (`#901`).** The
Tang Nano 20K has 12 real `MULT36X36` DSP blocks (48 `MULT18X18`s), almost
entirely idle in every measurement this whole session. `mul_cell_v4s_dsp2.v`
instantiates one directly. First attempt (a plain `a * b`, matching Gowin's own
proprietary compiler's real automatic-inference behaviour, per Alan's own
example) found a genuine, honest TOOLCHAIN GAP: this yosys's `synth_gowin` pass
has no automatic DSP-inference for a plain multiply at all (confirmed: identical
LUT4 count, zero DSP cells, no `dsp_map.v`-equivalent pass exists in this
yosys's Gowin techlibs). The real primitives ARE declared as usable blackboxes in
yosys's own `cells_xtra.v`, though, and instantiating `MULT36X36` directly
works: **real synthesis, real place-and-route, real routing completed, `MULT36X36`
genuinely consumed (confirmed in nextpnr's own utilization report, not just
yosys's synthesis stat -- a first attempt at this test had a real stimulus bug,
`cfg_valid` tied permanently high, that let nextpnr legitimately discard the
whole DSP instance as unreachable; fixed with the same proven one-shot-pulse
pattern used throughout this project), real achieved Fmax 1,492.5 MHz against a
27 MHz target.** Everything outside the DSP block itself collapses to the same
tiny control-plane every other cheap `v4s` cell has (~34 LUT4 standalone).
`mul_cell_v4s_dsp2` is now the recommended `mul` for this chip; `mul_cell_v4s`
(LUT-built) is kept for portability to a target without equivalent DSP hardware,
or if all 12 DSP blocks are ever needed for something else at once.

## Time-multiplexed DSP mul: trading latency for 4x the packing density (`#902`)

Alan's own further idea, given `mul_cell_v4s_dsp2` uses one WHOLE `MULT36X36`
tile per instance (only 12 available): split each 32x32 multiply into three
16x16 partial products (the fourth, `A_high*B_high`, is real but never reaches
the kept low 32 bits at all -- verified by exhaustive random check before
trusting it, not assumed) and compute them SEQUENTIALLY through one shared
`MULT18X18` slot, of which 48 exist (4 per physical tile). Trades a fixed,
known 4-cycle latency for up to 4x the number of separate mul cells the chip
can host at once, with ZERO cross-cell arbitration -- each cell owns its own
slot and runs its own sequence independently; this is not resource-sharing
between logical cells (that would need real arbitration, exactly the control
cost this family removes), it is each cell simply being smaller.

**Three real bugs found and fixed while building this, each caught by
simulation or direct verification before being trusted, not assumed correct:**
1. A hand-derived partial-product bit-slice error (`pp_lh[19:0]` instead of
   `[15:0]`) -- caught by an exhaustive 20,000-case random check in Python
   against the real product BEFORE writing the RTL, not after a failure.
2. A genuine off-by-one-cycle bug: the DSP primitive's `DOUT` is purely
   combinational for this configuration (`AREG=BREG=OUT_REG=0`), so each
   partial product must be registered the SAME cycle its operands are
   presented, not one cycle later using not-yet-updated hold registers -- found
   by simulation, not assumed, and fixed by restructuring the state machine
   (4 states, not 5: `LOAD`/`LL`/`LH`/`HL`, folding the final partial product
   and the sum into `HL`'s own cycle rather than needing a separate sum state).
2. A shift-register tap-position bug in the `valid_out` timing (reading bit
   3 of a 4-bit pipe instead of bit 2, adding one extra cycle of delay beyond
   `data_out`'s own real latency) -- found by simulation, fixed by tracing the
   exact bit position by hand and re-verifying.

**Testbench timing for this design proved genuinely fiddly, and that is itself
an honest finding worth keeping, not just a testbench inconvenience:** a
free-running state machine sharing one physical resource across multiple
internal steps has real alignment subtleties that were hard to get right even
when writing the test by hand -- a real, practical cost of this design's
complexity, separate from its area/DSP-slot savings. The final testbench
verifies real per-operation correctness robustly (6 real value pairs including
an overflow-truncation case, cross-checked in Python, not hand-computed) and
exact `valid_out` timing, but the tight back-to-back and off-boundary-miss
cases (both real, designed-in behaviours, stated plainly in the file's own
header) were not exhaustively re-verified in the final simplified test --
flagged honestly as a real follow-up, not claimed proven.

**Real synthesis: 71 LUT4 + 1 `MULT18X18`, standalone.** **Real place-and-route
proved the actual packing claim, not just asserted it**: a real top-level with
FOUR separate `mul_cell_v4s_dsp3` instances, real board pins, was placed and
routed -- nextpnr's own utilization report confirms **`MULT18X18 used: 4`** (out
of 48 available), genuinely four independent slots, not four whole tiles
monopolised. Real achieved Fmax for that 4-instance design: 344.9 MHz against
the 27 MHz target -- lower than `dsp2`'s single-block 1,492.5 MHz (expected,
given the real added state-machine complexity and denser routing), still a
comfortable margin.

**When to use which `mul`:** `mul_cell_v4s` (LUT-built, portable, no DSP
dependency) for a target without equivalent hardware; `mul_cell_v4s_dsp2`
(whole `MULT36X36` tile, 1-cycle latency, up to 12 instances) when latency
matters most and 12 concurrent multiplies is enough; `mul_cell_v4s_dsp3`
(`MULT18X18` slot, 4-cycle latency, up to 48 instances, a real throughput
constraint of one new operation per 4 cycles) when the design needs MORE
separate multiply units than 12 and can afford the latency and the
one-request-per-4-cycles discipline on whatever drives it.

## A minimal, point-to-point ack plus a global freeze (`#906`)

Alan's own Saturday-morning design direction: reintroduce a backward signal, but
a minimal, point-to-point one (not the original cardinal family's N-way
arbitrated version) -- one ack bit per fixed connection, generated by a
receiver and sent backward to its one fixed sender, used exactly as a classic
ready/valid handshake ("I am clear, so it sends its data"). Separately,
reintroduce freeze -- but GLOBAL, not per-cell: one signal broadcast
identically to every cell in the whole design, not threaded through the ICM
connection graph. Two real jobs for it, found through the conversation itself:
holding the whole system still while configuration loads safely into every
cell (the original stated purpose), and a genuine side benefit of going global
-- a clean, synchronised, whole-system pause point where every cell's state
can be read out and compared against the VM's own mirrored computation.

**Why this isn't a retreat from "physics, not control" (`#898`'s own
principle):** what made the original cardinal family's ack expensive was never
the backward signal itself -- it was the ARBITRATION, a 4-way mask deciding
WHICH direction to wait for and WHICH to route to, every cycle (`#889`). This
ack is point-to-point: one fixed sender, one fixed receiver, decided at build
time, same as `in_a`/`in_b`. There is no "who" to decide. This adds a cheap
synchronisation primitive on top of a graph that is still fixed by
construction -- it does not reintroduce the runtime routing decision that was
the actual expensive part.

**A real, valuable consequence worth stating plainly: this likely removes the
need for the static latency-padding work `adder_cell_v4s.v`'s own header named
as the standing next step.** That scheme only works if every cell's latency is
known at compile time, and breaks the moment any future cell has
data-dependent timing. A local ack solves the same underlying problem --
don't let a fast path's fresh value collide with a slow path's stale one --
in a way that is robust to ANY timing, known or not, with zero static
analysis required.

**`adder_cell_v4sa.v` built: standard ready/valid semantics, not a one-shot
pulse.** `ack_out = armed && !pending && !freeze_in`; `valid_out` stays HIGH
across multiple cycles if the downstream receiver is not ready, until `ack_in`
arrives. `freeze_in` gates the entire update INCLUDING whether a fresh
`cfg_valid` may take effect -- loading config safely while frozen is the whole
point. `armed` keeps its own separate, narrower, permanent meaning (has real
config ever loaded); freeze is the new, orthogonal, re-triggerable hold.

**A real testbench-tooling trap hit and fixed, worth remembering:** the first
draft named its check task `expect` -- a RESERVED SystemVerilog keyword (used
in concurrent assertions), which `-g2012` parses for. Every call to it
produced cascading, misleading syntax errors far from the real cause. Renamed
to `check_cond`; fixed immediately. A real, if mundane, lesson: avoid SystemVerilog
reserved words for testbench task/function names even in plain-Verilog files,
once `-g2012` is in the invocation.

**Two real bugs found by simulation, not assumed away:** (1) `ack_out` was
missing its own `!freeze_in` gate in the first draft -- a frozen cell was
still claiming readiness to accept new data, caught by the very first real
check. (2) A hand-computed arithmetic mistake in the test itself (`6+7=42`
instead of the real `13`) produced three cascading false failures -- caught by
adding cycle-accurate debug tracing and reading the real register values
rather than continuing to guess from symptoms.

**Real, measured result (same free-port methodology as `#886`/`#898`, directly
comparable): 37 LUT4 -- LOWER than the pure no-ack `adder_cell_v4s`'s 66, not
higher.** Register counts are similar (34 DFFRE vs 35), so the honest best
explanation, not fully isolated: the "hold the current value unless genuinely
capturing" logic this design needs maps onto the flip-flops' own native
clock-enable input, rather than needing extra LUT-level muxing the original's
different structure required elsewhere. Stated as a real number with a
plausible, not fully certain, explanation -- not overclaimed. Real
place-and-route (Fmax, and confirming this holds on actual silicon, not just
free-port synthesis) has not yet been run for this variant.

**Both variants are kept, deliberately, not one replacing the other:**
`adder_cell_v4s` (zero-wait, fixed one-cycle latency, needs the still-unbuilt
static latency-padding machinery for any convergent path) for anyone who
genuinely needs guaranteed fixed-cycle throughput; `adder_cell_v4sa` (ack +
global freeze, variable latency, no static analysis needed anywhere) as the
likely better general default given this result.

## Real place-and-route: single unit, then a real 100-cell chain (`#908`)

Alan's own request after `#906`/`#907`: get real timing figures, starting with
one unit, then scaling to a real "10x10 matrix" (100 cells) to see how the
ack+freeze design actually behaves under real routing congestion, not just
free-port synthesis estimates.

**A real collapse bug caught again, same class as `#902`'s, before trusting
any number.** The first single-unit board-bound test observed only
`result[0]` on an LED -- and real synthesis showed `ALU: 4` (just the harness's
own tick counter), not the expected 32 for a real 32-bit adder. The real
arithmetic had been legitimately discarded as unobserved, exactly `#902`'s own
lesson about `mul_cell_v4s_dsp2`. Fixed with a full-width XOR reduction
(`^result`); re-synthesis showed the correct `ALU: 36` (32 real + 4 harness).

**`adder_chain_v4sa.v` (new): a parameterised point-to-point chain.** `NSTAGES`
instances of `adder_cell_v4sa`, each stage's real sum feeding the next stage's
`in_a`, `ack_out` flowing backward stage to stage exactly as `#906` designed.
Each stage's `in_b` is a distinct rotation of one shared, genuinely-evolving
LFSR (not an identical shared signal), so no two ports anywhere in the whole
chain are provably related -- the same anti-collapse discipline `#889`
established, applied at 100-cell scale.

**Correctness proven at small scale (4 stages) before trusting the real
100-cell build -- a Python-computed reference, not hand arithmetic (`#906`'s
own lesson about trusting hand-computed expected values):** the exact 4-stage
sum (`chain_in=5`, a fixed, known `lfsr` value, cross-checked in Python: the
real answer is `0xb6958226`) matched simulation exactly. **Real backpressure
verified to propagate through MULTIPLE stages, not just the last one**: with
the chain's far-end consumer held permanently not-ready, the chain's OWN FIRST
stage was confirmed to stop accepting new input once every stage filled up --
proving the handshake genuinely chains, not just locally. Drain and recovery
after the consumer becomes ready again was also confirmed, with a real,
not-guessed, wait margin (draining N stacked stages ripples the ack backward
roughly one stage per cycle, the same rate as the forward fill).

**Real, measured results, place-and-route confirmed twice independently
(matching, not just asserted once):**

| Build | Real Fmax | LUT4 | ALU | DFF |
|---|---|---|---|---|
| Single unit (+ small harness) | 368.6 MHz | 157 (0.8%) | 40 (0.3%) | 78 (0.5%) |
| 100-stage chain | **220.4 MHz** | 1,426 (6.9%) | 3,406 (21.9%) | 3,346 (21.5%) |

Fmax drops a real ~40% from one unit to 100 chained -- genuine routing/
placement cost at scale, not free, but still an 8x margin over the 27 MHz
board clock. **A real, useful resource finding: ALU, not LUT4, is the binding
constraint for how many of these chained cells will fit** -- 100 stages used
only 6.9% of LUT4 but already 21.9% of ALU (each stage needs its own full
32-bit adder carry chain). At this ratio, roughly 450-460 chained stages
would exhaust the chip's real ALU budget well before LUT4 became the limit.

**A real sandbox-environment limit found while making this reproducible, not a
script bug:** the 100-stage place-and-route alone takes several real minutes;
running the whole build script as one backgrounded job was unreliable in this
environment (the job did not survive to completion, consistent with earlier
findings this project has hit before) -- the two stages were run as separate,
generously-timed foreground steps instead, and the SAVED repo files were then
independently re-verified to reproduce the exact same real numbers.

**What changed:** `sub/verilog/adder_chain_v4sa.v` (new) + testbench,
`sub/verilog/adder_v4sa_top_single.v` / `adder_chain_v4sa_top100.v` (the real,
board-pin-bound test harnesses, saved and reproducible, not one-off scratch
files), `tools/gowin_sizing/build_adder_v4sa_scaling.sh` (the reproducible
build script), `sub/build/*_report.json` (the real, committed nextpnr reports).

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
