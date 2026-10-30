"""Hex-N small detector with a DIRECT FEEDBACK INPUT, PYTHON MODEL ONLY (new file, 30 Oct 2026; no RTL, no card).
Alan, 30 Oct 21:56: the cell is the small counted detector plus a direct feedback input (the stage above says agree / disagree)
instead of the old feedback half. Question: does a one-bit feedback let the detector keep counting online and so (A) learn in use
from a tiny start, (B) follow slowly drifting patterns, (C) cope with a rise in noise, where the frozen detector cannot?
The detector is the counted detector of tools/hexn_ring_v1.py (same rules; imported). Online counting = the same counters (+K-1 own
class, -1 others, saturating +-31, weight +1/-1 when count >= T / <= -T), kept after training and updated per event.
The threshold follows two running means (own-class total, other-class total) with step 1/16 (a shift in hardware).
Arms with a trailing 'c' update the counters only and keep the trained threshold (added after the first run showed the threshold means drifting).
LOCAL arms (added after the counted-rule arms collapsed): 'loc' = on 'agree' only the winner's own counters move (lane on +1, lane off -1), nothing else; 'locneg' = as loc, and on 'disagree' the same step with the opposite sign; 'locT' = the same step on the TRUE class's detector (the upper bound for this rule).
CONTROLS: 'locnobit' = the local rule with NO feedback bit (always nudge the winner); 'locrand' = a fair coin instead of the bit.
Arms (prequential: each event is answered BEFORE it is used for an update):
  frozen    no updates after the first training
  self      no feedback: the cell trusts its own answer (when it gave one) as the label
  fb1       one-bit feedback: update with the answer as label only when the bit says 'agree'
  fb1neg    as fb1, and when the bit says 'disagree' the winner's counters are stepped down (-1) on its active lanes
  teacher   the true class is given (upper bound, a class number is far more than one bit)
The feedback bit is the truth with a flip probability --err (default 0.10), because a higher layer is not perfect."""
import argparse, importlib.util, os, random, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("ring", os.path.join(ROOT, "tools", "hexn_ring_v1.py")); R = importlib.util.module_from_spec(sp); sp.loader.exec_module(R)
R.AW = 7; CAP = R.CAP; STEP = 16


class Online:
    def __init__(self, X, y, K, S):
        self.K = K; self.nb = len(X[0]); self.T = max(1, min(R.TMAX, round(0.5 * S))); self.cap = (1 << R.AW) - 1
        self.cnt = [[0] * self.nb for _ in range(K)]
        for x, c in zip(X, y): self.step(x, c)
        self.w = self.weights(); self.mp = []; self.mn = []
        for k in range(K):
            pos = [R.tot(self.w[k], x, self.cap) for x, c in zip(X, y) if c == k]; neg = [R.tot(self.w[k], x, self.cap) for x, c in zip(X, y) if c != k]
            self.mp.append(sum(pos) / len(pos)); self.mn.append(sum(neg) / len(neg))
        self.mk_thr()
    def step(self, x, label):
        for k in range(self.K):
            d = (self.K - 1) if k == label else -1
            for j in range(self.nb):
                if x[j]: self.cnt[k][j] = max(-CAP, min(CAP, self.cnt[k][j] + d))
    def weights(self): return [[(1 if v >= self.T else -1 if v <= -self.T else 0) for v in row] for row in self.cnt]
    def mk_thr(self): self.thr = [max(0, min(self.cap, round((self.mp[k] + self.mn[k]) / 2))) for k in range(self.K)]
    def answer(self, x):
        self.tt = [R.tot(self.w[k], x, self.cap) for k in range(self.K)]
        return R.answer([R.burst(self.tt[k], self.thr[k]) for k in range(self.K)])
    def learn(self, x, label, thr=True):
        if thr:
            for k in range(self.K):
                if k == label: self.mp[k] += (self.tt[k] - self.mp[k]) / STEP
                else: self.mn[k] += (self.tt[k] - self.mn[k]) / STEP
        self.step(x, label); self.w = self.weights()
        if thr: self.mk_thr()
    def nudge(self, x, k, sgn=1):
        # LOCAL rule: only detector k's counters move: lanes that are on +1, lanes that are off -1 (times sgn); other detectors and the threshold are untouched
        for j in range(self.nb): self.cnt[k][j] = max(-CAP, min(CAP, self.cnt[k][j] + (sgn if x[j] else -sgn)))
        self.w = self.weights()
    def push_down(self, x, k):
        for j in range(self.nb):
            if x[j]: self.cnt[k][j] = max(-CAP, self.cnt[k][j] - 1)
        self.w = self.weights()


def run(seed, scen, arm, K=8, nb=18, q=0.15, S=16, N=3000, err=0.10, win=500):
    rnd = random.Random(seed); tpl = R.templates(rnd, K, nb, 4)
    tr = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(S)]; random.Random(seed + 5).shuffle(tr)
    m = Online([x for x, _ in tr], [c for _, c in tr], K, S); good = [0] * (N // win); sr = random.Random(seed + 99)
    for i in range(N):
        qq = q
        if scen == "C" and i >= N // 2: qq = 0.25
        if scen == "B" and i > 0 and i % 500 == 0:
            for c in range(K): tpl[c][sr.randrange(nb)] ^= 1
        y = sr.randrange(K); x = R.sample(sr, tpl[y], qq); a = m.answer(x); good[i // win] += (a == y)
        if arm == "frozen": continue
        if arm == "locT": m.nudge(x, y); continue
        if arm == "locnobit":   # CONTROL: no feedback at all, the winner is always nudged toward the input
            if a >= 0: m.nudge(x, a)
            continue
        if arm == "locrand":    # CONTROL: a fair coin in place of the feedback bit
            if a >= 0 and sr.random() < 0.5: m.nudge(x, a)
            continue
        if arm in ("loc", "locneg"):
            if a < 0: continue
            if (a == y) ^ (sr.random() < err): m.nudge(x, a)
            elif arm == "locneg": m.nudge(x, a, -1)
            continue
        th = not arm.endswith("c"); base = arm[:-1] if arm.endswith("c") else arm   # 'c' = counters only, the threshold stays as trained
        if base == "teacher": m.learn(x, y, th); continue
        if a < 0: continue
        bit = (a == y) ^ (sr.random() < err)
        if base == "self": m.learn(x, a, th)
        elif bit: m.learn(x, a, th)
        elif base == "fb1neg": m.push_down(x, a)
    return [g / win for g in good]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); ap.add_argument("--err", type=float, default=0.10); a = ap.parse_args()
    arms = ("frozen", "teacher", "locT", "loc", "locneg", "locnobit", "locrand")
    for scen, desc, S in (("A", "LEARN IN USE: trained on 2 samples per class only, then a steady stream", 2), ("A16", "reference: trained on 16 per class, steady stream", 16),
                          ("B", "DRIFT: trained on 16 per class; every 500 events one wire of every class pattern flips for good", 16), ("C", "NOISE RISE: trained on 16 per class at noise 0.15; noise 0.25 from event 1,500", 16)):
        print(f"\n{desc}  (K=8, 18 wires, {a.seeds} seeds, feedback bit wrong {a.err:.0%} of the time); accuracy per 500 events")
        for arm in arms:
            rs = [run(s, scen[0], arm, S=S, err=a.err) for s in range(a.seeds)]
            print(f"  {arm:8s} " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(rs[0]))), flush=True)
