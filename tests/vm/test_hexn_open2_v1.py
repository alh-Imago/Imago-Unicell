"""tests/vm/test_hexn_open2_v1.py -- Hex-N open unit STAGE 2 (1 Nov 2026): loadable tables and binning in simulation. The simulated ESP32 writes tables into the scratch RAM, copies them into the Morse decode, glyph, Morse scorer and reaction scorer tables, sets linear bins, and the personalities change behaviour
with no new build; the factory defaults can be restored. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_morse_gen_v1 as G, hexn_demo_rom_v1 as DR, hexn_scorer_ref_v1 as R  # noqa: E402
FILES = ["hexn_open_top_v2.v", "spi_bridge_v2.v", "hexn_tabs_v1.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hw262_shield_v2.v"]
def table_words(rows):
    """rows: dict slot -> (T) for Morse jobs; builds LOAD words like the generator but with the given thresholds"""
    W = [[[0] * 16 for _ in range(8)] for _ in range(2)]
    for slot, T in rows.items():
        for b in range(12): W[1][slot][b] = -10 * max(0, T - b); W[0][slot][b] = -10 * max(0, b - (T - 1))
    return [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in list(range(12)) + [15]] + [R.w_bias(0)]
def write_hex(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (w & 0xFFFFFFFF) for w in words) + "\n")
def make_files(d):
    # decode table: default, but a single dot (length 1, bits 0 -> index 32) now means Q (16)
    dec = []
    for idx in range(256):
        ln, bits = idx >> 5, idx & 31
        ch = 63
        for k, c in enumerate(G.ORDER):
            m = G.MORSE[c]
            if len(m) == ln and int("".join("1" if x == "-" else "0" for x in m), 2) == bits: ch = k
        dec.append(ch)
    dec[32] = 16
    write_hex(d, "dec_custom.hex", dec)
    gly = [G.segbyte(G.SEG[c]) if i < 36 and (c := G.ORDER[i]) else 0xFF for i in range(64)]
    gly[62] = 0xFF; gly[63] = 0xBF; gly[18] = 0xA0
    write_hex(d, "gly_custom.hex", gly)
    write_hex(d, "morse_fast.hex", table_words({0: 3, 1: 4, 2: 8}))     # linear 32 ms bins: dash from bin 3 (96 ms), letter gap from bin 4 (128 ms), word gap from bin 8 (256 ms)
    W, bias = DR.demo_table()
    for b in range(12): W[1][1][b] = -10 * max(0, b - 6); W[0][1][b] = -10 * max(0, 7 - b)   # good hit only up to bin 6 (under 128 ms)
    write_hex(d, "react_strict.hex", [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12)] + [R.w_bias(bias)])
def test_open_unit_stage2_loadable_tables_and_bins():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnopen2_")
    try:
        make_files(d)
        tb = open(os.path.join(ROOT, "tests", "hexn_open2", "tb_hexn_open2_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in FILES], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o, "+dir=" + d], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1800:]
