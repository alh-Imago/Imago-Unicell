"""Ledger #1299: Workbench v6 -- steady glow for cells holding a value; under a card SHAPE target, card-only cells (merge cores the generator adds) and absorbed design cells are shown. Uses the SHAPE made from the
simulated card read-back (needs iverilog); the browser part skips without playwright/Chromium."""
import os
import shutil
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for d in ("nano", "tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, d))
import workbench_v6 as w6  # noqa: E402
from test_workbench_card_shape_v1 import shapes  # noqa: E402,F401

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog missing")


def test_overlay_in_state(shapes, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    c = w6.WorkbenchController()
    assert c.set_target_shape(shapes["full"])["ok"]
    assert c.state()["state"].get("card") is None                      # no design loaded yet: nothing to compare
    assert c.load_icm_vix(ICM)["ok"]
    card = c.state()["state"]["card"]
    assert len(card["absorbed"]) == 4 and len(card["card_only"]) == 4  # 40 design cells, 36 + 4 generator merge cores on the card
    flagged = [x for x in c.state()["state"]["cells"].values() if x["absorbed"]]
    assert len(flagged) == 4
    c.clear_target()
    assert c.state().get("state", {}).get("card") is None              # back to free mode: no overlay


def test_overlay_in_browser(shapes, tmp_path, monkeypatch):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("playwright not installed")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    server = w6.serve(port=7495, open_browser=False)
    errs = []
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:
                pytest.skip(f"no chromium: {e}")
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://localhost:7495/"); pg.wait_for_timeout(400)
            assert pg.evaluate("async (s) => { const r = await post('/set_target_shape', {shape_path: s}); TARGET_KIND = 'card_shape'; return r.ok; }", shapes["full"])
            pg.evaluate("async (p) => { const r = await post('/load_icm_vix', {path: p}); const s = await get('/state'); renderState(s.state); }", ICM)
            assert pg.eval_on_selector_all(".tile.absorbed", "t => t.length") == 4
            placeholders = pg.eval_on_selector_all(".tile.cardonly", "t => t.length")
            badges = pg.eval_on_selector_all(".tile .badge", "t => t.length")
            print("card-only placeholders", placeholders, "badges", badges)
            assert placeholders + badges >= 1                                            # the 4 card-only cells show either as a placeholder tile or a badge on a shared site
            n0 = pg.eval_on_selector_all(".tile.has", "t => t.length")
            assert n0 == pg.evaluate("Object.values(LAST_STATE.cells).filter(hasValue).length")   # the glow is exactly the cells with a valid flag set (some designs preload values)
            pg.evaluate("async () => { for (let i = 0; i < 6; i++) { const r = await post('/step', {n: 1}); renderState(r.state || r); } }")
            n1 = pg.eval_on_selector_all(".tile.has", "t => t.length")
            assert n1 > 0 and n1 == pg.evaluate("Object.values(LAST_STATE.cells).filter(hasValue).length")
            print("holding a value: before", n0, "after 6 steps", n1)
            assert pg.eval_on_selector_all(".tile:not(.cardonly)", "t => t.length") == 40
            b.close()
    finally:
        server.shutdown()
    assert errs == []
