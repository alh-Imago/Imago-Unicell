"""Ledger #1036 addendum 6: the committed CORDIC unit bitstream package, the ESP32 sketch and the pin map agree with each other."""
import os, re, shutil, subprocess, sys, tempfile
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
    dh = open(os.path.join(WEB, "design.h")).read()
    assert all(k in dh for k in ('"cordic"', '"relay"', '"tree"')) and "/api/run" in ino and ("Basic" in ino or "authenticate" in ino)


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


def test_install_option_packaging_and_reorganisation_hold_together():
    """addendum 20: quickstart --install exists (dry run does nothing), the nine experimental scripts live under tools/experimental, the three dead shells are archived."""
    q = subprocess.run([sys.executable, os.path.join(ROOT, "quickstart.py"), "--install", "--dry-run"], capture_output=True, text=True)
    assert q.returncode == 0 and "dry run" in q.stdout and "yowasp-yosys" in q.stdout
    for n in ("chaos_topology_v1", "flow_demo_v1", "lif_demo_v1", "measure_cell_width_v1", "measure_flag_across_families_v1", "measure_flag_pnr_v1", "placement_extract_v1",
              "experimental_3d_chaos_run_v1", "experimental_3d_crossing_demo_v1"):
        assert os.path.exists(os.path.join(ROOT, "tools", "experimental", n + ".py")), n
    for n in ("corner_shell_v1", "cross_shell_v1", "merge_shell_v1"):
        assert os.path.exists(os.path.join(ROOT, "fpga", "archive", "older_cores", n + ".v")) and not os.path.exists(os.path.join(ROOT, "fpga", "verilog", n + ".v"))
    assert os.path.exists(os.path.join(ROOT, "tools", "make_package_v1.py")) and os.path.exists(os.path.join(ROOT, "fpga", "verilog", "VERSIONS.md"))


def test_web_page_lives_in_a_header_and_is_valid_javascript():
    """addendum 28: the Arduino IDE injected function prototypes into the page when it sat in the .ino (page dead on the real board). The page is in page.h; the .ino holds no raw string, and the script parses."""
    ino = open(os.path.join(WEB, "unicell_unit_web.ino")).read()
    page = open(os.path.join(WEB, "page.h")).read()
    assert 'R"HTML(' not in ino and '#include "page.h"' in ino
    m = re.search(r'R"HTML\((.*?)\)HTML"', page, re.S)
    assert m and "#line" not in m.group(1)
    js = re.search(r"<script>(.*?)</script>", m.group(1), re.S).group(1)
    if shutil.which("node"):
        p = os.path.join(tempfile.mkdtemp(), "page.js")
        open(p, "w").write(js)
        r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:500]


def test_design_and_sensor_choice_is_runtime_not_a_sketch_edit():
    """addendum 33: no compile-time DESIGN_ switch left in the .ino; design.h holds the three designs; /api/config exists; the Setup card is in the page; every default sensor index is valid."""
    ino = open(os.path.join(WEB, "unicell_unit_web.ino")).read()
    dh = open(os.path.join(WEB, "design.h")).read()
    page = open(os.path.join(WEB, "page.h")).read()
    h = open(os.path.join(WEB, "sensors.h")).read()
    assert not re.search(r"^\s*#define\s+DESIGN_", ino, re.M) and "#define LANES" not in ino
    assert '"/api/config"' in ino and 'id="cfgsave"' in page and "design_index" in dh
    n = len(re.findall(r'^\s*\{\s*"[^"]+",\s*\d+,\s*-?\d+,', h, re.M))
    assert n >= 4                                           # enough sensors for the 4-lane tree defaults 0..3
    assert re.search(r"MAX_LANES 4", dh) and re.search(r"g_laneSensor\[MAX_LANES\] = \{ 0, 1, 2, 3 \}", dh)


def test_design_id_register_agrees_between_generator_bridge_sketch_and_packages():
    """Register 10 (DESIGN_ID): the bridge exposes it, the generator sets it, the sketch knows the same ids, and each committed package carries its own."""
    vlog = open(os.path.join(ROOT, "fpga", "verilog", "spi_bridge_v1.v")).read()
    assert "8'd10: regread = DESIGN_ID" in vlog
    dh = open(os.path.join(WEB, "design.h")).read()
    ul = open(os.path.join(WEB, "unit_link.h")).read()
    assert re.search(r"R_DESIGN_ID = 10", ul)
    import json
    for key, top, pkg in (("cordic", "icm_cordic_z_convergence_flex", "unit_cordic_v1"), ("relay", "icm_small_relay_chain_flex", "unit_relay_v1"), ("tree", "icm_parallel_reduction_tree_flex", "unit_tree_v1")):
        want = U.design_id(top)
        assert re.search(r'"%s".*0x%08XUL' % (key, want), dh, re.I), key
        info = json.load(open(os.path.join(ROOT, "fpga", "build", pkg, "lanes.json")))
        assert int(info["design_id"], 16) == want, pkg
    assert len({U.design_id(t) for t in U.KNOWN_IDS}) == 3
