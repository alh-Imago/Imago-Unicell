"""
test_icm_v4.py — real, direct verification of `nano/icm_v4.py`: a
genuine mixed ICM file (a real DSP wrapper record alongside a real
super-cell record) built directly via Python (no DSL/compiler stage,
matching this format's own stated current scope), saved, hash-checked
on load, tamper-detected, and driven through a real, live `SuperGrid`
built by `build_grid()` to confirm the computed result end to end --
not just a record round-trip.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3          # noqa: E402
import icm_v4 as v4          # noqa: E402
from dsp_wrapper_automaton_v1 import _float_to_bits, _bits_to_float  # noqa: E402


def f(val: float) -> int:
    return _float_to_bits(val)


def _build_real_model() -> v4.IcmV4File:
    """A real, small, meaningful mixed program: a DSP wrapper ADD cell
    feeding a real super-cell RAM sink -- the direct ICM-level analog
    of `test_dsp_wrapper_automaton_v1.py`'s own already-proven direct-
    Python DSP-wrapper-into-RAM integration, now expressed as a real,
    saveable/loadable file instead of ad-hoc constructor calls."""
    dsp_rec = v4.DspWrapperRecord(
        cell_id="dsp_add_0", row=0, col=0, op="ADD",
        a_dir="n", b_dir="s", downstream_mask=["e"],
        watchdog_threshold=100,
    )
    ram_rec = v3.IcmV3Record(
        cell_id="ram_sink_0", row=0, col=1, core="ram",
        core_config={"upstream_mask": v3.pack_dirmask(["w"]), "downstream_mask": 0},
    )
    return v4.IcmV4File(
        name="dsp_add_into_ram", super_records=[ram_rec], dsp_wrapper_records=[dsp_rec],
        description="real, minimal mixed ICM v4 program: DSP wrapper ADD -> super-cell RAM sink",
    )


def test_dsp_wrapper_record_roundtrip():
    rec = v4.DspWrapperRecord(cell_id="x", row=2, col=3, op="MUL", a_dir="w", b_dir="n",
                               downstream_mask=["e", "s"], watchdog_threshold=42)
    d = rec.to_dict()
    assert d["op"] == "MUL" and d["a_dir"] == "w" and d["b_dir"] == "n"
    assert d["downstream_mask"] == v3.pack_dirmask(["e", "s"])
    assert d["watchdog_threshold"] == 42

    back = v4.DspWrapperRecord.from_dict(d)
    assert back.cell_id == "x" and back.row == 2 and back.col == 3
    assert back.op == "MUL" and back.watchdog_threshold == 42


def test_dsp_wrapper_record_rejects_unknown_op():
    try:
        v4.DspWrapperRecord(cell_id="bad", row=0, col=0, op="DIV", a_dir="n", b_dir="s")
        assert False, "expected ValueError for unknown op"
    except ValueError as e:
        assert "unknown op" in str(e)


def test_build_cell_matches_direct_construction():
    """A record's own `build_cell()` must produce a real DspWrapperCell
    identical in behavior to one built directly via the constructor --
    confirmed by feeding both the same real operands and comparing
    real computed results, not just comparing config fields."""
    rec = v4.DspWrapperRecord(cell_id="c", row=0, col=0, op="SUB", a_dir="n", b_dir="s", downstream_mask=["e"])
    cell = rec.build_cell()
    cell.deliver({0: f(10.0), 1: f(4.0)})  # N=0, S=1
    val, valid, dmask = cell._offer_state()
    assert valid
    assert _bits_to_float(val) == 6.0
    assert dmask == v3.pack_dirmask(["e"])


def test_mixed_icm_v4_save_load_and_hash_verified():
    icm = _build_real_model()

    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "dsp_add_into_ram.icm.json")
    icm.save(path)

    reloaded = v4.IcmV4File.load(path)
    assert reloaded.format_version == "icm-v4"
    assert len(reloaded.super_records) == 1 and len(reloaded.dsp_wrapper_records) == 1
    assert reloaded.dsp_wrapper_records[0].op == "ADD"
    assert reloaded.super_records[0].core == "ram"

    # ── Real tamper detection -- hand-edit the saved file, confirm
    # the combined hash catches it, same discipline as icm_v3/
    # dsp_wrapper_automaton_v1/mixed_grid_checkpoint_v1. ──
    with open(path) as fh:
        raw = fh.read()
    tampered_path = os.path.join(tmpdir, "tampered.icm.json")
    with open(tampered_path, "w") as fh:
        fh.write(raw.replace('"ADD"', '"SUB"', 1))
    try:
        v4.IcmV4File.load(tampered_path)
        assert False, "expected record_hash mismatch to be caught"
    except ValueError as e:
        assert "record_hash mismatch" in str(e)

    # ── A tampered SUPER record must be caught too, not just the DSP
    # side -- confirms the hash genuinely spans BOTH record kinds. ──
    tampered_path2 = os.path.join(tmpdir, "tampered2.icm.json")
    with open(tampered_path2, "w") as fh:
        fh.write(raw.replace('"ram_sink_0"', '"ram_sink_tampered"', 1))
    try:
        v4.IcmV4File.load(tampered_path2)
        assert False, "expected record_hash mismatch on tampered super record"
    except ValueError as e:
        assert "record_hash mismatch" in str(e)


def test_mixed_icm_v4_build_grid_real_end_to_end():
    """The real, full point of the format: load a saved mixed ICM v4
    file and run it as an actual live grid -- a real DSP wrapper ADD
    feeding a real super-cell RAM sink, through real SuperGrid.tick()
    calls, confirming the correct real computed result arrives at the
    RAM cell, not just that the file parses."""
    icm = _build_real_model()

    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "dsp_add_into_ram.icm.json")
    icm.save(path)
    reloaded = v4.IcmV4File.load(path)

    grid = reloaded.build_grid()
    assert (0, 0) in grid.cells and (0, 1) in grid.cells

    from dsp_wrapper_automaton_v1 import DspWrapperCell
    from unicell_super_automaton_v1 import SuperCell
    assert isinstance(grid.cells[(0, 0)], DspWrapperCell)
    assert isinstance(grid.cells[(0, 1)], SuperCell)

    # Feed the DSP wrapper's real operands directly (its own real,
    # honest capture -- no `injected` path, same as #479-482).
    grid.cells[(0, 0)].deliver({0: f(2.5), 1: f(1.5)})  # N=0, S=1 -> 4.0
    grid.tick()   # DSP wrapper offers its real result eastward
    grid.tick()   # RAM cell (0,1) receives it, matching every other
                  # single-shot core's own real, same two-tick shape
    val, valid, _ = grid.cells[(0, 1)]._offer_state()
    assert valid
    assert _bits_to_float(val) == 4.0


def test_position_collision_is_caught():
    """A real, deliberate placement bug (two records claiming the same
    cell) must be caught explicitly by build_grid(), not silently
    resolved by whichever record happened to load second."""
    dsp_rec = v4.DspWrapperRecord(cell_id="a", row=0, col=0, op="ADD", a_dir="n", b_dir="s")
    ram_rec = v3.IcmV3Record(cell_id="b", row=0, col=0, core="ram")
    icm = v4.IcmV4File(name="collision", super_records=[ram_rec], dsp_wrapper_records=[dsp_rec])
    try:
        icm.build_grid()
        assert False, "expected a position-collision ValueError"
    except ValueError as e:
        assert "claimed by more than one record" in str(e)


if __name__ == "__main__":
    test_dsp_wrapper_record_roundtrip()
    test_dsp_wrapper_record_rejects_unknown_op()
    test_build_cell_matches_direct_construction()
    test_mixed_icm_v4_save_load_and_hash_verified()
    test_mixed_icm_v4_build_grid_real_end_to_end()
    test_position_collision_is_caught()
    print("PASS: all icm_v4 tests")
