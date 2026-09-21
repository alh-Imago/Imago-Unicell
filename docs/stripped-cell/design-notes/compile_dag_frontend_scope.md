# A real frontend for `compile_dag()` — the bridged architecture, source-agnostic symbol resolution, and program-nexus segmentation (Alan/Claude, 2026-09-17)

*Per Alan's own direct request: `compile_dag()` (`vix_dag_dispatcher_
v1.py`, `#780`) is a real, tested backend with no real frontend feeding
it — every test built this session hand-constructed its own `DagInstr`/
`DagOperand` input directly. This note scopes what a real frontend
needs, matching this project's own established discipline (`composer_
scope.md`, `composer_full_editor_scope.md`, `pattern_library_
escalation_scope.md`) — define the real boundary and real dependencies
before writing any code, not after. A scoping pass only, nothing built.*

## The real premise

`compile_dag()` already does its own job correctly: given a real,
ordered list of `DagInstr`, it picks the right convergence shape
(`#777`), orients it correctly (`#778`), places it without collision
(`#780`), and emits real, runnable ICM. What it has never had is
something upstream of it — a real translator that takes an actual
program (LLVM IR text today; DSL text, and potentially others, later)
and produces that ordered `DagInstr` list automatically. This note
scopes that translator.

## 1. The bridged architecture — `ProgramIR` stays, `DagInstr` is a new target

Real decision, made directly: **bridged, not direct.** The existing
LLVM IR parser (`llvm_ir_frontend_v1.py`) keeps producing `ProgramIR`
exactly as it does today for the old backend (`compile_program_ir()`);
a new, real `ProgramIR -> DagInstr` translator sits between it and
`compile_dag()`. This reuses the existing, proven parser rather than
teaching it a second output format — real, deliberate "build on known
parts."

**What this real translator needs to do, concretely:** walk `ProgramIR`'s
own `PlaceIR` statement list and, for each one, produce a real
`DagInstr` with the right `opcode` and `DagOperand`s. `PlaceIR`'s own
real shape (a chain-oriented, `col_cursor`-based description) is not
the same shape as `DagInstr`'s own (frontier-oriented, dependency-list
based) — this translation is real, non-trivial work, not a renaming
exercise. Confirming exactly how `PlaceIR`'s own fields map onto
`DagOperand`'s three kinds is real, first work for whoever builds this.

## 2. Symbol resolution — a real, source-agnostic pass, ahead of `DagInstr` construction

Per Alan's own direct description, confirmed as standard, sound
compiler practice: a real, multi-pass front-end discipline that runs
regardless of which source (LLVM IR today, DSL or others later) is
being read:

1. **First pass** — scan the whole source, find every variable
   reference.
2. **Second pass** — confirm each one is genuinely declared before it
   becomes a usable reference. An undeclared reference is a real,
   clear error, not a silent guess.
3. **Third pass** — classify each resolved reference as a compile-time
   SET value or a runtime-DETERMINED one. This is exactly `DagOperand`'s
   own existing `const` vs `dynamic`/`ref` split — this pass is what
   decides which kind a given real value becomes.

**Real, confirmed decision on the DETERMINED case:** every real
function argument is treated as `DagOperand(kind="dynamic")` — never
as a compile-time constant, even though the old frontend's own
`argument_values` mechanism currently treats them that way for
simulation convenience. This is a real, deliberate, safety-first
choice: `#774` already proved `SEQUENCER` is the only shape that
cannot silently misfire when real arrival timing is unknowable, and a
genuine runtime argument's own timing is never knowable at compile
time. **Named consequence, not hidden:** this means `STAGGER` (`#771`)
will rarely if ever be selected in practice, since most real
convergence involves at least one genuine argument. `STAGGER` remains
correct and available for the narrow case of two purely compile-time-
composed values converging, but the common case defaults to
`SEQUENCER`'s own real, safe, if less efficient, behavior.

**Real, honest scope note on "reused variables":** real LLVM IR is
already SSA (each `%name` assigned exactly once, enforced by LLVM's
own verifier) — this specific failure mode cannot occur on that
source. This resolution pass is written source-agnostically anyway
(per Alan's own direct confirmation), since a future DSL or other
source may not carry the same guarantee.

## 3. Program-nexus segmentation — a real, second, distinct pass

**A real, second pass, run after symbol resolution, before per-
instruction `DagInstr` construction:** scan the resolved program for
every point where two or more separate, real values genuinely
converge — a real, PROGRAM-LEVEL nexus. This lets the frontend work in
real, bounded segments (between nexus points) rather than holding an
entire, large program's own dependency graph in mind at once — a real,
practical scalability property for anything beyond a small program.

**Real, deliberate terminology distinction, to avoid confusing two
genuinely different things that happen to share a name:** `#761`
already uses "nexus point" for a PLACEMENT-level concept — a physical,
already-placed cell found to have more than one real upstream
direction, discovered by scanning the actual grid after cells exist.
This new pass's own nexus is a PROGRAM-level concept — found by
scanning source/IR before anything is placed at all. The two are
causally connected (a program nexus, once built, is what PRODUCES a
placement nexus once `compile_dag()` runs) but occur at different
stages on different objects. This note refers to them as **program
nexus** and **placement nexus** respectively to keep them distinct in
any future document that references this scope.

**What the pass after segmentation does:** for the code between each
pair of program-nexus points, identify the actual opcodes used and
build a real, ordered map of the pieces needed, in the order they'll
be used — pulling each one from the opcode library (`vix_opcode_
library_v1.py`, `#793`) where an entry exists, or triggering the
real, two-part escalation below where one doesn't.

## 4. Opcode resolution and escalation — a real, two-part decision

For each real opcode encountered during segmentation, `library_
lookup()` (`#793`) is called. Two real outcomes:

- **A real entry exists** — proceed exactly as `add`/`sub`/`mul`/`and`/
  `or`/`xor` already do.
- **No real entry exists** — a real, two-part escalation, per Alan's
  own direct design:
  1. **If an AI connection is available** (per this session's own
     earlier discussion of agent connectivity, matching `#752`'s own
     already-scoped ladder's "AI research" rung), it is initiated
     automatically — a real, proposed entry comes back, and it must
     pass the same real verification discipline every entry this
     session has had (a real test, before it's trusted) before it's
     added to the library.
  2. **If no AI connection is available**, the user gets a real, clear
     diagnostic naming exactly what's missing, plus a prompt to open
     the Composer to build it directly.

**Real, honest, named dependency, confirmed directly against the
codebase, not assumed:** path 2 requires the Composer to have real
"design functions — the drag and drop, plus test" capability.
Confirmed directly against `composer_scope.md` and `composer_full_
editor_scope.md`: today's Composer is scoped and built only as a
placement/routing REVIEW tool for an already-compiled model (`#606`-
`#609`'s own real, shipped first pass) — the full drag-and-drop
AUTHORING editor `composer_scope.md` explicitly deferred is confirmed,
in `composer_full_editor_scope.md` itself, to still be genuinely
unbuilt. **This means escalation path 2, as designed, cannot function
until that separate, already-scoped, larger piece of work is built.**
This is real, separate, prerequisite work for this frontend's own
"no AI available" path to actually work end to end — named here
directly so it isn't discovered as a surprise later.

## 5. Incremental porting and testing — the proven process, continued

Per Alan's own direct confirmation: opcodes get ported into the new
library and dispatcher **one at a time, tested as they're created** —
the exact same real process `mul` (`#790`/`#791`) and `and`/`or`/`xor`
(`#792`) already went through this session. No big-bang port of the
old frontend's remaining opcodes (`icmp`, `select`, `shl`, `lshr`,
`ashr`) or of loop support is implied by this scope; each is real,
separate, later work, done and tested individually.

## 6. I/O injection — target-dependent, using what's already proven

**Real, confirmed design, mapped directly onto existing, tested
mechanisms — not a new abstraction:**

- **VM target:** `compile_dag()` already returns exactly what's
  needed. `dynamic_positions` names every real cell that needs a
  direct value injection (the real "entry box"); `positions` names
  every real cell whose result can be read (the real "exit box"). Per
  Alan's own direct instruction ("a direct injection into the cell,
  not a port of something that doesn't fit"), the real interface here
  is `grid.inject()`/direct read at those exact positions — no named-
  port indirection. `#774`'s own already-proven normalization (place a
  genuinely dynamic value into a real `ram` cell first) is the real
  mechanism already; this item is real, mostly-UI work (workbench and
  Composer boxes at those positions) on top of code that already
  exists and is already tested.
- **Card target:** a real, physical board has no Python object to
  inject a value into — the real interface is a memory-mapped address
  the host writes to and reads from. This is a genuinely different
  mechanism from the VM's direct injection, not a variant of it, and
  it maps onto the real, already-designed (though not yet built in the
  current codebase) "named port" concept found in `archeology/shared/
  docs/software/RUNNING.md` (a **ports** tab, named input/output
  declarations, addresses, "CLI compile with port scan and prompt").
  **Real, honest, confirmed finding:** this design exists only in the
  archeology documentation for an earlier, differently-packaged
  iteration of this project (`imago`, not the current `nano/` codebase)
  — the current, active `workbench_v1.py` has no port-declaration or
  I/O-window concept at all today (confirmed directly, not assumed).
  Porting this real, already-good design forward into the current
  workbench is real, separate work this scope depends on for the card
  case specifically.
- **ICM/Composer reflection:** per Alan's own direct instruction, both
  the entry/exit points (VM case) and the named ports (card case)
  should be reflected in the ICM format itself and visible in Composer
  for quick, direct testing — a real, named field on the ICM entry
  marking injection/read points, separate from and smaller than the
  full drag-and-drop editor (`composer_full_editor_scope.md`) named
  above. Worth scoping as its own small, achievable item rather than
  bundled into that larger, still-unbuilt piece.

## 7. Naming and format — recognizable, traceable

Per Alan's own direct instruction: keep a recognized, standard naming
format throughout this pipeline (symbol resolution → segmentation →
`DagInstr` construction) so that a person other than the one who built
it can read the intermediate representation and understand it — in
practice, this means preferring the original source's own real
identifiers (e.g., an LLVM `%name`) as a `DagInstr.name` directly,
rather than generating opaque, synthetic names, wherever that's
possible without collision.

## 8. The proof case

Matching this whole session's own established discipline and Alan's
own direct confirmation ("yes, it's the proven way, start small, and
test, build out from there"): before any of the above is built at
scale, the real, first target is one small, real LLVM IR snippet (two
or three instructions, no control flow) run through the real symbol-
resolution and segmentation passes, translated into real `DagInstr`,
compiled by the unchanged `compile_dag()`, loaded into the VM, and
checked against the correct numeric answer. That one, small, real,
end-to-end proof is what confirms the bridged architecture (item 1)
actually works, before further opcodes or the escalation/Composer/
card-side work gets built on top of it.

## Summary: real, named dependencies this scope surfaces, not hidden

1. `ProgramIR -> DagInstr` translation logic — genuinely new, non-
   trivial work (item 1).
2. A real, source-agnostic, multi-pass symbol-resolution module —
   new work, but a real, standard, well-understood shape (item 2).
3. A real, new program-nexus segmentation pass, kept terminologically
   distinct from `#761`'s own placement-nexus concept (item 3).
4. The Composer's own full drag-and-drop editor
   (`composer_full_editor_scope.md`) — confirmed still unbuilt,
   required for escalation path 2's "no AI" branch to function (item
   4).
5. The archeology `ports`-tab design — confirmed to exist only for an
   earlier, differently-packaged iteration of this project, not the
   current `nano/` codebase — needs porting forward for the card-target
   I/O case (item 6).
6. A real, small ICM-format extension plus a small, achievable
   Composer addition (short of the full editor) to reflect entry/exit
   and port points for quick testing (item 6).

None of these block *scoping* this frontend today, but items 4 and 5
in particular are real, separate, larger pieces of prerequisite work
this frontend's own full design depends on — worth sequencing
deliberately rather than discovering mid-build.

## Addendum (2026-09-21, `#795`) — item 1's premise checked against the real code, and corrected

*Per this project's own discipline: the note above is left as written; this records what building item 8's proof case actually found.*

**Item 1 proposed bridging `ProgramIR -> DagInstr`. That premise does not hold.** `ProgramIR` is the OLD frontend's own POST-PLACEMENT output: every `PlaceIR` already carries a row/col, names are synthetic (`op_0`, `value_north_0`), `sub x, 3` has already been rewritten into `add x, 0xFFFFFFFD` with the constant moved into `injections`, and dependencies exist only implicitly as column adjacency. Recovering dataflow from that would mean reverse-engineering it out of geometry, and would lose the original `%names` item 7 asks to keep. The real dataflow (names, opcodes, operand order) lives one level up, in llvmlite's own parse.

**What was built instead** (`nano/llvm_dag_frontend_v1.py`): the same reuse of the existing PARSER the note's own intent called for (llvmlite parse+verify), attached at the parsed function rather than at `ProgramIR`. Layered exactly as item 2 describes: one thin LLVM-specific extractor, then a source-agnostic three-pass symbol resolver (`resolve_symbols()`), so a DSL/C/Python frontend needs only its own extractor. The old frontend is untouched.

**Item 3 (program-nexus segmentation) is NOT built.** `compile_dag()` already detects convergence per instruction, and at proof-case scale nothing needed segmenting. Still open, still worth doing before large programs.

**Item 8's proof case passes**, and immediately exposed something the whole `#750`-`#793` arc could not, because every earlier test hand-built its own `DagInstr` input: **`compile_dag()`'s plain-chain path gives a non-commutative op's real+constant operands no operand-order guarantee** (`#770`'s hazard, previously shown only for convergence). Observed: `sub(dynamic,const)` right and `sub(const,dynamic)` wrong; `sub(ref,const)` wrong and `sub(const,ref)` right -- correctness by arrival luck. Worked around soundly in the frontend (`sub %v, C` -> `add %v, -C`, recorded in `rewrites`; `sub C, %v` refused with a diagnostic). The backend itself is NOT fixed; see `#795`.

**One correction to this note's own context:** the old frontend is not limited to straight chains -- its general DAG routing (`#701`/`#713`) already accepts the diamond `t3 = add t1, t2`. The new path's real differences today are that it is library-driven, treats arguments as runtime-determined, and compiles `mul` (which the old frontend rejects, `#791`) -- not that it accepts DAGs the old one cannot.

## Addendum (2026-09-21, `#796`-`#798`) — ordering guarantee, the scan pass, and the ports

**Item 5 (port opcodes one at a time) is done for every straight-line opcode the old frontend has:** `shl`/`lshr` (`#797`), `icmp` (six predicates), `select`, `ashr` (`#798`), plus `mul` which the old frontend lacks. Loops are the remaining old capability. Each is built by composing existing library ops (`icmp` = `sub` + comparator entry; `select` = mask-and-merge; `ashr` = `lshr` OR a `shl`'d sign mask); no new hardware.

**Operand ordering (`#796`).** The backend now guarantees order where it matters: `vix_dag_dispatcher_v1.ingestion_path()` routes an order-sensitive (non-commutative) real+constant pair through the sequenced convergence path; commutative ops keep the plain chain. The frontend's scan pass (`scan_ordering`) records, per instruction, whether order is essential, which ingestion path the dispatcher will take, and what guarantees it (`not needed` / `lowered to commutative` / `sequencer`), and traces expanded ops to their source `%name`.

**Item 3 (program-nexus segmentation) and item 4 (escalation) remain unbuilt.** New named limits found while porting: no occupancy-aware placement (so two independently computed values that must merge -- a `select` with two computed arms, a chain of `select`s -- are refused with a `place` diagnostic); ordered `icmp` predicates are exact only while their 32-bit difference does not overflow (surfaced as `caveats`).

## Addendum (2026-09-21, `#800`) — placement as a virtual-space stage

Per Alan's design, placement is now available as a stage where the design sits in a VIRTUAL space and is lowered to cells only at the end (`nano/vix_virtual_layout_v1.py`): the router chooses the faces at both ends of every route (cardinality is a result, not an input), tightening is a search for the smallest workable spacing, and folding wraps the layout into bands whose shape orientation flips on alternate bands. The growth dispatcher (`#780`) is unchanged and remains the first choice under `placer="auto"`. This resolves the two-computed-values-merging limit that `#798` documented, within the stated limits (planarity, <= 3 consumers per value, narrow folds of branching designs). See `#800`.
