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

TWO REAL MODES:
  - MANUAL (`row_offset`/`col_offset` both given): shift every record
    by that exact offset, check for collisions, done. The same
    behavior the workbench's own `load_region()` already had.
  - AUTO (`row_offset`/`col_offset` both omitted): a real, honest
    first-fit search -- try candidate anchor offsets in row-major
    order from `(0, 0)` up to `search_bound`, return the FIRST offset
    with zero collisions against the target grid's own occupied cells.

DELIBERATE, STATED SCOPE LIMIT, not glossed over: this is a real, but
genuinely simple placement search -- first-fit, not optimal, and NOT
DSP-aware. The real DSP-locality design (anchor-first seeded graph
embedding, pinning DSP-consuming tiles at known DSP columns first) is
item 6 of `#370`'s own priority list, a separate, later, harder
problem -- this loader gives every shape the exact same treatment
regardless of which cores it uses, which is honest but not yet
hardware-aware in that specific sense.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from icm_v3 import IcmV3Record
from dsl_diagnostics_v1 import CompileDiagnostic


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


def bind_shape(records: List[IcmV3Record], occupied: Dict[Tuple[int, int], object],
               row_offset: Optional[int] = None, col_offset: Optional[int] = None,
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

    AUTO mode: both omitted (`None`) -- calls `find_auto_placement()`
    and uses whatever it finds, or reports a real, clear diagnostic if
    nothing fits within `search_bound`.

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
