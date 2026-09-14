# From raw Verilog to a real core — a process guide (Alan/Claude, 2026-09-08)

This is a real, reusable process, written down because it's needed
more than once now (9 existing cores, `mul` as the 10th) and will be
needed again by anyone — including future sessions — adding a new
core. It's drawn directly from the real steps that built `mul_cell_
v4.v`/`mul_cell_v4c.v` (`points.md #724`), and from the real corrections
found building `_v4c` variants for the other 9 (`#720`-`#723`). Every
gotcha named here is a real one that was actually hit, not a
hypothetical.

## Step 0 — verify the raw design BEFORE trusting it with anything

Whatever the raw Verilog is — contributed, generated, copied from a
textbook — it gets its own, independent `iverilog` check before it's
allowed anywhere near a real core wrapper. This project's own real
precedent (`bitwise_multiplier_32bit.v`) was already verified once by
whoever contributed it; it still got re-verified from scratch before
`#724` built on top of it, against real edge cases (`0`, `0xFFFFFFFF ×
0xFFFFFFFF`) and cross-checked against Verilog's own native operator
as an independent reference. A design that "looked right" is not the
same as a design that's been checked.

**A real, concrete failure mode worth naming: a design can look
correct and still not compile.** `bitwise_divider_32bit.v` (a real
divider candidate, sitting in `future-core-candidates/`) has a literal
syntax error (`</generate>` instead of `endgenerate` — a copy/paste
artifact) and was saved UNMODIFIED, not silently patched, specifically
so nobody inherits a "fixed" file without knowing it was ever broken.
Confirm compilation with `iverilog -g2012` directly; don't assume.

**A real, separate check, distinct from correctness: does this fit
the real timing budget at all?** This whole architecture's premise is
wire-delay-based timing with a real, hard per-hop number (the super
carrier shell's own 200.76 MHz, `#322`). A purely combinational design
with a long, unbroken dependency chain — the divider candidate above
is 32 sequential subtract-and-shift stages, each depending on the
previous one's own result — is a real, serious risk to that budget in
a way a wide-but-shallow design (the multiplier's own 32-way parallel
adder tree, genuine log-depth once synthesis collapses it) isn't.
**Check this BEFORE building a wrapper, not after** — a core that's
functionally perfect but blows the clock budget is not a real core
yet, and finding that out after building the whole protocol around it
wastes the work.

## Step 1 — promote the design into `fpga/verilog/`

Real RTL lives in `fpga/verilog/`, not in a docs folder. Copy the file
over (`cp`, not a rewrite), and add a real header noting where it came
from and that it was re-verified before promotion — the file's own
history matters, and someone reading it later shouldn't have to guess
whether it's trusted or aspirational.

## Step 2 — pick the right existing core as a real template

Don't design a new protocol from scratch. Every core in this family
shares the same real shape: two-stage operand capture (`a_reg`/
`a_arrived`), a real `can_fire`/`capture_now` gate, `pending_ack`-based
multi-directional offering, a programming channel with `PROG_ID`
dispatch, the real `active`/`freeze_in` gating, and (for a standalone
`_v4`) the real 3-addon chain. Pick whichever existing core's own real
operand shape is closest:

- **Two dynamic operands in, one result out, no special semantics** —
  `adder_cell_v4.v` is the right template (this is what `mul` used).
- **One dynamic operand, a compile-time/config amount** — look at how
  the compiler's own `shl`/`lshr` shift addon fields work instead;
  the two-operand capture protocol is overkill for a single-operand
  core.
- **A real, single-bit or boolean result** — `compare_cell_v4.v` or
  `nano_gate_v4.v` are closer templates than a full arithmetic core.

Copy the template file wholesale, then work from there — don't build
the scaffolding by hand.

## Step 3 — swap the real arithmetic, and ONLY the real arithmetic

Replace the template's own core computation (e.g. `adder_v1`) with the
new design's own instantiation. Everything else — capture, fire, ack,
ready, the programming channel structure, `active`/`freeze_in` — stays
exactly as the template has it. This is the one part of the whole
process that's genuinely specific to the new operation; everything
else is boilerplate that's already been proven correct many times over
and doesn't need re-deriving.

**Real, honest scope decisions belong here, made explicitly, not left
implicit:**
- Does every field the template has still apply? `mul_cell_v4` removed
  `subtract_mode` entirely (no real equivalent for multiply) rather
  than leaving a dead, unused bit sitting in the config word.
- Does the new operation produce more bits than the port width allows?
  `mul`'s own real product is 64 bits; the core offers only the low 32
  (`Product[31:0]`), matching LLVM's own real `mul` truncation
  semantics — the same wraparound `add`/`sub` already use. State this
  choice directly in the header rather than letting a reader discover
  it by inspecting the code.
- Keep `PROG_ID` numbering STABLE when a field is removed — leave the
  old ID's own slot unused rather than renumbering everything above
  it. A later `_v4c` swap, or anything else that already knows the old
  numbering, shouldn't need to re-derive a new one just because a
  field went away.

Update the file's own header comment with the real, final `cfg_data`
field map — every bit range, named, with anything unused marked
`reserved`, not left undocumented.

## Step 4 — build a standalone testbench, adapted from an existing one

Don't write a testbench from scratch either — adapt the template
core's own real testbench. The real coverage shape every existing core
testbench already has is worth keeping:
1. Real core behavior against an independent reference (Verilog's own
   native operator, where one exists, is the simplest real ground
   truth — `a * b`, `a + b`, etc.)
2. Any real edge case specific to the NEW operation — for `mul`, the
   real low-32-bit overflow-truncation case (`0x10000 × 0x10000`
   wrapping to `0`) mattered specifically because it's exactly the
   kind of thing a 64-bit-capable multiplier feeding a 32-bit result
   path can get subtly wrong.
3. Real targeted `PROG_ID` reconfiguration — confirm the live-
   programming channel reaches whichever fields survived step 3.
4. The real addon chain (`_v4` only) — confirm at least one addon
   (`invert_en` is simplest) genuinely transforms the offered value.
5. Real `active=0` gating — confirm the cell goes fully silent, not
   just that its output looks quiet.

## Step 5 — verify `_v4` standalone before building `_v4c`

Compile and run with `iverilog` directly. Every check should pass
before moving on — a `_v4c` variant built on top of an unverified
`_v4` just doubles the surface area of whatever's actually wrong.

## Step 6 — build the `_v4c` variant

**Real, honest reasoning, not a mechanical copy — two real decisions,
both hard-won from correcting the other 9 cores (`#720`-`#723`):**

1. **Remove the internal addon chain entirely.** A carrier that wraps
   this core is meant to hold common functionality centrally (`#720`'s
   own real finding, from an actual architectural review) — a `_v4c`
   core carrying its own copy of the SAME transform the carrier
   already provides once is real, genuine duplication, not
   redundancy-as-safety-margin. Remove the three addon module
   instantiations, the `addon_config` register, its own `cfg_data`
   field, and its own `PROG_ID` case. Leave the freed bits `reserved`
   in the header, don't repurpose them for anything else without a
   real, separate reason.

2. **Feed this core's own `cfg_data` from the carrier's combinational
   `incoming_config`, NOT the registered `core_config`.** This is the
   one that actually cost real debugging time (`#723`): reasoning by
   direct analogy to `unicell_super_v9.v`'s own `#699` fix (which reads
   `core_config` CONTINUOUSLY) seems right, but it's wrong for THESE
   cores specifically, because they only ever LATCH `cfg_data` once,
   on their own `cfg_valid` pulse — and `core_config` is a registered
   value that only reflects a new commit ONE CLOCK CYCLE AFTER
   `cfg_valid` fires, while a core's own `cfg_valid` pulse is
   COMBINATIONAL, asserted the SAME cycle as the external commit. A
   core latching on its own `cfg_valid` this way needs the value
   that's ABOUT to land (`incoming_config`), not the one that already
   did. This was found by an ACTUAL failing testbench (the very first
   check failed, and the simulation hung later) — not assumed correct
   from the analogy. If a future core's own config-reading shape ever
   changes (e.g., a genuinely continuous reader, matching `v9`'s own
   `_v3` cells), THAT core would need `core_config` instead — the
   right source depends on how the core reads it, not on a blanket
   rule.

Base `_v4` file stays completely untouched throughout this whole
step — it's still the real, proven, standalone core for anywhere
nothing wraps it.

## Step 7 — adapt the testbench for `_v4c`, verify again

Remove the addon-specific check (step 4.4) — but check carefully
whether removing it also removes some REAL STATE ADVANCE later checks
depend on. This bit hard once already: `accumulator_cell_v4`'s own
addon test included a real `inc_pulse` that moved the running total
from 7 to 12, which a LATER check (unrelated to the addon chain
itself) depended on reaching. The fix wasn't to delete the whole
block — it was to keep the real state-advancing action and only
change the expectation from an inverted value to a plain one. Check
this for every removed block, not just assume removal is always safe.

## Step 8 — build matching shell wrappers

Every core gets wrapped by a thin cardinal shell (`_shell_v1`/
`_shell_v1c`) that OR-combines the core's own flat `active`/
`freeze_in` ports into real 4-directional ones. This is genuinely
mechanical — copy an existing shell, swap the instantiated core name,
done. No real design decisions live here.

## Step 9 — wiring into a real carrier (a separate, later step)

Everything above produces a real, standalone, verified core. Actually
wiring it into `unicell_vix_carrier_v1.v` (or any future carrier) is
its own, separate task: a new `core_select` value, a real `_cfg`
derivation (using whichever config source step 6.2 determined is
correct), a new mux entry in the shared output path, and a full
re-verification of every existing carrier testbench alongside a new
one for the added core. Don't treat this as "the last step of core
creation" — it's a real, separate integration with its own real risk
of breaking something already working, and deserves its own
verify-before-proceeding pass, not a bundled one.

## A real, standing question worth asking before starting all of this

**Is the new operation even mechanically related to an existing one,
such that "inverting" or reusing structure might work?** It's tempting
to assume a multiplier can be "flipped" into a divider, the way
`sub` is just `add` with one operand negated. It can't — multiply and
divide are genuinely different algorithms, not structural inverses.
The real multiplier here is a wide, PARALLEL tree (32 partial products
generated independently, summed via an adder tree — genuine log-depth
once synthesis collapses it). Division, done the standard
restoring-algorithm way, is SEQUENTIAL by its own real nature — each
of the 32 bit-stages depends on the previous stage's own running
remainder, a genuine linear-depth chain with no equivalent
parallelization. This is exactly why the divider candidate
(`bitwise_divider_32bit.v`, already sitting in `future-core-
candidates/`, real syntax bug and all) carries the real, serious
timing concern named in Step 0 and the multiplier doesn't -- they are
not the same shape of circuit at all, just because they're both "the
other arithmetic operation." Check the real algorithm's own shape
before assuming a shortcut exists; sometimes the honest answer is
"this needs an actually different design," not a clever reuse.
