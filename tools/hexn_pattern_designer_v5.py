#!/usr/bin/env python3
"""hexn_pattern_designer_v5 = designer_v4 on bases_v7 / wrgrid_v16 (3 Nov 2026); nothing else changed.
hexn_pattern_designer_v4 = designer_v3 on bases_v6 / wrgrid_v15 (3 Nov 2026); nothing else changed.
hexn_pattern_designer_v3 = designer_v2 on bases_v5 / wrgrid_v14 (3 Nov 2026); nothing else changed.
hexn_pattern_designer_v1: the PATTERN DESIGNER (2 Nov 2026, Alan 14:44: a design-specific bitstream is an option, fine on a Tang, but on a Kintex it takes an hour or two to build; so the patterns are PRELOADED CONCEPTS, and that leads to a pattern designer).
Given a WORKLOAD (the designs users bring, with how often) and a device (slot budget, build time), it designs a small set of PATTERNS to build and preload once: for each pattern a recipe (grid size, how many cells of each type, where the RAM layers or bands are), which designs it hosts, its slots.  Designs no pattern hosts are listed: those are the only ones that would need a design-specific build.
  1. candidate recipes come from the workload itself: the type mix each design needs (taken from its free plan), the unions of two such mixes, and variants with fewer join cores when RAM cells are present (a hold replaces a join for the add family), each with RAM none / two layers / a band every 4th column, on the smallest grids that can hold it (and one size up);
  2. a candidate hosts a design only if the planner places AND routes it on that exact recipe and the simulation equals the reference (hexn_bases_v3.fits);
  3. greedy choice: repeatedly take the pattern that adds the most workload weight (ties: fewer slots) until K patterns are chosen, no pattern adds anything, or all are covered.
Then session_report() prices a run of designs with the chosen patterns against design-specific builds, with the device's build time.  The recipes are the OUTPUT (nothing is built: a pattern is only a layout until it is synthesised and placed-and-routed on the chip).  Costs are the v9 mix of measured and estimated slot counts, no place and route.  The greedy choice is not guaranteed optimal."""
import os, sys, itertools, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_bases_v7 as B3
import hexn_wrgrid_v16 as G
from hexn_bases_v1 import needs_of

RAMS = [("none", 0), ("lead2", 1), ("every4", 0)]


def recipe_name(r):
    c = r["counts"]; n = r["n"]
    ctl = "".join(k for k in ("BR", "MG", "SQ", "PR") if c.get(k))
    mix = "J%d" % c.get("JN", 0) + ("U%d" % c["UN"] if c.get("UN") else "") + ("+" + ctl if ctl else "")
    return "%s_%d%s" % (mix, n, "" if r["ram"] == "none" else "_" + r["ram"])


def make_base(r):
    ram, lead = r["ram"], (1 if r["ram"] == "lead2" else 0)
    b = B3.Base(r["n"], r["counts"], "every4" if ram == "every4" else ram, lead, None)
    b.name = recipe_name(r); return b


def pattern_file(recipe):
    """the CARD-AGNOSTIC description of a pattern (the analogue of an ICM file for a whole bitstream): the grid, the type of every work cell, the RAM routing cells, nothing about any card.  A card's assembler turns it into that card's bitstream (hours on a Kintex, minutes on a Tang): that step is the expensive one, so it is done once per pattern, never per design; designs are then only PROGRAMS (hexn_bases_v2.program_of) for it, checked on the Python mirror (the simulator) before anything is loaded."""
    b = make_base(recipe)
    return dict(format="hexn-pattern-v1", name=b.name, rows=b.R, cols=b.C, lead_k=b.lead_k, recipe=dict(recipe),
                work_cells=[dict(r=r, c=c, type=t) for (r, c), t in sorted(b.type.items())], ram_cells=[list(x) for x in sorted(b.ram)],
                slots_estimate=b.cost(), note="slots: measured for the new cores and the join core, estimates for the rest, no place and route")


def candidates(workload, budget, sizes=(7, 9, 11)):
    """workload: {name: (task, weight)} -> list of recipes"""
    need = {}
    for nm, (task, w) in workload.items():
        P = G.plan9(task[0], task[1], task[2], 13, 13, tries=30); need[nm] = needs_of(P)
    mixes = {tuple(sorted(d.items())) for d in need.values()}
    for a, b in itertools.combinations(list(mixes), 2):
        da, db = dict(a), dict(b)
        mixes.add(tuple(sorted({k: max(da.get(k, 0), db.get(k, 0)) for k in set(da) | set(db)}.items())))
    out = []; seen = set()
    for m in sorted(mixes):
        base = dict(m)
        for ram, _ in RAMS:
            for dj in ((0,) if ram == "none" else (0, 1, 2)):
                c = dict(base)
                if dj:
                    if c.get("JN", 0) - dj < 0: continue
                    c["JN"] -= dj
                c = {k: v for k, v in c.items() if v}
                if not c: continue
                for n in sizes:
                    key = (tuple(sorted(c.items())), ram, n)
                    if key in seen: continue
                    try: b = B3.Base(n, c, "every4" if ram == "every4" else ram, 1 if ram == "lead2" else 0)
                    except ValueError: continue
                    if b.cost() > budget: continue
                    seen.add(key); out.append(dict(counts=c, ram=ram, n=n))
    return out, need


def hosts(recipe, workload, need):
    """the designs this recipe can host (cheap necessary test first, then the real fit)"""
    b = make_base(recipe); res = set()
    for nm, (task, w) in workload.items():
        nd = need[nm]; short = sum(max(0, nd.get(k, 0) - b.fill.get(k, 0)) for k in nd if k != "JN") + (max(0, nd.get("JN", 0) - b.fill.get("JN", 0)) if recipe["ram"] == "none" else max(0, nd.get("JN", 0) - b.fill.get("JN", 0) - 2))
        if short: continue
        if B3.fits(b, task): res.add(nm)
    return res


def design_patterns(workload, budget=B3.TIMES and 20000, K=4, sizes=(7, 9, 11), verbose=False):
    cands, need = candidates(workload, budget, sizes)
    if verbose: print("%d candidate recipes" % len(cands))
    cover = {i: hosts(r, workload, need) for i, r in enumerate(cands)}
    weight = {nm: w for nm, (t, w) in workload.items()}
    chosen = []; left = set(workload)
    while len(chosen) < K and left:
        best = max(cover, key=lambda i: (sum(weight[n] for n in cover[i] & left), -make_base(cands[i]).cost()))
        gain = cover[best] & left
        if not gain: break
        chosen.append((cands[best], sorted(gain))); left -= gain
    return chosen, sorted(left)


def session_report(workload, chosen, left, sequence, device="tang20k"):
    """seconds to run `sequence` (a list of design names) on the chosen patterns vs building a bitstream for every different design"""
    t = B3.DEVICES[device]; lib = [make_base(r) for r, _ in chosen]
    des = [(n, workload[n][0]) for n in sequence if n not in left]
    lib_s, swaps, _ = B3.session_cost(des, lib, t, "library") if des else (0, 0, 0)
    distinct = len({n for n in sequence}); tail_s = distinct * t["build"] + len(sequence) * t["swap"]
    unmatched = len([n for n in sequence if n in left])
    return dict(pattern_seconds=lib_s + unmatched * (t["build"] + t["swap"]), swaps=swaps, tailored_seconds=tail_s, unmatched_runs=unmatched)


if __name__ == "__main__":
    import time
    t0 = time.time(); T = B3.B2.all_tasks()
    freq = {n: (3 if n.startswith("old/") else 1) for n in T}
    workload = {n: (T[n], freq[n]) for n in T}
    chosen, left = design_patterns(workload, budget=20000, K=4, verbose=True)
    print("\nPATTERNS TO PRELOAD (%.0f s to design):" % (time.time() - t0))
    for r, gain in chosen:
        b = make_base(r); print("  %s   %d slots  hosts %d designs: %s" % (b.name, b.cost(), len(gain), ", ".join(x.split('/')[1] for x in gain)))
    print("  not hosted by any pattern (would need a design-specific build):", left or "none")
