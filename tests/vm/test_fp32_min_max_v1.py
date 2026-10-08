"""
test_fp32_min_max_v1.py -- points.md #857: verifies nano/
fp32_min_max_v1.py's real min/max against Python's own min()/max()
(which share the same order-preserving tie-break this module uses),
plus a real, measured demonstration of the honest gap against strict
IEEE-754 minNum/maxNum's own order-INDEPENDENT signed-zero rule.
"""
import sys
import os
import struct
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_min_max_v1 import fp32_min, fp32_max  # noqa: E402


def _bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _float32(f: float) -> float:
    return struct.unpack("<f", struct.pack("<f", f))[0]


_REAL_PAIRS = (
    (1.0, 2.0), (2.0, 1.0), (-1.0, 1.0), (-5.0, -3.0), (3.14159, 2.71828),
    (0.0, 5.0), (-100.0, 100.0), (1e30, 1e-30), (7.0, 7.0), (-7.0, -7.0),
)


def test_min_matches_python_exactly():
    for a, b in _REAL_PAIRS:
        af, bf = _float32(a), _float32(b)
        expected = _bits(min(af, bf))
        result = fp32_min(_bits(af), _bits(bf))
        assert result == expected, f"min({af!r},{bf!r}): got {result:08x}, expected {expected:08x}"


def test_max_matches_python_exactly():
    for a, b in _REAL_PAIRS:
        af, bf = _float32(a), _float32(b)
        expected = _bits(max(af, bf))
        result = fp32_max(_bits(af), _bits(bf))
        assert result == expected, f"max({af!r},{bf!r}): got {result:08x}, expected {expected:08x}"


def test_signed_zero_tie_break_is_order_dependent_the_real_honest_gap():
    """A real, measured demonstration (not just an assertion in a
    comment) of this module's own named limitation: strict IEEE-754
    minNum/maxNum mandate minNum(x,-0)=-0 and maxNum(x,+0)=+0
    REGARDLESS of argument order -- this module's own tie-break
    (return A) is order-DEPENDENT instead, matching Python's own
    min()/max() rather than the stricter spec. Checked both orders
    explicitly to prove the dependency is real, not assumed."""
    pos_zero, neg_zero = _bits(0.0), _bits(-0.0)
    assert fp32_min(pos_zero, neg_zero) == pos_zero   # A=+0 -> returns +0
    assert fp32_min(neg_zero, pos_zero) == neg_zero   # A=-0 -> returns -0 (order flipped the result)
    assert fp32_max(pos_zero, neg_zero) == pos_zero
    assert fp32_max(neg_zero, pos_zero) == neg_zero


def test_broad_random_sweep_matches_python():
    random.seed(8)
    checked = 0
    for _ in range(20000):
        a = random.uniform(-1e10, 1e10) * (10 ** random.randint(-10, 10))
        b = random.uniform(-1e10, 1e10) * (10 ** random.randint(-10, 10))
        af, bf = _float32(a), _float32(b)
        try:
            exp_min, exp_max = _bits(min(af, bf)), _bits(max(af, bf))
        except OverflowError:
            continue
        assert fp32_min(_bits(af), _bits(bf)) == exp_min
        assert fp32_max(_bits(af), _bits(bf)) == exp_max
        checked += 1
    assert checked > 15000
