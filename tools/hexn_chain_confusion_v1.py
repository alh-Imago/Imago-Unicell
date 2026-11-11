"""hexn_chain_confusion_v1 (11 Nov 2026): where the speech chain's errors go. Alan 19:07 (the weak digits can be tested). Direction doc section 93. Python reference only (the card gives the same answers: section 85).
Same data build and training as the kit (tools/hexn_chain_kitdata_v1.py). For the 1,079 test recordings: the confusion table at the kit's decision point (after window 3), right answers per digit after each of the 5 windows,
and for the wrong answers how close they were (was the right digit second best in the final score?). Also the same table on the TRAINING recordings, to tell 'not learnt' from 'does not carry over to new speakers'.
Usage: python3 tools/hexn_chain_confusion_v1.py DIR    (DIR holds shd_train.h5 and shd_test.h5)"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
import hexn_chain_hw_v1 as M, hexn_det_shd_v1 as D, hexn_det_net_v1 as N


def table(P, X, y, name, new=None):
    nw = P.nwin; conf = np.zeros((M.NC, M.NC), int); perwin = np.zeros((M.NC, nw), int); tot = np.zeros(M.NC, int); second = 0; wrong = 0; newmask = np.zeros(len(y), bool)
    if new is not None: newmask[new] = True
    okn = [0, 0]; oko = [0, 0]
    for i in range(len(y)):
        res = M.run_recording(P, M.events_of(X[i])); t = int(y[i]); tot[t] += 1
        for w in range(nw): perwin[t, w] += (res[w]["pred"] == t)
        p = res[2]["pred"]; conf[t, p] += 1
        if p != t:
            wrong += 1; S = res[2]["S"]; order = sorted(range(M.NC), key=lambda c: (-S[c], c)); second += (order[1] == t)
        a = okn if newmask[i] else oko; a[0] += (p == t); a[1] += 1
    print("\n%s: %d recordings, right after window 3: %d (%.1f%%)" % (name, len(y), int(np.trace(conf)), 100.0 * np.trace(conf) / len(y)))
    if new is not None and okn[1]: print("   speakers never heard in training: %d of %d (%.1f%%); speakers also in training: %d of %d (%.1f%%)" % (okn[0], okn[1], 100.0 * okn[0] / okn[1], oko[0], oko[1], 100.0 * oko[0] / oko[1]))
    print("   wrong answers: %d; in %d of them (%.0f%%) the right digit was second best" % (wrong, second, 100.0 * second / max(1, wrong)))
    print("   said (rows) -> answered (columns)    " + " ".join("%4d" % c for c in range(M.NC)) + "   | right % after window 1..5")
    for t in range(M.NC): print("   digit %d (%3d)                        " % (t, tot[t]) + " ".join("%4s" % (conf[t, c] if conf[t, c] else ".") for c in range(M.NC)) + "   | " + " ".join("%3.0f" % (100.0 * perwin[t, w] / tot[t]) for w in range(nw)))
    print("   answered wrongly AS each digit:       " + " ".join("%4d" % (conf[:, c].sum() - conf[c, c]) for c in range(M.NC)))


def main(d):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); P = M.train(Xtr3, ytr, 5, N.NIN, gap=10)
    table(P, Xte3, yte, "TEST set", new); table(P, Xtr3, ytr, "TRAINING set (the recordings the chain was built from)")


if __name__ == "__main__": main(sys.argv[1])
