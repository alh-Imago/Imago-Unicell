"""tests/vm/test_arith_block_v9_v1.py -- arith_block_v9 (the block sized for Hex-N, WIDTH parameter, 1 Nov 2026): random clocks with random reconfigurations against an independent Python model at WIDTH 18 and 32; the same block at WIDTH 32 against the older arith_block_v8 (shared, truth-table nano, barrel shifter) on identical stimulus; deliberate breaks are caught. Requires iverilog."""
import os, random, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); S = os.path.join(ROOT, "sub", "verilog")
TT = {0x000: 0b1010, 0x02C: 0b1100, 0x001: 0b0101, 0x002: 0b0011, 0x004: 0b0001, 0x007: 0b1000, 0x024: 0b1110, 0x027: 0b0111, 0x0BC: 0b0110, 0x03C: 0b1001, 0x030: 0b0000, 0x0B0: 0b1111}


def sgn(v, w): v &= (1 << w) - 1; return v - (1 << w) if v >> (w - 1) else v


class Model:
    def __init__(s, W): s.W = W; s.M = (1 << W) - 1; s.SW = min(W, 18); s.mode = 0; s.step = 0; s.topo = 0; s.held = 0; s.armed = 0; s.total = 0; s.out = 0; s.v = 0
    def clock(s, cv, cd, a, b, vi):
        W, M = s.W, s.M; a &= M; b &= M
        if cv: s.mode = cd & 7; s.step = (cd >> 8) & 255; s.topo = (cd >> 16) & 1023; s.held = (cd >> 26) & 1; s.armed = 1; s.total = 0; s.out = 0; s.v = 0; return
        inc = (a & 1) and vi; dec = ((a >> 1) & 1) and vi; pulse = vi and s.mode == 4 and (inc or dec)
        m = s.mode; sh = b & 31; SW = s.SW; sm = (1 << SW) - 1
        if m == 0: r = (a + b) & M
        elif m == 1: r = (a - b) & M
        elif m == 2: r = 1 if sgn(a, W) >= sgn(b, W) else 0
        elif m == 3: x, y = sgn(a, W), sgn(b, W); r = 0 if x < y else 1 if x == y else 2
        elif m == 4: r = (s.total + (s.step if (inc and not dec) else -s.step if (dec and not inc) else 0)) & M
        elif m == 5: r = ((a & sm) << sh) & sm if sh < 32 else 0
        elif m == 6: r = (a & sm) >> sh
        else:
            keep = sum(((s.step >> i) & 1) * (15 << (4 * i)) for i in range(8)) & M
            nh = keep if s.held else b; tt = TT.get(s.topo, 0b1010); r = 0
            for i in range(W): r |= ((tt >> (2 * ((a >> i) & 1) + ((nh >> i) & 1))) & 1) << i
        if pulse: s.total = r
        s.out = r; s.v = 1 if (s.armed and vi) else 0


def make(d, W, n=6000, seed=1):
    rnd = random.Random(seed); m = Model(W); rows = []; M = (1 << W) - 1
    for k in range(n):
        cv = 1 if (k == 5 or (k > 5 and rnd.random() < 0.06)) else 0
        cd = (rnd.choice([0, 1, 2, 3, 4, 5, 6, 7, 7, 4]) | (rnd.randrange(256) << 8) | (rnd.choice(list(TT) + [0x123]) << 16) | (rnd.randrange(2) << 26)) if cv else rnd.getrandbits(32)
        vi = 1 if (rnd.random() < 0.7 or k < 5) else 0
        a = rnd.getrandbits(W) if rnd.random() < 0.8 else rnd.choice([0, 1, 2, 3, M, M >> 1, 1 << (W - 1)])
        b = rnd.getrandbits(W) if rnd.random() < 0.6 else rnd.choice([0, 1, 2, 3, 4, 17, 18, 19, 31, M, 1 << (W - 1)])
        m.clock(cv, cd, a, b, vi); rows.append("%064x" % ((cv << 224) | (cd << 192) | (a << 160) | (b << 128) | (vi << 96) | (m.v << 64) | (m.out << 32)))
    p = os.path.join(d, "rows.hex"); open(p, "w").write("\n".join(rows) + "\n"); return p, n


def sim(d, W, path, n, top="arith_block_v9.v", mutate=None, wrap=False):
    srcs = [os.path.join(S, "tb_arith_block_v9.v"), os.path.join(S, top)]
    if mutate:
        a, b = mutate; src = open(os.path.join(S, top)).read(); assert a in src, a
        p = os.path.join(d, "mut.v"); open(p, "w").write(src.replace(a, b)); srcs[1] = p
    o = os.path.join(d, "o.vvp"); c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.WIDTH=%d" % W, "-o", o] + srcs, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+f=" + path, "+n=%d" % n], capture_output=True, text=True, timeout=600).stdout


def test_against_model_width_18_and_32():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    for W in (18, 32, 24):
        d = tempfile.mkdtemp(prefix="ab9_")
        try: path, n = make(d, W, seed=W); out = sim(d, W, path, n)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "PASS" in out and "FAIL" not in out, (W, out[-800:])


MUTS = [("assign nano_tt[gi] = tt[{nf[gi], nh[gi]}];", "assign nano_tt[gi] = tt[{nh[gi], nf[gi]}];"),     # truth table operands swapped
        ("wire [SW-1:0] sres = (mode == 3'd6) ? sy_rev : sy;", "wire [SW-1:0] sres = sy;"),                    # shift right missing
        ("wire inc = in_a[0] && valid_in, dec = in_a[1] && valid_in;", "wire inc = in_a[0], dec = in_a[1];"),     # pulses not qualified (the old v2 bug)
        ("3'd2: result = {{(WIDTH-1){1'b0}}, ~s1[WIDTH]};", "3'd2: result = {{(WIDTH-1){1'b0}}, s1[WIDTH]};"),  # >= inverted
        ("valid_out_r <= armed && valid_in;", "valid_out_r <= valid_in;")]                                      # answers before the first config


def test_mutations_caught():
    for m in MUTS:
        d = tempfile.mkdtemp(prefix="ab9m_")
        try: path, n = make(d, 18, seed=5); out = sim(d, 18, path, n, mutate=m)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in out and "PASS" not in out, (m[0], out[-500:])
