"""
fp32_boundary_v1.py -- points.md #839: the real IEEE-754 float32
boundary (UNPACK + PACK), packaged as reusable functions for the
first time.

UNPACK (extract_sign_exp / extract_mantissa) is `#697`'s own proven
mask-shift-mask-shift technique, verified bit-for-bit against real
IEEE-754 values in `tests/vm/test_unicell_super_automaton_v1.py` --
that logic lived inline in test code only, never packaged as a
callable function. It is transcribed here UNCHANGED (same addon_config
dicts, same apply_addons() calls) -- no new hardware, no new mechanism,
per the "clone, don't modify proven files" and "compose before new
hardware" discipline.

PACK is the real, previously-unbuilt mirror named as open scope in
`docs/stripped-cell/design-notes/mathtrix_mif_connection.md`: put
sign+exponent back at the top of the word (the exact reverse shift of
the extraction -- same shift_amt=20+shift_fine=3, direction flipped
from SHIFT_OUT to SHIFT_IN), and OR-combine with the already-correctly-
positioned mantissa. The OR-combine of two non-overlapping bit ranges
is exactly the mechanism `#692`-`#696` already proved correct and
zero-hop-cost at the real cell level (a gatherer cell's own offer
step) -- not re-derived here, just relied on, since sign_exp (bits
[31:23]) and mantissa (bits [22:0]) never overlap by construction.

Real, honest scope: this closes "can UNPACK and PACK round-trip
exactly," matching MIF's own real boundary-tile pair (MIF_UNPACK/
MIF_PACK). It does NOT build any arithmetic tile (ADD/MUL/etc.) --
that remains real, separate, unbuilt work, same as `#697` left it.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from unicell_super_automaton_v1 import apply_addons  # noqa: E402

_MASK32 = 0xFFFFFFFF


def extract_sign_exp(bits: int) -> int:
    """The top 9 bits (sign + 8-bit exponent), bits[31:23]. A plain
    logical right-shift by 23 (shift_amt=20 + shift_fine=3) zero-fills
    everything above the field for free -- no mask needed. Proven
    against real IEEE-754 values, #697."""
    return apply_addons(bits, {"shift_en": 1, "direction": 1, "shift_amt": 20, "shift_fine": 3})


def extract_mantissa(bits: int) -> int:
    """The low 23 bits (mantissa), bits[22:0]. A single nibble_mask
    can only cleanly reach 24 bits, which leaks bit 23 (the exponent's
    own real LSB) for any value with an odd exponent. Alan's own real
    fix, proven bit-for-bit against real IEEE-754 values (#697): mask
    to 24 bits, shift left 1 (moving the stray bit out of the 6-nibble
    window), mask to 24 bits again (now correctly dropping it), shift
    right 1 to restore the real bit positions."""
    stage1 = apply_addons(bits, {"mask_en": 1, "nibble_mask": 0b11000000,
                                  "shift_en": 1, "direction": 0, "shift_amt": 1})
    stage2 = apply_addons(stage1, {"mask_en": 1, "nibble_mask": 0b11000000,
                                    "shift_en": 1, "direction": 1, "shift_amt": 1})
    return stage2


def pack(sign_exp: int, mantissa: int) -> int:
    """The real, previously-unbuilt mirror of extract_sign_exp/
    extract_mantissa. sign_exp (bits[8:0], the value extract_sign_exp
    returns) gets shifted back to the top of the word -- the exact
    reverse of the extraction shift (same shift_amt=20+shift_fine=3,
    direction flipped from SHIFT_OUT/right to SHIFT_IN/left). mantissa
    is already at bits[22:0], its real original position, needing no
    further shift. The two fields never overlap by construction, so a
    plain OR reconstructs the word exactly -- the same non-overlapping-
    combine correctness already proven at the real cell level by
    #692-#696's lane-combine-tree work, relied on here, not re-proven."""
    sign_exp_shifted = apply_addons(sign_exp & _MASK32,
                                     {"shift_en": 1, "direction": 0, "shift_amt": 20, "shift_fine": 3})
    return (sign_exp_shifted | (mantissa & 0x7FFFFF)) & _MASK32


def unpack(bits: int):
    """Convenience: both real fields at once, as (sign_exp, mantissa)."""
    return extract_sign_exp(bits), extract_mantissa(bits)
