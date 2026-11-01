"""tests/vm/test_hexn_open11_v1.py -- Hex-N open unit stage 7 (1 Nov 2026): table space 7 = the PATTERN BANK (64 x 32 RAM) in the generic load and save paths (hexn_open_top_v11 + hexn_tabs_v5), in simulation through the whole unit over SPI. Alan, 18:09.
Checks: all zero after power-up and a save of count 0 writes exactly 64 words; 64 words loaded and saved back equal; a load of 100 words drops the 36 beyond the bank (no wrap onto slots 0 to 35); a load of 10 words changes slots 0 to 9 only; the preset RAM is untouched; a save running past the scratch RAM writes nothing; the factory restore clears the bank. Mutants are caught. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog"); R = os.path.join(ROOT, "rtl")
sys.path.insert(0, HERE)
from test_spi_bridge_v1 import MASTER  # noqa: E402
FILES = [V + "/" + f for f in ("hexn_open_top_v11.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v5.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v4.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hexn_scorer_v3.v", "hw262_shield_v2.v")] + [R + "/hexn_neural_v1.v", R + "/hexn_tanh512_v1.v"]


def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (int(w) & 0xFFFFFFFF) for w in words) + "\n")


def run(d, tabs_text=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    rng = np.random.default_rng(11)
    for name, n in (("c_pat", 64), ("c_big", 128), ("c_new", 64)): hexfile(d, name + ".hex", rng.integers(1, 2**32, size=n, dtype=np.uint64))
    tb = open(os.path.join(ROOT, "tests", "hexn_open11", "tb_hexn_open11_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp"); files = list(FILES)
    if tabs_text is not None:
        p = os.path.join(d, "tabs_mut.v"); open(p, "w").write(tabs_text); files[4] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+dir=" + d], capture_output=True, text=True, timeout=3000).stdout


def test_pattern_bank_through_the_unit():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen11_")
    try: res = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-2500:]
    assert res.count("ok ") == 10, res[-2500:]


MUTS = [("4'd7: sv_data = pat_data;", "4'd7: sv_data = pr_data;"),                                                             # save reads the preset RAM
        ("pt_we = (sp == 4'd7) && (i[7:0] < 64);", "pt_we = (sp == 4'd7);"),                                                  # no end guard: words beyond 64 wrap
        ("pt_we = 1; wd = pdef(i[5:0]);", "pt_we = 0; wd = pdef(i[5:0]);"),                                                   # factory fill does not clear the bank
        ("pat[wa[5:0]] <= wdp;", "pat[wa[5:0] + 6'd1] <= wdp;"),                                                              # writes one slot off
        ("(sctl[31:28] <= 4'd7)", "(sctl[31:28] <= 4'd6)"),                                                                    # save of space 7 refused
        ("pr_we = (sp == 4'd5) && (i[7:0] < 64); pt_we", "pr_we = (sp == 4'd5 || sp == 4'd7) && (i[7:0] < 64); pt_we")]       # a load of space 7 also writes the presets


def test_mutations_caught():
    src = open(os.path.join(V, "hexn_tabs_v5.v")).read()
    for a, b in MUTS:
        assert a in src, a
        d = tempfile.mkdtemp(prefix="hexnopen11m_")
        try: res = run(d, src.replace(a, b))
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in res and "PASS" not in res, (a, res[-800:])
