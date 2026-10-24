"""Two stages: the trained detector bank cleans, a store-and-learn memory works on its tokens. Python model only; stage 1 is the board-verified bank model (tools/hexn_bank_model_v2.py), stage 2 is a Python stand-in; nothing here has run on a board.
World: two sensors, each seen through its OWN trained 7-class detector bank (18 wires, test noise q per wire). An event is a pair (a, b) of true classes, chosen uniformly from the 49 pairs; its OUTCOME (one of 8 values) comes from a fixed random table over the pairs (NO sharing between pairs, so nothing can be guessed: it must be learned). After each event the true outcome arrives (ASSUMED always) and stage 2 stores the key with the true outcome when it did not answer or answered wrongly (store on miss or wrong, as hexn_learn_v1.py). No leap from a family: classes are distinct templates (at least 4 wires apart), so this tests cleaning, learning speed and size, NOT generalisation.
Token forms for stage 2 (the same event stream for all):
 T1 = the two winner ids (a stage-1 tie or silence on either sensor = no answer): an exact table.
 T2 = winner ids plus a confidence band per sensor (top count minus second count >= 3 or not): an exact table with 4 times the keys.
 T3 = the two vectors of 7 burst counts (0 to 7 each, 14 numbers): nearest stored vector by sum of absolute differences, accepted at 8 or less.
 B0 (reference, NO stage 1) = the raw 36 noisy wires of both sensors: nearest stored pattern by Hamming distance, accepted at 12 or less (about a third of the wires).
The acceptance limits are fixed once and not tuned per noise level. Sizes are counted bits of what is stored. Reported per window of 500 events (8 windows): correct, wrong, no answer, as shares of events. Usage: python3 tools/hexn_twostage_v1.py [SEEDS]"""
import sys, random, numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hexn_bank_model_v2 as B
K, NB, AW, O, N, WIN = 7, 18, 7, 8, 4000, 500
def band(g):
    s = sorted(g, reverse=True); return 1 if s[0] - s[1] >= 3 else 0
def run(seed, q):
    rnd = random.Random(seed); mA = B.make(seed, K, NB, AW, 16, 0.15, 50, 4); mB = B.make(seed + 10, K, NB, AW, 16, 0.15, 50, 4)
    table = [[rnd.randrange(O) for _ in range(K)] for _ in range(K)]
    t1, t2, v3, o3, raw, oraw = {}, {}, [], [], [], []
    names = ("T1", "T2", "T3", "B0"); win = {n: [[0, 0, 0] for _ in range(N // WIN)] for n in names}; tok_ok = 0; tok_tie = 0
    for k in range(N):
        a, b = rnd.randrange(K), rnd.randrange(K); truth = table[a][b]; w = k // WIN
        ba, bb = B.sample(rnd, mA["tpl"][a], q), B.sample(rnd, mB["tpl"][b], q)
        (pa, ga), = B.classify(mA, [(ba, a)]); (pb, gb), = B.classify(mB, [(bb, b)])
        tok_ok += (pa == a and pb == b); tok_tie += (pa < 0 or pb < 0)
        ans = {}
        key1 = (pa, pb) if pa >= 0 and pb >= 0 else None; ans["T1"] = t1.get(key1) if key1 else None
        key2 = (pa, pb, band(ga), band(gb)) if key1 else None; ans["T2"] = t2.get(key2) if key2 else None
        vec = np.array(ga + gb)
        if v3:
            d = np.abs(np.array(v3) - vec).sum(1); j = int(d.argmin()); ans["T3"] = o3[j] if d[j] <= 8 else None
        else: ans["T3"] = None
        rv = np.array(ba + bb, dtype=np.uint8)
        if raw:
            d = (np.array(raw) != rv).sum(1); j = int(d.argmin()); ans["B0"] = oraw[j] if d[j] <= 12 else None
        else: ans["B0"] = None
        for n in names:
            r = win[n][w]; r[0] += ans[n] == truth; r[1] += ans[n] is not None and ans[n] != truth; r[2] += ans[n] is None
        if key1 and t1.get(key1) != truth: t1[key1] = truth
        if key2 and t2.get(key2) != truth: t2[key2] = truth
        if ans["T3"] != truth: v3.append(vec.tolist()); o3.append(truth)
        if ans["B0"] != truth: raw.append(rv.tolist()); oraw.append(truth)
    bits = dict(T1=len(t1) * 9, T2=len(t2) * 11, T3=len(v3) * 45, B0=len(raw) * 39); ent = dict(T1=len(t1), T2=len(t2), T3=len(v3), B0=len(raw))
    return win, bits, ent, tok_ok / N, tok_tie / N
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"7 classes x 2 sensors, 49 pairs, 8 outcomes (no sharing), {N} events, {seeds} seeds. Cells: correct/wrong/no answer, as shares of events in that window")
    for q in (0.05, 0.15, 0.25):
        rs = [run(s, q) for s in range(seeds)]
        print(f"\nnoise {q}: stage 1 gets BOTH classes right in {np.mean([r[3] for r in rs]):.3f} of events, a tie or silence on either in {np.mean([r[4] for r in rs]):.3f}")
        print("form | entries | bits stored | window 1 | window 2 | window 4 | window 8")
        for n in ("T1", "T2", "T3", "B0"):
            cells = [" | ".join("%.2f/%.2f/%.2f" % tuple(np.mean([r[0][n][w][j] / WIN for r in rs]) for j in range(3)) for w in (0, 1, 3, 7))]
            print(f"{n:<4} | {np.mean([r[2][n] for r in rs]):7.0f} | {np.mean([r[1][n] for r in rs]):9.0f} | {cells[0]}")
