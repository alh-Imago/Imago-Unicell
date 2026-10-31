"""hexn_sensor_shadow_v1: SENSOR TEST, SHADOW HEIGHT -> ANIMAL, LEARNING FROM ALMOST NOTHING (Python + numpy; model only; SYNTHETIC world; new file 31 Oct 2026). Alan, 14:50: 'a simple design which allows the system to learn almost from nothing. Shadow heights, the goals are set to say if a shadow is of a certain height it is likely to be this animal, so observed shadows would indicate which it was, even from an unlearned set it should be able to calculate that.'
Reading taken: the GOAL TABLE is stated knowledge (animal -> typical shadow height and spread), and counts as the profile prior. One observation = an animal passes and the sensor reads its shadow height 5 times (3% reading noise on top of the individual animal's own height, drawn once per passing). LAYER 1 = 24 counted detectors (height bins of 8 cm over 0 to 192 cm): the observation becomes 24 small counts. NEURAL = one linear score per animal over those counts, softmax; learning = delta rule, one step per labelled observation. Six animals: rat 10+-2, cat 28+-4, dog 50+-10, sheep 75+-8, deer 110+-12, horse 150+-12 (cm; stated table).
Arms (all see the same observations): prior = the stated table turned into scores (log density of each bin for each animal, i.e. naive Bayes), NO learning; blank = zero weights, neural learning; neural = prior weights + neural learning; nb = the SIMPLE DESIGN: the same prior as pseudo-counts per animal and bin plus counting each labelled observation into its animal's histogram (a counted detector read as a table); cent = the other simple design: per-animal running mean of the observation's average height, prior mean as the first value, nearest mean wins.
Worlds: A = actual animals as stated; B = actual animals 25% taller than stated (the table is wrong); C = the shadow is scaled by an unknown sun factor drawn per observation from 0.7 to 1.3 (the table is right for factor 1).
Score: accuracy on 300 fresh observations after n labelled observations seen (n = 0, 3, 10, 30, 100, 300), mean over 40 seeds. Chance 1/6 = 0.17.
Usage: python3 tools/hexn_sensor_shadow_v1.py [WORLD ...]"""
import sys, os
import numpy as np
LR = float(os.environ.get('SHADOW_LR', '0.15'))   # neural learning rate (the 15:50 ledger row also gives 0.5 and 1.5)
NAMES = ["rat", "cat", "dog", "sheep", "deer", "horse"]; MU = np.array([10, 28, 50, 75, 110, 150.0]); SD = np.array([2, 4, 10, 8, 12, 12.0]); K = 6; NB = 24; BW = 8.0
def observe(rng, a, world):
    mu = MU[a] * (1.25 if world == "B" else 1.0); h = rng.normal(mu, SD[a]); f = rng.uniform(0.7, 1.3) if world == "C" else 1.0
    r = h * f * (1 + 0.03 * rng.standard_normal(5)); b = np.clip((r // BW).astype(int), 0, NB - 1); return np.bincount(b, minlength=NB).astype(float), r.mean()
def prior_w():
    c = (np.arange(NB) + 0.5) * BW; sd = np.maximum(SD, 3.0)[:, None]; ll = np.maximum(-0.5 * ((c[None, :] - MU[:, None]) / sd) ** 2, -8.0) - np.log(sd); return ll   # the table's log-likelihood per bin, floored at -8 (a bounded score, as a whole-number weight would be)
class Arm:
    def __init__(s, name): s.name = name; s.reset()
    def reset(s):
        n = s.name
        if n in ("prior", "neural"): s.W = prior_w().copy()
        elif n == "blank": s.W = np.zeros((K, NB))
        elif n == "nb": s.H = np.exp(prior_w()); s.H = s.H / s.H.sum(1, keepdims=True) * 4.0 + 1e-3   # prior worth 4 observations of 5 readings per animal
        elif n == "cent": s.m = MU.copy(); s.n = np.ones(K)
    def predict(s, x, mean):
        n = s.name
        if n in ("prior", "neural", "blank"): return int(np.argmax(s.W @ x))
        if n == "nb": return int(np.argmax(np.log(s.H / s.H.sum(1, keepdims=True)) @ x))
        return int(np.argmin(np.abs(s.m - mean)))
    def learn(s, x, mean, y):
        n = s.name
        if n in ("neural", "blank"):
            z = s.W @ x; z -= z.max(); p = np.exp(z); p /= p.sum(); t = np.zeros(K); t[y] = 1; s.W -= LR * np.outer(p - t, x)
        elif n == "nb": s.H[y] += x / 5.0 * 1.0
        elif n == "cent": s.n[y] += 1; s.m[y] += (mean - s.m[y]) / s.n[y]
def run(world, seeds=40, ns=(0, 3, 10, 30, 100, 300)):
    arms = ["prior", "blank", "neural", "nb", "cent"]; acc = {a: np.zeros(len(ns)) for a in arms}
    for sd in range(seeds):
        rng = np.random.default_rng(1000 + sd); test = [(a, *observe(rng, a, world)) for a in rng.integers(0, K, 300)]
        stream = [(a, *observe(rng, a, world)) for a in rng.integers(0, K, max(ns))]
        for an in arms:
            m = Arm(an); done = 0
            for j, n in enumerate(ns):
                for a, x, mean in stream[done:n]: m.learn(x, mean, a)
                done = n; acc[an][j] += np.mean([m.predict(x, mean) == a for a, x, mean in test])
    print("world %s   labelled observations seen:" % world, "  ".join("%4d" % n for n in ns))
    for an in arms: print("  %-7s accuracy:" % an, "  ".join("%.2f" % (v / seeds) for v in acc[an]))
if __name__ == "__main__":
    for w in (sys.argv[1:] or ["A", "B", "C"]): run(w)
