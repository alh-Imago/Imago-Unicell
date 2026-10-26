#!/usr/bin/env python3
"""prebuild.py for hexn_recall (clone of ../hexn_sweep/prebuild.py, left untouched; fixed design, no variants): core v4, lattice v18, bank v19, hexn_loader_v1. Writes gen_00_hexn.v into the build folder (argument 1) with the defines and every RTL file of the design.
Settings (environment): HEXN_REPO = the Imago-Unicell checkout (default ~/Imago-Unicell; use ~/hexn-wt), HEXN_SHAPE = hex7 or hex19 (default hex7), HEXN_NCELL = cells behind the glue buffer (default 7)."""
import os, sys
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/Imago-Unicell")); shape = os.environ.get("HEXN_SHAPE", "hex7"); ncell = int(os.environ.get("HEXN_NCELL", "7")); K = {"hex7": 7, "hex19": 19}[shape]
core, lat = "v4", "v18"
files = ["rtl/hexn_jtag_bridge_v1.v", "rtl/hexn_core_v4.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_%s_w18_v18.v" % shape, "rtl/hexn_bank_v19.v", "rtl/hexn_loader_v1.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
out = [("`define CORE_MOD hexn_core_v4\n`define LATMOD hexn_lattice_%s_v18\n`define NBW 18\n`define AWB 7\n`define NCLS %d\n`define NCELL %d\n`define ACCMODE 0\n`define CLKDIV 434\n") % (shape, K, ncell)]
for f in files:
    p = os.path.join(repo, f)
    if not os.path.exists(p): sys.exit("prebuild: %s not found (set HEXN_REPO to the checkout, branch Hex-N, git pull)" % p)
    out.append("// ---- %s ----\n" % f + open(p).read() + "\n")
open(os.path.join(sys.argv[1], "gen_00_hexn.v"), "w").write("".join(out))
print("prebuild: hexn_recall (core %s, lattice %s, bank v19, loader v1), %s, %d cells, %d files from %s" % (core, lat, shape, ncell, len(files), repo))
