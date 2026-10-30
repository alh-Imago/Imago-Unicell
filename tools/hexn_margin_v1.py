"""Hex-N layer 1 ANSWER RULE: margin readout, PYTHON MODEL ONLY (new file, 30 Oct 2026; no RTL, nothing on a card).
Alan, 30 Oct 22:21: after the baseline (22:14) showed the counted detector below a nearest-template classifier, try answering by the
detector's MARGIN (total minus threshold) instead of 'unique highest burst of detectors that fired'. Only the answer rule changes: the
weights and thresholds are exactly those of the counted detector (tools/hexn_ring_v1.py, AW 7). Same data as tools/hexn_baseline_v1.py.
Rules (a tie or silence counts WRONG unless the rule always answers):
  A strict   the recorded rule: unique highest burst among detectors that fired (burst = 1 + min(6, margin)); silent or tied = no answer
  B lowest   highest burst among those that fired, a tie goes to the lowest-numbered detector (a CHOOSE chain); silent = no answer
  C cap6     signed margin total-thr clamped to -6..+6 (needs the cell to report a margin below the threshold), always answers, ties to lowest
  D full     signed margin unclamped, always answers, ties to lowest
  E cap6n    as C but 'none' if nobody reached the threshold (best margin below 0)
  T tmpl     nearest template (from tools/hexn_baseline_v1.py; a tie counts wrong), for reference
  T2 tmpl-low  the same nearest template with ties to the lowest-numbered class (the SAME tie rule as B..E, the fair comparison)"""
import argparse, importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("bl", os.path.join(ROOT, "tools", "hexn_baseline_v1.py")); B = importlib.util.module_from_spec(sp); sp.loader.exec_module(B)
R = B.R; import random

def first_max(v): return v.index(max(v))
def rules(m, x, K):
    tt = [R.tot(m["w"][k], x, m["cap"]) for k in range(K)]; mg = [tt[k] - m["thr"][k] for k in range(K)]
    fired = [tt[k] > 0 and tt[k] >= m["thr"][k] for k in range(K)]
    g = [R.burst(tt[k], m["thr"][k]) for k in range(K)]; out = {"A": R.answer(g)}
    out["B"] = first_max(g) if max(g) > 0 else -1
    c6 = [max(-6, min(6, v)) for v in mg]; out["C"] = first_max(c6); out["D"] = first_max(mg)
    out["E"] = first_max(c6) if max(c6) >= 0 else -1
    return out

def one(seed, K, nb, q, S, per_test=100):
    rnd = random.Random(seed); tpl = R.templates(rnd, K, nb, 4)
    tr = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(S)]; random.Random(seed + 5).shuffle(tr)
    te = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(per_test)]
    m = R.train_bank([x for x, _ in tr], [c for _, c in tr], K, R.AW, S); acc = {k: 0 for k in "ABCDE"}; ans = {k: 0 for k in "ABCDE"}
    for x, c in te:
        o = rules(m, x, K)
        for k in acc: acc[k] += (o[k] == c); ans[k] += (o[k] >= 0)
    r = {k: acc[k] / len(te) for k in acc}; r.update({k + "cov": ans[k] / len(te) for k in ans}); r["T"] = B.one(seed, K, nb, q, S)["tmpl"]
    mean = [[sum(x[j] for x, c in tr if c == k) / S for j in range(nb)] for k in range(K)]; tm = [[1 if v >= 0.5 else 0 for v in row] for row in mean]
    r["T2"] = sum(min(range(K), key=lambda k: sum(a != b for a, b in zip(x, tm[k]))) == c for x, c in te) / len(te)
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); ap.add_argument("--capdiag", action="store_true", help="margin rule C against counter saturation CAP 31 / 127 / 1023 (the board trainer uses 31)"); a = ap.parse_args()
    if a.capdiag:
        for K, nb, q, S in ((4, 12, .15, 16), (8, 18, .15, 16), (16, 18, .15, 16), (16, 18, .25, 16), (8, 18, .15, 4)):
            row = []
            for cap in (31, 127, 1023):
                R.CAP = cap; rs = [one(s, K, nb, q, S) for s in range(a.seeds)]; row.append(f"CAP {cap}: C {st.mean(r['C'] for r in rs):.3f}")
            R.CAP = 31; print(f"K={K} wires={nb} noise={q} S={S}: " + " | ".join(row) + f" | template T2 {st.mean(r['T2'] for r in rs):.3f}")
        raise SystemExit
    print(f"{a.seeds} seeds; accuracy (silence/tie counts wrong where the rule can give none); coverage of E in brackets")
    print("K  wires noise S |   A strict | B lowest  | C cap6    | D full    | E cap6n (cov) | T tmpl | T2 tmpl-low")
    for K, nb in ((4, 12), (8, 18), (16, 18)):
        for q in (0.15, 0.25):
            for S in (16, 4, 2):
                rs = [one(s, K, nb, q, S) for s in range(a.seeds)]; mu = lambda k: st.mean(r[k] for r in rs)
                print(f"{K:<2d} {nb:<5d} {q:<5} {S:<2d} | {mu('A'):.3f}      | {mu('B'):.3f}     | {mu('C'):.3f}     | {mu('D'):.3f}     | {mu('E'):.3f} ({mu('Ecov'):.2f})  | {mu('T'):.3f}  | {mu('T2'):.3f}", flush=True)
