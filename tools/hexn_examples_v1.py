"""hexn_examples_v1: BUILDS AND CHECKS THE EXAMPLE LOADS (31 Oct 2026; Alan, 14:58: 'the animal test and the games become example loads, so the folder for each contains all the required files'). Python only; uses tools/hexn_item_v1.py (item format) and the 31 Oct test code.
make  : writes docs/hex-n/examples/shadow_animals/ and docs/hex-n/examples/connect4/ : numbered .hxi item files, manifest.txt (build limits, usage, and what each file is), sample data, README.md.
check FOLDER : reads manifest.txt, validates every item against the manifest's build and usage (the same check the front end would do), then runs the example's own test with ONLY the loaded files and prints the result.
Shadow example check : classifies the sample passings with the loaded weights (world A and world B samples), then lets the neural learn from the first 60 labelled passings of the B sample (float delta rule at the loaded rate) and scores the rest. Game example check : plays 40 games of depth-3 search with the LOADED weights (whole numbers, Q14) against the noisy opponent and reads the detector item.
Usage: python3 tools/hexn_examples_v1.py make | check FOLDER"""
import os, sys, struct, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_item_v1 as I, hexn_sensor_shadow_v1 as S
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); EX = os.path.join(ROOT, "docs/hex-n/examples")
TABLE = [("rat", 10, 2), ("cat", 28, 4), ("dog", 50, 10), ("sheep", 75, 8), ("deer", 110, 12), ("horse", 150, 12)]
SET_KEYS = {1: "look-back", 2: "learning rate x100", 3: "learning on", 4: "reading count per passing", 5: "search depth", 6: "random move percent", 7: "layer 2 gate x100", 8: "update constant (x 2^-29)", 9: "bias step input"}
def w(folder, name, b): open(os.path.join(folder, name), "wb").write(b)
def make_shadow():
    d = os.path.join(EX, "shadow_animals"); os.makedirs(d, exist_ok=True)
    g = I.goals_payload(TABLE, 24, 80); W = I.goals_to_weights(g, 8)
    w(d, "01_goals.hxi", I.pack(I.T_GOALS, g, usage=2, trained=b"table"))
    w(d, "02_weights.hxi", I.pack(I.T_WEIGHTS, I.weights_payload(W, [0] * 6, 8), usage=2, nin=24, wb=8, trained=b"table", parent=0))
    w(d, "03_settings.hxi", I.pack(I.T_SETTINGS, I.settings_payload({1: 3, 2: 150, 3: 1, 4: 5}), usage=2, lmax=3, trained=b"shadow"))
    w(d, "04_target.hxi", I.pack(I.T_TARGET, bytes([0]), usage=0))
    for tag, world in (("A", "A"), ("B", "B")):
        rng = np.random.default_rng(321 if world == "A" else 654); rows = []
        for _ in range(300):
            a = int(rng.integers(0, 6)); x, _m = S.observe(rng, a, world); rows.append("%d," % a + ",".join("%d" % v for v in x))
        open(os.path.join(d, "sample_world%s.csv" % tag), "w").write("# true animal index, then the 24 bin counts of one passing (5 readings); world %s: %s\n" % (tag, "animals as the table says" if world == "A" else "animals 25 percent taller than the table says") + "\n".join(rows) + "\n")
    open(os.path.join(d, "manifest.txt"), "w").write("""example shadow_animals
usage 2
build nin=24 wb=8 lmax=8
item 01_goals.hxi        goals     the goal table: six animals with typical shadow height and spread (cm)
item 02_weights.hxi      weights   neural starting weights made from the goals (Q8, 6 outputs x 24 inputs), goals_to_weights
item 03_settings.hxi     settings  look-back 3, learning rate 1.5, learning on, 5 readings per passing
item 04_target.hxi       target    strategist target: 0 = esp (a sensor needs no search: goal setter)
data sample_worldA.csv   300 labelled passings, animals as the table says
data sample_worldB.csv   300 labelled passings, animals 25 percent taller than the table says
""")
    open(os.path.join(d, "README.md"), "w").write("""# Example load: shadow height to animal

Synthetic sensor example (no real shadow recordings). Everything needed to start this usage is in this folder: the goals, the starting weights made from them, the settings, the target, and two sample runs of labelled passings.

Check it: `python3 tools/hexn_examples_v1.py check docs/hex-n/examples/shadow_animals`

Expected (see the 16:20 ledger row): with the table right the loaded weights classify about .92 of fresh passings with nothing learned; with the table wrong (world B) about .58, and learning from the first 60 labelled passings lifts the rest to about .85. The learning step in this check is in decimals; the whole-number multi-output step is not done.

To make your own: change the goal table (animals, heights, spreads), rebuild with `hexn_item_v1.goals_payload` and `goals_to_weights`, and load the new items; or load only the weights item from another run.
""")
def make_game():
    d = os.path.join(EX, "connect4"); os.makedirs(d, exist_ok=True)
    Wq = [410, 1638, 3686, -410, -1638, -3686, 0]
    w(d, "01_weights.hxi", I.pack(I.T_WEIGHTS, I.weights_payload([Wq], [0], 14), usage=1, nin=7, wb=14, trained=b"hand"))
    w(d, "02_settings.hxi", I.pack(I.T_SETTINGS, I.settings_payload({5: 3, 6: 5, 7: 50, 3: 0, 8: 5, 9: 64}), usage=1, lmax=3, trained=b"hand"))
    import json
    R = json.load(open(os.environ.get("HEXN_DETECT") or os.path.join(ROOT, "docs/hex-n/data/detect_8seeds.json")))
    allx = np.concatenate([np.array([R[o][k]["400"] for k in R[o]]) for o in R]); sc = allx.std(0) + 1e-6; names = ["habitN", "noisy2", "plain3", "plain4"]
    p = struct.pack("<BB", len(names), 4) + struct.pack("<4f", *sc)
    for o in names: p += struct.pack("<8s4f", o.encode().ljust(8, b" "), *(np.array([R[o][k]["400"] for k in R[o]]).mean(0) / sc))
    w(d, "03_detector.hxi", I.pack(I.T_DETECTOR, p, usage=1, trained=b"detect8"))
    w(d, "04_target.hxi", I.pack(I.T_TARGET, bytes([0]), usage=0))
    open(os.path.join(d, "manifest.txt"), "w").write("""example connect4
usage 1
build nin=7 wb=14 lmax=8
item 01_weights.hxi      weights   the hand score as whole numbers (Q14): own 1, 4, 9 and opponent -1, -4, -9 per counter, parity 0, bias 0
item 02_settings.hxi     settings  search depth 3, 5 percent random moves, layer 2 gate 0.50, learning off, update constant 5, bias step input 64, look-back 3
item 03_detector.hxi     detector  style detector: 4 opponent types, 4 features, scales and centroids at 400 opponent moves (example layout, not yet fixed)
item 04_target.hxi       target    strategist target: 0 = esp
""")
    open(os.path.join(d, "README.md"), "w").write("""# Example load: Connect Four

The game used for all the 31 Oct tests. The folder holds the starting weights (the hand score), the settings, the player-detector data and the target. The game rules and the layer 1 line counters are not items: they are the example's test world (`tools/hexn_connect4_v1.py`).

Check it: `python3 tools/hexn_examples_v1.py check docs/hex-n/examples/connect4`

It plays 40 games with the loaded whole-number weights against the noisy opponent at search depth 3. The 31 Oct figures for the same set-up are in the ledger (13:30 and 16:00 rows). Learning is OFF in this example; the selector turns it on for a habit opponent.
""")
def read_manifest(d):
    m = dict(items=[], data=[], build={}, usage=0)
    for line in open(os.path.join(d, "manifest.txt")):
        t = line.split()
        if not t: continue
        if t[0] == "usage": m["usage"] = int(t[1])
        elif t[0] == "build": m["build"] = {k: int(v) for k, v in (x.split("=") for x in t[1:])}
        elif t[0] == "item": m["items"].append(t[1])
        elif t[0] == "data": m["data"].append(t[1])
    return m
def check(d):
    m = read_manifest(d); items = {}; ok_all = True
    for f in m["items"]:
        b = open(os.path.join(d, f), "rb").read(); ok, why = I.validate(b, m["build"], m["usage"]); h = I.unpack(b); items[h["type"]] = h
        print("  %-18s type %d usage %d trained-on %-8s %s" % (f, h["type"], h["usage"], h["trained"], "ok" if ok else "REFUSED: " + why)); ok_all &= ok
    if not ok_all: print("refused"); return False
    name = os.path.basename(os.path.normpath(d))
    if name == "shadow_animals":
        Wq, Bq, wb = I.read_weights(items[I.T_WEIGHTS]["payload"]); W = np.array(Wq, dtype=float) / (1 << wb); st = I.read_settings(items[I.T_SETTINGS]["payload"]); lr = st[2] / 100.0
        for tag in ("A", "B"):
            rows = [l.strip().split(",") for l in open(os.path.join(d, "sample_world%s.csv" % tag)) if not l.startswith("#") and l.strip()]; y = np.array([int(r[0]) for r in rows]); X = np.array([[float(v) for v in r[1:]] for r in rows])
            acc0 = np.mean(np.argmax(X @ W.T, 1) == y); Wl = W.copy()
            for i in range(60):
                z = Wl @ X[i]; z -= z.max(); p = np.exp(z); p /= p.sum(); t = np.zeros(6); t[y[i]] = 1; Wl -= lr * np.outer(p - t, X[i])
            acc1 = np.mean(np.argmax(X[60:] @ Wl.T, 1) == y[60:]); acc0b = np.mean(np.argmax(X[60:] @ W.T, 1) == y[60:])
            print("  world %s: loaded weights, nothing learned: %.2f on all 300; on passings 61-300: %.2f; after learning from the first 60: %.2f" % (tag, acc0, acc0b, acc1))
    elif name == "connect4":
        import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_int_v1 as J
        Wq, Bq, wb = I.read_weights(items[I.T_WEIGHTS]["payload"]); st = I.read_settings(items[I.T_SETTINGS]["payload"]); j = J.OnlineInt("blank", "none", wb); j.W = list(Wq[0]); j.Bq = Bq[0]; B.JUDGE["x"] = j
        pl = B.plain_j(st[5], "x"); op = B.opponent("noisy2"); rnd = random.Random(1); sc = 0.0
        for i in range(40):
            w_ = B.game(pl, op, rnd) if i % 2 == 0 else B.game(op, pl, rnd); r = (1 if w_ == 1 else 2 if w_ == 2 else 0); sc += 0.5 if r == 0 else (1.0 if (r == 1) == (i % 2 == 0) else 0.0)
        p = items[I.T_DETECTOR]["payload"]; ng, nf = struct.unpack("<BB", p[:2])
        print("  detector item: %d opponent types, %d features; 40 games at depth %d with the loaded weights against noisy2: score %.2f" % (ng, nf, st[5], sc / 40))
    return True
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "make": make_shadow(); make_game()
    else: check(a[1])
