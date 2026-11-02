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
    assert m["vendor"] == "xilinx" and m["part"] == "XC7K480T" and m["card_id"].startswith("ypcb-00338-1p1") and m["native_width"] is None and m["dsp_blocks"] is None
    assert m["board"]["clock"]["SYS_CLK"]["pin"] == "AA28"
    with pytest.raises(ValueError, match="non-Intel"): P.load_man(PATH)


def test_claims_only_what_is_recorded():
    d = json.load(open(PATH))
    assert d["device"]["logic"]["lut_sites_nextpnr"] == 597200 and d["device"]["logic"]["lut6_yosys"] == 298600
    for k in ("lut4_total", "ff_total", "native_width"): assert d["device"]["logic"][k] is None
    assert d["device"]["dsp"]["total_blocks"] is None and d["device"]["bram"]["total_blocks"] is None and d["device"]["jtag_idcode"] is None
    assert "NONE" in d["verification"]["chip_database"] and "AC24" in " ".join(d["board"]["do_not"])
