"""
test_fp32_div_v1.py -- points.md #851: verifies nano/fp32_div_v1.py's
real round-to-nearest-even divide against Python's own correctly-
rounded float32 arithmetic.
"""
import sys
import os
import struct
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_div_v1 import fp32_div, DivisionByZeroNotSupported  # noqa: E402


def _bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _float32(f: float) -> float:
    return struct.unpack("<f", struct.pack("<f", f))[0]


def _check(a: float, b: float):
    af, bf = _float32(a), _float32(b)
    expected = _bits(af / bf)
    result = fp32_div(_bits(af), _bits(bf))
    assert result == expected, f"{af!r}/{bf!r}: got {result:08x}, expected {expected:08x}"


def test_no_shift_normalize_branch_exact():
    """Both 4.0/2.0 and, less obviously, 3.0/4.0 land in the SAME
    real normalize branch (checked directly during development,
    kept as an explicit regression guard rather than just trusting
    the derivation)."""
    _check(4.0, 2.0)
    _check(3.0, 4.0)


def test_shift_needed_normalize_branch_exact():
    for a, b in ((1.0, 1.5), (1.0, 3.0)):
        _check(a, b)


def test_sign_combinations_exact():
    for a, b in ((-6.0, 3.0), (1.0, -4.0), (-2.0, -4.0), (7.5, 2.5)):
        _check(a, b)


def test_zero_dividend_exact():
    for a, b in ((0.0, 5.0), (-0.0, 5.0), (0.0, -5.0), (-0.0, -5.0)):
        _check(a, b)


def test_division_by_zero_is_explicitly_refused_not_silently_wrong():
    for a in (1.0, -5.0, 0.0):
        for b in (0.0, -0.0):
            try:
                fp32_div(_bits(a), _bits(b))
                assert False, f"{a!r}/{b!r}: expected DivisionByZeroNotSupported"
            except DivisionByZeroNotSupported:
                pass


def test_underflow_below_smallest_normal_is_an_honest_named_gap():
    """Same real, honest limitation as #849's own multiply entry:
    1e-20/1e20=1e-40 underflows below float32's smallest normal value,
    explicitly out of scope. Documented directly, not hidden."""
    a, b = 1e-20, 1e20
    af, bf = _float32(a), _float32(b)
    expected = _bits(af / bf)
    result = fp32_div(_bits(af), _bits(bf))
    assert result != expected, (
        "this pair is specifically chosen to demonstrate the real, "
        "named underflow gap -- if this ever starts passing, the "
        "module's own scope may have changed"
    )


def test_remainder_specific_sticky_contribution():
    """A real, found-not-guessed pair where the quotient's own low
    bits (below the guard position) are all zero, but the actual
    division remainder is nonzero -- the ONE case that specifically
    isolates whether the remainder genuinely feeds into sticky.
    Found by direct search after a mutation check showed a first
    version of this test suite never happened to exercise this path
    (500 random pairs, 0 caught an "ignore remainder" mutation) --
    fixed by finding a real case instead of loosening the mutation
    check."""
    _check(1.0233038663864136, 1.4737268686294556)


def test_broad_random_sweep_bit_exact():
    """The real claim this entry makes: exact bit-match against
    Python's own correctly-rounded float32 division, over many random
    pairs, both signs, wide magnitude range."""
    random.seed(6)
    checked = 0
    for _ in range(20000):
        sign_a = random.choice([1, -1])
        sign_b = random.choice([1, -1])
        a = sign_a * random.uniform(1, 1000) * (10 ** random.randint(-10, 10))
        b = sign_b * random.uniform(1, 1000) * (10 ** random.randint(-10, 10))
        af, bf = _float32(a), _float32(b)
        if bf == 0.0:
            continue
        try:
            expected = _bits(af / bf)
        except OverflowError:
            continue
        result = fp32_div(_bits(af), _bits(bf))
        assert result == expected, f"{af!r}/{bf!r}: got {result:08x}, expected {expected:08x}"
        checked += 1
    assert checked > 15000, "sanity: most random pairs should have been real, checkable cases"
