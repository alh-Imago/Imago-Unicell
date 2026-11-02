"""tests/vm/test_hexn_cores_v2.py -- the serial work cores of 2 Nov 2026 (UCC v2): the two-input JOIN core with add, sub, and, or, xor, lt, min, max (sub/verilog/hexn_join_core_v2.v) and the one-input core with copy, shift left, shift right, mask, invert and accumulate (sub/verilog/hexn_unary_core_v1.v). Operands start at different clocks; edge words included. An OR in place of the AND must fail. Needs iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(tb, rtl, extra=()):
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexncore_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb"] + list(extra) + ["-o", o, os.path.join(ROOT, "tests", tb), os.path.join(ROOT, "sub", "verilog", rtl)], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        return subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_join_core_all_ops():
    r = _run("hexn_join_core_v2_tb.v", "hexn_join_core_v2.v")
    assert "FAIL" not in r and "ALL PASS 80 tests" in r and sum(1 for l in r.splitlines() if l.startswith("PASS op")) == 8, r


def test_join_core_or_instead_of_and_fails():
    assert "SOME FAILED" in _run("hexn_join_core_v2_tb.v", "hexn_join_core_v2.v", ["-P", "tb.OR_BUG=1"])


def test_unary_core_all_ops():
    r = _run("hexn_unary_core_v1_tb.v", "hexn_unary_core_v1.v")
    assert "FAIL" not in r and "ALL PASS 137 tests" in r, r
