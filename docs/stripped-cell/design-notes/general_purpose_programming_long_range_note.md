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

## Suggested first, low-risk step whenever this is picked up

Don't design the whole language. Answer the loop/variable/memory
questions above FIRST, in isolation, probably via the smallest possible
concrete experiment (e.g.: can a single bounded, compile-time-unrolled
loop over `place()` calls be given real syntax and compile to something
correct on Unicell-S, before anything else is attempted) — matching
this whole project's own "smallest test first" discipline, not a
ground-up language design effort.
