# yosys_counts_arith_v9_v1.py -- re-runs the synthesis counts quoted in the ledger row of 1 Nov 2026 18:35 (arith block v9, config gate v3). Run it from a SCRATCH directory: the YoWASP yosys can only write files in the current directory.
import re, subprocess
V = "/home/claude/hexn-wt/sub/verilog/"
def run(cmd, top):
    subprocess.run(["yosys", "-q", "-l", "cn.log", "-p", cmd + "; synth_gowin -top %s -nowidelut; tee -q -o cn.txt stat" % top], capture_output=True, text=True)
    t = open("cn.txt").read(); g = lambda k: sum(int(m.group(1)) for m in re.finditer(r"^\s+(\d+)\s+" + k + r"\s*$", t, re.M))
    l = g("LUT2") + g("LUT3") + g("LUT4"); a = g("ALU"); f = sum(g(k) for k in ("DFF","DFFE","DFFR","DFFS","DFFRE","DFFSE","DFFP","DFFC","DFFCE","DFFNE"))
    return "LUT %d ALU %d DFF %d MULT %d  slots %d" % (l, a, f, g("MULT18X18"), l + a)
for name, cmd, top in [("block v9 W18", "read_verilog -sv %sarith_block_v9.v; chparam -set WIDTH 18 arith_block_v9" % V, "arith_block_v9"),
                       ("block v9 W32", "read_verilog -sv %sarith_block_v9.v; chparam -set WIDTH 32 arith_block_v9" % V, "arith_block_v9"),
                       ("v8 shared+TT W32 (old block)", "read_verilog -sv %sarith_block_v8.v %sadder_v1.v; chparam -set SHARED 1 -set NANO_TT 1 arith_block_v8" % (V, V), "arith_block_v8"),
                       ("gate v3 W18", "read_verilog -sv %sconfig_gate_v3.v; chparam -set WIDTH 18 -set CFG_W 32 config_gate_v3" % V, "config_gate_v3"),
                       ("gate v3 W32", "read_verilog -sv %sconfig_gate_v3.v; chparam -set WIDTH 32 -set CFG_W 32 config_gate_v3" % V, "config_gate_v3")]:
    print(name + ":", run(cmd, top), flush=True)
