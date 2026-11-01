#!/usr/bin/env python3
"""hexn_c4_play_v1 (new file 1 Nov 2026): PLAY CONNECT FOUR AGAINST THE LAYER 3 / LAYER 4 MODELS, and say where the system is heading. Python models on the PC; nothing here runs on the board.
Alan, 02:08: add the games to the front end; when a human plays, highlight the probable moves the system is going towards, as an overlay. Chosen (02:10): Connect Four first; the overlay shows the system's OWN likely next moves; the moves come from the Python layer 3 / 4 models on the PC.
THE SYSTEM = the planner already tested in the ledger (30 Oct): tools/hexn_connect4_cand_v1.py P 'base' (tools/hexn_connect4_layer4_v3.py Planner3 on the plain layer 3), depth 4, free plies at confidence .8, theta .04, tactics prior. It plays X and moves FIRST (as in every test); the human plays O. It learns the human's moves as the games go (layer 3), and keeps what it learned from game to game until you press 'forget'.
THE OVERLAY ('where it is heading'): on the human's turn, for each reply the human might make, layer 3 gives a probability (with the same tactics prior the planner uses). For each reply the planner's own search then says which column it would play next (ties share equally). Adding those up, weighted by the reply probabilities, gives the chance that the system plays each column next. Replies that win the game for the human count as 'game over' and are not spread. It is a MODEL's estimate, not a promise: layer 3 knows only the moves it has seen.
Also given: 'reply' = layer 3's probability of each human reply, 'value' = the planner's value of each column NOW (-1 bad for the system ... +1 winning; only on the system's own turn).
column_values() repeats the loop of Planner2.pick (tools/hexn_connect4_layer4_v2.py) without choosing, so that the move played and the numbers shown cannot disagree; a test checks that its best columns equal what pick() would choose."""
import os, sys, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_layer4_v2 as L2, hexn_connect4_cand_v1 as X
from hexn_connect4_layer4_v1 import lands, can_win, ORDER
def make_planner(): return X.P("base", 0.0, mode="tree3", theta=0.04, tactics=True, dmax=4, conf=0.8)
def column_values(pl, b):
    """-> (values {col: v}, best [cols], forced note or ''): what Planner2.pick would weigh, without choosing."""
    legal_ = C.legal(b); w = can_win(b, 1)
    if w: return {c: (1.0 if c in w else 0.0) for c in legal_}, [w[0]], "it can win now"
    bl = can_win(b, 2)
    if bl: return {c: (0.0) for c in legal_}, [bl[0]], "it must block"
    pl.ply = 0; cache = {}; vals = {}; root = L2.Node(); root.kids = {}
    for c in [c for c in ORDER if c in legal_]:
        r = lands(b, c); b[c][r] = 1; sn = list(pl.m.snap); sn[0] = c
        ch = root.kids.setdefault(c, L2.Node())
        vals[c] = pl.val(ch, b, 2, pl.dmax - 1, 1.0, (tuple(pl.m.hist) + (tuple(sn),))[-5:], sn, cache)
        b[c][r] = 0
    best = max(vals.values()); return vals, [c for c in vals if abs(vals[c] - best) <= 1e-9], ""
def reply_dist(pl, b):
    """layer 3's probability of each human reply right now (after the system's last move), with the planner's tactics prior"""
    legal_ = [c for c in ORDER if b[c][L1.ROWS - 1] == 0]; return pl.odist(b, tuple(pl.m.hist), list(pl.m.snap), legal_, {})
def heading(pl, b):
    """-> (next {col: chance the system plays it next}, reply {col: chance of each human reply}, human_wins chance)"""
    rd = reply_dist(pl, b); nxt = {c: 0.0 for c in C.legal(b)}; hw = 0.0
    for c, p in rd.items():
        if p <= 0: continue
        b2 = [col[:] for col in b]; r = lands(b2, c); b2[c][r] = 2
        if L1.wins_at(b2, c, r, 2): hw += p; continue
        if not C.legal(b2): continue
        p2 = copy.deepcopy(pl); p2.observe(2, c); vals, best, _ = column_values(p2, b2)
        for k in best: nxt[k] = nxt.get(k, 0.0) + p / len(best)
    return nxt, rd, hw
class Game:
    def __init__(s, seed=0):
        s.rnd = random.Random(seed); s.pl = make_planner(); s.stats = {"games": 0, "system_wins": 0, "human_wins": 0, "draws": 0}; s.new()
    def forget(s): s.pl = make_planner(); s.stats = {"games": 0, "system_wins": 0, "human_wins": 0, "draws": 0}; s.new()
    def new(s):
        s.b = C.new(); s.pl.start(); s.status = "play"; s.moves = []; s.last = None; s.note = ""; s.over = None; s._system_move(); s._overlay()
    def _finish(s, w):
        s.status = "over"; s.stats["games"] += 1
        if w == 1: s.over = "system"; s.stats["system_wins"] += 1
        elif w == 2: s.over = "human"; s.stats["human_wins"] += 1
        else: s.over = "draw"; s.stats["draws"] += 1
    def _system_move(s):
        vals, best, note = column_values(s.pl, s.b); c = s.rnd.choice(best); s.values = vals; s.note = note
        r = C.drop(s.b, c, 1); s.pl.observe(1, c); s.moves.append((1, c, r)); s.last = (c, r)
        w = C.winner(s.b)
        if w or C.full(s.b): s._finish(w)
    def _overlay(s):
        if s.status != "play": s.next = {}; s.reply = {}; s.hwin = 0.0; return
        s.next, s.reply, s.hwin = heading(s.pl, s.b)
    def human(s, col):
        if s.status != "play": raise ValueError("the game is over: press New game")
        if col not in C.legal(s.b): raise ValueError("that column is full or does not exist")
        r = C.drop(s.b, col, 2); s.pl.observe(2, col); s.moves.append((2, col, r)); s.last = (col, r); s.note = ""; w = C.winner(s.b)
        if w or C.full(s.b): s._finish(w)
        else: s._system_move()
        s._overlay()
    def state(s):
        return {"board": [col[:] for col in s.b], "status": s.status, "over": s.over, "last": s.last, "moves": s.moves, "note": s.note, "legal": C.legal(s.b) if s.status == "play" else [],
                "next": {str(k): v for k, v in s.next.items()}, "reply": {str(k): v for k, v in s.reply.items()}, "human_wins_chance": s.hwin, "stats": dict(s.stats), "values": {str(k): v for k, v in (s.values or {}).items()},
                "win_cells": win_cells(s.b) if s.over in ("system", "human") else []}
def win_cells(b):
    for cells in C.LINES:
        v = b[cells[0][0]][cells[0][1]]
        if v and all(b[x][y] == v for x, y in cells): return [list(c) for c in cells]
    return []
