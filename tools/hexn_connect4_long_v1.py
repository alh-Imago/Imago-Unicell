"""hexn_connect4_long_v1: LONG, RESUMABLE RUNS for unattended / overnight use (Python only; no RTL, nothing on a card).
Alan, 30 Oct 2026: the long runs can go on his OptiPlex overnight; the cloud machine is sometimes swept away, so a run must be able to stop and carry on.
Two jobs, both saving their whole state (learned memories and the random generator) every 50 games to <outdir>/state_*.pkl and carrying on from it if the file exists (start the same command again after any stop):
 teach    : layer 3 ALONE (greedy, on a copy, 100 games) after N training games, trained (a) by its own play, (b) taught by layer 4 (tools/hexn_connect4_teach_v1.py), against opponents with 20% RANDOM MOVES added (so that a deterministic opponent cannot be beaten by replaying one memorised game): lookahead(2) and blocker. Checkpoints 250, 500, 1000, 2000, 3000 games.
 selfplay : two copies of the suggestion system (tools/hexn_connect4_suggest_v1.py) play each other (tools/hexn_connect4_selfplay_v1.py): blocks of 100 games (A wins / draws / B wins, plies, distinct openings), and every 1000 games each copy plays 100 greedy games against the blocker and the noisy lookahead(2), with layer 4 suggesting and with layer 3 alone.
Usage:  python3 tools/hexn_connect4_long_v1.py JOB GAMES SEED OUTDIR [CHECKPOINTS comma list] [GAMES PER EVALUATION, default 100]
Results are printed and appended to <outdir>/long_<job>_seed<seed>.txt. Limits as the scripts it uses: move-history contexts, small samples, nothing tuned."""
import os, sys, pickle, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_l23_v1 as L23, hexn_connect4_teach_v1 as T, hexn_connect4_suggest_v1 as S, hexn_connect4_selfplay_v1 as P
def noisy(opp, p):
    def f(b, who, rnd): return rnd.choice(C.legal(b)) if rnd.random() < p else opp(b, who, rnd)
    return f
def load(path):
    try:
        with open(path, "rb") as f: return pickle.load(f)
    except Exception: return None
def save(path, st):
    with open(path + ".tmp", "wb") as f: pickle.dump(st, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(path + ".tmp", path)
def out(fh, line): print(line, flush=True); fh.write(line + "\n"); fh.flush()
def job_teach(games, seed, outdir, cps, fh, n_eval=100):
    for oname, base in (("lookahead(2) + 20% random moves", C.make_lookahead(2)), ("blocker + 20% random moves", C.opp_blocker)):
        opp = noisy(base, 0.2)
        for mode in ("own", "taught"):
            path = os.path.join(outdir, "state_teach_s%d_%s_%s.pkl" % (seed, mode, "la2" if "look" in oname else "blk"))
            st = load(path) or dict(g=0, rnd=random.Random(seed), ag=(L23.L3Agent(5) if mode == "own" else T.Teacher(dmax=4, conf=0.8)), rows={})
            if st["g"]: out(fh, "resuming %s %s from game %d" % (oname, mode, st["g"]))
            while st["g"] < games:
                if mode == "own": r = L23.game(st["ag"], opp, st["rnd"], 0.1); st["ag"].end(r)
                else: T.teach_game(st["ag"], opp, st["rnd"])
                st["g"] += 1
                if st["g"] in cps:
                    ev = L23.evaluate(st["ag"] if mode == "own" else T.student(st["ag"].m, st["ag"].t), opp, random.Random(seed + 99), n_eval); st["rows"][st["g"]] = ev
                    out(fh, "%s | seed %d | %-6s | after %5d games: layer 3 alone %.2f / %.2f / %.2f" % (oname, seed, mode, st["g"], ev[0], ev[1], ev[2])); save(path, st)
                elif st["g"] % 50 == 0: save(path, st)
            save(path, st)
def job_selfplay(games, seed, outdir, cps, fh, n_eval=100):
    path = os.path.join(outdir, "state_selfplay_s%d.pkl" % seed)
    st = load(path) or dict(g=0, rnd=random.Random(seed), A=S.System(dmax=4, conf=0.8), B=S.System(dmax=4, conf=0.8), res=[], opens=[], plies=[])
    if st["g"]: out(fh, "resuming self-play from game %d" % st["g"])
    while st["g"] < games:
        r, seq = P.game(st["A"], st["B"], st["rnd"]); st["g"] += 1; st["res"].append(r); st["opens"].append(tuple(seq[:4])); st["plies"].append(len(seq))
        if st["g"] % 100 == 0:
            bl = st["res"][-100:]; out(fh, "self-play seed %d | games %5d-%5d | A(X) wins %.2f / draws %.2f / B(O) wins %.2f | plies %.1f | distinct openings %d" % (seed, st["g"] - 99, st["g"], bl.count(1) / 100, bl.count(0) / 100, bl.count(2) / 100, sum(st["plies"][-100:]) / 100, len(set(st["opens"][-100:]))))
        if st["g"] in cps:
            for name, ag in (("copy of A", st["A"]), ("copy of B", st["B"])):
                for oname, opp in (("blocker", C.opp_blocker), ("lookahead(2)+20% random", noisy(C.make_lookahead(2), 0.2))):
                    wl, fo, no = S.evaluate(ag, opp, random.Random(seed + 99), n_eval, True); wa = S.evaluate(ag, opp, random.Random(seed + 99), n_eval, False)[0]
                    out(fh, "self-play seed %d | after %5d games | %s vs %-24s with layer 4 %.2f / %.2f / %.2f (follow %.2f) | layer 3 alone %.2f / %.2f / %.2f" % (seed, st["g"], name, oname, wl[0], wl[1], wl[2], fo, wa[0], wa[1], wa[2]))
            save(path, st)
        elif st["g"] % 50 == 0: save(path, st)
    save(path, st)
def main():
    if len(sys.argv) < 5: sys.exit(__doc__)
    job, games, seed, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    cps = set(int(x) for x in sys.argv[5].split(",")) if len(sys.argv) > 5 else {250, 500, 1000, 2000, 3000} if job == "teach" else {1000, 2000, 3000}
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "long_%s_seed%d.txt" % (job, seed)), "a") as fh:
        out(fh, "start %s games %d seed %d at %s (carries on from saved state if any)" % (job, games, seed, time.strftime("%Y-%m-%d %H:%M:%S")))
        n_eval = int(sys.argv[6]) if len(sys.argv) > 6 else 100
        {"teach": job_teach, "selfplay": job_selfplay}[job](games, seed, outdir, cps, fh, n_eval)
        out(fh, "finished %s seed %d at %s" % (job, seed, time.strftime("%Y-%m-%d %H:%M:%S")))
if __name__ == "__main__": main()
