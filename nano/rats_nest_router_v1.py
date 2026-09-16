"""
rats_nest_router_v1.py — points.md #760: the real, general Manhattan
router this session's exploration of the "rat's nest" placement
approach needed as its core, reusable primitive -- per Alan's own
direct proposal: place things loosely first (generous slack, easy to
get right), see where the real convergence points (nexuses) fall out,
then iteratively tighten while re-validating correctness at each step,
drawing the final shape toward a minimum footprint.

REAL, HONEST SCOPE: this module is the "loose" half only -- a real,
correct way to connect two arbitrary, non-adjacent real positions with
a straight-then-turn relay chain (at most one turn; this grid has no
diagonal moves, confirmed directly by #759's own "a relay can only go
straight" finding). The "tighten toward minimum" half -- iteratively
shrinking these routes while re-checking correctness -- is real,
separate, NOT YET BUILT work.

Three real, concrete bugs found and fixed while building this,
directly instructive for anyone extending it:
1. The turning relay (where a route switches from closing the column
   gap to closing the row gap) must have its own real 'in' set to the
   direction it ACTUALLY receives from (the previous segment's own
   direction), never inferred from the new segment's own direction.
2. A "skip the last hop" optimization (assume the last emitted relay
   is already adjacent to the real destination) is genuinely buggy --
   it's not, in general, since the loop's own natural termination
   already handles this correctly. Simpler is correct here; the
   optimization was not needed and was wrong.
3. A route's own `start_pos` must be the real PRODUCER's own position
   (the router itself handles the first hop internally) -- passing the
   position one step past the producer (where its own output happens
   to land) silently starts the route one cell short of anything real.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import vix_tile_library_v1 as vtl
import icm_vix_v1 as vix

_DIR_STEP = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
_OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}


def manhattan_route(start_pos: Tuple[int, int], start_out_dir: str,
                     end_pos: Tuple[int, int], end_out_dir: str,
                     uid_prefix: str, occupied: Dict[Tuple[int, int], str]
                     ) -> List[vix.HierCell]:
    """Connect a real producer at `start_pos` (already configured to
    offer in `start_out_dir`) to a real consumer at `end_pos`, via a
    real, straight-then-turn chain of `ram_flowing` relay cells --
    closing the column gap first, then the row gap. Returns the full
    list of real relay `HierCell`s, INCLUDING one placed at `end_pos`
    itself, offering `end_out_dir` (toward whatever real consumer sits
    beyond it) -- the caller does not need to place anything at
    `end_pos` separately. `occupied` is updated in place with every
    real position this route now uses, for the caller's own collision
    bookkeeping across multiple routes.

    Real, deliberate scope: this does NOT check for collisions with
    cells the caller hasn't told it about via `occupied`, and it does
    NOT check timing/arrival-collision hazards at all -- purely a
    real, correct GEOMETRIC connector. A real placement system would
    need its own, separate pass checking `occupied` before calling
    this, and a separate real timing check (`#750`'s own convergence-
    collision hazard) after routing every producer into a shared
    consumer."""
    cells: List[vix.HierCell] = []
    row, col = start_pos
    incoming_dir = start_out_dir
    dr, dc = _DIR_STEP[start_out_dir]
    row, col = row + dr, col + dc
    end_row, end_col = end_pos
    i = 0

    def emit(row: int, col: int, out_dir: str, incoming_dir: str) -> vix.HierCell:
        c = vtl.place(vtl.TILE_RAM_FLOWING, {"in": _OPP[incoming_dir], "out": out_dir},
                      cell_id=f"{uid_prefix}_{i}", rel_row=row, rel_col=col)
        occupied[(row, col)] = c.cell_id
        return c

    while (row, col) != (end_row, end_col):
        if col != end_col:
            step_dir = "e" if end_col > col else "w"
        else:
            step_dir = "s" if end_row > row else "n"
        cells.append(emit(row, col, step_dir, incoming_dir))
        incoming_dir = step_dir
        i += 1
        dr, dc = _DIR_STEP[step_dir]
        row, col = row + dr, col + dc

    cells.append(emit(end_row, end_col, end_out_dir, incoming_dir))
    return cells
