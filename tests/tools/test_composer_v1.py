"""tests/tools/test_composer_v1.py -- the Composer's layout side (tools/flex_layout_view_v1.py) and its front-panel page (nano/composer_page_v1.py).

The checks the design note asks for: an imported design re-exports EXACTLY (same records, same hop model); a move is re-routed and re-balanced by the layout engine, and the moved
fp adder still computes the right answers in the FlexGrid VM; a refused move changes nothing; cells wired by fields the engine does not derive stay pinned; the page and its JSON API work."""
import json
import os
import sys
import threading
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for d in ("tools", "nano", os.path.join("tests", "vm")):
    sys.path.insert(0, os.path.join(ROOT, d))

import flex_layout_view_v1 as flv  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

EXAMPLES = os.path.join(ROOT, "nano", "examples")


def norm(r):
    cfg = {k: sorted(v) if isinstance(v, list) else v for k, v in r.core_config.items()}
    return (r.row, r.col, r.core, cfg, r.addon_config, r.preload_value, r.io_name)


def same(a, b):
    a, b = {r.cell_id: r for r in a}, {r.cell_id: r for r in b}
    assert set(a) == set(b)
    return [k for k in a if norm(a[k]) != norm(b[k])]


@pytest.fixture(scope="module")
def fp16():
    import fp_assembler_v1 as fa
    import fp_add_v1 as fadd
    g = Grid(rows=34, cols=330)
    ent, ex, consts = fadd.fp_add(g, fa.FP16)
    g.balance()
    return g, ent, ex, consts


def test_fp_adder_round_trips_exactly(fp16):
    g = fp16[0]
    lay = flv.Layout(g.records(), name="fp16")
    assert same(g.records(), lay.records()) == []
    assert lay.grid.hops() == g.hops() and lay.grid.problems() == []
    snap = lay.snapshot()
    assert snap["summary"]["cells"] == len(g.nodes) and len(snap["crossings"]) == len(g.crossed) > 0
    assert snap["summary"]["routes"] > 0 and not snap["summary"]["pinned"]


@pytest.mark.parametrize("name", sorted(f for f in os.listdir(EXAMPLES) if f.endswith(".json")))
def test_examples_round_trip_exactly(name, tmp_path):
    lay = flv.Layout.load(os.path.join(EXAMPLES, name))
    _, recs = flv.nl.load_records(os.path.join(EXAMPLES, name))
    def canon(v, k):
        if k in flv.MASKS and isinstance(v, list):
            return [d.lower() for d in v]
        if k == "upstream_dir" and isinstance(v, list) and len(v) == 1:          # ICM-VIX ["W"] is written as the ICM v3 code 3
            return "NSEW".index(v[0].upper())
        return v
    lower = lambda rs: [type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, addon_config=r.addon_config, io_name=r.io_name, preload_value=r.preload_value,
                                core_config={k: canon(v, k) for k, v in r.core_config.items()}) for r in rs]
    assert same(lower(recs), lower(lay.records())) == []
    out = lay.save(str(tmp_path / "x.icm.json"))
    assert len(IcmV3File.load(out).records) == len(recs)
    assert sorted(flv.nl.extract(out)[3]) == sorted(flv.nl.extract(os.path.join(EXAMPLES, name))[3])       # the same netlist, edge for edge


def test_branch_wired_cells_are_pinned():
    lay = flv.Layout.load(os.path.join(EXAMPLES, "cordic_z_convergence.icm-hier.json"))
    branch = next(k for k, n in lay.grid.nodes.items() if n["core"] == "branch")
    r, c = lay.grid.pos(branch)
    res = lay.move(branch, r, c + 1)
    assert not res["ok"] and "pinned" in res["error"]


def test_move_reroutes_and_the_adder_still_adds(fp16):
    from fp_block_runner_v1 import run_vm
    from test_fp_add_v1 import FORMATS, ref_add, vectors
    g, ent, ex, consts = fp16
    lay = flv.Layout(g.records(), name="fp16")
    before = lay.records()
    moved = 0
    for name in ("ADD.ADDSUM", "ADD.MULM", "ADD.ADDA"):
        r, c = lay.grid.pos(name)
        for dr, dc in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            res = lay.move(name, r + dr, c + dc)
            if res["ok"]:
                assert res["rerouted"] and lay.grid.pos(name) == (r + dr, c + dc)
                moved += 1
                break
    assert moved == 3 and lay.grid.problems() == []
    assert sorted((r.cell_id, r.row, r.col) for r in before) != sorted((r.cell_id, r.row, r.col) for r in lay.records())
    fmt = FORMATS["fp16"]
    A, B = vectors(fmt)
    n = 3
    got = run_vm(lay.records(), {ent["a"]: A[:n], ent["b"]: B[:n]}, ex, consts, ticks=900)["R"]
    assert got == [ref_add(fmt, x, y)[0] for x, y in zip(A[:n], B[:n])]
    for _ in range(moved):
        assert lay.undo()["ok"]
    assert same(before, lay.records()) == [] and not lay.undo()["ok"]


def test_refused_move_changes_nothing(fp16):
    g = fp16[0]
    lay = flv.Layout(g.records(), name="fp16")
    before = lay.records()
    r, c = lay.grid.pos("ADD.ADDSUM")
    occupied = lay.grid.pos("ADD.SF")
    res = lay.move("ADD.ADDSUM", *occupied)
    assert not res["ok"] and "taken" in res["error"]
    relay = next(v["relays"][0] for v in lay.grid.routes.values() if v["relays"])
    assert not lay.move(relay, r, c)["ok"]
    assert not lay.move("ADD.ADDSUM", -1, 0)["ok"]
    assert same(before, lay.records()) == []


def test_page_and_api():
    import frontend_v1
    server = frontend_v1.serve(port=0)
    port = server.server_address[1]
    base = f"http://localhost:{port}"

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req))
    try:
        html = urllib.request.urlopen(base + "/composer").read().decode()
        assert "Composer" in html and "/composer/api/move" in html
        assert "not built yet" not in urllib.request.urlopen(base + "/menu").read().decode()
        assert json.load(urllib.request.urlopen(base + "/composer/api/state"))["layout"] is None
        bad = post("/composer/api/load", {"text": "{not json", "name": "x.json"})
        assert not bad["ok"]
        res = post("/composer/api/load", {"example": "parallel_reduction_tree.icm-hier.json"})
        assert res["ok"] and res["layout"]["summary"]["routes"] == 6
        cell = next(c for c in res["layout"]["cells"] if c["movable"] and c["core"] == "adder")
        res = post("/composer/api/move", {"name": cell["name"], "r": cell["r"], "c": cell["c"] + 1})
        assert res["ok"], res
        saved = json.load(urllib.request.urlopen(base + "/composer/api/save"))
        assert saved["format_version"] == "icm-v3" and len(saved["records"]) >= 12       # a move may add relays (a longer route, or a timing detour)
        assert post("/composer/api/undo", {})["ok"]
    finally:
        server.shutdown()


@pytest.mark.skipif(__import__("shutil").which("iverilog") is None, reason="needs iverilog")
def test_moved_adder_in_generated_rtl(fp16, tmp_path):
    """The generator stays the oracle: the hand-moved adder, built to RTL, gives the reference result on every vector."""
    from fp_block_runner_v1 import run_rtl
    from test_fp_add_v1 import FORMATS, ref_add, vectors
    g, ent, ex, _ = fp16
    lay = flv.Layout(g.records(), name="fp16")
    for name, (dr, dc) in (("ADD.ADDSUM", (1, 0)), ("ADD.MULM", (0, 1)), ("ADD.RND.ADD3", (1, 0))):
        r, c = lay.grid.pos(name)
        assert lay.move(name, r + dr, c + dc)["ok"]
    fmt = FORMATS["fp16"]
    A, B = vectors(fmt)
    got = run_rtl(str(tmp_path), "composer_moved", lay.records(), {ent["a"]: A, ent["b"]: B}, ex, "plain", settle=60000)["R"]
    assert got == [ref_add(fmt, x, y)[0] for x, y in zip(A, B)]
