"""tests/vm/test_hexn_ring_cycle_v1.py - the ring-cycle script against a pretend card (logic only, not the hardware): settle then retry, id picks the vector, a missing hop and an unknown id are caught."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_ring_cycle_v1 as R, hexn_hexcard_host_v1 as Hh

A, B = 0x90894555, 0x8F532C4A
VEC = {A: {"rows": 7, "tests": [{"expected": 1}]}, B: {"rows": 6, "tests": [{"expected": 1}]}}


class Clock:
    def __init__(s): s.t = 0.0
    def now(s): return s.t
    def sleep(s, d): s.t += d


class Card:
    """ring A,B; after a hop it is silent for `quiet` seconds of fake time"""
    def __init__(s, clk, quiet=1.0, ring=(A, B), hops_work=True):
        s.clk, s.quiet, s.ring, s.i, s.until, s.work = clk, quiet, ring, 0, 0.0, hops_work; s.out = b""
    def hop(s):
        if s.work: s.i = (s.i + 1) % len(s.ring)
        s.until = s.clk.t + s.quiet
    def reset_input_buffer(s): s.out = b""
    def write(s, b):
        if b == b"I" and s.clk.t >= s.until: pid = s.ring[s.i]; s.out = pid.to_bytes(4, "little") + bytes([7 if pid == A else 6])
    def read(s, n): d, s.out = s.out[:n], s.out[n:]; return d


def run(card, clk, rounds=4, settle=0.5, vec=VEC, timeout=10):
    lines = []; Hh.run_test = lambda s, t: t["expected"]
    res = R.cycle(card, vec, rounds, settle, timeout, card.hop, out=lines.append, sleep=clk.sleep, clock=clk.now)
    return res, lines


def test_alternates_and_passes_when_the_card_is_slow_to_answer():
    clk = Clock(); res, lines = run(Card(clk, quiet=1.0), clk)
    assert [r[1] for r in res] == [A, B, A, B, A] and all(r[3] for r in res) and lines[-1].startswith("RING CYCLE PASS")
    assert all(0.9 < r[2] < 2.0 for r in res[1:])      # waited out the quiet time, not more than one retry beyond it


def test_a_hop_that_changes_nothing_is_reported():
    clk = Clock(); res, lines = run(Card(clk, hops_work=False), clk, rounds=2)
    assert not res[1][3] and "SAME CARD" in lines[1] and lines[-1].startswith("RING CYCLE FAIL")


def test_unknown_id_and_silence_are_failures():
    clk = Clock(); res, lines = run(Card(clk), clk, rounds=2, vec={A: VEC[A]})
    assert "UNKNOWN ID" in lines[1] and not res[1][3]
    clk = Clock(); res, lines = run(Card(clk, quiet=99), clk, rounds=2, timeout=5)
    assert res[-1][1] is None and "NO ANSWER" in lines[-2]


def test_a_card_that_dies_mid_selftest_is_a_failure_not_a_crash():
    clk = Clock(); card = Card(clk); lines = []
    def boom(s, t): raise SystemExit("timeout waiting for L count")
    Hh.run_test = boom
    res = R.cycle(card, VEC, 1, 0.5, 5, card.hop, out=lines.append, sleep=clk.sleep, clock=clk.now)
    assert not res[0][3] and "SELFTEST FAIL" in lines[0]
