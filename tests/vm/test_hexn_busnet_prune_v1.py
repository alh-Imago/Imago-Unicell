import os, sys, random, copy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_fb_v1 as F, hexn_busnet_prune_v1 as P


def _setup():
    n = F.make(1, 0.5, fb_k=4, fb_w=2); pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; return n, pats


def test_prune_keeps_exactly_keep_and_rebuilds_delivery():
    n, pats = _setup(); tg2 = T.targets(n); use = {g: {s: i for i, s in enumerate(n.table[g])} for g in n.table}
    P.prune(n, use, 5); assert all(len(t) == 5 for t in n.table.values())
    for g, tab in n.table.items():
        for s in tab: assert any(g in n.bus_cells[b] for b in n.targets[s])
    assert n.queues.keys() >= {b for bs in n.targets.values() for b in bs}


def test_pruned_net_still_runs_and_has_fewer_connections():
    n, pats = _setup(); before = P.n_conn(n); use = {g: {s: 0 for s in n.table[g]} for g in n.table}; P.prune(n, use, 6)
    assert P.n_conn(n) < before; pk, dr = P.traffic(n, pats, nrun=1); assert pk >= 0


def test_layer1_targets_are_layer1_cells():
    n, pats = _setup(); t = P.layer1_targets(n, pats); assert all(all(n.layer_of(g) == 1 for g in x) for x in t) and any(t)


def test_train_respects_ceiling():
    n, pats = _setup(); tg2 = T.targets(n); t1 = P.layer1_targets(n, pats); w0 = P.train(n, pats, tg2, t1, 2, ceil=2)
    for g in n.table:
        for s, w in n.table[g].items(): assert abs(w - w0[g][s]) <= 2
