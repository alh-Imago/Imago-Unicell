"""
test_fp32_add_v1.py -- points.md #844: verifies nano/fp32_add_v1.py's
same-sign addition against real Python float32 arithmetic.

Real, honest test structure, matching the module's own named
limitation: fp32_add truncates rather than rounds, so it is NOT
expected to bit-match Python's real `a + b` in every case. Two real
classes of test, kept explicitly separate rather than blurred:
  - EXACT: same-exponent pairs (no alignment shift, nothing ever
    discarded) -- these MUST bit-match real float32 addition exactly.
  - ULP-BOUNDED: differing-exponent pairs where real bits get shifted
    off during alignment -- fp32_add must be within 1 ULP of the real
    rounded result, and specifically never HIGH (truncation can only
    lose magnitude, never gain it).
"""
import sys
import os
import struct
import itertools

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_add_v1 import fp32_add, OppositeSignNotSupported, restore_implicit_one, strip_implicit_one  # noqa: E402
from fp32_boundary_v1 import unpack, pack  # noqa: E402


def _bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def _float32(f: float) -> float:
    return struct.unpack("<f", struct.pack("<f", f))[0]


# Same exponent by construction -- no alignment shift, nothing ever
# discarded, must match real float32 addition exactly.
_EXACT_SAME_EXPONENT_PAIRS = (
    (1.0, 1.0), (2.0, 2.0), (1.5, 1.5), (3.0, 3.0),
    (0.5, 0.5), (100.0, 100.0), (7.5, 7.5), (1024.0, 1024.0),
    (1.25, 1.75),   # same exponent (both in [1,2)), different mantissas
)

# Differing exponents -- real bits get shifted off during alignment;
# only ULP-bounded agreement is honestly claimable here.
_ULP_BOUNDED_PAIRS = (
    (1.0, 0.001), (100000.0, 1.0), (16777216.0, 1.0), (3.0, 4.0),
    (1.0, 0.1), (1000000.0, 0.5), (2.5, 0.0001), (500.0, 3.25),
)


def test_exact_same_exponent_addition_matches_real_float32_bit_for_bit():
    for a, b in _EXACT_SAME_EXPONENT_PAIRS:
        expected = _bits(_float32(a) + _float32(b))
        result = fp32_add(_bits(a), _bits(b))
        assert result == expected, (
            f"{a!r}+{b!r}: got {result:08x}, expected {expected:08x} (exact case, should never differ)"
        )


def test_differing_exponent_addition_is_within_one_ulp_and_never_high():
    for a, b in _ULP_BOUNDED_PAIRS:
        expected = _bits(_float32(a) + _float32(b))
        result = fp32_add(_bits(a), _bits(b))
        diff = expected - result   # both non-negative operands here, so this is a valid magnitude comparison
        assert 0 <= diff <= 1, (
            f"{a!r}+{b!r}: got {result:08x}, real {expected:08x}, diff {diff} "
            f"(truncation may only be exactly 0 or 1 ULP LOW, never high, never more than 1 off)"
        )


def test_negative_same_sign_pairs_also_work():
    """The sign-preservation path, specifically -- not covered by the
    positive-only pairs above."""
    for a, b in ((-1.0, -1.0), (-2.5, -2.5), (-100.0, -1.0)):
        expected = _bits(_float32(a) + _float32(b))
        result = fp32_add(_bits(a), _bits(b))
        diff = abs(expected - result)
        assert diff <= 1, f"{a!r}+{b!r}: got {result:08x}, real {expected:08x}"
        # Real, explicit check that the SIGN bit specifically came out right,
        # not just that the magnitude was close by coincidence.
        assert (result >> 31) == 1, f"{a!r}+{b!r}: result should be negative"


def test_opposite_sign_is_explicitly_refused_not_silently_wrong():
    for a, b in ((1.0, -1.0), (-5.0, 3.0), (2.5, -0.001)):
        try:
            fp32_add(_bits(a), _bits(b))
            assert False, f"{a!r}+{b!r}: expected OppositeSignNotSupported, got a silent result"
        except OppositeSignNotSupported:
            pass


def test_overflow_normalize_path_is_real_and_correct():
    """1.5+1.5=3.0 forces a real mantissa-add carry (bit 24 set),
    exercising the normalize shift-and-increment-exponent path
    specifically, not just addition in general."""
    result = fp32_add(_bits(1.5), _bits(1.5))
    assert result == _bits(3.0)
    result2 = fp32_add(_bits(8388608.0), _bits(8388608.0))  # 2^23 + 2^23 = 2^24, same-exponent, exact
    assert result2 == _bits(16777216.0)


def test_restore_and_strip_implicit_one_round_trip():
    for mantissa in (0x000000, 0x400000, 0x7FFFFF, 0x123456):
        sig = restore_implicit_one(exponent=127, mantissa=mantissa)
        assert sig & (1 << 23), "restored significand must have the implicit bit set"
        assert strip_implicit_one(sig) == mantissa
