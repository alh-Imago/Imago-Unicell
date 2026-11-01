"""tests/vm/test_arith_block_v10_v1.py -- arith_block_v10 (v9 + second-operand source bsrc = cfg_data[28:27], bit 31 reserved for the stage wrapper; 1 Nov 2026): random clocks with random reconfigurations against the Python model extended with bsrc, at WIDTH 18 and 32; with bsrc = 0 the block equals v9 on identical stimulus; deliberate breaks are caught. Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); S = os.path.join(ROOT, "sub", "verilog"); sys.path.insert(0, HERE)
from test_arith_block_v9_v1 import Model as M9, TT  # noqa: E402


class Model(M9):
    def __init__(s, W): super().__init__(W); s.bsrc = 0
    def clock(s, cv, cd, a, b, vi):
        if cv: s.bsrc = (cd >> 27) & 3
        else:
            a &= s.M; b = s.step if s.bsrc == 1 else a if s.bsrc == 2 else b & s.M
        super().clock(cv, cd, a, b, vi)


def make(d, W, n=6000, seed=1, zero_bsrc=False):
    rnd = random.Random(seed); m = Model(W); rows = []; M = (1 << W) - 1
    for k in range(n):
        cv = 1 if (k == 5 or (k > 5 and rnd.random() < 0.06)) else 0
        cd = (rnd.choice([0, 1, 2, 3, 4, 5, 6, 7, 7, 4]) | (rnd.randrange(256) << 8) | (rnd.choice(list(TT) + [0x123]) << 16) | (rnd.randrange(2) << 26) | (0 if zero_bsrc else rnd.randrange(4) << 27) | (rnd.randrange(2) << 31)) if cv else rnd.getrandbits(32)
        vi = 1 if (rnd.random() < 0.7 or k < 5) else 0
        a = rnd.getrandbits(W) if rnd.random() < 0.8 else rnd.choice([0, 1, 2, 3, M, M >> 1, 1 << (W - 1)])
        b = rnd.getrandbits(W) if rnd.random() < 0.6 else rnd.choice([0, 1, 2, 3, 4, 17, 18, 19, 31, M, 1 << (W - 1)])
        m.clock(cv, cd, a, b, vi); rows.append("%064x" % ((cv << 224) | (cd << 192) | (a << 160) | (b << 128) | (vi << 96) | (m.v << 64) | (m.out << 32)))
    p = os.path.join(d, "rows.hex"); open(p, "w").write("\n".join(rows) + "\n"); return p, n


def sim(d, W, path, n, top="arith_block_v10.v", tb="tb_arith_block_v10.v", mutate=None):
    srcs = [os.path.join(S, tb), os.path.join(S, top)]
    if mutate:
        a, b = mutate; src = open(os.path.join(S, top)).read(); assert a in src, a
        p = os.path.join(d, "mut.v"); open(p, "w").write(src.replace(a, b)); srcs[1] = p
    o = os.path.join(d, "o.vvp"); c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.WIDTH=%d" % W, "-o", o] + srcs, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+f=" + path, "+n=%d" % n], capture_output=True, text=True, timeout=600).stdout


def test_against_model_with_bsrc():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    for W in (18, 32):
        d = tempfile.mkdtemp(prefix="ab10_")
        try: path, n = make(d, W, seed=W); out = sim(d, W, path, n)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "PASS" in out and "FAIL" not in out, (W, out[-800:])


def test_bsrc_zero_equals_v9():
    d = tempfile.mkdtemp(prefix="ab10z_")
    try:
        path, n = make(d, 18, seed=7, zero_bsrc=True)
        o9 = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.WIDTH=18", "-o", os.path.join(d, "o9.vvp"), os.path.join(S, "tb_arith_block_v9.v"), os.path.join(S, "arith_block_v9.v")], capture_output=True, text=True); assert o9.returncode == 0, o9.stderr[:800]
        out9 = subprocess.run(["vvp", os.path.join(d, "o9.vvp"), "+f=" + path, "+n=%d" % n], capture_output=True, text=True).stdout
        out10 = sim(d, 18, path, n)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in out9 and "PASS" in out10, (out9[-400:], out10[-400:])    # the SAME stimulus and expected rows pass on v9 and on v10 (bit 31 random: v9 ignores it too)


MUTS = [("2'd1: in_b = step;", "2'd1: in_b = in_b_side;"),                 # constant source missing
        ("2'd2: in_b = in_a;", "2'd2: in_b = in_b_side;"),                 # a-op-a source missing
        ("bsrc <= cfg_data[28:27];", "bsrc <= cfg_data[27:26];"),           # field misplaced
        ("else if (cfg_valid) begin bsrc <= cfg_data[28:27];", "else if (cfg_valid) begin bsrc <= bsrc | cfg_data[28:27];")]   # bsrc not replaced by a new config


def test_mutations_caught():
    for m in MUTS:
        d = tempfile.mkdtemp(prefix="ab10m_")
        try: path, n = make(d, 18, seed=5); out = sim(d, 18, path, n, mutate=m)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in out and "PASS" not in out, (m[0], out[-500:])
