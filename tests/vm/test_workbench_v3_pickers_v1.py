"""Ledger #1295: Workbench v3 -- tabbed left column, drop-down file fields fed by GET /files, a Browse... picker that uploads the chosen file (POST /upload), and the card-SHAPE mirror still works."""
import json
import os
import shutil
import sys
import urllib.request

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for d in ("nano", "tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, d))
import workbench_v3 as w3  # noqa: E402
from test_workbench_card_shape_v1 import shapes, ICM  # noqa: E402,F401  (the SHAPE fixture)


@pytest.fixture
def wb(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.chdir(tmp_path)
    return w3.WorkbenchController()


def test_file_lists_find_the_repo_files(wb):
    man = wb.list_files("man")
    assert man["ok"] and {"kintex7-ypcb00338.man.json", "mustang-f100-a10.man.json", "tang-nano-20k.man.json"} <= {f["label"] for f in man["files"]}
    assert all(os.path.isabs(f["path"]) and os.path.isfile(f["path"]) for f in man["files"])
    design = wb.list_files("design")["files"]
    assert "cordic_z_convergence_v2.icm-hier.json" in {f["label"] for f in design} and any(f["label"].endswith(".icm") for f in design)
    assert wb.list_files("shape")["ok"] and not wb.list_files("nonsense")["ok"]


def test_upload_is_the_pickers_path_and_is_safe(wb, tmp_path):
    r = wb.upload_file("../../evil/card.shape.json", '{"a": 1}')
    assert r["ok"] and r["name"] == "card.shape.json" and r["path"].startswith(str(tmp_path / "cache")) and open(r["path"]).read() == '{"a": 1}'
    assert "card.shape.json  (uploaded)" in [f["label"] for f in wb.list_files("shape")["files"]]
    for bad in ("run.sh", "x.exe", "", "noext"):
        assert not wb.upload_file(bad, "x")["ok"]
    assert not wb.upload_file("big.json", "x" * (20 * 1024 * 1024 + 1))["ok"]
    assert not wb.upload_file("n.json", None)["ok"]


def test_page_has_tabs_dropdowns_and_pickers():
    h = w3.WORKBENCH_HTML
    for t in ("target", "load", "program", "run"):
        assert f'id="tab-{t}"' in h and f'showTab(\'{t}\')' in h
    assert '<select id="manPath">' in h and '<select id="shapePath">' in h and 'id="icmPick"' in h and "browseInto(" in h and 'id="fileBrowse"' in h and 'type="file"' in h
    for ident in ("targetCells", "targetShell", "icmPath", "regionList", "grid", "source", "dRow", "runRate", "diagnostics", "demoSelect"):
        assert f'id="{ident}"' in h               # every element the page's script reads is still there


def test_routes_over_http_and_shape_mirror_still_works(wb, shapes):
    server = w3.serve(port=7462, open_browser=False)
    try:
        def post(path, body):
            req = urllib.request.Request(f"http://localhost:7462{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req).read())
        files = json.loads(urllib.request.urlopen("http://localhost:7462/files?kind=man").read())
        assert files["ok"] and files["files"]
        up = post("/upload", {"name": "card.shape.json", "text": open(shapes["full"]).read()})
        assert up["ok"]
        r = post("/set_target_shape", {"shape_path": up["path"]})
        assert r["ok"] and r["target"]["confirmed_by_card"] == 39
        v = post("/load_icm_vix", {"path": ICM})
        assert v["ok"] and v["card_check"]["same_design"]
    finally:
        server.shutdown()
