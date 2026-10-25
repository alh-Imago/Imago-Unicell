"""(hexn_sweep: clone of ../hexn_u2/prebuild.py, left untouched, plus HEXN_VARIANT = base | A | B | AB: A = bank v18 + lattice v17 (cell controls registered), B = core v3 (readout from a shifted result register), AB = both. base is exactly the hexn_u2 design.)"""
#!/usr/bin/env python3
"""prebuild.py for the ypcb-00338-1p1 build flow (tools/xc7-build.sh runs it with the build directory as argument): writes gen_00_hexn.v there, ONE file holding the `defines and every RTL file of the Hex-N core, so the flow's `yosys ... gen_*.v *.v` sees them first and in one piece.
Settings (environment): HEXN_REPO = the Imago-Unicell checkout (default ~/Imago-Unicell); HEXN_SHAPE = hex7 or hex19 (default hex19); HEXN_NCELL = cells behind the glue buffer (default 19).
Lattice v16 / bank v17 / cell v5 are the versions that closed 50 MHz on this card (see docs/hex-n/HEXN_DESIGN.md)."""
import os, sys
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/Imago-Unicell")); shape = os.environ.get("HEXN_SHAPE", "hex19"); ncell = int(os.environ.get("HEXN_NCELL", "19")); K = {"hex7": 7, "hex19": 19}[shape]
var = os.environ.get("HEXN_VARIANT", "base"); assert var in ("base", "A", "B", "AB"), "HEXN_VARIANT must be base, A, B or AB"
core = "v3" if "B" in var else "v2"; lat = "v17" if "A" in var else "v16"; bank = "v18" if "A" in var else "v17"
files = ["rtl/hexn_jtag_bridge_v1.v", "rtl/hexn_core_%s.v" % core, "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_%s_w18_%s.v" % (shape, lat), "rtl/hexn_bank_%s.v" % bank, "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
out = [("`define CORE_MOD hexn_core_%s\n`define LATMOD hexn_lattice_%s_%s\n`define NBW 18\n`define AWB 7\n`define NCLS %d\n`define NCELL %d\n`define ACCMODE 0\n`define CLKDIV 434\n") % (core, shape, lat, K, ncell)]
for f in files:
    p = os.path.join(repo, f)
    if not os.path.exists(p): sys.exit("prebuild: %s not found (set HEXN_REPO to the Imago-Unicell checkout, branch Hex-N, git pull)" % p)
    out.append("// ---- %s ----\n" % f + open(p).read() + "\n")
open(os.path.join(sys.argv[1], "gen_00_hexn.v"), "w").write("".join(out))
print("prebuild: variant %s (core %s, lattice %s, bank %s), %s, %d cells, %d files from %s" % (var, core, lat, bank, shape, ncell, len(files), repo))
