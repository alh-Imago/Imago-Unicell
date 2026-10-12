#!/usr/bin/env python3
"""Capture REAL structure and source of every cell kind in all four families for the teaching manual's
cell pages. Parses the Verilog (module ports, parameters, registers, sub-module instances, always/assign
counts, header comment, setup-word field lines) and embeds the full source. Sizes are read from
nano/card_fit_v1.py and the Tang Nano MAN (quoted, not re-measured).
Writes docs/teaching/cells_data.json.   Run: python3 docs/teaching/capture_cells_v1.py
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FV, SV = "fpga/verilog", "sub/verilog"
sys.path[:0] = [os.path.join(REPO, "nano"), os.path.join(REPO, "tools")]

# kind -> family -> list of (file, role) ; the first file is the main one
def f4(k, **kw): return [(f"{FV}/{k}_cell_v4.v", "cell")]
def f4c(k): return [(f"{FV}/{k}_cell_v4c.v", "cell")]
def s(k): return [(f"{SV}/{k}_cell_v4s.v", "cell")]
def sa(k): return [(f"{SV}/{k}_cell_v4sa.v", "cell")]
K = {}
for k in ("accumulator", "adder", "branch", "compare", "latch", "ram", "sequencer"):
    K[k] = {"v4": f4(k), "v4c": f4c(k), "v4s": s(k), "v4sa": sa(k)}
K["nano"] = {"v4": [(f"{FV}/nano_gate_v4.v", "cell")], "v4c": [(f"{FV}/nano_gate_v4c.v", "cell")], "v4s": s("nano"), "v4sa": sa("nano")}
K["mul"] = {"v4": f4("mul"), "v4c": f4c("mul"), "v4s": s("mul") + [(f"{SV}/mul_cell_v4s_dsp{n}.v", "DSP variant") for n in ("", "2", "3")],
            "v4sa": sa("mul") + [(f"{SV}/mul_cell_v4sa_dsp.v", "DSP variant")]}
K["merge"] = {"v4": f4("merge"), "v4c": f4c("merge"), "v4sa": sa("merge")}
K["priority"] = {"v4": f4("priority"), "v4c": f4c("priority"), "v4sa": sa("priority")}
K["div"] = {"v4": f4("div"), "v4c": f4c("div"), "v4s": s("div"), "v4sa": sa("div")}
K["command"] = {"v4": f4("command"), "v4c": f4c("command")}
# corner / cross in sub and flex: no file of their own. tools/flexsub_icm_netlist_v1.py (splice_crosses, ledger #999/#1035) replaces each
# used direction of travel through a tile with one ordinary ram relay cell, so the page shows that ram cell with this role.
_WT = "no file of its own: the generator builds each used direction of the tile as one of these ram cells (one tick per tile)"
K["corner"] = {"v4": f4("corner"), "v4c": f4c("corner"), "v4s": [(f"{SV}/ram_cell_v4s.v", _WT)], "v4sa": [(f"{SV}/ram_cell_v4sa.v", _WT)]}
K["cross"] = {"v4": f4("cross"), "v4c": f4c("cross"), "v4s": [(f"{SV}/ram_cell_v4s.v", _WT)], "v4sa": [(f"{SV}/ram_cell_v4sa.v", _WT)]}
K["router"] = {"v4s": s("router"), "v4sa": sa("router")}
K["mask"] = {"v4": [(f"{FV}/nibble_mask_addon_v1.v", "the add-on block inside every standalone cell"), (f"{FV}/invert_addon_v1.v", "the invert add-on beside it")],
             "v4c": [(f"{FV}/nibble_mask_addon_v1.v", "the one shared add-on in the carrier")],
             "v4s": s("mask"), "v4sa": sa("mask")}
K["shift"] = {"v4": [(f"{FV}/shift_lane_addon_v2.v", "the coarse shift add-on"), (f"{FV}/shift_fine_addon_v1.v", "the fine (0-3) shift add-on before it")],
              "v4c": [(f"{FV}/shift_lane_addon_v2.v", "the one shared add-on in the carrier"), (f"{FV}/shift_fine_addon_v1.v", "the fine shift add-on")],
              "v4s": s("shift")}
K["shift_stage"] = {"v4s": [(f"{SV}/shift_stage_v4s.v", "cell")], "v4sa": [(f"{SV}/shift_stage_v4sa.v", "cell")]}

def strip(t): return re.sub(r"/\*.*?\*/", "", re.sub(r"//.*", "", t), flags=re.S)

def parse(path):
    raw = open(os.path.join(REPO, path), errors="replace").read()
    t = strip(raw)
    m = re.search(r"\bmodule\s+(\w+)\s*(#\s*\((.*?)\))?\s*\((.*?)\)\s*;", t, re.S)
    res = {"file": path, "lines": raw.count("\n") + 1, "source": raw}
    if not m: res.update({"module": None, "params": [], "ports": []}); return res
    params = [{"name": a, "default": b.strip()} for a, b in re.findall(r"parameter\s*(?:\[[^\]]*\])?\s*(\w+)\s*=\s*([^,\n)]+)", m.group(3) or "")]
    ports = []
    for d, body in re.findall(r"\b(input|output)\s+(?:wire\s+|reg\s+)?((?:\[[^\]]+\]\s*)?[^;]*?)(?=\binput\b|\boutput\b|$)", m.group(4) + " input", re.S):
        w = re.match(r"\[([^\]]+)\]", body.strip()); width = w.group(1).replace(" ", "") if w else None
        for n in [n.strip() for n in re.sub(r"\[[^\]]+\]", "", body).replace("\n", " ").split(",") if n.strip()]:
            ports.append({"dir": d, "name": n.split()[-1], "width": width})
    body = t[m.end():]
    regs = [{"name": n, "width": (w.replace(" ", "") if w else None)} for w, n in re.findall(r"\breg\s*(?:signed\s*)?(\[[^\]]+\])?\s*(\w+)", body)]
    regs = [r for r in regs if r["name"] not in ("begin",)]
    seen = set(); regs = [r for r in regs if not (r["name"] in seen or seen.add(r["name"]))]
    inst = re.findall(r"^\s*([a-z][a-zA-Z0-9_]*)\s*(?:#\s*\([^;]*?\))?\s+([A-Za-z_]\w*)\s*\(", body, re.M)
    kw = {"if", "else", "case", "casex", "casez", "for", "while", "repeat", "begin", "end", "function", "task", "always", "initial", "assign", "wire", "reg", "input", "output", "inout", "parameter", "localparam", "generate", "endgenerate", "module", "endmodule", "genvar", "integer", "default", "posedge", "negedge"}
    inst = [{"module": a, "name": b} for a, b in inst if a not in kw]
    # header comment: first contiguous run of // lines after the licence lines
    hdr, started = [], False
    for ln in raw.splitlines():
        if ln.startswith("//"):
            tx = ln[2:].strip()
            if re.match(r"(SPDX|Copyright|Hardware design)", tx): continue
            hdr.append(ln[2:].rstrip()); started = True
        elif started and ln.strip() == "":
            if hdr and hdr[-1] != "": hdr.append("")
        elif started: break
    while hdr and not hdr[0].strip(): hdr.pop(0)
    while hdr and not hdr[-1].strip(): hdr.pop()
    fields = []
    for ln in hdr:
        mm = re.match(r"\s*(?:cfg_data|cfg|\w+)?\s*\[(\d+(?::\d+)?)\]\s+([A-Za-z_][\w\[\]]*)\s*(?:--|—|-|=|:)?\s*(.*)$", ln)
        if mm and not ln.strip().startswith("cfg_data[") and re.match(r"^[A-Za-z_]\w{2,}$", mm.group(2)) and mm.group(2) not in ("regardless", "field", "the", "and", "see"): fields.append({"bits": mm.group(1), "name": mm.group(2), "what": mm.group(3).strip()[:140]})
    res.update({"module": m.group(1), "params": params, "ports": ports, "regs": regs, "instances": inst,
                "always": len(re.findall(r"\balways\b", body)), "assigns": len(re.findall(r"\bassign\b", body)),
                "header": "\n".join(hdr), "fields": fields[:16]})
    return res

out = {"kinds": {}}
for kind, fams in K.items():
    out["kinds"][kind] = {}
    for fam, files in fams.items():
        out["kinds"][kind][fam] = []
        for p, role in files:
            if not os.path.exists(os.path.join(REPO, p)):
                print("MISSING", p); continue
            d = parse(p); d["role"] = role; out["kinds"][kind][fam].append(d)
# sizes
import card_fit_v1 as cf
tm = json.load(open(os.path.join(REPO, "docs/man/tang-nano-20k.man.json")))
cc = tm["cell_costs"]
out["sizes"] = {"standalone_full": {k[:-5]: v for k, v in cf.LUT4_PER_POSITION.items() if k.endswith("_full")},
                "standalone_lean": {k[:-5]: v for k, v in cf.LUT4_PER_POSITION.items() if k.endswith("_lean")},
                "carrier_whole": cf.LUT4_PER_POSITION["vix_carrier_v1"], "v4s_adder": 66,
                "flex": {k: {"measured": cc["cells"][k]["single_nowidelut"], "fit": cc["fits"][k]["lut4_vs_W_nowidelut"]["coeffs_high_to_low"]} for k in cc["cells"]},
                "widths": cc["widths_measured"], "tang_lut4": tm["device"]["logic"]["lut4_total"]}
json.dump(out, open(os.path.join(HERE, "cells_data.json"), "w"))
tot = sum(len(f["source"]) for k in out["kinds"].values() for fl in k.values() for f in fl)
print("wrote cells_data.json", os.path.getsize(os.path.join(HERE, "cells_data.json")), "bytes; source", tot)
for kind, fams in out["kinds"].items():
    print(kind, {f: [(x["module"], len(x["ports"]), len(x["regs"]), len(x["instances"]), len(x["fields"])) for x in fl] for f, fl in fams.items()})
