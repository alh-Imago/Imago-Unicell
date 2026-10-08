"""
test_fp32_compare_v1.py -- points.md #840: verifies nano/
fp32_compare_v1.py's ordering-key comparison against Python's own
real float comparison operators, for every pair drawn from a real,
varied value set (not synthetic edge cases invented to pass).
"""
import sys
import os
import struct
import itertools

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_boundary_v1 import unpack  # noqa: E402
from fp32_compare_v1 import fp32_compare, fp32_lt, fp32_gt, fp32_eq  # noqa: E402

_REAL_VALUES = (
    3.14159, 1.0, -2.5, 100000.0, 0.001, -0.0, 0.0, 123456.789,
    -1.0, -100000.0, -0.001, 2.5, 7.0, -7.0, 42.0, -42.0,
    3.4028235e38, -3.4028235e38, 1.1754944e-38, -1.1754944e-38,
    1.4e-45, -1.4e-45,
)


def _real_bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _split(f: float):
    return unpack(_real_bits(f))


def test_every_real_pair_matches_python_ordering():
    """The real claim this entry exists to prove: for every pair drawn
    from a varied real value set (positive/negative, large/small,
    zero/negative-zero, same value twice), fp32_compare's own -1/0/1
    result matches Python's real <, ==, > on the actual float32
    values (round-tripped through struct so both sides agree on what
    'the float32 value' even is)."""
    for a, b in itertools.product(_REAL_VALUES, repeat=2):
        # round-trip through real float32 precision first, so Python's
        # own comparison is judging the SAME value fp32_compare sees
        a32 = struct.unpack("<f", struct.pack("<f", a))[0]
        b32 = struct.unpack("<f", struct.pack("<f", b))[0]
        a_se, a_m = _split(a)
        b_se, b_m = _split(b)
        result = fp32_compare(a_se, a_m, b_se, b_m)
        if a32 < b32:
            assert result == -1, f"{a32!r} < {b32!r} expected -1, got {result}"
        elif a32 > b32:
            assert result == 1, f"{a32!r} > {b32!r} expected 1, got {result}"
        else:
            assert result == 0, f"{a32!r} == {b32!r} expected 0, got {result}"


def test_positive_zero_and_negative_zero_are_equal():
    """A real, checked-not-assumed edge case: the ordering-key trick
    alone would NOT agree these are equal (their sign bits differ) --
    confirmed this module's explicit zero special-case actually fires."""
    pos_se, pos_m = _split(0.0)
    neg_se, neg_m = _split(-0.0)
    assert fp32_eq(pos_se, pos_m, neg_se, neg_m)
    assert fp32_compare(pos_se, pos_m, neg_se, neg_m) == 0
    assert not fp32_lt(pos_se, pos_m, neg_se, neg_m)
    assert not fp32_gt(pos_se, pos_m, neg_se, neg_m)


def test_lt_gt_eq_wrappers_agree_with_compare():
    for a, b in itertools.product(_REAL_VALUES, repeat=2):
        a_se, a_m = _split(a)
        b_se, b_m = _split(b)
        c = fp32_compare(a_se, a_m, b_se, b_m)
        assert fp32_lt(a_se, a_m, b_se, b_m) == (c < 0)
        assert fp32_gt(a_se, a_m, b_se, b_m) == (c > 0)
        assert fp32_eq(a_se, a_m, b_se, b_m) == (c == 0)


def test_ordering_is_a_real_total_order_across_the_full_sorted_set():
    """A stronger, structural check than pairwise comparison alone:
    sorting the real value set by fp32_compare must produce EXACTLY
    the same order as sorting by real Python float value -- catches a
    transitivity bug a pairwise-only check could miss."""
    import functools
    split_values = [(_split(v), v) for v in _REAL_VALUES]

    def cmp(item_a, item_b):
        (a_se, a_m), _ = item_a
        (b_se, b_m), _ = item_b
        return fp32_compare(a_se, a_m, b_se, b_m)

    sorted_by_fp32 = [v for _, v in sorted(split_values, key=functools.cmp_to_key(cmp))]
    sorted_by_python = sorted(_REAL_VALUES, key=lambda f: struct.unpack("<f", struct.pack("<f", f))[0])
    assert sorted_by_fp32 == sorted_by_python
