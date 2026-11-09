#!/usr/bin/env python3
"""prebuild.py for the ypcb-00338-1p1 build flow (tools/xc7-build.sh runs it with the build directory as argument): writes into that directory
  gen_00_chain.v : rtl/hexn_speech_chain_v1.v from the Imago-Unicell checkout (HEXN_REPO, branch Hex-N, default ~/Imago-Unicell) with its four $readmemh lines replaced by the contents of data/wrom.hex, thr.hex, lp.hex, cfg.hex written as initial assignments
  gen_01_rom.v   : module hexn_speech_rom, the replay program (data/prog.hex, ends at 16'hFFFF) and labels (data/lab.hex) as initial assignments
The card flow reads plain Verilog from a place we cannot rely on for relative or absolute data file paths, so nothing is read from files at build time.
Usage: prebuild.py BUILDDIR   (also used by tests/vm/test_hexn_speech_kit_v1.py, with HEXN_REPO set to the checkout it runs in)"""
import os, sys, re
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/Imago-Unicell")); here = os.path.dirname(os.path.abspath(__file__)); data = os.path.join(here, "data")
def words(name): return [l.strip() for l in open(os.path.join(data, name)) if l.strip()]
src = open(os.path.join(repo, "rtl", "hexn_speech_chain_v1.v")).read()
for mem, fn, bits in (("wrom", "wrom.hex", 20), ("thr", "thr.hex", 80), ("lp", "lp.hex", 80), ("cfgm", "cfg.hex", 16)):
    pat = re.compile(r'[ \t]*if \((\w+) != ""\) \$readmemh\(\1, %s\);\n' % mem); assert pat.search(src), "readmemh line for %s not found in the chain RTL" % mem
    src = pat.sub("".join("        %s[%d] = %d'h%s;\n" % (mem, i, bits, w) for i, w in enumerate(words(fn))), src, count=1)
prog = words("prog.hex"); lab = words("lab.hex"); assert prog[-1].lower() == "ffff"
rom = ["module hexn_speech_rom (input wire clk, input wire [15:0] pa, output reg [15:0] pw, input wire [8:0] la, output reg [3:0] ld);\n",
       "    reg [15:0] prog [0:%d];\n    reg [3:0] lab [0:%d];\n    initial begin\n" % (len(prog) - 1, len(lab) - 1)]
rom += ["        prog[%d] = 16'h%s;\n" % (i, w) for i, w in enumerate(prog)] + ["        lab[%d] = 4'h%s;\n" % (i, w) for i, w in enumerate(lab)]
rom += ["    end\n    always @(posedge clk) begin pw <= prog[pa]; ld <= lab[la]; end\nendmodule\n"]
os.makedirs(sys.argv[1], exist_ok=True)
open(os.path.join(sys.argv[1], "gen_00_chain.v"), "w").write(src); open(os.path.join(sys.argv[1], "gen_01_rom.v"), "w").write("".join(rom))
print("prebuild: chain RTL from %s with %d weight words, %d replay words, %d labels" % (repo, len(words("wrom.hex")), len(prog), len(lab)))
