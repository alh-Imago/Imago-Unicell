"""tools/fp_mul_tight_v1.py -- ledger #1013: the multiplier's FRONT block (N1) placed tightly from a drawn map (see tightplace_v1)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402
import netplace_v1 as npl  # noqa: E402
import tightplace_v1 as tp  # noqa: E402

shl, shr = fadd.shl, fadd.shr


def _operand(n, t, fmt):
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    INF = ((1 << E) - 1) << m
    P = lambda s: f"{t}.{s}"
    n.op(P("X"), "relay", [])                                                # the entry: the raw word
    n.op(P("SG"), "relay", [P("X")], addon=shr(m + E))
    n.op(P("ML"), "relay", [P("X")], addon=shl(W - m - E))                   # the sign dropped, the exponent at the top
    n.op(P("FL"), "relay", [P("ML")], addon=shl(E))
    n.op(P("F"), "relay", [P("FL")], addon=shr(W - m))                       # the fraction
    n.op(P("EV"), "relay", [P("ML")], addon=shr(W - E))                      # the exponent field
    n.op(P("MG"), "relay", [P("ML")], addon=shr(W - m - E))                  # the magnitude
    n.op(P("CH"), "cmp", [P("EV")], thr=1)                                    # hidden bit = [e >= 1]
    n.op(P("HD"), "relay", [P("CH")], addon=shl(m))
    n.op(P("Hx"), "relay", [P("HD")])                                         # (a spacer: the hidden bit and the fraction arrive one apart)
    n.op(P("SIG"), "add", [P("F"), P("Hx")])
    n.op(P("K1a"), "const", const=1)
    n.op(P("NC"), "sub", [P("K1a"), P("CH")])
    n.op(P("EE"), "add", [P("EV"), P("NC")])                                  # max(e, 1)
    n.op(P("C"), "cmp", [P("MG")], thr=INF)                                   # inf or nan
    n.op(P("N"), "cmp", [P("MG")], thr=INF + 1)                               # nan


def build_n1(fmt, rounding="rne"):
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    bias = (1 << (E - 1)) - 1
    INF = ((1 << E) - 1) << m
    n = npl.Net()
    n.mask = (1 << W) - 1
    _operand(n, "A", fmt)
    _operand(n, "B", fmt)
    n.op("PRD", "mul", ["A.SIG", "B.SIG"])
    n.op("O.PV", "relay", ["PRD"], addon=shl(W - 2 * S))
    n.op("ZP", "cmp", ["PRD"], thr=1)                                         # the product is not zero (an inf / nan has a nonzero significand, so only a zero operand makes it zero)
    n.op("KZ", "const", const=1)
    n.op("ZA", "sub", ["KZ", "ZP"])                                            # some operand is zero
    n.op("ES", "add", ["A.EE", "B.EE"])
    n.op("KE", "const", const=(-(bias - 1)) & ((1 << W) - 1))
    n.op("E1", "add", ["ES", "KE"])
    n.op("E1a", "relay", ["E1"])                                              # a copy of E1: E1 itself has two inputs, so only two faces for outputs
    n.op("C1", "cmp", ["E1a"], thr=1)
    n.op("K1c", "const", const=1)
    n.op("NE", "sub", ["K1c", "E1a"])
    n.op("K1d", "const", const=1)
    n.op("UR", "sub", ["K1d", "C1"])
    n.op("DD", "mul", ["NE", "UR"])
    n.op("O.D", "relay", ["DD"])
    n.op("XE", "add", ["E1a", "DD"])
    n.op("O.EXPIN", "relay", ["XE"])
    # the sign: bit 0 of the sum of the two sign bits (a mask by two shifts)
    n.op("XS", "add", ["A.SG", "B.SG"])
    n.op("SH", "relay", ["XS"], addon=shl(W - 1))
    n.op("SGN", "relay", ["SH"], addon=shr(W - 1))
    n.op("O.SGR", "relay", ["SGN"])
    n.op("O.SGF", "relay", ["SGN"])
    n.op("ZSH", "relay", ["SGN"], addon=shl(m + E))
    # the special values: spec = an inf / nan input; nan = a nan input, or (an inf / nan input) with a zero operand
    n.op("CSb", "relay", ["B.C"])                                              # one relay later than A.C, so the two do not arrive together
    n.op("CS", "add", ["A.C", "CSb"])
    n.op("SPC", "cmp", ["CS"], thr=1)
    n.op("O.SPEC", "relay", ["SPC"])
    n.op("NS1", "add", ["A.N", "B.N"])
    n.op("IZ", "mul", ["SPC", "ZA"])
    n.op("NS3", "add", ["NS1", "IZ"])
    n.op("NF", "cmp", ["NS3"], thr=1)
    n.op("NQ", "relay", ["NF"], addon=shl(m - 1))
    n.op("KIZ", "const", const=INF)
    n.op("Z1", "add", ["ZSH", "KIZ"])
    n.op("ZW", "add", ["Z1", "NQ"])
    n.op("O.ZW", "relay", ["ZW"])
    return n


MAP = """
.  .    A.EE  A.NC A.K1a .    .  .  .  .  .  .  .  .  .
.  A.SG A.EV  A.CH A.HD  A.Hx .  .  .  .  .  .  .  .  .
.  A.X  A.ML  A.FL A.F   A.SIG .  .  .  .  .  .  .  .  .
.  .    A.MG  A.N  .     .    .  .  .  .  .  .  .  .  .
.  .    A.C   .    .     .    .  .  .  .  .  .  .  .  .
.  .    .     .    .     .    .  .  .  .  .  .  .  .  .
.  .    .     .    .     .    .  .  .  .  .  .  .  .  .
.  .    B.C   .    .     .    .  .  .  .  .  .  .  .  .
.  .    B.MG  B.N  .     .    .  .  .  .  .  .  .  .  .
.  B.X  B.ML  B.FL B.F   B.SIG .  .  .  .  .  .  .  .  .
.  B.SG B.EV  B.CH B.HD  B.Hx .  .  .  .  .  .  .  .  .
.  .    B.EE  B.NC B.K1a .    .  .  .  .  .  .  .  .  .
"""


def place(g, fmt, name, r0, c0, rows=None, **kw):
    n = build_n1(fmt)
    return n, tp.place_map(g, name, n, (rows or MAP).strip("\n").split("\n"), r0, c0, **kw)


A_LOCAL = {"EE": (0, 2), "NC": (0, 3), "K1a": (0, 4), "SG": (1, 1), "EV": (1, 2), "CH": (1, 3), "HD": (1, 4), "Hx": (1, 5),
           "X": (2, 1), "ML": (2, 2), "FL": (2, 3), "F": (2, 4), "SIG": (2, 5), "MG": (3, 2), "N": (3, 3), "C": (4, 2)}


def operand_fixed(top=2, flip=15):
    fx = {}
    for k, (r, c) in A_LOCAL.items():
        fx["A." + k] = (top + r, c)
        fx["B." + k] = (flip - (top + r), c)
    return fx


def place_auto(g, fmt, name, r0, c0, seed=1, iters=60000, rows=26, cols=50, pitch=3, retries=0, rounding="rne"):
    n = build_n1(fmt, rounding)
    fx = operand_fixed()
    pos = tp.autoplace(n, fx, rows, cols, seed=seed, iters=iters, free_rect=(0, 8, rows - 2, cols - 4), pitch=pitch)
    allpos = dict(fx)
    allpos.update(pos)
    res = tp.place_map(g, name, n, [], r0, c0, extra=allpos, retries=retries)
    return n, allpos, res



SEEDS = (1, 5, 6, 7, 8, 9, 10, 11, 12)


def fp_mul_tight(g, fmt, name="MUL", rounding="rne", pads=None, seed=None):
    """The multiplier with a TIGHT front block (N1); the rest as fp_mul_v1. Returns (entries {a, b}, exits {R}, consts, placed)."""
    import fp_assembler_v1 as fa
    import fp_mul_v1 as fm
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    pads = pads or {}
    fal = fa.FpFormat(fmt.name + ".al", 2 * S, E, W)
    sn = W - (fal.Ka + 1)
    fnr = fa.FpFormat(fmt.name + ".nr", sn, E, W)
    low = sn + 1 - S
    consts, placed = {}, []
    last = None
    for sd in ([seed] if seed else SEEDS):
        snap = (dict(g.nodes), list(g.links), dict(g.routes), dict(g.minuend), dict(g.crossed), g._relay)
        try:
            n1, allpos, (nm1, c1, lanes1) = place_auto(g, fmt, f"{name}.N1", 2, 2, seed=sd, rounding=rounding)
            break
        except Exception as e:                       # a layout that cannot be routed: undo and try the next seed
            last = e
            g.nodes.clear(); g.nodes.update(snap[0]); g.links[:] = snap[1]; g.routes.clear(); g.routes.update(snap[2])
            g.minuend.clear(); g.minuend.update(snap[3]); g.crossed.clear(); g.crossed.update(snap[4]); g._relay = snap[5]
    else:
        raise last
    consts.update(c1)
    edge = max(c for _, c in (g.pos(q) for q in g.nodes)) + 8
    al = fa.align_sticky(g, fal, f"{name}.AL", 2, edge)
    consts.update(al.consts)
    edge2 = edge + al.extent[1] + 4
    nr = fa.normalise_chain_clamped(g, fnr, f"{name}.NR", 2, edge2)
    consts.update(nr.consts)
    edge3 = edge2 + nr.extent[1] + 6
    n3 = fm.build_n3(nr.exits["NORM"], al.exits["STK"])
    nm3, c3, lanes3, rest3, map3 = npl.place_net(g, f"{name}.N3", n3, {nr.exits["NORM"], al.exits["STK"]}, 2, edge3 + 4, edge3, pads.get("N3"))
    consts.update(c3)
    placed.append((f"{name}.N3", map3))
    edge4 = max(c for _, c in (g.pos(q) for q in g.nodes)) + 8
    rnd = fa.round_mode(g, fmt, rounding, f"{name}.RND", 2, edge4, low=low)
    consts.update(rnd.consts)
    edge5 = edge4 + rnd.extent[1] + 6
    n2 = fm.build_n2(fmt, rounding, rnd.exits["OUT"], nr.exits["EXPOUT"], nm1["O.SGF"], nm1["O.SPEC"], nm1["O.ZW"])
    ext2 = {rnd.exits["OUT"], nr.exits["EXPOUT"], nm1["O.SGF"], nm1["O.SPEC"], nm1["O.ZW"]}
    nm2, c2, lanes2, rest2, map2 = npl.place_net(g, f"{name}.N2", n2, ext2, 2, edge5 + 4, edge5, pads.get("N2"))
    consts.update(c2)
    placed.append((f"{name}.N2", map2))
    nets = [(nm1["O.PV"], al.entries["V"]), (nm1["O.D"], al.entries["D"]), (al.exits["OUT"], nr.entries["V"]), (nm1["O.EXPIN"], nr.entries["EXPIN"]),
            (nm3["O.X"], rnd.entries["X"])]
    if "SGN" in rnd.entries:
        nets.append((nm1["O.SGR"], rnd.entries["SGN"]))
    kw = {"spread": True}
    allnets = [(a, b, kw) for a, b in lanes3 + lanes2] + [(a, b, kw) for a, b in nets]
    g.route_nets(allnets)
    for rr in (rest3, rest2):
        rr()
    return {"a": nm1["A.X"], "b": nm1["B.X"]}, {"R": nm2["F"]}, consts, placed
