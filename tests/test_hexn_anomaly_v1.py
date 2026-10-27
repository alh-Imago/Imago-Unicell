"""Layer 2 self-check / anomaly store (tools/hexn_anomaly_v1.py) on the real routine recordings: the extra key 4 of run 3 is flagged (at the next press), context 1 and 2 raise no false alarm on runs 1 and 2, and a swapped goal key is caught only with a context of 3 events. Python only."""
import os, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_anomaly_v1 as A, hexn_layer2_v2 as V
def setup():
    V.R = V.runs(); return [[k for k, _ in r] for r in V.R]
def test_extra_key_flagged_in_run3_and_no_false_alarm_with_short_contexts():
    runs = setup()
    for k in (1, 2):
        for test in range(3):
            t = A.build([runs[j] for j in range(3) if j != test], k); f = A.flags(t, k, runs[test])
            assert (len(f) == 1 and f[0][0] == 21) if test == 2 else f == [], (k, test, f)
def test_goal_swap_needs_three_events():
    runs = setup(); r = random.Random(1)
    for k, want in ((1, 0.0), (2, 0.0), (3, 1.0)):
        hit = tot = 0
        for test in range(3):
            t = A.build([runs[j] for j in range(3) if j != test], k); base = set(i for i, _ in A.flags(t, k, runs[test]))
            for pos in [i for i, c in enumerate(runs[test]) if c in V.GOALS]:
                s = list(runs[test]); s[pos] = 37 - s[pos]; new = set(i for i, _ in A.flags(t, k, s)) - base; tot += 1; hit += any(i in (pos, pos + 1) for i in new)
        assert hit / tot == want, (k, hit, tot)
