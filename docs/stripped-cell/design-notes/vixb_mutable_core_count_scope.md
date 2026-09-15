# VIXb: mutable core count — a real scoping pass (Alan/Claude, 2026-09-15)

*Per Alan's own direct framing: this is a core unit of the whole
design, worth scoping properly before anything else, not another
quick patch. "VIXb" has existed only as a short label since the
original VIXa/VIXb split (`#719` onward) -- checked directly before
writing this: no prior note actually scoped it in detail. This is
that first real pass. Nothing built here; a decision to review.*

## The real problem, stated precisely, with real evidence behind it

Adding `mul` (`#726`) and `priority` (`#731`) as the 10th and 11th
cores each required the same real, hand-coordinated edit across
`unicell_vix_carrier_v1.v` (775 real lines) -- confirmed by actually
doing it twice, not estimated. Every one of these real touch points
had to be found and updated by hand, both times:

1. A new `SEL_<NAME>` value in the `core_select` localparam block.
2. A new `cfgv_<name>` wire (`effective_cfg_valid && core_select == SEL_<NAME>`).
3. A new `sel_<name>` wire (`core_select == SEL_<NAME>`).
4. A new `<name>_cfg` wire, sliced from `incoming_config` at the
   core's own real, correct width -- and the real width GENUINELY
   VARIES per core (confirmed directly: 64 bits for adder/compare/
   accumulator/latch/sequencer/command/mul/priority, 80 bits for ram/
   branch, 128 bits for nano -- not a fixed convention this file could
   assume).
5. A block of new `<name>_dn/ds/de/dw`, `<name>_fn/fs/fe/fw`,
   `<name>_ready`, `<name>_an/as_/ae/aw`, `<name>_pd`, `<name>_pan/
   pas/pae/paw` output wire declarations (14 real wires).
6. The full shell instantiation itself -- roughly 20 real port
   connections, most of them mechanical but requiring the core's own
   real status-port names to be checked directly rather than assumed
   (confirmed the hard way: `priority_shell_v1c`'s own status ports
   don't match `mul_shell_v1c`'s own, caught only by checking the
   actual file).
7. Adding the new core into EVERY ONE of 14 real, shared mux
   expressions -- the single addon-chain `mux_dout`, `fire`×4, `ack`×4,
   `ready`, `program_done`, and `prog_ack`×4.

**Roughly 20 real, separate edit points per core, confirmed twice, not
estimated once and assumed to generalize.** A 12th core would cost the
same again. This is real, repeated, error-prone manual work -- the
exact kind of thing this project's own established discipline
(`resolve_core_file()`, `#734`) already treats as a real bug class
when it shows up as a stale, hand-maintained list. `unicell_vix_
carrier_v1.v` itself, as a single hand-written file enumerating every
core explicitly, is the same real anti-pattern at a larger scale.

## Two real, genuinely different approaches — not a foregone conclusion

**Option A: true Verilog parameterization.** A single, generic RTL
module using `generate`/`parameter` constructs, where the actual core
mix is a build-time parameter rather than hardcoded module text. This
is what "parameterized hardware" usually means, and it's the more
hardware-native answer.

*The real, honest obstacle, not a minor wrinkle:* every core's own
real `cfg_data` width genuinely differs (64/80/128 bits, confirmed
above), and status ports genuinely differ by core too (`priority`'s
own 2-bit `status_winning_dir` versus `mul`'s own single-bit `status_
a_arrived`, confirmed directly building both). Real Verilog has no
clean way to array together module instances of genuinely different
port shapes. Making this work would mean either (a) forcing every
core's own shell to conform to one uniform, widest interface (128-bit
`cfg_data` for everyone, a generic status-port convention) -- a real,
invasive rewrite of all 11 existing `_v4c` shells, each currently
correct and independently verified -- or (b) a `case`-based generate
block that's genuinely no simpler to maintain than the current
hand-written mux chains, just wrapped in `generate` syntax.

**Option B: a real, Python-side RTL generator**, extending the same
pattern `tools/project_assemble_v1.py` already uses for every other
generated top-level file in this project (`generate_single_core_top()`,
`generate_top_vix()`, and now `derive_vix_dependencies()`, `#734`).
Given a real, explicit list of which cores a design actually needs, a
generator emits a correct, complete carrier `.v` file mechanically --
the same real edits I made by hand today for `mul`/`priority`, done
by code instead of by a person, using each core's own already-known
real width/status-port facts (already half-captured in `project_
assemble_v1.py`'s own `CORE_REGISTRY`, though that registry currently
describes the OLD lineage's cores, not the `_v4c` family -- a real gap
this option would need to close, not one it inherits pre-solved).

*Real, honest tradeoff, stated directly rather than glossed over:*
the generated file is still a static, one-shot RTL file once emitted
-- not a single, reusable, general-purpose Verilog module the way
Option A would be. But every existing core/shell RTL stays completely
untouched, each keeping its own natural width and interface, and the
approach requires zero changes to 11 already-verified files to
implement.

**This is the same real idea `#726`'s own "carrier build system" note
already queued** -- select which cores a design needs, build (and
test) a carrier sized to exactly that set. Worth being direct about
this: `VIXb` and that queued idea are not two separate problems that
happen to be related. They are the same problem, and Option B solves
both at once, deliberately, not as a side effect.

## A real, working recommendation, not a neutral list — but stated as one, for review

**Option B, for one real, concrete reason: it doesn't require
touching or re-verifying 11 files that already work.** Option A's own
real cost (uniform-interface rewrite across every existing shell) is
a large, risky undertaking for something whose whole point is
avoiding risk and repeated work. Option B's own real cost is building
one new, focused tool, following a pattern (`project_assemble_v1.py`'s
own generation functions) already proven in this exact codebase. This
is a recommendation, not a decision made unilaterally — the actual
call is Alan's, same as every other real architectural fork in this
project.

## Real, honest, open questions this scoping pass does NOT resolve

- **What does the generator's own real input look like?** A plain
  list of core names is the obvious minimum (`["adder", "ram", "mul",
  "priority"]`) -- but does it also need to accept the shift-addon
  exception (`#729`: `shift_lane_addon_v1` for standalone use, `v2`
  for the carrier's own shared chain) as an explicit input, or can
  that stay hardcoded since it's a property of the SHARED chain, not
  of which cores are selected?
- **Does `core_select`'s own 5-bit width (32 real slots, 11 used)
  need to become a real, generator-computed value** (narrower for a
  small carrier, e.g. 3 bits for 5 cores) or does it stay fixed at 5
  bits regardless of core count, trading a little real config-word
  efficiency for a simpler, more uniform generator? Real tradeoff, not
  yet weighed.
- **Does the generated file need its own generated testbench too?**
  `#726`'s own "build AND test" framing suggests yes -- but this
  project's own real testbenches (`tb_vix_carrier_mul_v1.v`, etc.) are
  hand-written per new capability being proven, not per specific core
  combination. Whether a genuinely useful GENERATED testbench looks
  like "re-run every included core's own standalone checks through
  the generated carrier" or something else entirely is real, unscoped
  work.
- **Where does this tool actually live** -- inside `project_assemble_
  v1.py` itself (extending its own existing generation functions,
  closest to Option B's own stated precedent) or as a genuinely
  separate tool? Real, undecided.
- **`CORE_REGISTRY` in `project_assemble_v1.py` currently describes
  the OLD lineage's cores, not the `_v4c` family at all** -- a real,
  separate, necessary piece of groundwork Option B would need
  regardless of every other question above: a real, current registry
  of each `_v4c` core's own width/status-port/PROG_ID facts, checked
  against the actual RTL the way `#734`'s own fixes insisted on
  throughout, not assumed from the old registry's own shape.

## Real, honest status

A scoping pass, not a build plan. No RTL, no generator code, no
registry written. The real recommendation above (Option B) is a
starting point for review, not a conclusion already acted on --
matching this project's own established discipline for anything at
this level of architectural weight.
