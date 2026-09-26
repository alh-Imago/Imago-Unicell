"""
fp32_add_v1.py -- points.md #845: extends #844's same-sign-only ADD
with the opposite-sign (effective subtraction) path, using real
leading-zero-detect renormalization -- the mechanism #844 named as
separate, unbuilt work.

Real, deliberate scope split, per Alan's own direct instruction
("move to that side, we can work on precision after the split"):
build the SAME-SIGN vs OPPOSITE-SIGN structural split for real and
correctly first; proper rounding (guard/round/sticky bits, the real
mechanism IEEE-754 round-to-nearest-even needs) is explicitly
deferred, same as #844 already deferred it. This entry's own new
honest limitation, real and worth naming precisely: opposite-sign
cancellation can expose MORE than 1 ULP of error when the alignment
shift already discarded real bits before the subtraction -- catastrophic
cancellation amplifies lost precision by construction (each
renormalizing left-shift moves the error up with the result, it does
not recover it). This is the real reason "precision after the split"
is the right order to build these in: the split's own correctness
(right magnitude, right sign, right exponent) is independent of and
comes before any rounding/guard-bit refinement.

Pipeline for opposite-sign, mirroring MIF's own real stage order:
  1. Determine which operand has the larger MAGNITUDE (not which
     arrived as 'a') -- reusing the same (exponent, mantissa) ordering
     `fp32_compare_v1` already proved correct, since ignoring sign that
     ordering IS magnitude ordering.
  2. Restore both implicit 1s, align the smaller by the real exponent
     difference (same clamped-at-24 right shift as the same-sign path).
  3. Subtract (big - small_aligned) -- guaranteed non-negative by
     construction, since big's magnitude was chosen >= small's.
  4. Real, NEW normalize step this entry adds: leading-zero-detect,
     then a renormalizing LEFT shift (using Python's own `bit_length`
     as the zero-count, not yet mapped to real hardware) to restore
     bit 23, decrementing the exponent by the same amount. Exact
     cancellation (result == 0) is a real, separate case, returned as
     +0.0 directly rather than run through a shift-by-infinity.
  5. Strip the implicit 1, PACK -- both already proven.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fp32_boundary_v1 import unpack, pack  # noqa: E402


def restore_implicit_one(exponent: int, mantissa: int) -> int:
    """23-bit stored mantissa -> 24-bit significand, restoring the
    real implicit leading 1 IEEE-754 never stores for a normal number.
    Real, honest gap, named not hidden: subnormals (exponent==0) have
    NO implicit 1 by definition -- this function does not special-case
    that; callers passing a subnormal operand get a wrong significand,
    same "no denormals" simplification as MIF's own old tiles."""
    return (1 << 23) | (mantissa & 0x7FFFFF)


def strip_implicit_one(significand: int) -> int:
    """24-bit significand (bit 23 always set by construction on every
    real path below) back to a 23-bit stored mantissa."""
    return significand & 0x7FFFFF


def _add_same_sign(sign: int, a_exp: int, a_m: int, b_exp: int, b_m: int) -> int:
    """#844's own original path, unchanged -- same-sign addition can
    only ever overflow UPWARD (a carry into bit 24), never needs a
    left-shift renormalize."""
    a_sig = restore_implicit_one(a_exp, a_m)
    b_sig = restore_implicit_one(b_exp, b_m)

    if a_exp >= b_exp:
        big_sig, small_sig, out_exp = a_sig, b_sig, a_exp
        exp_diff = a_exp - b_exp
    else:
        big_sig, small_sig, out_exp = b_sig, a_sig, b_exp
        exp_diff = b_exp - a_exp
    small_sig = 0 if exp_diff >= 24 else (small_sig >> exp_diff)

    raw_sum = big_sig + small_sig
    if raw_sum & (1 << 24):
        raw_sum >>= 1
        out_exp += 1
    out_sig = raw_sum & 0xFFFFFF

    out_mantissa = strip_implicit_one(out_sig)
    out_sign_exp = (sign << 8) | (out_exp & 0xFF)
    return pack(out_sign_exp, out_mantissa)


def _add_opposite_sign(a_sign: int, a_exp: int, a_m: int, b_sign: int, b_exp: int, b_m: int) -> int:
    """The new path this entry adds: effective subtraction, with real
    leading-zero-detect renormalization. See module docstring."""
    # Real magnitude ordering: (exponent, mantissa) concatenated is
    # exactly the same ordering fp32_compare_v1 already proved correct
    # for non-negative values -- reused here, not re-derived.
    a_mag = (a_exp << 23) | a_m
    b_mag = (b_exp << 23) | b_m
    if a_mag >= b_mag:
        big_sign, big_exp, big_m = a_sign, a_exp, a_m
        small_exp, small_m = b_exp, b_m
    else:
        big_sign, big_exp, big_m = b_sign, b_exp, b_m
        small_exp, small_m = a_exp, a_m

    big_sig = restore_implicit_one(big_exp, big_m)
    small_sig = restore_implicit_one(small_exp, small_m)
    exp_diff = big_exp - small_exp
    small_sig_aligned = 0 if exp_diff >= 24 else (small_sig >> exp_diff)

    # Guaranteed non-negative: big's magnitude was chosen >= small's,
    # and alignment only ever shrinks small_sig further.
    raw_diff = big_sig - small_sig_aligned

    if raw_diff == 0:
        return pack(0, 0)   # exact cancellation -> +0.0, a real, deliberate convention choice

    # Real, new normalize step: leading-zero-detect (via bit_length,
    # not yet mapped to real hardware -- see module docstring) then a
    # renormalizing LEFT shift to restore bit 23, decrementing the
    # exponent by the same real amount. A raw_diff that already has
    # bit 23 set needs shift=0 -- this unifies with the "no
    # cancellation happened" case for free.
    highest_bit = raw_diff.bit_length() - 1
    shift = 23 - highest_bit
    out_sig = (raw_diff << shift) & 0xFFFFFF
    out_exp = big_exp - shift   # real, honest gap: can go negative on extreme cancellation -- underflow/subnormal not handled, same "no denormals" scope as #844

    out_mantissa = strip_implicit_one(out_sig)
    out_sign_exp = (big_sign << 8) | (out_exp & 0xFF)
    return pack(out_sign_exp, out_mantissa)


def fp32_add(a_bits: int, b_bits: int) -> int:
    """Real FP32 addition, both same-sign and opposite-sign (effective
    subtraction) cases. See module docstring for exactly what's still
    simplified (no rounding, no denormal/underflow handling)."""
    a_se, a_m = unpack(a_bits)
    b_se, b_m = unpack(b_bits)
    a_sign, a_exp = (a_se >> 8) & 1, a_se & 0xFF
    b_sign, b_exp = (b_se >> 8) & 1, b_se & 0xFF

    if a_sign == b_sign:
        return _add_same_sign(a_sign, a_exp, a_m, b_exp, b_m)
    return _add_opposite_sign(a_sign, a_exp, a_m, b_sign, b_exp, b_m)
