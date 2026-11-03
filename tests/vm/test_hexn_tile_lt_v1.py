"""tests/vm/test_hexn_tile_lt_v1.py -- the LATCH tile (hexn_tile_lt_v1 on hexn_latch_core_v2), 3 Nov 2026. RTL only: the planner does not simulate the latch (a held level, not a word), so this checks the tile alone - set from W, clear from N, toggle from S, clear wins over set, level on the E data lane with flag 0, and the wipe. Requires iverilog."""
import os, shutil, subprocess, tempfile
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys_cfg = os.path.join(ROOT, "tools")


def test_latch_tile_testbench_passes():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="lt_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, os.path.join(ROOT, "tests/hexn_tile_lt_tb.v"), os.path.join(ROOT, "sub/verilog/hexn_tile_lt_v1.v"), os.path.join(ROOT, "sub/verilog/hexn_latch_core_v2.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        out = subprocess.run(["vvp", o], capture_output=True, text=True).stdout
        assert "PASS" in out and "FAIL" not in out, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_latch_config_word_roundtrip():
    import sys; sys.path.insert(0, sys_cfg)
    import hexn_tile_cfg_lt_v1 as L
    w = L.pack({"N": "W"}, "W", "N", "S", ("E",))
    u = L.unpack(w)
    assert L.width(4) == 25 and u["sels"] == 3 and u["selc"] == 0 and u["selt"] == 2 and u["result_to"] == [1] and u["route"][0] == 3
