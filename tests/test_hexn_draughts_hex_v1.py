"""Hex-N stack on draughts: plays legal complete games, learns online (its layer 3 gets events), and the no-model control uses a flat spread."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_draughts_v1 as D, hexn_draughts_plain_v1 as P, hexn_draughts_hex_v1 as H
def test_hex_plays_complete_legal_games_and_learns():
    h = H.Hex(2); rnd = random.Random(0)
    for _ in range(3): assert H.play(h, P.Plain(1), rnd) in (1, 2, 3)
    assert len(h.m.tab) > 0 and h.moves > 0
def test_empty_control_has_flat_replies():
    h = H.Hex(2, empty=True); g = D.Game(); g.play(g.legal()[0]); mv = g.legal()
    d = h.dist(mv, (), [None, None], {}); assert all(abs(v - 1.0 / len(mv)) < 1e-9 for v in d.values())
def test_hex_takes_a_win_in_one():
    b = [0] * 32; b[D.SQ[(5, 2)]] = 1; b[D.SQ[(4, 3)]] = 3; b[D.SQ[(7, 6)]] = 1       # X can capture the only O man
    g = D.Game(); g.b = b; g.turn = 1; h = H.Hex(2); h.start(1)
    mv = h.pick(g, random.Random(0)); assert mv[1] and g.b[D.SQ[(4, 3)]] == 3
