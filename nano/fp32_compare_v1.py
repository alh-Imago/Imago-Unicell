"""
fp32_compare_v1.py -- points.md #840: FP32 ordered comparison
(<, ==, >) on the split (sign_exp, mantissa) representation, built
entirely from `#839`'s already-proven pack() -- no new mechanism, no
barrel shifter needed, unlike ADD.

The technique: for two IEEE-754 floats, comparing their raw 32-bit
patterns as UNSIGNED integers gives the correct float ordering only
for same-sign, non-negative values -- negative-sign patterns sort
backwards (a more negative number has a numerically LARGER raw
pattern). The standard fix (also used for radix-sorting floats):
remap each pattern into one shared ordering key before comparing --
a positive value gets its sign bit forced to 1 (pushing it into the
upper half of key-space); a negative value gets EVERY bit inverted
(pushing it into the lower half, in the correct reversed order).
Plain unsigned comparison of the two keys then matches float ordering
exactly, including across the sign boundary.

Real, honest, MIF-precedent limitation, stated up front rather than
discovered later: NaN is explicitly NOT handled -- IEEE-754 defines
every comparison involving NaN as false (`a<b`, `a==b`, `a>b` all
false simultaneously), which this ordering-key scheme cannot express
(a key is always some real value, so it always compares as less,
equal, or greater than something). MIF's own old comparison tiles
carried the same simplification ("no NaN propagation"). +0.0/-0.0 ARE
handled correctly as equal here -- checked directly, not assumed --
since naive use of the key trick alone would NOT treat them as equal
(their raw patterns differ only in the sign bit, but that is exactly
the bit the trick treats as significant), and IEEE-754 requires
+0.0 == -0.0.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fp32_boundary_v1 import pack  # noqa: E402

_MASK32 = 0xFFFFFFFF


def _order_key(sign_exp: int, mantissa: int) -> int:
    """Remap a split FP32 value into a key such that plain unsigned
    integer comparison of two keys matches real float ordering."""
    bits = pack(sign_exp, mantissa)
    sign = (sign_exp >> 8) & 1   # sign_exp's own bit 8 is the real IEEE-754 sign bit
    if sign:
        return (~bits) & _MASK32
    return bits | 0x80000000


def fp32_compare(a_sign_exp: int, a_mantissa: int, b_sign_exp: int, b_mantissa: int) -> int:
    """Ordered comparison: -1 (a<b), 0 (a==b), 1 (a>b). NaN inputs give
    an unspecified (not IEEE-754-correct) result -- see module
    docstring; callers must exclude NaN themselves if it's possible."""
    a_bits = pack(a_sign_exp, a_mantissa)
    b_bits = pack(b_sign_exp, b_mantissa)
    # +0.0/-0.0: equal per IEEE-754, but the key trick alone would not
    # agree (their sign bits differ) -- handled explicitly, checked,
    # not assumed.
    if (a_bits & 0x7FFFFFFF) == 0 and (b_bits & 0x7FFFFFFF) == 0:
        return 0
    key_a = _order_key(a_sign_exp, a_mantissa)
    key_b = _order_key(b_sign_exp, b_mantissa)
    if key_a < key_b:
        return -1
    if key_a > key_b:
        return 1
    return 0


def fp32_lt(a_sign_exp, a_mantissa, b_sign_exp, b_mantissa) -> bool:
    return fp32_compare(a_sign_exp, a_mantissa, b_sign_exp, b_mantissa) < 0


def fp32_gt(a_sign_exp, a_mantissa, b_sign_exp, b_mantissa) -> bool:
    return fp32_compare(a_sign_exp, a_mantissa, b_sign_exp, b_mantissa) > 0


def fp32_eq(a_sign_exp, a_mantissa, b_sign_exp, b_mantissa) -> bool:
    return fp32_compare(a_sign_exp, a_mantissa, b_sign_exp, b_mantissa) == 0
