"""hexn_selftrain_v1: host-side simulation of the teacher-versus-self experiment (direction doc section 12, 7 Nov 2026). Simulation only; nothing here runs on the card.

The judge is the batch judge's arithmetic: pred = 1 if s1 + bias > s0, with s_c = sum over the eight sensors of W[c][sensor][class bin]
(bit-exact with tools/hexn_scorer_ref_v1.py; checked in tests/vm/test_hexn_selftrain_v1.py).

The task (an assumption of this tool, not a ruling): the judge sees the detector's classes for word t and must predict an EVENT in word t+1,
event = at least EV_MIN of the eight sensors are in a class >= HI. Persistence (dwell > 1) is what makes the next word predictable.
  Teacher label of word t : the event computed from the TRUE classes of word t+1 (the teaching system knows the answers).
  Self label of word t    : the event computed from the DETECTED classes of word t+1 (what the system itself observes). It is wrong whenever the detector is.

Judges:
  A  teacher only: perceptron on teacher data (several noise settings). Never changed afterwards. The yardstick.
  B  starts as a copy of A, then runs on a live stream and changes ONLY from its own feedback: after word t+1 arrives, if its prediction for t
     disagrees with the self label, it moves the weights it used by STEP (clipped to int8), and never further than CEIL from A's value.
  C  (control, --from-zero) starts from all zeros and learns from self labels only: can the system get there with no teacher at all?
Held-out words (fresh stream, TRUE labels) score every judge at each checkpoint: accuracy against the known answer, agreement with A.
"""
import argparse, json, random, sys
import hexn_bank_model_v2 as M
import hexn_kxlayer1_judge_v1 as J

NS = J.NS; NONE_BIN = J.NONE_BIN; HI = 4; EV_MIN = 4


def event(classes):
    """1 if at least EV_MIN sensors are in a class >= HI (no class counts as low)."""
    return 1 if sum(1 for c in classes if c >= HI) >= EV_MIN else 0


def score(W, bias, bins):
    s0 = sum(W[0][s][bins[s]] for s in range(NS)); s1 = sum(W[1][s][bins[s]] for s in range(NS))
    return (1 if s1 + bias > s0 else 0), s0, s1


def clip(v, lo=-127, hi=127): return max(lo, min(hi, v))


def stream(m, seed, nwords, noise, dwell):
    """-> (true classes[nwords][NS], detected classes[nwords][NS]); same templates (m), its own random stream."""
    rnd = random.Random(seed); cur = [0] * NS; left = [0] * NS; truth = []; samples = []
    for _ in range(nwords):
        row = []; yrow = []
        for s in range(NS):
            if dwell <= 1: y = rnd.randrange(J.K)
            else:
                if left[s] <= 0: cur[s] = rnd.randrange(J.K); left[s] = rnd.randint(dwell, 2 * dwell)
                left[s] -= 1; y = cur[s]
            yrow.append(y); row.append((M.sample(rnd, m["tpl"][y], noise), y))
        truth.append(yrow); samples.append(row)
    flat = [x for row in samples for x in row]; got = [c for c, _ in M.classify(m, flat)]
    det = [got[i * NS:(i + 1) * NS] for i in range(nwords)]
    return truth, det


def pairs(truth, det):
    """(bins of detected word t, teacher label from true t+1, self label from detected t+1)"""
    return [(J.bins_of(det[t]), event(truth[t + 1]), event(det[t + 1])) for t in range(len(truth) - 1)]


def zero(): return [[[0] * 16 for _ in range(NS)] for _ in range(2)], 0


def perceptron(W, bias, data, epochs, step):
    """teacher training: data = [(bins, label)]; a wrong prediction moves the weights used toward the label."""
    rnd = random.Random(1)
    for _ in range(epochs):
        order = list(data); rnd.shuffle(order); wrong = 0
        for bins, y in order:
            p = score(W, bias, bins)[0]
            if p != y:
                wrong += 1; d = step if y == 1 else -step
                for s in range(NS): W[1][s][bins[s]] = clip(W[1][s][bins[s]] + d); W[0][s][bins[s]] = clip(W[0][s][bins[s]] - d)
                bias = clip(bias - d, -300, 299)
        if wrong == 0: break
    return W, bias


def evaluate(W, bias, held, WA, biasA):
    n = len(held); acc = agree = 0
    for bins, y, _ in held:
        p = score(W, bias, bins)[0]; acc += (p == y); agree += (p == score(WA, biasA, bins)[0])
    return acc / n, agree / n


def drift(W, WA): return max(abs(W[c][s][b] - WA[c][s][b]) for c in range(2) for s in range(NS) for b in range(16))


def live_run(W, bias, WA, biasA, live, step, ceil, held, every, from_zero=False):
    """the self-feedback loop. Prediction for word t is made before word t+1 is seen; the self label then decides the update."""
    W = json.loads(json.dumps(W)); curve = []; hits = 0
    for i, (bins, _, ys) in enumerate(live):
        p = score(W, bias, bins)[0]; hits += (p == ys)
        if p != ys and step:
            d = step if ys == 1 else -step
            for s in range(NS):
                for c, dd in ((1, d), (0, -d)):
                    v = clip(W[c][s][bins[s]] + dd)
                    if not from_zero: v = max(WA[c][s][bins[s]] - ceil, min(WA[c][s][bins[s]] + ceil, v))
                    W[c][s][bins[s]] = v
            bias = clip(bias - d, -300, 299)
            if not from_zero: bias = max(biasA - ceil, min(biasA + ceil, bias))
        if (i + 1) % every == 0:
            acc, agr = evaluate(W, bias, held, WA, biasA); curve.append((i + 1, acc, agr, drift(W, WA), hits / (i + 1)))
    return W, bias, curve


def experiment(seed=3, teacher_words=300, live_words=3000, held_words=600, teach_noise=(0.05, 0.10, 0.15), live_noise=0.20, dwell=6,
               t_step=8, epochs=20, step=1, ceil=24, every=500, from_zero=False):
    m = M.make(seed, J.K, J.NB, J.AW, 16, 0.15); data = []
    for i, nz in enumerate(teach_noise): data += [(b, yt) for b, yt, _ in pairs(*stream(m, seed * 1000 + i, teacher_words, nz, dwell))]
    WA, biasA = perceptron(*zero(), data, epochs, t_step)
    held = pairs(*stream(m, seed * 1000 + 50, held_words, live_noise, dwell)); live = pairs(*stream(m, seed * 1000 + 60, live_words, live_noise, dwell))
    accA, _ = evaluate(WA, biasA, held, WA, biasA)
    out = {"A_accuracy": accA, "A_train_accuracy": evaluate(WA, biasA, [(b, y, 0) for b, y in data], WA, biasA)[0],
           "self_label_vs_truth": sum(1 for _, a, b in live if a == b) / len(live), "event_rate": sum(y for _, y, _ in held) / len(held)}
    WB, biasB, out["B"] = live_run(WA, biasA, WA, biasA, live, step, ceil, held, every)
    if from_zero:
        W0, b0 = zero(); WC, biasC, out["C"] = live_run(W0, b0, WA, biasA, live, step, ceil, held, every, True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=3); ap.add_argument("--live-words", type=int, default=3000); ap.add_argument("--live-noise", type=float, default=0.20)
    ap.add_argument("--dwell", type=int, default=6); ap.add_argument("--step", type=int, default=1); ap.add_argument("--ceil", type=int, default=24)
    ap.add_argument("--every", type=int, default=500); ap.add_argument("--from-zero", action="store_true")
    a = ap.parse_args()
    r = experiment(a.seed, live_words=a.live_words, live_noise=a.live_noise, dwell=a.dwell, step=a.step, ceil=a.ceil, every=a.every, from_zero=a.from_zero)
    print("A (teacher only): held-out accuracy %.3f (training %.3f); event rate %.3f; self label right %.3f of the time" % (r["A_accuracy"], r["A_train_accuracy"], r["event_rate"], r["self_label_vs_truth"]))
    for name in ("B", "C"):
        if name in r:
            print(name, "(%s)" % ("teacher start, self feedback" if name == "B" else "from zero, self feedback only"))
            print("  words  accuracy  agree_with_A  max_drift_from_A  live_hit_rate_vs_self_label")
            for n, acc, agr, dr, hr in r[name]: print("  %5d  %.3f     %.3f         %3d               %.3f" % (n, acc, agr, dr, hr))


if __name__ == "__main__": main()
