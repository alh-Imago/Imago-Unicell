#!/usr/bin/env python3
"""freeze_rtl_v1.py -- ledger #1036 addendum 64: freeze, capture, force into a second copy, resume -- in the RTL of the flex CORDIC (simulation, iverilog).

What it does (see docs/freeze/FREEZE_CAPTURE_LIST.md for the register table this tests):
  1. generates the flex CORDIC with project_assemble_v1, and makes a TEST COPY of the top in which the freeze line is a port (the generated file is not touched);
  2. design A runs two items; at a chosen cycle `cut` the freeze is raised on A, held for 3 cycles (a pause test), then the capture list (every dynamic register of
     every cell, read by hierarchical name) is forced into design B, which has been reset and configured but never fed; the host-side feed position is copied too;
  3. both are released on the same cycle; B must produce the same values on the same cycles as A, and A+B must equal the Python model.
  Negative controls: the same cut with the valid bits (`pending`...) not copied, with the data registers not copied, and with neither.
This is a SIMULATION. The load path used here (hierarchical assignment) does not exist in hardware (see the capture list, finding 1).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import cordic_baseline_v1 as cb  # noqa: E402

TOP = "icm_cordic_z_convergence_flex"
ITEMS = (50000, (-123456) & 0xFFFFFFFF)
# dynamic registers per cell type: (valid-type bits, data-type regs)
DYN = {
    "adder_cell_v4sa": (["pending", "pending_c"], ["out_buffer", "carry_buffer"]),
    "branch_cell_v4sa": (["pending_1", "pending_2", "has_loaded_1", "has_loaded_2"], ["held1_reg", "held2_reg", "out_buffer"]),
    "merge_cell_v4sa": (["pending"], ["rr", "out_buffer"]),
    "ram_cell_v4sa": (["pending", "have"], ["data_reg"]),
}


def build(workdir):
    gen = os.path.join(workdir, "gen")
    files = cb.assemble_unicell(gen)
    top = os.path.join(gen, TOP + ".v")
    text = open(top).read()
    assert text.count(".freeze_in(1'b0)") == 40
    text = text.replace(".freeze_in(1'b0)", ".freeze_in(freeze)").replace(f"module {TOP} (", f"module {TOP}_frz (\n    input  wire freeze,", 1)
    test_top = os.path.join(workdir, TOP + "_frz.v")
    open(test_top, "w").write(text)
    insts = re.findall(r"^(\w+_cell_v4sa)\s*#\(.*?\)\s*(\w+)\s*\(", text, re.M)
    assert len(insts) == 40 and {t for t, _ in insts} <= set(DYN), insts
    others = [f for f in files if not f.endswith(TOP + ".v")]
    lines = []
    for typ, name in insts:
        valid, data = DYN[typ]
        for r in valid:
            lines.append(f"    if (copy_valid) B.{name}.{r} = A.{name}.{r};")
        for r in data:
            lines.append(f"    if (copy_data) B.{name}.{r} = A.{name}.{r};")
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg = 0; always #5 clk = ~clk;
  reg frzA = 0, frzB = 0;
  reg [31:0] items [0:1]; initial begin items[0] = 32'd{ITEMS[0]}; items[1] = 32'd{ITEMS[1]}; end
  reg [31:0] zA = 0, zB = 0; reg vA = 0, vB = 0; integer iA = 0, iB = 0;
  wire ackA, ackB, ovA, ovB; wire [31:0] dA, dB;
  {TOP}_frz A (.freeze(frzA), .clk(clk), .rst(rst), .cfg_valid(cfg), .in_z_input_data(zA), .in_z_input_valid(vA), .in_z_input_ack(ackA),
               .out_z_output_data(dA), .out_z_output_valid(ovA), .out_z_output_ack(1'b1));
  {TOP}_frz B (.freeze(frzB), .clk(clk), .rst(rst), .cfg_valid(cfg), .in_z_input_data(zB), .in_z_input_valid(vB), .in_z_input_ack(ackB),
               .out_z_output_data(dB), .out_z_output_valid(ovB), .out_z_output_ack(1'b1));
  always @(posedge clk) if (!frzA && vA && ackA) begin if (iA + 1 < 2) begin iA <= iA + 1; zA <= items[iA + 1]; end else vA <= 0; end
  always @(posedge clk) if (!frzB && vB && ackB) begin if (iB + 1 < 2) begin iB <= iB + 1; zB <= items[iB + 1]; end else vB <= 0; end
  integer cut, copy_valid, copy_data, cyc, nA, nB, nPre, k;
  initial begin
    if (!$value$plusargs("cut=%d", cut)) cut = 0;
    if (!$value$plusargs("cv=%d", copy_valid)) copy_valid = 1;
    if (!$value$plusargs("cd=%d", copy_data)) copy_data = 1;
    nA = 0; nB = 0; nPre = -1; cyc = 0;
    repeat (4) @(posedge clk); rst <= 0;
    repeat (2) @(posedge clk); cfg <= 1; @(posedge clk); cfg <= 0;
    repeat (12) @(posedge clk);
    @(negedge clk); zA = items[0]; vA = 1; iA = 0;
    repeat (cut) @(negedge clk);
    frzA = 1; frzB = 1; nPre = nA;
    repeat (3) @(negedge clk);
{chr(10).join(lines)}
    zB = zA; vB = vA; iB = iA;
    @(negedge clk); frzA = 0; frzB = 0; cyc = 0;
    repeat (90) @(negedge clk);
    $display("NPRE %0d", nPre);
    $finish;
  end
  always @(posedge clk) begin
    if (nPre >= -1 || 1) cyc <= cyc + 1;
    if (ovA && !frzA && !rst) begin $display("A %0d %0d", $signed(dA), cyc); nA <= nA + 1; end
    if (ovB && !frzB && !rst && vB !== 1'bx && nPre >= 0 && frzA == 0) begin $display("B %0d %0d", $signed(dB), cyc); nB <= nB + 1; end
  end
endmodule
"""
    tbp = os.path.join(workdir, "tb_freeze.v")
    open(tbp, "w").write(tb)
    vvp = os.path.join(workdir, "freeze.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-o", vvp, tbp, test_top] + others, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return vvp, len(insts), sum(len(DYN[t][0]) + len(DYN[t][1]) for t, _ in insts)


CFG_REGS = {"armed", "subtract_mode", "carry_enable", "in1_fixed_mode", "in2_fixed_mode", "emit_source", "route_low", "route_equal", "route_high", "mode", "fixed_mode"}


def ff_coverage(workdir):
    """Synthesis check of the capture list: every flip-flop bit of the flattened generated design (yosys, before optimisation) must be a register named in
    the capture list (dynamic) or a configuration register. Returns (dynamic_bits, config_bits, bits_in_neither)."""
    import json
    gen = os.path.join(workdir, "gen")
    srcs = " ".join(sorted(f for f in os.listdir(gen) if f.endswith(".v")))
    out = os.path.join(workdir, "flat.json")
    r = subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {srcs}; hierarchy -top {TOP}; proc; flatten; opt_clean; write_json {out}"], cwd=gen, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    m = json.load(open(out))["modules"][TOP]
    dyn = {r for v, d in DYN.values() for r in v + d}
    names = {}
    for n, w in m["netnames"].items():
        if "." in n:
            for b in w["bits"]:
                if isinstance(b, int):
                    names.setdefault(b, set()).add(n.split(".", 1)[1])
    nd = nc = nx = 0
    for c in m["cells"].values():
        if "dff" in c["type"]:
            for b in c["connections"]["Q"]:
                ns = names.get(b, set())
                if ns & dyn:
                    nd += 1
                elif ns & CFG_REGS:
                    nc += 1
                else:
                    nx += 1
    return nd, nc, nx


def run_cut(vvp, cut, cv=1, cd=1):
    r = subprocess.run(["vvp", vvp, f"+cut={cut}", f"+cv={cv}", f"+cd={cd}"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    a, b, npre = [], [], None
    for ln in r.stdout.splitlines():
        p = ln.split()
        if p and p[0] == "A":
            a.append((int(p[1]), int(p[2])))
        elif p and p[0] == "B":
            b.append((int(p[1]), int(p[2])))
        elif p and p[0] == "NPRE":
            npre = int(p[1])
    return a, b, npre


def expected():
    return [cb.model(ITEMS[0] - (1 << 32) if ITEMS[0] >= 1 << 31 else ITEMS[0]), cb.model(ITEMS[1] - (1 << 32) if ITEMS[1] >= 1 << 31 else ITEMS[1])]


def judge(a, b, npre):
    """A alone must equal the model; the part of A after the cut must equal B in value AND cycle (cycle counts are shared, so compare directly)."""
    exp = expected()
    a_ok = [v for v, _ in a] == exp
    # outputs of A logged after the cut: the last len(a)-npre entries (outputs counted in A before the freeze are the first npre)
    a_post = a[npre:] if npre is not None else a
    b_ok = [v for v, _ in b] == [v for v, _ in a_post] and len(a_post) == len(b)
    t_ok = b_ok and [c for _, c in b] == [c for _, c in a_post]
    return a_ok, b_ok, t_ok, len(a_post)


def main():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        print("iverilog REQUIRED")
        return 2
    d = tempfile.mkdtemp(prefix="frz_")
    try:
        vvp, ncell, nreg = build(d)
        print(f"cells {ncell}, dynamic registers captured per copy {nreg}")
        if shutil.which("yosys"):
            print("flip-flop bits before optimisation: dynamic %d, configuration %d, in neither list %d" % ff_coverage(d))
        for label, cv, cd in (("all captured", 1, 1), ("valid bits NOT copied", 0, 1), ("data registers NOT copied", 1, 0), ("nothing copied", 0, 0)):
            ok = fl = 0
            for cut in range(0, 31):
                a, b, npre = run_cut(vvp, cut, cv, cd)
                a_ok, b_ok, t_ok, npost = judge(a, b, npre)
                if cut == 0 or npost == 0:
                    continue
                ok += a_ok and b_ok and t_ok
                fl += not (a_ok and b_ok and t_ok)
            print(f"{label:28s}: identical at {ok} cuts, differs at {fl}")
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
