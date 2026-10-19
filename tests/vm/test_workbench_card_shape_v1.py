"""Ledger #1294: the Workbench mirror takes the CARD'S OWN SHAPE (card.shape.json from the Walker) as its target; a hierarchical design loaded into it is checked against the cells and connections the card
has and has shown. Uses a SHAPE made from the simulated card read-back (the same bytes the card returns)."""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for d in ("nano", "tools"):
    sys.path.insert(0, os.path.join(ROOT, d))
import kintex_icm_runner_v6 as kr  # noqa: E402
import walker_card_v2 as wk  # noqa: E402
import vm_mirror_v2  # noqa: E402
from workbench_v2 import WorkbenchController  # noqa: E402

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")
OTHER = os.path.join(ROOT, "nano", "examples", "reduction_tree4_exit_v1.icm-hier.json")
KMAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog missing")


def snap_from_sim(out, d, sets):
    entries = [(e["name"], e["width"]) for e in d["entries"]]; exits = [(e["name"], e["width"]) for e in d["exits"]]
    lay = d["layout"]
    tb = kr.TB.replace("PROJECT", d["proj"]).replace("NWV", str(lay["nw"])).replace("NEV", str(len(entries))).replace("NXV", str(len(exits))).replace("DEPTHV", str(kr.DEPTH)).replace("MAGIC", str(kr.MAGIC))
    tb = tb.replace("RUNS", kr.tb_runs(entries, exits, lay, sets, int(d["fingerprint"], 16)))
    open(os.path.join(out, "tb_x.v"), "w").write(tb)
    svs = [f for f in os.listdir(out) if f.endswith(".sv")]
    assert subprocess.run(["iverilog", "-g2012", "-o", os.path.join(out, "x.vvp"), os.path.join(out, "tb_x.v"), os.path.join(out, d["proj"] + ".v")] + [os.path.join(out, f) for f in svs]).returncode == 0
    t = subprocess.run(["vvp", os.path.join(out, "x.vvp")], capture_output=True, text=True).stdout
    logs = []
    for k in range(len(sets)):
        h = re.search(r"SNAPALL %d ([0-9a-f]+)" % k, t).group(1)
        ws = [h[i:i + 8] for i in range(0, len(h), 8)][::-1]
        p = os.path.join(out, "x%d.log" % k); open(p, "w").write("SNAP result " + " ".join(ws) + "\n"); logs.append(p)
    return logs


@pytest.fixture(scope="module")
def shapes(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("w") / "o")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v6.py"), "-s", "flex", "--icm", ICM, "--man", KMAN, "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.load(open(os.path.join(out, "design.json")))
    exp = json.load(open(os.path.join(out, "expected.json")))
    entries = [(e["name"], e["width"]) for e in d["entries"]]; exits = [(e["name"], e["width"]) for e in d["exits"]]
    res = {}
    for key, vec, name in (("full", kr.wide_vectors(entries), "vectors_wide.txt"), ("partial", kr.default_vectors(entries, 0), "vectors.txt")):
        e = {n: exp[name]["exits"][n]["words"] for n, _ in exits}
        log = snap_from_sim(out, d, [(vec, e)])[0]
        sp = os.path.join(out, key + ".shape.json")
        assert wk.main([out, log, "--shape", sp]) == 0
        res[key] = sp
    return res


def test_card_shape_becomes_the_mirror_target_and_the_design_fits(shapes):
    wb = WorkbenchController()
    r = wb.set_target_shape(shapes["full"])
    assert r["ok"] and r["target"]["kind"] == "card_shape" and r["target"]["cells"] == 40 and r["target"]["connections"] == 39 and r["target"]["confirmed_by_card"] == 39 and r["target"]["complete"]
    assert wb.current_target()["target"]["kind"] == "card_shape"
    v = wb.load_icm_vix(ICM)
    assert v["ok"], v
    cc = v["card_check"]
    assert cc["checked"] and cc["same_design"] and not cc["cells_not_on_card"] and not cc["edges_not_on_card"] and not cc["edges_not_shown"]
    assert wb.session.mirror_bounds.kind == "card_shape"                 # the session stays bound to the card
    assert v["state"]["cell_count"] == 40                                # the VM runs all 40 of the design's own cells (36 become card cells, 4 are absorbed)
    assert cc["absorbed_in_build"] == ["s0.merge", "s1.merge", "s2.merge", "s3.merge"]      # the four entry merges the generator folded into their branches: the card has no separate cell


def test_partial_shape_loads_but_says_what_the_card_has_not_shown(shapes):
    wb = WorkbenchController()
    assert wb.set_target_shape(shapes["partial"])["ok"]
    v = wb.load_icm_vix(ICM)
    assert v["ok"] and v["card_check"]["same_design"] and len(v["card_check"]["edges_not_shown"]) == 16 and not v["card_check"]["edges_not_on_card"]


def test_a_design_the_card_does_not_have_is_refused_and_flat_programs_are_not_silently_checked(shapes):
    wb = WorkbenchController()
    assert wb.set_target_shape(shapes["full"])["ok"]
    v = wb.load_icm_vix(OTHER)
    assert not v["ok"] and "does not fit the card" in v["error"]
    assert wb.session.mirror_bounds.kind == "card_shape" and wb.session.describe()["cell_count"] == 0         # nothing was loaded
    c = wb.compile("x = 1", "python")
    assert not c["ok"] and "card SHAPE" in c["error"]
    bad = wb.set_target_shape(os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json"))
    assert not bad["ok"] and "not a usable card SHAPE" in bad["error"]


def test_man_target_still_works_as_before():
    wb = WorkbenchController()
    r = wb.set_target(os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json"), 4)
    assert r["ok"] and wb.current_target()["target"]["kind"] == "man"


def test_over_http_the_page_routes_work(shapes):
    import urllib.request
    import workbench_v2 as w2
    server = w2.serve(port=7461, open_browser=False)
    try:
        def post(path, body):
            req = urllib.request.Request(f"http://localhost:7461{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req).read())
        page = urllib.request.urlopen("http://localhost:7461/").read().decode()
        assert "setTargetShape()" in page and "loadIcmVix()" in page
        r = post("/set_target_shape", {"shape_path": shapes["full"]})
        assert r["ok"] and r["target"]["confirmed_by_card"] == 39
        v = post("/load_icm_vix", {"path": ICM})
        assert v["ok"] and v["card_check"]["same_design"]
        t = json.loads(urllib.request.urlopen("http://localhost:7461/target").read())
        assert t["target"]["kind"] == "card_shape"
    finally:
        server.shutdown()
