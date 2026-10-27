"""hexn_layer3_v1: LAYER 3 model (Python only; no RTL). Alan, 27 Oct 2026: layer 3 brings the channels together into one COMBINED PATH, keeps deeper memories, and gives PREDICTIVE POSSIBLES, each with a weight, as its outcome.
Design (a first model; every number below is a setting to be tuned, not a result):
 CHANNELS. Each channel (remote keys, light, thermistor ...) is one layer-1 stream that reports a stable key only when it changes: (time, channel, key).
 ALIGNMENT. Changes whose times lie within `align` ticks of the first change of a moment are one MOMENT (the channels are lined up at one instant). A moment is the set of changes {(channel, key)} plus the SNAPSHOT: the latest stable key of every channel after it.
 PATH MEMORY. Contexts are the last j snapshots (j = 1..L, L deeper than layer 2's 3), each seen through a channel MASK (all channels, or fewer). Each context holds the weights of the moments that followed it. Weights decay with a half-life of `half` moments, so old habits fade but are not erased.
 OUTCOME. `predict` returns the possible next moments, most weighted first, with weights that sum to at most 1; the remainder is 'something not seen'. Longest contexts speak first and pass the rest of the weight down by the PPM-C escape rule: a context seen t times with d different followers keeps t/(t+d) of the weight it has left. `channel_view` folds these into 'what will channel c do next' for the host.
Limits: the model is exact Python; no hardware; the test world is synthetic (the real recordings of light, pot and thermistor were made one at a time, not at once with the remote), so the numbers show that the mechanism works, not how well it will do on real coupled data."""
import math, itertools
class Layer3:
    def __init__(s, nch=3, L=4, align=2, half=200, masks=None):
        s.nch, s.L, s.align, s.half = nch, L, align, half
        s.masks = masks or [tuple([1] * nch)] + [tuple(1 if i <= k else 0 for i in range(nch)) for k in range(nch - 2, -1, -1)]
        s.levels = sorted(((j, m) for j in range(1, L + 1) for m in s.masks), key=lambda jm: (-jm[0] * sum(jm[1]), -jm[0]))
        s.snap = [None] * nch; s.hist = []; s.tab = {}; s.n = 0; s.pend = None; s.t0 = None
    def _ctx(s, j, m): return tuple(tuple(k if on else None for k, on in zip(sn, m)) for sn in s.hist[-j:]) if len(s.hist) >= j else None
    def _w(s, e): return e[0] * 0.5 ** ((s.n - e[1]) / s.half)
    def feed(s, t, ch, key):
        """one layer-1 change; returns the moment just closed (changes tuple) or None"""
        out = None
        if s.pend is not None and t - s.t0 > s.align: out = s._close()
        if s.pend is None: s.pend = {}; s.t0 = t
        s.pend[ch] = key; return out
    def flush(s): return s._close() if s.pend else None
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            d = s.tab.setdefault((j, m, c), {}); e = d.get(ch, (0.0, s.n)); d[ch] = (s._w(e) + 1.0, s.n)
        for c, k in ch: s.snap[c] = k
        s.hist.append(tuple(s.snap)); s.hist = s.hist[-s.L:]; s.n += 1; return ch
    def predict(s, top=8):
        p = {}; rem = 1.0
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None or None in s.snap: continue
            d = s.tab.get((j, m, c))
            if not d: continue
            ws = {k: s._w(e) for k, e in d.items()}; t = sum(ws.values()); dn = len(ws)
            for k, w in ws.items(): p[k] = p.get(k, 0.0) + rem * w / (t + dn)
            rem *= dn / (t + dn)
        r = sorted(p.items(), key=lambda kv: -kv[1]); return r[:top], rem
    def channel_view(s, ch, top=4):
        p, rem = s.predict(top=10 ** 6); v = {}
        for k, w in p:
            for c, key in k:
                if c == ch: v[key] = v.get(key, 0.0) + w
        return sorted(v.items(), key=lambda kv: -kv[1])[:top]
def moments(events, align=2):
    """offline: (t, ch, key) -> list of moments, each a tuple of (ch, key)"""
    m = Layer3(L=1, align=align); out = []
    for t, c, k in events:
        r = m.feed(t, c, k)
        if r: out.append(r)
    r = m.flush()
    if r: out.append(r)
    return out
def world(n_routines=400, seed=1, switch=(8, 15), noise=True):
    """synthetic coupled world on real vocabularies: remote routines A=0125 B=3126 C=0426 D=3425 (as in the recordings). A hidden light state (channel 1: key 0/1) toggles every 8-15 routines; light 0 -> routines A or B, light 1 -> C or D. Channel 2 (thermistor) drifts 0..3 by a random walk every ~20 moments and means nothing. Time in ticks; keys 1 tick apart inside a routine, 6 between routines."""
    import random
    r = random.Random(seed); R = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5]}
    ev = []; t = 0; light = 0; th = 1; left = r.randint(*switch); ev.append((0, 1, 0)); ev.append((0, 2, th)); ev.append((0, 0, 7)); nxt = 0
    for i in range(n_routines):
        if left == 0:
            light ^= 1; left = r.randint(*switch); t += 4; ev.append((t, 1, light))
        left -= 1; name = r.choice("AB" if light == 0 else "CD")
        for k in R[name]:
            t += 6 if k == R[name][0] else 3; ev.append((t, 0, k))
            if noise and r.random() < 0.05: t += 1; th = max(0, min(3, th + r.choice((-1, 1)))); ev.append((t + 40, 2, th))
    ev.sort(key=lambda e: e[0]); return ev
def evaluate(events, L=4, half=200, masks=None, align=2, only=None, warm=40):
    """online: predict each moment before it arrives; returns top-1 rate, top-3 rate and the mean weight given to what happened, scored from moment `warm` on. `only` keeps just those channels (renumbered from 0): the single-channel layer 2 reading."""
    if only is not None:
        mp = {c: i for i, c in enumerate(only)}; events = [(t, mp[c], k) for t, c, k in events if c in mp]
    nch = 1 + max(c for _, c, _ in events); seq = moments(events, align)
    ms = Layer3(nch=nch, L=L, half=half, masks=masks, align=align); h1 = h3 = tot = 0; wsum = 0.0
    for i, mo in enumerate(seq):
        if i >= warm and None not in ms.snap:
            p, rem = ms.predict(top=3); keys = [k for k, _ in p]; tot += 1; h1 += bool(keys) and keys[0] == mo; h3 += mo in keys; wsum += dict(p).get(mo, 0.0)
        for c, k in mo: ms.feed(i * 1000, c, k)
        ms.flush()
    return {"moments": tot, "top1": h1 / tot, "top3": h3 / tot, "weight_on_truth": wsum / tot}
def evaluate_remote(events, L=4, half=200, masks=None, align=2, only=None, warm=40):
    """Same target for every variant: at each moment that holds a REMOTE key (channel 0), how much weight did the model give that key (the channel view, renormalised over what the model expected channel 0 to do next), and was it the top choice? Moments of the other channels in between are ignored in the score but still fed."""
    if only is not None:
        mp = {c: i for i, c in enumerate(only)}; events = [(t, mp[c], k) for t, c, k in events if c in mp]
    nch = 1 + max(c for _, c, _ in events); seq = moments(events, align)
    ms = Layer3(nch=nch, L=L, half=half, masks=masks, align=align); h1 = tot = 0; wsum = 0.0
    for i, mo in enumerate(seq):
        d = dict(mo)
        if i >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); z = sum(w for _, w in v); tot += 1
            if z > 0: h1 += v[0][0] == d[0]; wsum += dict(v).get(d[0], 0.0) / z
        for c, k in mo: ms.feed(i * 1000, c, k)
        ms.flush()
    return {"remote_keys": tot, "top1": round(h1 / tot, 3), "weight_on_truth": round(wsum / tot, 3)}
if __name__ == "__main__":
    ev = world(); print("synthetic coupled world: %d changes, %d moments, remote keys only scored" % (len(ev), len(moments(ev))))
    for name, kw in (("remote only, context 3 (layer 2 reading)", dict(only=(0,), L=3, masks=[(1,)])), ("all channels, context 4, full mask only", dict(L=4, masks=[(1, 1, 1)])), ("all channels, context 4, reduced masks too", dict(L=4))):
        print("%-46s" % name, evaluate_remote(ev, **kw))
