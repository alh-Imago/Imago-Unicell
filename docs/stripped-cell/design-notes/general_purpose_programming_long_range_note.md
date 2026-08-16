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

## The second long-range thread: "the FPGA design side route"

Alan referenced this as a separate, existing long-range project whose
specifics carry real weight ("implications beyond the Unicell system")
— but I don't have a solid, documented anchor for its precise scope
after searching `points.md`, `PAPERS.md`, and past conversation history.
**This needs Alan's own clarification, not a guess, whenever it's
picked up** — worth a one-line recap at that point rather than this
note silently inventing a scope for it.

Alan's own framing of the payoff is clear even without that detail:
**linking the two — a general-purpose, language-agnostic software-to-
hardware compiler, AND whatever the FPGA design-side route actually
is — would be a substantial project in its own right, not a small
combination of two existing things.** Worth remembering as its own
future scoping conversation, not folded into either thread alone.

## Suggested first, low-risk step whenever this is picked up

Don't design the whole language. Answer the loop/variable/memory
questions above FIRST, in isolation, probably via the smallest possible
concrete experiment (e.g.: can a single bounded, compile-time-unrolled
loop over `place()` calls be given real syntax and compile to something
correct on Unicell-S, before anything else is attempted) — matching
this whole project's own "smallest test first" discipline, not a
ground-up language design effort.
