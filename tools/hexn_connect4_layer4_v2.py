"""hexn_connect4_layer4_v2: LAYER 4 WITH A SLIDING PLAN TREE AND A SHALLOW CHECK OF EVERY REPLY (Python only; no RTL, nothing on a card). Clone-extension of tools/hexn_connect4_layer4_v1.py (left untouched; its board helpers and opponent model are reused).
Alan, 29 Oct 2026, 15:50 and 16:03: the plan is kept between moves: if the opponent does what was predicted, layer 4 keeps the part of the tree under that reply, removes the branches not chosen, and extends the survivors at the far end; a reply that was not expanded has nothing to reuse and is searched fresh. Layer 4 never fully closes a possibility unless it ends the game: every legal reply is looked at least a little.
What is new against v1:
 - REUSE: the tree is made of nodes that stay between moves. After X plays and O replies, the root slides to the node under (X's move, O's reply) if it exists (everything else is dropped, i.e. forgotten); if that reply was never expanded, a fresh root. Every move the tree is extended again to `dmax` plies from the new root, but only the missing part is built (its leaf values and opponent distributions are computed once and kept).
 - FLOOR: a reply of O whose path probability is below `theta` is not dropped; it is searched `floor_d` plies deep (v1: not at all). `floor_d` = 0 switches this off.
 - Counted per move: `created` = nodes expanded or leaves valued for the first time (the real work), `visited` = nodes touched in the value update (cheap), and the share of O's replies that found an expanded subtree (reuse rate).
Limits: stored opponent distributions and leaf values are not refreshed after layer 3 learns more (stale by design, to be measured); X plays first; the step-target passing to layer 3 is NOT in this file (next version); small samples, nothing tuned."""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1
from hexn_connect4_layer4_v1 import lands, wins_at, can_win, ORDER, ROWS
class Node:
    __slots__ = ("kids", "dist", "leaf", "exp")
    def __init__(s): s.kids = None; s.dist = None; s.leaf = None; s.exp = 0
class Planner2(L1.Planner):
    def __init__(s, mode="tree3", theta=0.04, dmax=6, tactics=True, reuse=True, floor_d=2):
        super().__init__(mode, theta, dmax, tactics); s.reuse, s.floor_d = reuse, floor_d
        s.created = 0; s.visited = 0; s.replies = 0; s.reused = 0; s.root = Node(); s.xnode = None
    def start(s): super().start(); s.root = Node(); s.xnode = None
    def observe(s, who, c):
        super().observe(who, c)
        if who == 1:
            s.xnode = s.root.kids.get(c) if s.root.kids else None
        else:
            s.replies += 1
            nxt = s.xnode.kids.get(c) if (s.xnode is not None and s.xnode.kids) else None
            if nxt is not None and nxt.kids: s.reused += 1
            s.root = nxt if (nxt is not None and s.reuse) else Node()
    def val(s, node, b, turn, want, p, hist, snap, cache):
        s.visited += 1
        legal_ = [c for c in ORDER if b[c][ROWS - 1] == 0]
        if not legal_: return 0.0
        eff = want if p >= s.theta else min(want, s.floor_d)
        if eff <= 0:
            if node.leaf is None: node.leaf = s.leaf(b); s.created += 1
            return node.leaf
        if node.kids is None:
            node.kids = {}; s.created += 1
            if turn == 2: node.dist = s.odist(b, hist, snap, legal_, cache)
        if turn == 1:
            best = -2.0
            for c in legal_:
                r = lands(b, c); b[c][r] = 1
                if wins_at(b, c, r, 1): v = 1.0
                else:
                    ch = node.kids.get(c)
                    if ch is None: ch = node.kids[c] = Node()
                    sn = list(snap); sn[0] = c; v = s.val(ch, b, 2, eff - 1, p, (hist + (tuple(sn),))[-5:], sn, cache)
                b[c][r] = 0; best = max(best, v)
                if best >= 1.0: break
            return best
        tot = 0.0
        for c in legal_:
            pc = node.dist.get(c, 0.0)
            if pc <= 0: continue
            r = lands(b, c); b[c][r] = 2
            if wins_at(b, c, r, 2): v = -1.0
            else:
                ch = node.kids.get(c)
                if ch is None: ch = node.kids[c] = Node()
                sn = list(snap); sn[1] = c; v = s.val(ch, b, 1, eff - 1, p * pc, (hist + (tuple(sn),))[-5:], sn, cache)
            b[c][r] = 0; tot += pc * v
        return tot
    def pick(s, b, rnd):
        legal_ = C.legal(b); s.moves += 1
        w = can_win(b, 1)
        if w: return w[0]
        bl = can_win(b, 2)
        if bl: return bl[0]
        if s.mode == "forced": return rnd.choice(legal_)
        cache = {}; best, bc = -3.0, []; root = s.root
        if root.kids is None: root.kids = {}
        for c in [c for c in ORDER if c in legal_]:
            r = lands(b, c); b[c][r] = 1; sn = list(s.m.snap); sn[0] = c
            ch = root.kids.get(c)
            if ch is None: ch = root.kids[c] = Node()
            v = s.val(ch, b, 2, s.dmax - 1, 1.0, (tuple(s.m.hist) + (tuple(sn),))[-5:], sn, cache)
            b[c][r] = 0
            if v > best + 1e-9: best, bc = v, [c]
            elif abs(v - best) <= 1e-9: bc.append(c)
        return rnd.choice(bc)
def run(opp, games, seed, **kw):
    rnd = random.Random(seed); pl = Planner2(**kw); res = [L1.game(pl, opp, rnd) for _ in range(games)]
    return res, pl
VARIANTS = [("rebuild each move, no floor (as v1)", dict(reuse=False, floor_d=0)), ("rebuild each move, floor 2", dict(reuse=False, floor_d=2)),
            ("sliding tree, no floor", dict(reuse=True, floor_d=0)), ("sliding tree, floor 2", dict(reuse=True, floor_d=2))]
def main(games=100, seeds=1):
    h = games // 2
    for oname, opp in (("RANDOM opponent", C.opp_random), ("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))):
        print("\n%s: layer 3 prediction, theta .04, dmax 6; online [win / draw / loss] games 1-%d and %d-%d, mean of %d seeds; per move: created / visited nodes; reply found in tree" % (oname, h, h + 1, games, seeds))
        for name, kw in VARIANTS:
            rs = [run(opp, games, sd, **kw) for sd in range(seeds)]
            def sh(a, bb): n = len(rs) * (bb - a); return [sum(sum(1 for x in r[0][a:bb] if x == k) for r in rs) / n for k in (1, 0, 2)]
            f, l = sh(0, h), sh(h, games)
            mv = sum(r[1].moves for r in rs); cr = sum(r[1].created for r in rs) / mv; vi = sum(r[1].visited for r in rs) / mv; ru = sum(r[1].reused for r in rs) / max(sum(r[1].replies for r in rs), 1)
            print("%-38s %.2f / %.2f / %.2f   %.2f / %.2f / %.2f   created %6.0f visited %6.0f  reuse %.2f" % (name, f[0], f[1], f[2], l[0], l[1], l[2], cr, vi, ru), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
