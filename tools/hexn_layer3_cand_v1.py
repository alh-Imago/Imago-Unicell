"""hexn_layer3_cand_v1: LAYER 3 WITH LAYER 2's REFINEMENTS (Python only; no RTL; clone-extension of hexn_layer3_v1.py, which is untouched).
Alan, 30 Oct 2026, 14:18-14:20: layer 3 is layer 2 handling more inputs, and it works but not fully because it lacks what layer 2 has. Layer 2 (docs/hex-n/LAYER_INTERFACES_v2.md, tools/hexn_store_v2.py) has: (a) a CANDIDATE stage: a new pair only counts as known after N sightings inside a window of W events (a sighting at least W after the start restarts the count); (b) CONTRADICTED counts per stored sequence, kept beside the seen count, as the confidence.
What is added here to Layer3 (v1): (a) a follower entry (context level, mask, context, moment) is KNOWN only after N sightings inside W moments; until then it is a candidate and `predict` ignores it. (b) when a context is matched and its best KNOWN follower is not what comes next, that follower's contradicted count goes up (same half-life as the weights); `predict` multiplies each known follower's weight by seen/(seen+contradicted). The PPM-C escape structure of v1 is kept. Defaults N=2, W=400 as in the layer 2 store runs.
Limits: a first reading of the layer 2 rules, not a copy of the layer 2 store; moments here are single plies in the Connect Four use; nothing tuned."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1
class Layer3C(V1.Layer3):
    def __init__(s, *a, N=2, W=400, **k):
        super().__init__(*a, **k); s.N, s.W = N, W; s.cand = {}; s.known = set(); s.contra = {}
    def _best_known(s, j, m, c):
        d = s.tab.get((j, m, c))
        if not d: return None
        best, bw = None, 0.0
        for k, e in d.items():
            if (j, m, c, k) in s.known:
                w = s._w(e)
                if w > bw: best, bw = k, w
        return best
    def _close(s):
        ch = tuple(sorted(s.pend.items()))
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            b = s._best_known(j, m, c)
            if b is not None and b != ch:
                e = s.contra.get((j, m, c, b), (0.0, s.n)); s.contra[(j, m, c, b)] = (s._w(e) + 1.0, s.n)
            key = (j, m, c, ch)
            if key not in s.known:
                cnt, start = s.cand.get(key, (0, s.n))
                if s.n - start >= s.W: cnt, start = 0, s.n
                cnt += 1
                if cnt >= s.N: s.known.add(key); s.cand.pop(key, None)
                else: s.cand[key] = (cnt, start)
        return super()._close()
    def predict(s, top=8):
        p = {}; rem = 1.0
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None or None in s.snap: continue
            d = s.tab.get((j, m, c))
            if not d: continue
            ws = {}
            for k, e in d.items():
                if (j, m, c, k) not in s.known: continue
                w = s._w(e); ce = s.contra.get((j, m, c, k)); cw = s._w(ce) if ce else 0.0
                ws[k] = w * w / (w + cw) if w > 0 else 0.0
            if not ws: continue
            t = sum(ws.values()); dn = len(ws)
            for k, w in ws.items(): p[k] = p.get(k, 0.0) + rem * w / (t + dn)
            rem *= dn / (t + dn)
        r = sorted(p.items(), key=lambda kv: -kv[1]); return r[:top], rem
