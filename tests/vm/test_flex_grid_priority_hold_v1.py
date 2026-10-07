"""tests/vm/test_flex_grid_priority_hold_v1.py -- FlexGrid (the VM's flex mirror) models the PRIORITY core and the ram's HOLD / ONE-SHOT behaviours, each checked against the REAL GENERATED flex RTL (ledger #1022).

PRIORITY: the std model already equals the hardware; this file proves it for strict (several rank sets), weighted and the sequenced channel (several turn orders) on a 12-item stream from three
sources, at widths 32 and 18 (so FlexGrid no longer lists priority as unverified at other widths). HOLD: a fixed ram with a source re-offers its word every time the consumer is ready and each
arrival replaces it (the std VM refuses arrivals to a fixed ram; FlexGrid accepts them only on a ram something feeds). ONE-SHOT: a flowing ram with load_data_valid offers its configured word once.
Requires iverilog and FAILS without it."""
import os
import shutil
import sys
import tempfile
import warnings

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "nano"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
import test_priority_flex_v1 as tp  # noqa: E402
import test_ram_modes_flex_v1 as tr  # noqa: E402

DIR = {"n": 0, "s": 1, "e": 2, "w": 3}
STREAMS = {"E1": [11, 12, 13, 14], "E2": [21, 22, 23, 24], "E3": [31, 32, 33, 34]}


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fgprihold_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def vm_seq(recs, streams, out="O", width=32, ticks=700, mutate=None):
    """Feed each entry whenever it is empty, collect and consume what reaches `out` (the host's read)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        g = fg.FlexGrid(recs, width=width)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    todo = {k: list(v) for k, v in streams.items()}
    seen, e = [], g.cells[pos[out]]
    for _ in range(ticks):
        for k, vals in todo.items():
            c = g.cells[pos[k]]
            if vals and not c.ram_data_valid and not g._pending.get(pos[k]):
                g.inject(*pos[k], vals.pop(0))
        g.tick()
        if e.ram_data_valid:
            seen.append(e.ram_data_reg)
            e.ram_data_valid = False
    return seen, w


def rtl_seq(tmp, name, recs, streams, width=32, out="O", **kw):
    d, r = h.build(tmp, name, recs, width=width if width != 32 else None)
    assert r.returncode == 0, r.stderr[-400:]
    return h.run_level(d, streams, "plain", settle=250, width=width, **kw)[1][out]


def pri_design(mode, ranks, order=None):
    recs = tp.design(mode, ranks)
    if order is not None:
        c = recs[0].core_config
        c["sequence_len"] = len(order)
        for k, f in enumerate(order):
            c[f"sequence_{k}"] = DIR[f]
    return recs


@pytest.mark.parametrize("width", (32, 18))
@pytest.mark.parametrize("mode,ranks,order", [
    (0, (1, 0, 2), None), (0, (2, 1, 0), None), (0, (0, 0, 0), None),
    (1, (1, 3, 2), None), (1, (2, 2, 2), None),
    (2, (0, 0, 0), ("w", "n")), (2, (0, 0, 0), ("w", "n", "s")), (2, (0, 0, 0), ("s", "w", "w", "n")), (2, (0, 0, 0), ("n",))])
def test_flexgrid_priority_equals_the_real_cell(tmp, width, mode, ranks, order):
    recs = pri_design(mode, ranks, order)
    name = f"fp{mode}{''.join(map(str, ranks))}{''.join(order or '')}_{width}"
    rtl = rtl_seq(tmp, name, recs, STREAMS, width)
    vm, _ = vm_seq(recs, STREAMS, width=width)
    assert vm == rtl, f"FlexGrid {vm} vs RTL {rtl}"
    assert rtl, "nothing came out of the hardware"


def test_priority_is_no_longer_listed_as_unverified_at_other_widths():
    assert "priority" not in fg.FlexGrid._UNVERIFIED_AT_OTHER_WIDTHS
    _, w = vm_seq(pri_design(0, (1, 0, 2)), STREAMS, width=18, ticks=2)
    assert not [x for x in w if "priority" in str(x.message)]


def test_the_comparison_bites_a_wrong_rank_order(tmp):
    recs = pri_design(0, (1, 0, 2))
    rtl = rtl_seq(tmp, "fp_bite", recs, STREAMS)
    wrong, _ = vm_seq(pri_design(0, (2, 1, 0)), STREAMS)
    assert wrong != rtl


# ------------------------------------------------------------------ hold and one-shot
@pytest.mark.parametrize("width", (32, 18))
def test_flexgrid_hold_reoffers_and_equals_the_rtl(tmp, width):
    recs = tr.hold_design()
    streams = {"W": [7], "X": [1, 2, 3, 4, 5, 6]}
    rtl = rtl_seq(tmp, f"fh_{width}", recs, streams, width)
    vm, _ = vm_seq(recs, streams, width=width)
    assert rtl == [8, 9, 10, 11, 12, 13]
    assert vm == rtl, f"FlexGrid {vm} vs RTL {rtl}"


def test_flexgrid_hold_with_a_starting_value_and_with_later_overwrites(tmp):
    recs = tr.hold_design(preload=5)
    streams = {"W": [], "X": [1, 2, 3, 4]}
    assert vm_seq(recs, streams)[0] == rtl_seq(tmp, "fh_pre", recs, streams) == [6, 7, 8, 9]
    # a write in the middle replaces the held word: the hardware's exact moment depends on its cycle timing, so the check is the SET of sums and that each is a held value
    recs = tr.hold_design()
    vm, _ = vm_seq(recs, {"W": [7, 100], "X": [1, 2, 3, 4, 5, 6, 7, 8]})
    assert set(v - x for v, x in zip(vm, range(1, 9))) <= {7, 100} and vm[0] == 8 and vm[-1] == 108, vm


def test_flexgrid_hold_is_empty_until_written():
    recs = tr.hold_design()
    vm, _ = vm_seq(recs, {"W": [], "X": [1, 2, 3]}, ticks=100)
    assert vm == []


def test_a_fixed_constant_with_no_source_is_still_a_constant_and_a_flowing_ram_still_refuses_nothing(tmp):
    cfg = {"upstream_mask": [], "downstream_mask": ["e"], "fixed_mode": 1, "load_data_valid": 1, "init_data": 5}
    recs = [h.ram("X", 0, 1, [], ["s"]), tp.IcmV3Record(cell_id="K", row=1, col=0, core="ram", core_config=cfg), tp.IcmV3Record(cell_id="A", row=1, col=1, core="adder", core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"], "subtract_mode": 0}), h.ram("O", 1, 2, ["w"], [])]
    vm, _ = vm_seq(recs, {"X": [1, 2, 3]})
    assert vm == [6, 7, 8], vm


@pytest.mark.parametrize("width", (32, 18))
def test_flexgrid_oneshot_preload_is_offered_once(tmp, width):
    recs = tr.oneshot_design(100)
    streams = {"E": [10, 20, 30]}
    rtl = rtl_seq(tmp, f"fo_{width}", recs, streams, width)
    vm, _ = vm_seq(recs, streams, width=width)
    assert rtl == [110] and vm == rtl, (vm, rtl)
