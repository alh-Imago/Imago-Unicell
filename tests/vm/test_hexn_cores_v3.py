"""tests/vm/test_hexn_cores_v3.py -- branch, merge and latch cores in serial RTL (2 Nov 2026, UCC v2): hexn_branch_core_v1 (3-way signed compare, route per outcome to out1 / out2 / both / neither, emit fixed / a / b / a-b), hexn_merge_core_v1 (A only / B only / arbitrate round robin / join-OR), hexn_latch_core_v1 (set / clear / toggle, clear wins). The branch and merge cores use the FIFO cell hexn_ramfifo_v8 from hexn_join_core_v2.v. Needs iverilog."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = lambda f: os.path.join(ROOT, "sub", "verilog", f)


def _run(tb, rtls):
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexncore3_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(ROOT, "tests", tb)] + [V(f) for f in rtls], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        return subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_branch_core():
    r = _run("hexn_branch_core_v1_tb.v", ["hexn_join_core_v2.v", "hexn_branch_core_v1.v"])
    assert "FAIL" not in r and "ALL PASS 60 tests" in r, r


def test_merge_core():
    r = _run("hexn_merge_core_v1_tb.v", ["hexn_join_core_v2.v", "hexn_merge_core_v1.v"])
    assert "FAIL" not in r and "ALL PASS" in r and r.count("PASS ") >= 5, r


def test_latch_core():
    r = _run("hexn_latch_core_v1_tb.v", ["hexn_latch_core_v1.v"])
    assert "FAIL" not in r and "ALL PASS" in r, r
