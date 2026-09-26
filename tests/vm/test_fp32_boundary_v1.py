"""
test_fp32_boundary_v1.py -- points.md #839: verifies nano/
fp32_boundary_v1.py's new PACK direction, and the full UNPACK->PACK
round trip, bit-for-bit against real IEEE-754 values via Python's own
struct module -- same discipline as #697's own extraction tests, not
synthetic test values.
"""
import sys
import os
import struct

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from fp32_boundary_v1 import extract_sign_exp, extract_mantissa, pack, unpack  # noqa: E402

# Same real test values #697 already proved extraction against, plus
# real edge cases #697 did not cover (largest normal, smallest normal,
# a subnormal, +/-inf, nan) -- pack introduces new failure modes
# (overflow past bit 31, sign_exp/mantissa overlap) extraction alone
# could not have exposed, so these are genuinely new checks, not
# padding.
_REAL_VALUES = (
    3.14159, 1.0, -2.5, 100000.0, 0.001, -0.0, 123456.789,
    0.0, 3.4028235e38,          # largest finite normal float32
    1.1754944e-38,              # smallest positive normal float32
    1.4e-45,                    # a real subnormal (smallest positive float32)
    float("inf"), float("-inf"),
)


def _real_bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", f))[0]


def test_pack_reverses_the_sign_exp_shift_exactly():
    """pack's own sign_exp half, checked on its own before the
    combine: shifting extract_sign_exp's output back left by 23 must
    land exactly back at bits[31:23], with bits[22:0] all zero (no
    mantissa OR'd in yet)."""
    for value in _REAL_VALUES:
        bits = _real_bits(value)
        sign_exp = extract_sign_exp(bits)
        shifted_back = pack(sign_exp, 0)
        assert shifted_back == (bits & 0xFF800000), \
            f"{value!r}: got {shifted_back:08x}, expected {bits & 0xFF800000:08x}"


def test_full_unpack_pack_round_trip_matches_real_bits_exactly():
    """The real claim this entry exists to prove: split a real
    IEEE-754 word into sign_exp+mantissa, then pack it back, and get
    EXACTLY the original bit pattern -- not just a value that
    round-trips through Python float equality (which would hide a
    real bit-level bug in either direction)."""
    for value in _REAL_VALUES:
        bits = _real_bits(value)
        sign_exp, mantissa = unpack(bits)
        rebuilt = pack(sign_exp, mantissa)
        assert rebuilt == bits, \
            f"{value!r}: original {bits:08x}, rebuilt {rebuilt:08x}"


def test_round_trip_also_holds_for_nan_bit_patterns():
    """NaN doesn't survive Python equality (nan != nan), so it needs
    its own explicit bit-pattern check rather than sharing the loop
    above -- a real, separate case, not an oversight if it were left
    out."""
    bits = _real_bits(float("nan"))
    sign_exp, mantissa = unpack(bits)
    rebuilt = pack(sign_exp, mantissa)
    assert rebuilt == bits, f"nan: original {bits:08x}, rebuilt {rebuilt:08x}"


def test_sign_exp_and_mantissa_fields_never_overlap():
    """The real correctness precondition pack's plain OR depends on,
    checked directly rather than just asserted in a comment: for every
    real test value, extract_sign_exp's own result, shifted back to
    bits[31:23], and extract_mantissa's own result must share zero set
    bits -- confirming the OR-combine #692-#696 already proved correct
    for non-overlapping fields is genuinely being used within its own
    proven precondition here, not just by construction."""
    for value in _REAL_VALUES:
        bits = _real_bits(value)
        sign_exp, mantissa = unpack(bits)
        sign_exp_positioned = pack(sign_exp, 0)
        assert (sign_exp_positioned & mantissa) == 0, \
            f"{value!r}: fields overlap -- sign_exp={sign_exp_positioned:08x}, mantissa={mantissa:08x}"


def test_pack_defensively_masks_a_dirty_mantissa_argument():
    """A real gap found by mutation-checking pack() before trusting
    it: every real IEEE-754 value's own extracted mantissa is already
    clean (<=23 bits) by construction, so the round-trip tests above
    can't tell whether pack()'s own `mantissa & 0x7FFFFF` mask is
    doing anything at all -- removing it silently passed every other
    test in this file. Checked directly: a mantissa argument with
    stray bits set above bit 22 (as if a caller passed something other
    than extract_mantissa's own output) must still produce the exact
    same result as the clean mantissa alone, not a corrupted word."""
    clean_mantissa = 0x555555   # an arbitrary real 23-bit value, not all-ones
    dirty_mantissa = clean_mantissa | 0xFF800000   # every bit above 22 also set
    assert dirty_mantissa != clean_mantissa   # sanity: the two inputs really do differ
    assert pack(0x1FF, dirty_mantissa) == pack(0x1FF, clean_mantissa)


def test_pack_with_max_sign_exp_does_not_overflow_past_bit_31():
    """A real, honest boundary check pure algebra could get wrong
    silently: sign_exp is 9 bits (max 0x1FF=511), shifted left by 23.
    511 << 23 occupies bits [31:23] exactly (9 bits fit 9 positions,
    23 to 31 inclusive) -- confirmed directly, not just reasoned about,
    that this never spills into a 33rd bit that _MASK32 would need to
    truncate (which would silently corrupt the top real bit if the
    shift math were off by one anywhere in the chain)."""
    rebuilt = pack(0x1FF, 0)
    assert rebuilt == 0xFF800000
    assert rebuilt <= 0xFFFFFFFF
