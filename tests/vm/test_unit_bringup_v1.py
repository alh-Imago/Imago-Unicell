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


def test_quickstart_exists_and_readme_points_to_it_and_the_unit():
    q = open(os.path.join(ROOT, "quickstart.py")).read()
    assert "test_unit_designs_v1.py" in q and "unit_bringup_guide.md" in q
    readme = open(os.path.join(ROOT, "README.md")).read()
    assert "python3 quickstart.py" in readme and "The small unit: Tang Nano 20K" in readme
    assert "not wired yet (#888)" not in readme


def test_web_sketch_file_card_pins_are_off_the_unit_link_and_documented():
    ino = open(os.path.join(WEB, "unicell_unit_web.ino")).read()
    pins = {k: int(re.search(r"#define %s\s+(\d+)" % k, ino).group(1)) for k in ("FILE_CS", "FILE_SCK", "FILE_MOSI", "FILE_MISO")}
    assert pins == {"FILE_CS": 32, "FILE_SCK": 33, "FILE_MOSI": 25, "FILE_MISO": 26}
    assert not set(pins.values()) & {5, 18, 19, 23, 34}          # the unit link's pins
    assert not set(pins.values()) & {0, 2, 12, 15}               # strapping pins
    doc = open(os.path.join(ROOT, "docs", "unit_bringup_guide.md")).read()
    for row in ("| CS | IO32 |", "| CLK / SCK | IO33 |", "| MOSI / DI | IO25 |", "| MISO / DO | IO26 |"):
        assert row in doc, row


def test_web_sketch_has_the_live_sensor_feed_with_free_adc1_pins():
    """addendum 17: /api/live, sensors.h with ADC1-only default pins that do not clash with the unit link (5/18/19/23/34) or the file card (32/33/25/26)."""
    ino = open(os.path.join(WEB, "unicell_unit_web.ino")).read()
    h = open(os.path.join(WEB, "sensors.h")).read()
    assert '"/api/live"' in ino and '#include "sensors.h"' in ino
    used = {5, 18, 19, 23, 34, 32, 33, 25, 26}
    pins = [int(p) for p in re.findall(r'\{\s*"[^"]+",\s*\d+,\s*(\d+),', h)]
    assert pins and not (set(pins) & used) and all(32 <= p <= 39 for p in pins)
