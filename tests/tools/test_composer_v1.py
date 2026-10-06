"""tests/tools/test_composer_v1.py -- the Composer's layout side (tools/flex_layout_view_v1.py) and its front-panel page (nano/composer_page_v1.py).

The checks the design note asks for: an imported design re-exports EXACTLY (same records, same hop model); a move is re-routed and re-balanced by the layout engine, and the moved
fp adder still computes the right answers in the FlexGrid VM; a refused move changes nothing; cells wired by fields the engine does not derive stay pinned; the page and its JSON API work."""
import collections
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
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

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
        if k == "upstream_dir" and isinstance(v, list) and len(v) == 1:          # ICM-VIX ["W"] is written as the ICM v3 code 3
            return "NSEW".index(v[0].upper())
        if isinstance(v, list) and all(isinstance(d, str) and len(d) == 1 for d in v):
            return [d.lower() for d in v]
        return v
    lower = lambda rs: [type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, addon_config=r.addon_config, io_name=r.io_name, preload_value=r.preload_value,
                                core_config={k: canon(v, k) for k, v in r.core_config.items()}) for r in rs]
    assert same(lower(recs), lower(lay.records())) == []
    out = lay.save(str(tmp_path / "x.icm.json"))
    assert len(IcmV3File.load(out).records) == len(recs)
    assert sorted(flv.nl.extract(out)[3]) == sorted(flv.nl.extract(os.path.join(EXAMPLES, name))[3])       # the same netlist, edge for edge


def test_branch_cells_move_with_their_outcome_routes(tmp_path):
    """A branch's joins are tagged by outcome (route_low / equal / high) and input (upstream_dir), so it moves like any cell and the netlist keeps its outcomes."""
    path = os.path.join(EXAMPLES, "cordic_z_convergence.icm-hier.json")
    lay = flv.Layout.load(path)
    assert not lay.pinned
    moved = None
    joined = [t[1] for t, tag in lay.tags.items() if lay.grid.nodes[t[0]]["core"] == "branch" and set(tag["out"]) & {"low", "high"}]
    for k in joined:                            # a cell fed by a branch outcome, moved to the first square that routes (the design is packed tight)
        r, c = lay.grid.pos(k)
        for dr, dc in sorted(((dr, dc) for dr in range(-3, 4) for dc in range(-3, 4) if (dr, dc) != (0, 0)), key=lambda x: abs(x[0]) + abs(x[1])):
            if lay.move(k, r + dr, c + dc)["ok"]:
                moved = k
                break
        if moved:
            break
    assert moved
    out = lay.save(str(tmp_path / "moved.icm.json"))
    def logical(p):
        _, _, cells, edges, *_ = flv.nl.extract(p)
        return cells, edges
    c0, e0 = logical(path)
    c1, e1 = logical(out)
    def ends(cells, edges):                     # source -> destination through relay chains, with the outcome and role
        relay = {k for k, r in cells.items() if r.core == "ram" and set(r.core_config) <= set(flv.MASKS) | {"fixed_mode"} and not r.io_name and r.preload_value is None}
        nxt = collections.defaultdict(list)
        for a, b, d, role, oc in edges:
            nxt[a].append((b, role, oc))
        res = set()
        for a, b, d, role, oc in edges:
            if a in relay:
                continue
            cur, r = b, role
            while cur in relay and nxt[cur]:
                cur, r, _ = nxt[cur][0]
            res.add((a, cur, r, tuple(sorted(oc))))
        return res
    assert ends(c0, e0) == ends(c1, e1)


def test_nano_is_editable_and_a_wide_face_field_pins_it():
    """A nano's direction fields come from its joins like any cell's; one using the reserved up/down bits (above the four faces) is kept exactly as read."""
    recs = [IcmV3Record(cell_id="n", row=0, col=0, core="nano", core_config={"routing_mask": 4, "topology": 3, "ready": 1}),
            IcmV3Record(cell_id="r", row=0, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
    lay = flv.Layout(recs)
    assert "n" not in lay.pinned and lay.set_config("n", cfg={"topology": 0xBC, "cardinal_edge": 0b0100})["ok"]
    cfg = {r.cell_id: r for r in lay.records()}["n"].core_config
    assert cfg["topology"] == 0xBC and cfg["cardinal_edge"] == 4 and cfg["routing_mask"] == ["e"]
    wide = [IcmV3Record(cell_id="n", row=0, col=0, core="nano", core_config={"routing_mask": 0b010100, "topology": 3})] + recs[1:]
    lay = flv.Layout(wide)
    assert "n" in lay.pinned and not lay.move("n", 5, 5)["ok"]
    assert same(wide, lay.records()) == []


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
        assert "Composer" in html and "/composer/api/" in html and "SUPER_LATCH" in html
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


# ---- authoring from a blank board, and library blocks (#1004) ------------------------------------------------------------------------
def build_adder(lay, at=(0, 0), names=("A", "B", "ADD", "R"), io=("a", "b", "r")):
    r, c = at
    for (nm, core, dr, dc), port in zip(((names[0], "ram", 2, 1), (names[1], "ram", 6, 1), (names[2], "adder", 4, 8), (names[3], "ram", 4, 14)), (io[0], io[1], None, io[2])):
        res = lay.add_cell(core, r + dr, c + dc, name=nm, io=port)
        assert res["ok"], res
    for a, b in ((names[0], names[2]), (names[1], names[2]), (names[2], names[3])):
        assert lay.join(a, b)["ok"]
    assert lay.balance()["ok"] and lay.grid.problems() == []


def test_design_from_scratch_runs(tmp_path):
    from fp_block_runner_v1 import run_vm
    lay = flv.Layout.new(12, 20, "adder")
    build_adder(lay)
    recs = {r.cell_id: r for r in lay.records()}
    assert recs["ADD"].core_config["upstream_mask"] and recs["R"].io_name == "r"
    assert run_vm(lay.records(), {"A": [1, 5, 100], "B": [2, 7, 23]}, {"R": "R"}, {}, ticks=200)["R"] == [3, 12, 123]
    again = flv.Layout.load(lay.save(str(tmp_path / "adder.icm.json")))       # what was saved imports back to the same records
    assert same(lay.records(), again.records()) == []


def test_config_fields_are_checked():
    lay = flv.Layout.new(6, 6)
    assert lay.add_cell("comparator", 2, 2, name="C")["ok"]
    res = lay.set_config("C", cfg={"threshold": 77})
    assert res["ok"] and int(res["latch"], 16) == icm_v3_encode("comparator", {"threshold": 77, "upstream_mask": [], "downstream_mask": []})
    assert not lay.set_config("C", cfg={"threshold": 1 << 40})["ok"]           # wider than its 32-bit field
    assert not lay.set_config("C", cfg={"downstream_mask": 1})["ok"]           # faces come from the joins
    assert not lay.set_config("C", cfg={"no_such": 1})["ok"]
    assert lay.grid.nodes["C"]["cfg"] == {"threshold": 77}


def icm_v3_encode(core, cfg):
    import icm_v3
    return icm_v3.encode_super_latch(core, cfg)


def test_joins_use_ports_and_roles():
    """A latch's set/clear inputs, a branch's outcomes and a sequencer's lack of inputs are respected, and the file says so."""
    lay = flv.Layout.new(10, 12)
    for nm, core, r, c in (("S", "ram", 1, 1), ("K", "ram", 8, 1), ("L", "latch", 4, 6), ("Q", "sequencer", 1, 10), ("BR", "branch", 6, 10), ("LO", "ram", 9, 10), ("HI", "ram", 3, 10)):
        assert lay.add_cell(core, r, c, name=nm)["ok"]
    assert lay.join("S", "L", role="set")["ok"] and lay.join("K", "L", role="clear")["ok"]
    assert not lay.join("S", "Q")["ok"]                                       # a sequencer has no input
    assert not lay.join("S", "L", role="in")["ok"]                            # a latch has no plain input
    assert lay.join("L", "BR")["ok"]
    assert not lay.join("K", "BR")["ok"]                                      # a branch has ONE input
    assert lay.join("BR", "LO", out="low")["ok"] and lay.join("BR", "HI", out="high")["ok"]
    assert lay.join("BR", "LO", out="equal")["ok"]                            # a second outcome on the same join
    recs = {r.cell_id: r for r in lay.records()}
    lc, bc = recs["L"].core_config, recs["BR"].core_config
    assert lc["set_dir"] and lc["clear_dir"] and "upstream_mask" not in lc
    assert isinstance(bc["upstream_dir"], int) and bc["route_low"] == bc["route_equal"] and bc["route_high"] and bc["route_high"] != bc["route_low"]
    out = lay.records()
    f = IcmV3File(name="x", records=out)
    assert f.to_dict()["record_hash"]                                         # every record encodes


def test_delete_and_undo():
    lay = flv.Layout.new(12, 20)
    build_adder(lay)
    n = len(lay.grid.nodes)
    assert lay.delete_cell("B")["ok"]
    assert "B" not in lay.grid.nodes and not any("B" in t[:2] for t in lay.tags)
    assert lay.unjoin("A", "ADD")["ok"] and ("A", "ADD") not in lay.grid.routes
    assert lay.undo()["ok"] and lay.undo()["ok"] and len(lay.grid.nodes) == n


def test_library_blocks_compose_and_move(tmp_path):
    from fp_block_runner_v1 import run_vm
    lib = flv.Layout.new(12, 20, "adder")
    build_adder(lib)
    path = lib.save(str(tmp_path / "adder.icm.json"))
    lay = flv.Layout.new(22, 42, "two adders")
    b1 = lay.place_block(path, 1, 1)
    b2 = lay.place_block(path, 1, 22)
    assert b1["ok"] and b2["ok"] and b1["ports"] == ["a", "b", "r"]
    assert not lay.place_block(path, 1, 1)["ok"]                               # overlaps the first
    p1, p2 = lay.blocks[b1["block"]]["ports"], lay.blocks[b2["block"]]["ports"]
    assert lay.add_cell("ram", 14, 10, name="C")["ok"] and lay.add_cell("ram", 16, 38, name="OUT")["ok"]
    assert lay.join(p1["r"], p2["a"])["ok"] and lay.join("C", p2["b"])["ok"] and lay.join(p2["r"], "OUT")["ok"]
    assert lay.balance()["ok"]
    ins = {p1["a"]: [1, 5, 40], p1["b"]: [2, 7, 2], "C": [10, 20, 300]}
    assert run_vm(lay.records(), ins, {"o": "OUT"}, {}, ticks=400)["o"] == [13, 32, 342]
    assert lay.move_block(b2["block"], 6, 22)["ok"]
    assert min(lay.grid.nodes[k]["r"] for k in lay.blocks[b2["block"]]["cells"]) == 6
    r, c = lay.grid.pos(p2["a"])
    assert lay.move(p2["a"], r + 1, c)["ok"]                                  # dragging a cell inside a block moves the whole block
    assert min(lay.grid.nodes[k]["r"] for k in lay.blocks[b2["block"]]["cells"]) == 7
    assert run_vm(lay.records(), ins, {"o": "OUT"}, {}, ticks=400)["o"] == [13, 32, 342]
    assert lay.delete_block(b1["block"])["ok"] and not any(k.startswith(b1["block"] + ".") for k in lay.grid.nodes)
    assert lay.unpack_block(b2["block"])["ok"] and not lay.blocks and lay.movable(p2["a"])


def test_editing_api(tmp_path, monkeypatch):
    import composer_page_v1 as cp
    monkeypatch.setattr(cp, "LIBRARY_DIR", str(tmp_path))
    ctl = cp.ComposerController()
    assert ctl.load({"new": {"rows": 12, "cols": 20, "name": "adder"}})["ok"]
    for core, r, c, name in (("ram", 2, 1, "A"), ("ram", 6, 1, "B"), ("adder", 4, 8, "ADD"), ("ram", 4, 14, "R")):
        assert ctl.edit("add", {"core": core, "r": r, "c": c, "name": name})["ok"]
    for k, io in (("A", "a"), ("B", "b"), ("R", "r")):
        assert ctl.edit("config", {"name": k, "cfg": {}, "io": io})["ok"]
    assert ctl.edit("config", {"name": "ADD", "cfg": {"subtract_mode": "1"}})["ok"]
    for a, b in (("A", "ADD"), ("B", "ADD"), ("ADD", "R")):
        assert ctl.edit("join", {"a": a, "b": b})["ok"]
    res = ctl.edit("minuend", {"name": "ADD", "source": "B"})
    assert res["ok"] and not res["layout"]["problems"]
    assert ctl.save_library({"name": "sub ab"})["ok"] and os.path.exists(tmp_path / "sub_ab.icm.json")
    assert not ctl.save_library({"name": "sub ab"})["ok"]                      # no silent overwrite
    assert ctl.load({"new": {"rows": 16, "cols": 30}})["ok"]
    res = ctl.edit("block", {"source": "library", "file": "sub_ab.icm.json", "r": 1, "c": 1})
    assert res["ok"] and res["layout"]["blocks"][0]["ports"]
    assert not ctl.edit("block", {"source": "library", "file": "../../etc/passwd", "r": 1, "c": 1})["ok"]
    assert not ctl.edit("nonsense", {})["ok"]


# ---- saving blocks (ICM-VIX), nano authoring, the step-through (#1005) ----------------------------------------------------------------
def two_adders(tmp_path):
    lib = flv.Layout.new(12, 20, "adder")
    build_adder(lib)
    path = lib.save(str(tmp_path / "adder.icm.json"))
    lay = flv.Layout.new(22, 42, "two")
    b1, b2 = lay.place_block(path, 1, 1)["block"], lay.place_block(path, 1, 22)["block"]
    p1, p2 = lay.blocks[b1]["ports"], lay.blocks[b2]["ports"]
    assert lay.add_cell("ram", 14, 10, name="C")["ok"] and lay.add_cell("ram", 16, 38, name="OUT", io="out")["ok"]
    for a, b in ((p1["r"], p2["a"]), ("C", p2["b"]), (p2["r"], "OUT")):
        assert lay.join(a, b)["ok"]
    assert lay.balance()["ok"]
    return lay, b1, b2, {p1["a"]: [1, 5, 40], p1["b"]: [2, 7, 2], "C": [10, 20, 300]}


def test_save_keeps_blocks(tmp_path):
    from fp_block_runner_v1 import run_vm
    lay, b1, b2, ins = two_adders(tmp_path)
    out = lay.save(str(tmp_path / "two.icm-hier.json"))                      # a design with blocks saves as ICM-VIX
    doc = json.load(open(out))
    assert doc["format_version"] == "icm-vix-v1"
    assert [p["instance"] for p in doc["design_map"]["placements"]] == ["top", b1, b2]
    back = flv.Layout.load(out)
    assert set(back.blocks) == {b1, b2} and sorted(back.blocks[b2]["ports"]) == ["a", "b", "r"]
    assert same(lay.records(), back.records()) == []                          # same cells, same names, same configuration
    assert run_vm(back.records(), ins, {"o": "OUT"}, {}, ticks=400)["o"] == [13, 32, 342]
    assert back.move_block(b2, 5, 22)["ok"]                                    # a reloaded block is still a block (its ports stay cells, not relays)
    assert run_vm(back.records(), ins, {"o": "OUT"}, {}, ticks=400)["o"] == [13, 32, 342]
    flat = lay.save(str(tmp_path / "flat.icm.json"), fmt="v3")
    assert json.load(open(flat))["format_version"] == "icm-v3" and not flv.Layout.load(flat).blocks
    other = flv.Layout.new(30, 50)
    res = other.place_block(out, 1, 1)                                         # a model holding blocks is placed as ONE block (blocks do not nest)
    assert res["ok"] and len(other.blocks) == 1 and res["ports"] == ["out"]


def test_nano_authoring_and_its_operand_order():
    """Two operands arriving on one tick are OR-merged (a feature): shown as a note, never "balanced" away. Arriving in order, the nano takes A then B."""
    import flex_layout_sim_v1 as fls
    def nano(b_row):
        lay = flv.Layout.new(12, 14)
        for nm, core, r, c, io in (("A", "ram", 1, 1, "a"), ("B", "ram", b_row, 1, "b"), ("N", "nano", 4, 6, None), ("O", "ram", 4, 11, "o")):
            assert lay.add_cell(core, r, c, name=nm, io=io)["ok"]
        assert lay.grid.nodes["N"]["cfg"]["ready"] == 1                        # a nano with ready=0 never fires
        assert lay.set_config("N", cfg={"topology": 0xBC})["ok"]               # xor
        for a, b in (("A", "N"), ("B", "N"), ("N", "O")):
            assert lay.join(a, b)["ok"]
        return lay
    lay = nano(7)                                                              # symmetric: both operands arrive together
    snap = lay.snapshot()
    assert [m["cell"] for m in snap["merges"]] == ["N"] and not snap["problems"]
    assert lay.balance()["ok"] and lay.snapshot()["merges"]                    # Balance leaves a merge alone
    sim = fls.StepSim(lay)
    sim.run_items({"A": [0b1100, 0xF0], "B": [0b1010, 0x0F]})
    assert sim.view()["outputs"][0]["values"] == [(0b1100 | 0b1010) ^ (0xF0 | 0x0F)]   # item 1 merged = A, item 2 merged = B
    lay = nano(9)                                                              # B further away: A first, then B
    assert not lay.snapshot()["merges"]
    sim = fls.StepSim(lay)
    sim.run_items({"A": [0b1100, 0xF0], "B": [0b1010, 0x0F]})
    assert sim.view()["outputs"][0]["values"] == [0b0110, 0xFF]


def test_step_through():
    import flex_layout_sim_v1 as fls
    lay = flv.Layout.new(12, 20)
    build_adder(lay)
    sim = fls.StepSim(lay)
    assert sim.inputs == ["A", "B"] and sim.outputs == ["R"]
    sim.inject({"A": 1, "B": 2})
    sim.step(3)
    moving = [v for v in sim.state().values() if v["valid"]]
    assert sorted(v["v"] for v in moving) == [1, 2] and all("r" in v for v in moving)      # the two operands, on their way, with their squares
    sim.run()
    assert sim.view()["outputs"][0]["values"] == [3]
    sim.run_items({"A": [1, 5, 100], "B": [2, 7, 23]})                        # carries on from item 2: item 1 was injected by hand
    assert sim.view()["outputs"][0]["values"] == [3, 12, 123] and sim.items == 3


def test_step_through_reoffers_constants():
    import flex_layout_sim_v1 as fls
    lay = flv.Layout.new(10, 16)
    for nm, core, r, c, io in (("X", "ram", 2, 1, "x"), ("K", "ram", 7, 1, None), ("ADD", "adder", 4, 8, None), ("Y", "ram", 4, 13, "y")):
        assert lay.add_cell(core, r, c, name=nm, io=io)["ok"]
    assert lay.set_config("K", preload=5)["ok"]
    for a, b in (("X", "ADD"), ("K", "ADD"), ("ADD", "Y")):
        assert lay.join(a, b)["ok"]
    assert lay.balance()["ok"]
    sim = fls.StepSim(lay)
    assert sim.inputs == ["X"]
    sim.run_items({"X": [1, 2, 30]})
    assert sim.view()["outputs"][0]["values"] == [6, 7, 35]


def test_step_through_and_save_api(tmp_path, monkeypatch):
    import composer_page_v1 as cp
    monkeypatch.setattr(cp, "LIBRARY_DIR", str(tmp_path))
    ctl = cp.ComposerController()
    ctl.layout = flv.Layout.new(12, 20)
    build_adder(ctl.layout)
    assert not ctl.sim_op({"op": "step"})["ok"]                                # Start first
    assert ctl.sim_op({"op": "start"})["ok"]
    res = ctl.sim_op({"op": "items", "items": {"A": "1, 5, 0x64", "B": "2 7 23"}})
    assert res["ok"] and res["sim"]["outputs"][0]["values"] == [3, 12, 123]
    assert ctl.edit("move", {"name": "R", "r": 5, "c": 14})["ok"] and ctl.sim is None    # an edit ends the run
    name, text = ctl.icm_text()
    assert json.loads(text)["format_version"] == "icm-v3" and name.endswith(".icm.json")
    lay, *_ = two_adders(tmp_path)
    ctl.layout = lay
    name, text = ctl.icm_text()
    assert json.loads(text)["format_version"] == "icm-vix-v1" and name.endswith(".icm-hier.json")
    assert json.loads(ctl.icm_text("v3")[1])["format_version"] == "icm-v3"
