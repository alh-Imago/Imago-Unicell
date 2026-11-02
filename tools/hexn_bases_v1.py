#!/usr/bin/env python3
"""hexn_bases_v1: BASE DESIGNS (bitstreams) and fitting a user's design onto them (2 Nov 2026, Alan 12:46: "for a minimum number of actual bitstreams you would have to supply a set of them, see if the user's design fits onto them, and if not suggest a new base design, a new bitstream, and the programming to place their design onto it").

A BASE DESIGN is one bitstream: a grid whose work cells have a FIXED type (UN unary, AL aligned serial, JN join, BR branch, MG merge, PR priority, SQ sequencer, LT latch; see hexn_wrgrid_v10.CELLTYPES) and whose routing cells are all alike.  Loading a bitstream (seconds, state lost) fixes the types;
loading a PROGRAM (fast) sets what is programmable: which routing input feeds each routing output, each core's parameters (shift amount, merge mode, branch routes, sequencer values ...) and the pads.
  fits(base, task)      plans the user's design on the base (only cells of a suitable type, AL only when the operands can be aligned, JN always joins) and runs it in the simulator against the word-level reference.
  place(lib, task)      the cheapest library base that fits and the program for it; if none fits: the cheapest way to get one: the library base with the smallest change (types swapped / cells added), or a new base, and then the program.
  build_library(tasks)  start from one tailored base per design and MERGE bases while a merged base still fits every design of both and stays inside the slot budget: the fewest bitstreams for that set of designs.
Costs are the v8 / v9 figures: measured for the new cores and the join core, ESTIMATES for UN and AL and for routing cells (30, or 60 once any self-timed type is present); no place and route.  The default budget is a rough figure for the Tang Nano 20K as I recall it (about 20,000 4-input look-up tables): check it against the board before relying on it."""
import os, sys, random, itertools, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_wrgrid_v10 as G
from hexn_wrgrid_v6 import tasks as old_tasks

TYPES = list(G.CELLTYPES)
SELF_TIMED = {"JN", "BR", "MG", "PR", "SQ"}
BUDGET_TANG = 20000


def type_for(kind, mode):
    if kind in ("cp", "shl", "shr"): return "UN"
    if kind in ("add", "sub", "and", "or", "xor"): return "AL" if mode == "aligned" else "JN"
    if kind in ("lt", "min", "max"): return "JN"
    return {"branch": "BR", "merge": "MG", "prio": "PR", "seq": "SQ", "latch": "LT"}[kind]


def needs_of(plan):
    c = {}
    for i in plan.g.work.values(): t = type_for(i["op"], i["mode"]); c[t] = c.get(t, 0) + 1
    return c


class Base:
    def __init__(s, n, counts, name=None):
        s.n, s.counts = n, {k: v for k, v in counts.items() if v}
        cells = [(r, c) for r in range(n) for c in range(n) if r % 2 == 1 and c % 2 == 1]
        total = sum(s.counts.values())
        if total > len(cells): raise ValueError("grid %d has %d work cells, %d wanted" % (n, len(cells), total))
        fill = {**s.counts, "AL": s.counts.get("AL", 0) + len(cells) - total}      # the spare cells are cheap aligned cores
        # spread the types over the grid: weighted round robin by largest deficit, scarce types first in a tie
        seq = []; placed = {k: 0 for k in fill}
        for i in range(len(cells)):
            k = max((k for k in sorted(fill) if placed[k] < fill[k]), key=lambda k: (fill[k] / len(cells) * (i + 1) - placed[k], -fill[k]))
            seq.append(k); placed[k] += 1
        s.type = dict(zip(cells, seq)); s.name = name or "base%d_%s" % (n, "_".join("%s%d" % (k, v) for k, v in sorted(fill.items())))
        s.fill = fill
    def cost(s):
        routing = s.n * s.n - len(s.type)
        rc = 60 if any(t in SELF_TIMED for t in s.type.values()) else 30
        return sum(G.CELLTYPES[t][1] for t in s.type.values()) + routing * rc
    def __repr__(s): return "%s (%d x %d, %d slots)" % (s.name, s.n, s.n, s.cost())


_cache = {}
def fits(base, task, tries=14):
    """(plan or None): the design planned on the base AND simulated to the reference"""
    key = (base.name, id(task))
    if key in _cache: return _cache[key]
    nodes, ins, outs = task
    res = None
    try:
        P = G.plan10(nodes, ins, outs, base.n, base.n, base.type, tries=tries)
        ok, why = G.check_task(P, nodes, ins, outs)
        res = P if ok else None
    except RuntimeError:
        res = None
    _cache[key] = res; return res


def free_plan(task, n=13):
    nodes, ins, outs = task
    return G.plan9(nodes, ins, outs, n, n, tries=40)


def tailored(task, name=None):
    """the cheapest grid and type mix found for ONE design: start from the types its free plan needs, grow the grid until it fits"""
    P0 = free_plan(task); need = needs_of(P0)
    for n in (7, 9, 11, 13, 15):
        try: b = Base(n, need, name)
        except ValueError: continue
        if fits(b, task): return b
    raise RuntimeError("no base up to 15 x 15 fits")


def union(b1, b2):
    counts = {k: max(b1.counts.get(k, 0), b2.counts.get(k, 0)) for k in sorted(set(b1.counts) | set(b2.counts))}
    return counts


def build_library(tasks, budget=BUDGET_TANG, verbose=False):
    """tasks: {name: task}.  returns list of (base, [task names])"""
    lib = [[tailored(t), [nm]] for nm, t in tasks.items()]
    if verbose: print("tailored bases:", len(lib))
    while True:
        best = None
        for i, j in itertools.combinations(range(len(lib)), 2):
            (b1, m1), (b2, m2) = lib[i], lib[j]
            cnt = union(b1, b2)
            for n in sorted({b1.n, b2.n, max(b1.n, b2.n) + 2}):
                try: nb = Base(n, cnt)
                except ValueError: continue
                if nb.cost() > budget: continue
                if all(fits(nb, tasks[m]) for m in m1 + m2):
                    if best is None or nb.cost() < best[0].cost(): best = (nb, i, j, m1 + m2)
                    break
        if best is None: break
        nb, i, j, mem = best
        lib = [x for k, x in enumerate(lib) if k not in (i, j)] + [[nb, mem]]
        if verbose: print("merged -> %s for %d designs" % (nb, len(mem)))
    return lib


def program_of(base, plan, task):
    """the PROGRAM that places the design on the base: per work cell its parameters, per routing cell which input feeds each output, the pads; with the size of it in bits (an estimate of the encoding)"""
    g = G.configure9(plan)
    cells = {}
    for w, i in g.work.items():
        cells["%d,%d" % w] = dict(type=base.type[w], kind=i["op"], mode=i["mode"], k=i["k"], cfg={k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in i["cfg"].items()}, ins=i["ins"], outs=i["outs"])
    routing = {"%d,%d" % c: dict(sel) for c, sel in g.route.items()}
    bits = len(base.type) * 0 + (base.n * base.n - len(base.type)) * 12          # a routing cell: four outputs, each picks one of four inputs or none = 3 bits
    per = {"UN": 5, "AL": 3, "JN": 4, "BR": 40, "MG": 2, "PR": 25, "SQ": 131, "LT": 2}
    bits += sum(per[v["type"]] for v in cells.values())
    return dict(bitstream=base.name, cells=cells, routing=routing, pads_in={k: list(v) for k, v in g.pads_in.items()}, pads_out={k: list(v) for k, v in g.pads_out.items()}, config_bits_estimate=bits)


def run_program(base, program, task, inputs):
    """replay a PROGRAM on its base from the program text alone (no planner objects): the grid is rebuilt from the bitstream's types and the program's routing, cores and pads"""
    from hexn_wrgrid_v6 import Grid
    prog = json.loads(json.dumps(program))               # only what survives being written out as text
    g = Grid(base.n, base.n)
    for key, sel in prog["routing"].items(): r, c = map(int, key.split(",")); g.route[(r, c)] = dict(sel)
    for key, v in prog["cells"].items():
        r, c = map(int, key.split(","))
        assert v["type"] == base.type[(r, c)], "program asks a %s cell to be a %s" % (base.type[(r, c)], v["type"])
        assert v["kind"] in G.CELLTYPES[v["type"]][0]
        cfg = dict(v["cfg"])
        g.work[(r, c)] = dict(op=v["kind"], k=v["k"], mode=v["mode"], aligned=(v["mode"] == "aligned"), cfg=cfg, ins=v["ins"], outs=v["outs"])
    g.pads_in = {k: tuple(v) for k, v in prog["pads_in"].items()}; g.pads_out = {k: tuple(v) for k, v in prog["pads_out"].items()}
    return G.simulate9(None, inputs, task[2], g=g)


def place(lib, task, budget=BUDGET_TANG, members=None):
    """lib: [(base, member names)] -> a decision dict"""
    nodes, ins, outs = task
    try:
        P0 = free_plan(task); ok0, why0 = G.check_task(P0, nodes, ins, outs)
    except RuntimeError as e:
        return dict(decision="refused", reason="the design cannot be placed even on an unlimited grid: %s" % e)
    except IndexError:
        return dict(decision="refused", reason="a core waits for a word that a branch may never send (a conditional stream): the checker cannot verify such a design and the hardware could wait forever")
    if not ok0: return dict(decision="refused", reason="the design is wrong even on an unconstrained grid, so no base can host it: %s" % why0)
    ok = [(b, fits(b, task)) for b, _ in lib]
    ok = [(b, P) for b, P in ok if P]
    if ok:
        b, P = min(ok, key=lambda x: x[0].cost())
        return dict(decision="fits", base=b, program=program_of(b, P, task), plan=P)
    # no library base fits: the smallest CHANGE to a library base that makes it fit, else a new base
    need = needs_of(free_plan(task)); best = None
    for b, mem in lib:
        cnt = {k: max(b.counts.get(k, 0), need.get(k, 0)) for k in sorted(set(b.counts) | set(need))}
        for n in (b.n, b.n + 2, b.n + 4):
            try: nb = Base(n, cnt)
            except ValueError: continue
            if nb.cost() > budget: continue
            if fits(nb, task) and all(fits(nb, members[m]) for m in mem if members and m in members):
                if best is None or nb.cost() < best[0].cost(): best = (nb, b)
                break
    if best:
        nb, old = best; P = fits(nb, task)
        diff = {k: nb.fill.get(k, 0) - old.fill.get(k, 0) for k in sorted(set(nb.fill) | set(old.fill)) if nb.fill.get(k, 0) != old.fill.get(k, 0)}
        return dict(decision="extend", base=nb, derived_from=old, change=diff, program=program_of(nb, P, task), plan=P)
    nb = tailored(task); P = fits(nb, task)
    return dict(decision="new", base=nb, program=program_of(nb, P, task), plan=P)


def all_tasks():
    T = {}
    for nm, (nodes, ins, outs) in old_tasks().items():
        T["old/" + nm] = ([G.Node9(n.name, n.op, [x for x in (n.a, n.b) if x], k=n.k) for n in nodes], ins, outs)
    for nm, t in G.tasks9().items(): T["new/" + nm] = t
    return T


if __name__ == "__main__":
    import time
    t0 = time.time(); T = all_tasks()
    lib = build_library(T, verbose=True)
    print("\nLIBRARY: %d bitstreams for %d designs  (%.0f s)" % (len(lib), len(T), time.time() - t0))
    for b, mem in lib: print("  %s\n     fits: %s" % (b, ", ".join(mem)))
