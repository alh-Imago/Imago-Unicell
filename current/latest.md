# Current State (as of 2026-08-16, session close, part 2 -- see `archeology/sessions/archive-2026-08-16.md`'s own "PART 2" section for today's full continuation narrative, `points.md` #336-342 for the numbered ledger)

## Read this first

Today had two real phases. The morning was housekeeping (audit +
structural cleanup + Onion tool fix, `#325`-`#335`). The afternoon was
the actual start of `#324`'s own stated next phase -- real, tested,
committed work, not more groundwork. In order: **ICM v3 format**
(`#336`), **VM dispatch across all 6 cores** (`#337`), **the tile
library's Tier 0** (`#338`), **target tagging** (`#339`), **Tier 1
started with the sentinel** (`#340`), **Tier 1 generalized with
fan-out** (`#341`), and **Tier 1 generalized again with nested
composition** (`#342`). Every one of these has real tests (16/16,
19/19, 22/22, 14/14 across the four suites), verified against either
real RTL or the exact proven behavior of real, Quartus-fitted
hardware, and zero regression on the pre-existing 64+6-test nano
suite. All pushed to `origin/main`, current HEAD `c581c00`.

## What's real and built today

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

## What's NOT built yet -- the honest next step

**The DSL lexer/parser itself.** Nothing written yet. The design
note's own "suggested first, low-risk step": one real program end to
end -- a single Tier-0 placement statement, lexed, parsed, resolved,
placed, emitted as a real `IcmV3File`, reloaded -- plus one
deliberately-broken variant (missing port, bad direction) proving a
real `CompileDiagnostic` comes out the other end with a correct source
span and a genuinely helpful `why`. That proves every pipeline stage
and the diagnostics design actually work before the grammar grows to
cover `use`/`expose`/multi-cell programs. `twin_sentinel`'s own
hand-expanded form (in the design note) is the natural first
non-trivial DSL program to target once basic placement compiles.

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

Pick up with the DSL lexer/parser, per the design note's own suggested
first step. Read `points.md` #336-342 first if `#324`'s own phase
context needs refreshing -- each entry carries real reasoning, not
just a summary of what changed.
