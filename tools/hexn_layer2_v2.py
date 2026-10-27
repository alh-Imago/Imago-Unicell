"""hexn_layer2_v2: LAYER 2 ON THE REAL ROUTINE RECORDINGS (27 Oct, runs 1 to 3 of docs/hex-n/sessions/ROUTINES_RUN_SHEET_v1.md). Python only; no RTL; new file; reuses hexn_layer2_v1 (Table, hold_events, raw_events, ir_stream), hexn_exact_v1 (exact-match bank), hexn_session_check_v1 (press decoding) unchanged.
Data: what was ACTUALLY pressed (decoded from the IR edges files): run 1 = 14 routines (56 presses), run 2 = 14 routines (56), run 3 = 16 routines plus one extra key 4 (65). Runs 1 and 2 are two routines short of the plan (see the checker output); the pressed sequences are used as they are, because every pressed block is a complete routine.
Task: predict the NEXT event from the last k events (k = 1..4, table with back-off to shorter keys, 'unknown' if unseen). Two scores: all events, and GOAL events only (the event is key 7 or 8, the end of a routine; after the keys 2 3 or 5 6 the goal depends on the first key of the routine, 3 events back, so k = 3 is needed). Leave one run out: train on two runs (each learned on its own, no transition across runs), test on the third, mean of the three.
Conditions: (clean) the pressed keys are the events; (damaged) every press has its REAL number of frames (1 + repeats from the recording, mostly 2), each frame damaged by one flipped bit with probability p, through the exact-match bank, then (a) no hold, (b) hold n = 1 ignoring unknown, (c) hold n = 2 ignoring unknown; 200 seeds.
Limits: training on 2 runs of about 14 routines each is small; the routines were built so that a short window cannot decide the goal, so the k = 1..2 ceilings are known (about 50 percent on goal events); damage is simulated; the extra key in run 3 is real noise and is left in; goal events are found from the observed class (7 or 8), so a damaged stream is scored against what it observed, not against the plan.
Usage: python3 tools/hexn_layer2_v2.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer2_v1 as L2, hexn_session_check_v1 as C, hexn_exact_v1 as X
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "data")
GOALS = (18, 19)   # table index of keys 7 and 8
def runs():
    out = []
    for r in (1, 2, 3):
        ps, _ = C.presses_of(os.path.join(D, "esp_run_20261027_ir_routines_run%d_edges.csv" % r)); out.append([(k, 1 + rp) for k, _, rp in ps])
    return out
def score(table, seq):
    right = unk = n = gr = gu = gn = 0
    for i in range(1, len(seq)):
        p = table.predict(seq[:i]); g = seq[i] in GOALS; n += 1; gn += g
        if p is None: unk += 1; gu += g
        elif p == seq[i]: right += 1; gr += g
    return right, unk, n, gr, gu, gn
def evaluate(events_of, k, seeds):
    tot = [0] * 6
    for s in range(seeds):
        r = random.Random(s); evs = [events_of(rr, r) for rr in R]
        for test in range(3):
            t = L2.Table(k)
            for j in range(3):
                if j != test: t.learn(evs[j])
            for a, b in enumerate(score(t, evs[test])): tot[a] += b
    return tot
def main():
    global R; R = runs()
    import collections; print("pressed keys per run: %s; frames per press (frames: presses) per run: %s\n" % ([len(x) for x in R], [dict(sorted(collections.Counter(f for _, f in x).items())) for x in R]))
    clean = lambda rr, r: [k for k, _ in rr]
    print("CLEAN pressed keys (leave one run out)")
    print("k | next event right (all) | unknown | next GOAL event right | unknown")
    for k in (1, 2, 3, 4):
        a, u, n, gr, gu, gn = evaluate(clean, k, 1); print("%d | %.3f (%d of %d)       | %.3f   | %.3f (%d of %d)       | %.3f" % (k, a / n, a, n, u / n, gr / gn, gr, gn, gu / gn))
    m = X.model("direct0")
    for p in (0.05, 0.15):
        print("\nDAMAGED frames p = %.2f (real frames per press, exact-match bank, 200 seeds), k = 3" % p)
        print("events from           | next event right (all) | next GOAL event right | events per true press")
        for name, f in (("no hold", lambda rr, r: [c for _, c in L2.raw_events(L2.ir_stream(rr, p, r, m)[0])]), ("hold 1, skip unknown", lambda rr, r: [c for _, c in L2.hold_events(L2.ir_stream(rr, p, r, m)[0], 1, 1)]), ("hold 2, skip unknown", lambda rr, r: [c for _, c in L2.hold_events(L2.ir_stream(rr, p, r, m)[0], 2, 1)])):
            a, u, n, gr, gu, gn = evaluate(f, 3, 200); r0 = random.Random(0); ev = sum(len(f(rr, r0)) for rr in R) / sum(len(rr) for rr in R)
            print("%-21s | %.3f                  | %.3f                | %.2f" % (name, a / n, gr / max(1, gn), ev))
if __name__ == "__main__": main()
