#!/usr/bin/env python3
"""hexn_front_diag_v1: FIND WHERE A FRONT-END RUN GOES WRONG (new file 1 Nov 2026). Tests the chain one stage at a time and says which stage fails:
  1 link        : ID, and a register written and read back
  2 words       : words written to the unit's scratch RAM and read back, for several sizes (catches loss or corruption on the serial line, in the gateway or on SPI)
  3 one row     : a tiny table with two known weights, one row, one result against the reference (catches the engine / control-word path)
  4 full table  : the 96 weights of a random table loaded the way the front end loads one, then 97 probe rows (every detector slot and bin once) against the reference; lists the (slot, bin) pairs that differ
  5 many rows   : 400 random rows against the reference, one judge, then two judges
Usage: python3 tools/hexn_front_diag_v1.py (--port /dev/ttyUSB3 | --emulate)"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_open_host_v1 as H, hexn_scorer_ref_v1 as R
def main(u):
    ok = True
    def stage(name, good, detail=""):
        nonlocal ok; ok &= bool(good); print("%-12s %s %s" % (name, "ok  " if good else "FAIL", detail))
    stage("1 link", u.id() == H.UNIT_ID); u.reg_write(20, 0x12345678); stage("1 register", u.reg_read(20) == 0x12345678); u.reg_write(20, 0)
    rng = np.random.default_rng(7)
    for n in (1, 10, 100, 200, 255):
        bad = []
        for rep in range(5):
            w = [int(x) for x in rng.integers(0, 2 ** 32, size=n)]; u.write_words(0, w); r = u.read_words(0, n); bad += [i for i in range(n) if r[i] != w[i]]
        stage("2 words %3d" % n, not bad, "" if not bad else "%d of %d wrong over 5 tries, first at word %d" % (len(bad), 5 * n, bad[0]))
    # the unit KEEPS its weights between runs (by design), so clear all 192 weights first or leftovers from an earlier table would be added in
    W = np.zeros((2, 8, 16), dtype=int); W[1][0][5] = -7; W[0][0][5] = -3; u.preset(3)
    u.clear_judges("A"); u.stream([R.w_load(1, 0, 5, -7), R.w_load(0, 0, 5, -3), R.w_bias(2)])
    res = u.stream([R.w_score([5, 0, 0, 0, 0, 0, 0, 0])]); stage("3 one row", res == [R.score(W, 2, [5, 0, 0, 0, 0, 0, 0, 0])[0]], "got %s want %08x" % (["%08x" % x for x in res], R.score(W, 2, [5, 0, 0, 0, 0, 0, 0, 0])[0]))
    W = np.zeros((2, 8, 16), dtype=int); W[:, :, :12] = rng.integers(-120, 1, size=(2, 8, 12)); load = [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12)]
    u.preset(3); u.stream(load + [R.w_bias(0)])
    probes = [[0] * 8]; tag = [None]
    for s in range(8):
        for b in range(12): v = [0] * 8; v[s] = b; probes.append(v); tag.append((s, b))
    res = u.stream([R.w_score(v) for v in probes]); bad = [(tag[i], "%08x" % res[i], "%08x" % R.score(W, 0, probes[i])[0]) for i in range(len(probes)) if res[i] != R.score(W, 0, probes[i])[0]]
    stage("4 full table", not bad, "" if not bad else "%d of %d probes differ; (slot, bin) got want, first few: %s" % (len(bad), len(probes), bad[:6]))
    rows = [[int(x) for x in rng.integers(0, 12, size=8)] for _ in range(400)]; res = u.stream([R.w_score(v) for v in rows]); w1 = sum(1 for v, r in zip(rows, res) if r != R.score(W, 0, v)[0])
    stage("5 rows, 1 judge", w1 == 0, "%d of 400 wrong" % w1)
    u.preset(4); u.load_judges(load, 0, -40); res = u.stream([R.w_score(v) for v in rows]); e = []
    for v in rows: e += [R.score(W, 0, v)[0], R.score(W, -40, v)[0]]
    w2 = sum(1 for r, x in zip(res, e) if r != x); stage("5 rows, 2 judges", w2 == 0, "%d of %d result words wrong" % (w2, len(e)))
    print("ALL STAGES OK" if ok else "SOME STAGES FAILED: the first FAIL line above is the stage to look at")
    return ok
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--emulate", action="store_true"); a = ap.parse_args()
    if a.emulate: import hexn_open_emu_v1 as E; link = E.EmuLink()
    elif a.port: link = H.SerialLink(a.port)
    else: raise SystemExit("give --port or --emulate")
    sys.exit(0 if main(H.OpenUnit(link)) else 1)
