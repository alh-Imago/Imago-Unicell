# Long-range note: general-purpose programming on Unicell-S, and the FPGA design-side link

*Captured 2026-08-16, per Alan: "yes and that a step into the area i
mention a user supplying actual programming, compiled into the
substrate... a long range project... the ultimate in systems
programming, software to hardware, and language agnostic." Then: "make
it a long range note... it has implications beyond the Unicell
system... remember the fpga design side route, another long range
project... linking those two would be a benefit and probably a whole
project on its own." NOT scoped, NOT started -- this is a marker so the
idea survives intact until deliberately picked up, same discipline as
`super_tile_library_scope.md` before Tier 0 existed.*

## The vision, stated plainly

A user supplies real programming — not just declarative tile placement
— and it compiles onto the Unicell-S substrate directly. "Software to
hardware, and language agnostic." The language-agnostic part is not
aspirational — it's already real and tested (`points.md #344`/`#348`):
two structurally different frontends (the DSL's own grammar, and real
Python-AST syntax) already compile to one shared IR
(`program_ir_v1.ProgramIR`) and produce byte-identical output. What's
missing is the "actual programming" part — expressions, variables,
control flow — not the multi-frontend architecture itself.

## Real prior art already in this project, not to be reinvented

The old full-cell compiler (`compiler.py`/`compiler_int32.py`) already
answered part of this once, for a different substrate:
- Typed values (`Int32Value`), real 32-bit arithmetic and comparisons
- `if`/`else` compiled as a spatial MUX (evaluate both branches, select
  the output) — a genuine, working answer to "how does a branch even
  work on hardware with no program counter"
- A library of pre-compiled, tested operation tiles
  (`fp_tiles.TileLibrary`) the compiler assembled real logic from,
  rather than deriving gate logic from scratch per program — the same
  structural role `super_tile_library`/`composed_tile_library` already
  play for Unicell-S today
- Proven on real system logic, not toy examples: `sentinel_core.py`/
  `ward_core.py`/`shore_core.py`, 24 functions, real `.icm` output
  still sitting in `bootloader/icm/`, 105 passing tests at the time

What was explicitly out of scope even there, stated in `compiler.py`'s
own header: loops (`while`/`for`, "requires a loop unrolling pass"),
real addressed memory, classes/generators/exceptions. Loops and memory
addressing are the genuinely open, unsolved pieces — not just
unimplemented, but architecturally unclear on a substrate where every
cell is a fixed physical location, not an addressable memory cell.

## The real, load-bearing open questions

Not resolved here — this is the list a real scoping session would need
to start from:
- **What does a "variable" even mean** on a substrate where computation
  is fixed physical topology, not addressable memory? A cell holding a
  value is a specific physical location, not a slot a name can be
  reassigned to point at.
- **What does a loop compile to** with no program counter and no
  return address? The old system never solved this even for the full
  cell. Loop unrolling (compile-time, bounded) is the obvious first
  answer, but genuinely unbounded/data-dependent loops may be a real
  architectural dead end for this kind of substrate, not just a hard
  compiler problem.
- **How much of `compiler_int32.py`'s own approach actually transfers**
  to Unicell-S's coarser core model (one core = one operation, not
  bit-serial gate composition)? The MUX-as-branch idea likely
  generalizes cleanly (Unicell-S already has real muxing via routing);
  typed values and arithmetic already have direct homes (`adder`,
  `comparator`); what doesn't obviously transfer is anything that
  depended on the old system's much finer-grained, individually
  addressable bit-cells.

## The second long-range thread: "the FPGA design side route" (clarified 2026-08-16)

Alan's own clarification: while the compiler is being used to produce
the DSL's own ICM output, what if that gets taken a step further --
**lower all the way down to actual Verilog**. Not just configuring the
fixed, already-synthesized `unicell_super_v1.v` array (what ICM v3
does today), but generating a genuinely bespoke, synthesizable RTL
design *for that specific program*. Deliberately deferred: "sort after
all this is sorted" -- not started, not scoped for real work, this
section exists so the shape survives intact.

**The real distinction, stated plainly:** today's pipeline compiles a
program down to a CONFIGURATION for an already-fixed piece of silicon
-- the six cores in `unicell_super_v1.v` are always physically present;
`place`/`define` only ever choose `core_select` and wire up
`core_config` bits. The FPGA design-side idea is a different target
entirely: instead of configuring an existing substrate, SYNTHESIZE a
new one -- real Verilog modules and wiring generated specifically for
one program, the way a High-Level Synthesis (HLS) tool works.

**Why this fits cleanly with what's already built, not a detour from
it:** `#344`/`#348` already proved "many frontends, one shared IR"
(`program_ir_v1.ProgramIR`) really works -- the DSL and a real
Python-AST frontend both compile to the identical IR and produce
byte-identical output. The FPGA design-side idea is the SAME
architecture applied on the other end: one shared IR, MULTIPLE
BACKENDS. `dsl_compiler_v1.compile_program_ir()` -> `IcmV3File` would
become one backend among possibly several; a hypothetical
`compile_program_ir_to_verilog()` emitting real, synthesizable RTL
would be a second, targeting the same `ProgramIR` every frontend
already produces. Nothing about the frontend side would need to change
at all.

**The real scale of the undertaking, stated honestly rather than
undersold:** this is genuinely "build a small HLS tool for a bespoke
architecture" -- a well-known, hard, mature engineering domain in its
own right (real commercial HLS tools represent years of dedicated
engineering). Real open questions this would raise, not resolved here:
does each placed tile become a real Verilog module instantiation (the
most direct mapping, likely the right first answer -- `ram_constant`
already has real RTL in `ram_cell_v1.v` to draw from directly)? How
does cardinal wiring between placed cells become real port connections
and timing-correct wire delay? Does the output target the SAME device
family Unicell-S already targets (Arria 10), or could it target
anything synthesizable in principle -- and if so, does the whole
"two-arrival firing, wired-OR bus, no global sequencer" philosophy this
project is built on even survive being generated per-program rather
than being one proven, fixed design?

**Linking this to the general-purpose-programming thread above is
Alan's own explicit framing of the real prize:** software written by a
user, compiled all the way down to bespoke, synthesizable hardware --
"the ultimate in systems programming, software to hardware, and
language agnostic." A real, substantial project on its own, per Alan's
own words, not a small combination of two existing pieces.

## A third facet, extending the same idea further (2026-08-16): "LEGO for FPGA"

Alan's own extension: a shell with standard connections, cores that
snap in -- generalized beyond this project's own team into "a snap in
system for hardware designers" broadly. Not a new idea invented from
nothing -- **it's the direct fulfillment of a real requirement Alan
already stated, the day before this session began (`points.md #317`)**:
the super carrier shell's core-type selector "must be able to accept
NEW core types added after this session -- cores not yet discovered or
built -- without a field-map reshuffle." And the RTL genuinely already
honors it: `core_select` is a 5-bit field, only values 0-5 are assigned
to the 6 real cores; values 6-31 are real, deliberate, reserved
headroom -- confirmed directly in `nano/icm_v3.py`'s own code
(`"core_select {sel} has no field table (values 6-31 are reserved, per
#317)"`), not a leftover accident.

**What "LEGO for FPGA" would mean concretely, stated as a real
extension of what already exists, not invented fresh:** today, adding
a new core (values 6-31) is something only this project's own team
could do -- write new RTL, wire it into `unicell_super_v1.v`'s own
core-select mux, reserve a `core_config`/`addon_config` bit range for
it, resynthesize. Alan's extension: what if the SHELL's own port
contract -- what a plugged-in core must actually expose (the subset of
`cfg_data` it consumes, `arrived`/`fire`/`ready` signal conventions, how
it hooks into the addon chain) -- were formalized into a real,
documented, STABLE public specification? Then a third-party hardware
designer, not just this project's own team, could write a new core
targeting that contract and have it genuinely "snap in" to slot 6 (or
7, or 31) -- a real hardware-level plug-in ecosystem, one level BENEATH
the software tile library that already exists on top of the fixed 6
cores (`super_tile_library`/`composed_tile_library`, `#338`-`#345`).

**The real, honest scale question this raises, not resolved here:**
`unicell_super_v1.v`'s own header already states the real constraint
plainly -- every one of the 6 cores is ALWAYS physically instantiated
in every bitstream, whether selected or not (that's precisely how
`core_select` gets to be a cheap runtime write instead of a recompile,
per `#339`'s own crossed-wire resolution). A truly open, add-your-own-
core ecosystem genuinely can't preserve that property past some limit
-- every core anyone might ever plug in can't ALL be physically present
in every bitstream forever; real ALM budget is finite. So "LEGO for
FPGA" at real scale is a different, harder problem than the current
shell already solves: either accepting a real recompile-per-core-set
model for anything beyond the built-in 6 (losing the "always all
present, zero-cost runtime select" property for the extended cores),
or a genuinely different mechanism (partial reconfiguration? a proper
plug-in loader that swaps which extra cores are resident?) not
sketched here. Worth a real, separate scoping conversation whenever
this is picked up -- the requirement (`#317`) and the headroom to
support it (the reserved `core_select` values) are both real and
already built; the actual open-ecosystem mechanism on top is not.

## Suggested first, low-risk step whenever this is picked up

Don't design the whole language. Answer the loop/variable/memory
questions above FIRST, in isolation, probably via the smallest possible
concrete experiment (e.g.: can a single bounded, compile-time-unrolled
loop over `place()` calls be given real syntax and compile to something
correct on Unicell-S, before anything else is attempted) — matching
this whole project's own "smallest test first" discipline, not a
ground-up language design effort.

## Real, sequenced plan for upcoming sessions (Alan, 2026-08-16)

Captured as stated, not started, in this order:
1. `#216` item 3 -- dual CPU/GPU execution, the last real `#216` item
   (following `gpu_array.py`'s own real architecture pattern, not its
   code -- built for the old `UniCellArray`, a different cell model).
2. The workbench itself.
3. **Tidying the scattered root-level Python files** (the 77-file
   sprawl deliberately held all session, per `#218`'s own "concept
   survives, code doesn't" discipline) -- explicitly timed for AFTER
   the VM/workbench exist, since a real running space to validate
   cleanup/archival decisions against (rather than guessing from
   reading old code) is exactly what's been missing every prior attempt
   at this.

## A fourth, real concern flagged for later: the TRIX system

Alan's own words: "when we reach the TRIX system, that is going to be a
complex system to run through, may even have to add awareness to the
compiler." Checked directly, not assumed -- this is a real, well-
founded worry, not overblown. The TRIX family is genuinely large and
already built: `mathtrix_*`/`neurotrix_*`/`flowtrix_*`/`sensortrix_*`/
`nettrix_*`/`optitrix_*`/`miditrix_*` (13+ real files spanning fluid
dynamics, neural signal processing, sensor encoding, network packet
processing, and pure math -- Conway, Ising, N-body, PageRank, wave,
boids), plus `cell_format.py`'s own `FormatDefinition`/`FormatRegistry`
-- real cross-domain "bridges" with a confidence-threshold system and
compile-time contract enforcement (`check_pipeline_bridges()`,
`SI_CHECK` dimensional analysis).

**None of it touches anything built this session.** Every TRIX file
targets the old full-cell/`CellMapRecord` format through the old
`compiler.py`, with zero connection to `program_ir_v1.ProgramIR` or the
new Unicell-S compiler. The real gap, stated precisely rather than left
vague: TRIX has genuine DOMAIN typing (a sensor stream is a
categorically different KIND of thing from a fluid-simulation cell) and
cross-domain bridges with real semantic content (a confidence score, a
dimensional-analysis check) -- the current DSL (`place`/`define`/
`expose`) has no equivalent of any of this; it only knows raw integers
and cardinal directions. Bridging that gap genuinely may need the
compiler to learn about DOMAINS, not just ports and fields -- a
different kind of awareness than anything built this session, and
worth its own real scoping conversation, not a small extension of
`place`/`define`.

Not scoped further here -- deliberately deferred alongside the rest of
this note, until Alan is ready to look at it directly.
