#!/usr/bin/env python3
"""Host for the Kintex BASE design (judge + arrays + program library; 5 Nov 2026). Same link as hexn_kxarr_host_v1.py (OpenOCD + the JTAG frame link on USER2). Commands of the base: sub/verilog/hexn_base_ctl_v1.v.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxbase_host_v1.py info
  ... hexn_kxbase_host_v1.py selftest VECTOR.json [--array N] [--library]    run the first test of a vector on array N; --library writes the chain into library slot 0 and loads the array from there ('P' then 'Q')
  ... hexn_kxbase_host_v1.py judge VECTOR.json [--array N]                  AFTER mode: weights loaded, the array's output word is scored by the judge on its own, then read back with 'R' (the 5x5 vector's word 0x6bdc696a gives result word 0x00090014 with the weights set here)
Run from ~/ypcb-00338-1p1 (it finds the openocd.cfg there). Needs a card loaded with a base bitstream (HEXN_BASE=... build)."""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("HEXN_CHAIN", "2")
try: import serial
except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
import hexn_hexcard_host_v1 as Hh, hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA

LOAD = lambda cls, addr, wt: (12 << 28) | (cls << 24) | (addr << 16) | (wt & 255)
BIAS = lambda b: (13 << 28) | (b & 0xffff)


def info(link):
    link.write(b"N"); b = Hh.rd(link, 6, "N info")
    return dict(id="%08X" % int.from_bytes(b[:4], "little"), arrays=b[4], library_slots=b[5])


def select(link, n): link.write(b"A" + bytes([n])); Hh.k(link, "select array")


def library_write(link, slot, data): link.write(b"P" + bytes([slot]) + len(data).to_bytes(2, "big") + data); Hh.k(link, "library write")


def library_load(link, slot): link.write(b"Q" + bytes([slot])); Hh.k(link, "library load (K from the array's chain load)")


def judge_word(link, w): link.write(b"J" + w.to_bytes(4, "little")); Hh.k(link, "judge word")


def judge_result(link):
    """-> (results waiting before this read, the oldest result word (0 if none), words lost by the judge queue)"""
    link.write(b"R"); b = Hh.rd(link, 6, "R result"); return b[0] & 15, int.from_bytes(b[1:5], "little"), b[5]


def mode(link, m): link.write(b"M" + bytes([m])); Hh.k(link, "mode")


def run_vector_test(link, t, library):
    link.write(b"W"); Hh.k(link, "wipe")
    chain = bytes.fromhex(t["chain_hex"])
    if library: library_write(link, 0, chain); library_load(link, 0)
    else: link.write(b"B" + chain); Hh.k(link, "chain load")
    for row, word in t["inputs"]:
        link.write(bytes([ord("D"), row]) + word.to_bytes(4, "little")); Hh.k(link, "D row %d" % row)
    link.write(bytes([ord("G"), t["mask"]])); Hh.k(link, "G"); time.sleep(0.3)
    link.write(b"L"); n = Hh.rd(link, 1, "L count")[0]; got = []
    for _ in range(n):
        e = Hh.rd(link, 7, "L entry"); got.append([e[0], int.from_bytes(e[1:5], "little"), int.from_bytes(e[5:7], "little")])
    return got


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["info", "selftest", "judge"]); ap.add_argument("vector", nargs="?")
    ap.add_argument("--array", type=int, default=0); ap.add_argument("--library", action="store_true"); a = ap.parse_args()
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000); ok = True
    try:
        print("base:", info(link))
        if a.cmd != "info":
            v = json.load(open(a.vector)); select(link, a.array); pid, rows = Hh.ident(link)
            print("array %d: id %08X rows %d; vector id %s rows %d" % (a.array, pid, rows, v["pattern_id_hex"], v["rows"]))
            ok = pid == int(v["pattern_id_hex"], 16) and rows == v["rows"]; t = v["tests"][0]
            if a.cmd == "selftest":
                got = run_vector_test(link, t, a.library); good = got == t["expected"]; ok &= good
                print("%-8s %s  words %s%s" % (t["name"], "PASS" if good else "FAIL", [hex(w) for _, w, _ in got], "  (chain from the library)" if a.library else ""))
                if not good: print("   expected %s\n   got      %s" % (t["expected"], got))
            else:
                mode(link, 3); judge_word(link, LOAD(1, 10, 9)); judge_word(link, LOAD(0, 75, 20))
                got = run_vector_test(link, t, False); time.sleep(0.1); n, res, lost = judge_result(link)
                print("array words %s; judge: %d result(s) waiting, oldest 0x%08x, lost %d" % ([hex(w) for _, w, _ in got], n, res, lost))
                print("expected result 0x00090014 for the 5x5 addsub word 0x6bdc696a with these weights"); ok &= (res == 0x00090014)
        print("frames: %d scans, %d bad captures (CRC), %d resent frames" % (link.scans, link.bad, link.resends))
    finally:
        ex.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
