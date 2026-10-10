#!/usr/bin/env python3
"""tools/nor_adder_v1.py -- a 32-bit adder built ONLY from `nano` gate cells and shift cells (ledger #1036 addendum 48).

Word-level Kogge-Stone parallel prefix, every step one word-wide cell:
    G0 = A & B        P0 = A ^ B
    for k in 1, 2, 4, 8, 16:   G = G | (P & (G << k))      P = P & (P << k)
    sum = P0 ^ (G << 1)                                    (mod 2^32: the carry out is dropped, like the plain adder cell's sum)
A shift is a relay ram with a shift addon (pure wiring). The nano cells use topologies AND 0x007, OR 0x024, XOR 0x0BC, which the nano builds from NOR gates.
Wiring cells: plain relay rams (some carrying the shift add-on) and one crossing tile; no adder, comparator or other word cell is used.
Layout: the hand-drawn tile `build_tight` (80 cells). Automatic placement was tried first and is not kept: a hand grid of lanes gave 647 cells, simulated annealing could not be routed.

    python3 tools/nor_adder_v1.py --measure   build, assemble against the Tang Nano 20K MAN, synthesise (yosys synth_gowin -nowidelut), time it in FlexGrid, write docs/measurements/nor_adder_v1.json
    python3 tools/nor_adder_v1.py --check     exit 1 if that file differs from a fresh measurement
Test/design-support tooling: it only writes a Grid; the RTL generator and the VM stay the oracle."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flex_layout_v1 as fl  # noqa: E402

AND, OR, XOR = 0x007, 0x024, 0x0BC
fl.PAIR = tuple(fl.PAIR) + ("nano",)       # the layout engine's tie check applies to the nano too (the generator refuses a same-hop pair)


def shift_addon(k, left=True):
    return {"shift_en": 1, "direction": 0 if left else 1, "shift_amt": k}


def netlist(ks=(1, 2, 4, 8, 16)):
    """Returns (cells, nets): cells {name: (core, cfg, addon)}, nets [(src, dst)]."""
    cells, nets = {}, []
    nano = lambda t: ("nano", {"topology": t, "ready": 1}, None)
    cells["A"] = ("ram", None, None)
    cells["B"] = ("ram", None, None)
    cells["Bd"] = ("ram", None, None)           # B one hop later than A, so the two operands of the first gates never tie
    cells["G0"], cells["P0"] = nano(AND), nano(XOR)
    nets += [("B", "Bd"), ("A", "G0"), ("Bd", "G0"), ("A", "P0"), ("Bd", "P0")]
    cells["P0b"] = ("ram", None, None)                   # P0 is needed again at the very end: its own long lane
    cells["P0f"] = ("ram", None, None)                   # a nano drives ONE neighbour (a fan-out relay does the splitting): two inputs + two outputs would use all four faces
    nets += [("P0", "P0f"), ("P0f", "P0b")]
    p = "P0f"
    cells["r"] = ("ram", None, None)                     # one relay on the G lane: it keeps G a hop behind P, so the AND of the first stage never sees both operands in the same hop
    nets += [("G0", "r")]
    g = "r"
    for i, k in enumerate(ks):
        s = f"s{k}"
        last = i == len(ks) - 1
        cells[f"gf{s}"] = ("ram", None, None)              # fan-out relay: a nano drives ONE neighbour, the relay splits (two inputs + two outputs would use all four faces)
        cells[f"Gs{s}"] = ("ram", None, shift_addon(k))
        cells[f"T{s}"] = nano(AND)
        cells[f"Gn{s}"] = nano(OR)
        cells[f"pf{s}"] = ("ram", None, None)              # fan-out relay for P (in the last stage a plain pass-through: P feeds only T)
        nets += [(g, f"gf{s}"), (p, f"pf{s}"), (f"gf{s}", f"Gs{s}"), (f"pf{s}", f"T{s}"), (f"Gs{s}", f"T{s}"), (f"gf{s}", f"Gn{s}"), (f"T{s}", f"Gn{s}")]
        if not last:                                       # the last stage needs no new P: nothing would consume it
            cells[f"Ps{s}"] = ("ram", None, shift_addon(k))
            cells[f"q{s}"] = ("ram", None, None)           # three cells that all feed each other cannot sit on a grid (it is two-coloured): one relay on the shifted edge
            cells[f"Pn{s}"] = nano(AND)
            nets += [(f"pf{s}", f"Ps{s}"), (f"Ps{s}", f"q{s}"), (f"q{s}", f"Pn{s}"), (f"pf{s}", f"Pn{s}")]
            p = f"Pn{s}"
        g = f"Gn{s}"
    cells["C"] = ("ram", None, shift_addon(1))
    cells["S"] = nano(XOR)
    cells["E"] = ("ram", None, None)                      # the exit: the sum is read here
    nets += [(g, "C"), ("P0b", "S"), ("C", "S"), ("S", "E")]
    return cells, nets


def records(g):
    """Grid.records() with the nano's config in the nano's own vocabulary: it has a routing_mask (where its result goes) and no upstream mask."""
    out = []
    for r in g.records():
        if r.core == "nano":
            cc = dict(r.core_config)
            cc["routing_mask"] = cc.pop("downstream_mask")
            cc.pop("upstream_mask", None)
            r = type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=cc, addon_config=r.addon_config, io_name=r.io_name, preload_value=r.preload_value)
        out.append(r)
    return out


def build_tight(ks=(1, 2, 4, 8, 16), rows=20, cols=50, entry=((0, 0), (3, 0), (3, 1))):
    """Hand-drawn tile: each stage is an 8-cell block whose neighbours are LINKED directly (no relay), only the long lanes (the operands in, P0 to the sum) are routed. Stage i, base column b:
        row 0:  gf(b)  Gn(b+1)          G lane, flows east:   Gn -> next gf
        row 1:  Gs(b)  T(b+1)
        row 2:         pf(b+1) Pn(b+2)  P lane, flows east:   Pn -> next pf
        row 3:         Ps(b+1) q(b+2)"""
    cells, nets = netlist(ks)
    X0 = 6
    pos = {"G0": (0, X0 - 3), "r": (0, X0 - 2), "P0": (2, X0 - 1), "P0f": (2, X0), "P0b": (4, X0), "A": entry[0], "B": entry[1], "Bd": entry[2]}
    # (0,X0-1) stays free: gf0 sits at (0, X0)
    pos["r"] = (0, X0 - 1)
    pos["G0"] = (0, X0 - 2)
    for i, k in enumerate(ks):
        s, b = f"s{k}", X0 + 2 * i
        pos.update({f"gf{s}": (0, b), f"Gs{s}": (1, b), f"Gn{s}": (0, b + 1), f"T{s}": (1, b + 1), f"pf{s}": (2, b + 1), f"Ps{s}": (3, b + 1), f"q{s}": (3, b + 2), f"Pn{s}": (2, b + 2)})
    bl = X0 + 2 * len(ks)
    pos.update({"C": (0, bl - 1 + 1), "S": (0, bl + 1), "E": (0, bl + 2)})
    g = fl.Grid(rows=rows, cols=cols)
    for name, (core, cfg, addon) in cells.items():
        g.add(name, pos[name][0], pos[name][1], core, cfg, addon)
    long_nets = []
    for a, b in nets:
        if abs(pos[a][0] - pos[b][0]) + abs(pos[a][1] - pos[b][1]) == 1:
            g.link(a, b)
        else:
            long_nets.append((a, b))
    g.route_nets(long_nets, rounds=300)
    fix_ties(g)
    return g, long_nets


def fix_ties(g, depth=4):
    """Break the same-hop ties of the layout by lengthening the four routed operand paths into G0 / P0 (two relays each time). A search over short sequences; the first one that leaves no tie is kept."""
    import copy
    import itertools
    keys = (("Bd", "G0"), ("A", "G0"), ("Bd", "P0"), ("A", "P0"))
    if not g.problems():
        return []
    for n_ in range(1, depth + 1):
        for seq in itertools.product(keys, repeat=n_):
            h = copy.deepcopy(g)
            try:
                for key in seq:
                    h._lengthen(*key)
            except fl.LayoutError:
                continue
            if not h.problems():
                g.nodes, g.links, g.routes, g.crossed = h.nodes, h.links, h.routes, h.crossed
                return list(seq)
    raise fl.LayoutError(f"ties remain: {g.problems()[:3]}")


def plain_adder_grid():
    """The comparison: the dedicated adder cell, with the same one-hop stagger on B that the NOR adder uses (entries A, B -> Bd -> adder -> E)."""
    p = fl.Grid(rows=5, cols=5)
    p.add("A", 0, 2)
    p.add("B", 3, 2)
    p.add("Bd", 2, 2)
    p.add("ADD", 1, 2, "adder")
    p.add("E", 1, 3)
    p.link("A", "ADD")
    p.link("B", "Bd")
    p.link("Bd", "ADD")
    p.link("ADD", "E")
    assert p.problems() == []
    return p


def ticks_to_result(recs):
    """FlexGrid ticks from injecting A and B to a valid, correct sum at E."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nano"))
    import flex_grid_v1 as fg
    G = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    a, b = 123456789, 987654321
    G.inject(*pos["A"], a)
    G.inject(*pos["B"], b)
    for t in range(1, 2000):
        G.tick()
        c = G.cells[pos["E"]]
        if c.ram_data_valid:
            assert c.ram_data_reg == a + b
            return t
    raise AssertionError("no result")


def synth_counts(recs, name):
    """Assemble through project_assemble_v1 -s flex --icm --man (Tang Nano 20K), then run the .ys it writes. Returns the yosys cell counts."""
    import json
    import re
    import subprocess
    import tempfile
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nano"))
    from icm_v3 import IcmV3File
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = tempfile.mkdtemp(prefix="noradd_")
    IcmV3File(name=name, records=recs).save(os.path.join(d, name + ".icm"))
    out = os.path.join(d, "out")
    r = subprocess.run([sys.executable, os.path.join(root, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", os.path.join(d, name + ".icm"), "--man",
                        os.path.join(root, "docs", "man", "tang-nano-20k.man.json"), "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    ys = next(f for f in os.listdir(out) if f.endswith(".ys"))
    y = subprocess.run(["yosys", "-s", ys], cwd=out, capture_output=True, text=True).stdout
    c = {}
    for line in y.split("Number of cells")[-1].splitlines():
        p = line.split()
        if len(p) == 2 and p[1].isdigit():
            c[p[0]] = int(p[1])
    asm = json.load(open(os.path.join(out, "ASSEMBLY.json")))
    return {"assembled_cells": asm["cells"], "LUT4": sum(v for k, v in c.items() if k.startswith("LUT")), "ALU": c.get("ALU", 0), "DFF": sum(v for k, v in c.items() if k.startswith("DFF")),
            "yosys_cells": c}


def measure():
    g, _ = build_tight()
    recs = records(g)
    cores = {}
    for r in recs:
        cores[r.core] = cores.get(r.core, 0) + 1
    p = plain_adder_grid()
    return {"what": "32-bit add, mod 2^32, flex line, whole design incl. entry/exit rams; yosys synth_gowin -nowidelut via project_assemble_v1 -s flex --icm --man tang-nano-20k; SYNTHESIS ONLY",
            "nor_adder": dict(placed_cells=len(recs), by_core=cores, logic_cells=sum(1 for r in recs if r.core == "nano"), ticks_flexgrid=ticks_to_result(recs), **synth_counts(recs, "nor_adder")),
            "adder_cell": dict(placed_cells=len(p.nodes), ticks_flexgrid=ticks_to_result(p.records()), **synth_counts(p.records(), "plain_adder"))}


JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "measurements", "nor_adder_v1.json")

if __name__ == "__main__":
    import json
    if len(sys.argv) < 2 or sys.argv[1] not in ("--measure", "--check"):
        print(__doc__)
        sys.exit(2)
    m = measure()
    if sys.argv[1] == "--measure":
        json.dump(m, open(JSON, "w"), indent=1, sort_keys=True)
        print(json.dumps({k: {x: y for x, y in v.items() if x != "yosys_cells"} for k, v in m.items() if isinstance(v, dict)}, indent=1))
    else:
        ok = json.load(open(JSON)) == json.loads(json.dumps(m))
        print("nor_adder_v1.json matches a fresh measurement" if ok else "nor_adder_v1.json is OUT OF DATE")
        sys.exit(0 if ok else 1)
