"""hexn_connect4_cand_v1: DOES GIVING THE PLANNER'S LAYER 3 LAYER 2's REFINEMENTS HELP AGAINST AN OPPONENT WITH RANDOM MOVES (Python only; no RTL, nothing on a card).
Alan, 30 Oct 2026, 14:20. Background: stale_v3 (30 Oct) found that layer 4 with NO learned opponent model beat layer 4 with the live layer 3 (0.98 against 0.71 to 0.74 wins) against lookahead(2) + 20% random moves.
Variants of layer 4's opponent model (same Planner3, depth 4, free plies at conf .8, theta .04, tactics prior):
 base   - the plain layer 3 (as before)
 cand   - tools/hexn_layer3_cand_v1.py: candidate stage (N=2 sightings in W=400 moments) and contradicted counts
 blend  - the plain layer 3, then LAM of the reply mixed with a flat spread over the legal columns (before the tactics prior); the 12:10 idea, not a layer 2 feature
 cblend - cand and blend together
 empty  - no learned model at all (the stale_v3 control)
Usage: python3 tools/hexn_connect4_cand_v1.py VARIANT [LAM] [GAMES] [SEEDS]. Measured: online [win / draw / loss] of X over games 1-50 and 51-100 (for GAMES=100), summed over SEEDS seeds, against lookahead(2) + 20% random moves. Limits: planner only, one opponent and noise level, nothing tuned."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_layer4_v3 as L3P, hexn_layer3_v1 as V1, hexn_layer3_cand_v1 as CD, hexn_connect4_stale_v2 as S2
class P(L3P.Planner3):
    def __init__(s, variant, lam=0.0, **kw):
        super().__init__(**kw); s.variant, s.lam = variant, lam
        if variant in ("cand", "cblend"): s.m = CD.Layer3C(nch=2, L=5, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)])
    def odist(s, b, hist, snap, legal_, cache):
        n = len(legal_); base = {c: 1.0 / n for c in legal_}
        if s.variant != "empty":
            v = L1.l3_cols(s.m, hist, snap, cache); tot = 0.0; d = {c: 0.0 for c in legal_}
            for c, w in v.items():
                if c in d: d[c] += w; tot += w
            rem = max(0.0, 1.0 - tot); base = {c: d[c] + rem / n for c in legal_}
            if s.lam > 0: base = {c: (1 - s.lam) * base[c] + s.lam / n for c in legal_}
        if s.tactics:
            f = L1.can_win(b, 2) or L1.can_win(b, 1); f = [c for c in f if c in legal_]
            if f: base = {c: 0.2 * base[c] + (0.8 / len(f) if c in f else 0.0) for c in legal_}
        return base
def run(variant, lam, games, seed):
    rnd = random.Random(seed); opp = S2.noisy(C.make_lookahead(2), 0.2)
    pl = P(variant, lam, mode="tree3", theta=0.04, tactics=True, dmax=4, conf=0.8)
    return [L1.game(pl, opp, rnd) for _ in range(games)]
def main(variant="base", lam=0.0, games=100, seeds=6):
    h = games // 2; rs = [run(variant, lam, games, sd) for sd in range(seeds)]
    def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
    f, l = sh(0, h), sh(h, games)
    print("%-8s lam %.2f  %.2f / %.2f / %.2f    %.2f / %.2f / %.2f" % (variant, lam, f[0], f[1], f[2], l[0], l[1], l[2]), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; main(a[0] if a else "base", float(a[1]) if len(a) > 1 else 0.0, int(a[2]) if len(a) > 2 else 100, int(a[3]) if len(a) > 3 else 6)
