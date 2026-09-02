"""tests/vm/test_walker_sim_v1.py -- points.md #602: real tests for the
simulated Walker. Uses real DSL programs compiled through the real
mirrored-VM construction (vm_mirror_v1.py, #601) -- no mocking of the
grid or the discovery protocol itself."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vm_ai_port_v1  # noqa: E402
import walker_sim_v1  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_MAN = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")

# A real, known 2x2 layout (matching grid_dims(4) == (2, 2)):
#   (0,0)--(0,1)
#     |      |
#   (1,0)--(1,1)
GRID4_DSL = """
program grid4 {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 1
    }
    place r2 as ram_flowing at (0, 1) {
        in: w
        out: s
    }
    place r3 as ram_flowing at (1, 1) {
        in: n
        out: w
    }
    place r4 as ram_flowing at (1, 0) {
        in: e
        out: n
    }
}
"""

SINGLE_CELL_DSL = """
program one {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 1
    }
}
"""


def _grid4_session():
    return vm_ai_port_v1.VMSession.from_man(REAL_MAN, 4, dsl=GRID4_DSL)


# ── ping() ───────────────────────────────────────────────────────────

def test_ping_self_on_real_cell_returns_identity():
    session = _grid4_session()
    answer = walker_sim_v1.ping(session, 0, 0, "self")
    assert answer == {"cell_id": "r1@0,0", "type": "ram"}


def test_ping_self_on_empty_position_returns_none():
    session = _grid4_session()
    answer = walker_sim_v1.ping(session, 9, 9, "self")
    assert answer is None


def test_ping_cardinal_relays_one_hop_to_real_neighbor():
    session = _grid4_session()
    # From (0,0), pinging east should relay to (0,1) and get ITS
    # identity back, not (0,0)'s own.
    answer = walker_sim_v1.ping(session, 0, 0, "e")
    assert answer == {"cell_id": "r2@0,1", "type": "ram"}


def test_ping_cardinal_with_no_neighbor_returns_none():
    session = _grid4_session()
    # (0,0) has no real neighbor to the north in a 2x2 grid.
    assert walker_sim_v1.ping(session, 0, 0, "n") is None


def test_ping_rejects_bad_direction():
    session = _grid4_session()
    try:
        walker_sim_v1.ping(session, 0, 0, "up")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ── walk() ───────────────────────────────────────────────────────────

def test_walk_discovers_all_four_real_cells():
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    assert set(result.discovered.keys()) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert result.discovered[(0, 0)] == {"cell_id": "r1@0,0", "type": "ram"}
    assert result.ping_count > 0


def test_walk_discovers_exactly_four_real_edges_no_duplicates():
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    # 4 real physical links in a 2x2 grid: (0,0)-(0,1), (0,0)-(1,0),
    # (0,1)-(1,1), (1,0)-(1,1) -- each recorded exactly once, not twice
    # from both directions.
    assert len(result.edges) == 4
    link_sets = [frozenset((a, b)) for (a, _, b, _) in result.edges]
    assert len(set(link_sets)) == 4  # all genuinely distinct


def test_walk_never_reads_grid_cells_directly():
    """Real, honest discipline check, per #501's own 'all walk
    intelligence is host-side, cells are purely reactive' design:
    walk() must discover everything purely through ping() calls, never
    by reading session.grid.cells directly itself. Checked directly
    against walk()'s own real source (not its call counts, which
    include ping()'s own internal one-hop recursion as an
    implementation detail unrelated to this discipline) -- the one
    real place `.grid.cells` may appear at all is inside ping() itself,
    the sanctioned lookup boundary."""
    import inspect
    walk_source = inspect.getsource(walker_sim_v1.walk)
    assert "grid.cells" not in walk_source
    assert ".cells" not in walk_source


def test_walk_results_are_fully_explained_by_real_ping_calls():
    """A real, behavioral companion to the source check above: every
    discovered identity must equal what a direct, independent ping()
    call for that exact position returns -- confirming walk() isn't
    quietly substituting some other source of truth."""
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    for pos, info in result.discovered.items():
        assert walker_sim_v1.ping(session, pos[0], pos[1], "self") == info


def test_walk_from_non_origin_start_still_discovers_everything():
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(1, 1))
    assert set(result.discovered.keys()) == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_walk_single_cell_grid():
    session = vm_ai_port_v1.VMSession.from_man(REAL_MAN, 1, dsl=SINGLE_CELL_DSL)
    result = walker_sim_v1.walk(session, start=(0, 0))
    assert set(result.discovered.keys()) == {(0, 0)}
    assert result.edges == []


def test_walk_raises_no_target_error_on_empty_origin():
    """The real, direct point Alan raised: a Walker pointed at a
    session with nothing at the origin must fail honestly, not return
    a silently empty/misleading map."""
    session = _grid4_session()
    try:
        walker_sim_v1.walk(session, start=(9, 9))
        assert False, "expected NoTargetError"
    except walker_sim_v1.NoTargetError as e:
        assert "(9,9)" in str(e)


def test_walk_raises_no_target_error_on_free_mode_empty_session():
    """A real, honest end-to-end confirmation of Alan's own concern:
    a VMSession with no program loaded at all has no target."""
    session = vm_ai_port_v1.VMSession()  # empty grid, no mirror_bounds
    try:
        walker_sim_v1.walk(session, start=(0, 0))
        assert False, "expected NoTargetError"
    except walker_sim_v1.NoTargetError:
        pass


# ── to_shape() ───────────────────────────────────────────────────────

def test_to_shape_real_structure():
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    shape = walker_sim_v1.to_shape(result, session.mirror_bounds.card_id)
    assert shape["shape_version"] == "1.0"
    assert shape["card_id"] == "mustang-f100-a10-01"
    assert shape["discovery_method"] == "simulated_walker_ping_protocol"
    assert shape["source_file"] is None
    assert len(shape["cells"]) == 4
    assert len(shape["edges"]) == 4
    instances = {c["instance"] for c in shape["cells"]}
    assert instances == {"C_0_0", "C_0_1", "C_1_0", "C_1_1"}
    for c in shape["cells"]:
        assert c["role"] == "programmable_substrate"
        assert c["module_type"] == "ram"


def test_to_shape_instance_names_match_project_assemble_convention():
    """Real, direct cross-check: instance naming must match what an
    actual Quartus build's own top-level would use, not an invented
    scheme -- reuses project_assemble_v1.inst_name() directly."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
    import project_assemble_v1 as pa
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    shape = walker_sim_v1.to_shape(result, session.mirror_bounds.card_id)
    for c in shape["cells"]:
        assert c["instance"] == pa.inst_name(c["row"], c["col"])


def test_to_shape_edges_reference_real_declared_cells():
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    shape = walker_sim_v1.to_shape(result, session.mirror_bounds.card_id)
    instances = {c["instance"] for c in shape["cells"]}
    for e in shape["edges"]:
        assert e["from"]["instance"] in instances
        assert e["to"]["instance"] in instances
        assert e["from"]["direction"] in ("N", "S", "E", "W")
        assert e["to"]["direction"] in ("N", "S", "E", "W")


def test_to_shape_is_json_serializable():
    import json
    session = _grid4_session()
    result = walker_sim_v1.walk(session, start=(0, 0))
    shape = walker_sim_v1.to_shape(result, session.mirror_bounds.card_id)
    json.dumps(shape)  # must not raise
