"""
test_host_registry_v1.py — verifies the real host resource registry
(points.md #400), standalone and integrated with the real loader.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from host_registry_v1 import HostResourceRegistry, ResourceConflictError  # noqa: E402
from loader_v1 import bind_shape  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402


def test_query_occupied_starts_empty():
    r = HostResourceRegistry()
    assert r.query_occupied() == {}
    assert r.total_occupied_cells() == 0
    assert r.list_resources() == []


def test_register_load_updates_occupied():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0), (0, 1)])
    assert r.query_occupied() == {(0, 0): "a", (0, 1): "a"}
    assert r.total_occupied_cells() == 2
    assert r.list_resources() == ["a"]


def test_query_occupied_returns_a_real_copy_not_a_live_reference():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0)])
    occ = r.query_occupied()
    occ[(9, 9)] = "tampered"
    assert (9, 9) not in r.query_occupied()


def test_register_unload_frees_positions():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0), (0, 1)])
    r.register_unload("a")
    assert r.query_occupied() == {}
    assert r.list_resources() == []


def test_position_conflict_is_a_real_rejected_error():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0), (0, 1)])
    try:
        r.register_load("b", [(0, 1), (0, 2)])
    except ResourceConflictError as e:
        assert "already occupied" in str(e)
    else:
        raise AssertionError("expected ResourceConflictError")
    # the failed load must not have partially applied
    assert r.query_occupied() == {(0, 0): "a", (0, 1): "a"}


def test_duplicate_resource_id_is_a_real_rejected_error():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0)])
    try:
        r.register_load("a", [(1, 0)])
    except ResourceConflictError as e:
        assert "already registered" in str(e)
    else:
        raise AssertionError("expected ResourceConflictError")


def test_unloading_unknown_resource_is_a_real_rejected_error():
    r = HostResourceRegistry()
    try:
        r.register_unload("ghost")
    except ResourceConflictError as e:
        assert "not currently registered" in str(e)
    else:
        raise AssertionError("expected ResourceConflictError")


def test_double_unload_is_a_real_rejected_error():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0)])
    r.register_unload("a")
    try:
        r.register_unload("a")
    except ResourceConflictError as e:
        assert "not currently registered" in str(e)
    else:
        raise AssertionError("expected ResourceConflictError")


def test_resource_info_returns_real_data_or_raises_key_error():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0), (0, 1)], metadata={"language": "dsl"})
    info = r.resource_info("a")
    assert info["positions"] == [(0, 0), (0, 1)]
    assert info["metadata"] == {"language": "dsl"}
    try:
        r.resource_info("ghost")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_resource_info_returns_a_real_copy_of_positions():
    r = HostResourceRegistry()
    r.register_load("a", [(0, 0)])
    info = r.resource_info("a")
    info["positions"].append((9, 9))
    assert r.resource_info("a")["positions"] == [(0, 0)]


# ── Real integration with the loader (#375), not simulated ────────────

def test_registry_query_feeds_the_real_loader_directly():
    registry = HostResourceRegistry()
    icm, diags = compile_source(
        'program p { place r1 as ram_constant at (0,0) { out: e init_data: 1 } }'
    )
    assert diags == []
    bound, bind_diags = bind_shape(icm.records, registry.query_occupied())
    assert bind_diags == []
    assert [(r.row, r.col) for r in bound] == [(0, 0)]


def test_second_load_correctly_avoids_the_first_via_the_registry():
    registry = HostResourceRegistry()
    icm1, _ = compile_source('program p1 { place r1 as ram_constant at (0,0) { out: e init_data: 1 } }')
    bound1, _ = bind_shape(icm1.records, registry.query_occupied())
    registry.register_load("region_a", [(r.row, r.col) for r in bound1])

    icm2, _ = compile_source('program p2 { place r1 as ram_constant at (0,0) { out: e init_data: 2 } }')
    bound2, _ = bind_shape(icm2.records, registry.query_occupied())
    registry.register_load("region_b", [(r.row, r.col) for r in bound2])

    positions1 = {(r.row, r.col) for r in bound1}
    positions2 = {(r.row, r.col) for r in bound2}
    assert not (positions1 & positions2)   # genuinely non-overlapping


def test_unload_then_reload_correctly_reuses_the_freed_position():
    registry = HostResourceRegistry()
    icm, _ = compile_source('program p { place r1 as ram_constant at (0,0) { out: e init_data: 1 } }')
    bound1, _ = bind_shape(icm.records, registry.query_occupied())
    registry.register_load("a", [(r.row, r.col) for r in bound1])
    registry.register_unload("a")

    bound2, _ = bind_shape(icm.records, registry.query_occupied())
    assert [(r.row, r.col) for r in bound2] == [(0, 0)]   # the freed origin is reused


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
