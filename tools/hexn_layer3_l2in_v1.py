"""hexn_layer3_l2in_v1: LAYER 3 taking in SEVERAL LAYER 2 SIGNALS as well as the layer 1 classes (Python model only; new file 31 Oct 2026). Alan, 31 Oct 02:16: 'layer 3 has to take in possible multiple layer 2 signals as well'.
Each sensor channel has its own layer 2 predictor (the order-2 back-off counter of tools/hexn_layer2_base_v1.py, which the store equals with promotion 1 and room; this is the model, not store RTL). Before each change on channel c, layer 2 says what it expects: verdict 0 = as expected, 1 = surprise (expected something else), 2 = nothing known. That verdict is added to the same MOMENT as an extra channel (3 + c) beside the layer 1 class, so layer 3's path memory sees (class, verdict) pairs for every sensor. Arms: base (layer 1 classes only), v-all (verdicts of all three channels), v-remote (verdict of channel 0 only), v-others (channels 1 and 2 only). Scored as in hexn_layer3_cap_v1 (remote-key top-1 through channel_view), on the steady coupled world and on the rule-switch world. Limits: synthetic worlds where the thermistor means nothing and the light is the hidden rule; layer 2 sees only its own channel; one verdict alphabet; unbounded table."""
import argparse, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as L3, hexn_layer3_cap_v1 as CAP, hexn_layer2_base_v1 as B

def run(events, spans, extra, warm=40):
    seq = L3.moments(events, 2); nch = 3 + len(extra) if extra else 3; ms = L3.Layer3(nch=nch, L=4, half=200); l2 = {c: B.Ngram(2) for c in range(3)}; res = [[0, 0] for _ in spans]
    for i, mo in enumerate(seq):
        d = dict(mo)
        if i >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); ok = bool(v) and v[0][0] == d[0]
            for k, (a, b) in enumerate(spans):
                if a <= i < b: res[k][0] += ok; res[k][1] += 1
        add = []
        for c, k in mo:
            p = l2[c].predict(); verdict = 2 if p is None else (0 if p == k else 1); l2[c].observe(k)
            if c in extra: add.append((3 + extra.index(c), verdict))
        for c, k in tuple(mo) + tuple(add): ms.feed(i * 1000, c, k)
        ms.flush()
    return [a / max(1, b) for a, b in res]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=6); a = ap.parse_args()
    for name, mk, spans in (("STEADY world", lambda s: L3.world(400, s), [(200, 700)]), ("RULE SWITCH at about moment 1,500", lambda s: CAP.world2(600, s, 300), [(1000, 1500), (1500, 1900), (2300, 3000)])):
        print(f"\n{name}: remote-key top-1, {a.seeds} seeds, windows {spans}")
        for arm, ex in (("base (classes only)", ()), ("v-all", (0, 1, 2)), ("v-remote", (0,)), ("v-others", (1, 2))):
            rs = [run(mk(s), spans, ex) for s in range(a.seeds)]
            print(f"  {arm:20s} " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(spans))), flush=True)
