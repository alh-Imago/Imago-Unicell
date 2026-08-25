# Current State (as of 2026-08-25, real ordered priority queue set for the next several sessions, see `points.md` #495)

## Read this first (most recent)

**2026-08-25, session close, real ordered roadmap, Alan's own explicit
sequencing, captured before drift:**
1. `#469`'s real DSP IP correction (wrong IP name, first, ahead of
   everything below).
2. The branch/comparator core (`#491`-`#494`'s fully-scoped design,
   built for real this time).
3. The flow-through from that -- per-core watchdog wiring, then a real
   Designer starvation-hazard validation rule.
4. The Designer -- the new core's own tile registration (should cost
   one library module + one import line via the existing `#485`/`#486`
   hook), plus the data-input-point concept, stepped onboarding flow,
   real interactive polish, and ICM round-trip editing.
5. `#448`'s burst-write JTAG opcode.
6. The full 27-way scale family, extended to real host-driven
   operation.
7. Second-card mapping, framed as a software-stack question now too --
   how a second card's cells get addressed/placed/compiled for from
   the same tools that today only know one card.

Full detail: `points.md` `#495`. This is the order to start from next
session unless something changes it deliberately.

## Previous state (2026-08-25, in+N timing question resolved -- ICM-programming time, single fixed upstream direction now a settled constraint, see `points.md` #494)

**2026-08-25, real resolution to the compile-time-vs-runtime question
`#493` left open, same session.** `in+N` resolves at ICM-PROGRAMMING
time -- same moment `topology`/`threshold`/`routing_mask`/every other
core_config field already gets set -- not baked into the `.sof`
(would fix the direction mapping permanently, forcing a full rebuild
for a different orientation) and not re-resolved dynamically per
arrival either (if the upstream could accept from more than one
direction, the reference direction itself would vary unpredictably
firing to firing -- Alan's own words, "data going every which way...
if it hits it randomly"). The compiler/Designer computes the real
absolute direction for each configured `in+N` once, at placement time,
and bakes it into the core_config's own direction field, exactly like
every other direction field already works -- the `.sof` stays generic
and reusable across any placement. **Real, now-settled consequence:**
this core needs a SINGLE fixed upstream direction, not a multi-
direction mask like today's `comparator`'s own `upstream_mask` -- a
real constraint on the eventual field table, not just a note. **Still
nothing built.** `#492`'s own three-stage dependency chain (branch
mechanism -> per-core watchdog wiring -> Designer starvation-hazard
validation) is unchanged. Full detail: `points.md` `#494`.

## Previous state (2026-08-25, branch/comparator design corrected to a per-outcome table -- "conditional branching with teeth," see `points.md` #493)

**2026-08-25, real correction to `#492`'s own framing, same session.**
`#492` logged an intermediate "three separate modes" version (value/
direction/gate). Alan corrected it: the real, final shape is a
PER-OUTCOME TABLE, not three mutually-exclusive modes -- each of the 3
real comparator outcomes (`<`/`=`/`>`) independently configures three
orthogonal fields: **A** which value (relay the real supplied value,
or an up-to-8-bit fixed constant), **C** emit or not emit (real,
genuine suppression -- the qualitatively new piece; today's comparator
always emits something, even a real `0`), **D** direction, up to 3 at
once (relative `in+1`/`in+2`/`in+3`, real fan-out, matching the
existing `pattern_low`/`pattern_equal`/`pattern_high` bitmask
convention exactly). This subsumes `#492`'s three modes as special
cases rather than replacing them -- and lets each outcome in the SAME
cell do something genuinely different from the others (e.g. `<` stays
silent, `=` relays raw to `in+2`, `>` emits a fixed tag to both
`in+1`/`in+3` at once). Rough bit shape: 13 bits/outcome x 3 = 39 bits,
alongside existing `threshold`/`upstream_mask` -- tight but plausible
in the 80-bit `SUPER_LATCH`, real accounting deferred to build time.
**Real, honest scope: still nothing built.** `#492`'s own three-stage
dependency chain (branch mechanism -> per-core watchdog wiring ->
Designer starvation-hazard validation) is unchanged by this
correction. Full detail: `points.md` `#493`.

## Previous state (2026-08-25, branch/comparator design fully worked through -- three-stage dependency chain identified, see `points.md` #492)

**2026-08-25, real design session working through #491's own gap into
a concrete shape -- nothing built yet, captured in full per Alan's own
request.** Extends the existing `dynamic_route_en`/`pattern_low`/
`pattern_equal`/`pattern_high` mechanism (`#140`/`#156`) with: a real
mode switch (direction output vs. value output) on a branch/comparator
cell; RELATIVE direction addressing for direction mode (`in+1`/`in+2`/
`in+3`, offset from the arrival direction -- a real, deliberate
departure from every other absolute-compass direction field in the
system, kept deliberately for its rotation-invariant payoff); and a
further split within value mode (fixed table constant vs. the actual
supplied value, relayed through, GATED by outcome). Worked through
directly: outcome-gated relay can legitimately leave a branch
permanently quiet -- confirmed this is the standard, useful filter/
gate idiom (alarm/anomaly paths), explicitly NOT the same as the
already-known closed-relay-loop hazard, and the option should be KEPT.
The real hazard is narrower and specific: a gated output feeding a
REQUIRED multi-input join (only the `adder` core today) with no
starvation detection upstream. Chasing "use the watchdog for that"
surfaced a real, SECOND gap, checked directly against the RTL:
`watchdog_v1.v` is only wired into the DSP wrapper family, never into
`unicell_super_v1.v` or any ordinary core cell -- the same shape of
gap `#491` already found for branching, now found for watchdog too. A
"lanes" tangent (`#43`) was checked and ruled out as unrelated (FULL-
cell-only, never built, structurally different -- unconditional word
decomposition, not conditional branching). Full detail, including the
real three-stage dependency chain for whenever this gets picked back
up (branch mechanism -> per-core watchdog wiring -> only then a
meaningful Designer starvation-hazard validation rule): `points.md`
`#492`.

## Previous state (2026-08-24, real architectural gap identified: branching capability stranded on nano-only path, not reachable from the super cell, see `points.md` #491)

**2026-08-24, session close, a real architectural realization logged
before drift, Alan's own words.** `#490` answered a direct question
("was branching removed?") by confirming it: no, it's real, RTL-
confirmed, and still present in the standalone nano cell
(`dynamic_route_en`/`pattern_low`/`pattern_equal`/`pattern_high`,
`#140`/`#156`) -- but `unicell_super_v1.v`'s own nano-core
reconstruction only ever wired through the "basic" subset (`topology`/
`ready`/`routing_mask`/`cardinal_edge`), never the branching fields
(or the rest of nano's "full" feature set -- `hold_in`/`fb_internal_
in`/`is_command_cell`). `super_tile_library_v1.py` already names this
exact boundary as a reserved, unbuilt `target="nano-full"` tag.
Alan's own real, precise diagnosis, captured directly: without
branching reachable from any super-cell tile, every program built
through the current tile libraries/DSL/Designer is necessarily a
strictly linear, serial chain -- no runtime branching anywhere -- and
that's the concrete reason the current architecture's own scope has
felt smaller than intended. A related, precise (not blanket) point:
the original archived FULL cell genuinely had this capability in a way
the current super-cell architecture, for all its other real
advantages, does not yet match. **Real, honest scope: nothing built,
nothing scoped into steps yet** -- Alan's own explicit choice was to
log this and stop for the session, not scope or build it now. Full
detail, including the natural shape of what building this would
involve: `points.md` `#491`.

**Natural next-session starting point, when picked back up:** extend
the SUPER_LATCH `nano` core_config field table (or a new `branch`/
`nano_full` core) to carry the branching fields through to
`unicell_super_v1.v`, then thread that up through `icm_v3.py`'s field
tables and `super_tile_library_v1.py`'s own tile definitions -- from
there the already-built generic registry/hook mechanisms (`#485`/
`#486`) should pick it up in the Tile Designer/DSL/compiler
automatically, with no further compiler rewrite needed.

## Previous state (2026-08-24, drag-to-connect reciprocal auto-wire + comparator clarification, see `points.md` #490)

**2026-08-24, real reciprocal auto-wire added to the Tile Designer's
drag-to-connect gesture:** dragging A onto an adjacent cell B now
auto-wires B's own matching port back toward A when unambiguous
(target has exactly one unwired port left), client-side only, no
backend change. Also answered directly: the `comparator` core is a
simple two-way `>=` (`result = 1 if value >= threshold else 0`), no
three-way low/equal/high mode. Full detail: `points.md` `#490`.

## Earlier state (2026-08-24, real params/"internals" UI added to the Tile Designer + explainer updated to match, see `points.md` #489)

**2026-08-24, the internals/params piece Alan asked for directly**
("the comparator needs a value, the nano needs gate settings...
maybe look at the explainer as an idea, yes that needs updating
too"). `TileDesignerController.list_library()` now returns real
`param_info` per declared param -- plain `{"kind": "number"}` by
default, or `{"kind": "choice", "choices": [...]}` for the one real,
named picker that exists today: `nano_gate.topology`, sourced directly
from `unicell_gate_core.py`'s own real `TOPO_*` constants (AND/OR/
XOR/NAND/NOR/XNOR/PASS_A/PASS_B/NOT_A/ZERO/ONE), never hand-
duplicated. Small, explicit `_PARAM_CHOICES` table -- one real entry
today, extending it later costs one more dict entry. Inspector's own
new `renderParamFields()` renders whichever the server says. The SAME
real picker retrofitted into `tools/explainers/cell_pipeline_
explainer.html`'s own nano/topology field, replacing a raw hex input
-- per Alan's own direct confirmation this tool needed updating too.
New `tests/vm/test_cell_pipeline_explainer_v1.py` -- the first-ever
automated test for that explainer, persisting `#376`'s own manual
verification standard: the JS's own bit-packing proven byte-for-byte
against `nano/icm_v3.py`'s real Python encoder via a real `node`
subprocess, for all 11 named topologies. `tests/vm/test_tile_
designer_v1.py` gained 4 more functions (26 total) covering the same
ground on the Designer side, including a real end-to-end AND-gate
export/behavior check. Zero regression, 335/335 (was 327). Full
detail: `points.md` `#489`.

**Real, honest scope still open, per Alan's own stated next steps:** a
short, stepped onboarding flow through the Designer; a real, explicit
"data input point" concept for `#488`'s own `"open"` connection
status. Neither started.

## Previous state (2026-08-24, drag-to-connect + connection indicators added to the Tile Designer, see `points.md` #488)

**2026-08-24, first real UI iteration on the Tile Designer, per
Alan's own direct request ("to start," ahead of a stepped flow and a
data-input point).** Connection STATUS (open vs. connected, real
target coordinates) is computed server-side in `TileDesignerController.
_port_connections()` and returned as part of `/describe` -- the client
only renders what the server already reports, matching this project's
own "one authoritative place" principle rather than duplicating logic
into unverifiable JS. Real drag-to-connect gesture added: drag an
occupied grid cell onto an adjacent cell, the real cardinal direction
is inferred from the drop geometry, and whichever unwired port applies
gets set via the SAME existing `/set_port` endpoint. Connection
indicators (small colored markers, green=connected/amber=open) render
per wired port on the grid. Honest, stated-in-code limitation:
indicators are computed from an instance's own anchor, exact for
Tier-0-shaped tiles, an approximation for composed (Tier-1) instances
whose real ports may belong to an offset sub-cell -- doesn't affect
what actually exports, only how it's drawn. The one genuinely
client-side piece of logic (`directionFromDelta()`/`unwiredPorts()`)
was extracted from the served HTML and proven correct via a real
`node` subprocess run, not just eyeballed. `tests/vm/test_tile_
designer_v1.py`, 5 new functions (22 total), zero regression, 327/327
(was 322). Full detail: `points.md` `#488`.

**Real, honest scope still open, per Alan's own stated next steps:** a
short, stepped onboarding flow; a real, explicit "data input point"
concept (an `"open"` connection deliberately marked as a boundary
injection point). Neither started.

## Previous state (2026-08-24, real Tile Designer built and tested -- fifth tool in the #479 architecture, see `points.md` #487)

**2026-08-24, the fifth and final tool in `#479`'s own agreed
architecture: the Tile Designer.** Real scoping note written FIRST
(`docs/stripped-cell/design-notes/tile_designer_scope.md`), per the
project's own established discipline -- one real correction made to
the old archived Composer's own "reusable visual paradigm" finding
(`#387`): the old tool's drag-anywhere link gesture assumed bus
addressing; Unicell-S links are real cardinal DIRECTIONS, so the
Designer's own gesture is "select an instance, choose a direction per
port" instead. New `nano/tile_designer_v1.py` -- `TileDesignerController`
(HTTP-unaware, every method returns a plain `{"ok":...}` dict, matching
`WorkbenchController`'s own convention exactly) + a thin `http.server`
dispatcher on top, same two-layer split as `workbench_v1.py`. Reuses,
doesn't reimplement: `tile_source_registry_v1` for the real library
panel (every kind, uniformly, thanks to `#485`/`#486`), each tile's own
real `place()`/`place_composed()` for the one authoritative validation,
`icm_v3`/`icm_v4` for real output (format auto-selected the same
backward-compatible way `#485`'s compiler output is). One real bug
caught -- the same self-registration-import gap `#486` already found
once, now confirmed a second time in a second consuming file, fixed
the same way. `tests/vm/test_tile_designer_v1.py`, 17 functions
(controller-only PLUS a real running HTTP server with real sockets),
zero regression, 322/322 (was 305). Full detail: `points.md` `#487`.

**Real, honest scope still open, stated plainly in the scope note:**
the HTML/JS page's own interactive polish (can't be verified in this
environment -- no live browser here); drag-to-move-by-mouse; loading
an existing ICM file back in for further editing; real-time neighbor
highlighting.

## Previous state (2026-08-24, composed-tile support for multi-kind sub-cells built and tested, see `points.md` #486)

**2026-08-24, closing #485's own deliberately-flagged gap: composed
(Tier-1) tiles can now mix sub-cell kinds.** `composed_tile_library_v1.
py`'s own `place_composed()` resolves a sub-cell of ANY tile kind
registered into `tile_source_registry_v1.py` now, not just
`super_tile_library`'s own Tier-0 primitives -- a new `_resolve_
subcell_leaf()` helper checks the same explicit-`library`-param
override the function has always supported, then falls through to the
generic registry. Return TYPE deliberately unchanged (still a flat
list, real backward compatibility -- confirmed by the full 44-test
pre-existing composed-tile suite passing with zero edits); only the
CONTENTS may now genuinely mix `v3.IcmV3Record` and `icm_v4.
DspWrapperRecord`, bucketed by real `isinstance()` one layer up in
`dsl_compiler_v1.py`. Two more hardcoded `super_tile_library`
references found and generalized the same way: `_resolve_tile_by_
name()` (define-time sub-cell validation) and `_param_names()`'s own
composed recursion -- the SECOND one found directly by the first real
DSL `define`-block test failing with a `KeyError`, not anticipated in
advance. New real registered example tile, `dsp_add_and_hold` (DSP
wrapper ADD -> RAM sink, one composed tile) -- proven both via direct
Python and through a real DSL `define` block, both driven end to end
through a live grid, correct IEEE-754 results confirmed (7.5 and 3.0
respectively). `tests/vm/test_composed_multi_kind_v1.py`, 4 functions,
zero regression, 305/305 (was 301). Full detail: `points.md` `#486`.

**Real, honest scope still open:** a Tile Designer / visual authoring
story for mixed-kind composed tiles. Extending the same registry
pattern to any future dedicated hardware class still costs exactly one
new library module + one import line in `dsl_compiler_v1.py`.

## Previous state (2026-08-24, real generic compiler hook built -- DSP wrapper tiles now placeable through the DSL, see `points.md` #485)

**2026-08-24, the real "hook, not rewrite" extension mechanism Alan
asked for directly.** New `nano/tile_source_registry_v1.py` -- a
tiny, deliberately narrow registry (`TileSource`: a library, a
`place_fn`, an output bucket name). New `nano/dsp_wrapper_tile_
library_v1.py` -- a real Tier-0-shaped tile library for the DSP
wrapper family (`dsp_add`/`dsp_sub`/`dsp_mul`/`dsp_ge`/`dsp_le`/
`dsp_neq`, `dsp_add` marked silicon-proven per `#472`), targeting
`icm_v4.DspWrapperRecord` with its own real resolver (DSP wrapper's
`a_dir`/`b_dir` are genuinely single, distinct directions, not a
fan-out mask like every super-cell core's own fields). Both this new
library AND `super_tile_library_v1.py` (one small, additive change)
now self-register into the registry. `dsl_compiler_v1.py`'s own real
changes are all GENERALIZATIONS -- it asks the registry generically,
never hardcodes a kind name anywhere except one import line for the
new library's self-registration side effect. A real DSL program
placing a DSP wrapper tile alongside a super tile now compiles end to
end, through the SAME unmodified `compile_source()` every other
program already uses, into a real, new `IcmV4File`; a program using no
DSP wrapper tiles produces the exact same `IcmV3File` as before --
confirmed backward-compatible with a dedicated test, not assumed.
`tests/vm/test_dsp_wrapper_tile_library_v1.py`, 10 functions, zero
regression, 301/301 (was 291). Full detail: `points.md` `#485`.

**Real, honest scope still open:** Tier-1 composed tiles (`define`)
remain super-tile-only sub-cells -- `place_composed()` still only
emits `IcmV3Record`s, so mixing a DSP wrapper into a `define` block
isn't supported yet, deliberately left untouched rather than
half-working. Extending this same registry pattern to any future
dedicated hardware class costs one new library module + one import
line in `dsl_compiler_v1.py`, nothing more.

## Previous state (2026-08-24, real ICM v4 mixed-cell format built and tested, see `points.md` #484)

**2026-08-24, ICM-level construction, explicitly WITHOUT the compiler
(Alan's own direct instruction -- the compiler's own tile library/
resolver doesn't know DSP wrappers exist yet, a real, separate,
not-yet-started upgrade).** New `nano/icm_v4.py`: a real, mixed-cell
ICM format -- ICM v3's own `IcmV3Record` (SUPER_LATCH super cells)
reused completely unmodified, alongside a new `DspWrapperRecord` kind
for the real, hardware-confirmed DSP wrapper family. New format
version (`icm-v4`, not a silent extension of `icm-v3`) because DSP
wrappers are a real, deliberate, separate hardware class (`#453`/
`#474`) an ICM v3 reader has no `core_select` value for -- silently
tolerating that would be exactly the unnoticed-drop risk this
codebase's own field-validation discipline already refuses elsewhere.
`build_grid()` is the honest current substitute for a real loader/
binder stage (stated as such in its own docstring): turns a saved ICM
v4 file directly into a live, running `SuperGrid` mixing real
`SuperCell`s and `DspWrapperCell`s, with an explicit position-
collision check. A real, saved DSP-wrapper-ADD-into-RAM-sink program
built, saved, hash-verified (both record kinds independently confirmed
tamper-caught by one combined hash), reloaded, and run through two
real `SuperGrid.tick()` calls -- correct IEEE-754 result (2.5+1.5=4.0)
confirmed arriving at the RAM sink. `tests/vm/test_icm_v4.py`, 6
functions, zero bugs found, zero regression, 291/291 (was 285). Full
detail: `points.md` `#484`.

**Real, honest scope still open:** the DSL/compiler upgrade itself
(teaching the tile library/resolver DSP wrappers exist, so a real
program could target ICM v4 instead of direct Python calls) remains
real, separate, unbuilt work -- deliberately out of scope here. A real
Tile Designer / placement-anchoring story for DSP wrappers specifically
also remains open.

## Previous state (2026-08-24, mixed-grid checkpointing built and tested, see `points.md` #483)

**2026-08-24, picking the paused thread back up.** Alan's own choice
(offered a shortlist of open threads, picked this one): full
mixed-grid checkpointing -- `SuperCell.checkpoint()`/`restore()`
(generic, `dataclasses.fields()`-driven across all ~30 fields/6 cores
+ delegated nano `CACell`, a deliberate contrast with `#480`'s own
hand-typed `DspWrapperCell` approach -- SuperCell's real field count
makes hand-typing real ongoing drift risk) plus `nano/mixed_grid_
checkpoint_v1.py` (`save_mixed_model`/`load_mixed_model`, a
`cell_class` tag dispatching each snapshot to `SuperCell` or
`DspWrapperCell` unmodified). Real, genuine three-cell mixed mid-flight
state (dsp + adder both half-fed, accumulator mid-count) checkpointed
together, wiped, reloaded, and confirmed both data-exact AND
functionally correct through a real, live `SuperGrid.tick()`
propagation across the reconstructed chain -- not just isolated field
comparison. `tests/vm/test_mixed_grid_checkpoint_v1.py`, zero bugs
found, zero regression, 285/285 (was 283). Full detail: `points.md`
`#483`. This closes the second of `#482`'s own two flagged next
pieces -- the other, ICM-level construction for DspWrapperCell (per
`#478`'s compiler-gap item 4), remains open.

## Previous state (2026-08-24, session close -- full five-tool pipeline architecture agreed, real VM-side DSP wrapper work started and going well, see `points.md` #477-#482)

**2026-08-24, real architectural planning session, followed by real
VM-side building.** Real, final five-tool pipeline agreed precisely
(`#479`): **Composer** (element choice -> `top.v`, needs MAN) ->
real Quartus build -> **Walker** (extracts real SHAPE after the `.sof`
is actually on the card) -> **Compiler** (program -> ICM, needs SHAPE
+ user tile library) and **VM** (free mode: no file, unconstrained; or
mirror mode: needs a real SHAPE file). **Tile Designer** is its own,
separate tool (not folded into Composer) for visually building
reusable models saved as ICM, usable in either VM mode. Composer and
Walker are the only two tools that ever touch real hardware/Quartus;
everything else is real, software-only work.

**`#478`'s own itemized real gap list** exists for both the card VM
and the compiler -- concrete, specific items, not vague, covering what
each still needs (a general extraction pipeline, closing `#451`'s
boundary-cell gap, the actual mirror software itself for the VM; DSP-
wrapper awareness, real placement-anchoring, type-safety tracking for
the compiler). Real, agreed priority: VM extensions FIRST, since they
have no real hardware dependency and are the genuine "easy win" of the
five tools.

**Real VM-side building started, three clean pieces done, going
well** (`#480`-`#482`): `DspWrapperCell` built (genuine IEEE-754
correctness via Python's own `struct` module -- actually MORE correct
than the RTL sim stubs, which deliberately skip real math to isolate
protocol timing), a real, honestly tick-based watchdog (same real
protective purpose as the hardware version, adapted for a VM with no
real wall-clock context), and a real checkpoint/freeze/save/wipe/
reload mechanism -- tested against genuine mid-flight state (not a
clean snapshot), confirmed both data-exact and functionally correct
on continuation, with real tamper detection reusing the same discipline
already established for ICM files. Zero regression on the full
existing 29-test VM suite throughout.

**Real, explicit pause point, Alan's own call:** picking this back up
later. Natural next pieces, not started: full mixed-grid checkpointing
(SuperCell + DspWrapperCell together), and ICM-level construction
(building a model from a real program/DSL rather than only direct
Python calls, per `#478`'s own compiler-gap item 4).

**Real, unchanged queue from before this thread, still open:**
`#451`'s SHAPE boundary-cell gap, `#448`'s burst-write opcode, the
exhaustive Tcl placement dump, `#430`'s items 3/5/6, the 9/27-way
scale family, testing driven cells' own data-path ports over JTAG,
the real hard-DSP-block IP path (deferred until real PCIe capability
is available), `#477`'s own noted future task (full per-file
documentation, standalone vs. as-a-core distinction).

## Previous state (2026-08-24, session close -- full DSP wrapper thread closed and documented, real hardware confirmed for ADD, see `points.md` #470-#476)

**2026-08-24, full DSP thread close-out.** Real, hardware-confirmed
DSP wrapper (`dsp_arith_wrapper_v1.v` OP="ADD") -- fire/ACK/re-arming
all correct on actual silicon (`#472`), real, precise cost (354.0
ALM/instance, `#473`), and two real findings that only showed up on
actual hardware, not sim: the real IP in use does NOT touch the card's
own 1,687 real DSP blocks (pure fabric-LUT soft logic, `#472`), and a
watchdog threshold sized for simulation genuinely false-trips on real,
JTAG-paced hardware -- real JTAG round-trip is milliseconds, not the
handful of cycles a sim-convenient value assumes (`#472`).
`dsp_compare_wrapper_v1.v` (GE/LE/NEQ) given the same real correction
as the arith side but remains sim-only, entity name a reasoned
placeholder pending real IP generation (`#475`). Full regression
across all five DSP testbenches: zero failures.

**Real documentation close-out** (`#476`): `dsp_wrapper_timing.md`
rewritten with the real, corrected numbers and both hardware-only
findings; `fpga/ip-reference/README.md` gained the real, generated
`alterafpf_add_single.qsys` and a note on the entity-naming lesson;
`CORES_AND_WRAPPERS_REFERENCE.md` gained a full, real DSP-wrapper
section matching its own established rigor. `fpga/README_FPGA.md`
flagged as real, significant, pre-existing documentation debt
(describes an entirely different, much older architecture) --
explicitly NOT fixed, out of scope for this close-out.

**Real architectural threads opened tonight, not built, captured for
later (`#474`):**
- The "math loop" reuse pattern -- one DSP wrapper instance can serve
  a whole chain's own multi-step computation via runtime `n`
  reconfiguration, already proven via the existing re-arming tests.
- Composer scope extension -- a real, earlier stage (file selection +
  top-generation) in front of `#387`'s own existing placement-review
  scope, plus a naming/date/revision convention for generated `.sof`
  builds.
- "LEGO for FPGA" (`#353`) explicitly spun off into its own future
  repo -- tonight's DSP wrapper is real, concrete proof of the
  mechanism `#353` left unsketched, generalized beyond compute
  (frequency generators, programmable filters named as real examples).

**Real, honest, explicitly deferred decision:** whether to chase the
real hard-DSP-block IP path (Native Floating Point DSP) is on hold
until real PCIe capability is available -- Alan's own explicit call
(`#475`).

**Real, unchanged queue from before this thread, still open:**
`#451`'s SHAPE boundary-cell gap, `#448`'s burst-write opcode, the
exhaustive Tcl placement dump, `#430`'s items 3/5/6, the 9/27-way
scale family, testing driven cells' own data-path ports over JTAG.

## Previous state (2026-08-24 -- real DSP wrapper correction APPLIED and verified, zero regression, see `points.md` #470)

**2026-08-24, real correction from `#469` actually applied to the
RTL.** `dsp_arith_wrapper_v1.v` fixed IN PLACE (its own real Quartus
build had genuinely FAILED, so there was no known-good state the
usual "clone, don't modify" rule needed to protect) -- now instantiates
the real, confirmed `altera_nios_custom_instr_floating_point_2_multi`
with its real port names, real `start`/`done` handshake, and real
per-operation `n` values (ADD=253, SUB=254, MUL=252). Full regression
across all five DSP testbenches: zero failures, checked with an
explicit `grep` for FAIL lines, not just "did it finish."

**Real, honest confirmation the earlier protocol-level design was
sound:** `tb_dsp_four_modes_v1`/`tb_top_dsp_chain_v1` needed NO code
changes at all to keep passing against the corrected wrapper -- only
the actual megafunction instantiation was ever wrong, not the
surrounding capture/fire/ack/watchdog logic.

**Real, honest scope still open, real next steps:**
1. `dsp_compare_wrapper_v1.v` (GE/LE/NEQ) NOT yet corrected -- still
   uses the old, wrong port convention; the real "combinational"
   sub-component (`..._floating_point_2_combi`) likely has a genuinely
   different, simpler port set (no start/done) that hasn't been
   confirmed against a real generated `.qsys` the way the arithmetic
   side now is.
2. `reset_req`'s own real direction/contract remains a stated,
   unconfirmed assumption.
3. **No real Quartus rebuild or real hardware test has happened yet
   for the corrected wrapper** -- this is the real, immediate next
   step whenever Alan is back at the Quartus machine.
4. Everything else from `#458`'s own real queue remains untouched:
   `#451`'s SHAPE boundary-cell gap, `#448`'s burst-write opcode, the
   exhaustive Tcl placement dump, `#430`'s items 3/5/6, the 9/27-way
   scale family, testing driven cells' own data-path ports over JTAG.

## Previous state (2026-08-23, session close -- real DSP wrapper/watchdog built, real IP correction found late, see `points.md` #459-#469)

**2026-08-23, late session, real priority for next time:** `#469` --
the real IP Alan actually has is `altera_nios_custom_instr_floating_
point_2_multi` (Nios II Custom Instruction), NOT `alterafpf_add_single`
(`#462`'s own research was for a real but unavailable IP family).
Real, confirmed port names (`clk`/`clk_en`/`dataa`/`datab`/`n`/`reset`/
`reset_req`/`start`/`done`/`result`), a real `start`/`done` handshake
(replaces the counter-based wait entirely), and a real per-operation
`n`-select table from Intel's own docs (ADD=253/5cyc, SUB=254/5cyc,
MUL=252/4cyc, GE=228/1cyc -- all different from `#462`'s superseded
3-cycle assumption). `reset_req`'s own real contract is still unknown.
**`dsp_arith_wrapper_v1.v`/`dsp_compare_wrapper_v1.v` need real rework
with this data -- start here next session, before anything else.**

Also built and sim-verified this session, all still real and valid
independent of the IP-name correction (only the DSP megafunction
instantiation itself needs fixing, not the surrounding protocol logic):
`watchdog_v1.v` (real, programmable, `#464`), wired into the DSP
wrapper (`#465`), all four DSP modes structurally built (`#467`), a
full DSP chain bring-up build with real host bridge + Tcl harness
(`#468`) -- all of this needs re-verification once the real megafunction
port fix lands, not assumed to still pass unchanged.

## Previous state (2026-08-23, earlier -- MAN/SHAPE/placement tooling built and tested, physical placement gap closed, real queue set for next session, see `points.md` #447-#458)

**2026-08-23, session close, `#458`.** Real, working artifacts built
this session: `tools/shape_extract_v1.py` (logical adjacency, cell-role
classification, port availability -- confirmed byte-identical on
Alan's own machine), `docs/man/mustang-f100-a10.man.json` (real device/
board facts, cross-checked against a real `.pin` file), `tools/
placement_extract_v1.py` (real per-instance bounding boxes for all 13
`v3` cells, merged from Quartus's own Control Signals report -- found
only after two real, owned misses on Back-Annotate Assignments).

**A real DSP-integration design thread** (`#453`): a custom float
format, a real correction to Claude's own first framing (pipeline
latency needs no new shell mechanism -- the event-driven handshake and
sentinel's own event-count logic already tolerate it), and a chain
watchdog composed from zero new cell types (counter + comparator +
existing status path, with a real reset-on-activity requirement). One
unverified claim in it (Arria 10's hardened IEEE-754 DSP mode) needs
checking against real docs before any RTL starts.

**One real thread explicitly abandoned for tonight, not silently
dropped:** an exhaustive per-register Tcl placement dump ran to real
completion via `quartus_sta` but matched zero registers -- a genuine,
unresolved Tcl/collection-semantics question, left for a future
hands-on session rather than a fourth blind script.

**Real, honest queue for next session, previous state below still
relevant, see `#458`'s own full list:**
1. `#451`'s SHAPE boundary-cell dataflow-trace gap.
2. `#448`'s burst-write JTAG opcode (scoped, real numbers ready).
3. The exhaustive Tcl placement dump, worked through properly.
4. `#453`'s DSP float wrapper + watchdog, pending the IEEE-754 check.
5. Carried forward: `#430`'s items 3/5/6, the 9/27-way scale family,
   testing driven cells' own data-path ports over JTAG.

## Previous state (2026-08-23, evening session, planning/discussion only, see `points.md` #447-#453)

**2026-08-23, evening session, planning/discussion only -- a full,
connected arc, ending with a real correction found mid-thread.**

1. **`#447`:** DDR4 (when built) connects via BRAM as an intermediate
   buffer, not a direct fabric link. Real reasoning, no RTL.
2. **`#448`:** real per-command JTAG overhead measured directly from
   `#445`'s own hardware data (~6.5ms/command) -- the current bridge is
   a bring-up tool, not remotely viable for GB-scale staging while
   PCIe remains unavailable. A burst-write opcode scoped as the real
   next build, not yet started.
3. **`#449`/`#450`:** the MAN (per-card-model capability spec) vs SHAPE
   (per-compiled-design adjacency) distinction resolved. The FIRST
   real MAN file built (`docs/man/mustang-f100-a10.man.json`),
   populated from already-confirmed real data across this project's
   history. A real surprise found: PCIe WAS genuinely confirmed
   working on real hardware back in July, but that link belongs to the
   now-archived architecture, not the active one.
4. **`#451`/`#452`:** the first real SHAPE extractor built
   (`tools/shape_extract_v1.py`), two real bugs found and fixed by
   actually running it (not by inspection), then extended with cell-
   role classification (`programmable_substrate`/`host_interface`/
   `connection_point`) per the ALREADY-DECIDED `#253`/`#293` taxonomy.
   One real, honest limitation stands: it can't yet trace adjacency
   through registered/combinational logic, so it misses `#431`'s own
   original BRAM-boundary-cell case -- documented precisely, not
   glossed over.
5. **`#453`:** a full DSP-integration design thread -- a custom float
   format idea connecting to the old MIF precedent (`#379`) and the
   already-decided DSP wrapper conclusion (`#380`); a real correction
   Claude made and then had corrected by Alan (pipeline latency does
   NOT need a new shell mechanism -- the existing event-driven
   handshake and the sentinel's own event-count logic already tolerate
   it, confirmed directly against the real RTL); the DSP wrapper
   reduces to two already-proven RAM cells with the real hard DSP IP
   in the glue between them; a chain watchdog composed entirely from
   already-built cells (counter + comparator + signal), with a real,
   essential reset-on-activity requirement so it's a genuine watchdog,
   not a false-positive machine.

**Real, honest open items for next session:**
- The IEEE-754/hardened-Arria-10-DSP-floating-point-mode claim in
  `#453` needs real verification against Intel documentation before
  it's a design commitment (same discipline the fixed-point DSP chain
  format already got).
- `#448`'s burst-write opcode -- scoped, not built.
- `#451`'s dataflow-trace extension to SHAPE extraction (closing the
  BRAM-boundary-cell gap) -- scoped, not built.
- `#450`'s MAN file needs a real `.pin`-file-generator pass
  (`#28`/`#29`'s own canonical method) to replace the hand-assembled
  device-half data.
- Everything from the prior session's own close (`#446`) not yet
  touched tonight: `#430`'s queue items 3 (Composer)/5 (loader
  revisit, now partially addressed by `#449`-`#452`)/6 (VM reorder,
  still needing Alan's own scope clarification), extending host-driven
  operation to the 9/27-way scale family, testing driven cells' own
  data-path ports over JTAG.

## Previous state (2026-08-23, earlier -- real JTAG throughput measured and found unviable at GB scale while PCIe is unavailable; BRAM-as-buffer for future DDR4 decided; burst-write scoped as next real build; see `points.md` #447-#448)

**2026-08-23, real architectural planning session (no RTL today).**
Two real threads:

1. **`#447`: DDR4 (when built) connects via BRAM as an intermediate
   buffer, not a direct fabric link.** Real reasoning: protocol
   mismatch (DDR4/EMIF is burst-oriented, the fabric's event model
   needs BRAM's short deterministic latency), isolation of complexity
   (fabric-facing side never changes, only a new burst-fill/DMA stage
   is needed). DDR4 itself remains completely unbuilt (`#329`'s gap
   stands).

2. **`#448`: real per-command JTAG overhead measured directly from
   `#445`'s own hardware data -- ~6.53ms/command, ~0.75 KB/s
   effective, ~32.5 days for 2GB at the current one-word-per-
   transaction bridge protocol.** This is six orders of magnitude off
   an earlier PCIe-based back-of-envelope estimate (2.5 sec/4GB) --
   because PCIe isn't actually available yet for this architecture at
   all. The current JTAG bridge is a bring-up/correctness tool ONLY,
   not a bulk data path. A burst-write opcode is SCOPED (pack N words
   into one wider SOURCE register, one JTAG round-trip instead of N)
   with real throughput projections -- meaningful improvement (10-100x
   depending on batch size) but a real, honest ceiling well short of
   PCIe-class throughput even at impractically wide batches. NOT YET
   BUILT -- a real decision on timing is still open.

**Real confirmation, not new:** Alan's own plan to test PCIe on a
known-good dedicated machine (Dell Precision 5820) before assuming any
future PCIe ceiling is this project's fault directly confirms `#330`'s
own already-logged finding (PCIe throughput is a host-motherboard
property, not the card).

**NEXT, real open decision:** build the burst-write opcode now (a
concrete, scoped, buildable RTL task) or defer to a future session.
Also still open from the prior session's own close: `#430`'s remaining
queue items (3: Composer; 5: loader revisit; 6: VM reorder, still
needing Alan's own scope clarification), extending host-driven
operation to the 9/27-way scale family, and testing the driven cells'
own data-path ports over JTAG.

## Previous state (2026-08-22, session close -- real queue set for next session, see `points.md` #446)

**2026-08-22, session close.** A big real session: `#436`/`#437`
(collector_relay_v1 wired in as v2, real Quartus numbers), `#438`-
`#440` (real critical path traced and confirmed via Fitter data,
generalized to a structural family), `#441`/`#442` (FIRST real
host-driven hardware in this project's history -- JTAG bridge for
real BRAM read/write + ICM loading, confirmed on real silicon first
try), `#443`-`#445` (that bridge extended to the FULL 3-chain
mechanism as v3 -- sim-proven, one real hardware run initially failed
due to a forgotten reprogram, then confirmed FULLY correct on real
silicon once actually programmed).

**`#430`'s own queue, real state per `#446`:** item 2 (real JTAG
bring-up) is substantively done at both the isolated-cell and full-
mechanism scales. Real, honest remaining gaps: driven cells' own
data-path ports beyond the configs already tested remain untested over
JTAG; the 9-way/27-way scale family hasn't been extended to host-driven
operation. Items 3 (Composer), 5 (loader revisit), and 6 (VM reorder,
still needing Alan's own scope clarification) remain the real
untouched queue.

**NEXT SESSION: read this file, then `points.md` #446 for the full
real queue. Alan's own real choice at session start: continue host-
bridge work (data-path testing, or the 9/27-way scale family), or move
to items 3/5/6.**

## Previous state (2026-08-22, earlier -- REAL SUCCESS: full 3-chain host-driven mechanism confirmed on real silicon, #444's diagnosis retired as a mundane forgot-to-reprogram slip, see `points.md` #445)

**2026-08-22, real success, `#444` retired.** The card simply hadn't
been reprogrammed after the last compile -- the earlier "failure" was
the fabric running a stale/unrelated bitstream, not v3 at all. Once
actually programmed, EVERY checkpoint matched exactly: `cmd_count`
tracked real commands with zero spurious pulses (19 before rounds, 31
after, both exact), `q_data_out_n` produced the exact expected
1,1,1,2,2,2,3,3,3,4,4,4 sequence across all 12 real rounds, and the 3
chains reported completion in the exact right round-robin order
(`points.md` #445).

**`#430`'s own queue item 2 (real JTAG bring-up) now has its full-
mechanism half genuinely proven on real hardware.** Combined with
`#442`'s own earlier single-cell confirmation, both real capabilities
Alan originally asked for (real BRAM read/write, real ICM loading) are
now confirmed working at BOTH the isolated-cell scale and the full
3-chain mechanism scale.

**Real, honest scope still open:** the driven cells' own data-path
ports beyond this specific config remain untested over JTAG; the
9-way/27-way scale family (`#416`/`#425`) hasn't been extended to
host-driven operation; the real ~10x ALM jump (314->3,218) is now
understood as the genuine, legitimate cost of a much wider ISSP bridge
(249 total bits of real scan/sync circuitry) -- real, not a defect,
but a reminder that debug/JTAG bridges should be stripped for any
final production design, per this project's own already-stated
principle.

**NEXT, real options, not yet decided:** move to `#430`'s remaining
queue items (3: Composer: 5: loader revisit; 6: VM reorder, still
needing Alan's own scope clarification); extend host-driven operation
to the 9-way/27-way scale family; or test the driven cells' own
data-path ports over JTAG (not yet done at either bridge scale).

## Previous state (2026-08-22, earlier -- real hardware run for v3 FAILED, root cause not yet confirmed, real IP-generation checklist given to Alan, see `points.md` #444)

**2026-08-22, v3's real hardware run FAILED -- unlike #442's clean
single-cell success.** Every one of 12 real ADVANCE-driven rounds
produced wrong results; `free_cycle` stuck at exactly 0 across every
poll while `cmd_count` visibly (but wrongly) increments; `q_data_out_n`
reads back as large, essentially random 32-bit garbage (`points.md`
#444).

**Real diagnosis, NOT a fix:** the failure signature (a stuck TOP
field + a garbage-inflated MIDDLE field, on this project's widest-ever
ISSP probe at 158 bits) points at the real IP-generation/hardware-
integration layer, not RTL logic -- the exact same counter pattern
already worked correctly on real silicon at smaller widths (#442).
Sim (`#443`) already proves the RTL logic itself correct for this
exact bit layout -- NOTHING WAS CHANGED in the RTL based on this
failure, per this project's own "isolate the variable" discipline.

**Real, concrete checklist for Alan, not yet confirmed either way:**
1. Confirm the real `issp_sentinel_gather` IP was generated with EXACTLY
   Source width=91, Probe width=158 -- not a rounded/default value.
2. Confirm "Enable source synchronization registers" was actually
   checked when generating that IP.
3. The unexplained ~10x ALM jump (314 -> 3,218) is a related, flagged,
   unresolved data point -- possibly consistent with an accidentally
   much-wider-than-158 real probe.

**NEXT: Alan re-checks the real IP Catalog settings and reports back.
No RTL work should proceed on this thread until that's resolved one
way or the other.**

## Previous state (2026-08-22, earlier -- #430's queue item 2 extended to the full v2 mechanism, sim-proven, see `points.md` #443)

**2026-08-22, queue item 2 extended: real JTAG host bridge now drives
the FULL 3-chain mechanism, not just one isolated cell.** `top_
sentinel_gather_shared_bram_v3.v` -- cloned from v2 (`#437`'s own
proven 314 ALM/179.99MHz baseline, untouched), self-test FSM replaced
entirely by `host_bridge_sentinel_gather_v1.v` (`points.md` #443).
Extends `#441`/`#442`'s own real-hardware-confirmed single-cell bridge
pattern to all 4 configurable cells (H1/H2/H3/QUEUE) plus real
per-chain UNFREEZE and the real per-round ADVANCE the mechanism needs
(confirmed directly against the RTL: it does NOT free-run once armed).

Sim-verified clean end to end: all 4 cells configured, 12 BRAM
addresses preloaded, 3 chains unfrozen, 12 real ADVANCE-driven rounds
all produced the exact correct result, deterministic, zero regression
on v2 and on the single-cell bridge.

**Two real bugs caught and fixed by actually running code, not by
inspection:** a wrong expected-value formula in the testbench
(`round_idx % 4` instead of v2's own proven `round_idx / 3`), and
wrong SUPER_LATCH nibble ordering in the Tcl harness's own CFG_H1/H2/H3
values (caught by independently recomputing in Python against the
RTL's real concatenation order). Both fixed and re-verified.

**Real, honest gap, NOT resolved this session:** the actual Quartus
build and real JTAG exercise for v3 haven't been run -- needs Alan's
own machine. `Unicell-Q-sentinel-gather-shared-bram-v3.qsf`/`.sdc` and
`fpga/host_bridge_sentinel_gather.tcl` are ready. **NEXT: generate the
real `issp_sentinel_gather` IP (Source=91b, Probe=158b), build,
program, then run `quartus_stp -t host_bridge_sentinel_gather.tcl`.**

## Previous state (2026-08-22, earlier -- REAL HARDWARE CONFIRMED for the JTAG host bridge, first try, zero failures, see `points.md` #442)

**2026-08-22, real hardware success: the FIRST genuinely host-driven
hardware confirmation in this project's own history.** `#441`'s own
JTAG host bridge (`host_bridge_bram_icm_v1.v`) ran against the real
programmed card and every single check passed, zero failures,
matching the sim-predicted sequence exactly (`points.md` #442): real
BRAM write-then-read at two distinct addresses, `write_done` confirmed,
two real ICM loads (SEL_ACC then SEL_LATCH) each confirmed via
`status_core_select` readback, `cmd_count` exactly correct. Fmax on
`clk_div` measured at 212.27 MHz -- an 8.49x margin over the real
25MHz requirement.

A real, honest, flagged-not-alarmed observation: 3 unconstrained input
ports / 1 unconstrained output port showed in the report -- almost
certainly the device's own reserved JTAG boundary-scan pins (standard
for any ISSP-based design), not independently confirmed by name, not
treated as a real concern.

**`#430`'s own queue item 2 (real JTAG bring-up) now has a real,
working, first-slice foundation.** The deliberate scope from `#441`
(one isolated BRAM + one isolated cell) remains real and honest --
wiring this same bridge pattern into the full 3-chain v2 sentinel+
gather mechanism is real, separate, NOT YET STARTED integration work.
**NEXT, real options, not yet decided:** extend this bridge (or build a
similar one) to drive the full v2 mechanism directly; test the driven
cell's own data-path ports over JTAG (this build only proved config +
BRAM, not a full data round trip through the cell); or move to a
different queue item (`#430`'s items 3/5/6 -- Composer, loader revisit,
VM reorder).

## Previous state (2026-08-22, earlier -- real JTAG bring-up started, #430's queue item 2 first slice, see `points.md` #441)

**2026-08-22, queue item 2 started: the FIRST real host-driven hardware
in this project's own history.** `host_bridge_bram_icm_v1.v` -- a real
JTAG (ISSP) bridge covering exactly what Alan asked for: real BRAM
read/write, and real ICM (SUPER_LATCH) loading into the substrate
(`points.md` #441). Scoped deliberately small per this project's own
"smallest reproducible case first" discipline: drives ONE shared BRAM
and ONE `unicell_super_v1` cell directly, proving the two raw channels
work in isolation BEFORE wiring a host bridge into the full 3-chain v2
mechanism (real, separate, later integration work, not started).

Sim-verified clean: real BRAM write-then-read at two addresses, two
real ICM loads (SEL_ACC then SEL_LATCH) both confirmed via
`status_core_select` readback, deterministic, zero regression on the
existing `sentinel_issp_bridge_v1.v` testbench.

**A real bug caught before it ever reached hardware:** the first draft
of the Tcl harness's bit-packing (`hb_src_fields`) was WRONG -- caught
by actually running it in `tclsh` and hand-verifying every bit, not by
inspection. Rebuilt with real bit-shift arithmetic, round-trip tested
against an all-ones case across every field before being trusted.

**Real, honest gap, NOT resolved this session:** the actual Quartus
build and real JTAG exercise on Alan's own machine haven't been run.
`Unicell-Q-bram-icm-hostbridge-v1.qsf`/`.sdc` and `fpga/host_bridge_
bram_icm.tcl` are ready. **NEXT: generate the real `issp_bram_icm` IP
(Source=91b, Probe=112b) per the top file's own header instructions,
build, program, then run `quartus_stp -t host_bridge_bram_icm.tcl` --
this is the actual remaining half of queue item 2's first slice.**

## Previous state (2026-08-22, earlier -- real critical path found and traced, correcting #437's own earlier guess, see `points.md` #438-#440)

**2026-08-22, #437's own Fmax-cause hypothesis CORRECTED on real
evidence, not defended.** Alan's own real Report Timing data for v2
identified the actual critical path: `sentinel_counter_v1:SENT1|
diff[N]` -> `unicell_super_v1:H1|accumulator_cell_v1:CORE_ACC|
out_buffer[10]` (`points.md` #438) -- NOT `collector_relay_v1.v`'s own
logic or the shared-BRAM arbitration as first guessed. Traced through
the real RTL: `SENT1`'s own wide `diff==0` comparator drives `h1_freeze`
into H1's `freeze_in`, gating `capture_inc`/`capture_dec`, feeding a
real 32-bit adder that loads `out_buffer` -- landing on its own worst
carry-chain bit.

**The real, important confirmation:** `sentinel_counter_v1.v`/
`accumulator_cell_v1.v`/`unicell_super_v1.v` are all UNCHANGED by the
`collector_relay_v1` swap (zero diff, checked directly) -- this path
pre-dates v2's own work entirely. The small Fmax delta (`#437`) is most
likely a placement/routing artifact of the fitter placing a different,
smaller design, not a new logical bottleneck from the collector swap.
Not fully confirmed without v1's own Report Timing for direct
comparison -- a real, optional, low-priority item if ever worth
pinning down.

**`#430`'s own queue, unchanged from last update -- item 1 fully
closed (`#436`/`#437`/`#438`).** Next: item 2 (real JTAG bring-up) per
Alan's own choice, or items 5/6 (loader revisit / VM reorder, the
latter still needing Alan's own scope clarification).

## Previous state (2026-08-22, earlier -- real Quartus numbers for v2 in, #430's queue item 1 CLOSED, see `points.md` #437)

**2026-08-22, queue item 1 CLOSED with a real, honest, non-obvious
result.** `#436`'s v2 build (`collector_relay_v1` replacing the
`unicell_super_v1` shell + `cell_command_sequencer_v1` pair) now has
real Quartus numbers from Alan's own build (`points.md` #437): **314
ALM, 179.99 MHz** vs v1's own #426 baseline of 347 ALM / 188.86 MHz --
a real **-33 ALM (-9.51%)** reduction, but ALSO a real **-8.87 MHz
(-4.70%)** Fmax reduction. Both true simultaneously, neither forced to
net out. Still a genuine 7.2x margin over the real 25MHz requirement
(down from v1's own 7.55x) -- not a concern at this scale.

The per-instance data shows a much larger standalone saving
(`collector_relay_v1` costs 34.5 ALM vs the old subsystem's 100+ ALM)
than the whole design's -33 ALM delta -- reconciled via `#429`'s own
already-documented toolchain behavior (Quartus packs/shares logic
across entity boundaries), not a new mystery. The Fmax drop's own
cause is a stated hypothesis (critical path likely shifted into
`collector_relay_v1`'s own combinational logic or the shared-BRAM
arbitration), NOT confirmed via Report Timing/Chip Planner -- flagged
as real, open, low-priority given the comfortable margin still held.

**`#430`'s own queue, updated:**
1. ~~Wire `collector_relay_v1.v` in, get real Quartus numbers~~ --
   DONE (`#436`/`#437`).
2. Roadmap item (c): real JTAG bring-up, testing data in/out on the
   actual card (`#421`).
3. Roadmap item (d): Composer (rests on item (b)'s settled shape).
4. More documentation detail (ongoing discipline).
5. A revisit to the loader mechanism (`#431`'s own idea -- BRAM
   interface boundary cells, sentinel placement as the likely
   derivation mechanism).
6. A reorder on the VM (Alan's own words, "almost there" -- scope not
   yet stated, needs clarification at session start).

**Optional, low-priority, not on the numbered queue:** a real Report
Timing/Chip Planner pass on v2 to confirm where the new critical path
actually sits, if/when timing margin becomes genuinely tight at larger
scale (Level 9/27, `#416`/`#425`).

## Previous state (2026-08-22, earlier -- collector_relay_v1 wired into shared-BRAM top-level as v2, sim-proven, Quartus project prepared, see `points.md` #436)

**2026-08-22, continuing session, queue item 1 in progress.** Per
`#430`'s own ordered queue, item 1: `collector_relay_v1.v` (#428) wired
into the shared-BRAM sentinel+gather mechanism, replacing the general-
purpose `unicell_super_v1` shell + `cell_command_sequencer_v1:SEQ` pair
in the COLLECTOR role (`points.md` #436). Cloned to
`top_sentinel_gather_shared_bram_v2.v` from #426's own proven v1 (left
completely untouched) after a real mid-session process correction --
the swap was initially drafted directly into v1, caught as a violation
of this project's own "never modify a proven file in place" rule
before anything was committed, and fixed by restoring v1 from git
history first.

**Real design consequence:** dropping the sequencer means the
round-robin index it used to own is now a trivial local counter
(`active_dir_idx`), advanced by the collector's own real fire+ack
handshake completing rather than a separate programming protocol.
Sim-verified clean: all 12 rounds correct, deterministic across repeat
runs, zero regression on both v1 (re-run unchanged, still passes) and
`collector_relay_v1.v`'s own standalone testbench.

**Real, honest gap, NOT resolved this session:** the actual Quartus
build for v2 hasn't been run -- Quartus is node-locked to Alan's own
machine, not available in the sandbox. `Unicell-Q-sentinel-gather-
shared-bram-v2.qsf`/`.sdc` are prepared and ready. **NEXT: run the real
Quartus build for v2, report the real ALM/Fmax numbers back for
logging -- this is the actual remaining half of #430's own queue item
1.**

## Previous state (2026-08-22, session close, real next-session queue set, see `points.md` #429)

**2026-08-22, session close, real next-session queue (Alan's own
ordering, logged before drift per this project's own standing
discipline).** Real progress this session: `#425` fixed the Level 1
scale-family bug; `#426` got real Quartus numbers for the shared-BRAM
mechanism (347 ALM, 188.86 MHz); `#427` established a real principle
(the BRAM interface is dedicated one-time infrastructure, not part of
the user-programmable playing field, so it shouldn't pay the super
carrier shell's own reconfigurability tax); `#428` built and sim-
proved `collector_relay_v1.v` (a dedicated, non-shell-wrapped combiner
replacing nano+sequencer in the collector's own role) per that
principle; `#429` got real Quartus numbers for the v2 super carrier
shell with `SEL_SEQ` added (267 ALM, 207.3 MHz, a real +34.2 ALM shell-
level delta once test-FSM growth is correctly excluded).

**The real, ordered queue for next session, Alan's own list, not
started yet:**
1. Wire `collector_relay_v1.v` into `top_sentinel_gather_shared_bram_
   v1.v` in place of the nano-based `COLLECTOR` + `cell_command_
   sequencer_v1:SEQ`, get a real end-to-end sim result, then a third
   Quartus number for the real savings (`#428`'s own stated next step).
2. Roadmap item (c): real JTAG bring-up, testing data in/out on the
   actual card (`#421`).
3. Roadmap item (d): Composer, which rests on the core system's own
   settled shape from item (b) (`#421`/`#422`'s own explicit
   dependency note).
4. More documentation detail (item (e), the ongoing recurring
   discipline, not a one-time step).
5. **A revisit to the loader mechanism** -- Alan's own framing, "sort
   need to go backwards a bit" -- a deliberate look-back at the
   already-designed anchor-first seeded graph embedding / DSP
   placement loader concept (captured in memory, not yet cross-checked
   against this session's own real RTL progress) before building
   forward further.
6. **A reorder on the VM** -- Alan's own words, "almost there" -- real,
   specific scope not yet stated in this session's own record; needs
   Alan's own clarification at the start of next session before
   picking this up.

## Previous state (2026-08-20 -- docs synced against #410-#416; Level 1 of the scale family in progress, see `points.md` #416)

**2026-08-20, docs sync.** `docs/stripped-cell/design-notes/
ram_interface_collector_mechanism.md` (the authoritative doc for this
whole thread since `#381`) extended with the real `#410`-`#416` work:
the sentinel-integration bugs and fixes, the shared-BRAM architectural
correction (`#412`) and redesign (`#413`-`#415`), the real "data in
then confirm" readiness principle, and the scale-family plan
(1/3/9/27 chains). Also reconciled a real tension the doc itself had
been carrying: `#408`'s later closure of `#301`/`#302` doesn't
contradict the doc's own earlier "still genuinely unbuilt" section on
the real BRAM-read-result-delivery stage -- both are true, about
different things; `#408` is a real design constraint to build that
stage AGAINST, not proof it's already handled. A real, honest gap
stated explicitly for the first time: NONE of `#410`-`#416` exists in
the Python VM (`nano/unicell_super_automaton_v1.py` has zero
representation of `sentinel_counter_v1` or shared-BRAM arbitration,
checked directly) -- every proof so far is RTL/sim-only.

Also corrected this session: FlowTrix and the "UniCell Security
Module" are NOT current active-line items -- both live in
`current/PLAN.md`'s own stale, full-cell-era content (that file's own
header explicitly flags it as predating the current stripped/nano
work). FlowTrix is additionally closed on the current substrate
(`#371`/`#384`, the whole TRIX domain family concluded not viable).
Multi-card infrastructure IS genuine current-line work (`#325`), just
hardware-gated (needs a second physical machine), not full-cell
leftover -- worth keeping straight from the other two.

**2026-08-20, shared-BRAM mechanism passes clean.** `top_sentinel_
gather_shared_bram_v1.v` -- the real, correctly-architected shared-port
BRAM read mechanism (`#412`'s own correction: ONE shared read port,
arbitrated by reusing the existing round-robin gating, not one
memory per chain) -- now passes with zero errors, deterministic across
repeat runs, zero regression on both proven predecessors (`points.md`
#415). Real per-chain block preload (100/200/300 + offset) genuinely
read back and verified correct.

**The real fix, precisely diagnosed by Alan before it was built, not
guessed at:** a chain's own readiness (visible to the collector) was
becoming true the SAME cycle its shared-BRAM read was issued, not
after that read completed -- exposing a stale or default value instead
of the real one. Alan's own framing, confirmed correct by testing:
"the sequence should be based on actual data in the latch... data in
then confirm, not ready and waiting confirm then capture." Fixed with
`h*_fresh`, a PER-ROUND freshness flag (not the earlier, insufficient
one-time `h*_primed` flag) gating each chain's own readiness directly.
A related bug in this file's own verification logic (comparing a
read's data against an ALREADY-overwritten address register) was also
found and fixed, using the same latching technique already proven for
`read_owner` earlier in this same debugging arc.

**2026-08-20, scale family started, Level 1 in progress
(`points.md` #416).** Real architecture confirmed: every level of a
1/3/9/27-chain family shares the same per-chain building block,
differing only in arbitration depth (0/1/2/3 levels respectively).
Level 1 (trivial, no arbitration needed) hit one real wiring bug
(fixed: a config/topology mismatch) and a second, different bug found
and precisely located but NOT resolved (accumulator count sticks one
short of a full wrap; freeze asserts before the real final capture
completes). Stopped deliberately after an over-long diagnostic session
flooded far more trace output than intended -- a real lesson logged:
narrow the diagnostic window BEFORE running it. Levels 9 and 27 not
started.

**Real, honest remaining scope, current as of this sync:** all chain
proofs so far use synthetic, self-preloaded data (no genuinely
external BRAM source yet); the real host reload/JTAG round trip is
still not built (self-test FSM stands in for it); no Quartus build
attempted for any file in the `#410`-`#416` thread. The 27-leaf
hierarchical tree (`#402`, VM-proven only) remains the eventual target
once the scale family's own Level 9 proves the two-level arbitration
pattern works.

## Previous state (2026-08-19 -- sentinel+gather integration proven with synthetic data, see `points.md` #410)

**2026-08-19, sentinel+gather integration.** First real, sim-verified
proof that `#279`'s FULL SENTINEL SYSTEM (`sentinel_counter_v1.v`,
standalone-proven at `#281`, never before wired to a real chain) and
the header/collector/queue gather mechanism (`#397`/`#403`/`#404`/
`#406`/`#407`, Quartus-confirmed) work TOGETHER (`points.md` #410,
`tests/fpga/tb_top_sentinel_gather_v1.v`, all 12 rounds correct,
deterministic, zero regression on both proven predecessors). 3 real
accumulator chains (running-count work, not just relay), each with its
own independent sentinel, each freezing on its own local block's wrap
without waiting on the others.

**A real architectural bug found and fixed on Alan's own direct
diagnosis** (his own words: "the order should be data in, advances
count, counter... say i have reached my limit, thus is frozen... the
data now moves to the head cell of the chain"): the counter's own
freeze (stop counting, immediate) and the accumulator's own freeze
(stop OFFERING what it holds) had been wrongly conflated into one
signal, stranding the wrap-triggering final value -- captured
correctly, but never offered. Fixed by driving the accumulator's own
`freeze_in` from `results_ready_flag` (existing sentinel output, no new
ports) instead of `freeze_out` directly -- only freezing the
accumulator once the final value's own delivery is confirmed complete.

**Real, honest scope:** all 3 chains use identical block shape in this
first proof; the real host reload/JTAG round trip is not built (self-
test FSM stands in for it); no real BRAM read yet (address value
stands in as data, a synthetic source); no Quartus build yet for this
file. `#409`'s block-partitioned addressing folds in naturally once
real BRAM addressing replaces the synthetic stand-in.

**NEXT, real options, not yet decided:** real BRAM read side; real
host/JTAG reload round trip; scale from 3 chains to the full 27-leaf
tree (`#402`'s VM-proven shape), now informed by a real, working
sentinel-per-chain pattern.

## Previous state (2026-08-19, earlier -- real Quartus size/timing result for the flat gather mechanism)

**2026-08-19, session close.** Real work this session, in order:
1. Full 27-leaf (3x3x3) hierarchical collector tree proven at VM level
   for the first time (`#402`).
2. First real, self-contained, Quartus-ready top-level for the flat
   3-header collector mechanism built, debugged (5 real bugs found and
   fixed, `#403`/`#404`/`#406`), and Quartus-CONFIRMED on real silicon
   numbers: **274 ALM, 235.96 MHz vs 25 MHz requirement, 0 DSP/BRAM/
   HSSI/PLL** (`#407`). Corrects the design note's own earlier rough
   "~180 ALM/chain" placeholder with real, measured data.
3. `#301`'s stale-data hazard and `#302`'s write-exceeds-read worry
   both re-examined against the real, now-proven RTL and genuinely
   closed -- both fall out of the standing "offer stays stable until
   acked" discipline every core in this project already follows, not a
   new fix (`#408`). Alan's own precise framing of WHY, worth
   remembering as a standing design principle: "the control is handed
   to the chain, not the BRAM side."
4. A real simplification captured for the next round, not yet built:
   **block-partitioned (not interleaved) addressing** -- each chain
   owns a fixed, contiguous address range with a trivial local
   increment-and-wrap counter; "true randomness" falls out of the
   partition itself, not per-cycle computed addressing. The real
   remaining complexity sits in the DISPERSION mechanism (assigning
   each chain its own block), not per-chain addressing logic (`#409`).

**NEXT, in order:** the 27-leaf tree in real RTL (extending `#397`'s
proven flat testbench to a genuine 3-level tree of real instances,
matching `#402`'s own VM-proven shape) -- the one clear remaining piece
of item 7 (memory functions) on the standing priority list (`#371`).
Block-partitioned addressing (`#409`) is a real design direction to
fold in when that work resumes. Item 8 (the Composer) remains last,
not started.

## Previous state (2026-08-19, earlier -- first real Quartus build result)

**2026-08-19, later:** Per Alan's request for real Quartus size/timing
data, built `fpga/verilog/top_collector_mechanism_v1.v` -- the first
autonomous (no host driving it), self-contained top-level for the
header/collector/command/queue RAM-interface mechanism (`#381`/`#382`/
`#390`/`#395`/`#396`/`#397`), targeting the flat 3-header case (the
smallest RTL-proven unit). Sim-verified clean via
`tests/fpga/tb_top_collector_mechanism_v1.v` (iverilog) -- deterministic
across repeat runs, zero regression against `#397`'s own proven
testbench and the full 277-test VM suite. Five real RTL bugs found and
fixed along the way (`points.md` #403): config ordering, ambiguous
`seq_index` gating, a "drop readiness immediately on fire" race solved
twice, a real Verilog width-truncation bug, and a genuine
drain/reprogram/capture ordering inversion. `fpga/quartus/Unicell-Q-
collector-mechanism-v1.qsf` + `top_collector_mechanism_v1.sdc` are
built and ready -- Quartus itself can't run in this sandbox (Windows-
only, node-locked), so the real ALM/Fmax build is Alan's own next step.
Also this session: `#402` -- the full 27-leaf (3x3x3) hierarchical
collector tree proven at VM level for the first time (4/4 tests, first
run), extending `#382`/`#397`'s flat-case proofs to the full
hierarchical scale, honestly scoped as VM-only (no RTL/Quartus/
hardware, no real grid-embedded placement attempted).

## Previous state (2026-08-17, day 3 -- priority-list execution; items 1-6 done, see `points.md` #372-377)

**Day 3, working the priority list in order, per Alan: "yes lets
concentratye on the list in that order ok."** Item 1 (parser error
recovery, `#372`) -- real statement-level panic-mode recovery with a
maintained brace-depth counter (a real design bug found and fixed
mid-build, traced by hand before trusting either version). Item 2
(`define` forward references, `#373`) -- a real topological sort with
cycle detection, per Alan's own suggestion to build a name table first.
Item 3 (C/Rust frontends, `#374`) -- C done (Alan's own scoping: C
first since `pycparser` was already installed, plain function-call
syntax, `place`/`field` only for pass one, cross-checked directly
against the DSL for identical output), Rust explicitly deferred. Item 4
(a real loader/binder stage, `#375`) -- built as `nano/loader_v1.py`
(manual + real first-fit auto-placement), then ACTUALLY INTEGRATED into
`workbench_v1.py`'s own `load_region()` per Alan's direct instruction
("should be callable from the workbench system"). A real transport-
layer bug found and fixed along the way (`row_offset`/`col_offset`
defaulting to `0` instead of `None`, which would have silently
defeated the whole auto-placement contract). Item 5 (manuals and
descriptions, `#376`) -- `docs/build_manual.py`'s own `SECTIONS`
rewritten against only real, current docs and ACTUALLY RUN; found and
fixed a genuine bug in the third-party `markdown` package itself (a
wrapped `#NNN`-starting line misread as a heading), a real relative-
link bug, and made a real design correction (link to `points.md`
rather than embed 300+ entries inline). `tools/explainers/
cell_pipeline_explainer.html` fully rebuilt for the current
`SUPER_LATCH` architecture -- cross-checked bit-for-bit against
`nano/icm_v3.py`'s own real encoder across 4 different cores before
being trusted. Item 6 (DSP connection, `#377`) -- checked `current/
PLAN.md`'s own "Hybrid Hard-IP Architecture" section first, found it
answers a genuinely different, mostly-obsolete question tied to the
archived Shore OS-layer system; built `find_dsp_aware_placement()` in
`nano/loader_v1.py` instead, a real, honestly-scoped first pass with
`dsp_columns`/`dsp_consuming_cores` as real caller-supplied inputs (no
real Quartus data exists yet), wired into the workbench's own
`/load_region` endpoint. 255/255 across the full new-work suite (up
from 211 at the start of this arc), zero regression on the legacy 64+6
nano scripts throughout. All pushed to `origin/main`. Next: item 7,
memory functions.

## Previous state

**`#216` final status:** items 1 (`#355`), 2/4 (`#356`/`#358`), 3
(`#361`), 5 (`#354`), 6 (`#359`) all real and done. Item 8 (the `core/`
folder name) is bookkeeping only -- `nano/` already satisfies the goal.
Per Alan's own sequencing (`#360`): **the workbench itself is next.**

## What's real and built

- **`nano/icm_v3.py`** -- `SUPER_LATCH[79:0]` encode/decode, verified
  bit-for-bit against `tb_unicell_super_v1.v`'s own real RTL test
  vectors (iverilog installed fresh this session, wasn't there
  before).
- **`nano/unicell_super_automaton_v1.py`** -- `SuperCell`/`SuperGrid`,
  dispatching across all 6 core types. nano delegated to the existing,
  already-proven `CACell` (composition, not reinvention); the other 5
  cores' behavior transcribed from their own real RTL bodies.
- **`nano/super_tile_library_v1.py`** -- Tier 0, six single-cell
  primitives with named ports, plus target tagging
  (`TARGET_UNICELL_N`/`TARGET_UNICELL_S`, `"universal"`/`"super-only"`)
  and a real second placement backend (`place_on_nano()`) proving
  "universal" is a functional guarantee, not a label.
- **`nano/composed_tile_library_v1.py`** -- Tier 1, `place_composed()`.
  Three tiles: `sentinel` (verified against the exact proven hardware
  behavior sequence), `dual_threshold_monitor` (fan-out + non-linear
  placement), `twin_sentinel` (nested composition -- a composed tile
  built from OTHER composed tiles, proven with double-namespaced
  params resolving correctly at arbitrary depth).
- **`docs/stripped-cell/design-notes/super_tile_library_scope.md`** --
  the Tier-0/Tier-1 scoping note, written before any of the above was
  built.
- **`docs/stripped-cell/design-notes/unicell_s_dsl_and_compiler_scope.md`**
  -- the DSL/compiler design proposal. Alan's own real choices so far:
  a fresh purpose-built DSL (not a Python-AST subset), diagnostics
  that are first-class (what/problem/why/suggestion, not bare
  exceptions), and a multi-pass architecture where passes collect
  every problem in one go rather than stopping at the first --
  `cell_format.py`'s own `check_pipeline_bridges()` is the real,
  already-built precedent for that shape. Nested composition
  (originally an open question in this note) is now CONFIRMED and
  PROVEN (`#342`).
- **`nano/dsl_diagnostics_v1.py`/`dsl_lexer_v1.py`/`dsl_parser_v1.py`/
  `dsl_compiler_v1.py`** -- the DSL's first real slice (`#343`). A
  `program { place ... }` grammar compiles end to end for both Tier-0
  and Tier-1 tiles (including fan-out lists and nested/namespaced
  params), with real `CompileDiagnostic`s (what/problem/why/suggestion
  + a real source span) rather than bare exceptions. RESOLVE/PLACE
  reuse `place()`/`place_composed()`'s own existing validation
  directly. "Collect every problem, don't stop at the first" confirmed
  directly for resolve/place-stage errors; lex/parse error recovery is
  the one honest, stated limitation (stops at the first syntax error).
- **`nano/program_ir_v1.py`** -- the shared, frontend-agnostic IR
  (`#344`), pulled directly out of the DSL parser's own node shapes
  (not redesigned speculatively). `dsl_compiler_v1.compile_program_ir()`
  is the real backend now; `compile_source()` is the DSL's own thin
  wrapper on top of it.
- **`nano/python_frontend_v1.py`** -- a second, real, working frontend
  proving the IR/backend split actually works, not just asserting it.
  Builds `ProgramIR` from plain Python dicts, never touches the DSL
  lexer/parser at all, and produces byte-identical output to the DSL
  frontend for the same program (`test_dsl_and_dict_frontends_agree_
  on_the_same_program`).
- **`nano/user_tile_loader_v1.py` / `nano/dsl_cli_v1.py`** -- "use this
  model" (`#345`). A real, working command-line tool: `python3
  dsl_cli_v1.py program.uc --model my_tile.json -o out.icm`. The JSON
  model format is a direct mirror of `ComposedTileSpec`, not a new
  format -- so a future composer export just needs to produce this same
  shape. `ComposedTileLibrary` gained optional parent-chaining so a
  user model shadows a same-named built-in without ever mutating the
  real registry -- tested both directions (shadowing confirmed,
  unrelated built-ins still resolve correctly alongside a loaded user
  model). Tested as a real command via `subprocess.run()`, not just
  Python internals called in-process.
- **`define`/`expose` grammar (`#346`, internals finished `#347`).** A
  program can define its own reusable composed tile inline: `define
  NAME { place ... expose ... }`, then `place` it exactly like any
  built-in tile. Fixed sub-cell params (`SubCellPlacement.fixed_params`)
  and forward declarations (two-pass: all defines first, in their own
  order, then all places) both real and tested -- a `define` still
  can't forward-reference a LATER `define`, a real, narrower, stated
  limit.
- **`nano/python_ast_frontend_v1.py`** -- a real Python-AST frontend
  (`#348`), genuinely distinct from `#344`'s dict-based proof-of-concept:
  parses actual Python syntax (`ast.parse()`, never `exec()`s it) --
  `place(...)` calls and `with define("name"): ...` blocks, every
  argument a plain literal. Cross-checked against the DSL frontend for
  the same program, byte-identical output. Every `#347` mechanism
  (define/expose/fixed-params) inherited for free, confirmed not
  assumed, since this frontend produces the same `ProgramIR` shape.
- **`docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`** (`#349`, corrected
  `#350`) -- the language reference. Every code example independently
  compiled and confirmed working before inclusion. `#350` fixed a real
  framing error: "no automatic placement" was listed as a compiler
  limitation, but this project already settled that exact architectural
  boundary for the old full-cell system (`model -> ICM (shape-neutral)
  -> [BINDER] -> placement -> loader -> silicon`) -- corrected to state
  it as a genuine boundary (§9), not a gap the compiler should fill.
- **Naming hygiene lint + circular-reference guard (`#350`)** --
  `_lint_names()` (`dsl_compiler_v1.py`): real `severity: "warning"`
  diagnostics for duplicate local names, collected, shown, never
  blocking compilation. A REAL circular-reference bug found and fixed
  in `place_composed()` (`composed_tile_library_v1.py`) -- a
  hand-crafted `--model` JSON tile could self-reference or cycle
  indirectly with zero protection; confirmed as a genuine
  `RecursionError` before being fixed, not assumed. Now a clear
  `ValueError` naming the exact cycle chain.
- **The long-range note (`#351`/`#352`/`#353`)** --
  `docs/stripped-cell/design-notes/general_purpose_programming_
  long_range_note.md`. Captured, not started: real general-purpose
  programming on Unicell-S; "the FPGA design side route" clarified
  (lowering the compiler's own output past ICM v3 to real synthesizable
  Verilog, a natural backend-side extension of the already-proven "many
  frontends, one shared IR"); "LEGO for FPGA," which turned out to be
  the direct fulfillment of a real requirement Alan already stated the
  day before this session began (`#317`) -- the RTL's own `core_select`
  field already reserves the headroom for it.
- **`nano/vm_introspection_v1.py`** (`#354`) -- JSON introspection for
  the real VM, the first piece of `#216`'s own VM-core architecture,
  per Alan's own chosen sequencing (VM-core work before the workbench
  itself). Verified against actual running VM state -- the proven
  `sentinel` sequence, including its real sticky-latch behavior still
  correctly visible through the introspection layer once the
  accumulator drops back below threshold.
- **`nano/root_definition_extractor_v1.py` / `validate_icm_v3_
  against_rtl_v1.py` / `regenerate_root_definition_v1.py`** (`#355`) --
  `#216` item 1. Mechanically extracts field-map bit positions directly
  from the RTL's own comments -- confirmed genuinely tractable before
  building, not assumed. Two real parser bugs found and fixed against
  actual RTL during development (wrapped headers/descriptions silently
  losing fields), locked in as regression tests. The real payoff: an
  independent cross-check against `icm_v3.py`'s own hand-typed field
  tables (built by a human this session, transcribing the same RTL
  comments) -- PASSED, zero mismatches, genuine positive confirmation
  the earlier transcription was accurate. `nano/root_definition.json`
  is the real, re-runnable persisted artifact. Honest gap:
  `addon_config`'s own fields aren't covered (wired via module ports,
  not the same comment convention).
- **`nano/generic_field_codec_v1.py`** (`#356`) -- `#216` items 2/4,
  which turned out to be the same undertaking once scoped. Field pack/
  unpack driven entirely by `root_definition.json`, never consulting
  `icm_v3.py`'s own hand-typed tables. Proven bit-for-bit equivalent to
  `icm_v3.py`'s already-RTL-verified codec across all 6 cores and many
  values, checked systematically not assumed. Real, honest scope
  boundary: `addon_config` still isn't covered; the direction-name/list
  convenience deliberately isn't re-derived here (a separate,
  reusable-as-is concern). The actual grid/cell construction layer
  using this codec is still unstarted -- this is the field-level
  foundation only.
- **`docs/stripped-cell/SUPER_CELL_INTERNALS.md`** (`#357`, new) --
  found and fixed real doc staleness (confirmed via git log, not file
  mtimes): neither `CELL_INTERNALS.md` nor `CORES_AND_WRAPPERS_
  REFERENCE.md` covered the super carrier shell at all. Every field
  table cross-checked against the live code; every hardware figure
  checked against its own `points.md` entry (caught and fixed one own
  mistake -- a rounded timing figure). `docs/README.md`'s own index was
  also stale, missing two already-existing docs.
- **Two small wins (`#358`).** A real registry (`CoreHandler`/
  `register_core_handler()`) replaced `SuperCell`'s if/elif core
  dispatch -- proven by registering a genuinely new core type with zero
  edits to `SuperCell` itself, and confirmed zero behavior change on the
  5 real cores via the full pre-existing suite run unchanged right
  after. Root-definition-driven validation added to `SuperCell.
  from_record()`, closing a real gap: typo'd `core_config` keys were
  previously silently ignored (default zero used, no error) -- now
  caught with a clear message naming both the bad key and the correct
  one, using the same `generic_field_codec_v1.field_table()` `#356`
  already proved equivalent to `icm_v3.py`'s own.
- **`nano/vm_ai_port_v1.py`** (`#359`) -- `#216` item 6. `VMSession`:
  compile (DSL or Python-AST) -> real ICM v3 -> real running VM -> real
  JSON introspection, all through one clean object. Deliberately not
  the old `attach_ai()` precedent directly -- no ML dependency needed
  just for the port to exist; a real model attachment stays a separate,
  optional, later layer. Building and testing this end to end
  immediately found a REAL bug: `SuperGrid.run_to_quiescence()` checked
  `_pending` before ever calling `tick()` once, silently under-
  reporting quiescence for a continuously-live core with zero prior
  stimulus -- a direct violation of its own documented contract, fixed
  the same session (do-while instead of while-do), with real regression
  tests for both the broken case and the genuinely-idle case.
- **`nano/gpu_array_v1.py`** (`#361`) -- `#216` item 3, THE LAST REAL
  `#216` ITEM. `VectorizedOfferSelector` vectorizes exactly the
  cell-SELECTION phase `gpu_array.py`'s own real precedent vectorizes
  (confirmed by reading its actual kernel, not just its header -- even
  its own "Stage 1" never vectorized per-cell logic evaluation, only
  selection). Proven equivalent to `SuperGrid.tick()`'s own Pass 4
  condition, tick-by-tick, across `sentinel`/`dual_threshold_monitor`/
  `twin_sentinel`. No CUDA hardware in this sandbox (confirmed
  directly) -- CPU path real and tested, GPU path's code untested here,
  stated honestly. Fully additive: zero changes to `SuperGrid.tick()`
  itself, confirmed by the full pre-existing suite passing unchanged.

**`#216` is now closed on every real item**: 1 (`#355`), 2/4
(`#356`/`#358`), 3 (`#361`), 5 (`#354`), 6 (`#359`). Item 8 is
bookkeeping only.

- **`docs/stripped-cell/design-notes/workbench_scope.md` +
  `nano/workbench_v1.py`** (`#362`/`#363`, day 2) -- the new workbench,
  MILESTONE FINISHED. Built on a genuine line-level audit of the old
  `workbench.py`, not guessed at: confirmed which parts are dead
  (address/`gate_state`-keyed everywhere, including the embedded
  browser JS's own field bindings) vs. reusable (tick/step concept,
  `http.server` plumbing). `WorkbenchController`/`WorkbenchHandler`/
  `serve()` -- a thin HTTP layer directly over `VMSession` (`#359`),
  which already provided almost the whole replacement data layer.
  Extended with a real demo library (6 working programs, `#363`), real
  multi-program REGION management (`load_region()`/`clear_region()` on
  a shared grid, with careful `_pending` cleanup reasoned through up
  front, not found as a bug afterward), and a rewritten UI (real 2D
  grid, demo picker, region controls). Proven against a genuinely LIVE
  server twice, per Alan's own "let's see how it will work in reality":
  the original sentinel sequence via `curl`, then the full demo/region
  UX via real HTTP calls -- two independent `sentinel` regions driven
  to their proven state separately, one cleared, the other confirmed
  completely untouched. Embedded JS syntax-checked with `node --check`.
  A real sandbox constraint found and worked around (background
  processes don't survive across separate tool calls) -- the permanent
  automated test suite starts/stops the server WITHIN the same pytest
  process instead, real sockets, not mocked.

## What's NOT built yet -- open, real options

Per `#349`/`#350`'s own remaining "known limitations": parser error
recovery (one syntax error stops compilation, not a full list);
`define` can't forward-reference a LATER `define`; no multiple programs
per file (DSL or Python frontend). C/Rust frontends need an external
parser library first, not attempted. A REAL loader/binder stage for
Unicell-S is genuinely new, unscoped work now that `#350` corrected the
manual's framing -- the compiler deliberately does NOT do real hardware
placement, and nothing yet does. The actual generic grid/cell BEHAVIOR
engine (data-driven capture/offer semantics, not just field packing)
remains unstarted and may not be simply achievable -- `#358`'s own
honest scope note: that would need something much bigger (a real
hardware-behavior description language), not attempted. **The
workbench milestone is now CLOSED** -- real, honest remaining gaps for
whenever they matter, none part of the stated milestone: no
persistence (the in-memory grid/regions don't survive a server
restart); no authentication (single-user, localhost-only, matching the
old workbench's own scope); visual styling is functional, not
polished. Per Alan's own sequencing (`#360`), the real next step is
tidying the scattered 77-file root Python sprawl, deliberately timed
for after a real VM/workbench exist. The TRIX system (`mathtrix_*`/
`neurotrix_*`/`flowtrix_*`/etc., a real, sizeable, existing system with
genuine domain typing and cross-domain bridges) is a real, checked,
well-founded concern for later -- may need the compiler to learn about
DOMAINS, not just ports/fields, per `#360`'s own note. The composer
(Stage 5, `#20`) remains explicitly later work, after both compiler and
workbench.

## Also still open (carried forward, unchanged from this morning)

- `hardware/Arria10_Programming_Procedure.md` -- needs Alan's own
  judgment call (archive vs. refresh).
- The `mathtrix` root/community structural question.
- The super carrier shell's own remaining gaps (`latch_in`/
  `latch_A_dis` absent from every core; the `#323` register-count
  discrepancy; a real host/JTAG-wrapped version of the super cell).
- The RAM-side address-arbitration/retry-loop mechanism (`#301`/`#302`)
  -- needs real testing before trust.
- `sentinel_counter_v1.v`/`v2.v` still not wired into any real chain;
  `shared_bram_arbiter_v1.v` still not wired into the full tree
  system.
- The two long-queued Quartus diagnostic experiments (duplication
  flags, aggressive optimization mode).
- The 77-file root Python sprawl -- still deliberately held until the
  real VM/`core/` rebuild (now genuinely underway) is far enough along
  that archival is a real replacement, not speculative deletion.

**A real chaos-testing tool built and run (`#388`/`#389`):** `tools/
chaos_topology_v1.py` -- random core assignment, random valid wiring,
known-value injection, real observed VM behavior. Sparked by Alan
bringing an AI-generated ("Copilot") transcript full of evocative but
fictional narrative ("pulse lattices," "freeze cascades") about
exploring the substrate -- the other AI couldn't actually read the repo
or run anything. The real idea underneath (genuine chaos testing) was
kept, the fiction discarded. Random 10x10 topologies consistently fail
to reach quiescence within 200 ticks, confirmed across 5 seeds -- BOTH
obvious hypotheses (known heartbeat cores: accumulator/latch/RAM-
fixed_mode) were tested with real control experiments and DISPROVEN.
**Then genuinely resolved (`#389`):** a minimal, deliberate 2-cell
reproduction (one single-shot RAM seed feeding two plain relay-mode
`nano` cells wired as a pair) confirmed the real mechanism -- closed
RELAY cycles forming by chance in random cardinal wiring, zero
heartbeat cores required, a value that enters one circulates forever
(confirmed to 5000+ ticks). Two real bugs found and fixed while
building the reproduction: injected values always take the consume
path, never relay; `cardinal_edge` only relays the specific direction
it's configured for. Confirmed at larger scale too, as originally
asked: 10x10/20x20/30x30 (up to 900 cells) all show the same behavior,
all fast (well under a second of wall-clock time even at 900 cells).

**Item 1 of the real build order DONE at the simulation level (`#390`):**
`fpga/verilog/unicell_super_v1.v` now has a real, working shell-level
`program_in`/`prog_data_in_*`/`prog_arrived_in_*`/`program_done`
channel, gated to nano via the file's own existing `sel_active_nano`
convention, `program_done` routed through the established per-core
output MUX. `tests/fpga/tb_super_program_in_v1.v` -- 5/5 real checks
passing, confirming the channel genuinely reprograms `cardinal_edge`
through the shell and the reprogrammed behavior fires correctly.
Zero regression on the existing `tb_unicell_super_v1.v` (all 6 cores)
or the real Quartus-target wrapper. Five real bugs found and fixed
during a hand-traced debugging arc (a missing dependency, an off-by-
one word-encoding bug, stale internal state needing a real `rst` not
just a `cfg_valid` reload, a classic nonblocking-assignment race, and
the actual root cause -- a wrong `routing_mask` bit in the testbench
itself). No Quartus build run yet -- `iverilog` simulation only. **Item
2 (the collector core RTL) is now genuinely unblocked**, not just
theoretically. The exact `iverilog` command to reproduce is in `#390`.

**A real, confirmed VM gap flagged, not yet fixed (`#391`):** the
Python VM (`unicell_super_automaton_v1.py`) has ZERO support for the
new shell-level programming channel `#390` just added -- checked
directly, not assumed. `#381`/`#382`'s own collector-cell VM testing
worked by reaching directly into the internal `_nano` object, a
reasonable shortcut before real matching RTL existed. Now that it does,
the VM should expose the same shell-level interface, not the internal
one, to keep "RTL is ground truth, the VM must match it" intact.

**A real, honest item-2 re-scoping, before building anything (`#392`):**
checked both existing "command cell" candidates directly -- neither
`cell_command_v1.v` nor `cell_cardinal_cmd_v1.v` matches the current
`PROG_ID`-based interface at all (both predate it, zero references to
`prog_data_in`/`PROG_ID` in either file, confirmed by grep). A
genuinely NEW command-cell module is needed -- one that can sequence
through MULTIPLE `cardinal_edge` values over time (the collector's own
real use case), not apply one static value once. Not yet built --
picking this up from real, checked understanding, not an assumption.

**A real chaos-topology visual demo built (`#393`), plus a real
feature idea flagged for the tool itself (`#394`):**
`tools/explainers/chaos_topology_demo.html` -- a standalone page built
from an ACTUAL captured VM run (not synthetic), play/pause/scrub
through 30 real ticks of a 12x12 random topology. A real mistake
caught before shipping: the first attempt left an unsubstituted
placeholder in `JSON.parse(...)`, rebuilt with the real data properly
embedded. The demo honestly shows the run settling into a repeating
2-state oscillation by ~tick 10 -- consistent with `#388`/`#389`'s own
closed-relay-loop finding, not hidden. **Flagged, not built:** turning
the one-off capture script into a real, first-class capability of
`tools/chaos_topology_v1.py` itself (`capture_run()`, a real CLI, a
documented stable JSON schema) so captures can be produced for later
analysis by others, not just this one demo.

**Item 2 (the collector core RTL) -- real progress (`#395`):**
`fpga/verilog/cell_command_sequencer_v1.v` -- the genuinely new
command-cell module `#392` scoped (neither existing candidate matched
the current `PROG_ID` interface). Verified end to end against the real
shell: a real 3-value `cardinal_edge` cycle (N-relay -> S-relay ->
E-relay -> wraps back to N-relay), 12/12 checks passing, confirmed at
every step both via direct signal inspection AND real cell relay
behavior with correct values. A real testbench bug found and fixed: a
shared `rst` between the sequencer and the shell silently wiped real
sequencer progress on every per-step reset -- fixed with separated
`dut_rst`/`rst`. Zero regression on `#390`'s own testbench or the
pre-existing `tb_unicell_super_v1.v`. Real, honest remaining scope:
the header/counter/queue cells and real inter-cell physical wiring
(this testbench drives the target directly via named ports, not
through real cardinal wiring between two placed shell instances) --
not yet started.

**The header role -- DONE, no new RTL needed (`#396`):** the EXISTING
accumulator core (`core_select=SEL_ACC`) proven to serve `#381`/`#382`'s
own "header" role directly. 6/6 checks: real continuous heartbeat
offering, a real repeatable increment (0->1->2). Two real issues found
and fixed, both revealing genuine protocol lessons, not RTL bugs:
holding `ack_in_e` high BEFORE a fire happens masks `pending_ack`
entirely (fire never becomes visible even though it genuinely
occurred); the accumulator correctly withholds a newer value from
`out_buffer` until the CURRENT pending offer is acknowledged, rather
than overwriting it out from under an unacknowledged consumer. **Item
2's own real remaining scope, updated:** header/collector/command all
DONE, queue already real (plain RAM cells). Counter still needs
proving (likely another existing core, same "check before assuming"
discipline). Real inter-cell physical wiring between placed instances
-- not yet built.

**MAJOR MILESTONE -- item 2 fully closed at the simulation level
(`#397`):** the COMPLETE end-to-end collector mechanism, six real,
separate module instances (3 headers, collector, command sequencer,
queue) wired together as genuine physical connections, not shared
testbench ports. A full 3-round cycle proven: H1's value (1), H2's
value (2), H3's value (3), each independently verified correct, plus
correct wraparound back to round 1's own configuration. `tests/fpga/
tb_full_collector_mechanism_v1.v`, 8/8 checks. A real, hand-traced
debugging arc -- FIVE distinct issues found and fixed, each a genuine
lesson, not repeats of the same mistake: a real Verilog reg/wire
design error; the OR-combine hazard `#381`/`#382` predicted, now
confirmed live in a real multi-source system; a genuine architectural
finding (a terminal RAM cell can only capture ONCE, ever -- confirming,
not contradicting, Alan's own "chain of RAM cells" design as load-
bearing, not stylistic); the real root cause of multi-round failures
(a continuously-live header re-firing before the next round began);
and a precise timing refinement (dropping a header's readiness the
INSTANT its fire is observed, not after settling). Real, honest scope:
simulation only, no Quartus build; readiness-gating is testbench-
driven for now, not yet derived automatically from sequencer state.

**The real sync pass DONE (`#398`):** docs corrected in two places
(`SUPER_CELL_INTERNALS.md`'s own stale "programming channel tied to
inactive defaults" claim; the RAM interface design note given a real
update section stating the mechanism is now proven RTL, not just
Python-VM simulation). `#391`'s own flagged VM gap genuinely CLOSED --
`SuperCell` now has a real `program_in`/`program_word()`/`program_done`
interface, matching the exact calling convention already established
for the standalone `CACell`, gated identically to the real RTL's own
`sel_active_nano` convention. 4 new, real, permanent tests. 259/259
across the full VM suite. The workbench checked directly -- confirmed
genuinely clean already, zero stale references, nothing to correct.
**A real architectural generalization confirmed and recorded:** the
proven 3-header collector (`#397`) is the actual building block the
whole `27 = 3×3×3` hierarchical addressing scheme is built from -- more
sources means real repetition of this exact mechanism, composed
hierarchically, not new RTL design. This is now the concrete basis for
any future BRAM/memory interface needing more than 3 chains.

**`#301`/`#302` re-examined against `#397`, precisely re-located, not
resolved (`#399`):** neither hazard applies to what `#397` actually
proved. `#301`'s stale-data hazard concerns the read-RESULT-delivery
side (a real BRAM read's result reaching a possibly-stalled downstream
consumer) -- `#397` only proves the address/value-SUPPLY side, and
never builds a retry-loop-for-stalled-consumers at all. A real,
genuine architectural advantage confirmed along the way: each header
owns its own local value exclusively, so `#301`'s own "someone else
wrote to my queued location while I waited" hazard has no direct
analogue here. `#302`'s own write-side "out>in" concern is about a
genuinely different, real, already-confirmed WRITE-combining topology
-- `#397` is purely read-side, strictly 1:1 rounds-to-outputs, and
doesn't touch that question either way. Both remain exactly as open as
their own original entries stated -- now precisely located in stages
that don't exist yet, not confused with what's now real and proven.

**A real host resource registry built and integrated (`#400`):**
`nano/host_registry_v1.py` -- closes a real, named gap: the host needs
a queryable, load/unload-tracked authority on what's currently placed,
independent of any one workbench session. Confirmed the gap directly
first (the workbench manipulates `session.grid.cells` raw, with no
separate registry at all). Deliberately generic, matching `loader_v1.
py`'s own precedent -- `query_occupied()` is a real drop-in source for
`bind_shape()`'s own occupancy parameter. Real, deliberate validation:
position conflicts and reused/unknown resource IDs are real, raised
errors, never silently merged. Integrated into the workbench SAFELY --
added alongside the already-tested `self.regions` tracking, kept in
sync, not a risky full replacement. Zero regression on all 27
pre-existing workbench tests. 13/13 new registry tests plus a real
integration test. 273/273 across the full VM suite. Real, honest
remaining work: the registry isn't yet the sole source of truth
anywhere, and no real host driver exists yet to consume it outside the
workbench -- this builds the real, generic component itself.

**A real, verified architectural connection (`#401`):** `#400`'s
registry confirmed to fill the exact same role the old, archived Shore
system once did -- checked against Shore's own real, documented
definition ("purely tables and address space; the fabric consults the
table, the data plane fills it"), not a loose analogy. `query_
occupied()` IS the fabric consulting; `register_load()`/`register_
unload()` ARE the data plane filling. No old Shore code was read or
ported -- found after the fact, real proof the project's own "concept
survives, code doesn't" archival principle actually paid off.

## Next session

**The real, current, in-order priority list (`#370` + `#371`) --
items 1-6 DONE, start at item 7:**
1. ~~Parser error recovery.~~ DONE (`#372`).
2. ~~`define` forward-referencing a later `define`.~~ DONE (`#373`).
3. ~~C/Rust frontends.~~ C DONE (`#374`), Rust explicitly deferred (a
   real, separate undertaking -- `tree-sitter`/`tree-sitter-rust`
   confirmed installable, same design pattern would apply).
4. ~~A real loader/binder stage.~~ DONE (`#375`) -- `nano/loader_v1.py`,
   integrated into `workbench_v1.py`'s own `load_region()`.
5. ~~Manuals/descriptions.~~ DONE (`#376`) -- `docs/build_manual.py`'s
   own `SECTIONS` rewritten and actually run (found and fixed a real
   bug in the third-party `markdown` package along the way, plus a
   real relative-link bug and a real design correction re: embedding
   `points.md`). `tools/explainers/cell_pipeline_explainer.html`
   rebuilt for the current `SUPER_LATCH` chain -- cross-checked
   bit-for-bit against `nano/icm_v3.py`'s own real encoder across 4
   cores before being trusted.
6. ~~DSP connection.~~ DONE (`#377`) -- checked `current/PLAN.md`'s own
   "Hybrid Hard-IP Architecture" section first, found it answers a
   genuinely different, mostly-obsolete question tied to the archived
   Shore OS-layer system (soft-fabric-to-DSP arithmetic offload, not
   placement/locality). Built `find_dsp_aware_placement()` in
   `nano/loader_v1.py` instead -- a real, honestly-scoped first pass
   (biases placement toward given DSP columns for DSP-consuming cores,
   treats the shape as one rigid unit rather than the full anchor-
   first BFS design still on record for later). Both `dsp_columns` and
   `dsp_consuming_cores` are real caller-supplied inputs, not hardcoded
   assumptions -- no real Quartus post-fit data exists yet. Wired into
   the workbench's own `/load_region` endpoint, matching item 4's own
   "build standalone, then integrate" precedent.
7. **Memory functions -- REAL DESIGN + SIMULATED VALIDATION DONE
   (`#382`), no RTL yet.** The full mechanism is now ACTUALLY TESTED
   against the live, RTL-matched Python VM (`nano/unicell_automaton_v1.py`),
   not just designed: header/collector/command/counter/queue/sentinel,
   verified clean across two full rounds, zero faults. Real corrections
   found along the way: the collector's selected direction must be
   `relay`, not `consume` (confirmed the opposite of the original
   assumption); sources need `hold_in`+`a_reemit_in` pre-loaded to
   reemit only on trigger. Full write-up:
   `docs/stripped-cell/design-notes/ram_interface_collector_mechanism.md`
   -- READ THIS FIRST before picking item 7 back up. Also covers: the
   real DDR4/external-RAM question (an 8GB on-board resource exists,
   `#147`'s own throughput analysis is real but from the OLD, now-
   archived architecture's own bridge -- a genuinely new bridge is
   needed for the current substrate, not yet built); a real, honestly-
   caveated size estimate (~180 ALM/chain, ~4,860 ALM at the 27-chain
   max, ~2% of GX660 -- explicitly NOT measured, no RTL exists yet).
   Meant to become a standard, reusable substrate pattern for any
   system needing RAM access, per Alan's own direct call. Still open:
   the stale-data hazard (`#301`), `#302`'s write-side concern, the
   hierarchical (27-leaf) staggering question, the real downstream
   RAM-cell queue (not yet correctly modeled), and both a real DDR4
   bridge and real hardware testing of the whole mechanism -- neither
   started yet. **Three more real findings added (`#385`):** the
   shell's own bit-layout IS fully documented, but its runtime access
   mechanism is NOT -- same `#371` gap, confirmed from a new angle, a
   real design/build task, not a doc gap. The loader has ZERO
   connection-point awareness, confirmed directly against the code --
   two real design options surfaced (each region brings its own
   memory-interface set, vs. cross-region connection awareness). The
   underlying placement problem is CONFIRMED NP-complete (Numberlink,
   real cited sources) -- validates the existing anchor-first-BFS
   heuristic direction as the right KIND of approach, and surfaces a
   genuine reframing of the Composer's own premise (`#20`/`#370`): not
   just "create models," but potentially "help a human place/route an
   already-compiled model by eye."
8. **The Composer (`#20`, Stage 5) -- SCOPED (`#387`), no code yet.**
   Scoped around `#385`'s own real reframing -- a placement/routing
   helper for an already-compiled model (leveraging real human
   strength at the NP-complete connection problem), not the original,
   doubted "create models" premise. Full write-up: `docs/stripped-
   cell/design-notes/composer_scope.md`. Real, reusable pieces
   identified: the OLD composer's own visual paradigm (checked
   directly, its data model is old/incompatible but the interaction
   pattern is real); `workbench_v1.py`'s own grid rendering (extend,
   don't duplicate); `loader_v1.py`'s own automated placement (the
   Composer's job is the human-assisted half, not a replacement). A
   real, deliberately minimal first scope: view + confirm/adjust an
   automated placement, not a full routing editor.

**A real, unplanned offshoot (`#386`):** reviving the archived FULL
cell's own richer capability (`unicell64_v3.v`, `#314`) under nano's
own proven cardinal-only communication layer -- architecturally
coherent, applies the same SHELL/CORE separation already proven
(`#253`). Plus a counter-scheduled TDM scheme for cross-zone/cross-card
bursts, riding on top of the already-decided PCIe/backplane physical
layer (`#325`), not competing with it. A real self-check resolved
precisely: the risk of reintroducing bus wiring is real but LOCALIZED
to exactly one place (the physical PCIe boundary, per `#325`) -- the
fix reuses the already-proven header/collector/queue chain-relay
pattern (`#381`/`#382`) rather than inventing something new. Full
write-up: `docs/stripped-cell/design-notes/
full_cell_capability_and_cross_card_scheduling.md`. No RTL, no
implementation -- a real, captured design direction, not a decision to
build.

**Real future core candidates saved, not integrated (`#378`):** a
multiplier, divider, and subtractor from Alan, saved to `docs/
stripped-cell/design-notes/future-core-candidates/` for whenever "LEGO
for FPGA" (`#353`) gets picked up -- `core_select` 6-31 is real,
reserved headroom for exactly this. One real bug found and verified in
the divider (a Verilog syntax error, confirmed with `iverilog`, saved
unmodified with the fix documented in the folder's own README, not
silently patched). A real timing concern recorded up front: the
divider's own 32-stage unrolled combinational critical path would
likely violate the real, hard per-hop timing this architecture depends
on -- worth remembering before wrapping it as a real core, not
discovering it after the fact.

**A real DSP-chain-vs-BRAM design note (`#379`/`#380`), IMPORTANT
context for item 7 (memory functions) specifically:** `docs/stripped-
cell/design-notes/dsp_chain_vs_bram_connectivity.md` -- Arria 10 DSP
blocks have a real, hardwired, column-local `chainin`/`chainout`
cascade bus (64-bit, confirmed via real Intel documentation); chain
position is fixed at Quartus place-and-route time, so it's a
PLACEMENT concern (matching `loader_v1.py`'s own role), not a runtime
protocol field. M20K/BRAM connects through NORMAL fabric interconnect
instead -- no dedicated cascade bus at all, confirmed with the same
rigor. **Read this note before starting item 7** -- memory connection
is a genuinely different kind of problem from DSP connection (`#377`),
not the same placement concept applied twice. Also confirmed the
actual archived MathTrix/MIF precedent (extracted from `old_trix_
domain_family.onion`, not recalled from memory) -- a real asymmetric
control/mantissa split by function, not an even bit-count split,
though the underlying principle does support Alan's own proposed even
32/32 split for the DSP case specifically, since a flat accumulator
has no natural asymmetric boundary the way a float does. **A real
architectural conclusion added on top (`#380`):** DSP needs its own
specialist wrapper CORE TYPE (not a mode on any existing core,
`core_select` 6-31 headroom); the 64-bit chain resolves into TWO
PARALLEL 32-bit-wide chains, each using the fabric's own already-real
32-bit value convention. Independently converges on the exact same
structural shape MIF already uses -- a genuine, useful cross-check
worth remembering: "N standard-width cells, not one wide cell" is
probably the right general answer for wide hard-IP interfaces here,
not a DSP-specific one-off. Still real, open, unresolved: how the two
32-bit lanes stay correctly paired as they propagate, and whether
high/low are the same core type with a role field or two distinct
types. **The 64-bit format itself now CONFIRMED against the primary
source (`#383`):** a flat two's complement value, no internal
structure, plus three real, dynamic control signals (NEGATE/LOADCONST/
ACCUMULATE) confirmed to fit the EXACT same `program_in`/`PROG_ID`
pattern every other core already uses -- no new mechanism needed. A
real, hard constraint found: these controls are non-functional in
`m27x27`/`m18x18_full` modes, a genuine tradeoff against full 27-bit
precision. Closed with a real, honest scope note: the current
substrate has no signed-number or fixed-point convention at all, so
losing `m27x27` costs nothing usable right now -- and more broadly,
the substrate itself remains genuinely narrow (6 cores, unsigned-ish
32-bit integers, no negatives, no fixed point) -- this DSP work adds
precision/throughput on top of that, it doesn't broaden the value
model itself.

**Confirmed NOT wanted, don't build these:** multiple programs per ICM
file, the `core/` folder rename.

**Explicitly deferred, with a real stated reason each:** hardware-
target work ("too many variables" right now); "LEGO for FPGA" ("maybe
when we get there").

**Explicitly OUT of scope, a real future enabler not a task (`#371`):**
integrating the command-cell wrapper (`cell_command_v1.v` --
docs/stripped-cell/CELL_INTERNALS.md's own "Companion modules" section)
into Unicell-S. It's not exposed anywhere in the shell's own reduced
nano subset today. Alan's own words: "not part of the scope directly,
but if it were it would open some more possibilities later" -- recorded
so the reasoning isn't lost, not because it's queued.

**Already done earlier this session (`#370`):** the pytest `sys.exit(0)`
crash is genuinely FIXED (`norecursedirs` in `pyproject.toml`), not
just re-flagged -- confirmed a bare `pytest --collect-only` no longer
crashes. A real, separate, pre-existing issue surfaced while checking:
`tests/fpga/` fails to import `pyserial` -- confirmed NOT a regression
(same error count as before, previously masked by the crash), a real,
still-open item, not chased further given limited usage.

**Real conclusions from Alan worth remembering, not just "still
open":** TRIX -- "would not be viable on this model at all," a real,
definitive conclusion, stronger than `#360`'s earlier "checked concern
for later." Treat as closed. Loops/general-purpose memory -- still a
genuinely open question, but Alan gave a real, sharp reason the scope
is likely to stay limited: branching on this substrate means every
branch outcome needs its own physical cells existing simultaneously
(spatial MUX), so branch-heavy control flow doesn't scale the way it
does on a substrate with a real program counter. `hardware/
Arria10_Programming_Procedure.md` still needs Alan's own human call
(archive vs. refresh), per `#333`'s own earlier note.

Read `points.md` #336-371 first if `#324`'s own phase context needs
refreshing -- each entry carries real reasoning, not just a summary of
what changed. The DSL manual
(`docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`) is the right starting
point for the compiler/DSL side; `docs/stripped-cell/
SUPER_CELL_INTERNALS.md` is the right starting point for the shell/RTL
side; `nano/vm_ai_port_v1.py`'s `VMSession` (or the workbench itself,
`python3 nano/workbench_v1.py`) is the easiest way to try something out
end to end without wiring the compiler/VM/introspection together by
hand.

A genuinely long-range thread was also captured, not started
(`#351`/`#352`/`#353`, `docs/stripped-cell/design-notes/
general_purpose_programming_long_range_note.md`): real, general-purpose
programming compiled onto Unicell-S, a clarified "FPGA design side
route" (lowering the compiler's own output past ICM v3 all the way to
real, synthesizable Verilog per program), and now a third facet --
"LEGO for FPGA," a snap-in core ecosystem for third-party hardware
designers. Worth noting: this third piece isn't a new idea, it's the
direct fulfillment of a real requirement Alan already stated the day
before this session began (`#317`) -- and the RTL's own `core_select`
field already reserves the headroom for it (values 6-31, confirmed live
in `nano/icm_v3.py`'s own code). Deliberately deferred -- Alan's own
words: "sort after all this is sorted." Don't raise it again until he
does.
