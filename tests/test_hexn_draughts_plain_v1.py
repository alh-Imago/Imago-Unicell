"""Plain draughts baseline: takes a free piece, beats random play, a deeper search beats a shallower one more often than not."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_draughts_v1 as D, hexn_draughts_plain_v1 as P
def test_score_is_zero_at_the_start_and_antisymmetric():
    b = D.new(); assert P.score(b, 1) == 0 and P.score(b, 2) == 0
    b[D.SQ[(5, 0)]] = 0; assert P.score(b, 1) < 0 and P.score(b, 2) == -P.score(b, 1)
def test_search_finds_the_loss_when_there_is_no_move():
    b = [0] * 32; b[0] = 3; assert P.search(b, 1, 3, -10 ** 9, 10 ** 9) < -9000
def test_beats_random_play():
    aw, dr, bw = P.match(P.Plain(3), P.Rand(), 6, 1); assert aw >= 5
def test_deeper_beats_shallower_more_often_than_not():
    aw, dr, bw = P.match(P.Plain(4), P.Plain(1), 8, 2); assert aw > bw
