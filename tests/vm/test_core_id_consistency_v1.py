"""Ledger #1337: every place that names a core by number agrees with the RTL it belongs to (two lineages: the super shell / ICM v3 / composer, and the VIX carrier / grid generator / VM carrier model),
every ICM file's core names are known, and the composer's carrier numbers (shown in the bar's hover text) are the carrier RTL's."""
import os, subprocess, sys
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
for p in ("tools", "nano", os.path.join("nano", "examples")):
    sys.path.insert(0, os.path.join(ROOT, p))
import core_id_consistency_v1 as C
import composer_page_v1 as comp


def test_checker_passes_on_the_repo():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "core_id_consistency_v1.py"), "--quiet"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "all consistent within each lineage" in r.stdout


def test_the_two_lineages_really_differ_and_are_both_fixed():
    vixen = C.rtl_ids("fpga/verilog/unicell_vixen_v1.v")
    sup = C.rtl_ids("fpga/verilog/unicell_super/unicell_super_v9.v")
    assert (vixen["adder"], vixen["ram"], vixen["mul"], vixen["div"]) == (1, 2, 9, 15)
    assert (sup["adder"], sup["ram"]) == (2, 1)


def test_composer_carrier_numbers_equal_the_carrier_rtl():
    vixen = C.rtl_ids("fpga/verilog/unicell_vixen_v1.v")
    for core, n in comp.CARRIER_SEL.items():
        assert vixen[core] == n, core
    page = comp.page_composer()
    assert "SUPER shell / ICM v3 numbering" in page and "the VIX carrier numbers this core" in page
