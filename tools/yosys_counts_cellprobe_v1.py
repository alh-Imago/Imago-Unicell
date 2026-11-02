# yosys_counts_cellprobe_v1.py -- synthesis counts for the UCC v2 cell prototypes in sub/verilog/hexn_cell_probe_v1.v (2 Nov 2026). Run it from a SCRATCH directory: the YoWASP yosys can only write files in the current directory.
import re, subprocess, sys
V = "/home/claude/hexn-wt/sub/verilog/hexn_cell_probe_v1.v"
def run(n, kind, wide):
    cmd = "read_verilog -sv %s; chparam -set N %d -set KIND %d hexn_probe_line; synth_gowin -top hexn_probe_line %s; tee -q -o cp.txt stat" % (V, n, kind, "" if wide else "-nowidelut")
    subprocess.run(["yosys", "-q", "-l", "cp.log", "-p", cmd], capture_output=True, text=True)
    t = open("cp.txt").read(); g = lambda k: sum(int(m.group(1)) for m in re.finditer(r"^\s+(\d+)\s+" + k + r"\s*$", t, re.M))
    l = g("LUT1") + g("LUT2") + g("LUT3") + g("LUT4"); a = g("ALU"); f = sum(g(k) for k in ("DFF", "DFFE", "DFFR", "DFFS", "DFFRE", "DFFSE", "DFFP", "DFFC", "DFFCE", "DFFNE"))
    return l, a, f, g("MUX2_LUT5") + g("MUX2_LUT6") + g("MUX2_LUT7") + g("MUX2_LUT8"), g("RAM16SDP4") + g("SSRAM") + g("RAM16SDP1"), g("BSRAM") + g("SP") + g("SDPB")
NAMES = ["table in flip-flops (64-bit shift load)", "table in memory (64 x 1)", "bit-serial adder (fixed)"]
for wide in (False, True):
    print("== synth_gowin %s ==" % ("default (wide LUT muxes allowed)" if wide else "-nowidelut"))
    for kind in (0, 1, 2):
        for n in (1, 8, 32):
            l, a, f, m, r, b = run(n, kind, wide); print("%-40s N=%2d  LUT4-ish %5d  ALU %3d  DFF %5d  MUXn %4d  RAM16 %3d  BSRAM %d   slots %5d  per cell %.1f" % (NAMES[kind], n, l, a, f, m, r, b, l + a, (l + a) / n), flush=True)
