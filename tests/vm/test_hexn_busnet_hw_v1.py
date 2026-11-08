import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_hw_v1 as W


def tiny(**kw):
    n = W.HWNet(1, k=3, nin=6, layers=1, groups=1, per=2, leak_every=0, **kw); g0, g1 = n.gid(1, 0), n.gid(1, 1)
    n.table[g0] = {0: 1, 1: 1, 2: 1}; n.table[g1] = {}; n.targets = {0: {(1, 0)}, 1: {(1, 0)}, 2: {(1, 0)}}; n.th_cell[g0] = 3; return n, g0


def test_one_input_id_per_clock_and_one_packet_per_bus_per_clock():
    n, g0 = tiny(); n.step(0, [0, 1, 2])             # three ids at once: serialiser sends one, so only one weight arrives this clock
    assert n.acc[g0] == 1 and n.served == 1
    n.step(1); n.step(2); assert n.acc[g0] == 0 or n.fires.get(g0)     # all three delivered by clock 2 -> fired


def test_two_ports_serve_two_packets_per_clock():
    n, g0 = tiny(ports=2); q = n.sqs[((1, 0), (0, 0))]; q.extend([0, 1]); n.step(0); assert n.served == 2 and n.acc[g0] == 2


def test_event_on_a_line_that_is_still_pending_is_merged_and_counted():
    n, g0 = tiny(); n.step(0, [0, 0]); assert n.drop_fq == 1 and n.dropped == 1


def test_serialiser_rotates_so_no_source_starves():
    n, g0 = tiny(); n.step(0, [0, 1, 2]); n.step(1); n.step(2)
    assert n.ptr[(0, 0)] == 3 and not n.pend[(0, 0)]


def test_fresh_run_resets_merger_state():
    import hexn_busnet_train_v1 as T
    n, g0 = tiny(); n.step(0, [0, 1, 2]); m = T.fresh_run(n, {}); assert not any(m.pend.values()) and all(not q for q in m.sqs.values()) and m.pushed == 0
