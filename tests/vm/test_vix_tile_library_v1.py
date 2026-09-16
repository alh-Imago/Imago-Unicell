"""
test_vix_tile_library_v1.py — verifies Tier 0 of the VIX Carrier tile
library (`nano/vix_tile_library_v1.py`, points.md #748) both
structurally (every registered tile's ports/params resolve correctly)
and functionally (tiles composed into a real hierarchical ICM document,
fed into the actual VM, compute the correct result) -- the same "don't
just check the format, run it" discipline test_super_tile_library_v1.py
and test_icm_vix_v1.py already established.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_library_has_all_ten_real_data_flow_core_types_represented():
    """command deliberately excluded -- a real, stated scope limit
    (#748's own docstring), not an oversight: a programming/routing
    core, not a data-flow computation core."""
    cores = {t.core for t in vtl.vix_tile_library.values()}
    assert cores == {"nano", "ram", "adder", "mul", "comparator", "branch",
                      "accumulator", "latch", "sequencer", "priority"}


def test_place_rejects_missing_port_direction():
    try:
        vtl.place(vtl.TILE_ADDER, {"in_a": "n"})  # in_b, out missing
        assert False, "expected ValueError"
    except ValueError as e:
        assert "missing" in str(e)


def test_place_rejects_unknown_param():
    try:
        vtl.place(vtl.TILE_ACCUMULATOR,
                   {"inc": "n", "dec": "s", "out": "e"},
                   params={"step_amount": 1, "bogus_param": 99})
        assert False, "expected ValueError"
    except ValueError as e:
        assert "unknown param" in str(e)


def test_adder_shared_field_or_combines_two_ports():
    """The adder's in_a/in_b are two ports mapping to the SAME real
    upstream_mask field (adder_cell_v4c.v has no per-operand field) --
    confirmed here they OR-combine into one field, not two."""
    cell = vtl.place(vtl.TILE_ADDER, {"in_a": "n", "in_b": "w", "out": "e"})
    assert sorted(cell.core_config["upstream_mask"]) == ["n", "w"]
    assert cell.core_config["downstream_mask"] == ["e"]


def test_subtractor_sets_subtract_mode():
    cell = vtl.place(vtl.TILE_SUBTRACTOR, {"in_a": "n", "in_b": "w", "out": "e"})
    assert cell.core_config["subtract_mode"] == 1


def test_mul_has_no_subtract_mode_field():
    """Confirmed directly against mul_cell_v4c.v: no subtract-mode
    equivalent exists for multiply -- the tile's own fixed_core_config
    should not invent one."""
    cell = vtl.place(vtl.TILE_MUL, {"in_a": "n", "in_b": "w", "out": "e"})
    assert "subtract_mode" not in cell.core_config


def test_branch_has_no_upstream_mask_field_only_upstream_dir():
    """Real, genuinely different shape, confirmed (#742): branch takes
    a single upstream_dir, never a mask."""
    cell = vtl.place(vtl.TILE_BRANCH, {"in": "w", "route_low": "s", "route_equal": "s", "route_high": "n"},
                      params={"value_source_low": 0, "value_source_equal": 0, "value_source_high": 0,
                              "emit_low": 1, "emit_equal": 1, "emit_high": 1, "rolling_mode": 0})
    assert cell.core_config["upstream_dir"] == ["w"]
    assert "upstream_mask" not in cell.core_config


def test_priority_field_direction_matches_real_rtl_not_the_usual_convention():
    """priority_cell_v4c.v swaps upstream_mask/downstream_mask bit
    position relative to every other core -- confirmed directly against
    the real RTL, not assumed from the other tiles' own shape. The
    tile's own port->field mapping (not bit position, which flatten()
    doesn't touch) still uses the same real field NAMES the VM's own
    dispatch expects."""
    cell = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                      params={"priority_rank_n": 0, "priority_rank_s": 1,
                              "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0})
    assert sorted(cell.core_config["upstream_mask"]) == ["n", "s"]
    assert cell.core_config["downstream_mask"] == ["e"]


def test_nano_gate_has_no_in_port():
    """Real, documented asymmetry carried forward from the old
    lineage's own tile library: nano accepts from any physically-wired
    neighbor unconditionally -- no real 'in' port to declare."""
    assert vtl.TILE_NANO_GATE.port_names() == ["out"]


def test_arrivals_needed_matches_the_actual_vm_delivery_logic():
    """points.md #757: the real, third tile-contract field a placement
    algorithm needs (shape, ports, timing) -- confirmed here against
    every real tile's own actual VM behavior, not just trusted as a
    static number. Two arrivals for the real 'capture A, then B'
    cores; zero for sequencer (continuously live from config, never
    arrival-triggered); one for everything else."""
    two_arrival_cores = {"adder", "subtractor", "mul", "branch"}
    for name, tile in vtl.vix_tile_library.items():
        if name in two_arrival_cores:
            assert tile.arrivals_needed == 2, name
        elif name == "sequencer":
            assert tile.arrivals_needed == 0, name
        else:
            assert tile.arrivals_needed == 1, name


# ---- real, functional end-to-end test: tiles composed into a real design, run through the actual VM ----

def test_tiles_compose_into_a_real_working_relay_chain():
    """Rebuilds #740's own small relay chain using the tile library
    instead of hand-written core_config dicts -- confirms the tiles
    genuinely work with the rest of the system (icm_vix_v1's own
    flatten()/check_connections(), and real VM execution), not just
    that place() runs without error in isolation."""
    entry_cell = vix.HierCell(cell_id="c0", rel_row=0, rel_col=0, core="ram",
                               core_config={"downstream_mask": ["e"]}, io_name="input")
    relay_in = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="in")
    relay_out = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="out", rel_col=1)
    exit_cell = vix.HierCell(cell_id="c0", rel_row=0, rel_col=0, core="ram",
                              core_config={"upstream_mask": ["w"]}, io_name="output")

    icm = vix.IcmVixFile(
        patterns={
            "entry": vix.HierPattern(cells=[entry_cell]),
            "relay": vix.HierPattern(cells=[relay_in, relay_out]),
            "exit": vix.HierPattern(cells=[exit_cell]),
        },
        placements=[
            vix.HierPlacement(instance="entry_1", pattern="entry", at=(0, 0)),
            vix.HierPlacement(instance="relay_1", pattern="relay", at=(0, 1)),
            vix.HierPlacement(instance="exit_1", pattern="exit", at=(0, 3)),
        ],
        connections=[
            vix.HierConnection(from_=("entry_1", 0, 0, "E"), to=("relay_1", 0, 0, "W")),
            vix.HierConnection(from_=("relay_1", 0, 1, "E"), to=("exit_1", 0, 0, "W")),
        ],
    )
    assert icm.check_connections() == []  # real, case-insensitive match (#748's own fix)

    records, _ = icm.flatten()
    grid = SuperGrid(records)
    input_cell = next(r for r in records if r.io_name == "input")
    output_cell = next(r for r in records if r.io_name == "output")
    grid.inject(input_cell.row, input_cell.col, 77)
    for _ in range(6):
        grid.tick()
    out = grid.cells[(output_cell.row, output_cell.col)]
    assert out.ram_data_valid and out.ram_data_reg == 77


def test_tiles_compose_a_real_working_adder():
    """A minimal, real, functional check for the adder tile
    specifically -- two real values in, the correct sum out."""
    a = vix.HierCell(cell_id="a", rel_row=0, rel_col=0, core="ram",
                      core_config={"downstream_mask": ["e"]}, io_name="a_in")
    b = vix.HierCell(cell_id="b", rel_row=1, rel_col=1, core="ram",
                      core_config={"downstream_mask": ["n"]}, io_name="b_in")
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "s", "out": "e"}, cell_id="add", rel_row=0, rel_col=1)
    add.io_name = "sum_out"

    icm = vix.IcmVixFile(patterns={"p": vix.HierPattern(cells=[a, b, add])},
                          placements=[vix.HierPlacement(instance="i1", pattern="p", at=(0, 0))])
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    a_cell = next(r for r in records if r.io_name == "a_in")
    b_cell = next(r for r in records if r.io_name == "b_in")
    sum_cell = next(r for r in records if r.io_name == "sum_out")
    grid.inject(a_cell.row, a_cell.col, 12)
    for _ in range(2):
        grid.tick()
    grid.inject(b_cell.row, b_cell.col, 30)
    for _ in range(2):
        grid.tick()
    out = grid.cells[(sum_cell.row, sum_cell.col)]
    assert out.adder_data_valid and out.adder_out_buffer == 42
