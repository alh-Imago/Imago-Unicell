"""hexn_layer1_v2: layer-1 IR detector bank in DIRECT / EXACT-MATCH mode (Alan, 27 Oct 2026: layer 1 is a detector system, so it needs a direct/exact-match mode; layer 2 only receives clean codes). Python model only, no RTL: weights are wired straight from each key's code (+1 for a 1-bit, -1 for a 0-bit, 0 unused), threshold = number of ones minus slack (at least 1), written by the host through the existing loader (LOADDET 0x13). New file; uses hexn_layer1_v1 and hexn_exact_v1 unchanged.
Tests: (1) every code decoded from the real recording (data frames + repeats) classified; (2) random 1-bit and 2-bit flips of the real codes: right / unknown / wrong; midpoint rule shown for comparison.
Usage: python3 tools/hexn_layer1_v2.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer1_v1 as L, hexn_exact_v1 as X, hexn_tang_script_v1 as S1
def run(rule):
    m = X.model(rule); seen = [c for c in L.ir_keys(True)]; idx = {c: i for i, c in enumerate(X.TABLE)}
    real = sum(X.answer(m, c)[0] == idx[c] for c in seen if c in idx); n = sum(c in idx for c in seen); r = random.Random(3); out = [rule, "%d/%d" % (real, n)]
    valid = set(X.TABLE)
    for nf in (1, 2):
        right = unk = wrong = amb = tot = 0
        for c in seen:
            if c not in idx: continue
            bs = r.sample(range(8), nf); f = c
            for b in bs: f ^= 1 << b
            if f in valid: continue
            tot += 1; k, mx = X.answer(m, f)
            if mx == 0: unk += 1
            elif k == -1: amb += 1
            elif k == idx[c]: right += 1
            else: wrong += 1
        out.append("%d flips: right %d unknown %d ambiguous %d WRONG %d (of %d)" % (nf, right, unk, amb, wrong, tot))
    return out
def main():
    print("rule | real recorded codes right | single-bit flips | two-bit flips (flips onto another valid key left out: no redundancy to catch them)")
    for rule in ("midpoint", "exact", "direct0", "direct1"): print(" | ".join(run(rule)))
if __name__ == "__main__": main()
