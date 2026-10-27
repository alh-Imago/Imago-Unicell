"""hexn_ctxstore_acc_v1: accuracy of the bit-true context store model (tools/hexn_ctxstore_v1.py) inside the layer 3 predictor, same worlds and measure as tools/hexn_layer3_tiers_acc_v1.py (steady, and changing A-D / F-I / A-D). Compares: unbounded (time-faded weights, reference), tiered (earlier model), hw14 (this store, 14 slots), hw6 (6 slots), hw14 with a deliberately small hash table (BB=9, 512 buckets) to show what overflow does. Python only."""
import os, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_tiers_acc_v1 as A, hexn_layer3_v1 as V1, hexn_ctxstore_v1 as C
def k31(key): return zlib.crc32(repr(key).encode()) & 0x7FFFFFFF
class HW(V1.Layer3):
    def __init__(s, store, **k): super().__init__(**k); s.st = store; s.ids = {}; s.rev = {}; s.slow = {}
    @property
    def nent(s): return s.st.c['created']
    def _fid(s, ch):
        if ch not in s.ids: s.ids[ch] = len(s.ids) + 1; s.rev[s.ids[ch]] = ch
        return s.ids[ch]
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            s.st.obs(k31((j, m, c)), s._fid(ch))
        for c, k in ch: s.snap[c] = k
        s.hist.append(tuple(s.snap)); s.hist = s.hist[-s.L:]; s.n += 1; return ch
    def predict(s, top=8):
        p = {}; rem = 1.0
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None or None in s.snap: continue
            f, sl = s.st.rd(k31((j, m, c)))
            d = {fid: w for fid, w in sl if w}
            if not d: continue
            t = sum(d.values()); dn = len(d)
            for fid, w in d.items(): p[s.rev[fid]] = p.get(s.rev[fid], 0.0) + rem * w / (t + dn)
            rem *= dn / (t + dn)
        r = sorted(p.items(), key=lambda kv: -kv[1]); return r[:top], rem
_orig = A.make
def make(rule, cap):
    if rule == "hw14": return HW(C.CtxStore(16, 8, 14), nch=3, L=4, align=2)
    if rule == "hw6": return HW(C.CtxStore(16, 8, 6), nch=3, L=4, align=2)
    if rule == "hw14_small": return HW(C.CtxStore(9, 8, 14), nch=3, L=4, align=2)
    return _orig(rule, cap)
A.make = make
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    for changing in (False, True):
        ev, ph = A.world(n, changing); print("\n%s world, %d changes" % ("CHANGING (A-D, F-I, A-D)" if changing else "STEADY", len(ev)))
        print("%-11s | " % "rule" + " | ".join("phase %d: n  top1  weight" % (p + 1) for p in range(3 if changing else 1)) + " | entries")
        for rule in ("unbounded", "tiered", "hw14", "hw6", "hw14_small"):
            acc, ents = A.run(ev, ph, rule, 300)
            cells = []
            for p in range(3 if changing else 1):
                a = acc.get(p, [0, 0, 0.0]); cells.append("%7d %6.3f %6.3f" % (a[0], a[1] / a[0] if a[0] else 0, a[2] / a[0] if a[0] else 0))
            print("%-11s | " % rule + " | ".join(cells) + " | %s" % ents)
