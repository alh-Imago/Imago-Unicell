"""tests/vm/test_flex_merge_core_v1.py -- ledger #1036: an ICM `merge` core (the main theme's merge, core 12) on the FLEX family. The flex builds a merge as a relay behind merge_cell_v4sa with the mode per cell, so the
ICM core is rewritten to that (icm_v3.merge_cores_as_relays) and its `mode` (2 arbitrate, 3 join-or) picks the merge core's mode. Checked in the REAL GENERATED RTL against FlexGrid. Modes 0 / 1 (A only, B only) are
pass-throughs and refused on flex; the sub family refuses the core. Requires iverilog."""
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402
from test_flex_grid_merge_v1 import vm_sequence  # noqa: E402

ram = h.ram


def design(mode):
    return [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]),
            IcmV3Record(cell_id="M", row=1, col=1, core="merge", core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"], "mode": mode}),
            ram("E", 1, 2, ["w"], [])]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="flexmergecore_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def rtl(tmp, name, recs, streams):
    d, r = h.build(tmp, name, recs)
    assert r.returncode == 0, r.stderr[:400]
    _, got = h.run_level(d, streams, "plain", 5, settle=200)
    return got["E"]


def test_arbitrate_core_sequences_two_simultaneous_items(tmp):
    streams = {"X": [0x00F0, 0x1111], "Y": [0x0F00, 0x2222]}
    r = rtl(tmp, "marb", design(2), streams)
    assert sorted(r[:2]) == [0x00F0, 0x0F00] and sorted(r[2:]) == [0x1111, 0x2222]
    assert vm_sequence(design(2), streams, "arbitrate") == r


def test_join_or_core_waits_for_both_and_ors(tmp):
    streams = {"X": [0x00F0, 0x1111], "Y": [0x0F00, 0x2222]}
    r = rtl(tmp, "mjoin", design(3), streams)
    assert r == [0x0FF0, 0x3333]
    assert vm_sequence(design(3), streams, "arbitrate") == r         # the merge_mode argument is overridden by the core's own mode


@pytest.mark.parametrize("mode", [0, 1])
def test_pass_through_modes_are_refused_on_flex(tmp, mode):
    with pytest.raises(ValueError, match="pass-through"):
        fg.FlexGrid(design(mode))
    icm = os.path.join(tmp, f"pass{mode}.icm")
    h.IcmV3File(name=f"pass{mode}", records=design(mode)).save(icm)
    r = h.cli("-s", "flex", "--icm", icm, "--output", os.path.join(tmp, f"g_pass{mode}"))
    assert r.returncode != 0 and "pass-through" in (r.stderr + r.stdout)


def test_sub_family_refuses_the_merge_core(tmp):
    icm = os.path.join(tmp, "sub.icm")
    h.IcmV3File(name="sub", records=design(2)).save(icm)
    r = h.cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_sub"))
    assert r.returncode != 0 and "merge" in (r.stderr + r.stdout)
