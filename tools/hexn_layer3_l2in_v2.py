"""hexn_layer3_l2in_v2: clone of hexn_layer3_l2in_v1.py (v1 untouched). Alan, 31 Oct 02:19: yes to the three open tests, and 'the layer 2 feeds are the same number as the layer 1 feeds, they are the arms of the input side': one layer 2 per layer 1 feed, as in v1 (3 channels, 3 layer 2 predictors).
New here (Python model only): (a) GATE: while a channel's layer 2 reports a surprise, that channel's key (not the remote channel 0) enters layer 3 as the marker -1, so the context stops trusting it; (b) PRED: layer 2's predicted next key of a channel is added as an extra channel; (c) a world where one sensor's surprise predicts another's behaviour (world3): the thermistor runs a fixed cycle 0,1,2,3,0.. one step per routine; when the hidden regime flips (every 3 to 6 routines; regime 0 uses routines A or B, regime 1 uses C or D) the thermistor SKIPS a step. The skip is a layer 2 surprise on channel 2 that comes before the first key of the first routine of the new regime; the thermistor key alone does not show it unless the previous key is still in the context (layer 3 holds only the last 4 snapshots, about one routine).
Arms: base; v-all; v-ch2 (verdict of the thermistor only); gate (channels 1 and 2); pred-all; v-ch2+gate. Score: remote-key top-1 by channel_view, as before; unbounded table; 6 seeds."""
import argparse, os, random, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as L3, hexn_layer3_cap_v1 as CAP, hexn_layer2_base_v1 as B

def world3(n=600, seed=1):
    r = random.Random(seed); R = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5]}
    ev = [(0, 1, 0), (0, 2, 0), (0, 0, 7)]; t = 0; reg = 0; left = r.randint(3, 6); th = 0
    for i in range(n):
        flip = False
        if left == 0: reg ^= 1; left = r.randint(3, 6); flip = True
        left -= 1; th = (th + (2 if flip else 1)) % 4; t += 3; ev.append((t, 2, th)); name = r.choice("AB" if reg == 0 else "CD")
        for k in R[name]: t += 3; ev.append((t, 0, k))
    ev.sort(key=lambda e: e[0]); return ev

def run(events, spans, v=(), gate=(), pred=(), warm=40, L=4):
    seq = L3.moments(events, 2); nx = len(v) + len(pred); ms = L3.Layer3(nch=3 + nx, L=L, half=200); l2 = {c: B.Ngram(2) for c in range(3)}; res = [[0, 0] for _ in spans]
    for i, mo in enumerate(seq):
        d = dict(mo)
        if i >= warm and 0 in d and None not in ms.snap:
            vw = ms.channel_view(0, top=10 ** 6); ok = bool(vw) and vw[0][0] == d[0]
            for k, (a, b) in enumerate(spans):
                if a <= i < b: res[k][0] += ok; res[k][1] += 1
        out = []; add = []
        for c, k in mo:
            p = l2[c].predict(); verdict = 2 if p is None else (0 if p == k else 1); l2[c].observe(k)
            out.append((c, -1 if (c in gate and verdict == 1) else k))
            if c in v: add.append((3 + v.index(c), verdict))
            if c in pred: add.append((3 + len(v) + pred.index(c), -1 if p is None else p))
        for c, k in out + add: ms.feed(i * 1000, c, k)
        ms.flush()
    return [a / max(1, b) for a, b in res]

ARMS = (("base (classes only)", {}), ("v-all", dict(v=(0, 1, 2))), ("v-ch2 (thermistor verdict)", dict(v=(2,))), ("gate ch1+ch2", dict(gate=(1, 2))), ("pred-all", dict(pred=(0, 1, 2))), ("v-ch2 + gate", dict(v=(2,), gate=(1, 2))))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=6); a = ap.parse_args()
    for name, mk, spans in (("WORLD 3: thermistor skip announces the regime flip", lambda s: world3(500, s), [(200, 900)]), ("STEADY world (as v1)", lambda s: L3.world(400, s), [(200, 700)]), ("RULE SWITCH world (as v1; before | just after | long after)", lambda s: CAP.world2(600, s, 300), [(1000, 1500), (1500, 1900), (2300, 3000)])):
        print(f"\n{name}: remote-key top-1, {a.seeds} seeds, windows {spans}")
        for arm, kw in ARMS:
            rs = [run(mk(s), spans, **kw) for s in range(a.seeds)]
            print(f"  {arm:28s} " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(spans))), flush=True)
