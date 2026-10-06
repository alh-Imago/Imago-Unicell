"""tools/fp_add_v1.py -- ledger #990: a whole floating-point ADDER from flex cells, parametric in the format (Alan: "continue with the adder side").

    result = a + b   (normal numbers and zero; round-to-nearest-even; no subnormal / overflow / inf / nan handling -- the same scope as nano/fp32_add_v1.py)

Algorithm (no branch, no data-dependent routing, no loop; every step is a cell that exists today):
  unpack      x -> sign, exponent, significand with its hidden bit (hidden = [exp >= 1], so zero unpacks to 0); shifts only
  differences diff = eb - ea;  dA = diff * [diff >= 0],  dB = (-diff) * [-diff >= 1]     (each operand is shifted by the amount it is SMALLER by, the other by 0: no swap, no select)
  align       TWO align_sticky blocks (#988): A by dA, B by dB. Whichever operand has the smaller exponent is shifted right, its lost bits come out as a sticky flag.  eBig = ea + dA
  add/sub     S = A5 + sgn*B5, sgn = 1 - 2*(sa xor sb); X5 = (aligned << 1) + sticky (the sticky is a 3rd extra bit under guard and round); magnitude M = S * (2*[S>=0] - 1)
  normalise   normalise_chain on the S+4-bit window (#984): NORM = M << lz, EXPOUT = (eBig + 1) - lz
  round       round_rne (low = 4): the guard is bit 3, the sticky is bits 2..0
  finish      rounding overflow: exponent + [OUT >= 2^S];  zero: exponent and sign * [NORM >= 1];  result sign = sa xor [S < 0];  pack by shifts and two adders
The exponent and the sign travel to the end in ONE word (Y = eBig + (sa << E)) down the corridor between the two align bands; the stage-to-stage values are wires, so nothing crosses.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_assembler_v1 as fa  # noqa: E402

M32 = 0xFFFFFFFF


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


def fp_add(g, fmt, name="ADD", upto="all"):
    """Build the adder on grid g. Returns (entries {a, b}, exits {result}, consts). `upto="M"` stops after the add/subtract and exposes the taps M (magnitude of the sum), P (= [S >= 0]),
    EB (= max exponent + 1) and SA (= sign of a)."""
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
        # the packed word: sign << PK  +  exponent (own copies of both, on the outside of the cluster)
        sa_ = P(tag + "SA"); g.add(sa_, hr - s, 4, addon=shr(W - 1))
        sb_ = P(tag + "SB"); g.add(sb_, hr - 2 * s, 4, addon=shl(PK))
        f1 = P(tag + "F1"); g.add(f1, hr, 3, addon=shl(1))
        f2 = P(tag + "F2"); g.add(f2, hr, 2, addon=shr(W - E))
        at = P(tag + "T"); g.add(at, hr - 2 * s, 3, "adder")
        for x, y in ((head, sa_), (sa_, sb_), (sb_, at), (head, f1), (f1, f2)):
            g.link(x, y)
        nets.append((f2, at))
        return {"head": head, "exp": e2, "w": wd, "t": at}

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
    nrm = fa.normalise_chain(g, wide, P("NRM"), 10, nrm_c0)
    rnd = fa.round_rne(g, fmt, P("RND"), 10, rnd_c0, low=4)
    nz = P("NZ"); g.add(nz, 19, fx + 1)
    nzc = P("NZC"); g.add(nzc, 19, fx, "comparator", {"threshold": 1})
    g.link(nzc, nz)
    fl = P("FL"); g.add(fl, 12, fx, addon=shl(W - m))
    fr = P("FR"); g.add(fr, 12, fx + 1, addon=shr(W - m))
    g.link(fl, fr)
    cmpr = P("CMPR"); g.add(cmpr, 16, fx, "comparator", {"threshold": 1 << S})
    rr = P("RR"); g.add(rr, 16, fx + 1)
    addr = P("ADDR"); g.add(addr, 16, fx + 2, "adder")
    mule = P("MULE"); g.add(mule, 17, fx + 2, "mul")
    she = P("SHE"); g.add(she, 17, fx + 3, addon=shl(m))
    g.link(cmpr, rr); g.link(rr, addr); g.link(addr, mule); g.link(mule, she)
    k1b = b.const(P("K1B"), 24, fx, 1)
    nps = P("NPS"); g.add(nps, 23, fx, "adder", {"subtract_mode": 1})
    g.minuend[nps] = k1b
    npv = P("NPV"); g.add(npv, 23, fx + 1)
    sn = P("SN"); g.add(sn, 23, fx + 2, "adder")
    sb1 = P("SB1"); g.add(sb1, 23, fx + 3, addon=shl(W - 1))
    sb2 = P("SB2"); g.add(sb2, 23, fx + 4, addon=shr(W - 1))
    mulsg = P("MULSG"); g.add(mulsg, 22, fx + 4, "mul")
    sh31 = P("SH31"); g.add(sh31, 22, fx + 5, addon=shl(W - 1))
    for x_, y_ in ((k1b, nps), (nps, npv), (npv, sn), (sn, sb1), (sb1, sb2), (sb2, mulsg), (mulsg, sh31)):
        g.link(x_, y_)
    addf1 = P("ADDF1"); g.add(addf1, 14, fx + 3, "adder")
    addf2 = P("ADDF2"); g.add(addf2, 14, fx + 4, "adder")
    res = P("RES"); g.add(res, 14, fx + 5)
    g.link(addf1, addf2); g.link(addf2, res)
    nets2 = [(addi, nrm.entries["EXPIN"]), (mm, nrm.entries["V"]), (nrm.exits["NORM"], rnd.entries["X"]),
             (rnd.exits["OUT"], fl), (rnd.exits["OUT"], cmpr), (rnd.exits["OUT"], nzc), (nrm.exits["EXPOUT"], addr), (nz, mule), (nz, mulsg),
             (px, nps), (saa, sn), (fr, addf1), (she, addf1), (sh31, addf2)]
    g.route_nets(nets)
    g.route_nets(nets2)
    return {"a": ua["head"], "b": ub["head"]}, {"R": res}, {**ad.consts, **bd.consts, **b.consts, **nrm.consts}
