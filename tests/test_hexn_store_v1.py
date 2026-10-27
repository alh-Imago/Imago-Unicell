"""Layer 2 store and retrieve model (tools/hexn_store_v1.py): real runs, retrieve, repeated anomaly promoted by the rate rule, candidate capacity. Python only."""
import os, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_store_v1 as S, hexn_layer2_v2 as V, hexn_host_promote_v1 as HP
def runs():
    V.R = V.runs(); return [[k for k, _ in r] for r in V.R]
def test_capacity_holds_real_pairs_and_run2_has_no_flags():
    r = runs(); st = S.Store(); st.load([r[0], r[2]]); assert st.dropped_k == 0
    f, h, t = S.run_stream(st, r[1], 1000); assert f == []
def test_run3_extra_key_flagged_once_and_stored_as_candidate_not_known():
    r = runs(); st = S.Store(); st.load([r[0], r[1]]); n = len(st.known); f, h, t = S.run_stream(st, r[2], 1000)
    assert [i for i, v in f] == [22] and st.cand and len(st.known) == n
def test_retrieve_goal_needs_three_events():
    r = runs(); st = S.Store(); st.load(r)
    assert st.retrieve([12, 13, 14])[1] == 18 and st.retrieve([15, 13, 14])[1] == 19 and st.retrieve([12, 16, 17])[1] == 19
    lvl, b, p, tot = st.retrieve([13, 14]); assert lvl == 2 and p < 1.0     # 2 events cannot decide the goal
def test_repeated_anomaly_promoted_when_fast_not_when_slow():
    rb = HP.real_blocks(); pool = list(set(b for run in rb[:2] for b in run)); TRUE = S.truth_pairs(pool); base = [k for b in rb[0] + rb[1] for k in b]
    res = {}
    for G in (4, 40):
        st = S.Store(N=3, W=80); st.load([base]); rnd = random.Random(3); seq = []
        for blk in range(300):
            seq += list(rnd.choice(pool))
            if blk and blk % G == 0: seq.insert(len(seq) - 1, 15)
        hist = []
        for i, x in enumerate(seq):
            if hist: st.observe(hist, x, i)
            hist.append(x)
        res[G] = any(k not in TRUE for k in st.known)
    assert res == {4: True, 40: False}
def test_small_candidate_store_still_learns_new_routine_but_four_slots_do_not():
    assert S.learn_new(4, seeds=4)[1] == 0.0 and S.learn_new(16, seeds=4)[1] == 1.0
