"""hexn_layer3_v2: LAYER 3 with REWARD, GOAL COMPARISON and a FEEDBACK RECORD STREAM (Python only; clone-extension of hexn_layer3_v1.py, which is untouched; no RTL).
Alan, 27 Oct 2026: add the reward and compare-with-goal mechanisms at layer 3; the comparison produces a new set of data that can be fed back through the teaching side: an overarching feedback mechanism.
What is added to layer 3 (v1):
 VALUES. Every path-memory entry (context level, mask, context -> moment) also carries a value and a count. After a trial the reward moves the values of every entry used since the last reward toward the reward by a constant step (1/8), as the layer 2 store does.
 GOAL READ (`choose`). At a choice point the possible moments (the options) are looked up from the most specific context down; the first level where some option has been tried at least `min_n` times decides; options never tried count as value 0 (so a bad known option gives way to an untried one).
 GOAL COMPARISON (`compare`). The goal arrives as a channel (a request); when the outcome comes, layer 3 compares it with the goal and makes a RECORD: goal, desired outcome, outcome, the weight its own path gave to the desired outcome just before it happened, the choices made, and the reward (+64 reached, -32 missed; the same signed bytes as the layer 2 REW command).
 FEEDBACK. The reward stream of those records is sent down through the layer 2 store's own teaching command (REW), so layer 3 acts as the teacher of layer 2; the records can also be replayed into a fresh store (checked: the same tables come out).
Test world (SYNTHETIC): each trial the goal channel requests desired end 5 (g=0) or 6 (g=1) at random; the agent picks key 1 in {0,3} and key 2 in {1,4}; the trial ends 5 if (0,1) or (3,4), else 6 (after a fixed key 2 in between); a thermistor channel drifts and means nothing. Layer 2 (remote keys only) cannot see the request, so it cannot beat chance; layer 3, which has the goal channel in its path, can.
Limits: synthetic world, constant tuning, no hardware; the reward rule is the teacher's compare rule, not a measured one."""
import os, sys, random, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1, hexn_store_v3 as S
class Layer3R(V1.Layer3):
    def __init__(s, *a, step=0.125, min_n=3, **k):
        super().__init__(*a, **k); s.val = {}; s.used = []; s.step = step; s.min_n = min_n
    def _close(s):
        ch = tuple(sorted(s.pend.items()))
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is not None: s.used.append((j, m, c, ch))
        s.used = s.used[-400:]; return super()._close()
    def reward(s, r):
        """r: signed 8-bit, 64 = +1. Every entry used since the last reward moves toward r."""
        for j, m, c, ch in s.used:
            v, n = s.val.get((j, m, c), {}).get(ch, (0.0, 0)); s.val.setdefault((j, m, c), {})[ch] = (v + (r - v) * s.step, n + 1)
        s.used = []
    def choose(s, options):
        """goal read: returns (option, level index or None)"""
        for i, (j, m) in enumerate(s.levels):
            c = s._ctx(j, m)
            if c is None: continue
            d = s.val.get((j, m, c), {}); seen = [(d.get(o, (0.0, 0)), o) for o in options]
            if any(n >= s.min_n for (v, n), o in seen):
                best = max(((v if n else 0.0), o) for (v, n), o in seen); return best[1], i
        return None, None
def compare(goal, outcome, p_desired, choices, r_hit=64, r_miss=-32):
    """the goal comparison: one feedback record"""
    hit = outcome == goal["desired"]
    return {"goal": goal["request"], "desired": goal["desired"], "outcome": outcome, "reached": hit, "p_desired": round(p_desired, 3), "choices": choices, "reward": r_hit if hit else r_miss}
END = {(0, 1): 5, (3, 4): 5, (0, 4): 6, (3, 1): 6}
def trial_events(t, g, k1, k2, e, th=None):
    ev = [(t, 1, g), (t + 6, 0, k1), (t + 9, 0, k2), (t + 12, 0, 2), (t + 15, 0, e)]
    if th is not None: ev.append((t + 20, 2, th))
    return ev
def run(n=800, seed=0, eps=0.1, passive=40, mode="l3", log=False):
    """mode: 'l3' (layer 3 agent), 'l2' (layer 2 store, remote keys only, taught by layer 3's reward records), 'rand'"""
    rnd = random.Random(seed); m = V1.Layer3 if False else Layer3R(nch=3, L=4, align=2, half=400); st = S.StoreV3(N=2, W=400, vshift=3, glvl=1)
    t = 0; th = 1; hits = []; recs = []; l2cmds = []
    def feed(tt, ch, k):
        m.feed(tt, ch, k); m.flush()
    for tt, ch, k in ((0, 1, 0), (0, 2, th), (0, 0, 7)): m.feed(tt, ch, k)
    m.flush(); st.step(S.OBS, 7, 0); l2cmds.append(("OBS", 7, 0))
    for i in range(n):
        t += 30; g = rnd.randrange(2); goal = {"request": g, "desired": 5 if g == 0 else 6}; feed(t, 1, g)
        explore = i < passive or rnd.random() < eps or mode == "rand"; ch = []
        k = []
        for opts, tk in (((0, 3), t + 6), ((1, 4), t + 9)):
            if explore: pick = rnd.choice(opts)
            elif mode == "l3":
                mo, _ = m.choose([((0, o),) for o in opts]); pick = mo[0][1] if mo else rnd.choice(opts)
            else:
                l2cmds.append(("RD", 0, tk)); gb = st.step(S.RD, 0, tk)["gbest"]; pick = gb if gb in opts else rnd.choice(opts)
            k.append(pick); ch.append("explore" if explore else "read")
            feed(tk, 0, pick); l2cmds.append(("OBS", pick, tk)); st.step(S.OBS, pick, tk)
        feed(t + 12, 0, 2); l2cmds.append(("OBS", 2, t + 12)); st.step(S.OBS, 2, t + 12)
        e = END[(k[0], k[1])]; v = dict(m.channel_view(0, top=10 ** 6)); z = sum(v.values()) or 1.0; pd = v.get(goal["desired"], 0.0) / z
        feed(t + 15, 0, e); l2cmds.append(("OBS", e, t + 15)); st.step(S.OBS, e, t + 15)
        rec = compare(goal, e, pd, [k[0], k[1]]); recs.append(rec) if log else None; hits.append(rec["reached"])
        m.reward(rec["reward"]); st.step(S.REW, r=rec["reward"]); l2cmds.append(("REW", rec["reward"], 0))
        if rnd.random() < 0.1: th = max(0, min(3, th + rnd.choice((-1, 1)))); feed(t + 20, 2, th)
    return hits, recs, l2cmds, st
def share(h, a, b): return sum(h[a:b]) / (b - a)
def replay(l2cmds):
    """feed the recorded observe and reward commands into a fresh layer 2 store"""
    st = S.StoreV3(N=2, W=400, vshift=3, glvl=1)
    for c, x, t in l2cmds:
        if c == "OBS": st.step(S.OBS, x, t)
        elif c == "RD": st.step(S.RD, 0, t)
        else: st.step(S.REW, r=x)
    return st
def tables(st): return ([tuple(e) if e else None for e in st.k], [tuple(e) if e else None for e in st.c])
def main(seeds=10):
    print("goal is a request each trial (desired end 5 or 6 at random); chance = 0.5; share of trials reaching the desired end, trials 600-800, mean of %d seeds" % seeds)
    for mode, name in (("rand", "random choices"), ("l2", "layer 2 store (remote keys only), taught by layer 3's reward records"), ("l3", "layer 3 (goal channel in its path)")):
        hs = [run(seed=s, mode=mode)[0] for s in range(seeds)]
        print("%-70s %.3f   (trials 40-100: %.3f)" % (name, sum(share(h, 600, 800) for h in hs) / seeds, sum(share(h, 40, 100) for h in hs) / seeds))
    h, recs, cmds, st = run(seed=0, mode="l2", log=True); st2 = replay(cmds); print("layer 2 live vs replayed from the recorded commands: same tables = %s" % (tables(st) == tables(st2)))
    h, recs, cmds, st = run(seed=0, mode="l3", log=True)
    p = [r["p_desired"] for r in recs[600:]]; ok = [r["p_desired"] for r in recs[600:] if r["reached"]]; print("layer 3 records: %d; mean weight its path gave the desired end before it happened: %.3f (%.3f when reached)" % (len(recs), sum(p) / len(p), sum(ok) / len(ok)))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "sessions", "layer3_feedback_records_v2.json"); json.dump({"note": "synthetic world, seed 0, layer 3 agent; one record per trial", "records": recs}, open(out, "w")); print("wrote", os.path.normpath(out))
if __name__ == "__main__": main()
