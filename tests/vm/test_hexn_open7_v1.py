"""tests/vm/test_hexn_open7_v1.py -- Hex-N open unit stage 5a (1 Nov 2026): the REVERSE COPY (save) of the table spaces into the scratch RAM, in simulation through the whole unit over SPI (hexn_open_top_v7 + hexn_tabs_v3). Alan, 13:01.
Saved: the factory reaction table, a custom reaction table, a Morse table, the decode table (zero-extended 6 bits), the glyph table (8 bits) and the preset RAM; count 0 = the space's own size, exactly that many words written; a full cycle (save, restore factory defaults, load the saved words back) restores the table exactly; a save past scratch word 1023 and a save of a missing space write nothing. Mutations are caught. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE)
from test_spi_bridge_v1 import MASTER  # noqa: E402
FILES = ["hexn_open_top_v7.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v3.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v3.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hexn_scorer_v2.v", "hw262_shield_v2.v"]


def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (int(w) & 0xFFFFFFFF) for w in words) + "\n")


def run(d, tabs_text=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    rng = np.random.default_rng(5)
    for name, n in (("c_rt", 64), ("c_mt", 64), ("c_dec", 256), ("c_gly", 64), ("c_pre", 64)): hexfile(d, name + ".hex", rng.integers(1, 2**32, size=n, dtype=np.uint64))
    tb = open(os.path.join(ROOT, "tests", "hexn_open7", "tb_hexn_open7_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
    files = [os.path.join(V, f) for f in FILES]
    if tabs_text is not None:
        p = os.path.join(d, "tabs_mut.v"); open(p, "w").write(tabs_text); files[FILES.index("hexn_tabs_v3.v")] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+dir=" + d], capture_output=True, text=True, timeout=3000).stdout


def test_reverse_copy_through_the_unit():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen7_")
    try: res = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-2500:]
    assert res.count("ok ") == 13, res[-2500:]


def test_reverse_copy_mutations_caught():
    src = open(os.path.join(V, "hexn_tabs_v3.v")).read()
    muts = [("assign sv_addr = sbase[9:0] + {2'b00, i[7:0]};", "assign sv_addr = sbase[9:0] + {2'b00, i[7:0]} + 10'd1;"),      # address off by one
            ("4'd3: sv_data = {26'd0, dec_ch};", "4'd3: sv_data = rt_data;"),                                                      # decode table saves the wrong table
            ("if (i + 1 >= scnt || i == 255) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_SA; end", "if (i >= scnt || i == 255) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_SA; end"),   # one word too many
            ("({4'd0, sctl[27:16]} + scount_in <= 17'd1024)", "1'b1")]                                                            # no end-of-scratch guard
    for a, b in muts:
        assert a in src, a
        d = tempfile.mkdtemp(prefix="hexnopen7m_")
        try: res = run(d, src.replace(a, b))
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in res and "PASS" not in res, (a, res[-800:])
