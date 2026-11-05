#!/usr/bin/env python3
"""Host side of the base's WEIGHT STORE and cross-index (hexn_base_ctl_v4, 5 Nov 2026). Needs a card (or sim) built with HEXN_BASE_VER=4 (tools/hexn_kxbase_v4.py). Extends hexn_kxbase_host_v1.py; nothing there is changed.
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxweights_host_v1.py selftest kx_vec_7.json --array 0
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxweights_host_v1.py dump 0 --out set0.json      (read weight set 0 back to a file)
  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 hexn_kxweights_host_v1.py restore set0.json [--save 1]  (send a file's words to the judge; --save s also stores them as set s)
'selftest': weights are loaded into the judge, saved as set 1, overwritten, restored with 'F' (scores compared at each step); then the vector's program is written to library slot 0, tied to set 1 ('E'), the weights overwritten, and 'Q' must bring weights and program back together; the tie is removed at the end.
Set 0 is left alone by the selftest. Run from ~/ypcb-00338-1p1 (finds the openocd.cfg there)."""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("HEXN_CHAIN", "2")
try: import serial
except ImportError: import types; sys.modules["serial"] = types.ModuleType("serial")
import hexn_hexcard_host_v1 as Hh, hexn_jtag_host_v1 as J, hexn_kxarr_host_v1 as KA, hexn_kxbase_host_v1 as KB

WORDS = 257                          # 128 x (class 0, class 1) + the bias word
SCORE = 3 | (2 << 4)


def weights_save(link, s): link.write(b"O" + bytes([s])); b = Hh.rd(link, 1, "O save"); return b == b"K"
def weights_load(link, s): link.write(b"F" + bytes([s])); Hh.k(link, "F load")
def weights_index(link, slot, s): link.write(b"E" + bytes([slot, s])); Hh.k(link, "E index")          # s >= 4 removes the tie


def weights_read(link, s, first=0, n=WORDS):
    """words first .. first+n-1 of set s (at most 255 per request)"""
    out = []
    while n > 0:
        k = min(n, 255); link.write(b"r" + bytes([s, first >> 8, first & 255, k])); b = Hh.rd(link, 4 * k, "r read")
        out += [int.from_bytes(b[4 * i:4 * i + 4], "little") for i in range(k)]; first += k; n -= k
    return out


def score(link):
    """one SCORE word through the judge -> its result word (s1 << 16 | s0 for these small weights)"""
    KB.mode(link, 2); KB.judge_word(link, SCORE); n, r, lost = KB.judge_result(link); return r if n else None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dump", "restore"]); ap.add_argument("arg"); ap.add_argument("--array", type=int, default=0)
    ap.add_argument("--out"); ap.add_argument("--save", type=int); a = ap.parse_args()
    ex = J.OpenOCDExec(KA.find_cfg()); link = J.JtagLink(ex.scan, maxpoll=3000); ok = True
    try:
        print("base:", KB.info(link))
        if a.cmd == "dump":
            w = weights_read(link, int(a.arg)); json.dump(dict(set=int(a.arg), words=w), open(a.out, "w")); print("wrote %d words to %s (%d non-zero entries besides the headers)" % (len(w), a.out, sum(1 for x in w[:-1] if x & 255)))
        elif a.cmd == "restore":
            w = json.load(open(a.arg))["words"]
            for x in w: KB.judge_word(link, x)
            print("sent %d words to the judge" % len(w))
            if a.save is not None: print("saved as set %d:" % a.save, weights_save(link, a.save))
        else:
            v = json.load(open(a.arg)); t = v["tests"][0]; KB.select(link, a.array); chain = bytes.fromhex(t["chain_hex"])
            OLD, NEW = 0x00050007, 0x0009000b; LD = KB.LOAD
            KB.judge_word(link, LD(1, 3, 5)); KB.judge_word(link, LD(0, 18, 7)); r1 = score(link); print("scored with the first weights: 0x%08x (expect 0x%08x)" % (r1 or 0, OLD)); ok &= r1 == OLD
            print("save as set 1:", weights_save(link, 1)); w = weights_read(link, 1, 6, 2); print("words 6, 7 of set 1: 0x%08x 0x%08x (expect 0x%08x 0x%08x)" % (w[0], w[1], LD(0, 3, 0), LD(1, 3, 5))); ok &= w == [LD(0, 3, 0), LD(1, 3, 5)]
            KB.judge_word(link, LD(1, 3, 9)); KB.judge_word(link, LD(0, 18, 11)); r2 = score(link); print("overwritten: 0x%08x (expect 0x%08x)" % (r2 or 0, NEW)); ok &= r2 == NEW
            weights_load(link, 1); r3 = score(link); print("after F 1: 0x%08x (expect 0x%08x)" % (r3 or 0, OLD)); ok &= r3 == OLD
            link.write(b"P\x00" + len(chain).to_bytes(2, "big") + chain); Hh.k(link, "library write"); weights_index(link, 0, 1)
            KB.judge_word(link, LD(1, 3, 9)); KB.judge_word(link, LD(0, 18, 11)); print("before Q 0 (tied to set 1): 0x%08x" % (score(link) or 0))
            KB.library_load(link, 0); r4 = score(link); print("after Q 0: 0x%08x (expect 0x%08x)" % (r4 or 0, OLD)); ok &= r4 == OLD
            weights_index(link, 0, 255); KB.judge_word(link, LD(1, 3, 9)); KB.judge_word(link, LD(0, 18, 11)); KB.library_load(link, 0); r5 = score(link); print("tie removed, Q 0 again: 0x%08x (expect 0x%08x, weights unchanged)" % (r5 or 0, NEW)); ok &= r5 == NEW
            print("WEIGHT STORE %s" % ("PASS" if ok else "FAIL"))
        print("frames: %d scans, %d bad captures (CRC), %d resent frames" % (link.scans, link.bad, link.resends))
    finally: ex.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__": main()
