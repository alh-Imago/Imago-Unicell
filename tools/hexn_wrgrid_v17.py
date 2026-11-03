#!/usr/bin/env python3
"""hexn_wrgrid_v17 = v16 with the BRANCH core cost set from PLACE AND ROUTE (3 Nov 2026): BR = 237 (was the yosys-only 154). Basis: an all-BR 7x7 pattern placed at 3,322 slots, an all-AL pattern at 1,245 (so a BR tile is about 231 placed slots more than an AL tile, about 276 per tile = core 237 + TILE_EXTRA 39; the tile alone measured 208 in yosys, 51 over the core). Timing and everything else as v16.
Original v16 docstring follows.
hexn_wrgrid_v16 = v15 on the CORRECTED CORE TIMING (3 Nov 2026, Alan 09:27): the buffered ops lt / min / max follow the RTL (+1 / +3 clocks, hexn_wrgrid_v8b); costs and everything else as v15. v15 and earlier untouched.
Original v15 docstring follows.
hexn_wrgrid_v15 = v14 with the JOIN core cost set from PLACE AND ROUTE (3 Nov 2026): JN = 223 slots (was the yosys-only 141). Basis: an all-JN 7x7 pattern (J9_7) placed at 3,197 slots against 2,396 yosys alone (+33%: the FIFO RAM16SDP4 primitives and ALU chain starts), and an all-AL pattern at 1,245, so a JN tile is about 217 more placed slots than an AL tile; with AL tile 45 that is about 262 per JN tile, i.e. core 223 + TILE_EXTRA 39. Checked on a DIFFERENT pattern (J4U2_7: 2 UN + 3 AL + 4 JN, see the ledger). Only JN is changed; the lt/min/max CATALOGUE entries, BR, MG, PR, SQ, LT and RAM are still not re-measured as placed tiles and will probably carry a similar packing excess.
Original v14 docstring follows.
hexn_wrgrid_v14 = v13 with the ALIGNED CORE MEASURED (3 Nov 2026): AL = 11 slots (yosys 0.69 synth_gowin -nowidelut, hexn_aligned_core_v1 alone), was an estimate of 43. The AL tile alone (hexn_tile_al_v1) is 50 slots = 11 + 39, so TILE_EXTRA 39 is now confirmed for a second core type.
UNCHANGED and still estimates: lt/min/max stay at 43 + 72 (not re-measured), JN 141, BR 154, MG 82, PR 419, SQ 141, LT 3 are core-only counts, RAM routing cell 87 is a six-face probe. Planner behaviour is unchanged; only the AL numbers are.
Original v13 docstring follows.
hexn_wrgrid_v13 = v12 with CORRECTED COSTS (2 Nov 2026, Alan 22:33: 'correct the planner first'). Behaviour of the planner is unchanged; only the numbers are.
From the first full tile (sub/verilog/hexn_tile_v1.v, yosys 0.69 synth_gowin -nowidelut, slots = LUT + ALU, one tile alone, no place and route; ledger 2 Nov 23:58):
  UN (unary core: cp shl shr mask inv acc) = 124 slots MEASURED (107 LUT + 17 ALU), was an estimate of 43.
  ROUTE_COST = 24 MEASURED (4-face routing cell WITH the flag lane; the old 30 / 60 were six-face-shaped estimates and the flag lane is always present now).
  TILE_EXTRA = 39 per work cell = its own routing cell (24) + the glue that chooses result-or-route and the operand face (15 LUT, measured for the unary tile). ASSUMED the same for the other core types: their wrappers are not built.
  Not re-measured: AL 43 (estimate), JN / BR / MG / PR / SQ / LT (core-only counts from the earlier rows), RAM routing cell 87 (a six-face probe).
Original v12 docstring follows.

hexn_wrgrid_v12 = v11 + RAM CELLS IN THE ROUTING (2 Nov 2026, Alan 14:40: bitstream patterns such as "two layers of RAM before any work cores", "a band of RAM cells every so often"; the programmer fits the design onto the pattern).
Some routing cells are RAM cells (ram = set of cells; lead_k = extra pure-routing columns in front of the work cells).  A RAM cell on a stream's path can HOLD it for a programmed number of ticks (HOLD_MIN..HOLD_MAX).  A hold fixes any gap, odd or even, so a two-input core whose operands meet only after a hold is ALIGNED (cheap, no FIFO) where v11 would have needed a JOIN core (141 slots against 43).
MODEL, not yet RTL-checked in this grid: a hold is an ideal delay of the bit AND its start marker (the v7 assumption that the marker rides with the data).  The RAM cell RTL (hexn_ramroute_v5) was checked with a start flag that is driven at the planned clock; its hold range 2..96 is from there.  A held wire is never shared with another consumer of the same stream.
hexn_wrgrid_v11 = v10 + DEAD BRANCHES (2 Nov 2026, Alan 14:35: "in a flat unrolled system a branch that feeds a branch is only used occasionally, the second even less"). A stream may be ABSENT (a branch sends on one output only; what hangs off the other output is dead this run). ref9 propagates absence, the planner marks such streams and never ALIGNS a core with a possibly-absent operand (an aligned core has no FIFO and would compute with a missing operand, a wrong word), and stranded_words() reports a word left waiting in a cell for a partner that never came (the cell must be cleared before the next run).
hexn_wrgrid_v10 = v9 + FIXED CELL TYPES (2 Nov 2026, Alan 12:46): plan10(..., celltype={work cell: type}) places a design only on cells of a suitable type (the BASE DESIGN of a bitstream), see hexn_bases_v1.py.
hexn_wrgrid_v9: the CATALOGUE PLANNER (2 Nov 2026, Alan 09:46: "start the planner, design so it can include those at the same time").
v8 knew eleven ops with two inputs (W, N) and one output (E) hard-wired.  v9 takes the shape of every core from a CATALOGUE: which faces it reads, which faces it writes, how it is timed, what it costs.
Cores in the catalogue: the stream and two-input ops of v8 (cp shl shr add sub and or xor lt min max), and the new serial cores: merge (2 in, 1 out), branch (2 in, 2 out), priority (up to 3 in on a square grid, 1 out), sequencer (1 in), latch (3 in: planned and routed only), mul (not built: refused).
Timing class decides how a core is placed:
  'static'   its output start is a fixed number of ticks after its inputs start (v8's direct / aligned / join logic for the ops; branch: later start + 38; sequencer: advance + 2; merge A-only / B-only: start + 4; join-OR: later start + 4)
  'dynamic'  merge arbitrate and priority: the order words leave depends on who arrives first.  Its output start is NOT known when planning, so a consumer that wants its two operands to meet (an ALIGNED core) must use a JOIN instead.
A stream can carry several words (merge, priority, sequencer): inputs are {name: word} or {name: [(offset, word), ...]}, outputs are lists of (start tick, word).
The new cores are simulated by the word-level twins of hexn_twins_v1.py (checked against the RTL tick for tick); the old ops by the bit-level Core of v8.  The latch is not simulated (it makes a level, not a word): v9 only plans and routes it.
Costs: 'measured' = yosys synth_gowin -nowidelut slot counts of the RTL (branch 154, merge 82, priority 419, sequencer 141, latch 3); 'estimate' = the v8 figures (work core 43, routing core 30 or 60, join FIFO 36 each).  No place and route.
"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hexn_wrgrid_v6 import Grid, Plan, DIRS, OPP, W, MASK, OPS
from hexn_wrgrid_v8b import Core, delta, UNARY7, SERIAL7, BUF7
import hexn_twins_v1 as T

R = random.Random


HOLD_MIN, HOLD_MAX = 2, 96


class Grid12(Grid):
    """Grid with lead_k extra pure-routing column pairs in front of the work lattice (columns 0..2*lead_k carry no work cell) and a set of RAM routing cells"""
    def __init__(s, rows, cols, lead_k=0, ram=None):
        super().__init__(rows, cols); s.lead_k = lead_k; s.ram = set(ram or ()); s.holds = {}
    def is_work(s, r, c): return r % 2 == 1 and c % 2 == 1 and c >= 2 * s.lead_k + 1


ROUTE_COST, TILE_EXTRA = 24, 39      # see the docstring: measured routing cell with flag lane; per work cell: own routing cell + glue


class Spec:
    def __init__(s, ins, outs, timing, cost, measured=False, note=""):
        s.ins, s.outs, s.timing, s.cost, s.measured, s.note = ins, outs, timing, cost, measured, note


CATALOGUE = {}
for _op in ("cp", "shl", "shr"):
    CATALOGUE[_op] = Spec(["W"], ["E"], "static", 124, True, "v8 'direct' (reads the link straight); 124 slots = the unary core as built (v13)")
for _op in ("add", "sub", "and", "or", "xor"):
    CATALOGUE[_op] = Spec(["W", "N"], ["E"], "static", 11, True, "aligned when both operands can meet, else join (v8 rule); 11 slots = the aligned core as built (v14)")
for _op in ("lt", "min", "max"):
    CATALOGUE[_op] = Spec(["W", "N"], ["E"], "static", 43 + 72, note="always join (two FIFO cells hold the words)")
CATALOGUE["merge"] = Spec(["W", "N"], ["E"], "mode", 82, True, "mode 0 A only, 1 B only, 2 arbitrate (dynamic), 3 join-OR")
CATALOGUE["branch"] = Spec(["W", "N"], ["E", "S"], "static", 154, True, "result starts at later start + 38 on out1 (E) and/or out2 (S) as routed")
CATALOGUE["prio"] = Spec(["W", "N", "S"], ["E"], "dynamic", 419, True, "square grid: 3 inputs (a 4-input priority needs the hex layout or a tree of two); 419 slots is the full cell with the weighted mode")
CATALOGUE["seq"] = Spec(["W"], ["E"], "static", 141, True, "one value per advance (the start flag of the word on W), up to 4 values")
CATALOGUE["latch"] = Spec(["W", "N", "S"], ["E"], "control", 3, True, "set / clear / toggle; planned and routed only, not simulated")
CATALOGUE["mul"] = Spec(["W", "N"], ["E"], "unbuilt", 0, False, "uses the chip's 18x18 multiplier; not built, the planner refuses it")


class Node9:
    def __init__(s, name, kind, ins, outs=None, k=0, cfg=None):
        s.name, s.kind, s.ins, s.outs, s.k, s.cfg = name, kind, list(ins), list(outs) if outs else [name], k, cfg or {}


def _out_cond(n, incond, oi):
    """may output oi be absent this run, given which inputs may be absent"""
    k = n.kind
    if k == "branch": return True
    if k == "merge":
        m = n.cfg.get("mode", 2)
        return (incond[0] if m == 0 else incond[1] if m == 1 else any(incond) if m == 3 else all(incond))
    if k == "prio": return all(incond)
    return any(incond)


def check_spec(n):
    sp = CATALOGUE.get(n.kind)
    if sp is None: raise RuntimeError("unknown core %s" % n.kind)
    if sp.timing == "unbuilt": raise RuntimeError("%s is not built yet (%s)" % (n.kind, sp.note))
    if len(n.ins) > len(sp.ins):
        raise RuntimeError("%s has %d inputs but a square-grid work cell has %d input faces for it (%s)" % (n.kind, len(n.ins), len(sp.ins), "needs the hex layout (6 faces) or a tree" if n.kind == "prio" else ""))
    if len(n.outs) != len(sp.outs): raise RuntimeError("%s writes %d outputs, got %d names" % (n.kind, len(sp.outs), len(n.outs)))
    return sp


def out_cell9(w, face): dr, dc = DIRS[face]; return (w[0] + dr, w[1] + dc)


def static_out(n, arr, P):
    """output start tick (at the source wire) for a core whose inputs start at ticks arr (dict face -> tick), or None when unknowable"""
    k = n.kind
    if k in ("cp", "shl", "shr"): return arr["W"] + delta(k, "direct", n.k) + 1
    if k == "branch": return max(arr.values()) + 38 + 1
    if k == "seq": return arr["W"] + 2 + 1
    if k == "merge":
        m = n.cfg.get("mode", 2)
        if m == 3: return max(arr.values()) + 4 + 1
        if m == 0: return arr["W"] + 4 + 1
        if m == 1: return arr["N"] + 4 + 1
        return None
    return None


# cell types of a bitstream: which kinds a work cell can be (and, for the add family, in which mode)
CELLTYPES = {
    "UN": (frozenset({"cp", "shl", "shr"}), 124, "unary core cp / shl / shr / mask / inv / acc as built: 107 LUT + 17 ALU (measured, hexn_tile_v1); the planner only places cp shl shr"),
    "AL": (frozenset({"add", "sub", "and", "or", "xor"}), 11, "serial two-input core, ALIGNED mode only, no FIFO: 11 slots (11 LUT, 0 ALU) MEASURED, hexn_aligned_core_v1"),
    "JN": (frozenset({"add", "sub", "and", "or", "xor", "lt", "min", "max"}), 223, "join core: two FIFO cells, any arrival order. 223 = PLACED-calibrated (yosys alone 138 + 4 RAM16SDP4, tile 182; placed about 262 per tile, minus TILE_EXTRA 39), v15; was the yosys-only 141"),
    "BR": (frozenset({"branch"}), 237, "branch core. 237 = PLACED-calibrated (yosys alone 157 + 4 RAM16SDP4, tile 208; an all-BR 7x7 pattern placed at 3,322 slots against 2,629 yosys alone, +26%), v17; was the yosys-only 154"),
    "MG": (frozenset({"merge"}), 82, "merge (measured)"),
    "PR": (frozenset({"prio"}), 419, "priority, full (measured)"),
    "SQ": (frozenset({"seq"}), 141, "sequencer (measured)"),
    "LT": (frozenset({"latch"}), 3, "latch (measured)"),
}


def plan10(nodes, inputs, outputs, R_, C_, celltype, tries=40, gmax=8, ram=None, lead_k=0):
    return plan9(nodes, inputs, outputs, R_, C_, tries, gmax, celltype, ram, lead_k)


def plan9(nodes, inputs, outputs, R_, C_, tries=40, gmax=8, celltype=None, ram=None, lead_k=0):
    last = None
    for attempt in range(tries):
        try:
            return _plan9(nodes, inputs, outputs, R_, C_, random.Random(attempt), attempt, gmax, celltype, ram, lead_k)
        except (RuntimeError, IndexError) as e:
            last = RuntimeError("no plan: %s" % e)
    raise last


def _plan9(nodes, inputs, outputs, R_, C_, rnd, attempt, gmax, celltype=None, ram=None, lead_k=0):
    g = Grid12(R_, C_, lead_k, ram); P = Plan(); P.g = g; g.hold = {}; P.flag_paths = []; P.paths = {}; P.src_cell = {}; P.src_face = {}; P.modes = {}; P.nodes = {n.name: n for n in nodes}; P.celltype = celltype; cond = set(); P.cond = cond
    t_out = {}
    for n in nodes: check_spec(n)
    pads = [(r, 0) for r in range(R_) if not g.is_work(r, 0) and r % 2 == 1] + [(r, 0) for r in range(R_) if r % 2 == 0]
    if attempt: rnd.shuffle(pads)
    for name in inputs:
        p = pads.pop(0); P.src_cell[name] = p; P.src_face[name] = "E"; g.pads_in[name] = p; t_out[name] = 2
    free = g.work_cells()
    for n in nodes:
        sp = CATALOGUE[n.kind]; faces = list(zip(sp.ins, n.ins))
        pts = [P.src_cell[x] for _, x in faces]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        pool = [w for w in free if celltype is None or n.kind in CELLTYPES[celltype[w]][0]]
        cand = sorted(pool, key=lambda w: abs(w[0] - cx) + abs(w[1] - cy) + (rnd.random() * 3 if attempt else 0))
        done = False
        for w in cand[:(12 if celltype is None else 40)]:
            hm = {}; ok = True
            for face, srcn in faces:
                dst = g.in_cell(w, face); sc = P.src_cell[srcn]
                if not g.inside(*dst): ok = False; break
                hm[face] = abs(sc[0] - dst[0]) + abs(sc[1] - dst[1]) + 1
            if not ok or not all(g.inside(*out_cell9(w, f)) for f in sp.outs): continue
            ta0 = {f: (t_out[sn] + hm[f] - 1) if t_out[sn] is not None else None for f, sn in faces}
            known = all(v is not None for v in ta0.values())
            condin = any(sn in cond for _, sn in faces)
            two = n.kind in SERIAL7 or n.kind in BUF7
            variants = []                                    # (mode, use_hold) in order of preference
            if two:
                if n.kind in BUF7 or not known or condin: variants = [("join", False)]
                else:
                    gap = abs(ta0["W"] - ta0["N"])
                    if gap == 0 or (gap % 2 == 0 and gap <= gmax): variants = [("aligned", False)]
                    else: variants = ([("aligned", True)] if g.ram else []) + [("join", False)]
            elif n.kind in ("cp", "shl", "shr"): variants = [("direct", False)]
            else: variants = [("self", False)]
            if celltype is not None and (n.kind in SERIAL7):
                if celltype[w] == "AL": variants = [v for v in variants if v[0] == "aligned"]          # an aligned-only core cannot join
                if celltype[w] == "JN": variants = [("join", False)]                                    # a join core always joins
            for mode, use_hold in variants:
                taken = {}; seq = []; ok = True
                late = max(ta0.values()) if (mode == "aligned" and not use_hold) else None
                for face, srcn in faces:
                    dst = g.in_cell(w, face); sc = P.src_cell[srcn]
                    want = hm[face] + ((late - ta0[face]) if late is not None else 0); path = None
                    for extra in (0, 2, 4, 6):
                        path = g.find_path(sc, dst, want + extra, taken, srcn)
                        if path is not None: break
                    if path is None: ok = False; break
                    for wire, val in path: taken[wire] = val
                    seq.append([face, srcn, dst, path])
                if not ok: continue
                holds = {}
                if use_hold:
                    a0 = {f: t_out[srcn] + len(path) for f, srcn, dst, path in seq}; lt = max(a0.values())
                    for item in seq:
                        face, srcn, dst, path = item; h = lt - a0[face]
                        if h == 0: continue
                        if h < HOLD_MIN or h > HOLD_MAX: ok = False; break
                        j = next((j for j, (wire, val) in enumerate(path) if wire[0] in g.ram and wire not in g.used and sum(1 for x in seq for (w2, v2) in x[3] if w2 == wire) == 1), None)
                        if j is None: ok = False; break
                        wire, val = path[j]; path[j] = (wire, (val[0], val[1], 'H')); holds[wire] = h
                    if not ok: continue
                arr = {f: (t_out[srcn] + len(path) + sum(h for wr, h in holds.items() if any(wr == w2 for (w2, v2) in path))) if t_out[srcn] is not None else None for f, srcn, dst, path in seq}
                if mode == "aligned" and len(set(arr.values())) != 1: continue
                for face, srcn, dst, path in seq:
                    for wire, val in path: g.used[wire] = val
                    g.used[(dst, OPP[face])] = (srcn, len(path), 'F')
                    P.paths[(n.name, face)] = (srcn, path, dst)
                g.holds.update(holds)
                if all(v is not None for v in arr.values()):
                    if two:
                        base = max(arr.values()); t_main = base + delta(n.kind, "join" if mode == "join" else mode if mode == "aligned" else "direct", n.k) + 1
                    else: t_main = static_out(n, arr, P)
                else: t_main = None
                if sp.timing == "dynamic": t_main = None
                for of, oname in zip(sp.outs, n.outs):
                    t_out[oname] = t_main
                    g.used[(w, of)] = (oname, 0, 'WK'); P.src_cell[oname] = out_cell9(w, of); P.src_face[oname] = of
                P.modes[n.name] = mode
                for oi, oname in enumerate(n.outs):
                    if _out_cond(n, [sn in cond for _, sn in faces], oi): cond.add(oname)
                g.work[w] = dict(ctype=(celltype[w] if celltype else None), op=n.kind, k=n.k, node=n.name, aligned=(mode == 'aligned'), mode=mode, held=bool(holds), cfg=n.cfg, ins=n.ins, outs=n.outs); free.remove(w); done = True; break
            if done: break
        if not done: raise RuntimeError("no place/route for %s" % n.name)
    east = [(r, C_ - 1) for r in range(R_) if not g.is_work(r, C_ - 1)]
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


def configure9(P):
    g = P.g
    for (nm, face), (srcn, path, dst) in P.paths.items():
        prev = OPP[P.src_face[srcn]]
        for ((p, d), _v) in path:
            g.route.setdefault(p, {})[d] = prev; prev = OPP[d]
        if face == "out": g.route.setdefault(dst, {})["E"] = prev
        else: g.route.setdefault(dst, {})[OPP[face]] = prev
    return g


class OldCore:
    """the v8 bit-level core behind the uniform interface"""
    INS = ("W", "N")
    def __init__(s, op, k, aligned): s.c = Core(op, k, aligned)
    def step(s, t, ins):
        a, af = ins.get("W", (0, 0)); b, bf = ins.get("N", (0, 0))
        s.c.step(a, af, b, bf); return {"E": (s.c.r, s.c.rs)}


def make_core(info):
    k, cfg = info["op"], info["cfg"]
    if k in UNARY7 or k in SERIAL7 or k in BUF7: return OldCore(k, info["k"], info.get("aligned", False))
    if k == "merge": return T.MergeTwin(cfg.get("mode", 2))
    if k == "branch": return T.BranchTwin(cfg.get("route_lt", 1), cfg.get("route_eq", 1), cfg.get("route_gt", 2), cfg.get("emit", 1), cfg.get("fixed", 0))
    if k == "seq": return T.SeqTwin(cfg["vals"], cfg["len"])
    if k == "prio":
        mp = {"W": 0, "N": 1, "S": 2}          # the planner's three input faces become cell faces n, s, e of the twin (order only matters for the tie rule)
        pt = T.PrioTwin(cfg.get("mask", 15), cfg.get("ranks", (0, 0, 0, 0)), cfg.get("mode", 0), cfg.get("len", 0), cfg.get("order", (0, 0, 0, 0)))
        pt.INS = ("W", "N", "S", "E")           # twin face index i is the i-th face in this tuple
        return pt
    raise RuntimeError("no simulation for %s" % k)


def simulate9(P, inputs, outputs, ticks=900, g=None, want_cores=False):
    from hexn_wrgrid_v6 import DIRS as D
    g = g or configure9(P)
    rout, rflag, wout = {}, {}, {}
    from collections import deque
    dq = {wire: deque([(0, 0)] * h) for wire, h in getattr(g, 'holds', {}).items()}
    cores = {w: make_core(i) for w, i in g.work.items() if i["op"] != "latch"}
    words_in = {n: (v if isinstance(v, list) else [(0, v)]) for n, v in inputs.items()}
    padcell = {pad: n for n, pad in g.pads_in.items()}
    outpad = {pad: n for n, pad in g.pads_out.items()}
    cap = {n: [] for n in outputs}; cur = {n: None for n in outputs}
    for t in range(1, ticks + 1):
        nr = {}
        for cell, sel in g.route.items():
            for od, idf in sel.items():
                if idf == "W" and cell in padcell:
                    nm = padcell[cell]; v = 0; f = 0
                    for off, word in words_in[nm]:
                        i = t - 1 - off
                        if 0 <= i < W: v = (word >> i) & 1; f = 1 if i == 0 else 0
                else:
                    dr, dc = D[idf]; nb = (cell[0] + dr, cell[1] + dc)
                    if g.is_work(*nb): v, f = wout.get((nb, OPP[idf]), (0, 0))
                    else: v = rout.get((nb, OPP[idf]), (0, 0))[0]; f = rout.get((nb, OPP[idf]), (0, 0))[1]
                if (cell, od) in dq: dq[(cell, od)].append((v, f)); v, f = dq[(cell, od)].popleft()
                nr[(cell, od)] = (v, f)
        nw = {}
        for w, core in cores.items():
            ins = {}
            for face in core.INS:
                c = g.in_cell(w, face); ins[face] = rout.get((c, OPP[face]), (0, 0))
            outs = core.step(t, ins)
            for of, vf in outs.items(): nw[(w, of)] = vf
        for pad, nm in outpad.items():
            v, f = rout.get((pad, "E"), (0, 0))
            if f: cur[nm] = [t, 0, 0]
            if cur[nm] is not None and cur[nm][1] < W:
                c = cur[nm]; c[2] |= v << c[1]; c[1] += 1
                if c[1] == W: cap[nm].append((c[0], c[2])); cur[nm] = None
        rout.update(nr); wout = {**wout, **nw}
    return (cap, {i['node'] if 'node' in i else str(w): cores[w] for w, i in g.work.items() if w in cores}) if want_cores else cap


# ---------------------------------------------------------------- reference (word level; None marks an order the hardware does not fix)
def ref9(nodes, inputs):
    """expected words per stream: {stream: (ordered?, [words])}; an absent stream is an empty list.  Inputs: {name: word | [(offset, word)]}."""
    v = {n: ([w for _, w in x] if isinstance(x, list) else [x]) for n, x in inputs.items()}
    sg = lambda x: x - (1 << W) if x >> (W - 1) else x
    ordered = {}
    for n in nodes:
        k = n.kind
        if k in OPS:
            ls = [v[x] for x in n.ins]
            if any(not l for l in ls): v[n.name] = []
            else:
                a = ls[0][0]; b = ls[1][0] if len(ls) > 1 else 0
                v[n.name] = [OPS[k][0](a, b, n.k)]
        elif k == "branch":
            A, B = v[n.ins[0]], v[n.ins[1]]; c = n.cfg
            if not A or not B: v[n.outs[0]] = []; v[n.outs[1]] = []
            else:
                a, b = A[0], B[0]
                route = c.get("route_eq", 1) if a == b else c.get("route_lt", 1) if sg(a) < sg(b) else c.get("route_gt", 2)
                val = [c.get("fixed", 0), a, b, (a - b) & MASK][c.get("emit", 1)]
                v[n.outs[0]] = [val] if route & 1 else []; v[n.outs[1]] = [val] if route & 2 else []
        elif k == "merge":
            m = n.cfg.get("mode", 2); A, B = v[n.ins[0]], v[n.ins[1]]
            if m == 3: v[n.name] = [A[0] | B[0]] if A and B else []
            elif m == 0: v[n.name] = list(A)
            elif m == 1: v[n.name] = list(B)
            else: v[n.name] = list(A) + list(B); ordered[n.name] = False
        elif k == "prio":
            mask = n.cfg.get("mask", 15); ws = []
            for i, nm in enumerate(n.ins):
                if (mask >> i) & 1: ws += v[nm]
            v[n.name] = ws; ordered[n.name] = False
        elif k == "seq":
            c = n.cfg; cnt = len(v[n.ins[0]]); v[n.name] = [c["vals"][i % c["len"]] for i in range(cnt)] if c["len"] else []
        else: raise RuntimeError("no reference for " + k)
        for o in n.outs: ordered.setdefault(o, True)
    return {s: (ordered.get(s, True), ws) for s, ws in v.items()}


def tasks9():
    N = Node9; T_ = {}
    T_["branch_route"] = ([N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=3))], ["x", "y"], ["lo", "hi"])
    T_["merge_two"] = ([N("m", "merge", ["x", "y"], cfg=dict(mode=2))], ["x", "y"], ["m"])
    T_["or_join"] = ([N("u", "add", ["x", "k"]), N("v", "shl", ["y"], k=3), N("z", "merge", ["u", "v"], cfg=dict(mode=3))], ["x", "k", "y"], ["z"])
    T_["seq_add"] = ([N("s", "seq", ["trig"], cfg=dict(vals=[1000, 2000, 3000, 4000], len=3)), N("r", "add", ["s", "x"])], ["trig", "x"], ["r"])
    T_["prio3"] = ([N("p", "prio", ["x", "y", "z"], cfg=dict(mask=7, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z"], ["p"])
    T_["branch_merge_add"] = ([N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=3)), N("m", "merge", ["lo", "hi"], cfg=dict(mode=2)), N("r", "add", ["m", "c"])], ["x", "y", "c"], ["r"])
    T_["seq_branch_prio"] = ([N("sq", "seq", ["trig"], cfg=dict(vals=[500000, 20, 900000, 5], len=4)), N("br", "branch", ["x", "sq"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=3, route_gt=2, emit=1)),
                              N("p", "prio", ["lo", "hi", "w"], cfg=dict(mask=7, ranks=(0, 1, 2, 3), mode=0))], ["trig", "x", "w"], ["p"])
    return T_


def estimate9(P):
    """slots: measured parts for the new cores, v8 estimates for the rest.  (total, routing cells, breakdown)"""
    g = P.g; cells = len({c for (c, d) in g.used} - set(g.work)); work = {}
    joins = sum(1 for i in g.work.values() if i["mode"] == "join" and i["op"] in SERIAL7 | BUF7)
    any_join = any(i["mode"] in ("join", "self") and i["op"] in SERIAL7 | BUF7 | {"merge", "branch", "prio"} for i in g.work.values())
    rc = 60 if any_join else 30
    tot = cells * rc
    for i in g.work.values():
        c = CATALOGUE[i["op"]].cost
        work[i["op"]] = work.get(i["op"], 0) + c; tot += c
    tot += joins * 2 * 36
    return tot, cells, work


def stranded_words(P, inputs, outputs):
    """words still waiting in a cell at the end of the run: {node: count}.  A cell that holds a word for a partner that never came must be cleared before the next run, or that word pairs with the wrong partner."""
    cap, cores = simulate9(P, inputs, outputs, want_cores=True); out = {}
    for nm, c in cores.items():
        if isinstance(c, OldCore): n = int(c.c.fa.have) + int(c.c.fb.have) if c.c.op in SERIAL7 | BUF7 and not c.c.aligned else 0
        else: n = sum(1 for x in c.rx.values() if x["rel"] is None)
        if n: out[nm] = n
    return out


def needs(nodes):
    """which core kinds a task uses: picks the bitstream variant (a build with only the kinds it needs is smaller)"""
    ks = {}
    for n in nodes: ks[n.kind] = ks.get(n.kind, 0) + 1
    return ks


def check_task(P, nodes, ins, outs, trials=6, seed=5):
    """simulate the planned grid on random inputs and compare with the word-level reference; returns (ok, why)"""
    rnd = random.Random(seed); why = ""
    for trial in range(trials):
        iv = {n: rnd.randrange(1 << 20) for n in ins}
        if trial == 3: iv = {n: 12345 for n in ins}                   # equal words: the eq route
        if "trig" in ins: iv["trig"] = [(0, 7)]
        ref = ref9(nodes, iv); cap = simulate9(P, iv, outs)
        for o in outs:
            got = [w for _, w in cap[o]]; ordd, want = ref[o]
            if (got != want) if ordd else (sorted(got) != sorted(want)): return False, "%s got %s want %s (inputs %s)" % (o, got, want, iv)
    return True, ""


if __name__ == "__main__":
    Rr = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    for name, (nodes, ins, outs) in tasks9().items():
        try: P = plan9(nodes, ins, outs, Rr, Rr)
        except RuntimeError as e: print("%-18s NO PLAN %s" % (name, e)); continue
        ok, why = check_task(P, nodes, ins, outs)
        e, cells, parts = estimate9(P)
        print("%-18s ok=%-5s modes=%s  %d slots (%d route cells) %s %s" % (name, ok, {k: v for k, v in P.modes.items()}, e, cells, needs(nodes), why))
