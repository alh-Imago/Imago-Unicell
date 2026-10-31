"""tests/vm/test_hexn_open4_v1.py -- Hex-N open unit stage 3, the PIN MATRIX (1 Nov 2026), in simulation: with all pool registers at 0 the wiring is the original one; the ESP32 can move the three buttons and the buzzer to other pool pins at run time
(the old pins go quiet), and the status register shows the live level of all 16 pool pins. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
FILES = ["hexn_open_top_v4.v", "hexn_pins_v1.v", "spi_bridge_v2.v", "hexn_tabs_v1.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v1.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hw262_shield_v2.v"]
def test_open_unit_stage3_pin_matrix():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    d = tempfile.mkdtemp(prefix="hexnopen4_")
    try:
        tb = open(os.path.join(ROOT, "tests", "hexn_open4", "tb_hexn_open4_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
        open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in FILES], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-1800:]
