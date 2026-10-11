#!/usr/bin/env python3
"""Capture REAL Workbench behaviour for the teaching manual's second Workbench section (which grid it builds, its options, what a hand-placed
FlexGrid does inside it). Real HTTP server on a free local port plus direct WorkbenchController calls. Python VM only.
Writes docs/teaching/wb_data.json.   Run: python3 docs/teaching/capture_wb_v1.py
"""
import json, os, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
os.chdir(REPO)
sys.path[:0] = [os.path.join(REPO, "nano"), os.path.join(REPO, "tools")]
import icm_v3 as v3
import workbench_v1 as wbm
from workbench_v1 import WorkbenchController
from vm_ai_port_v1 import VMSession
from flex_grid_v1 import FlexGrid

TANG = "docs/man/tang-nano-20k.man.json"
add = v3.IcmV3File.load("nano/library_std/add.icm.json")
pos = {r.io_name: (r.row, r.col) for r in add.records if r.io_name}
out = {}

def result(wb):
    st = wb.state()["state"]; c = st["cells"]["%d,%d" % pos["r"]]
    return {"grid": type(wb.session.grid).__name__, "width": wb.session.grid.width, "r": c["ram"]["data_reg"], "valid": c["ram"]["data_valid"], "tick": st["tick_count"]}
def drive(wb, a=200000, b=100000, n=18):
    wb.inject(*pos["a"], a); wb.inject(*pos["b"], b)
    for _ in range(n): wb.step(1)
    return result(wb)

# 1. every route in: which grid
src = open(os.path.join(REPO, "nano/workbench_v1.py")).read()
out["grid_sites"] = [{"line": i + 1, "text": l.strip()} for i, l in enumerate(src.splitlines()) if "SuperGrid(" in l and "import" not in l]
out["flex_mentions"] = src.count("FlexGrid")

# 2. standard route
w = WorkbenchController(); w.load_icm("nano/library_std/add.icm.json")
out["std_route"] = drive(w)

# 3. a file that declares 18 bits, loaded by the Workbench
f18 = v3.IcmV3File(name="add18", records=add.records, description="min_bit_width 18", min_bit_width=18)
p18 = "/tmp/_wb_add18.icm.json"; f18.save(p18)
w = WorkbenchController(); r = w.load_icm(p18)
out["declared_18"] = {"declared": f18.min_bit_width, "ok": r["ok"], **drive(w)}

# 4. a FlexGrid placed into the controller by hand
w = WorkbenchController(); w.session = VMSession(FlexGrid(add.records, width=18))
out["flex_by_hand"] = drive(w)
st = w.state()["state"]; out["state_keys"] = sorted(st.keys())
# ... what the next ordinary action does to it
r = w.load_demo("adder_pair"); out["flex_then_demo"] = {"ok": r["ok"], "grid": type(w.session.grid).__name__, "width": w.session.grid.width}
w.session = VMSession(FlexGrid(add.records, width=18)); w._records = {(x.row, x.col): x for x in add.records}
sv = w.save_icm("/tmp/_wb_flex_saved.icm.json", "flexsaved"); out["flex_save"] = {"ok": sv["ok"], "cells": sv["cell_count"], "min_bit_width_in_file": json.load(open("/tmp/_wb_flex_saved.icm.json")).get("min_bit_width")}

# 5. targets
w = WorkbenchController(); t = w.set_target(TANG, 400); out["target_400"] = {"ok": t["ok"], "grid": type(w.session.grid).__name__}
out["target_then_load_400"] = {k: v for k, v in w.load_icm("nano/library_std/add.icm.json").items() if k in ("ok", "error")}
w = WorkbenchController(); w.set_target(TANG, 100); r = w.load_icm("nano/library_std/add.icm.json")
out["target_then_load_100"] = {"ok": r["ok"], "error": (r.get("error") or "")[:230]}
w = WorkbenchController(); w.set_target(TANG, 400, "v3"); r = w.load_icm("nano/library_std/add.icm.json"); out["target_shell_v3_load"] = {"ok": r["ok"], "error": (r.get("error") or "")[:200]}

# 6. a real HTTP server: what the page and a script can see
server = wbm.serve(0, open_browser=False); port = server.server_port
def get(path):
    return json.load(urllib.request.urlopen(f"http://localhost:{port}{path}"))
def post(path, body):
    rq = urllib.request.Request(f"http://localhost:{port}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}); return json.load(urllib.request.urlopen(rq))
out["http"] = {"state_keys": sorted(get("/state").keys()), "target": get("/target"), "shells": sorted(get("/shells").keys()),
               "set_target": post("/set_target", {"man_path": TANG, "cells": 400})["target"], "run_status": get("/run_status"),
               "demos": sorted(get("/demos")["demos"].keys())}
page = urllib.request.urlopen(f"http://localhost:{port}/").read().decode()
out["http"]["page_mentions_width"] = bool(re.search(r"FlexGrid|merge_mode|min_bit_width|bit width", page, re.I)); out["http"]["page_bytes"] = len(page)
server.shutdown()
out["cli"] = {"usage": "python3 nano/workbench_v1.py [port]", "default_port": 7420, "host": "localhost", "opens_browser": True}
json.dump(out, open(os.path.join(HERE, "wb_data.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("grid_sites",)}, indent=1)[:3500]); print(out["grid_sites"])
