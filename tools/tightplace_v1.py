"""tools/tightplace_v1.py -- ledger #1013: TIGHT placement of a small netlist from a hand-drawn MAP (Alan, 12 Oct: "a simple mul with its extras out one side ... the exp and flags in the other side dealt with as required").
The loose placer (`netplace_v1`) gives every op its own column and runs every connection through gutter lanes: 94% of the multiplier's cells were relays. Here the designer DRAWS the block as a text map, one op name
per cell (`.` is empty), ops that are neighbours on the map are LINKED directly, and only the connections whose ends are not neighbours are ROUTED (relay lanes, crossings allowed). The netlist is the same `_Net`
the loose placer takes (kinds relay / cmp / add / sub / mul / const; `sub`'s first source is its minuend: a constant, which must be a neighbour), so the arithmetic is unchanged and only the geometry differs.
An op with no sources is an ENTRY (a lane or an external cell reaches it)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flex_layout_v1 import LayoutError  # noqa: E402


def place_map(g, name, n, rows, r0, c0, route_order=None, cross=True, extra=None, retries=0, ports=None):
    """Place netlist `n` on grid g from `rows` (a list of strings of whitespace-separated op names / dots), the top-left at (r0, c0). Returns (names {op: grid name}, consts {grid name: value}, routed [(src, dst)])."""
    at = {}
    for i, line in enumerate(rows):
        for j, tok in enumerate(line.split()):
            if tok != ".":
                if tok in at.values() or tok not in n.cells:
                    raise LayoutError(f"{name}: map token {tok!r} {'is repeated' if tok in at.values() else 'is not an op of the netlist'}")
                at[(i, j)] = tok
    for op, pos in (extra or {}).items():
        if op in at.values() or op not in n.cells or pos in at:
            raise LayoutError(f"{name}: extra position for {op!r} clashes or is not an op ({pos})")
        at[pos] = op
    placed = {v: k for k, v in at.items()}
    missing = [c for c in n.order if c not in placed]
    if missing:
        raise LayoutError(f"{name}: ops not on the map: {missing}")
    names = {c: f"{name}.{c}" for c in n.order}
    consts = {}
    mask = getattr(n, "mask", 0xFFFFFFFF)
    for c in n.order:
        k, (i, j) = n.cells[c], placed[c]
        r, cc = r0 + i, c0 + j
        if k["kind"] == "relay":
            g.add(names[c], r, cc, addon=k["addon"])
        elif k["kind"] == "add":
            g.add(names[c], r, cc, "adder")
        elif k["kind"] == "sub":
            g.add(names[c], r, cc, "adder", {"subtract_mode": 1})
        elif k["kind"] == "mul":
            g.add(names[c], r, cc, "mul")
        elif k["kind"] == "const":
            g.add(names[c], r, cc, preload=k["const"] & mask)
            consts[names[c]] = k["const"] & mask
        else:
            g.add(names[c], r, cc, "comparator", {"threshold": k["thr"]})
    uses = {c: len(n.cells[c]['srcs']) for c in n.order}
    for c in n.order:
        for q in n.cells[c]['srcs']:
            uses[q] += 1
    over = {c: u for c, u in uses.items() if u > 4}
    if over:
        raise LayoutError(f"{name}: more connections than faces (4): {over}")
    adj = lambda a, b: abs(placed[a][0] - placed[b][0]) + abs(placed[a][1] - placed[b][1]) == 1
    routed = []
    for c in n.order:
        k = n.cells[c]
        if k["kind"] == "sub":
            g.minuend[names[c]] = names[k["srcs"][0]]
        for q in k["srcs"]:
            if n.cells[q]["kind"] == "const" and not adj(q, c):
                raise LayoutError(f"{name}: constant {q} must be a neighbour of {c}")
            if adj(q, c):
                g.link(names[q], names[c])
            else:
                routed.append((q, c))
    order = route_order or sorted(routed, key=lambda e: abs(placed[e[0]][0] - placed[e[1]][0]) + abs(placed[e[0]][1] - placed[e[1]][1]))
    import random
    rr = random.Random(5)
    reserved = set()
    for op, side in (ports or {}).items():                           # a face kept free for a lane from / to another block (east for an output, west for an entry)
        nm = names[op]
        r_, c_ = g.pos(nm)
        occ_ = g.at()
        fr = [(r_ + dr, c_ + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)) if (r_ + dr, c_ + dc) not in occ_ and 0 <= r_ + dr < g.rows and 0 <= c_ + dc < g.cols and (r_ + dr, c_ + dc) not in reserved]
        if not fr:
            raise LayoutError(f"{nm}: no free face for its outside lane")
        reserved.add(max(fr, key=lambda q: (q[1] if side == 'E' else -q[1], -abs(q[0] - r_))))
    stubs = _assign_stubs(g, names, placed, routed, reserved)
    done = []
    doneset = set()
    for attempt in range(retries + 1):
        try:
            for q, c in order:
                nq, nc_ = names[q], names[c]
                occ = g.at()
                nbrs = lambda nm: [(g.pos(nm)[0] + dr, g.pos(nm)[1] + dc) for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                                   if (g.pos(nm)[0] + dr, g.pos(nm)[1] + dc) not in occ and 0 <= g.pos(nm)[0] + dr < g.rows and 0 <= g.pos(nm)[1] + dc < g.cols]
                ours = {stubs[(q, c)][0], stubs[(q, c)][1]}
                keep = set()
                for k_, (s1, s2) in stubs.items():
                    if k_ != (q, c) and k_ not in doneset:
                        keep.update((s1, s2))
                keep.update(sq for sq in nbrs(nq) if sq != stubs[(q, c)][0])
                keep.update(sq for sq in nbrs(nc_) if sq != stubs[(q, c)][1])
                keep.update(reserved)
                keep -= ours
                g.route(nq, nc_, cross=cross, avoid=keep, spread=True)
                done.append((q, c))
                doneset.add((q, c))
            break
        except LayoutError:
            for q, c in reversed(done):
                g.unroute(names[q], names[c])
            done = []
            doneset = set()
            if attempt == retries:
                raise
            order = list(order)
            rr.shuffle(order)
    return names, consts, [(names[q], names[c]) for q, c in order]


def autoplace(n, fixed, rows, cols, seed=1, iters=60000, free_rect=None, crowd=1.0, pitch=2):
    """Simulated annealing on a lattice: ops in `fixed` ({op: (i, j)}) stay; every other op sits on a SITE of a pitch-`pitch` lattice inside `free_rect` = (i0, j0, i1, j1) (pitch 2 leaves a square between
    neighbouring sites for a relay lane, so the lanes can always be laid) and is moved to minimise the total relays its connections need. A constant is not moved: it is put on a free square beside its
    consumer afterwards. Returns {op: (i, j)} for every op not in `fixed`."""
    import math
    import random
    rnd = random.Random(seed)
    i0, j0, i1, j1 = free_rect or (0, 0, rows - 1, cols - 1)
    is_const = lambda c: n.cells[c]["kind"] == "const"
    edges = [(q, c) for c in n.order for q in n.cells[c]["srcs"] if not is_const(q)]
    adj = {c: [] for c in n.order}
    for e in edges:
        adj[e[0]].append(e)
        adj[e[1]].append(e)
    movable = [c for c in n.order if c not in fixed and not is_const(c)]
    pos = dict(fixed)
    occ = set(fixed.values())
    sites = [(i0 + pitch * a, j0 + pitch * b) for a in range((i1 - i0) // pitch + 1) for b in range((j1 - j0) // pitch + 1)]
    sites = [p for p in sites if p not in occ]
    free_sites = set(sites)
    for c in movable:
        nb = [x for x in ((e[0] if e[1] == c else e[1]) for e in adj[c]) if x in pos]
        cand = sorted(free_sites, key=lambda p: (sum(abs(p[0] - pos[x][0]) + abs(p[1] - pos[x][1]) for x in nb), rnd.random()))[:6] if nb else list(free_sites)
        p = rnd.choice(cand)
        pos[c] = p
        occ.add(p)
        free_sites.discard(p)

    def cost_of(c):
        t = 0
        for e in adj[c]:
            a, b = pos.get(e[0]), pos.get(e[1])
            if a is None or b is None:
                continue
            t += abs(a[0] - b[0]) + abs(a[1] - b[1]) - 1
        return t
    T0 = 3.0
    for it in range(iters):
        T = T0 * (1 - it / iters) + 0.05
        c = rnd.choice(movable)
        old = pos[c]
        if rnd.random() < 0.6 and adj[c]:
            e = rnd.choice(adj[c])
            o = e[0] if e[1] == c else e[1]
            d = rnd.choice(((0, pitch), (pitch, 0), (0, -pitch), (-pitch, 0)))
            new = (pos[o][0] + d[0], pos[o][1] + d[1])
        else:
            new = (old[0] + pitch * rnd.randint(-2, 2), old[1] + pitch * rnd.randint(-2, 2))
        if new not in free_sites:
            continue
        nbrs = {(e[0] if e[1] == c else e[1]) for e in adj[c]}
        before = cost_of(c)
        pos[c] = new
        after = cost_of(c)
        if after <= before or rnd.random() < math.exp((before - after) / T):
            free_sites.discard(new)
            free_sites.add(old)
            occ.discard(old)
            occ.add(new)
            continue
        pos[c] = old
    out = {c: pos[c] for c in movable}
    occ = set(fixed.values()) | set(out.values())
    for c in n.order:                                           # the constants: a free square beside the consumer, away from the consumer's other lanes
        if not is_const(c):
            continue
        cons = [k for k in n.order if c in n.cells[k]["srcs"]]
        k = cons[0]
        base = pos[k]
        mids = set()                                            # squares a lane would use right next to the consumer: keep the constant off them
        for e in edges:
            if k in e:
                o = e[0] if e[1] == k else e[1]
                di, dj = pos[o][0] - base[0], pos[o][1] - base[1]
                mids.add((base[0] + (di > 0) - (di < 0), base[1]) if abs(di) >= abs(dj) else (base[0], base[1] + (dj > 0) - (dj < 0)))
                mids.add((base[0], base[1] + (dj > 0) - (dj < 0)) if di else (base[0] + (di > 0) - (di < 0), base[1]))
        for d in sorted(((0, 1), (1, 0), (0, -1), (-1, 0)), key=lambda d: ((base[0] + d[0], base[1] + d[1]) in mids)):
            q = (base[0] + d[0], base[1] + d[1])
            if q not in occ and 0 <= q[0] < rows and 0 <= q[1] < cols:
                out[c] = q
                occ.add(q)
                break
        else:
            raise LayoutError(f"no free square beside {k} for its constant {c}")
    return out


def _assign_stubs(g, names, placed, routed, reserved=()):
    """Give every routed lane its own square beside each end (the first and the last relay of the lane), chosen before anything is routed, so no lane can wall a cell in (ledger #1013)."""
    occ = g.at()
    taken, stubs = {sq: None for sq in reserved}, {}
    D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
    def free(nm):
        r, c = g.pos(nm)
        return [(r + dr, c + dc) for dr, dc in D4 if (r + dr, c + dc) not in occ and 0 <= r + dr < g.rows and 0 <= c + dc < g.cols]
    lanes = sorted(routed, key=lambda e: abs(g.pos(names[e[0]])[0] - g.pos(names[e[1]])[0]) + abs(g.pos(names[e[0]])[1] - g.pos(names[e[1]])[1]))
    for q, c in lanes:
        pq, pc = g.pos(names[q]), g.pos(names[c])
        d = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
        sq = sorted((s_ for s_ in free(names[q]) if s_ not in taken), key=lambda s_: (d(s_, pc), s_))
        if not sq:
            raise LayoutError(f"{names[q]}: no free face left for its lane to {names[c]}")
        s1 = sq[0]
        taken[s1] = (q, c)
        sc = sorted((s_ for s_ in free(names[c]) if s_ not in taken or s_ == s1 and taken[s_] == (q, c)), key=lambda s_: (d(s_, s1), s_))
        if not sc:
            raise LayoutError(f"{names[c]}: no free face left for the lane from {names[q]}")
        s2 = sc[0]
        taken[s2] = (q, c)
        stubs[(q, c)] = (s1, s2)
    return stubs
