"""tools/fp_add_tight_v1.py -- the floating-point ADDER, TIGHTLY placed (the same treatment as the comparator #1012 and the multiplier #1013-#1016).

The arithmetic is the loose adder's (fp_add_v1: two align blocks, each operand shifted by the amount it is SMALLER by, add / subtract with the sticky as a third extra bit, clamped normalise,
round, pack) and the results are bit-for-bit the same; only the geometry differs.  The loose adder is ~90% pure relays (distance lanes: the two packed sign+exponent words alone ran 182 squares each).
What is done here:
  * FRONT: both operands' unpack, the exponent difference and the two shift amounts, the sign logic and eBig + 1 are ONE small netlist, hand-drawn operand blocks (the multiplier's) with the rest annealed
    (tightplace_v1);  the exponent and the signs are computed where the operands already are, so no packed sign+exponent word travels to the far end.
  * COMBINE: the two aligned operands meet in a small netlist at the east end of the align bands (add / subtract, sign, magnitude).
  * the flags that are only needed at the very end (the sign of operand a and the zero-sign flag) ride in ONE word.
  * the blocks that are already straight assembly lines (align, normalise, round) are reused and laid in a U: the front and the two align bands run east on top, normalise / round / the pack run WEST underneath,
    so the pack ends up beside the front.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402
import fp_mul_tight_v1 as fmt1  # noqa: E402
import netplace_v1 as npl  # noqa: E402
import tightplace_v1 as tp  # noqa: E402

shl, shr = fadd.shl, fadd.shr
M32 = 0xFFFFFFFF


def _operand(n, t, fmt, specials=False):
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    wlow = fmt.Ka + 3
    INF = ((1 << E) - 1) << m
    P = lambda s: f"{t}.{s}"
    n.op(P("X"), "relay", [])                                                # the entry: the raw word
    n.op(P("SG"), "relay", [P("X")], addon=shr(m + E))                       # sign, 0 / 1
    n.op(P("ML"), "relay", [P("X")], addon=shl(W - m - E))                   # the sign dropped, the exponent at the top
    n.op(P("FL"), "relay", [P("ML")], addon=shl(E))                          # the fraction at the top
    n.op(P("F"), "relay", [P("FL")], addon=shr(W - m - wlow))                # ... down to bit wlow
    n.op(P("EV"), "relay", [P("ML")], addon=shr(W - E))                      # the exponent field
    n.op(P("CH"), "cmp", [P("EV")], thr=1)                                    # hidden bit = [e >= 1]
    n.op(P("HD"), "relay", [P("CH")], addon=shl(wlow + m))
    n.op(P("Hx"), "relay", [P("HD")])
    n.op(P("SIG"), "add", [P("F"), P("Hx")])                                  # the significand with its hidden bit, bit wlow..
    n.op(P("K1a"), "const", const=1)
    n.op(P("NC"), "sub", [P("K1a"), P("CH")])
    n.op(P("EE"), "add", [P("EV"), P("NC")])                                  # the effective exponent max(e, 1)
    if specials:
        n.op(P("MG"), "relay", [P("ML")], addon=shr(W - m - E))              # the magnitude
        n.op(P("C"), "cmp", [P("MG")], thr=INF)                               # inf or nan
        n.op(P("N"), "cmp", [P("MG")], thr=INF + 1)                           # nan


def build_front(fmt, rounding="rne", specials=False):
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    n = npl.Net()
    n.mask = (1 << W) - 1
    _operand(n, "A", fmt, specials)
    _operand(n, "B", fmt, specials)
    # the exponent difference diff = eb - ea (B's effective exponent must arrive FIRST: it is the minuend), dA = diff * [diff >= 0], dB = (-diff) * [-diff >= 1]
    n.op("EAd", "relay", ["A.EE"])                                           # one relay later than B.EE
    n.op("SUBD", "sub", ["B.EE", "EAd"])
    n.op("DF", "relay", ["SUBD"])
    n.op("CMPC", "cmp", ["DF"], thr=0)
    n.op("RC", "relay", ["CMPC"])
    n.op("MULA", "mul", ["DF", "RC"])
    n.op("DA", "relay", ["MULA"])
    n.op("K0", "const", const=0)
    n.op("NEG", "sub", ["K0", "DF"])
    n.op("ND", "relay", ["NEG"])
    n.op("CMPN", "cmp", ["ND"], thr=1)
    n.op("RN", "relay", ["CMPN"])
    n.op("MULB", "mul", ["ND", "RN"])
    n.op("DB", "relay", ["MULB"])
    # EXPIN = eBig + 1 = ea + dA + 1
    n.op("EBG", "add", ["EAd", "DA"])
    n.op("K1e", "const", const=1)
    n.op("EXPIN", "add", ["EBG", "K1e"])
    # the signs: XS = sa + sb;  sgn = 1 - 2 * ((sa + sb) mod 2);  zs = sa AND sb (round down: sa OR sb)
    n.op("SBd", "relay", ["B.SG"])
    n.op("XS", "add", ["A.SG", "SBd"])
    n.op("SH", "relay", ["XS"], addon=shl(W - 1))
    n.op("SX2", "relay", ["SH"], addon=shr(W - 2))                            # 2 * (sa xor sb)
    n.op("K1s", "const", const=1)
    n.op("SGN", "sub", ["K1s", "SX2"])
    n.op("ZS", "cmp", ["XS"], thr=1 if rounding == "rdn" else 2)
    n.op("ZSH", "relay", ["ZS"], addon=shl(1))
    n.op("PKW", "add", ["A.SG", "ZSH"])                                       # the flags for the pack, ONE word: sa + 2 * zs
    return n


# the operand block, drawn: local (row, col) of each op (A on top; B is its mirror image)
A_LOCAL = {"EE": (0, 2), "NC": (0, 3), "K1a": (0, 4), "SG": (1, 1), "EV": (1, 2), "CH": (1, 3), "HD": (1, 4), "Hx": (1, 5),
           "X": (2, 1), "ML": (2, 2), "FL": (2, 3), "F": (2, 4), "SIG": (2, 5), "MG": (3, 2), "N": (3, 3), "C": (4, 2)}


def operand_fixed(top=2, flip=15, specials=False):
    fx = {}
    for k, (r, c) in A_LOCAL.items():
        if k in ("MG", "N", "C") and not specials:
            continue
        fx["A." + k] = (top + r, c)
        fx["B." + k] = (flip - (top + r), c)
    fx["EAd"] = (top - 1, 2)                         # the spacer beside A's effective exponent (its one output lane forks here)
    return fx
