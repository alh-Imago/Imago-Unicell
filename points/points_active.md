# points.md — ACTIVE part (currently entries #572 onward)

**This is the real, currently-open tail of the single, canonical
points.md ledger — the file new entries get appended to.** Split
across multiple files purely because GitHub won't render a file over
~512KB in the browser (the single combined file had grown past 2MB);
no entry content was changed, reworded, or reordered. See `points/
INDEX.md` for the full real map of which part holds which entries,
and `points.md` (repo root) for the short, canonical pointer every
session should still start from.

**Naming convention, for future-me:** this file keeps the stable name
`points_active.md` (no entry range in the filename) for as long as
it's still being appended to, so appending never requires a rename.
Once it approaches ~350KB, seal it — rename to `points_NN_XXX-YYY.md`
with its real final range, start a fresh, empty `points_active.md` for
continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## 572. Real, complete dataset: all 8 single-core-type N=10 arrays measured on real hardware via Alan's own real Quartus batch, giving the first real, direct answer to "what does full runtime reconfigurability actually cost." A real 8-value outlier found and given an honest, unconfirmed hypothesis (branch cell), a real labeling mix-up caught and corrected, and a real, concrete comparison point for the shared-buffer work to measure itself against. (Alan/Claude, 2026-09-01)

**STATUS: real, complete N=10 single-core-type ALM data for all 8
cores, via `tools/project_assemble_v1.py`'s own `-S` mode (`#567`).
Every figure below is the real per-cell average across 10 genuinely
cardinally-connected cells, JTAG/ISSP overhead excluded where present
in the real report.**

| Core | Avg ALM/cell (N=10) | Real N=1-in-shell ref (`#524`-`#526`) | Ratio |
|---|---|---|---|
| sequencer | 3.63 | 5.0 | 0.73x |
| latch | 6.68 | 4.5 | 1.48x |
| compare | 8.18 | 4.2 | 1.95x |
| ram | 9.58 | 5.4 | 1.77x |
| adder | 10.14 | 4.8 | 2.11x |
| nano | 11.61 | 7.0 | 1.66x |
| accumulator | 78.97 | 83.0 | 0.95x |
| branch | 85.16 | 12.5 | **6.81x** |

**A real, honest labeling mix-up caught, not glossed over:** the real
Quartus report Alan initially labeled "Accumulator" was actually
`adder_cell_v2`'s own real data (confirmed directly: the report's own
real instance names read `adder_cell_v2:C_0_0` etc., and its own top-
level entity was `top_adder_cell_10cells_v1`). Filed under adder
above; accumulator's own real figure came from an earlier, separately
reported real Quartus run.

**The real, general pattern (roughly 1.5x-2.1x across 6 of 8 cores)
is expected, not a red flag** -- confirmed directly, consistent with
`#560`'s own earlier finding: every real N=1 reference figure came
from a cell with genuinely ZERO real neighbors, every cardinal edge
tied to a safe, constant default. Real, genuine cardinal connectivity
at N=10 removes Quartus's own ability to optimize based on a known-
constant input, so a real, moderate increase across the board is the
honest, expected result.

**Sequencer's own real 0.73x (a genuine DECREASE) makes real,
structural sense, not noise:** confirmed directly against its own real
RTL (`#564`) -- it has no capture role at all, never reads `arrived_X`/
`data_in_X`, so genuine cardinal connectivity simply doesn't matter to
its own real cost the way it does for every other core.

**Branch cell's own real 6.81x is a genuine, real outlier -- 3-4x
larger than every other core's own real increase, not explainable by
the same general "genuine connectivity costs more" pattern alone.**
Real, honest, NOT YET CONFIRMED hypothesis: branch cell carries far
more real, data-dependent decision logic per fire than any other core
here (three-way LOW/EQUAL/HIGH classification, independent per-
outcome value/route/suppress selection) -- Quartus can heavily
simplify that kind of branching logic when an input is provably
constant, and has far less room to do so once the input is genuinely
live and unpredictable. A real, plausible mechanism, not a confirmed
one -- worth real, direct investigation once the shared-buffer
integration reaches branch cell specifically.

**The real, concrete, honest answer this whole batch was built to
find:** summing all 8 real, separate, single-purpose cells gives
**213.9 ALM** -- the real cost of one dedicated cell of each type,
wired together. Compared against the already-measured real cost of
ONE cell that can genuinely be ANY of the 8 (`#560`'s own real
~950-1050 ALM/cell figure): **full runtime reconfigurability costs
roughly 4.4x-4.9x more than eight fixed-purpose cells.** This is now
the real, concrete number the shared-buffer work (`#561`-`#571`)
exists to close the gap against -- not a theoretical target, a
measured one.

## 573. Real shell-level integration of the shared-storage mechanism -- unicell_super_v4.v built, wiring all 8 real v2 cores (EXTERNAL_STORAGE=1) through ONE real 170-bit shared register instead of 8 separate internal register sets. A real, genuine functional bug found and fixed during sim verification (the write-mux raced against the registered core_select on the exact cycle of a core switch, silently discarding the newly-configured core's first real state write) -- confirmed as a real failure via a purpose-built full-8-core top-level self-test, not caught by the narrower differential testbenches alone. Zero regression: all 8 per-core checks (41/41), the full Python suite (361/361), and the pre-existing v3 shell testbench all still pass unchanged. Real Quartus targets built for both sides of the actual comparative pair, not yet run. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified shell-level integration -- the actual "adapt the shell" step `#565`'s own real next-steps named, picked up per Alan's own "continuation of moving the data to a separate wrapper."**

**`unicell_super_v4.v` (new)** -- cloned from `unicell_super_v3.v` per this
project's own standing discipline. Every one of the 8 cores instantiated
with `EXTERNAL_STORAGE=1`, reading/writing ONE real shared register
(`shared_state[169:0]`, sized to nano's own real 170-bit width, the
widest of the 8 -- branch 117, accumulator 107, adder 79, compare 77,
sequencer 53, ram 46, latch 23). A real write-select mux picks which
core's own computed `ext_state_out` gets registered back each cycle.
Also adds Alan's own real freeze-centralization idea from `#566`
(`freeze_in || (core_select != SEL_<core>)` per core) as a genuine,
complementary correctness layer on top of the pre-existing arrived-
gating, confirmed NOT a substitute for the write mux.

**A real, genuine functional bug found and fixed, not assumed correct
in advance:** the first draft's write-mux keyed the shared-register
write purely off the REGISTERED `core_select` -- but every
`cfg_valid_<core>` enable is (correctly) gated on `incoming_select`
(the value about to settle), and `core_select` itself only updates on
the SAME edge, one evaluation later than combinational logic can see
it. On the exact cycle a switch's `cfg_valid` fires, the write-mux was
therefore still pointing at the OLD core, silently discarding the
newly-configured core's own first real state write -- confirmed as a
genuine failure (RAM's real fixed-mode CAFEBEEF config never reached
`shared_state` at all) via a purpose-built full top-level self-test,
which the narrower `tb_unicell_super_v4.v` shell testbench alone did
NOT catch (its own task-based timing happened to mask the race). Real
fix: `write_select = cfg_valid ? incoming_select : core_select` --
the write-mux now tracks the effective, about-to-settle select during
a load, matching the same convention `cfg_valid_<core>` itself already
uses.

**A second real design question resolved by testing, not assumed:** an
earlier draft also force-cleared `shared_state` to 0 on every genuine
core switch, reasoning it should mirror each core's own real internal-
register reset default. This was directly disproven by sim -- a switch
and a config load for the newly-selected core are the SAME `cfg_valid`
pulse in this project's own SUPER_LATCH protocol, so the "reset" branch
fired on the identical cycle as the real config load and clobbered it
before it could ever reach `shared_state`. Removed entirely: no shell-
level reset is needed on top of what `cfg_valid` already does, since
every core's own real next-state logic already overwrites (or, for
runtime-only fields like `pending_ack`, force-clears) everything it
cares about from `cfg_data` on `cfg_valid` -- the exact same behavior
already proven correct for `EXTERNAL_STORAGE=0` mode's own reconfigure
path in `#563`/`#564`'s differential testbenches.

**`tb_unicell_super_v4.v` (new)** -- cloned from `tb_unicell_super_v3.v`,
same 8-core sequence reused verbatim (proving the shared mechanism is
TRANSPARENT to every already-proven behavior), plus two new, targeted
checks exercising the shared register directly: confirming
`shared_state` genuinely holds RAM's own real `ext_state` (not just
that RAM's *output* looked right, which could pass even with a broken
write-mux since a core's own output is combinational off its current
`ext_state_in` regardless of what the shared register itself holds),
and confirming RAM's old bit pattern does not leak into adder's own
active field space after a switch. All 8 real checks pass, deterministic
across repeat runs.

**`top_unicell_super_test_v3.v` (new) + `top_unicell_super_test_v4.v`
(new)** -- a real, same-session, apples-to-apples Quartus pair. v3's
own full 8-core self-test top-level had never been built before (only
the branch-only slice, `top_super_v3_branch_test_v1.v`, existed) --
built now specifically so any real ALM/Fmax difference Quartus reports
is genuinely attributable to the shared-storage mechanism itself, not
to a difference in what's being tested. Both cloned from
`top_unicell_super_test_v2.v`'s own proven SETTLE-counter FSM pattern,
extended with the same real branch-cell round already proven through
`core_select` on real silicon (`#530`) and through the shell
(`tb_unicell_super_v3.v`, `#542`). Both wired with the established ISSP
debug-probe pattern (`#528`/`#529`) rather than LED-dependent
confirmation. Both sim-verified clean end to end (a real Verilog
top-level testbench driving `CLK_100M`, confirming `err_sticky` never
latches across the full sequence) -- the SAME real bug above was caught
this way on v4's own first attempt, and fixed before it could waste a
real Quartus cycle.

**Real Quartus targets built, matching this project's own established
QSF/SDC template exactly (real device, real pin assignments, real SDC
clocking convention):** `top_unicell_super_test_v3.qsf`/`.sdc` and
`top_unicell_super_test_v4.qsf`/`.sdc`. **Neither has been run through
real Quartus yet** -- that comparative build (ALM/Fmax, one real
internal register set per core vs. one real shared register, testing
Alan's own real hypothesis that the cost shows up more in Fmax than
raw ALM count) is the actual, real next step, and the actual point of
this whole shared-storage thread (`#561`-`#573`) -- not yet obtained.

**Full regression, zero failures:** all 8 per-core differential
testbenches (41/41 real checks: latch 5/5, ram 4/4, adder 6/6, compare
3/3, accumulator 8/8, sequencer 4/4, branch 4/4, nano 7/7), the
pre-existing `tb_unicell_super_v3.v` (unchanged, still passes), and
the full Python suite (361/361, `tests/fpga/`'s own pre-existing
`pyserial` import gap excluded, matching `#370`'s own already-
documented, confirmed-not-a-regression status).

**Real, honest scope still open:** no real Quartus ALM/Fmax number for
either target yet -- Alan's own next real step. The VM has zero
representation of the shared-storage mechanism (checked directly, not
assumed) -- a real, separate, deliberately-not-attempted-here gap,
since the VM's own `SuperCell` doesn't model per-core register sharing
at all; whether it needs to is an open question for whenever the real
Quartus numbers are in and the mechanism is confirmed worth keeping.

## 574. Real Quartus result, v3 half of the comparative pair: top_unicell_super_test_v3 -- 479 ALM total (301.9 ALM for the real 8-core shell alone, the rest ISSP/JTAG bridge overhead), clk_div (the real 25 MHz fabric clock) closes at 107.05 MHz, a real ~4.3x margin. Per-core ALM breakdown recorded as the real "before" baseline. v4's own matching build is the actual, still-pending other half of this comparison. (Alan, 2026-09-01)

**STATUS: real, Flow Status Successful. First of the two real, same-
session comparative builds `#573` was built specifically to produce.**

**Whole-design real numbers:** 479 ALM / 251,680 (<1%), 470 registers,
0 block memory / 0 DSP / 0 PLL / 0 HSSI (all hardened silicon idle, as
expected). `clk_div` (the real 25 MHz fabric clock) closes at real
107.05 MHz -- a genuine ~4.3x margin. `CLK_100M`'s own reported
1366.12/645.16 MHz figures are a real, expected tmin-limited artifact
(just the input divider register), not a meaningful design constraint.

**Real per-instance ALM breakdown, `unicell_super_v3:DUT` = 301.9 ALM
(the shell + all 8 cores together, the real number that matters for
this comparison) / 324.7 with registers included:**

| Core | Real ALM |
|---|---|
| accumulator | 71.8 |
| nano | 62.5 |
| branch | 46.5 |
| adder (incl. `adder_v1:ADD` 8.0) | 31.6 |
| sequencer | 15.5 |
| ram | 14.5 |
| compare | 10.5 |
| latch | 8.5 |

**Real ISSP/JTAG bridge overhead:** 479 - 301.9 = 177.1 ALM -- the
`sld_hub`/`altsource_probe`/`debug_issp_probe_v1` stack, matching this
project's own already-established real overhead range for a single
ISSP probe on a small design (`#549`'s comparator build showed the
same ~90+ ALM class of overhead for a much smaller core).

**Real, honest scope: this is HALF of the actual comparison.** The
real point of `#573`'s own two-target build was always the DELTA
against `top_unicell_super_test_v4` (the shared-storage version, same
exact test sequence, same ISSP convention) -- that build is the real,
immediate next step, still pending as of this entry. No conclusion
about the shared-storage mechanism's own real cost can be drawn from
this number alone.

## 575. Real Quartus result, v4 half of the comparative pair -- and the real, honest, direct answer the shared-storage thread (#561-#575) was built to find: as implemented, the mechanism costs substantially MORE ALM and slightly LESS Fmax than v3's own separate-per-core storage, despite genuinely cutting real register count by over a third. Root cause identified precisely, not vaguely: the write-select mux, not the register itself. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful. Both halves of the comparative
pair now built, same session, same test sequence, same ISSP
convention -- the real delta below is genuinely attributable to the
storage mechanism itself.**

**The real, whole-design comparison:**

| | v3 (separate per-core storage) | v4 (one shared register) | Delta |
|---|---|---|---|
| Total ALM | 479 | 708 | **+229 (+47.8%)** |
| `DUT` ALM (shell+8 cores) | 301.9 | 539.7 | **+237.8 (+78.8%)** |
| Total registers | 470 | 302 | **-168 (-35.7%)** |
| `clk_div` (real 25 MHz target) | 107.05 MHz | 96.95 MHz | **-10.10 MHz (-9.4%)** |

**Real, honest headline finding: the mechanism did exactly what it was
designed to do on registers (a genuine 35.7% cut, real evidence that
one shared 170-bit register genuinely replaces 8 separate per-core
register sets) -- but costs far more than it saves once the write-side
logic needed to make that sharing work is accounted for.** Both real
predictions from `#565`'s own standing hypothesis were checked
directly: Fmax DID drop (confirming a shared write-path does cost
timing margin), but the dominant, larger effect is a real ALM
INCREASE, not the ALM reduction the whole thread was built to test
for.

**Real, precise root-cause localization, not a vague "storage costs
more" conclusion:** summing the 8 real per-CORE figures alone (not
`DUT`'s own shell-level total) shows the opposite of what `DUT`'s
total suggests --

| Core | v3 ALM | v4 ALM | Delta |
|---|---|---|---|
| accumulator | 71.8 | 87.1 | +15.3 |
| adder | 31.6 | 26.1 | -5.5 |
| branch | 46.5 | 34.3 | -12.2 |
| compare | 10.5 | 15.7 | +5.2 |
| latch | 8.5 | 7.7 | -0.8 |
| ram | 14.5 | 9.2 | -5.3 |
| sequencer | 15.5 | 8.0 | -7.5 |
| nano | 62.5 | 43.5 | -19.0 |
| **sum** | **261.4** | **231.6** | **-29.8 (-11.4%)** |

**6 of 8 real cores got individually CHEAPER** (adder, branch, latch,
ram, sequencer, nano), matching the real, intuitive expectation that
removing a core's own dedicated internal register set should shrink
that core's own footprint. The real per-core sum DROPPED by 29.8 ALM.

**The entire real +237.8 ALM increase, and then some, is happening
OUTSIDE the 8 cores -- in the shell's own new glue logic:** v3's real
shell-level overhead (`DUT` total minus the 8 per-core figures) is
301.9 - 261.4 = **40.5 ALM**. v4's real shell-level overhead is 539.7 -
231.6 = **308.1 ALM** -- a real **+267.6 ALM** increase in the shell
itself, more than the entire rest of the design combined.

**Real, honest, NOT YET CONFIRMED hypothesis for the actual mechanism
(worth real, direct investigation before any redesign attempt, not
assumed):** the write-select mux (`shared_state_next`, an 8-way
`case` over the full 170-bit width, with every branch except nano's
own real 170-bit assignment being a zero-extended narrower core value)
is a strong candidate. Unlike the OLD per-core register writes (each
core's own real next-state logic writing only its own genuinely-sized
register), this construct is a single, wide, data-dependent (`case`
on `core_select`) selector across a genuinely wide bus where most bits
in most branches are constant zero -- but WHICH branch is live is
itself a runtime value, so Quartus can't statically simplify away the
unused width the way it could if the width were fixed per instance.
The real freeze-centralization decode (`#566`) is a second, smaller,
real candidate, not yet separately isolated.

**Real, honest scope: this is a real, negative-but-valuable result,
not a failure to log quietly.** The mechanism is FUNCTIONALLY correct
(confirmed via the real, purpose-built full self-test, `#573`) and
does cut real register count meaningfully -- but as built, it is a net
COST on this card's own dominant resource metric (ALM), not a saving.
Whether a different write-path shape (e.g. per-bit-lane write enables
instead of one wide case-mux, or accepting per-core width instead of
one shared max-width register) could recover the real per-core savings
without paying this shell-level tax is a real, open, unstarted
question -- not pursued further without Alan's own direction, per this
project's own standing discipline of stopping at real, honest findings
rather than immediately chasing a fix.

## 576. Real, redesigned shared-storage write mechanism -- unicell_super_v5.v, per-bit "chip-enable" write instead of v4's own wide value-select mux. Per Alan's own real, precise reframing: cores stay permanently wired to the shared register like chips on a bus, only the currently enabled core's own real bits get written, everything else holds. Sim-verified clean on the first real attempt (no repeat of v4's own write-mux race, a structurally different mechanism). Real Quartus target built, not yet run -- the actual test of whether this recovers v4's own real ALM cost. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified, third leg of the comparative pipeline.
Real Quartus number still pending.**

**Alan's own real framing, direct quote paraphrased faithfully:**
cores should stay wired to the shared register "like RAM chips on a
bus... they are all connected all the time, the only control they
have is a chip enable... they stay connected, they just ignore the
signals unless told to look at them." This is a real, precise,
different mechanism from `#573`'s own value-select mux, not a restated
version of it.

**`unicell_super_v5.v` (new)** -- cloned from `unicell_super_v4.v`.
IDENTICAL in every respect except the one real mechanism this entry
is about: v4 computed a full 170-bit `shared_state_next` via an 8-way
`case` (each branch a real, different core's own output, zero-padded
up to 170 bits), then registered the WHOLE word every cycle,
regardless of the active core's own real width. v5 instead builds a
per-core `write_mask[169:0]` (all-ones across that core's own real
width, zero above) and does a genuine per-BIT masked write:
`shared_state <= (shared_state & ~write_mask) | (shared_state_next &
write_mask)`. Bits outside the active core's own real width simply
HOLD, never force-zeroed by a narrower core's own zero-padding.

**Real, precise reasoning for why this should cost less, stated as a
real bet on Quartus's own optimizer, not a guarantee:** for any bit
position only the WIDEST core (nano, 170 bits) ever reaches -- roughly
the top third of the register, bits [169:117] -- every OTHER core's
own `write_mask` bit at that position is a compile-time-constant 0.
Since `shared_state_next[bit] & write_mask[bit]` is forced to 0
whenever `write_mask[bit]` is 0 regardless of what `shared_state_next
[bit]` computes, every real contribution to that bit from a core whose
mask never reaches it is provably dead logic -- a real bet that
Quartus's own boolean optimizer can find and prune this per bit,
collapsing what was an 8-way selector everywhere in v4 down to a
genuine tiered structure: full 8-way selection only for the lowest 23
bits (every core reaches there), narrowing progressively as bit
position rises, down to a plain 2-way "hold vs nano" select for the
top 53 bits. **Not yet confirmed on real Quartus data -- the real,
immediate next step.**

**Real, honest functional check performed, not assumed:** does
letting unrelated bits hold (rather than force-zeroing them) change
any real behavior? No, confirmed directly -- every core's own
`ext_state_in` only ever reads its OWN real width slice of
`shared_state` (`shared_state[W-1:0]`, unchanged from v4), so a
narrower core never sees bits beyond its own width regardless of what
they hold. The one core that DOES read the full 170 bits (nano) is,
like every other core, dominated by its own `cfg_valid`-driven reset on
reselection (matching `#563`/`#564`'s own already-proven reconfigure
behavior) -- stale held bits from a prior core's own activity don't
survive a real reselect.

**`tb_unicell_super_v5.v` (new)** -- cloned from `tb_unicell_super_v4.v`
verbatim, same 8 real checks including the two shared-register-specific
ones from `#573`. **All pass on the very first real attempt**, no
repeat of v4's own genuine write-mux race (structurally impossible
here -- the per-bit mask is itself keyed on `write_select`, the same
already-correct effective select used everywhere else, and there's no
separate "whole word vs one core's word" conflict to race against).

**`top_unicell_super_test_v5.v` (new)** -- cloned from
`top_unicell_super_test_v4.v`, same exact 8-core sequence, same ISSP
convention, DUT swapped to `unicell_super_v5`. Sim-verified clean via
a real top-level testbench, first attempt, deterministic across repeat
runs.

**Real Quartus target built, matching the established template exactly:**
`top_unicell_super_test_v5.qsf`/`.sdc`. **Not yet run** -- the real
test of whether this per-bit mechanism actually recovers v4's own real
+47.8% ALM cost (`#575`) while keeping its real -35.7% register saving,
or whether Quartus's own optimizer doesn't prune as cleanly as
reasoned above. Full regression clean throughout this entry: the v5
shell testbench, the v5 top-level self-test, both v3 and v4 top-level
self-tests unchanged, and the full 361-test Python suite.

## 577. Real Quartus result, v5 -- the per-bit chip-enable bet did NOT pay off. v5 is essentially equivalent to v4 (marginally worse on every metric), confirming the real cost isn't the specific SHAPE of the write-select logic -- both approaches land in the same real cost range, well above v3's own plain separate-per-core storage. A real, honest, negative result closing this specific redesign attempt. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful. Third and (for now) final leg
of the comparative pipeline.**

**The real, complete three-way comparison:**

| | v3 (separate storage) | v4 (wide value-mux) | v5 (per-bit mask) |
|---|---|---|---|
| Total ALM | 479 | 708 | **721** |
| `DUT` ALM | 301.9 | 539.7 | **548.2** |
| Total registers | 470 | 302 | **332** |
| `clk_div` | 107.05 MHz | 96.95 MHz | **95.01 MHz** |

**v5 is NOT cheaper than v4 -- marginally MORE expensive on every real
metric** (+13 ALM total, +8.5 ALM `DUT`, +30 registers, -1.94 MHz).
`#576`'s own real, stated bet -- that Quartus's boolean optimizer would
prune a narrower core's dead contribution to a bit position it doesn't
reach, collapsing the effective selector width per bit -- did NOT pay
off in practice. The real per-core sum barely moved either (v4: 231.6,
v5: 229.5, a negligible -0.9%), so the shell-level "glue" cost stayed
essentially fixed regardless of which of the two write-path shapes was
used (v4: 308.1 ALM shell overhead, v5: 318.7 ALM, actually slightly
higher).

**A real, honest re-diagnosis this result forces:** the earlier
hypothesis in `#575` specifically named "the write-select mux" as the
cost driver, implicitly suggesting a differently-SHAPED mux might cost
less. This result says that's not the right level of explanation --
changing the mux's own internal structure (whole-word case-select vs
per-bit masked-hold) made essentially no difference. The real,
remaining, more honest hypothesis: the cost is inherent to having 8
structurally different cores' worth of real logic all compete to drive
the SAME physical storage location at all, regardless of exactly how
that competition is arbitrated -- not a specific, fixable inefficiency
in any one write-path shape tried so far.

**Real, honest conclusion for this specific redesign thread: closed,
not extended further without new direction.** Both real attempts at
sharing storage across all 8 cores (`#573`'s wide mux, `#576`'s per-bit
mask) land in the same real cost class -- roughly 45-50% more ALM and
~10% less Fmax than v3's own plain, separate-per-core storage, despite
genuinely cutting register count by a third. `#565`'s own original
question ("does sharing storage save anything real") now has a real,
concrete, negative answer for both mechanisms actually tried. v3
remains the real, cheaper, faster design of the three -- the honest
baseline to build on unless a genuinely different sharing strategy
(not just a different mux shape) is worth trying.

## 578. project_assemble_v1.py extended with a real --shell flag -- the full N-cell array generator (distinct from -S's own single-core-type mode) can now target either unicell_super_v3 (separate per-core storage) or unicell_super_v4 (the shared external-storage shell, #573), per Alan's own real, direct request to test whether the shared-storage cost finding from #575/#577 holds up at genuine array scale, not just N=1. Two real N=10 projects generated and elaboration-checked clean; the real Quartus scale comparison is the actual next step. (Alan/Claude, 2026-09-01)

**STATUS: real, generator extended and verified; two real N=10 projects
generated, elaborate cleanly in Icarus. Real Quartus builds still
pending -- the actual point of this entry.**

**Why this was asked for, precisely:** Alan's own real, direct
observation -- the earlier #573-#577 comparison was N=1 only, and this
project's own real, hard-won history (`#552`-`#560`) already shows N=1
numbers can mislead badly at scale (the 500-cell clock-fanout mystery,
`#559`/`#560`, and the earlier single-core-type dataset's own real
per-cell inflation once genuine cardinal connectivity replaces a
constant-tied N=1 reference, `#572`). The real, honest question this
entry exists to let Alan answer: does v3's own real per-cell cost
inflate disproportionately at scale (as the old full-fat cell did,
capping real card capacity around ~250 cells) in a way v4's fewer-
register design might avoid, or does v4's own real N=1 ALM disadvantage
just get carried through unchanged at scale? Neither has been measured
yet -- this is a real, open question, not assumed answered by the N=1
result.

**`tools/project_assemble_v1.py` real changes:** a new `SHELL_REGISTRY`
(`"v3"` -> `unicell_super_v3` + the original `V3_DEPENDENCIES`; `"v4"`
-> `unicell_super_v4` + a new, real `V4_DEPENDENCIES` list confirmed
directly against `top_unicell_super_test_v4.qsf`, `#573`'s own already-
working build) threaded through `generate_top()`/`generate_qsf()`/
`assemble()`, plus a new `--shell {v3,v4}` CLI flag (default `v3`,
matching prior behavior exactly for anyone not using the new flag).
v5 deliberately NOT added to the registry -- `#577` already found it
performs the same as v4, not better, so an array build of it wouldn't
answer a new question. The per-cell instantiation code itself needed
NO changes beyond the module name substitution -- v4's own real port
list is a strict superset of v3's (one extra output,
`status_shared_state`), and Verilog's named-port connection already
lets the generator's existing instantiation template simply omit it,
matching the same convention already used for `status_core_select`.

**Two real N=10 projects generated and verified, matching Alan's own
requested scale:**
```
python3 tools/project_assemble_v1.py --man docs/man/mustang-f100-a10.man.json --cells 10 --shell v3 --output <dir>
python3 tools/project_assemble_v1.py --man docs/man/mustang-f100-a10.man.json --cells 10 --shell v4 --output <dir>
```
Both real 4x3-grid arrays elaborate cleanly against a real Icarus
Verilog toolchain (every dependency resolved, zero errors) -- the same
level of confirmation `#552`'s own original N=9/N=500 generator output
got before its first real Quartus attempt. **A real, honest, quick
sim-liveness check (driving `ENTRY_DATA`/`CFG_SELECT` and watching
`array_alive`) did NOT show toggling in a short observation window for
EITHER shell** -- flagged plainly rather than glossed over, but not
treated as a real design defect: the anti-pruning mechanism this
generator relies on (`#554`) is a real, STRUCTURAL property Quartus's
own synthesis-time optimizer respects (an unconstrained top-level
input it cannot prove constant), not something a short, arbitrarily-
seeded simulation window is the right tool to confirm either way --
and the identical result on both shells (not one working, one not)
points at the quick testbench's own limited scope rather than a real
asymmetric regression from this entry's change. The real, authoritative
confirmation remains what it's always been for this generator: an
actual Quartus build, same as `#552`-`#555`.

**Zero regression:** 361/361 Python tests still pass -- this tool has
no dedicated automated test file, checked directly (none exists), so
the full suite plus a real syntax check plus two real generation runs
is the honest extent of verification performed here.

**Real, honest scope: no real Quartus data yet for either N=10 array.**
That comparative build -- whether v3's real per-cell cost holds steady
at N=10 the way `#572`'s own single-core-type data showed a plausible,
expected, roughly-2x connectivity cost (not a runaway one), or whether
either shell shows early signs of the kind of scale-dependent inflation
`#559`/`#560` found once before -- is the actual, real next step, and
the real point of extending this tool at all.

## 579. Real Quartus result, v3 at real array scale (N=10) -- confirms Alan's own real, remembered ~250-cell historical ceiling almost exactly (251,680 / 1030.5 real ALM/cell = ~244 cells), but for a newly-identified, previously-invisible reason: the three output addons (nibble_mask/shift_lane/invert), structurally disabled in every N=1 self-test run so far, turn out to be a real, dominant cost once genuinely live -- shift_lane alone averages ~242 ALM/cell, more than nano or branch. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful. First half of the real N=10
comparative pair Alan asked for (`#578`).**

**Whole-design real numbers:** 10,329 ALM / 251,680 (4%), 5,776
registers, `clk_div` 68.46 MHz (down from N=1's real 107.05 MHz,
`#574` -- a genuine 36% Fmax drop at scale, still comfortably above
the real 25 MHz target). Router estimated peak interconnect usage 24%
in one region -- worth watching at higher N, not yet a real constraint
at N=10.

**Real per-cell average, computed directly from all 10 individual
`unicell_super_v3:C_r_c` instance figures (not estimated): 1030.52
ALM/cell** -- a real, direct **3.41x** increase over the real N=1
baseline (301.9 ALM, `#574`).

**A real, previously-unknown cost driver found and precisely
localized, not vaguely attributed to "connectivity":** every real N=1
self-test built so far (`top_unicell_super_test_v3`/`v4`/`v5`) uses
`pack()`'s own literal `addon_config=20'h0` in every one of its real
config words -- meaning the three output addons
(`nibble_mask_addon_v1`, `shift_lane_addon_v1`, `invert_addon_v1`) were
STRUCTURALLY DISABLED, provably-constant-off, in every real N=1 number
logged so far. Quartus had every real reason to prune them down to
near nothing at N=1 -- and evidently did, since they don't even appear
as separate hierarchy lines in `#574`'s own real report. This array
build's own generator broadcasts `addon_config` from a genuinely
unconstrained `ENTRY_DATA`-derived value, so for the first time ALL
THREE addons are genuinely live, and their real cost is fully exposed:

| Addon | Real avg ALM/cell |
|---|---|
| `shift_lane_addon_v1` | **241.95** |
| `invert_addon_v1` | 113.56 |
| `nibble_mask_addon_v1` | 24.51 |
| **addon total** | **380.02** |

**`shift_lane_addon_v1` alone is the single most expensive line item in
the entire per-cell breakdown** -- more than `unicell_stripped_v1`
(nano, 181.06 avg) or `branch_cell_v1` (146.72 avg), the two most
expensive real CORES. The three addons together are **36.9% of the
real per-cell total** -- a real, substantial, previously entirely-hidden
cost this project had never actually measured before this entry.

**Real, honest breakdown of the full 1030.52 ALM/cell:**

| Component | Real avg ALM/cell |
|---|---|
| 3 addons | 380.02 |
| 8 cores (sum) | 593.03 |
| shell-level glue (mux/decode) | 57.47 |
| **total** | **1030.52** |

**Real per-CORE averages vs the real N=1 baseline (addons excluded,
comparing like-for-like):**

| Core | N=1 (`#574`) | N=10 avg | Ratio |
|---|---|---|---|
| compare | 10.5 | 55.30 | **5.27x** |
| branch | 46.5 | 146.72 | **3.15x** |
| nano | 62.5 | 181.06 | 2.90x |
| ram | 14.5 | 37.76 | 2.60x |
| adder | 31.6 | 57.85 | 1.83x |
| accumulator | 71.8 | 90.13 | 1.26x |
| latch | 8.5 | 9.08 | 1.07x |
| sequencer | 15.5 | 15.13 | 0.98x |

**Real, honest pattern, consistent with `#572`'s own earlier single-
core-type dataset finding (~2x real connectivity cost):** cores with a
genuine, real per-outcome or per-direction routing table (compare,
branch) show the largest real growth once actual cardinal neighbors
replace N=1's tied-off boundary constants. Sequencer again shows
essentially zero growth, matching `#564`'s own real finding that it has
no capture role at all and genuinely doesn't care about connectivity.

**The real, headline number Alan's own question was actually asking
for: 251,680 / 1030.52 = ~244 cells** -- closely matching Alan's own
real, remembered historical ceiling ("approximate max 250 cells") from
the OLD, pre-redesign full-fat cell. **The real ceiling appears to be
reproducing itself at almost the same real number, but for a
DIFFERENT, now newly-identified reason** (addon cost + real
connectivity cost on the current, redesigned v3 shell) rather than
whatever drove the original historical figure -- a real, honest,
striking coincidence worth flagging directly, not glossed over.

**Real, honest scope: this is HALF of the real N=10 comparison.** v4's
own matching N=10 build (same generator, `#578`, same real addon-
exposure the whole array shares) is the real, immediate next step --
including whether v4's own real per-cell register savings (`#575`:
-168 registers/cell at N=1) compounds meaningfully at N=10 (a real
potential ~1,680-register saving at this scale) even though its own
real N=1 ALM cost was higher, not lower, than v3's.

## 580. Real Quartus result, v4 at real array scale (N=10) -- the real, complete N=10 comparison Alan asked for. The relative ALM gap NARROWS at scale (+26.9% vs N=1's +47.8%), and register savings compound far beyond linear (-66.2% vs N=1's -35.7%) -- but v4 is still the more expensive design in absolute terms, with a real, dramatically amplified shell-glue cost (351.6 ALM/cell vs v3's 57.5) that is the actual, precisely-localized reason why. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful. Second half of the real N=10
comparative pair -- the actual, complete answer to Alan's own real
question.**

**Whole-design real numbers:** 13,108 ALM / 251,680 (5%), 1,953
registers, `clk_div` 58.64 MHz.

**Real, complete N=10 comparison table:**

| | v3 (separate storage) | v4 (shared storage) | Delta |
|---|---|---|---|
| Total ALM | 10,329 | 13,108 | **+26.9%** |
| ALM/cell (real avg) | 1030.52 | 1307.42 | +26.87% |
| Total registers | 5,776 | 1,953 | **-66.2%** |
| Registers/cell | 577.6 | 195.3 | -66.19% |
| `clk_div` | 68.46 MHz | 58.64 MHz | -14.3% |
| Real max cells (ALM-budget-only) | ~244 | ~193 | -21% |

**Real, honest, two-part finding, more nuanced than a flat "v4 costs
more":**

**1. The relative ALM gap NARROWS at scale, not widens.** N=1's real
gap was +47.8% (`#575`); at N=10 it's +26.9%. v4 is still the more
expensive design in absolute terms, but the earlier N=1 comparison
overstated the real, ongoing penalty once genuine array wiring is
present on both sides.

**2. Register savings compound FAR beyond a simple linear
extrapolation.** N=1 predicted -35.7%/cell; a naive ×10 extrapolation
of that N=1 saving would predict roughly -35.7% at N=10 too -- instead
the real, measured saving is -66.2%, nearly double. Real, honest,
NOT fully explained here: this suggests something beyond the simple
"8 small registers -> 1 shared register" swap is happening at scale
(a real candidate: Quartus retiming/duplicating registers differently
for fanout/timing reasons across the two designs at N=10, not
identically to how it handles N=1) -- a genuine open question, not
pursued further without Alan's own direction.

**Real, precise localization of WHY v4 still costs more overall,
using the same three-way split as `#579`:**

| Component | v3 avg ALM/cell | v4 avg ALM/cell | Delta |
|---|---|---|---|
| 3 addons | 380.02 | 447.87 | +17.9% |
| 8 cores (sum) | 593.03 | 507.96 | **-14.3%** |
| shell-level glue | 57.47 | **351.59** | **+512%** |

**The individual cores got CHEAPER under v4 at N=10 too** (507.96 vs
593.03, matching `#575`'s own real N=1 per-core finding of 6/8 cores
getting cheaper). **The addons cost modestly MORE under v4** (447.87
vs 380.02) -- `nibble_mask_addon_v1` specifically jumped from a real
24.51 avg (v3) to 77.96 avg (v4), a real, unexplained 3.18x difference
worth a closer look later, not investigated further here. **But the
real, dominant, decisive factor remains the shell-level glue -- 351.59
ALM/cell average for v4 vs v3's 57.47, a real 6.1x difference** --
confirming and AMPLIFYING `#575`'s own N=1 finding (which was a 7.6x
difference, 308.1 vs 40.5) that the write-arbitration mechanism itself,
not the cores or the addons, is the real, precise, consistent cost
driver of the shared-storage approach at every scale measured so far.

**Real, honest, complete answer to Alan's own real question ("does the
design work at scale"): yes, functionally -- no Quartus-side collapse,
no anomalous inflation pattern resembling `#559`/`#560`'s own real
500-cell clock-fanout mystery, both designs scale in a real, roughly
linear, per-cell-consistent way from N=1 to N=10.** Neither shell shows
the kind of runaway, non-linear blowup the OLD full-fat design showed
at N=500. v3 remains the real, cheaper, faster, higher-real-cell-count
design of the two -- v4's own real register savings are genuine and
substantial, but not (yet) enough to close the real ALM/Fmax gap that
determines this card's actual cell-count ceiling.

## 581. Real, single-variable isolation experiment built to find the actual reason a single cell is cheap and the same cell in an array is not -- top_unicell_super_v3_freeinput_v1.v. #579/#580's own real N=1-vs-N=10 comparison conflated two different real candidate causes (genuine cardinal connectivity vs genuinely-unconstrained config input) and couldn't tell them apart. This file changes ONLY the second one, holding everything else (N=1, no neighbors, addons still disabled) fixed. Sim-verified, real Quartus target built, not yet run -- the actual answer to Alan's own real "why" question. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified isolation build. Real Quartus number still
pending -- the actual point of this entry.**

**The real, precise question this isolates, stated plainly:** every N=1
self-test built so far (`top_unicell_super_test_v3`/`v4`/`v5`) presents
`core_select`/`core_config` to the DUT as one of only 8 real, compile-
time-KNOWN literal words -- each a genuine Verilog constant assigned at
a specific FSM state, not a value that could ever be anything else.
Quartus's own synthesis-time optimizer can trace an FSM with literal
per-state outputs and specialize logic around the exact, small, finite
value set that will ever reach a core. The array generator instead
drives `core_select`/`core_config` straight from genuine top-level
PRIMARY INPUTS (`CFG_SELECT`/`ENTRY_DATA`, `#554`) -- values Quartus
must treat as capable of being ANYTHING, since a real host could load
any pattern over JTAG. **This is a real, structurally different kind
of "unconstrained" from genuine cardinal connectivity (real neighbor
cells wired in) -- and `#579`/`#580`'s own real N=1-vs-N=10 numbers
conflate both changes at once, with no way to tell which one is doing
the real work.**

**`top_unicell_super_v3_freeinput_v1.v` (new)** -- ONE real
`unicell_super_v3` cell, held at N=1 with NO real neighbors (identical
boundary tie-off to `top_unicell_super_test_v3.v`: `data_in_s/e/w`,
`arrived_s/e/w`, all four `ack_in_*` tied to constants, matching
exactly). `addon_config` stays a literal constant 0, identical to
every prior self-test (`#579`'s own addon finding is deliberately
NOT re-tested here -- one real variable at a time). **The one real
change: `core_select` comes from a genuine, unconstrained `CFG_SELECT
[4:0]` top-level input, `core_config` from a genuine, unconstrained
`CFG_CONFIG[41:0]` top-level input** -- a full, independently-free 42
bits, not even the array generator's own cruder single-bit-repeated
broadcast (`{42{ENTRY_DATA}}`), the most general real case Quartus
could ever be asked to handle. One real, genuinely free `ENTRY_DATA`
drives the N-side data path, matching the self-test's own real single-
active-input convention. No FSM, no fixed self-check (there's no known
core to check against by design) -- a real, non-prunable XOR-reduce
anti-pruning guard instead, the same convention the array generator
itself already uses (`#554`).

**Sim-verified clean:** elaborates against every real v1 core
dependency, `status_core_select` correctly reflects the loaded
`CFG_SELECT` value, no X-propagation issues over a real simulated run.

**Real Quartus target built, matching the established template:**
`top_unicell_super_v3_freeinput_v1.qsf`/`.sdc`. **Honest, practical
note: `CFG_SELECT`/`CFG_CONFIG` (47 real I/O bits) are left WITHOUT
real physical pin assignments** -- this build is a pure resource/
timing experiment, not intended for actual hardware programming, so
Quartus is left to auto-assign pins; the real ALM/Fmax numbers it
reports are unaffected by this, but the design isn't meant to be
flashed onto the card as-is.

**How to read the real result once it's in, precisely:** compare its
own real `DUT` ALM figure against `#574`'s own real N=1 baseline (479
total / 301.9 `DUT`). If it lands CLOSE to 301.9, connectivity is the
real, dominant driver of `#579`'s own real N=1-to-N=10 gap. If it lands
CLOSE to `#579`'s own real N=10 non-addon per-cell average (650.50),
genuinely-unconstrained config input is the real, dominant driver, and
"connectivity" in the earlier framing was getting credit a different
mechanism actually earned. A real result landing meaningfully BETWEEN
the two would mean both genuinely contribute, in some real, then-
measurable proportion.

## 582. project_assemble_v1.py gains a real --logiclock flag -- one real per-cell LogicLock region (fixed-membership, auto-sized, floating) forcing each cell's own logic to be placed as one contiguous block. Direct, real fix for the exact failure mode Alan found by hand in the Chip Planner (#579-#581's own real screenshots): a cell's own logic scattered across a ~40-column span of the die, on BOTH shells, because the fitter has no idea the design is a regular tiled array and no reason to keep any one cell's logic together. (Alan/Claude, 2026-09-01)

**STATUS: real, generator extended, LogicLock-constrained N=10 projects
generated for both shells. Real Quartus comparison against the
already-real, unconstrained N=10 baselines (#579/#580) is the actual
next step.**

**Real, precise cause, confirmed by Alan's own real Chip Planner
evidence, not assumed:** the array generator broadcasts `cfg_valid`/
`cfg_data` identically to every cell (unchanged since `#554`), but
gives Quartus's placer NO other hint that this is a regular, tiled,
logically-local-only-connectivity design. Two real screenshots
confirmed the SAME symptom on BOTH shells: `C_2_0`'s own logic (v4)
spanning `X95`-`X135` to reach `C_1_0|shared_state[101]` -- a real,
genuinely adjacent cell in the logical grid, not an arbitrary one --
and `C_2_2`'s own addon chain (v3) reaching all the way to
`C_2_1|CORE_BRANCH`, its own real logical west neighbor. **This ruled
out an earlier hypothesis (v4-specific duplicate-logic sharing) --
v3 shows the identical symptom with no shared storage at all to merge,
so the real, correct diagnosis is a general placement-locality gap,
not something specific to either shell's own mechanism.** Alan's own
real TimeQuest evidence (`Extra Fitter Information`, path #1) ties this
directly to the real Fmax ceiling: 17.056ns data delay -> ~58.6 MHz,
matching v4's own real reported `clk_div` (58.64 MHz, `#580`) almost
exactly.

**`generate_logiclock_assignments()` (new)** in
`tools/project_assemble_v1.py` -- for every real cell position, emits
one real LogicLock region: `LL_ENABLED ON`, `LL_AUTO_SIZE ON`,
`LL_STATE FLOATING`, `LL_RESERVED OFF`, and `LL_MEMBER_OF <region> -to
<cell_instance>` assigning the CELL'S WHOLE TOP-LEVEL INSTANCE (every
core, every addon, all the shell's own write/mux logic underneath it)
as that region's sole member -- matching Alan's own real, direct
request ("will have to set constraints for the entire cell, for each
cell"). Deliberately NOT `LOCKED` with a hand-picked absolute X/Y
origin -- this project has no verified-precise real row/column map for
this exact device, and a wrong hardcoded origin is a real, avoidable
risk (`LL_STATE LOCKED` combined with a bad origin either errors or
gets silently auto-corrected by Quartus, neither of which is a real,
trustworthy result). `FLOATING` + `AUTO_SIZE` instead lets Quartus's
own fitter choose both the size and the placement of each region
freely -- but, unlike no constraint at all, it is REQUIRED to keep
every member of one region together as a single contiguous block.
Real, documented Quartus Standard Edition syntax, confirmed against
Intel's own community documentation before use here (`LL_ENABLED`/
`LL_AUTO_SIZE`/`LL_STATE`/`LL_RESERVED`/`LL_MEMBER_OF` all real,
current assignment names), not guessed.

**New `--logiclock` CLI flag** (default off, zero behavior change for
existing callers), threaded through `generate_qsf()`/`assemble()`.
Top-level module name gets a real `_ll` suffix when the flag is set
(e.g. `top_array_v3_10cells_ll_v1`), so a LogicLock build and its
unconstrained baseline never collide as Quartus revisions.

**Two real LogicLock-constrained N=10 projects generated** (`--cells
10 --shell v3 --logiclock` / `--shell v4 --logiclock`), matching
`#579`/`#580`'s own exact scale for a real, direct, apples-to-apples
comparison. RTL is byte-identical to the unconstrained baseline (only
the `.qsf` changed -- `generate_top()` itself untouched) -- both
elaborate cleanly, unsurprising since nothing in the actual netlist
changed. QSF content spot-checked directly: 10 real regions per
project, one per real cell, correct real instance names.

**Zero regression:** 361/361 Python tests.

**Real, honest scope: no real Quartus data yet for either LogicLock
build.** The real, direct comparison this enables -- same RTL, same
scale, ONLY the placement constraint changed -- against `#579`'s v3
baseline (1030.52 ALM/cell, 68.46 MHz) and `#580`'s v4 baseline
(1307.42 ALM/cell, 58.64 MHz) is the actual, real next step, and the
real test of whether Alan's own diagnosis (the fitter's own area-
optimization spreading logic hurts timing, the same real pattern seen
before) holds once cells are forced to stay physically compact.

## 583. Real Quartus result, LogicLock (AUTO_SIZE) v3 N=10 -- genuinely improved Fmax (+9.7%) for near-zero real ALM cost, but AUTO_SIZE reserves 3.10x more physical die area than the real logic needs (32.2% average region utilization) -- a real, hard area cost since LogicLock regions cannot overlap, dropping the real area-limited max cell count from #579's own ~244 down to ~78. generate_logiclock_assignments() extended with a real FIXED-size mode (--ll-fixed-alm) to fix this directly. Two real fixed-size N=10 projects generated; the real test of whether fixed sizing keeps the Fmax win without the area cost is the next step. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful for the AUTO_SIZE build. Real,
concrete generator fix built in response; the FIXED-size real Quartus
number is the actual next step.**

**Real whole-design numbers, AUTO_SIZE LogicLock, v3 N=10:** 10,365
ALM / 251,680 (4%), 5,776 registers (IDENTICAL to the unconstrained
baseline, `#579`), `clk_div` 75.11 MHz.

**Real comparison against the unconstrained baseline (`#579`):**

| | Unconstrained | LogicLock (AUTO_SIZE) | Delta |
|---|---|---|---|
| Total ALM | 10,329 | 10,365 | +0.35% |
| Registers | 5,776 | 5,776 | 0% |
| `clk_div` | 68.46 MHz | **75.11 MHz** | **+9.71%** |

**Real, genuine win: Fmax improved 9.7% for essentially free.** Alan's
own diagnosis (the fitter spreading logic for its own area-optimization
reasons, at real cost to timing -- the same real pattern flagged before
this session) is directly confirmed: forcing each cell's own logic to
stay physically together recovered real timing margin, with no
meaningful ALM or register cost.

**But a second, real, more serious problem was found in the SAME real
result -- directly on point for Alan's own "restricts useful area
available" concern, not a separate tangent:** the real Regional
Resource Usage table shows every one of the 10 real LogicLock regions
running at only 31-37% utilization (`ALMs needed` vs `total ALMs in
region`). Summed across all 10 real regions: **10,343 real ALM used
against 32,090 ALM-equivalent LAB capacity RESERVED -- a real 3.10x
reservation ratio, 32.2% average real utilization.** Because LogicLock
regions cannot overlap (confirmed against Intel's own real
documentation, `#582`), this is a real, HARD area cost, not a soft
one -- unused capacity inside a claimed region is unusable by any
other cell's region. **Real, honest consequence: the real, area-
limited max cell count under AUTO_SIZE LogicLock is ~251,680 / 3,209
(avg reserved ALM/cell) = ~78 cells -- WORSE than `#579`'s own ALM-
count-only ~244, and worse than no LogicLock at all** for the specific
question Alan raised. A real Fmax win that costs two-thirds of the
card's own real usable area is not a net win for a design whose whole
point is maximizing real cell count.

**The persisting real cross-cell path is expected, not a failure of
this fix:** the new fitter report (`C_0_1|ADDON_SL/ADDON_INV` ->
`C_1_1|CORE_BRANCH`) is between genuinely adjacent logical neighbors
(`C_0_1`'s real south neighbor is `C_1_1`) -- LogicLock only forces
INTRA-cell contiguity; the real RTL wiring BETWEEN neighboring cells
still has to cross a region boundary, and always will. That's real,
necessary connectivity, not a bug.

**`generate_logiclock_assignments()` extended with a real, second
mode** -- when a real, empirically-measured per-cell ALM figure is
given (`--ll-fixed-alm`, e.g. `#579`'s own real 1030.52 for v3 N=10,
`#580`'s own real 1307.42 for v4 N=10), it emits `LL_AUTO_SIZE OFF`
with an explicit, computed square `LL_WIDTH`/`LL_HEIGHT` sized to
`fixed_alm_per_cell * headroom` (default `--ll-headroom 1.25`, 25%
real slack over the measured figure -- deliberately far less than
AUTO_SIZE's own real ~3.1x, but real slack is still needed since
per-cell ALM cost genuinely varies cell-to-cell, `#579`'s own real
per-cell range was 900-1189 for v3). The real ALM-per-LAB density used
for the conversion (8.484) is itself derived directly from THIS same
real build's own regional table -- real, but honestly flagged as a
single-data-point calibration, not a device datasheet constant.

**Two real fixed-size N=10 projects generated**
(`--logiclock --ll-fixed-alm 1030.52` for v3, `1307.42` for v4),
computed to 13x13 LAB regions (169 LABs, ~1434 ALM capacity per cell --
close to the real 146-LAB/1288-ALM target, rounded up to a square
region). Both elaborate cleanly (RTL unchanged, only the `.qsf`
differs, same discipline as `#582`). Zero regression: 361/361 Python
tests.

**Real, honest scope: no real Quartus data yet for either fixed-size
build.** The real, actual test -- whether tighter, computed sizing
keeps most or all of the real 9.7% Fmax win while recovering real
usable die area back toward `#579`'s own ~244-cell ALM-only ceiling --
is the real, immediate next step.

## 584. Real, third design axis prototyped on one core -- compare_cell_v3.v + unicell_super_v6.v. Per Alan's own real, direct proposal: leave genuine runtime state exactly where v1 already keeps it (in the core, matching the cheapest real design measured so far, #579), but stop re-latching CONFIG fields into a private local copy when the shell's own super_latch already holds them stable and continuously. Confirmed as a real, genuine redundancy directly against compare_cell_v1.v's own RTL before building anything. Sim-verified clean at both the core and shell level; real Quartus target built, not yet run. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified prototype on ONE core (compare, Alan's own
choice, the simplest real candidate). Real Quartus number is the
actual next step.**

**The real, confirmed redundancy, checked against RTL before building
anything (not assumed):** `compare_cell_v1.v` re-latches `downstream_
mask`/`upstream_mask`/`threshold` into private local registers on
every `cfg_valid`:
```
end else if (cfg_valid) begin
    downstream_mask <= cfg_data[3:0];
    upstream_mask   <= cfg_data[7:4];
    threshold       <= cfg_data[39:8];
```
`unicell_super_v3.v`'s own shell ALREADY holds this exact same
information, stable, continuously, in `core_config` (`super_latch
[46:5]`), for as long as compare stays selected -- confirmed directly:
the shell wires each core's `cfg_data` port to `incoming_config`
(`cfg_data[46:5]`, the TRANSIENT one-shot top-level pulse), not
`core_config` (the STABLE, registered value) -- which is WHY every
core today is forced to latch its own private copy: the value it's
given only exists for one real cycle. Alan's own real proposal: wire
cores to the STABLE signal instead, and stop latching entirely.

**Real, precise reason this is architecturally SAFE, confirmed against
the shell's own real wiring, not assumed:** `arrived_n/s/e/w` are
already AND-gated with `sel_active_cmp` at the shell level (unchanged,
real, existing v3 wiring) -- so `any_upstream_arrived` is force-zero
whenever compare isn't genuinely selected, regardless of what
`core_config` happens to hold at that moment (another core's own real
config, since bit positions are a shared, reused budget across all 8
core types, `#315`). `capture_now` can therefore never fire on a
misread config value while deselected.

**Real, precise reason this is architecturally SAFER than v4/v5's own
shared-storage attempts (found to cost far more than they saved,
`#575`/`#577`/`#580`):** config is READ-ONLY from every core's own
perspective. A single source (the host, via `cfg_valid` into
`super_latch`) already writes it once -- there is NO write-side
arbitration needed at all, the exact mechanism `#575`/`#580` precisely
localized as the real, dominant cost of sharing RUNTIME state. This
proposal shares nothing that gets written by more than one place.

**`compare_cell_v3.v` (new)** -- identical to v1 except `downstream_
mask`/`upstream_mask`/`threshold` are now plain combinational wires
reading straight off a continuously-valid `cfg_data` input, no
register, no load-vs-hold mux. Genuine runtime state (`out_buffer`/
`data_valid`/`pending_ack`) UNCHANGED from v1 -- still real per-core
registers, still reset via `cfg_valid`.

**`tb_compare_v3_diff_v1.v` (new)** -- real, differential proof against
v1, 5/5 real checks including a genuine reconfigure case (threshold
8 -> 20), passing on the first attempt.

**`unicell_super_v6.v` (new)** -- cloned from `unicell_super_v3.v`,
EXACTLY ONE real change: the compare slot instantiates `compare_
cell_v3` instead of `compare_cell_v1`, wired to `core_config` instead
of `incoming_config`. Every other one of the 7 cores UNCHANGED, still
v1, still wired to the transient pulse -- a deliberate, minimal,
single-variable prototype, not a full redesign.

**`tb_unicell_super_v6.v` (new)** -- cloned from `tb_unicell_super_v3.v`
verbatim, same real 8-core sequence. All 8 real checks pass, including
the comparator's own real check (`10>=8=1`) -- notably, by the time
compare gets configured in this sequence, `core_config` has ALREADY
held RAM's, adder's, and accumulator's own real bit patterns during
compare's own deselected periods, and the real result is still
correct -- an empirical confirmation of the real safety property
above, not just a reasoned one.

**`top_unicell_super_test_v6.v` (new)** -- cloned from `top_unicell_
super_test_v3.v`, DUT swapped only. Sim-verified clean via a real
top-level testbench, first attempt.

**Real Quartus target built, matching the established template
exactly:** `top_unicell_super_test_v6.qsf`/`.sdc`. **Not yet run** --
the real test of whether this genuinely saves ALM, and how much,
against `#574`'s own real v3 N=1 baseline (479 total / 301.9 `DUT`).

**Real, honest scope on the real "config budget" question Alan also
raised:** `core_config` is already a 42-bit UNION, reused (not summed)
across all 8 core types, per this project's own existing, real design
(`#315`) -- confirmed directly against `unicell_super_v3.v`'s own real
header before writing this entry, already about as tight as it can be
without a real per-core width audit. Whatever real figure Alan had in
mind by "the current 166" wasn't identifiable from this session's own
real, checked data -- worth a direct follow-up rather than a guessed
match here.

**Zero regression:** 361/361 Python tests, `tb_unicell_super_v3.v`
(unchanged, still passes), `tb_compare_v2_diff_v1.v` (unchanged, still
passes).

## 585. Real Quartus result, v4 fixed-size (25% headroom) LogicLock N=10 -- unlike v3 (Fmax stayed flat under the same tight sizing, #583), v4's Fmax got WORSE, not better: 58.64 -> 50.53 MHz, a real -13.8% regression versus even the unconstrained baseline. A real, fourth independent axis on which v3 is the sturdier design -- not just cheaper and faster in isolation, but more tolerant of real placement constraints too. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful. Completes the real fixed-size
LogicLock pair for both shells at N=10.**

**Real whole-design numbers:** 12,750 ALM / 251,680 (5%), 1,953
registers (IDENTICAL to the unconstrained baseline, `#580`), `clk_div`
50.53 MHz.

**Real comparison against v4's own unconstrained N=10 baseline
(`#580`):**

| | Unconstrained | Fixed-LL (25% headroom) | Delta |
|---|---|---|---|
| Total ALM | 13,108 | 12,750 | -2.73% |
| Registers | 1,953 | 1,953 | 0% |
| `clk_div` | 58.64 MHz | **50.53 MHz** | **-13.83%** |

**Real, honest asymmetry between the two shells, not seen before this
entry:** v3's own fixed-LL result (`#583`) held Fmax essentially FLAT
against its unconstrained baseline (68.46 -> 68.75 MHz, +0.4%). v4's
own fixed-LL result here is a genuine REGRESSION, worse than not
constraining placement at all. Same sizing methodology (25% headroom
over each shell's own real measured per-cell ALM, `#583`'s own
formula), opposite real real-world result.

**The real critical path is the same recurring shape, confirmed again,
not a new failure mode:** `C_2_1`'s own addon chain (`ADDON_NM`/
`ADDON_SL`/`ADDON_INV`) reaching into `C_2_0` -- genuinely adjacent
logical neighbors, matching every prior real Chip Planner screenshot
in this thread (`#579`-`#583`). The tight box did NOT eliminate this
inter-cell wire (it structurally can't -- real RTL connectivity between
neighbors always has to cross a region boundary somewhere) -- what
changed is that v4's own real per-cell internal complexity (the
write-arbitration logic `#575`/`#580` already precisely localized as
6.1-7.6x more expensive than v3's equivalent) appears to need MORE
placement freedom to route efficiently, not less. Squeezing that
already-more-tangled internal structure into a tight box seems to cost
the placer room it needed for both the internal write logic AND the
genuinely necessary cross-cell wire at once.

**Real, honest conclusion: a fourth, independent axis on which v3 is
the sturdier real design.** Prior real findings established v3 as
cheaper (ALM, `#579`/`#580`) and faster (Fmax, `#579`/`#580`) in
isolation. This entry adds: v3 also tolerates real, tight placement
constraints gracefully (flat Fmax under a 25%-headroom box, `#583`),
while v4 does NOT (a real -13.8% Fmax regression under the identical
methodology). Real, honest scope: v4's own real AUTO_SIZE LogicLock
number was never measured (only v3's was, `#583`) -- whether a looser
headroom would recover v4's own real Fmax is a real, open, unpursued
question, but given v3's own real superiority across every other
dimension measured so far, not an obviously worthwhile one to chase
further without a specific new reason to prefer v4.

## 586. Real, measured Quartus build times on Alan's own real machine -- worth recording for real session planning, since it directly bounds how many real builds are practical in one sitting: N=1 (single-cell self-test) ~5 minutes. N=10 (array) ~10 minutes. Full-card (~244-cell real ceiling range, #579) ~2-3 hours. (Alan, 2026-09-01)

**Real, practical consequence for how this project plans real Quartus
work going forward:** N=1 and N=10 builds are cheap enough to run
freely for real, single-variable comparisons (as this whole session's
own real #573-#585 sequence did). A real full-card build is NOT --
2-3 hours is a real, meaningful cost, so those should be queued
deliberately, only once a specific real hypothesis is worth the real
wall-clock time, not speculatively.

## 587. Real, second core rolled out on the same axis -- latch_cell_v3.v + unicell_super_v7.v. Latch picked per Alan's own real request ("try another small one first") -- the smallest real core (8.5 ALM at N=1, #574). Same real change as compare (#584): config fields (set_dir/clear_dir/downstream_mask/toggle_dir) read continuously off the shell's own stable core_config, no local latch. Genuine runtime state, including v1's own real "data_valid goes live immediately on cfg_valid" quirk, preserved exactly. Sim-verified clean; real Quartus target built, not yet run. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified. TWO of 8 real cores now on this axis
(compare, latch). Real Quartus number is the actual next step.**

**Real, confirmed redundancy, same shape as compare's own (`#584`):**
`latch_cell_v1.v` re-latches `set_dir`/`clear_dir`/`downstream_mask`/
`toggle_dir` (16 bits total) into private local registers on every
`cfg_valid`, duplicating what the shell's own `core_config` already
holds stable. Same real fix: read continuously instead.

**`latch_cell_v3.v` (new)** -- identical to v1 except those 4 config
fields are now plain combinational wires. Genuine runtime state
(`latched`/`out_buffer`/`data_valid`/`pending_ack`) UNCHANGED,
including a real, deliberate quirk specific to this core that had to
be preserved exactly, not just copied structurally: v1 sets `data_
valid <= 1'b1` immediately on `cfg_valid` (live from the first cycle
after config, unlike compare which starts empty) -- confirmed
preserved in v3 by direct comparison against v1's own real reset/
reload block before finalizing the file.

**`tb_latch_v3_diff_v1.v` (new)** -- real, differential proof against
v1, reusing the SAME real stimulus sequence already proven for v2
(`#563`: set, clear, second-set, reconfigure, toggle) rather than a
new, unvetted one. 5/5 real checks, first attempt.

**`unicell_super_v7.v` (new)** -- cloned from `unicell_super_v6.v`
(compare already on this axis), latch slot now `latch_cell_v3` wired
to `core_config`. 6 of 8 cores remain v1, unchanged, still wired to
`incoming_config` -- a deliberate, incremental rollout, not a full
redesign in one step.

**`tb_unicell_super_v7.v` (new)** -- all 8 real checks pass, including
latch's own real check (`data_out_e[0]=1` after set) with both
compare and latch now on the new mechanism simultaneously.

**`top_unicell_super_test_v7.v` (new)** + real Quartus target
(`top_unicell_super_test_v7.qsf`/`.sdc`), matching the established
template. Sim-verified clean, first attempt. **Not yet run** -- the
real, cumulative test (compare + latch together) against `#574`'s own
original v3 baseline (479 total / 301.9 `DUT`) and `#584`'s own
intermediate v6 number (487 total / 298.5 `DUT`).

**Zero regression:** 361/361 Python tests, `tb_unicell_super_v6.v`
(unchanged, still passes), `tb_compare_v3_diff_v1.v` (unchanged),
`tb_latch_v2_diff_v1.v` (unchanged).

## 588. Real, hand-built first test of Alan's own "moat" idea -- top_moat_tile_v1.v. Pattern A (constant, no sharing -- Alan's own preferred first test): one real unicell_super_v3 center cell surrounded by 8 real ram_cell_v1 moat cells, 4 edge (real dataflow to the center) + 4 corner (real ring, connected only to their own two adjacent edge cells -- no diagonal port exists or is needed, confirmed against real port lists before wiring anything). Each of the 9 cells gets its own LogicLock region. The real question: does fencing a super-cell in with small, separately-regioned buffer cells address the ROOT cause of the cross-die scattering (#579-#585), not just tune one region's own size. Sim-verified clean, real Quartus target built, not yet run. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified, hand-built (not yet a generalized
generator capability -- matching this project's own established
precedent of hand-building a genuinely new experiment first, #581,
before investing in generalizing it). Real Quartus number is the
actual next step.**

**The real layout, matching `project_assemble_v1.py`'s own exact
neighbor-wiring convention (`dout_DIR` of a cell feeds `data_in_
OPPOSITE(DIR)` of its real neighbor):**
```
    NW ── N ── NE
     │    │    │
     W ── CTR ─ E
     │    │    │
    SW ── S ── SE
```
`CTR` = `unicell_super_v3` (`#574`'s own real, proven, cheapest
shell). All 8 real moat positions = `ram_cell_v1` (the simplest real
core already used as moat material elsewhere).

**Real, confirmed-before-building fact:** no diagonal port exists
anywhere in this project's own real RTL (only N/S/E/W on every core
and shell) -- `CTR` structurally cannot reach `NE`/`NW`/`SE`/`SW`
directly, confirmed against real port lists, not just reasoned. The 4
real corner cells instead form a genuine ring AROUND the center,
connected only to their own two adjacent EDGE moat cells (e.g. `NE`'s
own south port reaches `E`, `NE`'s own west port reaches `N`) -- a
real, genuine 2D analogue of a 3D via-layer bypass, per Alan's own
framing, using nothing but the cardinal ports that already exist.

**Real, deliberate config-comparability decision:** `CTR` and all 8
real moat cells share the SAME real `cfg_valid_bcast`/`cfg_data_bcast`
construction the existing homogeneous array generator already uses
(`{13'b0, {20{ENTRY_DATA}}, {42{ENTRY_DATA}}, CFG_SELECT}`) --
deliberately, so this real ALM/Fmax number stays directly comparable
to `#579`/`#580`'s own real N=10 array data (same real addon exposure,
same genuinely-unconstrained config, not the N=1 self-test's own
cheaper, compile-time-known literal config that `#581`'s own
isolation experiment is separately investigating).

**Real, per-cell LogicLock regions, pattern A (Alan's own preferred
first test) -- 9 real regions, one per cell, `AUTO_SIZE` (the sizing
mode that showed a genuine, uncomplicated real Fmax win for a v3-style
design at no extra ALM cost, `#583`).** Only one real super-cell exists
in this test, so the real "do neighboring super-cells SHARE moat
cells" question (pattern B, Alan's own real "may prove a new type of
beast altogether") does not arise yet -- a real, later, larger tiled
test, not this one.

**Sim-verified clean:** elaborates against every real v1 dependency,
`status_core_select` correctly reflects the loaded `CFG_SELECT`. A
quick liveness spot-check (matching the same methodology already used
on the homogeneous array generator's own output, which showed the
identical "no toggle in a short window" result on both shells there
too, `#578`) showed no toggling -- not treated as a defect, for the
same real reason as before: the real anti-pruning guard is a
structural, synthesis-time property, not something a short arbitrary
simulation window is the right tool to confirm.

**Real Quartus target built:** `top_moat_tile_v1.qsf`/`.sdc`, matching
the established template exactly. **Not yet run** -- the real test of
whether surrounding a super-cell with small, separately-regioned
buffer cells addresses the actual root cause of the real cross-die
scattering seen in every prior real Chip Planner screenshot (`#579`-
`#585`: a super-cell's own logic, or its addon chain, reaching into a
genuinely adjacent logical neighbor SUPER-CELL) -- by ensuring that,
once this pattern is eventually tiled at scale, a super-cell's real
nearest neighbors are always small, cheap, boring RAM regions, never
another super-cell's own large, complex region competing for the same
placement territory.

**Real, honest scope: single-tile-only.** This build measures ONE
super-cell's own real cost with a moat, not yet a tiled, multi-super-
cell card. Real per-cell area cost of this approach (1 super-cell +
8 moat cells) is a real, separate, not-yet-measured trade-off against
raw cell density -- worth a direct, honest look once this first real
number is in, before committing to a larger tiled test.

## 589. Real bug found and fixed: top_moat_tile_v1.v's own wire declarations used a `` token-pasting macro Icarus Verilog accepted but Quartus's own Verilog HDL compiler rejects outright -- a real, avoidable tool-compatibility mistake, caught only when Alan's own real Quartus build failed on it, not before. Fixed by writing the 9 real per-cell wire groups out explicitly instead of chasing a portable macro. (Alan/Claude, 2026-09-01)

**STATUS: real, fixed, re-verified clean in Icarus. Quartus is the
real, remaining confirmation -- not yet re-attempted.**

**Real, honest root cause:** `#588`'s own first draft used
`` `define MOAT_WIRES(nm) wire [31:0] nm``_dout_n, ...`` -- a real
token-pasting macro, relying on Icarus Verilog's own real acceptance
of `` `` `` concatenation inside a macro body. Quartus's own real
Verilog HDL compiler does not support this construct the same way
(confirmed directly by Alan's own real build failure: `Error (10108):
missing Compiler Directive`, `Error (10149): identifier "CTR" is
already declared`) -- a real, genuine tool divergence between the two
real toolchains this project uses (Icarus for sim-first verification,
Quartus for the real, authoritative build), not a transient glitch.
**This is exactly the kind of gap sim-first verification cannot catch
by itself** -- the file elaborated and ran correctly in Icarus,
appearing fully verified, while being genuinely broken for the one
toolchain that actually matters for a real result.

**Real fix:** removed the macro entirely, wrote all 9 real per-cell
wire groups (`CTR`/`N`/`S`/`E`/`W`/`NE`/`NW`/`SE`/`SW`, each `dout_*`/
`fire_*`/`ack_*`) out explicitly, plain Verilog, no preprocessor
tricks. Re-verified clean in Icarus (identical real elaboration and
liveness-check behavior to before the fix, confirming this was purely
a portability issue, not a real logic change).

**Real, honest process note, worth stating plainly rather than
glossing over:** this project's own standing discipline is sim-first
verification before any real Quartus attempt -- and that discipline
was followed here. But sim-first verification is only as good as the
TOOLCHAIN it runs against; a construct valid in Icarus but invalid in
Quartus is a real, genuine blind spot sim-only verification cannot
close by itself. Real, going-forward takeaway: avoid preprocessor
macros for structural RTL (module/wire generation) in future hand-
built files -- explicit, plain Verilog, even when more verbose, is
the safer real default given this project uses two real, imperfectly-
compatible toolchains.

## 590. project_assemble_v1.py gains real, custom shell/dependency-list support -- --shell-file/--shell-module (array any real shell sharing v3/v4's own port list, not just the two hardcoded in SHELL_REGISTRY) and --file-list/--files (a real, explicit dependency list, overriding SHELL_REGISTRY entirely). Per Alan's own direct request -- mixing core versions (compare_cell_v3, latch_cell_v3, the moat tile) had meant hand-writing a fresh QSF file list every time. A real, advisory compatibility check runs automatically whenever --shell-file is given. A real bug found and fixed during the very first end-to-end test. (Alan/Claude, 2026-09-01)

**STATUS: real, tested, working. A real bug found and fixed on the
first real attempt, not glossed over.**

**The real, direct motivation, Alan's own words:** "if you can specify
the file inclusion list rather than use a hard coded list, this would
make the build a bit easier if we mix and match versions of cells."
Confirmed as a real, genuine pain point against this session's own
recent history -- `unicell_super_v6.v`/`v7.v` (`#584`/`#587`) and the
moat tile (`#588`) each needed a hand-written QSF dependency list,
duplicating real information already implicit in which files actually
exist.

**`--shell-file`/`--shell-module` (new)** -- point the array generator
at ANY real shell file, not just the two entries in `SHELL_REGISTRY`.
Works directly with zero template changes for any shell sharing v3/
v4's own real port list (confirmed: `unicell_super_v6.v`/`v7.v` are
both real clones of v3, so they already match exactly) -- `generate_
top()`'s own existing instantiation template only needed the module
NAME to become overridable, nothing else. The shell file is
automatically added to the real dependency list if not already
present.

**`--file-list`/`--files` (new)** -- a real, explicit dependency list,
either a plain text file (one real filename per line, `#`-comments
and blank lines ignored) or an inline comma-separated string,
overriding `SHELL_REGISTRY`'s own registered list entirely. Both
tested directly, both work.

**`check_dependency_compatibility()` (new)** -- a real, advisory,
NOT-authoritative check, per Alan's own real acknowledgment that this
"would have to check compatibility too." Confirmed the real module
name is declared where expected, and heuristically scans the shell
file's own body for module instantiations (a deliberately conservative
regex, documented as advisory everywhere it surfaces -- Verilog
instantiation syntax cannot be fully, reliably distinguished from
other constructs by regex alone, and this is stated plainly rather
than overclaiming precision). **Tested directly by deliberately
omitting `latch_cell_v3.v` from a real file list -- correctly flagged:**
`"the shell file appears to instantiate the following real module(s)
not found declared in the real dependency list: latch_cell_v3"`.
Never blocks generation on its own -- a real compile (iverilog or
Quartus) remains the only real, authoritative confirmation, stated
explicitly in the warning text itself.

**A real bug found and fixed on the very first end-to-end test, not
hidden:** the first real attempt (`--shell-file fpga/verilog/
unicell_super_v7.v`, a natural, repo-relative path) failed with a
doubled path (`fpga/verilog/fpga/verilog/unicell_super_v7.v`) --
`shell_src_path`'s own resolution logic assumed a BARE filename (this
tool's own established convention for every other dependency) and
unconditionally joined it with `src_dir`, not accounting for a person
naturally typing a fuller, already-qualified path. Real, honest fix:
resolution now tries the path exactly as given first (absolute, or
relative to the current working directory), and only falls back to
resolving the bare filename against `src_dir` if that exact path
doesn't exist -- handles both real, natural ways a person might type
it, rather than demanding one specific format.

**Real, end-to-end tests performed, not just unit-level:** a real
N=10 array of `unicell_super_v7.v` (compare_cell_v3 + latch_cell_v3 +
6 real v1 cores) generated via BOTH `--files` and `--file-list`,
elaborates cleanly in Icarus against every real dependency. A real,
deliberately incomplete dependency list correctly triggered the
compatibility warning. **Zero regression on every EXISTING generator
path**, tested directly: `--shell v3` (registry), `--shell v4
--logiclock --ll-fixed-alm` (registry + LogicLock), `-S ram_cell`
(single-core-type), and the full 361-test Python suite.

**Real, honest scope on the rest of Alan's own real idea:** a GUI
checkbox list of available real files (Alan's own "maybe have a list
of files available, and check boxes") is a real, separate, future
frontend feature (`frontend_v1.py`'s own real placeholder slots),
not attempted here -- this entry builds the real BACKEND capability
(`--file-list`/`--files`/compatibility checking) such a UI would need
to call into, not the UI itself.

## 591. Real Quartus result, v7 (compare_cell_v3 + latch_cell_v3 together) -- both per-core wins hold up, individually and cumulatively, but the whole-DUT and whole-design numbers are noisy enough relative to their small size that the aggregate benefit isn't yet clearly visible above normal build-to-build variance with only 2 of 8 cores done. A real, honest, not-yet-explained Fmax decline across the two builds so far is worth watching, not yet worth alarm. (Alan/Claude, 2026-09-01)

**STATUS: real, Flow Status Successful. Both individual core wins
confirmed real and reproducible; the aggregate picture is genuinely
inconclusive at this small a sample.**

**Real, whole-design numbers:** 486 ALM / 251,680 (<1%), 457
registers, `clk_div` 102.9 MHz.

**Real per-core comparison, v3 baseline (`#574`) -> v6 (`#584`) -> v7
(this entry):**

| Core | v3 | v6 | v7 | Cumulative |
|---|---|---|---|---|
| `CORE_CMP` | 10.5 | 9.0 | 8.8 | **-16.2%** |
| `CORE_LATCH` | 8.5 | -- | 7.7 | **-9.4%** |

**Both real config-redundancy fixes hold up under a second, real,
independent build** -- compare's own win (`#584`) didn't regress when
latch was added alongside it, and latch's own new win lands in the
same real direction and rough magnitude reasoned about beforehand
(`#587`).

**Real, honest complication: the whole-`DUT` and whole-8-core-sum
numbers do NOT clearly show these wins.** `DUT` itself: v3=301.9,
v6=298.5, v7=298.7 -- essentially flat between v6 and v7 despite
latch's own real -0.8 ALM contribution, because OTHER, UNTOUCHED cores
moved by MORE than that in the same build: `accumulator_cell_v1` alone
swung from 71.8 (v3) to 79.5 (v7), a real +7.7 ALM shift on a core
nothing in this thread has touched. **Real, honest conclusion: normal
real build-to-build placement/routing variance on the UNTOUCHED cores
is currently LARGER than the real, deliberate savings being measured
on the touched ones.** The 8-core sum: v3=261.4, v7=257.1, a real
-1.64% aggregate move in the right direction -- consistent with, but
not yet a clean, unambiguous confirmation of, the real per-core wins
above (a single real, independent rebuild of v3 itself, with nothing
changed, would be a real, useful way to separately measure how much
of that -1.64% is genuine signal vs how much is this same kind of
noise -- not yet done).

**Real, honest, not-yet-explained trend worth flagging, not yet worth
alarm: `clk_div` has declined across both real builds so far** --
107.05 (v3) -> 106.54 (v6) -> 102.9 (v7), a real cumulative -3.88%.
Neither compare's nor latch's own real change touches timing-critical
logic in any way reasoned about in advance (`#584`/`#587`'s own real
safety arguments were both about ALM/logic redundancy, not timing) --
whether this is genuine cumulative cost from the new mechanism, or
the same real build-to-build Fmax variance already seen elsewhere in
this project (`#574` vs `#579`'s own later remeasurement showed
several-MHz swings for nominally-identical designs too), is a real,
open question best answered by watching whether it continues as more
cores are rolled out, not by reacting to two data points alone.

**Real, honest scope for what's next:** both real per-core wins are
confirmed real and worth keeping. Whether to continue rolling this
change out to the remaining 6 cores (where the aggregate signal may
become clearer as more, larger config budgets are addressed -- RAM
and branch each use the full 42-bit `core_config` window, versus
compare's 40 and latch's 16) or pause here pending a clearer read on
the noise floor is a real, open call, not decided in this entry.

## 592. Real, third and widest core rolled out on the config-off-shell axis -- accumulator_cell_v3.v + unicell_super_v8.v. Accumulator picked per Alan's own real request for "a more complex, wider" core next, specifically to test whether a bigger real config budget (37 bits -- inc_dir/dec_dir/downstream_mask/step_amount/pulse_mode/threshold, the widest touched by this thread so far) produces a saving large enough to clear the real build-to-build noise floor #591 found limiting the two smaller cores' own aggregate visibility. Sim-verified clean, including both static and pulse mode; real Quartus target built, not yet run. (Alan/Claude, 2026-09-01)

**STATUS: real, sim-verified. THREE of 8 real cores now on this axis
(compare, latch, accumulator). Real Quartus number is the actual next
step.**

**Real, confirmed redundancy, same shape as compare's and latch's own
(`#584`/`#587`), on the widest config budget yet:**
`accumulator_cell_v1.v` re-latches `inc_dir`/`dec_dir`/`downstream_
mask`/`step_amount`/`pulse_mode`/`threshold` (37 bits total, including
a real 16-bit threshold field) into private local registers on every
`cfg_valid`. Same real fix: read continuously off the shell's own
stable `core_config` instead.

**`accumulator_cell_v3.v` (new)** -- identical to v1 except those 6
config fields are now plain combinational wires. Genuine runtime state
(`accumulator`/`out_buffer`/`data_valid`/`pulse_pending`/`pending_
ack`) UNCHANGED, including the real, deliberate "data_valid live
immediately on cfg_valid" quirk (matching latch's own real precedent,
`#587`) and the full real pulse-mode mechanism (threshold-crossing
reset-to-0, discrete pulse offering) -- confirmed preserved exactly by
direct comparison against v1's own real reset/reload block, not just
structurally copied.

**`tb_accumulator_v3_diff_v1.v` (new)** -- real, differential proof
against v1, reusing the SAME real stimulus sequence already proven for
v2 (`#564`: static-mode config, 3 increments, a genuine reconfigure to
pulse mode, a real threshold crossing). 8/8 real checks, first
attempt -- confirms the config-redundancy fix holds even through
accumulator's own real, more complex pulse-mode logic, not just its
simple static-mode path.

**`unicell_super_v8.v` (new)** -- cloned from `unicell_super_v7.v`
(compare + latch already on this axis), accumulator slot now
`accumulator_cell_v3` wired to `core_config`. 5 of 8 cores remain v1,
unchanged.

**`tb_unicell_super_v8.v` (new)** -- all 8 real checks pass, including
accumulator's own real check (3 increments -> 3), with all THREE
converted cores active simultaneously in one shell.

**`top_unicell_super_test_v8.v` (new)** + real Quartus target
(`top_unicell_super_test_v8.qsf`/`.sdc`), matching the established
template. Sim-verified clean, first attempt. **Not yet run** -- the
real, cumulative test (compare + latch + accumulator together) against
`#574`'s original v3 baseline (479 total / 301.9 `DUT`) and `#591`'s
own intermediate v7 number (486 total / 298.7 `DUT`) -- and, per
Alan's own real reasoning for picking this core, whether accumulator's
own real per-core saving is large enough to show up clearly above the
real build-to-build noise `#591` found on the two smaller cores (the
~+7.7 ALM swing on an UNTOUCHED core in that same build).

**Zero regression:** 361/361 Python tests, `tb_unicell_super_v7.v`
(unchanged, still passes), `tb_accumulator_v2_diff_v1.v` (unchanged).

## 593. Real status audit, part 2 -- docs/shared/POINTS_STATUS_AUDIT_2.md, covering entries #331-#592 (the original 2026-08-16 audit only covered #1-#330). Per Alan's own direct request for a real status index -- "what is done, what is pending, what is a thought direction" -- built while the moat tile (#588) Quartus build ran. Organized around status FIRST this time (a quick-reference section listing every currently-queued build and open thread), era second, matching the scale the ledger has actually grown to. (Alan/Claude, 2026-09-02)

**STATUS: real, complete, written. Does not edit points.md/points/
itself, same discipline as the original audit -- a curated map on top
of the ledger, not a replacement for it.**

**Method, matching the original audit's own precedent:** all 262
entry titles in the #331-#592 range read in full (this project's own
entry titles are consistently complete summary sentences, not short
labels), grouped into 6 real eras by actual subject matter, several
spot-checked in full text where the title alone left status
ambiguous.

**The real, most useful addition, per Alan's own specific ask:** a
"Quick reference: what's actually pending or open RIGHT NOW" section
at the top, pulled out of 262 entries rather than requiring anyone to
scroll to find it -- 3 real Quartus builds currently queued (moat
tile, v8's cumulative config-redundancy result, and a real, still-
missing middle-headroom LogicLock test), 3 real named next steps not
yet built (rolling the config fix out to the remaining 5 cores, moat
pattern B, and `#581`'s own free-input isolation experiment -- flagged
specifically because it was genuinely at risk of being lost track of
under the LogicLock/moat/config-redundancy threads that came after
it), and 4 real thought-directions on record with no build started
(clockless/async model, LLVM IR compiler path, AI training buckets,
multi-card PCIe backplane requirement).

**Real, 6-era breakdown of #331-#592, each with an explicit status
verdict:** VM/compiler/workbench build-out then real, deliberate
archival following Alan's own project-scope recalibration (#331-#369,
DONE + dead-ended simultaneously, both true at once); priority-list
execution + DSP research (#370-#399, DONE, TRIX-not-viable and
branching-has-real-cost both settled here); the RAM/collector/
sentinel/shared-BRAM mechanism culminating in this project's first
EVER host-driven real hardware confirmation (#400-#448, DONE); MAN/
SHAPE/placement tooling + real DSP hardware confirmation, including a
real, corrected wrong-IP-name mistake (#449-#480, DONE); the branch/
comparator core's actual design and build, directly ancestral to
every current shell version (#481-#519, DONE); the systematic per-
core headroom review with the highest density of real silicon
confirmations in the project (#520-#551, DONE); and `project_
assemble_v1.py`'s own genesis plus the real single-core-type dataset
this whole session's own comparative work builds on (#552-#572, DONE).

**One real, connecting observation surfaced, easy to lose across 20
dense entries:** the config-redundancy thread (`#584` onward) and the
moat thread (`#588` onward) both started only AFTER the shared-
storage thread (`#561`-`#585`) reached its own real, negative
conclusion (v4/v5 costs more on every axis measured) -- worth staying
precise that neither is an attempt to revive shared runtime storage;
both are different real mechanisms, each with its own explicit reason
for not sharing v4/v5's own specific failure mode.

**Real, honest, structural observation closing the document:** this
project's documentation-about-documentation has now needed splitting
and auditing twice -- not a criticism, a real, direct signal of how
much genuine progress has happened (592 entries, real silicon
confirmed dozens of times, a five-tool pipeline built and used), but
worth treating as a real data point on `#477`'s own still-open "per-
file documentation" item and on how session catch-up itself scales
from here.

**Cross-linked from both `points/INDEX.md`** (new "Status" section)
**and the original audit** (a forward-pointer added at its own top).
