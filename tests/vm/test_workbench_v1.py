"""
test_workbench_v1.py — verifies the new Unicell-S workbench
(`nano/workbench_v1.py`, `points.md #362`) two ways: the
`WorkbenchController`'s own logic directly (no HTTP needed), and the
REAL running HTTP server, started and torn down within this same test
process (real sockets, real `urllib` requests) -- not just testing the
controller in isolation and assuming the HTTP layer works. This mirrors
the exact end-to-end sequence already confirmed manually via curl
against a real running server before this file was written.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from workbench_v1 import WorkbenchController, serve, DEMOS  # noqa: E402
from unicell_automaton_v1 import N  # noqa: E402

SENTINEL_DSL = """
program my_sentinel {
    place s1 as sentinel at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
"""


# ── WorkbenchController: pure logic, no HTTP ───────────────────────────

def test_controller_state_before_compile():
    ctrl = WorkbenchController()
    result = ctrl.state()
    assert result == {"ok": False, "error": "no program compiled yet"}


def test_controller_compile_and_full_sentinel_sequence():
    ctrl = WorkbenchController()
    result = ctrl.compile(SENTINEL_DSL, "dsl")
    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["state"]["cell_count"] == 3

    for _ in range(9):
        ctrl.deliver(0, 0, "n", 1)
    result = ctrl.step(15)
    assert result["ok"] is True
    state = result["state"]
    assert state["cells"]["0,0"]["accumulator"]["total"] == 9
    assert state["cells"]["0,1"]["comparator"]["out_buffer"] == 1
    assert state["cells"]["0,2"]["latch"]["state"] is True


def test_controller_compile_failure_returns_real_diagnostics():
    ctrl = WorkbenchController()
    broken = "program broken { place r1 as ram_constant at (0,0) { init_data: 1 } }"
    result = ctrl.compile(broken, "dsl")
    assert result["ok"] is False
    assert len(result["diagnostics"]) == 1
    assert result["diagnostics"][0]["stage"] == "place"
    assert "missing" in result["diagnostics"][0]["problem"]


def test_controller_deliver_unknown_direction():
    ctrl = WorkbenchController()
    ctrl.compile(SENTINEL_DSL, "dsl")
    result = ctrl.deliver(0, 0, "bogus", 1)
    assert result["ok"] is False
    assert "direction" in result["error"]


def test_controller_deliver_unplaced_position():
    ctrl = WorkbenchController()
    ctrl.compile(SENTINEL_DSL, "dsl")
    result = ctrl.deliver(99, 99, "n", 1)
    assert result["ok"] is False
    assert "(99,99)" in result["error"]


def test_controller_inject():
    ctrl = WorkbenchController()
    ctrl.compile("program p { place r1 as ram_flowing at (0,0) { in: n out: e } }", "dsl")
    result = ctrl.inject(0, 0, 5)
    assert result["ok"] is True


# ── Demo library (points.md #363) ──────────────────────────────────────

def test_list_demos_reports_real_demos():
    ctrl = WorkbenchController()
    result = ctrl.list_demos()
    assert result["ok"] is True
    assert "sentinel" in result["demos"]
    assert "python_ast_example" in result["demos"]


def test_load_demo_sentinel_compiles_and_runs():
    ctrl = WorkbenchController()
    result = ctrl.load_demo("sentinel")
    assert result["ok"] is True
    assert result["state"]["cell_count"] == 3


def test_load_demo_unknown_name():
    ctrl = WorkbenchController()
    result = ctrl.load_demo("totally_bogus")
    assert result["ok"] is False
    assert "totally_bogus" in result["error"]


def test_load_demo_python_ast_example_actually_works():
    ctrl = WorkbenchController()
    result = ctrl.load_demo("python_ast_example")
    assert result["ok"] is True
    assert result["state"]["cell_count"] == 3


# ── Region management (points.md #363): the real new capability ───────

def test_load_two_non_overlapping_regions():
    ctrl = WorkbenchController()
    r1 = ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    r2 = ctrl.load_region("b", DEMOS["sentinel"]["source"], "dsl", 5, 0)
    assert r1["ok"] is True and r2["ok"] is True
    assert r1["region"]["positions"] == [(0, 0), (0, 1), (0, 2)]
    assert r2["region"]["positions"] == [(5, 0), (5, 1), (5, 2)]
    assert len(ctrl.session.grid.cells) == 6


def test_load_region_rejects_a_real_collision():
    ctrl = WorkbenchController()
    ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    result = ctrl.load_region("collider", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    assert result["ok"] is False
    assert "collides" in result["error"]
    # the first region must be completely unaffected by the rejected attempt
    assert len(ctrl.session.grid.cells) == 3
    assert "collider" not in ctrl.regions


def test_load_region_duplicate_name_rejected():
    ctrl = WorkbenchController()
    ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    result = ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 5, 0)
    assert result["ok"] is False
    assert "already loaded" in result["error"]


def test_two_regions_run_independently_and_clearing_one_does_not_disturb_the_other():
    # the real acceptance test for this whole capability: two full
    # sentinel instances sharing one grid, driven to their real proven
    # set-latch state independently, then one is cleared entirely --
    # the other must be completely untouched, and the grid must stay
    # stable (no crash from stale pending events referencing removed
    # cells) for further ticks afterward.
    ctrl = WorkbenchController()
    ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    ctrl.load_region("b", DEMOS["sentinel"]["source"], "dsl", 5, 0)

    for row in (0, 5):
        for _ in range(9):
            ctrl.session.deliver(row, 0, {N: 1}, None)
    ctrl.step(15)

    state = ctrl.state()["state"]
    assert state["cells"]["0,0"]["accumulator"]["total"] == 9
    assert state["cells"]["0,2"]["latch"]["state"] is True
    assert state["cells"]["5,0"]["accumulator"]["total"] == 9
    assert state["cells"]["5,2"]["latch"]["state"] is True

    result = ctrl.clear_region("a")
    assert result["ok"] is True
    state2 = result["state"]
    assert "0,0" not in state2["cells"] and "0,1" not in state2["cells"] and "0,2" not in state2["cells"]
    assert state2["cells"]["5,0"]["accumulator"]["total"] == 9
    assert state2["cells"]["5,2"]["latch"]["state"] is True
    assert "a" not in ctrl.regions and "b" in ctrl.regions

    # must not crash, and region b must keep computing correctly
    for _ in range(10):
        ctrl.step(1)
    state3 = ctrl.state()["state"]
    assert state3["cells"]["5,2"]["latch"]["state"] is True


def test_clear_region_unknown_name():
    ctrl = WorkbenchController()
    result = ctrl.clear_region("never_loaded")
    assert result["ok"] is False
    assert "never_loaded" in result["error"]


def test_state_annotates_cells_with_their_region():
    ctrl = WorkbenchController()
    ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    state = ctrl.state()["state"]
    assert state["cells"]["0,0"]["region"] == "a"


def test_single_program_compile_still_works_alongside_region_support():
    # the simple case (#362) must be completely unaffected by adding
    # region support -- a fresh compile() clears any prior regions too.
    ctrl = WorkbenchController()
    ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    assert "a" in ctrl.regions
    result = ctrl.compile(DEMOS["adder_pair"]["source"], "dsl")
    assert result["ok"] is True
    assert ctrl.regions == {}


# ── The real loader/binder stage integration (points.md #375) ─────────

def test_load_region_auto_placement_when_offsets_both_omitted():
    ctrl = WorkbenchController()
    result = ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl")   # no offsets at all
    assert result["ok"] is True
    assert result["region"]["positions"] == [(0, 0), (0, 1), (0, 2)]


def test_load_region_auto_placement_finds_the_next_free_spot():
    ctrl = WorkbenchController()
    ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)   # occupies (0,0),(0,1),(0,2)
    result = ctrl.load_region("b", DEMOS["sentinel"]["source"], "dsl")   # auto -- must NOT collide
    assert result["ok"] is True
    b_positions = set(result["region"]["positions"])
    a_positions = set(ctrl.regions["a"])
    assert not (a_positions & b_positions)   # genuinely non-overlapping


def test_load_region_manual_mode_unaffected_by_the_loader_refactor():
    # the exact original acceptance sequence from #363, re-run to prove
    # the refactor onto loader_v1.bind_shape() changed nothing observable
    ctrl = WorkbenchController()
    r1 = ctrl.load_region("a", DEMOS["sentinel"]["source"], "dsl", 0, 0)
    r2 = ctrl.load_region("b", DEMOS["sentinel"]["source"], "dsl", 5, 0)
    assert r1["ok"] is True and r2["ok"] is True
    assert r1["region"]["positions"] == [(0, 0), (0, 1), (0, 2)]
    assert r2["region"]["positions"] == [(5, 0), (5, 1), (5, 2)]


def test_load_region_dsp_aware_placement_biases_toward_the_given_column():
    # points.md #377, item 6 -- real DSP-column-aware auto-placement,
    # reachable through the workbench, not just the loader module alone.
    ctrl = WorkbenchController()
    result = ctrl.load_region("a", "program p { place r1 as ram_constant at (0,0) "
                                    "{ out: e init_data: 1 } }", "dsl",
                               dsp_columns=[12])
    assert result["ok"] is True
    assert result["region"]["positions"] == [(0, 12)]


# ── The real, running HTTP server -- started and torn down within this
# same test process, real sockets, real requests, not mocked. ─────────

def _http_get(port, path):
    with urllib.request.urlopen(f"http://localhost:{port}{path}") as resp:
        return resp.status, json.loads(resp.read())


def _http_post(port, path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"http://localhost:{port}{path}", data=data,
                                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_real_server_full_sentinel_sequence_end_to_end():
    server = serve(port=7433, open_browser=False)
    try:
        time.sleep(0.3)   # real socket bind, give the thread a moment

        status, body = _http_get(7433, "/state")
        assert body == {"ok": False, "error": "no program compiled yet"}

        status, body = _http_post(7433, "/compile", {"source": SENTINEL_DSL, "language": "dsl"})
        assert body["ok"] is True
        assert body["state"]["cell_count"] == 3

        for _ in range(9):
            _http_post(7433, "/deliver", {"row": 0, "col": 0, "direction": "n", "value": 1})

        status, body = _http_post(7433, "/step", {"n": 15})
        assert body["ok"] is True
        state = body["state"]
        assert state["cells"]["0,0"]["accumulator"]["total"] == 9
        assert state["cells"]["0,1"]["comparator"]["out_buffer"] == 1
        assert state["cells"]["0,2"]["latch"]["state"] is True

        # the sticky-latch check too, same discipline as #340's own acceptance test
        for _ in range(5):
            _http_post(7433, "/deliver", {"row": 0, "col": 0, "direction": "s", "value": 1})
        status, body = _http_post(7433, "/step", {"n": 15})
        state = body["state"]
        assert state["cells"]["0,0"]["accumulator"]["total"] == 4
        assert state["cells"]["0,1"]["comparator"]["out_buffer"] == 0
        assert state["cells"]["0,2"]["latch"]["state"] is True   # still sticky-set
    finally:
        server.shutdown()


def test_real_server_html_page_loads():
    server = serve(port=7434, open_browser=False)
    try:
        time.sleep(0.3)
        with urllib.request.urlopen(f"http://localhost:7434/") as resp:
            assert resp.status == 200
            html = resp.read().decode()
            assert "<!DOCTYPE html>" in html
            assert "Unicell-S Workbench" in html
    finally:
        server.shutdown()


def test_real_server_unknown_route_returns_404():
    server = serve(port=7435, open_browser=False)
    try:
        time.sleep(0.3)
        try:
            urllib.request.urlopen(f"http://localhost:7435/bogus")
            raise AssertionError("expected HTTPError 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()


def test_real_server_compile_failure_over_http():
    server = serve(port=7436, open_browser=False)
    try:
        time.sleep(0.3)
        broken = "program broken { place r1 as ram_constant at (0,0) { init_data: 1 } }"
        status, body = _http_post(7436, "/compile", {"source": broken, "language": "dsl"})
        assert body["ok"] is False
        assert "missing" in body["diagnostics"][0]["problem"]
    finally:
        server.shutdown()


def test_real_server_demos_and_regions_end_to_end():
    server = serve(port=7437, open_browser=False)
    try:
        time.sleep(0.3)
        status, body = _http_get(7437, "/demos")
        assert body["ok"] is True and "sentinel" in body["demos"]

        status, body = _http_post(7437, "/load_region", {
            "name": "a", "source": DEMOS["sentinel"]["source"], "language": "dsl",
            "row_offset": 0, "col_offset": 0,
        })
        assert body["ok"] is True

        status, body = _http_post(7437, "/load_region", {
            "name": "b", "source": DEMOS["sentinel"]["source"], "language": "dsl",
            "row_offset": 5, "col_offset": 0,
        })
        assert body["ok"] is True

        status, body = _http_get(7437, "/regions")
        assert set(body["regions"].keys()) == {"a", "b"}

        status, body = _http_post(7437, "/deliver", {"row": 0, "col": 0, "direction": "n", "value": 1})
        for _ in range(8):
            _http_post(7437, "/deliver", {"row": 0, "col": 0, "direction": "n", "value": 1})
        status, body = _http_post(7437, "/step", {"n": 15})
        assert body["state"]["cells"]["0,2"]["latch"]["state"] is True

        status, body = _http_post(7437, "/clear_region", {"name": "a"})
        assert body["ok"] is True
        assert "0,0" not in body["state"]["cells"]

        status, body = _http_get(7437, "/regions")
        assert set(body["regions"].keys()) == {"b"}
    finally:
        server.shutdown()


def test_real_server_load_region_auto_placement_end_to_end():
    # the real loader/binder stage (#375), exercised through the actual
    # live HTTP API -- omitting row_offset/col_offset entirely (not
    # sending the keys at all, the real way a client would do it) must
    # trigger auto-placement, not silently default to (0,0)-manual in
    # a way that would collide with an already-loaded region.
    server = serve(port=7438, open_browser=False)
    try:
        time.sleep(0.3)
        status, body = _http_post(7438, "/load_region", {
            "name": "a", "source": DEMOS["sentinel"]["source"], "language": "dsl",
            "row_offset": 0, "col_offset": 0,
        })
        assert body["ok"] is True

        # NOTE: row_offset/col_offset genuinely absent from this body,
        # not sent as 0 -- this is the real auto-placement request shape.
        status, body = _http_post(7438, "/load_region", {
            "name": "b", "source": DEMOS["sentinel"]["source"], "language": "dsl",
        })
        assert body["ok"] is True
        b_positions = set(tuple(p) for p in body["region"]["positions"])
        assert not ({(0, 0), (0, 1), (0, 2)} & b_positions)
    finally:
        server.shutdown()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
