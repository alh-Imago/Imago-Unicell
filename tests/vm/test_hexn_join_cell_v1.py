"""tests/vm/test_hexn_join_cell_v1.py -- the serial JOIN cell (sub/verilog/hexn_join_cell_v1.v): two one-word FIFO cells feed a serial adder, the AND of their 'have' flags releases both. Operand B starts 0, 1, 7, 20, 31, 33 or 45 clocks after A, or before it by 1, 7, 31, 33, 45 clocks; twelve rounds in a row through the same cell must all give the right sum (so the cell also re-arms itself). An OR instead of the AND must fail. Needs iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(extra):
    d = tempfile.mkdtemp(prefix="hexnjn_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb"] + extra + ["-o", o, os.path.join(ROOT, "tests", "hexn_join_cell_tb_v1.v"), os.path.join(ROOT, "sub", "verilog", "hexn_join_cell_v1.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        return subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_join_cell_any_arrival_order():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    r = _run([])
    assert "FAIL" not in r and "ALL PASS" in r and sum(1 for l in r.splitlines() if l.startswith("PASS join")) == 12, r


def test_join_cell_or_instead_of_and_fails():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    assert "SOME FAILED" in _run(["-P", "tb.OR_BUG=1"])
