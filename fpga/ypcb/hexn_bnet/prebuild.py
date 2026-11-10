#!/usr/bin/env python3
"""prebuild.py for the ypcb-00338-1p1 build flow (tools/xc7-build.sh runs it with the build directory as argument): writes gen_00_bnet.v there, ONE file holding the merged bus network RTL (v2 files) and the wrapper with its shape set.
Settings (environment): HEXN_REPO = the Imago-Unicell checkout, branch Hex-N (default ~/Imago-Unicell); HEXN_G (buses per layer, default 4), HEXN_PER (cells per bus, 16), HEXN_NIN (input lines, 48), HEXN_SQL (sub-queue depth = 2**SQL, 3), HEXN_FB (feedback 1/0, 1)."""
import os, re, sys
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/Imago-Unicell"))
par = dict(G=int(os.environ.get("HEXN_G", "4")), PER=int(os.environ.get("HEXN_PER", "16")), NIN=int(os.environ.get("HEXN_NIN", "48")), SQL=int(os.environ.get("HEXN_SQL", "3")), FB=int(os.environ.get("HEXN_FB", "1")))
nv = os.environ.get("HEXN_NETV", "v4"); assert nv in ("v2", "v3", "v4", "v5"), "HEXN_NETV must be v2, v3, v4 or v5"      # v3 = the arbiter without multipliers (no DSP blocks); v2 = the first Kintex builds
files = ["sub/verilog/hexn_bnet_bus_v2.v", "sub/verilog/hexn_bnet_ser_v2.v", "sub/verilog/hexn_bnet_tbus_%s.v" % nv, "sub/verilog/hexn_bnet_net_%s.v" % nv, "sub/verilog/hexn_bnet_pnr_top_v1.v"]
out = []
for f in files:
    p = os.path.join(repo, f)
    if not os.path.exists(p): sys.exit("prebuild: %s not found (set HEXN_REPO to the Imago-Unicell checkout, branch Hex-N, git pull)" % p)
    t = open(p).read().replace("always_comb", "always @*")      # the card flow reads plain Verilog (no -sv): always_comb is a SystemVerilog word. The simulation uses always_comb (always @* raced at time 0 in iverilog); in synthesis the two mean the same.
    if f.endswith("pnr_top_v1.v"):
        t = t.replace("hexn_bnet_net_v1 #", "hexn_bnet_net_%s #" % nv)                      # the wrapper was written for v1: point it at the chosen netlist
        for k, v in par.items(): t = re.sub(r"parameter %s = \d+" % k, "parameter %s = %d" % (k, v), t, count=1)
    out.append("// ---- %s ----\n" % f + t + "\n")
open(os.path.join(sys.argv[1], "gen_00_bnet.v"), "w").write("".join(out))
print("prebuild: merged bus network %s, %s, %d files from %s" % (nv, par, len(files), repo))
