"""tests/vm/test_hexn_c4_play_v1.py -- Connect Four play engine (1 Nov 2026, Python models only): (1) the columns column_values() calls best are exactly the columns Planner2.pick() can return; (2) the 'reply' numbers are the same ones the search itself uses for the human's reply; (3) a full game is legal, the overlay adds up to 1 (with the human-wins share), errors are errors; (4) the system learns a human's habit (its expected-reply share for that habit rises) and 'forget' resets it."""
import os, sys, random, copy
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_c4_play_v1 as P, hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1
def play_some(pl, n, rnd):
    """a position after n plies of random play with the planner observing (X = system moves from column_values)"""
    b = C.new(); pl.start(); turn = 1
    for _ in range(n):
        if C.winner(b) or C.full(b): break
        c = (rnd.choice(P.column_values(pl, b)[1]) if turn == 1 else rnd.choice(C.legal(b))); C.drop(b, c, turn); pl.observe(turn, c); turn = 3 - turn
    return b, turn
def test_best_columns_equal_what_pick_can_return():
    rnd = random.Random(3)
    for n in (2, 4, 6, 8, 10, 12):
        pl = P.make_planner(); b, turn = play_some(pl, n, rnd)
        if turn != 1 or C.winner(b) or C.full(b): continue
        vals, best, note = P.column_values(pl, b); picks = set()
        for sd in range(40): picks.add(pl.pick([col[:] for col in b], random.Random(sd)))
        assert picks <= set(best) and (len(best) == 1 or len(picks) > 1), (n, vals, best, picks)
def test_reply_numbers_come_from_the_search_function_and_differ_only_by_learning_the_move():
    """reply_dist() calls the same planner.odist() the search calls. Given the SAME context (layer 3's history and snapshot as the search builds them, no learning step in between) the numbers are identical.
    The live numbers can differ from what the search used when it chose its move, only because layer 3 has since LEARNED the system's own move (when that move leaves the last-move context unchanged, the new entry dilutes the prediction): found 1 Nov 2026, kept as shown."""
    rnd = random.Random(8); checked = 0; changed = 0
    for n in (2, 6, 10):
        pl = P.make_planner(); b, turn = play_some(pl, n, rnd)
        if turn != 1 or C.winner(b) or C.full(b): continue
        for c in C.legal(b):
            r = L1.lands(b, c); b[c][r] = 1; sn = list(pl.m.snap); sn[0] = c; legal_ = [k for k in L1.ORDER if b[k][L1.ROWS - 1] == 0]
            if not legal_ or L1.wins_at(b, c, r, 1): b[c][r] = 0; continue
            expect = pl.odist(b, (tuple(pl.m.hist) + (tuple(sn),))[-5:], sn, legal_, {})                 # exactly what Planner3.val passes for O's reply
            p3 = copy.deepcopy(pl); p3.m.hist = list((tuple(pl.m.hist) + (tuple(sn),))[-5:]); p3.m.snap = list(sn)                     # the same context, set by hand: NO learning step
            same = P.reply_dist(p3, b); assert set(same) == set(expect) and all(abs(same[k] - expect[k]) < 1e-12 for k in same); checked += 1
            p2 = copy.deepcopy(pl); p2.observe(1, c); live = P.reply_dist(p2, b); b[c][r] = 0
            assert abs(sum(live.values()) - 1.0) < 1e-9; changed += any(abs(live[k] - expect[k]) > 1e-9 for k in live)
    assert checked > 10
def test_full_game_overlay_and_errors():
    g = P.Game(seed=2); rnd = random.Random(4); assert g.status == "play" and len(g.moves) == 1 and g.moves[0][0] == 1
    try: g.human(9); raise AssertionError("illegal column accepted")
    except ValueError: pass
    while g.status == "play":
        st = g.state(); assert abs(sum(st["next"].values()) + st["human_wins_chance"] - 1.0) < 1e-9 and set(map(int, st["next"])) <= set(st["legal"])
        g.human(rnd.choice(st["legal"]))
    assert g.state()["over"] in ("system", "human", "draw") and g.stats["games"] == 1
    try: g.human(0); raise AssertionError("move after the end accepted")
    except ValueError: pass
    if g.over in ("system", "human"): assert len(g.state()["win_cells"]) == 4
    g.new(); assert g.status == "play" and g.stats["games"] == 1
    g.forget(); assert g.stats["games"] == 0 and len(g.moves) == 1
def test_it_learns_a_habit_and_forget_resets():
    g = P.Game(seed=0); first = g.reply.get(0, 0.0); first_state = dict(g.reply)
    for _ in range(12):
        while g.status == "play":
            g.human(0 if 0 in g.state()["legal"] else g.state()["legal"][0])
        g.new()
    assert g.reply.get(0, 0.0) > first + 0.05, (first, g.reply)
    g.forget(); assert all(abs(g.reply[k] - first_state[k]) < 1e-9 for k in first_state)
