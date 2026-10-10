#!/usr/bin/env python3
"""freeze_pure_v1.py -- ledger #1036 addendum 65: can the freeze / save / restore idea stand on a PURE Verilog CORDIC, with no cells at all?

Two hand-written designs (fpga/baselines/cordic_z_v1/): cordic_z_pipe_frz_v1.v (no back-pressure) and cordic_z_hs_frz_v1.v (valid/ack handshake), each the
unchanged baseline plus a freeze input and a 132-bit scan chain. Test, per design, as in freeze_rtl_v1.py: design A runs two items; at each cut 1..30 the freeze is raised,
the whole chain is shifted out of A (A's own chain recirculates, so A is restored) into a never-fed design B, both are released on the same cycle; B must give the same
values on the same cycles as A, and A must equal the Python model. Control: B loaded with zeros instead of A's bits.  --measure: synthesis and place-and-route cost.
SIMULATION AND SYNTHESIS ONLY: nothing on a board.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import cordic_baseline_v1 as cb  # noqa: E402
import freeze_rtl_v1 as fr  # noqa: E402

BASE = cb.BASE
NBITS = 132
DESIGNS = {
    "pipe_frz": ("cordic_z_pipe_frz_v1", "cordic_z_pipe_v1"),
    "hs_frz": ("cordic_z_hs_frz_v1", "cordic_z_hs_v1"),
}


def tb_text(kind):
    mod = DESIGNS[kind][0]
    hs = kind == "hs_frz"
    ports = lambda s: (f".clk(clk), .rst(rst), .freeze(frz{s}), .scan_en(sc), .scan_in(si{s}), .scan_out(so{s}), .in_data(z{s}), .in_valid(v{s}), "
                       + (f".in_ack(ack{s}), " if hs else "") + f".out_data(d{s}), .out_valid(ov{s})" + (", .out_ack(1'b1)" if hs else ""))
    if hs:
        feed = lambda s: (f"always @(posedge clk) if (!frz{s} && v{s} && ack{s}) begin if (i{s} + 1 < 2) begin i{s} <= i{s} + 1; z{s} <= items[i{s} + 1]; end else v{s} <= 0; end")
    else:
        feed = lambda s: (f"always @(posedge clk) if (st{s} && !frz{s}) i{s} <= i{s} + 1;\n  always @* begin v{s} = st{s} && i{s} < 2; z{s} = (i{s} < 2) ? items[i{s}] : 32'd0; end")
    decl_hs = "wire ackA, ackB; reg [31:0] zA = 0, zB = 0; reg vA = 0, vB = 0;" if hs else "reg [31:0] zA = 0, zB = 0; reg vA = 0, vB = 0; reg stA = 0, stB = 0;"
    start_a = "zA = items[0]; vA = 1; iA = 0;" if hs else "stA = 1; iA = 0;"
    copy_drv = "zB = zA; vB = vA; iB = iA;" if hs else "stB = stA; iB = iA;"
    return f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1; always #5 clk = ~clk;
  reg frzA = 0, frzB = 0, sc = 0;
  reg [31:0] items [0:1]; initial begin items[0] = 32'd{fr.ITEMS[0]}; items[1] = 32'd{fr.ITEMS[1]}; end
  integer iA = 0, iB = 0;
  {decl_hs}
  wire ovA, ovB; wire [31:0] dA, dB; wire soA, soB; reg load = 1;
  wire siA = soA;                 // A's chain recirculates, so A is put back as it was
  wire siB = load ? soA : 1'b0;   // B gets A's bits (or zeros, in the control run)
  {mod} A ({ports('A')});
  {mod} B ({ports('B')});
  {feed('A')}
  {feed('B')}
  integer cut, cyc, nA, nPre, k;
  initial begin
    if (!$value$plusargs("cut=%d", cut)) cut = 0;
    if (!$value$plusargs("load=%d", k)) k = 1;
    load = k;
    nA = 0; nPre = -1; cyc = 0;
    repeat (4) @(posedge clk); rst <= 0;
    repeat (14) @(posedge clk);
    @(negedge clk); {start_a}
    repeat (cut) @(negedge clk);
    frzA = 1; frzB = 1; nPre = nA;
    repeat (3) @(negedge clk);
    sc = 1; repeat ({NBITS}) @(negedge clk); sc = 0;
    {copy_drv}
    @(negedge clk); frzA = 0; frzB = 0; cyc = 0;
    repeat (90) @(negedge clk);
    $display("NPRE %0d", nPre);
    $finish;
  end
  always @(posedge clk) begin
    cyc <= cyc + 1;
    if (ovA && !frzA && !rst) begin $display("A %0d %0d", $signed(dA), cyc); nA <= nA + 1; end
    if (ovB && !frzB && !rst && nPre >= 0 && !sc) begin $display("B %0d %0d", $signed(dB), cyc); end
  end
endmodule
"""


def build(workdir, kind):
    tbp = os.path.join(workdir, f"tb_{kind}.v")
    open(tbp, "w").write(tb_text(kind))
    vvp = os.path.join(workdir, f"{kind}.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-o", vvp, tbp, os.path.join(BASE, DESIGNS[kind][0] + ".v")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return vvp


def run_cut(vvp, cut, load=1):
    r = subprocess.run(["vvp", vvp, f"+cut={cut}", f"+load={load}"], capture_output=True, text=True)
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


def sweep(vvp, load=1):
    same = diff = 0
    for cut in range(1, 31):
        a, b, npre = run_cut(vvp, cut, load)
        a_ok, b_ok, t_ok, npost = fr.judge(a, b, npre)
        assert a_ok, (cut, a)
        if npost == 0:
            continue
        if b_ok and t_ok:
            same += 1
        else:
            diff += 1
    return same, diff


_orig_wrapper = cb.wrapper


def _wrapper(kind):
    if kind not in ("pipe_frz", "hs_frz"):
        return _orig_wrapper(kind)
    hs = kind == "hs_frz"
    extra = ".in_ack(), " if hs else ""
    tail = ", .out_ack(1'b1)" if hs else ""
    mod = DESIGNS[kind][0]
    # freeze, scan_en and scan_in come from three input-shift-register bits and scan_out is folded into the output, so none of it is optimised away
    return f"""`default_nettype none
module wrap_top (input wire clk, input wire sin, output reg sout);
    reg [7:0] por = 8'd0; reg [31:0] zin = 32'd0; wire [31:0] od; wire ov; wire so;
    always @(posedge clk) begin por <= por + (por != 8'hFF); zin <= {{zin[30:0], sin}}; sout <= ^od ^ ov ^ so; end
    wire rst = (por < 8'd8);
    {mod} dut (.clk(clk), .rst(rst), .freeze(zin[0]), .scan_en(zin[1]), .scan_in(zin[2]), .scan_out(so), .in_data(zin), .in_valid(1'b1), {extra}.out_data(od), .out_valid(ov){tail});
endmodule
"""


def measure():
    cb.wrapper = _wrapper
    B = lambda n: [os.path.join(BASE, n + ".v")]
    out = {"what": "the hand-written CORDIC with and without a freeze input and a 132-bit scan chain (cordic_z_*_frz_v1.v). Counts: system yosys synth_gowin -nowidelut; "
                   "Fmax: nextpnr-himbaechel-gowin, GW2AR-LV18QN88C8/I7, target 400 MHz, three seeds, inside the same small wrapper (freeze and scan pins driven from the "
                   "wrapper's shift register so nothing is optimised away). SYNTHESIS AND PLACE-AND-ROUTE ONLY.", "designs": {}}
    for name, top, kind in (("pipe", "cordic_z_pipe_v1", "pipe"), ("pipe_frz", "cordic_z_pipe_frz_v1", "pipe_frz"), ("hs", "cordic_z_hs_v1", "hs"), ("hs_frz", "cordic_z_hs_frz_v1", "hs_frz")):
        files = B(top)
        out["designs"][name] = {"synth": cb.synth_counts(files, top), "pnr_in_wrapper": cb.place_and_route(files, kind)}
    return out


def main():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        print("iverilog REQUIRED")
        return 2
    if "--measure" in sys.argv:
        m = measure()
        json.dump(m, open(os.path.join(ROOT, "docs", "measurements", "freeze_pure_v1.json"), "w"), indent=1)
        for k, v in m["designs"].items():
            print(k, {a: v["synth"][a] for a in ("LUT", "ALU", "DFF")}, [(r.get("fmax_mhz"), r.get("LUT4")) for r in v["pnr_in_wrapper"]])
        return 0
    d = tempfile.mkdtemp(prefix="frzp_")
    try:
        for kind in DESIGNS:
            vvp = build(d, kind)
            s, f = sweep(vvp, 1)
            s0, f0 = sweep(vvp, 0)
            print(f"{kind:9s}: chain loaded -> identical at {s} cuts, differs at {f};  zeros loaded (control) -> identical at {s0}, differs at {f0}")
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
