"""SAVE AND RECALL with partial matching, concept model (no RTL). Alan, 22 Oct: save a pattern, later 'have I seen this before, even partially', recall it, and see how well it fits or deviates.
World: OBJ objects, each a random NB-wire pattern (an INSTANCE, not a trained class). SAVE: the object is watched for WS windows, each a fresh copy with wire-flip noise qs; every wire has a small saturating up/down counter (+1 wire high, -1 wire low, clamp +-7); the sign of the counter after the last window is the stored bit (a tie stores 0). This is the temporal cleaning, a per-wire integrator, and the stored pattern goes into a slot. RECALL: a cue = the object with a share 'hide' of wires unknown and (optionally) 'chg' known-or-unknown wires changed (a modified object), watched for NC windows with noise qc, integrated the same way over the KNOWN wires only. Score of a slot = matching known wires / known wires. Best slot wins if its score >= FAM and it is the unique best.
Reported (per row, over TR tries): ID = the best slot is the object's own slot; EXACT = the stored pattern equals the original object (the saved copy was clean); DEV = mean number of known wires that differ between the integrated cue and the recalled slot (the 'deviation'), against the true number of changed known wires; NOVEL = share of never-saved random objects wrongly called familiar.
Usage: python3 tools/hexn_saverecall_model_v1.py [NB] [OBJ] [TRIES] [MARGIN]"""
import sys, random
NB = int(sys.argv[1]) if len(sys.argv) > 1 else 18; OBJ = int(sys.argv[2]) if len(sys.argv) > 2 else 8; TR = int(sys.argv[3]) if len(sys.argv) > 3 else 400
FAM = 0.75; MARGIN = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0   # MARGIN: the best slot must also beat the second best by this share of the known wires
def watch(r, obj, wires, n, q):
    c = {j: 0 for j in wires}
    for _ in range(n):
        for j in wires: c[j] = max(-7, min(7, c[j] + (1 if (obj[j] ^ (1 if r.random() < q else 0)) else -1)))
    return {j: (1 if c[j] > 0 else 0) for j in wires}
def run(WS, qs, NC, qc, hide, chg, seed):
    r = random.Random(seed); ident = exact = fam = 0; dev = tchg = 0.0; novel = 0
    objs = [[r.randrange(2) for _ in range(NB)] for _ in range(OBJ)]
    slots = [[watch(r, o, range(NB), WS, qs)[j] for j in range(NB)] for o in objs]
    for _ in range(TR):
        k = r.randrange(OBJ); o = list(objs[k]); known = [j for j in range(NB) if r.random() >= hide]
        if len(known) < 3: known = list(range(3))
        ch = r.sample(range(NB), chg) if chg else []
        for j in ch: o[j] ^= 1
        cue = watch(r, o, known, NC, qc)
        sc = [sum(cue[j] == s[j] for j in known) / len(known) for s in slots]; mx = max(sc); best = [i for i, v in enumerate(sc) if v == mx]
        srt = sorted(sc, reverse=True); ok = len(best) == 1 and mx >= FAM and (len(srt) < 2 or mx - srt[1] >= MARGIN); fam += ok; ident += ok and best[0] == k
        exact += slots[k] == objs[k]
        if ok and best[0] == k: dev += sum(cue[j] != slots[k][j] for j in known); tchg += sum(1 for j in ch if j in known)
    for _ in range(TR):
        o = [r.randrange(2) for _ in range(NB)]; known = [j for j in range(NB) if r.random() >= hide]
        if len(known) < 3: known = list(range(3))
        cue = watch(r, o, known, NC, qc); sc = [sum(cue[j] == s[j] for j in known) / len(known) for s in slots]; mx = max(sc)
        srt = sorted(sc, reverse=True); novel += mx >= FAM and sc.count(mx) == 1 and (len(srt) < 2 or mx - srt[1] >= MARGIN)
    n = max(1, ident)
    return ident / TR, exact / TR, dev / n, tchg / n, novel / TR
print("%d wires, %d objects stored, %d tries per row, familiar if best score >= %.2f" % (NB, OBJ, TR, FAM))
print("save: WS windows at noise qs | cue: NC windows, noise qc, hide share, changed wires | ID | saved copy exact | deviation found vs true changed (known wires) | NOVEL called familiar")
rows = [(1, .15, 1, .15, 0, 0), (3, .15, 1, .15, 0, 0), (8, .15, 1, .15, 0, 0), (8, .15, 3, .15, 0, 0),
        (8, .15, 1, .15, .3, 0), (8, .15, 1, .15, .5, 0), (8, .15, 3, .15, .5, 0), (1, .15, 3, .15, .5, 0),
        (8, .15, 3, .15, 0, 2), (8, .15, 3, .15, 0, 4), (8, .15, 3, .15, .3, 4), (8, .25, 3, .25, .3, 2), (3, .25, 3, .25, .3, 2)]
for i, (ws, qs, nc, qc, hide, chg) in enumerate(rows):
    idr, ex, dv, tc, nv = run(ws, qs, nc, qc, hide, chg, 100 + i)
    print("WS=%d qs=%.2f | NC=%d qc=%.2f hide=%.1f chg=%d | ID %.3f | exact %.3f | dev %.2f vs true %.2f | novel %.3f" % (ws, qs, nc, qc, hide, chg, idr, ex, dv, tc, nv))
