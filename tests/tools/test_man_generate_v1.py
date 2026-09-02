"""tests/tools/test_man_generate_v1.py -- points.md #599: real tests for
man_generate_v1.build_man(), including the new user-supplied pin-location
feature (jtag_pins/config_pins/extra_pins). None of these tools had any
test coverage before this entry -- a real, honest gap closed here, not
just for the new feature but for build_man()'s pre-existing behavior too.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))

import man_generate_v1  # noqa: E402


BASE_ARGS = dict(
    card_id="test-card", part="10AX066H2F34E2SG", family="Arria 10",
    jtag_idcode=None, alm_total=251680, dsp_total=1687, m20k_bits=None,
    clk_pin="PIN_E23", led0_pin="PIN_AE7", led1_pin="PIN_AH2",
)


def test_build_man_minimal_unchanged():
    """Backward compatibility: calling with only the original required
    args (no pin tables) still produces a valid, loadable MAN structure
    with empty pin tables, not an error."""
    man = man_generate_v1.build_man(**BASE_ARGS)
    assert man["card_id"] == "test-card"
    assert man["device"]["part"] == "10AX066H2F34E2SG"
    assert man["board"]["clock"]["CLK_100M"]["pin"] == "PIN_E23"
    assert man["board"]["leds"]["LED0_N"] == "PIN_AE7"
    assert man["board"]["jtag"]["device_pins"] == {}
    assert man["board"]["configuration"]["pins"] == {}
    assert man["board"]["additional_pins"]["pins"] == {}


def test_build_man_jtag_pins_populate_device_pins():
    man = man_generate_v1.build_man(**BASE_ARGS, jtag_pins={"tck": "PIN_AH12", "tdi": "PIN_AH13"})
    assert man["board"]["jtag"]["device_pins"] == {"tck": "PIN_AH12", "tdi": "PIN_AH13"}
    # Real, honest note updates when real user data is present.
    assert "NOT independently verified" in man["board"]["jtag"]["note"]


def test_build_man_config_pins_populate_configuration_block():
    man = man_generate_v1.build_man(**BASE_ARGS, config_pins={"nCONFIG": "PIN_AF13"})
    assert man["board"]["configuration"]["pins"] == {"nCONFIG": "PIN_AF13"}
    assert "NOT independently verified" in man["board"]["configuration"]["note"]


def test_build_man_config_pins_empty_keeps_old_note():
    """Real, honest regression guard: when no config pins are given, the
    note should read exactly as before this feature existed."""
    man = man_generate_v1.build_man(**BASE_ARGS)
    assert man["board"]["configuration"]["note"] == "not populated by this generator"


def test_build_man_extra_pins_populate_additional_pins():
    man = man_generate_v1.build_man(**BASE_ARGS, extra_pins={"pcie_refclk_p": "PIN_AB28"})
    assert man["board"]["additional_pins"]["pins"] == {"pcie_refclk_p": "PIN_AB28"}
    assert "user-supplied" in man["board"]["additional_pins"]["note"]
    assert "NEVER auto-parsed" in man["board"]["additional_pins"]["note"]


def test_build_man_pin_dicts_are_copied_not_aliased():
    """Mutating the caller's dict after the call must not affect the
    already-built MAN structure."""
    src = {"tck": "PIN_AH12"}
    man = man_generate_v1.build_man(**BASE_ARGS, jtag_pins=src)
    src["tck"] = "MUTATED"
    assert man["board"]["jtag"]["device_pins"]["tck"] == "PIN_AH12"


def test_cli_jtag_pin_repeatable(tmp_path):
    """Real, end-to-end CLI test: --jtag-pin/--config-pin/--extra-pin are
    repeatable and land in the right schema slots."""
    out = tmp_path / "test.man.json"
    argv = [
        "man_generate_v1.py",
        "--card-id", "cli-test", "--part", "10AX066H2F34E2SG",
        "--alm-total", "251680", "--dsp-total", "1687",
        "--clk-pin", "PIN_E23", "--led0-pin", "PIN_AE7", "--led1-pin", "PIN_AH2",
        "--jtag-pin", "tck=PIN_AH12", "--jtag-pin", "tdi=PIN_AH13",
        "--config-pin", "nCONFIG=PIN_AF13",
        "--extra-pin", "pcie_refclk_p=PIN_AB28",
        "-o", str(out),
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        rc = man_generate_v1.main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    import json
    man = json.loads(out.read_text())
    assert man["board"]["jtag"]["device_pins"] == {"tck": "PIN_AH12", "tdi": "PIN_AH13"}
    assert man["board"]["configuration"]["pins"] == {"nCONFIG": "PIN_AF13"}
    assert man["board"]["additional_pins"]["pins"] == {"pcie_refclk_p": "PIN_AB28"}


def test_cli_malformed_pin_arg_raises(tmp_path):
    out = tmp_path / "test.man.json"
    argv = [
        "man_generate_v1.py",
        "--card-id", "cli-test", "--part", "10AX066H2F34E2SG",
        "--alm-total", "251680", "--dsp-total", "1687",
        "--clk-pin", "PIN_E23", "--led0-pin", "PIN_AE7", "--led1-pin", "PIN_AH2",
        "--jtag-pin", "tck-no-equals-sign",
        "-o", str(out),
    ]
    old_argv = sys.argv
    sys.argv = argv
    try:
        try:
            man_generate_v1.main()
            assert False, "expected SystemExit for malformed --jtag-pin"
        except SystemExit:
            pass
    finally:
        sys.argv = old_argv
