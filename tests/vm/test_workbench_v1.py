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

from workbench_v1 import WorkbenchController, serve  # noqa: E402
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


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
