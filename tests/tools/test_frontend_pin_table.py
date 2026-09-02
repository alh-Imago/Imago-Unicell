"""tests/tools/test_frontend_pin_table.py -- points.md #599: real tests
for the frontend's new user-supplied pin-location table, both the raw
parser and the full generate_man() controller path (no live HTTP socket
needed, matching WorkbenchController's own established testing pattern)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import frontend_v1  # noqa: E402


def test_parse_pin_table_empty():
    assert frontend_v1.FrontendController._parse_pin_table("") == {"jtag": {}, "config": {}, "extra": {}}


def test_parse_pin_table_recognized_groups():
    raw = "jtag.tck = PIN_AH12\nconfig.nCONFIG = PIN_AF13\nextra.pcie_refclk_p = PIN_AB28"
    result = frontend_v1.FrontendController._parse_pin_table(raw)
    assert result["jtag"] == {"tck": "PIN_AH12"}
    assert result["config"] == {"nCONFIG": "PIN_AF13"}
    assert result["extra"] == {"pcie_refclk_p": "PIN_AB28"}


def test_parse_pin_table_unrecognized_group_falls_back_to_extra():
    result = frontend_v1.FrontendController._parse_pin_table("ddr4.reset = PIN_AC5")
    assert result["extra"] == {"ddr4.reset": "PIN_AC5"}


def test_parse_pin_table_no_dot_falls_back_to_extra():
    result = frontend_v1.FrontendController._parse_pin_table("some_pin = PIN_X1")
    assert result["extra"] == {"some_pin": "PIN_X1"}


def test_parse_pin_table_blank_lines_and_comments_ignored():
    raw = "\n# a comment\njtag.tck = PIN_AH12\n\n"
    result = frontend_v1.FrontendController._parse_pin_table(raw)
    assert result["jtag"] == {"tck": "PIN_AH12"}


def test_parse_pin_table_missing_equals_raises():
    try:
        frontend_v1.FrontendController._parse_pin_table("jtag.tck PIN_AH12")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "line 1" in str(e)


def test_parse_pin_table_missing_location_raises():
    try:
        frontend_v1.FrontendController._parse_pin_table("jtag.tck =")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "missing location" in str(e)


def test_generate_man_end_to_end_with_pin_table(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "test.man.json"
    fields = {
        "card_id": "web-test", "part": "10AX066H2F34E2SG", "family": "Arria 10",
        "alm_total": "251680", "dsp_total": "1687",
        "clk_pin": "PIN_E23", "led0_pin": "PIN_AE7", "led1_pin": "PIN_AH2",
        "pin_table": "jtag.tck = PIN_AH12\nconfig.nCONFIG = PIN_AF13\nextra.pcie_refclk_p = PIN_AB28",
        "output": str(out),
    }
    result = controller.generate_man(fields)
    assert result["ok"], result.get("error")
    man = json.loads(out.read_text())
    assert man["board"]["jtag"]["device_pins"] == {"tck": "PIN_AH12"}
    assert man["board"]["configuration"]["pins"] == {"nCONFIG": "PIN_AF13"}
    assert man["board"]["additional_pins"]["pins"] == {"pcie_refclk_p": "PIN_AB28"}
    # Real, honest check: the CLI-equivalent string shown to the user
    # must actually reproduce the same pins via the real CLI flags.
    assert "--jtag-pin tck=PIN_AH12" in result["cli_equivalent"]
    assert "--config-pin nCONFIG=PIN_AF13" in result["cli_equivalent"]
    assert "--extra-pin pcie_refclk_p=PIN_AB28" in result["cli_equivalent"]


def test_generate_man_malformed_pin_table_returns_error_not_exception():
    controller = frontend_v1.FrontendController()
    fields = {
        "card_id": "web-test", "part": "10AX066H2F34E2SG",
        "alm_total": "251680", "dsp_total": "1687",
        "clk_pin": "PIN_E23", "led0_pin": "PIN_AE7", "led1_pin": "PIN_AH2",
        "pin_table": "not a valid line",
        "output": "/tmp/unused.man.json",
    }
    result = controller.generate_man(fields)
    assert not result["ok"]
    assert "pin table line 1" in result["error"]
