# The Unicell-S DSL — Language Manual

*A reference for the language `nano/dsl_lexer_v1.py`/`dsl_parser_v1.py`/`dsl_compiler_v1.py` actually implement, verified against those files and the live tile registries at time of writing (`points.md` #343, #346, and #347). If this manual and the code ever disagree, the code is right — this document describes what's built, not an aspiration.*

## 1. What this is

A small, purpose-built language for describing programs for the
Unicell-S super cell (`unicell_super_v1.v`). A program is a set of
`place` statements — put a tile (a pre-defined behavior) at a physical
grid position, wire its ports to real cardinal directions, and give it
whatever parameters it needs. The compiler turns that into a real
`icm_v3.IcmV3File` — a program the VM (`unicell_super_automaton_v1.py`)
can run and real hardware can eventually load.

This is a genuinely separate language from Python, C, or anything else
— not a subset of an existing language. See §7 for other ways to
produce the same underlying format.

## 2. A first program

```
program simple_ram {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 0xCAFEBEEF
    }
}
```

This places one cell at grid position `(0, 0)`, running the
`ram_constant` tile, offering its constant value eastward. Compile it:

```bash
python3 nano/dsl_cli_v1.py simple_ram.uc -o simple_ram.icm
```

## 3. Syntax

### 3.1 Comments

`#` to end of line.

### 3.2 Programs

```
program NAME {
    STATEMENT*
}
```

Exactly one `program` block per file. `NAME` becomes the compiled
file's own internal `name` field — `dsl_cli_v1.py` doesn't currently
offer a way to override it independent of that.

### 3.3 `place`

```
place LOCAL_NAME as TILE_NAME at (ROW, COL) {
    FIELD*
}
```

- `LOCAL_NAME` — an identifier, used only for diagnostics and internal
  bookkeeping (it doesn't have to be globally unique across a whole
  program, but keep it distinct within one `program`/`define` block so
  error messages stay meaningful).
- `TILE_NAME` — must resolve to something real: a Tier-0 primitive
  (§4), a Tier-1 composed tile — built-in (§5), `define`d earlier in
  this program (§3.5), or loaded via `--model` (§6).
- `(ROW, COL)` — the tile's anchor position. For a multi-cell Tier-1
  tile, this is where its own `(0, 0)`-relative sub-cell offsets are
  measured from.
- Each `FIELD` is either a **port** (a physical direction, or a list of
  directions — see §3.4) or a **param** (a plain value the tile needs,
  e.g. a threshold or an initial value). Which is which is determined
  by the tile's own real contract — give an unknown field name and the
  compiler tells you exactly which ports and params that tile actually
  has.

### 3.4 Field values

```
field := IDENT ":" value
value := IDENT | NUMBER | "[" IDENT ("," IDENT)* "]"
```

- A bare direction: `out: e` (one of `n`, `s`, `e`, `w`).
- A **fan-out** list of directions, for a port that can drive more than
  one physical neighbor at once: `out: [e, s]`.
- A number: `threshold: 8` or `init_data: 0xCAFEBEEF` (plain decimal or
  `0x`-prefixed hex).
- A **namespaced** identifier for a composed tile's own internal
  params: `cmp.threshold: 8` (see §5). Namespacing uses a literal dot
  inside one identifier token — `cmp.threshold`, not `cmp . threshold`.

### 3.5 `define` / `expose`

A program can define its own reusable composed tile, entirely inline:

```
program my_program {
    define my_sentinel {
        place acc as accumulator at (0, 0) {
            out: e
        }
        place cmp as comparator at (0, 1) {
            in: w
            out: e
        }
        place lat as latch at (0, 2) {
            set: w
        }

        expose inc -> acc.inc
        expose dec -> acc.dec
        expose clear -> lat.clear
        expose out -> lat.out
    }

    place s1 as my_sentinel at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
```

Inside `define`, a `place` statement's `(ROW, COL)` means a **relative
offset** from the defined tile's own anchor, not an absolute grid
position — the tile can be placed anywhere later, and every sub-cell
moves with it.

Two ways a sub-cell's own port or param gets resolved:

- **Wired internally** — give it a direction (for a port) or a value
  (for a param) directly inside that sub-cell's own `place` block. A
  port wired this way is a fixed link to another sub-cell, not
  something the tile's own caller ever sees. A **param** fixed this way
  is baked into the definition — it disappears from what the defined
  tile requires from its caller entirely (see §5.2).
- **Exposed** — `expose EXTERNAL_NAME -> SUBCELL.PORT` names a port
  under a name the tile's own caller uses (which doesn't have to match
  the sub-cell's own port name — `sentinel`'s own `inc` port really is
  `acc`'s `inc`, renamed for a cleaner outward-facing API).

Every port on every sub-cell must resolve one way or the other — the
compiler checks this the moment the `define` is written, not later when
someone tries to use it.

**A `define`d tile can itself be built from other `define`d (or
built-in, or `--model`-loaded) tiles** — nesting works to any depth,
with params double- (or triple-, or deeper-) namespacing naturally
(`s1.cmp.threshold`).

**Forward references:** a `place` statement may reference a `define`
appearing anywhere else in the same program, including later in the
file. As of `points.md #373`, a `define` may now also reference
another `define` appearing later in the file — `define`s are resolved
in real DEPENDENCY order (a topological sort), not textual order, so
`A` referencing `B` works regardless of which one is written first. The
one real remaining limit: a genuine CIRCULAR reference (`A` contains
`B` contains `A`, directly or through a longer chain) is still a real,
reported error — that would mean infinite physical cell expansion,
which can't exist on real hardware, not something dependency ordering
can paper over.

## 4. Tier-0 tiles — built-in primitives

One tile per physical core the super cell can become. Every tile below
is verified directly against the live registry (`nano/
super_tile_library_v1.py`), not transcribed from memory.

| Tile | Ports | Params | Notes |
|---|---|---|---|
| `nano_gate` | `out` | `topology` | A two-arrival NOR-tree gate. Accepts input from **any** physically wired neighbor — there's no `in`-style port to configure, because this core has no `upstream_mask` at all. `target: universal` — the only tile that also runs on a plain Unicell-n grid (see §8). |
| `ram_constant` | `out` | `init_data` | A fixed value, offered forever. No `in` port — nothing ever recaptures it. |
| `ram_flowing` | `in`, `out` | — | Captures one value, offers it, re-opens once drained. |
| `adder` | `in_a`, `in_b`, `out` | — | 32-bit add. `in_a`/`in_b` **share one underlying field** — whichever configured direction's arrival lands first becomes A, the second becomes B; direction alone doesn't decide the role. |
| `accumulator` | `inc`, `dec`, `out` | — | A running total, continuously offered. `inc`/`dec` are genuinely separate fields (unlike the adder). Same-tick arrivals on both net to zero. |
| `comparator` | `in`, `out` | `threshold` | Stateless: `1` if the input (signed) is `>= threshold`, else `0`. |
| `latch` | `set`, `clear`, `out` | — | A continuously-live sticky bit. `clear` wins if both arrive the same tick. |

## 5. Tier-1 tiles — built-in composed tiles

Multi-cell, real grid-adjacency-respecting compositions.

### `sentinel`

`accumulator -> comparator -> latch`, the proven monitor topology
(`points.md #291`-`#298`/`#306`-`#308`, real Quartus data: 78 ALM,
272.26 MHz). Ports: `inc`, `dec`, `clear`, `out`. Params:
`cmp.threshold`.

### `dual_threshold_monitor`

One accumulator fanning out to two independent low/high threshold
alarms. Ports: `inc`, `dec`, `clear_low`, `out_low`, `clear_high`,
`out_high`. Params: `cmp_low.threshold`, `cmp_high.threshold`.

### `twin_sentinel`

Two wholly independent `sentinel` instances side by side — mainly a
worked example of nested composition and double-namespaced params.
Ports: `s1_inc`, `s1_dec`, `s1_clear`, `s1_out`, `s2_inc`, `s2_dec`,
`s2_clear`, `s2_out`. Params: `s1.cmp.threshold`, `s2.cmp.threshold`.

### 5.1 Example — placing `sentinel`

```
program my_monitor {
    place alarm as sentinel at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
```

### 5.2 A worked example of fixing a param — a preset threshold

If you never want `sentinel`'s threshold to vary per-instance, `define`
your own version with it fixed:

```
program p {
    define alarm_at_10 {
        place acc as accumulator at (0, 0) { out: e }
        place cmp as comparator at (0, 1) {
            in: w
            out: e
            threshold: 10
        }
        place lat as latch at (0, 2) { set: w }

        expose inc -> acc.inc
        expose dec -> acc.dec
        expose clear -> lat.clear
        expose out -> lat.out
    }

    place a as alarm_at_10 at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        # no cmp.threshold here -- it's fixed at 10, not the caller's business
    }
}
```

## 6. User models — `--model FILE`

Compile against a tile you've written yourself, without editing the
compiler's own source (`points.md #345`):

```bash
python3 nano/dsl_cli_v1.py program.uc --model my_tile.json -o out.icm
```

`--model` may be given more than once. The JSON format is a direct
mirror of `ComposedTileSpec`/`SubCellPlacement`:

```json
{
    "name": "my_pair",
    "description": "an adder feeding a comparator",
    "subcells": [
        {"name": "add", "offset": [0, 0], "tile_name": "adder",
         "internal_directions": {"out": "e"}},
        {"name": "cmp", "offset": [0, 1], "tile_name": "comparator",
         "internal_directions": {"in": "w"}}
    ],
    "external_ports": {
        "in_a": ["add", "in_a"], "in_b": ["add", "in_b"],
        "out": ["cmp", "out"]
    }
}
```

A user model **shadows** a same-named built-in tile — an explicit
`--model` load is a deliberate override, not an accident. Loaded models
are per-invocation only; there's no cross-session persistence yet (that
belongs to the composer — see §9).

## 7. Other frontends

The DSL is not the only way to produce an `icm_v3.IcmV3File` for
Unicell-S — every frontend below compiles down to the exact same shared
IR (`program_ir_v1.ProgramIR`) and the exact same backend
(`dsl_compiler_v1.compile_program_ir()`), so they behave identically
for the same logical program.

- **A real Python-AST frontend** (`nano/python_ast_frontend_v1.py`,
  `points.md #348`) — a declarative subset of real Python syntax:

  ```python
  def my_sentinel_program():
      with define("my_sentinel"):
          place("acc", "accumulator", (0, 0), out="e")
          place("cmp", "comparator", (0, 1), **{"in": "w", "out": "e"})
          place("lat", "latch", (0, 2), set="w")
          expose("inc", "acc.inc")
          expose("dec", "acc.dec")
          expose("clear", "lat.clear")
          expose("out", "lat.out")

      place("s1", "my_sentinel", (0, 0), inc="n", dec="s", clear="s",
            out="e", **{"cmp.threshold": 8})
  ```
  Exactly one top-level `def program_name():` per file; only
  `place(...)` calls and `with define("name"): ...` blocks are
  understood; every argument must be a plain Python literal (a
  variable, a loop, or a function call is rejected with a real,
  explained diagnostic, not executed). `in` being a reserved Python
  keyword is why `**{"in": "w"}` dict-unpacking exists as an option
  alongside plain keyword arguments.

- **A minimal dict-based frontend** (`nano/python_frontend_v1.py`,
  `points.md #344`) exists purely to prove the IR/backend split itself
  works — not meant for hand-authoring programs.

- **A real C-AST frontend** (`nano/c_frontend_v1.py`, `points.md
  #374`) — uses `pycparser` (a real, pure-Python C99 parser) to parse
  REAL, valid C syntax:

  ```c
  void my_program(void) {
      place("r1", "ram_constant", 0, 0);
      field("r1", "out", "e");
      field("r1", "init_data", 42);
  }
  ```
  Deliberately narrower than the DSL's own current feature set, stated
  plainly: `place(name, tile, row, col)` + separate `field(name, key,
  value)` calls only — no inline fields (C has no natural keyword-
  argument syntax to lean on the way Python does), no `define`/`expose`
  yet, no direction-LIST-valued fields, no preprocessor (`#include`/
  macros aren't supported — every example must already be valid,
  unpreprocessed C). Exactly one top-level `void PROGRAM_NAME(void) {
  ... }` per file. Every argument must be a real C string or integer
  literal. A `field()` call must reference a name already established
  by an EARLIER `place()` call in the same function body.

  **A real Rust frontend is not built yet.** `tree-sitter`/`tree-
  sitter-rust` are confirmed installable (checked directly before
  choosing this approach for C), and the same design pattern would
  apply — a real, separate undertaking, not attempted in this pass.

## 8. Targets — Unicell-n vs. Unicell-S

Every built-in tile is tagged `target: "universal"` or `target:
"super-only"` (`points.md #339`). `nano_gate` is the only universal
one — it's the only tile using nothing beyond the basic subset a plain
Unicell-n cell (`unicell_stripped_v1.v` alone, no super shell) also
has. Everything else uses one of Unicell-S's five extra cores (RAM,
adder, accumulator, comparator, latch), which simply don't exist on a
plain Unicell-n grid. This manual's own `place`/`define` grammar always
targets Unicell-S; there's no dedicated Unicell-n program format yet.

## 9. What this isn't

- **Not the composer.** The composer (Stage 5, `points.md #20`) is a
  real, separate, later piece of this project — a spatial/visual
  authoring surface. This DSL is a text format; nothing here draws or
  places cells graphically.
- **Not persistence.** `--model` loads are per-invocation. There's no
  `~/.imago`-style saved library of your own tiles across sessions yet.
- **Not a placer.** This is an architectural distinction, not a missing
  feature — the project already established it for the old full-cell
  system (`points.md`, the SHAPE BINDER note): `model -> ICM
  (shape-neutral, portable) -> [BINDER] -> placement -> loader (dumb) ->
  silicon`. Every `(row, col)` this DSL writes is genuinely just a
  coordinate in a SHAPE — the relative structure of a program, not a
  commitment to real hardware geometry. Nothing here decides how that
  shape lands on an actual device: avoiding collisions with whatever
  else is already running, optimizing for real DSP/M20K locality,
  picking a physical region on a specific card — that's the loader/
  binder's job, a separate, not-yet-built stage for Unicell-S. Today,
  the numbers you write ARE what ends up in the emitted `IcmV3Record`s
  unmodified, which is a fine, working default for a single, standalone
  program — but it should be read as "this program's shape happens to
  be pinned directly onto the grid for now," not as evidence the
  compiler's job is (or should be) to do real hardware placement.

## 10. Known limitations, stated plainly

- **No multiple programs per file**, in either the DSL or the
  Python-AST frontend. Deliberate, not accidental — simpler to reason
  about at this stage.

## 11. Naming hygiene warnings

Two local-name hazards are caught and shown, as `severity: "warning"`
diagnostics — never blocking compilation, but never silently ignored
either (`points.md #350`):

- Two top-level `place`/`define` statements sharing one local name in a
  program.
- Two sub-cells sharing one local name inside the SAME `define` block
  — this one is genuinely ambiguous, not just hard to read, since
  `expose` resolves a sub-cell by name.

```
program p {
    place r1 as ram_constant at (0, 0) { out: e init_data: 1 }
    place r1 as ram_constant at (0, 1) { out: e init_data: 2 }
}
```
```
WARNING [lint] at 3:5: program statement 'r1'
  problem: the local name 'r1' is reused for more than one top-level statement in this program
  ...
```

## 12. A real safety net: circular tile references

`place`/`define` themselves now have their own real cycle protection
too, not just `--model` JSON files (`points.md #373`): the `define`-
ordering pass (§3.5) is a real topological sort with cycle detection,
so a genuine `A` contains `B` contains `A` reference among `define`s in
the SAME file is caught cleanly, with a clear diagnostic naming the
whole cycle — not left to `place_composed()`'s own later, lower-level
guard to catch it. A hand-crafted `--model` JSON file (§6), loaded
directly rather than authored through `define`, still relies on that
lower-level guard, since it bypasses the DSL's own ordering pass
entirely. Confirmed as a real, exploitable bug before fixing it, not
assumed: a self-referencing tile crafted directly and placed produced a
genuine Python `RecursionError` (`points.md #350`). Now caught cleanly
instead, at whichever layer first sees the cycle:

```
ValueError: circular composed-tile reference: a -> b -> a -- a tile can
never (directly or indirectly) contain itself
```
