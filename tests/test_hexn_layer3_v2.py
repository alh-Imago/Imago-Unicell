"""Layer 3 with reward, goal comparison and the feedback record stream."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_layer3_v2 as M
def test_compare_record():
    r = M.compare({"request": 0, "desired": 5}, 6, 0.2, [0, 4]); assert r["reached"] is False and r["reward"] == -32
    assert M.compare({"request": 1, "desired": 6}, 6, 0.9, [3, 1])["reward"] == 64
def test_layer3_steers_and_layer2_cannot():
    h3 = [M.run(seed=s, n=500, mode="l3")[0] for s in range(4)]; h2 = [M.run(seed=s, n=500, mode="l2")[0] for s in range(4)]
    assert sum(M.share(h, 300, 500) for h in h3) / 4 > 0.9
    assert abs(sum(M.share(h, 300, 500) for h in h2) / 4 - 0.5) < 0.08
def test_records_replay_into_layer2_store():
    h, recs, cmds, st = M.run(seed=1, n=200, mode="l2", log=True)
    assert M.tables(st) == M.tables(M.replay(cmds)) and len(recs) == 200 and set(r["reward"] for r in recs) <= {64, -32}
