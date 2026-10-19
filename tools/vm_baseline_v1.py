#!/usr/bin/env python3
"""tools/vm_baseline_v1.py -- record (or check) what the CURRENT VM delivers for every example ICM design (ledger #1269).

Why: a new FlexGrid (v2, held constants) must not change any design that already works. This tool feeds every ICM file in nano/examples the same fixed
words on the VM and saves each exit's words. Run it before the change (--write) and after (--check); any difference is listed, and the only
allowed ones are the designs the change is meant to fix.

    python3 tools/vm_baseline_v1.py --write FILE     record
    python3 tools/vm_baseline_v1.py --check FILE     compare with a recorded file, exit 1 on any difference
    --grid flex|flex2|super   which VM (default flex; flex2 = FlexGrid v2)

Entries and exits are found the way the flex generator finds them. Words fed to every entry: 7, 3, 12, 100 (fixed).
A design the VM cannot build or run is recorded as {"error": "..."} (that too is compared).
"""
import argparse
import glob
import json
import os
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
WORDS = [7, 3, 12, 100]


def load(path):
    if path.endswith(".icm-hier.json"):
        import flexsub_icm_netlist_v1 as nl
        return nl.extract(path)[1]
    from icm_v3 import IcmV3File
    return IcmV3File.load(path).records


def ports(path):
    """Entries and exits exactly as the flex generator finds them (its plan): entries = cells nothing feeds that are not constants, exits = the plan's exits."""
    import flexsub_icm_generate_v1 as g
    p = g.plan(path, True, family="flex", rings=True)
    roots = {c for c in p["const"] if not p["inputs"].get(c)}
    cells = p["cells"]
    ent = [c for c in p["order"] if not p["inputs"].get(c) and c not in roots and cells[c].core != "sequencer" and c not in p["oneshots"]]
    base = lambda c: c[:-4] if c.endswith("__in") else c          # the generator's own wrapper ids for named cells
    return [base(c) for c in ent], sorted(base(c) for c in p["exits"])


def run(path, recs, grid, ticks=1500):
    ent, ex = ports(path)
    if not ent or not ex:
        return {"note": "no entry or no exit found", "entries": ent, "exits": ex}
    if grid == "flex":
        import flex_grid_v1 as g_
        G = g_.FlexGrid
    elif grid == "flex2":
        import flex_grid_v2 as g_
        G = g_.FlexGrid2
    else:
        from unicell_super_automaton_v1 import SuperGrid as G
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = G(recs)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    core = {r.cell_id: r.core for r in recs}
    todo = {e: list(WORDS) for e in ent}
    seen = {x: [] for x in ex}
    for _ in range(ticks):
        for k, vals in todo.items():
            c = g.cells[pos[k]]
            if vals and not c.ram_data_valid and not getattr(g, "_pending", {}).get(pos[k]):
                g.inject(*pos[k], vals.pop(0))
        g.tick()
        for x in ex:
            e = g.cells[pos[x]]
            if core[x] == "adder":
                if e.adder_data_valid:
                    seen[x].append(int(e.adder_out_buffer)); e.adder_data_valid = False
            elif e.ram_data_valid:
                seen[x].append(int(e.ram_data_reg)); e.ram_data_valid = False
    # collapse the same way the card runner does (a holding exit shows one word): runs of equal words become one
    out = {}
    for x, v in seen.items():
        c = []
        for w in v:
            if not c or c[-1] != w:
                c.append(w)
        out[x] = c[:64]
    return {"entries": ent, "exits": out}


def snapshot(grid):
    res = {}
    files = sorted(glob.glob(os.path.join(ROOT, "nano", "examples", "*.icm-hier.json")) + glob.glob(os.path.join(ROOT, "nano", "examples", "card_tested", "*.icm.json")))
    for f in files:
        name = os.path.relpath(f, ROOT)
        try:
            res[name] = run(f, load(f), grid)
        except Exception as e:      # recorded, so a design that fails before and after is not a difference
            res[name] = {"error": type(e).__name__ + ": " + str(e)[:120]}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write")
    ap.add_argument("--check")
    ap.add_argument("--grid", default="flex", choices=["flex", "flex2", "super"])
    a = ap.parse_args()
    snap = snapshot(a.grid)
    if a.write:
        json.dump({"grid": a.grid, "words": WORDS, "designs": snap}, open(a.write, "w"), indent=1, sort_keys=True)
        print("wrote", a.write, "-", len(snap), "designs;", sum(1 for v in snap.values() if "error" in v), "could not run")
        return 0
    if a.check:
        old = json.load(open(a.check))["designs"]
        diffs = [n for n in sorted(set(old) | set(snap)) if old.get(n) != snap.get(n)]
        for n in diffs:
            print("DIFFERENT:", n, "\n   before:", json.dumps(old.get(n))[:300], "\n   after: ", json.dumps(snap.get(n))[:300])
        print(len(diffs), "difference(s) in", len(snap), "designs")
        return 1 if diffs else 0
    print(json.dumps(snap, indent=1)[:4000])


if __name__ == "__main__":
    sys.exit(main())
