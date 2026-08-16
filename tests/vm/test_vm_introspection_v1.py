"""
test_vm_introspection_v1.py — verifies JSON introspection
(`vm_introspection_v1.py`, `points.md #216`/`#354`) against REAL running
`SuperGrid`s, not just structural shape checks -- confirming the JSON
output actually reflects true VM state after real computation, the
same "don't just check the format, run it" discipline every other
module this session was held to.
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import vm_introspection_v1 as vi  # noqa: E402
from super_tile_library_v1 import super_tile_library, place  # noqa: E402
from composed_tile_library_v1 import composed_tile_library, place_composed  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from unicell_automaton_v1 import N, S  # noqa: E402


def test_ram_constant_cell_reflects_real_config():
    tile = super_tile_library.get("ram_constant")
    rec = place(tile, 0, 0, {"out": "e"}, params={"init_data": 0xCAFEBEEF})
    grid = SuperGrid([rec])
    d = vi.cell_to_dict(grid.cells[(0, 0)])
    assert d["core"] == "ram"
    assert d["ram"]["data_reg"] == 0xCAFEBEEF
    assert d["ram"]["fixed_mode"] is True


def test_nano_cell_reflects_config_and_is_json_serializable():
    tile = super_tile_library.get("nano_gate")
    rec = place(tile, 0, 0, {"out": "e"}, params={"topology": 0x24})
    grid = SuperGrid([rec])
    d = vi.cell_to_dict(grid.cells[(0, 0)])
    assert d["core"] == "nano"
    assert d["nano"]["topology"] == 0x24
    assert d["nano"]["routing_mask"] == ["e"]
    # must be genuinely JSON-serializable, not just a plain dict that
    # happens to look right -- confirm the real round trip
    reloaded = json.loads(json.dumps(d))
    assert reloaded == d


def test_grid_introspection_reflects_real_post_run_state_sentinel():
    # the real acceptance test: place and RUN the proven sentinel
    # (same sequence #340 already verified), then confirm the JSON
    # dump matches the actual, real post-run VM state exactly.
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    acc = grid.cells[(0, 0)]
    for _ in range(9):
        acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()

    d = vi.grid_to_dict(grid)
    assert d["cell_count"] == 3
    assert d["tick_count"] == 15
    assert d["cells"]["0,0"]["accumulator"]["total"] == 9
    assert d["cells"]["0,1"]["comparator"]["out_buffer"] == 1   # 9 >= 8
    assert d["cells"]["0,2"]["latch"]["state"] is True

    # and the whole thing must genuinely round-trip through real JSON
    text = vi.grid_to_json(grid)
    reloaded = json.loads(text)
    assert reloaded == d


def test_sticky_latch_state_visible_after_accumulator_drops_below_threshold():
    # confirms introspection reflects the REAL sticky behavior (#340's
    # own proven sequence), not just a snapshot that happens to look
    # plausible -- the latch must show state=True even once the
    # comparator's own live output has gone back to 0.
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    acc = grid.cells[(0, 0)]
    for _ in range(9):
        acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()
    for _ in range(5):
        acc.deliver({S: 1}, None)
    for _ in range(15):
        grid.tick()

    d = vi.grid_to_dict(grid)
    assert d["cells"]["0,0"]["accumulator"]["total"] == 4     # dropped below threshold
    assert d["cells"]["0,1"]["comparator"]["out_buffer"] == 0  # live comparator now reads 0
    assert d["cells"]["0,2"]["latch"]["state"] is True         # but latch stays sticky-set


def test_cell_at_returns_the_correct_single_cell():
    tile = super_tile_library.get("accumulator")
    rec = place(tile, 3, 7, {"inc": "n", "dec": "s", "out": "e"})
    grid = SuperGrid([rec])
    d = vi.cell_at(grid, 3, 7)
    assert d["row"] == 3 and d["col"] == 7 and d["core"] == "accumulator"


def test_cell_at_raises_clear_error_for_empty_position():
    tile = super_tile_library.get("ram_constant")
    rec = place(tile, 0, 0, {"out": "e"}, params={"init_data": 1})
    grid = SuperGrid([rec])
    try:
        vi.cell_at(grid, 9, 9)
    except KeyError as e:
        assert "(9,9)" in str(e)
    else:
        raise AssertionError("expected KeyError for an unplaced position")


def test_addon_config_appears_in_introspection():
    tile = super_tile_library.get("ram_constant")
    rec = place(tile, 0, 0, {"out": "e"}, params={"init_data": 1},
                addon_config={"invert_en": 1})
    grid = SuperGrid([rec])
    d = vi.cell_at(grid, 0, 0)
    assert d["addon_config"] == {"invert_en": 1}


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
