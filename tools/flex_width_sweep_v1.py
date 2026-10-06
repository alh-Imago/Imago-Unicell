#!/usr/bin/env python3
"""flex_width_sweep_v1.py -- measure every flex (v4sa) cell the assembler knows at several widths with yosys `synth_gowin`, and write
docs/measurements/flex_width_sweep_975/costs.json (the source of the Tang MAN's `cell_costs`). Ledger #975, extended at #976.

Per cell and width: the SINGLE cell alone (every config port a real input) in the default `-nowidelut` flow and in the historical wide-LUT flow, and a 3x3 ARRAY (nine cells
in the generated assembler top, `-nowidelut`). For the three cells with a second output port (adder carry, mul / mul_dsp high word) the single cell is also measured WITH the
port built (SECOND_PORT=1, `single_nowidelut_port2`): the port is a build parameter set from the compiler's ICM flag, so the default cells carry no cost for it.

  python3 tools/flex_width_sweep_v1.py [--workdir DIR] [--widths 4,8,16,18,24,32] [--jobs 2] [--out costs.json]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_assemble_v1 as fsa  # noqa: E402

PORT2_CELLS = ("adder", "mul", "mul_dsp")
WORK = "/tmp/flex_sweep"


def parse(out):
    c = {}
    for line in out.split("Number of cells")[-1].splitlines():
        p = line.split()
        if len(p) == 2 and p[1].isdigit():
            c[p[0]] = int(p[1])
    return [sum(v for k, v in c.items() if k.startswith("LUT")), c.get("ALU", 0), sum(v for k, v in c.items() if k.startswith("DFF")), sum(v for k, v in c.items() if k.startswith("MULT"))]


def run(job):
    cell, w = job
    d = os.path.join(WORK, f"{cell}_w{w}_n9")
    shutil.rmtree(d, ignore_errors=True)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "-S", cell, "-w", str(w), "--cells", "9", "--output", d], capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        return dict(cell=cell, w=w, error=(r.stderr + r.stdout)[-300:])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    mod, top = rec["cell_module"], rec["top"]
    deps = [f for f in os.listdir(d) if f.endswith(".v") and f != top + ".v"]

    def synth(srcs, topn, pre, extra):
        o = subprocess.run(["yosys", "-p", f"read_verilog -sv {' '.join(srcs)}; {pre} hierarchy -top {topn}; synth_gowin -top {topn} {extra} -json /dev/null; stat"], cwd=d, capture_output=True, text=True, timeout=3000).stdout
        return parse(o)
    res = dict(cell=cell, w=w, module=mod)
    try:
        pre = f"chparam -set WIDTH {w} {mod};"
        res["single_widelut"] = synth(deps, mod, pre, "")
        res["single_nowidelut"] = synth(deps, mod, pre, "-nowidelut")
        res["array3x3_nowidelut"] = synth([top + ".v"] + deps, top, "", "-nowidelut")
        if cell in PORT2_CELLS:
            res["single_nowidelut_port2"] = synth(deps, mod, pre + f" chparam -set SECOND_PORT 1 {mod};", "-nowidelut")
    except Exception as e:  # noqa: BLE001
        res["error"] = str(e)[:300]
    return res


def fits(cells, widths):
    import numpy as np
    out = {}
    x = np.array(widths, float)
    for c, d in cells.items():
        ys = np.array([d["single_nowidelut"][str(w)][0] for w in widths], float)
        deg = 2 if c == "mul" else 1
        p = np.polyfit(x, ys, deg)
        fy = np.array([d["single_nowidelut"][str(w)][2] for w in widths], float)
        pf = np.polyfit(x, fy, 1)
        out[c] = {"lut4_vs_W_nowidelut": {"degree": deg, "coeffs_high_to_low": [round(float(v), 4) for v in p], "max_abs_residual": round(float(np.abs(np.polyval(p, x) - ys).max()), 1)},
                  "dff_vs_W": {"coeffs_high_to_low": [round(float(v), 3) for v in pf], "max_abs_residual": round(float(np.abs(np.polyval(pf, x) - fy).max()), 1)}}
    return out


def write_readme(costs_path):
    d = json.load(open(costs_path))
    W = d["widths"]
    L = ["# Flex cell cost vs width (ledger #975, extended #976)\n",
         "Measured by `tools/flex_width_sweep_v1.py` (yosys `synth_gowin`, synthesis only -- no place-and-route, no timing, nothing run on a board). Raw numbers: `costs.json`; they are also carried in the Tang Nano 20K MAN file under `cell_costs`. Regenerate this file with `python3 tools/flex_width_sweep_v1.py --readme-only`.\n",
         "Each cell was built at widths " + ", ".join(map(str, W)) + ": the **single cell** alone (every configuration port a real input -- the honest per-cell cost) in the card's default `-nowidelut` flow and in the historical wide-LUT flow, and a **3x3 array** (nine cells in the generated assembler top). The adder, multiplier and DSP multiplier were also built **with their second output port** (`SECOND_PORT=1`).\n",
         "## Single cell, LUT4 (default `-nowidelut` flow)\n", "| cell | " + " | ".join(f"W{w}" for w in W) + " | fit LUT4 vs W | max error |", "|---|" + "---|" * len(W) + "---|---|"]
    for c, v in d["cells"].items():
        f = d["fits"][c]["lut4_vs_W_nowidelut"]
        co = f["coeffs_high_to_low"]
        if c == "sequencer":
            eq, err = "36 (saturates from W8; no useful fit)", "-"
        else:
            eq = (f"{co[0]:.2f}W^2 {co[1]:+.2f}W {co[2]:+.1f}" if f["degree"] == 2 else (f"{co[0]:.2f}W {co[1]:+.1f}" if abs(co[0]) > 0.05 else f"{co[1]:.0f} (flat)"))
            err = f["max_abs_residual"]
        L.append(f"| {c} | " + " | ".join(str(v["single_nowidelut"][str(w)][0]) for w in W) + f" | {eq} | {err} |")
    L += ["\n## With the second output port built (`SECOND_PORT=1`), LUT4 / DFF\n", "| cell | " + " | ".join(f"W{w}" for w in W) + " |", "|---|" + "---|" * len(W)]
    for c, v in d["cells"].items():
        if "single_nowidelut_port2" in v:
            L.append(f"| {c} (port off -> on) | " + " | ".join(f"{v['single_nowidelut'][str(w)][0]}/{v['single_nowidelut'][str(w)][2]} -> {v['single_nowidelut_port2'][str(w)][0]}/{v['single_nowidelut_port2'][str(w)][2]}" for w in W) + " |")
    L += ["\n## Single cell, flip-flops (DFF)\n", "| cell | " + " | ".join(f"W{w}" for w in W) + " |", "|---|" + "---|" * len(W)]
    for c, v in d["cells"].items():
        L.append(f"| {c} | " + " | ".join(str(v["single_nowidelut"][str(w)][2]) for w in W) + " |")
    L += ["\nALU (carry-chain) cells, `mul_dsp` DSP blocks and the wide-LUT and 3x3 numbers are in `costs.json`.\n", "## How to read this\n",
          "- **Use the single-cell nowidelut numbers to project.** They are smooth in W and the fits hold to a few LUTs.",
          "- **The wide-LUT flow is not smooth** (the mapper changes its mind between widths), so do not extrapolate from it; the nowidelut flow is the card's default (`synthesis.nowidelut.default`).",
          "- **The 3x3 array is not nine times the single cell.** The generated top pins each cell's configuration, so constant-config logic folds away. It tells you what a hard-wired cluster costs, not a runtime-configurable one.",
          "- **The second port is a build parameter** set from the compiler's ICM flag (adder `carry_mode`, multiplier `wide_mode`): a cell the compiler did not flag is built without it and carries no cost for it.",
          "- **W-independent cells:** latch, router, shift_stage and mul_dsp (plus one DSP block) cost the same LUTs at every width and only add flip-flops. The sequencer saturates at 8 bits and FlexGrid refuses it below 8.",
          "- Not covered: place-and-route or timing.\n",
          "## On the Tang Nano 20K (20,736 LUT4)\n", "Whole cells that fit if the device held nothing else (single-cell nowidelut cost, ignoring routing and the 15,552 flip-flop limit):\n",
          "| cell | " + " | ".join(f"W{w}" for w in W) + " |", "|---|" + "---|" * len(W)]
    for c, v in d["cells"].items():
        L.append(f"| {c} | " + " | ".join(str(20736 // max(1, v["single_nowidelut"][str(w)][0])) for w in W) + " |")
    open(os.path.join(os.path.dirname(costs_path), "README.md"), "w").write("\n".join(L) + "\n")


def main():
    global WORK
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=WORK)
    ap.add_argument("--widths", default="4,8,16,18,24,32")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "measurements", "flex_width_sweep_975", "costs.json"))
    ap.add_argument("--readme-only", action="store_true", help="rebuild README.md from the existing costs.json, measure nothing")
    a = ap.parse_args()
    if a.readme_only:
        write_readme(a.out)
        return
    WORK = a.workdir
    os.makedirs(WORK, exist_ok=True)
    widths = [int(x) for x in a.widths.split(",")]
    cells = fsa.cells_for("flex")
    jobs = [(c, w) for c in cells for w in widths if not (c == "mul_dsp" and w > 36)]
    with Pool(a.jobs) as p:
        results = p.map(run, jobs)
    bad = [r for r in results if "error" in r]
    if bad:
        sys.exit("sweep errors: " + json.dumps(bad)[:800])
    out = {"note": "yosys synth_gowin LUT4/ALU/DFF/MULT per flex cell (v4sa) at several widths; produced by tools/flex_width_sweep_v1.py (ledger #975/#976). single_* = the cell module alone, every config port a real input; "
                   "single_nowidelut_port2 = the same with the second output port built (SECOND_PORT=1, adder / mul / mul_dsp only); array3x3_* = nine cells in the generated assembler top "
                   "(config pinned by the harness, so constant-config logic folds away: NOT a per-cell figure).",
           "widths": widths, "cells": {}, "fits": {}}
    for r in results:
        d = out["cells"].setdefault(r["cell"], {})
        for k in ("single_nowidelut", "single_widelut", "array3x3_nowidelut", "single_nowidelut_port2"):
            if k in r:
                d.setdefault(k, {})[str(r["w"])] = r[k]
    out["cells"] = dict(sorted(out["cells"].items()))
    out["fits"] = fits(out["cells"], widths)
    json.dump(out, open(a.out, "w"), indent=1)
    write_readme(a.out)
    print(f"wrote {a.out}: {len(results)} builds")


if __name__ == "__main__":
    main()
