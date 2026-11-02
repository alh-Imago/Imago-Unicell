"""tests/vm/test_hexn_cores_v4.py -- sequencer and priority cores in serial RTL (2 Nov 2026, UCC v2): hexn_seq_core_v1 (up to 4 values, next one on each advance, wraps) and hexn_prio_core_v1 (up to 4 inputs; strict / weighted / sequenced).
The priority core is checked against a Python model of the arbitration of priority_cell_v4sa.v (same rules, written independently here from the cell's header) over random scenarios, and each deliberate break (BUG=n) must be caught. Needs iverilog."""
import os, random, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = lambda f: os.path.join(ROOT, "sub", "verilog", f)


def _build(d, tb, rtls, defs=()):
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    o = os.path.join(d, "o.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb"] + list(defs) + ["-o", o, os.path.join(ROOT, "tests", tb)] + [V(f) for f in rtls], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    return o


def test_seq_core():
    d = tempfile.mkdtemp(prefix="hexnseq_")
    try:
        o = _build(d, "hexn_seq_core_v1_tb.v", ["hexn_seq_core_v1.v"])
        r = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600).stdout
        assert "FAIL" not in r and "ALL PASS" in r and r.count("PASS ") >= 7, r
    finally:
        shutil.rmtree(d, ignore_errors=True)


def model_cases(seed, n):
    """random scenarios + expected release order from the cell's rules; returns (text, ncases)"""
    rnd = random.Random(seed); out = []
    for _ in range(n):
        mode = rnd.choice([0, 0, 1, 1, 2, 2]); mask = rnd.choice([15, 15, 15, 7, 11, 13, 14, rnd.randrange(1, 16)])
        ranks = rnd.randrange(256); ln = rnd.randrange(0, 5) if mode == 2 else 0; order = rnd.randrange(256)
        rk = [(ranks >> (2 * f)) & 3 for f in range(4)]
        fifo = [None] * 4; sent = [0] * 4; cr = [0] * 4; sidx = 0; rounds = []
        for _r in range(rnd.randrange(2, 5)):
            present = [f for f in range(4) if rnd.random() < 0.75 and (fifo[f] is None or not (mask >> f) & 1)]
            pm = sum(1 << f for f in present)
            for f in present:
                if (mask >> f) & 1: fifo[f] = sent[f]
                sent[f] += 1
            exp = []
            while True:
                if mode == 2 and ln == 0: break
                due = (order >> (2 * (sidx & 3))) & 3
                cand = [fifo[f] is not None and (mask >> f) & 1 and (mode != 2 or due == f) for f in range(4)]
                if not any(cand): break
                inc = [cr[f] + rk[f] if cand[f] else cr[f] for f in range(4)]
                tw = sum(rk[f] for f in range(4) if cand[f])
                sc = [inc[f] if mode == 1 else 3 - rk[f] for f in range(4)]
                win = None
                for f in range(4):                              # highest score, ties N > S > E > W
                    if cand[f] and all(not cand[g] or sc[f] >= sc[g] for g in range(4) if g != f) and win is None: win = f
                exp.append((win, fifo[win])); fifo[win] = None
                if mode == 2: sidx = 0 if sidx + 1 >= ln else sidx + 1
                if mode == 1: cr = [(max(inc[f] - tw, 0) if f == win else inc[f]) for f in range(4)]
            rounds.append((pm, exp))
        out.append("%d %d %d %d %d %d" % (mode, mask, ranks, ln, order, len(rounds)))
        for pm, exp in rounds:
            out.append("%d %d %s" % (pm, len(exp), " ".join("%d %d" % e for e in exp)))
    return "\n".join(out) + "\n"


def _split(text):
    """one chunk per scenario: the cell's one-word stores are not cleared by cfgload, so each scenario gets a fresh simulation"""
    lines = text.strip().split("\n"); i = 0; out = []
    while i < len(lines):
        n = int(lines[i].split()[5]); out.append("\n".join(lines[i:i + 1 + n]) + "\n"); i += 1 + n
    return out


def _run_prio(d, bug, seed=1, n=40):
    o = _build(d, "hexn_prio_core_v1_tb.v", ["hexn_join_core_v2.v", "hexn_prio_core_v1.v"], ["-Ptb.BUG=%d" % bug])
    res = []
    for chunk in _split(model_cases(seed, n)):
        with open(os.path.join(d, "cases.txt"), "w") as f: f.write(chunk)
        res.append(subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600, cwd=d).stdout)
    return "".join(res)


def test_prio_core():
    d = tempfile.mkdtemp(prefix="hexnprio_")
    try:
        r = _run_prio(d, 0)
        assert "FAIL" not in r and "ALL PASS" in r and r.count("ALL PASS") == 40, r
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_prio_mutants_caught():
    for bug in (1, 2, 3, 4, 5):
        d = tempfile.mkdtemp(prefix="hexnprio_")
        try:
            r = _run_prio(d, bug)
            assert "FAIL" in r, "mutant BUG=%d survived: %s" % (bug, r[-300:])
        finally:
            shutil.rmtree(d, ignore_errors=True)
