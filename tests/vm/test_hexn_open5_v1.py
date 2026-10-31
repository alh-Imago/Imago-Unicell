"""tests/vm/test_hexn_open5_v1.py -- Hex-N open unit stage 4b (1 Nov 2026): PRESETS and the SECOND TABLE (two judges), in simulation. Factory presets start the games with no mode register written; a custom preset loaded into table space 5 moves buttons and buzzer in one write;
a raw stream with control words loads judge A and judge B (different tables) and every result (A, B per row) equals the bit-exact reference. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_scorer_ref_v1 as R  # noqa: E402
FILES = ["hexn_open_top_v5.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v2.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v2.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hw262_shield_v2.v"]
def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (w & 0xFFFFFFFF) for w in words) + "\n")
def make(d):
    # preset RAM: presets 0..3 are the factory ones, preset 5 (psel 6) is custom
    p = [0] * 64
    p[0 * 8] = 1; p[1 * 8] = 2; p[2 * 8] = 3; p[3 * 8] = 3; p[3 * 8 + 6] = 1
    p[5 * 8] = 1; p[5 * 8 + 4] = 9 | (11 << 4) | (9 << 8); p[5 * 8 + 5] = (12 ^ 6) << 12
    hexfile(d, "preset.hex", p)
    rng = np.random.default_rng(11)
    WA = np.zeros((2, 8, 16), dtype=int); WB = np.zeros((2, 8, 16), dtype=int)
    WA[:, :, :12] = rng.integers(-60, 61, size=(2, 8, 12)); WB[:, :, :12] = rng.integers(-60, 61, size=(2, 8, 12))
    ld = lambda W: [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12)]
    CTRL = lambda jc: (14 << 28) | jc
    # preset 4 starts with jc = 1 (two judges, loads to A). Load A; switch to loads-to-B (jc 3); load B and its bias; back to loads-to-A (jc 1); A's bias; then rows.
    s = ld(WA) + [CTRL(3)] + ld(WB) + [R.w_bias(-17), CTRL(1), R.w_bias(25)]
    e = []
    for k in range(20):
        v = [int(x) for x in rng.integers(0, 12, size=8)]; s.append(R.w_score(v)); e += [R.score(WA, 25, v)[0], R.score(WB, -17, v)[0]]
    assert len(s) <= 512
    hexfile(d, "stream.hex", s); hexfile(d, "expect.hex", e)
    return len(s), len(e)
def test_open_unit_stage4b_presets_and_two_judges():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnopen5_")
    try:
        ns, nr = make(d)
        tb = open(os.path.join(ROOT, "tests", "hexn_open5", "tb_hexn_open5_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in FILES], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o, "+dir=" + d, "+ns=%d" % ns, "+nr=%d" % nr], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1800:]
