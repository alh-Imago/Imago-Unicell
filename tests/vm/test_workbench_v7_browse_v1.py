"""Ledger #1300: Workbench v7 -- Browse... on the Load tab keeps the picked file in the drop-down (even when its name is one the lists do not match) and loads it at once."""
import os
import shutil
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for d in ("nano", "tools"):
    sys.path.insert(0, os.path.join(ROOT, d))
import workbench_v7 as w7  # noqa: E402

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")


def test_browse_loads_and_keeps_selection(tmp_path, monkeypatch):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pytest.skip("playwright not installed")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "c"))
    odd = tmp_path / "k7_icm_cordic_copy.json"            # not *.icm-hier.json, so the drop-down list does not know this name
    shutil.copy(ICM, odd)
    server = w7.serve(port=7498, open_browser=False)
    errs = []
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:
                pytest.skip(f"no chromium: {e}")
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://localhost:7498/"); pg.wait_for_timeout(500)
            pg.click("#tabbtn-load")
            with pg.expect_file_chooser() as fc:
                pg.click("#tab-load button:text-is('Browse…')")
            fc.value.set_files(str(odd))
            pg.wait_for_timeout(1500)
            assert pg.eval_on_selector("#icmPick", "s => s.options[s.selectedIndex].textContent").startswith("k7_icm_cordic_copy.json")   # the drop-down shows the picked file
            assert pg.input_value("#icmPath").endswith("k7_icm_cordic_copy.json")
            assert pg.eval_on_selector_all(".tile", "t => t.length") == 40                                                                  # and it was loaded
            b.close()
    finally:
        server.shutdown()
    assert errs == []
