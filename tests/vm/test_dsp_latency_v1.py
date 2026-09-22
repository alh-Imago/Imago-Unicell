"""tests/vm/test_dsp_latency_v1.py — points.md #822: DSP-wrapper lowering closed at the smallest safe scope. A
DSP-bound cell's output relay chain is extended by an exact, even number of extra hops via a rectangular free-space
detour, so its real latency becomes elapsed VM time instead of zero -- with no change to the shared tick loop or
router. Verified end to end on the real, compiled program, and against controlled synthetic refusal cases.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import card_fit_v1 as C  # noqa: E402
import dsp_latency_v1 as DL  # noqa: E402
import icm_v3 as v3  # noqa: E402
import llvm_dag_frontend_v1 as F  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(HERE, "..", "..", "docs", "man", "mustang-f100-a10.man.json")
M = 0xFFFFFFFF


def mk(cell_id, row, col, core, **cfg):
    return v3.IcmV3Record(cell_id=cell_id, row=row, col=col, core=core, core_config=cfg)


def _mul_add_program():
    src = "define i32 @f(i32 %x, i32 %y) {\nentry:\n  %a = mul i32 %x, %y\n  %b = add i32 %a, 1\n  ret i32 %b\n}\n"
    t = C.target_from_man(MAN, rows=224, cols=150, alm_per_position=100.0)
    res, diags = F.compile_llvm_via_dag(src, target=t)
    assert diags == []
    return res


def _run_to_correct(res, x, y, ticks=400):
    expect = ((x * y) + 1) & M
    grid = SuperGrid(res.records)
    vals = {"x": x, "y": y}
    for name, sites in res.arg_injections.items():
        for pos in sites:
            grid.cells[pos].ram_data_reg = vals[name]
            grid.cells[pos].ram_data_valid = True
    rc = res.result_cell
    for t in range(ticks):
        grid.tick()
        c = grid.cells[rc]
        if getattr(c, f"{c.core}_data_valid", None) and getattr(c, f"{c.core}_out_buffer", None) == expect:
            return t + 1
    return None


def _run_padded_to_correct(res, mul_pos, extra_hops, x, y, ticks=400):
    records = DL.pad_output_latency(res.records, mul_pos, extra_hops)
    expect = ((x * y) + 1) & M
    grid = SuperGrid(records)
    vals = {"x": x, "y": y}
    for name, sites in res.arg_injections.items():
        for pos in sites:
            grid.cells[pos].ram_data_reg = vals[name]
            grid.cells[pos].ram_data_valid = True
    rc = res.result_cell
    for t in range(ticks):
        grid.tick()
        c = grid.cells[rc]
        if getattr(c, f"{c.core}_data_valid", None) and getattr(c, f"{c.core}_out_buffer", None) == expect:
            return t + 1, records
    return None, records


# ---- end to end, on the real compiled, DSP-site-bound program ----------------------------------------------------

def test_a_mul_with_a_real_dsp_target_is_bound_to_a_real_dsp_site():
    res = _mul_add_program()
    assert res.fit.bindings and res.fit.bindings[0][1] == "dsp"
    assert any(r.core == "mul" and (r.row, r.col) == res.fit.bindings[0][2] for r in res.records)


def test_zero_extra_hops_reproduces_the_baseline_exactly():
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    baseline = _run_to_correct(res, 6, 7)
    padded_tick, _ = _run_padded_to_correct(res, mul_pos, 0, 6, 7)
    assert baseline is not None and baseline == padded_tick


@pytest.mark.parametrize("extra", [2, 4, 8, 20])
def test_padding_adds_exactly_that_many_ticks_and_the_result_stays_correct(extra):
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    baseline = _run_to_correct(res, 6, 7)
    padded_tick, records = _run_padded_to_correct(res, mul_pos, extra, 6, 7)
    assert padded_tick == baseline + extra
    assert len(records) - len(res.records) == extra


def test_padding_is_correct_for_other_operand_values_too_not_just_one_case():
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    for x, y in ((0, 5), (1, 1), (100, 200), (M, 3)):
        tick, _ = _run_padded_to_correct(res, mul_pos, 6, x, y)
        assert tick is not None, (x, y)


def test_no_two_cells_share_a_position_after_padding():
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    records = DL.pad_output_latency(res.records, mul_pos, 12)
    pos = [(r.row, r.col) for r in records]
    assert len(pos) == len(set(pos))


def test_the_original_records_list_is_not_mutated_by_padding():
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    before = [(r.row, r.col, r.core, dict(r.core_config)) for r in res.records]
    DL.pad_output_latency(res.records, mul_pos, 8)
    after = [(r.row, r.col, r.core, dict(r.core_config)) for r in res.records]
    assert before == after


# ---- the parity constraint --------------------------------------------------------------------------------------

def test_an_odd_number_of_extra_hops_is_refused_with_the_parity_reason():
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    with pytest.raises(DL.DspLatencyError, match="even"):
        DL.pad_output_latency(res.records, mul_pos, 3)


def test_a_negative_extra_hops_is_refused():
    res = _mul_add_program()
    mul_pos = res.fit.bindings[0][2]
    with pytest.raises(ValueError, match=">= 0"):
        DL.pad_output_latency(res.records, mul_pos, -2)


# ---- refusal paths, on controlled synthetic geometry (points.md #822) --------------------------------------------

def test_a_genuine_fan_out_is_refused():
    recs = [mk("src", 0, 0, "mul", downstream_mask=["n", "s"], upstream_mask=["w"]),
            mk("c1", -1, 0, "adder", upstream_mask=["s"], downstream_mask=[]),
            mk("c2", 1, 0, "adder", upstream_mask=["n"], downstream_mask=[])]
    with pytest.raises(DL.DspLatencyError, match="fan-out"):
        DL.find_output_chain(recs, (0, 0))


def test_a_cell_with_no_downstream_face_is_refused():
    recs = [mk("src", 0, 0, "mul", downstream_mask=[], upstream_mask=["w"])]
    with pytest.raises(DL.DspLatencyError, match="exactly one downstream face"):
        DL.find_output_chain(recs, (0, 0))


def test_an_output_path_leaving_the_compiled_design_is_refused():
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"])]
    with pytest.raises(DL.DspLatencyError, match="leaves the compiled design"):
        DL.find_output_chain(recs, (0, 0))


def test_a_broken_relay_mid_chain_is_refused():
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"]),
            mk("badrelay", 0, 1, "ram", upstream_mask=["n"], downstream_mask=["e"]),
            mk("consumer", 0, 2, "adder", upstream_mask=["w"], downstream_mask=[])]
    with pytest.raises(DL.DspLatencyError, match="not a plain single-in/single-out hop"):
        DL.find_output_chain(recs, (0, 0))


def test_no_room_for_the_detour_is_refused_not_silently_placed_elsewhere():
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"]),
            mk("relay", 0, 1, "ram", upstream_mask=["w"], downstream_mask=["e"]),
            mk("consumer", 0, 2, "adder", upstream_mask=["w"], downstream_mask=[]),
            mk("wall1", -1, 0, "adder", downstream_mask=[]), mk("wall2", 1, 0, "adder", downstream_mask=[]),
            mk("wall3", -1, 1, "adder", downstream_mask=[]), mk("wall4", 1, 1, "adder", downstream_mask=[])]
    with pytest.raises(DL.DspLatencyError, match="no free"):
        DL.pad_output_latency(recs, (0, 0), 2)


def test_no_record_at_the_given_position_is_refused():
    with pytest.raises(DL.DspLatencyError, match="no record at"):
        DL.find_output_chain([], (0, 0))


# ---- a hand-checked small detour, verified structurally not just by outcome ---------------------------------------

def test_a_two_hop_detour_forms_the_expected_rectangle_and_still_connects_correctly():
    """A direct, hand-worked case: dsp(0,0) -east-> relay(0,1) -east-> consumer(0,2). Padding by 2 must detour
    through EXACTLY one perpendicular cell on each side (a 2x1 rectangle: n of (0,0) and n of (0,1), or the s pair),
    not touch (0,1) itself, and the original relay position must be gone (rebuilt)."""
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"]),
            mk("relay", 0, 1, "ram", upstream_mask=["w"], downstream_mask=["e"]),
            mk("consumer", 0, 2, "adder", upstream_mask=["w"], downstream_mask=[])]
    padded = DL.pad_output_latency(recs, (0, 0), 2)
    pos = {(r.row, r.col) for r in padded}
    assert (0, 1) not in pos or any(r.cell_id.startswith("pad_") for r in padded if (r.row, r.col) == (0, 1))
    assert len(padded) == len(recs) + 2
    detour_cells = [(r.row, r.col) for r in padded if r.cell_id.startswith("pad_detour_")]
    assert set(detour_cells) in ({(-1, 0), (-1, 1)}, {(1, 0), (1, 1)})


def test_extra_hops_of_zero_returns_an_equivalent_but_distinct_list_object():
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"]),
            mk("relay", 0, 1, "ram", upstream_mask=["w"], downstream_mask=["e"]),
            mk("consumer", 0, 2, "adder", upstream_mask=["w"], downstream_mask=[])]
    out = DL.pad_output_latency(recs, (0, 0), 0)
    assert out is not recs and [(r.row, r.col, r.core) for r in out] == [(r.row, r.col, r.core) for r in recs]


def test_the_return_leg_is_checked_too_not_only_the_outward_leg():
    """The gap a mutation surfaced: skipping the return leg's own free-space check would let a detour run through a
    cell the design already occupies. North's outward step is free here but its return step (beside the relay, not
    the dsp cell) is blocked; south is fully free, so the algorithm must fall back to south rather than wrongly
    accepting north."""
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"]),
            mk("relay", 0, 1, "ram", upstream_mask=["w"], downstream_mask=["e"]),
            mk("consumer", 0, 2, "adder", upstream_mask=["w"], downstream_mask=[]),
            mk("block_north_of_relay", -1, 1, "adder", downstream_mask=[])]
    padded = DL.pad_output_latency(recs, (0, 0), 2)
    pos = [(r.row, r.col) for r in padded]
    assert len(pos) == len(set(pos)) and (-1, 1) not in {(r.row, r.col) for r in padded if r.cell_id.startswith("pad_")}
    assert {(1, 0), (1, 1)} <= set(pos)                                  # it used the south fallback


def test_when_neither_directions_return_leg_has_room_the_detour_is_refused():
    recs = [mk("dsp", 0, 0, "mul", downstream_mask=["e"], upstream_mask=["w"]),
            mk("relay", 0, 1, "ram", upstream_mask=["w"], downstream_mask=["e"]),
            mk("consumer", 0, 2, "adder", upstream_mask=["w"], downstream_mask=[]),
            mk("block_north_of_relay", -1, 1, "adder", downstream_mask=[]),
            mk("block_south_of_relay", 1, 1, "adder", downstream_mask=[])]
    with pytest.raises(DL.DspLatencyError, match="no free"):
        DL.pad_output_latency(recs, (0, 0), 2)
