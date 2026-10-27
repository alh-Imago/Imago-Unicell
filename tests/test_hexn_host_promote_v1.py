"""Host routine that picks the promotion level N, W from a training stream (tools/hexn_host_promote_v1.py): default with too few anomalies (the real run 3), data-set levels beat the default at high noise. Python only."""
import os, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_host_promote_v1 as H
def setup():
    rb = H.real_blocks(); pool = list(set(b for run in rb[:2] for b in run)); return rb, pool, set(pool)
def test_real_run3_has_too_few_anomalies_so_default():
    rb, pool, known = setup(); c = H.choose(rb[2], known); assert (c["N"], c["W"]) == H.DEFAULT and c["source"].startswith("default")
def test_blocks_end_at_goals():
    rb, pool, known = setup(); assert len(pool) == 4 and all(b[-1] in H.GOALS for run in rb for b in run)
def test_host_level_beats_default_at_high_noise_and_still_finds_new_routine():
    rb, pool, known = setup(); tr = [b for b, _ in H.make_stream(pool, random.Random(11), 0.6, 1500)]; c = H.choose(tr, known)
    assert c["source"] == "from data"
    f1 = f2 = 0; found = 0
    for s in range(10):
        st = H.make_stream(pool, random.Random(1000 + s), 0.6, 3000, (12, 16, 14, 18))
        a, p = H.evaluate(st, known, c["N"], c["W"]); f1 += a; found += p is not None
        f2 += H.evaluate(st, known, *H.DEFAULT)[0]
    assert f1 < f2 and found == 10
