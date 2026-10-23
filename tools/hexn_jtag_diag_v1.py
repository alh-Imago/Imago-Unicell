#!/usr/bin/env python3
"""Step-by-step look at the JTAG link on the card: raw polls, one data frame, what the card sends back. Run (from ~/ypcb-00338-1p1): nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/Imago-Unicell/tools/hexn_jtag_diag_v1.py"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_jtag_host_v1 as J
cfg = next((c for c in (os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")) if c and os.path.isfile(c)), None)
ex = J.OpenOCDExec(cfg); ex.s.settimeout(15)
def tryscan(label, v):
    t = time.time()
    try: r = ex.scan(v); print("%-28s sent %040x\n%-28s got  %040x  (%.0f ms)" % (label, v, "", r, (time.time() - t) * 1000)); return r
    except Exception as e: print("%-28s FAILED after %.1f s: %s" % (label, time.time() - t, str(e)[:700])); return None
try:
    for i in range(3): tryscan("poll %d" % i, J.pack(0, 0, 0, b""))
    print("-- raw drscan reply text for a poll:", repr(ex.cmd("drscan %s 160 0x%x" % (ex.tap, J.pack(0, 0, 0, b"")))))
    r = tryscan("1-byte data frame (0x20)", J.pack(1, 0, 1, bytes([0x20])))
    if r is not None: print("   decoded:", J.unpack(r))
    for i in range(3): r = tryscan("poll after", J.pack(0, 0, 1, b"")); print("   decoded:", J.unpack(r) if r is not None else None)
finally:
    ex.close()
print("OpenOCD log:\n" + (open("/tmp/hexn_openocd.log").read()[-1200:] if os.path.exists("/tmp/hexn_openocd.log") else "(none)"))
