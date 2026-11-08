"""hexn_sensor_profiles_v1 (8 Nov 2026; Alan 01:27: per-sensor cleaning is important, it is part of the judge's design: match data to known sensor types and load the appropriate design for the input; for unknown sensors, try the options as part of the choice).
Host-side, Python model only. A sensor PROFILE says how that sensor's class stream is cleaned before the judge sees it. Cleaner specs: 'none'; 'carryK' (where the bank gives no class, repeat the last class if seen at most K steps ago; a given class is never altered); 'holdN' (the built layer 1 hold counter, `hold_ref`: the held class stays until a different value, or no class, has been seen N steps in a row).
KNOWN TYPES (from the 27 Oct recordings, tools/hexn_replay_carry_v1.py, direction doc section 21): light none, pot none, thermistor hold20 (186 output changes down to 3), ir (exact-match bank, damaged frames answer 'unknown') carry1 (taken from the 27 Oct layer 2 finding that a hold of 1 ignoring unknown answers worked best; NOT re-run here).
UNKNOWN SENSOR: `choose_blind` (no teacher; a rule PROPOSED here and tested only on the streams below) or `choose_taught` (known answers: best held-out accuracy, ties to fewer changes, then to the lighter cleaner).
Blind rule: (1) if at least 1 percent of steps have no class, start with carry3, else none; (2) a hold N is ALLOWED only if at least half of the steps (of the stream before the hold) lie in runs of at least 10 x N steps (the delay of N steps then costs at most a tenth of a run; this stops the rule from 'removing chatter' by deleting real changes on a stream whose classes last only a few steps). Measured on the streams here: synthetic 6 to 12 step streams 0.00 at every N; real light 1.00, pot 0.95 to 1.00, thermistor 0.76 to 0.98 (raw, N=20, is the lowest). A clean separation, but only these streams, and the half is a guess; (3) among allowed N in (3, 10, 20): if the largest allowed N removes at least half of the output changes, use the smallest allowed N whose changes are within 1.5 times those at the largest, else no hold. Two earlier versions were wrong and are why (2) exists: without it the rule chose carry3+hold10 or hold20 on the 6 to 12 step synthetic streams, where section 18 showed holds hurt; a version that measured run lengths AFTER the hold still chose hold20 on 400-word synthetic streams (a hold that never lets the class change makes long runs).
Limits: the 1 percent, one half and 1.5 are guesses chosen with these streams in view, not tuned or independently tested; the rule sees only the class stream, not the sensor's physics."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_replay_carry_v1 as C

KNOWN = {"light": "none", "pot": "none", "thermistor": "hold20", "ir": "carry1"}
HOLDS = (3, 10, 20)


def parse(spec):
    if spec == "none": return ("none", 0)
    for kind in ("carry", "hold"):
        if spec.startswith(kind) and spec[len(kind):].isdigit() and int(spec[len(kind):]) > 0: return (kind, int(spec[len(kind):]))
    raise ValueError("cleaner spec must be none, carryK or holdN (K, N > 0): %r" % spec)


def clean(stream, spec):
    kind, n = parse(spec)
    return stream if kind == "none" else C.carry1(stream, n) if kind == "carry" else C.hold1(stream, n)


def changes(s): return sum(s[i] != s[i - 1] for i in range(1, len(s)))


def long_run_share(s, minlen):
    """share of the steps that lie in runs (same value in a row) of at least minlen steps"""
    tot = i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]: j += 1
        if j - i >= minlen: tot += j - i
        i = j
    return tot / len(s)


def choose_blind(stream):
    """-> (spec, reasons)"""
    nonef = sum(c < 0 for c in stream) / len(stream); first = "carry3" if nonef >= 0.01 else "none"; s = clean(stream, first)
    base = changes(s); held = {n: clean(s, "hold%d" % n) for n in HOLDS}; ch = {n: changes(held[n]) for n in HOLDS}
    ok = [n for n in HOLDS if long_run_share(s, 10 * n) >= 0.5]; why = dict(no_class_share=nonef, changes_before_hold=base, changes_with_hold=ch, allowed_holds=ok)
    if base == 0 or not ok or ch[max(ok)] > 0.5 * base: return first, why
    n = min(n for n in ok if ch[n] <= 1.5 * ch[max(ok)]); spec = "hold%d" % n if first == "none" else first + "+hold%d" % n
    return spec, why


def clean_chain(stream, spec):
    """a spec may chain two cleaners with '+', carry first: 'carry3+hold10'"""
    for part in spec.split("+"): stream = clean(stream, part)
    return stream


def choose_taught(stream, ref, ntrain, candidates=("none", "carry3", "hold3", "hold10", "hold20")):
    best = None
    for k, spec in enumerate(candidates):
        r, nn, ch, run = C.score(clean_chain(stream, spec), ref, ntrain); key = (-round(r, 6), ch, k)
        if best is None or key < best[0]: best = (key, spec, r, ch)
    return best[1], dict(right=best[2], changes=best[3])


def clean_columns(rows, specs):
    """rows[t][sensor] -> same shape, each sensor column cleaned by its own spec (specs: one per sensor, or one string for all)"""
    ns = len(rows[0]); specs = [specs] * ns if isinstance(specs, str) else list(specs); assert len(specs) == ns
    cols = [clean_chain([r[s] for r in rows], specs[s]) for s in range(ns)]
    return [[cols[s][t] for s in range(ns)] for t in range(len(rows))]
