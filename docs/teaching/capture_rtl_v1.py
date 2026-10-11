#!/usr/bin/env python3
"""Capture REAL outputs for the teaching manual's Verilog/RTL and MAN tabs.
Runs tools/project_assemble_v1.py on one ICM (nano/library_std/add.icm.json and mul.icm.json)
against the two MAN files in docs/man/, reads the generated ASSEMBLY.json / .ys / .cst, and
reads the MAN files themselves.  Writes docs/teaching/rtl_data.json (embedded by the builder).
Nothing in the JSON is typed by hand.   Run: python3 docs/teaching/capture_rtl_v1.py
"""
import json, os, subprocess, sys, tempfile, re, glob, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TMP = tempfile.mkdtemp()
MANS = {"tang": "docs/man/tang-nano-20k.man.json", "mustang": "docs/man/mustang-f100-a10.man.json"}

def run(args, name):
    out = os.path.join(TMP, name)
    r = subprocess.run([sys.executable, "tools/project_assemble_v1.py", *args, "--output", out],
                       cwd=REPO, capture_output=True, text=True)
    res = {"cmd": "python3 tools/project_assemble_v1.py " + " ".join(args) + " --output DIR",
           "ok": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()[-400:]}
    if r.returncode == 0:
        files = sorted(os.listdir(out)); res["files"] = {}
        for f in files:
            p = os.path.join(out, f); res["files"][f] = sum(1 for _ in open(p, errors="replace"))
        res["sha"] = {f: hashlib.sha1(open(os.path.join(out, f), "rb").read()).hexdigest()[:10] for f in files if f != "ASSEMBLY.json"}
        for f in files:
            if f.endswith(".qsf"):
                res["qsf_key"] = [l for l in open(os.path.join(out, f)).read().splitlines()
                                  if re.search(r"\b(FAMILY|DEVICE|PIN_E23)\b", l)][:4]
        ap = os.path.join(out, "ASSEMBLY.json")
        if os.path.exists(ap):
            a = json.load(open(ap))
            res["assembly"] = {k: a.get(k) for k in ("family", "top", "cells", "built_width", "synth_flags",
                                                       "synth_flags_reason", "output_latency_cycles", "pad_relay_cells", "exits")}
        for f in files:
            if f.endswith(".ys"): res["ys"] = open(os.path.join(out, f)).read().strip().splitlines()
            if f.endswith(".cst"): res["cst_head"] = open(os.path.join(out, f)).read().splitlines()[:8]; res["cst_lines"] = res["files"][f]
            if f.endswith(".v") and f.startswith(("icm_", "flexsub_")): res["top_head"] = open(os.path.join(out, f)).read().splitlines()[:6]
    return res

out = {"runs": {}}
for key, man in MANS.items():
    mf = os.path.join(REPO, man)
    out["runs"][f"add_flex_{key}"] = run(["-s", "flex", "--icm", "nano/library_std/add.icm.json", "--man", man], f"af_{key}")
    out["runs"][f"add_sub_{key}"] = run(["-s", "sub", "--icm", "nano/library_std/add.icm.json", "--man", man], f"as_{key}")
    out["runs"][f"mul_sub_auto_{key}"] = run(["-s", "sub", "--icm", "nano/library_std/mul.icm.json", "--man", man, "--mul", "auto"], f"ma_{key}")
    out["runs"][f"mul_sub_dsp_{key}"] = run(["-s", "sub", "--icm", "nano/library_std/mul.icm.json", "--man", man, "--mul", "dsp"], f"md_{key}")
    out["runs"][f"chain_flex_{key}"] = run(["-s", "flex", "-S", "adder", "--cells", "4", "--man", man], f"cf_{key}")
out["runs"]["quartus_mustang"] = run(["--man", MANS["mustang"], "--cells", "4", "-S", "adder_cell"], "qm")
out["runs"]["quartus_tang"] = run(["--man", MANS["tang"], "--cells", "4", "-S", "adder_cell"], "qt")
out["runs"]["add_flex_w18_nomn"] = run(["-s", "flex", "--icm", "nano/library_std/add.icm.json", "-w", "18"], "nm")

# --- MAN files themselves
def brief(v, n=120):
    s = json.dumps(v); return s if len(s) <= n else s[:n] + "…"
mans = {}
for key, man in MANS.items():
    d = json.load(open(os.path.join(REPO, man)))
    mans[key] = {
        "path": man, "bytes": os.path.getsize(os.path.join(REPO, man)),
        "top_keys": list(d.keys()),
        "top_sizes": {k: len(json.dumps(v)) for k, v in d.items()},
        "man_version": d.get("man_version"), "card_id": d.get("card_id"), "vendor": d.get("vendor"),
        "generated": d.get("generated"), "generated_by": (d.get("generated_by") or "")[:160],
        "device_keys": list(d["device"].keys()),
        "part": d["device"]["part"], "family": d["device"]["family"],
        "capabilities": d.get("capabilities"),
        "synthesis": d.get("synthesis"),
        "native_width": d["device"].get("logic", {}).get("native_width"),
        "logic": {k: d["device"]["logic"][k] for k in ("unit", "lut4_total", "ff_total", "tiles") if k in d["device"].get("logic", {})},
        "alm_total": d["device"].get("alm_total"),
        "dsp_total_blocks": d["device"].get("dsp", {}).get("total_blocks"),
        "dsp_primitives": [p["name"] for p in d["device"].get("dsp", {}).get("primitives", [])],
        "board_keys": list(d.get("board", {}).keys()),
        "verification": d.get("verification"),
        "has_cell_costs": "cell_costs" in d,
    }
    if "cell_costs" in d:
        cc = d["cell_costs"]
        mans[key]["cell_costs_widths"] = cc.get("widths_measured")
        mans[key]["cell_kinds"] = list(cc["cells"].keys())
        mans[key]["adder_costs"] = cc["cells"]["adder"]["single_nowidelut"]
        mans[key]["adder_fit"] = cc["fits"]["adder"]
        mans[key]["mul_costs"] = cc["cells"]["mul"]["single_nowidelut"]
        mans[key]["mul_dsp_costs"] = cc["cells"]["mul_dsp"]["single_nowidelut"]
        mans[key]["mul_fit"] = cc["fits"]["mul"]
        mans[key]["cost_unit"] = cc.get("unit")
# all per-cell costs + fits of the Tang Nano MAN (the only one that has them)
tm = json.load(open(os.path.join(REPO, MANS["tang"])))
out["costs"] = {"unit": tm["cell_costs"]["unit"], "widths": tm["cell_costs"]["widths_measured"],
                "lut4_total": tm["device"]["logic"]["lut4_total"], "ff_total": tm["device"]["logic"]["ff_total"],
                "kinds": {k: {"measured": tm["cell_costs"]["cells"][k]["single_nowidelut"],
                              "lut4_fit": tm["cell_costs"]["fits"][k]["lut4_vs_W_nowidelut"],
                              "dff_fit": tm["cell_costs"]["fits"][k].get("dff_vs_W")}
                          for k in tm["cell_costs"]["cells"]}}
# card_fit budgets (nano/card_fit_v1.target_from_man) -- how many cell POSITIONS each card holds at a measured per-position cost
sys.path[:0] = [os.path.join(REPO, "nano"), os.path.join(REPO, "tools")]
import card_fit_v1 as cf
bud = []
for sh in ("nano_lean", "adder_lean", "adder_full", "nano_full"):
    t_ = cf.target_from_man(os.path.join(REPO, MANS["tang"]), rows=8, cols=8, shell=sh)
    bud.append({"card": "tang", "shell": sh, "unit": "LUT4", "per_position": cf.LUT4_PER_POSITION[sh],
                "total": tm["device"]["logic"]["lut4_total"], "budget": t_.cell_budget, "max_cells": t_.max_cells})
mm = json.load(open(os.path.join(REPO, MANS["mustang"])))
for sh in ("nano", "super_v3", "super_v4"):
    t_ = cf.target_from_man(os.path.join(REPO, MANS["mustang"]), rows=8, cols=8, shell=sh)
    bud.append({"card": "mustang", "shell": sh, "unit": "ALM", "per_position": cf.ALM_PER_POSITION[sh],
                "total": mm["device"]["alm_total"], "budget": t_.cell_budget, "max_cells": t_.max_cells})
out["budgets"] = bud
import vm_mirror_v1 as vmm
from types import SimpleNamespace as NS
mir = {"program": "nano/library_std/add.icm.json", "runs": []}
recs = [NS(cell_id=r["cell_id"], row=r["row"], col=r["col"]) for r in json.load(open(os.path.join(REPO, mir["program"])))["records"]]
mir["cells"] = [[r.row, r.col, r.cell_id] for r in recs]; mir["records"] = len(recs); mir["rows_span"] = [min(r.row for r in recs), max(r.row for r in recs)]; mir["cols_span"] = [min(r.col for r in recs), max(r.col for r in recs)]
for n in (16, 27, 64, 100, 400):
    b = vmm.load_mirror_bounds(os.path.join(REPO, MANS["mustang"]), n)
    pr = vmm.check_records_fit(recs, b)
    mir["runs"].append({"cells": n, "rows": b.rows, "cols": b.cols, "problems": len(pr), "first": pr[0] if pr else None, "valid": sorted([list(x) for x in b.valid_positions])})
out["mirror"] = mir
out["mans"] = mans

# --- the Verilog library, counted from the files
vd = os.path.join(REPO, "sub", "verilog")
names = sorted(os.listdir(vd))
cells = [n for n in names if not n.startswith("tb_")]
out["verilog"] = {
    "files_total": len(names), "testbenches": sum(1 for n in names if n.startswith("tb_")),
    "v4s": sorted(n[:-len("_cell_v4s.v")] for n in cells if n.endswith("_cell_v4s.v")),
    "v4sa": sorted(n[:-len("_cell_v4sa.v")] for n in cells if n.endswith("_cell_v4sa.v")),
}
def ports(fn):
    t = open(os.path.join(vd, fn)).read(); m = re.search(r"^module\s+\w+\s*(#\(.*?\))?\s*\((.*?)\);", t, re.S | re.M)
    body = (m.group(1) or "") + "\n" + m.group(2)
    body = re.sub(r"//.*", "", body)
    return [re.sub(r"\s+", " ", x).strip() for x in re.findall(r"(?:parameter|input|output)[^,\n)]*", body)]
out["adder_ports"] = {"v4s": ports("adder_cell_v4s.v"), "v4sa": ports("adder_cell_v4sa.v")}
json.dump(out, open(os.path.join(HERE, "rtl_data.json"), "w"), indent=1)
print("wrote rtl_data.json;", {k: (v["ok"]) for k, v in out["runs"].items()})
