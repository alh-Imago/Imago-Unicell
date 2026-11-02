"""tests/vm/test_hexn_ramroute_v6.py -- the trigger-driven RAM-routing cell (sub/verilog/hexn_ramroute_v6.v, Alan 09:02: a 'high' pulse sets it off, it resets itself when empty): hold with release after 40, 5, 20, 31 and 33 clocks (late and early stream-out, five different words, one after another through the same cell, which also shows the reset), repeat (two replays). Needs iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ramroute_v6_trigger_hold_repeat():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnrr6_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(ROOT, "tests", "hexn_ramroute_tb_v2.v"), os.path.join(ROOT, "sub", "verilog", "hexn_ramroute_v6.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        r = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "FAIL" not in r and "ALL PASS" in r and r.count("PASS ") >= 8, r
