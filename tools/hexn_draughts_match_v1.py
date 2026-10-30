"""hexn_draughts_match_v1: STAGE 4 OF THE DRAUGHTS PLAN, THE COMPARISON (Python only; no RTL, nothing on a card). Alan, 30 Oct 2026, 20:20: build draughts and test Hex-N against a similar-style plain design.
Every CANDIDATE plays the same OPPONENT, colours alternating, the first 2 plies random, fresh players for each seed (a Hex player's layer 3 learns online across the games of one seed). Candidates: plainD = tools/hexn_draughts_plain_v1.py alpha-beta at depth D (no learning); hexD = tools/hexn_draughts_hex_v1.py expectimax at depth D with the online-learned layer 3; hexED = the same without any learned model (flat spread over the replies). Opponents: noisy2 = plain depth 2 playing a random move 20% of the time; plain3 = plain depth 3.
Reported: wins / draws / losses of the candidate, its score (wins + half the draws) / games, the mean time per candidate move in milliseconds (all moves of the candidate, Python speed), and for Hex the mean nodes per move.
Usage: python3 tools/hexn_draughts_match_v1.py OPPONENT CANDIDATE... [--games N] [--seeds S]   e.g.  noisy2 plain2 plain3 hex2 hex3 hexE3
Limits: one hand score for all; Python speed; first versions, nothing tuned; one opponent family per run."""
import os, sys, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_draughts_v1 as D, hexn_draughts_plain_v1 as P, hexn_draughts_hex_v1 as H
class Noisy:
    def __init__(s, pl, p): s.pl, s.p = pl, p
    def pick(s, g, rnd): return rnd.choice(g.legal()) if rnd.random() < s.p else s.pl.pick(g, rnd)
class Timed:
    """wraps a candidate: counts its moves and the time they take"""
    def __init__(s, pl): s.pl = pl; s.n = 0; s.t = 0.0
    def pick(s, g, rnd): t = time.time(); r = s.pl.pick(g, rnd); s.t += time.time() - t; s.n += 1; return r
    def start(s, side):
        if hasattr(s.pl, "start"): s.pl.start(side)
    def observe(s, side, mv):
        if hasattr(s.pl, "observe"): s.pl.observe(side, mv)
def make(name):
    if name.startswith("hexE"): return H.Hex(int(name[4:]), empty=True)
    if name.startswith("hex"): return H.Hex(int(name[3:]))
    if name.startswith("plain"): return P.Plain(int(name[5:]))
    raise SystemExit("unknown " + name)
def opponent(name):
    if name == "noisy2": return Noisy(P.Plain(2), 0.2)
    if name == "plain3": return P.Plain(3)
    raise SystemExit("unknown opponent " + name)
def main(opp, cands, games, seeds):
    print("opponent %s; %d seeds x %d games, colours alternate, first 2 plies random" % (opp, seeds, games), flush=True)
    for c in cands:
        w = d = l = 0; nm = 0; tm = 0.0; nodes = 0; hm = 0
        for sd in range(seeds):
            rnd = random.Random(sd); cand = Timed(make(c)); op = opponent(opp)
            for i in range(games):
                if i % 2 == 0: r = H.play(cand, op, rnd); w += r == 1; l += r == 2
                else: r = H.play(op, cand, rnd); w += r == 2; l += r == 1
                d += r == 3
            nm += cand.n; tm += cand.t
            if hasattr(cand.pl, "moves"): nodes += cand.pl.nodes; hm += cand.pl.moves
        n = seeds * games
        print("%-8s W %3d D %3d L %3d   score %.2f   %.0f ms per move%s" % (c, w, d, l, (w + 0.5 * d) / n, 1000 * tm / max(nm, 1), ("   nodes/move %.0f" % (nodes / hm)) if hm else ""), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; games, seeds = 40, 3
    if "--games" in a: i = a.index("--games"); games = int(a[i + 1]); del a[i:i + 2]
    if "--seeds" in a: i = a.index("--seeds"); seeds = int(a[i + 1]); del a[i:i + 2]
    main(a[0], a[1:], games, seeds)
