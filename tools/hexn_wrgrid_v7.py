#!/usr/bin/env python3
"""Work/routing grid model v7: SELF-TIMED (JOIN) cores.  (Alan 2 Nov 09:11 and 09:14: every two-input work core has a one-word FIFO cell on each input; each raises 'have' when its word has
started; the AND releases both; they re-arm by themselves.)  No alignment planning at all: the planner only places and routes by SHORTEST path (no detours, no delay cores, no exact-length lines, no flag pads).
The start marker of every word travels with the data as a second bit on every link (a second plane, same selects): this is the assumption the design still has to settle; it doubles the wires.
Cores: binary serial ops (add sub and or xor) and the buffered ones (lt min max) use the join (2 FIFO cells); one-input ops (cp, shl, shr) read the stream straight off the link.
Cycle-accurate on the links and the join; the FIFO is the Python twin of sub/verilog/hexn_ramfifo_v7.v (checked here by the same rules as hexn_join_cell_v1.v).  Tasks, ops and Grid come from hexn_wrgrid_v6.py.
"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hexn_wrgrid_v6 import Grid, Node, tasks, ref_eval, OPS, OPP, DIRS, W, MASK, configure as _configure_v6, Plan

UNARY7 = {"cp", "shl", "shr"}
SERIAL7 = {"add", "sub", "and", "or", "xor"}
BUF7 = {"lt", "min", "max"}


class Fifo:
    """twin of hexn_ramfifo_v7: step(din, wstart, rel) computes the new registers from the old ones"""
    def __init__(s):
        s.mem = [0] * 32; s.wq = 0; s.rq = 0; s.wr_run = 0; s.rd_run = 0; s.wa = 0; s.ra = 0; s.q = 0; s.qs = 0; s.have = 0
    def step(s, din, wstart, rel):
        we = wstart and not s.wq; re = rel and not s.rq
        wq, rq = wstart, rel
        have, wr_run, rd_run, wa, ra = s.have, s.wr_run, s.rd_run, s.wa, s.ra
        q, qs = s.q, 0
        w_idx = None
        if we and not s.have:
            have = 1; wr_run = 1; w_idx = 0; wa = 1
        elif s.wr_run:
            w_idx = s.wa; wa = (s.wa + 1) & 31
            if s.wa == 31: wr_run = 0
        rd_idx = None
        if re and s.have and not s.rd_run:
            rd_run = 1; ra = 0
        if s.rd_run:
            q = s.mem[s.ra]; qs = 1 if s.ra == 0 else 0; ra = (s.ra + 1) & 31
            if s.ra == 31:
                rd_run = 0; have = 0
        else:
            q = 0
        if w_idx is not None: s.mem[w_idx] = din
        s.wq, s.rq, s.have, s.wr_run, s.rd_run, s.wa, s.ra, s.q, s.qs = wq, rq, have, wr_run, rd_run, wa, ra, q, qs


class Core:
    def __init__(s, op, k):
        s.op, s.k = op, k
        s.fa, s.fb = Fifo(), Fifo()
        s.c = 0; s.r = 0; s.rs = 0
        s.cnt = None; s.hist = []; s.A = []; s.B = []; s.emit = None
    def step(self, a, af, b, bf):
        """one clock: returns nothing; the registered outputs are s.r / s.rs"""
        s = self; op = s.op
        if op in SERIAL7 or op in BUF7:
            qa, qsa, qb = s.fa.q, s.fa.qs, s.fb.q
            both = s.fa.have and s.fb.have
            r, rs = 0, 0
            if op in SERIAL7:
                rs = qsa
                if op in ("and", "or", "xor"):
                    r = (qa & qb) if op == "and" else (qa | qb) if op == "or" else (qa ^ qb)
                else:
                    bb = qb ^ 1 if op == "sub" else qb
                    ci = (1 if op == "sub" else 0) if qsa else s.c
                    r = qa ^ bb ^ ci; s.c = (qa & bb) | (qa & ci) | (bb & ci)
            else:
                # buffered: collect the two read streams (32 clocks from the read start), then emit the result
                if qsa and s.cnt is None: s.cnt = 0; s.A = []; s.B = []
                if s.cnt is not None and s.emit is None:
                    s.A.append(qa); s.B.append(qb); s.cnt += 1
                    if s.cnt == 32:
                        av = sum(v << i for i, v in enumerate(s.A)); bv = sum(v << i for i, v in enumerate(s.B))
                        val = {"lt": int(av < bv), "min": min(av, bv), "max": max(av, bv)}[op]
                        s.emit = [(val >> i) & 1 for i in range(32)]; s.cnt = None
                elif s.emit is not None:
                    pass
                if s.emit is not None and len(s.emit) == 32 and not getattr(s, "emitting", False):
                    s.emitting = True; s.ei = 0
                if getattr(s, "emitting", False):
                    r = s.emit[s.ei]; rs = 1 if s.ei == 0 else 0; s.ei += 1
                    if s.ei == 32: s.emitting = False; s.emit = None
            s.r, s.rs = r, rs
            s.fa.step(a, af, both); s.fb.step(b, bf, both)
        else:
            r, rs = 0, 0
            if af and s.cnt is None: s.cnt = 0; s.hist = []
            if s.cnt is not None:
                i = s.cnt; s.hist.append(a)
                if op == "cp":
                    r = a; rs = 1 if i == 0 else 0
                elif op == "shl":
                    r = s.hist[i - s.k] if i >= s.k else 0; rs = 1 if i == 0 else 0
                else:                                  # shr: out bit j = a[j + k], first output at index k
                    j = i - s.k
                    if 0 <= j <= 31 - s.k: r = a; rs = 1 if j == 0 else 0
                    elif j > 31 - s.k and j <= 31: r = 0
                s.cnt += 1
                if s.cnt >= 32 + s.k + 1: s.cnt = None
            s.r, s.rs = r, rs


def plan7(nodes, inputs, outputs, R, C, tries=40):
    last = None
    for attempt in range(tries):
        try:
            return _plan7(nodes, inputs, outputs, R, C, random.Random(attempt), attempt)
        except (RuntimeError, IndexError) as e:
            last = RuntimeError("no plan: %s" % e)
    raise last


def _plan7(nodes, inputs, outputs, R, C, rnd, attempt):
    g = Grid(R, C); P = Plan(); P.g = g; g.hold = {}; P.flag_paths = []; P.paths = {}; P.src_cell = {}
    pads = [(r, 0) for r in range(R) if not g.is_work(r, 0)]
    if attempt: rnd.shuffle(pads)
    for name in inputs:
        p = pads.pop(0); P.src_cell[name] = p; g.pads_in[name] = p
    free = g.work_cells()
    for n in nodes:
        pts = [P.src_cell[x] for x in (n.a, n.b) if x]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        cand = sorted(free, key=lambda w: abs(w[0] - cx) + abs(w[1] - cy) + (rnd.random() * 3 if attempt else 0))
        done = False
        for w in cand[:12]:
            faces = [("W", n.a)] + ([("N", n.b)] if n.b else [])
            taken = {}; seq = []; ok = True
            for face, srcn in faces:
                dst = g.in_cell(w, face); sc = P.src_cell[srcn]
                if not g.inside(*dst): ok = False; break
                hmin = abs(sc[0] - dst[0]) + abs(sc[1] - dst[1]) + 1; path = None
                for extra in (0, 2, 4, 6):
                    path = g.find_path(sc, dst, hmin + extra, taken, srcn)
                    if path is not None: break
                if path is None: ok = False; break
                for wire, val in path: taken[wire] = val
                seq.append((face, srcn, dst, path))
            if not ok or not g.inside(*g.out_cell(w)): continue
            for face, srcn, dst, path in seq:
                for wire, val in path: g.used[wire] = val
                g.used[(dst, OPP[face])] = (srcn, len(path), 'F')
                P.paths[(n.name, face)] = (srcn, path, dst)
            g.used[(w, "E")] = (n.name, 0, 'WK'); P.src_cell[n.name] = g.out_cell(w)
            g.work[w] = dict(op=n.op, k=n.k, node=n.name); free.remove(w); done = True; break
        if not done: raise RuntimeError("no place/route for %s" % n.name)
    east = [(r, C - 1) for r in range(R) if not g.is_work(r, C - 1)]
    for name in outputs:
        sc = P.src_cell[name]; best = None
        for pad in sorted(east, key=lambda q: abs(q[0] - sc[0]) + abs(q[1] - sc[1])):
            if pad in g.pads_out.values(): continue
            hmin = abs(sc[0] - pad[0]) + abs(sc[1] - pad[1]) + 1
            for extra in (0, 2, 4):
                path = g.find_path(sc, pad, hmin + extra, {}, name)
                if path is not None: best = (pad, path); break
            if best: break
        if best is None: raise RuntimeError("no output route for %s" % name)
        pad, path = best
        for wire, val in path: g.used[wire] = val
        g.pads_out[name] = pad; P.paths[(name, "out")] = (name, path, pad)
    return P


def simulate7(P, inputs, outputs, ticks=700):
    g = _configure_v6(P)
    rout, rflag, wout, wflag = {}, {}, {}, {}
    cores = {w: Core(i["op"], i["k"]) for w, i in g.work.items()}
    bits_in = {n: [(v >> i) & 1 for i, _ in enumerate(range(W))] for n, v in inputs.items()}
    bits_in = {n: [(v >> i) & 1 for i in range(W)] for n, v in inputs.items()}
    padcell = {pad: n for n, pad in g.pads_in.items()}
    outpad = {pad: n for n, pad in g.pads_out.items()}
    cap = {n: [] for n in outputs}; start = {n: None for n in outputs}
    for t in range(1, ticks + 1):
        nr, nf = {}, {}
        for cell, sel in g.route.items():
            for od, idf in sel.items():
                if idf == "W" and cell in padcell:
                    n = padcell[cell]; i = t - 1
                    v = bits_in[n][i] if 0 <= i < W else 0; f = 1 if t == 1 else 0
                else:
                    dr, dc = DIRS[idf]; nb = (cell[0] + dr, cell[1] + dc)
                    if g.is_work(*nb): v = wout.get(nb, 0); f = wflag.get(nb, 0)
                    else: v = rout.get((nb, OPP[idf]), 0); f = rflag.get((nb, OPP[idf]), 0)
                nr[(cell, od)] = v; nf[(cell, od)] = f
        nw, nwf = {}, {}
        for w, core in cores.items():
            a_c = g.in_cell(w, "W"); b_c = g.in_cell(w, "N")
            a = rout.get((a_c, "E"), 0); af = rflag.get((a_c, "E"), 0)
            b = rout.get((b_c, "S"), 0); bf = rflag.get((b_c, "S"), 0)
            core.step(a, af, b, bf); nw[w] = core.r; nwf[w] = core.rs
        # outputs: read the pad wire (value before this update = what the pad sees this tick)
        for pad, n in outpad.items():
            v = rout.get((pad, "E"), 0); f = rflag.get((pad, "E"), 0)
            if f and start[n] is None: start[n] = t
            if start[n] is not None and t < start[n] + 32: cap[n].append(v)
        rout.update(nr); rflag.update(nf); wout, wflag = nw, nwf
    res = {n: sum(b << i for i, b in enumerate(cap[n])) if len(cap[n]) == 32 else None for n in outputs}
    return res, start


if __name__ == "__main__":
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    for name, (nodes, ins, outs) in tasks().items():
        try: P = plan7(nodes, ins, outs, R, R)
        except RuntimeError as e: print(name, "NO PLAN", e); continue
        rnd = random.Random(3); ok = True
        for _ in range(5):
            iv = {n: rnd.randrange(1 << 16) for n in ins}
            res, st = simulate7(P, iv, outs)
            if res != {o: ref_eval(nodes, iv)[o] for o in outs}: ok = False
        nb = sum(1 for n in nodes if n.b); ncells = len({c for (c, d) in P.g.used})
        print("%-14s ok=%-5s work=%d (joins %d -> %d FIFOs)  link wires=%d  cells touched=%d  first result bit at clock %s" % (name, ok, len(nodes), nb, 2 * nb, len(P.g.used), ncells, st))
