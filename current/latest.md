# Current State (as of 2026-08-16, later same day -- a new session picked up after a usage reset; see `points.md` #343 for what got added, `archeology/sessions/archive-2026-08-16.md`'s own "PART 2" section for the fuller #336-342 narrative)

## Read this first

Everything through `#345` (documented below) was built earlier this
session. Alan then said "yes if you can, that open more options in the
compiler side" to `use`/`expose` grammar. Built `define`/`expose`
(`#346`): a Unicell-S program can now define its own reusable composed
tile inline, entirely in the DSL, with zero changes to the underlying
`ComposedTileSpec` model -- confirmed `use` really was redundant
(`place` already handles Tier-1 tiles transparently), so the real gap
was always `expose`. Eager validation, nested define-of-define tested
directly, per-call disposable library scoping confirmed. 10 new tests,
115/115 across the full new-work suite, zero regression on the legacy
64+6 nano scripts. Pushed to `origin/main`.

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
- **`define`/`expose` grammar (`#346`).** A program can define its own
  reusable composed tile inline: `define NAME { place ... expose ... }`,
  then `place` it exactly like any built-in tile. Confirmed `use` really
  was redundant first, then built the real gap (`expose`). Zero changes
  to `composed_tile_library_v1.py`'s core model -- pure translation to
  the same `ComposedTileSpec` shape everything else already uses. Eager
  validation at define-time, nested define-of-define tested directly
  (double-namespaced params resolving to distinct instances correctly),
  per-call disposable library scoping confirmed (a defined tile can't
  leak between separate compiles). Stated limitations: no fixed
  sub-cell params inside `define` yet, no forward declarations.

## What's NOT built yet -- open, real options

`#346` closed with several genuinely open next steps, not one obvious
path: fixed sub-cell params inside `define`; forward declarations
(two-pass resolution, so `place` can reference a `define` appearing
later in the same program); parser error recovery (collecting multiple
syntax errors from one bad file, not just the first -- stated as a
limitation since `#343`, still unbuilt); a real Python-AST frontend
(walking `ast.parse()`'s output for actual Python control flow -- a
bigger, separate undertaking than `#344`'s dict-based proof-of-concept);
C/Rust frontends (need an external parser library first, not
attempted). The workbench (user-facing frontend) also still hasn't had
its own scoping conversation at all. The composer (Stage 5, `#20`)
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

Several genuinely open options, per the "what's NOT built yet" section
above -- no single obvious next step this time. Read `points.md`
#336-346 first if `#324`'s own phase context needs refreshing -- each
entry carries real reasoning, not just a summary of what changed.
