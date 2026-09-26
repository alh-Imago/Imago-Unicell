"""
test_fp32_mul_v1.py -- points.md #849: verifies nano/fp32_mul_v1.py's
real round-to-nearest-even multiply against Python's own correctly-
rounded float32 arithmetic.
"""
import sys
import os
import struct
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_mul_v1 import fp32_mul  # noqa: E402


def _bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _float32(f: float) -> float:
    return struct.unpack("<f", struct.pack("<f", f))[0]


def _check(a: float, b: float):
    af, bf = _float32(a), _float32(b)
    expected = _bits(af * bf)
    result = fp32_mul(_bits(af), _bits(bf))
    assert result == expected, f"{af!r}*{bf!r}: got {result:08x}, expected {expected:08x}"


def test_basic_positive_pairs_exact():
    for a, b in ((2.0, 2.0), (1.5, 1.5), (3.0, 4.0), (7.5, 2.5), (100.0, 0.01)):
        _check(a, b)


def test_sign_combinations_exact():
    for a, b in ((1.0, -1.0), (-2.5, -4.0), (-3.0, 5.0)):
        _check(a, b)


def test_zero_cases_exact():
    for a, b in ((0.0, 0.0), (0.0, 5.0), (5.0, 0.0), (-0.0, 5.0), (0.0, -5.0), (-0.0, -0.0)):
        _check(a, b)


def test_the_derivation_check_case_2x2_equals_4():
    """The specific concrete case the exponent-arithmetic derivation
    was checked against before trusting the general formula -- kept as
    an explicit regression guard, not just folded into the sweep."""
    _check(2.0, 2.0)


def test_normalize_case_where_product_needs_the_extra_shift():
    """1.5*1.5=2.25 -- the product's own top bit lands at position 47
    (needs shift=24, exponent+1), the OTHER real normalize branch from
    2.0*2.0's shift=23 case -- both real branches checked explicitly."""
    _check(1.5, 1.5)   # 1.5*1.5=2.25 -- exercises shift=24 branch
    _check(1.0, 1.0)   # 1.0*1.0=1.0 -- exercises shift=23 branch


def test_small_and_large_magnitude_exact():
    """Kept within NORMAL float32 range deliberately -- see the
    separate underflow test below for what happens outside it."""
    for a, b in ((1.1754944e-38, 2.0), (3.4028235e30, 1e-5), (1e-10, 1e-10)):
        _check(a, b)


def test_underflow_below_smallest_normal_is_an_honest_named_gap():
    """A real limitation found while writing this entry's own tests,
    not hidden: 1e-20*1e-20=1e-40 underflows below float32's smallest
    normal value (~1.18e-38) -- genuine subnormal/underflow territory,
    explicitly out of scope per this module's own "no denormals, no
    underflow handling" limitation. Documented by checking that this
    case is WRONG (not silently treated as correct), same discipline
    as #845's own cancellation-gap test."""
    a, b = 1e-20, 1e-20
    af, bf = _float32(a), _float32(b)
    expected = _bits(af * bf)
    result = fp32_mul(_bits(af), _bits(bf))
    assert result != expected, (
        "this pair is specifically chosen to demonstrate the real, "
        "named underflow gap -- if this ever starts passing, the "
        "module's own scope may have changed and its docstring should "
        "be revisited"
    )


def test_broad_random_sweep_bit_exact():
    """The real claim this entry makes: exact bit-match against
    Python's own correctly-rounded float32 multiplication, checked
    over many random pairs, both signs, wide magnitude range."""
    random.seed(4)
    checked = 0
    for _ in range(20000):
        sign_a = random.choice([1, -1])
        sign_b = random.choice([1, -1])
        a = sign_a * random.uniform(1, 1000) * (10 ** random.randint(-10, 10))
        b = sign_b * random.uniform(1, 1000) * (10 ** random.randint(-10, 10))
        af, bf = _float32(a), _float32(b)
        try:
            expected = _bits(af * bf)
        except OverflowError:
            continue   # genuine float32 overflow -- honestly out of scope
        result = fp32_mul(_bits(af), _bits(bf))
        assert result == expected, f"{af!r}*{bf!r}: got {result:08x}, expected {expected:08x}"
        checked += 1
    assert checked > 15000, "sanity: most random pairs should have been real, checkable cases"
