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
    # the exits (east face): the two significands, the two shift amounts, eBig + 1, the +-1 and the flags word
    n.op("O.VA", "relay", ["A.SIG"])
    n.op("O.VB", "relay", ["B.SIG"])
    n.op("O.DA", "relay", ["DA"])
    n.op("O.DB", "relay", ["DB"])
    n.op("O.EXPIN", "relay", ["EXPIN"])
    n.op("O.SGN", "relay", ["SGN"])
    n.op("O.PKW", "relay", ["PKW"])
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


def place_front(g, fmt, name, r0, c0, rounding="rne", seed=1, iters=60000, rows=26, cols=50, pitch=3):
    n = build_front(fmt, rounding)
    fx = operand_fixed()
    pos = tp.autoplace(n, fx, rows, cols, seed=seed, iters=iters, free_rect=(0, 8, rows - 2, cols - 4), pitch=pitch)
    allpos = dict(fx)
    allpos.update(pos)
    ports = {"A.X": "W", "B.X": "W", **{o: "E" for o in n.order if o.startswith("O.")}}
    res = tp.place_map(g, name, n, [], r0, c0, extra=allpos, ports=ports)
    return n, allpos, res


def build_combine(fmt, rounding="rne"):
    """COMBINE (east end of the align bands): the two aligned operands (+ their stickies) meet, add / subtract, magnitude, and the result's sign."""
    E, m, W = fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    n = npl.Net()
    n.mask = (1 << W) - 1
    for e in ("AOUT", "ASTK", "BOUT", "BSTK", "SGNI", "PKI"):
        n.op(e, "relay", [])
    n.op("AR", "relay", ["AOUT"], addon=shl(1))
    n.op("BR", "relay", ["BOUT"], addon=shl(1))
    n.op("ADDA", "add", ["AR", "ASTK"])
    n.op("ADDB", "add", ["BR", "BSTK"])
    n.op("MULT", "mul", ["ADDB", "SGNI"])                                     # +-1 times the second operand: add / subtract
    n.op("ADDSUM", "add", ["ADDA", "MULT"])
    n.op("SF", "relay", ["ADDSUM"])
    n.op("CMPP", "cmp", ["SF"], thr=0)                                        # p = [S >= 0]
    n.op("P2", "relay", ["CMPP"], addon=shl(1))
    n.op("KM1", "const", const=(1 << W) - 1)
    n.op("SUBP", "add", ["P2", "KM1"])
    n.op("SG2", "relay", ["SUBP"])                                            # 2p - 1 = +-1
    n.op("MULM", "mul", ["SF", "SG2"])
    n.op("O.M", "relay", ["MULM"])                                            # the magnitude
    # the result's sign: sb2 = (1 - p + sa) mod 2; the flags word PKI = sa + 2 zs
    n.op("K1B", "const", const=1)
    n.op("NPS", "sub", ["K1B", "CMPP"])
    n.op("NPV", "relay", ["NPS"])
    n.op("SAH", "relay", ["PKI"], addon=shl(W - 1))
    n.op("SAV", "relay", ["SAH"], addon=shr(W - 1))
    n.op("ZSV", "relay", ["PKI"], addon=shr(1))
    n.op("SN", "add", ["NPV", "SAV"])
    n.op("SB1", "relay", ["SN"], addon=shl(W - 1))
    n.op("SB2", "relay", ["SB1"], addon=shr(W - 1))                           # the result sign, 0 / 1
    n.op("ZS2", "relay", ["ZSV"], addon=shl(1))
    n.op("SGW", "add", ["SB2", "ZS2"])
    n.op("O.SGW", "relay", ["SGW"])                                           # sign + 2 zs, one word, for the pack
    if rounding != "rne" and rounding != "rna":
        pass
    n.op("O.SGR", "relay", ["SB2"])                                           # the sign for the rounding block (directed modes)
    return n


def build_pack(fmt):
    """PACK (west end of the bottom band, beside the front): bits = ((er - 1) << m) + M + (sign << (m+E)), the zero-sign correction."""
    E, m, W = fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    n = npl.Net()
    n.mask = (1 << W) - 1
    for e in ("RO", "EXR", "SGWI"):
        n.op(e, "relay", [])
    n.op("NZC", "cmp", ["RO"], thr=1)
    n.op("NZ", "relay", ["NZC"])
    n.op("KME", "const", const=(1 << W) - 1)
    n.op("ADDR", "add", ["KME", "EXR"])
    n.op("MULE", "mul", ["ADDR", "NZ"])
    n.op("SHE", "relay", ["MULE"], addon=shl(m))
    n.op("SBH", "relay", ["SGWI"], addon=shl(W - 1))
    n.op("SBV", "relay", ["SBH"], addon=shr(W - 1))
    n.op("ZSH", "relay", ["SGWI"], addon=shr(1))
    n.op("MULSG", "mul", ["SBV", "NZ"])
    n.op("K1N", "const", const=1)
    n.op("NNZ", "sub", ["K1N", "NZC"])
    n.op("MZ", "mul", ["ZSH", "NNZ"])
    n.op("ADDS", "add", ["MULSG", "MZ"])
    n.op("SH31", "relay", ["ADDS"], addon=shl(m + E))
    n.op("ADDF1", "add", ["RO", "SHE"])
    n.op("ADDF2", "add", ["ADDF1", "SH31"])
    n.op("O.F", "relay", ["ADDF2"])
    return n


def _scratch_place(g_main, fmt, name, n, entries, rows, cols, pitch, outs, gap=1, seeds=fmt1.SEEDS):
    sg = fmt1._scratch(g_main)
    nm, c, _ = fmt1.place_net_tight(sg, n, name, 2, 2, entries, rows, cols, pitch=pitch, gap=gap, outs=outs, seeds=seeds)
    return sg, nm, c


def fp_add_tight_u(g, fmt, name="ADD", rounding="rne", gap=6, seed=None, front_seed=None):
    """The adder as a U. Returns (entries {a, b}, exits {R}, consts, info)."""
    import fp_assembler_v1 as fa
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    wlow = fmt.Ka + 3
    wide = fa.FpFormat(fmt.name + "+4", S + 4, E, W)
    consts = {}
    kw = {"spread": True}
    snap, last = fmt1._snapshot(g), None
    for sd in ([front_seed] if front_seed else fmt1.SEEDS):
        try:
            n1, allpos, (nm1, c1, lanes1) = place_front(g, fmt, f"{name}.FR", 2, 2, rounding=rounding, seed=sd)
            break
        except Exception as e:
            last = e
            fmt1._restore(g, snap)
    else:
        raise last
    consts.update(c1)
    r1min, r1max, _, c1max = fmt1._bbox(g)
    # ---- top bands: ALA (flipped: its D bus at the bottom) over ALB (D bus at the top), both flowing east
    sg = fmt1._scratch(g)
    ala = fa.align_sticky(sg, fmt, f"{name}.ALA", 6, 6, flip=True)
    consts.update(ala.consts)
    h_a, w_a = fmt1._transplant(g, sg, 2, c1max + gap + 2)
    rowB = r1max - h_a + 1
    sg = fmt1._scratch(g)
    alb = fa.align_sticky(sg, fmt, f"{name}.ALB", 6, 6)
    consts.update(alb.consts)
    h_b, w_b = fmt1._transplant(g, sg, rowB, c1max + gap + 2)
    g.route_nets([(nm1["O.DA"], ala.entries["D"], kw), (nm1["O.VA"], ala.entries["V"], kw),
                  (nm1["O.DB"], alb.entries["D"], kw), (nm1["O.VB"], alb.entries["V"], kw)])
    cal_right = max(nd["c"] for k, nd in g.nodes.items() if k.startswith((f"{name}.ALA", f"{name}.ALB")))
    # ---- combine, east of the bands
    sg, ncb, cc = _scratch_place(g, fmt, f"{name}.CB", build_combine(fmt, rounding), ["AOUT", "ASTK", "BOUT", "BSTK", "SGNI", "PKI"], 18, 36, 3, ["O.M", "O.SGW", "O.SGR"])
    consts.update(cc)
    fmt1._transplant(g, sg, 2, cal_right + gap)
    g.route_nets([(ala.exits["OUT"], ncb["AOUT"], kw), (ala.exits["STK"], ncb["ASTK"], kw), (alb.exits["OUT"], ncb["BOUT"], kw), (alb.exits["STK"], ncb["BSTK"], kw),
                  (nm1["O.SGN"], ncb["SGNI"], kw), (nm1["O.PKW"], ncb["PKI"], kw)])
    ccmax = max(nd["c"] for k, nd in g.nodes.items() if k.startswith(f"{name}.CB"))
    rbot = max(nd["r"] for nd in g.nodes.values()) + gap + 1
    # ---- bottom band, built right to left: NRM under the combine's right end, then RND, then the pack beside the front
    sg = fmt1._scratch(g)
    nrm = fa.normalise_chain_clamped(sg, wide, f"{name}.NRM", 0, 0)
    consts.update(nrm.consts)
    _, _, cmin, cmax = fmt1._bbox(sg)
    c_nr = ccmax - (cmax - cmin)
    fmt1._transplant(g, sg, rbot, c_nr, flip_h=True)
    g.route_nets([(nm1["O.EXPIN"], nrm.entries["EXPIN"], kw), (ncb["O.M"], nrm.entries["V"], kw)])
    sg = fmt1._scratch(g)
    rnd = fa.round_mode(sg, fmt, rounding, f"{name}.RND", 0, 0, low=4)
    consts.update(rnd.consts)
    _, _, cmin, cmax = fmt1._bbox(sg)
    c_rd = c_nr - gap - (cmax - cmin + 1)
    fmt1._transplant(g, sg, rbot, c_rd, flip_h=True)
    sg, npk, cp = _scratch_place(g, fmt, f"{name}.PK", build_pack(fmt), ["RO", "EXR", "SGWI"], 12, 24, 3, ["O.F"])
    consts.update(cp)
    _, _, cmin, cmax = fmt1._bbox(sg)
    c_pk = c_rd - gap - (cmax - cmin + 1)
    if c_pk < 0:
        raise tp.LayoutError(f"the bottom band does not fit: needs {-c_pk} more columns on the left")
    fmt1._transplant(g, sg, rbot, c_pk, flip_h=True)
    nets = [(nrm.exits["NORM"], rnd.entries["X"]), (rnd.exits["OUT"], npk["RO"]), (nrm.exits["EXPOUT"], npk["EXR"]), (ncb["O.SGW"], npk["SGWI"])]
    if "SGN" in rnd.entries:
        nets.append((ncb["O.SGR"], rnd.entries["SGN"]))
    g.route_nets([(a, b, kw) for a, b in nets])
    return {"a": nm1["A.X"], "b": nm1["B.X"]}, {"R": npk["O.F"]}, consts, []
