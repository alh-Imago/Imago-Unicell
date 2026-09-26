"""
fp32_add_v1.py -- points.md #844: the first real arithmetic tile on
the split representation, closing the piece #839's own scope note
named as remaining ("does NOT build any arithmetic tile").

Real, honest, MIF-precedent scope decision, made explicitly rather
than discovered as a bug later: SAME-SIGN addition only. MIF's own
real prior art (`fp_tiles.py`) treats same-sign and opposite-sign
mantissa combination as genuinely different problems -- "if same
sign: add mantissas; if different sign: subtract" -- and subtraction
needs a real, separate mechanism this entry does not build: leading-
zero detection and a renormalizing LEFT shift for cancellation (e.g.
1.5 - 1.4 produces a small result that needs re-normalizing upward,
not the overflow-driven single-bit RIGHT shift same-sign addition
needs). Attempting both in one pass would conflate two different
normalize mechanisms; same-sign addition alone is still a real,
complete, independently useful tile.

Also real and explicit: NO ROUNDING. The result is truncated, not
rounded to nearest-even the way IEEE-754 requires. This means results
will NOT always bit-match Python's own `a + b` on real float32 values
-- they will be correct or exactly 1 ULP low, never high, whenever a
non-zero bit gets shifted off during alignment. Same simplification
MIF's own old tiles made ("no denormals, no NaN propagation"): a real,
named limitation, not a hidden bug.

Pipeline, mirroring MIF's own real stage order:
  1. UNPACK both operands (`fp32_boundary_v1`, already proven)
  2. Restore each operand's implicit leading 1 -> 24-bit significand
  3. Compare exponents, align the smaller significand by the real
     difference (a right shift -- the same operation `#840` found has
     no live-reconfigure-free mechanism on real hardware yet; this
     module models the ARITHMETIC only, not the substrate mapping)
  4. Add the two 24-bit significands -> a 25-bit sum (24 bits + carry)
  5. Normalize: if bit 24 (the carry) is set, shift right 1 and
     increment the exponent by 1 -- the SAME overflow-driven shift
     `#843`'s own design-note conditional-shifter and branch-and-pad
     ideas exist to eventually implement on real hardware
  6. Strip the implicit leading 1 back to a 23-bit stored mantissa
  7. PACK the result (`fp32_boundary_v1`, already proven)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fp32_boundary_v1 import unpack, pack  # noqa: E402


class OppositeSignNotSupported(NotImplementedError):
    """Real, honest, explicit refusal -- not a silent wrong answer.
    Effective subtraction (opposite-sign addition) needs leading-zero
    detection and a renormalizing left shift, a genuinely separate
    mechanism this entry does not build. See module docstring."""


def restore_implicit_one(exponent: int, mantissa: int) -> int:
    """23-bit stored mantissa -> 24-bit significand, restoring the
    real implicit leading 1 IEEE-754 never stores for a normal number.
    Real, honest gap, named not hidden: subnormals (exponent==0) have
    NO implicit 1 by definition -- this function does not special-case
    that; callers passing a subnormal operand get a wrong significand,
    same "no denormals" simplification as MIF's own old tiles."""
    return (1 << 23) | (mantissa & 0x7FFFFF)


def strip_implicit_one(significand: int) -> int:
    """24-bit significand (bit 23 always set, guaranteed by
    construction for the same-sign-add path -- see fp32_add's own
    normalize step) back to a 23-bit stored mantissa."""
    return significand & 0x7FFFFF


def fp32_add(a_bits: int, b_bits: int) -> int:
    """Same-sign FP32 addition only -- raises OppositeSignNotSupported
    otherwise. See module docstring for the real, honest scope."""
    a_se, a_m = unpack(a_bits)
    b_se, b_m = unpack(b_bits)
    a_sign, a_exp = (a_se >> 8) & 1, a_se & 0xFF
    b_sign, b_exp = (b_se >> 8) & 1, b_se & 0xFF

    if a_sign != b_sign:
        raise OppositeSignNotSupported(
            "fp32_add_v1 only supports same-sign addition; effective "
            "subtraction needs leading-zero-detect renormalization, "
            "not yet built (see module docstring)."
        )

    a_sig = restore_implicit_one(a_exp, a_m)
    b_sig = restore_implicit_one(b_exp, b_m)

    # Real align stage: the larger exponent's operand stays put; the
    # smaller is shifted right by the real difference. Clamped at 24 --
    # a shift of 24+ discards the whole 24-bit significand, matching
    # real hardware behaviour rather than Python's own unbounded shift.
    if a_exp >= b_exp:
        big_sig, small_sig, out_exp = a_sig, b_sig, a_exp
        exp_diff = a_exp - b_exp
    else:
        big_sig, small_sig, out_exp = b_sig, a_sig, b_exp
        exp_diff = b_exp - a_exp
    small_sig = 0 if exp_diff >= 24 else (small_sig >> exp_diff)

    # Real add stage: 24-bit + 24-bit -> up to 25 bits (a real carry).
    raw_sum = big_sig + small_sig

    # Real normalize stage: same-sign addition can only ever overflow
    # UPWARD (carry into bit 24), never need a left-shift renormalize --
    # that asymmetry is exactly why the opposite-sign case is refused
    # above rather than half-handled.
    if raw_sum & (1 << 24):
        raw_sum >>= 1
        out_exp += 1
    out_sig = raw_sum & 0xFFFFFF

    out_mantissa = strip_implicit_one(out_sig)
    out_sign_exp = (a_sign << 8) | (out_exp & 0xFF)
    return pack(out_sign_exp, out_mantissa)
