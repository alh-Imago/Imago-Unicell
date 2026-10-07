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

## The real "flex" width parameter -- 18-bit confirmed to deliver exactly the predicted ALU saving (`#909`)

Alan's own follow-up to `#908`'s "ALU runs out before LUT4" finding: `#906`-
`#908` are all 32-bit. If a cell's width matches the MAN file's own recorded
native width (18 for this card, `#903`/`#904`), the cells themselves get
narrower -- and since `#908` just found ALU, not LUT4, is the real ceiling for
arithmetic chains, going native-width directly attacks that exact ceiling,
not just a vague general saving. He named the three real pieces this needs:
a variable-width version of the core files, a switch in the assembler to pick
the right width per target, and the VM side reflecting the same choice.

**`adder_cell_v4sa.v` made genuinely width-parameterised, purely additively.**
A real `parameter WIDTH = 32` now controls `in_a`/`in_b`/`data_out`/
`out_buffer`, passed straight through to `adder_v1`'s own already-existing
`WIDTH` parameter. Defaults to 32, so every one of `#906`/`#908`'s committed
measurements stays exactly valid, unchanged -- this is not a new cell, it is
the same cell made flexible. `cfg_data` deliberately stays a fixed 32 bits
regardless of `WIDTH`: it only ever needs to hold a 1-bit `subtract_mode`
flag here, and `sequencer_cell_v4s` already needed a config bus WIDER than
its own data width, so tying the two together would be the wrong coupling to
bake in now.

**Real correctness proven specifically at 18-bit, not just assumed from the
parameter working syntactically.** A dedicated testbench confirms real
18-bit addition AND the width-specific wraparound boundary (`0x3FFFF + 1`
wraps to `0` at bit 18, not bit 32) -- proving `WIDTH` genuinely changes the
real arithmetic, not just the port declarations. One real testbench mistake
caught before trusting it: an attempted "this would be the wrong, 32-bit-style
answer" negative check used an 18-bit literal (`18'h40000`) that was itself
out of range and silently truncated to 0 by Verilog before the comparison
ever ran, making the check meaningless as written -- removed once diagnosed,
since the positive wraparound check alone already proves the real behaviour.

**Real, measured result: the predicted ALU saving confirmed EXACTLY, not
approximately.** ALU: 32 (WIDTH=32, `#906`) -> **18 (WIDTH=18)** -- a precise
linear match with the width ratio (18/32 = 0.5625), exactly as the ripple-
carry structure predicts. LUT4: 37 -> 23 (62%, a bit more than pure
proportionality, since the armed/pending/ack control logic has a fixed cost
that does not shrink with data width at all -- only the arithmetic and
data-path muxing do). This is the real, quantified version of `#908`'s own
ALU-is-the-ceiling finding turning into an actual fix: at 18-bit, the same
100-stage chain that used 21.9% of the chip's ALU at 32-bit would use
roughly 12.3%, meaning something closer to 175-180 chained stages become
possible before hitting the same ALU ceiling `#908` measured, not ~100.

**What is genuinely done here, and what Alan's own three pieces still need --
stated precisely, not blurred together:** the CORE FILE is now real,
parameterised, and measured at both widths -- that part is finished. The
ASSEMBLER SWITCH (reading the MAN file's native width and instantiating with
the right `WIDTH`) and the VM-SIDE REFLECTION of that same choice are both
still the standing, not-yet-built architecture work from `#903`-`#905` --
this entry gives that future work a real, working, measured parameter to
drive, it does not build the thing that drives it.

## The real 100-cell chain at 18-bit -- and a real arithmetic mistake corrected (`#910`)

Alan: test the 100-cell array at the real native width, then move on to the
rest of the core files and the assembler. `adder_chain_v4sa.v`'s own `WIDTH`
parameter threaded through purely additively (default 32 unchanged, confirmed
by re-running `#908`'s own existing chain testbench with zero changes needed).
Real 4-stage correctness re-proven specifically at 18-bit first, against a
fresh Python-computed reference (`0x18226` for a known `chain_in`/`lfsr`),
before trusting the full 100-stage build -- same discipline every real number
in this family has needed.

**Real, measured, place-and-routed results, 32-bit vs. 18-bit, same 100
stages:**

| Width | Real Fmax | LUT4 | ALU | DFF |
|---|---|---|---|---|
| 32-bit (`#908`) | 220.4 MHz | 1,426 (6.9%) | 3,406 (21.9%) | 3,346 (21.5%) |
| 18-bit (`#910`) | **287.4 MHz** | 711 (3.4%) | 2,006 (12.9%) | 1,946 (12.5%) |

**Fmax went UP, not just resource usage down** -- a genuine bonus `#909`'s
single-cell test could not show: a narrower datapath means less wiring and
less routing congestion across the whole chain, not only fewer gates. ALU
landed at 12.9%, closely matching `#909`'s own single-cell-based prediction
of ~12.3% (the small gap is the harness's own fixed overhead -- the LFSR,
tick counter -- which does not shrink with `WIDTH`, becoming a slightly
larger share of a smaller total).

**A real arithmetic mistake, caught by checking the extrapolation against
real measured data rather than trusting it, and corrected here rather than
left standing.** `#909` estimated "~175-180 chained stages" would be possible
at 18-bit before exhausting the chip's ALU budget. Checked against this
entry's own real, placed-and-routed 100-stage figure (12.9%, not assumed):
the real number is **100 x (100/12.9) = ~775 stages**, not 175-180 -- `#909`'s
estimate was wrong by roughly 4.4x, a genuine computational slip, not a
rounding difference. Correct comparison: ~457 stages at 32-bit (from `#908`'s
21.9%) versus ~775 at 18-bit (from this entry's real 12.9%) -- a real ~1.7x
capacity increase, consistent with the 32/18 = 1.78 width ratio, not the much
larger, wrong figure `#909` stated. Recorded here plainly, the same way
`#883`/`#884`/`#906` already recorded their own corrected measurements --
the mistake stands in the ledger alongside the fix, not quietly edited away.

**What changed:** `sub/verilog/adder_chain_v4sa.v` (now genuinely
width-parameterised, purely additive), `tb_adder_chain_v4sa_width18.v` (new,
real 18-bit 4-stage correctness proof), `adder_chain_v4sa_top100_width18.v`
(the real, board-pin-bound, saved and reproducible 18-bit 100-stage harness),
`sub/build/adder_chain_v4sa_top100_width18_report.json` (the real, committed
nextpnr report). No existing file's behaviour changed; both pre-existing
chain tests re-run unchanged and still pass.

## The Flex-Sub family begins: `accumulator_cell_v4sa` (`#911`)

Alan: start converting the core files to the real "Flex-Sub" shape -- ack+freeze
(`#906`) plus a genuine `WIDTH` parameter (`#909`/`#910`) -- for the rest of
the family, not just adder. Given `#906`'s own finding that ack+freeze costs
LESS than the pure fixed-latency design, the Flex-Sub foundation is built on
the ack-bearing shape from the start for cells that did not already have one,
rather than bolting `WIDTH` onto the older no-ack `v4s` versions separately.

**A real, pre-existing bug found and fixed while building this, not inherited
silently.** `accumulator_cell_v4s.v` already had an internal `WIDTH`
parameter, but its `data_out` PORT stayed hardcoded `[31:0]` regardless -- the
external interface never actually reflected a narrower width correctly.
Fixed in `accumulator_cell_v4sa.v`: `data_out` is genuinely `[WIDTH-1:0]`.

**A real testbench race bug, the SAME class `#906` first found, caught again
here -- worth naming plainly as a pattern to watch for, not a one-off.**
Clearing `inc_pulse`/`dec_pulse` with a bare blocking assignment immediately
after `@(posedge clk)`, in the same active region as the edge, raced the
DUT's own same-edge sampling of those signals. The symptom was genuinely
confusing on its face: `out_buffer` captured correctly while `accumulator`
itself appeared stuck at 0 forever, which looked like two DIFFERENT register
updates behaving inconsistently despite sharing the same triggering
condition. Diagnosed with `$strobe` (true end-of-timestep values, removing
any ambiguity `$display` plus a settling delay could not fully resolve) --
confirmed `dut.inc_pulse` read 0 at the DUT during the very edges where a
real capture clearly happened, proving the RTL itself was correct and the
race was entirely in the test. Fixed with the same proven pattern: settle
BEFORE clearing, not just before the next read.

**Real, measured result: the same clean ALU ratio found again, independently,
on a second cell.** ALU: 128 (`WIDTH=32`) -> **72 (`WIDTH=18`)** -- 0.5625,
the exact same ratio `#909` found for `adder_cell_v4sa`, confirming this is a
genuine, general property of width-parameterised arithmetic on this chip, not
a one-off result specific to the adder. LUT4 (summed LUT1-4): 325 -> 242
(74.5%), a smaller reduction than the pure ALU ratio since the armed/pending/
pulse_mode/threshold control logic has a fixed cost that does not shrink
with `WIDTH`, same reasoning as `#909`'s own adder finding.

**A deliberate, stated scoping decision, not a silently skipped step:** the
18-bit-specific wraparound boundary (the thing `#909` built a dedicated test
for on the adder) was NOT separately re-proven here. The underlying
truncation is the same Verilog language-level mechanism (`+` on a
declared-width register) already proven correct at 18-bit for
`adder_cell_v4sa` -- re-testing that exact mechanism per cell has
diminishing real value once the language guarantee itself is established.
Real correctness WAS re-proven for everything cell-specific: continuous
mode, pulse mode's real threshold crossing, real backpressure holding the
stale offer across multiple stalled cycles, and freeze as a true, total
pause -- 12 real checks, all passing.

**What changed:** `sub/verilog/accumulator_cell_v4sa.v` (new) + testbench.
`sub/README.md` updated. No existing file's behaviour changed.

## `compare_cell_v4sa`: the lessons applied proactively, and a genuine, honest surprise (`#912`)

Alan: proceed carefully into the next cell, remembering the lessons from
`#906`/`#911`. Applied deliberately this time, not discovered again: the
testbench's `cfg()` and a new `fire_compare()` helper both settle (a real
delay) BEFORE clearing any signal the DUT also samples on the same edge --
the exact race class both those entries hit. Real payoff: **all 14 checks
passed on the first run, no debugging needed this time.**

**Real, measured: the same 0.5625 ALU ratio confirmed a THIRD time,
independently.** ALU: 32 (`WIDTH=32`) -> **18 (`WIDTH=18`)** -- exactly the
same ratio `#909`/`#911` found for adder and accumulator. Three different
cells, three different arithmetic operations (add, running-total add,
signed compare), the same clean linear ALU scaling every time -- this is
clearly a real, general property of this chip's primitives, not a
coincidence tied to any one cell's structure.

**A genuine, honest surprise, reported plainly rather than smoothed over:
LUT4 went UP at 18-bit, not down** (28 at WIDTH=32 -> 86 at WIDTH=18, summed
LUT1-4). Confirmed not a `-chparam` artifact by rebuilding with `WIDTH=18`
hardcoded directly as the default. The real cause was not chased down to
certainty -- that would mean digging into ABC's internal synthesis
heuristics for a curiosity, not a correctness question, and the absolute
numbers involved are tiny either way (both well under 0.5% of the chip's
20,736-LUT4 budget). What this entry WILL state plainly: the clean ALU ratio
found on adder and accumulator does NOT mean every resource scales down
predictably with `WIDTH` for every cell -- `compare`'s particular
"mostly-constant output with one real bit" structure synthesises
differently at this narrower width, and LUT4 in particular should be
measured per cell, not assumed from the ALU pattern alone.

**What changed:** `sub/verilog/compare_cell_v4sa.v` (new) + testbench.
`sub/README.md` updated. No existing file touched.

## Five more Flex-Sub cells: latch, sequencer, ram, router, mask (`#915`)

Alan: move through the remaining cell types with care, remembering the
lessons from `#906`/`#911`/`#912`. Applied proactively from the start on
every one of these five: the settle-before-clear discipline, built into every
testbench's own helper tasks before writing a single check. Real payoff:
**all five cells passed their full test suites on the first simulation run**
-- no debugging sessions needed on any of them.

**`latch_cell_v4sa` / `sequencer_cell_v4sa`: WIDTH genuinely does not change
real cost, and that is stated honestly, not oversold.** Both cells' real
payload is a fixed, narrow value (1 bit for latch, 8 bits for sequencer,
packed into `cfg_data`'s own field layout) -- `WIDTH` only changes
`data_out`'s zero-padding. Measured identically at `WIDTH=32` and `WIDTH=18`
for both (17 cells and 193 cells respectively, unchanged) -- confirms the
expectation precisely rather than assuming it.

**`ram_cell_v4sa`: a real design point worth stating precisely.** Fixed mode
and flowing mode genuinely need different treatment, not one shape forced
onto both -- fixed mode's whole point is "always valid, never drains," so it
does not use the pending/ack protocol at all (`ack_out` simply reflects
"configured", not "not busy"); flowing mode uses the standard discipline.
Real, meaningful DFF/LUT reduction from the narrower stored register: DFFRE
35 -> 21, LUT1-4 39 -> 25.

**`router_cell_v4sa`: a genuinely new design question, resolved and tested
precisely.** Two independent outputs, each potentially feeding a different
downstream receiver on its own schedule -- resolved as "the router only
accepts new input once every ENABLED output's own previous offer has been
acked; a disabled output never blocks anything, since it never offered
anything." Tested directly, not just asserted: a real differential-
backpressure case (one output acks immediately, the other stalls for several
cycles) confirmed `ack_out` correctly stays low until BOTH enabled outputs
have genuinely cleared, not just the fast one. Real DFF reduction from the
narrower data register (37 -> 23); LUT4 unchanged (the busy/pending control
logic does not depend on data width).

**`mask_cell_v4sa`: the mask word scales with the width (ledger #968, supersedes the nibble design described in #877).**
The mask word is always 8 bits, so each mask bit covers `GROUP = ceil(WIDTH/8)` data bits: 1 bit up to WIDTH 8, 2 up to 16, 3 up to 24,
4 up to 32 (exactly the original nibble, so WIDTH=32 is unchanged), 5 up to 40. There are `ceil(WIDTH/GROUP)` real groups (always <= 8),
the top group may be partial, and mask bits beyond the last group are ignored. Every data bit is covered at every width. The earlier
fixed 4-bit nibble left bits 32+ without a mask bit at WIDTH > 32 (nibble 8 read `nibble_mask[8]`, out of range, and was x). At WIDTH=18
a mask bit covers 3 bits (6 groups), no longer a nibble: the same mask value means different bits at different widths -- a deliberate
uniform rule, to be stated in the user documentation. Checked against the real cell at W = 4, 8, 9, 16, 17, 18, 24, 25, 32, 33, 36, 40
(`tests/vm/test_flex_grid_addons_v1.py`) and by `tb_mask_cell_v4sa_width18.v`. (Cost figures below were measured with the nibble design.) Real DFF/LUT reduction, roughly
proportional to width: DFFRE 43 -> 26, LUT1-4 37 -> 23.

**What changed:** `sub/verilog/latch_cell_v4sa.v`, `sequencer_cell_v4sa.v`,
`ram_cell_v4sa.v`, `router_cell_v4sa.v`, `mask_cell_v4sa.v` (all new) + their
testbenches, plus `tb_mask_cell_v4sa_width18.v` (the real 18-bit
partial-nibble proof). `sub/README.md` updated. No existing file touched.

## shift_stage and both mul variants join the Flex-Sub family (`#916`)

Alan: for shift, the real max shift value is directly tied to WIDTH (the
meaningful range is 0 to WIDTH-1, not an independent fixed ceiling); for mul,
keep both the on-board DSP logic and the actual LUT-built mul core available
as real options, not one replacing the other.

**`shift_stage_v4sa`: WIDTH threaded through correctly, the SHIFT_AMT-vs-WIDTH
relationship stated precisely.** The underlying shift (`<<`/`>>` on a
WIDTH-bit value) needed no new logic -- the same real Verilog truncation
mechanism `#909` already proved correct for arithmetic applies here too.
Proven specifically at the real 18-bit boundary: a left shift by 10 of an
all-1s 18-bit value truncates correctly WITHIN 18 bits, cross-checked in
Python, confirmed NOT to accidentally behave like a 32-bit shift would. One
real testbench mistake caught and fixed: a backpressure check wrongly
expected a STALE value to persist, when the test's own prior step had
already freed `pending`, meaning the next `valid_in` genuinely captured a
NEW value -- an RTL-correct, test-wrong case, same honest accounting as
every other caught mistake in this family. Real DFF reduction from the
narrower register (26 -> 10); LUT4 unchanged (control logic, same as
router/mask's own pattern).

**`mul_cell_v4sa_dsp`: the real DSP block, Flex-Sub'd, with its own honest
hardware ceiling stated plainly.** `WIDTH` must be `<= 36` here -- a genuine
hardware limit, not a soft guideline: `MULT36X36` is a FIXED-size primitive
that does not get cheaper as `WIDTH` narrows, only the small amount of
surrounding LUT logic does. At this card's own real native width (18), the
fit is genuinely exact (`MULT18X18` would need no padding at all), but this
file keeps using `MULT36X36` generically so one file covers every width up
to 36 without per-width primitive selection. Real synthesis confirms the
DSP block still genuinely survives at `WIDTH=18` (`MULT36X36: 1`, ~28 total
cells) -- the real check `#901`/`#902` established, not assumed.

**`mul_cell_v4sa`: "the actual mul core itself," built without touching a
shared file.** `bitwise_multiplier_32bit.v` (the real primitive
`mul_cell_v4`/`v4c`/`v4s` all use) is hardcoded for exactly 32-bit operands
AND is shared with the mainline cardinal-routed cells -- not something to
modify for this family's own purposes, the same caution `mask_cell_v4sa.v`
already applied to `nibble_mask_addon_v1.v`. Built instead with a plain,
genuinely `WIDTH`-generic `in_a * in_b` -- `#901` already confirmed directly
that this toolchain never infers DSP from a plain multiply, so it
synthesises to ordinary LUT logic, functionally equivalent to the array
multiplier's own real purpose even though not gate-identical in structure.

**A genuinely different scaling story for multiplication, worth stating
clearly -- not the same clean linear ALU ratio found on add/compare/
accumulate.** LUT-core mul: ~4,257 LUT4-equivalent at `WIDTH=32` -> ~1,045 at
`WIDTH=18` -- a MUCH bigger proportional saving (~24.5%) than the ~56.25%
linear ratio `#909`/`#911`/`#912` found, because multiplication's real cost
scales roughly with width SQUARED (an NxN multiply needs O(N^2) partial
product terms), not linearly like addition or comparison. And the real DSP
alternative remains dramatically cheaper regardless of width -- ~28 total
cells at `WIDTH=18` versus ~1,045 for the LUT-core version at the SAME
width -- confirming `#901`'s original finding even more sharply now that
both variants carry the same real ack+freeze+WIDTH treatment for a genuine
like-for-like comparison.

**What changed:** `sub/verilog/shift_stage_v4sa.v`, `mul_cell_v4sa_dsp.v`,
`mul_cell_v4sa.v` (all new) + their testbenches, plus
`tb_shift_stage_v4sa_width18.v` (the real 18-bit truncation proof).
`sub/README.md` updated. No existing file touched.

**A real, outstanding gap named plainly, not silently carried forward
again: `nano`, the original general-purpose logic core, still has no `v4s`/
`v4sa` version at all.** Flagged back in `#898`/`#899` as the family's one
real structural exception (it needs two genuinely different input roles --
a held operand plus a flowing one -- not the uniform shape every other cell
got), and never actually built while the specialised cells took priority.
Still outstanding; a real item for the next session, not forgotten again.

## `nano` arrives: the original logic core, finally built, v4s then v4sa compared directly (`#917`)

Alan: build the real `nano`/logic-core base as a `v4s` version first, then the
`v4sa` version to compare against -- the gap flagged back in `#898`/`#899` and
caught again in `#916`, finally closed.

**Read `nano_gate_v4c.v` in full before writing anything**, not reconstructed
from memory. Its real function: a universal 2-input logic gate -- AND, OR,
XOR, NAND, NOR, XNOR, NOT-held, NOT-flow, pass-held, pass-flow, constant-0,
constant-1 -- selected by a `topology` field, applied between a HELD operand
and a FLOWING one. Verified by hand against a full truth table before
trusting the derived gate names (`g8`/`g9` are genuinely XNOR/XOR, confirmed
by direct computation, not assumed from the NOR-decomposition's shape alone).

**`nano_cell_v4s.v`: the real structural exception finally resolved.** Two
dedicated ports, `hold_in_data` (loaded rarely, via an explicit `load_hold`
pulse -- there is no more cardinal arrival-order trick to infer "first
arrival" from) and `flow_in_data` (new every cycle), matching the same "one
dedicated wire per real role" principle `adder_cell_v4s.v`'s own `in_a`/
`in_b` established, applied here to two roles that are genuinely different
in KIND (one persistent, one transient), not just two equal operands.

**A real, genuine RTL bug found and fixed, not a testbench mistake this
time.** The first draft defined `hold_in_data` as a port but its own load
logic mistakenly read from `flow_in_data` instead -- `held_value <=
flow_in_data` where it should have read `hold_in_data`. Caught by the very
first real test (the hold failed to persist a loaded value across multiple
flowing operands -- the cell's own defining behaviour), diagnosed with
direct debug tracing, fixed in one line. 13 real checks pass after the fix,
including the hold genuinely persisting correctly across three different
flowing values with no reload between them.

**`nano_cell_v4sa.v`: the ack+freeze+WIDTH version, built to compare against
`v4s` directly, per Alan's own request.** `load_hold` is treated as a real,
silent side effect -- it updates what future flowing captures compute
against, but is not itself an offer, matching the original cell's own real
behaviour (loading the hold was never an output event there either). One
real mistake caught while WRITING the testbench itself, before it ever ran:
a planned check would have called the `fire()` helper (which waits for
`ack_out`) with `ack_in` already held low, which could never resolve --
caught by re-reading the test's own logic before running it, not by a hang.
10 real checks pass.

**Real, measured comparison -- `#906`'s surprise confirmed again, at real
scale, not just on the simple adder.**

| Variant | LUT1-4 sum |
|---|---|
| `nano_cell_v4s` (no ack) | 1,117 |
| `nano_cell_v4sa` (ack+freeze, `WIDTH=32`) | 1,088 |
| `nano_cell_v4sa` (ack+freeze, `WIDTH=18`) | 626 |

Even on this much more complex cell -- a full universal gate selector, not a
single fixed operation -- ack+freeze comes out SMALLER than the pure no-ack
version, not larger. `#906`'s original finding was not a fluke specific to a
simple adder; it holds at real complexity too. The `WIDTH=18` reduction
(0.575 of the `WIDTH=32` figure) sits close to, but not exactly at, the
clean 0.5625 linear ratio -- consistent with `#911`'s own observation that a
cell mixing real width-dependent logic with some width-independent control
overhead lands slightly off the purest ratio.

**What changed:** `sub/verilog/nano_cell_v4s.v`, `nano_cell_v4sa.v` (both
new) + their testbenches. `sub/README.md` updated with the full finding. No
existing file touched.

## `branch` resolved: the last real structural gap in the family, closed through a full design conversation (`#918`)

`branch` had sat flagged since `#898` as the one cell whose entire job is a
runtime decision -- genuine tension with a family built around removing
exactly that. Resolved not by fiat but through a real, multi-turn design
conversation with Alan, confirming the real original (`branch_cell_v4c.v`)
first, then building the new shape together, choice by choice.

**The real design, agreed point by point:** two dedicated inputs (`in1`,
`in2`), each INDEPENDENTLY runtime-selectable as fixed (held, reloaded via
its own valid pulse) or flowing (fresh every firing) -- matching
`ram_cell_v4sa`'s own fixed/flowing choice, applied per-input here. A real
new capability this gives, which the original never had: comparing two
genuinely live streams against each other, not just one value against a
held reference. The 3-way signed compare (low/equal/high) is unchanged in
spirit. `emit_source` is ONE shared, config-time choice (fixed constant /
in1 / in2 / diff) -- Alan's own deliberate simplification once per-outcome
value selection was found to add real complexity for little value. `diff =
in1 - in2`, true signed subtraction, same convention as `adder_cell_v4sa`'s
own `subtract_mode`.

**A real simplification found DURING the conversation, not assumed from the
start:** per-outcome routing to out1/out2/both/neither subsumes the
original's separate per-outcome emit-enable bits for free -- routing to
"neither" IS the swallow-silently case, no extra bit needed.

**Real bugs found and fixed, split cleanly between RTL and testbench, each
diagnosed with real tracing rather than guessed at:**
- Testbench: a route encoding mistake (`2'b10` used for "both" when the
  real encoding needed `2'b11`) and an inverted fixed-mode bit (a comment
  said "flowing" while the value actually set "fixed") -- both caught by
  direct register-level tracing, not assumed from the test's own comments.
- Testbench: the `fire`-style helper waited for `ack_out` to return, which
  (with `ack_in` held continuously high) meant the offer had ALREADY been
  consumed by the time the check ran -- the same class of "checked too
  late" mistake `shift_stage_v4sa` hit, caught here by noticing the debug
  trace showed the CORRECT value one display earlier than the check ran.
  Fixed by giving the testbench an explicit `present_round`/`wait_ready`
  split instead of one helper trying to do both jobs.
- Testbench: the freeze check itself had the expectation backwards --
  outputs already pending BEFORE freezing should STAY pending while frozen
  (freeze blocks `ack_in` from clearing them), not go to zero. The RTL was
  correct throughout; the test's own expectation was inverted.

19 real checks pass after all three fixes: the full low/equal/high x
emit-source matrix, the swallow case, real synchronisation between two
flowing streams, real differential backpressure across two independent
outputs (mirroring `router_cell_v4sa`'s own test), and freeze correctly
preserving in-flight state.

**Real, measured result: the same clean linear ALU ratio found on every
other arithmetic cell, holding here too.** ALU: 64 (`WIDTH=32`) -> **36
(`WIDTH=18`)** -- the exact 0.5625 ratio, consistent with branch doing two
real 32-bit-scale operations internally (the signed compare and the diff),
giving 2x32=64 and 2x18=36. LUT1-4: 335 -> 201 (0.6, the usual small
deviation from pure-linear seen on every cell with real control overhead
alongside its arithmetic).

**What changed:** `sub/verilog/branch_cell_v4sa.v` (new) + testbench.
`sub/README.md` updated with the full finding. No existing file touched.

## `merge_cell_v4sa`: the merge becomes a core, and gets the one function the VM's OR could not express (`#954`/`#955`)

In the original architecture every cell can take several upstream faces, so a merge is a property of the cell. The flex cells each have ONE input, so a merge needs somewhere to live.
A first version put selection logic ("an arbiter") into the generator's emitted glue and the whole hand-built cordic ran; Alan's ruling was that the system is built from **known core
designs** and that arbitrary hand-woven glue at particular points goes against the idea of it. So the merge is a core, with its own bench, like every other cell.

**Why not simply OR, as the VM does:** under a handshake two sources can both stay valid for as long as a cell is busy; a plain OR would then consume both and fuse two separate items
into one corrupt value. The core has four modes, selected by `cfg_data[1:0]`:

| mode | name | behaviour |
|---|---|---|
| 0 | A only | pass `in_a`; `in_b` is never accepted (a one-path "merge": a configurable pass-through) |
| 1 | B only | pass `in_b`; `in_a` is never accepted |
| 2 | **arbitrate** | either source, one at a time; grant one, acknowledge ONLY that one, rotate priority after every grant (neither can starve). For paths that are *alternatives* -- a branch's two outcomes rejoining (the cordic's `gather`) |
| 3 | **join-OR** | WAIT for both, then output `in_a \| in_b` and acknowledge both together. For paths that are *halves of one item* -- the VM's "free OR" used as a feature, made deterministic: it no longer depends on the two items happening to arrive in the same cycle |

Ports follow the stated design rule below (two dedicated inputs, each with its own valid and ready; the mode selects *behaviour*, never what a port *means*). Protocol as every v4sa cell:
a registered output held until `ack_in`, one item per two cycles, `freeze_in` gates everything, configuration arms the cell and clears its state; so one cycle of added latency, like a relay.

**Verified:** `tb_merge_cell_v4sa.v` (37 self-checking cases) with **12 deliberate defects all caught** (round-robin ignored, B acknowledged without a grant, join-OR not waiting, AND for OR,
A acknowledged without B, mode 0 accepting B, capture when unarmed, priority never rotating, freeze ignored, reconfiguration not clearing a pending output, swapped data select, release
without `ack_in`); and `tests/test_flexsub_flex_merge_v1.py`: the whole cordic (36 cells, 4 merge cores) == the real VM on 12 starting angles + the -404 anchor, and join-OR resolves the
same-cycle divergence (the VM's `0x0f0 | 0xf00 = 0xff0` is ONE value; arbitrate mode gives two outputs, join-OR gives one, equal to the VM).

**In the generator (`#957`):** a core is placed per ICM merge and only where one exists; a merge of 3 or 4 sources becomes a balanced TREE of two-input cores (arbitrate: round-robin at every level; join-or: OR is
associative, so the tree waits for ALL sources); the mode is chosen PER MERGE with `--merge-mode "consumer=join-or,arbitrate"` (a mistyped name is refused, listing the real ones). Until the ICM itself can carry the
choice, the command line is where it is given.

**Stated limit:** no cell can restore the ORDER of items between two paths (that needs per-item tags), so an arbitrating merge is only well-defined with at most one item in flight in the region
it joins (true of the loop-style designs that use merges; the compiler never emits one). Join-OR does not have the problem: it takes one item from each side per output.

## Since the merge core: the VM mirror, four RTL fixes, second ports (`#956`-`#986`)

**The sequencer on flex (`#956`).** It is free-running: `advance_in` is tied to the cell's own ready, so the consumer's ack paces it. Fixed on the way:
an unconfigured `sequencer_cell_v4sa` with `advance_in` high offered a spurious value. It is now gated by `armed` like every other v4sa cell. Pairing
differs from the VM on purpose: flex pairs item k with `VALUE_(k mod 4)`, while the VM's sequencer pairs with itself.

**`FlexGrid`, the VM's mirror of this family (`#964`-`#973`).** `nano/flex_grid_v1.py` is a `SuperGrid` subclass with its own per-core handlers. It
takes its structure from the same planner the generator uses. Each core was checked against the **generated flex RTL as the oracle** at W = 4, 8, 18,
32 and 36. The sweep found four RTL limits, now resolved:

| cell | limit found (`#970`) | resolution |
|---|---|---|
| `nano_cell_v4sa` | captured on `valid_in` without checking `armed` | captures on `valid_in && armed` (`#971`); bench case added |
| `compare_cell_v4sa` | above 32 bits, the threshold came from a 32-bit `cfg_data` and read as x | the threshold has its **own `cfg_threshold [WIDTH-1:0]` port** (`#972`; Alan: "if two parts are needed then they have two ports; the nano is the exception, not the rule"). It is still one data input and one result output |
| `accumulator_cell_v4sa` | did not elaborate below 16 bits (negative replication counts) | a generate: at W >= 16 exactly the original logic and cost; below 16, `\|total\|` and the 16-bit threshold compare in a 17-bit space, so a threshold the data cannot reach never fires and is never cut down (`#973`). Step and threshold stay plain numbers (raw8/raw16 in the ICM) |
| `sequencer_cell_v4sa` | does not build below 8 bits | refused with the reason (still open) |

The mask's limit above 32 bits was resolved separately by scaling the mask word (`#968`, in the `mask_cell_v4sa` section above).

**Second output ports (`#974`/`#976`/`#981`).** Alan's rule: two results means two ports. `adder_cell_v4sa` gains `carry_out` (the carry as a 0/1
word, so it can feed another adder's `in_b`; for subtract it is NOT-borrow) with its own `valid_out_c`/`ack_in_c`. `mul_cell_v4sa` and
`mul_cell_v4sa_dsp` gain `data_out_hi` (the high half of the 2W product) with `valid_out_hi`/`ack_in_hi`. These rules match the branch: each output
clears on its own ack, and a new round starts only when neither output is pending.

- **`SECOND_PORT` build parameter** (default 0). The ports always exist at fixed names (strict placement), but at 0 their logic is not built and costs
  nothing. At 1, a config bit (adder `cfg_data[1]`, mul `cfg_data[0]`) turns the port on at run time. Built cost: adder +4 LUT4 / +3 DFF; the LUT
  multiplier roughly doubles; `mul_dsp` goes from 5 to 8 LUT4. **Correction (`#976`):** the `#974`/`#975` adder figures (29/19/24, W + 9) included the
  unused port. With it off the adder is back to 23/18/21 (W + 5).
- **Every instantiation must tie `ack_in_c` / `ack_in_hi` high when unused**, or a pending second word stalls the cell. The ICM emitter, the
  hand-built chains, the benches and the harness all do.
- **Proven:** `tb_second_port_v4sa.v` (14 checks), and `tb_carry_chain_v4sa.v`, where three 8-bit adders make a 16-bit add over 400 random pairs.
  Through the generator, a **64-bit add from two 32-bit limbs** passes, with limb 0's carry going straight into limb 1's adder (`#981`).
- **The ICM side** is target-agnostic. A cell asks with `second_output` and can route the second word with `second_downstream_mask` (see
  `docs/stripped-cell/ICM_V3_FORMAT.md`). The planner builds the port only on flagged cells. It puts a merge core (sum then carry) in front of a
  consumer that takes both words, and gives a consumer that takes one word that port directly. The **sub family has no second port.**

**Accumulator cascade (`#975`).** Two pulse-mode accumulators, each one's offer driving the next one's `inc_pulse`, fire once per T1 x T2 events.
That gives 1000 x 1000 = 1,000,000 events, beyond the 65,535 one 16-bit threshold holds; this is proven in RTL (`tb_acc_cascade_v4sa.v`) and in FlexGrid.
Conditions: each stage's `ack_in` is held high, and hits are at least 2 cycles apart. A cascade multiplies the event-counting range; a wider *number*
uses the carry port instead.

**Cost against width (`#975`/`#976`).** `tools/flex_width_sweep_v1.py` measures every flex cell at W = 4, 8, 16, 18, 24, 32. The data is in
`docs/measurements/flex_width_sweep_975/` and the Tang MAN's `cell_costs`; see `docs/man/README.md` for how to read it.

**Shift is any amount on flex (`#985`/`#986`).** The flex shift is plain wiring, so any amount 0-31 in either direction is made directly from the
ICM's one `shift_amt` number (coarse + fine are only how the number is written). The sub family still makes coarse taps only, and `lane_cut` with a
non-tap amount is refused on flex. `nano/target_capabilities_v1.py` refuses an amount a named target cannot make. At W = 36 the 5-bit field cannot
express amounts above 31 (open).

**fp32 stages on these cells (`#982`-`#988`).** Unpack, carry → exponent bump, high word → normalise bit, a 5-stage left-normalise with exponent
adjust, sticky, round-to-nearest-even, and a 6-stage align with sticky (one multiplier per stage: high word = shifted value, low word = the bits shifted out, `#988`) are built from flex cells with no loops. They are tested in generated RTL (plain and with random stalls),
equal to FlexGrid and the Python model. Design note: `docs/stripped-cell/design-notes/fp32_stage_map_second_ports.md`. The comparator is **signed**,
so a bit isolated at bit 31 reads as negative (`#984`).

## The whole fp adder from flex cells, and the crossing tile (`#989`/`#990`/`#999`)

**The open fp assembler (`#989`).** `tools/fp_assembler_v1.py` has `FpFormat` (FP32, FP16, BF16 or custom) and parametric normalise,
align-with-sticky and round blocks. `tools/flex_layout_v1.py` places cells and links on a grid, routes them, and `balance()` removes the
operand-arrival ties the generator refuses. In the flex VM, same-tick operands are no longer ORed: one is taken, and a subtract raises
an error.

**The whole adder (`#990`).** `tools/fp_add_v1.py: fp_add(g, fmt)` builds the full chain from flex cells:
- unpack and the exponent difference / swap decision, using a packed sign+exponent word;
- two align-with-sticky blocks, then the significand add/sub and `|S|`;
- normalise, round-to-nearest-even, the rounding-overflow bump, zero detection, sign and pack.

fp32 in generated RTL (plain and random stalls) == FlexGrid == a reference anchored to `fp32_add_v1` on 3,000 pairs, with 0
mismatches; bf16 and fp16 match too. **Scope:** normal numbers and zero. Not yet: sub-normals, exponent overflow/underflow, inf,
nan, or formats wider than 32 bits. The placement is a hand template; routing and timing balance are automatic.

**The crossing tile (`#999`).** Routing the adder hit topological walls: closed "rooms" that no lane can leave except through a data
cell. Alan's answer is a tile that passes west↔east and north↔south straight through, with no control logic. It costs **one tick
per tile per direction of travel**, like every other core (Alan: "add the tick as 1 per tile"): each used direction is its own
one-word register slice, so the two axes never share state, and long chains of tiles do not lengthen the critical path. It is ICM
core `cross`, core_select 10 (confirmed by Alan). In RTL the netlist extractor gives every used (tile, direction) an ordinary ram
relay slice. FlexGrid models the slices as hidden relay cells. The layout engine lets a route cross another at right angles and
adds one hop to both routes. **Open:** native cores per family (built from ram slices today), and cost rows for the router and MAN.

## `priority_cell_v4sa`: the last flex core, with all three of the VM's modes (`#1017`/`#1018`)

The priority core is the VM's N-way arbiter: up to four faces (N, S, E, W) compete for one output. On flex it is a core with its own bench, like every other cell.
Each face has its own data, valid and ready, so a face is **ready only when it is the one granted**: the winner is acknowledged, the losers keep their items where
they are and are never blocked. One item per two cycles, `freeze_in` gates everything, one cycle of latency, `WIDTH`-parameterised.

| mode | `cfg_data` | behaviour |
|---|---|---|
| 0 strict | `[12]=0 [13]=0` | the candidate with the lowest rank wins (`score = 3 - rank`); ties go N, S, E, W |
| 1 weighted | `[12]=1` | surplus round robin: every candidate's credit grows by its weight each round, the highest credit wins, only the winner's credit is reduced (by the total weight of that round's candidates). 3:1 gives `n n n s` exactly; 2:2:1 gives `n s n s e` |
| 2 sequenced | `[13]=1` | a fixed repeating turn order (`[16:14]` turns, `[24:17]` the faces, 2 bits each); ONLY the due face is a candidate, every other arrival waits, the turn advances when the due face is taken. An empty order never captures |

`[3:0]` is the upstream mask and `[11:4]` the four 2-bit ranks (weights in mode 1). A candidate is a face that is valid **and** enabled by the mask.
The VM's downstream mask is not in the cell: a consumer is wiring, and the generator forks the one output to every consumer.

**Sequenced channel, and why it is in the file now.** Mode 2 is Alan's #772: the order is guaranteed by the cell's own state, not by path lengths or placement,
at the price of head-of-line blocking (a face that never delivers stops the whole channel; that is the point). It existed only as a VM prototype, because the ICM file
had nowhere to record the turn order. It now does (`sequence_len`, `sequence_0..3`, see `docs/stripped-cell/ICM_V3_FORMAT.md`); the compiler's placers write it, the VM
reads it, and the generators act on it:

- A **two-turn** sequenced priority in front of a two-operand cell becomes plain operand wiring, with the **turn** deciding A and B (so `x - y` generates on sub from the
  saved file). A strict two-source priority is eliminated the same way, by rank.
- Any other priority stays a real core on **flex**; **sub** has no priority core and refuses one it cannot eliminate.
- Refused with the reason: a sequenced priority with no usable recorded order, an order longer than four turns, a due face the mask excludes, a due face nobody feeds
  (the VM would wait for ever), a constant (always-valid) source, and any other mode value.

**Cost** (`synth_gowin -nowidelut`, W=32, every config port a real input): 291 LUTs, 155 ALUs, 94 flip-flops. It is the largest of the flex cells, almost all of it the weighted
mode's 8-bit credit arithmetic. A generated design pins the configuration, so the cost depends on the mode. Measured on a whole generated design (a two-face priority plus
its three ram cells, whole-design totals LUT / ALU / flip-flops): strict 46 / 0 / 133, weighted 108 / 51 / 149, sequenced 51 / 6 / 136 (the three rams are the common floor).

**Proof.** `tb_priority_cell_v4sa.v` (129 checks: unarmed, rank order, backpressure, the losers served in order, ties, the mask, a lone candidate, weighted 3:1 / 2:2:1 / 1:1:1:1,
reconfiguration, freeze; and for mode 2 turn orders N,E / N,N,S / W,S,E,N, an early arrival waiting, an empty order, a masked due face, restart at turn 0, freeze); 22 planted defects,
every one caught (`tests/vm/test_priority_cell_v1.py`); generated designs under random stalls and skewed arrivals, nothing lost, duplicated or reordered, weighted shares and sequenced
order exact (`tests/vm/test_priority_flex_v1.py`, `tests/vm/test_priority_sequence_v1.py`); a compiled `x - y` from the saved file, generated RTL == VM
(`tests/test_flexsub_icm_generate_v1.py`). **Not mirrored:** FlexGrid has no priority model, so the RTL is the reference (as for a merge of more than two sources).

## Status

Fourteen cell functions are proven, simulated and measured: adder, compare, accumulator, latch, sequencer, ram, router, mask, mul,
shift/shift_stage, **nano** (`#917`), **branch** (`#918`) and, flex only, **merge** (`#955`) and **priority** (`#1017`/`#1018`). Each has a testbench. Both families are driven end to end
by the ICM generators (`tools/flexsub_icm_generate_v1.py` for sub, `tools/flexsub_icm_flex_v1.py` for flex; every core the planner translates,
including the sequencer on flex since `#956`), checked against the real VM. The flex family is also mirrored by `FlexGrid` at any width the cells build.
**Not on real hardware yet** (the board has run a cell from the original family, `#896`).

Not to be done: `command` is not ported to sub or flex, by Alan's decision (#1020): it rewrites other cells' configuration live, and a sub/flex cell is one function fixed at build time. Still to do: a FlexGrid model of the priority
core; priority orders longer than four turns; the `--icm` generators at widths other than 32; the sequencer below 8 bits; a 6-bit shift amount for W = 36; and place-and-route of whole
generated designs.

## A stated design rule (Alan's own, confirmed across every cell built so far)

However many genuinely distinct roles a function needs -- operands, or
independent events, or triggers -- that's how many dedicated ports it gets.
Never a runtime decision about which port means what. `adder`/`mul`'s `in_a`/
`in_b`; `accumulator`'s `inc_pulse`/`dec_pulse`; `latch`'s three pulses;
`router`'s fixed per-output enables -- all the same rule, applied to whatever
the function actually needs, not a fixed template forced onto every cell.
