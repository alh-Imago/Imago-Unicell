# yosys_counts_scell_v1.py -- synthesis counts of the bit-serial multi-core hex cell (sub/verilog/hexn_scell_v1.v), 2 Nov 2026, by switching the cores on one at a time. Run from a SCRATCH directory.
import re, subprocess
V = "/home/claude/hexn-wt/sub/verilog/hexn_scell_v1.v"
def run(add, lg, dl, wide):
    cmd = "read_verilog -sv %s; chparam -set ADD %d -set LOGIC %d -set DELAY %d hexn_scell_v1; synth_gowin -top hexn_scell_v1 %s; tee -q -o sc.txt stat" % (V, add, lg, dl, "" if wide else "-nowidelut")
    subprocess.run(["yosys", "-q", "-l", "sc.log", "-p", cmd], capture_output=True, text=True)
    t = open("sc.txt").read(); g = lambda k: sum(int(m.group(1)) for m in re.finditer(r"^\s+(\d+)\s+" + k + r"\s*$", t, re.M))
    l = g("LUT1") + g("LUT2") + g("LUT3") + g("LUT4"); f = sum(g(k) for k in ("DFF", "DFFE", "DFFR", "DFFS", "DFFRE", "DFFSE", "DFFP", "DFFC", "DFFCE", "DFFNE"))
    return l, f, g("MUX2_LUT5") + g("MUX2_LUT6") + g("MUX2_LUT7") + g("MUX2_LUT8"), g("ALU")
for wide in (False, True):
    print("== %s ==" % ("default flow" if wide else "-nowidelut"))
    for name, a, l, d in [("route only (6 faces out, config)", 0, 0, 0), ("+ add / subtract", 1, 0, 0), ("+ logic (4-bit table)", 0, 1, 0), ("+ delay 0..31 (shift left)", 0, 0, 1), ("all four", 1, 1, 1)]:
        lu, f, m, al = run(a, l, d, wide); print("%-34s LUT %3d  DFF %3d  MUX2 %3d  ALU %d" % (name, lu, f, m, al), flush=True)
