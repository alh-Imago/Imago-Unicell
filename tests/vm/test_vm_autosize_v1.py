"""tests/vm/test_vm_autosize_v1.py -- points.md #667: real tests for
the auto-sized VM construction tool and named I/O entry/exit points.
Closes the standing #651 gap: an ICM file already carries everything
needed to derive its own minimum runnable footprint; this is the first
real test coverage for the tool that does it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3
from vm_autosize_v1 import (
    build_auto_sized_vm, compute_bounding_box, remap_records_to_origin, collect_io_points,
)


def _loop_records_at(row_offset, col_offset):
    """A real, small 3-cell chain (RAM -> adder -> RAM), deliberately
    placed at a large offset -- simulating a design authored somewhere
    far from the origin in a much larger conceptual space."""
    return [
        v3.IcmV3Record(cell_id="IN", row=row_offset, col=col_offset, core="ram",
                        core_config={"downstream_mask": ["e"]}, io_name="data_in"),
        v3.IcmV3Record(cell_id="ADD", row=row_offset, col=col_offset + 1, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        v3.IcmV3Record(cell_id="OUT", row=row_offset, col=col_offset + 2, core="ram",
                        core_config={"upstream_mask": ["w"]}, io_name="data_out"),
    ]


def test_compute_bounding_box():
    records = _loop_records_at(50, 100)
    assert compute_bounding_box(records) == (50, 100, 50, 102)


def test_compute_bounding_box_rejects_empty():
    try:
        compute_bounding_box([])
    except ValueError as e:
        assert "empty" in str(e)
    else:
        raise AssertionError("expected ValueError for an empty record list")


def test_remap_records_to_origin_shifts_correctly():
    records = _loop_records_at(50, 100)
    remapped = remap_records_to_origin(records)
    positions = {r.cell_id: (r.row, r.col) for r in remapped}
    assert positions == {"IN": (0, 0), "ADD": (0, 1), "OUT": (0, 2)}


def test_remap_preserves_io_name_and_config():
    records = _loop_records_at(50, 100)
    remapped = remap_records_to_origin(records)
    io_by_id = {r.cell_id: r.io_name for r in remapped}
    assert io_by_id == {"IN": "data_in", "ADD": None, "OUT": "data_out"}
    add = next(r for r in remapped if r.cell_id == "ADD")
    assert add.core_config == {"upstream_mask": ["w"], "downstream_mask": ["e"]}


def test_remap_always_returns_fresh_records_even_at_origin():
    records = _loop_records_at(0, 0)
    remapped = remap_records_to_origin(records)
    assert remapped is not records
    assert remapped[0] is not records[0]


def test_collect_io_points_resolves_correctly():
    records = remap_records_to_origin(_loop_records_at(50, 100))
    points = collect_io_points(records)
    assert points == {"data_in": (0, 0), "data_out": (0, 2)}


def test_collect_io_points_rejects_duplicates():
    records = [
        v3.IcmV3Record(cell_id="A", row=0, col=0, core="ram", io_name="dup"),
        v3.IcmV3Record(cell_id="B", row=0, col=1, core="ram", io_name="dup"),
    ]
    try:
        collect_io_points(records)
    except ValueError as e:
        assert "duplicate" in str(e) and "dup" in str(e)
    else:
        raise AssertionError("expected ValueError for a duplicate io_name")


def test_build_auto_sized_vm_produces_a_tight_grid():
    icm = v3.IcmV3File(name="test", records=_loop_records_at(50, 100))
    vm = build_auto_sized_vm(icm)
    assert (vm.rows, vm.cols) == (1, 3)
    assert set(vm.grid.cells.keys()) == {(0, 0), (0, 1), (0, 2)}


def test_auto_sized_vm_end_to_end_data_flow():
    """Points.md #667: the real, decisive test -- inject via a named
    entry point on a design placed far from the origin, and read the
    real, correct result back via a named exit point, with the caller
    never touching a raw coordinate at any point."""
    icm = v3.IcmV3File(name="test", records=_loop_records_at(50, 100))
    vm = build_auto_sized_vm(icm)

    vm.inject_named("data_in", 42)
    vm.grid.run_to_quiescence()
    vm.inject_named("data_in", 8)
    vm.grid.run_to_quiescence()

    assert vm.read_named("data_out") == 50


def test_inject_named_rejects_unknown_name():
    icm = v3.IcmV3File(name="test", records=_loop_records_at(0, 0))
    vm = build_auto_sized_vm(icm)
    try:
        vm.inject_named("typo", 1)
    except KeyError as e:
        assert "typo" in str(e) and "data_in" in str(e)
    else:
        raise AssertionError("expected KeyError for an unknown io_name")


def test_read_named_rejects_unknown_name():
    icm = v3.IcmV3File(name="test", records=_loop_records_at(0, 0))
    vm = build_auto_sized_vm(icm)
    try:
        vm.read_named("typo")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for an unknown io_name")


def test_read_named_honestly_rejects_unsupported_core_types():
    """Points.md #669: branch remains real, deliberately excluded --
    it emits a genuine multi-way routing decision across low/equal/
    high, not one settled value to read back."""
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="BR", row=0, col=0, core="branch", io_name="route"),
    ])
    vm = build_auto_sized_vm(icm)
    try:
        vm.read_named("route")
    except ValueError as e:
        assert "branch" in str(e) and "supported yet" in str(e)
    else:
        raise AssertionError("expected ValueError for reading an unsupported core type")


def test_read_named_supports_nano():
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="N", row=0, col=0, core="nano",
                        core_config={"ready": 1}, io_name="n_out"),
    ])
    vm = build_auto_sized_vm(icm)
    # Real, established behavior (confirmed elsewhere this project):
    # nano always requires two real arrivals to fire, even when only
    # one value is actually meaningful -- the second is a real, dummy
    # confirming arrival, not a bug in this test.
    vm.inject_named("n_out", 0xABCD)
    vm.grid.run_to_quiescence()
    vm.inject_named("n_out", 0xFFFFFFFF)
    vm.grid.run_to_quiescence()
    assert vm.read_named("n_out") == 0xABCD


def test_io_name_defaults_to_none_and_is_backward_compatible():
    rec = v3.IcmV3Record(cell_id="X", row=0, col=0, core="ram")
    assert rec.io_name is None
    d = rec.to_dict()
    assert d["io_name"] is None
    rec2 = v3.IcmV3Record.from_dict(d)
    assert rec2.io_name is None


def test_io_name_survives_a_real_dict_roundtrip():
    rec = v3.IcmV3Record(cell_id="X", row=0, col=0, core="ram", io_name="my_entry")
    rec2 = v3.IcmV3Record.from_dict(rec.to_dict())
    assert rec2.io_name == "my_entry"


# ═══════════════════════════════════════════════════════════════════════
# points.md #669: real_named() extended to comparator/accumulator/latch/
# sequencer. Comparator was a genuine oversight in #667's own original
# scope (it does have a real, settled 0/1 value, cmp_out_buffer) -- not
# a new capability, a correction. Accumulator/latch surfaced a real,
# separate finding along the way: both explicitly document "injected
# unsupported" in their own real delivery logic (they only ever act on
# a genuine cardinal arrival matching their own configured direction),
# so inject_named() is honestly a real no-op for them, not a trigger --
# read_named() still works correctly once driven by a direct cardinal
# delivery (matching how their own existing tests already do it).
# ═══════════════════════════════════════════════════════════════════════

def test_read_named_supports_comparator():
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="C", row=0, col=0, core="comparator",
                        core_config={"threshold": 5}, io_name="cmp_out"),
    ])
    vm = build_auto_sized_vm(icm)
    vm.inject_named("cmp_out", 7)
    vm.grid.run_to_quiescence()
    assert vm.read_named("cmp_out") == 1


def test_read_named_supports_sequencer_current_index():
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="S", row=0, col=0, core="sequencer",
                        core_config={"VALUE_0": 11, "VALUE_1": 22, "downstream_mask": ["e"]},
                        io_name="seq_out"),
    ])
    vm = build_auto_sized_vm(icm)
    assert vm.read_named("seq_out") == 11


def test_read_named_supports_accumulator_driven_by_a_real_cardinal_arrival():
    """Points.md #669: accumulator's own real "injected unsupported"
    behavior means this must be driven by a genuine cardinal arrival,
    not inject_named() -- documented and tested honestly, not papered
    over."""
    from unicell_super_automaton_v1 import N
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="A", row=0, col=0, core="accumulator",
                        core_config={"inc_dir": ["n"], "step_amount": 3}, io_name="acc_out"),
    ])
    vm = build_auto_sized_vm(icm)
    vm.grid.cells[(0, 0)].deliver({N: 1}, None)
    assert vm.read_named("acc_out") == 3


def test_read_named_supports_latch_driven_by_a_real_cardinal_arrival():
    from unicell_super_automaton_v1 import N
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="L", row=0, col=0, core="latch",
                        core_config={"set_dir": ["n"]}, io_name="latch_out"),
    ])
    vm = build_auto_sized_vm(icm)
    vm.grid.cells[(0, 0)].deliver({N: 1}, None)
    assert vm.read_named("latch_out") is True


def test_inject_named_is_a_real_honest_noop_for_accumulator():
    """Points.md #669: not a silent failure -- accumulator's own real
    delivery logic explicitly treats a directionless arrival as a
    real no-op (documented in its own code), so inject_named() simply
    doesn't move the total, rather than raising a confusing error."""
    icm = v3.IcmV3File(name="test", records=[
        v3.IcmV3Record(cell_id="A", row=0, col=0, core="accumulator",
                        core_config={"inc_dir": ["n"], "step_amount": 3}, io_name="acc_out"),
    ])
    vm = build_auto_sized_vm(icm)
    vm.inject_named("acc_out", 1)
    vm.grid.run_to_quiescence()
    assert vm.read_named("acc_out") == 0


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
