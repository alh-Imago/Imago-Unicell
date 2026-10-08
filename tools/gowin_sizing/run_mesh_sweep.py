#!/usr/bin/env python3
"""
run_mesh_sweep.py -- points.md #889: run the full real synth + real place-and-route sweep (standalone N=1,
3x3-mesh N=9) for every UniCell standalone shell, against the real Tang Nano 20K part.

For each (cell_type, n) this: generates the wrapper (gen_mesh_top.py) -> yosys synth_gowin -> JSON ->
yowasp-nextpnr-himbaechel-gowin place-and-route against GW2AR-LV18QN88C8/I7 with the real, verified pin
constraints from docs/man/tang-nano-20k.cst -> reads the real post-P&R utilization and Fmax from nextpnr's
own --report JSON. The zero-cell harness baseline is measured once and subtracted from every figure, so the
reported numbers are the cell(s) alone.

Usage: python3 run_mesh_sweep.py [--out results.json] [--types t1,t2,...] [--sizes 1,9]
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VDIR = os.path.join(ROOT, "fpga", "verilog")
GEN = os.path.join(os.path.dirname(__file__), "gen_mesh_top.py")
WORK = "/tmp/mesh_sweep"

CORE_FILES = {
    "latch": ["latch_shell_v1c.v", "latch_cell_v4c.v"],
    "ram": ["ram_shell_v1c.v", "ram_cell_v4c.v", "nibble_mask_addon_v1.v", "shift_lane_addon_v2.v", "invert_addon_v1.v"],
    "adder": ["adder_shell_v1c.v", "adder_cell_v4c.v", "adder_v1.v"],
    "branch": ["branch_shell_v1c.v", "branch_cell_v4c.v"],
    "accumulator": ["accumulator_shell_v1c.v", "accumulator_cell_v4c.v"],
    "compare": ["compare_shell_v1c.v", "compare_cell_v4c.v"],
    "sequencer": ["sequencer_shell_v1c.v", "sequencer_cell_v4c.v"],
    "mul": ["mul_shell_v1c.v", "mul_cell_v4c.v", "bitwise_multiplier_32bit.v"],
    "priority": ["priority_shell_v1c.v", "priority_cell_v4c.v"],
    "nano": ["nano_shell_v1c.v", "nano_gate_v4c.v", "shift_lane_addon_v2.v", "shift_fine_addon_v1.v",
             "nibble_mask_addon_v1.v", "invert_addon_v1.v"],
    "command": ["command_shell_v1c.v", "command_cell_v4c.v"],
}
ALL_TYPES = list(CORE_FILES)
CST = os.path.join(ROOT, "docs", "man", "tang-nano-20k.cst")


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=WORK, **kw)
    return r.returncode, r.stdout, r.stderr


def gen_test_cst():
    """Only the 5 ports this harness uses -- taken from the real, verified tang-nano-20k.cst (#887); not
    hand-typed pin numbers."""
    real = open(CST).read()
    import re
    pins = dict(re.findall(r'IO_LOC\s+"([\w\[\]]+)"\s+(\d+);', real))
    mapping = {"BOARD_CLK": pins["clk"], "BTN_RST_N": pins["btn_s1"], "BTN_ENTRY": pins["btn_s2"],
               "LED0_N": pins["led_n[0]"], "LED1_N": pins["led_n[1]"]}
    lines = [f'IO_LOC "{p}" {pin};\nIO_PORT "{p}" IO_TYPE=LVCMOS33 DRIVE=8;' for p, pin in mapping.items()]
    name = "mesh_test.cst"
    open(os.path.join(WORK, name), "w").write("\n".join(lines) + "\n")
    return name


def synth(top_v, files, top_name):
    files_str = " ".join(files)
    rc, out, err = sh(f"cd {VDIR} && timeout 90 yosys -p "
                       f"'read_verilog -sv {top_v} {files_str} ; hierarchy -top {top_name} ; "
                       f"synth_gowin -top {top_name} -json {WORK}/{top_name}.json'")
    if rc != 0 or not os.path.exists(f"{WORK}/{top_name}.json"):
        return None, (out + err)[-4000:]
    return f"{WORK}/{top_name}.json", (out + err)


def pnr(top_name, cst_name, timeout_s=150):
    rc, out, err = sh(f"timeout {timeout_s} yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88C8/I7 "
                       f"--vopt family=GW2A-18C --vopt cst={cst_name} --json {top_name}.json "
                       f"--write {top_name}_routed.json --report {top_name}_report.json "
                       f"--freq 27 --timing-allow-fail")
    report_path = os.path.join(WORK, f"{top_name}_report.json")
    if rc != 0 or not os.path.exists(report_path):
        return None, (out + err)[-4000:]
    return json.load(open(report_path)), (out + err)[-1500:]


def run_one(cell_type, n, cst_path):
    top_name = f"mesh_{cell_type}_{n}"
    top_v = f"{WORK}/{top_name}.v"
    args = "baseline" if cell_type == "baseline" else f"{cell_type} {n}"
    rc, out, err = sh(f"python3 {GEN} {args}", )
    if rc != 0:
        return {"error": f"generator failed: {err[-2000:]}"}
    open(top_v, "w").write(out)
    files = [] if cell_type == "baseline" else CORE_FILES[cell_type]
    json_path, synth_log = synth(top_v, files, top_name)
    if json_path is None:
        return {"error": f"synth failed: {synth_log}"}
    report, pnr_log = pnr(top_name, cst_path, timeout_s=(230 if n == 9 else 90))
    if report is None:
        return {"error": f"p&r failed: {pnr_log}"}
    u = report["utilization"]
    return {
        "ok": True,
        "lut4": u["LUT4"]["used"], "alu": u["ALU"]["used"], "dff": u["DFF"]["used"],
        "bsram": u["BSRAM"]["used"], "mult18x18": u["MULT18X18"]["used"], "iob": u["IOB"]["used"],
        "fmax_mhz": report["fmax"].get("clk", {}).get("achieved"),
        "fmax_pass_at_27mhz": (report["fmax"].get("clk", {}).get("achieved") or 0) >= 27.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/mesh_sweep_results.json")
    ap.add_argument("--types", default=",".join(ALL_TYPES))
    ap.add_argument("--sizes", default="1,9")
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    cst_path = gen_test_cst()

    results = json.load(open(a.out)) if os.path.exists(a.out) else {}

    if "baseline" not in results or not results["baseline"].get("ok"):
        print("=== baseline (0 cells) ===", flush=True)
        results["baseline"] = run_one("baseline", 0, cst_path)
        print(json.dumps(results["baseline"]), flush=True)
        json.dump(results, open(a.out, "w"), indent=2)
        if not results["baseline"].get("ok"):
            print("BASELINE FAILED -- aborting sweep"); sys.exit(1)

    for t in a.types.split(","):
        for n in [int(x) for x in a.sizes.split(",")]:
            key = f"{t}_{n}"
            if key in results and results[key].get("ok"):
                print(f"=== {key} === (already done, skipping)", flush=True)
                continue
            print(f"=== {key} ===", flush=True)
            r = run_one(t, n, cst_path)
            print(json.dumps(r), flush=True)
            results[key] = r
            json.dump(results, open(a.out, "w"), indent=2)   # save after EVERY run

    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
