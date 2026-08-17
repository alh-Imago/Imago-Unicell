"""
loader_v1.py — the real loader/binder stage, item 4 of `points.md
#370`'s own priority list. Takes a compiled program's own SHAPE (a set
of `IcmV3Record`s at row/col coordinates relative to wherever the
compiler happened to place them, per `#350`'s own corrected framing --
"ICM coordinates are shape offsets, not hardware placement
commitments") and BINDS it to real coordinates on a shared target grid.

Deliberately genericLY REUSABLE, not workbench-specific: this module
has zero knowledge of HTTP, sessions, or regions -- it operates purely
on `IcmV3Record`s and a plain `Dict[(row, col), Any]` occupancy map
(the exact same shape `SuperGrid.cells` already uses), so anything
holding a grid can call it, not just `nano/workbench_v1.py`. The
workbench (`points.md #375`) is the first real caller, refactored to
delegate to this module instead of its own inline shift+collision
logic -- proving this is a real, independent piece, not workbench
glue extracted after the fact.

THREE REAL MODES:
  - MANUAL (`row_offset`/`col_offset` both given): shift every record
    by that exact offset, check for collisions, done. The same
    behavior the workbench's own `load_region()` already had.
  - AUTO (`row_offset`/`col_offset` both omitted, `dsp_columns` not
    given): a real, honest first-fit search -- try candidate anchor
    offsets in row-major order from `(0, 0)` up to `search_bound`,
    return the FIRST offset with zero collisions against the target
    grid's own occupied cells.
  - DSP-AWARE AUTO (`dsp_columns` given, `#377`): a real cost-based
    search -- among every collision-free offset, pick the one
    minimizing the real, computed distance from DSP-consuming cells to
    the nearest given DSP column. See `find_dsp_aware_placement()`'s
    own docstring for the honest, stated scope limit versus the full
    anchor-first-seeded-graph-embedding design on record
    (`points.md #54`/`#220`).

A REAL FINDING WORTH STATING PLAINLY (`#377`): `current/PLAN.md`'s own
"Hybrid Hard-IP Architecture" section, which also discusses DSP
placement, is answering a genuinely DIFFERENT, mostly-obsolete question
-- whether to offload arithmetic from the OLD soft-fabric (NOR-gate-
composed) tile model onto hard DSP blocks. That question doesn't apply
the same way to Unicell-S, where adder/accumulator/comparator/RAM are
already real, distinct hardware cores, not composed from NOR gates at
all. This module answers a different, current question instead: given
those real cores already exist, where on the physical grid should they
be PLACED for good DSP-column locality. Not the same problem, and this
module doesn't claim to resolve `PLAN.md`'s own separate one.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

from icm_v3 import IcmV3Record
from dsl_diagnostics_v1 import CompileDiagnostic

# Real engineering judgment, NOT measured from actual Quartus synthesis
# data (that data doesn't exist yet -- the `.isi` sidecar concept,
# per `points.md #54`/`#220`, is itself still "identified, not yet
# implemented"). RAM/adder/accumulator/comparator are the arithmetic/
# memory cores, reasonably likely to synthesize using real DSP/M20K
# blocks on Arria 10; nano (pure NOR-gate logic) and latch (a single
# flip-flop) are pure logic-fabric cells with no obvious DSP/M20K need.
# A real, honestly-stated, overridable DEFAULT, not a measured fact.
DEFAULT_DSP_CONSUMING_CORES: FrozenSet[str] = frozenset({"ram", "adder", "accumulator", "comparator"})


def _footprint(records: List[IcmV3Record], row_offset: int, col_offset: int) -> List[Tuple[int, int]]:
    return [(r.row + row_offset, r.col + col_offset) for r in records]


def _collisions(positions: List[Tuple[int, int]], occupied: Dict[Tuple[int, int], object]) -> List[Tuple[int, int]]:
    return [p for p in positions if p in occupied]


def find_auto_placement(records: List[IcmV3Record], occupied: Dict[Tuple[int, int], object],
                         search_bound: int = 64) -> Optional[Tuple[int, int]]:
    """A real, honest first-fit search: try every `(row_offset,
    col_offset)` pair in row-major order from `(0, 0)` up to
    `search_bound` (exclusive) in both dimensions, return the FIRST
    offset whose shifted footprint has zero collisions with
    `occupied`. Returns `None` if nothing in that bound works -- the
    caller decides how to report that, this function never raises."""
    if not records:
        return (0, 0)
    for row_offset in range(search_bound):
        for col_offset in range(search_bound):
            positions = _footprint(records, row_offset, col_offset)
            if not _collisions(positions, occupied):
                return (row_offset, col_offset)
    return None


def _column_distance_to_nearest(col: int, dsp_columns: Iterable[int]) -> int:
    dsp_columns = list(dsp_columns)
    if not dsp_columns:
        return 0
    return min(abs(col - c) for c in dsp_columns)


def find_dsp_aware_placement(records: List[IcmV3Record], occupied: Dict[Tuple[int, int], object],
                              dsp_columns: Iterable[int],
                              dsp_consuming_cores: FrozenSet[str] = DEFAULT_DSP_CONSUMING_CORES,
                              search_bound: int = 64) -> Optional[Tuple[int, int]]:
    """A real, but genuinely SIMPLER first pass than the full anchor-
    first-seeded-graph-embedding design already on record (`points.md
    #54`/`#220`'s own "pin DSP-consuming tiles at known DSP columns
    first, grow outward BFS along dataflow edges, cost = hops"). This
    function does the FIRST half honestly (bias placement toward DSP
    columns for the cells that plausibly need them) but treats the
    WHOLE shape as one rigid unit rather than doing real per-cell BFS
    growth along dataflow edges -- that's a genuinely bigger, separate
    piece of work, deferred honestly, not attempted here.

    `dsp_columns` is a real, caller-supplied list of column indices --
    NOT a hardcoded hardware assumption. No real Quartus post-fit data
    confirming actual DSP-column positions on any specific card exists
    yet (the `.isi` sidecar concept itself is still "identified, not
    yet implemented", `points.md #54`) -- this parameter is exactly
    where that real data would plug in once it exists.

    Among every collision-free candidate offset within `search_bound`,
    picks the one minimizing the REAL, computed sum of column-distances
    from each DSP-consuming cell's own final position to its nearest
    given DSP column -- a genuine cost function (`points.md #220`'s own
    "cost = hops" framing, approximated here as column distance, not a
    full routed-hop count), not just "first that fits"
    (`find_auto_placement()`'s own simpler standard). Returns `None` if
    nothing collision-free exists in the search bound, same contract as
    `find_auto_placement()`."""
    if not records:
        return (0, 0)

    best_offset: Optional[Tuple[int, int]] = None
    best_cost: Optional[int] = None
    for row_offset in range(search_bound):
        for col_offset in range(search_bound):
            positions = _footprint(records, row_offset, col_offset)
            if _collisions(positions, occupied):
                continue
            cost = sum(
                _column_distance_to_nearest(pos[1], dsp_columns)
                for rec, pos in zip(records, positions)
                if rec.core in dsp_consuming_cores
            )
            if best_cost is None or cost < best_cost:
                best_cost, best_offset = cost, (row_offset, col_offset)
            if cost == 0:
                return best_offset   # can't do better than exactly on-column
    return best_offset


def bind_shape(records: List[IcmV3Record], occupied: Dict[Tuple[int, int], object],
               row_offset: Optional[int] = None, col_offset: Optional[int] = None,
               dsp_columns: Optional[Iterable[int]] = None,
               dsp_consuming_cores: FrozenSet[str] = DEFAULT_DSP_CONSUMING_CORES,
               search_bound: int = 64,
               what: str = "binding a program's shape to the grid"
               ) -> Tuple[Optional[List[IcmV3Record]], List[CompileDiagnostic]]:
    """The real entry point. `records` is never mutated in place (real
    copies are returned) -- callers can safely retry with a different
    offset without the original shape having been silently altered by
    a prior failed attempt.

    MANUAL mode: both `row_offset`/`col_offset` given -- shifts and
    checks for collisions, exactly matching the workbench's own
    original inline behavior (`#363`) before this module existed.

    AUTO mode: both omitted (`None`), `dsp_columns` not given -- calls
    `find_auto_placement()` and uses whatever it finds, or reports a
    real, clear diagnostic if nothing fits within `search_bound`.

    DSP-AWARE AUTO mode (`#377`): both offsets omitted AND `dsp_columns`
    given -- calls `find_dsp_aware_placement()` instead, biasing the
    search toward good DSP-column locality for the cores in
    `dsp_consuming_cores` rather than plain first-fit.

    Real, deliberate validation: exactly one of "both given" or "both
    omitted" is accepted -- a caller passing ONE but not the other is a
    genuine misuse, reported as a real error, not silently guessed at."""
    if (row_offset is None) != (col_offset is None):
        return None, [CompileDiagnostic(
            severity="error", stage="bind", what=what,
            problem="row_offset and col_offset must both be given (manual "
                    "placement) or both omitted (auto placement) -- got only one",
            why="a partial offset has no sensible meaning -- there's no way "
                "to auto-place along just one axis while pinning the other",
        )]

    if row_offset is None:
        if dsp_columns is not None:
            found = find_dsp_aware_placement(records, occupied, dsp_columns,
                                              dsp_consuming_cores, search_bound)
        else:
            found = find_auto_placement(records, occupied, search_bound)
        if found is None:
            return None, [CompileDiagnostic(
                severity="error", stage="bind", what=what,
                problem=f"no valid auto-placement found within a "
                        f"{search_bound}x{search_bound} search area",
                why="every candidate offset in that range collided with "
                    "something already on the grid, or the grid is simply "
                    "too full near the origin",
                suggestion="try a smaller shape, clear some existing regions "
                           "first, or fall back to a manual row_offset/"
                           "col_offset if you know a specific free spot",
            )]
        row_offset, col_offset = found

    shifted = [replace(r, row=r.row + row_offset, col=r.col + col_offset,
                        core_config=copy.deepcopy(r.core_config),
                        addon_config=copy.deepcopy(r.addon_config))
               for r in records]

    positions = [(r.row, r.col) for r in shifted]
    collisions = _collisions(positions, occupied)
    if collisions:
        return None, [CompileDiagnostic(
            severity="error", stage="bind", what=what,
            problem=f"collides with existing cells at {sorted(set(collisions))} "
                    f"at offset ({row_offset},{col_offset})",
            why="two different placements can't share one physical cell",
            suggestion="choose a different offset, or omit row_offset/"
                       "col_offset entirely to let the loader find one "
                       "automatically",
        )]

    return shifted, []
