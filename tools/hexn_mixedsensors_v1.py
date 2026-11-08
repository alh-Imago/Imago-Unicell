"""hexn_mixedsensors_v1 (8 Nov 2026; Alan 16:57: process that side first). Simulation, host side.
A MIXED set of eight sensors for the judge: sensors 0 to 3 are GAP sensors (the detector's raw answers, with 'no class' gaps and some wrong classes: carry-forward is the right fix) and sensors 4 to 7 are CHATTER sensors (never 'no class'; around every real class change the answer flips back and forth between the old and the new class for +-8 steps, plus 1 percent single-step wrong classes: a hold is the right fix, as with the real thermistor). Classes last 100 to 200 steps, so a hold of 10 is safe for the run-length guard.
Strategies, each gives one cleaner per sensor; the judge weights are then taught (known answers) with those cleaners in front, and the judge is scored on unseen words against the event in the TRUE classes of the next word:
  none          no cleaner anywhere
  carry3        carry3 on every sensor
  hold10        hold10 on every sensor
  oracle        per sensor, the cleaner with the best single-sensor accuracy against the true classes (uses answers; the best possible per-sensor pick)
  blind cost    per sensor, from its raw stream alone: the cost c = 10 (hexn_trychatter_v1) among the cleaners the run-length guard allows (no labels, no judge)
  blind judge   per sensor in turn, the others held at their current pick: every cleaner is tried with its own taught weights and scored by agreement with a self label read from the RAW classes of the next word (certain words only; hexn_trycleaners_v1); one pass from all-none
Task and weights as in hexn_selftrain_v1 (event = at least 4 of 8 sensors in class >= 4 in the next word).
Usage: python3 tools/hexn_mixedsensors_v1.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_selftrain_v1 as S, hexn_sensor_profiles_v1 as P, hexn_trychatter_v1 as T, hexn_bank_model_v2 as M, hexn_kxlayer1_judge_v1 as J

CANDS = ("none", "carry3", "hold3", "hold10", "carry3+hold10")
GAP, CHATTER = (0, 1, 2, 3), (4, 5, 6, 7)


def chatter_col(truth_col, rnd, w=8, flip=0.01):
    out = list(truth_col)
    for i in range(1, len(truth_col)):
        if truth_col[i] != truth_col[i - 1]:
            for j in range(max(0, i - w), min(len(truth_col), i + w + 1)): out[j] = rnd.choice((truth_col[i - 1], truth_col[i]))
    for i in range(len(out)):
        if rnd.random() < flip: out[i] = rnd.randrange(J.K)
    return out


def mixed_stream(m, seed, nwords, noise, dwell=100):
    truth, det, _ = S.stream(m, seed, nwords, noise, dwell); rnd = random.Random(seed + 9)
    cols = [[r[s] for r in det] for s in range(S.NS)]
    for s in CHATTER: cols[s] = chatter_col([r[s] for r in truth], rnd)
    return truth, [[cols[s][t] for s in range(S.NS)] for t in range(nwords)]


def train(streams, specs):
    data = []
    for tr, dt in streams: data += [(b, y) for b, y, _ in S.pairs(tr, P.clean_columns(dt, specs))]
    return S.perceptron(*S.zero(), data, 20, 8)


def judge_acc(W, bias, truth, det, specs):
    live = S.pairs(truth, P.clean_columns(det, specs)); return sum(S.score(W, bias, b)[0] == y for b, y, _ in live) / len(live)


def col_acc(cl, tcol): return sum(a == b for a, b in zip(cl, tcol)) / len(cl)


def run(seed, noise, nwords=2500, tw=400, teach_noise=(0.05, 0.10, 0.15)):
    m = M.make(seed, J.K, J.NB, J.AW, 16, 0.15)
    ts = [mixed_stream(m, seed * 1000 + i, tw, nz) for i, nz in enumerate(teach_noise)]
    truth, det = mixed_stream(m, seed * 1000 + 60, nwords, noise); cols = [[r[s] for r in det] for s in range(S.NS)]; tcols = [[r[s] for r in truth] for s in range(S.NS)]
    picks = {"none": ["none"] * 8, "carry3": ["carry3"] * 8, "hold10": ["hold10"] * 8}
    picks["oracle"] = [max(CANDS, key=lambda c: col_acc(P.clean_chain(cols[s], c), tcols[s])) for s in range(8)]
    picks["blind cost"] = [min([c for c in CANDS if T.allowed(cols[s], c)], key=lambda c: T.cost(P.clean_chain(cols[s], c), cols[s], 10)) for s in range(8)]
    ys = [S.event(det[t + 1]) for t in range(nwords - 1)]; conf = [S.confident(det[t + 1]) for t in range(nwords - 1)]; cur = ["none"] * 8
    for s in range(8):
        best = None
        for c in CANDS:
            sp = list(cur); sp[s] = c; W, bias = train(ts, sp); live = S.pairs(truth, P.clean_columns(det, sp))
            idx = [i for i in range(len(live)) if conf[i]]; sc = sum(S.score(W, bias, live[i][0])[0] == ys[i] for i in idx) / max(1, len(idx))
            if best is None or sc > best[0]: best = (sc, c)
        cur[s] = best[1]
    picks["blind judge"] = cur
    res = {}
    for name, sp in picks.items():
        W, bias = train(ts, sp); res[name] = judge_acc(W, bias, truth, det, sp)
    return res, picks


def main():
    for nz in (0.10, 0.20):
        allr = []; allp = []
        for sd in range(1, 7): r, p = run(sd, nz); allr.append(r); allp.append(p)
        print("\nnoise %.2f, judge accuracy on unseen words, mean of 6 seeds (min / max):" % nz)
        for name in allr[0]: v = [r[name] for r in allr]; print("  %-12s %.3f  (%.3f / %.3f)" % (name, sum(v) / 6, min(v), max(v)))
        for name in ("oracle", "blind cost", "blind judge"):
            g = sum(1 for p in allp for s in GAP if "carry" in p[name][s] and "hold" not in p[name][s]); h = sum(1 for p in allp for s in CHATTER if "hold" in p[name][s])
            print("  %-12s picks: gap sensors given carry3 only in %d of 24, chatter sensors given a hold in %d of 24" % (name, g, h))


if __name__ == "__main__": main()
