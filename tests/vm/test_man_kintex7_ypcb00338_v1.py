"""test_man_kintex7_ypcb00338_v1.py -- ledger #1235: the MAN file for the Kintex-7 card (board YZCA-00338-104).

Protects: the committed MAN and .xdc are exactly what the generator writes; the identity facts that were measured
(JTAG IDCODE) are in it; the vendor-neutral readers (identity, Flex-Sub assembler, VM mirror) accept it; the Quartus
loader refuses it clearly; the pins agree with the constraints in the bring-up kit and in the k7_tree4 kit; and the
MAN does not claim more than was verified (no schematic check, no chip database, designs run on the card).
"""
import json
import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "man_gen"))

import flexsub_assemble_v1 as fa  # noqa: E402
import gen_kintex7_ypcb00338_man_v1 as gen  # noqa: E402
import project_assemble_v1 as pa  # noqa: E402
import vm_mirror_v1 as vmm  # noqa: E402

MAN_PATH = gen.MAN_PATH
XDC_PATH = gen.XDC_PATH
MAN = json.load(open(MAN_PATH))


def test_the_committed_files_are_exactly_what_the_generator_writes():
    assert open(MAN_PATH).read() == json.dumps(gen.build(), indent=1, ensure_ascii=False) + "\n"
    assert open(XDC_PATH).read() == gen.build_xdc()


def test_identity_and_the_measured_idcode():
    assert MAN["vendor"] == "xilinx" and MAN["man_version"] == "1.0"
    assert MAN["device"]["part"] == "XC7K480T-FFG1156"
    assert MAN["device"]["jtag_idcode"] == "0x23751093"          # read on the card, ledger #1189
    assert MAN["device"]["alm_total"] is None and MAN["device"]["logic"]["unit"] == "LUT6"
    assert MAN["device"]["logic"]["lut6_total"] == MAN["device"]["logic"]["slices"] * 4


def test_the_xdc_pins_agree_with_the_man_and_with_the_bringup_kits():
    b = MAN["board"]
    want = {"CLK": b["clock"]["CLK"]["pin"], "LED0": b["leds"]["LED0"]["pin"],
            "LED1": b["leds"]["LED1"]["pin"], "LED2": b["leds"]["LED2"]["pin"]}
    for path in (XDC_PATH, os.path.join(ROOT, "fpga", "kintex7_bringup", "blink_k7_v1.xdc"),
                 os.path.join(ROOT, "fpga", "kintex7_tests", "k7_tree4", "k7_tree4_v1.xdc")):
        got = dict(re.findall(r"PACKAGE_PIN\s+(\w+)\s+\[get_ports (\w+)\]", open(path).read()))
        got = {port: pin for pin, port in got.items()}
        assert got == want, path
    assert len(set(want.values())) == 4, "no pin used twice"


def test_the_vendor_neutral_readers_accept_it_and_the_quartus_loader_refuses_it_clearly():
    assert pa.load_man_identity(MAN_PATH)["card_id"] == MAN["card_id"]
    info = fa.load_man_flexsub(MAN_PATH)
    assert info["vendor"] == "xilinx" and info["logic_unit"] == "LUT6" and info["dsp_blocks"] == 1920
    assert vmm.load_mirror_bounds(MAN_PATH, 4).card_id == MAN["card_id"]
    with pytest.raises(ValueError, match="non-Intel"):
        pa.load_man(MAN_PATH)


def test_the_man_does_not_claim_more_than_was_verified():
    v = MAN["verification"]
    assert v["schematic"] == "NOT CHECKED"
    assert v["chip_database"].startswith("NOT READ")
    assert "seen by eye" in v["designs_run_on_card"], "the k7_tree4 result is a visual observation and the MAN must say so"
    assert MAN["device"]["logic"]["ff_total"] is None and MAN["device"]["bram"]["total"] is None
    assert MAN["cell_costs"]["measured"] is None
    assert MAN["capabilities"]["uart"] is False and MAN["capabilities"]["leds"] == 3
    assert "feasibility NOT verified" in MAN["board"]["io_available"]
    assert MAN["board"]["clock"]["CLK"]["status"].count("not been measured") == 1
