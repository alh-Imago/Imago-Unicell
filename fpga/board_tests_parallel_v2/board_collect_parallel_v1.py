#!/usr/bin/env python3
"""board_collect_parallel_v1.py -- ledger #1180: collector for the parallel / no-interrupt bitstreams (groups P, Q, R).
Unlike board_collect_v2.py it does NOT ignore `last=` (the clock the final word arrived): these runs have no random stalls, so the card must give the SAME clock count as the
simulation, and the point of the tests is whether that count moves. It then states the three questions in plain words. Standard library only.  usage: python3 board_collect_parallel_v1.py [raw_dir] [out_prefix]"""
import glob, json, os, re, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "raw")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "board_results")
board, sims = {}, {}
out = [f"UniCell on-board PARALLEL / NO-INTERRUPT run  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}", "=" * 100]
for js in sorted(glob.glob(os.path.join(HERE, "groups", "group_*.json"))):
    meta = json.load(open(js)); g = meta["group"]
    p = os.path.join(RAW, f"group_{g}.bin")
    text = (open(p, "rb").read() if os.path.exists(p) else b"").decode("latin1")
    for name in meta["tests"]:
        sim = meta["sim_lines"][name]; sims[name] = sim
        full = [l for l in re.findall(r"UCT " + re.escape(name) + r" res=[PF] n=[0-9A-F]{4} e=[0-9A-F]{4} bad=[0-9A-F]{4} to=\d last=[0-9A-F]{8} sig=[0-9A-F]{8} w=[0-9A-F,]*", text) if len(l) == len(sim)]
        line = max(set(full), key=full.count) if full else ""
        board[name] = line
        status = "NOREPORT" if not line else ("PASS" if line == sim else ("FAIL (words wrong)" if " res=F " in line else "DIFFERS from simulation"))
        last = lambda l: int(re.search(r"last=([0-9A-F]+)", l).group(1), 16) if l else None
        out += [f"{name:<8} {status:<24} clocks on card: {last(line)}   simulated: {last(sim)}", f"   board    : {line or '(nothing complete received)'}", f"   simulated: {sim}", ""]
clk = lambda n: int(re.search(r"last=([0-9A-F]+)", board[n]).group(1), 16) if board.get(n) else None
def verdict(title, names, same_as):
    got = [clk(n) for n in names]
    if None in got: return f"{title}: incomplete (no report from {[n for n in names if clk(n) is None]})"
    return f"{title}: {dict(zip(names, got))} -> " + ("ALL EQUAL to " + same_as if len(set(got)) == 1 and got[0] == clk(same_as) else "NOT all equal -- see lines above")
out += ["=" * 100,
        verdict("T1 isolation (job alone / beside 4 / beside 8 storm lanes)", ["iso_s0", "iso_s4", "iso_s8"], "iso_s0"),
        verdict("T4 independent copies (4 copies at once vs the single job)", ["ind_0", "ind_1", "ind_2", "ind_3"], "iso_s0"),
        verdict("T5 shared port (1, 2, 4, 8 lanes behind one input/output; simulation says a single lane already fills the port)", ["iso_s0", "sh_k2", "sh_k4", "sh_k8"], "iso_s0")]
exact = sum(1 for n in sims if board.get(n) == sims[n])
out.append(f"EXACT MATCH WITH SIMULATION: {exact} of {len(sims)}")
open(OUT + ".txt", "w").write("\n".join(out) + "\n"); print("\n".join(out[-5:]))
