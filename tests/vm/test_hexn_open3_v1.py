"""tests/vm/test_hexn_open3_v1.py -- Hex-N open unit stage 4a (1 Nov 2026): MODE 3, RAW WORD STREAM, in simulation. A mixed stream of LOAD, BIAS and SCORE words is written into the scratch RAM over SPI, the engine feeds it to the scorer and writes the results back;
every result is compared with the bit-exact Python reference (hexn_scorer_ref_v1). Weights survive a mode change, the bias does not. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_scorer_ref_v1 as R  # noqa: E402
FILES = ["hexn_open_top_v3.v", "spi_bridge_v2.v", "hexn_tabs_v1.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v1.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hw262_shield_v2.v"]
def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (w & 0xFFFFFFFF) for w in words) + "\n")
def make(d):
    rng = np.random.default_rng(5)
    W = np.zeros((2, 8, 16), dtype=int); W[:, :, :12] = rng.integers(-127, 128, size=(2, 8, 12))
    bias1 = 37; bias2 = -123
    loads = [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12)]      # 192 words
    vec = lambda: [int(x) for x in rng.integers(0, 12, size=8)]
    s1 = loads + [R.w_bias(bias1)]; e1 = []
    for k in range(55):
        if k == 30:                                 # a LOAD in the middle of the stream changes later results
            W[1][3][5] = 99; s1.append(R.w_load(1, 3, 5, 99))
        v = vec(); s1.append(R.w_score(v)); e1.append(R.score(W, bias1, v)[0])
    assert len(s1) <= 255
    s2 = [R.w_bias(bias2)]; e2 = []
    for k in range(40): v = vec(); s2.append(R.w_score(v)); e2.append(R.score(W, bias2, v)[0])
    hexfile(d, "s1.hex", s1); hexfile(d, "e1.hex", e1); hexfile(d, "s2.hex", s2); hexfile(d, "e2.hex", e2)
    return len(s1), len(e1), len(s2), len(e2)
def _run(make_fn):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnopen3_")
    try:
        n1, r1, n2, r2 = make_fn(d)
        tb = open(os.path.join(ROOT, "tests", "hexn_open3", "tb_hexn_open3_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in FILES], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o, "+dir=" + d, "+n1=%d" % n1, "+r1=%d" % r1, "+n2=%d" % n2, "+r2=%d" % r2], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1800:]

def test_open_unit_stage4a_raw_word_stream():
    _run(make)
def make_real(d):
    """REAL River Exe rows: batch 1 = the int8 table (193 words) + 60 rows; batch 2 (after a mode change) = 150 more rows, weights kept, bias 0 as learned"""
    import hexn_raw_replay_v1 as P
    table, rows, exp, lab, af, ai = P.build(210)
    hexfile(d, "s1.hex", table + rows[:60]); hexfile(d, "e1.hex", exp[:60]); hexfile(d, "s2.hex", rows[60:]); hexfile(d, "e2.hex", exp[60:])
    return len(table) + 60, 60, 150, 150
def test_open_unit_stage4a_real_river_rows():
    _run(make_real)
