# Current State (as of 2026-08-31, Alan's reformulated shared-storage idea proven on two cores of different widths -- a genuinely optional, parameter-gated interface built INTO each core file, not a separate wrapper. A real testbench race condition found and fixed across all three differential testbenches this session, see `points.md` #563)

## Read this first (most recent)

**2026-08-31, real external-storage mechanism proven on latch (23
bits) and ram (46 bits).** `latch_cell_v2.v`/`ram_cell_v2.v` (new),
each cloned from v1 with a genuinely optional `EXTERNAL_STORAGE`
parameter (default 0, byte-for-byte identical to v1 for all existing
standalone use). Real differential testbenches confirm both modes
match v1 exactly -- 5/5 and 4/4 real checks.

**Alan's own real reformulation, now built:** rather than wrapping an
unmodified core from outside, each core file itself gains a real,
optional capability -- one source of truth for both standalone and
shell use, so future fixes never need to be applied twice.

**A real, important methodological bug found and fixed:** RAM's own
differential test surfaced a genuine divergence, traced to a classic
Verilog testbench race (clearing a signal at the exact same simulation
time as the edge meant to sample it) present in all three differential
testbenches built this session -- including the earlier wrapped-
experimental one, whose "6/6 passing" result hadn't been re-checked
for this. Fixed with a real `#1` delay; all three re-verified from
scratch, all still pass.

Full detail: `points.md` `#563`.

**Real, honest scope: 2 of 8 cores proven, deliberately different
sizes.** The remaining 6 not yet attempted. No real Quartus data yet
for either `_v2` core or the actual shell integration -- the real next
step.

## Previous state (2026-08-31, full 8-core shared-buffer VM prototype complete, a real architectural finding surfaced (each core is a separate proven module, not inline logic), and Alan's own real wrapper-extraction experiment designed, built, differentially verified, and packaged as a ready-to-build Quartus project, see `points.md` #562)

## Read this first (most recent)

**2026-08-31, real, substantial progress across three fronts while
Alan was away.**

1. **Full 8-core VM coverage completed** -- `shared_buffer_prototype_
v1.py` now covers all 8 real cores, 12/12 tests passing. Sequencer
required real care (no existing VM reference), implemented fresh
directly from its own real RTL.

2. **A real, important architectural finding, checked directly
against the RTL:** the 8 cores are separate, already-proven module
files, not inline logic waiting to be merged -- meaning "share the
storage" has two real, different shapes (modify each proven core
file, or write one new unified shell), each with real tradeoffs, laid
out fully in `experimental/shared_buffer_v1/README.md`. Neither
started -- a real, deliberate decision left for Alan's own input.

3. **Alan's own real, third idea built and verified**: extract the
config-distribution logic into a separate wrapper module (touching
NONE of the 8 proven core files), testing whether that alone changes
Quartus's own real optimization behavior. `super_latch_wrapper_v1.v`
+ `unicell_super_v3_wrapped_experimental.v` (new), differentially
verified against the real, original v3 -- 6/6 real checks, identical
behavior, reusing `tb_unicell_super_v3.v`'s own proven stimulus.
Packaged as a complete, ready-to-build Quartus project in
`experimental/shared_buffer_v1/quartus_wrapper_test/`.

Full detail: `points.md` `#562`.

**Real, honest scope: the wrapper experiment is ready to build in
Quartus right now**, independent of the bigger Option A/B decision --
a real, cheap, single-cell test against the known 144.8 ALM/cell
baseline.

## Previous state (2026-08-31, Alan's shared-buffer union-register idea prototyped and verified in the VM -- 8/8 real cross-checks pass against known-correct behavior for 4 representative cores, real shared width corrected to 166 bits (not 128), see `points.md` #561)

## Read this first (most recent)

**2026-08-31, shared-buffer prototype built and verified.**
`nano/shared_buffer_prototype_v1.py` (new) + `tests/vm/test_shared_
buffer_prototype_v1.py` (new), 8/8 passing -- every test vector reused
from already-proven-correct tests elsewhere in this project (adder
subtract/borrow, the real 3-pulse accumulator check, the real,
silicon-confirmed branch cell LOW/EQUAL classification), not new,
independent claims.

**Real, honest correction found while designing it:** Alan's own
starting figure was "128 bits max" (nano's own `cmd_latch`). Real
total persistent state for nano is `cmd_latch`(128) + `data_reg`(32) +
`pending_ack`(6) = 166 bits -- `data_reg`/`pending_ack` sit alongside
`cmd_latch`, not inside it. 166 bits is the real, honest shared width
used, still a real ~4.2x reduction on the covered subset (694 bits
summed across all 8 cores today).

**A second real correction found mid-verification:** adder's own
register count was first estimated at 76 bits from an incomplete
grep; the real, complete total is 79 (`a_arrived` was missed) -- a
direct confirmation of why cross-checking against known-correct
behavior matters more than careful-looking manual counting.

**Real, honest scope: 4 of 8 cores covered** (adder, accumulator,
branch, nano -- chosen for genuinely different update patterns, not
the simplest 4). The remaining 4 follow the same proven pattern, not
implemented here.

Full detail: `points.md` `#561`.

**Real, honest scope for the whole idea: this proves the LOGIC is
sound, not the real ALM savings.** The real next step: design and
sim-verify the actual merged RTL (`always @(posedge clk) case
(core_select)`, one real write-side mux) before it costs a real,
slow Quartus cycle to find out whether the hoped-for savings
materialize in practice.

## Previous state (2026-08-31, a real, substantial future architecture thread named -- shifting UniCell to a genuinely clockless model, matching Wave Computing's own real DPU design, connected to two already-established real facts rather than starting fresh, see `points.md` #560. Real 500-cell ALM-fanout mystery resolved -- confirmed a real, fair "fully-connected cell" cost, not a bug, ~250 cells is the real honest ceiling on this card)

## Read this first (most recent)

**2026-08-31, real clockless-architecture thread named.** Connects
directly to `#435`'s own already-established, honestly-stated "not
cosmetic" timing difference from Wave Computing's real DPU (true
GALS, no shared clock, vs. UniCell's current single synchronous FPGA
clock), and a separate, earlier real observation that the two-arrival
firing model is already inherently asynchronous in spirit -- causality
from path length, not a clock sequencer. Real, honest engineering cost
named plainly (genuine async design is a real, difficult discipline
mainstream FPGA tooling doesn't meaningfully support). A real, better-
fitting eventual home identified: the standing Tiny Tapeout ASIC path,
not the current Arria 10/Quartus target.

Full detail: `points.md` `#560`.

**Real, honest scope: named and grounded, nothing designed or built.**
A genuine future direction, separate from the still-open, more
immediate 500-cell ALM-fanout investigation (N=1 clean at 144.8
ALM/cell, N=500 catastrophically inflated at 476,891 ALM, real working
hypothesis centered on clock-network promotion at scale) -- awaiting
the real N=100 data point, fitter still running as of this entry.

## Previous state (2026-08-31, real clock-generator clarification + a real architectural connection logged -- clock-enable fix -> genuine hardware single-step -> future card-targeting workbench mode, see `points.md` #559. Real 500-cell ALM-fanout mystery still open, awaiting the 100-cell data point)

## Read this first (most recent)

**2026-08-31, real clock-generator clarification + a real architectural
connection.** Confirmed by checking real docs: the programmable clock
generator Alan remembered (MS5351) belongs to the Tang Nano 20K
(`#327`, never purchased), not the current Mustang-F100-A10, which has
no documented programmable oscillator. A separate real mention
("motherboard clock generator") is the PCIe REFCLK, unrelated.

Real, useful connection surfaced instead: a clock-enable design (a
candidate fix for the real 500-cell ALM-fanout mystery still under
investigation) would also give genuine, JTAG-driven single-step control
of the fabric. Alan's own real point: once built, this belongs exposed
in a future card-targeting workbench mode, mirroring the speed control
the VM-targeting workbench already has today.

Full detail: `points.md` `#559`.

**Real, honest scope: nothing built, no code changed.** Connects real,
separate threads that were sitting apart. The real 500-cell ALM-
fanout investigation itself remains open -- N=1 confirmed clean
(144.8 ALM/cell, no problem), N=500 catastrophically inflated
(476,891 ALM, ~3x too high even accounting for genuine all-8-cores
preservation), real hypothesis is clock-promotion at scale
(`div_cnt[1]` used directly as `clk`, 292K max fan-out reported at
N=500 vs 197 at N=1). Awaiting a real N=100 data point (currently
compiling) to distinguish a sudden cliff from gradual scaling before
committing to a specific fix.

## Previous state (2026-08-31, real help icons wired into every front-end page, opening this project's own existing docs at the relevant section -- regenerated fresh every request, stdlib-only, see `points.md` #558)

## Read this first (most recent)

**2026-08-31, real "one button reuse of something built" help
system.** `tools/manual_generate_v1.py` (new) -- a real, minimal,
stdlib-only Markdown-to-HTML converter (deliberately no external
dependency, matching every other tool built this session), converting
this project's own EXISTING real docs into one browsable manual with
real, stable, slugified per-header anchors. `nano/frontend_v1.py`
updated with a real `/manual` route (regenerated fresh from the
current repo state on EVERY request, never cached or drifted) and a
real, reused help icon on every page, each linking to the genuinely
relevant real section -- confirmed end to end, not assumed: every
page's own help link checked against the correct real anchor, and
`/manual` confirmed to serve real, correctly-anchored content live.

One real bug found and fixed: the sidebar table of contents initially
showed raw, unconverted Markdown (literal backticks) because it used
header text directly instead of running it through the same inline
conversion the section headers themselves already got.

Full detail: `points.md` `#558`.

**Real, honest scope:** the Walker page's own help link has no perfect
match among the 6 curated docs (`#501`'s design lives in `points.md`,
not currently a manual source) -- pointed at the closest genuinely
relevant section rather than force a misleading link.

## Previous state (2026-08-31, the real "main front end" built and verified -- nano/frontend_v1.py, 4 real pages, 2 honest placeholders, plus the first real MAN file generator, see `points.md` #557)

**2026-08-31, real front end built and verified.** `nano/frontend_v1.py`
reuses `workbench_v1.py`'s own proven Controller/Handler architecture.
Four real, working pages (welcome, MAN generation, cell creation
wrapping `project_assemble_v1.py`, a menu linking to the real
workbench/compiler), two honest placeholder slots (Walker, Composer)
that state plainly "not built yet" and cite their own real design
docs rather than faking functionality. `tools/man_generate_v1.py`
built alongside it -- the first real MAN file generator this project
has had (the existing MAN file was hand-assembled).

Verified two real ways: Controller methods called directly and
confirmed to write real, correct files; the full HTTP server started,
all 5 routes checked for a real 200, and a real POST form submission
confirmed end to end. `project_assemble_v1.py` refactored
(`assemble()` extracted) so the CLI and frontend share one real code
path, never a duplicate.

Every real action page also shows its exact CLI equivalent, generated
from the same real values just submitted, per Alan's own explicit
request.

Full detail: `points.md` `#557`.

**Real, honest scope still open:** Walker and Composer slots exist
structurally but have zero real backend -- gated on `#501`'s design
being built and a real Composer scoping decision.

## Previous state (2026-08-31, real ISSP debug probe added to the generator BEFORE the next build, not after -- avoids a second ~2-hour rebuild just for JTAG confirmation, see `points.md` #555)

## Read this first

**2026-08-31, ISSP probe added proactively to the generator.** Alan's
own practical question -- add a probe now, in case the fix works, so
a real silicon check doesn't need its own separate rebuild -- answered
by doing it. `tools/project_assemble_v1.py` now generates `debug_issp_
probe_v1.v` into the output, wires it in, and includes `issp.qsys` in
the `.qsf`. `probe[0]=array_alive` (the real anti-pruning signal),
`probe[1]=heartbeat`. Re-verified functionally at both N=9 and the
real N=500 target.

Full detail: `points.md` `#555`.

## Previous state (2026-08-31, real bug found and fixed in the 500-cell generator -- Alan's real Quartus build came back at a catastrophic 13 ALM, root cause precisely diagnosed and fixed, re-verified at both small and full scale before handing back, see `points.md` #554)

**2026-08-31, real bug found and fixed in `#552`'s own generator.**
Alan's real 500-cell Quartus build came back at 13 ALM -- Quartus
correctly reported real "Stuck at GND" warnings on internal registers
across the whole design. Root cause found precisely: the generator's
own `cfg_valid=1'b0` hardcoded on every cell meant Quartus could PROVE
every cell's `SUPER_LATCH` register never left its reset value -- a
huge network of provably-IDENTICAL, fully-determined logic, exactly
what Boolean synthesis collapses aggressively, not the ordinary
dead-code pruning `#552`'s own anti-pruning defense guarded against.

**Real fix:** a genuine, one-shot, broadcast config-load pulse fires
`cfg_valid` exactly once, simultaneously to every cell, loading a real
`core_select` value from a new, genuinely unconstrained top-level
input Quartus cannot predict -- so it can no longer prove which of the
8 real cores ends up selected for any cell, and cannot collapse any of
them away.

**Re-verified functionally, not just re-compiled, at both N=9 and the
real N=500 target:** the broadcast pulse fires exactly once, and every
tested cell -- including the actual last cell generated at each scale
-- correctly loads its own `core_select`.

Full detail: `points.md` `#554`.

**Real, honest scope: closes the specific mechanism found this time,
does not guarantee no other surprise exists at this scale.** Real next
step unchanged: Alan's own real Quartus build, now against the
corrected generator.

## Previous state (2026-08-31, real documentation catch-up -- both README.md and tools/README.md were genuinely stale, both rewritten to reflect the real, current project state, see `points.md` #553)

**2026-08-31, real doc catch-up.** `README.md` still described the
original 6-core shell with numbers from early in the project's
history (213 ALM/200.76 MHz), predating branch cell/sequencer/this
session's own field extensions entirely. Updated with a real table
covering all three shell versions' current numbers, the session-wide
ISSP-based silicon confirmation work, and a new section covering the
real DSP/BRAM hard-IP wrappers (both silicon-confirmed, honest DSP
soft-logic caveat included), MAN/SHAPE/placement tooling, and the new
`project_assemble_v1.py` generator.

`tools/README.md` only ever documented the onion submodule --
`shape_extract_v1.py`, `placement_extract_v1.py`,
`chaos_topology_v1.py`, and the new generator were entirely
undocumented. Rewritten to cover all five real tools with real scope
and honest limitations.

Full detail: `points.md` `#553`.

## Previous state (2026-08-31, real new tool built: tools/project_assemble_v1.py -- generates a complete, Quartus-importable N-cell array from a MAN file, verified at both N=9 and the real N=500 target, one real bug caught before it reached Quartus, see `points.md` #552)

**2026-08-31, the real "initial creator" tool built and verified.**
`tools/project_assemble_v1.py` (`--man <path> --cells <N>`) --
distinct from Composer (visual placement-review only, RTL generation
explicitly out of scope) and the Walker (live discovery, gated on this
build existing). Generates real source files + generated top-level RTL
+ matching `.qsf`/`.sdc`, all confirmed to compile at both N=9 and the
real N=500 target.

**A real, already-known risk designed against directly:** Quartus
prunes logic it can prove unreachable (confirmed twice already this
session, `#528`/`#550`) -- guarded against the same way every self-
test did it, scaled up: one real, unconstrained entry input, one real
XOR-reduced output covering every cell, so nothing can be pruned away.

**A real bug caught before Quartus:** the generator initially read the
`FAMILY` string straight from the MAN file (`"Arria 10 GX"`) -- every
proven, working `.qsf` actually uses `"Arria 10"`. Fixed, documented
in the code so it doesn't silently regress.

**Real verification performed:** hand-checked both a corner cell and
a fully-interior cell's own real wiring in a 3x3 test array --
structurally correct, not just "it compiled."

Full detail: `points.md` `#552`.

**Real, honest scope still open:** never run through an actual
Quartus build yet -- no real ALM/Fmax number exists for a genuine
500-cell array. That's the real next step. DSP/BRAM set-piece
integration not yet wired into the generator either.

## Previous state (2026-08-31, real correction: this session's own picture of the shape/placement tooling was incomplete -- confirmed the current extractor is NOT the real Walker; Alan's own precise description matches #501's already-converged design from 6 days earlier, now with a real, concrete justification layer added on top, see `points.md` #551)

**2026-08-31, real correction + real connection to #501.** This
session's earlier framing of `tools/shape_extract_v1.py` as "the
Walker" was incomplete -- it's real, but pure RTL-source analysis; the
Quartus fitter doesn't respect that map at all, and `CELL_ID` values
aren't guaranteed consistent enough to trust a static map as ground
truth. Alan's own precise, independent description of how the real
Walker needs to work matches `#501`'s own already fully-converged
design from six days earlier almost exactly: `core_select=31`
discovery sentinel, live cardinal-port ping-relay (self answers,
direction relays unchanged, one real hop at a time), real header cells
identifying specialist hardware (BRAM/DSP) on its behalf.

**Real addition on top of `#501`'s own design:** the concrete
justification for why live discovery is required, now doubly
validated by this session's own real, lived evidence -- `#445`'s own
"compiled then forgot to program" bug and `#535`'s own stale-Quartus-
project saga are both real demonstrations of "what should be on the
chip" diverging from "what's actually there," exactly the failure mode
live-only discovery makes structurally impossible.

Full detail: `points.md` `#551`.

**Real, honest scope: still nothing built.** `#501`'s design remains
the real plan; genuinely gated on the full-card build providing a real
target worth walking.

## Previous state (2026-08-31, REAL PASS: branch cell confirmed working through core_select routing in the real 8-core v3 shell -- both #548 targets now closed, plus a real architectural finding about nano's own non-prunability, see `points.md` #550)

**2026-08-31, real branch cell pass through the v3 shell, on silicon.**
`quartus_stp -t debug_issp_poll.tcl` against the real, programmed
`top_super_v3_branch_test_v1`: heartbeat changed 6 times across 15
reads, `err_sticky=0` throughout. REAL PASS -- branch cell's
held-reference capture, per-outcome routing, and genuine suppression
all confirmed correct through the real shell's own `core_select`
routing. `clk_div` real Fmax: 312.7 MHz.

**Real, predicted-in-advance pruning, confirmed exactly:** 131 ALM
total, but only branch cell (16.0 ALM in-shell, vs 12.7 standalone)
and nano (9.8 ALM) show up in the shell -- every other core correctly
pruned since `core_select` never left `SEL_BRANCH`, matching `#528`'s
own mechanism.

**A real, genuinely interesting finding this surfaced:** nano is
structurally NOT prunable the way every other non-selected core is --
its own `ready` bit broadcasts unconditionally on all 4 cardinal ports
regardless of `core_select`, so Quartus can never prove its logic
dead. A real, structural asymmetry, not a one-off.

Full detail: `points.md` `#550`.

**Both of `#548`'s new targets now confirmed** -- comparator (`#549`)
and branch cell through the v3 shell (this entry). The v3 shell's own
real "all 8 cores coexisting" ALM figure remains deliberately
unmeasured, per Alan's own call: build it only if that specific number
is ever actually needed.

## Previous state (2026-08-31, REAL PASS: comparator's own >= logic confirmed on silicon, first-ever standalone target, tiny 3.0 ALM real footprint, see `points.md` #549)

**2026-08-31, real comparator pass on silicon, first standalone
confirmation.** `quartus_stp -t debug_issp_poll.tcl` against the real,
programmed `top_compare_test_v1`: heartbeat changed 7 times across 15
reads, `err_sticky=0` throughout. REAL PASS -- comparator's real `>=`
logic (both outcomes) confirmed correct on silicon for the first time
standalone. Real footprint: only 3.0 ALM for the actual logic (96 ALM
total, rest is JTAG/ISSP overhead) -- the smallest core measured this
session. Real Fmax: `clk_div` 400.16 MHz, the fastest build this
session.

Full detail: `points.md` `#549`.

**Real, honest scope: 1 of `#548`'s 2 new targets confirmed.**
`top_super_v3_branch_test_v1` (the 8-core v3 shell) remains open.

## Previous state (2026-08-31, two new real Quartus build targets ready -- comparator's first standalone self-test, and the v3 8-core shell's first real attempt (branch cell through core_select), both ISSP-equipped from the start, see `points.md` #548)

**2026-08-31, two new real build targets ready for the next build
cycle.** `top_compare_test_v1.v` -- comparator's first-ever standalone
Quartus target (real cost only ever measured within the shell so far);
tests both real comparison outcomes (threshold=8, A=10 and A=5).
`top_super_v3_branch_test_v1.v` -- the first real Quartus attempt for
the 8-core v3 shell, focused on branch cell through `core_select`
routing (the genuinely new thing needing confirmation), reusing the
exact real design already confirmed on silicon standalone (`#530`/
`#541`). Both sim-verified clean, both ISSP-equipped from the start
(matching `#528`/`#529`/`#537`'s own hard-won lesson), matching `.sdc`/
`.qsf` files built on `#538`'s proven flat-file template.

Full detail: `points.md` `#548`.

**Real, honest next step, Alan's own stated order:** comparator and v3
first (last of the individual-core/shell builds), then a full card
build (500+ cells) as the real target everything downstream (the
Walker, JTAG burst mode, ICM load/unload) depends on.

## Previous state (2026-08-31, a real, long-standing intent named explicitly -- a future compiler stage lowering real programs directly onto the substrate via LLVM IR, built from already-proven composable primitives rather than synthesized from scratch, see `points.md` #547)

**2026-08-31, real future architecture thread named: LLVM IR ->
substrate compiler.** Alan's own long-standing intent, named explicitly
for the first time: could real programs (not just hand-written
Unicell-S) compile directly onto the substrate? Checked against real
prior art before treating this as tractable -- distinguishes binary
translation (QEMU/Rosetta 2, doesn't apply, both sides need the same
PC/register/addressed-memory shape UniCell deliberately lacks) from
High-Level Synthesis (Vitis HLS/Intel HLS Compiler -- the real field
this actually belongs to, genuinely hard even after decades of
industrial investment, mainly on unbounded loops/recursion/dynamic
allocation).

**Real, concrete refinement: LLVM IR, not raw machine code** -- already
closer to SSA/dataflow form, already what Vitis HLS itself uses
internally, and a genuinely bounded program subset (static loops, no
recursion, no dynamic allocation) matches the FlowTrix/LBM demo's own
already-standing shape.

**Alan's own additional, load-bearing refinement:** the compiler
should draw from this project's own already-proven library of
composable patterns (the T-tree, `#544`'s lane-split-merge, branch
cell's held-reference classification, the cascade counter/multiply/
divide compositions) rather than synthesizing novel hardware from
scratch for each IR construct -- "recognize the pattern, instantiate
it," a natural extension of `#514`'s own standing Tile Designer thread.

Full detail: `points.md` `#547`.

**Real, honest scope: named, not built.** A real, substantial future
thread now sitting in the ledger with real prior art cited on both
sides.

## Previous state (2026-08-30, the real 1->3->9 T-tree from #545 built and proven in the VM -- a real geometric collision found and fixed BEFORE running anything, by checking the layout programmatically first, see `points.md` #546)

**2026-08-30, real T-tree broadcast proven, 9 leaves, equal depth.**
`tests/vm/test_t_tree_broadcast_v1.py`, 2/2 passing: 16 real cells (1
root + 3 branches + 3 relay + 9 leaves), quiesces in 4 ticks, every
leaf shows the exact broadcast value -- `#545`'s own 1-in-3-out,
recursed-to-9 design principle, built for real.

**A real geometric collision found and fixed BEFORE it cost a wasted
run** -- directly validating `#545`'s own pentacross-era
"embeddability" concern in practice: a naive tight embedding causes
diagonal sibling branches to collide at shared corner positions (the
north branch's own east child and the east branch's own north child
land on the same cell). Fixed with one extra "runway" hop per branch
before fanning out -- keeps every leaf at the same total depth (3
hops), preserving `#544`'s own equal-path-length requirement.
Verified programmatically (all 16 positions distinct, every edge
genuinely cardinal-adjacent) BEFORE running the simulation -- passed
cleanly on the first real attempt, a direct payoff of checking geometry
first rather than debugging it against the VM by trial and error.

Full detail: `points.md` `#546`.

**Real, honest scope: proves the down-broadcast half.** The mirrored
up-merge half (9 leaves recombining back through 3 mergers into 1) is
a real, separate next step, not built here. VM only -- no real
Verilog testbench yet.

## Previous state (2026-08-30, real T-tree design principle logged, and a real, precise continuity found back to the pre-nano pentacross design, see `points.md` #545)

**2026-08-30, T-tree design principle + pentacross continuity.** A
real design principle derived from `#544`'s own constraint: every
cell has 4 cardinal ports, one spent on the parent link, leaving
exactly 3 free -- a forced T shape, giving powers of 3 through
recursion. A real, precise continuity found back to the pre-nano
"pentacross placement" rule -- same plus-shaped geometry, forced by
the same 4-port constraint, solving two genuinely different problems
51 days apart (bus contention in the old architecture vs. hop-count
synchronization in the current one). Full detail: `points.md` `#545`.

## Previous state (2026-08-30, Alan's real lane-split/recombine architecture idea proven in the VM both ways -- correct recombination with equal hop counts, real silent data loss AND non-quiescence with mismatched ones, see `points.md` #544)

**2026-08-30, real lane-split/recombine mechanism proven, zero new

**Alan's own real insight -- equal hop counts on every path is a hard
correctness requirement, not tidiness -- confirmed directly against
the RTL** (RAM's `!data_valid` capture gate blocks any arrival once
one direction is already captured) and proven both ways in
`tests/vm/test_lane_split_recombine_v1.py` (2/2 passing): a positive
case (6 real cells, both lanes exactly 3 hops, correctly reconstructs
`0x11223344` from independently-masked high/low halves) and a
negative case (mismatched 1-hop vs 2-hop paths) showing BOTH real
failure modes at once -- the merge cell settles on only the shorter
lane's value, and the system never reaches quiescence.

**A real bug found and fixed along the way:** the broadcast source was
initially configured `fixed_mode=1` (RAM's real "offer forever"
semantic), causing perpetual re-transmission. Fixed to `fixed_mode=0,
load_data_valid=1` -- a genuine one-shot preload.

Full detail: `points.md` `#544`.

**Real, honest scope: proves the 2-lane case.** The 4-lane (matching
RAM's real 4-port limit) and 8-lane (needing a real 2-stage OR-tree)
versions are designed and understood but not yet built. No real
Verilog testbench exists yet either -- VM only so far.

## Previous state (2026-08-30, full VM sync complete -- branch cell wired into a real RTL slot (#542), then this session's own new fields (adder subtract, latch toggle, nano's exposed ports) synced across icm_v3.py and the VM, a real cell_type bug fixed, a working end-to-end create/save/reload demo built, and SUPER_CELL_INTERNALS.md fully rewritten, see `points.md` #543)

## Read this first

**2026-08-30, full VM/doc sync following #542's real branch cell RTL
addition.** Alan's own explicit ordering: wire branch cell in first,
then sync the VM (all parts), then the docs. All three done.

**VM sync:** `icm_v3.py` and `unicell_super_automaton_v1.py` now fully
implement adder's `subtract_mode`, latch's `toggle_dir` (full `CLEAR>
SET>TOGGLE` chain), and nano's 5 exposed ports (`hold_in`/`fb_
internal_in`/etc -- a real, honest finding: `CACell` already fully
implemented all 5, this was purely a passthrough gap). Branch cell's
own "VM-provisional" comments corrected to reflect `#542`'s real RTL
slot -- its dispatch logic was already correct.

**A real, structural gap found and handled honestly:** nano's 5
exposed ports are real ports, not part of nano's own cfg_data field
map, physically separated from it in the RTL -- the mechanical
extractor genuinely cannot see them. Fixed with a manual, explicitly-
warned addition to `root_definition.json` (confirmed the warning is
necessary by triggering the wipe once and having to redo it). Also
found `root_definition.json` had never been regenerated since `#521`/
`#522`'s own RTL changes at all -- fixed.

**A real bug found and fixed in `icm_v3.py` itself:** `IcmV3File`'s
own `cell_type` field was hardcoded to `"unicell_super_v1"` regardless
of what cores a saved file actually used. Fixed with a real, computed
`minimum_shell_version()` -- 4 new tests confirm v1/v2/v3 detection
works correctly, including mixed-core files.

**The real "create, save, reload, run" workflow Alan asked for, now
working end to end:** `nano/example_icm_branch_demo_v1.py` -- builds a
real 2-cell program, saves the exact 80-bit `super_latch_hex` words a
host bridge would write to the board, reloads from disk as a genuinely
separate object, and confirms real behavior reproduces correctly from
the reloaded data alone.

**10 new real regression tests, 345/345 passing** (up from 335).
`docs/stripped-cell/SUPER_CELL_INTERNALS.md` fully rewritten -- all
three shell versions, every new field, honest verification status per
version.

Full detail: `points.md` `#543`.

**Real, honest scope still open:** sequencer's own real-RTL-zero-VM-
dispatch gap remains untouched. No real Quartus/silicon data for the
8-core v3 shell yet. `addon_config`'s own field table remains hand-
typed and mechanically unvalidated (pre-existing, separate gap).

## Previous state (2026-08-30, MILESTONE: all 5 of #523's self-tests confirmed, alias-free, on real silicon -- branch cell, accumulator pulse mode, adder subtract, nano feedback, latch toggle, see `points.md` #541)

**2026-08-30, THE FULL SWEEP: all five real self-tests confirmed on
actual silicon.** `quartus_stp -t debug_issp_poll.tcl` against the
real, programmed `top_latch_toggle_test_v1`: heartbeat changed 7 times
across 15 reads, `err_sticky=0` throughout. REAL PASS -- `#522`'s
toggle_dir field, including the full `CLEAR>SET>TOGGLE` priority
chain, confirmed correct on real silicon. `clk_div` real Fmax: 373.0
MHz, the fastest of all five self-tests (matching latch's own
smallest, simplest real footprint).

**This closes out `#523`'s entire self-test arc.** Every real
capability added to this project's core set this session -- branch
cell (`#500`-`#520`), accumulator's `step_amount`/`pulse_mode`
(`#515`), adder's `subtract_mode` (`#521`), latch's `toggle_dir` and
nano's exposed `hold_in`/`fb_internal_in` (`#522`) -- now has real,
independent, LED-agnostic, alias-free confirmation on actual hardware.
Full accounting, including the real bugs found and fixed along the
way (wrong LED pins `#528`, a nastier-than-expected stale Quartus
project `#535`, a real aliasing bug in the diagnostic tooling itself
`#537`): `points.md` `#541`.

**Real, honest scope still open, not implied finished:** the two full
super-carrier shells (v1/v2) still only have LED-based confirmation
attempted, never the reliable ISSP-based check -- the natural next
step. `unicell_super_v2.v` still has no dedicated testbench. Every
other standing roadmap item (ICM-level construction, shared-BRAM
wiring, the recombiner, decimal-division design, standalone shift
wrapper, branch cell's own real super-shell slot, VM/ICM sync for this
session's new fields, the funded-hardware-dependent ADC/ESP testbed)
remains exactly where it was.

## Previous state (2026-08-30, REAL PASS: nano's exposed hold_in/fb_internal_in confirmed on silicon -- closing the retroactive "was it ever really stuck" question, see `points.md` #540)

**2026-08-30, real nano feedback pass on silicon -- closes a real
open question.** `quartus_stp -t debug_issp_poll.tcl` against the
real, programmed `top_super_nano_feedback_test_v1`, built with
`#538`'s proven QSF template: heartbeat changed 7 times across 15
reads, `err_sticky=0` throughout. REAL PASS -- `#522`'s exposed
`hold_in`/`fb_internal_in` ports confirmed correct through the real
shell.

**This is the exact same design that showed "stuck" three times in
`#535`.** Now, tested with the poll script from the start, it's
definitively alive -- confirming directly that the earlier result was
`#537`'s own aliasing artifact, not a real fault. `clk_div` real Fmax:
316.26 MHz, over 12x margin.

Full detail: `points.md` `#540`.

**Real, honest scope: 4 of 5 self-tests from `#523` now confirmed**
(branch cell `#530`, accumulator pulse mode `#537`, adder subtract
`#539`, nano feedback `#540`). Only latch toggle remains.

## Previous state (2026-08-30, REAL PASS: adder subtract_mode confirmed on silicon -- clean, alias-free from the start using the proven QSF template and poll-based diagnostic, see `points.md` #539)

**2026-08-30, real adder subtract_mode pass on silicon, clean this
time.** `quartus_stp -t debug_issp_poll.tcl` (15 reads, 500ms apart)
against the real, programmed `top_adder_subtract_test_v1`, built
fresh with `#538`'s proven flat-file QSF template: heartbeat changed 7
times across 15 reads, `err_sticky=0` throughout. REAL PASS -- `#521`'s
subtract_mode confirmed on real silicon.

**Real, clean confirmation, no aliasing detour needed:** unlike
accumulator pulse mode (`#537`), this build went straight to the poll
script from the start and showed genuine toggling immediately --
confirming both the design AND that `#538`'s proven QSF template is a
reliable, repeatable real process now, not a one-off.

Full detail: `points.md` `#539`.

**Real, honest scope: 3 of 5 self-tests from `#523` now confirmed**
(branch cell `#530`, accumulator pulse mode `#537`, adder subtract
`#539`). Latch toggle and nano feedback remain open -- nano feedback's
own prior "stuck" result is still suspected to be the same aliasing
artifact `#537` found, not yet independently re-confirmed.

## Previous state (2026-08-30, REAL PASS: accumulator pulse_mode confirmed on silicon + a real aliasing bug found and fixed in the read script itself, see `points.md` #537)

**2026-08-30, real accumulator pulse_mode pass on silicon, plus a real
diagnostic-tooling bug found and fixed.** `quartus_stp -t debug_issp_
poll.tcl` (15 reads, 500ms apart) against the real, programmed
`top_accumulator_pulse_mode_test_v1`: heartbeat changed 6 times across
15 reads, `err_sticky=0` throughout -- REAL PASS, `#515`'s reset-
after-fire pulse mode confirmed on real silicon.

**Real, valuable root cause found along the way:** the ORIGINAL
`debug_issp_read.tcl` (fixed 2-second gap between its two reads)
reported this same design as stuck, three separate times. Real
finding: the design's own real toggle period is close to 2 seconds --
nearly matching the script's own fixed gap, causing classic ALIASING
(the same phenomenon that makes a spinning wheel look stationary under
a strobe light at the wrong frequency). The design was never stuck;
the read script was structurally vulnerable to this the whole time.
**This very likely explains the earlier nano feedback "stuck" result
too, retroactively** -- same script, same vulnerability, never
re-tested with the new poll-based script before Quartus project chaos
consumed the rest of that session. Nano feedback's own real status is
now understood as "needs a poll-based re-test," not "might be broken."

**Real, general fix:** `debug_issp_poll.tcl` (many reads over a
varied-interval, genuinely long window) is now the recommended PRIMARY
diagnostic for any new self-test's first real hardware check --
`debug_issp_read.tcl` kept only for quick sanity checks once a
design's real behavior is already independently understood.

Full detail: `points.md` `#537`.

**Real, honest scope: 2 of 5 self-tests from `#523` now have real,
alias-free functional confirmation on silicon** (branch cell `#530`,
accumulator pulse mode this entry). Adder subtract, latch toggle, and
nano feedback remain open -- all three should be re-tested with
`debug_issp_poll.tcl` specifically, not the older fixed-gap script.

## Previous state (2026-08-29, real ISSP debug channel extended to all 4 remaining self-tests -- every one of #523's 5 self-tests now has the same LED-independent, JTAG-readable confirmation path branch cell just proved, see `points.md` #531)

**2026-08-29, ISSP probe extended to the remaining 4 self-tests.**
`debug_issp_probe_v1.v` (`#529`) wired into accumulator pulse mode,
adder subtract, latch toggle, and nano feedback -- identically to how
it was wired into branch cell, which just proved the whole pattern
works end-to-end on real silicon (`#530`). All 4 sim-verified clean
with the matching stub; all 4 correctly require the real `issp` module
for synthesis, matching branch cell's own proven behavior exactly.
QSFs updated for all 4.

Full detail: `points.md` `#531`.

**Real, honest scope still open:** none of the 4 have been run on real
hardware with this probe yet -- real, remaining work for whenever Alan
next has time at the board. `debug_issp_read.tcl` works identically
for all 5 self-tests without any changes needed.

## Previous state (2026-08-29, REAL FUNCTIONAL CONFIRMATION on real silicon -- branch_cell_v1.v's held-reference mechanism and per-outcome table, including genuine suppression, is CORRECT on real hardware. The single biggest unknown this project has carried all session is now closed, see `points.md` #530)

**2026-08-29, real, complete, unambiguous PASS on real silicon.**
`quartus_stp -t debug_issp_read.tcl` against the real, programmed
`top_branch_cell_test_v1` bitstream: heartbeat genuinely changed
between two reads 200ms apart (ruling out "passed because it never
got far enough to fail"), `err_sticky=0` on both reads (no error ever
latched across the full real test sequence: seed reference=8, LOW=5
fires with its own marker, EQUAL=8 fires with its own marker, HIGH=10
genuinely suppressed over a real 32-cycle window).

**Real, honest significance:** `branch_cell_v1.v` had never touched
real hardware in any form before this session. `#528` closed the
resource/timing half of that unknown (12.7 ALM, 364.3 MHz). **This
entry closes the functional half** -- the core's own real mechanism is
now confirmed correct on actual silicon, not just simulated, not just
"compiled without errors." First core in the entire composed-
application arc (`#516`-`#521`, all built on this core) to get this
level of independent, LED-agnostic hardware confirmation.

Full detail: `points.md` `#530`.

**Real, honest scope still open:** the other 4 self-tests from `#523`
(accumulator pulse mode, adder subtract, latch toggle, nano feedback)
only have LED-based confirmation attempted so far, not this same
ISSP-based confirmation -- given `#528`'s still-open LED-wiring
uncertainty, whether they genuinely passed on silicon remains open too.

## Previous state (2026-08-29, real ISSP debug channel wired into the branch cell test -- a JTAG-readable pass/fail independent of the still-open LED-wiring question, see `points.md` #529)

**2026-08-29, real ISSP debug channel added.** `#528` surfaced a real,
still-open uncertainty: `LED0_N`/`LED1_N`'s pin locations are confirmed
correct in the FPGA's own pin file, but whether the actual PCB has
visible LEDs wired to those pins was never independently confirmed
(this project's own manifest already flagged this exact caveat).
Rather than keep debugging an LED that might not physically exist,
`debug_issp_probe_v1.v` (new, minimal, reusable -- 2-bit read-only
probe: `err_sticky` + `heartbeat`) wired into `top_branch_cell_test_v1
.v`, giving a real, JTAG-readable pass/fail via `quartus_stp` that
doesn't depend on the LED question at all. `debug_issp_read.tcl` reads
it, deliberately twice ~200ms apart, requiring the heartbeat to
genuinely change before trusting a pass (a static `err_sticky=0` alone
can't distinguish "passed" from "frozen before checking anything").

**Alan's own real generated IP config (`issp.qsys`/`.sopcinfo`,
uploaded) confirmed to already match exactly what was needed --
`probe_width=2`, `source_width=1`, `create_source_clock=false` -- zero
regeneration required.** That last setting means the generated `issp`
module has only 2 ports (no `source_clk`), confirmed directly from the
real `.qsys` XML before writing the wrapper, not assumed from the
existing (differently-configured) sentinel bridge.

Full detail: `points.md` `#529`.

**Real, honest scope still open:** only branch cell has this wired in
so far (the other 4 self-tests from `#523` don't yet). Alan's own real
generated `issp` HDL output still needs adding to the Quartus project
-- not tracked in this repo, same convention as `issp.qsys` itself.

## Previous state (2026-08-29, real first Quartus results for all 5 of #523's new self-tests -- branch_cell_v1.v's own first-ever real number, 12.7 ALM -- plus a real, project-wide LED pin-assignment bug found and fixed, see `points.md` #528)

**2026-08-29, real Quartus data for all 5 new self-tests, all Flow
Status Successful.** Standalone ALM/Fmax: accumulator pulse mode 52.7
ALM/161.89 MHz, adder subtract 22.7 ALM/300.93 MHz, latch toggle 3.0
ALM/375.66 MHz, nano feedback through the shell 16.2 ALM/337.61 MHz
(real caveat: `core_select` never changes in this test, so Quartus
could prune the other 6 cores entirely -- `#524`/`#526`'s 31.3-35.2
ALM remains the fairer "nano coexisting" reference). **`branch_cell_
v1.v`: 12.7 ALM, 364.3 MHz -- the first real number this core has
EVER had, on any hardware.** Genuinely small and reassuring.

**A real, project-wide, pre-existing bug found and fixed:** Alan
programmed all 5 onto the real board, saw no LED activity. Root cause:
`LED0_N`/`LED1_N` were never given real physical pin assignments in
ANY of 37 top-level self-test QSF files across this project's entire
history -- confirmed by direct search, including files already used
THIS session. Quartus auto-assigns some pin so the build still
succeeds, almost certainly not the board's real LED pins (`AE7`/`AH2`
per the official pin file). The designs were very likely running
correctly the whole time -- the LED signal just never reached a real
LED. Fixed: new QSF files for all 5 new self-tests with the real pins
added, plus the two already-tested targets sharing the gap (super-
carrier v2, adder-chain50) and a missing super-carrier v1 QSF that
never existed in the repo at all. Deliberately NOT fixed: ~32 other
historical files sharing the same gap -- flagged, out of scope without
Alan's own direction.

Full detail: `points.md` `#528`.

**Real, honest next step:** re-run with the corrected QSFs and confirm
LED1_N genuinely stays dark on real hardware -- the actual functional
pass/fail these self-tests exist to provide, still not yet obtained.

## Previous state (2026-08-29, ESTIMATE ONLY -- rough card capacity at current shell size, ~620-880 cells depending which per-cell figure applies, DSP path unresolved -- see `points.md` #527)

**2026-08-29, capacity ESTIMATE, not a real measurement.** Computed
from `#526`'s own real single-shell v2 data plus this project's own
established 75% realistic-utilization ceiling: ~619 cells using the
conservative whole-self-test-build figure (305 ALM), or ~881 using
just the shell's own DUT-level cost (214.3 ALM, excluding one-time
self-test FSM overhead). Alan's own "around 650" lands on the
conservative side -- a reasonable real estimate, not a wild guess.

**Two real, explicitly-flagged, currently-unresolved dependencies:**
(1) which of the two per-cell figures is actually right for a genuine
multi-cell array is unknown without building one (the old full-fat
cell got its own real number from an actual 750-cell build, `#247`;
the new shell architecture hasn't had that yet). (2) the DSP path --
1,687 hard DSP blocks sit at 0% utilization on every real build so
far; native hard-DSP floating point remains deferred until PCIe. If
math-heavy cores ever move onto real DSP silicon, this estimate could
shift meaningfully in either direction.

**LABELED CLEARLY AS AN ESTIMATE throughout -- not confirmed capacity.**
Full detail: `points.md` `#527`.

## Previous state (2026-08-29, real Quartus result for the 7-core super carrier shell (v2) -- 305 ALMs, 99.57 MHz real Fmax, genuinely LESS than a single old full-fat cell despite packing 7 real cores in, see `points.md` #526)

**2026-08-29, real Quartus result for v2 (7-core shell with
sequencer).** `top_unicell_super_test_v2`, SDC applied: 305 ALMs, 316
registers, real Fmax `clk_div` 99.57 MHz (~4x margin above the 25 MHz
target, lower than v1's own 129.48 MHz -- real, expected cost of a
wider `core_select` mux). Sequencer's own first-ever real ALM cost:
11.7 ALMs. Shell-level total (`unicell_super_v2:DUT`) 214.3 ALMs vs
v1's 176-178 -- most of the ~36-38 ALM growth is the wider mux, not
the sequencer's own logic.

**Alan's own real concern checked directly, not guessed at:** "getting
back to the full fat cell size." Found a real, measured number in the
project's own archived records: the ORIGINAL full-fat cell
(`unicell64_v3.v`) cost ~464 real ALMs per cell (measured directly,
full-card build), down from an earlier ~615 ALM estimate. **The real
comparison: v2's entire 7-core shell costs 305 ALMs total -- genuinely
LESS than a single old full-fat cell doing only one fixed function.**
Not a regression toward the old architecture -- the real, expected
cost of a 7th core, still well under what even one old cell cost.

Full detail: `points.md` `#526`.

**Real, honest scope still open:** the 5 new self-tests from `#523`
remain entirely unbuilt on real hardware. `branch_cell_v1.v`'s own
ALM/Fmax cost is still the single biggest unknown.

## Previous state (2026-08-29, real, trustworthy Fmax confirmed for the super carrier shell -- 129.48 MHz real, over 5x margin above the 25 MHz target, see `points.md` #525)

**2026-08-29, real SDC-constrained timing result.** `top_unicell_
super_test_v1` re-run with its own SDC properly applied this time:
233 ALMs, 257 registers, and for the first time this session a REAL,
trustworthy Fmax -- `clk_div` (the actual 25 MHz fabric clock) closes
at 129.48 MHz, over 5x real margin. `CLK_100M` domain (just the
divider register) closes at 584.8 MHz.

**A real, worth-recording clarification:** the previous run's own
1582.28 MHz / 645.16 MHz figures (`#524`) are now confirmed to have
been meaningless -- no SDC means no defined clock period to analyze
against, so Quartus reports a best-effort figure with no real meaning.
This run is the first trustworthy number, and "slower" here means
"real," not "the design got worse." A small ALM/register delta
between the two runs (237->233, 275->257) with zero RTL changed is
normal Quartus fitter run-to-run variance, not a functional
difference -- recorded honestly as such.

Full detail: `points.md` `#525`.

**Real, honest scope still open:** the 5 new self-tests from `#523`
(SDC-equipped per `#524`) remain entirely unbuilt on real hardware.
`branch_cell_v1.v`'s own ALM/Fmax cost is still the single biggest
unknown.

## Previous state (2026-08-29, first real Quartus result for the super carrier shell this session -- 237 ALMs, real hardware confirmed the build itself; SDC files built for all 5 new self-test tops so they don't hit the same gap, see `points.md` #524)

**2026-08-29, first real Quartus data point of this session.** Alan's
own real `top_unicell_super_test_v1` build: Flow Status Successful,
237 ALMs (<1% of 251,680), 275 registers, zero block memory/DSP/HSSI/
PLL usage. Real per-core ALM breakdown recorded as a baseline (no
pre-session number exists for comparison): accumulator 66.6, nano
31.3, adder 30.7 (carry chain alone 8.0), RAM 12.0, latch 8.7,
comparator 8.0.

**A real gap in this run, not the RTL:** no SDC file was applied
("NOTE NO SDC File") -- the reported Fmax figures are an unconstrained
default analysis, not real timing closure, matching this project's
own already-documented `derive_clocks` phantom-clock lesson. A real,
correct SDC already exists for this target (`top_unicell_super_test_v1
.sdc`) -- just needs to actually be applied on the next run to get a
trustworthy Fmax number.

**Gap closed the same session it was found:** none of `#523`'s 5 new
self-test tops had an SDC file yet either -- would have hit the exact
same issue. Five new SDC files built, all matching the established
explicit-clock convention. Full detail: `points.md` `#524`.

**Real, honest scope still open:** re-run `top_unicell_super_test_v1`
WITH its SDC applied for a real Fmax number. All 5 new self-tests from
`#523` remain entirely unbuilt on real hardware -- branch_cell_v1.v's
own ALM/Fmax cost is still the single biggest unknown.

## Previous state (2026-08-28, five new real Quartus self-test tops built for everything this session added that had never touched silicon -- plus a real bug caught before it could waste a real build, see `points.md` #523)

**2026-08-28, five new Quartus self-tests, sim-verified clean.** Real,
concrete build targets for every capability this session added that
had never been synthesized: `top_accumulator_pulse_mode_test_v1.v`,
`top_adder_subtract_test_v1.v`, `top_latch_toggle_test_v1.v`, `top_
super_nano_feedback_test_v1.v` (through the real shell), and `top_
branch_cell_test_v1.v` -- the single biggest gap closed here, since
`branch_cell_v1.v` had never touched real silicon in any form before
this, anywhere.

**A real bug caught BEFORE it could waste a real build**, not after:
the two existing super-carrier self-tests (`top_unicell_super_test_v1/
v2.v`) still had the exact truncated-accumulator-config bug already
fixed in the testbench back in `#515`, never propagated to these real
hardware-bound files -- would have silently failed on real silicon.
Both fixed.

**A real, reusable lesson from building the nano feedback test:** an
initial exact-per-cycle-phase check of a free-running oscillation was
wrong -- fragile, dependent on this FSM's own transition overhead, not
a meaningful hardware property. Corrected to a robust watch-window
(confirm both real values appear across a real cycle count) -- worth
using this same pattern for any future self-test of oscillating/
free-running real hardware behavior.

Full detail: `points.md` `#523`. **All 7 real build targets (5 new + 2
fixed) are sim-verified and ready for Alan's own real Quartus run --
ALM/Fmax numbers and real hardware confirmation still entirely open.**

## Previous state (2026-08-28, real latch TOGGLE input + nano's real hidden ports finally exposed through the super carrier shell -- #505's per-core review complete for this pass, see `points.md` #522)

**2026-08-28, real latch TOGGLE + nano port exposure, sim-verified
clean.** Latch: a genuine third trigger (`toggle_dir`), flips instead
of forcing, real `CLEAR > SET > TOGGLE` priority chain confirmed in
full (not just pairwise). Nano: `hold_in`/`fb_internal_in`/
`a_reemit_in`/`a_update_in`/`a_self_update_in` -- real, already-tested
ports (`#115`/`#118`/`#119`/`#120`), previously hardwired to constant
0 at the shell's own nano instantiation -- exposed via 5 new
`core_config` bits. Real, honestly-scoped limitation stated directly
in the RTL: this exposes the capability, not lightweight runtime
toggling (only refreshes on a full reconfigure).

**Two real bugs found and fixed while proving this actually works:**
(1) a real testbench-infrastructure gap -- `unicell_super_v1.v`'s own
`program_in`/`prog_*` ports were never tied off by the existing,
proven `tb_unicell_super_v1.v` either, just never surfaced since that
file's nano check is "sanity only." (2) A real, honest divergence from
the standalone feedback reference, root-caused not assumed: the
reconfigure needed to flip `fb_internal_in` on also resets
`out_buffer` (confirmed `data_reg`/`a_arrived` survive it, `out_buffer`
doesn't), so the internal feedback loop correctly settles into a
DIFFERENT 2-cycle oscillation than the standalone test's own
live-toggled version -- equally real, equally correct, just seeded
differently. New testbench `tb_super_nano_feedback_v1.v`, 7/7 passing.
Full detail: `points.md` `#522`.

**`#505`'s per-core review is now complete for this pass:** comparator
(closed), accumulator, adder, latch, nano's exposure all done. RAM
confirmed genuinely full (42/42 bits) -- nothing to build there without
restructuring.

## Previous state (2026-08-28, real ADD/SUBTRACT mode built for adder_cell_v1.v -- #505's per-core review continues, see `points.md` #521)

**2026-08-28, real ADD/SUBTRACT mode, sim-verified clean, zero new
arithmetic hardware.** `#505`'s per-core review picked back up: adder
had 8 of 42 `core_config` bits used before this (34 spare, checked
directly). `subtract_mode` reuses `adder_v1.v`'s own already-present
`cin`/`cout` ports (previously wired `cin=0` unconditionally) on the
SAME carry chain -- `subtract_mode=1` inverts B and sets `cin=1`,
computing A-B via ordinary two's complement. `tb_adder_cell_v1.v`:
10/10 checks (5 original ADD pairs unchanged, 5 new SUBTRACT pairs
including a real borrow, exact zero, and a reconfigure-back-to-ADD
check). A real wiring gap found and fixed proactively (before it could
cause a silent bug, not after) -- the exact same class of truncation
bug `#515`/`#519` already caught for the accumulator -- in both
`unicell_super_v1.v` and `unicell_super_v2.v`. Full detail: `points.md`
`#521`.

**A real, honest, deliberately-deferred design also logged this
entry:** Alan's own real long-division-to-decimal-expansion design --
`#518`'s halted division loop, resumed by scaling the remainder x10
and feeding it back in for another pass, one more digit each time.
Two real open questions correctly named as genuine design decisions,
not details: repeat detection needs the FULL remainder history, not
just the last 2-3 (periods up to divisor-1 digits long); and the x10
scaling step is a genuinely new composable piece (a runtime value,
not a host-known constant) -- solvable with zero new RTL via two
`shift_lane_addon_v1.v` relay stages (x8+x2) feeding this session's
own new subtract-capable adder. A real, currently-unresolved gap
surfaced by this design: `#518`'s own remainder was testbench-only
arithmetic, never a real wired hardware register -- would need
building for this loop to ever run in real hardware. Not built this
session, per Alan's own explicit "one step at a time" -- logged so the
design isn't re-derived from scratch later.

**Real, honest scope still open from `#505`'s own per-core review:**
latch (12/42 bits used, real toggle-input or sticky-VALUE-not-just-bit
possibilities identified), RAM (genuinely full, 42/42 bits, no
headroom without restructuring), nano (not spare bits -- already-built
real capability deliberately not exposed through the super shell's own
restricted field mapping, a different, already-known kind of gap).

## Previous state (2026-08-28, real VM/ICM sync -- accumulator's #515 fields fully wired, branch_cell_v1.v registered as a genuine VM-provisional core, see `points.md` #519; plus a separate, purely exploratory 3D VM thought experiment, `points.md` #520)

**2026-08-28, 3D VM exploration (`#520`), purely exploratory, zero RTL,
kept deliberately separate.** Real architectural question -- does a
6-cardinal (N/S/E/W/U/D) fabric unlock genuinely new shapes, or just
bigger versions of what 4-cardinal already does -- explored cheaply in
a standalone toy VM (`nano/experimental_3d_*.py`), not touching any
proven file. Two real findings: a genuine crossing shape with no 2D
equivalent (two relay paths cross in projection, sharing zero physical
cells); and a real, NOT-3D-specific finding that random directed
wiring readily creates cycles, causing a modest random grid to
oscillate forever rather than quiesce (4/4 seeds tried). Motivating
case: FlowTrix's own future D3Q19 ambition. Picked back up only if
that becomes concrete, or a system with real headroom for larger
grids is available. Full detail: `points.md` `#520`.

## Previous state (2026-08-28, real VM/ICM sync -- accumulator's #515 fields fully wired, branch_cell_v1.v registered as a genuine VM-provisional core, see `points.md` #519)

**2026-08-28, real VM/ICM sync, all 335 Python tests passing.** Picked
up on Alan's own explicit call ("update the VM first... gives you the
correct test area") before continuing further core work, after three
real composed applications (`#516`-`#518`) had built up real RTL
capability the VM didn't know about yet.

**Accumulator:** `step_amount`/`pulse_mode`/`threshold` (`#515`) fully
wired into `icm_v3.py`, `root_definition.json`, and `unicell_super_
automaton_v1.py`'s dispatch -- including the real reset-after-fire
semantics and a dynamic `is_continuously_live()` override for pulse
mode (the second core, after RAM's `fixed_mode`, to need one).

**Branch cell registered as a genuine VM core for the first time**
(`SEL_BRANCH=7`, VM-provisional -- no real RTL `core_select` slot
exists yet in any `unicell_super_*.v` file, honestly flagged
throughout rather than glossed over). Full `SuperCell` dispatch added
and confirmed working directly (reference seeding, per-outcome
routing, real multi-direction fan-out).

**Cross-validated against real RTL, not just internally consistent:**
the mechanical extractor + `validate_icm_v3_against_rtl_v1.py` both
extended to cover branch cell -- exact match, zero mismatches, for
both the extended accumulator table and the new branch table.

**Every real Python call site updated explicitly** (not left to
silently default to a broken `step_amount=0`) -- the VM dataclass
default was deliberately kept at real silicon's own honest reset value
(0), matching `#504`'s own established discipline. Touched: VM tests,
the tile library (accumulator's `step_amount` now a required param,
composed tiles fixed via `fixed_params`), codec round-trip tests, and
every compiler frontend's test suite plus the workbench's own demo.

Full detail: `points.md` `#519`.

**Real, honest scope still open:** `SEL_SEQ=6` (the sequencer, real
RTL since `unicell_super_v2.v`) still has no VM dispatch at all --
a pre-existing gap, mirror-image of branch cell's own real-VM-but-
no-RTL situation. Branch cell's own physical super-shell wiring
(a `unicell_super_v3.v`, matching the sequencer's "clone, don't
modify" precedent) remains separate, unstarted work.

## Previous state (2026-08-28, real division-via-repeated-subtraction built with feedback -- third and hardest of #506's composed applications, zero new RTL, see `points.md` #518)

**2026-08-28, real division via repeated subtraction with feedback,
sim-verified clean, zero new RTL.** The third and hardest of `#506`'s
three composed applications built: two `accumulator_cell_v1.v`
instances (SUBTRACTED, QUOTIENT) and one `branch_cell_v1.v` instance,
wired as a genuine self-sustaining closed feedback loop with zero
external stop signal -- BR's held reference seeded once with the
host-precomputed `(A-B)`, every later SUBTRACTED value compared
against it, continuing (fanned out to both SUBTRACTED and QUOTIENT at
once) while `SUBTRACTED <= (A-B)`, genuinely suppressing (not just
zero-emitting) once it isn't. Correct across 23/7, 21/7 (exact,
boundary `is_equal` case), 3/7 (`A<B` degenerate case), and 100/9 (11
iterations).

**A real, general composition-level race found, misdiagnosed once,
then correctly root-caused:** a continuously-offering accumulator's
own ack round trip (1 cycle) is faster than the full loop round trip
needed to deliver a genuinely new value (3 cycles) -- left unguarded,
it re-offers the same stale value once before the real update lands,
producing a consistent "quotient +1, remainder -B" error. A first fix
(freeze only until the first real capture, then latch open) was built,
tested, and directly DISPROVEN by tracing -- it just relocated the
duplicate. The real, general fix: `freeze_in` tied permanently to the
real upstream trigger (`!br_fire_e`), every round, using only an
existing mechanism, zero new RTL. Full detail: `points.md` `#518`.

**`#506`'s three composed applications are now ALL built** (cascade
counter `#516`, multiplication `#517`, division `#518`). Remaining:
`#497`'s recombiner-pattern hardware readout (still introspection-only
everywhere), a genuinely self-driving preloadable pulse generator, and
`#505`'s per-core review (adder/latch/RAM/nano still open).

## Previous state (2026-08-28, real multiplication-via-repeated-addition built -- second of #506's composed applications, zero new RTL, see `points.md` #517)

**2026-08-28, real multiplication via repeated addition, sim-verified
clean, zero new RTL.** The second of `#506`'s own three composed
applications built: two plain `accumulator_cell_v1.v` instances -- a
PRODUCT accumulator (`step_amount=A`) and an independent COUNTER
(`step_amount=1`) -- both fed the same external pulse train, proving
real multiplication (7x13=91, 17x23=391, plus a reconfiguration case)
using nothing beyond `#515`'s own `step_amount` field. A real, honest
scoping line drawn against `#506`'s own "counting down from B" phrase:
what's built is the arithmetic core (repeated addition via
`step_amount`, B supplied externally, matching multiplication's own
known-count-in-advance property) -- a genuinely self-driving,
preloadable "counts down from B and stops" pulse generator is real,
separate, harder work (closer in shape to what division needs) and is
NOT built here. Full detail: `points.md` `#517`.

**Real, honest scope still open from `#506`'s own list:** division via
repeated subtraction with feedback -- the one that genuinely needs new
composition (accumulator + comparator/branch cell watching for the
stop condition), not just a step_amount trick.

## Previous state (2026-08-28, real cascade/carry counter built on the accumulator's new pulse_mode -- zero new RTL, see `points.md` #516)

**2026-08-28, real cascade/carry counter, sim-verified clean, zero new
RTL.** The first of `#506`'s own three composed applications actually
built: three plain `accumulator_cell_v1.v` instances (`#515`'s real
`pulse_mode`) wired stage-to-stage with the same direct fire->arrived/
ack_out->ack_in pattern already proven between different core types --
proven here between three instances of the SAME core type. Driven with
237 real individual external pulses, correctly decomposed into
2 hundreds / 3 tens / 7 ones with zero pulses lost or double-counted.
Confirms directly, for the first time in a genuine multi-stage
composition, that `#515`'s own "internal total updates unconditionally,
never gated by pending_ack" design choice is exactly what makes this
kind of chaining work cleanly. One real, harmless-but-fixed config-
literal width bug found and corrected across every accumulator config
site touched this session (a 27-bit-too-narrow zero-pad that Verilog
was silently zero-extending correctly, but not worth leaving implicit
for real Quartus synthesis later). Full detail: `points.md` `#516`.

**Real, honest scope: no real hardware-readable digit-output path
built** -- every stage's digit is read via direct internal signal
access for verification, matching this project's own established
testbench convention, not a real wired readout. `#497`'s own
recombiner-pattern connection remains separate, unbuilt future work.
`#506`'s other two composed applications (multiply/divide via repeated
add/subtract with feedback) remain unbuilt.

## Previous state (2026-08-28, real accumulator upgrade built -- variable step_amount + reset-after-fire pulse mode, see `points.md` #515)

**2026-08-28, real accumulator_cell_v1.v upgrade, sim-verified clean,
zero regression.** #506's own two worked-through possibilities --
data-driven `step_amount` (was hardcoded +-1) and a genuine
reset-after-fire `pulse_mode`/`threshold` (crossing `|accumulator| >=
threshold` fires a discrete pulse and hard-resets the internal total
to 0) -- both built. Backward compatible by construction: `pulse_mode
=0` reproduces the exact prior behavior, every existing field kept at
its original bit position. `tests/fpga/tb_accumulator_cell_v1.v` now
has 6 test groups / 13 checks, all passing, including proof the pulse
genuinely REPEATS (not a one-shot) and that negative-direction
crossings fire too. A real wiring bug (not just a test gap) was found
and fixed along the way: both `unicell_super_v1.v` and `unicell_
super_v2.v` were truncating the accumulator's `core_config` to the
original 12 bits, silently dropping the two new fields -- widened to
pass through the real bits the new fields now use. Every other real
call site (the super-carrier testbench, both sentinel decomposition
testbenches, both real Quartus top-level targets) updated explicitly
to pass `step_amount=1`, matching `#504`'s own established discipline
for keeping prior-tested behavior byte-for-byte identical. Full detail:
`points.md` `#515`.

**Real, honest scope still open:** Quartus synthesis/timing; VM
dispatch (`unicell_super_automaton_v1.py`); `icm_v3.py`/`root_
definition.json` field-table entries (`regenerate_root_definition_v1.py
--check` correctly flags staleness now -- expected, not a bug, left
unregenerated deliberately). Same real boundary `#500`/`#504` already
left open for the branch cell, applied consistently rather than
reopened as a new question. `#506`'s own three composed applications
(cascade counters, multiply/divide via repeated add/subtract) remain
unbuilt -- this closes only the accumulator core's own new capability.

## Previous state (2026-08-25, real rolling-mode capability added to branch_cell_v1.v -- the exact 42nd and final config bit, see `points.md` #504)

**2026-08-25, real rolling-mode addition, sim-verified clean, zero
regression.** `rolling_mode` (bit [41] -- the exact last bit available
in the real 42-bit `core_config` budget, zero headroom left after this
one) turns the branch cell from "compare against a fixed baseline"
into genuine continuous change/drift detection: on every real
comparison, the just-compared value becomes the new held reference,
regardless of whether that outcome's own `emit` bit reported it
downstream. First arrival still just seeds the reference either way.
Real, load-bearing test confirmed correct on the first run: with an
original reference of 100, comparing 90 fires LOW and rolls the
reference to 90; comparing 95 next fires HIGH (not LOW) because 95 >
90 (the CURRENT reference), even though 95 < 100 (the ORIGINAL
reference a static-mode cell would still be holding) -- proving
genuine rolling behavior, not just a new bit that compiles.
`tests/fpga/tb_branch_cell_v1.v` now has 7 test groups / 12 checks,
all passing, deterministic across repeat runs, zero regression on
every one of `#500`'s own original static-mode tests. Full detail:
`points.md` `#504`.

**Real, honest scope still open, unchanged from `#500`:** Quartus
synthesis/timing; VM dispatch; `icm_v3.py`/`root_definition.json`
field table entries (now including `rolling_mode`); Designer/DSL tile
registration; the recombiner's own composed-tile registration.

## Previous state (2026-08-25, real host-driven discovery/walk design fully converged -- the Walker's own real job, see `points.md` #501)

**2026-08-25, real, complete design for host-driven topology/type
discovery -- the Walker's own real job -- worked out end to end while
Alan was away from a keyboard.** The real, final, converged shape:
`core_select=31` (reserved, unused) as a one-time-destructive
discovery-mode entry, after which the cell's OWN ordinary cardinal
ports carry cheap, non-destructive ping traffic (address+cardinal-or-
self) instead of payload. Self -> answer with own real ID+type.
Cardinal -> relay unchanged out that one port, let the real neighbor
answer for itself -- no address ever bundled inside a response, only
discovered by directly asking. Real specialist-cell gap (RAM/DSP have
no `core_select` to hijack) resolved: every discoverable thing is
core-shaped by construction -- a real HEADER CELL (its own reserved
`core_select`-family code, e.g. "header for DSP") answers on behalf of
whatever specialist hardware sits behind it; that hardware is
invisible to the walk entirely. Real, final division of knowledge: the
Composer/fitter are the ONLY things needing real physical layout
knowledge; the ICM's general programming never targets specialist
hardware directly, only through a header; the live walk only needs the
ENDS (ID+type/role), never the internal wiring; ALL walk intelligence
is host-side -- cells are purely reactive, nothing stored, nothing
inferred anywhere in the mesh. A real, more expensive alternative
(baking a full neighbor-type/ID table into every cell as a compile-
time constant) was proposed, worked out in detail, and correctly
discarded once the live-ping model fully replaced the need for it.
Full detail: `points.md` `#501`.

**Real, honest scope: nothing built.** This closes out the DESIGN for
the Walker's own real, still-unbuilt job (the only "Walker" that
exists today is a legacy, full-cell-era test). Real, concrete next
steps whenever picked up: reserve the discovery-mode `core_select`
value(s) and header-role codes; wire real relay logic behind the
currently-dead `cmd`/cardinal-mode ports; write the host-side walker
driver itself.

## Previous state (2026-08-25, branch/comparator core RTL built and sim-verified -- first real implementation step done, see `points.md` #500)

**2026-08-25, real, first RTL draft: `fpga/verilog/branch_cell_v1.v`,
sim-first, matching every other core's discipline.** Field layout
exactly matches `#497`'s own final table (41 of 64 bits used). The
held-reference mechanism works as designed. One real RTL bug found and
fixed: a held `arrived_n` could double-capture the same physical
arrival (once as reference, once compared against itself) since this
core's two capture paths don't share a common blocking guard the way
every other core's single path does -- fixed with a new `consumed`
latch. One real testbench race found and fixed, explicitly NOT an RTL
defect: clearing `cfg_valid` immediately after `@(posedge clk)` races
against the DUT's own same-edge sampling -- traced with a cycle-by-
cycle monitor, fixed with the standard `#1`-before-clear idiom, applied
throughout. `tests/fpga/tb_branch_cell_v1.v` -- held-reference capture,
all three outcomes (relay/fixed/suppress), release-on-reprogram, and
real fan-out all confirmed, deterministic across 3 repeat runs. Zero
regression across the whole DSP test suite (all 5 testbenches
re-verified) and the whole Python suite (335/335). Full detail:
`points.md` `#500`.

**Real, honest scope still open for the branch/comparator core:**
Quartus synthesis/timing/ALM cost (not yet attempted); VM dispatch
(`unicell_super_automaton_v1.py`); `icm_v3.py`/`root_definition.json`
field table entries; Designer/DSL tile registration (needs a bespoke
`place()` function, not the generic Tier-0 one, since `in+N`
resolution is unique to this core); the recombiner's own composed-tile
registration (deferred until this core exists to feed it).

## Previous state (2026-08-25, real design principle logged + two doc deliverables built, see `points.md` #498)

**2026-08-25, real, foundational architecture principle stated by
Alan, now logged and carried into real documentation.** "Prefer a
CORE over a specialist cell" -- a core joins `core_select`, placeable
anywhere, ICM-mutable, no `.sof` rebuild needed to rearrange; a
specialist cell (DSP wrapper family) is fixed to specific grid
positions at bitstream-build time, permanently. Building specialist
cells by default erodes the whole ICM/Designer/compiler stack's own
real mutability. Real, known exception, not a contradiction: genuinely
scarce hard-IP-adjacent resources (the DSP wrapper's own real,
already-stated reason for existing outside `core_select`). The
recombiner (`#497`) is the concrete proof the default already works --
built from two already-universal pieces, zero new position-fixed
hardware.

**Two real docs built to carry this forward, closing #477's own
long-unstarted ask along the way:**
1. `CORES_AND_WRAPPERS_REFERENCE.md` extended -- the design principle
   above, plus a real, CHECKED standalone-vs-super-carrier behavior
   summary (five of six cores identical in both contexts; nano is the
   one real exception, now the documented reason the branch/
   comparator core exists at all).
2. New `docs/stripped-cell/CELL_GOTCHAS.md` -- per-cell/mechanism
   facts that silently produce wrong results if unknown, split into
   WIRING (fixed by a composed tile, not a note) vs. BEHAVIORAL (no
   composed tile can fix these) gotchas. Seeded with everything real
   from this session: branch cell release/addressing constraints, the
   recombiner's exact wiring and entropy limits, DSP watchdog
   timescale mismatch, per-op hardware status, entity-naming lesson,
   nano's own gap.

Full detail: `points.md` `#498`.

## Previous state (2026-08-25, branch/comparator core design fully closed out -- held-reference optimization + recombiner pattern, see `points.md` #497)

**2026-08-25, real, final design close-out for the branch/comparator
core -- ready to implement, nothing built yet.** Alan's own held-
reference insight closes the real `core_config` budget question `#494`
left open: the comparison reference never travels through config at
all -- it's the first value captured after programming (or after a
release), held indefinitely, compared against by every later arrival;
release happens on reprogram (`cfg_valid`), reusing an existing
mechanism, zero new ports. Real, final field table: `upstream_dir`(2)
+ per-outcome `value_source`(1)/`fixed_value`(7)/`emit`(1)/`route`(4)
x3 = **41 bits total**, one spare, inside the real 42-bit budget.
`threshold` is gone as a config field -- runtime state now.

**A real, separate, complementary mechanism also settled: the
recombiner**, for reconstituting a wider composite word from several
narrow (7-bit) branch-cell outputs. Needs ZERO new RTL -- `shift_lane_
addon_v1.v` already supports shift-by-8 (one of its real, already-
proven discrete amounts), and since the accumulator and each fresh
byte never share a bit position, addition and OR are identical, so the
existing `adder_cell_v1.v` does the combine step unmodified. 4 bytes
-> 3 folds -> 6 extra cells total, all already-proven parts. Real,
honest caveat Alan raised and confirmed: this repackages what already
went in, it doesn't manufacture entropy (round-robin from ONE branch
cell is degenerate; four independent ones cap at `2^28` distinct
outputs, not `2^32`) -- it's for composite classification tags, not
for preserving an arbitrary value (that's what relay mode already
does directly). Deliberately sequenced as a composable multi-cell
PATTERN first, not a dedicated packer core, matching the project's own
"Lego" philosophy -- zero new proving burden. Full detail, including
one still-open confirmation (fixed-shift-by-8 vs. growing shift
amount per fold, currently assumed fixed): `points.md` `#497`.

**Roadmap status (`#495`):** item 1 (`#469` DSP fix) closed `#496`.
Item 2 (branch/comparator core) is now fully designed -- RTL, VM,
`icm_v3.py`/`root_definition.json` field tables, and Designer/DSL tile
registration are the real next steps whenever building starts.

## Previous state (2026-08-25, DSP compare wrapper entity name confirmed for real -- #475's last open gap closed, see `points.md` #496)

**2026-08-25, real, closing correction to the whole DSP wrapper
thread.** Alan uploaded his own real generated `alterafpf_ge_single_
comb.qsys`, closing `#475`'s own honestly-flagged reasoned-placeholder
gap. Real, confirmed facts: top-level entity `alterafpf_ge_single_comb`
(matching `#471`'s own hard-learned "filename, not internal Qsys
kind" lesson), real port list `dataa`/`datab`/`n`/`result` ONLY --
genuinely, purely combinational, no clock ports at all (even fewer
than the reasoned placeholder assumed). `dsp_compare_wrapper_v1.v`
corrected, old placeholder stub replaced, docs updated. Zero
regression across all five real DSP testbenches. **Real, honest
status, unchanged in substance:** ADD remains the only mode with real
hardware confirmation (`#472`); everything else (SUB/MUL/GE/LE/NEQ) is
now sim-verified with CONFIRMED real entity names, but none has
individually run on real silicon. Full detail: `points.md` `#496`.

**This closes item 1 of `#495`'s own ordered queue.** Next: item 2,
the branch/comparator core -- currently paused on a real, open
`core_config` budget question (`42-bit` total, tighter than `#493`'s
own rough math assumed) sent to Alan, not yet answered.

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
