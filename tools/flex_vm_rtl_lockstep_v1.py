#!/usr/bin/env python3
"""flex_vm_rtl_lockstep_v1.py -- ledger #1095: run the FlexGrid VM and the assembler-generated flex RTL (iverilog) side by side, clock for tick, on the open-ring looped CORDIC, and compare
the state of every cell. It answers: at which moments is the VM's state the SAME as the RTL's, register for register? (That decides where a VM save can be loaded into the RTL unchanged.)

Zero of time = the clock where the RTL accepts z0 / the VM tick after the inject. Compared per cell and per tick: (valid, data) of the cell's output register -- ram (pending/data_reg; a fixed ram is always
valid), adder (pending/out_buffer), branch (pending_1|pending_2/out_buffer), plus the merge core's `rr` against the VM relay's `_merge_rr`, and the branch's loaded-reference flag.
The 4 merge relays (`sN.merge`) exist only in the VM (the RTL branch absorbs them) and the 4 `sN.gather.merge` cores only in the RTL; they are left out of the cell compare (the gather merge `rr` is compared with the VM gather relay's `_merge_rr`).
Constant sources and `zero_source` are left out of the data compare: the generator makes `zero_source` a constant (always valid); the VM treats it as a one-shot.
Usage: python3 tools/flex_vm_rtl_lockstep_v1.py [TICKS=158]    (prints a JSON summary)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "nano"))
import looped_cordic_v1 as L  # noqa: E402
from flex_grid_v1 import FlexGrid  # noqa: E402

REGS = {"adder": ["pending", "out_buffer"], "ram": ["pending", "have", "fixed_mode", "data_reg"],
        "branch": ["pending_1", "pending_2", "out_buffer", "has_loaded_2", "held2_reg"], "merge": ["pending", "rr", "out_buffer"]}


def ident(n):
    return "c_" + re.sub(r"[^A-Za-z0-9_]", "_", n)


def rtl_run(work, results=4):
    icm = os.path.join(work, "open.icm-hier.json")
    shutil.copy(os.path.join(ROOT, "nano", "examples", "looped_cordic_v1_open.icm-hier.json"), icm)
    out = os.path.join(work, "rtl")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm, "--output", out, "--top", "icm_open_flex"], check=True, capture_output=True)
    top = open(os.path.join(out, "icm_open_flex.v")).read()
    inst = re.findall(r"^(adder|ram|branch|merge)_cell_v4sa #\(\.CELL_ID\(16'd\d+\)\) (c_\w+) \(", top, re.M)
    disp = []
    for kind, name in inst:
        disp.append('$display("S %%0d %s %s %s", cyc-t0, %s);' % (name, kind, " ".join("%s=%%h" % r for r in REGS[kind]), ", ".join("d.%s.%s" % (name, r) for r in REGS[kind])))
    tb = open(os.path.join(ROOT, "sub", "verilog", "tb_looped_cordic_open_flex_v1.v")).read()
    tb = tb.replace("integer n=0, cyc=0, last=0;", "integer n=0, cyc=0, last=0, t0=0;")
    tb = tb.replace("begin started <= 1; inj <= 0; last <= cyc; end", "begin started <= 1; inj <= 0; last <= cyc; t0 = cyc; end\n    if (started || (inj && iack)) begin #1; " + " ".join(disp) + " end")
    tb = tb.replace("n+1 >= 40", "n+1 >= %d" % results)
    open(os.path.join(work, "tb.v"), "w").write(tb)
    vvp = os.path.join(work, "ls.vvp")
    subprocess.run(["iverilog", "-g2012", "-o", vvp, os.path.join(work, "tb.v")] + [os.path.join(out, f) for f in os.listdir(out) if f.endswith(".v")], check=True, capture_output=True)
    rtl = {}
    for l in subprocess.run(["vvp", vvp], check=True, capture_output=True, text=True).stdout.splitlines():
        if l.startswith("S "):
            p = l.split()
            rtl.setdefault(p[2], {})[int(p[1])] = {kv.split("=")[0]: kv.split("=")[1] for kv in p[4:]}
    return rtl


def rview(st):
    if "pending_1" in st:
        return (int(st["pending_1"], 16) | int(st["pending_2"], 16), int(st["out_buffer"], 16))
    if "fixed_mode" in st:
        return (1 if int(st["fixed_mode"], 16) else int(st["pending"], 16), int(st["data_reg"], 16))
    return (int(st["pending"], 16), int(st["out_buffer"], 16))


def vview(c):
    if c.core == "ram":
        return (int(bool(c.ram_data_valid)), (c.ram_data_reg or 0) & 0xFFFFFFFF)
    if c.core == "adder":
        return (int(bool(c.adder_data_valid)), (c.adder_out_buffer or 0) & 0xFFFFFFFF)
    return (int(bool(c.br_data_valid)), (c.br_out_buffer or 0) & 0xFFFFFFFF)


def lockstep(ticks=158):
    work = tempfile.mkdtemp()
    rtl = rtl_run(work, results=max(4, ticks // 40 + 1))
    g, _ = L.new_grid(FlexGrid)
    per_tick, hidden = {}, {"rr_equal": 0, "rr_total": 0, "rr_bad_ticks": set(), "ref_loaded_rtl": set(), "ref_valid_vm": set(), "adder_a_is_constant": True, "adder_waiting_non_constant_ticks": []}
    consts = {c.cell_id: c for c in g.cells.values() if "const" in c.cell_id or "zero_source" in c.cell_id}
    cells0 = {c.cell_id for c in g.cells.values()}
    common = [n for n in cells0 if ident(n) in rtl and n not in consts]
    for t in range(1, ticks + 1):
        g.tick()
        if t < 2:
            continue
        cells = {c.cell_id: c for c in g.cells.values()}
        bad = []
        for n in common:
            r, v = rview(rtl[ident(n)][t]), vview(cells[n])
            if r[0] != v[0] or (r[0] and r[1] != v[1]):
                bad.append(n)
        per_tick[t] = bad
        for s in range(4):
            hidden["rr_total"] += 1
            same = int(rtl["c_s%d_gather_merge" % s][t]["rr"], 16) == int(cells["s%d.gather" % s]._merge_rr)
            hidden["rr_equal"] += int(same)
            if not same:
                hidden["rr_bad_ticks"].add(t)
            hidden["ref_loaded_rtl"].add(rtl["c_s%d_branch" % s][t]["has_loaded_2"])
            hidden["ref_valid_vm"].add(bool(cells["s%d.branch" % s].br_ref_valid))
        cv = {(c.ram_data_reg & 0xFFFFFFFF) for c in consts.values() if c.core == "ram"}
        for n, c in cells.items():
            if c.core == "adder" and c.adder_a_arrived and (c.adder_a_reg & 0xFFFFFFFF) not in cv:
                hidden["adder_waiting_non_constant_ticks"].append((t, n))
    good = [t for t, b in per_tick.items() if not b]
    return {"ticks": ticks, "equal_ticks": good, "n_equal": len(good), "n_compared": len(per_tick), "cells_compared": len(common),
            "mismatch_cells": sorted({n for b in per_tick.values() for n in b}),
            "merge_rr_equal": [hidden["rr_equal"], hidden["rr_total"]], "merge_rr_differs_at_equal_ticks": sorted(hidden["rr_bad_ticks"] & set(good)), "branch_ref_loaded_in_rtl": sorted(hidden["ref_loaded_rtl"]), "branch_ref_valid_in_vm": sorted(hidden["ref_valid_vm"]),
            "adder_first_operand_not_a_constant_at": hidden["adder_waiting_non_constant_ticks"][:6], "n_adder_waiting_non_constant": len(hidden["adder_waiting_non_constant_ticks"])}


if __name__ == "__main__":
    print(json.dumps(lockstep(int(sys.argv[1]) if len(sys.argv) > 1 else 158), indent=1))
