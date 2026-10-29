import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_connect4_v1 as C
def test_gravity_and_columns():
    b = C.new(); assert C.drop(b, 3, 1) == 0 and C.drop(b, 3, 2) == 1 and C.height(b, 3) == 2
    for _ in range(4): C.drop(b, 3, 1)
    assert 3 not in C.legal(b) and len(C.legal(b)) == 6
    C.undo(b, 3); assert 3 in C.legal(b)
def test_four_in_a_row_all_directions():
    assert len(C.LINES) == 69
    b = C.new()
    for c in range(4): C.drop(b, c, 1)
    assert C.winner(b) == 1
    b = C.new()
    for _ in range(4): C.drop(b, 6, 2)
    assert C.winner(b) == 2
    b = C.new()   # diagonal for X: columns 0..3 with heights 0,1,2,3
    for c in range(4):
        for _ in range(c): C.drop(b, c, 2)
        C.drop(b, c, 1)
    assert C.winner(b) == 1
    b = C.new()   # anti-diagonal
    for c in range(4):
        for _ in range(3 - c): C.drop(b, c, 2)
        C.drop(b, c, 1)
    assert C.winner(b) == 1
def test_players_take_wins_and_blocks_and_games_end():
    rnd = random.Random(1); b = C.new()
    for c in range(3): C.drop(b, c, 1)
    assert C.opp_blocker(b, 1, rnd) == 3 and C.opp_blocker(b, 2, rnd) == 3   # win, or block
    assert C.make_lookahead(2)(b, 1, rnd) == 3
    for i in range(6):
        r, s = C.play_game(C.opp_random, C.opp_blocker, random.Random(i)); assert 0 <= r <= 2 and 4 <= len(s) <= 42
def test_search_beats_weaker_players():
    w, d, l, m = C.match(C.make_lookahead(3), C.opp_random, 10, seed=3); assert w >= 18 and l == 0
