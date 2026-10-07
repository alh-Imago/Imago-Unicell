"""tools/fp_compare_tight_v1.py -- ledger #1012: the comparator, TIGHTLY placed (Alan: "start simple, say the comparator system ... divide and conquer").
The same arithmetic as fp_compare_v1 (key = magnitude x (1 - 2 sign); r = [d>=1] + [d>=0] - 1; nan -> 2), but laid out by hand as TWO SHORT PATHS per operand that meet at one pair of cells:
  magnitude path:  X -> shift left -> shift right (the sign bit gone) -> * key sign
  sign / flag path: X -> sign -> x2 -> (1 - x2) -> the key sign;  the magnitude also feeds the nan test
and the two operands meet in one subtract / add, then a short tail of compare and add cells. Every connection is a direct neighbour link where the geometry allows, else a routed relay lane."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402

shl, shr = fadd.shl, fadd.shr


def fp_compare_tight(g, fmt, name="CMP", r0=1, c0=0):
    E, m, W = fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    INF = ((1 << E) - 1) << m
    P = lambda s: f"{name}.{s}"
    consts = {}
    cells = {}

    def put(key, r, c, core="ram", cfg=None, addon=None, pre=None):
        g.add(P(key), r0 + r, c0 + c, core, cfg, addon, pre)
        cells[key] = P(key)
        return P(key)

    def const(key, r, c, v):
        put(key, r, c, pre=v)
        consts[P(key)] = v

    def operand(t, flip):
        R = (lambda r: 9 - r) if flip else (lambda r: r)
        put(t + "X", R(3), 0)
        put(t + "ML", R(2), 0, addon=shl(W - m - E))
        put(t + "MG", R(2), 1, addon=shr(W - m - E))
        put(t + "N", R(1), 1, "comparator", {"threshold": INF + 1})
        put(t + "M1", R(2), 2)                                           # the magnitude walks round the key sign's constant to the key's north face
        put(t + "M2", R(2), 3)
        put(t + "M3", R(3), 3)
        put(t + "KY", R(4), 3, "mul")
        put(t + "SG", R(4), 0, addon=shr(m + E))
        put(t + "S2", R(4), 1, addon=shl(1))
        put(t + "NS", R(4), 2, "adder", {"subtract_mode": 1})
        const(t + "K1", R(3), 2, 1)
        g.minuend[P(t + "NS")] = P(t + "K1")
        for a, b in (("X", "ML"), ("X", "SG"), ("ML", "MG"), ("MG", "N"), ("MG", "M1"), ("M1", "M2"), ("M2", "M3"), ("M3", "KY"),
                     ("SG", "S2"), ("S2", "NS"), ("K1", "NS"), ("NS", "KY")):
            g.link(P(t + a), P(t + b))
    operand("A", False)
    operand("B", True)
    # the meeting: DF = key_a + (0 - key_b); KY_A (4,3) and KY_B (5,3) are neighbours, DF east of KY_A, NKB east of KY_B
    put("DF", 4, 4, "adder")
    put("NKB", 5, 4, "adder", {"subtract_mode": 1})
    const("K0a", 6, 4, 0)
    g.minuend[P("NKB")] = P("K0a")
    for a, b in (("AKY", "DF"), ("BKY", "NKB"), ("K0a", "NKB"), ("NKB", "DF")):
        g.link(P(a), P(b))
    # the tail: r = [d>=1] + [d>=0] - 1 ; then the nan override
    put("C1", 4, 5, "comparator", {"threshold": 1})
    put("C0", 3, 4, "comparator", {"threshold": 0})
    put("C0a", 3, 5)                                                     # C0's flag takes two relays longer than C1's, so the two do not arrive together
    put("C0b", 3, 6)
    put("RS", 4, 6, "adder")
    const("KM", 5, 7, (1 << W) - 1)
    put("R", 4, 7, "adder")
    for a, b in (("DF", "C1"), ("DF", "C0"), ("C0", "C0a"), ("C0a", "C0b"), ("C0b", "RS"), ("C1", "RS"), ("RS", "R"), ("KM", "R")):
        g.link(P(a), P(b))
    put("NR", 4, 8, "adder", {"subtract_mode": 1})
    const("K0b", 5, 8, 0)
    g.minuend[P("NR")] = P("K0b")
    put("D2", 4, 9, "adder")
    const("K2", 5, 9, 2)
    put("MU", 4, 10, "mul")
    put("F", 4, 11, "adder")
    put("UC", 5, 10, "comparator", {"threshold": 1})
    put("US", 5, 11, "adder")
    for a, b in (("R", "NR"), ("K0b", "NR"), ("NR", "D2"), ("K2", "D2"), ("D2", "MU"), ("MU", "F"), ("UC", "MU"), ("US", "UC")):
        g.link(P(a), P(b))
    g.route(P("R"), P("F"), cross=True)
    g.route(P("AN"), P("US"), cross=True)
    g.route(P("BN"), P("US"), cross=True)
    return {"a": P("AX"), "b": P("BX")}, {"R": P("F")}, consts
