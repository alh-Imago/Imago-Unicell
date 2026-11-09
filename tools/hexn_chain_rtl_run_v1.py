"""hexn_chain_rtl_run_v1 (10 Nov 2026): run the 300 test recordings of the spoken digits through the SIMULATED RTL (rtl/hexn_speech_chain_v1.v, iverilog; configuration written through the cfg_ port) and compare with the exact-arithmetic model. Direction doc section 63.
Usage: python3 tools/hexn_chain_rtl_run_v1.py DIR WORKDIR"""
import sys, os, random, pathlib, importlib.util
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_chain_hw_v1 as M, hexn_det_shd_v1 as D, hexn_det_net_v1 as N
sp = importlib.util.spec_from_file_location("tc", os.path.join(ROOT, "tests", "vm", "test_hexn_speech_chain_v1.py")); T = importlib.util.module_from_spec(sp); sp.loader.exec_module(T)


def main(d, work):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); P = M.train(Xtr3, ytr, 5, N.NIN, gap=10)
    r0 = random.Random(0); pick = []
    for c in range(M.NC): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    pick = np.array(pick); y = yte[pick]; is_new = np.isin(pick, new); recs = [M.events_of(Xte3[i]) for i in pick]
    w = pathlib.Path(work); w.mkdir(parents=True, exist_ok=True); T.write_files(w, P, recs); got = T.run_sim(w, 1)
    want = [(q["cls"], q["pred"], q["gap"], q["stop"]) for ev in recs for q in M.run_recording(P, ev)]
    print("RTL windows: %d, model windows: %d, identical: %s" % (len(got), len(want), got == want))
    g = np.array(got).reshape(len(recs), 5, 4)
    for p in range(5): print("  after %d windows: %.1f | %.1f" % (p + 1, 100 * np.mean(g[:, p, 1] == y), 100 * np.mean(g[is_new.nonzero()[0], p, 1] == y[is_new])))
    for gp in (5, 10, 20, 40):
        stop = (g[:, :, 2] >= gp); first = np.where(stop.any(axis=1), stop.argmax(axis=1), 4)
        print("  stop when gap >= %d (computed from the RTL gap outputs): mean windows %.2f, accuracy %.1f" % (gp, np.mean(first + 1), 100 * np.mean(g[np.arange(len(recs)), first, 1] == y)))


if __name__ == "__main__": main(*sys.argv[1:3])
