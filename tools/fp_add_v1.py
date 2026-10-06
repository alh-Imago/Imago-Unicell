"""tools/fp_add_v1.py -- ledger #990: a whole floating-point ADDER from flex cells, parametric in the format (Alan: "continue with the adder side").

    result = a + b   (round-to-nearest-even. Normal numbers, zero and, since #1006, SUBNORMAL inputs and results (gradual underflow); with `specials=True` (#1001) inf, nan and overflow too)

Algorithm (no branch, no data-dependent routing, no loop; every step is a cell that exists today):
  unpack      x -> sign, exponent, significand with its hidden bit (hidden = [exp >= 1], so zero unpacks to 0); shifts only
  differences diff = eb - ea;  dA = diff * [diff >= 0],  dB = (-diff) * [-diff >= 1]     (each operand is shifted by the amount it is SMALLER by, the other by 0: no swap, no select)
  align       TWO align_sticky blocks (#988): A by dA, B by dB. Whichever operand has the smaller exponent is shifted right, its lost bits come out as a sticky flag.  eBig = ea + dA
  add/sub     S = A5 + sgn*B5, sgn = 1 - 2*(sa xor sb); X5 = (aligned << 1) + sticky (the sticky is a 3rd extra bit under guard and round); magnitude M = S * (2*[S>=0] - 1)
  normalise   normalise_chain_clamped on the S+4-bit window (#984, #1006): NORM = M << min(lz, eBig), EXPOUT = (eBig + 1) - that shift (>= 1: a result below the smallest normal stays unnormalised)
  round       round_rne (low = 4): the guard is bit 3, the sticky is bits 2..0
  finish      pack = ((EXPOUT - 1) * nonzero << m) + rounded significand WITH its hidden bit (a rounding carry, normal or subnormal, lands in the exponent field by itself);  result sign = sa xor [S < 0]
  unpack      the exponent used for the difference and the packed word is the EFFECTIVE one, max(e, 1) (a subnormal has the exponent of the smallest normal; hidden bit = [e >= 1])
The exponent and the sign travel to the end in ONE word (Y = eBig + (sa << E)) down the corridor between the two align bands; the stage-to-stage values are wires, so nothing crosses.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_assembler_v1 as fa  # noqa: E402
from flex_layout_v1 import LayoutError  # noqa: E402

M32 = 0xFFFFFFFF
WEST = 14        # columns of free corridor west of the core when the special-value block is built (#1001)


def shl(n):
    return {"shift_en": 1, "direction": 0, "shift_amt": n}


def shr(n):
    return {"shift_en": 1, "direction": 1, "shift_amt": n}


class AddBuild:
    def __init__(self, g, fmt):
        self.g, self.fmt = g, fmt
        self.consts = {}
        self.S, self.E, self.m = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1
        self.Ka = fmt.Ka
        self.W = fmt.word

    def const(self, name, r, c, v):
        self.g.add(name, r, c, preload=v & M32)
        self.consts[name] = v & M32
        return name


def fp_add(g, fmt, name="ADD", upto="all", specials=False, pads=None):
    """Build the adder on grid g. Returns (entries {a, b}, exits {result}, consts). `upto="M"` stops after the add/subtract and exposes the taps M (magnitude of the sum), P (= [S >= 0]),
    EB (= max exponent + 1) and SA (= sign of a). `specials=True` (ledger #1001) adds the IEEE special values on the output side: inf/nan inputs, overflow to inf (see `_specials`)."""
    b = AddBuild(g, fmt)
    S, E, m, Ka, W = b.S, b.E, b.m, b.Ka, b.W
    L = W - 1 - (m + E)                                   # the format's own top-align shift (0 for fp32)
    wlow = Ka + 3                                         # lsb of the unpacked significand word: after the align's extra shift it sits at bit 2, after << 1 at bit 3
    P = lambda s: f"{name}.{s}"
    A0, B0 = 4, 22                                        # align bands: A rows 4..9 (flipped: d bus at the bottom), B rows 22..27 (d bus at the top)
    C0 = 42
    ad = fa.align_sticky(g, fmt, P("ALA"), A0, C0, flip=True)
    bd = fa.align_sticky(g, fmt, P("ALB"), B0, C0)
    rowA, rowB = A0 + 2, B0 + 3                           # the rows of the two V lanes
    nets = []
    PK = 10                                               # the packed word T = sign * 2^PK + exponent travels OUTSIDE the datapath (north / south strip) to the far-east unit

    def unpack(tag, hr, up):
        """Operand unpack, mirrored for B (up = -1). Returns dict of cells: head, exp (the room lane), w, t (the packed sign+exponent word, for the outside lane)."""
        s = 1 if up == 1 else -1
        head = P(tag + "H")
        g.add(head, hr, 4, addon=shl(L) if L else None)
        e1 = P(tag + "E1"); g.add(e1, hr + s, 4, addon=shl(1))
        e2 = P(tag + "E2"); g.add(e2, hr + 2 * s, 4, addon=shr(W - E))                  # exponent -> the room (south of A / north of B)
        m1 = P(tag + "M1"); g.add(m1, hr, 5, addon=shl(1 + E))                            # mantissa to the top
        m2 = P(tag + "M2"); g.add(m2, hr, 6, addon=shr(W - m - wlow))                     # ... and down to bit wlow
        wd = P(tag + "W"); g.add(wd, hr, 7, "adder")
        ch = P(tag + "CH"); g.add(ch, hr + 2 * s, 5, "comparator", {"threshold": 1})       # hidden = [exp >= 1]
        hs = P(tag + "HS"); g.add(hs, hr + 2 * s, 6, addon=shl(wlow + m))
        for x, y in ((head, e1), (e1, e2), (head, m1), (m1, m2), (m2, wd), (e2, ch), (ch, hs)):
            g.link(x, y)
        nets.append((hs, wd))
        # the EFFECTIVE exponent ee = max(e, 1) = (e - [e >= 1]) + 1: a subnormal operand has the exponent of the smallest normal (ledger #1005). Directly south of the exponent lane.
        xs = P(tag + "XS"); g.add(xs, hr + 3 * s, 4, "adder", {"subtract_mode": 1})
        ee = P(tag + "EE"); g.add(ee, hr + 4 * s, 4, "adder")
        k1 = b.const(P(tag + "K1"), hr + 4 * s, 3, 1)
        g.link(e2, xs); g.link(xs, ee); g.link(k1, ee)
        g.minuend[xs] = e2
        nets.append((ch, xs))                                                           # ch -> one relay -> xs (a short routed lane; balance can lengthen it)
        # the packed word: sign << PK  +  effective exponent (own copy of the sign, on the outside of the cluster)
        sa_ = P(tag + "SA"); g.add(sa_, hr - s, 4, addon=shr(W - 1))
        sb_ = P(tag + "SB"); g.add(sb_, hr - 2 * s, 4, addon=shl(PK))
        at = P(tag + "T"); g.add(at, hr - 2 * s, 3, "adder")
        for x, y in ((head, sa_), (sa_, sb_), (sb_, at)):
            g.link(x, y)
        nets.append((ee, at))
        out = {"head": head, "exp": ee, "w": wd, "t": at}
        if specials:
            # two taps for the special-value logic, reserved now as one-relay stubs on free faces (so the core's routes cannot wall them in): the magnitude word (f1 = x << 1, sign gone)
            # below / above f1, and the sign bit (sa_ = x >> (W-1)) east of sa_.
            f1 = P(tag + "F1"); g.add(f1, hr, 3, addon=shl(1))
            tm = P(tag + "TM"); g.add(tm, hr + s, 3)
            ts = P(tag + "TS"); g.add(ts, hr - s, 5)
            g.link(head, f1)
            g.link(f1, tm)
            g.link(sa_, ts)
            out["raw"] = [tm, ts]
        return out

    ua = unpack("A", rowA, 1)                              # A's head at the A V-lane row
    ub = unpack("B", rowB, -1)
    # --- the room (between the two align bands): exponent difference diff = eb - ea, dA = diff * [diff >= 0], dB = (-diff) * [-diff >= 1] ------------------
    sub = P("SUBD"); g.add(sub, 15, 10, "adder", {"subtract_mode": 1})
    g.minuend[sub] = ub["exp"]                             # eb - ea: the minuend (eb) must arrive FIRST
    df = P("DF"); g.add(df, 15, 11)
    cmpc = P("CMPC"); g.add(cmpc, 14, 11, "comparator", {"threshold": 0})
    rc = P("RC"); g.add(rc, 14, 12)
    mula = P("MULA"); g.add(mula, 15, 12, "mul")
    da = P("DA"); g.add(da, 15, 13)
    g.link(sub, df); g.link(df, cmpc); g.link(cmpc, rc); g.link(rc, mula); g.link(df, mula); g.link(mula, da)
    k0 = b.const(P("K0"), 17, 11, 0)
    neg = P("NEG"); g.add(neg, 16, 11, "adder", {"subtract_mode": 1})
    g.minuend[neg] = k0
    nd = P("ND"); g.add(nd, 16, 12)
    cmpn = P("CMPN"); g.add(cmpn, 16, 13, "comparator", {"threshold": 1})
    rn = P("RN"); g.add(rn, 17, 13)
    mulb = P("MULB"); g.add(mulb, 17, 12, "mul")
    db = P("DB"); g.add(db, 18, 12)
    g.link(df, neg); g.link(k0, neg); g.link(neg, nd); g.link(nd, cmpn); g.link(cmpn, rn); g.link(rn, mulb); g.link(nd, mulb); g.link(mulb, db)
    nets += [(da, ad.entries["D"]), (db, bd.entries["D"]), (ua["w"], ad.entries["V"]), (ub["w"], bd.entries["V"]), (ub["exp"], sub), (ua["exp"], sub)]
    # --- east: the combine (a wall: the two aligned operands meet here) -----------------------------------------------------------------------------
    xe = C0 + 50
    ar = P("AR"); g.add(ar, 6, xe, addon=shl(1))
    adda = P("ADDA"); g.add(adda, 6, xe + 1, "adder")
    br = P("BR"); g.add(br, 25, xe, addon=shl(1))
    addb = P("ADDB"); g.add(addb, 25, xe + 1, "adder")
    mult = P("MULT"); g.add(mult, 22, xe + 4, "mul")
    addsum = P("ADDSUM"); g.add(addsum, 14, xe + 6, "adder")
    sf = P("SF"); g.add(sf, 14, xe + 7)
    cmpp = P("CMPP"); g.add(cmpp, 13, xe + 7, "comparator", {"threshold": 0})
    p2 = P("P2"); g.add(p2, 13, xe + 8, addon=shl(1))
    km1 = b.const(P("KM1"), 12, xe + 9, M32)
    subp = P("SUBP"); g.add(subp, 13, xe + 9, "adder")
    sg2 = P("SG2"); g.add(sg2, 14, xe + 9)
    mulm = P("MULM"); g.add(mulm, 14, xe + 8, "mul")
    mm = P("M"); g.add(mm, 15, xe + 8)
    px = P("PX"); g.add(px, 12, xe + 7)                   # the sign flag p = [S >= 0] (a tap and a lane to the finish)
    g.link(cmpp, px)
    for x_, y_ in ((ar, adda), (br, addb), (addsum, sf), (sf, cmpp), (sf, mulm), (cmpp, p2), (p2, subp), (km1, subp), (subp, sg2), (sg2, mulm), (mulm, mm)):
        g.link(x_, y_)
    nets += [(ad.exits["OUT"], ar), (ad.exits["STK"], adda), (bd.exits["OUT"], br), (bd.exits["STK"], addb), (addb, mult), (adda, addsum), (mult, addsum)]
    # --- the far-east unit (outside): from the two packed words T = sign*2^PK + exp: sgn = +-1, sign of a, and eBig + 1 ----------------------------------------------
    wide = fa.FpFormat(fmt.name + "+4", S + 4, E, W)                                  # the sum's window: S bits + guard, round, sticky + the carry bit
    nrm_c0, rnd_c0 = 104, 104 + 9 * (wide.K - 1) + 14
    fx = rnd_c0 + 14                                       # finish cluster columns
    ux = fx + 22                                           # far-east unit
    xa = P("XA"); g.add(xa, 6, ux)
    saa = P("SAA"); g.add(saa, 5, ux, addon=shr(PK))
    ea1 = P("EA1"); g.add(ea1, 6, ux - 1, addon=shl(W - PK))
    ea2 = P("EA2"); g.add(ea2, 6, ux - 2, addon=shr(W - PK))
    xb = P("XB"); g.add(xb, 26, ux)
    wpa = P("WPA"); g.add(wpa, 1, ux + 1)                 # waypoints: the packed words come in from the north / south and join in the middle
    wpb = P("WPB"); g.add(wpb, 31, ux + 1)
    wps2 = P("WPS2"); g.add(wps2, 28, xe + 5)
    wps = P("WPS"); g.add(wps, 28, ux - 2)                 # the sign lane runs back west along the south, under the finish
    subt = P("SUBT"); g.add(subt, 16, ux - 4, "adder", {"subtract_mode": 1})
    g.minuend[subt] = xb
    addu = P("ADDU"); g.add(addu, 16, ux - 5, "adder")
    ku = b.const(P("KU"), 15, ux - 5, (3 << PK) // 2 * 1)                             # 1.5 * 2^PK : (sb - sa + 1) in the upper field, diff + 2^(PK-1) in the lower
    uf = P("UF"); g.add(uf, 16, ux - 6)
    g.link(subt, addu); g.link(ku, addu); g.link(addu, uf)
    l1 = P("L1"); g.add(l1, 15, ux - 6, addon=shl(W - PK))
    l2 = P("L2"); g.add(l2, 14, ux - 6, addon=shr(W - PK))
    k5 = b.const(P("K5"), 13, ux - 7, -(1 << (PK - 1)))
    dfs = P("DFS"); g.add(dfs, 13, ux - 6, "adder")                                   # diff = L - 2^(PK-1)  (as L + the two's complement)
    df2 = P("DF2"); g.add(df2, 12, ux - 6)
    cmpc2 = P("CMPC2"); g.add(cmpc2, 11, ux - 6, "comparator", {"threshold": 0})
    rc2 = P("RC2"); g.add(rc2, 11, ux - 7)
    mula2 = P("MULA2"); g.add(mula2, 12, ux - 7, "mul")
    da2 = P("DA2"); g.add(da2, 12, ux - 8)
    adde2 = P("ADDE2"); g.add(adde2, 12, ux - 9, "adder")
    ebg = P("EBG"); g.add(ebg, 12, ux - 10)
    addi = P("ADDI"); g.add(addi, 12, ux - 11, "adder")                                  # EXPIN = eBig + 1 (the sum may carry out one bit)
    k1i = b.const(P("K1I"), 11, ux - 11, 1)
    for x_, y_ in ((xa, ea1), (xa, saa), (ea1, ea2), (uf, l1), (l1, l2), (l2, dfs), (k5, dfs), (dfs, df2), (df2, cmpc2), (cmpc2, rc2), (rc2, mula2), (df2, mula2), (mula2, da2),
                   (da2, adde2), (adde2, ebg), (ebg, addi), (k1i, addi)):
        g.link(x_, y_)
    h1 = P("H1"); g.add(h1, 17, ux - 6, addon=shr(PK))
    h2 = P("H2"); g.add(h2, 18, ux - 6, addon=shl(W - 1))
    h3 = P("H3"); g.add(h3, 19, ux - 6, addon=shr(W - 1))
    h4 = P("H4"); g.add(h4, 20, ux - 6, addon=shl(1))
    k1s = b.const(P("K1S"), 21, ux - 7, -1)
    sgs = P("SGS"); g.add(sgs, 21, ux - 6, "adder")                                   # sgn = 2*bit - 1
    sgn = P("SGN"); g.add(sgn, 22, ux - 6)
    for x_, y_ in ((uf, h1), (h1, h2), (h2, h3), (h3, h4), (h4, sgs), (k1s, sgs), (sgs, sgn)):
        g.link(x_, y_)
    nets += [(ua["t"], wpa), (wpa, xa), (ub["t"], wpb), (wpb, xb), (xa, subt), (xb, subt), (ea2, adde2), (sgn, wps), (wps, wps2), (wps2, mult)]
    if upto == "M":
        g.route_nets(nets)
        return {"a": ua["head"], "b": ub["head"]}, {"M": mm, "P": px, "EB": addi, "SA": saa}, {**ad.consts, **bd.consts, **b.consts}
    # --- normalise / round / finish (east) ---------------------------------------------------------------------------------------------------
    nrm = fa.normalise_chain_clamped(g, wide, P("NRM"), 10, nrm_c0)
    rnd = fa.round_rne(g, fmt, P("RND"), 10, rnd_c0, low=4)
    nz = P("NZ"); g.add(nz, 19, fx + 1)
    nzc = P("NZC"); g.add(nzc, 19, fx, "comparator", {"threshold": 1})
    g.link(nzc, nz)
    # the pack (ledger #1005): bits = ((er - 1) << m) + M, M = the rounded S-bit significand INCLUDING its hidden bit. A normal number: er - 1 + 1 = the exponent field. A subnormal result (the clamped
    # normalise stops at er = 1, M < 2^m): the field is 0. A rounding carry (M = 2^S, or M = 2^m for a subnormal) lands in the exponent field by itself -- no bump step, no masking of the hidden bit.
    kme = b.const(P("KME"), 16, fx + 1, M32)                                             # -1
    addr = P("ADDR"); g.add(addr, 16, fx + 2, "adder")
    mule = P("MULE"); g.add(mule, 17, fx + 2, "mul")
    she = P("SHE"); g.add(she, 17, fx + 3, addon=shl(m))
    g.link(kme, addr); g.link(addr, mule); g.link(mule, she)
    k1b = b.const(P("K1B"), 24, fx, 1)
    nps = P("NPS"); g.add(nps, 23, fx, "adder", {"subtract_mode": 1})
    g.minuend[nps] = k1b
    npv = P("NPV"); g.add(npv, 23, fx + 1)
    sn = P("SN"); g.add(sn, 23, fx + 2, "adder")
    sb1 = P("SB1"); g.add(sb1, 23, fx + 3, addon=shl(W - 1))
    sb2 = P("SB2"); g.add(sb2, 23, fx + 4, addon=shr(W - 1))
    mulsg = P("MULSG"); g.add(mulsg, 22, fx + 4, "mul")
    sh31 = P("SH31"); g.add(sh31, 22, fx + 5, addon=shl(m + E))      # the result sign, up to the format's own sign bit
    for x_, y_ in ((k1b, nps), (nps, npv), (npv, sn), (sn, sb1), (sb1, sb2), (sb2, mulsg), (mulsg, sh31)):
        g.link(x_, y_)
    addf1 = P("ADDF1"); g.add(addf1, 14, fx + 3, "adder")
    addf2 = P("ADDF2"); g.add(addf2, 14, fx + 4, "adder")
    res = P("RES"); g.add(res, 14, fx + 5)
    g.link(addf1, addf2); g.link(addf2, res)
    nets2 = [(addi, nrm.entries["EXPIN"]), (mm, nrm.entries["V"]), (nrm.exits["NORM"], rnd.entries["X"]),
             (rnd.exits["OUT"], nzc), (nrm.exits["EXPOUT"], addr), (nz, mule), (nz, mulsg),
             (px, nps), (saa, sn), (rnd.exits["OUT"], addf1), (she, addf1), (sh31, addf2)]
    if specials:
        for nd in g.nodes.values():                           # a free corridor west of the core for the lanes of the special-value block (translation only: nothing is routed yet)
            nd["c"] += WEST
        out, c3, route_rest = _specials(g, b, name, ua, ub, res, addf1, pads=pads or {})
    if specials:
        route_rest.early()
    g.route_nets(nets)
    g.route_nets(nets2)
    if specials:
        route_rest()
        return {"a": ua["head"], "b": ub["head"]}, {"R": out}, {**ad.consts, **bd.consts, **b.consts, **nrm.consts, **c3}
    return {"a": ua["head"], "b": ub["head"]}, {"R": res}, {**ad.consts, **bd.consts, **b.consts, **nrm.consts}


class _Net:
    """A tiny netlist for the special-value logic: named cells with their sources, placed on a LOOSE lattice by data-flow level (Alan: "loose fit, then tighten if that helps") and wired by the router."""
    def __init__(self):
        self.cells, self.order = {}, []

    def op(self, name, kind, srcs=(), thr=None, addon=None, const=None):
        self.cells[name] = {"kind": kind, "srcs": list(srcs), "thr": thr, "addon": addon, "const": const}
        self.order.append(name)
        return name


def _specials(g, b, name, ua, ub, res, mule, row0=38, col0=30, pads=None):
    """IEEE special values on the output side (ledger #1001), around the finished adder: inputs inf / nan, overflow to inf.  Everything is cells that exist today.
        per operand x:  mag = x without its sign; c = [mag >= INF] (inf or nan); n = [mag >= INF + 1] (nan); inf = c - n; sign = x >> (m+E)
        nan out  = [ n_a + n_b + inf_a * inf_b * (sa xor sb) >= 1 ]  (quiet bit set: a NaN)       spec = [c_a + c_b >= 1]
        sign of the infinity = [sa*c_a + sb*c_b >= 1];  Z = (that sign << (m+E)) + INF + (nan << (m-1))
        overflow: ovf = [the packed magnitude (before the sign) >= INF] (the exponent field incl. the rounding carry reaches 2^E - 1);  F_fin = R + ovf * ((R's sign + INF) - R)
        result    F = F_fin + spec * (Z - F_fin)
    Places the cells and lays the lanes from outside at once; returns (exit cell, consts, route_rest) -- call route_rest() after the core's own routing."""
    S, E, m, W = b.S, b.E, b.m, b.W
    L = W - 1 - (m + E)
    INF = ((1 << E) - 1) << m
    taps = [*ua["raw"], *ub["raw"]]
    at_ = g.at()

    def port(cell):                                            # a one-relay stub on a free face of `cell`, reserved before the core's routing (the result and the exponent lanes leave through these)
        r_, c_ = g.pos(cell)
        free = [(r_ + dr, c_ + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (r_ + dr, c_ + dc) not in at_ and 0 <= r_ + dr < g.rows and 0 <= c_ + dc < g.cols]
        r2, c2 = free[0]
        sn = cell + ".sp"
        g.add(sn, r2, c2)
        g.link(cell, sn)
        return sn
    res, mule = port(res), port(mule)
    n = _Net()
    x = {}
    for t, u in (("A", ua), ("B", ub)):
        raw0, raw1 = u["raw"]
        n.op(f"{t}.MG", "relay", [raw0], addon=shr(1))                 # the magnitude, top-aligned (x << 1 >> 1 without the sign)
        n.op(f"{t}.SG", "relay", [raw1])                               # the sign bit, 0 / 1
        n.op(f"{t}.C", "cmp", [f"{t}.MG"], thr=INF << L)
        n.op(f"{t}.N", "cmp", [f"{t}.MG"], thr=(INF + 1) << L)
        n.op(f"{t}.I", "sub", [f"{t}.C", f"{t}.N"])
    n.op("II", "mul", ["A.I", "B.I"])
    n.op("XS", "add", ["A.SG", "B.SG"])
    n.op("X1", "cmp", ["XS"], thr=1)
    n.op("X2", "cmp", ["XS"], thr=2)
    n.op("XR", "sub", ["X1", "X2"])
    n.op("CF", "mul", ["II", "XR"])
    n.op("NS1", "add", ["A.N", "B.N"])
    n.op("NS2", "add", ["NS1", "CF"])
    n.op("NO", "cmp", ["NS2"], thr=1)
    n.op("NQ", "relay", ["NO"], addon=shl(m - 1))
    n.op("CS", "add", ["A.C", "B.C"])
    n.op("SP", "cmp", ["CS"], thr=1)
    n.op("SAC", "mul", ["A.SG", "A.C"])
    n.op("SBC", "mul", ["B.SG", "B.C"])
    n.op("SI", "add", ["SAC", "SBC"])
    n.op("SN", "cmp", ["SI"], thr=1)
    n.op("SH", "relay", ["SN"], addon=shl(m + E))
    n.op("KI", "const", const=INF)
    n.op("Z1", "add", ["SH", "KI"])
    n.op("Z", "add", ["Z1", "NQ"])
    n.op("OV", "cmp", [mule], thr=INF)                        # overflow: the packed magnitude (exponent field, rounding carry included) reaches the infinity pattern
    n.op("RR", "relay", [res])                                 # the result enters here, then fans out
    n.op("RS1", "relay", ["RR"], addon=shr(m + E))
    n.op("RS", "relay", ["RS1"], addon=shl(m + E))
    n.op("KI2", "const", const=INF)
    n.op("IS", "add", ["RS", "KI2"])
    n.op("D1", "sub", ["IS", "RR"])
    n.op("M1X", "mul", ["OV", "D1"])
    n.op("FF", "add", ["RR", "M1X"])
    n.op("D2", "sub", ["Z", "FF"])
    n.op("M2X", "mul", ["SP", "D2"])
    n.op("F", "add", ["FF", "M2X"])
    ext = {x_: None for x_ in (*taps, res, mule)}
    return _place_and_route(g, name, n, ext, ua["raw"], ub["raw"], res, mule, row0, col0, pads=pads or {})


def _chains(n, ext):
    """Alan's layout (6 Oct 2026): "lay out each path as a separate thing ... a series of simple paths ... joined on one at a time; where they cross, use a cross".
    The netlist is cut into CHAINS: repeatedly the longest path through the cells not yet placed (a chain = one row, its cells left to right in data-flow order). The column of a cell is its
    data-flow level, the row is its chain. Constants are not chained: they sit beside the cell they feed. Returns ({cell: (row_index, level)}, [chains])."""
    lvl = {}

    def level(c):
        if c in ext:
            return -1
        if c in lvl:
            return lvl[c]
        lvl[c] = 1 + max((level(q) for q in n.cells[c]["srcs"] if n.cells[c]["kind"] != "const"), default=-1)
        return lvl[c]
    for c in n.order:
        level(c)
    cells = [c for c in n.order if n.cells[c]["kind"] != "const"]
    preds = {c: [q for q in n.cells[c]["srcs"] if q in n.cells and n.cells[q]["kind"] != "const"] for c in cells}
    for c in cells:                                          # a subtract chains through its MINUEND (the first source): the subtrahend is then a lane, and a lane can be given extra length
        if n.cells[c]["kind"] == "sub":
            preds[c] = [q for q in preds[c] if q == n.cells[c]["srcs"][0]]
    left, chains = set(cells), []
    while left:
        best = {}
        for c in sorted(left, key=lambda c: lvl[c]):
            ps = [q for q in preds[c] if q in left]
            best[c] = max(((best[q][0] + 1, q) for q in ps), default=(1, None))
        end = max(left, key=lambda c: (best[c][0], -lvl[c]))
        path, c = [], end
        while c is not None:
            path.append(c)
            c = best[c][1]
        path.reverse()
        chains.append(path)
        left -= set(path)
    # row order: the next chain is the one most connected to the rows already placed (a chain with the longest path first)
    links = collections.Counter()
    owner = {c: i for i, ch in enumerate(chains) for c in ch}
    for c in cells:
        for q in preds[c]:
            if owner[q] != owner[c]:
                links[frozenset((owner[q], owner[c]))] += 1
    order = [0]
    while len(order) < len(chains):
        nxt = max((i for i in range(len(chains)) if i not in order), key=lambda i: (sum(links[frozenset((i, j))] for j in order), -i))
        order.append(nxt)
    rowof = {ci: r for r, ci in enumerate(order)}
    pos = {c: (rowof[owner[c]], lvl[c]) for c in cells}
    return pos, [chains[i] for i in order]


def _place_and_route(g, name, n, ext, raw_a, raw_b, res, mule, row0, col0, pads=None):
    pads = pads or {}
    """Alan's recipe (6 Oct 2026): every path is its own simple line, joined one at a time, a CROSS wherever two lines meet.
      * the netlist is cut into chains (`_chains`); a chain is one ROW, its cells joined by a straight wire along the row (the primary wires);
      * every cell has its OWN column (3 apart), so a vertical lane from a cell can never meet another cell;
      * every other connection is a three-leg line: out of the source's top or bottom port, vertically to a horizontal TRACK row in the gutter between two chains, along the track, vertically into
        the target's top or bottom port. The track rows are allocated first-fit (no two runs overlap), the gutters are as tall as their tracks;
      * where a line meets another it passes through the other's straight relay: a crossing tile (`Grid.route_line`).
    No search, no rip-up: the geometry is computed, then every line is laid. Lanes from outside (the operand taps, the result and the exponent) come to a gate at the west edge of their row."""
    taps_ = {*raw_a, *raw_b}
    pos0, chains = _chains(n, ext)
    nrows = len(chains)
    rowidx = {c: r for r, ch in enumerate(chains) for c in ch}
    cells = [c for ch in chains for c in ch]
    order = sorted(cells, key=lambda c: (pos0[c][1], rowidx[c]))
    C = {c: col0 + 3 * i for i, c in enumerate(order)}
    names = {c: f"{name}.SP.{c}" for c in n.order}
    prim = {(ch[k], ch[k + 1]) for ch in chains for k in range(len(ch) - 1)}
    edges = [(q, c) for c in cells for q in n.cells[c]["srcs"] if q not in ext and n.cells[q]["kind"] != "const"]
    assert prim <= set(edges), "a chain step that is not a netlist edge"
    sec = [e for e in edges if e not in prim]
    extin = [(q, c) for c in cells for q in n.cells[c]["srcs"] if q in ext]
    constin = [(q, c) for c in cells for q in n.cells[c]["srcs"] if q not in ext and n.cells[q]["kind"] == "const"]
    # ---- ports: every cell has a top (N) and a bottom (S) port, plus the west face when it has no chain input and no lane from outside, plus the east face when it ends its chain.
    #      A port is EITHER one input OR the start of up to three outputs (the west / east faces carry one line)
    prim_in = {v for _, v in prim}
    prim_out = {u for u, _ in prim}
    ext_in = {c for _, c in extin}
    out_side, in_side, const_side = {}, {}, {}
    for c in cells:
        taken = {"N": None, "S": None, "W": None, "E": None}
        free_w = c not in prim_in and c not in ext_in
        free_e = c not in prim_out
        ins = [("const", e) for e in constin if e[1] == c] + [("net", e) for e in sec if e[1] == c]
        outs = [e for e in sec if e[0] == c]
        for kind, e in ins:
            pref = "N" if kind == "const" or rowidx[e[0]] < rowidx[c] else "S"
            cand = [pref, "S" if pref == "N" else "N"] + (["W"] if free_w else []) + (["E"] if free_e else [])
            side = next((x for x in cand if taken[x] is None), None)
            if side is None:
                raise LayoutError(f"special-value cell {c}: no free port for an input")
            taken[side] = "in"
            (const_side if kind == "const" else in_side)[e] = side
        for e in outs:
            pref = "N" if rowidx[e[1]] < rowidx[c] else "S"
            cand = [pref, "S" if pref == "N" else "N"]
            side = next((x for x in cand if taken[x] in (None, "out")), None)
            if side is None:
                cand = (["E"] if free_e else []) + (["W"] if free_w else [])
                side = next((x for x in cand if taken[x] is None), None)
            if side is None:
                raise LayoutError(f"special-value cell {c}: no free port for an output")
            taken[side] = "out"
            out_side[e] = side
    # ---- gutters and tracks
    lane_off, per = {}, collections.defaultdict(list)
    for e in sec:
        per[(e[0], out_side[e])].append(e)
    for key, lst in per.items():
        if key[1] in "WE" and len(lst) > 1:
            raise LayoutError(f"special-value cell {key[0]}: two outputs on the {key[1]} face")
        if len(lst) > 3:
            raise LayoutError(f"special-value cell {key[0]}: {len(lst)} outputs on one port (3 fit)")
        for k, e in enumerate(lst):
            lane_off[e] = (-1 if key[1] == "W" else 1) if key[1] in "WE" else (0, 1, -1)[k]
    in_off = {e: ((-1 if in_side[e] == "W" else 1) if in_side[e] in "WE" else 0) for e in sec}
    gut, span = {}, collections.defaultdict(list)
    for e in sec:
        u, v = e
        i, j = rowidx[u], rowidx[v]
        lo, hi = -1, nrows - 1
        if out_side[e] == "S":
            lo = max(lo, i)
        elif out_side[e] == "N":
            hi = min(hi, i - 1)
        if in_side[e] == "S":
            lo = max(lo, j)
        elif in_side[e] == "N":
            hi = min(hi, j - 1)
        if lo > hi:
            raise LayoutError(f"special-value net {u} -> {v}: no gutter between its two ports")
        want = (i if out_side[e] == "S" else i - 1) if out_side[e] in "NS" else (j if in_side[e] == "S" else j - 1) if in_side[e] in "NS" else (i + j) // 2
        gut[e] = min(max(want, lo), hi)
        x1, x2 = sorted((C[u] + lane_off[e], C[v] + in_off[e]))
        span[gut[e]].append((x2 - x1, x1, x2, e))
    track, T = {}, collections.defaultdict(int)
    for gi, lst in span.items():
        rows_ = []                                           # per track: list of (x1, x2)
        for _w, x1, x2, e in sorted(lst, key=lambda t: (t[1], t[2])):
            pad = pads.get(e, 0)                             # a lane that must arrive later takes a track `pad` rows deeper: +2 relays per row
            while len(rows_) < pad:
                rows_.append([])
            t = next((k for k, iv in enumerate(rows_) if k >= pad and all(x2 + 2 < a or x1 > b + 2 for a, b in iv)), None)
            if t is None:
                rows_.append([])
                t = len(rows_) - 1
            rows_[t].append((x1, x2))
            track[e] = t
        T[gi] = len(rows_)
    R = {-1: row0}
    for gi in range(-1, nrows):
        R[gi + 1] = R[gi] + T[gi] + 4
    if R[nrows] + 2 > g.rows:
        raise LayoutError(f"the special-value block needs {R[nrows] + 2} grid rows (grid has {g.rows})")
    if C[order[-1]] + 3 > g.cols:
        raise LayoutError("the special-value block does not fit the grid width")
    # ---- cells, ports, corners
    for c in cells:
        k = n.cells[c]
        r, cc = R[rowidx[c]], C[c]
        nm = names[c]
        if k["kind"] == "relay":
            g.add(nm, r, cc, addon=k["addon"])
        elif k["kind"] == "add":
            g.add(nm, r, cc, "adder")
        elif k["kind"] == "sub":
            g.add(nm, r, cc, "adder", {"subtract_mode": 1})
        elif k["kind"] == "mul":
            g.add(nm, r, cc, "mul")
        else:
            g.add(nm, r, cc, "comparator", {"threshold": k["thr"]})
    sq = lambda c, side: (R[rowidx[c]] + (1 if side == "S" else -1 if side == "N" else 0), C[c] + (1 if side == "E" else -1 if side == "W" else 0))
    stub_o, stub_i = {}, {}
    for (c, side) in {(e[0], out_side[e]) for e in sec}:
        r_, c_ = sq(c, side)
        g.add(f"{names[c]}.o{side}", r_, c_)
        g.link(names[c], f"{names[c]}.o{side}")
    for e in sec:
        stub_o[e] = f"{names[e[0]]}.o{out_side[e]}"
        r_, c_ = sq(e[1], in_side[e])
        stub_i[e] = f"{names[e[1]]}.i{in_side[e]}"
        g.add(stub_i[e], r_, c_)
        g.link(stub_i[e], names[e[1]])
    _LAST_NETS.clear()
    _LAST_NETS.update({stub_i[e]: e for e in sec})
    consts = {}
    for q, c in constin:
        r_, c_ = sq(c, const_side[(q, c)])
        g.add(names[q], r_, c_, preload=n.cells[q]["const"] & M32)
        g.link(names[q], names[c])
        consts[names[q]] = n.cells[q]["const"] & M32
    corner = {}
    for e in sec:
        u, v = e
        gi, y = gut[e], R[gut[e]] + 2 + track[e]
        xu, xv = C[u] + lane_off[e], C[v] + in_off[e]
        pts = []
        if lane_off[e] and out_side[e] in "NS":
            pts.append((sq(u, out_side[e])[0], xu))
        pts += [(y, xu), (y, xv)]
        cn = []
        for k, (r_, c_) in enumerate(pts):
            nm = f"{name}.SP.w{len(corner)}_{k}"
            g.add(nm, r_, c_)
            cn.append(nm)
        corner[e] = cn
    gates = {}
    for q, c in extin:
        gates[(q, c)] = f"{names[c]}.gate"
        g.add(gates[(q, c)], R[rowidx[c]], 2)
    for c in n.order:
        if n.cells[c]["kind"] == "sub":
            q = n.cells[c]["srcs"][0]
            g.minuend[names[c]] = q if q in ext else names[q]
    # lanes from outside that must be laid BEFORE the core's own routing (the west edge fills up): the operand taps
    for (q, c), gate in gates.items():
        g.route_line(gate, names[c])                         # the last stretch along the row is reserved first, so no lane can arrive over it

    def _lane(q, gate):
        if q.endswith("ATS"):                                # A's sign tap sits north of the core: go round the north edge into the west corridor, never through the room (SUBD's routes)
            wp = f"{q}.wp"
            g.add(wp, 1, 12)
            g.route(q, wp, spread=True, cross=True)
            g.route(wp, gate, spread=True, cross=True)
        else:
            g.route(q, gate, spread=True, cross=True)

    def route_early():                                       # the lanes that leave the core's own east side (result, overflow tap): laid BEFORE the core's routes fill that corner
        for (q, c), gate in gates.items():
            if q in (res, mule):
                _lane(q, gate)

    def route_rest():
        for u, v in sorted(prim):
            g.route_line(names[u], names[v])
        for e in sorted(sec, key=lambda e: (gut[e], track[e])):
            chain_ = [stub_o[e], *corner[e], stub_i[e]]
            for a_, b_ in zip(chain_, chain_[1:]):
                g.route_line(a_, b_)
        for (q, c), gate in gates.items():
            if q not in (res, mule):
                _lane(q, gate)
    route_rest.early = route_early
    return names["F"], consts, route_rest


_PADS = {}
_LAST_NETS = {}          # in-stub cell name -> the netlist edge (u, v) it ends, of the block built last


def fp_add_grid(fmt, specials=True, rows=220, cols=330, name="ADD", attempts=1):
    """Build the adder (with the special-value block) on a fresh grid and return (grid, entries, exits, consts), timing ties and subtract orders of the block already removed.
    The block's lines cannot be lengthened by `Grid.balance` (they cross other lines), so a lane that must arrive later is given a deeper track (`pads`, +2 relays per row): the block is laid again
    with the pads the previous try asked for (the geometry is computed, so this is a handful of tries; the pads are remembered per format)."""
    from flex_layout_v1 import Grid
    pads = dict(_PADS.get(fmt.name, {})) if specials else {}
    for attempt in range(attempts):
        g = Grid(rows=rows, cols=cols)
        ent, ex, consts = fp_add(g, fmt, name=name, specials=specials, pads=pads)
        if not specials:
            break
        probs = [p_ for p_ in g.problems() if p_[0].startswith(f"{name}.SP.")]
        if not probs:
            break
        t, srcs = g.hops(), g.sources()
        grown = False
        for c, kind, x, y in probs:
            arr = lambda q: t[q] + g.xdelay.get((c, q), 0)
            lane = next((q for q in (x, y) if q.endswith((".iN", ".iS", ".iW", ".iE"))), None)
            if lane is None:
                continue
            other = y if lane == x else x
            need = 1 if kind == "tie" else max(1, (arr(other) - arr(lane)) // 2 + 1) if kind == "order" and lane == y else 1
            key = _LAST_NETS.get(lane)
            if key is None:
                continue
            pads[key] = pads.get(key, 0) + need
            grown = True
        if not grown:
            break
    if specials:
        _PADS[fmt.name] = pads
    return g, ent, ex, consts
