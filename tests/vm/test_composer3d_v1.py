"""tests/vm/test_composer3d_v1.py -- ledger #1312: the separate 3D Composer (experimental/three_d/composer3d_v1.py), VM ONLY exploration of the six-face toy grid.
Checks: edits refused cleanly and undo; join routing (including through other layers); file round-trip; the stepper equals Grid3.run; the adder example equals real addition;
the live HTTP server serves the page and the JS and answers the API; the loopback-only host check."""
import json
import os
import random
import sys
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "experimental", "three_d"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import composer3d_v1 as c3  # noqa: E402
import experimental_3d_nor_v2 as m3  # noqa: E402

M = 0xFFFFFFFF


def to_grid3(d):
    g = m3.Grid3()
    for p, n in d.nodes.items():
        c = m3.Cell3(n["kind"], n["gate"], n["shift"], n["left"])
        c.down = sorted(n["down"])
        g.add(p, c)
    return g


def test_place_refusals_and_undo():
    d = c3.Design(4, 4, 2)
    d.place((0, 0, 0), name="a")
    for bad in ({"pos": (0, 0, 0)}, {"pos": (4, 0, 0)}, {"pos": (0, 0, 2)}, {"pos": (1, 1, 0), "name": "a"}, {"pos": (1, 1, 0), "kind": "gate", "gate": "BAD"}, {"pos": (1, 1, 0), "shift": 40}):
        with pytest.raises(c3.DesignError):
            d.place(**bad)
    assert list(d.nodes) == [(0, 0, 0)]
    d.place((1, 0, 0))
    d.undo()
    assert list(d.nodes) == [(0, 0, 0)]
    d.undo()
    assert not d.nodes
    with pytest.raises(c3.DesignError):
        d.undo()


def test_face_needs_a_neighbour_and_join_adjacent():
    d = c3.Design(3, 3, 3)
    a = d.place((1, 1, 1), name="a")
    with pytest.raises(c3.DesignError):
        d.set_face(a, "U", True)
    d.place((1, 1, 2), name="b")
    d.set_face(a, "U", True)
    assert d.nodes[a]["down"] == {4}
    d.set_face(a, "U", False)
    assert d.nodes[a]["down"] == set()
    assert d.link(a, (1, 1, 2)) == []
    with pytest.raises(c3.DesignError):
        d.link(a, (1, 1, 2))          # already joined


def test_route_goes_through_other_layers_when_the_layer_is_blocked():
    d = c3.Design(3, 5, 2)
    d.place((1, 0, 0), name="s")
    d.place((1, 4, 0), name="t")
    for r in range(3):                 # a wall on layer 0 at column 2
        d.place((r, 2, 0), name="x%d" % r)
    with pytest.raises(c3.DesignError):
        d.link((1, 0, 0), (1, 4, 0), any_layer=False)
    path = d.link((1, 0, 0), (1, 4, 0), any_layer=True)
    assert path and any(p[2] == 1 for p in path)
    # and it really carries a word
    out = c3.Sim(d, {(1, 0, 0): 0x1234}, (1, 4, 0)).run_to_watch()
    assert out == (len(path) + 2, 0x1234)


def test_route_does_not_run_into_a_face_that_points_at_a_free_square():
    d = c3.Design(1, 5, 1)
    d.place((0, 0, 0), name="a")
    d.place((0, 4, 0), name="b")
    d.place((0, 2, 0), name="m")
    d.nodes[(0, 0, 0)]["down"].add(2)                 # a points E at (0,1): a dangling face, whose square a new relay must not take
    with pytest.raises(c3.DesignError):
        d.link((0, 4, 0), (0, 0, 0), any_layer=False)


def test_layers_added_and_removed_keep_neighbours():
    d = c3.Design(2, 2, 2)
    d.place((0, 0, 0), name="a")
    d.place((0, 0, 1), name="b")
    d.link((0, 0, 0), (0, 0, 1))
    d.add_layer("bottom")
    assert sorted(d.nodes) == [(0, 0, 1), (0, 0, 2)] and d.layers == 3
    assert d.pos_of("a") == (0, 0, 1) and d.nodes[(0, 0, 1)]["down"] == {4}
    with pytest.raises(c3.DesignError):
        d.remove_layer("top")
    d.remove_layer("bottom")
    assert d.layers == 2 and d.pos_of("a") == (0, 0, 0)
    with pytest.raises(c3.DesignError):
        d.resize(layers=1)


def test_export_roundtrip_and_bad_files():
    d = c3.EXAMPLES["gate"][1]()
    doc = json.loads(json.dumps(d.export()))
    e = c3.Design.from_export(doc)
    assert e.export() == d.export()
    for bad in ({}, {"format": c3.FORMAT, "version": 2}, dict(doc, cells=[dict(doc["cells"][0], pos=[9, 9, 9])]), dict(doc, cells=[doc["cells"][0], doc["cells"][0]]), dict(doc, cells=[dict(doc["cells"][0], down=["X"])])):
        with pytest.raises(c3.DesignError):
            c3.Design.from_export(bad)


@pytest.mark.parametrize("which", ["gate", "crossing"])
def test_stepper_equals_grid3_run(which):
    d = c3.EXAMPLES[which][1]()
    g = to_grid3(d)
    inj = {d.pos_of("A"): 0xF0F0F0F0, d.pos_of("B"): 0x0FF00FF0} if which == "gate" else {d.pos_of("a0"): 0xAAAA, d.pos_of("b0"): 0xBBBB}
    for watch in sorted(d.nodes):
        want = g.run(inj, watch)
        got = c3.Sim(d, inj, watch).run_to_watch()
        assert got == want, watch


def test_gate_example_is_xor_then_shift():
    d = c3.EXAMPLES["gate"][1]()
    t, val = c3.Sim(d, {d.pos_of("A"): 0xFF00FF00, d.pos_of("B"): 0x0F0F0F0F}, d.pos_of("E")).run_to_watch()
    assert val == ((0xFF00FF00 ^ 0x0F0F0F0F) << 4) & M and t == 3


def test_crossing_example_keeps_two_words_apart():
    d = c3.EXAMPLES["crossing"][1]()
    s = c3.Sim(d, {d.pos_of("a0"): 0xAAAA, d.pos_of("b0"): 0xBBBB})
    assert s.run()
    assert s.out[d.pos_of("a4")] == 0xAAAA and s.out[d.pos_of("b6")] == 0xBBBB and s.out[d.pos_of("a2")] == 0xAAAA


def test_adder_example_is_real_addition():
    d = c3.EXAMPLES["adder"][1]()
    assert d.summary()["cells"] == 44 and d.layers >= 3
    res = c3.selfcheck(d)
    assert res["ok"] and res["checked"] > 90 and len(res["ticks"]) == 1
    # the check bites: break one join and it must fail
    p = next(p for p, n in sorted(d.nodes.items()) if n["kind"] == "gate")
    d.nodes[p]["gate"] = "OR" if d.nodes[p]["gate"] != "OR" else "XOR"
    assert not c3.selfcheck(d)["ok"]


def test_problems_report_loops_and_lonely_gates():
    d = c3.Design(1, 3, 1)
    d.place((0, 0, 0), name="a")
    d.place((0, 1, 0), name="b")
    d.place((0, 2, 0), kind="gate", gate="AND", name="g")
    d.link((0, 0, 0), (0, 1, 0))
    d.link((0, 1, 0), (0, 0, 0))
    d.link((0, 1, 0), (0, 2, 0))
    msgs = " | ".join(p["msg"] for p in d.problems())
    assert "loop" in msgs and "gate g has 1 input" in msgs


def test_controller_sim_flow():
    c = c3.Composer3D(c3.EXAMPLES["gate"][1]())
    st = c.handle("sim_start", {"inputs": {"A": "0xFF", "B": 15}, "watch": "E"})
    assert st["sim"]["tick"] == 0 and st["entries"] == ["A", "B"]
    st = c.handle("sim_run", {})
    assert st["sim"]["settled"] and st["sim"]["watch"]["value"] == (0xFF ^ 15) << 4
    assert c.handle("sim_reset", {})["sim"] is None
    with pytest.raises(c3.DesignError):
        c.handle("sim_step", {})
    with pytest.raises(c3.DesignError):
        c.handle("sim_start", {"inputs": {"A": "zz"}})
    c.handle("sim_start", {"inputs": {"A": 1}})
    assert c.handle("place", {"pos": [0, 0, 0]})["sim"] is None      # any edit stops the run


@pytest.fixture(scope="module")
def server():
    srv = c3.serve(c3.Composer3D(c3.EXAMPLES["gate"][1]()), port=0, block=False)
    yield "http://127.0.0.1:%d" % srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def _post(base, action, body):
    req = urllib.request.Request(base + "/api/" + action, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def test_http_page_js_and_api(server):
    page = urllib.request.urlopen(server + "/").read().decode()
    assert "3D Composer" in page and 'id="depth"' in page and "composer3d_v1.js" in page and "Exploration only" in page
    js = urllib.request.urlopen(server + "/composer3d_v1.js").read().decode()
    assert "pointerdown" in js and "alphaOf" in js
    st = json.loads(urllib.request.urlopen(server + "/api/state").read())
    assert st["ok"] and len(st["cells"]) == 4 and st["size"]["layers"] == 2
    bad = _post(server, "place", {"pos": [0, 0, 0], "kind": "gate", "gate": "NOPE"})
    assert not bad["ok"] and "gate" in bad["error"]
    assert not _post(server, "nonsense", {})["ok"]
    assert not _post(server, "place", {})["ok"]                       # missing field: refused, not a crash
    ok = _post(server, "place", {"pos": [0, 0, 0]})
    assert ok["ok"] and len(ok["cells"]) == 5
    assert _post(server, "undo", {})["ok"]


def test_http_refuses_foreign_host(server):
    req = urllib.request.Request(server + "/api/state", headers={"Host": "evil.example"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 403
