#!/usr/bin/env python3
"""hexn_bases_v3: NAMED BITSTREAM PATTERNS and weighing a program against a new bitstream (2 Nov 2026, Alan 14:40: "a math-heavy design, a logic-processing design ... two layers of RAM before any work cores, it's a pattern as a bitstream, then the programmer fits the design to that"; "weigh the program usage against the redesigned bitstreams").
A PATTERN is a recipe for a base design at any size: how the work cells are typed (hexn_wrgrid_v13.CELLTYPES) and where the RAM routing cells are:
  math    mostly aligned adders, some unary, a few joins                 no RAM
  logic   many join cores, branch / merge / sequencer, one priority      no RAM
  mixed   aligned + join + one each of branch / merge / sequencer       no RAM
  ram2    math body behind TWO LAYERS of RAM cells (two pure-routing columns in front of the work cells)
  banded  mixed body with a band of RAM cells (one column) every 4th column
A RAM cell holds a stream for a programmed time, so an add-family core whose operands do not meet by a detour is still ALIGNED (43 slots) instead of joined (141); compare cores (lt / min / max) always join.
Costs (v4, corrected 2 Nov 2026 22:33, see hexn_wrgrid_v13): work cell = core + 39 (own routing cell + glue), plain routing cell 24 (four faces, flag lane), RAM routing cell 87 (hexn_ramroute probe v6, NOT re-measured at four faces); the unary core is 124 measured, other cores as before; no place and route.
WEIGHING: for one design the options are (a) a program on the bitstream already loaded, (b) a program on another library bitstream (swap: seconds, state lost), (c) a new bitstream (build: minutes, then swap).  The times are ASSUMED orders of magnitude (Alan: reload microseconds, swap seconds, Tang build a few minutes), change them in TIMES: program 1 microsecond per config bit, swap 3 s, build 300 s."""
import os, sys, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_wrgrid_v13 as G
import hexn_bases_v2 as B2          # all_tasks(), program_of's helpers are re-done here
from hexn_bases_v1 import type_for, needs_of

TIMES = dict(prog_per_bit=1e-6, swap=3.0, build=300.0)
# build time per device: Tang from Alan (a few minutes); the Kintex figure is his 'an hour or two' for a design-specific bitstream; its swap time is MY GUESS.  The slot budgets are for the designer to be given.
DEVICES = {"tang20k": dict(prog_per_bit=1e-6, swap=3.0, build=300.0), "kintex": dict(prog_per_bit=1e-6, swap=10.0, build=5400.0)}
RAM_COST, SELF_TIMED = 87, {"JN", "BR", "MG", "PR", "SQ"}


class Base:
    def __init__(s, n, counts, ram="none", lead_k=0, name=None):
        s.n, s.lead_k, s.ram_kind = n, lead_k, ram
        s.R, s.C = n, n + 2 * lead_k
        g = G.Grid12(s.R, s.C, lead_k)
        cells = sorted(g.work_cells())
        s.counts = {k: v for k, v in counts.items() if v}
        total = sum(s.counts.values())
        if total > len(cells): raise ValueError("%d work cells, %d wanted" % (len(cells), total))
        fill = {**s.counts, "AL": s.counts.get("AL", 0) + len(cells) - total}
        seq = []; placed = {k: 0 for k in fill}
        for i in range(len(cells)):
            k = max((k for k in sorted(fill) if placed[k] < fill[k]), key=lambda k: (fill[k] / len(cells) * (i + 1) - placed[k], -fill[k]))
            seq.append(k); placed[k] += 1
        s.type = dict(zip(cells, seq)); s.fill = fill
        allr = [(r, c) for r in range(s.R) for c in range(s.C) if not g.is_work(r, c)]
        if ram == "none": s.ram = set()
        elif ram == "lead2": s.ram = {(r, c) for (r, c) in allr if c in (1, 2)}          # the two pure columns behind the pad column
        elif ram.startswith("every"): k = int(ram[5:]); s.ram = {(r, c) for (r, c) in allr if c % 2 == 0 and c > 0 and c % k == 0 and c < s.C - 1}
        else: raise ValueError(ram)
        s.name = name or "n%d_%s%s_%s" % (n, "".join("%s%d" % (k, v) for k, v in sorted(fill.items())), "" if ram == "none" else "+" + ram, "L%d" % lead_k)
    def cost(s):
        routing = s.R * s.C - len(s.type); plain = routing - len(s.ram)
        return sum(G.CELLTYPES[t][1] + G.TILE_EXTRA for t in s.type.values()) + plain * G.ROUTE_COST + len(s.ram) * RAM_COST      # v4: measured routing cell, every work position is a tile
    def __repr__(s): return "%s (%d x %d, %d slots)" % (s.name, s.R, s.C, s.cost())


def make_pattern(name, n):
    cells = ((n - 1) // 2) ** 2
    f = lambda x, lo=1: max(lo, round(x * cells))
    if name in ("math", "ram2"): cnt = dict(UN=f(.125), JN=f(.125), AL=0); cnt.pop("AL")
    elif name == "logic": cnt = dict(JN=f(.375), BR=1, MG=1, SQ=1, PR=(1 if cells >= 16 else 0))
    elif name in ("mixed", "banded"): cnt = dict(JN=f(.25), UN=f(.1), BR=1, MG=1, SQ=1)
    else: raise ValueError(name)
    if name == "ram2": return Base(n, cnt, "lead2", 1, "ram2_%d" % n)
    if name == "banded": return Base(n, cnt, "every4", 0, "banded_%d" % n)
    return Base(n, cnt, "none", 0, "%s_%d" % (name, n))


PATTERNS = ["math", "logic", "mixed", "ram2", "banded"]
def pattern_library(sizes=(7, 9, 11)): return [make_pattern(p, n) for p in PATTERNS for n in sizes]


_cache = {}
def fits(base, task, tries=14):
    key = (base.name, id(task))
    if key in _cache: return _cache[key]
    nodes, ins, outs = task; res = None
    try:
        P = G.plan10(nodes, ins, outs, base.R, base.C, base.type, tries=tries, ram=base.ram, lead_k=base.lead_k)
        ok, why = G.check_task(P, nodes, ins, outs); res = P if ok else None
    except RuntimeError: res = None
    _cache[key] = res; return res


def program_bits(base, P):
    routing = base.R * base.C - len(base.type); per = {"UN": 5, "AL": 3, "JN": 4, "BR": 40, "MG": 2, "PR": 25, "SQ": 131, "LT": 2}
    return routing * 12 + sum(per[base.type[w]] for w in P.g.work) + 7 * len(P.g.holds)          # a hold: its length, 7 bits


def options(lib, task, current=None, times=None):
    """every way to run the design: [(seconds, slots, kind, base, plan)] sorted"""
    t = times or TIMES; out = []
    for b in lib:
        P = fits(b, task)
        if P:
            sec = program_bits(b, P) * t["prog_per_bit"] + (0 if (current is not None and b.name == current) else t["swap"])
            out.append((sec, b.cost(), "program on " + ("the loaded bitstream" if current == b.name else "another library bitstream (swap)"), b, P))
    # a new bitstream tailored to the design: the types its free plan needs, on the smallest grid that fits, plain routing
    nodes, ins, outs = task
    try:
        need = needs_of(G.plan9(nodes, ins, outs, 13, 13, tries=30))
        for n in (7, 9, 11, 13, 15):
            try: nb = Base(n, need, "none", 0, "new_%s" % "".join("%s%d" % kv for kv in sorted(need.items())))
            except ValueError: continue
            P = fits(nb, task)
            if P: out.append((t["build"] + t["swap"] + program_bits(nb, P) * t["prog_per_bit"], nb.cost(), "NEW bitstream (build + swap)", nb, P)); break
    except RuntimeError: pass
    return sorted(out, key=lambda x: (x[0], x[1]))


def session_cost(designs, lib, times=None, policy="library"):
    """total seconds to run a sequence of designs in order.  policy 'library': the best option each time given what is loaded (swap only when the loaded bitstream does not fit);
    'tailored': a new bitstream for every change of design (nothing is reused).  designs: list of (name, task).  (One big bitstream that hosts everything needs no swaps: its time is just the programs, see one_base_seconds.)"""
    t = times or TIMES; total = 0.0; cur = None; swaps = 0; builds = 0; seen = set()
    for nm, task in designs:
        if policy == "library":
            opts = [o for o in options(lib, task, cur, t) if not o[2].startswith("NEW")]
            sec, slots, kind, b, P = opts[0]; cur2 = b.name
            swaps += 1 if cur2 != cur else 0; total += sec; cur = cur2
        elif policy == "tailored":
            opts = [o for o in options(lib, task, None, t) if o[2].startswith("NEW")]
            if not opts: raise RuntimeError("no tailored base for " + nm)
            sec, slots, kind, b, P = opts[0]
            if nm not in seen: total += t["build"]; builds += 1; seen.add(nm)
            if cur != nm: total += t["swap"]; swaps += 1
            total += program_bits(b, P) * t["prog_per_bit"]; cur = nm
    return total, swaps, builds


def one_base_seconds(designs, big, times=None):
    """one big bitstream (a hexn_bases_v2 Base) hosting every design: programs only, no swaps"""
    t = times or TIMES; total = 0.0
    for nm, task in designs:
        P = B2.fits(big, task); assert P, nm
        total += B2.program_of(big, P, task)["config_bits_estimate"] * t["prog_per_bit"]
    return total


if __name__ == "__main__":
    T = B2.all_tasks(); lib = pattern_library()
    print("pattern library: %d bitstreams" % len(lib))
    for b in lib: print("  ", b)
    print("\nwhich designs fit which pattern (any size):")
    for nm, task in T.items():
        row = []
        for p in PATTERNS:
            fs = [b for b in lib if b.name.startswith(p) and fits(b, task)]
            row.append("%s:%s" % (p, str(min(b.R for b in fs)) if fs else "-"))
        print("  %-24s %s" % (nm, "  ".join(row)))
