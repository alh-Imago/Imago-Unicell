"""
test_fp32_add_v1.py -- points.md #847: verifies nano/fp32_add_v1.py's
real round-to-nearest-even addition against Python's own correctly-
rounded float32 arithmetic. The bar changed from #844/#845's "within 1
ULP" to real, bit-exact match everywhere -- that's the whole point of
building real guard/sticky rounding.
"""
import sys
import os
import struct
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_add_v1 import fp32_add, restore_implicit_one, strip_implicit_one  # noqa: E402


def _bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _float32(f: float) -> float:
    return struct.unpack("<f", struct.pack("<f", f))[0]


def _check(a: float, b: float):
    af, bf = _float32(a), _float32(b)
    expected = _bits(af + bf)
    result = fp32_add(_bits(af), _bits(bf))
    assert result == expected, f"{af!r}+{bf!r}: got {result:08x}, expected {expected:08x}"


def test_same_exponent_pairs_exact():
    for a, b in ((1.0, 1.0), (2.0, 2.0), (1.5, 1.5), (3.0, 3.0), (0.5, 0.5),
                 (100.0, 100.0), (7.5, 7.5), (1024.0, 1024.0), (1.25, 1.75)):
        _check(a, b)


def test_differing_exponent_same_sign_exact():
    for a, b in ((1.0, 0.001), (100000.0, 1.0), (16777216.0, 1.0), (3.0, 4.0),
                 (1.0, 0.1), (1000000.0, 0.5), (2.5, 0.0001), (500.0, 3.25)):
        _check(a, b)


def test_negative_same_sign_pairs_exact():
    for a, b in ((-1.0, -1.0), (-2.5, -2.5), (-100.0, -1.0)):
        _check(a, b)


def test_overflow_normalize_path_exact():
    _check(1.5, 1.5)
    _check(8388608.0, 8388608.0)


def test_opposite_sign_same_exponent_exact():
    for a, b in ((1.5, -1.0), (3.0, -2.0), (7.5, -6.5), (100.0, -75.0), (1.0, -1.0)):
        _check(a, b)


def test_exact_cancellation_gives_positive_zero():
    for v in (1.0, 100.0, 0.001, 3.14159):
        result = fp32_add(_bits(v), _bits(-v))
        assert result == _bits(0.0)


def test_zero_and_signed_zero_cases_exact():
    """A real bug found and fixed while building this entry: 0.0+0.0
    gave the wrong answer (restore_implicit_one wrongly added the
    implicit 1 to true zero) before this fix -- checked directly here
    as a real regression guard, not just an abstract edge case."""
    for a, b in ((0.0, 0.0), (-0.0, -0.0), (0.0, -0.0), (0.0, 5.0),
                 (5.0, 0.0), (0.0, -5.0), (-0.0, 5.0)):
        _check(a, b)


def test_845s_own_measured_cancellation_gap_is_now_exact():
    """The exact pair #845 found with an 8192-ULP error under plain
    truncation -- the real reason this entry (#847) exists. Checked
    directly rather than just trusting the broad sweep below to cover
    this one specific, previously-known-bad case."""
    _check(0.5000320138008947, -0.49998339250387785)


def test_a_second_real_bug_found_during_development_is_now_exact():
    """A second real pair found by broad random sweeping while
    developing this entry (a first, incomplete fix handled guard's
    contribution to borrowing but not sticky's) -- kept as an explicit
    regression guard, not just folded silently into the sweep below."""
    _check(0.013522987986828884, -11880.078496739)


def test_broad_random_sweep_bit_exact():
    """The real claim this entry makes: EXACT bit-match against
    Python's own correctly-rounded float32 addition, not just bounded
    to 1 ULP -- checked over many random pairs, both signs, wide
    magnitude range, not just the hand-picked cases above."""
    random.seed(1)
    checked = 0
    for _ in range(20000):
        a = random.uniform(1, 1000) * (10 ** random.randint(-10, 10))
        sign_b = random.choice([1, -1])
        b = sign_b * random.uniform(1, 1000) * (10 ** random.randint(-10, 10))
        af, bf = _float32(a), _float32(b)
        try:
            expected = _bits(af + bf)
        except OverflowError:
            continue   # genuine float32 overflow -- honestly out of scope, not this module's claim
        result = fp32_add(_bits(af), _bits(bf))
        assert result == expected, f"{af!r}+{bf!r}: got {result:08x}, expected {expected:08x}"
        checked += 1
    assert checked > 15000, "sanity: most random pairs should have been real, checkable cases"


def test_restore_and_strip_implicit_one_round_trip():
    for mantissa in (0x000000, 0x400000, 0x7FFFFF, 0x123456):
        sig = restore_implicit_one(exponent=127, mantissa=mantissa)
        assert sig & (1 << 23)
        assert strip_implicit_one(sig) == mantissa


def test_restore_implicit_one_handles_true_zero():
    assert restore_implicit_one(exponent=0, mantissa=0) == 0
