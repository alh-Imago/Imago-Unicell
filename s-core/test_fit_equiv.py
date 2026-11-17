#!/usr/bin/env python3
"""test_fit_equiv.py - proves fit_search_tree (sc_sys_v14) gives the same answer as the serial loop of sc_sys_v13 (fit_search_serial, copied from it).
Every pattern of busy slices (2^S) x every task width (1, 2, 4, 8, 16, 32) for S = 1..8, 11, 12 and 16, with best-fit on and off; random patterns of different
density for S = 20, 32 and 64.  Compares fit_found and fit_base (including base 0 when nothing fits).  Needs iverilog.   python3 test_fit_equiv.py"""
import subprocess, sys, os, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
EXH = [1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 16]
RND = [(20, 150000), (32, 300000), (64, 300000)]
tb = """module chk #(parameter S = 4, parameter BF = 1, parameter RANDN = 0) ();
  reg [63:0] sb; reg [5:0] w; wire f1, f2; wire [5:0] b1, b2;
  fit_search_serial #(.S(S), .BESTFIT(BF)) a (.slice_busy(sb), .cur_w(w), .fit_found_o(f1), .fit_base_o(b1));
  fit_search_tree   #(.S(S), .BESTFIT(BF)) b (.slice_busy(sb), .cur_w(w), .fit_found(f2),   .fit_base(b2));
  integer n, bad, wi, i, d; reg [5:0] ws [0:5]; reg [63:0] mask, r;
  initial begin
    ws[0] = 1; ws[1] = 2; ws[2] = 4; ws[3] = 8; ws[4] = 16; ws[5] = 32; bad = 0; n = 0;
    mask = (S >= 64) ? 64'hFFFFFFFFFFFFFFFF : ((64'd1 << S) - 64'd1);
    for (wi = 0; wi < 6; wi = wi + 1) begin
      w = ws[wi];
      if (RANDN == 0) begin
        for (i = 0; i < (1 << S); i = i + 1) begin
          sb = i; #1; n = n + 1;
          if (f1 !== f2 || b1 !== b2) bad = bad + 1;
        end
      end else begin
        for (i = 0; i < RANDN / 6; i = i + 1) begin
          r = {$random, $random}; d = i % 4;
          if (d == 1) r = r & {$random, $random}; else if (d == 2) r = r | {$random, $random}; else if (d == 3) r = r & {$random, $random} & {$random, $random};
          sb = r & mask; #1; n = n + 1;
          if (f1 !== f2 || b1 !== b2) begin bad = bad + 1; if (bad < 4) $display("MISMATCH S=%0d BF=%0d w=%0d busy=%h serial=%b/%0d tree=%b/%0d", S, BF, w, sb, f1, b1, f2, b2); end
        end
      end
    end
    $display("S=%0d BESTFIT=%0d  %0d cases  %0d mismatches", S, BF, n, bad);
  end
endmodule
module top; """
for s in EXH:
    for bf in (1, 0): tb += "chk #(.S(%d), .BF(%d)) c_%d_%d (); " % (s, bf, s, bf)
for s, n in RND:
    for bf in (1, 0): tb += "chk #(.S(%d), .BF(%d), .RANDN(%d)) r_%d_%d (); " % (s, bf, n, s, bf)
tb += "initial begin #100000000; $finish; end endmodule\n"
d = tempfile.mkdtemp(); f = os.path.join(d, "tb.v"); open(f, "w").write(tb)
r = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "a.vvp"), "-s", "top", f, os.path.join(HERE, "fit_search_serial.v"), os.path.join(HERE, "fit_search_tree.v")], capture_output=True, text=True)
if r.returncode: print(r.stderr[:2000]); sys.exit(1)
r = subprocess.run(["vvp", os.path.join(d, "a.vvp")], capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if "mismatches" in l or "MISMATCH" in l]
print("\n".join(sorted(lines)))
tot = sum(int(l.split()[-2]) for l in lines if "mismatches" in l)
cases = sum(int(l.split()[-4]) for l in lines if "mismatches" in l)
ok = (tot == 0 and len([l for l in lines if "mismatches" in l]) == 2 * (len(EXH) + len(RND)))
print("RESULT", "PASS" if ok else "FAIL", "-", cases, "cases,", tot, "mismatches")
sys.exit(0 if ok else 1)
