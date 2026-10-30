"""English draughts rules engine: perft against the published sequence, mandatory capture, multi-jump, crowning ends a jump, no moves = loss."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_draughts_v1 as D
def test_perft_matches_the_published_numbers():
    b = D.new()
    for depth, want in ((1, 7), (2, 49), (3, 302), (4, 1469), (5, 7361), (6, 36768), (7, 179740)):
        assert D.perft(b, 1, depth) == want, depth
    assert b == D.new()                      # apply / undo leave the board as it was
def test_capture_is_mandatory():
    b = [0] * 32; b[D.SQ[(5, 2)]] = 1; b[D.SQ[(4, 3)]] = 3; b[D.SQ[(3, 4)]] = 0; b[D.SQ[(7, 0)]] = 1
    mv = D.moves(b, 1); assert mv and all(m[1] for m in mv)          # a jump exists, so no plain step is offered
def test_multi_jump_and_no_double_jump():
    b = [0] * 32; b[D.SQ[(6, 1)]] = 1; b[D.SQ[(5, 2)]] = 3; b[D.SQ[(3, 4)]] = 3; b[D.SQ[(1, 6)]] = 3
    mv = D.moves(b, 1); assert len(mv) == 1 and len(mv[0][1]) == 3 and mv[0][0][-1] == D.SQ[(0, 7)]     # three jumps in a row, crowned on the last
def test_crowning_ends_the_jump():
    b = [0] * 32; b[D.SQ[(2, 1)]] = 1; b[D.SQ[(1, 2)]] = 3; b[D.SQ[(1, 4)]] = 3        # after landing on row 0 the new king could jump again; it must stop
    mv = D.moves(b, 1); assert mv and all(len(m[1]) == 1 for m in mv)
    rec = D.apply(b, mv[0]); assert b[mv[0][0][-1]] == 2; D.undo(b, mv[0], rec); assert b[D.SQ[(2, 1)]] == 1
def test_no_legal_move_loses_and_random_games_end():
    g = D.Game(); b = [0] * 32; b[0] = 3; g.b = b; g.turn = 1; assert g.result() == 2        # X has no pieces
    for seed in range(30):
        r = random.Random(seed); g = D.Game()
        while not g.result(): g.play(r.choice(g.legal()))
        assert g.result() in (1, 2, 3)
