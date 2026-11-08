"""hexn_trychatter_v1 (8 Nov 2026; Alan 16:43: yes, build the stream where a hold is the right answer, from the real thermistor). Simulation, host side, single sensor streams.
Question: when the right cleaner is a hold (edge chatter between valid classes, the real thermistor), does a blind try-both pick it? Candidates are cleaners only here (the bank is already trained; no judge in this test): none, carry3, hold3, hold10, hold20, carry3+hold10, carry3+hold20. Streams: the real light, pot and thermistor (raw and median) class streams from the 27 Oct recordings (tools/hexn_replay_carry_v1.collect), and one synthetic sensor (classes last 6 to 12 steps; noise 0.10, 0.20, 0.30; 400 words).
Two blind scores, neither uses the reference:
  AGREE  share of steps where the cleaned class at t equals the raw detected class at t+1 (raw 'no class' skipped): the score of try_cleaners_v1 carried over to one sensor.
  COST(c) c x (output changes of the cleaned stream) + (steps where the cleaned class differs from a raw class that was given): a description-length style cost, the cleaned stream should explain the raw one with few changes. Lowest cost wins. c is the price of one change in mistakes; c = 1, 3, 10 are shown, none was tuned.
GUARD+COST  the cost with c = 10, among only those cleaners whose hold (if any) passes the run-length condition of hexn_sensor_profiles_v1 (at least half the steps, measured before the hold, lie in runs of at least 10 x N steps). Added AFTER seeing that cost alone fails: see the results.
Truth (only to check): share of steps where the cleaned class equals the reference ('no class' counts as wrong).
Usage: python3 tools/hexn_trychatter_v1.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_sensor_profiles_v1 as P, hexn_replay_carry_v1 as C, hexn_bank_model_v2 as M, hexn_kxlayer1_judge_v1 as J

CANDS = ("none", "carry3", "hold3", "hold10", "hold20", "carry3+hold10", "carry3+hold20")


def agree(cl, raw):
    ts = [t for t in range(len(raw) - 1) if raw[t + 1] >= 0]; return sum(cl[t] == raw[t + 1] for t in ts) / len(ts)


def cost(cl, raw, c): return c * P.changes(cl) + sum(1 for a, b in zip(cl, raw) if b >= 0 and a != b)


def truth(cl, ref, start=0): return sum(cl[i] == ref[i] for i in range(start, len(ref))) / (len(ref) - start)


def streams():
    out = [(n, o, r, nt) for n, o, r, nt in C.collect()]
    for nz in (0.10, 0.20, 0.30):
        m, samples, W, bias = J.make_data(1, 400, noise=nz, dwell=6); cl = [c for c, _ in M.classify(m, [row[0] for row in samples])]
        out.append(("synthetic noise %.2f" % nz, cl, [row[0][1] for row in samples], 0))
    return out


def allowed(raw, cnd):
    parts = cnd.split("+"); hold = [int(x[4:]) for x in parts if x.startswith("hold")]
    if not hold: return True
    base = P.clean_chain(raw, "+".join(x for x in parts if not x.startswith("hold")) or "none"); return P.long_run_share(base, 10 * hold[0]) >= 0.5


def evaluate(name, raw, ref, nt, cands=CANDS):
    res = {}
    for cnd in cands:
        cl = P.clean_chain(raw, cnd); res[cnd] = dict(truth=truth(cl, ref, nt), agree=agree(cl, raw), cost={c: cost(cl, raw, c) for c in (1, 3, 10)}, changes=P.changes(cl))
    pick = dict(truth=max(cands, key=lambda k: res[k]["truth"]), agree=max(cands, key=lambda k: res[k]["agree"]))
    for c in (1, 3, 10): pick["cost%d" % c] = min(cands, key=lambda k: res[k]["cost"][c])
    pick["guard"] = min([k for k in cands if allowed(raw, k)], key=lambda k: res[k]["cost"][10])
    return res, pick


def main():
    for name, raw, ref, nt in streams():
        res, pick = evaluate(name, raw, ref, nt)
        print("\n%s (%d steps, raw changes %d)" % (name, len(raw), P.changes(raw)))
        print("  %-14s %6s %6s %8s %8s %8s %8s" % ("cleaner", "truth", "agree", "cost c=1", "cost c=3", "cost c=10", "changes"))
        for k, v in res.items(): print("  %-14s %6.3f %6.3f %8d %8d %9d %8d" % (k, v["truth"], v["agree"], v["cost"][1], v["cost"][3], v["cost"][10], v["changes"]))
        print("  picks: best by truth %s | AGREE %s | COST c=1 %s | c=3 %s | c=10 %s | GUARD+c=10 %s" % (pick["truth"], pick["agree"], pick["cost1"], pick["cost3"], pick["cost10"], pick["guard"]))


if __name__ == "__main__": main()
