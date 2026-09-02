"""tests/tools/test_frontend_walker.py -- points.md #602: real tests
for the frontend's Step 3 (/walker) controller, now a real, working
feature (no longer a placeholder). No mocking of the underlying
mirrored-VM/discovery chain."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import frontend_v1  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_MAN = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")

GRID4_DSL = """
program grid4 {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 1
    }
    place r2 as ram_flowing at (0, 1) {
        in: w
        out: s
    }
    place r3 as ram_flowing at (1, 1) {
        in: n
        out: w
    }
    place r4 as ram_flowing at (1, 0) {
        in: e
        out: n
    }
}
"""


def test_run_walker_end_to_end(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "shape.json"
    result = controller.run_walker({
        "man_path": REAL_MAN, "cells": "4", "dsl": GRID4_DSL, "output": str(out),
    })
    assert result["ok"], result.get("error")
    assert result["cells_discovered"] == 4
    assert result["edges_discovered"] == 4
    assert result["ping_count"] > 0
    assert out.exists()
    import json
    shape = json.loads(out.read_text())
    assert shape["discovery_method"] == "simulated_walker_ping_protocol"


def test_run_walker_missing_field_errors():
    controller = frontend_v1.FrontendController()
    result = controller.run_walker({"man_path": REAL_MAN, "cells": "4"})
    assert not result["ok"]
    assert "dsl" in result["error"]
    assert "output" in result["error"]


def test_run_walker_bad_start_origin_errors_cleanly(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "shape.json"
    result = controller.run_walker({
        "man_path": REAL_MAN, "cells": "4", "dsl": GRID4_DSL, "output": str(out),
        "start_row": "9", "start_col": "9",
    })
    assert not result["ok"]
    assert "(9,9)" in result["error"]
    assert not out.exists()


def test_run_walker_compile_failure_returns_error_not_exception(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "shape.json"
    result = controller.run_walker({
        "man_path": REAL_MAN, "cells": "4", "dsl": "not valid dsl at all {{{", "output": str(out),
    })
    assert not result["ok"]
    assert result["error"]


def test_page_walker_renders_real_form_not_placeholder_language():
    html = frontend_v1.page_walker()
    assert 'name="dsl"' in html
    assert 'name="man_path"' in html
    assert "Run simulated Walker" in html
    assert "Not built yet" not in html


def test_page_walker_renders_result():
    result = {
        "ok": True, "card_id": "mustang-f100-a10-01", "cells_discovered": 4,
        "edges_discovered": 4, "ping_count": 17, "output": "/tmp/x.shape.json",
        "cli_equivalent": "python3 tools/walker_sim_cli_v1.py ...",
    }
    html = frontend_v1.page_walker(result)
    assert "Cells discovered: 4" in html
    assert "real pings taken: 17" in html
