"""tests/vm/test_hexn_morse_v1.py -- Hex-N (1 Nov 2026): the Morse-key demo (hexn_morse_top_v1) in simulation with a fast clock: S, O, 1, C, a word gap, 6 symbols (not a character), E, clear, O S O, sidetone. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); V = os.path.join(ROOT, "fpga", "verilog")
def test_morse_key_decodes_with_the_scorer_table():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_morse_gen_v1.py")], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnmorse_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, os.path.join(ROOT, "tests", "hexn_morse", "tb_hexn_morse_v1.v")] + [os.path.join(V, f) for f in ("hexn_morse_top_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hw262_shield_v2.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=900).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-800:]
