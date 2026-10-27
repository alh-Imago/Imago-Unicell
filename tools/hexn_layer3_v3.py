"""hexn_layer3_v3: layer 3's feedback APPLIED to layer 2 (Python only; extends hexn_layer3_v2.py, untouched; no RTL).
Alan, 27 Oct 2026: apply the feedback from layer 3 into layer 2 and see if it improves the scoring overall.
Layer 2 alone cannot beat chance in the v2 test world because the goal request lives on a channel it cannot see (its events are 3-bit classes of the remote only). Two things come down from layer 3:
 (1) the reward from the goal comparison (v2: REW with +64 / -32), and
 (2) the GOAL ITSELF as an event: before each trial layer 3 sends layer 2 one OBS event whose class is the DESIRED END (class 5 or 6), so layer 2's own history context now holds 'what is wanted', and its goal read (context length 2, so that the choice of key 1 sees (previous end, wanted) and the choice of key 2 sees (wanted, key 1)) can steer.
No new layer 2 hardware command is used: OBS, REW and RD, with glvl set to 2 (STOREVAL).
Modes: rand, l2 (v2: rewards only), l2fb (rewards + goal events), l3 (layer 3 alone, as v2). Score: share of trials reaching the desired end.
Limits: synthetic world; the goal event takes one of the 8 classes already used by the keys (class 5 or 6 doubles as an end key; the contexts keep them apart because of position, which is a fact of this world, not a general rule)."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1, hexn_layer3_v2 as V2, hexn_store_v3 as S
def run(n=800, seed=0, eps=0.1, passive=40, mode="l3", glvl=2, vshift=3):
    rnd = random.Random(seed); m = V2.Layer3R(nch=3, L=4, align=2, half=400); st = S.StoreV3(N=2, W=400, vshift=vshift, glvl=glvl if mode == "l2fb" else 1)
    t = 0; th = 1; hits = []
    def feed(tt, ch, k): m.feed(tt, ch, k); m.flush()
    for tt, ch, k in ((0, 1, 0), (0, 2, th), (0, 0, 7)): m.feed(tt, ch, k)
    m.flush(); st.step(S.OBS, 7, 0)
    for i in range(n):
        t += 30; g = rnd.randrange(2); goal = {"request": g, "desired": 5 if g == 0 else 6}; feed(t, 1, g)
        if mode == "l2fb": st.step(S.OBS, goal["desired"], t)
        explore = i < passive or rnd.random() < eps or mode == "rand"; k = []
        for opts, tk in (((0, 3), t + 6), ((1, 4), t + 9)):
            if explore: pick = rnd.choice(opts)
            elif mode == "l3": mo, _ = m.choose([((0, o),) for o in opts]); pick = mo[0][1] if mo else rnd.choice(opts)
            else: gb = st.step(S.RD, 0, tk)["gbest"]; pick = gb if gb in opts else rnd.choice(opts)
            k.append(pick); feed(tk, 0, pick); st.step(S.OBS, pick, tk)
        feed(t + 12, 0, 2); st.step(S.OBS, 2, t + 12); e = V2.END[(k[0], k[1])]
        feed(t + 15, 0, e); st.step(S.OBS, e, t + 15)
        rec = V2.compare(goal, e, 0.0, k); hits.append(rec["reached"]); m.reward(rec["reward"]); st.step(S.REW, r=rec["reward"])
        if rnd.random() < 0.1: th = max(0, min(3, th + rnd.choice((-1, 1)))); feed(t + 20, 2, th)
    return hits
def main(seeds=10):
    print("share of trials reaching the desired end (chance 0.5), mean of %d seeds" % seeds)
    print("%-52s %-8s %-8s %-8s" % ("", "40-100", "100-300", "600-800"))
    for name, kw in (("random choices", dict(mode="rand")), ("layer 2, rewards only (v2)", dict(mode="l2")), ("layer 2, rewards + goal events, context 2", dict(mode="l2fb", glvl=2)), ("layer 2, rewards + goal events, context 3", dict(mode="l2fb", glvl=3)), ("layer 3 alone", dict(mode="l3"))):
        hs = [run(seed=s, **kw) for s in range(seeds)]; f = lambda a, b: sum(V2.share(h, a, b) for h in hs) / seeds
        print("%-52s %.3f    %.3f    %.3f" % (name, f(40, 100), f(100, 300), f(600, 800)))
if __name__ == "__main__": main()
