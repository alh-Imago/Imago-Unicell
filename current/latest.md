# Current State (as of 2026-08-16, later same day -- a new session picked up after a usage reset; see `points.md` #343 for what got added, `archeology/sessions/archive-2026-08-16.md`'s own "PART 2" section for the fuller #336-342 narrative)

## Read this first

**New session, 2026-08-16 continued -- `#216` is now CLOSED on every
real item.** Alan opened with "onto the cpu/gpu port of the vm" --
item 3, the last real `#216` item. Built `#361`:
`nano/gpu_array_v1.py`'s `VectorizedOfferSelector`, matching
`gpu_array.py`'s own real "Stage 1" precedent exactly (vectorize cell
SELECTION only, keep per-core logic as real Python -- the precedent
itself never vectorized more than that either, confirmed by reading its
actual kernel code, not just its header). Proven equivalent to
`SuperGrid.tick()`'s own Pass 4 condition tick-by-tick across all 3 real
composed tiles this session built. This sandbox has no CUDA hardware
(confirmed directly) -- the CPU path is real and tested, the GPU path's
code is untested here, stated honestly. Kept fully additive: zero
changes to `SuperGrid.tick()` itself. 8 new tests, 189/189 across the
full new-work suite, zero regression on the legacy 64+6 nano scripts.
Pushed to `origin/main`.

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
bookkeeping only. Per Alan's own sequencing (`#360`): the workbench
itself is next.

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
hardware-behavior description language), not attempted. **The workbench
itself is the real next step**, per Alan's own sequencing (`#360`):
CPU/GPU port (done, `#361`) -> workbench -> then tidying the scattered
77-file root Python sprawl, deliberately timed for after a real
VM/workbench exist. The TRIX system (`mathtrix_*`/`neurotrix_*`/
`flowtrix_*`/etc., a real, sizeable, existing system with genuine domain
typing and cross-domain bridges) is a real, checked, well-founded
concern for later -- may need the compiler to learn about DOMAINS, not
just ports/fields, per `#360`'s own note. The composer (Stage 5, `#20`)
remains explicitly later work, after both compiler and workbench.

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

## Next session

**The workbench itself**, per Alan's own sequencing (`#360`) -- `#216`
is now fully closed on every real item. No design note for it exists
yet -- this needs its own real scoping conversation before any code,
same discipline as everything else this session (start with what
`workbench.py`'s own real feature list already proves useful, see
`points.md #55`, but rebuilt against the real Unicell-S stack, not the
old `unicell_array`/`controller`/`compiler` classes it currently
imports). After the workbench: tidying the scattered 77-file root
Python sprawl, now genuinely well-timed with a real VM to validate
cleanup against. Read `points.md` #336-361 first if `#324`'s own phase
context needs refreshing -- each entry carries real reasoning, not just
a summary of what changed. The DSL manual (`docs/stripped-cell/
UNICELL_S_DSL_MANUAL.md`) is the right starting point for the
compiler/DSL side; `docs/stripped-cell/SUPER_CELL_INTERNALS.md` is the
right starting point for the shell/RTL side; `nano/vm_ai_port_v1.py`'s
`VMSession` is the easiest way to try something out end to end without
wiring the compiler/VM/introspection together by hand.

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
