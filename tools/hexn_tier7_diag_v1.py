"""Diagnose the tier link on the card when a second run fails after a first one worked (29 Oct 2026: first `--info` run answered, the next run: 'the card answered 0 of 8 bytes'). It separates three suspects: the JTAG bridge (does a plain poll still return a good frame, what are its counters?), the tier command layer (does an unknown opcode 0x99 still get its 0xEE answer, does INFO answer?), and per-session state (does a fresh link in the same process, or a fresh OpenOCD, behave differently?).
Usage (from ~/ypcb-00338-1p1, nix shell with openocd, same as the card script):
    nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/tools/hexn_tier7_diag_v1.py
Option --sessions N (default 3): how many fresh links (same OpenOCD) to try; --polls N (default 3000): poll limit per read before giving up. Prints only facts it read; no pass/fail beyond the lines."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_jtag_host_v1 as J, hexn_tier7_host_v1 as H
def show(tag, ln):
    print("  %s: seq %d abs_got %d rxfree %d rxq %d scans %d bad_crc %d resends %d" % (tag, ln.seq, ln.abs_got, ln.rxfree, len(ln.rxq), ln.scans, ln.bad, ln.resends))
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sessions", type=int, default=3); ap.add_argument("--polls", type=int, default=3000); a = ap.parse_args()
    cands = [os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")]
    cfg = next((c for c in cands if c and os.path.isfile(c)), None)
    if cfg is None: sys.exit("openocd.cfg not found; set OPENOCD_CFG or run from ~/ypcb-00338-1p1")
    os.environ["HEXN_CHAIN"] = "3"; ex = J.OpenOCDExec(cfg)
    try:
        for s in range(a.sessions):
            print("session", s); ln = J.JtagLink(ex.scan, maxpoll=a.polls)
            try: ln._sync(); show("after sync", ln)
            except Exception as e: print("  sync failed:", e); continue
            raw = ex.scan(J.pack(0, 0, 0, b"")); u = J.unpack(raw); print("  plain poll: crc_ok %s nvalid %d pop %d echo %d rxfree %d" % (u["ok"], u["nvalid"], u["pop"], u["echo"], u["rxfree"]))
            for name, c, n in (("unknown opcode 0x99 (expect 0xEE)", b"\x99", 1), ("INFO", H.cmd_info(), 8), ("INFO again", H.cmd_info(), 8)):
                try:
                    ln.write(c); r = ln.read(n); print("  %s -> %s" % (name, r.hex())); 
                except Exception as e: print("  %s -> FAILED: %s" % (name, e)); show("state", ln)
    finally: ex.close()
if __name__ == "__main__": main()
