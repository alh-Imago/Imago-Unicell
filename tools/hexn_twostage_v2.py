"""(v2, a new file beside hexn_twostage_v1.py which is left untouched.) Stage 1 takes L independent looks at each sensor and SUMS each class's burst count over the looks (what the leaky cell totals do when they are carried between windows with no leak, 'keep'); the winner is the class with the unique highest total, a tie or an all-zero total = no answer. Looks are independent noisy copies (ASSUMED: noise that is the same in every look would not be cleared). Stage 2 is the winner-id exact table T1 of v1 (the form v1 chose), learned by store on miss or wrong, and the reference B0 = raw wires, here with each wire the majority of L looks (L odd; ties go to the first look), nearest stored pattern by Hamming distance accepted at 12 or less of 36. Same world as v1: two sensors, 49 pairs, 8 outcomes with no sharing, true outcome always arrives, limits fixed and not tuned. Python model only; nothing on a board. Usage: python3 tools/hexn_twostage_v2.py [SEEDS]"""
import sys, random, numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hexn_bank_model_v2 as B
K, NB, AW, O, N, WIN = 7, 18, 7, 8, 4000, 500
def winner(totals): mx = max(totals); return totals.index(mx) if mx > 0 and totals.count(mx) == 1 else -1
def run(seed, q, L):
    rnd = random.Random(seed); mA = B.make(seed, K, NB, AW, 16, 0.15, 50, 4); mB = B.make(seed + 10, K, NB, AW, 16, 0.15, 50, 4)
    table = [[rnd.randrange(O) for _ in range(K)] for _ in range(K)]
    t1, raw, oraw = {}, [], []; win = {n: [[0, 0, 0] for _ in range(N // WIN)] for n in ("T1", "B0")}; both = tie = 0
    for k in range(N):
        a, b = rnd.randrange(K), rnd.randrange(K); truth = table[a][b]; w = k // WIN
        la = [B.sample(rnd, mA["tpl"][a], q) for _ in range(L)]; lb = [B.sample(rnd, mB["tpl"][b], q) for _ in range(L)]
        ta = [sum(x) for x in zip(*[g for (_, g) in B.classify(mA, [(bits, a) for bits in la])])]; tb = [sum(x) for x in zip(*[g for (_, g) in B.classify(mB, [(bits, b) for bits in lb])])]
        pa, pb = winner(ta), winner(tb); both += (pa == a and pb == b); tie += (pa < 0 or pb < 0)
        key = (pa, pb) if pa >= 0 and pb >= 0 else None; ans = {"T1": t1.get(key) if key else None}
        cue = np.concatenate([(np.array(la).sum(0) * 2 > L).astype(np.uint8) if L > 2 else np.array(la[0], dtype=np.uint8), (np.array(lb).sum(0) * 2 > L).astype(np.uint8) if L > 2 else np.array(lb[0], dtype=np.uint8)])
        if raw: d = (np.array(raw) != cue).sum(1); j = int(d.argmin()); ans["B0"] = oraw[j] if d[j] <= 12 else None
        else: ans["B0"] = None
        for n in ans: r = win[n][w]; r[0] += ans[n] == truth; r[1] += ans[n] is not None and ans[n] != truth; r[2] += ans[n] is None
        if key and t1.get(key) != truth: t1[key] = truth
        if ans["B0"] != truth: raw.append(cue.tolist()); oraw.append(truth)
    return win, len(t1) * 9, len(raw) * 39, both / N, tie / N
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"{N} events, {seeds} seeds; last two windows (1,000 events) averaged; cells correct/wrong/no answer")
    print("noise | looks L | stage 1 both right | tie or silence | T1 correct/wrong/none | T1 right among answers | T1 bits | B0 correct/wrong/none (B0 uses L=1 cue when L is 2) | B0 bits")
    for q in (0.15, 0.25):
        for L in (1, 2, 3, 5):
            rs = [run(s, q, L) for s in range(seeds)]
            m = lambda n, j: np.mean([(r[0][n][6][j] + r[0][n][7][j]) / (2 * WIN) for r in rs])
            c, wr, no = m("T1", 0), m("T1", 1), m("T1", 2); bc, bw, bn = m("B0", 0), m("B0", 1), m("B0", 2)
            print(f"{q} | {L} | {np.mean([r[3] for r in rs]):.3f} | {np.mean([r[4] for r in rs]):.3f} | {c:.2f}/{wr:.2f}/{no:.2f} | {c / max(1e-9, c + wr):.2f} | {np.mean([r[1] for r in rs]):.0f} | {bc:.2f}/{bw:.2f}/{bn:.2f} | {np.mean([r[2] for r in rs]):.0f}")
