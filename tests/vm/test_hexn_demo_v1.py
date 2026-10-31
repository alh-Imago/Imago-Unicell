"""tests/vm/test_hexn_demo_v1.py -- Hex-N (1 Nov 2026): the reaction-game demo (hexn_demo_top_v1: shield buttons, millisecond counter, scorer, display, buzzer) in simulation with a fast clock. Requires iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "fpga", "verilog")
def test_reaction_game_rounds_and_judging():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    subprocess.run(["python3", os.path.join(ROOT, "tools", "hexn_demo_rom_v1.py")], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexndemo_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, os.path.join(ROOT, "tests", "hexn_demo", "tb_hexn_demo_v1.v")] + [os.path.join(V, f) for f in ("hexn_demo_top_v1.v", "hexn_demo_rom_v1.v", "hexn_scorer_v1.v", "hw262_shield_v1.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=900).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-800:]
