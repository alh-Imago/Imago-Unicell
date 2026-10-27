"""hexn_system_trace_v1: runs the REAL routine recordings through the layer 2 store (bit-true model tools/hexn_store_v3.py) and writes a JSON TRACE for the system view page (docs/hex-n/frontend/hexn_system_v1.html): what each layer saw and said at every event, the settings, a summary, and the store's tables at the end. The rules live only in the Python model that the RTL is checked against; the page just shows the trace.
Layer 1: the pressed key and its real number of frames (decoded from the IR edge files; the keys are the exact-match bank's clean answers, no damage is added). Layer 2: for each key after the first of a session, the store's PREDICTION made before the key arrived (best next key, its count, the total count at that context, the context length used), the VERDICT (ok / contradiction / novel; start for the first key), the GOAL READ (the key the reward values favour and its value), whether a candidate was PROMOTED by this key, and the REWARD sent at a goal key (+1 for the desired goal key, -0.5 for the other). Layer 3: not built, so nothing is shown for it.
Usage: python3 tools/hexn_system_trace_v1.py [--train 1,2] [--play 3] [--n 2] [--w 80] [--vshift 3] [--glvl 1] [--goal 7] [--out docs/hex-n/sessions/system_trace_run3_v1.json]
Training runs are put in by host load (no rewards); the play runs go through observe with rewards at goal keys. Limits: real data is three short runs; the analog channels are not used; the reward is a rule (the desired goal key), not a measured teacher."""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_session_check_v1 as C, hexn_store_v3 as M
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "data")
def presses(r):
    ps, _ = C.presses_of(os.path.join(D, "esp_run_20261027_ir_routines_run%d_edges.csv" % r)); return ps
def key_of(code): return code - 11
def build(train=(1, 2), play=(3,), N=2, W=80, vshift=3, glvl=1, goal=7):
    st = M.StoreV3(N=N, W=W, vshift=vshift, glvl=glvl); t = 0
    for r in train:
        st.step(M.CLR)
        for code, _, _ in presses(r): st.step(M.LOAD, code - 12, t); t += 1
    start_known = st.n_known; events = []; flagged = 0; rights = {1: [0, 0], 2: [0, 0], 3: [0, 0]}; goals_hit = goals = rewards = 0
    for r in play:
        st.step(M.CLR); ps = presses(r); prev_us = None
        for i, (code, us, rp) in enumerate(ps):
            x = code - 12; p0 = st.promoted; out = st.step(M.OBS, x, t); t += 1
            ev = dict(run=r, n=i + 1, key=key_of(code), frames=1 + rp, gap_s=None if prev_us is None else round((us - prev_us) / 1e6, 3), verdict=["ok", "contradiction", "novel", "start"][out["verdict"]],
                      pred=dict(level=out["plevel"], key=out["pbest"] + 1, seen=out["pbest_seen"], total=out["ptotal"]) if out["plevel"] else None,
                      goal_read=dict(key=out["gbest"] + 1, value=out["gval"]) if out["plevel"] else None, promoted=st.promoted - p0, known=st.n_known, candidates=st.n_cand, reward=None)
            prev_us = us
            if out["plevel"]:
                rights[out["plevel"]][1] += 1; rights[out["plevel"]][0] += (out["pbest"] == x)
            if out["verdict"] in (1, 2): flagged += 1
            if key_of(code) in (7, 8):
                goals += 1; rv = 64 if key_of(code) == goal else -32; goals_hit += key_of(code) == goal; st.step(M.REW, r=rv); ev["reward"] = rv / 64.0; rewards += 1
            events.append(ev)
    known = [dict(len=e[0][0], ctx=[c + 1 for c in e[0][1]], next=e[0][2] + 1, seen=e[1], contra=e[2], value=st.val[i]) for i, e in enumerate(st.k) if e]
    known.sort(key=lambda d: (-d["len"], -d["seen"], d["ctx"], d["next"]))
    cands = sorted([dict(len=e[0][0], ctx=[c + 1 for c in e[0][1]], next=e[0][2] + 1, count=e[1]) for e in st.c if e], key=lambda d: (-d["count"], -d["len"], d["ctx"]))
    return dict(version=1, source="routine recordings run %s played after host load of run %s" % (",".join(map(str, play)), ",".join(map(str, train))),
                settings=dict(promote_after=N, window_events=W, value_step_shift=vshift, goal_read_context=glvl, desired_goal_key=goal, known_capacity=st.KCAP, candidate_capacity=st.CCAP),
                summary=dict(events=len(events), flagged=flagged, known_at_start=start_known, known_at_end=st.n_known, candidates_at_end=st.n_cand, promoted=st.promoted, goals=goals, desired_goals=goals_hit, rewards_sent=rewards,
                             next_event_right={str(l): dict(right=a, of=b) for l, (a, b) in rights.items()}),
                events=events, known=known, candidates=cands)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--train", default="1,2"); ap.add_argument("--play", default="3"); ap.add_argument("--n", type=int, default=2); ap.add_argument("--w", type=int, default=80)
    ap.add_argument("--vshift", type=int, default=3); ap.add_argument("--glvl", type=int, default=1); ap.add_argument("--goal", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(D, "..", "sessions", "system_trace_run3_v1.json")); a = ap.parse_args()
    tr = build(tuple(int(x) for x in a.train.split(",") if x), tuple(int(x) for x in a.play.split(",")), a.n, a.w, a.vshift, a.glvl, a.goal)
    json.dump(tr, open(a.out, "w"), indent=1); s = tr["summary"]
    print("wrote %s: %d events, %d flagged, known %d -> %d, candidates %d, promoted %d, goals %d (%d desired), next-event right %s" % (os.path.normpath(a.out), s["events"], s["flagged"], s["known_at_start"], s["known_at_end"], s["candidates_at_end"], s["promoted"], s["goals"], s["desired_goals"], s["next_event_right"]))
if __name__ == "__main__": main()
