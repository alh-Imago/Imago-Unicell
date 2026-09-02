"""vm_mirror_v1.py — points.md #601: the real MAN -> mirrored-VM
construction. `#598`'s own entry described "VM mirror mode" as
"already real and existing" -- checked directly before building
anything here, and that was NOT accurate: `SuperGrid` takes a flat
list of ICM records at whatever `(row, col)` they happen to carry,
with zero code anywhere tying a grid to a real card's MAN file or to
`project_assemble_v1.py`'s own real N-cell tiling convention
(`grid_dims()`/`cell_positions()` -- the exact row-major layout a real
Quartus build for that card/cell-count would actually use). "Mirror
mode" existed only as a docstring distinction from "free mode," never
as an enforced mechanism.

WHY THIS MATTERS, Alan's own direct point: a simulated Walker needs an
HONEST target. Discovering topology on an arbitrary Python grid shape
that no real hardware build could ever produce would prove nothing
about the real, card-based methodology this whole exercise exists to
demonstrate (`#598`). This module is the real, minimal fix: given a
MAN file and a cell count, compute the exact same real row-major
layout `project_assemble_v1.py` would use for an actual Quartus build
of that size on that card, and validate any program's own real placed
cells against it -- REUSING `grid_dims()`/`cell_positions()` directly,
not a reimplementation, so there is exactly one real source of truth
for "what does an N-cell layout on this card look like," shared with
the actual project generator.

REAL, HONEST SCOPE: this checks TOPOLOGY (every placed cell falls on a
position a real N-cell build would actually instantiate, no two
records collide), not real ALM/DSP capacity -- per-cell ALM cost
varies by shell version and core mix (`#574`-`#592`) and isn't a
settled-enough figure to enforce a hard budget check against here.
That remains a real, separate, still-open question, not conflated with
this module's own real job.
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import project_assemble_v1 as pa  # noqa: E402


@dataclass
class MirrorBounds:
    """The real, honest shape of an N-cell layout on a real card --
    everything a simulated Walker (or anything else) needs to know
    what "fits" means for this session."""
    card_id: str
    man_path: str
    cells: int
    rows: int
    cols: int
    valid_positions: Set[Tuple[int, int]]


class MirrorFitError(Exception):
    """Raised when a compiled/loaded program's own real cell placements
    don't fit the real card's own N-cell layout -- the honest failure
    mode for a program that could never correspond to an actual
    Quartus build, rather than silently accepting it."""

    def __init__(self, problems: List[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


def load_mirror_bounds(man_path: str, cells: int) -> MirrorBounds:
    """Real, direct reuse of `project_assemble_v1.load_man()`/
    `grid_dims()`/`cell_positions()` -- the SAME functions the actual
    Quartus project generator calls, so a mirrored VM session's own
    topology is genuinely, not just nominally, the same shape a real
    build for this card/cell-count would produce."""
    if cells < 1:
        raise ValueError("cells must be >= 1")
    man = pa.load_man(man_path)
    rows, cols = pa.grid_dims(cells)
    positions = pa.cell_positions(cells, rows, cols)
    return MirrorBounds(
        card_id=man["card_id"], man_path=man_path, cells=cells,
        rows=rows, cols=cols, valid_positions=set(positions),
    )


def check_records_fit(records, bounds: MirrorBounds) -> List[str]:
    """Real, honest validation -- returns a list of real problem
    strings (empty list = fits). Never raises itself; callers (e.g.
    `VMSession.from_man()`) decide whether a non-empty result is
    fatal."""
    problems: List[str] = []
    seen: Set[Tuple[int, int]] = set()
    for r in records:
        pos = (r.row, r.col)
        if pos not in bounds.valid_positions:
            problems.append(
                f"cell_id {r.cell_id} at ({r.row},{r.col}) is outside the real "
                f"{bounds.rows}x{bounds.cols} row-major layout for {bounds.cells} "
                f"cells on card '{bounds.card_id}' -- not a position a real "
                f"Quartus build of this size would ever instantiate"
            )
        if pos in seen:
            problems.append(f"cell_id {r.cell_id} collides with another real record already placed at ({r.row},{r.col})")
        seen.add(pos)
    return problems
