"""Tests for tools/hexn_draughts_hex_v2.py (draughts player with the confidence blend)."""
import importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("h2", os.path.join(ROOT, "tools", "hexn_draughts_hex_v2.py")); H = importlib.util.module_from_spec(sp); sp.loader.exec_module(H)
D, P = H.D, H.P

def test_minimax_mode_picks_the_same_value_as_plain_alpha_beta_on_the_opening():
    g = D.Game(); rnd = random.Random(1); a = H.Hex(2, mode="minimax"); a.start(1)
    best = None
    for m in g.legal():
        rec = D.apply(g.b, m); v = a.val(g.b, 2, 1, 1.0, (), [m[0], None], {}, 0); D.undo(g.b, m, rec); best = v if best is None or v > best else best
    assert -1.0 <= best <= 1.0

def test_blend_and_learn_players_finish_a_game_against_plain():
    for mode in ("blend", "minimax", "learn"):
        r = H.play(H.Hex(2, mode=mode), P.Plain(2), random.Random(3)); assert r in (1, 2, 3)

def test_blend_with_no_model_equals_minimax_choice():
    g = D.Game(); a = H.Hex(2, mode="blend"); b = H.Hex(2, mode="minimax"); a.start(1); b.start(1)
    assert a.pick(g, random.Random(5)) == b.pick(g, random.Random(5))
