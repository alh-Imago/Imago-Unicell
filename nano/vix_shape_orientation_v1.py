"""
vix_shape_orientation_v1.py — points.md #778: the real, practical
helper Alan's own direct question motivated -- "examine the
orientation of the shape, that may have an effect overall." Confirmed
directly, measurably (see `tests/vm/test_shape_orientation_v1.py`): a
library shape's own fixed port orientation, when it doesn't match
where its actual real neighbors sit, costs real, additional cells and
relay hops (50% more in the tested example) versus orienting the
shape's own ports to match.

This module provides the real, concrete "which orientation" decision
`#777`'s own shape catalog was silent on -- `choose_convergence_shape()`
picks WHICH shape (plain chain / priority / stagger / sequencer); this
picks HOW that shape's own ports should face, given where its real
neighbors actually are, before any placement or routing happens.
"""
from __future__ import annotations

from typing import Dict, Tuple

Position = Tuple[int, int]

_ALL_DIRS = ("n", "s", "e", "w")


def _general_direction(from_pos: Position, to_pos: Position) -> str:
    """The real, general cardinal direction from `from_pos` TOWARD
    `to_pos` -- for non-cardinally-aligned positions, picks whichever
    axis has the larger real distance (the same real, practical rule
    real PCB/schematic tools use for pin-side assignment: face the
    side the connection travels furthest along)."""
    dr = to_pos[0] - from_pos[0]
    dc = to_pos[1] - from_pos[1]
    if abs(dr) >= abs(dc):
        return "s" if dr > 0 else ("n" if dr < 0 else ("e" if dc >= 0 else "w"))
    return "e" if dc > 0 else "w"


def choose_two_way_orientation(target_pos: Position, src_a_pos: Position,
                                src_b_pos: Position) -> Dict[str, str]:
    """Real, direct answer to Alan's own question for the most common,
    real case this session's own work needed: a 2-way combine unit (a
    `priority` cell with two real inputs and one real output). Returns
    a real dict `{"in_a": dir, "in_b": dir, "out": dir}` -- the three
    real cardinal directions to configure the shape's own ports with,
    chosen to match where its real neighbors actually sit, rather than
    a fixed default requiring a real, costly detour when it doesn't
    match (confirmed directly, `#778`).

    Real, deliberate, bounded scope: if both real sources fall on the
    SAME general direction (a real tie), the second one is assigned
    the next real direction in a fixed, deterministic rotation order
    (`n`->`s`->`e`->`w`) rather than colliding on the same face -- a
    real, honest, simple tie-break, not an optimal one. The real
    output direction is whichever of the two remaining real directions
    is NOT used by either input, chosen deterministically (the first
    one, in the same fixed rotation order) -- a genuinely general
    "which way should the result exit" choice is real, separate,
    unattempted work (it would need to know the target's OWN real
    downstream consumer position too, which this function does not
    take as an input)."""
    dir_a = _general_direction(target_pos, src_a_pos)
    dir_b = _general_direction(target_pos, src_b_pos)
    if dir_b == dir_a:
        for candidate in _ALL_DIRS:
            if candidate != dir_a:
                dir_b = candidate
                break
    remaining = [d for d in _ALL_DIRS if d not in (dir_a, dir_b)]
    out_dir = remaining[0]
    return {"in_a": dir_a, "in_b": dir_b, "out": out_dir}
