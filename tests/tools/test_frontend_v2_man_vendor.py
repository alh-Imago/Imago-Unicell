"""tests/tools/test_frontend_v2_man_vendor.py - the vendor-aware Card/MAN page (frontend_v2 + man_generate_v2), 2 Nov 2026."""
import json, os, sys, threading, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import frontend_v2  # noqa: E402
import man_generate_v2  # noqa: E402

FACTS = os.path.join(ROOT, "docs", "man", "data", "xc7k480tffg1156.chipdb_facts.json")
COMMITTED = os.path.join(ROOT, "docs", "man", "ypcb-00338-1p1.man.json")
KINTEX = dict(card_id="x", part="XC7K480T", family="Xilinx Kintex-7", package="FFG1156", facts=FACTS, speed_grade="-1",
              clock_pin="AA28", clock_hz=50000000, clock_io="LVCMOS18", led_pins=["P30", "M30", "N30"], led_io="LVCMOS18", lut6_yosys=298600)


def test_xilinx_builder_reproduces_committed_kintex_device_section():
    man = man_generate_v2.build_man_xilinx(**KINTEX)
    old = json.load(open(COMMITTED))
    for k in ("logic", "dsp", "bram", "other_sites", "package_pins"):
        a, b = dict(man["device"][k]), dict(old["device"][k])
        a.pop("note", None); b.pop("note", None)
        assert a == b, k
    assert man["vendor"] == "xilinx"
    assert man["board"]["clock"]["SYS_CLK"]["pin"] == "AA28" and man["board"]["clock"]["SYS_CLK"]["freq_hz"] == 50000000


def test_blank_board_facts_stay_null_not_guessed():
    man = man_generate_v2.build_man_xilinx("c", "XC7K480T", "K", "FFG1156", FACTS)
    assert man["device"]["speed_grade"] is None and man["device"]["jtag_idcode"] is None
    assert "clock" not in man["board"] and "leds" not in man["board"]


def test_pin_not_in_package_is_refused():
    try:
        man_generate_v2.build_man_xilinx("c", "XC7K480T", "K", "FFG1156", FACTS, clock_pin="ZZ99")
    except ValueError as e:
        assert "ZZ99" in str(e)
    else:
        raise AssertionError("expected refusal")


def test_dispatcher_vendors():
    for v in ("gowin", "nonsense"):
        try:
            man_generate_v2.build_man(vendor=v)
        except ValueError:
            pass
        else:
            raise AssertionError(v)
    intel = man_generate_v2.build_man(vendor="intel", card_id="i", part="10AX066H2F34E2SG", family="Arria 10", jtag_idcode=None,
                                      alm_total=100, dsp_total=1, m20k_bits=None, clk_pin="PIN_A", led0_pin="PIN_B", led1_pin="PIN_C")
    assert "vendor" not in intel or intel["vendor"] != "xilinx"


def test_controller_xilinx_writes_file_and_cli(tmp_path):
    out = str(tmp_path / "k.man.json")
    r = frontend_v2.FrontendController().generate_man({
        "vendor": "xilinx", "card_id_x": "k", "part_x": "XC7K480T", "family_x": "Xilinx Kintex-7", "package_x": "FFG1156",
        "chip_facts": FACTS, "clock_pin": "AA28", "clock_hz": "50000000", "led_pins": "P30 M30,N30", "do_not": "never pull AC24 down\n",
        "pin_table": "extra.sysmon = AB1", "output": out})
    assert r["ok"], r
    man = json.load(open(out))
    assert man["board"]["leds"]["led[2]"] == "N30" and man["board"]["do_not"] == ["never pull AC24 down"] and man["board"]["extra_pins"] == {"sysmon": "AB1"}
    assert "man_generate_v2.py --vendor xilinx" in r["cli_equivalent"] and "--led-pin N30" in r["cli_equivalent"]


def test_controller_xilinx_errors(tmp_path):
    c = frontend_v2.FrontendController()
    assert not c.generate_man({"vendor": "xilinx", "output": "x"})["ok"]
    r = c.generate_man({"vendor": "xilinx", "card_id_x": "k", "part_x": "p", "package_x": "q", "chip_facts": str(tmp_path / "none.json"), "output": str(tmp_path / "o")})
    assert not r["ok"] and "not found" in r["error"]
    assert "not made on this page yet" in c.generate_man({"vendor": "gowin"})["error"]


def test_controller_intel_unchanged(tmp_path):
    out = str(tmp_path / "i.json")
    fields = dict(card_id="c", part="10AX066H2F34E2SG", alm_total="100", clk_pin="PIN_E23", led0_pin="PIN_AE7", led1_pin="PIN_AH2", output=out)
    a = frontend_v2.FrontendController().generate_man(fields)
    import frontend_v1
    out1 = str(tmp_path / "i1.json"); fields["output"] = out1
    b = frontend_v1.FrontendController().generate_man(fields)
    assert a["ok"] and b["ok"]
    ja, jb = json.load(open(out)), json.load(open(out1))
    ja.pop("generated", None); jb.pop("generated", None)
    assert ja == jb


def test_page_has_vendor_dropdown_and_posts_over_http(tmp_path):
    html = frontend_v2.page_man()
    assert 'name="vendor"' in html and "Xilinx" in html and "Gowin" in html and "function setVendor(v) {" in html
    srv = frontend_v2.serve(port=0)
    try:
        port = srv.server_address[1]
        out = str(tmp_path / "h.json")
        body = urllib.parse.urlencode({"vendor": "xilinx", "card_id_x": "k", "part_x": "XC7K480T", "package_x": "FFG1156", "chip_facts": FACTS, "output": out}).encode()
        page = urllib.request.urlopen(urllib.request.Request(f"http://localhost:{port}/man", data=body)).read().decode()
        assert "Wrote:" in page and os.path.exists(out)
    finally:
        srv.shutdown()
