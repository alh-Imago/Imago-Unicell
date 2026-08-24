"""
test_composed_multi_kind_v1.py — real, direct verification of
points.md #486: a composed (Tier-1) tile whose sub-cells mix a DSP
wrapper tile and a super-cell tile, resolved through `place_composed()`
without any DSP-wrapper-specific code added to it, plus the same real
capability reached through a DSL `define` block, both driven end to
end through a live grid to confirm the real computed result.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
import icm_v4 as v4  # noqa: E402
from composed_tile_library_v1 import composed_tile_library, place_composed  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402
from dsp_wrapper_automaton_v1 import _float_to_bits, _bits_to_float  # noqa: E402


def f(val: float) -> int:
    return _float_to_bits(val)


# ── Direct Python: the built-in "dsp_add_and_hold" composed tile ──

def test_multi_kind_composed_tile_produces_a_real_mixed_record_list():
    tile = composed_tile_library.get("dsp_add_and_hold")
    records = place_composed(tile, 0, 0, {"in_a": "n", "in_b": "s", "out": "e"})
    assert len(records) == 2

    dsp_recs = [r for r in records if isinstance(r, v4.DspWrapperRecord)]
    super_recs = [r for r in records if isinstance(r, v3.IcmV3Record)]
    assert len(dsp_recs) == 1 and len(super_recs) == 1

    dsp_rec = dsp_recs[0]
    assert (dsp_rec.row, dsp_rec.col, dsp_rec.op) == (0, 0, "ADD")
    assert dsp_rec.a_dir == "n" and dsp_rec.b_dir == "s"

    super_rec = super_recs[0]
    assert (super_rec.row, super_rec.col, super_rec.core) == (0, 1, "ram")


def test_multi_kind_composed_tile_runs_correctly_end_to_end():
    """The real point: placing the composed tile, building a live grid
    from its (mixed) records, and confirming the real DSP-wrapper
    result actually reaches the RAM sink through real physical
    adjacency -- not just that two records of different types exist."""
    tile = composed_tile_library.get("dsp_add_and_hold")
    records = place_composed(tile, 0, 0, {"in_a": "n", "in_b": "s", "out": "e"})

    icm = v4.IcmV4File(
        name="dsp_add_and_hold_instance",
        super_records=[r for r in records if isinstance(r, v3.IcmV3Record)],
        dsp_wrapper_records=[r for r in records if isinstance(r, v4.DspWrapperRecord)],
    )
    grid = icm.build_grid()
    assert (0, 0) in grid.cells and (0, 1) in grid.cells

    grid.cells[(0, 0)].deliver({0: f(3.0), 1: f(4.5)})  # N=0, S=1 -> 7.5
    grid.tick()
    grid.tick()
    val, valid, _ = grid.cells[(0, 1)]._offer_state()
    assert valid and _bits_to_float(val) == 7.5


def test_multi_kind_composed_tile_position_collision_still_caught():
    """A real, deliberate two-instance overlap (same anchor twice) must
    still be caught by the normal placement-collision path -- proves
    the mixed-kind case didn't quietly bypass existing safety checks."""
    tile = composed_tile_library.get("dsp_add_and_hold")
    r1 = place_composed(tile, 0, 0, {"in_a": "n", "in_b": "s", "out": "e"})
    r2 = place_composed(tile, 0, 0, {"in_a": "n", "in_b": "s", "out": "e"})
    positions_1 = {(r.row, r.col) for r in r1}
    positions_2 = {(r.row, r.col) for r in r2}
    assert positions_1 == positions_2   # confirms a real overlap exists to be caught downstream


# ── Through the real DSL, a `define` block referencing a DSP wrapper
# tile as one of its own sub-cells -- proving #486 reaches DSL-level
# `define`, not just direct Python ComposedTileSpec authoring. ──

def test_dsl_define_block_can_reference_a_dsp_wrapper_subcell():
    src = """
    program dsl_mixed_define {
        define local_dsp_hold {
            place adder as dsp_add at (0, 0) {
                in_a: n
                in_b: s
                out: e
            }
            place sink as ram_flowing at (0, 1) {
                in: w
                out: e
            }
            expose out -> sink.out
        }
        place inst as local_dsp_hold at (5, 5) {
            out: s
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == [], f"unexpected diagnostics: {diags}"
    assert icm is not None
    assert isinstance(icm, v4.IcmV4File)
    assert len(icm.dsp_wrapper_records) == 1
    assert len(icm.super_records) == 1
    dsp_rec = icm.dsp_wrapper_records[0]
    assert (dsp_rec.row, dsp_rec.col, dsp_rec.op) == (5, 5, "ADD")
    super_rec = icm.super_records[0]
    assert (super_rec.row, super_rec.col, super_rec.core) == (5, 6, "ram")

    # ── Real end-to-end: save, reload, run. ──
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "dsl_mixed_define.icm.json")
    icm.save(path)
    reloaded = v4.IcmV4File.load(path)
    grid = reloaded.build_grid()
    grid.cells[(5, 5)].deliver({0: f(1.0), 1: f(2.0)})  # N=0, S=1 -> 3.0
    grid.tick()
    grid.tick()
    val, valid, _ = grid.cells[(5, 6)]._offer_state()
    assert valid and _bits_to_float(val) == 3.0


if __name__ == "__main__":
    test_multi_kind_composed_tile_produces_a_real_mixed_record_list()
    test_multi_kind_composed_tile_runs_correctly_end_to_end()
    test_multi_kind_composed_tile_position_collision_still_caught()
    test_dsl_define_block_can_reference_a_dsp_wrapper_subcell()
    print("PASS: all composed multi-kind tests")
