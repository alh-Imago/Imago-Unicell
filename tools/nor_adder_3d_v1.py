#!/usr/bin/env python3
"""tools/nor_adder_3d_v1.py -- the NOR-built 32-bit adder (same word-level Kogge-Stone network as tools/nor_adder_v1.py) laid out in the SIX-neighbour toy grid of nano/experimental_3d_nor_v2.py (ledger #1036 addendum 50).

VM ONLY, a thought experiment (see the header of that model for its scope). What it measures: how many cells and how many grid squares the same netlist needs when a cell has six neighbours instead of four.
    python3 tools/nor_adder_3d_v1.py            search layouts, print the best (stage tiles placed by formula, the rest by a free-square search; simulated-annealing placement was tried first and could not be routed)
    python3 tools/nor_adder_3d_v1.py --measure  write docs/measurements/nor_adder_3d_v1.json
    python3 tools/nor_adder_3d_v1.py --check    exit 1 if that file differs from a fresh run"""
import collections
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "nano"))
import experimental_3d_nor_v2 as m3  # noqa: E402

JSON = os.path.join(HERE, "..", "docs", "measurements", "nor_adder_3d_v1.json")
KS = (1, 2, 4, 8, 16)


def netlist(ks=KS):
    """cells {name: (kind, gate, shift, left)}; nets [(src, dst)]. No fan-out relays: a cell can feed up to five neighbours here."""
    c, n = {}, []
    for nm in ("A", "B", "E"):
        c[nm] = ("relay", None, 0, True)
    c["G0"], c["P0"] = ("gate", "AND", 0, True), ("gate", "XOR", 0, True)
    n += [("A", "G0"), ("B", "G0"), ("A", "P0"), ("B", "P0")]
    c["P0f"] = ("relay", None, 0, True)       # P0 would otherwise use all six faces (two operands in, Ps, Pn, T and the sum out): one fan-out relay
    n += [("P0", "P0f")]
    g, p = "G0", "P0f"
    for i, k in enumerate(ks):
        s, last = f"s{k}", i == len(ks) - 1
        c[f"Gs{s}"], c[f"T{s}"], c[f"Gn{s}"] = ("relay", None, k, True), ("gate", "AND", 0, True), ("gate", "OR", 0, True)
        n += [(g, f"Gs{s}"), (p, f"T{s}"), (f"Gs{s}", f"T{s}"), (g, f"Gn{s}"), (f"T{s}", f"Gn{s}")]
        if not last:
            c[f"Ps{s}"], c[f"Pn{s}"] = ("relay", None, k, True), ("gate", "AND", 0, True)
            c[f"q{s}"] = ("relay", None, 0, True)          # three cells that feed each other cannot be neighbours on a cubic lattice either (it is two-coloured): one relay on the shifted edge
            n += [(p, f"Ps{s}"), (p, f"Pn{s}"), (f"Ps{s}", f"q{s}"), (f"q{s}", f"Pn{s}")]
            p = f"Pn{s}"
        g = f"Gn{s}"
    c["C"], c["S"] = ("relay", None, 1, True), ("gate", "XOR", 0, True)
    n += [(g, "C"), ("P0f", "S"), ("C", "S"), ("S", "E")]
    return c, n


def _nb(p):
    return [(p[0] + dr, p[1] + dc, p[2] + dl) for dr, dc, dl in m3.DELTA.values()]


LAST_FAIL = None


def _fail(tag, a, b):
    global LAST_FAIL
    LAST_FAIL = (tag, a, b)
    return None


def route(cells, nets, pos, box, rounds=200, seed=1):
    rng = random.Random(seed)
    for k in range(rounds):
        r = _route_once(cells, nets, pos, box, rng if k else None)
        if r is not None:
            return r
    return None


def _route_once(cells, nets, pos, box, rng):
    """Link neighbours directly; every other net gets a relay chain. Each end of such a net first RESERVES its own free face (the closest one to the other end), so no chain can wall a cell in;
    then the two reserved squares are joined by a shortest path through free squares. Returns (relay squares, links) or None."""
    R, C, L = box
    inbox = lambda q: 0 <= q[0] < R and 0 <= q[1] < C and 0 <= q[2] < L
    dist = lambda p, q: sum(abs(x - y) for x, y in zip(p, q))
    occupied = set(pos.values())
    links, reserved, ends = [], set(), []
    longn = []
    for a, b in nets:
        if dist(pos[a], pos[b]) == 1:
            links.append((pos[a], pos[b]))
        else:
            longn.append((a, b))
    longn.sort(key=lambda n: dist(pos[n[0]], pos[n[1]]))
    if rng:
        rng.shuffle(longn)
    pick = (lambda cand, key: min(cand, key=key)) if rng is None else (lambda cand, key: sorted(cand, key=lambda q: (key(q) + rng.random() * 2.5))[0])
    for a, b in longn:
        pa, pb = pos[a], pos[b]
        fa = [q for q in _nb(pa) if inbox(q) and q not in occupied and q not in reserved]
        fb = [q for q in _nb(pb) if inbox(q) and q not in occupied and q not in reserved]
        common = [q for q in fa if q in fb]
        if common:
            t = common[0] if rng is None else rng.choice(common)
            reserved.add(t)
            ends.append((a, b, t, t))
            continue
        if not fa or not fb:
            return _fail("1", a, b)
        ta = pick(fa, lambda q: dist(q, pb))
        reserved.add(ta)
        fb = [q for q in fb if q != ta]
        if not fb:
            return _fail("2", a, b)
        tb = pick(fb, lambda q: dist(q, pa))
        reserved.add(tb)
        ends.append((a, b, ta, tb))
    used = occupied | reserved
    relays = list(reserved)
    for a, b, ta, tb in ends:
        links.append((pos[a], ta))
        links.append((tb, pos[b]))
        if ta == tb:
            continue
        prev, q, found = {ta: None}, collections.deque([ta]), False
        while q and not found:
            cur = q.popleft()
            for nx in _nb(cur):
                if nx == tb:
                    prev[nx] = cur
                    found = True
                    break
                if inbox(nx) and nx not in used and nx not in prev:
                    prev[nx] = cur
                    q.append(nx)
        if not found:
            return _fail("3", a, b)
        path, x = [], tb
        while x is not None:
            path.append(x)
            x = prev[x]
        path.reverse()
        for u, v in zip(path, path[1:]):
            links.append((u, v))
        for sq in path[1:-1]:
            used.add(sq)
            relays.append(sq)
    return relays, links


def check(g, pos, n=200):
    rng = random.Random(5)
    M = m3.M32
    vs = [(0, 0), (M, 1), (1, M), (M, M), (0x7FFFFFFF, 1), (0x55555555, 0xAAAAAAAA)] + [((1 << i) - 1, 1) for i in range(1, 33)] + [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(n)]
    ticks = set()
    for a, b in vs:
        t, v = g.run({pos["A"]: a, pos["B"]: b}, pos["E"])
        if v != (a + b) & M:
            return None
        ticks.add(t)
    return ticks


ORIENT = [((0, 1, 0), (1, 0, 0), (0, 0, 1)), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
          ((0, 0, 1), (0, 1, 0), (1, 0, 0)), ((1, 0, 0), (0, 0, 1), (0, 1, 0)), ((0, 0, 1), (1, 0, 0), (0, 1, 0))]


def _add(*vs):
    return tuple(sum(x) for x in zip(*vs))


def stacked_positions(perms, ks=KS):
    """Stage tile in 3D. With g = the previous Gn and (a, b, c) three orthogonal unit steps:  Gs = g+a, Gn = g+b, T = g+a+b, p = g+a+b+c, Ps = p+a, q = p+a+b, Pn = p+b.
    Every link inside the tile is a direct neighbour link, and the next stage starts at g' = Gn, p' = Pn (needs a'+b'+c' = a+b+c, so any permutation of the axes will do)."""
    pos = {}
    g = (4, 4, 4)
    pos["G0"] = g
    p = None
    for i, k in enumerate(ks):
        a, b, c = ORIENT[perms[i]]
        s = f"s{k}"
        pos[f"Gs{s}"], pos[f"Gn{s}"], pos[f"T{s}"] = _add(g, a), _add(g, b), _add(g, a, b)
        pp = _add(g, a, b, c)
        if i == 0:
            pos["P0f"] = pp
        if i < len(ks) - 1:
            pos[f"Ps{s}"], pos[f"q{s}"], pos[f"Pn{s}"] = _add(pp, a), _add(pp, a, b), _add(pp, b)
        g = pos[f"Gn{s}"]
    return pos


def build_stacked(perms, seed=1):
    """Stage tiles placed by formula; the cells at the ends (A, B, G0, P0, C, S, E) and every net that is not a direct neighbour link are placed by a free-square search."""
    cells, nets = netlist()
    pos = stacked_positions(perms)
    if len(set(pos.values())) != len(pos):
        return None
    rng = random.Random(seed)
    # the free-form cells: choose the free square nearest to what they connect to
    placed = dict(pos)
    adj = collections.defaultdict(list)
    for a_, b_ in nets:
        adj[a_].append(b_)
        adj[b_].append(a_)
    occ = set(placed.values())
    for nme in ("P0", "A", "B", "C", "S", "E"):
        tgt = [placed[o] for o in adj[nme] if o in placed]
        if not tgt:
            tgt = [placed["G0"]]
        cand = [q for q in _all_squares(placed) if q not in occ]
        q = min(cand, key=lambda q: sum(sum(abs(x - y) for x, y in zip(q, t)) for t in tgt) + rng.random() * 0.5)
        placed[nme] = q
        occ.add(q)
    return placed, cells, nets


def _all_squares(placed, margin=3):
    lo = [min(p[i] for p in placed.values()) - margin for i in range(3)]
    hi = [max(p[i] for p in placed.values()) + margin for i in range(3)]
    return [(r, c, l) for r in range(lo[0], hi[0] + 1) for c in range(lo[1], hi[1] + 1) for l in range(lo[2], hi[2] + 1)]


def build_stacked_grid(perms, seed=1, margin=2):
    r = build_stacked(perms, seed)
    if r is None:
        return None
    placed, cells, nets = r
    lo = [min(p[i] for p in placed.values()) - margin for i in range(3)]
    placed = {n: tuple(p[i] - lo[i] for i in range(3)) for n, p in placed.items()}
    box = tuple(max(p[i] for p in placed.values()) + 1 + margin for i in range(3))
    rt = route(cells, nets, placed, box, seed=seed)
    if rt is None:
        return None
    relays, links = rt
    g = m3.Grid3()
    for n, (kind, gate, sh, left) in cells.items():
        g.add(placed[n], m3.Cell3(kind, gate, sh, left))
    for sq in relays:
        g.add(sq, m3.Cell3("relay"))
    for a, b in links:
        g.link(a, b)
    return g, placed


def bbox_volume(g):
    pts = list(g.cells)
    return math.prod(max(p[i] for p in pts) - min(p[i] for p in pts) + 1 for i in range(3))


PERMS = ((0, 5, 0, 5, 0), (0, 5, 0, 5, 1))        # the only two orientation sequences of the stage tile that do not collide (found by trying all 6^4)


def search(seeds=range(1, 61)):
    best = None
    for perms in PERMS:
        for seed in seeds:
            r = build_stacked_grid(perms, seed)
            if r is None:
                continue
            g, pos = r
            key = (len(g.cells), bbox_volume(g), perms, seed)
            if best is None or key < best:
                if check(g, pos, 40) is not None:
                    best = key
    return best


def measure():
    cells_n, vol, perms, seed = search()
    g, pos = build_stacked_grid(perms, seed)
    ticks = check(g, pos, 200)
    assert ticks is not None
    gates = sum(1 for c in g.cells.values() if c.kind == "gate")
    shifts = sum(1 for c in g.cells.values() if c.kind == "relay" and c.shift)
    return {"what": "32-bit add mod 2^32, same word-level network as nor_adder_v1, six-neighbour toy grid (VM only, no RTL, no flow control)", "orientations": list(perms), "seed": seed, "cells": cells_n,
            "gates": gates, "shift_cells": shifts, "plain_relays": cells_n - gates - shifts, "bounding_box_squares": vol, "ticks": sorted(ticks), "vectors_checked": 6 + 32 + 200}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("--measure", "--check"):
        print(json.dumps(measure(), indent=1))
        sys.exit(0)
    res = measure()
    if sys.argv[1] == "--measure":
        json.dump(res, open(JSON, "w"), indent=1, sort_keys=True)
        print(json.dumps(res, indent=1))
    else:
        ok = json.load(open(JSON)) == json.loads(json.dumps(res))
        print("nor_adder_3d_v1.json matches a fresh measurement" if ok else "nor_adder_3d_v1.json is OUT OF DATE")
        sys.exit(0 if ok else 1)
