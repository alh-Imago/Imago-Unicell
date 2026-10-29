"""The Bench v7: Make-a-design can build the design as a grid of TRIMMED carriers with Mode A (extra cores ticked by the person), into <demo>/carrier_builds/<name>."""
import json, os, sys
import pytest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "frontend"))
import unicell_frontend_v7 as fe  # noqa: E402


def _state(tmp_path, monkeypatch):
    monkeypatch.setattr(fe, "SETTINGS", str(tmp_path / "cfg" / "unicell_bench.json"))
    demo = tmp_path / "demo"
    demo.mkdir()
    return fe.State(str(demo), ROOT), demo


def _paths():
    icms = {i["name"]: i["path"] for i in fe.icm_files(ROOT)}
    cards = {c["file"]: c["path"] for c in fe.card_files(ROOT)}
    return icms, cards


def test_cores_route_gives_the_headers_table():
    icms, _ = _paths()
    x = fe.icm_cores(ROOT, icms["parallel_reduction_tree"])
    assert x["cores_used"] == ["adder", "ram"] and x["unsupported"] == []
    assert "output" in x["io_names"] and "mul" in x["all"]
    y = fe.icm_cores(ROOT, icms["looped_cordic_v1_open"])
    assert y["cores_used"] == ["adder", "branch", "ram"]


def test_carrier_build_with_extra_cores(tmp_path, monkeypatch):
    st, demo = _state(tmp_path, monkeypatch)
    try:
        icms, cards = _paths()
        r = st.create_from_icm(icms["parallel_reduction_tree"], cards["tang-nano-20k.man.json"], "tree_c", build_as="carrier", keep=["multiplier", "mul", "comparator"], tap="output")
        assert r["ok"] and r["flow"] == "carrier"
        g = json.load(open(demo / "carrier_builds" / "tree_c" / "GRID.json"))
        assert g["keep"] == ["adder", "compare", "mul", "ram"] and g["keep_extra"] == ["compare", "mul"]
        assert "added by you: compare, mul" in r["output"]
        assert fe.list_kits(str(demo)) == []                                # a carrier grid is not a card project: not in the Designs list
        with pytest.raises(ValueError):
            st.create_from_icm(icms["parallel_reduction_tree"], cards["tang-nano-20k.man.json"], "tree_c", build_as="carrier", tap="output")      # never overwrites
    finally:
        for t in st.terms.values():
            t.close()


def test_carrier_build_refusals(tmp_path, monkeypatch):
    st, demo = _state(tmp_path, monkeypatch)
    try:
        icms, cards = _paths()
        card = cards["tang-nano-20k.man.json"]
        r = st.create_from_icm(icms["parallel_reduction_tree"], card, "bad_core", build_as="carrier", keep=["foo"], tap="output")
        assert not r["ok"] and "unknown core" in r["output"] and not (demo / "carrier_builds" / "bad_core").exists()
        r = st.create_from_icm(icms["parallel_reduction_tree"], card, "bad_tap", build_as="carrier", tap="nonesuch")
        assert not r["ok"] and "observation point" in r["output"]
        for bad in (["../x"], ["MUL"], "mul"):
            with pytest.raises(ValueError):
                st.create_from_icm(icms["parallel_reduction_tree"], card, "evil", build_as="carrier", keep=bad, tap="output")
        with pytest.raises(ValueError):
            st.create_from_icm(icms["parallel_reduction_tree"], card, "evil2", build_as="carrier", tap="a b")
    finally:
        for t in st.terms.values():
            t.close()


def test_page_v2_has_the_controls_and_server_loads_it():
    page = open(os.path.join(ROOT, "tools", "frontend", "page_v2.html")).read()
    for needle in ("id=buildas", "id=corelist", "/api/icm/cores", "build_as:", "keep:["):
        assert needle in page, needle
    assert "page_v2.html" in open(os.path.join(ROOT, "tools", "frontend", "unicell_frontend_v7.py")).read()
