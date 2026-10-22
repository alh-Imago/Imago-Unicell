"""Hex-N built-in self-test (BIST) training sets: deterministic training sets for K detectors x NB wires, 16 samples per class, chosen so that the battery as a whole reaches the arithmetic edge cases that went wrong on the board
(counters exactly at the weight cutoff T and one either side, counters at the +-31 saturation, threshold sums that land exactly on a rounding tie, both parities). make_set(K, NB, AW, cfg) -> script-style dict; coverage(K, NB, AW, sets) -> dict of counts.
Used by tools/hexn_tang_bist_v1.py; run this file to search for configurations: python3 tools/hexn_bist_sets_v1.py K NB AW"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1
def make_set(K, NB, AW, cfg, spc=16):
    seed, dens, noise, T = cfg; r = random.Random(seed)
    tpl = [[1 if r.random() < dens else 0 for _ in range(NB)] for _ in range(K)]
    tr = [([b ^ (1 if r.random() < noise else 0) for b in tpl[y]], y) for y in range(K) for _ in range(spc)]; r.shuffle(tr)
    te = [([b ^ (1 if r.random() < 0.1 else 0) for b in tpl[y]], y) for y in range(K) for _ in range(4)]; r.shuffle(te)
    return dict(wires=NB, classes=K, spc=spc, T=T, aw=AW, labels=[str(i) for i in range(K)], train=tr, test=te)
def coverage(K, NB, AW, sets, hw_s=16):
    c = dict(at_T=0, below_T=0, at_negT=0, above_negT=0, sat_pos=0, sat_neg=0, tie_even=0, tie_odd=0, thr_zero=0, thr_max=0, fwd_sat=0)
    for d in sets:
        m = S1.make_model(d, hw_s); T = d["T"]
        for row in m["cnt"]:
            for v in row:
                c["at_T"] += v == T; c["below_T"] += v == T - 1; c["at_negT"] += v == -T; c["above_negT"] += v == -T + 1; c["sat_pos"] += v == 31; c["sat_neg"] += v == -31
        nP, nN = hw_s, hw_s * (K - 1)
        for k in range(K):
            num = m["sump"][k] * nN + m["sumn"][k] * nP; den = 2 * nP * nN; q, rr = divmod(num, den)
            if 2 * rr == den: c["tie_even" if q % 2 == 0 else "tie_odd"] += 1
            c["thr_zero"] += m["thr"][k] == 0; c["thr_max"] += m["thr"][k] == (1 << AW) - 1
            c["fwd_sat"] += any(S1.fwd_of(S1.net_of(m["wts"][k], b), AW) == (1 << AW) - 1 for b, y in d["train"])
    return c
if __name__ == "__main__":
    K, NB, AW = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]); found = []
    for seed in range(1, 400):
        for dens in (0.3, 0.5, 0.7):
            for noise in (0.05, 0.2, 0.35):
                for T in (8, 3, 13):
                    cfg = (seed, dens, noise, T); c = coverage(K, NB, AW, [make_set(K, NB, AW, cfg)])
                    if c["tie_even"] or c["tie_odd"]: print(cfg, c)
