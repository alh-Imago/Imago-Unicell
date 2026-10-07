"""tools/netplace_v1.py -- ledger #1008: place a small NETLIST of flex cells on a Grid by Alan's rule ("each path its own simple line, joined one at a time, a cross wherever two lines meet").
Extracted from the special-value block of fp_add_v1 (#1001) and made general, so the multiplier (fp_mul_v1) can be written as netlists instead of hand-placed cells."""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fa_add  # noqa: E402
from flex_layout_v1 import LayoutError  # noqa: E402

M32 = 0xFFFFFFFF
Net = fa_add._Net


def _place_net(g, name, n, ext, row0, col0, gatecol, pads=None):
    pads = pads or {}
    """(ledger #1008: the special-value placer of fp_add_v1, made general: any netlist, any number of lanes from outside, the cells' grid names returned, the lanes from outside LEFT to the caller
    (`lane_nets`: (source, gate) pairs for route_nets), the gate column a parameter.)
    Alan's recipe (6 Oct 2026): every path is its own simple line, joined one at a time, a CROSS wherever two lines meet.
      * the netlist is cut into chains (`_chains`); a chain is one ROW, its cells joined by a straight wire along the row (the primary wires);
      * every cell has its OWN column (3 apart), so a vertical lane from a cell can never meet another cell;
      * every other connection is a three-leg line: out of the source's top or bottom port, vertically to a horizontal TRACK row in the gutter between two chains, along the track, vertically into
        the target's top or bottom port. The track rows are allocated first-fit (no two runs overlap), the gutters are as tall as their tracks;
      * where a line meets another it passes through the other's straight relay: a crossing tile (`Grid.route_line`).
    No search, no rip-up: the geometry is computed, then every line is laid. Lanes from outside (the operand taps, the result and the exponent) come to a gate at the west edge of their row."""
    for _ in range(12):                                      # a connection between two cells of the SAME row (not neighbours) has no gutter to run in: give it a relay of its own, which lands on another row
        pos0, chains = fa_add._chains(n, ext)
        rowof = {c: r for r, ch in enumerate(chains) for c in ch}
        prim_ = {(ch[k], ch[k + 1]) for ch in chains for k in range(len(ch) - 1)}
        fix = [(q, c) for c in rowof for q in n.cells[c]["srcs"] if q in rowof and (q, c) not in prim_ and rowof[q] == rowof[c]]
        if not fix:
            break
        for q, c in fix:
            nm_ = f"{q}~{c}"
            n.op(nm_, "relay", [q])
            n.cells[c]["srcs"] = [nm_ if x == q else x for x in n.cells[c]["srcs"]]
    pos0, chains = fa_add._chains(n, ext)
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
            raise LayoutError(f"special-value net {u} -> {v}: no gutter between its two ports (rows {i}, {j}; out {out_side[e]}, in {in_side[e]})")
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
    consts = {}
    for q, c in constin:
        r_, c_ = sq(c, const_side[(q, c)])
        g.add(names[q], r_, c_, preload=n.cells[q]["const"] & getattr(n, "mask", M32))
        g.link(names[q], names[c])
        consts[names[q]] = n.cells[q]["const"] & getattr(n, "mask", M32)
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
        g.add(gates[(q, c)], R[rowidx[c]], gatecol)
    for c in n.order:
        if n.cells[c]["kind"] == "sub":
            q = n.cells[c]["srcs"][0]
            g.minuend[names[c]] = q if q in ext else names[q]
    for (q, c), gate in gates.items():
        g.route_line(gate, names[c])                         # the last stretch along the row is reserved first, so no lane can arrive over it

    def route_rest():
        for u, v in sorted(prim):
            g.route_line(names[u], names[v])
        for e in sorted(sec, key=lambda e: (gut[e], track[e])):
            chain_ = [stub_o[e], *corner[e], stub_i[e]]
            for a_, b_ in zip(chain_, chain_[1:]):
                g.route_line(a_, b_)
    lane_nets = [(q, gate) for (q, c), gate in gates.items()]
    nets_of = {stub_i[e]: e for e in sec}
    return names, consts, lane_nets, route_rest, nets_of


def place_net(g, name, n, ext, row0, col0, gatecol, pads=None):
    """Place the netlist `n` (see `_place_net`). A cell has two ports, north and south, and a port is EITHER one input OR the start of up to three outputs: a cell that gets a lane from below and
    sends lanes below too has no way out -- it gets a RELAY right after it, and its consumers read the relay (one more hop on those lanes; the layout is computed again)."""
    import re
    for _ in range(40):
        try:
            return _place_net(g, name, n, ext, row0, col0, gatecol, pads)
        except LayoutError as e:
            m_ = re.search(r"net (\S+) -> (\S+): no gutter", str(e)) or re.search(r"cell (\S+): (?:no free port for an output|two outputs|\d+ outputs)", str(e))
            if not m_:
                raise
            u = m_.group(1)
            r_ = f"{u}'"
            while r_ in n.cells:
                r_ += "'"
            n.op(r_, "relay", [u])
            for c, k in n.cells.items():
                if c != r_:
                    k["srcs"] = [r_ if x == u else x for x in k["srcs"]]
    raise LayoutError(f"place_net {name}: port conflicts could not be resolved")
