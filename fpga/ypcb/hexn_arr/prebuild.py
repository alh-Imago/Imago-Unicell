#!/usr/bin/env python3
"""prebuild.py for designs/hexn_arr (the ypcb build flow runs it with the build directory as argument): writes gen_00_hexn_arr.v there, ONE file holding the RTL of the design and the JTAG bridge.
Settings (environment): HEXN_REPO = the Imago-Unicell checkout (default ~/hexn-wt, branch Hex-N).
  ONE ARRAY (tools/hexn_kxarr_v1.py): HEXN_REF = the pattern reference JSON (default docs/hex-n/data/hexrefs/hex7_off2_mix.json; also hex6.json, hex5.json); HEXN_FRAME=v4|v5 (v5 adds the S status command); HEXN_NORAM=1|ram|srl (no inferred RAM32M / SRL16E).
  BASE (tools/hexn_kxbase_v1.py): HEXN_BASE = comma list of pattern names, e.g. hex7_off2_mix,hex6,hex5 (up to 4): judge + those arrays + program library in one design; HEXN_NORAM as above; HEXN_LIBREG=1 makes the library flip-flops instead of block RAM.
The board top (hexn_arr.v) and the pins (hexn.xdc) are static files of this folder. Does not touch a board."""
import os, subprocess, sys
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/hexn-wt"))
base = os.environ.get("HEXN_BASE")
if base:
    tool = os.path.join(repo, "tools", "hexn_kxbase_v1.py"); refs = [os.path.join(repo, "docs/hex-n/data/hexrefs", n + ".json") for n in base.split(",")]
    for p in [tool] + refs:
        if not os.path.exists(p): sys.exit("prebuild: %s not found (git pull in %s; names in HEXN_BASE are hex7_off2_mix, hex6, hex5)" % (p, repo))
    sys.exit(subprocess.call([sys.executable, tool, "build", sys.argv[1]] + refs))
ref = os.path.expanduser(os.environ.get("HEXN_REF", os.path.join(repo, "docs/hex-n/data/hexrefs/hex7_off2_mix.json")))
tool = os.path.join(repo, "tools", "hexn_kxarr_v1.py")
for p in (tool, ref):
    if not os.path.exists(p): sys.exit("prebuild: %s not found (set HEXN_REPO to the Imago-Unicell checkout, branch Hex-N, git pull; HEXN_REF to a pattern reference JSON)" % p)
sys.exit(subprocess.call([sys.executable, tool, "build", ref, sys.argv[1]]))
