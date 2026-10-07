"""tests/vm/fp_round_ref_v1.py -- ledger #1007: an exact reference for IEEE binary addition in every rounding mode (an independent integer / Fraction implementation, any format).
`add_ref(fmt, a, b, mode)`: exact sum, ONE rounding (rne, rna, rtz, rup, rdn), subnormals, overflow (infinity or the largest finite number, by mode and sign), the sign of an exact zero
(+0, except round-down; both operands the same sign keep it), inf / nan. NaN results come back as a canonical quiet NaN. Anchored to numpy (round-to-nearest-even) and, where the C library
lets it, to numpy under fesetround (the directed modes) in test_fp_round_modes_v1.py."""
from fractions import Fraction

MODES = ("rne", "rna", "rtz", "rup", "rdn")


def decode(fmt, v):
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    s, e, f = v >> (m + E), (v >> m) & ((1 << E) - 1), v & ((1 << m) - 1)
    return s, e, f


def add_ref(fmt, a, b, mode):
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    emax = (1 << E) - 1
    bias = (1 << (E - 1)) - 1
    SG = 1 << (m + E)
    INF = emax << m
    MAXF = INF - 1
    qnan = INF | (1 << (m - 1))
    sa, ea, fa_ = decode(fmt, a)
    sb, eb, fb = decode(fmt, b)
    a_nan, b_nan = ea == emax and fa_, eb == emax and fb
    a_inf, b_inf = ea == emax and not fa_, eb == emax and not fb
    if a_nan or b_nan or (a_inf and b_inf and sa != sb):
        return qnan
    if a_inf:
        return a
    if b_inf:
        return b

    def val(s, e, f):
        mag = Fraction(f if e == 0 else f | (1 << m)) * Fraction(2) ** ((max(e, 1)) - bias - m)
        return -mag if s else mag
    exact = val(sa, ea, fa_) + val(sb, eb, fb)
    if exact == 0:
        if sa == sb:
            return SG if sa else 0
        return SG if mode == "rdn" else 0
    neg = exact < 0
    mag = -exact if neg else exact
    emin = 1 - bias
    e2 = mag.numerator.bit_length() - mag.denominator.bit_length()          # floor(log2 mag) within 1
    while Fraction(2) ** e2 > mag:
        e2 -= 1
    while Fraction(2) ** (e2 + 1) <= mag:
        e2 += 1
    unit = Fraction(2) ** (max(e2, emin) - m)
    n = mag / unit
    q, r = n.numerator // n.denominator, n - (n.numerator // n.denominator)
    if r:
        if mode == "rne":
            up = r > Fraction(1, 2) or (r == Fraction(1, 2) and q & 1)
        elif mode == "rna":
            up = r >= Fraction(1, 2)
        elif mode == "rtz":
            up = False
        elif mode == "rup":
            up = not neg
        else:
            up = neg
        q += 1 if up else 0
    rounded = q * unit
    over = rounded >= Fraction(2) ** (emax - bias)                          # past the largest finite number
    if over:
        to_inf = mode in ("rne", "rna") or (mode == "rup" and not neg) or (mode == "rdn" and neg)
        return (SG if neg else 0) | (INF if to_inf else MAXF)
    if rounded < Fraction(2) ** emin:                                       # subnormal (or the carry into the smallest normal)
        bits = int(rounded / (Fraction(2) ** (emin - m)))
    else:
        ee = rounded.numerator.bit_length() - rounded.denominator.bit_length()
        while Fraction(2) ** ee > rounded:
            ee -= 1
        while Fraction(2) ** (ee + 1) <= rounded:
            ee += 1
        bits = ((ee + bias) << m) | int((rounded / Fraction(2) ** ee - 1) * (1 << m))
    return (SG if neg else 0) | bits
