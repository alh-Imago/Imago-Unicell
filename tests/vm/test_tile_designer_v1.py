"""
test_tile_designer_v1.py — real, direct verification of
`nano/tile_designer_v1.py` (points.md #487): the `TileDesignerController`
tested directly (no HTTP), and the real, running HTTP server exercised
with real sockets and real `urllib` requests -- matching `test_
workbench_v1.py`'s own established two-layer testing discipline.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
import icm_v4 as v4  # noqa: E402
from tile_designer_v1 import TileDesignerController, serve  # noqa: E402
from dsp_wrapper_automaton_v1 import _float_to_bits, _bits_to_float  # noqa: E402


def f(val: float) -> int:
    return _float_to_bits(val)


# ── Controller: pure logic, no HTTP ─────────────────────────────────

def test_library_lists_both_kinds_and_composed():
    ctrl = TileDesignerController()
    result = ctrl.list_library()
    assert result["ok"] is True
    names = {t["name"] for t in result["tiles"]}
    assert "ram_constant" in names          # super Tier-0
    assert "dsp_add" in names               # DSP wrapper
    assert "sentinel" in names              # composed
    assert "dsp_add_and_hold" in names      # multi-kind composed (#486)

    sentinel_entry = next(t for t in result["tiles"] if t["name"] == "sentinel")
    assert sentinel_entry["kind"] == "composed"
    assert "cmp.threshold" in sentinel_entry["params"]


def test_add_instance_rejects_unknown_tile():
    ctrl = TileDesignerController()
    result = ctrl.add_instance("x", "no_such_tile", 0, 0)
    assert result["ok"] is False
    assert "no tile named" in result["error"]


def test_add_instance_rejects_duplicate_id():
    ctrl = TileDesignerController()
    ctrl.add_instance("x", "ram_constant", 0, 0)
    result = ctrl.add_instance("x", "ram_constant", 1, 1)
    assert result["ok"] is False
    assert "already exists" in result["error"]


def test_set_port_rejects_unknown_port():
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "dsp_add", 0, 0)
    result = ctrl.set_port("a", "bogus_port", "n")
    assert result["ok"] is False
    assert "no port" in result["error"]


def test_move_and_remove_instance():
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "ram_constant", 0, 0)
    result = ctrl.move_instance("a", 3, 4)
    assert result["ok"] is True
    assert (result["instance"]["row"], result["instance"]["col"]) == (3, 4)
    result = ctrl.remove_instance("a")
    assert result["ok"] is True
    assert ctrl.describe()["instances"] == []


def test_validate_reports_unresolved_ports():
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "dsp_add", 0, 0)
    result = ctrl.validate()
    assert result["ok"] is False
    assert len(result["errors"]) == 1
    assert result["errors"][0]["instance_id"] == "a"


def test_validate_and_export_succeed_once_fully_wired():
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "dsp_add", 0, 0)
    ctrl.set_port("a", "in_a", "n")
    ctrl.set_port("a", "in_b", "s")
    ctrl.set_port("a", "out", "e")
    result = ctrl.validate()
    assert result["ok"] is True and result["errors"] == []

    icm = ctrl.export_icm("solo_dsp_add")
    assert isinstance(icm, v4.IcmV4File)
    assert len(icm.dsp_wrapper_records) == 1 and icm.super_records == []


def test_export_icm_raises_when_design_invalid():
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "dsp_add", 0, 0)   # unwired
    try:
        ctrl.export_icm("broken")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "real error" in str(e)


def test_position_collision_caught_by_validate():
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "ram_constant", 0, 0)
    ctrl.set_port("a", "out", "e")
    ctrl.set_param("a", "init_data", 1)
    ctrl.add_instance("b", "ram_constant", 0, 0)   # same cell
    ctrl.set_port("b", "out", "e")
    ctrl.set_param("b", "init_data", 2)
    result = ctrl.validate()
    assert result["ok"] is False
    assert any("already occupied" in e["problem"] for e in result["errors"])


def test_mixed_design_super_and_dsp_wrapper_produces_icm_v4_and_runs_correctly():
    """The real point: a Designer session mixing a DSP wrapper
    instance and a super-cell instance, exported to a real IcmV4File,
    then actually RUN through a live grid to confirm the correct
    computed result -- not just that export succeeds."""
    ctrl = TileDesignerController()
    ctrl.add_instance("adder", "dsp_add", 0, 0)
    ctrl.set_port("adder", "in_a", "n")
    ctrl.set_port("adder", "in_b", "s")
    ctrl.set_port("adder", "out", "e")

    ctrl.add_instance("sink", "ram_flowing", 0, 1)
    ctrl.set_port("sink", "in", "w")
    ctrl.set_port("sink", "out", "e")

    result = ctrl.validate()
    assert result["ok"] is True

    icm = ctrl.export_icm("designer_mixed_demo")
    assert isinstance(icm, v4.IcmV4File)
    assert len(icm.dsp_wrapper_records) == 1 and len(icm.super_records) == 1

    grid = icm.build_grid()
    grid.cells[(0, 0)].deliver({0: f(2.0), 1: f(5.5)})   # N=0, S=1 -> 7.5
    grid.tick()
    grid.tick()
    val, valid, _ = grid.cells[(0, 1)]._offer_state()
    assert valid and _bits_to_float(val) == 7.5


def test_super_only_design_produces_plain_icm_v3():
    ctrl = TileDesignerController()
    ctrl.add_instance("r", "ram_constant", 2, 2)
    ctrl.set_port("r", "out", "e")
    ctrl.set_param("r", "init_data", 99)
    icm = ctrl.export_icm("super_only_demo")
    assert isinstance(icm, v3.IcmV3File)
    assert not isinstance(icm, v4.IcmV4File)


def test_composed_tile_instance_via_designer():
    """A composed (Tier-1) tile placed through the Designer -- proves
    the controller treats composed and Tier-0-shaped tiles uniformly,
    same as the compiler does (#485/#486)."""
    ctrl = TileDesignerController()
    ctrl.add_instance("s", "sentinel", 0, 0)
    ctrl.set_port("s", "inc", "n")
    ctrl.set_port("s", "dec", "s")
    ctrl.set_port("s", "clear", "s")
    ctrl.set_port("s", "out", "e")
    ctrl.set_param("s", "cmp.threshold", 8)
    result = ctrl.validate()
    assert result["ok"] is True, result["errors"]
    icm = ctrl.export_icm("designer_sentinel")
    assert isinstance(icm, v3.IcmV3File)
    assert len(icm.records) == 3   # acc, cmp, lat


def test_save_icm_writes_a_real_loadable_file(tmp_path):
    ctrl = TileDesignerController()
    ctrl.add_instance("a", "dsp_add", 0, 0)
    ctrl.set_port("a", "in_a", "n")
    ctrl.set_port("a", "in_b", "s")
    ctrl.set_port("a", "out", "e")
    path = str(tmp_path / "designer_output.icm.json")
    result = ctrl.save_icm(path, "saved_demo")
    assert result["ok"] is True
    reloaded = v4.IcmV4File.load(path)
    assert len(reloaded.dsp_wrapper_records) == 1


# ── Real, running HTTP server -- real sockets, real requests ────────

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


def test_real_server_full_mixed_design_sequence_end_to_end():
    server = serve(port=7441, open_browser=False)
    try:
        time.sleep(0.3)

        status, body = _http_get(7441, "/library")
        assert body["ok"] is True
        assert any(t["name"] == "dsp_add" for t in body["tiles"])

        status, body = _http_post(7441, "/add_instance",
                                   {"instance_id": "adder", "tile_name": "dsp_add", "row": 0, "col": 0})
        assert body["ok"] is True

        _http_post(7441, "/set_port", {"instance_id": "adder", "port_name": "in_a", "direction": "n"})
        _http_post(7441, "/set_port", {"instance_id": "adder", "port_name": "in_b", "direction": "s"})
        _http_post(7441, "/set_port", {"instance_id": "adder", "port_name": "out", "direction": "e"})

        status, body = _http_post(7441, "/add_instance",
                                   {"instance_id": "sink", "tile_name": "ram_flowing", "row": 0, "col": 1})
        assert body["ok"] is True
        _http_post(7441, "/set_port", {"instance_id": "sink", "port_name": "in", "direction": "w"})
        _http_post(7441, "/set_port", {"instance_id": "sink", "port_name": "out", "direction": "e"})

        status, body = _http_post(7441, "/validate", {})
        assert body["ok"] is True and body["errors"] == []

        status, body = _http_post(7441, "/export_icm", {"name": "http_mixed_demo"})
        assert body["ok"] is True
        icm_dict = body["icm"]
        assert icm_dict["format_version"] == "icm-v4"
        assert len(icm_dict["dsp_wrapper_records"]) == 1
        assert len(icm_dict["super_records"]) == 1
    finally:
        server.shutdown()


def test_real_server_html_page_loads():
    server = serve(port=7442, open_browser=False)
    try:
        time.sleep(0.3)
        with urllib.request.urlopen("http://localhost:7442/") as resp:
            assert resp.status == 200
            html = resp.read().decode()
            assert "Tile Designer" in html
    finally:
        server.shutdown()


def test_real_server_unknown_route_returns_404():
    server = serve(port=7443, open_browser=False)
    try:
        time.sleep(0.3)
        try:
            urllib.request.urlopen("http://localhost:7443/bogus")
            assert False, "expected HTTPError"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()


def test_real_server_add_instance_bad_tile_returns_ok_false_not_500():
    server = serve(port=7444, open_browser=False)
    try:
        time.sleep(0.3)
        status, body = _http_post(7444, "/add_instance",
                                   {"instance_id": "x", "tile_name": "no_such_tile", "row": 0, "col": 0})
        assert status == 200
        assert body["ok"] is False
    finally:
        server.shutdown()
