"""
fp32_div_v1.py -- points.md #851: fp32 divide, the third real
arithmetic tile on the split representation. Checked against MIF's own
old MIF_DIV prior art first (fp_tiles.py: restoring binary long
division, 24 stages, one quotient bit per stage) -- confirms the
standard algorithm, and confirms real hardware precedent tonight's
earlier conversation already covered (this is exactly the 486's own
shift-and-subtract approach, not the Pentium's faster SRT). Real,
worth noting: the old MIF_DIV tile is explicitly marked
`ieee754_compliant = False` in its own metadata -- this entry's real
round-to-nearest-even surpasses it, same as #847/#849 already
surpassed MIF_ADD/MIF_MUL's own "no correct rounding" scope.

Real algorithm, mirroring MIF_DIV's own real stage order:
  sign   = XOR(a_sign, b_sign)
  exp    = a_exp - b_exp + 127 (real, biased-exponent arithmetic --
           the exact mirror of MUL's own add-then-rebias, this time
           subtract-then-rebias)
  mant   = a_sig / b_sig

Genuinely simpler than the 24-stage bit-by-bit hardware algorithm for
this VM-level correctness proof: both a_sig and b_sig are in
[2^23, 2^24), so a_sig/b_sig is a real value in (0.5, 2) -- the prior
art's own real, correct observation that AT MOST one bit of
normalizing left-shift is ever needed (never a generic multi-bit
renormalize the way opposite-sign ADD's cancellation needed). Using
Python's own exact integer division at generous extra width (the same
_EXTRA=32 convention as ADD/MUL) gives the quotient and remainder
exactly; the remainder folds directly into the sticky flag (a nonzero
division remainder means the true result isn't exactly representable,
same real meaning sticky already carries in ADD/MUL), then the same
shared round_to_nearest_even from fp32_boundary_v1.py finishes it.

Real, honest scope, same family as ADD/MUL: no denormal/subnormal
input handling, no overflow/underflow handling. Divide-by-zero is
explicitly REFUSED (a real, named exception), not silently producing
a wrong answer or attempting infinity -- genuinely undefined/infinite
results are separate, unbuilt work, matching #844's own precedent for
refusing opposite-sign addition before that mechanism existed.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fp32_boundary_v1 import unpack, pack, restore_implicit_one, strip_implicit_one, round_to_nearest_even  # noqa: E402

_WIDE = 32   # generous headroom; same convention as ADD/MUL's _EXTRA


class DivisionByZeroNotSupported(NotImplementedError):
    """Real, honest refusal -- not a silent wrong answer. Division by
    zero produces +/-infinity or NaN in real IEEE-754, genuinely
    separate, unbuilt work (this module family has no infinity/NaN
    representation to produce), same precedent as #844's own
    OppositeSignNotSupported before that mechanism existed."""


def fp32_div(a_bits: int, b_bits: int) -> int:
    """Real FP32 divide (a / b) with real round-to-nearest-even, using
    the same shared, tested rounding machinery #847/#849 already
    settled on for ADD and MUL."""
    a_se, a_m = unpack(a_bits)
    b_se, b_m = unpack(b_bits)
    a_sign, a_exp = (a_se >> 8) & 1, a_se & 0xFF
    b_sign, b_exp = (b_se >> 8) & 1, b_se & 0xFF
    out_sign = a_sign ^ b_sign

    if b_exp == 0 and b_m == 0:
        raise DivisionByZeroNotSupported(
            "fp32_div_v1 does not support division by zero -- real "
            "IEEE-754 result would be +/-infinity or NaN, neither "
            "representable in this module family yet (see docstring)."
        )
    if a_exp == 0 and a_m == 0:
        return pack(out_sign << 8, 0)   # 0/x -> correctly signed zero

    a_sig = restore_implicit_one(a_exp, a_m)
    b_sig = restore_implicit_one(b_exp, b_m)

    wide_dividend = a_sig << _WIDE
    q = wide_dividend // b_sig
    r = wide_dividend % b_sig

    out_exp = a_exp - b_exp + 127

    # Real, correct-by-construction normalize: a_sig/b_sig is always in
    # (0.5, 2) since both operands are in [2^23, 2^24) -- at most ONE
    # bit of left-shift is ever needed, never a generic renormalize.
    # Checked directly against two concrete cases (4.0/2.0=2.0 landing
    # in the no-shift branch; 3.0/4.0=0.75 ALSO landing in the
    # no-shift branch, less obvious than it first looks) before
    # trusting the general check.
    if not (q & (1 << _WIDE)):
        q <<= 1
        out_exp -= 1

    out_shift = _WIDE - 23
    out_sig = q >> out_shift
    guard = (q >> (out_shift - 1)) & 1
    below_mask = (1 << (out_shift - 1)) - 1
    # The real division remainder folds directly into sticky: a
    # nonzero remainder means the true quotient isn't exactly
    # representable at any finite precision, the same real meaning
    # sticky already carries for ADD/MUL's own discarded bits.
    sticky = 1 if ((q & below_mask) or r) else 0

    out_sig = round_to_nearest_even(out_sig & 0xFFFFFF, guard, sticky)
    if out_sig & (1 << 24):   # rounding itself can overflow
        out_sig >>= 1
        out_exp += 1

    out_mantissa = strip_implicit_one(out_sig & 0xFFFFFF)
    out_sign_exp = (out_sign << 8) | (out_exp & 0xFF)
    return pack(out_sign_exp, out_mantissa)
