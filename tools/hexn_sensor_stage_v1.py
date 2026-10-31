"""hexn_sensor_stage_v1: THREE-STAGE LEARNING, FAST START THEN SLOW (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:59: 'another switched level, fast start, then notice [it has settled / diverged], switch to slower'.
Same world D, corrected-height arm, 4 cm bins, whole-number learning. The neural's own wrong guesses (made before learning) over the last 20 labelled passings drive three stages:
  OFF  : no learning; goes to FAST when wrong >= 8 of 20 (the 17:55 switch).
  FAST : rate FASTR (default 192/128); goes to SLOW when wrong <= SETTLE (default 3) of the last 20 (window full).
  SLOW : rate 16/128; goes back to FAST if wrong >= 8 of 20 (the world has changed).
Arms: low (switch to the fixed rate 16, the 18:30 result), stage (3 stages), simple (running mean). Scenarios: RIGHT table, WRONG table (x1.25), SHIFT (right table; at passing 1500 every animal becomes 25 per cent taller; test passings are scaled after that). Usage: python3 tools/hexn_sensor_stage_v1.py [SEEDS] [FASTR] [SETTLE]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S
def run(seeds=6, fastr=192, settle=3, slow=16, win=20, limit=8):
    D.BW = 4.0; D.NB = 48; ns = (0, 10, 30, 100, 300, 1000, 1500, 1600, 1800, 2200, 3000); arms = ["low", "stage", "simple"]
    for sc, scale in (("RIGHT", 1.0), ("WRONG", 1.25), ("SHIFT", 1.0)):
        acc = {a: np.zeros(len(ns)) for a in arms}; fires = []; settles = []; backs = []
        for sd in range(seeds):
            rng = np.random.default_rng(9000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, max(ns))]
            if sc == "SHIFT":
                stream = [(a, r * (1.25 if i >= 1500 else 1.0), b) for i, (a, r, b) in enumerate(stream)]; test2 = [(a, r * 1.25, b) for a, r, b in test]
            for arm in arms:
                if arm == "simple": m = D.MU * scale; nn = np.ones(D.K)
                else: mo = MO.MultiOutInt(S.table(scale), slow)
                st = "FAST" if False else "OFF"; hist = []; done = 0
                for j, n in enumerate(ns):
                    for i in range(done, n):
                        a, r, band = stream[i]
                        if arm == "simple": nn[a] += 1; m[a] += (r.mean() / D.FB[band] - m[a]) / nn[a]; continue
                        x = D.feats("corr", r, band); hist.append(mo.predict(x) != a); hist = hist[-win:]; w = sum(hist)
                        if arm == "low":
                            if st == "OFF" and w >= limit: st = "SLOW"; fires.append(i)
                        else:
                            if st == "OFF" and w >= limit: st = "FAST"; mo.rate = fastr; fires.append(i)
                            elif st == "FAST" and len(hist) == win and w <= settle: st = "SLOW"; mo.rate = slow; settles.append(i)
                            elif st == "SLOW" and w >= limit: st = "FAST"; mo.rate = fastr; backs.append(i)
                        if st != "OFF": mo.learn(x, a)
                    done = n; T = test2 if (sc == "SHIFT" and n > 1500) else test
                    if arm == "simple": ok = np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in T])
                    else: ok = np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in T])
                    acc[arm][j] += ok
        print("%s table, 4 cm bins, fast %d slow %d settle<=%d; passings:" % (sc, fastr, slow, settle), "  ".join("%5d" % n for n in ns), flush=True)
        for a in arms: print("  %-7s" % a, "  ".join("%.3f" % (v / seeds) for v in acc[a]))
        print("  stage arm: median passing of settle->slow %s, returns to fast %d times in %d runs" % (int(np.median(settles)) if settles else "-", len(backs), seeds), flush=True)
if __name__ == "__main__": run(*[int(v) for v in sys.argv[1:]])
