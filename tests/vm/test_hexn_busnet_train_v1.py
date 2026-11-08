import os, sys, random, copy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T


def test_targets_are_disjoint_and_sized():
    n = B.Net(1); tg = T.targets(n); assert all(len(t) == 10 for t in tg); assert len(set().union(*tg)) == 80


def test_train_step_respects_ceiling_and_wmax():
    n = B.Net(1); w0 = copy.deepcopy(n.table); tg = T.targets(n); p = B.pattern(random.Random(100)); ev = B.noisy(p, random.Random(1))
    for _ in range(30):
        m = T.fresh_run(n, ev); T.train_step(m, w0, ev, tg[0]); n.table = m.table
    for g in n.table:
        for s, w in n.table[g].items(): assert abs(w - w0[g][s]) <= T.CEIL and abs(w) <= T.WMAX


def test_train_step_raises_missed_target_cell_weights():
    n = B.Net(1); w0 = copy.deepcopy(n.table); tg = T.targets(n); ev = B.noisy(B.pattern(random.Random(100)), random.Random(1))
    m = T.fresh_run(n, ev); missed = [g for g in tg[0] if g not in B.map_of(m)]
    before = {g: sum(m.table[g].values()) for g in missed}; T.train_step(m, w0, ev, tg[0])
    assert all(sum(m.table[g].values()) >= before[g] for g in missed) and any(sum(m.table[g].values()) > before[g] for g in missed)


def test_fresh_run_does_not_mutate_template():
    n = B.Net(1); ev = B.noisy(B.pattern(random.Random(100)), random.Random(1)); T.fresh_run(n, ev); assert not n.fires and n.pushed == 0
