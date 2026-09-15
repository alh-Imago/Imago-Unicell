# ICM VIX Format — the hierarchical program format for the VIX Carrier lineage

*Real, implemented, verified 2026-09-15. Implementation:
`nano/icm_vix_v1.py`. Tests: `tests/vm/test_icm_vix_v1.py` (14/14
passing). Design history: `points.md` #737-#742 (three real, distinct
examples proven before this spec was written down), formalized `#747`.*

## Why this is a new format, not v3/v4 extended

`icm_v3.py` and `icm_v4.py` are both scoped to the OLD core lineage's
own flat SUPER_LATCH record shape — a plain list of placed cells, one
record per cell, no notion of a reusable structure. Real compiled
output (loop unrolling, repeated inlined patterns) genuinely has
repeating shapes a flat format can't name — the direct, real motivation
Alan raised for this format (`#737`). Rather than stretching v3/v4's
own field list to cover something structurally different, this is a
new, differently-named format, matching the same honest-naming
discipline `icm_v4.py`'s own docstring already establishes: `icm_vix`,
because it targets the VIX Carrier lineage specifically, not the old
`unicell_super_v1.v`-`v9.v` family.

## The real design, proven before it was written down

Every mechanic below was tested against three genuinely different real
examples (`nano/examples/`) before this spec existed — this document
describes what was proven, not a speculative design:

- **`small_relay_chain.icm-hier.json`** — a linear, 8-cell chain:
  single-use patterns at each end, a real, 2-cell pattern used three
  times in the middle (chosen specifically to exercise multi-cell port
  attachment).
- **`parallel_reduction_tree.icm-hier.json`** — a 4-lane parallel
  reduction: real repetition exercised meaningfully (four values
  flowing concurrently), converging through a real adder spine.
- **`cordic_z_convergence.icm-hier.json`** — the opposite case: 4
  genuinely DISTINCT stage patterns, nothing repeats at all, each
  carrying its own real `atan(2^-i)` constant, with a real, dynamic,
  sign-based `branch` decision routing each stage's own value.

## The real, whole-file shape

```json
{
  "format_version": "icm-vix-v1",
  "name": "example_program",
  "description": "...",
  "header": {"cores_used": ["ram", "adder"], "cell_count": 12},
  "patterns": {
    "pattern_name": {
      "cells": [
        {"cell_id": "c0", "rel_row": 0, "rel_col": 0, "core": "ram",
         "core_config": {"downstream_mask": ["E"]}, "io_name": "input"}
      ]
    }
  },
  "design_map": {
    "placements": [
      {"instance": "inst1", "pattern": "pattern_name", "at": [0, 0],
       "overrides": {"c0": {"io_name": "input_0"}}}
    ],
    "connections": [
      {"from": ["inst1", 0, 0, "E"], "to": ["inst2", 0, 0, "W"]},
      {"from": ["inst2", 0, 1, "E"], "to": "NC"}
    ]
  },
  "record_hash": "<sha256 of canonical patterns + design_map>"
}
```

## Patterns — every real shape, even one used exactly once (`#738`)

**The real, central design rule:** every distinct real cell shape
becomes a named pattern, whether it's used once or a thousand times.
This removes the need for any per-instance-override mechanism on
`core_config` itself — a pipeline's first stage, middle stages, and
last stage that genuinely differ simply become three separate, named
patterns, each internally fixed and exact, rather than one shared
template needing parameterized variation. The real, honest cost: a
design with many genuinely distinct shapes produces many pattern
entries, some used only once — but even a single-use pattern is a
named, legible unit, and any shape that DOES repeat still collapses to
one real definition plus cheap references.

A pattern's own cells are addressed in LOCAL coordinates
(`rel_row`/`rel_col`), relative to that pattern's own (0,0) — never
absolute. Each cell carries the exact same real fields `icm_v3.
IcmV3Record` does (`core`, `core_config`, `addon_config`, `io_name`,
`preload_value`), minus `row`/`col` (replaced by `rel_row`/`rel_col`)
and `cell_id` (still present, but scoped to the pattern's own local
namespace — see Placements below for how it becomes globally unique).

## The design map — placement and advisory wiring, kept genuinely separate

### Placements — direct, explicit anchors, never solver-derived (`#739`)

A placement names a real instance (`instance`), which pattern it uses
(`pattern`), and a direct, absolute anchor position (`at: [row, col]`).
**The loader never solves for placement** — `at` is always a given,
explicit coordinate; each pattern cell's own real, global position is
simply `(at[0] + rel_row, at[1] + rel_col)`. This is a deliberate
design choice, not a limitation: a loader that tried to derive
placement from the connection graph would be solving a real,
unneeded constraint problem (confirmed directly while building this,
`#742`'s own real find-and-fix history).

Each cell's own real, GLOBAL `cell_id` (used in the flattened
`IcmV3Record` list, the connections' own addressing, and diff files)
is `f"{instance}.{cell_id}"` — the instance name and the pattern-local
cell id, joined with a dot.

### Per-instance overrides — the one real, principled exception (`#741`)

A placement may carry an optional `overrides` dict, keyed by the
pattern's own local `cell_id`, supplying `io_name` and/or
`preload_value` for that one specific instance. **This is not a crack
in "every shape is a pattern"** — `io_name` and `preload_value` are
not part of a cell's own real computational SHAPE (which determines
which pattern it belongs to); they're metadata about how one specific
placed instance is being used externally. Four real, parallel uses of
the SAME pattern (e.g. four input lanes) genuinely need four different,
unique `io_name`s — which can't live in the one, shared pattern
definition without breaking the "identical everywhere it's used"
guarantee that makes pattern reuse meaningful in the first place.

### Connections — real, precise, advisory cross-checking (`#739`)

**The single most load-bearing fact in this whole format, confirmed
directly and worth restating precisely: the `connections` list is
NOT what makes cells actually connect.** The real, authoritative
wiring mechanism is exactly the one that already exists today and
needs no reinvention — each flattened cell's own real `core_config`
bits (`upstream_mask`/`downstream_mask`, or `branch`'s own genuinely
different `upstream_dir`, a single direction rather than a mask,
confirmed directly against `_deliver_branch()`). The connections list
is real, human-readable documentation and machine-checkable
cross-referencing — confirming a given placement's own real, configured
bits actually agree with what the design says should connect,
catching a real mismatch rather than driving the connection itself.
This is directly, precisely the same real pattern `tools/project_
assemble_v1.py`'s own `discover_instantiated_modules()`/`check_
dependency_compatibility()` (`#590`) already uses elsewhere in this
project: a real, useful, best-effort ADVISORY check, never the
authoritative source of truth.

A connection's `from` is always a real 4-tuple: `[instance, rel_row,
rel_col, face]` — the source cell's own pattern-LOCAL coordinates
(not global), and which of its own faces (`N`/`S`/`E`/`W`) the link is
declared on. `to` is either the same 4-tuple shape (a real reference
to another placed cell), or the literal string `"NC"` — a real,
distinct, documented "deliberately not connected" claim, borrowed
directly from standard hardware/schematic notation rather than
invented. `NC` is itself a checkable claim, not an unchecked escape
hatch: `check_connections()` flags a declared `NC` whose source cell
actually has that face configured in its own real `core_config`.

`check_connections()` verifies, for every non-`NC` connection: (1) the
two endpoints are genuinely grid-adjacent in the stated direction
(confirms `to`'s own real global position is exactly one step from
`from`'s, in the declared face's direction); (2) the declared faces are
real opposites (`N`↔`S`, `E`↔`W`); (3) the source cell's own real
`downstream_mask` includes the declared face; (4) the destination
cell's own real `upstream_mask` (or `upstream_dir`, for `branch`)
includes the opposite face. Every check returns a real, human-readable
warning string on mismatch — **it never raises**, matching `#590`'s own
established advisory-check shape: the real compile/RTL remains
authoritative either way.

## The header — always derived, never hand-maintained (`#734`'s own lesson applied here)

`cores_used` and `cell_count` are computed fresh, every time, from the
real pattern and placement data — never a stored, hand-maintained field
that can silently go stale. This is the exact same real discipline
`minimum_shell_version()` already established for the old lineage
(scan the real records, don't trust a stored field), applied here from
day one specifically because `#734`'s own real regression (a
hand-maintained dependency list going stale across a whole correction
arc) is the exact failure mode this design avoids by construction.

## Structural validity vs. advisory mismatch — a real, important distinction

`flatten()` raises `IcmVixFormatError` for a genuinely INVALID
document — a placement referencing a pattern that doesn't exist, or
two cells landing on the same real grid position. These are real
structural errors; the document cannot be flattened into a real,
executable grid at all. `check_connections()`, by contrast, NEVER
raises — a connection mismatch is a real, useful warning about likely
programmer error, not a reason to refuse to run the design. Keeping
these two failure modes distinct matters: a structural error means
"this file cannot become a program"; an advisory mismatch means "this
program might not do what its own connections claim it does."

## `record_hash` — the same real integrity discipline as ICM v3

Computed the same way `icm_v3.py`'s own `record_hash()` is (a
canonical JSON serialization, `sort_keys=True, separators=(",",
":")`, SHA-256), over the real patterns and design map. `IcmVixFile.
load()` recomputes it and raises `ValueError` on mismatch, catching a
hand-edited or corrupted file rather than silently loading it —
confirmed directly by deliberately corrupting a saved file and
checking the load fails with a clear, specific error.

## The real, separate save/state mechanism (`#737`'s own design, now with a full, tested round trip)

**The genuinely important architectural point, confirmed by checking
the actual code, not just asserted:** program STRUCTURE and runtime
STATE are two different, orthogonal concerns. A named pattern is, by
definition, a SHARED template used by potentially many instances —
attaching one specific run's own current values directly into a
pattern's shared definition doesn't make sense, since different
instances of the same pattern hold different real values at any given
moment.

**The real mechanism, per `#737`'s own original design, restated
directly by Alan and now fully implemented:** a save is the original
structure file (already on disk, genuinely unchanged) PLUS a real,
separate diff file, holding only the current runtime values that
matter, keyed by each cell's own real, stable, globally-unique
`cell_id` — the exact same identifier `flatten()` already produces.

- **`snapshot_diff(records, grid)`** — real, direct capture of every
  cell's own current value, reading whichever of the real, per-core
  "current value" fields is populated (`ram`'s own `ram_data_reg` when
  `ram_data_valid`, `adder`'s own `adder_out_buffer` when `adder_data_
  valid`, `accumulator`'s own always-live `acc_total`).
- **`save_state(structure_path, diff_path, records, grid)`** — writes
  the diff file, referencing the structure path rather than duplicating
  it.
- **`load_state(diff_path)`** — loads the diff file, then loads the
  ORIGINAL structure it references fresh from disk (never assumes it's
  already in memory), returning `(icm, records, diff)` ready for a
  fresh grid.
- **`apply_diff(records, grid, diff)`** — replays a loaded diff onto a
  grid, by real `cell_id`. Returns any `cell_id`s the diff references
  that no longer resolve to a real cell (a genuinely changed structure
  file since the diff was saved) — applies every OTHER real entry
  regardless, rather than failing the whole operation over one stale
  reference.

**Verified as a real, complete round trip, not just as separate
pieces:** run the real CORDIC pipeline (`#742`) partway, save
(structure + diff), then load the diff, load the original structure
FRESH from disk, build a COMPLETELY NEW grid that never ran anything,
and replay the diff onto it — the exact same, known-correct result
(`z_output = -404`) reappears (`tests/vm/test_icm_vix_v1.py::
test_full_state_save_and_restore_round_trip`). This is the real piece
`#744` named as "never attempted" — now proven working, not just
designed.

## What's verified, and how

1. **14/14 real tests** (`tests/vm/test_icm_vix_v1.py`), covering: all
   three real example files loading clean with zero advisory warnings;
   all three actually RUNNING to their own known-correct result (not
   just "it loads") — the relay chain's exact input value, the
   reduction tree's exact sum (100), and the CORDIC pipeline's exact,
   independently-computed convergence value (-404); the advisory check
   catching a real, deliberate break in a shared pattern AND a false
   `NC` claim; per-instance overrides producing genuinely distinct
   `io_name`s from one shared pattern; structural errors (unknown
   pattern reference) raising correctly; the structure file's own
   save/load round trip; `record_hash` catching a hand-edited file;
   and the full state save/restore round trip onto a fresh grid.
2. **Zero regression** — the full project test suite (749 tests) was
   re-run after this module and its tests were added, confirming no
   existing behavior anywhere else changed.

## What's deliberately NOT built yet, stated honestly

- **Nested patterns** (a pattern containing other named patterns).
  None of the three real examples needed more than one level — a real,
  deliberately deferred question (`#737`), not decided against.
- **Any LLVM IR or DSL compiler emit path targeting this format.**
  Confirmed directly (`#746`): the entire current compiler backend
  (`nano/dsl_compiler_v1.py`'s own `compile_program_ir()`) emits only
  `icm_v3.IcmV3File`/`icm_v4.IcmV4File` — this format has no compiler
  producing it yet, only the hand-authored/prototype-generated real
  examples proven above.
- **Workbench integration** — `nano/workbench_v1.py`'s own `save_icm`/
  `load_icm` are still scoped to `icm_v3.IcmV3File` only; real,
  separate work to wire this format (and its own real save/state
  mechanism) into the workbench's own load/save flow.
- **A VIX-specific tile library.** `#746`'s own real finding stands:
  `super_tile_library_v1.py` only defines tiles for the old lineage;
  no tile exists yet for `mul`/`priority`/the `_v4c` core family this
  format is ultimately meant to describe designs built from.
