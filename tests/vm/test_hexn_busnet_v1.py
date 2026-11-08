"""tests/vm/test_hexn_busnet_v1.py - the bus network toy (model only). Fast."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B


def tiny(**kw): return B.Net(1, k=3, nin=6, layers=1, groups=1, per=2, **kw)


def test_only_cells_with_an_entry_take_a_packet_and_one_packet_per_bus_per_clock():
    n = tiny(leak_every=0); g0, g1 = n.gid(1, 0), n.gid(1, 1); n.table[g0] = {0: 2}; n.table[g1] = {1: 2}; n.targets = {0: {(1, 0)}, 1: {(1, 0)}}
    n.step(0, [0, 1]); assert n.acc[g0] == 2 and n.acc[g1] == 0 and n.served == 1       # only id 0 was served this clock
    n.step(1); assert n.acc[g1] == 2 and n.served == 2


def test_queue_drops_when_full_and_counts():
    n = tiny(qdepth=2); n.targets = {0: {(1, 0)}}
    n.step(0, [0, 0, 0, 0]); assert n.dropped == 2 and n.maxq == 2


def test_fire_resets_refractory_and_leak():
    n = tiny(th=2, refr=3, leak_every=0); g0 = n.gid(1, 0); n.table[g0] = {0: 2}; n.table[n.gid(1, 1)] = {}; n.targets = {0: {(1, 0)}}
    assert n.step(0, [0]) == [g0] and n.acc[g0] == 0
    n.step(1, [0]); assert n.acc[g0] == 0                                            # refractory: the packet is ignored
    n2 = tiny(th=5, leak_every=1); h = n2.gid(1, 0); n2.table[h] = {0: 2}; n2.targets = {0: {(1, 0)}}
    n2.step(0, [0]); assert n2.acc[h] == 1                                           # +2 then leak 1


def test_deterministic():
    r = __import__("random").Random(3); p = B.pattern(r); ev = {}
    for i, t in p: ev.setdefault(t, []).append(i)
    a, _ = B.trial(1, ev); b, _ = B.trial(1, ev); assert a.fires == b.fires and a.pushed == b.pushed
