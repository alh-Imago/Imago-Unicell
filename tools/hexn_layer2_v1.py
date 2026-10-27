"""hexn_layer2_v1: LAYER 2 FIRST MODEL ON THE REAL RECORDINGS (Python only; no RTL; new file; reuses hexn_ir_decode_v1, hexn_layer1_v1, hexn_exact_v1, hexn_hold_v1 (which captures the replay outputs of hexn_replay_v1) unchanged).
What layer 2 sees: the EVENT stream = the stable class each time the hold output changes (what hexn_hold_v1 / hexn_hist_v1 hand over). What it learns here: NEXT EVENT given the last k events (a table keyed on the last k classes, backing off to shorter keys; 'unknown' when no key has been seen). This is the 'what is likely next' (inference) read of the history store; the goal/reward path learning of hexn_path_v1 needs a goal teacher, which the recordings do not have.
Streams:
  IR remote (21 keys pressed in order, then 13 again; presses decoded from the real recording): trained on round 1 (21 events), tested on round 2 (13). Run clean, and with frames damaged (probability p of ONE flipped bit per frame; every press has 1 + repeats frames) through the exact-match bank (direct wiring) and either NO hold or the hold (n = 2, ignore unknown): events, precision/recall against the true presses and next-key accuracy, 300 seeds. Training and testing both use the damaged stream (worst case: no clean training).
  Pot sweep (4 bands, real recording, trained pot bank, hold n = 20): events and next-band accuracy for k = 1 and k = 2, trained on the first half of the events and tested on the second.
  Thermistor (3 bands, finger run, hold n = 20): only the event count and dwell are shown: too few events to learn from.
Limits: the key order in round 1 defined the table's key numbers, round 2 was physically pressed in the same order (verified: the decoded codes of round 2 equal those of round 1 key for key), so the IR sequence is a trivial cycle: it tests the chain (frames -> exact bank -> hold -> history -> prediction), not the difficulty of learning. The pot sweep has ONE learnable structure (direction reversal). No goal or reward. Very small data.
Usage: python3 tools/hexn_layer2_v1.py"""
import sys, os, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_ir_decode_v1 as IR, hexn_layer1_v1 as L, hexn_exact_v1 as X, hexn_tang_script_v1 as S1, hexn_hold_v1 as H
NONE = 15
def hold_events(xs, n, skip):
    """stable-class changes of the hold rule; the first sample is an event (the first state)"""
    cur = None; cand = None; cnt = 0; ev = []
    for i, x in enumerate(xs):
        if cur is None: cur = x; ev.append((i, x))
        elif skip and x == NONE: pass
        elif x == cur: cand = None; cnt = 0
        else:
            cnt = cnt + 1 if cand == x else 1; cand = x
            if cnt >= max(n, 1): cur = x; cand = None; cnt = 0; ev.append((i, x))
    return ev
def raw_events(xs):
    ev = []
    for i, x in enumerate(xs):
        if not ev or ev[-1][1] != x: ev.append((i, x))
    return ev
class Table:
    def __init__(self, k): self.k = k; self.t = [collections.defaultdict(collections.Counter) for _ in range(k + 1)]
    def learn(self, seq):
        for i in range(1, len(seq)):
            for j in range(0, self.k + 1):
                if i >= j: self.t[j][tuple(seq[i - j:i])][seq[i]] += 1
    def predict(self, hist):
        for j in range(self.k, -1, -1):
            if len(hist) >= j and tuple(hist[len(hist) - j:]) in self.t[j] and j > 0: return self.t[j][tuple(hist[len(hist) - j:])].most_common(1)[0][0]
        return None
    def score(self, seq):
        right = unk = 0; n = 0
        for i in range(1, len(seq)):
            p = self.predict(seq[:i]); n += 1
            if p is None: unk += 1
            elif p == seq[i]: right += 1
        return right, unk, n
def ir_presses():
    ps = IR.presses(IR.decode(IR.load(os.path.join(L.DATA, "esp_run_20261027_ir_all_keys_edges.csv"))))
    return [(X.TABLE.index(q["bytes"][2]), 1 + q["repeats"]) for q in ps if q["kind"] == "data" and q["bytes"][2] in X.TABLE]
def ir_stream(presses, p, r, m):
    xs = []; marks = []
    for key, nf in presses:
        marks.append(len(xs))
        for _ in range(nf):
            c = X.TABLE[key]
            if r.random() < p: c ^= 1 << r.randrange(8)
            k, g = S1.classify(m, X.bits(c)); xs.append(k if k >= 0 and max(g) > 0 else NONE)
    return xs, marks
def ir_run(p, use_hold, seeds=300):
    m = X.model("direct0"); ps = ir_presses(); r1 = ps[:21]; r2 = ps[21:]; acc = []; prec = []; rec = []; unk = []
    for s in range(seeds):
        r = random.Random(s); a, _ = ir_stream(r1, p, r, m); b, mb = ir_stream(r2, p, r, m)
        ea = hold_events(a, 2, 1) if use_hold else raw_events(a); eb = hold_events(b, 2, 1) if use_hold else raw_events(b)
        sa = [c for _, c in ea]; sb = [c for _, c in eb]; t = Table(2); t.learn(sa); right, u, n = t.score(sb)
        truth = [k for k, _ in r2]; ok = sum(1 for c in sb if c in truth)
        got = set()
        for idx, c in eb:
            for q, mk in enumerate(mb):
                if mk <= idx < (mb[q + 1] if q + 1 < len(mb) else 10**9) and r2[q][0] == c: got.add(q)
        acc.append(right / n); unk.append(u / n); prec.append(sum(1 for idx, c in eb if any(mk <= idx < (mb[q + 1] if q + 1 < len(mb) else 10**9) and r2[q][0] == c for q, mk in enumerate(mb))) / max(1, len(eb))); rec.append(len(got) / len(r2))
    mean = lambda v: sum(v) / len(v)
    return mean(acc), mean(unk), mean(prec), mean(rec)
def main():
    ps = ir_presses(); print("IR remote: %d decoded presses (round 1: %d, round 2: %d); round 2 key order equals round 1's: %s\n" % (len(ps), 21, len(ps) - 21, [k for k, _ in ps[21:]] == [k for k, _ in ps[:len(ps) - 21]]))
    print("p (frames damaged) | layer 1 -> layer 2 events          | event precision | true presses seen | next-key right | next-key 'unknown'")
    for p in (0.0, 0.05, 0.15, 0.30):
        for uh in (False, True):
            a, u, pr, rc = ir_run(p, uh); print("%.2f               | %-34s | %.3f           | %.3f             | %.3f          | %.3f" % (p, "exact bank + hold(2, skip)" if uh else "exact bank, no hold", pr, rc, a, u))
    H.R.light(); H.R.pot(); H.R.therm(); cap = {n: o for n, o, _, _ in H.CAP}
    pot = [NONE if x == -1 else x for x in cap["pot"]]; ev = hold_events(pot, 20, 1); seq = [c for _, c in ev]; half = len(seq) // 2
    print("\nPot sweep: %d events %s" % (len(seq), seq))
    for k in (1, 2):
        t = Table(k); t.learn(seq[:half]); right, u, n = t.score(seq[half - k:]) if half > k else (0, 0, 1); print("  k=%d (trained on first %d events, tested on the rest): right %d of %d, unknown %d" % (k, half, right, n, u))
    th = [NONE if x == -1 else x for x in cap["therm raw"]]; ev = hold_events(th, 20, 1)
    print("\nThermistor (finger run, raw bank + hold 20): %d events %s at samples %s; dwell between events (samples) %s: too few events to learn from" % (len(ev), [c for _, c in ev], [i for i, _ in ev], [b[0] - a[0] for a, b in zip(ev, ev[1:])]))
if __name__ == "__main__": main()
