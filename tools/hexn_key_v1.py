"""hexn_key_v1: the QUICK KEY of an engram, measured at the DETECTOR BANK (Python model of the bank, board-verified rules of hexn_tang_script_v1; no RTL; new file). Design: docs/hex-n/CARD_SLICE_v1.md, test-ladder step 4.
E engrams = E stored sets of detector settings (the script's training data with the class labels shifted by s = 0..E-1, so every set maps the same patterns to different detectors; ASSUMPTION: this is how contexts differ here, a hand-made choice).
Key of a bank = for each of P fixed probe patterns, which detectors fire (output burst count > 0): P x K bits. The key of an engram is stored with its settings (computed from clean probes, no damage).
Recall test: the bank's settings are DAMAGED (n_d random lane settings or thresholds changed), the probes are shown with noise q (each bit flipped), the observed key is matched against the stored keys (smallest Hamming distance, a tie = no recall), and the matching engram's settings are loaded back.
Reported: how often the right engram is recalled, and the task accuracy (share of the script's test samples that the bank classifies as the engram's own label) of the damaged bank and of the bank after recall.
Probe kinds: 'random' = random 18-bit patterns; 'data' = patterns from the script's training samples (drawn once, same for all engrams).
Usage: python3 tools/hexn_key_v1.py script [E] [reps]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1
def engram_model(d, s, hw_s=16):
    K = d["classes"]; ds = dict(d); ds["train"] = [(b, (y + s) % K) for b, y in d["train"]]; ds["test"] = [(b, (y + s) % K) for b, y in d["test"]]
    return S1.make_model(ds, hw_s)
def key_of(m, probes): return [int(c > 0) for p in probes for c in S1.classify(m, p)[1]]
def accuracy(m, tests): return sum(S1.classify(m, b)[0] == y for b, y in tests) / len(tests)
def damage(m, rnd, n):
    w = [list(r) for r in m["wts"]]; thr = list(m["thr"])
    for _ in range(n):
        k = rnd.randrange(m["K"])
        if rnd.random() < 0.85: j = rnd.randrange(m["NB"]); w[k][j] = rnd.choice([v for v in (-1, 0, 1) if v != w[k][j]])
        else: thr[k] = max(0, min((1 << m["AW"]) - 1, thr[k] + rnd.choice((-3, -2, -1, 1, 2, 3))))
    d = dict(m); d["wts"] = w; d["thr"] = thr; return d
def ham(a, b): return sum(x != y for x, y in zip(a, b))
def main():
    d = S1.parse_script(open(sys.argv[1]).read()); E = int(sys.argv[2]) if len(sys.argv) > 2 else 7; reps = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    K, NB = d["classes"], d["wires"]; models = [engram_model(d, s) for s in range(E)]
    print(f"{E} engrams of {K} detectors x {NB} wires (labels shifted by s); undamaged accuracy (own label, test samples): " + " ".join(f"{accuracy(m, [(b, (y + s) % K) for b, y in d['test']]):.2f}" for s, m in enumerate(models)))
    for kind in ("random", "data"):
        for P in (6, 12, 24):
            pr = random.Random(100 + P)
            probes = [[pr.randint(0, 1) for _ in range(NB)] for _ in range(P)] if kind == "random" else [pr.choice(d["train"])[0] for _ in range(P)]
            keys = [key_of(m, probes) for m in models]; dd = [ham(keys[i], keys[j]) for i in range(E) for j in range(i)]
            print(f"\nprobes: {kind}, P = {P} ({P * K}-bit key); stored keys: pairwise Hamming min {min(dd)} mean {sum(dd) / len(dd):.1f} of {P * K}")
            print(" damage | probe noise | right engram recalled | accuracy: damaged -> after recall (undamaged)")
            for nd in (0, 6, 12, 24):
                for q in (0.0, 0.1, 0.2):
                    rnd = random.Random(7); hit = tot = 0; a_dam = a_rec = a_org = 0.0
                    for e in range(E):
                        tests = [(b, (y + e) % K) for b, y in d["test"]]
                        for r in range(reps):
                            dm = damage(models[e], rnd, nd); np_ = [[b ^ (1 if rnd.random() < q else 0) for b in p] for p in probes]; obs = key_of(dm, np_)
                            dist = [ham(obs, k) for k in keys]; best = min(dist); cand = [i for i, x in enumerate(dist) if x == best]
                            rec = cand[0] if len(cand) == 1 else -1; hit += rec == e; tot += 1
                            a_dam += accuracy(dm, tests); a_org += accuracy(models[e], tests); a_rec += accuracy(models[rec], tests) if rec >= 0 else 0.0
                    print(f"  {nd:3d}   |    {q:.1f}      |   {hit:4d} / {tot:4d}        |  {a_dam / tot:.2f} -> {a_rec / tot:.2f}  ({a_org / tot:.2f})")
main()
