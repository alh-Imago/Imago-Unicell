#!/usr/bin/env python3
"""Talk to a Kintex array card (fpga/ypcb/hexn_arr, frame v4 behind the JTAG bridge on USER2) from the OptiPlex (4 Nov 2026). Same commands and same vector files as the Tang host (tools/hexn_hexcard_host_v1.py), but the transport is OpenOCD + the frame link of tools/hexn_jtag_host_v1.py.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 hexn_kxarr_host_v1.py id
  nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 hexn_kxarr_host_v1.py selftest VECTOR.json
Run from ~/ypcb-00338-1p1 (it finds board/ypcb-00338-1p1/openocd.cfg there) or set OPENOCD_CFG. Needs the board's cable free (no hw_server/xsdb running). Makes the vector with tools/hexn_hexcard_vector_v2.py."""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("HEXN_CHAIN", "2")
import hexn_hexcard_host_v1 as Hh, hexn_jtag_host_v1 as J


def find_cfg():
    for c in (os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")):
        if c and os.path.isfile(c): return c
    sys.exit("openocd.cfg not found; set OPENOCD_CFG=<path to board/ypcb-00338-1p1/openocd.cfg> or run from ~/ypcb-00338-1p1")


def selftest(link, v, out=print):
    """-> True if the id matches and every test's words and ticks equal the vector"""
    pid, rows = Hh.ident(link)
    out("card: id %08X rows %d; vector: id %s rows %d" % (pid, rows, v["pattern_id_hex"], v["rows"]))
    ok = pid == int(v["pattern_id_hex"], 16) and rows == v["rows"]
    if not ok: out("ID MISMATCH: wrong design on the card?")
    for t in v["tests"]:
        got = Hh.run_test(link, t); good = got == t["expected"]; ok &= good
        out("%-8s %s  words %s" % (t["name"], "PASS" if good else "FAIL", [hex(w) for _, w, _ in got]))
        if not good: out("   expected %s\n   got      %s" % (t["expected"], got))
    out("SELFTEST " + ("PASS" if ok else "FAIL")); return ok


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["id", "selftest"]); ap.add_argument("vector", nargs="?"); a = ap.parse_args()
    ex = J.OpenOCDExec(find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000)
    try:
        if a.cmd == "id": pid, rows = Hh.ident(link); print("pattern id %08X rows %d" % (pid, rows)); ok = True
        else: ok = selftest(link, json.load(open(a.vector)))
        print("frames: %d scans, %d bad captures (CRC), %d resent frames" % (link.scans, link.bad, link.resends))
    finally:
        ex.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
