"""tests/vm/test_man_ypcb_00338_1p1_v1.py -- the Kintex MAN file (2 Nov 2026): committed file equals the generator's output, the vendor-neutral reader accepts it, the Quartus reader refuses it clearly,
and it claims nothing it has no source for (every unrecorded figure is null)."""
import json, os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "tools", "man_gen"))
import gen_ypcb_00338_1p1_man as G
import flexsub_assemble_v1 as F
import project_assemble_v1 as P
PATH = os.path.join(ROOT, "docs", "man", "ypcb-00338-1p1.man.json")


def test_committed_equals_generator():
    assert json.load(open(PATH)) == json.loads(json.dumps(G.build()))


def test_readers():
    m = F.load_man_flexsub(PATH)
    assert m["vendor"] == "xilinx" and m["part"] == "XC7K480T" and m["card_id"].startswith("ypcb-00338-1p1") and m["native_width"] is None and m["dsp_blocks"] == 1920
    assert m["board"]["clock"]["SYS_CLK"]["pin"] == "AA28"
    with pytest.raises(ValueError, match="non-Intel"): P.load_man(PATH)


def test_claims_only_what_is_recorded():
    d = json.load(open(PATH)); lg = d["device"]["logic"]
    assert lg["lut_sites_nextpnr"] == 597200 == lg["slice" + "s"] * 8 == lg["ff_total"] and lg["lut6_yosys"] == 298600     # slices x 8 equals the nextpnr figure of the card-flow note
    for k in ("lut4_total", "native_width"): assert lg[k] is None
    assert d["device"]["jtag_idcode"] is None and d["synthesis"]["nowidelut"]["supported"] is None
    assert d["device"]["dsp"]["total_blocks"] == 1920 and d["device"]["bram"]["total_blocks"] == 955 and d["device"]["bram"]["ramb18_sites"] == 1910
    assert "AC24" in " ".join(d["board"]["do_not"])


def test_board_pins_exist_in_the_package_table():
    d = json.load(open(PATH)); t = d["device"]["package_pins"]["table"]
    assert d["device"]["package_pins"]["pads"] == 562 and len(t) == 555
    b = d["board"]
    for pin in [b["clock"]["SYS_CLK"]["pin"], b["leds"]["led[0]"], b["leds"]["led[1]"], b["leds"]["led[2]"], "AC24"]: assert pin in t, pin


def test_facts_rederive_from_the_chip_database_when_present():
    bba = "/mnt/user-data/uploads/xc7k480tffg1156.bba"
    if not os.path.exists(bba): pytest.skip("SKIP: chip database file not present; the committed facts file was not re-derived")
    import bba_read_v1 as R
    got = R.read(bba); want = json.load(open(G.FACTS))
    for k in ("sites", "slice_lut_sites", "slice_ff_sites", "packages", "pads"): assert got[k] == want[k], k
