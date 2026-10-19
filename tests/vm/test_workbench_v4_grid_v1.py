"""Ledger #1296: Workbench v4 grid -- small tiles, background = family, inner colour = core, brighten on change, edge arrows for flow, details only for the clicked cell. Browser checks run in
Chromium through playwright and are skipped where it is not installed."""
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for d in ("nano", "tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, d))
import workbench_v4 as w4  # noqa: E402
from test_workbench_card_shape_v1 import shapes  # noqa: E402,F401

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")


def test_page_markup_and_palette():
    h = w4.WORKBENCH_HTML
    assert 'id="gridLegend"' in h and 'id="cellDetail"' in h and "function showDetail(" in h and "flashit" in h and "ARROW_OUT" in h
    for fam in ("std", "carrier", "flex", "sub", "bridge"):
        assert f'"{fam}":' in h
    assert '"adder": "#c17f45"' in h and '"branch": "#b48ad0"' in h          # the Composer's core palette
    assert "state.cells[key].col" not in h                                    # the old grid placement (broke with negative rows/cols) is gone


def _browser():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("playwright not installed")
    return sync_playwright


def test_grid_in_a_real_browser(shapes, tmp_path, monkeypatch):
    sync_playwright = _browser()
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    server = w4.serve(port=7491, open_browser=False)
    errs = []
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:
                pytest.skip(f"no chromium: {e}")
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://localhost:7491/"); pg.wait_for_timeout(400)
            pg.evaluate("async (p) => { const r = await post('/load_icm_vix', {path: p}); renderState(r.state); }", ICM)
            assert pg.eval_on_selector_all(".tile", "t => t.length") == 40
            assert pg.eval_on_selector_all(".tile", "t => t.every(x => parseInt(x.style.gridRow) >= 1 && parseInt(x.style.gridColumn) >= 1)")      # negative ICM coordinates are shifted
            assert "Click a cell" in pg.inner_text("#cellDetail")                       # details are not shown until a cell is chosen
            assert pg.eval_on_selector_all(".tile .ar.out", "a => a.length") > 0 and pg.eval_on_selector_all(".tile .ar.in", "a => a.length") > 0
            fams = pg.eval_on_selector_all(".tile", "t => [...new Set(t.map(x => x.title.split(' ').pop()))]")
            assert fams == ["Std"]                                                      # no family named and no card target: the VM's standard cells
            assert pg.eval_on_selector_all(".tile.flash", "t => t.length") == 0
            pg.evaluate("async () => { for (let i = 0; i < 6; i++) { const r = await post('/step', {n: 1}); renderState(r.state || r); } }")
            assert pg.eval_on_selector_all(".tile.flash", "t => t.length") > 0          # cells whose state changed are brightened
            pg.click(".tile >> nth=3")
            assert pg.eval_on_selector_all(".tile.sel", "t => t.length") == 1 and "downstream_mask" in pg.inner_text("#cellDetail")
            pg.click(".tile.sel")                                                         # a second click closes the details
            assert "Click a cell" in pg.inner_text("#cellDetail")
            # a card SHAPE target: tiles take the Flex family colour
            pg.fill("#shapePath", "") if False else None
            r = pg.evaluate("async (s) => { const r = await post('/set_target_shape', {shape_path: s}); if (r.ok) { TARGET_KIND = 'card_shape'; } return r.ok; }", shapes["full"])
            assert r
            pg.evaluate("async (p) => { const r = await post('/load_icm_vix', {path: p}); renderState(r.state); }", ICM)
            assert pg.eval_on_selector_all(".tile", "t => [...new Set(t.map(x => x.title.split(' ').pop()))]") == ["Flex"]
            b.close()
    finally:
        server.shutdown()
    assert errs == []
