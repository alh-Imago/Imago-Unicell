"""tools/flow2d_flex_v1.py -- WORK IN PROGRESS (not yet in the ledger): a 2x2 sheet over 2 steps is bit-exact in the RTL; the 3x3 sheet does not route yet (tile exits walled in; pair spacing fix `pw = wa + pgap + wb + pgap` still to be applied and tested). Was to be ledger #1034: FLOW DYNAMICS IN TWO DIMENSIONS (Alan: "try the 2d mechanics"): the 1-D medium of #1033 (tools/flow_flex_v1.py) on an R x Q sheet of cells, four neighbours each.
Per step every cell hands on, conservatively (closed edges):
  * STANDARD flow: d = C >> k to EACH existing neighbour (north, south, west, east);
  * INSTRUCTED flow: two command words per cell per step, aE and aS: it hands  pE = (C*aE) >> s  to its EAST neighbour and  pS = (C*aS) >> s  to its SOUTH neighbour.
  keep  nb/2^k + (aE + aS)/2^s <= 1  (nb = number of neighbours, at most 4; k = s = 3 -> aE + aS <= 4).
Each (cell, step) is two tiles, A (hand-offs from C and the commands) and B (adds what arrives), set side by side as a PAIR; the pairs of one stage form an R x Q sheet, the next stage is the next sheet to the east
(the amount lane from a cell to the same cell one step later is the long one).  `flow2d_ref` is the exact integer reference."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_add_v1 as fadd  # noqa: E402
import netplace_v1 as npl  # noqa: E402
import fp_mul_tight_v1 as fmt1  # noqa: E402

shl, shr = fadd.shl, fadd.shr


class EnclosedError(AssertionError):
    pass


def _open_face(g, at, cell, prefer):
    """The free square beside `cell` that opens onto the biggest free region (a flood fill, capped): a stub must not sit in a pocket the tile's own relays enclose (#1034)."""
    r_, c_ = g.pos(cell)
    best = None
    for rank, (dr, dc) in enumerate(prefer):
        q = (r_ + dr, c_ + dc)
        if q in at or not (0 <= q[0] < g.rows and 0 <= q[1] < g.cols):
            continue
        seen, todo = {q}, [q]
        while todo and len(seen) < 150:
            a, b = todo.pop()
            for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if (x, y) not in seen and (x, y) not in at and 0 <= x < g.rows and 0 <= y < g.cols:
                    seen.add((x, y))
                    todo.append((x, y))
        key = (len(seen), -rank)
        if best is None or key > best[0]:
            best = (key, q)
    if best is None or best[0][0] < 120:
        raise EnclosedError(f"{cell}: every free face opens onto a closed pocket")
    return best[1]


def _place_pinned(g, n, name, entries, outs, rows, cols, pitch, seed):
    """Like fp_mul_tight_v1.place_net_tight, but the EXITS are pinned too: entries down the west column, exits down the east column, the rest annealed between (#1034). An exit left to the annealer could end up
    inside the tile, walled in by its own relays, with no way out for its lane."""
    import tightplace_v1 as tp
    ccol = ((cols - 1) // pitch) * pitch
    fixed = {e: (pitch * k, 0) for k, e in enumerate(entries)}
    fixed.update({o: (pitch * k, ccol) for k, o in enumerate(outs)})
    pos = tp.autoplace(n, fixed, rows, cols, seed=seed, free_rect=(0, 2, rows - 1, ccol - 2), pitch=pitch)
    allp = dict(fixed)
    allp.update(pos)
    names, cs, _ = tp.place_map(g, name, n, [], 2, 2, extra=allp, ports={**{e: "W" for e in entries}, **{o: "E" for o in outs}})
    return names, cs


def flow2d_ref(c0, cmds, k=3, s=3):
    """c0: R x Q amounts; cmds[t] = (aE, aS), each R x Q (aE of the last column and aS of the last row are ignored). -> list of sheets after each step."""
    R, Q = len(c0), len(c0[0])
    c, out = [list(r) for r in c0], []
    for aE, aS in cmds:
        d = [[x >> k for x in r] for r in c]
        pE = [[(c[i][j] * aE[i][j]) >> s if j < Q - 1 else 0 for j in range(Q)] for i in range(R)]
        pS = [[(c[i][j] * aS[i][j]) >> s if i < R - 1 else 0 for j in range(Q)] for i in range(R)]
        n = [[0] * Q for _ in range(R)]
        for i in range(R):
            for j in range(Q):
                nb = (i > 0) + (i < R - 1) + (j > 0) + (j < Q - 1)
                v = c[i][j] - nb * d[i][j] - pE[i][j] - pS[i][j]
                if i > 0:
                    v += d[i - 1][j] + pS[i - 1][j]
                if i < R - 1:
                    v += d[i + 1][j]
                if j > 0:
                    v += d[i][j - 1] + pE[i][j - 1]
                if j < Q - 1:
                    v += d[i][j + 1]
                n[i][j] = v
        c = n
        out.append([list(r) for r in c])
    return out


def _nbrs(i, j, R, Q):
    return [x for x, ok in (("N", i > 0), ("S", i < R - 1), ("W", j > 0), ("E", j < Q - 1)) if ok]


def build_a2(i, j, R, Q, k, s):
    n = npl.Net()
    nbs = _nbrs(i, j, R, Q)
    n.op("C", "relay", [])
    n.op("Cb", "relay", ["C"])                                     # (a cell has four faces: C feeds D, Cx and Cb; Cb feeds Cy and Ce)
    n.op("D", "relay", ["C"], addon=shr(k))
    # D feeds its own total and up to two exit relays Da / Db (each with up to two exits)
    ex_d = [f"O.d{x}" for x in nbs]
    groups = [ex_d[:2], ex_d[2:]]
    own = "D"
    for gi, grp in enumerate(groups):
        if grp:
            n.op(f"D{'ab'[gi]}", "relay", ["D"])
            for e in grp:
                n.op(e, "relay", [f"D{'ab'[gi]}"])
    nb = len(nbs)
    if nb == 1:
        tot = "D"
    elif nb in (2, 4):
        n.op("Dm", "relay", ["D"], addon=shl(1 if nb == 2 else 2))
        tot = "Dm"
    else:
        n.op("Dm", "relay", ["D"], addon=shl(1))
        n.op("Dm2", "relay", ["Dm"])                               # (a spacer: arrives after Db, so the add below has no tie)
        n.op("Dt", "add", ["Dm2", "Db"])
        tot = "Dt"
    if j < Q - 1:
        n.op("AE", "relay", [])
        n.op("Cx", "relay", ["C"])
        n.op("MpE", "mul", ["Cx", "AE"])
        n.op("PE", "relay", ["MpE"], addon=shr(s))
        n.op("O.PE", "relay", ["PE"])
        n.op("T1", "add", [tot, "PE"])
        tot = "T1"
    if i < R - 1:
        n.op("AS", "relay", [])
        n.op("Cy", "relay", ["Cb"])
        n.op("MpS", "mul", ["Cy", "AS"])
        n.op("PS", "relay", ["MpS"], addon=shr(s))
        n.op("O.PS", "relay", ["PS"])
        n.op("T2", "add", [tot, "PS"])
        tot = "T2"
    n.op("Ox", "relay", [tot])
    n.op("KM", "const", const=(1 << 32) - 1)
    n.op("Ng", "mul", ["Ox", "KM"])                                # minus the total leaving; added (an add needs no operand order)
    n.op("Ce", "relay", ["Cb"])
    n.op("E", "add", ["Ce", "Ng"])
    n.op("O.E", "relay", ["E"])
    return n


def build_b2(i, j, R, Q):
    n = npl.Net()
    n.op("E", "relay", [])
    ins = [f"from{x}" for x in _nbrs(i, j, R, Q)]
    if j > 0:
        ins.append("pW")
    if i > 0:
        ins.append("pN")
    for x in ins:
        n.op(x, "relay", [])
    last = ins[0]
    for q, x in enumerate(ins[1:]):
        n.op(f"S{q}", "add", [last, x])
        last = f"S{q}"
    n.op("Cn", "add", ["E", last])
    n.op("O.C", "relay", ["Cn"])
    n.op("O.Obs", "relay", ["Cn"])
    return n


def flow2d_medium(g, R, Q, T, k=3, s=3, name="F2", r0=3, c0=2, rh=22, rgap=40, wa=30, wb=14, pgap=30, sgap=60, pitch=3):
    """Returns (entries {('C', i, j): cell, ('AE'|'AS', i, j, t): command entry}, exits {(i, j, t): amount after step t}, consts)."""
    ent, ex, consts, A, B = {}, {}, {}, {}, {}
    col = c0
    pw = wa + pgap + wb + pgap

    def place(n, entries, outs, nm, row, c, rows, cols):
        snap, last = fmt1._snapshot(g), None
        snap_c = dict(consts)
        for sd in fmt1.SEEDS:                                      # a tile whose exit or entry is closed in by its own relays is re-placed with the next seed (#1034)
            try:
                sg = fmt1._scratch(g)
                names, cs = _place_pinned(sg, n, nm, entries, outs, rows, cols, pitch, sd)
                fmt1._transplant(g, sg, row, c, flip_h=False)
                names = dict(names)
                at = g.at()
                for o in outs:                                     # a one-relay STUB on an open face of every exit that feeds another tile
                    if o == "O.Obs":
                        continue
                    r2, c2 = _open_face(g, at, names[o], ((0, 1), (1, 0), (-1, 0), (0, -1)))
                    sn = names[o] + ".stub"
                    g.add(sn, r2, c2)
                    g.link(names[o], sn)
                    at[(r2, c2)] = sn
                    names[o] = sn
                for e in entries:                                  # ... and a stub in front of every entry that a lane feeds; command entries are injected, no lane
                    if e in ("AE", "AS"):
                        continue
                    r2, c2 = _open_face(g, at, names[e], ((0, -1), (1, 0), (-1, 0), (0, 1)))
                    sn = names[e] + ".in"
                    g.add(sn, r2, c2)
                    g.link(sn, names[e])
                    at[(r2, c2)] = sn
                    names[e + ".lane"] = sn
                consts.update(cs)
                return names
            except (EnclosedError, fmt1.tp.LayoutError) as e_:
                last = e_
                fmt1._restore(g, snap)
                consts.clear()
                consts.update(snap_c)
        raise last
    for t in range(T):
        nets_ab, nets_cc = [], []
        for i in range(R):
            for j in range(Q):
                row, ca = r0 + i * (rh + rgap), col + j * pw
                nbs = _nbrs(i, j, R, Q)
                ents = ["C"] + (["AE"] if j < Q - 1 else []) + (["AS"] if i < R - 1 else [])
                outs = ["O.E"] + [f"O.d{x}" for x in nbs] + (["O.PE"] if j < Q - 1 else []) + (["O.PS"] if i < R - 1 else [])
                A[(i, j, t)] = place(build_a2(i, j, R, Q, k, s), ents, outs, f"{name}.A{i}_{j}_{t}", row, ca, rh, wa - 4)
                if t == 0:
                    ent[("C", i, j)] = A[(i, j, t)]["C.lane"]
                else:
                    nets_cc.append((B[(i, j, t - 1)]["O.C"], A[(i, j, t)]["C.lane"], {"spread": True}))
                if j < Q - 1:
                    ent[("AE", i, j, t)] = A[(i, j, t)]["AE"]
                if i < R - 1:
                    ent[("AS", i, j, t)] = A[(i, j, t)]["AS"]
                bents = ["E"] + [f"from{x}" for x in nbs] + (["pW"] if j > 0 else []) + (["pN"] if i > 0 else [])
                B[(i, j, t)] = place(build_b2(i, j, R, Q), bents, ["O.C", "O.Obs"], f"{name}.B{i}_{j}_{t}", row, ca + wa + pgap, rh, wb)
                ex[(i, j, t)] = B[(i, j, t)]["O.Obs"]
                g.route(A[(i, j, t)]["O.E"], B[(i, j, t)]["E.lane"], spread=True)          # the pair's own lane first, while both ends are still open (#1034)
        if nets_cc:
            g.route_nets(nets_cc)
        for i in range(R):
            for j in range(Q):
                for x, (di, dj) in (("N", (-1, 0)), ("S", (1, 0)), ("W", (0, -1)), ("E", (0, 1))):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < R and 0 <= nj < Q:
                        opp = {"N": "S", "S": "N", "W": "E", "E": "W"}[x]
                        nets_ab.append((A[(ni, nj, t)][f"O.d{opp}"], B[(i, j, t)][f"from{x}.lane"], {"spread": True}))
                if j > 0:
                    nets_ab.append((A[(i, j - 1, t)]["O.PE"], B[(i, j, t)]["pW.lane"], {"spread": True}))
                if i > 0:
                    nets_ab.append((A[(i - 1, j, t)]["O.PS"], B[(i, j, t)]["pN.lane"], {"spread": True}))
        g.route_nets(nets_ab)
        col += Q * pw + sgap
    return ent, ex, consts
