"""Ledger #1036 addendum 6: the committed CORDIC unit bitstream package, the ESP32 sketch and the pin map agree with each other."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sd_unit_top_v1 as U

PKG = os.path.join(ROOT, "fpga", "build", "unit_cordic_v1")
INO = os.path.join(ROOT, "tools", "esp32", "unicell_unit_bridge", "unicell_unit_bridge.ino")


def test_committed_bitstream_package_uses_the_generators_pins():
    assert os.path.getsize(os.path.join(PKG, "unit_top.fs")) > 1_000_000
    cst = open(os.path.join(PKG, "unit_top.cst")).read()
    for name, pin in U.PINS.items():
        if "[" in name:
            continue
        assert re.search(r'IO_LOC "%s" %d;' % (re.escape(name), pin), cst), name


def test_esp32_sketch_wiring_matches_the_wiring_sheet():
    ino = open(INO).read()
    want = {"PIN_CS": 5, "PIN_SCLK": 18, "PIN_MOSI": 23, "PIN_MISO": 19, "PIN_READY": 34}
    for k, v in want.items():
        assert re.search(r"#define %s\s+%d\b" % (k, v), ino), k
    doc = open(os.path.join(ROOT, "docs", "playout_capture_v1.md")).read()
    for row in ("| CS_N | IO5 | 73 |", "| SCLK | IO18 | 74 |", "| MOSI | IO23 | 75 |", "| MISO | IO19 | 76 |", "| READY | IO34 | 77 |"):
        assert row in doc, row


def test_sketch_register_numbers_match_the_bridge():
    ino = open(INO).read()
    vhdl = open(os.path.join(ROOT, "fpga", "verilog", "spi_bridge_v1.v")).read()
    assert "UNIT_ID = 0x57320001" in ino and "0x57320001" in vhdl
    for name, n in (("R_ID", 0), ("R_STATUS", 1), ("R_CONTROL", 2), ("R_START_BLOCK", 3), ("R_NBLOCKS", 4), ("R_PLAY_COUNT", 5), ("R_CAP_COUNT", 6), ("R_SCRATCH", 7), ("R_MAX_OUT", 8), ("R_RPI", 9)):
        assert re.search(r"\b%s = %d\b" % (name, n), ino), name


WEB = os.path.join(ROOT, "tools", "esp32", "unicell_unit_web")


def test_web_sketch_link_layer_matches_the_bridge_and_wiring():
    link = open(os.path.join(WEB, "unit_link.h")).read()
    ino = open(os.path.join(WEB, "unicell_unit_web.ino")).read()
    for k, v in {"PIN_CS": 5, "PIN_SCLK": 18, "PIN_MOSI": 23, "PIN_MISO": 19, "PIN_READY": 34}.items():
        assert re.search(r"#define %s\s+%d\b" % (k, v), link), k
    assert "0x57320001" in link
    for name, n in (("R_ID", 0), ("R_STATUS", 1), ("R_CONTROL", 2), ("R_START_BLOCK", 3), ("R_NBLOCKS", 4), ("R_PLAY_COUNT", 5), ("R_CAP_COUNT", 6), ("R_SCRATCH", 7), ("R_MAX_OUT", 8), ("R_RPI", 9)):
        assert re.search(r"\b%s = %d\b" % (name, n), link), name
    for name, n in (("C_LOAD", 1), ("C_SAVE", 2), ("C_PLAY", 4), ("C_CAP_CLEAR", 8), ("C_CLEAR_DONE", 16), ("C_SD_REINIT", 32)):
        assert re.search(r"\b%s = %d\b" % (name, n), link), name
    assert "DESIGN_CORDIC 1" in ino and "/api/run" in ino and "Basic" in ino or "authenticate" in ino
