"""
fp32_mul_v1.py -- points.md #849: fp32 multiply, the second real
arithmetic tile on the split representation, checked against MIF's own
old MIF_MUL prior art before building (fp_tiles.py: "sign_r =
XOR(a_sign,b_sign); exp_r = a_exp+b_exp-127; mant_r = a_sig*b_sig")
-- confirming the real, standard algorithm, not re-derived from
scratch.

Genuinely simpler than ADD (#844/#845/#847): no alignment shift, no
cancellation, no leading-zero-detect renormalize. The two REAL
mechanisms multiply needs instead:

  1. EXPONENT: the two BIASED exponents simply add (each carries the
     +127 bias once, so the sum carries it twice -- subtract 127 once
     to correct). Verified by direct derivation, not just copied from
     MIF: for a_sig, b_sig in [2^23, 2^24) representing normalized
     values in [1,2), the product lands in [2^46, 2^48) -- a single
     real normalize check (does the product's own top bit land at
     position 46 or 47) decides whether the exponent needs one more
     +1 beyond the base a_exp+b_exp-127.

  2. MANTISSA: a real 24x24 -> up to 48-bit multiply (exact, no
     precision lost in the multiply itself -- unlike ADD's alignment
     shift, nothing is discarded until the final rounding step). The
     top 24 bits become the result significand; the low 23 or 24 bits
     (depending on which normalize case fired) are guard+sticky for
     real round-to-nearest-even, using the exact same shared machinery
     ADD's own #847 rewrite settled on after two real, caught mistakes
     -- built in from the start here, not bolted on after a truncation
     bug was found the hard way this time.

Real, honest scope, same as every entry in this module family: no
denormal/subnormal input handling, no overflow/underflow handling
(exponent can exceed the real 8-bit range on extreme inputs,
unhandled), true zero (exponent==0, mantissa==0) handled explicitly
via the same fix #847 already made to restore_implicit_one.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fp32_boundary_v1 import unpack, pack, restore_implicit_one, strip_implicit_one, round_to_nearest_even  # noqa: E402


def fp32_mul(a_bits: int, b_bits: int) -> int:
    """Real FP32 multiply with real round-to-nearest-even, built in
    from the start using the same shared, tested rounding machinery
    #847 settled on for ADD."""
    a_se, a_m = unpack(a_bits)
    b_se, b_m = unpack(b_bits)
    a_sign, a_exp = (a_se >> 8) & 1, a_se & 0xFF
    b_sign, b_exp = (b_se >> 8) & 1, b_se & 0xFF
    out_sign = a_sign ^ b_sign

    # Real, explicit zero handling -- checked directly (same lesson
    # #847 learned the hard way for ADD): a true-zero operand makes
    # the whole product zero, with the correctly XORed sign, regardless
    # of the other operand's value.
    if (a_exp == 0 and a_m == 0) or (b_exp == 0 and b_m == 0):
        return pack(out_sign << 8, 0)

    a_sig = restore_implicit_one(a_exp, a_m)
    b_sig = restore_implicit_one(b_exp, b_m)
    product = a_sig * b_sig   # exact; up to 48 bits, both factors 24-bit

    exp_sum = a_exp + b_exp - 127

    # Real normalize check: does the product's own leading bit land at
    # position 47 (needs an extra +1 on the exponent, shift by 24) or
    # 46 (shift by 23)? Derived and verified against a concrete case
    # (2.0*2.0=4.0) before trusting the general formula.
    if product & (1 << 47):
        shift = 24
        exp_sum += 1
    else:
        shift = 23

    out_sig = product >> shift
    guard = (product >> (shift - 1)) & 1
    sticky_mask = (1 << (shift - 1)) - 1
    sticky = 1 if (product & sticky_mask) else 0

    out_sig = round_to_nearest_even(out_sig, guard, sticky)
    if out_sig & (1 << 24):   # rounding itself can overflow (e.g. 0xFFFFFF + 1)
        out_sig >>= 1
        exp_sum += 1

    out_mantissa = strip_implicit_one(out_sig & 0xFFFFFF)
    out_sign_exp = (out_sign << 8) | (exp_sum & 0xFF)
    return pack(out_sign_exp, out_mantissa)
