#!/usr/bin/env python3
"""tools/flex_scan_check_v1.py -- ledger #1145: A/B simulation of in-flight capture and restore on the flex looped CORDIC, through the scan chain of tools/flex_scan_net_v1.py.

For each freeze lag (trig_lag 0..31, so the freeze lands at a different place in the pipeline each time) and several stop counts:
  A  runs the looped CORDIC from the start value, stops itself by FREEZE after k1 results (the word may be inside the grid);
  the scan chain of A is read out by recirculating (scan_in = scan_out, so A is left as it was);
  B  is a fresh card: reset, the same configuration pulse, the closing-register word loaded, then the captured stream shifted in;
  A and B are released together and both must deliver the same next k2 results, with the same spacing in time, equal to the Python model (nano/looped_cordic_v1.py).
Mutants (--mutant) break the restore on purpose; the check must then FAIL:  zeros = shift zeros in instead of the stream,  noword = do not restore the closing register,  flip = flip one stream bit.

  python3 tools/flex_scan_check_v1.py [--mutant none|zeros|noword|flip] [--lags 0-31] [--k1 3,4,5]
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_freeze_net_v1 as fz, flex_busy_port_v1 as bz, flex_scan_net_v1 as sn, looped_cordic_v1 as L  # noqa: E402


def build(work):
    shutil.copy(os.path.join(ROOT, "nano", "examples", "looped_cordic_v1_open.icm-hier.json"), os.path.join(work, "open.icm-hier.json"))
    g = os.path.join(work, "grid")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", os.path.join(work, "open.icm-hier.json"), "--output", g, "--top", "icm_open_flex"], check=True, capture_output=True)
    fz.make(g, "icm_open_flex"); bz.add(g, "icm_open_flex")
    sn.make(g, "icm_open_flex")
    for f in ("looped_cordic_stop_wrapper_v3.v", "accumulator_cell_v4sa.v", "latch_cell_v4sa.v"):
        shutil.copy(os.path.join(ROOT, "sub", "verilog", f), g)
    return g, json.load(open(os.path.join(g, "SCAN_MAP.json")))


TB = r"""`timescale 1ns/1ps
module tb;
  localparam NB = @NB@;
  reg clk = 0; always #5 clk = ~clk;
  reg rst_a = 1, rst_b = 1;
  reg a_cfg_grid = 0, a_cfg_acc = 0, a_load = 0, a_has = 0, a_rel = 0, a_se = 0, a_hold = 0; reg [31:0] a_ld = 0; reg [15:0] a_n = 0;
  reg b_cfg_grid = 0, b_cfg_acc = 0, b_load = 0, b_has = 0, b_rel = 0, b_se = 0, b_hold = 0, b_bit = 0; reg [31:0] b_ld = 0; reg [15:0] b_n = 0;
  reg [1:0] mode = 2; reg [2:0] dly = 0; reg [4:0] lag = 0;
  wire a_busy, a_stopped, a_hv, a_take, a_so; wire [15:0] a_steps; wire [31:0] a_held, a_td;
  wire b_busy, b_stopped, b_hv, b_take, b_so; wire [15:0] b_steps; wire [31:0] b_held, b_td;
  looped_cordic_stop_wrapper_v3 A (.clk(clk), .rst(rst_a), .cfg_grid(a_cfg_grid), .cfg_acc(a_cfg_acc), .n_steps(a_n), .mode(mode), .feed_delay(dly), .trig_lag(lag),
     .load_valid(a_load), .load_has(a_has), .load_data(a_ld), .scan_hold(a_hold), .scan_en(a_se), .scan_in(a_so), .scan_out(a_so), .release_pulse(a_rel), .busy(a_busy), .stopped(a_stopped),
     .steps_done(a_steps), .held_word(a_held), .held_valid(a_hv), .take_o(a_take), .take_data(a_td));
  looped_cordic_stop_wrapper_v3 B (.clk(clk), .rst(rst_b), .cfg_grid(b_cfg_grid), .cfg_acc(b_cfg_acc), .n_steps(b_n), .mode(mode), .feed_delay(dly), .trig_lag(lag),
     .load_valid(b_load), .load_has(b_has), .load_data(b_ld), .scan_hold(b_hold), .scan_en(b_se), .scan_in(b_bit), .scan_out(b_so), .release_pulse(b_rel), .busy(b_busy), .stopped(b_stopped),
     .steps_done(b_steps), .held_word(b_held), .held_valid(b_hv), .take_o(b_take), .take_data(b_td));
  reg [NB-1:0] stream, bits;
  reg rec = 0; integer ia = 0, ib = 0; reg [31:0] av [0:63]; reg [31:0] bv [0:63]; integer at [0:63]; integer bt [0:63]; integer clkn = 0;
  always @(posedge clk) clkn <= clkn + 1;
  always @(posedge clk) begin
    if (rec && a_take) begin av[ia] <= a_td; at[ia] <= clkn; ia <= ia + 1; end
    if (rec && b_take) begin bv[ib] <= b_td; bt[ib] <= clkn; ib <= ib + 1; end end
  integer fd, bad = 0, trials = 0, i, w, j, mism;
  reg [31:0] aw; reg ahv, abusy; reg [15:0] asteps; reg [31:0] mdl [0:127];
  task tick(input integer n); begin repeat (n) @(posedge clk); #1; end endtask
  task trial(input integer k1, input integer lagv, input integer dlyv, input integer k2); begin
    trials = trials + 1; rec = 0; ia = 0; ib = 0; lag = lagv; mode = 2; dly = dlyv;
    rst_a = 1; rst_b = 1; b_hold = 1; tick(20); rst_a = 0; tick(3);
    a_cfg_grid = 1; tick(1); a_cfg_grid = 0; tick(3);
    a_n = k1; a_cfg_acc = 1; tick(1); a_cfg_acc = 0; tick(1);
    a_ld = @Z0@; a_has = 1; a_load = 1; tick(1); a_load = 0;
    w = 0; while (!a_stopped && w < 20000) begin tick(1); w = w + 1; end
    tick(20);
    aw = a_held; ahv = a_hv; abusy = a_busy; asteps = a_steps;
    // capture: recirculate the whole chain (scan_in = scan_out), A is left as it was
    a_se = 1; #0;
    for (i = 0; i < NB; i = i + 1) begin stream[NB-1-i] = a_so; tick(1); end
    a_se = 0; tick(2);
    // B: fresh card, same configuration, closing register, then the stream shifted in
    rst_b = 0; tick(3);
    b_cfg_grid = 1; tick(1); b_cfg_grid = 0; tick(3);
    b_n = k2; b_cfg_acc = 1; tick(1); b_cfg_acc = 0; tick(1);
    bits = stream;
    if (@MUT@ == 1) bits = 0;
    if (@MUT@ == 3) bits[(trials * 37 + @FLIP@) % NB] = ~bits[(trials * 37 + @FLIP@) % NB];
    b_ld = aw; b_has = ahv; if (@MUT@ == 2) begin b_ld = 0; b_has = 0; end
    b_load = 1; tick(1); b_load = 0;
    b_se = 1; for (i = 0; i < NB; i = i + 1) begin b_bit = bits[NB-1-i]; tick(1); end b_se = 0; b_bit = 0;
    tick(2);
    // release both together: A re-armed for k2 more results
    a_n = k2; a_cfg_acc = 1; tick(1); a_cfg_acc = 0; tick(1);
    rec = 1; a_rel = 1; b_hold = 0; tick(1); a_rel = 0;
    w = 0; while ((ia < k2 || ib < k2) && w < 20000) begin tick(1); w = w + 1; end
    tick(40); rec = 0;
    mism = 0;
    if (ia < k2 || ib < k2) mism = 1000;
    for (j = 0; j < k2; j = j + 1) begin
      if (av[j] !== mdl[asteps + j]) mism = mism + 1;
      if (bv[j] !== av[j]) mism = mism + 1;
      if ((bt[j] - bt[0]) != (at[j] - at[0])) mism = mism + 1; end
    if (mism) bad = bad + 1;
    $display("TRIAL k1=%0d lag=%0d dly=%0d steps=%0d busy=%0d held_valid=%0d | next %0d results A=%0d B=%0d | %s", k1, lagv, dlyv, asteps, abusy, ahv, k2, ia, ib, mism ? "MISMATCH" : "same");
    $fdisplay(fd, "%0d %0d %0d %0d %0d %h", k1, lagv, asteps, abusy, ahv, stream);
  end endtask
  // chain integrity, independent of the workload: shift a known pattern into a frozen fresh grid, read it back by recirculating
  reg [NB-1:0] pat, got; integer pbad = 0;
  task ptest(input integer kind, input integer seed); integer q; begin
    rst_b = 1; b_hold = 1; tick(5); rst_b = 0; tick(3); b_cfg_grid = 1; tick(1); b_cfg_grid = 0; tick(3);
    for (q = 0; q < NB; q = q + 1) pat[q] = (kind == 0) ? $random(seed) : (kind == 1) ? 1'b1 : (kind == 2) ? 1'b0 : (q % 7 == 3);
    b_se = 1; for (q = 0; q < NB; q = q + 1) begin b_bit = pat[NB-1-q]; tick(1); end b_se = 0; tick(2);
    b_se = 1; for (q = 0; q < NB; q = q + 1) begin got[NB-1-q] = b_so; b_bit = b_so; tick(1); end b_se = 0; tick(2);
    if (got !== pat) begin pbad = pbad + 1; bad = bad + 1; end
    $display("PATTERN kind=%0d %s", kind, (got === pat) ? "read back equal" : "DIFFERENT");
    b_hold = 0; end endtask
  initial begin fd = $fopen("streams.txt", "w"); $readmemh("model.hex", mdl);
    tick(10);
    if (@PT@) begin ptest(0, 11); ptest(0, 22); ptest(0, 33); ptest(1, 0); ptest(2, 0); ptest(3, 0); end
@@TRIALS@@
    $fclose(fd); $display("SCANCHECK trials=%0d bad=%0d", trials, bad); $finish; end
  initial begin #@TMO@; $display("SIMTIMEOUT"); $finish; end
endmodule
"""


def run(work, g, info, mutant, lags, k1s, k2, flip, dlys):
    model = L.model(120)
    open(os.path.join(work, "model.hex"), "w").write("\n".join("%08x" % (v & 0xFFFFFFFF) for v in model) + "\n")
    trials = "\n".join("    trial(%d, %d, %d, %d);" % (k1, lg, dl, k2) for k1 in k1s for lg in lags for dl in dlys)
    t = (TB.replace("@NB@", str(info["total_bits"])).replace("@Z0@", str(L.Z0)).replace("@MUT@", str({"none": 0, "zeros": 1, "noword": 2, "flip": 3, "chain": 0}[mutant]))
         .replace("@FLIP@", str(flip)).replace("@PT@", "1" if mutant in ("none", "chain") else "0").replace("@@TRIALS@@", trials).replace("@TMO@", "400000000"))
    open(os.path.join(work, "tb.v"), "w").write(t)
    files = sorted(os.path.join(g, f) for f in os.listdir(g) if f.endswith(".v") and f not in ("icm_open_flex.v", "icm_open_flex_fz.v"))
    c = subprocess.run(["iverilog", "-g2012", "-o", "tb.vvp", "tb.v"] + files, cwd=work, capture_output=True, text=True)
    if c.returncode:
        raise SystemExit("iverilog: " + c.stderr[:2000])
    return subprocess.run(["vvp", "tb.vvp"], cwd=work, capture_output=True, text=True, timeout=7200).stdout


def parse_range(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def coverage(work, info):
    """Which dynamic registers held a non-zero value in at least one captured stream (so the test really exercised them)."""
    seen = {}
    N = info["total_bits"]
    for line in open(os.path.join(work, "streams.txt")):
        f = line.split()
        v = int(f[5], 16)
        for c in info["chain"]:
            for r in c["regs"]:
                off = r["stream_offset"]
                x = (v >> (N - off - r["bits"])) & ((1 << r["bits"]) - 1)
                if x:
                    seen.setdefault((c["type"], r["name"]), set()).add(c["cell"])
    return seen


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--mutant", default="none", choices=["none", "zeros", "noword", "flip", "chain"])
    ap.add_argument("--lags", default="0-31"); ap.add_argument("--k1", default="3,4,5"); ap.add_argument("--dly", default="0-4"); ap.add_argument("--k2", type=int, default=6)
    ap.add_argument("--flip", type=int, default=1900, help="stream bit to flip for the flip mutant")
    ap.add_argument("--keep", default=None)
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix="scan_check_")
    try:
        g, info = build(work)
        if a.mutant == "chain":   # break the chain on purpose: one adder cell loses its link to the next cell
            f = os.path.join(g, "adder_cell_v4sa_scan.v"); t = open(f).read()
            assert "scan_vec[SB-2:0], scan_in}" in t
            open(f, "w").write(t.replace("scan_vec[SB-2:0], scan_in}", "scan_vec[SB-2:0], 1'b0}", 1))
        out = run(work, g, info, a.mutant, parse_range(a.lags), parse_range(a.k1), a.k2, a.flip, parse_range(a.dly))
        lines = [l for l in out.splitlines() if l.startswith(("TRIAL", "PATTERN", "SCANCHECK", "SIMTIMEOUT"))]
        print("\n".join(lines))
        cov = coverage(work, info) if os.path.exists(os.path.join(work, "streams.txt")) else {}
        allregs = {(c["type"], r["name"]) for c in info["chain"] for r in c["regs"]}
        if os.path.exists(os.path.join(work, "streams.txt")):
            rows = [l.split() for l in open(os.path.join(work, "streams.txt"))]
            print("STATES %d trials, %d distinct captured streams, held_valid=1 in %d, busy=1 in %d" % (len(rows), len({r[5] for r in rows}), sum(r[4] == "1" for r in rows), sum(r[3] == "1" for r in rows)))
        print("COVERAGE %d of %d register kinds held a non-zero value in some captured stream; never non-zero: %s" % (len(cov), len(allregs), sorted(allregs - set(cov))))
        verdict = next((l for l in lines if l.startswith("SCANCHECK")), "no verdict")
        failed = "bad=0 " not in (verdict + " ") and "bad=0" != verdict.split("bad=")[-1]
        if a.mutant != "none":
            print("MUTANT %s -> %s" % (a.mutant, "caught" if failed else "NOT CAUGHT")); sys.exit(0 if failed else 1)
        print("SCAN CHECK", "FAIL" if failed else "PASS"); sys.exit(1 if failed else 0)
    finally:
        if a.keep:
            shutil.copytree(work, a.keep, dirs_exist_ok=True)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
