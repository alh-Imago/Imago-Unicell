"""hexn_connect4_layer4_v3: LAYER 4 WITH DEPTH CHOSEN BY LAYER 3's CONFIDENCE (Python only; no RTL, nothing on a card). Extends tools/hexn_connect4_layer4_v2.py (left untouched).
Alan, 29 Oct 2026, 18:38-18:40: depth beyond what the first model used did not pay (theta .01, floor 2); the route he chose is to vary the depth by how sure layer 3 is of the opponent's reply.
Rule: the tree has a base depth `dmax`. When layer 3 gives the opponent's reply a probability >= `conf` (a nearly forced line, branching about 1, so going on costs almost nothing), that reply does not use up a ply of the budget; a hard cap `dcap` on total plies stops it. Replies below `theta` path probability are dropped as in v1 (no floor, no reuse: both showed no gain in v2). `conf` = 2 switches the rule off (plain v1 behaviour with this dmax).
Counted: positions created per move. Limits: 1 seed, small samples, nothing tuned; step-target passing to layer 3 is NOT here."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_layer4_v2 as L2
from hexn_connect4_layer4_v1 import lands, wins_at, ORDER, ROWS
class Planner3(L2.Planner2):
    def __init__(s, conf=0.8, dcap=10, **kw):
        kw.setdefault("reuse", False); kw.setdefault("floor_d", 0); super().__init__(**kw); s.conf, s.dcap = conf, dcap; s.ply = 0; s.free = 0
    def pick(s, b, rnd): s.ply = 0; return super().pick(b, rnd)
    def val(s, node, b, turn, want, p, hist, snap, cache):
        s.visited += 1
        legal_ = [c for c in ORDER if b[c][ROWS - 1] == 0]
        if not legal_: return 0.0
        if want <= 0 or p < s.theta:
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
                    ch = node.kids.get(c) or node.kids.setdefault(c, L2.Node()); sn = list(snap); sn[0] = c
                    s.ply += 1; v = s.val(ch, b, 2, want - 1, p, (hist + (tuple(sn),))[-5:], sn, cache); s.ply -= 1
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
                ch = node.kids.get(c) or node.kids.setdefault(c, L2.Node()); sn = list(snap); sn[1] = c
                free = pc >= s.conf and s.ply < s.dcap
                s.ply += 1; v = s.val(ch, b, 1, want + (1 if free else 0) - 1 + 0, p * pc, (hist + (tuple(sn),))[-5:], sn, cache); s.ply -= 1
                if free: s.free += 1
            b[c][r] = 0; tot += pc * v
        return tot
def run(opp, games, seed, **kw):
    rnd = random.Random(seed); pl = Planner3(**kw); res = [L1.game(pl, opp, rnd) for _ in range(games)]
    return res, pl
VARIANTS = [("fixed depth 6 (as v1)", dict(dmax=6, conf=2.0)), ("fixed depth 4", dict(dmax=4, conf=2.0)), ("depth 4 + free plies at conf .8", dict(dmax=4, conf=0.8)),
            ("depth 4 + free plies at conf .6", dict(dmax=4, conf=0.6)), ("depth 6 + free plies at conf .8", dict(dmax=6, conf=0.8))]
def main(games=30, seeds=1):
    h = games // 2
    for oname, opp in (("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))):
        print("\n%s: layer 3 prediction, theta .04; online [win / draw / loss] games 1-%d and %d-%d, %d seed(s); positions created per move" % (oname, h, h + 1, games, seeds))
        for name, kw in VARIANTS:
            rs = [run(opp, games, sd, **kw) for sd in range(seeds)]
            def sh(a, bb): n = len(rs) * (bb - a); return [sum(sum(1 for x in r[0][a:bb] if x == k) for r in rs) / n for k in (1, 0, 2)]
            f, l = sh(0, h), sh(h, games); mv = sum(r[1].moves for r in rs)
            print("%-34s %.2f / %.2f / %.2f   %.2f / %.2f / %.2f   created %6.0f   free plies %5.1f per move" % (name, f[0], f[1], f[2], l[0], l[1], l[2], sum(r[1].created for r in rs) / mv, sum(r[1].free for r in rs) / mv), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
