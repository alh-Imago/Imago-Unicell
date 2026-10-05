"""icm_width_v1.py -- the DESIGN-LEVEL `min_bit_width` flag of an ICM file (ledger #958).

Alan's ruling: the ICM stays 32 bits wide and as OPEN and CROSS-TARGETABLE as possible; a design can DECLARE, in the file's header, the minimum bit width it needs
(`min_bit_width`), so the flag travels with the artifact. When the flag is ABSENT the width is 32 -- nothing changes for any existing file. The loader and the
save functions are where the width is dealt with; a target that is narrower than 32 (the Tang's native 18) may use a declared smaller width, and a target that can
be widened (the flex cells, and specifically the nano, to 36) is told by this flag how wide it must be.

SEMANTICS (stated precisely, because "minimum" is easy to misread): the flag is a REQUIREMENT, "this design needs AT LEAST this many bits". Building a design WIDER than
its minimum always satisfies it. So a consumer that builds only 32-bit designs correctly accepts any declared minimum up to 32, and must REFUSE a larger one (it cannot
meet it) rather than silently ignore it. The flag is a user DECLARATION, not something derivable from the data, so it is stored (the VIX header's other fields, `cores_used`
and `cell_count`, stay derived from the data every time, as before) and it is covered by the file's integrity hash when present, so a hand-edit that changes what the
design means is caught on load.
"""
DEFAULT_MIN_BIT_WIDTH = 32
LOWEST_MIN_BIT_WIDTH = 1
HIGHEST_MIN_BIT_WIDTH = 64            # the widest the assembler's WIDTH parameter allows (flexsub_assemble_v1.MAX_WIDTH)


class IcmWidthError(ValueError):
    """A malformed `min_bit_width` flag."""


def validate_min_bit_width(w):
    """None (absent) or a real int in [1, 64]. bool is rejected (True is an int in Python and would silently mean 1)."""
    if w is None:
        return None
    if isinstance(w, bool) or not isinstance(w, int):
        raise IcmWidthError(f"min_bit_width must be an integer number of bits, got {w!r} ({type(w).__name__})")
    if not (LOWEST_MIN_BIT_WIDTH <= w <= HIGHEST_MIN_BIT_WIDTH):
        raise IcmWidthError(f"min_bit_width must be between {LOWEST_MIN_BIT_WIDTH} and {HIGHEST_MIN_BIT_WIDTH} bits, got {w}")
    return w


def effective_min_bit_width(w):
    """The width the design needs: the declared one, or 32 when the flag is absent."""
    return DEFAULT_MIN_BIT_WIDTH if w is None else validate_min_bit_width(w)


def hash_suffix(w):
    """What the flag adds to an integrity hash: NOTHING when absent (so every existing file hashes exactly as before), a fixed suffix when set."""
    return "" if w is None else f"|min_bit_width={validate_min_bit_width(w)}"
