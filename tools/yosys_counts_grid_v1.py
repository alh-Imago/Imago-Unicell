# yosys_counts_grid_v1.py -- synthesis counts of the UCC v2 grid prototype (sub/verilog/hexn_grid_v1.v) for several sizes, 2 Nov 2026. Run from a SCRATCH directory (YoWASP yosys writes only in the current directory).
import re, subprocess
V = "/home/claude/hexn-wt/sub/verilog/hexn_grid_v1.v"
def run(r, c):
    cmd = "read_verilog -sv %s; chparam -set R %d -set C %d hexn_grid_v1; synth_gowin -top hexn_grid_v1 -nowidelut; tee -q -o gc.txt stat" % (V, r, c)
    subprocess.run(["yosys", "-q", "-l", "gc.log", "-p", cmd], capture_output=True, text=True)
    t = open("gc.txt").read(); g = lambda k: sum(int(m.group(1)) for m in re.finditer(r"^\s+(\d+)\s+" + k + r"\s*$", t, re.M))
    l = g("LUT1") + g("LUT2") + g("LUT3") + g("LUT4"); a = g("ALU"); f = sum(g(k) for k in ("DFF", "DFFE", "DFFR", "DFFS", "DFFRE", "DFFSE", "DFFP", "DFFC", "DFFCE", "DFFNE"))
    return l, a, f, g("RAM16SDP4"), g("RAM16SDP1"), g("SDPB") + g("SP") + g("DPB")
for r, c in [(4, 4), (6, 6), (8, 8), (9, 9)]:
    l, a, f, r4, r1, b = run(r, c); n = r * c
    print("%dx%d = %3d cells: LUT %5d  ALU %d  DFF %4d  RAM16SDP4 %4d  RAM16SDP1 %3d  BSRAM %d   slots %5d = %.1f per cell" % (r, c, n, l, a, f, r4, r1, b, l + a, (l + a) / n), flush=True)
