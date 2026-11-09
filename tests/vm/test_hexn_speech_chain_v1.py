"""Cross-check of rtl/hexn_speech_chain_v1.v (iverilog) against the exact-arithmetic Python model tools/hexn_chain_hw_v1.py, with RANDOM parameters and random event streams (no speech data needed).
Per window end the RTL's class, prediction, gap and stop flag must equal the model's, for every window of every recording; once with the configuration preloaded from files and once written at run time through the cfg_ port. A mutated model (one shift code changed) must DISAGREE with the RTL, so the comparison is not vacuous.
Needs iverilog: FAILS (does not skip) without it."""
import os, sys, random, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", ".."); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_chain_hw_v1 as M

NWIN, STEPS, NL = 5, 4, 48; WSZ = STEPS * NL


def b8(v): return int(v) & 0xFF


def make_params(seed):
    r = random.Random(seed)
    wrom = [[tuple(r.choice((0, 0, 0, 1, -1)) for _ in range(M.NC)) for _ in range(WSZ)] for _ in range(NWIN)]
    thr = [[r.randint(-8, 8) for _ in range(M.NC)] for _ in range(NWIN)]
    lp = [[[[r.randint(-127, 0) for _ in range(M.A)] for _ in range(M.A)] for _ in range(NWIN)] for _ in range(M.NC)]
    code = [r.randint(0, 10) for _ in range(NWIN)]; gap = r.randint(2, 8)
    return M.Params(NWIN, STEPS, NL, wrom, thr, lp, code, gap), r


def write_files(d, P, recs):
    def tern(t):
        w = 0
        for c, x in enumerate(t): w |= (1 if x == 1 else 3 if x == -1 else 0) << (2 * c)
        return w
    (d / "wrom.hex").write_text("\n".join("%05x" % tern(t) for w in range(NWIN) for t in P.wrom[w]) + "\n")
    (d / "thr.hex").write_text("\n".join("%020x" % sum(b8(P.thr[w][c]) << (8 * c) for c in range(M.NC)) for w in range(NWIN)) + "\n")
    lines = []
    for w in range(NWIN):
        for prev in range(M.A):
            for cls in range(M.A): lines.append("%020x" % sum(b8(P.lp[c][w][prev][cls]) << (8 * c) for c in range(M.NC)))
    (d / "lp.hex").write_text("\n".join(lines) + "\n")
    (d / "cfg.hex").write_text("\n".join("%04x" % x for x in P.code + [P.gap]) + "\n")
    prog = []
    for ev in recs:
        prog.append(0x4000)
        for w in range(NWIN):
            for st, ln in sorted(e for e in ev if e[0] // STEPS == w): prog.append((st % STEPS) * NL + ln)
            prog.append(0x8000)
    (d / "prog.hex").write_text("\n".join("%04x" % x for x in prog) + "\n")


def run_sim(d, load):
    srcs = [os.path.join(ROOT, "rtl", "hexn_speech_chain_v1.v"), os.path.join(HERE, "hexn_speech_chain_v1_tb.v")]
    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.LOAD=%d" % load, "-o", str(d / "sim")] + srcs, check=True, capture_output=True)
    out = subprocess.run(["vvp", str(d / "sim")], cwd=d, capture_output=True, text=True, check=True).stdout
    assert "DONE" in out
    return [tuple(int(x) for x in l.split()[2:]) for l in out.splitlines() if l.startswith("R ")]      # (cls, pred, gap, stop)


def test_chain_matches_model(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    P, r = make_params(7); recs = []
    for k in range(40):
        n = r.choice((0, 3, 10, 30, 60)); recs.append([(r.randrange(NWIN * STEPS), r.randrange(NL)) for _ in range(n)])
    want = [(q["cls"], q["pred"], q["gap"], q["stop"]) for ev in recs for q in M.run_recording(P, ev)]
    assert len({w[0] for w in want}) > 3 and len({w[1] for w in want}) > 3 and {0, 1} <= {w[3] for w in want}      # the random case exercises classes, predictions and both stop values
    for load in (0, 1):
        d = tmp_path / ("load%d" % load); d.mkdir(); write_files(d, P, recs)
        got = run_sim(d, load)
        assert len(got) == len(want) == 40 * NWIN
        bad = [i for i in range(len(want)) if got[i] != want[i]]
        assert not bad, "first mismatch at window %d: rtl %s model %s" % (bad[0], got[bad[0]], want[bad[0]])
    P2, _ = make_params(7); P2.code[0] = (P2.code[0] + 3) % 11            # mutation: the comparison must notice
    other = [(q["cls"], q["pred"], q["gap"], q["stop"]) for ev in recs for q in M.run_recording(P2, ev)]
    assert other != got
