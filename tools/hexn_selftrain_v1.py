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

NS = J.NS; NONE_BIN = J.NONE_BIN; HI = 4; EV_MIN = 4; AGE_CAP = 12
_pr = random.Random(12345); SUCC = [_pr.sample(range(J.K), J.K) for _ in range(NS)]   # per sensor, the class that usually follows each class (a fixed permutation)


def event(classes):
    """1 if at least EV_MIN sensors are in a class >= HI (no class counts as low)."""
    return 1 if sum(1 for c in classes if c >= HI) >= EV_MIN else 0


def score(W, bias, bins):
    s0 = sum(W[0][s][bins[s]] for s in range(len(bins))); s1 = sum(W[1][s][bins[s]] for s in range(len(bins)))
    return (1 if s1 + bias > s0 else 0), s0, s1


def clip(v, lo=-127, hi=127): return max(lo, min(hi, v))


def l2_next(det, minc=2):
    """a layer 2 stand-in that predicts: per sensor, from (current detected class, how many words it has lasted, capped) it learns online which class follows,
    and gives the predicted class for the NEXT word. No prediction yet (fewer than minc sightings) -> the current class. Learned only from the detected stream."""
    counts = [{} for _ in range(NS)]; age = [0] * NS; out = []
    for t in range(len(det)):
        row = []
        for s in range(NS):
            cur = det[t][s]; age[s] = age[s] + 1 if t and det[t - 1][s] == cur else 1
            ctr = counts[s].get((cur, min(age[s], AGE_CAP)))
            if cur >= 0 and ctr and sum(ctr.values()) >= minc: row.append(max(ctr.items(), key=lambda kv: (kv[1], -kv[0]))[0])
            else: row.append(cur)
        out.append(row)
        if t + 1 < len(det):                           # the transition into word t+1 becomes known only now, so it can only help later predictions
            for s in range(NS):
                cur, nxt = det[t][s], det[t + 1][s]
                if cur >= 0 and nxt >= 0:
                    k = (cur, min(age[s], AGE_CAP)); counts[s].setdefault(k, {}); counts[s][k][nxt] = counts[s][k].get(nxt, 0) + 1
    return out


def l2_inputs_of(det, mode):
    """judge input bins from the layer 2 prediction. 'replace': the predicted next class takes each sensor's slot (the judge keeps its 8 slots).
    'both': the current class AND the predicted next class (16 slots; the present scorer has 8, so this would be a new layout)."""
    pr = l2_next(det)
    return [J.bins_of(p) for p in pr] if mode == "replace" else [J.bins_of(c) + J.bins_of(p) for c, p in zip(det, pr)]


def stream(m, seed, nwords, noise, dwell, hold=0, l2_fill=False, seq=0.0, l2_pred=None):
    """-> (true classes[nwords][NS], detected classes[nwords][NS]); same templates (m), its own random stream."""
    rnd = random.Random(seed); cur = [0] * NS; left = [0] * NS; truth = []; samples = []
    for _ in range(nwords):
        row = []; yrow = []
        for s in range(NS):
            if dwell <= 1: y = rnd.randrange(J.K)
            else:
                if left[s] <= 0: cur[s] = SUCC[s][cur[s]] if (seq > 0 and rnd.random() < seq) else rnd.randrange(J.K); left[s] = rnd.randint(dwell, 2 * dwell)
                left[s] -= 1; y = cur[s]
            yrow.append(y); row.append((M.sample(rnd, m["tpl"][y], noise), y))
        truth.append(yrow); samples.append(row)
    flat = [x for row in samples for x in row]; got = [c for c, _ in M.classify(m, flat)]
    det = hold_det([got[i * NS:(i + 1) * NS] for i in range(nwords)], hold)
    inp = l2_inputs_of(det, l2_pred) if l2_pred else None
    return truth, (layer2(det, "fill") if l2_fill else det), inp


def hold_det(det, n):
    """the layer 1 hold counter, as a filter on a detected stream: a sensor's class is passed on only after the same class was seen n words in a row; otherwise 'no class' (-1). n <= 1 leaves the stream alone."""
    if n <= 1: return det
    out = []
    for t in range(len(det)):
        out.append([det[t][s] if t >= n - 1 and det[t][s] >= 0 and all(det[t - k][s] == det[t][s] for k in range(n)) else -1 for s in range(NS)])
    return out


def layer2(det, mode, minc=2):
    """a layer 2 stand-in (history per sensor, the next class predicted from the last, learned online from the detected stream only; no teacher).
    The verdict for a sensor's class at word t is 'ok' when it equals the predicted next class (a prediction needs at least minc earlier sightings of that transition).
    mode 'mask': keep the class only when the verdict is ok, else 'no class' (-1). Novel or contradicted classes become unknown.
    mode 'fill': keep the class when ok or when there is no prediction yet; when it contradicts the prediction (or is 'no class'), use the predicted class.
    This is a model of the idea, not the Tang store v5 (which keeps dense heaps and context lengths)."""
    counts = [{} for _ in range(NS)]; out = [[-1] * NS if mode == "mask" else list(det[0])]
    for t in range(1, len(det)):
        row = []
        for s in range(NS):
            prev, cur = det[t - 1][s], det[t][s]; pred = None
            if prev >= 0 and prev in counts[s]:
                best = max(counts[s][prev].items(), key=lambda kv: (kv[1], -kv[0]))
                if best[1] >= minc: pred = best[0]
            ok = pred is not None and cur == pred
            row.append((cur if ok else -1) if mode == "mask" else (cur if (ok or pred is None) else pred))
            if prev >= 0 and cur >= 0: counts[s].setdefault(prev, {}); counts[s][prev][cur] = counts[s][prev].get(cur, 0) + 1
        out.append(row)
    return out


def pairs(truth, det, inp=None):
    """(bins of detected word t, teacher label from true t+1, self label from detected t+1)"""
    return [((inp[t] if inp else J.bins_of(det[t])), event(truth[t + 1]), event(det[t + 1])) for t in range(len(truth) - 1)]


def confident(det_row):
    """is the self label certain? Sensors with no class are unknown: the label counts as certain only if it would be the same whether each unknown were high or low."""
    hi = sum(1 for c in det_row if c >= HI); unk = sum(1 for c in det_row if c < 0)
    return hi >= EV_MIN or hi + unk < EV_MIN


def zero(slots=NS): return [[[0] * 16 for _ in range(slots)] for _ in range(2)], 0


def perceptron(W, bias, data, epochs, step):
    """teacher training: data = [(bins, label)]; a wrong prediction moves the weights used toward the label."""
    rnd = random.Random(1)
    for _ in range(epochs):
        order = list(data); rnd.shuffle(order); wrong = 0
        for bins, y in order:
            p = score(W, bias, bins)[0]
            if p != y:
                wrong += 1; d = step if y == 1 else -step
                for s in range(len(bins)): W[1][s][bins[s]] = clip(W[1][s][bins[s]] + d); W[0][s][bins[s]] = clip(W[0][s][bins[s]] - d)
                bias = clip(bias - d, -300, 299)
        if wrong == 0: break
    return W, bias


def evaluate(W, bias, held, WA, biasA):
    n = len(held); acc = agree = 0
    for bins, y, _ in held:
        p = score(W, bias, bins)[0]; acc += (p == y); agree += (p == score(WA, biasA, bins)[0])
    return acc / n, agree / n


def drift(W, WA): return max(abs(W[c][s][b] - WA[c][s][b]) for c in range(2) for s in range(len(W[0])) for b in range(16))


def live_run(W, bias, WA, biasA, live, step, ceil, held, every, from_zero=False, conf=None, vote=1):
    """the self-feedback loop. Prediction for word t is made before word t+1 is seen; the self label then decides the update.
    vote > 1: every mismatch only adds one vote for each weight it concerns; a weight moves by STEP once it holds VOTE net votes the same way, so a stray wrong label is outvoted."""
    W = json.loads(json.dumps(W)); curve = []; hits = 0; acc = {}

    def nudge(c, s, b, sign):
        k = (c, s, b); acc[k] = acc.get(k, 0) + sign
        if abs(acc[k]) >= vote:
            v = clip(W[c][s][b] + step * (1 if acc[k] > 0 else -1)); acc[k] = 0
            if not from_zero: v = max(WA[c][s][b] - ceil, min(WA[c][s][b] + ceil, v))
            W[c][s][b] = v
    for i, (bins, _, ys) in enumerate(live):
        p = score(W, bias, bins)[0]; hits += (p == ys)
        if p != ys and step and (conf is None or conf[i]):
            d = 1 if ys == 1 else -1
            for s in range(len(bins)): nudge(1, s, bins[s], d); nudge(0, s, bins[s], -d)
            k = ("bias",); acc[k] = acc.get(k, 0) - d
            if abs(acc[k]) >= vote:
                bias = clip(bias + step * (1 if acc[k] > 0 else -1), -300, 299); acc[k] = 0
                if not from_zero: bias = max(biasA - ceil, min(biasA + ceil, bias))
        if (i + 1) % every == 0:
            a_, g_ = evaluate(W, bias, held, WA, biasA); curve.append((i + 1, a_, g_, drift(W, WA), hits / (i + 1)))
    return W, bias, curve


def experiment(seed=3, teacher_words=300, live_words=3000, held_words=600, teach_noise=(0.05, 0.10, 0.15), live_noise=0.20, dwell=6,
               t_step=8, epochs=20, step=1, ceil=24, every=500, from_zero=False, conf_filter=False, vote=1, hold=0, hold_labels=0, l2_inputs=False, l2_labels=False, seq=0.0, l2_pred=None):
    m = M.make(seed, J.K, J.NB, J.AW, 16, 0.15); data = []
    for i, nz in enumerate(teach_noise): data += [(b, yt) for b, yt, _ in pairs(*stream(m, seed * 1000 + i, teacher_words, nz, dwell, hold, l2_inputs, seq, l2_pred))]
    WA, biasA = perceptron(*zero(2 * NS if l2_pred == 'both' else NS), data, epochs, t_step)
    held = pairs(*stream(m, seed * 1000 + 50, held_words, live_noise, dwell, hold, l2_inputs, seq, l2_pred)); lt, ld, linp = stream(m, seed * 1000 + 60, live_words, live_noise, dwell, hold, False, seq, l2_pred); live = pairs(lt, layer2(ld, "fill") if l2_inputs else ld, linp)
    ldl = layer2(ld, "mask") if l2_labels else hold_det(ld, hold_labels)                 # hold_labels: the hold counter applied to the labels only; the judge's inputs stay unheld
    live = [(b, yt, event(ldl[t + 1])) for t, (b, yt, _) in enumerate(live)]
    conf = [confident(ldl[t + 1]) for t in range(len(ldl) - 1)] if conf_filter else None
    accA, _ = evaluate(WA, biasA, held, WA, biasA)
    out = {"A_accuracy": accA, "A_train_accuracy": evaluate(WA, biasA, [(b, y, 0) for b, y in data], WA, biasA)[0],
           "self_label_vs_truth": sum(1 for _, a, b in live if a == b) / len(live), "event_rate": sum(y for _, y, _ in held) / len(held)}
    WB, biasB, out["B"] = live_run(WA, biasA, WA, biasA, live, step, ceil, held, every, conf=conf, vote=vote)
    if from_zero:
        W0, b0 = zero(2 * NS if l2_pred == 'both' else NS); WC, biasC, out["C"] = live_run(W0, b0, WA, biasA, live, step, ceil, held, every, True, conf, vote)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=3); ap.add_argument("--live-words", type=int, default=3000); ap.add_argument("--live-noise", type=float, default=0.20)
    ap.add_argument("--dwell", type=int, default=6); ap.add_argument("--step", type=int, default=1); ap.add_argument("--ceil", type=int, default=24)
    ap.add_argument("--every", type=int, default=500); ap.add_argument("--from-zero", action="store_true"); ap.add_argument("--conf", action="store_true"); ap.add_argument("--vote", type=int, default=1); ap.add_argument("--hold", type=int, default=0); ap.add_argument("--hold-labels", type=int, default=0); ap.add_argument("--l2-inputs", action="store_true"); ap.add_argument("--seq", type=float, default=0.0); ap.add_argument("--l2-pred", choices=["replace", "both"]); ap.add_argument("--l2-labels", action="store_true")
    a = ap.parse_args()
    r = experiment(a.seed, live_words=a.live_words, live_noise=a.live_noise, dwell=a.dwell, step=a.step, ceil=a.ceil, every=a.every, from_zero=a.from_zero, conf_filter=a.conf, vote=a.vote, hold=a.hold, hold_labels=a.hold_labels, l2_inputs=a.l2_inputs, l2_labels=a.l2_labels, seq=a.seq, l2_pred=a.l2_pred)
    print("A (teacher only): held-out accuracy %.3f (training %.3f); event rate %.3f; self label right %.3f of the time" % (r["A_accuracy"], r["A_train_accuracy"], r["event_rate"], r["self_label_vs_truth"]))
    for name in ("B", "C"):
        if name in r:
            print(name, "(%s)" % ("teacher start, self feedback" if name == "B" else "from zero, self feedback only"))
            print("  words  accuracy  agree_with_A  max_drift_from_A  live_hit_rate_vs_self_label")
            for n, acc, agr, dr, hr in r[name]: print("  %5d  %.3f     %.3f         %3d               %.3f" % (n, acc, agr, dr, hr))


if __name__ == "__main__": main()
