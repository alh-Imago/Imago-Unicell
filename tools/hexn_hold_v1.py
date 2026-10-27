"""hexn_hold_v1: HOLD-N-SAMPLES rule on the layer-1 output, tested on the replayed recordings (Python model only; no RTL; new file; reuses the banks of hexn_replay_v1 unchanged, by capturing what its report() receives).
Rule: the output keeps its last stable answer; it changes to a new answer only after that answer has been the bank's output for N samples in a row (N = 1 is no hold). An answer of -1 (no answer/tie) counts as an answer like any other here.
Reported per stream and N: output changes (the reference makes the number shown), share right on the held-out part, longest wrong run (samples and seconds at 200 per second; the light stream is pair-averaged, 100 per second, so its seconds are doubled in this table's count only if noted), and the delay to follow a real change = the mean number of samples from each reference change to the first correct output.
Limits: same as hexn_replay_v1 (separate recordings, hand-made band edges, thermistor reference = centred-median band); the hold is a host-side rule here, not hardware.
Usage: python3 tools/hexn_hold_v1.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_replay_v1 as R, hexn_tang_script_v1 as S1
CAP = []
R.report = lambda name, bits, ref, ntrain, m, note="": CAP.append((name, [S1.classify(m, b)[0] for b in bits], ref, ntrain))
def hold(out, n):
    cur = out[0]; cand = None; cnt = 0; res = [cur]
    for x in out[1:]:
        if x == cur: cand = None; cnt = 0
        elif x == cand: cnt += 1
        else: cand = x; cnt = 1
        if cand is not None and cnt >= n: cur = cand; cand = None; cnt = 0
        res.append(cur)
    return res
def delay(out, ref):
    ds = []
    for i in range(1, len(ref)):
        if ref[i] != ref[i - 1]:
            j = i
            while j < len(ref) and ref[j] == ref[i] and out[j] != ref[i]: j += 1
            ds.append(j - i)
    return sum(ds) / len(ds) if ds else 0
def main():
    R.light(); R.pot(); R.therm()
    print("name       | N  | output changes (reference) | right (held-out) | longest wrong run (samples) | mean delay after a real change (samples)")
    for name, out, ref, nt in CAP:
        rc = sum(ref[i] != ref[i - 1] for i in range(1, len(ref)))
        for n in (1, 3, 5, 10, 20, 40):
            o = hold(out, n); h = range(nt, len(o)); run = best = 0
            for i in h:
                run = run + 1 if o[i] != ref[i] else 0; best = max(best, run)
            print("%-10s | %2d | %4d (%d) | %.3f | %3d | %.1f" % (name, n, sum(o[i] != o[i - 1] for i in range(1, len(o))), rc, sum(o[i] == ref[i] for i in h) / len(h), best, delay(o, ref)))
if __name__ == "__main__": main()
