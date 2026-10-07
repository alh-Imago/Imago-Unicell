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
    n.op("ZSH", "relay", ["SGN"], addon=shl(m + E))
    # the special values: spec = an inf / nan input; nan = a nan input, or (an inf / nan input) with a zero operand
    n.op("CSb", "relay", ["B.C"])                                              # one relay later than A.C, so the two do not arrive together
    n.op("CS", "add", ["A.C", "CSb"])
    n.op("SPC", "cmp", ["CS"], thr=1)
    n.op("SPK", "relay", ["SPC"], addon=shl(m + E + 1))                        # the flags ride in ONE word: result | spec << (m+E+1) | sign << (m+E+2) (one long lane instead of three)
    n.op("NS1", "add", ["A.N", "B.N"])
    n.op("IZ", "mul", ["SPC", "ZA"])
    n.op("NS3", "add", ["NS1", "IZ"])
    n.op("NF", "cmp", ["NS3"], thr=1)
    n.op("NQ", "relay", ["NF"], addon=shl(m - 1))
    n.op("KIZ", "const", const=INF)
    n.op("Z1", "add", ["ZSH", "KIZ"])
    n.op("ZW", "add", ["Z1", "NQ"])
    n.op("SGK", "relay", ["SGN"], addon=shl(m + E + 2))
    n.op("PK1", "add", ["ZW", "SPK"])
    n.op("O.PK", "add", ["PK1", "SGK"])
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
    ports = {"A.X": "W", "B.X": "W", **{o: "E" for o in n.order if o.startswith("O.")}}
    res = tp.place_map(g, name, n, [], r0, c0, extra=allpos, retries=retries, ports=ports)
    return n, allpos, res



SEEDS = (1, 5, 6, 7, 8, 9, 10, 11, 12)


def _snapshot(g):
    import copy
    return copy.deepcopy((g.nodes, g.links, g.routes, g.minuend, g.crossed, g._relay))


def _restore(g, snap):
    import copy
    nodes, links, routes, minuend, crossed, rel = copy.deepcopy(snap)
    g.nodes.clear(); g.nodes.update(nodes)
    g.links[:] = links
    g.routes.clear(); g.routes.update(routes)
    g.minuend.clear(); g.minuend.update(minuend)
    g.crossed.clear(); g.crossed.update(crossed)
    g._relay = rel


def place_net_tight(g, n, name, r0, c0, entries, rows, cols, pitch=3, seeds=SEEDS, gap=3, outs=()):
    """Tightly place netlist `n` (ledger #1013/#1014): the `entries` (ops with no sources: the lanes from other blocks arrive there) sit in column 0, one per `pitch` rows; every other op is annealed
    onto a pitch lattice east of them and routed with lane stubs. Returns (names, consts, lanes)."""
    snap, last = _snapshot(g), None
    fixed = {e: (pitch * k, 0) for k, e in enumerate(entries)}
    for sd in seeds:
        try:
            pos = tp.autoplace(n, fixed, rows, cols, seed=sd, free_rect=(0, gap, rows - 1, cols - 1), pitch=pitch)
            allp = dict(fixed)
            allp.update(pos)
            return tp.place_map(g, name, n, [], r0, c0, extra=allp, ports={**{e: "W" for e in entries}, **{o: "E" for o in outs}})
        except Exception as e:                       # a layout that cannot be routed: undo and try the next seed
            last = e
            _restore(g, snap)
    raise last


def build_n3_tight():
    import fp_mul_v1 as fm
    n = npl.Net()
    n.op("SH1", "relay", [], addon=shl(1))
    n.op("STKR", "relay", [])
    n.op("O.X", "add", ["SH1", "STKR"])
    return n


def build_n2_tight(fmt, rounding):
    import fp_mul_v1 as fm
    n = fm.build_n2(fmt, rounding, "RO", "EXR", "SGX", "SPR", "ZWR")
    E, m, W = fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    Fw = m + E + 1
    for c in ("RO", "EXR"):
        n.cells[c]["srcs"] = []
    mk = lambda kind, srcs, addon=None: {"kind": kind, "srcs": srcs, "thr": None, "addon": addon, "const": None}
    n.cells["PKR"] = mk("relay", [])                                            # the packed flags word
    n.cells["SPS"] = mk("relay", ["PKR"], shl(W - Fw - 1))                      # spec -> the top bit
    n.cells["ZSX"] = mk("relay", ["PKR"], shl(W - Fw))                          # the special value (the low Fw bits) -> the top
    n.cells["SGX"] = mk("relay", ["PKR"], shr(Fw + 1))                          # the sign
    n.cells["SPR"] = mk("relay", ["SPS"], shr(W - 1))
    n.cells["ZWR"] = mk("relay", ["ZSX"], shr(W - Fw))
    n.order = ["PKR", "SPS", "ZSX"] + [c for c in n.order if c not in ("PKR", "SPS", "ZSX")]
    n.cells["MAGc"] = {"kind": "relay", "srcs": ["MAG"], "thr": None, "addon": None, "const": None}        # MAG has five connections: a copy takes two of its users (a cell has four faces)
    n.order.insert(n.order.index("MAG") + 1, "MAGc")
    for c in ("OV", "NM"):
        n.cells[c]["srcs"] = ["MAGc" if x == "MAG" else x for x in n.cells[c]["srcs"]]
    return n


def fp_mul_tight(g, fmt, name="MUL", rounding="rne", pads=None, seed=None):
    """The multiplier with TIGHT N1, N3 and N2 blocks; AL / NR / RND as fp_mul_v1. Returns (entries {a, b}, exits {R}, consts, placed)."""
    import fp_assembler_v1 as fa
    import fp_mul_v1 as fm
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    fal = fa.FpFormat(fmt.name + ".al", 2 * S, E, W)
    sn = W - (fal.Ka + 1)
    fnr = fa.FpFormat(fmt.name + ".nr", sn, E, W)
    low = sn + 1 - S
    consts, placed = {}, []
    snap, last = _snapshot(g), None
    for sd in ([seed] if seed else SEEDS):
        try:
            n1, allpos, (nm1, c1, lanes1) = place_auto(g, fmt, f"{name}.N1", 2, 2, seed=sd, rounding=rounding)
            break
        except Exception as e:
            last = e
            _restore(g, snap)
    else:
        raise last
    consts.update(c1)
    edge = max(c for _, c in (g.pos(q) for q in g.nodes)) + 8
    al = fa.align_sticky(g, fal, f"{name}.AL", 2, edge)
    consts.update(al.consts)
    kw = {"spread": True}
    g.route_nets([(nm1["O.D"], al.entries["D"], kw), (nm1["O.PV"], al.entries["V"], kw)])          # the lanes into a block are laid as soon as it stands (before other lanes wall it in)
    edge2 = edge + al.extent[1] + 4
    nr = fa.normalise_chain_clamped(g, fnr, f"{name}.NR", 2, edge2)
    consts.update(nr.consts)
    g.route_nets([(nm1["O.EXPIN"], nr.entries["EXPIN"], kw), (al.exits["OUT"], nr.entries["V"], kw)])
    edge3 = edge2 + nr.extent[1] + 6
    nm3, c3, _ = place_net_tight(g, build_n3_tight(), f"{name}.N3", 2, edge3 + 4, ["SH1", "STKR"], 6, 8, pitch=2, gap=1, outs=["O.X"])
    consts.update(c3)
    edge4 = max(c for _, c in (g.pos(q) for q in g.nodes)) + 8
    rnd = fa.round_mode(g, fmt, rounding, f"{name}.RND", 2, edge4, low=low)
    consts.update(rnd.consts)
    edge5 = edge4 + rnd.extent[1] + 6
    n2 = build_n2_tight(fmt, rounding)
    nm2, c2, _ = place_net_tight(g, n2, f"{name}.N2", 2, edge5 + 4, ["RO", "EXR", "PKR"], 18, 36, outs=["F"])
    consts.update(c2)
    nets = [(nr.exits["NORM"], nm3["SH1"]), (al.exits["STK"], nm3["STKR"]), (nm3["O.X"], rnd.entries["X"]),
            (rnd.exits["OUT"], nm2["RO"]), (nr.exits["EXPOUT"], nm2["EXR"]), (nm1["O.PK"], nm2["PKR"])]
    if "SGN" in rnd.entries:
        nets.append((nm1["O.SGR"], rnd.entries["SGN"]))
    g.route_nets([(a, b, {"spread": True}) for a, b in nets])
    return {"a": nm1["A.X"], "b": nm1["B.X"]}, {"R": nm2["F"]}, consts, placed


# ---------------------------------------------------------------------------------------------------------------------------------------------
# #1016: the U-shape. N1 and AL run left to right on the top band; NR, N3, RND and N2 run right to left on a band UNDER them, so N2 ends up beside N1
# (the packed-flags lane is a few squares instead of the length of the whole strip). A block is built on a scratch grid, mirrored left-right if it flows leftwards, and moved onto the main grid.
def _bbox(sg):
    rs = [n["r"] for n in sg.nodes.values()]
    cs = [n["c"] for n in sg.nodes.values()]
    return min(rs), max(rs), min(cs), max(cs)


def _transplant(g, sg, r0, c0, flip_h=False):
    """Move everything on scratch grid `sg` onto `g` with its top-left bounding-box corner at (r0, c0); `flip_h` mirrors it left-right first. Returns (height, width)."""
    import copy
    rmin, rmax, cmin, cmax = _bbox(sg)
    at = g.at()
    new = {}
    for k, n in sg.nodes.items():
        n2 = copy.deepcopy(n)
        n2["r"] = n["r"] - rmin + r0
        n2["c"] = (cmax - n["c"] if flip_h else n["c"] - cmin) + c0
        if (n2["r"], n2["c"]) in at or not (0 <= n2["r"] < g.rows and 0 <= n2["c"] < g.cols):
            raise tp.LayoutError(f"{k}: square ({n2['r']},{n2['c']}) is taken or outside the grid")
        new[k] = n2
    g.nodes.update(new)
    g.links.extend(sg.links)
    g.routes.update(sg.routes)
    g.minuend.update(sg.minuend)
    g.crossed.update(sg.crossed)
    g._relay = max(g._relay, sg._relay)
    return rmax - rmin + 1, cmax - cmin + 1


def _scratch(g, rows=60, cols=200):
    from flex_layout_v1 import Grid
    sg = Grid(rows=rows, cols=cols)
    sg._relay = g._relay
    return sg


def fp_mul_tight_u(g, fmt, name="MUL", rounding="rne", gap=6, seed=None):
    """The multiplier laid out as a U (see above). Returns (entries {a, b}, exits {R}, consts, placed)."""
    import fp_assembler_v1 as fa
    import fp_mul_v1 as fm
    S, E, m, W = fmt.sig_bits, fmt.exp_bits, fmt.sig_bits - 1, fmt.word
    fal = fa.FpFormat(fmt.name + ".al", 2 * S, E, W)
    sn = W - (fal.Ka + 1)
    fnr = fa.FpFormat(fmt.name + ".nr", sn, E, W)
    low = sn + 1 - S
    consts = {}
    snap, last = _snapshot(g), None
    for sd in ([seed] if seed else SEEDS):
        try:
            n1, allpos, (nm1, c1, lanes1) = place_auto(g, fmt, f"{name}.N1", 2, 2, seed=sd, rounding=rounding)
            break
        except Exception as e:
            last = e
            _restore(g, snap)
    else:
        raise last
    consts.update(c1)
    r1, _, _, c1max = _bbox(g)
    kw = {"spread": True}
    # ---- top band: AL, flowing right
    sg = _scratch(g)
    al = fa.align_sticky(sg, fal, f"{name}.AL", 0, 0)
    consts.update(al.consts)
    ral = _bbox(sg)
    h_al, w_al = _transplant(g, sg, 2, c1max + gap + 2)
    g.route_nets([(nm1["O.D"], al.entries["D"], kw), (nm1["O.PV"], al.entries["V"], kw)])
    rbot = max(n["r"] for n in g.nodes.values() if True) + gap + 1            # the bottom of N1 / AL and the lanes beside them
    cal_right = max(n["c"] for k, n in g.nodes.items() if k.startswith(f"{name}.AL"))
    # ---- bottom band, built right to left: NR first (its right edge under AL's right end), then N3, RND, N2 to its left
    sg = _scratch(g)
    nr = fa.normalise_chain_clamped(sg, fnr, f"{name}.NR", 0, 0)
    consts.update(nr.consts)
    _, rmaxn, cminn, cmaxn = _bbox(sg)
    wnr = cmaxn - cminn + 1
    c_nr = cal_right - wnr + 1 + 4
    _transplant(g, sg, rbot, c_nr, flip_h=True)
    g.route_nets([(nm1["O.EXPIN"], nr.entries["EXPIN"], kw), (al.exits["OUT"], nr.entries["V"], kw)])
    sg = _scratch(g)
    nm3, c3, _ = place_net_tight(sg, build_n3_tight(), f"{name}.N3", 2, 2, ["SH1", "STKR"], 6, 8, pitch=2, gap=1, outs=["O.X"])
    consts.update(c3)
    _, _, c3min, c3max = _bbox(sg)
    w3 = c3max - c3min + 1
    c_n3 = c_nr - gap - w3
    _transplant(g, sg, rbot, c_n3, flip_h=True)
    sg = _scratch(g)
    rnd = fa.round_mode(sg, fmt, rounding, f"{name}.RND", 0, 0, low=low)
    consts.update(rnd.consts)
    _, _, crmin, crmax = _bbox(sg)
    wrd = crmax - crmin + 1
    c_rd = c_n3 - gap - wrd
    _transplant(g, sg, rbot, c_rd, flip_h=True)
    sg = _scratch(g)
    n2 = build_n2_tight(fmt, rounding)
    nm2, c2, _ = place_net_tight(sg, n2, f"{name}.N2", 2, 2, ["RO", "EXR", "PKR"], 18, 36, outs=["F"])
    consts.update(c2)
    _, _, c2min, c2max = _bbox(sg)
    w2 = c2max - c2min + 1
    c_n2 = c_rd - gap - w2
    if c_n2 < 0:
        raise tp.LayoutError(f"the bottom band does not fit: needs {-c_n2} more columns on the left")
    _transplant(g, sg, rbot, c_n2, flip_h=True)
    nets = [(nr.exits["NORM"], nm3["SH1"]), (al.exits["STK"], nm3["STKR"]), (nm3["O.X"], rnd.entries["X"]),
            (rnd.exits["OUT"], nm2["RO"]), (nr.exits["EXPOUT"], nm2["EXR"]), (nm1["O.PK"], nm2["PKR"])]
    if "SGN" in rnd.entries:
        nets.append((nm1["O.SGR"], rnd.entries["SGN"]))
    g.route_nets([(a, b, kw) for a, b in nets])
    return {"a": nm1["A.X"], "b": nm1["B.X"]}, {"R": nm2["F"]}, consts, []
