"""tests/tools/test_frontend_create_project.py -- points.md #600: real
tests for the frontend's Step 2 (/cells) controller, covering the shell/
LogicLock/custom-shell-file/dependency-override options that were newly
wired through from tools/project_assemble_v1.py's own real assemble().
Uses the real, existing MAN file and real fpga/verilog sources -- no
mocking of the actual build pipeline, matching this project's own
sim-first/real-verification discipline applied to tooling."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import frontend_v1  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_MAN = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")


def test_create_project_default_shell_v3(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "proj"
    result = controller.create_project({"man_path": REAL_MAN, "cells": "1", "output": str(out)})
    assert result["ok"], result.get("error")
    assert result["shell"] == "v3"
    assert "--shell" not in result["cli_equivalent"]  # v3 is the default, omitted for a clean CLI line


def test_create_project_explicit_shell_v4(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "proj"
    result = controller.create_project({"man_path": REAL_MAN, "cells": "1", "output": str(out), "shell": "v4"})
    assert result["ok"], result.get("error")
    assert result["shell"] == "v4"
    assert "--shell v4" in result["cli_equivalent"]


def test_create_project_logiclock_checkbox_present_means_on(tmp_path):
    """Real HTML checkbox semantics: presence (any truthy value, e.g.
    'on') means checked; the key's absence means unchecked."""
    controller = frontend_v1.FrontendController()
    out = tmp_path / "proj"
    result = controller.create_project({"man_path": REAL_MAN, "cells": "1", "output": str(out), "logiclock": "on"})
    assert result["ok"], result.get("error")
    assert result["logiclock"] is True
    assert "--logiclock" in result["cli_equivalent"]


def test_create_project_logiclock_absent_means_off(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "proj"
    result = controller.create_project({"man_path": REAL_MAN, "cells": "1", "output": str(out)})
    assert result["ok"], result.get("error")
    assert result["logiclock"] is False
    assert "--logiclock" not in result["cli_equivalent"]


def test_create_project_ll_fixed_alm_and_headroom_passed_through(tmp_path):
    controller = frontend_v1.FrontendController()
    out = tmp_path / "proj"
    result = controller.create_project({
        "man_path": REAL_MAN, "cells": "1", "output": str(out),
        "logiclock": "on", "ll_fixed_alm": "1030.52", "ll_headroom": "1.3",
    })
    assert result["ok"], result.get("error")
    assert "--ll-fixed-alm 1030.52" in result["cli_equivalent"]
    assert "--ll-headroom 1.3" in result["cli_equivalent"]


def test_create_project_shell_file_without_module_errors_cleanly():
    """Real, direct mirror of the CLI's own main()-level check (#590)
    -- assemble() itself doesn't enforce this, so the frontend must,
    or a confusing downstream error/mismatch would result instead."""
    controller = frontend_v1.FrontendController()
    result = controller.create_project({
        "man_path": REAL_MAN, "cells": "1", "output": "/tmp/unused",
        "shell_file": "fpga/verilog/unicell_super_v7.v",
    })
    assert not result["ok"]
    assert "shell-module" in result["error"]


def test_create_project_custom_shell_file_end_to_end(tmp_path):
    """Real, end-to-end test with an actual custom shell file
    (unicell_super_v7.v, a real, existing file in this repo) --
    confirms the whole chain (validation, assemble() call, dependency
    resolution, compat check) wires through from the frontend."""
    controller = frontend_v1.FrontendController()
    out = tmp_path / "proj"
    shell_file = os.path.join(REPO_ROOT, "fpga", "verilog", "unicell_super_v7.v")
    result = controller.create_project({
        "man_path": REAL_MAN, "cells": "1", "output": str(out),
        "shell_file": shell_file, "shell_module": "unicell_super_v7",
    })
    assert result["ok"], result.get("error")
    assert "compat_warnings" in result
    assert f"--shell-file {shell_file} --shell-module unicell_super_v7" in result["cli_equivalent"]


def test_create_project_missing_output_still_required(tmp_path):
    controller = frontend_v1.FrontendController()
    result = controller.create_project({"man_path": REAL_MAN, "cells": "1"})
    assert not result["ok"]
    assert "output" in result["error"]


def test_page_cells_renders_new_fields():
    html = frontend_v1.page_cells()
    assert 'name="shell"' in html
    assert 'name="logiclock"' in html
    assert 'name="ll_fixed_alm"' in html
    assert 'name="ll_headroom"' in html
    assert 'name="shell_file"' in html
    assert 'name="shell_module"' in html
    assert 'name="file_list"' in html
    assert 'name="files"' in html
    assert "What's actually needed, and why" in html


def test_page_cells_renders_compat_warnings():
    result = {
        "ok": True, "files_written": 5, "output": "/tmp/x", "rows": 1, "cols": 1,
        "alm_total": 251680, "cli_equivalent": "python3 tools/project_assemble_v1.py ...",
        "shell": "v7", "logiclock": False, "compat_warnings": ["real, advisory warning text"],
    }
    html = frontend_v1.page_cells(result)
    assert "real, advisory warning text" in html
    assert "Compatibility warnings" in html
