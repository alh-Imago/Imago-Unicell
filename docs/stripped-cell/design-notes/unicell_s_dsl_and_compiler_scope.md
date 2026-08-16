# Unicell-S DSL + compiler — design scope (CONCEPT, review before building)

*Captured 2026-08-16, per Alan: a fresh, purpose-built DSL (not a
Python-AST subset), and diagnostics that explain WHY something failed
and build user confidence, not bare exceptions. Same discipline as
`super_tile_library_scope.md`: this is a proposal to review and correct,
not a locked spec -- nothing below is built yet.*

## What the compiler's job actually is, precisely

Lower a program written in the new DSL down to a real `icm_v3.IcmV3File`
-- a list of placed `IcmV3Record`s, each with a real `row`/`col` and a
real `core_config`/`addon_config` that `unicell_super_automaton_v1.py`
can run and `nano/icm_v3.py` can encode into a genuine `SUPER_LATCH`.
Everything the compiler does is really just automating what a person
would otherwise do by hand-calling `place()`/`place_composed()` directly
(as every test in `#338`-`#341` already does) -- parse the user's
intent, resolve it against the Tier-0/Tier-1 libraries, validate it, and
emit the same kind of record list those calls already produce.

## Pipeline

```
source text (.uc? -- name TBD)
    -> LEXER      (tokens, each carrying real line/col)
    -> PARSER     (AST, each node carrying its own source span)
    -> RESOLVER   (AST -> tile references resolved against
                   super_tile_library / composed_tile_library,
                   ports/params checked against each tile's own
                   contract -- reuses place()/place_composed()'s
                   EXISTING validation logic, doesn't reimplement it)
    -> PLACER     (resolves relative/symbolic positions to real row/col,
                   catches genuine placement conflicts -- two things
                   claiming the same cell -- which neither place() nor
                   place_composed() currently checks, since each call
                   today trusts the caller's own row/col)
    -> EMITTER    (IcmV3File, ready to .save())
```

Every stage produces either a clean handoff to the next stage or a
`CompileDiagnostic` (below) -- never a bare Python exception surfacing
to the user.

## Diagnostics, first-class from the start (Alan's own explicit ask)

A structured diagnostic, not a string:

```python
@dataclass
class CompileDiagnostic:
    severity: str          # "error" | "warning"
    stage: str              # "lex" | "parse" | "resolve" | "place" | "emit"
    what: str                # what was being attempted, in the user's own terms
                              # e.g. "placing tile 'sentinel' as 'alarm1'"
    problem: str              # what specifically went wrong
                              # e.g. "port 'clear' given direction 'e', but
                              #       'alarm1.lat' already offers 'out' on 'e'"
    why: str                   # why it's a real problem, not an arbitrary
                                # rule -- e.g. "a cell can only drive one
                                # value onto a given direction per tick;
                                # two fields targeting 'e' would collide"
    suggestion: Optional[str]  # a concrete next step, when one exists
                                # e.g. "try 'clear: s' instead -- free on
                                #       this cell"
    source_span: Optional[Tuple[int, int, int, int]]  # (line, col, line, col)
```

Every place in the existing library where a bare `ValueError` is raised
today (`_resolve()`, `place()`, `place_on_nano()`, `place_composed()`)
is a candidate `problem`/`why` pair already written in reasonably plain
English -- the compiler's diagnostic layer doesn't need to invent this
reasoning from scratch, it needs to CARRY it through with real source
location attached, which raw exceptions from those functions don't have
today (they know nothing about which line of user text asked for the
placement that failed).

**Real, honest scope note:** giving every diagnostic a genuinely useful
`suggestion` is aspirational, not guaranteed -- some failures (e.g. "this
port doesn't exist on this tile at all") don't have one good next step
without knowing more about user intent. `suggestion` stays `Optional`
rather than a required field the compiler would have to fabricate
something weak just to fill.

## DSL syntax -- a concrete proposal to review, not a decision

Kept close to what `SubCellPlacement`/`ComposedTileSpec` already ARE in
Python, so the resolver stage is close to mechanical translation, not a
second design effort:

```
program dual_alarm {
    place acc as accumulator at (0, 0) {
        inc: n
        dec: s
        out: [e, s]
    }
    place cmp_low as comparator at (1, 0) {
        in: n
        out: e
        threshold: 3
    }
    place lat_low as latch at (1, 1) {
        set: w
        clear: s      # this cell's own external port
        out: w        # this cell's own external port
    }
    place cmp_high as comparator at (0, 1) {
        in: w
        out: e
        threshold: 10
    }
    place lat_high as latch at (0, 2) {
        set: w
        clear: n
        out: e
    }

    expose inc -> acc.inc
    expose dec -> acc.dec
    expose clear_low -> lat_low.clear
    expose out_low -> lat_low.out
    expose clear_high -> lat_high.clear
    expose out_high -> lat_high.out
}
```

This is literally `dual_threshold_monitor` (`#341`) hand-expanded from
its composed-tile shorthand into raw cell-by-cell placement -- proof the
syntax can express what the Python API already proves works, before
anything language-specific gets added on top.

**The actual payoff over hand-calling `place_composed()` directly**
would be referencing an EXISTING Tier-1 tile instead of expanding it:

```
program my_monitor {
    use sentinel as alarm1 at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
```

Two real, open questions this raises, not resolved here:
- **Nested composition -- CONFIRMED IN SCOPE (Alan, 2026-08-16: "yes
  number 1").** A `program` block should be able to become a reusable
  named tile others can `use`, the same way `sentinel`/`dual_threshold_
  monitor` already work -- generalizing Tier 1 from "composed of Tier-0
  pieces only" to "composed of Tier-0 OR Tier-1 pieces, recursively."
  This needs proving at the Python-API level FIRST (same "smallest-
  test-first" discipline already used for fan-out, `#341`) before the
  DSL's own `use` keyword can trust it -- see `#342` below.
- Auto-placement (`at (0,0)` chosen automatically) vs. explicit
  coordinates (required, as sketched above) -- explicit is simpler to
  build and to give clear placement-conflict diagnostics for; automatic
  placement is a much harder, separate problem (real bin-packing/graph-
  layout territory) that shouldn't block a first working compiler.

## Multi-pass architecture, per Alan's own recollection of the old compiler

Alan (2026-08-16): "the old compiler did several passes, maybe that's
where the user errors could be caught." Checked directly against
`cell_format.py`'s own `check_pipeline_bridges()` (not `compiler.py`
itself, which is closer to single-pass, but a real, already-built
precedent in this codebase): it runs as a DISTINCT validation step
BEFORE any real placement is attempted, and returns a structured result
-- `{ok, errors, warnings, auto, summary}` -- covering EVERY connection
in the whole pipeline, not just the first bad one found. That shape is
worth adopting directly, and it changes the pipeline sketched above from
five stages that could each abort on first failure into five real
PASSES, each collecting a full list of diagnostics rather than raising:

```
Pass 0 LEX      -- tokenize the whole source; collect every lex error found
Pass 1 PARSE    -- build the AST; where recovery is feasible, keep parsing
                    past a bad statement to report more issues in one pass
                    (aspirational for a first version -- real parser error
                    recovery is genuinely hard; stopping at the first
                    unrecoverable parse error is an honest fallback, not
                    a design failure, if recovery isn't there yet)
Pass 2 RESOLVE  -- for EVERY place/use statement in the program, check the
                    referenced tile name exists (Tier 0, Tier 1, or a
                    previously-compiled program registered as a tile) --
                    catches every "unknown tile" error across the whole
                    program in one pass, not one at a time across repeated
                    compile attempts
Pass 3 VALIDATE -- for every resolved placement, check port/param
                    completeness using place()/place_composed()'s own
                    existing validation logic (not reimplemented), but
                    collecting every failure across every statement,
                    matching check_pipeline_bridges' own "don't stop at
                    the first problem" shape
Pass 4 PLACE    -- compute real row/col for every placement, THEN check
                    for genuine collisions (two statements claiming the
                    same cell) across the WHOLE grid at once -- a real
                    check neither place() nor place_composed() does today,
                    since each trusts the caller's own row/col
Pass 5 EMIT     -- build the IcmV3File
```

The point, stated plainly: a user should see EVERY real problem with
their program from one compile attempt wherever the pass structure makes
that possible (passes 2-4 are all naturally whole-program, not
early-exit), rather than fix-one-error/recompile/hit-the-next-one. Not
promised for pass 0/1 (lex/parse) where real recovery is a harder,
separate problem -- stated honestly as a real limitation of a first
version, not glossed over.

## What's genuinely new work here, honestly scoped

1. **Lexer/parser** -- hand-written, not a new dependency (nothing else
   in this project pulls in a parser-generator library; `compiler.py`'s
   own precedent uses Python's own `ast` module because it was parsing
   real Python, which doesn't apply here since the DSL is new syntax).
   Every token/node needs to carry its own source span for the
   diagnostics layer to be genuinely useful, not an afterthought bolted
   on later.
2. **Resolver** -- looks up `accumulator`/`comparator`/... against
   `super_tile_library`, `sentinel`/`dual_threshold_monitor` against
   `composed_tile_library` -- reuses `place()`/`place_composed()`
   directly rather than reimplementing their validation, wrapping their
   `ValueError`s into `CompileDiagnostic`s with source spans attached.
3. **Placer** -- a genuinely NEW check neither `place()` nor
   `place_composed()` does today: detecting when two different
   placements (from two different `place`/`use` statements) claim the
   same `(row, col)`. Worth building as its own real check with its own
   real test, not assumed to fall out of the existing functions for
   free.
4. **Emitter** -- thin; `IcmV3File(records=[...])` already does the
   real work (`record_hash`, `.save()`).

## Suggested first, low-risk step whenever this is picked up

**Prove nested composition at the Python-API level FIRST, before any
lexer/parser work** -- same "smallest-test-first" discipline `#341`
already used for fan-out (proved it worked in `place()` directly before
building a composed tile on top of it). See `#342` below. Only once that
mechanism is real and tested does the DSL's `use` keyword have something
trustworthy to compile down to.

Then, for the DSL/compiler itself: don't build the full grammar first.
Get ONE real program end to end -- a single `place` statement for one
Tier-0 tile (e.g. `ram_constant`) -- lexed, parsed, resolved, placed,
emitted, and loaded back with `IcmV3File.load()` -- with at least one
deliberately-broken variant (missing port, bad direction) proving a real
`CompileDiagnostic` comes out the other end with a correct source span
and a genuinely helpful `why`. That's the smallest slice that proves
every pipeline stage exists and the diagnostics design actually works
end to end, before the grammar grows to cover `use`/`expose`/multi-cell
programs.
