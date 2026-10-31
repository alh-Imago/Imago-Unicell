"""tests/vm/test_hexn_open_v1.py -- Hex-N open unit stage 1 (1 Nov 2026): one build (hexn_open_top_v1), personality chosen over simulated SPI: ID 0x57320002, config register write and read-back, a 64-word and a 200-word write/read through the scratch RAM (the transfers that fail on spi_bridge_v1),
then MODE 1 (reaction game) and MODE 2 (Morse key) selected by register: the chosen one runs, the other stays idle, and switching back and forth restarts each. Requires iverilog."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
FILES = ["hexn_open_top_v1.v", "spi_bridge_v2.v", "hexn_react_core_v1.v", "hexn_morse_core_v1.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hw262_shield_v2.v"]
TB = open(os.path.join(ROOT, "tests", "hexn_open", "tb_hexn_open_v1.v")).read()
def test_open_unit_modes_and_long_transfers():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_demo_rom_v1.py")], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_morse_gen_v1.py")], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnopen_")
    try:
        tb = TB.replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in FILES], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1500:]
