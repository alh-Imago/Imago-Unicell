"""hexn_replay_carry_v1 (8 Nov 2026): carry-forward and the hold counter tried on the REAL recorded ESP32 sensor data (27 Oct recordings), through the same layer 1 banks as tools/hexn_replay_v1.py (reused unchanged: its data preparation is captured, its printing is replaced). Python model only; nothing on the card.
Per sensor stream (light, pot, thermistor raw, thermistor with the 9-sample median), the bank's class for every sample is cleaned by one rule and scored on the held-out part exactly as hexn_replay_v1 scores it: share right ('no class' counts as wrong), share with no class, output changes against the reference's changes (extra = chatter), and the longest run of wrong answers.
Rules: none; carry K (where the bank gives no class, repeat the last class if seen at most K samples ago; a given class is never altered); hold N (the built layer 1 hold counter, `hold_ref` in hexn_hold_card_v1: the held class stays until a different value, or no class, has been seen N samples in a row).
Limits: same as hexn_replay_v1 (sensors recorded separately; light = three steady files joined end to end, so no real light transitions; pot labels are bands of the knob reading itself; thermistor reference = centred-median band with hand-made edges); K and N are in SAMPLES at 200 per second (light is pair-averaged at 100 per second).
Usage: python3 tools/hexn_replay_carry_v1.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_replay_v1 as R, hexn_tang_script_v1 as S1, hexn_hold_card_v1 as HC


def carry1(out, k):
    res = []; last = None; at = -10 ** 9
    for i, c in enumerate(out):
        if c >= 0: last, at = c, i; res.append(c)
        else: res.append(last if (last is not None and i - at <= k) else -1)
    return res


def hold1(out, n): return [(-1 if c == 15 else c) for c, _ in HC.hold_ref([15 if x < 0 else x for x in out], n)]


def score(out, ref, ntrain):
    n = len(out); h = range(ntrain, n)
    right = sum(out[i] == ref[i] for i in h) / len(h); none = sum(out[i] < 0 for i in h) / len(h)
    chg = sum(out[i] != out[i - 1] for i in range(1, n)); run = best = 0
    for i in h:
        run = run + 1 if out[i] != ref[i] else 0; best = max(best, run)
    return right, none, chg, best


def collect():
    got = []
    R.report = lambda name, bits, ref, ntrain, m, note="": got.append((name, [S1.classify(m, b)[0] for b in bits], ref, ntrain))
    R.light(); R.pot(); R.therm(); return got


def main():
    rules = [("none", lambda o: o)] + [("carry %d" % k, (lambda k: lambda o: carry1(o, k))(k)) for k in (1, 3, 10, 20)] + [("hold %d" % n, (lambda n: lambda o: hold1(o, n))(n)) for n in (3, 10, 20)]
    for name, out, ref, nt in collect():
        rchg = sum(ref[i] != ref[i - 1] for i in range(1, len(ref))); print("\n%s (%d samples, held-out %d, reference changes %d)" % (name, len(out), len(out) - nt, rchg))
        print("  %-9s %6s %9s %8s %10s" % ("rule", "right", "no class", "changes", "longest wrong run"))
        for rn, f in rules:
            r, nn, c, b = score(f(out), ref, nt); print("  %-9s %6.3f %8.3f%% %8d %10d" % (rn, r, 100 * nn, c, b))


if __name__ == "__main__": main()
