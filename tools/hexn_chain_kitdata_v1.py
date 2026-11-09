"""hexn_chain_kitdata_v1 (10 Nov 2026): writes the data files of the Kintex kit fpga/ypcb/hexn_speech/ : the trained chain (wrom, thr, lp, cfg hex), the replay program of the 300 test recordings (prog.hex, 16-bit words, 0xFFFF ends it) and their labels (lab.hex), plus EXPECTED.txt (what the model says the chain gets right after window DECIDE_WIN). Direction doc section 63.
Usage: python3 tools/hexn_chain_kitdata_v1.py DIR OUTDIR    (DIR holds shd_train.h5 and shd_test.h5)"""
import sys, os, random, importlib.util, pathlib
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_chain_hw_v1 as M, hexn_det_shd_v1 as D, hexn_det_net_v1 as N
sp = importlib.util.spec_from_file_location("tc", os.path.join(ROOT, "tests", "vm", "test_hexn_speech_chain_v1.py")); T = importlib.util.module_from_spec(sp); sp.loader.exec_module(T)
DECIDE_WIN = 2


def main(d, out):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); P = M.train(Xtr3, ytr, 5, N.NIN, gap=10)
    r0 = random.Random(0); pick = []
    for c in range(M.NC): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    random.Random(11).shuffle(pick); pick = np.array(pick); y = yte[pick]; recs = [M.events_of(Xte3[i]) for i in pick]
    o = pathlib.Path(out); o.mkdir(parents=True, exist_ok=True); T.write_files(o, P, recs)
    with open(o / "prog.hex", "a") as f: f.write("ffff\n")
    (o / "lab.hex").write_text("\n".join("%x" % v for v in y) + "\n")
    ok = sum(M.run_recording(P, e)[DECIDE_WIN]["pred"] == t for e, t in zip(recs, y))
    (o / "EXPECTED.txt").write_text("recordings %d\ndecide_after_window %d\ncorrect %d\n" % (len(recs), DECIDE_WIN + 1, ok))
    print("wrote", o, "recordings", len(recs), "correct after window %d: %d" % (DECIDE_WIN + 1, ok), "prog words", len((o / "prog.hex").read_text().split()))


if __name__ == "__main__": main(*sys.argv[1:3])
