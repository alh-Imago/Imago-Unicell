"""tests/vm/test_hexn_open6_v1.py -- Hex-N open unit stage 4c (1 Nov 2026): the CLEAR control word of the raw engine v3 / scorer v2, in simulation. Everything stage 4b proved is repeated on the v6 top (presets, two judges, the pin routing), then:
after two different tables are loaded into judge A and judge B, the control word 0xE000000B clears judge B only (A must still give the reference answers, B must give all zeros), and 0xE000000C clears both (every answer zero). Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import test_hexn_open5_v1 as T5  # noqa: E402
import numpy as np, hexn_scorer_ref_v1 as R  # noqa: E402
FILES = ["hexn_open_top_v6.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v2.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v3.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hexn_scorer_v2.v", "hw262_shield_v2.v"]
EXTRA = r'''
        // ---- CLEAR: judge B only, then both
        for (i = 0; i < n3; i = i + 1) wbuf[i] = s3[i]; wr_words(16'd0, n3);
        wr_reg(8'd24, (600 << 16) | n3); seq = seq + 1; wr_reg(8'd25, seq); repeat (20) @(negedge clk); wait_raw;
        rd_words(16'd600, nr3); bad = 0; for (i = 0; i < nr3; i = i + 1) if (rbuf[i] !== e3[i]) bad = bad + 1;
        check(bad == 0, "clear B: A kept, B zero");
        for (i = 0; i < n4; i = i + 1) wbuf[i] = s4[i]; wr_words(16'd0, n4);
        wr_reg(8'd24, (600 << 16) | n4); seq = seq + 1; wr_reg(8'd25, seq); repeat (20) @(negedge clk); wait_raw;
        rd_words(16'd600, nr4); bad = 0; for (i = 0; i < nr4; i = i + 1) if (rbuf[i] !== 32'h0) bad = bad + 1;
        check(bad == 0, "clear both: all zero");
'''
def make(d):
    n, nr = T5.make(d)
    rng = np.random.default_rng(11)                                 # same generator and order as T5.make, to recover the two tables and the biases
    WA = np.zeros((2, 8, 16), dtype=int); WB = np.zeros((2, 8, 16), dtype=int)
    WA[:, :, :12] = rng.integers(-60, 61, size=(2, 8, 12)); WB[:, :, :12] = rng.integers(-60, 61, size=(2, 8, 12))
    Z = np.zeros((2, 8, 16), dtype=int); rows = [[int(x) for x in rng.integers(0, 12, size=8)] for _ in range(6)]
    s3 = [(14 << 28) | 0xB, (14 << 28) | 1] + [R.w_score(v) for v in rows]; e3 = []
    for v in rows: e3 += [R.score(WA, 25, v)[0], R.score(Z, 0, v)[0]]
    s4 = [(14 << 28) | 0xC, (14 << 28) | 1] + [R.w_score(v) for v in rows]
    T5.hexfile(d, "s3.hex", s3); T5.hexfile(d, "e3.hex", e3); T5.hexfile(d, "s4.hex", s4)
    return n, nr, len(s3), len(e3), len(s4), 2 * len(rows)
def test_open_unit_stage4c_clear_control_word():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnopen6_")
    try:
        n, nr, n3, nr3, n4, nr4 = make(d)
        tb = open(os.path.join(ROOT, "tests", "hexn_open5", "tb_hexn_open5_v1.v")).read().replace("hexn_open_top_v5", "hexn_open_top_v6")
        tb = tb.replace("reg [31:0] pset [0:63];", "reg [31:0] pset [0:63]; reg [31:0] s3 [0:63]; reg [31:0] e3 [0:63]; reg [31:0] s4 [0:63]; integer n3, nr3, n4, nr4;")
        tb = tb.replace('if (!$value$plusargs("dir=%s", dir)', 'if (!$value$plusargs("n3=%d", n3) || !$value$plusargs("nr3=%d", nr3) || !$value$plusargs("n4=%d", n4) || !$value$plusargs("nr4=%d", nr4)) begin $display("FAIL args"); $finish; end\n        if (!$value$plusargs("dir=%s", dir)')
        tb = tb.replace('$sformat(fn, "%0s/preset.hex", dir);', '$sformat(fn, "%0s/s3.hex", dir); $readmemh(fn, s3); $sformat(fn, "%0s/e3.hex", dir); $readmemh(fn, e3); $sformat(fn, "%0s/s4.hex", dir); $readmemh(fn, s4);\n        $sformat(fn, "%0s/preset.hex", dir);')
        tb = tb.replace('        if (fails == 0) $display("PASS");', EXTRA + '        if (fails == 0) $display("PASS");')
        tb = tb.replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in FILES], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o, "+dir=" + d, "+ns=%d" % n, "+nr=%d" % nr, "+n3=%d" % n3, "+nr3=%d" % nr3, "+n4=%d" % n4, "+nr4=%d" % nr4], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "ok clear B: A kept, B zero" in res and "ok clear both: all zero" in res, res[-1800:]
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1800:]
