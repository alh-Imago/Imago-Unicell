"""
test_t_tree_broadcast_v1.py — points.md #545/#546: the real T-tree
design principle proven in the VM. Every cell has 4 cardinal ports;
a non-root node spends 1 receiving from its own parent, leaving
exactly 3 free -- a forced "T" shape (1 in, 3 out), not a chosen one.
Recursing gives powers of 3: one T yields 3 outputs, a T on each of
those yields 9 (Alan's own real worked example).

A REAL, HONEST STRUCTURAL ISSUE found and fixed while building this,
directly validating #545's own pentacross-era "embeddability" concern
in practice: a naive tight embedding (each branch's children placed at
its own immediate cardinal neighbors) causes DIAGONAL SIBLING BRANCHES
TO COLLIDE at shared corner positions -- e.g. the north branch's own
east child and the east branch's own north child land on the identical
grid cell. Fixed with one extra "runway" hop per branch straight
outward before it fans out to its own 3 children -- pushes the three
fan-out zones far enough apart to guarantee zero collisions, while
keeping every leaf at the SAME total depth (3 hops from root),
preserving the equal-path-length property #544 already proved is a
hard correctness requirement. Verified programmatically (collision +
adjacency checks) BEFORE running the simulation, not by trial and
error against the VM itself.

Real, honest scope: proves the DOWN-broadcast half of the tree --
all 9 leaves receive the exact broadcast value at equal depth. The
mirrored UP-merge half (recombining 9 real values back through 3
mergers into 1, the natural next step for a full round-trip matching
#544's own recombination pattern) is a real, separate, larger next
step, not built here.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

TEST_VALUE = 0x11223344

LEAF_POSITIONS = [
    (-3, 0), (-2, 1), (-2, -1),   # north branch's 3 leaves
    (-1, 2), (1, 2), (0, 3),      # east branch's 3 leaves
    (-1, -2), (1, -2), (0, -3),   # west branch's 3 leaves
]


def _ram(cell_id, row, col, downstream, upstream, one_shot=False, value=0):
    cfg = {"downstream_mask": downstream, "upstream_mask": upstream,
           "fixed_mode": 0, "load_data_valid": 1 if one_shot else 0,
           "init_data": value if one_shot else 0}
    return v3.IcmV3Record(cell_id=cell_id, row=row, col=col, core="ram", core_config=cfg)


def _build_tree(value):
    """The real, verified-collision-free layout: root -> 3 branches
    (N/E/W) -> 1 runway relay hop each -> 3 leaves each = 9 total."""
    return [
        _ram("root", 0, 0, ["n", "e", "w"], [], one_shot=True, value=value),

        _ram("L1_N", -1, 0, ["n"], ["s"]),
        _ram("L1_E", 0, 1, ["e"], ["w"]),
        _ram("L1_W", 0, -1, ["w"], ["e"]),

        _ram("relay_N2", -2, 0, ["n", "e", "w"], ["s"]),
        _ram("relay_E2", 0, 2, ["n", "s", "e"], ["w"]),
        _ram("relay_W2", 0, -2, ["n", "s", "w"], ["e"]),

        _ram("leaf_N_N", -3, 0, [], ["s"]),
        _ram("leaf_N_E", -2, 1, [], ["w"]),
        _ram("leaf_N_W", -2, -1, [], ["e"]),

        _ram("leaf_E_N", -1, 2, [], ["s"]),
        _ram("leaf_E_S", 1, 2, [], ["n"]),
        _ram("leaf_E_E", 0, 3, [], ["w"]),

        _ram("leaf_W_N", -1, -2, [], ["s"]),
        _ram("leaf_W_S", 1, -2, [], ["n"]),
        _ram("leaf_W_W", 0, -3, [], ["e"]),
    ]


def test_layout_has_no_position_collisions_and_only_cardinal_edges():
    """Real, programmatic verification of the layout itself -- done
    BEFORE trusting the simulation result, the lesson learned building
    this: check geometry first, don't debug it via trial and error
    against the VM."""
    records = _build_tree(TEST_VALUE)
    positions = [(r.row, r.col) for r in records]
    assert len(positions) == len(set(positions)) == 16, "position collision detected"

    by_id = {r.cell_id: (r.row, r.col) for r in records}
    edges = [
        ("root", "L1_N"), ("root", "L1_E"), ("root", "L1_W"),
        ("L1_N", "relay_N2"), ("L1_E", "relay_E2"), ("L1_W", "relay_W2"),
        ("relay_N2", "leaf_N_N"), ("relay_N2", "leaf_N_E"), ("relay_N2", "leaf_N_W"),
        ("relay_E2", "leaf_E_N"), ("relay_E2", "leaf_E_S"), ("relay_E2", "leaf_E_E"),
        ("relay_W2", "leaf_W_N"), ("relay_W2", "leaf_W_S"), ("relay_W2", "leaf_W_W"),
    ]
    for a, b in edges:
        ra, ca = by_id[a]
        rb, cb = by_id[b]
        diff = (rb - ra, cb - ca)
        assert diff in [(-1, 0), (1, 0), (0, -1), (0, 1)], f"{a}->{b} not cardinal-adjacent: {diff}"


def test_all_nine_leaves_receive_the_broadcast_value_at_equal_depth():
    records = _build_tree(TEST_VALUE)
    grid = SuperGrid(records)
    ticks = grid.run_to_quiescence(max_ticks=50)
    assert ticks < 50

    for pos in LEAF_POSITIONS:
        cell = grid.cells[pos]
        assert cell.ram_data_reg == TEST_VALUE, f"leaf {pos}: expected 0x{TEST_VALUE:08X}, got 0x{cell.ram_data_reg:08X}"
        assert cell.ram_data_valid is True


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
