"""
test_super_tile_library_v1.py — verifies Tier 0 of the super-cell tile
library both structurally (every registered tile's ports/params
resolve correctly) and functionally (a placed tile, fed into a real
SuperGrid, computes the correct result) -- the same "don't just check
the format, run it" discipline test_icm_v3.py and
test_unicell_super_automaton_v1.py already established.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from super_tile_library_v1 import super_tile_library, place, SuperTileSpec, TilePort  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_library_has_all_seven_core_types_represented():
    """points.md #608/#609: branch and sequencer both added (real VM
    dispatch already existed for branch, #501/#519's own resolution;
    sequencer's own real VM dispatch was built fresh in #609, closing
    #519's other half). Tier-0 now covers all 8 real core types."""
    cores = {super_tile_library.get(n).core for n in super_tile_library.names()}
    assert cores == {"nano", "ram", "adder", "accumulator", "comparator", "latch", "branch", "sequencer"}


def test_place_rejects_missing_port_direction():
    tile = super_tile_library.get("adder")
    try:
        place(tile, 0, 0, {"in_a": "n"})  # missing in_b and out
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_rejects_unknown_port():
    tile = super_tile_library.get("comparator")
    try:
        place(tile, 0, 0, {"in": "n", "out": "e", "bogus": "s"}, params={"threshold": 0})
    except ValueError as e:
        assert "unexpected" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_rejects_missing_param():
    tile = super_tile_library.get("comparator")
    try:
        place(tile, 0, 0, {"in": "n", "out": "e"})  # threshold missing
    except ValueError as e:
        assert "missing required param" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_rejects_unknown_param():
    tile = super_tile_library.get("nano_gate")
    try:
        place(tile, 0, 0, {"out": "n"}, params={"topology": 0x24, "bogus": 1})
    except ValueError as e:
        assert "unknown param" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_adder_shared_field_or_combines_both_ports():
    tile = super_tile_library.get("adder")
    rec = place(tile, 0, 0, {"in_a": "n", "in_b": "w", "out": "e"})
    assert rec.core_config["upstream_mask"] == ["n", "w"]  # ONE field, both directions OR'd
    assert rec.core_config["downstream_mask"] == ["e"]


def test_accumulator_inc_dec_are_genuinely_separate_fields():
    tile = super_tile_library.get("accumulator")
    rec = place(tile, 0, 0, {"inc": "n", "dec": "s", "out": "e"}, params={"step_amount": 1})
    assert rec.core_config["inc_dir"] == ["n"]
    assert rec.core_config["dec_dir"] == ["s"]


def test_nano_gate_has_no_in_port():
    tile = super_tile_library.get("nano_gate")
    assert tile.port_names() == ["out"]
    rec = place(tile, 0, 0, {"out": "n"}, params={"topology": 0x24})
    assert "upstream_mask" not in rec.core_config


def test_ram_constant_has_no_in_port_and_carries_init_data_param():
    tile = super_tile_library.get("ram_constant")
    assert tile.port_names() == ["out"]
    rec = place(tile, 0, 0, {"out": "e"}, params={"init_data": 0xCAFEBEEF})
    assert rec.core_config["init_data"] == 0xCAFEBEEF
    assert rec.core_config["fixed_mode"] == 1


def test_placed_tile_super_latch_round_trips():
    tile = super_tile_library.get("latch")
    rec = place(tile, 2, 3, {"set": "n", "clear": "s", "out": "e"})
    latch = rec.super_latch()
    decoded = v3.decode_super_latch(latch)
    assert decoded["core"] == "latch"
    assert decoded["core_config"]["set_dir"] == ["n"]
    assert decoded["core_config"]["clear_dir"] == ["s"]
    assert decoded["core_config"]["downstream_mask"] == ["e"]


# ── End-to-end: a placed tile actually computes the right thing when
# run through a real SuperGrid, not just structurally correct JSON. ──

def test_placed_adder_computes_correctly_in_a_real_grid():
    tile = super_tile_library.get("adder")
    rec = place(tile, 0, 0, {"in_a": "n", "in_b": "w", "out": "e"})
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    accepted, _ = cell.deliver({0: 100}, None)   # N=0
    assert accepted
    accepted, _ = cell.deliver({3: 23}, None)    # W=3
    assert accepted
    assert cell.adder_out_buffer == 123


def test_placed_ram_constant_and_flowing_deliver_across_grid():
    const_tile = super_tile_library.get("ram_constant")
    flow_tile = super_tile_library.get("ram_flowing")
    source = place(const_tile, 0, 0, {"out": "e"}, params={"init_data": 555}, cell_id="src")
    sink = place(flow_tile, 0, 1, {"in": "w", "out": "n"}, cell_id="sink")
    grid = SuperGrid([source, sink])
    for _ in range(5):
        grid.tick()
    assert grid.cells[(0, 1)].ram_data_reg == 555


def test_placed_accumulator_and_comparator_chain_in_a_real_grid():
    # accumulator at (0,0) counting north-arrivals, offering south to a
    # comparator at (1,0) with threshold=2 -- a real, if minimal, Tier-1
    # preview built entirely from Tier-0 pieces placed adjacently.
    acc_tile = super_tile_library.get("accumulator")
    cmp_tile = super_tile_library.get("comparator")
    acc = place(acc_tile, 0, 0, {"inc": "n", "dec": "w", "out": "s"}, params={"step_amount": 1}, cell_id="acc")
    cmp = place(cmp_tile, 1, 0, {"in": "n", "out": "e"}, params={"threshold": 2}, cell_id="cmp")
    grid = SuperGrid([acc, cmp])
    grid.inject(0, 0, 1)  # non-directional inject has no effect on accumulator (documented)
    # drive real directional increments instead
    acc_cell = grid.cells[(0, 0)]
    acc_cell.deliver({0: 1}, None)  # N
    acc_cell.deliver({0: 1}, None)
    acc_cell.deliver({0: 1}, None)
    assert acc_cell.acc_total == 3
    for _ in range(5):
        grid.tick()
    cmp_cell = grid.cells[(1, 0)]
    assert cmp_cell.cmp_data_valid is True
    assert cmp_cell.cmp_out_buffer == 1  # 3 >= 2


# ── branch (points.md #608, new) ────────────────────────────────────

def test_branch_tile_compiles_and_places():
    tile = super_tile_library.get("branch")
    rec = place(tile, 0, 0, {"in": "w", "route_low": "n", "route_equal": "e", "route_high": "s"},
                params={"rolling_mode": 0}, cell_id="br")
    assert rec.core == "branch"
    assert rec.core_config["upstream_dir"] == ["w"]
    assert rec.core_config["route_low"] == ["n"]
    assert rec.core_config["emit_low"] == 1  # real, necessary default -- see tile's own docstring


def test_branch_tile_first_arrival_becomes_reference_no_emit():
    tile = super_tile_library.get("branch")
    rec = place(tile, 0, 0, {"in": "w", "route_low": "n", "route_equal": "e", "route_high": "s"},
                params={"rolling_mode": 0}, cell_id="br")
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    cell.deliver({3: 5}, None)  # W=3
    assert cell.br_ref_valid is True
    assert cell.br_ref_value == 5
    assert cell.br_data_valid is False  # real: capturing the reference itself never emits


def test_branch_tile_routes_low_equal_high_correctly():
    """Real, functional confirmation of the actual 3-way routing --
    the whole real point of this core, not just that it compiles."""
    tile = super_tile_library.get("branch")
    for value, expected_mask, label in [(2, 1, "low->N"), (5, 4, "equal->E"), (9, 2, "high->S")]:
        rec = place(tile, 0, 0, {"in": "w", "route_low": "n", "route_equal": "e", "route_high": "s"},
                    params={"rolling_mode": 0}, cell_id="br")
        grid = SuperGrid([rec])
        cell = grid.cells[(0, 0)]
        cell.deliver({3: 5}, None)  # reference = 5
        cell.deliver({3: value}, None)
        assert cell.br_data_valid is True, label
        assert cell.br_active_route == expected_mask, label
        assert cell.br_out_buffer == value, label  # real passthrough, not a fixed override


def test_branch_tile_rolling_mode_updates_reference_each_time():
    tile = super_tile_library.get("branch")
    rec = place(tile, 0, 0, {"in": "w", "route_low": "n", "route_equal": "e", "route_high": "s"},
                params={"rolling_mode": 1}, cell_id="br")
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    cell.deliver({3: 5}, None)   # reference = 5
    cell.deliver({3: 10}, None)  # 10 > 5 -> high; rolling -> reference becomes 10
    assert cell.br_active_route == 2  # S (high)
    assert cell.br_ref_value == 10    # real, rolling: this compared value is now the reference


def test_branch_tile_shell_compatibility_reachable_via_real_dsl():
    """The real point of #608: confirms the shell-compat rejection
    path (workbench_v1.py, #606) is now reachable end to end through
    real DSL source, not just synthetic records."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))
    import workbench_v1
    dsl = """
    program br_test {
        place b as branch at (0, 0) {
            in: w
            route_low: n
            route_equal: e
            route_high: s
            rolling_mode: 0
        }
    }
    """
    man_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "man", "mustang-f100-a10.man.json")
    ctrl_v1 = workbench_v1.WorkbenchController()
    ctrl_v1.set_target(man_path, 4, shell="v1")
    result_v1 = ctrl_v1.compile(dsl, "dsl")
    assert not result_v1["ok"]
    assert "branch" in result_v1["error"]

    ctrl_v3 = workbench_v1.WorkbenchController()
    ctrl_v3.set_target(man_path, 4, shell="v3")
    result_v3 = ctrl_v3.compile(dsl, "dsl")
    assert result_v3["ok"], result_v3.get("error")


# ── sequencer (points.md #609, new) ─────────────────────────────────

def test_sequencer_tile_compiles_and_places():
    tile = super_tile_library.get("sequencer")
    rec = place(tile, 0, 0, {"out": "e"},
                params={"VALUE_0": 10, "VALUE_1": 20, "VALUE_2": 30, "VALUE_3": 0, "SEQUENCE_LEN": 2},
                cell_id="seq")
    assert rec.core == "sequencer"
    assert rec.core_config["downstream_mask"] == ["e"]
    assert rec.core_config["VALUE_0"] == 10
    assert rec.core_config["SEQUENCE_LEN"] == 2


def test_sequencer_tile_real_cycling_through_a_real_grid():
    tile = super_tile_library.get("sequencer")
    seq_rec = place(tile, 0, 0, {"out": "e"},
                     params={"VALUE_0": 1, "VALUE_1": 2, "VALUE_2": 0, "VALUE_3": 0, "SEQUENCE_LEN": 1},
                     cell_id="seq")
    ram_tile = super_tile_library.get("ram_flowing")
    ram_rec = place(ram_tile, 0, 1, {"in": "w", "out": "n"}, cell_id="consumer")
    grid = SuperGrid([seq_rec, ram_rec])
    seq_cell = grid.cells[(0, 0)]
    ram_cell = grid.cells[(0, 1)]
    received = []
    for _ in range(8):
        grid.tick()
        if ram_cell.ram_data_valid:
            received.append(ram_cell.ram_data_reg)
            ram_cell.ram_data_valid = False
    assert received[:4] == [1, 2, 1, 2]


def test_sequencer_tile_shell_compatibility_reachable_via_real_dsl():
    """The real point of #609: confirms the shell-compat rejection
    path is reachable end to end for sequencer too, not just branch --
    v1 lacks sequencer, v2 has it."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))
    import workbench_v1
    dsl = """
    program seq_test {
        place s as sequencer at (0, 0) {
            out: e
            VALUE_0: 10
            VALUE_1: 20
            VALUE_2: 0
            VALUE_3: 0
            SEQUENCE_LEN: 1
        }
    }
    """
    man_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "man", "mustang-f100-a10.man.json")
    ctrl_v1 = workbench_v1.WorkbenchController()
    ctrl_v1.set_target(man_path, 4, shell="v1")
    result_v1 = ctrl_v1.compile(dsl, "dsl")
    assert not result_v1["ok"]
    assert "sequencer" in result_v1["error"]

    ctrl_v2 = workbench_v1.WorkbenchController()
    ctrl_v2.set_target(man_path, 4, shell="v2")
    result_v2 = ctrl_v2.compile(dsl, "dsl")
    assert result_v2["ok"], result_v2.get("error")


def test_registering_duplicate_name_raises():
    from super_tile_library_v1 import SuperTileLibrary
    lib = SuperTileLibrary()
    lib.register(SuperTileSpec(name="x", core="ram", description="",
                                ports=[TilePort("out", "out", "downstream_mask")]))
    try:
        lib.register(SuperTileSpec(name="x", core="ram", description="",
                                    ports=[TilePort("out", "out", "downstream_mask")]))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for duplicate registration")


# ── Target tagging (points.md #339) ───────────────────────────────────

def test_nano_gate_tagged_universal_others_super_only():
    from super_tile_library_v1 import TARGET_UNICELL_N, TARGET_UNICELL_S, valid_targets
    assert super_tile_library.get("nano_gate").target == "universal"
    assert valid_targets(super_tile_library.get("nano_gate")) == {TARGET_UNICELL_N, TARGET_UNICELL_S}
    for name in ["ram_constant", "ram_flowing", "adder", "accumulator", "comparator", "latch", "branch", "sequencer"]:
        tile = super_tile_library.get(name)
        assert tile.target == "super-only", name
        assert valid_targets(tile) == {TARGET_UNICELL_S}, name


def test_for_target_filters_correctly():
    from super_tile_library_v1 import TARGET_UNICELL_N, TARGET_UNICELL_S
    on_n = super_tile_library.for_target(TARGET_UNICELL_N)
    on_s = super_tile_library.for_target(TARGET_UNICELL_S)
    assert on_n == ["nano_gate"]   # the ONLY tile with a Unicell-n equivalent today
    assert on_s == sorted(super_tile_library.names())   # Unicell-S is the strict superset


def test_place_on_nano_produces_a_real_working_cacell():
    from super_tile_library_v1 import place_on_nano
    from unicell_automaton_v1 import CAGrid
    from unicell_gate_core import TOPO_OR

    tile = super_tile_library.get("nano_gate")
    cell = place_on_nano(tile, 0, 0, {"out": "e"}, params={"topology": TOPO_OR})
    grid = CAGrid(1, 2)
    grid.cells[(0, 0)] = cell   # drop the tile-built cell straight into a real CAGrid
    # two-arrival OR: A=0 then B=0xFF -> OR = 0xFF, offered east once fired.
    # (0,1) is left as a default, un-armed CACell -- irrelevant here, this
    # test is about the tile-built (0,0) cell's own correct behavior, not
    # end-to-end delivery, which test_nano_delegates_to_real_cacell-style
    # coverage already exercises elsewhere.)
    grid.inject(0, 0, 0)
    grid.tick()
    grid.inject(0, 0, 0xFF)
    grid.tick()
    assert grid.cells[(0, 0)].out_buffer == 0xFF   # OR(0, 0xFF), fired and offered east
    assert grid.cells[(0, 0)].routing_mask == 0b0100   # 'e' bit, matching pack_dirmask convention


def test_place_on_nano_rejects_super_only_tile():
    from super_tile_library_v1 import place_on_nano
    tile = super_tile_library.get("adder")
    try:
        place_on_nano(tile, 0, 0, {"in_a": "n", "in_b": "w", "out": "e"})
    except ValueError as e:
        assert "no Unicell-n equivalent" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_and_place_on_nano_share_the_same_port_validation():
    from super_tile_library_v1 import place_on_nano
    tile = super_tile_library.get("nano_gate")
    try:
        place_on_nano(tile, 0, 0, {}, params={"topology": 0x24})  # missing 'out' port
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError")


# ── Fan-out (points.md #341): one port, several directions ────────────

def test_single_port_fans_out_to_multiple_directions():
    tile = super_tile_library.get("accumulator")
    rec = place(tile, 0, 0, {"inc": "n", "dec": "w", "out": ["e", "s"]}, params={"step_amount": 1})
    assert rec.core_config["downstream_mask"] == ["e", "s"]


def test_fanout_and_shared_field_combine_correctly_together():
    # the adder's own in_a/in_b (two ports, one field) plus a fanned-out
    # 'out' port (one port, two directions) -- both mechanisms feeding
    # the SAME field-grouping logic, must not interfere with each other.
    tile = super_tile_library.get("adder")
    rec = place(tile, 0, 0, {"in_a": "n", "in_b": ["w", "s"], "out": "e"})
    assert rec.core_config["upstream_mask"] == ["n", "s", "w"]


def test_fanout_rejects_empty_direction_list():
    tile = super_tile_library.get("comparator")
    try:
        place(tile, 0, 0, {"in": "n", "out": []}, params={"threshold": 0})
    except ValueError as e:
        assert "at least one direction" in str(e)
    else:
        raise AssertionError("expected ValueError")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
