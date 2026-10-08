"""tools/ot_w2_v1.py -- ledger #1033: the 1D WASSERSTEIN-2 DISTANCE between two discrete distributions, built from flex cells as a FIXED network
(after Mirauta et al., "Robust blind unmixing", arXiv:2610.04091, section 4.1; notes in docs/references/mirauta_2026_robust_blind_unmixing.md).

Inputs: two SORTED signatures of n Diracs each, integer positions x and integer weights w, both totalling T.  Output: S = T * W2^2, exact (an integer).

The paper computes the optimal 1D plan with the north-west corner walk, a loop whose next step depends on the data. Its result is the same as MERGING the two sorted lists of
cumulative weights, and a merge is a fixed comparator network, so it can be built from cells:
  * breakpoints: mu's cumulative weights F_mu[0..n-2] and nu's F_nu[0..n-2] (each list sorted because the weights are >= 0), each padded to n with the total T;
  * every breakpoint carries ONE signed payload: mu's step in position, x_mu[i+1] - x_mu[i], or minus nu's, -(x_nu[j+1] - x_nu[j]);
  * an odd-even merge network (Batcher) sorts the 2n breakpoints, each compare-exchange moving key and payload together:
        d = a - b ; s = [d >= 1] ; min = a - d*s ; max = b + d*s     (and the same select for the payload)
  * on the merged segments (t_{k-1}, t_k]:  D_k = (x_mu[0] - x_nu[0]) + the payloads before k  ( = Q_mu - Q_nu on that segment, no indexing needed),
        S = sum_k (t_k - t_{k-1}) * D_k^2      (prefix sums, multiplies, an adder tree).
Everything is 32-bit integer arithmetic; with positions < 2^8 and T <= 2^8, S < 2^24.

`w2_ref` is the merge formula in plain Python; `w2_nwca` is an independent reference: the north-west corner algorithm itself (Algorithm 5 of the paper)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netplace_v1 as npl  # noqa: E402

M32 = 0xFFFFFFFF


def w2_nwca(xm, wm, xn, wn):
    """T * W2^2 by the north-west corner algorithm on sorted signatures (the paper's Algorithm 5): walk both, move the smaller remaining mass, pay mass * distance^2."""
    i = j = 0
    sm, sn = wm[0], wn[0]
    cost = 0
    while i < len(wm) and j < len(wn):
        p = min(sm, sn)
        cost += p * (xm[i] - xn[j]) ** 2
        sm -= p
        sn -= p
        if sm == 0:
            i += 1
            if i < len(wm):
                sm = wm[i]
        if sn == 0:
            j += 1
            if j < len(wn):
                sn = wn[j]
    return cost


def w2_ref(xm, wm, xn, wn):
    """The same value by the merge formula the cells use (breakpoints with payloads, sorted, then prefix sums)."""
    T = sum(wm)
    assert sum(wn) == T, "both signatures must have the same total weight"
    ev, f = [], 0
    for i in range(len(wm) - 1):
        f += wm[i]
        ev.append((f, xm[i + 1] - xm[i]))
    f = 0
    for j in range(len(wn) - 1):
        f += wn[j]
        ev.append((f, -(xn[j + 1] - xn[j])))
    ev.sort(key=lambda e: e[0])
    s, prev, d = 0, 0, xm[0] - xn[0]
    for t, e in ev + [(T, 0)]:
        s += (t - prev) * d * d
        prev, d = t, d + e
    return s


def merge_pairs(n2):
    """Batcher's odd-even MERGE of two sorted halves of an n2-long list (n2 a power of two): the compare-exchange pairs (i, j), i < j, min to i."""
    out = []

    def merge(lo, n, r):
        step = r * 2
        if step < n:
            merge(lo, n, step)
            merge(lo + r, n, step)
            out.extend((i, i + r) for i in range(lo + r, lo + n - r, step))
        else:
            out.append((lo, lo + r))
    merge(0, n2, 1)
    return out


NEG1 = M32                                                                   # -1 as a 32-bit word: a - b is built as a + (-1) * b


def _neg(net, name, src):
    """(-1) * src: a multiplier with a constant -1 beside it. The engine has NO subtract: every two-input op is an add or a multiply, so operand ORDER never
    matters (FlexGrid takes a same-tick pair one operand at a time, which is exact for add and multiply)."""
    net.op(f"{name}.K", "const", const=NEG1)
    return net.op(name, "mul", [src, f"{name}.K"])


def front_net(side, n, T):
    """One signature's front: entries X0..X{n-1}, W0..W{n-2}; exits the breakpoint keys O.F*, their payloads O.P*, the first position O.X0 and the pad (key T, payload 0)."""
    net = npl.Net()
    for i in range(n):
        net.op(f"X{i}", "relay", [])
    for i in range(n - 1):
        net.op(f"W{i}", "relay", [])
    for i in range(n):                                                       # mu uses -x[i] for i < n-1, nu uses -x[i] for i > 0
        if (side == "M" and i < n - 1) or (side == "N" and i > 0):
            _neg(net, f"NX{i}", f"X{i}")
    prev = None
    for i in range(n - 1):
        f = f"F{i}"
        net.op(f, "relay" if i == 0 else "add", ["W0"] if i == 0 else [prev, f"W{i}"])
        prev = f
        if side == "M":
            net.op(f"P{i}", "add", [f"X{i + 1}", f"NX{i}"])                 # x[i+1] - x[i]
        else:
            net.op(f"P{i}", "add", [f"X{i}", f"NX{i + 1}"])                 # -(x[i+1] - x[i])
        net.op(f"O.F{i}", "relay", [f])
        net.op(f"O.P{i}", "relay", [f"P{i}"])
    net.op("O.X0", "relay", ["X0"])
    net.op("KT", "const", const=T)                                           # the pad: key T, payload 0 (its segment has no length)
    net.op("O.KT", "relay", ["KT"])
    net.op("KZ", "const", const=0)
    net.op("O.KZ", "relay", ["KZ"])
    outs = [f"O.F{i}" for i in range(n - 1)] + [f"O.P{i}" for i in range(n - 1)] + ["O.X0", "O.KT", "O.KZ"]
    return net, [f"X{i}" for i in range(n)] + [f"W{i}" for i in range(n - 1)], outs


def ce_net():
    """One compare-exchange on (key, payload) pairs: d = ka - kb, s = [d >= 1], min = ka - d*s, max = kb + d*s, the payloads selected by the same s."""
    net = npl.Net()
    for e in ("KA", "KB", "PA", "PB"):
        net.op(e, "relay", [])
    _neg(net, "NKB", "KB")
    net.op("D", "add", ["KA", "NKB"])                    # d = ka - kb
    net.op("S", "cmp", ["D"], thr=1)                     # s = [ka > kb]
    net.op("M", "mul", ["D", "S"])
    _neg(net, "NM", "M")
    net.op("LO", "add", ["KA", "NM"])                    # min key = ka - d*s
    net.op("HI", "add", ["KB", "M"])                     # max key = kb + d*s
    _neg(net, "NPB", "PB")
    net.op("E", "add", ["PA", "NPB"])
    net.op("F", "mul", ["E", "S"])
    _neg(net, "NF", "F")
    net.op("PL", "add", ["PA", "NF"])                    # the payload of the min key
    net.op("PH", "add", ["PB", "F"])
    return net, ["KA", "KB", "PA", "PB"], ["LO", "HI", "PL", "PH"]


def seg_net(first, last):
    """One merged segment k: its length DT = K_k - K_{k-1} (K_0 alone for the first), the running difference D_k (D_0 = XM - XN in the first), TM = DT * D_k^2.
    Hands on K_k and D_{k+1} = D_k + E_k to the next segment."""
    net = npl.Net()
    ents = ["KA"] + ([] if first else ["KP", "DIN"]) + ([] if last else ["E"]) + (["XM", "XN"] if first else [])
    for e in ents:
        net.op(e, "relay", [])
    if first:
        _neg(net, "NXN", "XN")
        net.op("DIN", "add", ["XM", "NXN"])
        net.op("DT", "relay", ["KA"])
    else:
        _neg(net, "NKP", "KP")
        net.op("DT", "add", ["KA", "NKP"])
    net.op("DC", "relay", ["DIN"])                                       # copies: the square needs the value on two inputs
    net.op("DD", "relay", ["DC"])
    net.op("SQ", "mul", ["DC", "DD"])
    net.op("TM", "mul", ["DT", "SQ"])
    outs = ["TM"]
    if not last:
        net.op("KN", "relay", ["KA"])
        net.op("DOUT", "add", ["DIN", "E"])
        outs += ["KN", "DOUT"]
    return net, ents, outs


def sum_net(m):
    """An adder tree over m terms T0..T{m-1}."""
    net = npl.Net()
    terms = [net.op(f"T{i}", "relay", []) for i in range(m)]
    ents = list(terms)
    lvl = 0
    while len(terms) > 1:
        nxt = [net.op(f"S{lvl}.{a // 2}", "add", [terms[a], terms[a + 1]]) for a in range(0, len(terms) - 1, 2)]
        if len(terms) % 2:
            nxt.append(terms[-1])
        terms, lvl = nxt, lvl + 1
    net.op("O.W2", "relay", [terms[0]])
    return net, ents, ["O.W2"]


def merge_stages(n2):
    """The merge network's compare-exchanges grouped into stages (a stage only uses lanes the previous stages have finished with)."""
    depth, out = [0] * n2, []
    for a, b in merge_pairs(n2):
        st = max(depth[a], depth[b])
        while len(out) <= st:
            out.append([])
        out[st].append((a, b))
        depth[a] = depth[b] = st + 1
    return out


def port_names(n):
    return [f"XM{i}" for i in range(n)] + [f"WM{i}" for i in range(n - 1)] + [f"XN{i}" for i in range(n)] + [f"WN{i}" for i in range(n - 1)]


def _apply_pads(net, pads):
    """Delay an op's input by k relays: {(op, source op): k}. How the engine fixes an operand tie or a subtract whose minuend would arrive second (see w2_grid)."""
    for (op, src), k in sorted(pads.items()):
        prev = src
        for j in range(k):
            prev = net.op(f"{op}~{src}~{j}", "relay", [prev])
        net.cells[op]["srcs"] = [prev if x == src else x for x in net.cells[op]["srcs"]]


def _tile(g, net, name, entries, outs, r0, c0, rows=40, cols=60, pads=None, info=None):
    """Place a small netlist tightly on a scratch grid and move it onto g with its top-left at (r0, c0). Returns ({op: grid name}, consts, (height, width)).
    `pads` delays chosen inputs (see _apply_pads); `info` collects grid name -> (tile, op, netlist) for the padding loop."""
    import fp_mul_tight_v1 as fmt1
    _apply_pads(net, (pads or {}).get(name, {}))
    last = None
    for k in range(4):                                     # a tile that does not fit tightly (e.g. after padding) gets a larger scratch area and a wider pitch
        sg = fmt1._scratch(g, rows + 20 * k, cols + 30 * k)
        try:
            names, consts, _ = fmt1.place_net_tight(sg, net, name, 2, 2, entries, rows + 20 * k, cols + 30 * k, pitch=3 + (k >= 2), gap=2, outs=outs)
            break
        except Exception as e:
            last = e
    else:
        raise last
    rmin, rmax, cmin, cmax = fmt1._bbox(sg)
    fmt1._transplant(g, sg, r0, c0)
    g._relay = max(g._relay, sg._relay)
    if info is not None:
        for op, gn in names.items():
            info[gn] = (name, op, net)
    return names, consts, (rmax - rmin + 1, cmax - cmin + 1)


def _route_batches(g, batches):
    """Route the joins between tiles, batch after batch (one batch per column of tiles). Every port in the whole engine is kept clear (the square west of each tile
    input, east of each tile output), so no route can wall off a port that a later route needs; each join may use only its own two."""
    def face(cell, dc):
        r, c = g.pos(cell)
        return (r, c + dc)
    guard = {face(b, -1) for nets in batches for _, b in nets} | {face(a, +1) for nets in batches for a, _ in nets}
    for nets in batches:
        g.route_nets([(a, b, {"spread": True, "avoid": tuple(guard - {face(b, -1), face(a, +1)})}) for a, b in nets])


def w2_engine(g, n=4, T=64, name="W2", r0=2, c0=2, gap=10, pads=None, info=None):
    """Place the engine on grid g as tiles (a front per signature, one tile per compare-exchange, a back) joined by routes.
    Returns (entries {port: cell}, exits {"W2": cell}, consts)."""
    n2 = 2 * n
    consts, nets, batches = {}, [], []
    ent = {}
    # fronts, stacked in the first column
    fronts, row, wmax = {}, r0, 0
    for side in ("M", "N"):
        net, ents, outs = front_net(side, n, T)
        nm, cs, (h, w) = _tile(g, net, f"{name}.F{side}", ents, outs, row, c0, pads=pads, info=info)
        consts.update(cs)
        fronts[side] = nm
        for i in range(n):
            ent[f"X{side}{i}"] = nm[f"X{i}"]
        for i in range(n - 1):
            ent[f"W{side}{i}"] = nm[f"W{i}"]
        row += h + gap
        wmax = max(wmax, w)
    # the lanes entering the merge: mu's breakpoints and pad, then nu's
    lanes = []
    for side in ("M", "N"):
        f = fronts[side]
        lanes += [(f[f"O.F{i}"], f[f"O.P{i}"]) for i in range(n - 1)] + [(f["O.KT"], f["O.KZ"])]
    col = c0 + wmax + gap
    for si, stage in enumerate(merge_stages(n2)):
        row, wmax = r0, 0
        for ci, (a, b) in enumerate(stage):
            net, ents, outs = ce_net()
            nm, cs, (h, w) = _tile(g, net, f"{name}.C{si}.{ci}", ents, outs, row, col, pads=pads, info=info)
            consts.update(cs)
            (ka, pa), (kb, pb) = lanes[a], lanes[b]
            nets += [(ka, nm["KA"]), (kb, nm["KB"]), (pa, nm["PA"]), (pb, nm["PB"])]
            lanes[a], lanes[b] = (nm["LO"], nm["PL"]), (nm["HI"], nm["PH"])
            row += h + gap
            wmax = max(wmax, w)
        batches.append(nets)                                               # each column's lanes are one batch: small batches route quickly
        nets = []
        col += wmax + gap
    row, wmax, prev, terms = r0, 0, None, []
    for i in range(n2):                                   # the segments, one tile each, in a column
        net, ents, outs = seg_net(i == 0, i == n2 - 1)
        nm, cs, (h, w) = _tile(g, net, f"{name}.G{i}", ents, outs, row, col, pads=pads, info=info)
        consts.update(cs)
        nets.append((lanes[i][0], nm["KA"]))
        if i < n2 - 1:
            nets.append((lanes[i][1], nm["E"]))
        if i == 0:
            nets += [(fronts["M"]["O.X0"], nm["XM"]), (fronts["N"]["O.X0"], nm["XN"])]
        else:
            nets += [(prev["KN"], nm["KP"]), (prev["DOUT"], nm["DIN"])]
        terms.append(nm["TM"])
        prev = nm
        row += h + gap
        wmax = max(wmax, w)
    batches.append(nets)
    nets = []
    col += wmax + gap
    net, ents, outs = sum_net(n2)
    nm, cs, _ = _tile(g, net, f"{name}.SUM", ents, outs, r0, col, pads=pads, info=info)
    consts.update(cs)
    nets += [(t, nm[f"T{i}"]) for i, t in enumerate(terms)]
    batches.append(nets)
    _route_batches(g, batches)
    return ent, {"W2": nm["O.W2"]}, consts


def w2_grid(n=4, T=64, rows=300, cols=400, name="W2"):
    """Build the engine on a fresh grid. Returns (grid, entries, exits, consts). The engine has no subtract, so there is no operand ORDER to keep; operand ties
    (two words reaching an add or a multiply on the same tick) are exact in FlexGrid. The flex generator still refuses such ties (it needs an operand order for
    every pair core), so the generated-RTL check waits on that (see the module notes and ledger #1033)."""
    from flex_layout_v1 import Grid
    g = Grid(rows=rows, cols=cols)
    ent, ex, consts = w2_engine(g, n, T, name=name)
    return g, ent, ex, consts
