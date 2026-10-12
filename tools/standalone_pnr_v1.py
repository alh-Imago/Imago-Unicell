#!/usr/bin/env python3
"""tools/standalone_pnr_v1.py -- ledger #1116: yosys + nextpnr (GW2A-18C, Tang Nano 20K) for a standalone-shell grid (tools/standalone_grid_v1.py) of the std-line looped CORDIC with ring control.
The grid is wrapped so it needs only BOARD_CLK and LED0_N..LED3_N: a power-up counter performs the proven sequence (load z0 at clock 40, optional release later), the tap word is XOR-reduced to a LED
so nothing is pruned. The grid's edge faces (nothing is attached to them) are tied low. Reports LUT/FF/DSP use, Fmax (nextpnr, static, labelled so) and fit.
  python3 tools/standalone_pnr_v1.py --laps 6 [--freq 27] [--seed 1] [--out DIR]"""
import argparse, json, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "nano"), os.path.join(ROOT, "nano", "examples")):
    sys.path.insert(0, p)
import standalone_grid_v1 as S
import board_tests_v1 as bt
import looped_cordic_v1 as L
import verilog_deps_v1 as vd


def build(laps, out):
    recs = L.build_records(join=True, ring_laps=laps)
    inp = next(r for r in recs if r.io_name == "z_input")
    tap = next(r.cell_id for r in recs if r.cell_id.endswith("fb19"))
    meta = S.generate(recs, out, "std_grid", tap)
    zi = next(c["index"] for c in meta["cells"] if c["cell_id"] == inp.cell_id)
    n = len(meta["ext"])
    top = """`default_nettype none
module board_top(input wire BOARD_CLK, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);
    reg [31:0] cnt = 32'd0; always @(posedge BOARD_CLK) cnt <= cnt + 32'd1;
    reg rst = 1'b1; always @(posedge BOARD_CLK) if (cnt == 32'd16) rst <= 1'b0;
    wire ld = (cnt == 32'd%(t)d);
    wire tv; wire [31:0] td;
    std_grid g(.clk(BOARD_CLK), .rst(rst), .ld_valid(ld), .ld_cell(16'd%(zi)d), .ld_word(32'd%(z0)d), .tap_valid(tv), .tap_data(td),
        .ext_arrived(%(n)d'b0), .ext_ack_in(%(n)d'b0), .ext_data_in({%(nb)d{1'b0}}), .ext_fire(), .ext_data_out());
    reg [31:0] acc = 32'd0; reg seen = 1'b0; always @(posedge BOARD_CLK) if (tv) begin acc <= acc ^ td; seen <= 1'b1; end
    assign LED0_N = ~(^acc); assign LED1_N = ~seen; assign LED2_N = ~cnt[24]; assign LED3_N = ~(&acc[7:0]);
endmodule
""" % dict(t=44, zi=zi, z0=L.Z0 & 0xFFFFFFFF, n=n, nb=32 * n)
    open(os.path.join(out, "board_top.v"), "w").write(top)
    cst = "".join('IO_LOC "%s" %s;\nIO_PORT "%s" IO_TYPE=LVCMOS33%s;\n' % (p, bt.PINS[p], p, " PULL_MODE=NONE" if p == "BOARD_CLK" else " DRIVE=8") for p in ("BOARD_CLK", "LED0_N", "LED1_N", "LED2_N", "LED3_N"))
    open(os.path.join(out, "g.cst"), "w").write(cst)
    deps = set()
    for m in meta["shells"]:
        deps |= set(vd.deps(m, [out, os.path.join(ROOT, "fpga", "verilog")]))
    return meta, ["board_top.v", "std_grid.v"] + sorted(deps)


def run(laps, freq, seed, out):
    meta, files = build(laps, out)
    s = subprocess.run(["yosys", "-q", "-p", "read_verilog -sv %s; hierarchy -check -top board_top; synth_gowin -top board_top -nowidelut -json g.json; tee -o g.stat stat" % " ".join(files)], cwd=out, capture_output=True, text=True, timeout=6000)
    if s.returncode:
        return {"stage": "yosys", "error": s.stderr[-800:]}
    stat = open(os.path.join(out, "g.stat")).read()
    p = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", bt.DEVICE, "--vopt", "family=GW2A-18C", "--vopt", "cst=g.cst", "--seed", str(seed), "--json", "g.json", "--write", "g_r.json",
                        "--report", "g_rep.json", "--freq", str(freq)], cwd=out, capture_output=True, text=True, timeout=9000)
    log = p.stdout[-6000:] + p.stderr[-3000:]
    res = {"cells": len(meta["cells"]), "laps": laps, "target_mhz": freq, "seed": seed}
    mm = re.search(r"Max frequency for clock '[^']*': ([0-9.]+) MHz", log)
    if mm:
        res["fmax_mhz"] = float(mm.group(1))
    if p.returncode and not mm:
        res.update(stage="nextpnr", error=log[-1500:])
        return res
    rep = json.load(open(os.path.join(out, "g_rep.json"))) if os.path.exists(os.path.join(out, "g_rep.json")) else {}
    res["utilization"] = {k: "%d/%d" % (v["used"], v["available"]) for k, v in rep.get("utilization", {}).items() if v.get("used")}
    res["timing_met"] = p.returncode == 0
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--laps", type=int, default=6)
    ap.add_argument("--freq", type=float, default=27)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    print(json.dumps(run(a.laps, a.freq, a.seed, a.out or tempfile.mkdtemp(prefix="stdpnr_")), indent=1))
