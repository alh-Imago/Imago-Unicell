"""tests/vm/test_hexn_ramroute_v1.py -- the one-word FIFO RAM-routing cell (sub/verilog/hexn_ramroute_v5.v, UCC v2 prototype, 2 Nov 2026): pass-through routing, hold with delay 1, 10, 31, 32, 50 (early stream-out and whole-word wait), repeat (two replays). Needs iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ramroute_pass_hold_repeat():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnrr_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(ROOT, "tests", "hexn_ramroute_tb_v1.v"), os.path.join(ROOT, "sub", "verilog", "hexn_ramroute_v5.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        r = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "FAIL" not in r and "ALL PASS" in r and r.count("PASS hold") == 5 and r.count("PASS repeat") == 2, r
