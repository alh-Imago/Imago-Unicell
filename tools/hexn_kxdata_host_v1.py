#!/usr/bin/env python3
"""Host side of the base's DATA RAM and run-from-RAM (hexn_base_ctl_v3, 5 Nov 2026). Needs a card (or sim) built with HEXN_BASE_VER=3 (tools/hexn_kxbase_v3.py). Extends hexn_kxresults_host_v1.py; nothing there is changed.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxdata_host_v1.py run   kx_vec_7.json --array 0
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxdata_host_v1.py drain kx_vec_7.json --array 0 [--runs 600] [--wait 2000]
'run'   : load the vector's chain, arm and clear the results RAM, store the vector's inputs and ONE go in the data RAM, run it from the RAM ('H'), read the records back, compare with the vector.
'drain' : store the inputs and --runs gos (the same inputs again and again) in the data RAM and run them; whenever the controller stops at a go because the results RAM is FULL ('F'), read every record back (each is compared with the vector's words and ticks), clear, and continue from where it stopped, until all gos are done.
Entry format (8 bytes): b0 bit 7 = 0: set input, b0[2:0] = row, b1..b4 = word; b0 bit 7 = 1: go, b0[6:0] = row mask, b1 b2 = clocks to wait after the go; see hexn_base_ctl_v3.v. Run from ~/ypcb-00338-1p1 (finds the openocd.cfg there)."""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("HEXN_CHAIN", "2")
try: import serial
except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
import hexn_hexcard_host_v1 as Hh, hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB, hexn_kxresults_host_v1 as R


def entry_d(row, word): return bytes([row & 7]) + word.to_bytes(4, "little") + bytes(3)
def entry_g(mask, wait): return bytes([0x80 | (mask & 0x7f)]) + wait.to_bytes(2, "little") + bytes(5)


def entries_for(t, gos=1, wait=2000):
    """a vector test as data RAM entries: its inputs, then `gos` goes (the same inputs held for each)"""
    return [entry_d(r, w) for r, w in t["inputs"]] + [entry_g(t["mask"], wait)] * gos


def data_store(link, addr, entries):
    link.write(b"T" + addr.to_bytes(2, "big") + len(entries).to_bytes(2, "big") + b"".join(entries)); Hh.k(link, "T store")


def data_run(link, addr, n):
    """-> (status letter: K all done, F stopped at a go because the results RAM is FULL, E the frame did not answer; entries executed)"""
    link.write(b"H" + addr.to_bytes(2, "big") + n.to_bytes(2, "big")); b = Hh.rd(link, 3, "H run")
    return chr(b[0]), b[1] | b[2] << 8


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "drain"]); ap.add_argument("vector"); ap.add_argument("--array", type=int, default=0)
    ap.add_argument("--runs", type=int, default=600); ap.add_argument("--wait", type=int, default=2000); a = ap.parse_args()
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000); ok = True
    try:
        print("base:", KB.info(link)); v = json.load(open(a.vector)); t = v["tests"][0]; KB.select(link, a.array)
        pid, rows = Hh.ident(link); print("array %d: id %08X rows %d; vector id %s" % (a.array, pid, rows, v["pattern_id_hex"])); ok = pid == int(v["pattern_id_hex"], 16)
        link.write(b"W"); Hh.k(link, "wipe"); link.write(b"B" + bytes.fromhex(t["chain_hex"])); Hh.k(link, "chain load")
        R.results_arm(link, True); exp = [tuple(e) for e in t["expected"]]; nd = len(t["inputs"])
        if a.cmd == "run":
            e = entries_for(t, 1, a.wait); data_store(link, 0, e); t0 = time.time(); s, n = data_run(link, 0, len(e)); print("run from the data RAM: status %s, %d of %d entries, %.3f s" % (s, n, len(e), time.time() - t0))
            st = R.results_status(link); recs = R.results_read(link); got = [(r["row"], r["word"], r["tick"]) for r in recs]
            for r in recs: print("  record %d: row %d tick %d word 0x%08x" % (r["index"], r["row"], r["tick"], r["word"]))
            good = s == "K" and n == len(e) and got == exp and st["lost"] == 0; ok &= good; print("DATA RAM RUN %s" % ("PASS" if good else "FAIL"))
        else:
            e = entries_for(t, a.runs, a.wait)
            if len(e) > 512: raise SystemExit("data RAM holds 512 entries (the default build); %d needed: lower --runs (at most %d)" % (len(e), 512 - nd))
            data_store(link, 0, e); pos = 0; total = 0; stops = 0; bad = 0; t0 = time.time()
            while pos < len(e):
                s, n = data_run(link, pos, len(e) - pos); pos += n; st = R.results_status(link); recs = R.results_read(link); total += len(recs)
                for k in range(0, len(recs), len(exp)):
                    if [(r["row"], r["word"], r["tick"]) for r in recs[k:k + len(exp)]] != exp: bad += 1
                print("H stopped %s after %d entries (position %d of %d): %d records read back, lost %d" % (s, n, pos, len(e), len(recs), st["lost"])); R.results_off(link, False); R.results_arm(link, True)
                if s == "F": stops += 1
                elif s != "K": print("run ended with status %s" % s); ok = False; break
            good = ok and total == a.runs * len(exp) and bad == 0 and stops >= 1; ok = good
            print("DRAIN %s: %d gos, %d records (expected %d), %d wrong groups, %d stops at FULL, %.2f s" % ("PASS" if good else "FAIL", a.runs, total, a.runs * len(exp), bad, stops, time.time() - t0))
        R.results_off(link, True)
        print("frames: %d scans, %d bad captures (CRC), %d resent frames" % (link.scans, link.bad, link.resends))
    finally: ex.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__": main()
