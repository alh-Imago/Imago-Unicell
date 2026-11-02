#!/usr/bin/env python3
"""Work/routing grid model + planner (Hex-N UCC v2 idea, first sketch).  v1.

The pattern (Alan, 2 Nov): work cores and routing cores alternate; only routing cores touch each other;
a work core sits between routing cores and has fixed faces: inputs W (a) and N (b), output E, S unused.
Square grid here (4 faces) as the simplest stand-in for the hex (6 faces); work cores at (odd,odd).

Routing core: per output face a select of one input face (or 0); every output is REGISTERED = 1 clock per hop.
A routing core can carry up to 4 lines (one per output face) - a "cross" is just two lines using different faces.
Work core: bit-serial, LSB first, 32-bit word; op latency 1 clock (buffered ops wait for the whole word).

Planner (idea taken from tools/netplace_v1.py: every path its own simple line, joined one at a time, never
sharing a wire): place nodes in order, route each input, make both operands arrive on the same clock by
lengthening the early one with detours (a detour adds 2 hops; the grid keeps parity so this always fits).

The sim runs the PLACED grid bit by bit and compares with plain Python arithmetic.  Model only: no RTL yet.
"""
import itertools, sys, random
W = 32
MASK = (1 << W) - 1
DIRS = {"N": (-1, 0), "E": (0, 1), "S": (1, 0), "W": (0, -1)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}

# op: (python fn on (a,b) -> value, emit offset e = clocks after the word starts before output bit 0 is produced (None for shr: = k), buffered?)   buffered = needs a whole-word store (not in the 119-LUT serial cell)
def elat(op, k): return k if op == 'shr' else OPS[op][1]
def _s(x): return x - (1 << W) if x >> (W - 1) else x
OPS = {
    "cp":  (lambda a, b, k: a, 1, False),
    "add": (lambda a, b, k: (a + b) & MASK, 0, False),
    "sub": (lambda a, b, k: (a - b) & MASK, 0, False),
    "and": (lambda a, b, k: a & b, 0, False),
    "or":  (lambda a, b, k: a | b, 0, False),
    "xor": (lambda a, b, k: a ^ b, 0, False),
    "shl": (lambda a, b, k: (a << k) & MASK, 0, False),       # k-clock delay with zero fill (needs a bit counter)
    "shr": (lambda a, b, k: a >> k, None, True),             # skips k bits: the word is cut
    "lt":  (lambda a, b, k: int(a < b), W, True),         # unsigned flag, known only at the last bit
    "min": (lambda a, b, k: min(a, b), W, True),
    "max": (lambda a, b, k: max(a, b), W, True),
}
UNARY = {"shl", "shr", "cp"}


class Grid:
    def __init__(s, rows, cols):
        s.R, s.C = rows, cols
        s.used = {}             # directed wire (cell, dir) -> (source stream, hop index, in-face): a stream may BRANCH (share its prefix), nothing else shares a wire
        s.work = {}             # (r,c) -> dict(op,k,node)
        s.route = {}            # (r,c) -> {outdir: indir}
        s.pads_in, s.pads_out = {}, {}
    def is_work(s, r, c): return r % 2 == 1 and c % 2 == 1
    def inside(s, r, c): return 0 <= r < s.R and 0 <= c < s.C
    def work_cells(s): return [(r, c) for r in range(s.R) for c in range(s.C) if s.is_work(r, c)]

    def nbrs(s, p):
        r, c = p
        for d, (dr, dc) in DIRS.items():
            q = (r + dr, c + dc)
            if s.inside(*q) and not s.is_work(*p) and not s.is_work(*q):
                yield d, q

    def find_path(s, src, dst, hops, taken, srcn=None):
        """routing-core path src..dst with exactly `hops` routing cells (both ends included), over wires not in used/taken
        and not reused inside the line.  Backward feasibility table first (exact up to own-wire reuse), then a pruned walk."""
        steps = hops - 1
        def blocked(w, left=None, inface=None):
            for dct in (s.used, taken):
                v = dct.get(w)
                if v is not None:
                    if left is not None and v[0] == srcn and v[1] == steps - left and (inface is None or v[2] == inface):
                        continue
                    return True
            return False
        feas = [set() for _ in range(steps + 1)]
        feas[0].add(dst)
        for left in range(1, steps + 1):
            for q in feas[left - 1]:
                for d, p in s.nbrs(q):          # p -> q uses wire (p, OPP-direction)
                    dd = OPP[d]
                    if not blocked((p, dd), left):
                        feas[left].add(p)
        if src not in feas[steps]:
            return None
        path_w = set()
        def walk(p, left, inface='P'):
            if left == 0:
                return []
            for d, q in s.nbrs(p):
                w = (p, d)
                if blocked(w, left, inface) or w in path_w or q not in feas[left - 1]:
                    continue
                path_w.add(w)
                rest = walk(q, left - 1, OPP[d])
                if rest is not None:
                    return [(w, (srcn, steps - left, inface))] + rest
                path_w.discard(w)
            return None
        sys.setrecursionlimit(10000)
        r = walk(src, steps)
        return r

    # an input face of a work cell is fed by the routing cell on that side; its output goes to the E routing cell
    def in_cell(s, w, face): dr, dc = DIRS[face]; return (w[0] + dr, w[1] + dc)
    def out_cell(s, w): return (w[0], w[1] + 1)


class Node:
    def __init__(s, name, op, a=None, b=None, k=0):
        s.name, s.op, s.a, s.b, s.k = name, op, a, b, k

def ref_eval(nodes, inputs):
    v = dict(inputs)
    for n in nodes:
        f = OPS[n.op][0]
        v[n.name] = f(v[n.a], v[n.b] if n.b else 0, n.k)
    return v


class Plan:
    pass

def plan(nodes, inputs, outputs, rows=9, cols=9, tries=60):
    """place + route; returns Plan or raises"""
    for attempt in range(tries):
        rnd = random.Random(attempt)
        try:
            return _plan(nodes, inputs, outputs, rows, cols, rnd, attempt)
        except (RuntimeError, IndexError) as e:
            err = RuntimeError(f'grid too small: {e}')
    raise err

def _plan(nodes, inputs, outputs, R, C, rnd, attempt):
    g = Grid(R, C)
    P = Plan(); P.g = g
    t_out = {}      # node -> start clock at its source wire
    src_cell = {}   # node -> routing cell where it appears (first routing cell after the source)
    pad_row = 0
    # pads: inputs enter at routing cells on the west edge (col 0), rows even-parity with the grid
    free_pads = [(r, 0) for r in range(R) if not g.is_work(r, 0)]
    # parity: route cells reachable from E-out cells (odd,even): r+c odd. keep pads on r+c odd
    free_pads = [p for p in free_pads if (p[0] + p[1]) % 2 == 1]
    rnd.shuffle(free_pads) if attempt else None
    for name in inputs:
        p = free_pads.pop(0)
        src_cell[name] = p; t_out[name] = 2       # input stream starts on the pad cell at clock 1 (cell's own register = hop 1)
        g.pads_in[name] = p
    free_work = g.work_cells()
    P.paths = {}
    P.arr = {}
    place = {}
    queue = list(nodes)
    P.nodes = []
    while queue:
        n = queue.pop(0)
        if n.b and (t_out[n.a] - t_out[n.b]) % 2:
            # the two operands differ by an odd number of clocks: detours only add 2, so one stream gets a 1-clock delay cell (copy) first
            lo = n.a if t_out[n.a] < t_out[n.b] else n.b
            cpn = Node(f"{lo}~d{len(P.nodes)}", "cp", lo)
            if lo == n.a: n = Node(n.name, n.op, cpn.name, n.b, n.k)
            else: n = Node(n.name, n.op, n.a, cpn.name, n.k)
            queue.insert(0, n); queue.insert(0, cpn)
            continue
        P.nodes.append(n)
        # candidate cells: nearest to the sources first (random tie-break on retries)
        pts = [src_cell[x] for x in (n.a, n.b) if x]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        cand = sorted(free_work, key=lambda w: (abs(w[0] - cx) + abs(w[1] - cy) + (rnd.random() * 3 if attempt else 0)))
        done = False
        for w in cand[:12]:
            faces = [("W", n.a)] + ([("N", n.b)] if n.b else [])
            # shortest route for each operand (cells counted incl. both ends)
            taken = {}; chosen = []; ok = True
            for face, srcn in faces:
                dst = g.in_cell(w, face)
                if not g.inside(*dst):
                    ok = False; break
                sc = src_cell[srcn]
                hmin = abs(sc[0] - dst[0]) + abs(sc[1] - dst[1]) + 1
                chosen.append([face, srcn, sc, dst, hmin])
            if not ok: continue
            # arrival clock at the work input = t_out + hops (each routing cell registers)
            for ch in chosen:
                ch.append(t_out[ch[1]] + ch[4] - 1)
            tmax = max(ch[5] for ch in chosen)
            seq = []
            ok = True
            for ch in sorted(chosen, key=lambda c: c[5]):
                face, srcn, sc, dst, hmin, arr = ch
                want = hmin + (tmax - arr)      # lengthen the early operand
                # inputs sharing the first wire out of the pad: a pad cell has 4 out wires, fine
                path = None
                for extra in range(0, 4, 2):
                    path = g.find_path(sc, dst, want + extra, taken, srcn)
                    if path is not None and tmax - arr >= 0:
                        break
                    path = None
                if path is None or (want + extra - hmin) % 2 and False:
                    ok = False; break
                for wire, val in path: taken[wire] = val
                seq.append((face, srcn, sc, dst, path, want + extra))
            if not ok: continue
            arrs = {s_[0]: t_out[s_[1]] + s_[5] - 1 for s_ in seq}
            if len(set(arrs.values())) != 1:
                continue   # parity problem: operands cannot be aligned by detours
            # commit
            for face, srcn, sc, dst, path, hops in seq:
                for wire, val in path: g.used[wire] = val
                # last wire must enter the work cell: dst -> work cell, direction toward w
                fd = OPP[face]       # direction from dst cell toward the work cell
                g.used[(dst, fd)] = (srcn, len(path), 'F')
                P.paths[(n.name, face)] = (srcn, path, dst)
            tin = list(arrs.values())[0]
            place[n.name] = w
            free_work.remove(w)
            t_out[n.name] = tin + elat(n.op, n.k) + 2     # +1: the work register; first routing cell of the output counted by its own hop
            oc = g.out_cell(w)
            if not g.inside(*oc): continue
            g.used[(w, "E")] = (n.name, 0, 'WK')
            src_cell[n.name] = oc
            P.arr[n.name] = tin
            g.work[w] = dict(op=n.op, k=n.k, node=n.name)
            done = True
            break
        if not done:
            raise RuntimeError(f"no place/route for {n.name}")
    # outputs: route each to a pad on the east edge (any clock; report its clock)
    P.out_clock = {}
    east = [(r, C - 1) for r in range(R) if not g.is_work(r, C - 1)]
    for name in outputs:
        sc = src_cell[name]
        best = None
        for pad in sorted(east, key=lambda q: abs(q[0] - sc[0]) + abs(q[1] - sc[1])):
            if pad in g.pads_out.values(): continue
            hmin = abs(sc[0] - pad[0]) + abs(sc[1] - pad[1]) + 1
            path = g.find_path(sc, pad, hmin, {}, name)
            if path is not None:
                best = (pad, path, hmin); break
        if best is None:
            raise RuntimeError(f"no output route for {name}")
        pad, path, hmin = best
        for wire, val in path: g.used[wire] = val
        g.pads_out[name] = pad
        P.paths[(name, "out")] = (name, path, pad)
        P.out_clock[name] = t_out[name] + hmin - 1
    P.place = place; P.src_cell = src_cell; P.t_out = t_out
    return P


def configure(P):
    """turn the paths into per-cell routing selects (out face <- in face); first cell of an input path takes the pad / E-face"""
    g = P.g
    for (nm, face), (srcn, path, dst) in P.paths.items():
        prev_in = None
        sc = P.src_cell[srcn]
        # the source feeds the first routing cell through its 'source' face: pad = W (west edge pad), work out = W (it sits west of its E cell)
        prev = "W"                                  # both pads (west edge) and work cores' E output arrive on the cell's W face
        cell = sc
        for ((p, d), _v) in path:
            g.route.setdefault(p, {})[d] = prev
            dr, dc = DIRS[d]; prev = OPP[d]
        # final cell: out toward work cell (input faces) or out to the pad
        if face == "out":
            g.route.setdefault(dst, {})["E"] = prev
        else:
            g.route.setdefault(dst, {})[OPP[face]] = prev
    return g


def simulate(P, inputs, outputs, ticks=None):
    """cycle-accurate bit-serial run of the placed grid"""
    g = configure(P)
    ticks = ticks or 400
    # state: routing registers rout[(cell,dir)], work out reg
    rout = {}
    wout = {}
    st = {}      # work cell internal: bufa, bufb lists of received bits
    bits_in = {n: [(v >> i) & 1 for i in range(W)] for n, v in inputs.items()}
    cap = {n: [] for n in outputs}
    padcell = {pad: n for n, pad in g.pads_in.items()}
    outpad = {pad: n for n, pad in g.pads_out.items()}
    for t in range(1, ticks + 1):
        # sample the wires seen by each cell at the start of the clock
        new_rout = {}
        for cell, sel in g.route.items():
            for od, idf in sel.items():
                if idf == "W" and cell in padcell and True:
                    # west face of a pad cell is the pad itself... unless a real neighbour feeds it (west edge: none)
                    n = padcell[cell]
                    i = t - 1
                    v = bits_in[n][i] if 0 <= i < W else 0
                else:
                    dr, dc = DIRS[idf]
                    nb = (cell[0] + dr, cell[1] + dc)
                    if g.is_work(*nb):
                        v = wout.get(nb, 0)         # work core output
                    else:
                        v = rout.get((nb, OPP[idf]), 0)
                new_rout[(cell, od)] = v
        # work cores
        new_w = {}
        for w, info in g.work.items():
            a_c = g.in_cell(w, "W"); b_c = g.in_cell(w, "N")
            a = rout.get((a_c, "E"), 0); b = rout.get((b_c, "S"), 0)
            s_ = st.setdefault(w, dict(A=[], B=[], carry=None, out=[]))
            op = info["op"]; k = info["k"]
            s_["A"].append(a); s_["B"].append(b)
            new_w[w] = 0
        rout.update(new_rout)
        for w, info in g.work.items():
            s_ = st[w]
            out = s_["out"]
            # find the first tick at which input 'a' stream starts: the planner told us (P.arr) - the hardware would use the word-start flag
            node = info["node"]
            t0 = P.arr[node]
            if info["op"] in UNARY:
                pass
            i = t - t0        # index of the bit being presented on the inputs at clock t (inputs registered at t, seen at t+1 -> aligned by planner)
        # outputs of work cores are generated below from the collected word (serial ops are bitwise; buffered ones wait): done after the loop for clarity
        for pad, n in outpad.items():
            if pad in g.route:
                cap[n].append(rout.get((pad, "E"), 0))
        wout = {w: _wbit(P, st[w], g.work[w], t) for w in g.work}
    res = {}
    for n in outputs:
        t0 = P.out_clock[n]
        bits = cap[n][t0 - 2: t0 - 2 + W]
        res[n] = sum(b << i for i, b in enumerate(bits))
    return res


def _wbit(P, s_, info, t):
    """output bit presented by a work core at clock t+1 (i.e. registered): bitwise for serial ops, from the stored word for buffered ones"""
    node = info["node"]; t0 = P.arr[node]
    op, k = info["op"], info["k"]
    A, B = s_["A"], s_["B"]
    # A[t-1], B[t-1] are the bits seen at clock t; the word starts at clock t0 (arrival clock)
    def bit(lst, i): j = t0 - 1 + i; return lst[j] if 0 <= j < len(lst) else 0
    # output bit index produced now, for registered output at clock t+1: index i = t - t0 (latency 1)
    e = elat(op, k)
    # serial ops: output bit i available after seeing input bit i at clock t0+i, latency 1 -> out register shows it at t0+i+1
    if op == "cp":
        i = t - t0 - 1
        return bit(A, i) if 0 <= i < W else 0
    if op in ("add", "sub", "and", "or", "xor"):
        i = t - t0
        if not 0 <= i < W: return 0
        a, b = bit(A, i), bit(B, i)
        if op == "and": return a & b
        if op == "or": return a | b
        if op == "xor": return a ^ b
        if i == 0: s_["carry"] = 0 if op == "add" else 1
        c = s_["carry"]
        if op == "sub": b ^= 1
        sbit = a ^ b ^ c
        s_["carry"] = (a & b) | (c & (a ^ b))
        return sbit
    if op == "shl":
        i = t - t0
        if not 0 <= i < W: return 0
        return bit(A, i - k) if i >= k else 0
    # buffered ops: value known once the needed bits are in; emit from word
    a_val = sum(bit(A, j) << j for j in range(W) if t0 - 1 + j < len(A))
    b_val = sum(bit(B, j) << j for j in range(W) if t0 - 1 + j < len(B))
    if op == "shr":
        i = t - t0 - k
        i = t - t0 - k
        return ((a_val >> k) >> i) & 1 if 0 <= i < W - k else 0
    # lt/min/max: word complete at clock t0+W-1 -> emit from t0+W
    i = t - (t0 + W)
    if not 0 <= i < W: return 0
    v = {"lt": int(a_val < b_val), "min": min(a_val, b_val), "max": max(a_val, b_val)}[op]
    return (v >> i) & 1


# ------------------------------------------------------------------ example tasks (mine; the original '12 steps' list was not kept in the repo)
def tasks():
    T = {}
    def N(name, op, a, b=None, k=0): return Node(name, op, a, b, k)
    T["scale_offset"]  = ([N("m", "shl", "x", k=3), N("y", "add", "m", "off")], ["x", "off"], ["y"])
    T["diff_abs"]      = ([N("d", "sub", "x", "y"), N("e", "sub", "y", "x"), N("r", "max", "d", "e")], ["x", "y"], ["r"])
    T["clamp"]         = ([N("lo", "max", "x", "a"), N("r", "min", "lo", "b")], ["x", "a", "b"], ["r"])
    T["field_extract"] = ([N("s", "shr", "x", k=4), N("r", "and", "s", "mask")], ["x", "mask"], ["r"])
    T["threshold"]     = ([N("f", "lt", "x", "t")], ["x", "t"], ["f"])
    T["sum4"]          = ([N("s1", "add", "a", "b"), N("s2", "add", "c", "d"), N("r", "add", "s1", "s2")], ["a", "b", "c", "d"], ["r"])
    T["bin12"]         = ([N("q", "sub", "x", "lo"), N("s", "shr", "q", k=3), N("r", "min", "s", "top")], ["x", "lo", "top"], ["r"])
    T["parity_mix"]    = ([N("a1", "xor", "a", "b"), N("a2", "and", "a", "b"), N("r", "or", "a1", "a2")], ["a", "b"], ["r"])
    T["mac"]           = ([N("m", "shl", "x", k=2), N("s", "add", "m", "acc"), N("r", "sub", "s", "bias")], ["x", "acc", "bias"], ["r"])
    T["mid"]           = ([N("s", "add", "a", "b"), N("r", "shr", "s", k=1)], ["a", "b"], ["r"])
    T["range_ok"]      = ([N("f1", "lt", "x", "lo"), N("f2", "lt", "hi", "x"), N("r", "or", "f1", "f2")], ["x", "lo", "hi"], ["r"])
    T["chain8"]        = ([N("a1", "add", "x", "y"), N("a2", "add", "a1", "y"), N("a3", "add", "a2", "y"), N("a4", "add", "a3", "y"),
                           N("a5", "add", "a4", "y"), N("a6", "add", "a5", "y"), N("a7", "add", "a6", "y"), N("r", "add", "a7", "y")], ["x", "y"], ["r"])
    return T


def run_all(R=9, C=9, trials=6, verbose=True):
    rows = []
    for name, (nodes, ins, outs) in tasks().items():
        try:
            P = plan(nodes, ins, outs, R, C)
        except RuntimeError as e:
            rows.append((name, "NO PLAN", str(e), "", "", "")); continue
        ok = True
        rnd = random.Random(7)
        for _ in range(trials):
            iv = {n: rnd.randrange(0, 1 << 16) for n in ins}
            exp = ref_eval(nodes, iv)
            got = simulate(P, iv, outs)
            if any(got[o] != exp[o] for o in outs):
                ok = False
        g = P.g
        cells = {c for (c, d) in g.used}
        extra = sum(1 for (nm, f), (s, path, dst) in P.paths.items())
        pad = max(0, max(P.out_clock.values()))
        buffered = sum(1 for n in nodes if OPS[n.op][2])
        rows.append((name, "ok" if ok else "MISMATCH", f"{len(nodes)} work", f"{len(g.work)} used of {len(g.work_cells())}",
                     f"{len(g.used)} wires", f"result at clock {pad}; {buffered} buffered"))
    return rows


if __name__ == "__main__":
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    for r in run_all(R, R):
        print(" | ".join(str(x) for x in r))
