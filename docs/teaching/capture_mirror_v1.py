#!/usr/bin/env python3
"""Capture REAL behaviour of the VM's card mirror (nano/vm_mirror_v1.py, VMSession.from_man, nano/walker_sim_v1.py, the Workbench's
set_target) for the teaching manual's "Mirror VM" page: the layout rule, fit checks of library designs at several cell counts on both MAN
files, a recorded Walker run (every ping), the combined shape + flex-width recipe, error messages and the shell repertoires.
Python VM only; nothing here simulates Verilog.   Writes docs/teaching/mirror_data.json.   Run: python3 docs/teaching/capture_mirror_v1.py
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
os.chdir(REPO)
sys.path[:0] = [os.path.join(REPO, "nano"), os.path.join(REPO, "tools")]
import icm_v3 as v3
import vm_mirror_v1 as vmm
import walker_sim_v1 as ws
import shell_compat_v1 as sc
import card_fit_v1 as cf
from vm_ai_port_v1 import VMSession
from flex_grid_v1 import FlexGrid
from workbench_v1 import WorkbenchController

MANS = {"tang": "docs/man/tang-nano-20k.man.json", "mustang": "docs/man/mustang-f100-a10.man.json"}
DESIGNS = ["add", "sub", "mul", "lif4", "fp16_add"]
COUNTS = [4, 9, 16, 25, 36, 49, 64, 100, 225, 400]
out = {"mans": {}, "layouts": {}, "designs": {}, "fit": {}, "walker": {}, "recipe": {}, "errors": {}, "shells": {}, "budgets": {}}

# --- the two MAN files: what the mirror reads from each
for k, p in MANS.items():
    m = json.load(open(p))
    nw = ((m.get("device") or {}).get("logic") or {}).get("native_width")
    out["mans"][k] = {"path": p, "card_id": vmm.pa.load_man_identity(p)["card_id"], "native_width": nw}

# --- the layout rule, real functions, for every cell count 1..400 (the page recomputes it in JS and is tested against these)
out["layouts"] = {str(n): list(vmm.pa.grid_dims(n)) for n in list(range(1, 41)) + COUNTS + [50, 60, 80, 120, 144, 150, 200, 300]}

# --- designs: positions and the real fit result at each count, on both cards
for d in DESIGNS:
    path = f"nano/library_std/{d}.icm.json"
    icm = v3.IcmV3File.load(path)
    out["designs"][d] = {"path": path, "cells": [{"id": r.cell_id, "row": r.row, "col": r.col, "core": r.core, "io": r.io_name} for r in icm.records],
                         "extent": [max(r.row for r in icm.records) + 1, max(r.col for r in icm.records) + 1]}
    out["fit"][d] = {}
    for n in COUNTS:
        per = {}
        for k, mp in MANS.items():
            b = vmm.load_mirror_bounds(mp, n)
            pr = vmm.check_records_fit(icm.records, b)
            per[k] = {"rows": b.rows, "cols": b.cols, "problems": len(pr), "first": pr[0] if pr else None, "card_id": b.card_id}
        out["fit"][d][str(n)] = per

# smallest cell count (1..400) whose real layout holds the whole design, and whether the two MAN files ever differ in the fit result
for d in DESIGNS:
    icm = v3.IcmV3File.load(f"nano/library_std/{d}.icm.json")
    mn = next((n for n in range(1, 401) if not vmm.check_records_fit(icm.records, vmm.load_mirror_bounds(MANS["tang"], n))), None)
    out["designs"][d]["min_cells"] = mn
    out["designs"][d]["cards_differ"] = any(out["fit"][d][str(n)]["tang"]["problems"] != out["fit"][d][str(n)]["mustang"]["problems"] or out["fit"][d][str(n)]["tang"]["rows"] != out["fit"][d][str(n)]["mustang"]["rows"] for n in COUNTS)

# --- capacity (what the mirror does NOT check): cell budget per card at the measured per-position costs
for card, shells in (("tang", ("nano_lean", "adder_lean", "adder_full")), ("mustang", ("super_v3",))):
    for sh in shells:
        t = cf.target_from_man(MANS[card], rows=8, cols=8, shell=sh)
        out["budgets"][f"{card}/{sh}"] = {"budget": t.cell_budget, "max_cells": t.max_cells}

# --- the Walker: record every ping on a mirrored session of the library adder at 400 cells on the Tang's MAN file
log = []
orig = ws.ping
def rec_ping(session, row, col, direction):
    a = orig(session, row, col, direction)
    log.append({"at": [row, col], "dir": direction, "answer": a})
    return a
ws.ping = rec_ping
s = VMSession.from_man(MANS["tang"], 400, icm_path="nano/library_std/add.icm.json")
origin = tuple(next((c["row"], c["col"]) for c in out["designs"]["add"]["cells"] if c["io"] == "a"))
res = ws.walk(s, start=origin)
log_walk = list(log)
shape = ws.to_shape(res, s.mirror_bounds.card_id)
out["walker"] = {"design": "add", "cells": 400, "origin": list(origin), "pings": log_walk, "ping_count": res.ping_count,
                 "found": len(res.discovered), "edges": len(res.edges), "design_cells": len(out["designs"]["add"]["cells"]),
                 "shape_keys": sorted(shape.keys()), "shape_sample": {k: shape[k] for k in ("shape_version", "card_id", "discovery_method", "origin", "ping_count")},
                 "shape_cell0": shape["cells"][0], "shape_edge0": shape["edges"][0],
                 "edge_list": [[list(a), da, list(b), db] for a, da, b, db in res.edges]}
# a walk from an empty position
try:
    ws.walk(s, start=(19, 19))
except Exception as e:
    out["walker"]["no_target"] = {"type": type(e).__name__, "msg": str(e)}
# a design with a gap: two separate pieces -> the walk finds only the piece the origin is in
ws.ping = orig

# --- the recipe: shape check (SuperGrid mirror) vs behaviour (FlexGrid at the MAN's native width), and both together
add = v3.IcmV3File.load("nano/library_std/add.icm.json")
pos = {r.io_name: (r.row, r.col) for r in add.records if r.io_name}
def runadd(sess, w):
    sess.inject(*pos["a"], 200000); sess.inject(*pos["b"], 100000)
    ticks = sess.run_to_quiescence()
    return {"ticks": ticks, "r": sess.describe_cell(*pos["r"])["ram"]["data_reg"]}
a = VMSession.from_man(MANS["tang"], 400, icm_path="nano/library_std/add.icm.json")
nw = out["mans"]["tang"]["native_width"]
b = vmm.load_mirror_bounds(MANS["tang"], 400)
probs = vmm.check_records_fit(add.records, b)
f = VMSession(FlexGrid(add.records, width=nw)); f.mirror_bounds = b
out["recipe"] = {"native_width": nw, "from_man": {"grid": type(a.grid).__name__, "width": a.grid.width, **runadd(a, 32)},
                 "flex_by_hand": {"grid": type(f.grid).__name__, "width": f.grid.width, "problems": len(probs), **runadd(f, nw)},
                 "expected_wrap": (200000 + 100000) % (1 << nw)}

# --- errors, in the code's own words
E = {}
def cap(key, fn):
    try:
        fn(); E[key] = "no error"
    except Exception as e:
        E[key] = f"{type(e).__name__}: {str(e)[:230]}"
cap("none_given", lambda: VMSession.from_man(MANS["tang"], 400))
cap("two_given", lambda: VMSession.from_man(MANS["tang"], 400, dsl="x", python="y"))
cap("zero_cells", lambda: VMSession.from_man(MANS["tang"], 0, icm_path="nano/library_std/add.icm.json"))
cap("missing_man", lambda: VMSession.from_man("docs/man/nope.json", 4, icm_path="nano/library_std/add.icm.json"))
cap("too_small", lambda: VMSession.from_man(MANS["tang"], 4, icm_path="nano/library_std/add.icm.json"))
out["errors"] = E
wb = WorkbenchController()
r1 = wb.set_target(MANS["tang"], 400)
r2 = wb.set_target(MANS["tang"], 400, "v3")
r3 = wb.set_target(MANS["tang"], 400, "v99")
out["errors"]["workbench"] = {"ok": r1["target"], "with_shell_v3": r2["target"], "unknown_shell": r3["error"], "grid_class": type(wb.session.grid).__name__}
cli = subprocess.run([sys.executable, "nano/llvm_cli_v1.py", "x.ll", "--man", MANS["tang"]], capture_output=True, text=True)
out["errors"]["llvm_cli_man_only"] = {"rc": cli.returncode, "stderr": cli.stderr.strip()}

# --- shell repertoires (which core kinds each assembler shell instantiates), the check set_target(shell=) applies
for name, path in sc.discover_shell_versions().items():
    out["shells"][name] = sorted(sc.supported_cores(path))

json.dump(out, open(os.path.join(HERE, "mirror_data.json"), "w"), indent=1)
print("wrote mirror_data.json", os.path.getsize(os.path.join(HERE, "mirror_data.json")))
print(out["mans"], out["walker"]["ping_count"], out["walker"]["found"], out["walker"]["edges"], out["walker"].get("no_target"))
print(json.dumps(out["recipe"])); print(json.dumps(out["errors"], indent=1)[:2500]); print(out["budgets"]); print({k: len(v) for k, v in out["shells"].items()})
for d in DESIGNS: print(d, out["designs"][d]["min_cells"], out["designs"][d]["cards_differ"], out["designs"][d]["extent"], {n: out["fit"][d][str(n)]["tang"]["problems"] for n in COUNTS})
