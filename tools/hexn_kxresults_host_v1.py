#!/usr/bin/env python3
"""Host side of the base's RESULTS RAM (hexn_base_ctl_v2, 5 Nov 2026). Needs a card (or sim) built with tools/hexn_kxbase_v2.py. Extends hexn_kxbase_host_v1.py; nothing there is changed.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxresults_host_v1.py run  kx_vec_7.json --array 0
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxresults_host_v1.py fill kx_vec_7.json --array 0 [--max 40]
'run'  : arm and clear the results RAM, run the vector's first test, read back status and every record, compare the records with the vector's expected words and ticks.
'fill' : the same run repeated until the controller refuses the next start with 'F' (RAM FULL); prints the status after each run, then reads every record back and clears.
Run from ~/ypcb-00338-1p1 (finds the openocd.cfg there)."""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("HEXN_CHAIN", "2")
try: import serial
except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
import hexn_hexcard_host_v1 as Hh, hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB


def parse_status(b):
    return dict(count=b[0] | b[1] << 8, lost=b[2], full=bool(b[3] & 1), armed=bool(b[3] & 2), read_pointer=b[4] | b[5] << 8, refused=b[6])


def parse_records(b):
    """b = what 'V' returned: k, then k x 8 bytes -> list of dicts"""
    k = b[0]
    if len(b) != 1 + 8 * k: raise ValueError("expected %d bytes, got %d" % (1 + 8 * k, len(b)))
    out = []
    for i in range(k):
        r = b[1 + 8 * i: 9 + 8 * i]
        out.append(dict(kind="judge" if r[0] >> 7 else "word", array=(r[0] >> 5) & 3, row=r[0] & 7, tick=int.from_bytes(r[1:3], "little"), word=int.from_bytes(r[3:7], "little"), index=r[7]))
    return out


def results_arm(link, clear=True): link.write(b"X" + bytes([1 | (2 if clear else 0)])); Hh.k(link, "X arm")


def results_off(link, clear=False): link.write(b"X" + bytes([2 if clear else 0])); Hh.k(link, "X off")


def results_status(link): link.write(b"Y"); return parse_status(Hh.rd(link, 7, "Y status"))


def results_read(link, chunk=32):
    """read every stored record from the read pointer on, `chunk` records per 'V'"""
    out = []
    while True:
        link.write(b"V" + bytes([chunk])); k = Hh.rd(link, 1, "V count")[0]
        if k == 0: return out
        out += parse_records(bytes([k]) + Hh.rd(link, 8 * k, "V records"))


def start_run(link, t, load_chain=True):
    """W, B (optional), D rows, G. -> True if the run started, False if the controller refused the start with 'F' (results RAM full)"""
    if load_chain:
        link.write(b"W"); Hh.k(link, "wipe"); link.write(b"B" + bytes.fromhex(t["chain_hex"])); Hh.k(link, "chain load")
    for row, word in t["inputs"]:
        link.write(bytes([ord("D"), row]) + word.to_bytes(4, "little")); Hh.k(link, "D row %d" % row)
    link.write(bytes([ord("G"), t["mask"]])); b = Hh.rd(link, 1, "G reply"); time.sleep(0.3)
    if b == b"F": return False
    if b != b"K": raise SystemExit("G: expected K or F, got %r" % b)
    return True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "fill"]); ap.add_argument("vector"); ap.add_argument("--array", type=int, default=0); ap.add_argument("--max", type=int, default=40)
    a = ap.parse_args(); ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000); ok = True
    try:
        print("base:", KB.info(link)); v = json.load(open(a.vector)); t = v["tests"][0]; KB.select(link, a.array)
        pid, rows = Hh.ident(link); print("array %d: id %08X rows %d; vector id %s" % (a.array, pid, rows, v["pattern_id_hex"])); ok = pid == int(v["pattern_id_hex"], 16)
        results_arm(link, True); print("status after arm:", results_status(link))
        if a.cmd == "run":
            started = start_run(link, t); print("run started:", started); st = results_status(link); print("status:", st)
            recs = results_read(link); exp = [tuple(e) for e in t["expected"]]; got = [(r["row"], r["word"], r["tick"]) for r in recs if r["kind"] == "word"]
            for r in recs: print("  record %d: %s array %d row %d tick %d word 0x%08x" % (r["index"], r["kind"], r["array"], r["row"], r["tick"], r["word"]))
            good = started and got == exp and st["lost"] == 0; ok &= good; print("RESULTS RAM %s: %d records, expected %d words" % ("PASS" if good else "FAIL", len(recs), len(exp)))
        else:
            n = 0; first = True
            while n < a.max:
                if not start_run(link, t, load_chain=first): print("run %d REFUSED ('F'): results RAM full" % (n + 1)); break
                first = False; n += 1; print("run %d: %s" % (n, results_status(link)))
            else: print("never refused in %d runs" % a.max); ok = False
            st = results_status(link); recs = results_read(link); print("final:", st, "| records read back:", len(recs))
            ok &= st["full"] and st["refused"] >= 1 and st["lost"] == 0 and len(recs) == st["count"]; print("STOP-AND-FLAG %s" % ("PASS" if ok else "FAIL"))
            results_off(link, clear=True); print("cleared:", results_status(link))
        print("frames: %d scans, %d bad captures (CRC), %d resent frames" % (link.scans, link.bad, link.resends))
    finally: ex.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__": main()
