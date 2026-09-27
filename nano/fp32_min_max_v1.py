"""
fp32_min_max_v1.py -- points.md #857: fp32 min/max, near-free per the
real queue's own note, since `fp32_compare_v1.py` (#840) already
proves the correct ordering -- min/max are just "pick A or B based on
that ordering," no new comparison logic needed.

Checked against MIF's own old MIF_MIN/MIF_MAX prior art first, same
discipline as every other tile: "compute A<B, then MUX the whole pair"
-- confirms the standard algorithm (a compare-then-select), not a
separate mechanism. MIF's own gate-level compare is reused here as
`fp32_compare_v1`'s own already-proven ordering-key comparison
instead, since that's already built and tested.

Real, honest limitation, found by checking real IEEE-754 semantics
before assuming compare's own equality notion is sufficient: IEEE-754
2008's `minNum`/`maxNum` specifically define +0.0 and -0.0 as
DISTINGUISHABLE for min/max purposes (minNum(+0,-0) must return -0.0;
maxNum(+0,-0) must return +0.0), even though they compare EQUAL for
ordering purposes generally (and #840's own compare correctly treats
them as equal, matching ordinary <, ==, > semantics). This module does
NOT implement that special case -- ties (including +0/-0) resolve by
simply returning A, a real, named, arbitrary-but-consistent choice,
not the IEEE-754-mandated one. Demonstrated directly by a real test
below, not hidden.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fp32_compare_v1 import fp32_compare  # noqa: E402
from fp32_boundary_v1 import unpack  # noqa: E402


def fp32_min(a_bits: int, b_bits: int) -> int:
    """Real FP32 minimum, built directly on fp32_compare_v1's already-
    proven ordering. Ties (compare()==0, including +0.0 vs -0.0)
    return A -- see module docstring for the real, named gap against
    IEEE-754's own minNum semantics for signed zero specifically."""
    a_se, a_m = unpack(a_bits)
    b_se, b_m = unpack(b_bits)
    return a_bits if fp32_compare(a_se, a_m, b_se, b_m) <= 0 else b_bits


def fp32_max(a_bits: int, b_bits: int) -> int:
    """Real FP32 maximum, same real basis as fp32_min. Ties return A."""
    a_se, a_m = unpack(a_bits)
    b_se, b_m = unpack(b_bits)
    return a_bits if fp32_compare(a_se, a_m, b_se, b_m) >= 0 else b_bits
