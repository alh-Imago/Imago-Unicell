# Current State (as of 2026-08-16, later same day -- a new session picked up after a usage reset; see `points.md` #343 for what got added, `archeology/sessions/archive-2026-08-16.md`'s own "PART 2" section for the fuller #336-342 narrative)

## Read this first

Everything through `#342` (documented below) was done in an earlier
session today. A fresh session picked up after a usage reset and built
the DSL/compiler's own first real slice: `#343` -- a working
`program { place ... }` grammar, lex/parse/resolve/place/emit/reload,
real diagnostics with real source spans. 18/18 new tests, 89/89 across
the full new-work suite, zero regression on the legacy 64+6 nano
scripts. Pushed to `origin/main`.

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

## What's NOT built yet -- the honest next step

**`use`/`expose` grammar.** `place` already transparently handles
Tier-1 tiles today (a composed tile is resolved and placed the same
way a Tier-0 tile is), so it's worth confirming whether `use` is
actually needed as separate syntax before adding it, rather than
assuming it is. `expose` (a compiled DSL program's own external ports,
letting it become a `use`-able tile from ANOTHER program) is the real
gap -- it would generalize `#342`'s nested composition (proven at the
Python level) up into the DSL layer itself, which hasn't been touched.
Parser error recovery (collecting multiple syntax errors from one bad
file, not just the first) remains explicitly unbuilt too.

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

Pick up with `use`/`expose` grammar (or confirm `use` is redundant
and skip straight to `expose`), per the honest next-step note above.
Read `points.md` #336-343 first if `#324`'s own phase context needs
refreshing -- each entry carries real reasoning, not just a summary of
what changed. Also worth raising with Alan: the workbench (user-facing
frontend) hasn't had its own scoping conversation yet at all -- flagged
explicitly as the one major piece with no design note yet, once the
compiler's own grammar is far enough along to be worth a frontend.
