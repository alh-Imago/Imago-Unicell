"""tests/vm/test_spi_bridge_v3.py -- spi_bridge_v3 (2 Nov 2026): v2 plus read-only register 11 = PATTERN_ID ([31:16] type, [15:0] version). Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE)
from test_spi_bridge_v1 import MASTER  # noqa: E402
TB = open(os.path.join(ROOT, "tests", "hexn_open", "tb_spi_bridge_v3.v")).read()


def _run(bridge_file, tb):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="spiv3_")
    try:
        tb = tb.replace("//MASTER//", MASTER.replace("wire miso;", "").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v"), os.path.join(V, bridge_file)], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        return subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_pattern_id_register():
    res = _run("spi_bridge_v3.v", TB)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1500:]


def test_mutant_register_not_wired_is_caught():
    src = open(os.path.join(V, "spi_bridge_v3.v")).read().replace("8'd11: regread = PATTERN_ID;", "")
    d = tempfile.mkdtemp(prefix="spiv3m_")
    try:
        open(os.path.join(d, "mut.v"), "w").write(src)
        tb = TB.replace("//MASTER//", MASTER.replace("wire miso;", "").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v"), os.path.join(d, "mut.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:800]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "FAIL" in res and "PASS" not in res
