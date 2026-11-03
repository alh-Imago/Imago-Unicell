"""tests/vm/test_hexn_cross_v1.py -- the SERIAL<->PARALLEL CROSSING (sub/verilog/hexn_cross_v1.v, hexn_xtop_v1.v), 3 Nov 2026, Alan 10:07. (1) the loopback testbench with the real flex/sub bridge (6 words, latency, wipe); (2) programs on the PR/SQ pattern run with PARALLEL words in and PARALLEL words out: the words equal the serial run's words and the serial VM's, and the ticks are the serial ticks plus the constant 33 (32 bits + the registered valid). Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest
import test_hexn_pattern_prsq_v1 as T
import hexn_pattern_verify_v15 as V, hexn_cross_verify_v1 as X


def test_loopback_testbench_passes():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="cr_")
    try:
        o = os.path.join(d, "o.vvp"); v = os.path.join(ROOT, "sub/verilog")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, os.path.join(ROOT, "tests/hexn_cross_tb.v"), v + "/hexn_cross_v1.v", v + "/flex_sub_bridge_v1.v"], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        out = subprocess.run(["vvp", o], capture_output=True, text=True).stdout
        assert "PASS" in out and "FAIL" not in out and "TIMEOUT" not in out, out
        assert "LAT in->flag 2, flag->valid 32, in->held 35" in out, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("name", ["strict_xyz", "strict_yzx", "weighted", "sequenced_yxz"])
def test_parallel_in_parallel_out_equals_serial_run(name):
    t = T.TASKS[name]; prog = T._program(t); icm, program = T._load(prog, name)
    rnd = random.Random(7); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    ser = V.sim_run(T.REF, program, iv); par = X.xrun(T.REF, program, iv)
    for o in t[2]:
        assert [w for _, w in par["out"][o]] == [w for _, w in ser["out"][o]] and par["out"][o], (name, par["out"][o], ser["out"][o])
        assert [tk for tk, _ in par["out"][o]] == [tk + 33 for tk, _ in ser["out"][o]], name


def test_sequencer_through_the_crossing():
    t = ([T.N("s", "seq", ["trig"], cfg=dict(vals=[1000, 2000, 3000, 4000], len=3))], ["trig"], ["s"])
    prog = T._program(t); icm, program = T._load(prog, "seq")
    ser = V.sim_run(T.REF, program, {"trig": 5}); par = X.xrun(T.REF, program, {"trig": 5})
    assert [w for _, w in par["out"]["s"]] == [1000] and [tk for tk, _ in par["out"]["s"]] == [tk + 33 for tk, _ in ser["out"]["s"]]
