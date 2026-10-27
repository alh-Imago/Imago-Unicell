"""hexn_anomaly_v1: SELF-CHECK / ANOMALY STORE for layer 2 (Alan, 27 Oct 2026: with known sequences, a last event that breaks the prediction is logged and stored as a new sequence / anomaly). Python only; no RTL; new file; uses hexn_layer2_v2 (the real routine recordings) and hexn_layer2_v1.Table unchanged.
Rule: after each event, the longest known context (the last 3, else 2, else 1 events) has a set of successors seen in training. The NEXT event is CONFIRMED if it is in that set; it is an ANOMALY if the context is known but the event is not in the set ('contradiction'), or if not even the last event was ever seen ('novel'). An anomaly is stored as a candidate sequence (its context plus the event); a candidate seen twice is promoted to a known sequence (the same two-confirmation idea as the sequence-prediction rules).
Tests: (1) real: train on runs 1 and 2, run 3 online (it holds the real extra key 4) and each run left out in turn; (2) injected faults in the left-out run: one goal key swapped (7 for 8 or 8 for 7) or one extra random digit key inserted, 300 per run and context length, to show what a context of 1, 2 or 3 events can catch.
Limits: the routine order is random, so the first key of a routine can legitimately follow any routine end; the check works inside routines; two training runs; faults are injected, not measured; no hardware.
Usage: python3 tools/hexn_anomaly_v1.py"""
import sys, os, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer2_v2 as V
def build(seqs, k):
    t = [collections.defaultdict(collections.Counter) for _ in range(k + 1)]
    for seq in seqs:
        for i in range(1, len(seq)):
            for j in range(1, k + 1):
                if i >= j: t[j][tuple(seq[i - j:i])][seq[i]] += 1
    return t
def verdict(t, k, hist, x):
    for j in range(k, 0, -1):
        if len(hist) >= j and tuple(hist[-j:]) in t[j]: return "ok" if x in t[j][tuple(hist[-j:])] else "contradiction"
    return "novel"
def flags(t, k, seq): return [(i, verdict(t, k, seq[:i], seq[i])) for i in range(1, len(seq)) if verdict(t, k, seq[:i], seq[i]) != "ok"]
def main():
    V.R = V.runs(); runs = [[key for key, _ in r] for r in V.R]; nm = lambda c: {12: "1", 13: "2", 14: "3", 15: "4", 16: "5", 17: "6", 18: "7", 19: "8"}.get(c, str(c))
    print("REAL RUNS (leave one run out; flags per run, event numbers are positions in the pressed sequence, from 1)")
    for k in (1, 2, 3):
        row = []
        for test in range(3):
            t = build([runs[j] for j in range(3) if j != test], k); row.append(flags(t, k, runs[test]))
        print("context %d: " % k + "; ".join("run %d: %s" % (r + 1, [(i + 1, nm(runs[r][i]), v) for i, v in row[r]] or "none") for r in range(3)))
    print("\nINJECTED FAULTS in the left-out run (300 per run, mean over the three runs): share flagged (a fault is detected if some flag lies at the fault event or the next event)")
    print("fault \\ context  |    1    |    2    |    3")
    rnd = random.Random(7)
    for fault in ("goal key swapped (7<->8)", "extra random digit inserted"):
        out = []
        for k in (1, 2, 3):
            hit = tot = 0
            for test in range(3):
                t = build([runs[j] for j in range(3) if j != test], k); base = set(i for i, _ in flags(t, k, runs[test]))
                for _ in range(300):
                    s = list(runs[test])
                    if fault.startswith("goal"):
                        pos = rnd.choice([i for i, c in enumerate(s) if c in V.GOALS]); s[pos] = 37 - s[pos]
                    else:
                        pos = rnd.randrange(1, len(s)); s.insert(pos, rnd.choice([12, 13, 14, 15, 16, 17, 18, 19]))
                    new = set(i for i, _ in flags(t, k, s)) - base; tot += 1; hit += any(i in (pos, pos + 1) for i in new)
            out.append(hit / tot)
        print("%-27s | %.3f | %.3f | %.3f" % ((fault,) + tuple(out)))
    print("\nONLINE STORE on run 3 (trained on runs 1 and 2, context 3): anomalies are stored as candidates, promoted when seen twice")
    t = build([runs[0], runs[1]], 3); cand = collections.Counter(); promoted = []; seq = runs[2]
    for i in range(1, len(seq)):
        v = verdict(t, 3, seq[:i], seq[i])
        if v != "ok":
            key = tuple(seq[max(0, i - 3):i + 1]); cand[key] += 1; print("  event %d (%s) after %s: %s -> stored candidate %s (count %d)" % (i + 1, nm(seq[i]), [nm(c) for c in seq[max(0, i - 3):i]], v, [nm(c) for c in key], cand[key]))
            if cand[key] == 2: promoted.append(key)
        for j in range(1, 4):
            if i >= j: t[j][tuple(seq[i - j:i])][seq[i]] += 1
    print("  promoted to known sequences: %s" % (promoted or "none (each anomaly occurred once)"))
if __name__ == "__main__": main()
