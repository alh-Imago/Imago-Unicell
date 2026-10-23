"""Hex-N ALL-CELLS test (Kintex card, any NCELL up to 255; also the Tang with its NCELL). New file; builds on tools/hexn_tang_leak_v2.py (LeakBoard, FakeLeakBoard) and the Python chain of tools/hexn_cellbank_check_v4.py.
Trains the board with the script, then loads EVERY cell n = 0..NCELL-1 with its own random lane settings (0 off, 1 positive, 2 negative per detector) and threshold, and plays episodes of windows with leak settings (the first window of an episode with the leak cleared). After every window RUNCELLN is compared, for all cells, with the Python chain: each cell's forward total and output burst count. Prints the number of differing cells/frames and CELLS TEST PASS or FAIL. The leaky-cell test v2 only loads cells 0..classes-1; this one covers the other cells of a big build.
Usage on the card (from ~/ypcb-00338-1p1): python3 ~/hexn-wt/tools/hexn_card_run_v1.py tools/hexn_tang_cells_v1.py docs/hex-n/frontend/example_random19_script_v1.txt --ncell 128 [--episodes 40]      |  --selftest (Python stand-in)"""
import sys, os, argparse, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_cellbank_check_v4 as C4, hexn_tang_leak_v2 as L
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--ncell", type=int, required=True)
    ap.add_argument("--episodes", type=int, default=40); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--hw-s", type=int, default=16); ap.add_argument("--seed", type=int, default=3); ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    d = S1.parse_script(open(a.script).read()); K, NB, AW = d["classes"], d["wires"], d["aw"]; NC = a.ncell
    assert K <= 20 and NB == 18 and AW == 7 and 1 <= NC <= 255, "needs 18 wires, AW 7, at most 20 classes and 1..255 cells"
    m = S1.make_model(d, a.hw_s); r = random.Random(a.seed)
    if a.selftest: H.M.t5.mc.AW = AW; ser = L.FakeLeakBoard(m)
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5)
    b = L.LeakBoard(ser, K, NB)
    if not a.selftest and not b.sync(): sys.exit(2)
    b.train(m); got = b.dump(); bad_set = sum(1 for k in range(K) if got[k] != (sum(1 << j for j in range(NB) if m["wts"][k][j] > 0), sum(1 << j for j in range(NB) if m["wts"][k][j] < 0), m["thr"][k]))
    print("trained settings: %d of %d detectors differ from the rules" % (bad_set, K))
    cfg = [[r.choice((0, 0, 1, 1, 2)) for _ in range(K)] for _ in range(NC)]; thr = [r.randrange(0, 12) for _ in range(NC)]
    for n in range(NC): b.loadcelln(n, thr[n], cfg[n])
    tpl = {}
    for bits, y in d["train"] + d["test"]: tpl.setdefault(y, []).append(bits)
    frames = bad_frames = bad_cells = fired = 0; seen_bad = []
    for ep in range(a.episodes):
        s = r.choice((1, 2, 3, 7)); state = [0] * NC; y = r.randrange(K); base = r.choice(tpl[y])
        for w in range(6):
            bits = [x ^ (1 if r.random() < a.noise else 0) for x in base]; lk = 0 if w == 0 else s; b.setleak(lk)
            lens = S1.classify(m, bits)[1]; exp = [C4.cell_run(K, lens, cfg[n], thr[n], C4.leaked(state[n], lk)) for n in range(NC)]; state = [e[0] for e in exp]
            tot, cnt = b.runcelln(H.mask(bits), NC); frames += 1
            bad = [n for n in range(NC) if tot[n] != exp[n][0] or cnt[n] != exp[n][1]]; fired += sum(1 for e in exp if e[1] > 0)
            if bad:
                bad_frames += 1; bad_cells += len(bad)
                if len(seen_bad) < 5: seen_bad.append((ep, w, bad[0], "board total/count %d/%d, rules %d/%d" % (tot[bad[0]], cnt[bad[0]], exp[bad[0]][0], exp[bad[0]][1])))
    print("%d cells, %d frames: frames with any cell differing: %d; differing cell results: %d of %d; cell outputs that fired (rules): %d" % (NC, frames, bad_frames, bad_cells, frames * NC, fired))
    for x in seen_bad: print("   first differences: episode %d window %d cell %d: %s" % x)
    ok = not (bad_set or bad_frames); print("CELLS TEST PASS" if ok else "CELLS TEST FAIL"); sys.exit(0 if ok else 1)
if __name__ == "__main__": main()
