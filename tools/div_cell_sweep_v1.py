#!/usr/bin/env python3
"""div_cell_sweep_v1.py -- ledger #1070: measure div_cell_v4sa at several WIDTH / STEPS with yosys synth_gowin (-nowidelut) and
yowasp nextpnr-himbaechel-gowin place-and-route (GW2AR-LV18QN88C8/I7, the Tang Nano 20K part), the same method as tools/cordic_baseline_v1.py.

The cell sits in a small wrapper: operands come from registered LFSRs that advance each time the cell takes a pair, results are folded
into an XOR register and reduced to one LED bit, so every output bit is observed and nothing can be discarded. Target 400 MHz (unreachable on
purpose, so the router keeps trying; --timing-allow-fail), several seeds, the minimum Fmax over seeds is reported. SYNTHESIS AND
PLACE-AND-ROUTE ONLY: nothing is run on a board. The wrapper's own LFSR/XOR logic is in every number; the 'wrapper only' row is
measured the same way (cell replaced by a register stage) so it can be read off.

  python3 tools/div_cell_sweep_v1.py [--widths 18,32] [--steps 1,2,4,8,W] [--seeds 1,2] [--jobs 2] [--out results.json]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = os.path.join(ROOT, "sub", "verilog", "div_cell_v4sa.v")
CELL_V4S = os.path.join(ROOT, "sub", "verilog", "div_cell_v4s.v")      # ledger #1072: --family sub measures this one (32 bits only, no ack)
DEVICE = "GW2AR-LV18QN88C8/I7"
CST = """IO_LOC "BOARD_CLK" 4;
IO_PORT "BOARD_CLK" IO_TYPE=LVCMOS33;
IO_LOC "LED0_N" 15;
IO_PORT "LED0_N" IO_TYPE=LVCMOS33 DRIVE=8;
"""


def wrapper(width, steps, with_cell=True, family="flex"):
    if family == "sub" and with_cell:
        cell = f"""
    div_cell_v4s #(.STEPS({steps})) dut (
        .clk(BOARD_CLK), .rst(1'b0), .cfg_valid(boot_pulse), .cfg_data(32'd2),
        .in_a(a), .in_b(b), .valid_in(1'b1), .data_out(q), .valid_out(vq));
    assign r = {width}'d0; assign vr = 1'b0; assign ack_out = 1'b1;"""
    else:
      cell = f"""
    div_cell_v4sa #(.WIDTH({width}), .STEPS({steps}), .SECOND_PORT(1)) dut (
        .clk(BOARD_CLK), .rst(1'b0), .freeze_in(1'b0), .cfg_valid(boot_pulse), .cfg_data(32'd1),
        .in_a(a), .in_b(b), .valid_in(ack_out), .ack_out(ack_out),
        .data_out(q), .valid_out(vq), .ack_in(1'b1),
        .rem_out(r), .valid_out_r(vr), .ack_in_r(1'b1));""" if with_cell else f"""
    reg [{width-1}:0] q_r = 0, r_r = 0;
    assign q = q_r; assign r = r_r; assign vq = 1'b0; assign vr = 1'b0; assign ack_out = 1'b1;
    always @(posedge BOARD_CLK) begin q_r <= a + b; r_r <= a ^ b; end"""
    return f"""
module wrap_top(input wire BOARD_CLK, output wire LED0_N);
    reg [15:0] boot = 16'd0;
    wire boot_pulse = (boot == 16'd8);
    always @(posedge BOARD_CLK) if (boot != 16'hFFFF) boot <= boot + 16'd1;
    reg [{width-1}:0] a = {width}'d1, b = {width}'d3;
    wire [{width-1}:0] q, r;
    wire vq, vr, ack_out;
    reg [{width-1}:0] acc = 0;
    {cell}
    always @(posedge BOARD_CLK) begin
        if (ack_out) begin
            a <= {{a[{width-2}:0], a[{width-1}] ^ a[{max(width-4,0)}] ^ 1'b1}};
            b <= {{b[{width-2}:0], b[{width-1}] ^ b[{max(width-3,0)}] ^ 1'b1}} | {width}'d1;
        end
        acc <= acc ^ q ^ r ^ {{{width}{{vq ^ vr}}}};
    end
    assign LED0_N = ^acc;
endmodule
"""


def count_cells(text):
    """Reads yosys `stat` lines; the count may come before or after the cell name depending on the yosys version."""
    c = {}
    for line in text.splitlines():
        p = line.split()
        if len(p) == 2:
            if p[0].isdigit() and not p[1].isdigit():
                c[p[1]] = int(p[0])
            elif p[1].isdigit() and not p[0].isdigit():
                c[p[0]] = int(p[1])
    return {"LUT": sum(v for k, v in c.items() if k.startswith("LUT")), "ALU": c.get("ALU", 0),
            "DFF": sum(v for k, v in c.items() if k.startswith("DFF"))}


def gate_depth(d, files):
    """Longest topological path (in simple gates, techmapped, flip-flops cut) from yosys `ltp -noff`. Ledger #1072: nextpnr's Fmax was found NOT to
    follow the long subtract-and-select chain (a 32-step chain reported FASTER than a 1-step one; a synthetic chain test showed the same), so this
    independent, relative depth number is reported next to it. It is gate depth, not nanoseconds."""
    r = subprocess.run(["yosys", "-p", f"read_verilog -sv {files}; hierarchy -top wrap_top; proc; flatten; opt -fast; techmap; opt -fast; ltp -noff"],
                       cwd=d, capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "Longest topological path" in line and "length=" in line:
            return int(line.split("length=")[1].split(")")[0])
    return None


def measure(job):
    width, steps, with_cell, seeds, target, family = job
    d = tempfile.mkdtemp(prefix="divsweep_")
    try:
        open(os.path.join(d, "w.v"), "w").write(wrapper(width, steps, with_cell, family))
        open(os.path.join(d, "w.cst"), "w").write(CST)
        cellfile = CELL_V4S if family == "sub" else CELL
        shutil.copy(cellfile, d)
        files = f"w.v {os.path.basename(cellfile)}" if with_cell else "w.v"
        r = subprocess.run(["yosys", "-p", f"read_verilog -sv {files} ; hierarchy -top wrap_top ; synth_gowin -nowidelut -top wrap_top -json w.json ; tee -o stat.txt stat"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode:
            return dict(width=width, steps=steps, cell=with_cell, error=(r.stderr + r.stdout)[-400:])
        depth = gate_depth(d, files)
        res = dict(width=width, steps=steps, cell=with_cell, gate_depth=depth, synth=count_cells(open(os.path.join(d, "stat.txt")).read()), fmax_mhz=None, seeds=[])
        for sd in seeds:
            p = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", DEVICE, "--vopt", "family=GW2A-18C", "--vopt", "cst=w.cst", "--seed", str(sd),
                                "--json", "w.json", "--report", "rep.json", "--freq", str(target), "--timing-allow-fail"], cwd=d, capture_output=True, text=True)
            if p.returncode:
                res["seeds"].append({"seed": sd, "error": (p.stderr or p.stdout)[-300:]})
                continue
            rep = json.load(open(os.path.join(d, "rep.json")))
            fm = [v["achieved"] for v in rep["fmax"].values()]
            res["seeds"].append({"seed": sd, "fmax_mhz": round(min(fm), 1) if fm else None})
        vals = [s["fmax_mhz"] for s in res["seeds"] if s.get("fmax_mhz")]
        res["fmax_mhz"] = min(vals) if vals else None
        return res
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--widths", default="18,32")
    ap.add_argument("--steps", default="1,2,4,8,W")
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--family", default="flex", choices=["flex", "sub"], help="flex = div_cell_v4sa (any width); sub = div_cell_v4s (32 bits, no ack)")
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.family == "sub" and a.widths != "32":
        a.widths = "32"                                 # the sub cell is 32 bits, no width control
    if a.out is None:
        a.out = os.path.join(ROOT, "docs", "measurements", "div_cell_sweep_1070" if a.family == "flex" else "div_cell_sweep_1072", "results.json")
    seeds = [int(x) for x in a.seeds.split(",")]
    jobs = []
    for w in [int(x) for x in a.widths.split(",")]:
        jobs.append((w, 1, False, seeds, a.target, a.family))
        for s in a.steps.split(","):
            k = w if s == "W" else int(s)
            if k <= w:
                jobs.append((w, k, True, seeds, a.target, a.family))
    with Pool(a.jobs) as pool:
        rows = pool.map(measure, jobs)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump({"what": ("div_cell_v4sa" if a.family == "flex" else "div_cell_v4s") + ": yosys synth_gowin -nowidelut + nextpnr-himbaechel-gowin, " + DEVICE + ", wrapper with LFSR operands and XOR-observed outputs; "
               "target %d MHz, seeds %s, minimum Fmax over seeds. Synthesis and place-and-route only; not run on a board." % (a.target, seeds), "rows": rows}, open(a.out, "w"), indent=1)
    print(f"{'W':>3} {'K':>3} {'clocks':>6} {'LUT':>6} {'ALU':>5} {'DFF':>5} {'Fmax MHz':>9} {'depth':>6}  (cell = {'yes'}; K=0 row is the wrapper alone)")
    for r in rows:
        if "error" in r:
            print(r["width"], r["steps"], "ERROR", r["error"][-200:])
            continue
        k = r["steps"] if r["cell"] else 0
        clocks = (-(-r["width"] // r["steps"]) + (1 if a.family == "flex" else 0)) if r["cell"] else 0      # flex: +1 capture clock; sub: first clock works from the inputs
        s = r["synth"]
        print(f"{r['width']:>3} {k:>3} {clocks:>6} {s['LUT']:>6} {s['ALU']:>5} {s['DFF']:>5} {r['fmax_mhz'] if r['fmax_mhz'] else 'n/a':>9} {r.get('gate_depth') or 'n/a':>6}")


if __name__ == "__main__":
    main()
