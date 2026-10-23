"""experimental/three_d/placer3d_v1.py -- an AUTOMATIC placer and router for the six-face toy grid (ledger #1313). VM ONLY, an exploration.

REAL, HONEST SCOPE. Same as the rest of this folder: no 3D RTL, no card; the target is the toy model `experimental_3d_nor_v2.py` (relay cells with a shift add-on, gate cells AND / OR / XOR / NOR / NAND / XNOR, six faces,
one tick per cell, no flow control). This tool takes any NETLIST of such cells and lays it out by itself, then PROVES the layout by running it: every exit cell must give the same word as a direct evaluation of the
netlist, for many random inputs. (The earlier 3D adder layout was placed by a hand-derived formula; an automatic annealing placement on a dense grid was tried in #1036 addendum 50 and was never routable. This is a different
construction, described below, and it is measured against that hand-placed layout, not assumed to beat it.)

HOW IT WORKS
  1. Check the netlist (no loops; a gate has exactly two inputs; a relay at most one; a cell's inputs + outputs fit its six faces).
  2. SPREAD: cells go on a lattice with one empty square between neighbours in every direction (rows and columns always; layers too when three or more are allowed), so every cell has all six faces free and
     there are corridors everywhere. The positions are found by simulated annealing on total wire length.
  3. ROUTE: every net gets a chain of relay cells through free squares (shortest path by Dijkstra, squares next to other cells cost more so nobody is walled in; nets are re-ordered and retried; if routing keeps failing
     the lattice is made roomier). In this toy a cell sends only through the faces it is told to, so neighbouring cells do not interfere; the only rule is that two nets never share a relay square.
  4. COMPACT: a whole plane (a row, a column or a layer) can be deleted when everything in it is a relay that goes straight through it; the two neighbours then touch directly. This is repeated until nothing more goes.
  5. VERIFY by running (see above). A layout that fails verification is refused, never returned.

    python3 experimental/three_d/placer3d_v1.py --example adder --layers 3 --out adder_auto.3d.json
    python3 experimental/three_d/placer3d_v1.py --netlist my_net.json --layers 2 --out my.3d.json
A netlist file is {"format": "imago-3d-netlist", "version": 1, "cells": [{"name", "kind": "relay"|"gate", "gate", "shift", "left"}], "nets": [["from", "to"], ...]}.
"""
import argparse
import heapq
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(REPO, "tools"), os.path.join(REPO, "nano"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import experimental_3d_nor_v2 as m3  # noqa: E402
import composer3d_v1 as c3  # noqa: E402  (the Design class: the placed result is a composer design)

M32 = m3.M32
NETLIST_FORMAT = "imago-3d-netlist"
DIRS = [(d, m3.DELTA[d]) for d in range(6)]


class PlaceError(ValueError):
    """The netlist is not placeable as given, or no verified layout was found."""


# ------------------------------------------------------------------------------------------------------------------------------ netlists
def netlist_doc(cells, nets):
    """cells {name: (kind, gate, shift, left)} and nets [(a, b)] -> the file form."""
    return {"format": NETLIST_FORMAT, "version": 1,
            "cells": [{"name": n, "kind": k, "gate": g, "shift": s, "left": bool(l)} for n, (k, g, s, l) in cells.items()],
            "nets": [[a, b] for a, b in nets]}


def parse_netlist(doc):
    """File form -> (cells {name: (kind, gate, shift, left)}, nets). Raises PlaceError with a plain reason."""
    if not isinstance(doc, dict) or doc.get("format") != NETLIST_FORMAT or doc.get("version") != 1:
        raise PlaceError("not an %s version 1 file" % NETLIST_FORMAT)
    cells, nets = {}, []
    try:
        for c in doc["cells"]:
            name = str(c["name"])
            if name in cells:
                raise PlaceError("cell name %r appears twice" % name)
            kind, gate, shift, left = c3.Design._clean(c.get("kind", "relay"), c.get("gate"), c.get("shift", 0), c.get("left", True))
            if kind == "gate" and shift:
                raise PlaceError("gate %s has a shift; a gate has none in this model" % name)
            if not c3.NAME_RE.match(name):
                raise PlaceError("cell name %r is not valid" % name)
            cells[name] = (kind, gate, shift, left)
        for a, b in doc["nets"]:
            nets.append((str(a), str(b)))
    except c3.DesignError as e:
        raise PlaceError(str(e))
    except (KeyError, TypeError, ValueError) as e:
        raise PlaceError("bad netlist: %s" % e)
    return cells, nets


def check_netlist(cells, nets):
    if not cells:
        raise PlaceError("the netlist has no cells")
    seen = set()
    ins = {n: [] for n in cells}
    outs = {n: [] for n in cells}
    for a, b in nets:
        if a not in cells or b not in cells:
            raise PlaceError("net %s -> %s names a cell that does not exist" % (a, b))
        if a == b:
            raise PlaceError("net %s -> %s joins a cell to itself" % (a, b))
        if (a, b) in seen:
            raise PlaceError("net %s -> %s is listed twice" % (a, b))
        seen.add((a, b))
        outs[a].append(b)
        ins[b].append(a)
    for n, (kind, gate, shift, left) in cells.items():
        if kind == "gate" and len(ins[n]) != 2:
            raise PlaceError("gate %s has %d input(s); it needs exactly two" % (n, len(ins[n])))
        if kind == "relay" and len(ins[n]) > 1:
            raise PlaceError("relay %s has %d inputs; a relay passes one word (use a gate to combine)" % (n, len(ins[n])))
        if len(ins[n]) + len(outs[n]) > 6:
            raise PlaceError("cell %s has %d connections but only six faces (add a fan-out relay)" % (n, len(ins[n]) + len(outs[n])))
        if not ins[n] and not outs[n]:
            raise PlaceError("cell %s is not joined to anything" % n)
    # loops
    indeg = {n: len(ins[n]) for n in cells}
    q = [n for n in cells if not indeg[n]]
    order = []
    while q:
        n = q.pop()
        order.append(n)
        for b in outs[n]:
            indeg[b] -= 1
            if not indeg[b]:
                q.append(b)
    if len(order) != len(cells):
        raise PlaceError("the netlist has a loop (%s ...); the placer handles feed-forward netlists" % sorted(n for n in cells if indeg[n])[0])
    return ins, outs, order


def evaluate(cells, ins, order, inputs):
    """Direct evaluation of the netlist with the toy's own operations: {exit name: word}. `inputs` maps each entry cell to a word."""
    val = {}
    for n in order:
        kind, gate, shift, left = cells[n]
        if not ins[n]:
            v = inputs[n] & M32
            val[n] = c3.shifted({"shift": shift, "left": left}, v) if kind == "relay" else v
        elif kind == "relay":
            val[n] = c3.shifted({"shift": shift, "left": left}, val[ins[n][0]])
        else:
            val[n] = m3.GATES[gate](val[ins[n][0]], val[ins[n][1]])
    return val


# ------------------------------------------------------------------------------------------------------------------------------ geometry
def add3(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


def manhattan(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2])


def shape(n, layers, factor):
    """Lattice (rows, cols, cell layers) and the layer spacing for n cells within `layers` layers."""
    sz = 1                                   # dense lattice: neighbouring slots touch, so a net between neighbours needs no relay
    k = max(1, min(layers, math.ceil(n / 10)))
    side = max(2, math.ceil(math.sqrt(factor * n / k)))
    return side, side, k, sz


def anneal(names, nets, R, C, K, sz, rng, steps):
    """Cells -> lattice slots (dense: slot (i, j, k) is the square (1 + i, 1 + j, k)), to shorten wires AND keep every cell's faces free: a net between cells that touch needs no relay, any other net needs a free
    square beside each end, so a cell with many nets must not be walled in by cells it is not joined to."""
    slots = [(i, j, k) for i in range(R) for j in range(C) for k in range(K)]
    order = list(names)
    rng.shuffle(order)
    where = {n: slots[i] for i, n in enumerate(order)}
    at = {s: n for n, s in where.items()}
    nb = {n: [] for n in names}
    for a, b in nets:
        nb[a].append(b)
        nb[b].append(a)
    NB = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

    def wire(n, s):
        t = 0.0
        for m in nb[n]:
            d = manhattan(s, where[m])
            t += max(0, d - 1) + 0.1 * d
        return t

    def pen(c):
        deg = len(nb[c])
        s = where[c]
        blocked = 0
        for d in NB:
            q = (s[0] + d[0], s[1] + d[1], s[2] + d[2])
            if not 0 <= q[2] < K:
                blocked += 1
            else:
                o = at.get(q)
                if o is not None and o not in nb[c]:
                    blocked += 1
        return 4.0 * max(0, min(deg + 1, 6) - (6 - blocked))

    def around(s):
        out = []
        for d in NB:
            o = at.get((s[0] + d[0], s[1] + d[1], s[2] + d[2]))
            if o is not None:
                out.append(o)
        return out

    t0 = 3.0
    for step in range(steps):
        T = t0 * (0.003) ** (step / max(1, steps - 1))
        n = rng.choice(names)
        s = rng.choice(slots)
        o = where[n]
        if s == o:
            continue
        m = at.get(s)
        aff = {n} | set(around(o)) | set(around(s))
        if m:
            aff.add(m)
        before = wire(n, o) + (wire(m, s) if m else 0) + sum(pen(c) for c in aff)
        where[n] = s
        del at[o]
        at[s] = n
        if m:
            where[m] = o
            at[o] = m
        after = wire(n, s) + (wire(m, o) if m else 0) + sum(pen(c) for c in aff)
        d = after - before
        if d <= 0 or rng.random() < math.exp(-d / T):
            continue
        where[n] = o
        at[o] = n
        if m:
            where[m] = s
            at[s] = m
        else:
            del at[s]
    return {n: (1 + s[0], 1 + s[1], s[2]) for n, s in where.items()}


def route_all(pos, nets, box, rng, shuffle, iterations=30):
    """Vertex-disjoint relay chains for every net, by negotiated congestion (rip up and re-route): nets may share squares at first, sharing gets dearer every round, and a square that was fought over keeps a
    memory of it, until no square is used twice. Squares next to cells cost a little more so nobody is walled in. Returns {net: [squares]} (neighbours: []) or None."""
    Rb, Cb, Lb = box
    inbox = lambda q: 0 <= q[0] < Rb and 0 <= q[1] < Cb and 0 <= q[2] < Lb
    cellsq = set(pos.values())
    near = set()
    for p in cellsq:
        for _, d in DIRS:
            near.add(add3(p, d))
    paths = {}
    todo = []
    for a, b in nets:
        if manhattan(pos[a], pos[b]) == 1:        # neighbours: one face, no relay
            paths[(a, b)] = []
        else:
            todo.append((a, b))
    todo.sort(key=lambda e: manhattan(pos[e[0]], pos[e[1]]))
    occ, hist = {}, {}
    pfac = 0.6
    for it in range(iterations if todo else 0):
        order = list(todo)
        if it:
            rng.shuffle(order)
        for e in order:
            for q in paths.get(e, ()):
                occ[q] -= 1
            a, b = e
            pa, pb = pos[a], pos[b]
            goal = {add3(pb, d) for _, d in DIRS}
            heap, best, prev = [], {}, {}
            cost = lambda q: (1.0 + (0.7 if q in near else 0.0)) * (1.0 + hist.get(q, 0.0)) + pfac * occ.get(q, 0)
            for _, d in DIRS:
                q = add3(pa, d)
                if inbox(q) and q not in cellsq:
                    c = cost(q)
                    best[q], prev[q] = c, None
                    heapq.heappush(heap, (c, q))
            end = None
            while heap:
                c, cur = heapq.heappop(heap)
                if c > best.get(cur, 1e18):
                    continue
                if cur in goal:
                    end = cur
                    break
                for _, d in DIRS:
                    nx = add3(cur, d)
                    if not inbox(nx) or nx in cellsq:
                        continue
                    nc = c + cost(nx)
                    if nc < best.get(nx, 1e18):
                        best[nx], prev[nx] = nc, cur
                        heapq.heappush(heap, (nc, nx))
            if end is None:
                return None
            path, x = [], end
            while x is not None:
                path.append(x)
                x = prev[x]
            path.reverse()
            paths[e] = path
            for q in path:
                occ[q] = occ.get(q, 0) + 1
        clash = [q for q, c in occ.items() if c > 1]
        if not clash:
            return paths
        for q in clash:
            hist[q] = hist.get(q, 0.0) + 0.6
        pfac *= 1.4
    return None


def box_of(pos):
    hi = [max(p[i] for p in pos.values()) for i in range(3)]
    return (hi[0] + 2, hi[1] + 2, hi[2] + 1)


def route_retry(pos, nets, rng, rounds=2):
    for r in range(rounds):
        paths = route_all(pos, nets, box_of(pos), rng, shuffle=bool(r))
        if paths is not None:
            return paths
    return None


def relay_count(paths):
    return sum(len(v) for v in paths.values())


def squeeze(pos, nets, paths, rng):
    """Close the gaps between rows / columns / layers of cells one square at a time, re-routing every net after each, keeping a squeeze only if it still routes with no more relays than before."""
    improved = True
    while improved:
        improved = False
        axes = [0, 1, 2]
        rng.shuffle(axes)
        for axis in axes:
            vals = sorted({p[axis] for p in pos.values()})
            for lo, hi in zip(vals, vals[1:]):
                if hi - lo < 2:
                    continue
                trial = {n: tuple(q[i] - (1 if i == axis and q[i] >= hi else 0) for i in range(3)) for n, q in pos.items()}
                tp = route_retry(trial, nets, rng)
                if tp is not None and relay_count(tp) <= relay_count(paths):
                    pos, paths, improved = trial, tp, True
                    break
            if improved:
                break
    return pos, paths


def build_nodes(cells, pos, paths):
    """{square: node dict} with names, kinds and `down` faces, for cells and relay chains."""
    nodes = {}
    for n, p in pos.items():
        kind, gate, shift, left = cells[n]
        nodes[p] = {"name": n, "kind": kind, "gate": gate, "shift": shift, "left": left, "down": set()}
    k = 0
    taken = set(cells)

    def face(a, b):
        return next(f for f, d in DIRS if add3(a, d) == b)

    for (a, b), path in paths.items():
        chain = [pos[a]] + path + [pos[b]]
        for sq in path:
            while True:
                k += 1
                nm = "w_%d" % k
                if nm not in taken:
                    break
            taken.add(nm)
            nodes[sq] = {"name": nm, "kind": "relay", "gate": None, "shift": 0, "left": True, "down": set()}
        for u, v in zip(chain, chain[1:]):
            nodes[u]["down"].add(face(u, v))
    return nodes


def compact(nodes, original):
    """Delete planes that hold only straight-through route relays. `original` = names of netlist cells (never deleted). Returns (nodes, planes removed)."""
    removed = 0
    changed = True
    while changed:
        changed = False
        for axis in (0, 1, 2):
            lo = min(p[axis] for p in nodes)
            hi = max(p[axis] for p in nodes)
            p = lo
            while p <= hi:
                plane = [q for q in nodes if q[axis] == p]
                if plane and all(_straight(nodes, q, axis, original) for q in plane):
                    gone = set(plane)
                    nodes = {(_shift(q, axis) if q[axis] > p else q): n for q, n in nodes.items() if q not in gone}
                    # the faces are unchanged: a face that pointed at a deleted relay now points at what was behind it
                    removed += 1
                    hi -= 1
                    changed = True
                    continue
                p += 1
        # empty planes (nothing on them at all) also close up
        for axis in (0, 1, 2):
            used = sorted({q[axis] for q in nodes})
            remap = {v: i for i, v in enumerate(used)}
            if any(remap[v] != v for v in used):
                nodes = {tuple(remap[q[i]] if i == axis else q[i] for i in range(3)): n for q, n in nodes.items()}
    return nodes, removed


def _shift(q, axis):
    q = list(q)
    q[axis] -= 1
    return tuple(q)


def _straight(nodes, q, axis, original):
    n = nodes[q]
    if n["name"] in original or n["kind"] != "relay" or n["shift"] or len(n["down"]) != 1:
        return False
    (f,) = tuple(n["down"])
    d = m3.DELTA[f]
    if d[axis] == 0:
        return False
    back = tuple(q[i] - d[i] for i in range(3))
    src = nodes.get(back)
    if src is None or m3.OPP[f] is None:
        return False
    senders = [s for s in nodes if f in nodes[s]["down"] and add3(s, d) == q]
    return senders == [back]


# ------------------------------------------------------------------------------------------------------------------------------ verify
def to_grid3(nodes):
    g = m3.Grid3()
    for p, n in nodes.items():
        c = m3.Cell3(n["kind"], n["gate"], n["shift"], n["left"])
        c.down = sorted(n["down"])
        g.add(p, c)
    return g


def verify(nodes, cells, nets, trials=64, seed=7):
    """Run the layout and compare every exit with direct evaluation. Returns {ok, trials, ticks, failed}."""
    ins, outs, order = check_netlist(cells, nets)
    where = {n["name"]: p for p, n in nodes.items()}
    entries = [n for n in cells if not ins[n]]
    exits = [n for n in cells if not outs[n]]
    g = to_grid3(nodes)
    rng = random.Random(seed)
    words = [0, M32, 1, 0x80000000, 0x55555555, 0xAAAAAAAA]
    ticks = set()
    for t in range(trials):
        inp = {n: (rng.choice(words) if t < 12 else rng.getrandbits(32)) for n in entries}
        want = evaluate(cells, ins, order, inp)
        for e in exits:
            tick, got = g.run({where[n]: inp[n] for n in entries}, where[e])
            if got != want[e]:
                return {"ok": False, "trials": t + 1, "ticks": sorted(ticks), "failed": {"exit": e, "inputs": {k: v for k, v in inp.items()}, "got": got, "want": want[e]}}
            ticks.add((e, tick))
    return {"ok": True, "trials": trials, "ticks": sorted({t for _, t in ticks}), "failed": None}


# ------------------------------------------------------------------------------------------------------------------------------ the placer
def place(cells, nets, layers=3, seed=1, tries=40, keep=3, log=None):
    """Return (Design, report). Several verified layouts are found (`keep`) and the one with fewest cells is returned. Raises PlaceError when no verified layout is found."""
    ins, outs, order = check_netlist(cells, nets)
    if not 1 <= layers <= c3.LIMITS["layers"][1]:
        raise PlaceError("layers must be 1 to %d" % c3.LIMITS["layers"][1])
    names = sorted(cells)
    rng = random.Random(seed)
    factor, fails, last = 2.2, 0, None
    found = []
    for attempt in range(1, tries + 1):
        if len(found) >= keep:
            break
        R, C, K, sz = shape(len(names), layers, factor)
        pos = anneal(names, nets, R, C, K, sz, rng, steps=4000 + 400 * len(names))
        box = (R + 2, C + 2, K)
        paths = None
        for r in range(3):
            paths = route_all(pos, nets, box, rng, shuffle=bool(r))
            if paths is not None:
                break
        if paths is None:
            fails += 1
            last = "no disjoint routes in a %dx%dx%d box" % box
            if fails % 3 == 0:
                factor += 0.5
            if log:
                log("attempt %d: %s (factor %.1f)" % (attempt, last, factor))
            continue
        pos, paths = squeeze(pos, nets, paths, rng)
        nodes = build_nodes(cells, pos, paths)
        before = len(nodes)
        nodes, planes = compact(nodes, set(cells))
        res = verify(nodes, cells, nets)
        if not res["ok"]:
            raise PlaceError("internal error: a routed layout failed verification (%s); nothing returned" % res["failed"])
        found.append((len(nodes), attempt, nodes, planes, before, res))
        if log:
            log("attempt %d: routed, %d cells in all" % (attempt, len(nodes)))
    if not found:
        raise PlaceError("no routable layout found in %d tries (%s); allow more layers or simplify the netlist" % (tries, last))
    total, attempt, nodes, planes, before, res = min(found, key=lambda f: f[0])
    lo = [min(p[i] for p in nodes) for i in range(3)]
    margin = (1, 1, 0)                                         # one empty row / column round the edge; layers are exactly the layers used
    moved = {tuple(p[i] - lo[i] + margin[i] for i in range(3)): n for p, n in nodes.items()}
    hi = [max(p[i] for p in moved) for i in range(3)]
    d = c3.Design(hi[0] + 2, hi[1] + 2, hi[2] + 1)
    d.nodes = moved
    d.description = "Placed automatically by placer3d_v1.py (%d netlist cells + %d relay cells, verified against the netlist by running it %d times)." % (len(cells), total - len(cells), res["trials"])
    d.meta = {"expect": "netlist", "netlist": netlist_doc(cells, nets), "placer": {"seed": seed, "layers_allowed": layers}}
    used_layers = len({p[2] for p in d.nodes})
    if d.layers > layers:
        raise PlaceError("internal error: result uses %d layers, %d allowed" % (d.layers, layers))
    rep = {"cells": len(cells), "relays_added": total - len(cells), "total": total, "planes_removed": planes, "relays_before_compaction": before - len(cells),
           "box": [d.rows, d.cols, d.layers], "layers_used": used_layers, "layouts_found": len(found), "totals_found": sorted(f[0] for f in found), "attempts": attempt, "verify": res,
           "gates": sum(1 for c in cells.values() if c[0] == "gate")}
    return d, rep


def adder_netlist():
    import nor_adder_3d_v1 as t3
    return t3.netlist()


def main(argv=None):
    ap = argparse.ArgumentParser(description="automatic placer for the six-face toy grid (VM only)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--netlist", metavar="FILE")
    src.add_argument("--example", choices=["adder"])
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", metavar="FILE", help="write the result as an imago-3d-design file (open it in composer3d_v1.py)")
    a = ap.parse_args(argv)
    try:
        if a.example:
            cells, nets = adder_netlist()
        else:
            with open(a.netlist) as f:
                cells, nets = parse_netlist(json.load(f))
        d, rep = place(cells, nets, a.layers, a.seed, log=print)
    except (PlaceError, OSError, ValueError) as e:
        print("placement failed:", e)
        return 1
    print(json.dumps({k: v for k, v in rep.items() if k != "verify"}, indent=1))
    print("verified: %d random runs, every exit equal to direct evaluation; ticks %s" % (rep["verify"]["trials"], rep["verify"]["ticks"]))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(d.export(), f, indent=1)
        print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
