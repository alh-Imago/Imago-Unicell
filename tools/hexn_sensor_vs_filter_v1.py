"""hexn_sensor_vs_filter_v1: IS HEX-N WORTH FOLLOWING FURTHER AS A SENSOR FOLLOWER? A HEAD-TO-HEAD WITH CHEAP FILTERS (Python only; no RTL, nothing on a card).
Alan, 30 Oct 2026, 20:10: run the comparison and see if Hex-N is worth following further. Origin: the 20:20 row of docs/hex-n/HEXN_DESIGN.md (simple cheap solutions first; compare with a few lines on a small microcontroller).
THE TASK (the same for every contestant): one steady ADC-like reading, one number per sample. Predict the NEXT clean value, and flag outliers. Score: mean absolute error against the CLEAN value on non-spike samples (a contestant that just repeats the last noisy value scores about 2.4 to 2.5, i.e. about 0.8 x sigma; smoothing can score lower), the error in the 50 samples after each step shift, and the precision / recall of the spike flags. Scenarios (20,000 samples, 5 seeds each, noise sigma 3 counts, spikes of 50 to 150 counts with probability .003):
 drift  - slow random-walk drift
 cycle  - drift plus a repeating cycle (amplitude 80 counts, period 400 samples)
 steps  - drift plus a step shift of +-60 counts about every 3000 samples
THE SAME OUTLIER RULE for all: flag when |x - prediction| > 5 x (running estimate of the typical residual); a flagged sample is replaced by the contestant's own prediction before it is used (so a spike is not learned); but after 3 flags in a row the sample is ACCEPTED as a real shift (the first run of this file lacked this and every contestant lost a step shift for ever, which measured the test, not the contestants; those figures were discarded). Only the PREDICTOR differs.
CONTESTANTS: persist = last accepted value; ema = exponential average (alpha .2); ab = alpha-beta tracker (alpha .2, beta .02: about ten lines of code, 2 numbers of state); hexL = Hex-N history predictor (tools/hexn_layer3_v1.py Layer3, one channel, contexts of 1 to 3, exact-history with PPM blending) on the LEVEL classes round(x / 8); hexD = the same on the DELTA classes round((x - last) / 2); hexR = alpha-beta plus the history predictor on the alpha-beta RESIDUAL classes round(res / 2) (trend for the smooth part, history for repeating patterns). When the history predictor has no prediction it falls back to the last accepted value (hexL, hexD) or the alpha-beta prediction (hexR).
Reported also: Hex-N table entries at the end (a memory proxy; not hardware cost).
Limits: synthetic data made by this file, not recordings; one noise level; steady sampling (no gaps); the history predictor is the Python model, with floating-point weights and no hardware; parameters of contestants not tuned (those of ab and ema are first guesses); Layer 1 is taken as plain quantisation."""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1
N, SIG = 20000, 3.0
def make(kind, seed):
    r = random.Random(seed); clean = []; v = 2000.0; shift = 0.0; steps = []; spk = []; obs = []
    nxt = r.randint(2000, 4000)
    for t in range(N):
        v += r.gauss(0, 0.05)
        if kind == "steps" and t == nxt: shift += r.choice((-60, 60)); steps.append(t); nxt += r.randint(2500, 3500)
        c = v + shift + (80 * math.sin(2 * math.pi * t / 400) if kind == "cycle" else 0.0); clean.append(c)
        x = c + r.gauss(0, SIG); sp = r.random() < 0.003
        if sp: x += r.choice((-1, 1)) * r.uniform(50, 150)
        obs.append(x); spk.append(sp)
    return clean, obs, spk, steps
class Base:
    def coast(s, p): return p
    def __init__(s): s.last = None
    def pred(s): return s.last
    def upd(s, x): s.last = x
class Ema(Base):
    def upd(s, x): s.last = x if s.last is None else s.last + 0.2 * (x - s.last)
class AB(Base):
    def __init__(s): s.x = None; s.v = 0.0
    def pred(s): return None if s.x is None else s.x + s.v
    def upd(s, x):
        if s.x is None: s.x = x; return
        p = s.x + s.v; r = x - p; s.x = p + 0.2 * r; s.v += 0.02 * r
class Hist:
    """history predictor on classes of a derived signal"""
    def __init__(s): s.m = V1.Layer3(nch=1, L=3, align=2, half=10 ** 9, masks=[(1,)]); s.t = 0
    def top(s):
        p, rem = s.m.predict(top=1); return p[0][0][0][1] if p else None
    def feed(s, k): s.t += 5; s.m.feed(s.t, 0, k); s.m.flush()
    def entries(s): return sum(len(d) for d in s.m.tab.values())
class HexL(Base):
    def __init__(s): s.last = None; s.h = Hist()
    def pred(s):
        k = s.h.top(); return s.last if k is None else k * 8.0
    def upd(s, x): s.last = x; s.h.feed(int(round(x / 8.0)))
class HexD(Base):
    def __init__(s): s.last = None; s.h = Hist()
    def pred(s):
        k = s.h.top(); return s.last if (k is None or s.last is None) else s.last + 2.0 * k
    def upd(s, x):
        if s.last is not None: s.h.feed(max(-60, min(60, int(round((x - s.last) / 2.0)))))
        s.last = x
class HexR(Base):
    def __init__(s): s.ab = AB(); s.h = Hist(); s.pa = None
    def coast(s, p): return s.pa if s.pa is not None else p
    def pred(s):
        s.pa = s.ab.pred()
        if s.pa is None: return None
        k = s.h.top(); return s.pa if k is None else s.pa + 2.0 * k
    def upd(s, x):
        pa = s.ab.pred()
        if pa is not None: s.h.feed(max(-60, min(60, int(round((x - pa) / 2.0)))))
        s.ab.upd(x)
def run(factory, clean, obs, spk, steps):
    f = factory(); sig = 20.0; err = []; post = []; tp = fp = fn = 0; run_fl = 0; stepset = {}
    for st in steps:
        for j in range(1, 51): stepset[st + j] = 1
    for t in range(N):
        p = f.pred(); x = obs[t]
        if p is not None and t > 60:
            e = abs(p - clean[t])
            if not spk[t]: err.append(e); (post.append(e) if t in stepset else None)
            fl = abs(x - p) > 5 * sig
            if fl and spk[t]: tp += 1
            elif fl and not spk[t]: fp += 1
            elif not fl and spk[t]: fn += 1
        else: fl = False
        if p is not None:
            run_fl = run_fl + 1 if fl else 0
            if run_fl >= 3: fl = False          # three flags in a row: a real shift, accept it
            if not fl: sig += 0.01 * (1.25 * abs(x - p) - sig)
            xa = f.coast(p) if fl else x
        else: xa = x
        f.upd(xa)
    ent = f.h.entries() if hasattr(f, "h") else 0
    return sum(err) / len(err), (sum(post) / len(post) if post else float("nan")), tp / max(tp + fn, 1), tp / max(tp + fp, 1), ent
CONT = [("persist", Base), ("ema", Ema), ("ab", AB), ("hexL", HexL), ("hexD", HexD), ("hexR", HexR)]
def main(seeds=5):
    for kind in ("drift", "cycle", "steps"):
        data = [make(kind, sd) for sd in range(seeds)]
        print("\n%s: mean over %d seeds; MAE vs clean value (repeat-last scores ~2.5), MAE in the 50 samples after a step, spike recall / precision, Hex-N table entries" % (kind, seeds), flush=True)
        for name, fac in CONT:
            rs = [run(fac, *d) for d in data]; m = [sum(r[i] for r in rs) / seeds for i in range(5)]
            print("%-8s MAE %6.2f   after-step %6.2f   recall %.2f  precision %.2f   entries %6.0f" % (name, m[0], m[1], m[2], m[3], m[4]), flush=True)
if __name__ == "__main__": main(*[int(x) for x in sys.argv[1:]])
