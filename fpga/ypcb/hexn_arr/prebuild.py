#!/usr/bin/env python3
"""prebuild.py for designs/hexn_arr (the ypcb build flow runs it with the build directory as argument): writes gen_00_hexn_arr.v there, ONE file holding the RTL of one hex pattern array, its byte-port frame and the JTAG bridge.
Settings (environment): HEXN_REPO = the Imago-Unicell checkout (default ~/hexn-wt, branch Hex-N); HEXN_REF = the pattern reference JSON (default docs/hex-n/data/hexrefs/hex7_off2_mix.json in that checkout; also hex6.json, hex5.json).
The board top (hexn_arr.v) and the pins (hexn.xdc) are static files of this folder. Does not touch a board."""
import os, subprocess, sys
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/hexn-wt"))
ref = os.path.expanduser(os.environ.get("HEXN_REF", os.path.join(repo, "docs/hex-n/data/hexrefs/hex7_off2_mix.json")))
tool = os.path.join(repo, "tools", "hexn_kxarr_v1.py")
for p in (tool, ref):
    if not os.path.exists(p): sys.exit("prebuild: %s not found (set HEXN_REPO to the Imago-Unicell checkout, branch Hex-N, git pull; HEXN_REF to a pattern reference JSON)" % p)
sys.exit(subprocess.call([sys.executable, tool, "build", ref, sys.argv[1]]))
