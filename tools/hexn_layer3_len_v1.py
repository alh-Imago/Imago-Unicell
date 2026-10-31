"""hexn_layer3_len_v1: HOW LONG SHOULD LAYER 3's LOOK-BACK BE? (Python model only; new file 31 Oct 2026.) Alan, 31 Oct 02:23, recalling an earlier optimum 'of 7' (not found in the ledger by search; this test measures it afresh). Sweeps L = number of past snapshots used as context (layer 2 uses 3) for the layer 3 model (classes only, default masks) on the three synthetic worlds, scoring remote-key top-1, and counts what the table must hold at the end of the run: entries (context, moment pairs) and contexts. 6 seeds, unbounded table, half-life 200."""
import argparse, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as L3, hexn_layer3_cap_v1 as CAP, hexn_layer3_l2in_v2 as V2
def one(events, spans, L, warm=40):
    seq = L3.moments(events, 2); ms = L3.Layer3(nch=3, L=L, half=200); res = [[0, 0] for _ in spans]
    for i, mo in enumerate(seq):
        d = dict(mo)
        if i >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); ok = bool(v) and v[0][0] == d[0]
            for k, (a, b) in enumerate(spans):
                if a <= i < b: res[k][0] += ok; res[k][1] += 1
        for c, k in mo: ms.feed(i * 1000, c, k)
        ms.flush()
    return [a / max(1, b) for a, b in res], sum(len(d) for d in ms.tab.values()), len(ms.tab)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=6); ap.add_argument("--Ls", default="2,3,4,5,6,7,8,9,10,12"); a = ap.parse_args()
    for name, mk, spans in (("WORLD 3 (thermistor skip announces the flip)", lambda s: V2.world3(500, s), [(200, 900)]), ("STEADY world", lambda s: L3.world(400, s), [(200, 700)]), ("RULE SWITCH world (before | just after | long after)", lambda s: CAP.world2(600, s, 300), [(1000, 1500), (1500, 1900), (2300, 3000)])):
        print(f"\n{name}: remote-key top-1 | entries | contexts (end of run); {a.seeds} seeds")
        for L in map(int, a.Ls.split(",")):
            rs = [one(mk(s), spans, L) for s in range(a.seeds)]
            print(f"  L={L:2d} " + "  ".join(f"{st.mean(r[0][i] for r in rs):.3f}" for i in range(len(spans))) + f" | {st.mean(r[1] for r in rs):7.0f} | {st.mean(r[2] for r in rs):7.0f}", flush=True)
