"""tests/vm/test_vix_shape_orientation_v1.py — points.md #778: real
tests for the orientation-selection helper, confirming it computes the
same "matched," measurably cheaper orientation directly proven in
`test_shape_orientation_v1.py`, not just a plausible-looking function.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from vix_shape_orientation_v1 import choose_two_way_orientation  # noqa: E402


def test_matches_the_real_measured_efficient_orientation():
    """The exact real geometry from #778's own direct cost comparison
    -- confirms this function recommends the SAME orientation that was
    directly measured to cost 12 cells / 8 hops, not the mismatched
    one that cost 18 cells / 14 hops."""
    result = choose_two_way_orientation(target_pos=(0, 0), src_a_pos=(0, -5), src_b_pos=(5, 0))
    assert result["in_a"] == "w"
    assert result["in_b"] == "s"
    assert result["out"] not in (result["in_a"], result["in_b"])


def test_sources_directly_north_and_south():
    result = choose_two_way_orientation(target_pos=(5, 5), src_a_pos=(0, 5), src_b_pos=(10, 5))
    assert result["in_a"] == "n"
    assert result["in_b"] == "s"


def test_tied_direction_does_not_collide_on_the_same_face():
    """Both real sources fall on the same general direction (both
    north) -- confirmed the tie-break assigns a genuinely different,
    real face to the second one rather than colliding."""
    result = choose_two_way_orientation(target_pos=(5, 5), src_a_pos=(0, 4), src_b_pos=(0, 6))
    assert result["in_a"] != result["in_b"]
    assert result["out"] not in (result["in_a"], result["in_b"])


def test_all_three_directions_are_always_distinct():
    import random
    rng = random.Random(42)
    for _ in range(50):
        target = (rng.randint(-20, 20), rng.randint(-20, 20))
        src_a = (rng.randint(-20, 20), rng.randint(-20, 20))
        src_b = (rng.randint(-20, 20), rng.randint(-20, 20))
        if src_a == target or src_b == target:
            continue
        result = choose_two_way_orientation(target, src_a, src_b)
        assert len({result["in_a"], result["in_b"], result["out"]}) == 3
