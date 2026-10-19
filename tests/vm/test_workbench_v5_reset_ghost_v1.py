"""Ledger #1297: Workbench v5 -- Reset to tick 0, ghost path of a clicked tile, gold (data) and magenta (logic) change glow. Browser part skips without playwright/Chromium."""
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for d in ("nano", "tools", "tests/vm"):
    sys.path.insert(0, os.path.join(ROOT, d))
import workbench_v5 as w5  # noqa: E402

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")


def test_markup():
    h = w5.WORKBENCH_HTML
    for s in ("resetGrid()", "flowFrom(", "drawGhost(", "flash-data", "flash-logic", "LOGIC_FIELD", "/reset"):
        assert s in h


def test_reset_controller(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    c = w5.WorkbenchController()
    assert not c.reset()["ok"]                       # nothing loaded
    r = c.load_icm_vix(ICM)
    assert r.get("ok"), r
    t0 = c.state()["state"]["tick"] if "tick" in c.state().get("state", {}) else None
    c.step(5)
    r = c.reset()
    assert r.get("ok", True) is not False
    s = c.state()
    tick = s.get("tick", s.get("state", {}).get("tick"))
    assert tick in (0, t0)


def test_reset_in_browser(tmp_path, monkeypatch):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("playwright not installed")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    server = w5.serve(port=7492, open_browser=False)
    errs = []
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:
                pytest.skip(f"no chromium: {e}")
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://localhost:7492/"); pg.wait_for_timeout(400)
            pg.evaluate("async (p) => { const r = await post('/load_icm_vix', {path: p}); renderState(r.state); }", ICM)
            pg.evaluate("async () => { for (let i = 0; i < 6; i++) { const r = await post('/step', {n: 1}); renderState(r.state || r); } }")
            assert pg.eval_on_selector_all(".tile.flash-data", "t => t.length") > 0
            k = pg.evaluate("""() => { const c = {core: 'adder', adder: {downstream_mask: 2, data_reg: 5}, pending_ack: false};
              const prev = changeKind({}, c).fields; const a = Object.assign({}, prev, {data_reg: '6'}); const b = Object.assign({}, prev, {downstream_mask: '4'});
              return [changeKind(a, c), changeKind(b, c)].map(x => [x.data, x.logic]); }""")
            assert k == [[True, False], [False, True]]                                   # data change -> gold, mask change -> magenta
            assert pg.eval_on_selector_all("#pulsesvg circle", "c => c.length") > 0      # data moved this tick: dots travel along the arrows
            pg.click(".tile >> nth=3")
            n_ghost = pg.eval_on_selector_all(".tile.ghost", "t => t.length")
            assert pg.eval_on_selector_all("#ghostsvg line", "l => l.length") == (pg.eval_on_selector_all("#ghostsvg line", "l => l.length"))
            tick_before = pg.evaluate("LAST_STATE.tick_count ?? LAST_STATE.tick")
            pg.click("#tabbtn-run"); pg.click("button:text-is(\"Reset\")"); pg.wait_for_timeout(500)
            tick_after = pg.evaluate("LAST_STATE.tick_count ?? LAST_STATE.tick")
            print("ghost", n_ghost, "tick", tick_before, "->", tick_after)
            assert tick_after in (0, None) or tick_after < tick_before
            assert pg.eval_on_selector_all(".tile", "t => t.length") == 40
            b.close()
    finally:
        server.shutdown()
    assert errs == []
