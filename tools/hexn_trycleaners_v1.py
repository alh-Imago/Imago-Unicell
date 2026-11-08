"""hexn_trycleaners_v1 (8 Nov 2026; Alan 16:27: apply the TRY-BOTH method first, the step to letting the system make choices on blind data). Simulation, host side.
For a sensor type nobody has declared, each candidate DESIGN is tried on the incoming stream and the system keeps the one that fits. A design here = a cleaner (tools/hexn_sensor_profiles_v1.py) plus the judge weights taught with that cleaner in front (teacher data with known answers, as in the agreed training scheme).
Blind score (no labels on the incoming stream): how often the design's prediction for word t agrees with the SELF label for word t, where the self label is the event read from the RAW detected classes of word t+1, counted only where that label is certain (hexn_selftrain_v1.confident). The self label is the same for every candidate, so no cleaner can raise its own score by making the stream easier to predict (a first thought was to label from each candidate's own cleaned stream; a hold of 20 makes a stream constant and would win that for nothing).
Truth score (used only to check the choice): accuracy against the event in the TRUE classes of word t+1.
Reported: which design the blind score picks, which design the truth score picks, and the REGRET = truth accuracy of the best design minus truth accuracy of the blind pick.
Task and data as in hexn_selftrain_v1 (predict a next-word event from the classes now; synthetic streams where each class lasts dwell to 2 x dwell steps).
Usage: python3 tools/hexn_trycleaners_v1.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_selftrain_v1 as S, hexn_sensor_profiles_v1 as P, hexn_bank_model_v2 as M, hexn_kxlayer1_judge_v1 as J

CANDS = ("none", "carry3", "hold3", "carry3+hold3", "hold10")


def one(seed, noise, dwell, cands=CANDS, teach_words=300, live_words=1500, teach_noise=(0.05, 0.10, 0.15)):
    m = M.make(seed, J.K, J.NB, J.AW, 16, 0.15)
    tstreams = [S.stream(m, seed * 1000 + i, teach_words, nz, dwell)[:2] for i, nz in enumerate(teach_noise)]
    truth, det, _ = S.stream(m, seed * 1000 + 60, live_words, noise, dwell)
    ys = [S.event(det[t + 1]) for t in range(len(det) - 1)]; conf = [S.confident(det[t + 1]) for t in range(len(det) - 1)]
    out = {}
    for c in cands:
        data = []
        for tr, dt in tstreams: data += [(b, y) for b, y, _ in S.pairs(tr, P.clean_columns(dt, c))]
        W, bias = S.perceptron(*S.zero(), data, 20, 8)
        live = S.pairs(truth, P.clean_columns(det, c))
        preds = [S.score(W, bias, b)[0] for b, _, _ in live]
        acc = sum(p == yt for p, (_, yt, _) in zip(preds, live)) / len(live)
        cs = [i for i in range(len(live)) if conf[i]]; blind = sum(preds[i] == ys[i] for i in cs) / max(1, len(cs))
        out[c] = (acc, blind)
    return out


def sweep(seeds=range(1, 7), noises=(0.10, 0.20, 0.30), dwells=(6, 40), cands=CANDS):
    rows = []
    for dw in dwells:
        for nz in noises:
            res = [one(sd, nz, dw, cands) for sd in seeds]
            mean = lambda c, k: sum(r[c][k] for r in res) / len(res)
            truth_best = max(cands, key=lambda c: mean(c, 0)); blind_pick = max(cands, key=lambda c: mean(c, 1))
            per_seed = [max(cands, key=lambda c: r[c][1]) for r in res]; tb = [max(cands, key=lambda c: r[c][0]) for r in res]
            regret = [max(r[c][0] for c in cands) - r[max(cands, key=lambda c: r[c][1])][0] for r in res]
            rows.append(dict(dwell=dw, noise=nz, truth={c: mean(c, 0) for c in cands}, blind={c: mean(c, 1) for c in cands}, truth_best=truth_best, blind_pick=blind_pick,
                             seeds_same_pick=sum(a == b for a, b in zip(per_seed, tb)), nseeds=len(res), mean_regret=sum(regret) / len(regret), max_regret=max(regret)))
    return rows


def main():
    for r in sweep():
        print("dwell %2d noise %.2f | truth accuracy %s | blind score %s" % (r["dwell"], r["noise"], " ".join("%s %.3f" % (c, v) for c, v in r["truth"].items()), " ".join("%s %.3f" % (c, v) for c, v in r["blind"].items())))
        print("    best by truth: %-12s blind pick: %-12s per-seed picks equal to best-by-truth: %d of %d; regret mean %.3f max %.3f" % (r["truth_best"], r["blind_pick"], r["seeds_same_pick"], r["nseeds"], r["mean_regret"], r["max_regret"]))


if __name__ == "__main__": main()
