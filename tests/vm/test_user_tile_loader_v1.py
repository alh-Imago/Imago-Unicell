"""
test_user_tile_loader_v1.py — verifies the "use this model" CLI feature
(`points.md #345`): loading a user-authored composed-tile JSON file,
registering it with correct shadow-a-built-in precedence, and the real
end-to-end `dsl_cli_v1.py` CLI itself (invoked as a real subprocess,
not just its Python functions called in-process -- the point of a CLI
test is confirming the actual command someone would type works).
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from user_tile_loader_v1 import load_composed_tile  # noqa: E402
from composed_tile_library_v1 import ComposedTileSpec, composed_tile_library, ComposedTileLibrary, place_composed  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402

NANO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "nano")
CLI_PATH = os.path.join(NANO_DIR, "dsl_cli_v1.py")


def _write(tmp_path, name, content):
    path = os.path.join(tmp_path, name)
    with open(path, "w") as f:
        f.write(content)
    return path


# ── Loader ───────────────────────────────────────────────────────────

def test_load_composed_tile_produces_a_real_spec(tmp_path):
    path = _write(str(tmp_path), "my_pair.json", json.dumps({
        "name": "my_pair", "description": "adder into comparator",
        "subcells": [
            {"name": "add", "offset": [0, 0], "tile_name": "adder", "internal_directions": {"out": "e"}},
            {"name": "cmp", "offset": [0, 1], "tile_name": "comparator", "internal_directions": {"in": "w"}},
        ],
        "external_ports": {"in_a": ["add", "in_a"], "in_b": ["add", "in_b"], "out": ["cmp", "out"]},
    }))
    tile = load_composed_tile(path)
    assert isinstance(tile, ComposedTileSpec)
    assert tile.name == "my_pair"
    assert tile.port_names() == ["in_a", "in_b", "out"]

    # and it actually works when placed -- not just structurally parsed
    records = place_composed(tile, 0, 0, {"in_a": "n", "in_b": "w", "out": "e"},
                              {"cmp.threshold": 5},
                              composed_library=ComposedTileLibrary(parent=composed_tile_library))
    assert len(records) == 2
    assert {r.core for r in records} == {"adder", "comparator"}


def test_load_composed_tile_missing_file():
    try:
        load_composed_tile("/tmp/definitely_does_not_exist_12345.json")
    except ValueError as e:
        assert "not found" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_load_composed_tile_malformed_json(tmp_path):
    path = _write(str(tmp_path), "bad.json", "{not valid json")
    try:
        load_composed_tile(path)
    except ValueError as e:
        assert "not valid JSON" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_load_composed_tile_missing_required_key(tmp_path):
    path = _write(str(tmp_path), "incomplete.json", json.dumps({"name": "x"}))
    try:
        load_composed_tile(path)
    except ValueError as e:
        assert "missing required key" in str(e)
    else:
        raise AssertionError("expected ValueError")


# ── Precedence: user model shadows a same-named built-in ──────────────

def test_user_model_shadows_same_named_builtin_via_compile_source(tmp_path):
    path = _write(str(tmp_path), "shadow.json", json.dumps({
        "name": "sentinel", "description": "user override, adder-based not accumulator-based",
        "subcells": [
            {"name": "add", "offset": [0, 0], "tile_name": "adder", "internal_directions": {"out": "e"}},
            {"name": "cmp", "offset": [0, 1], "tile_name": "comparator", "internal_directions": {"in": "w"}},
        ],
        "external_ports": {"in_a": ["add", "in_a"], "in_b": ["add", "in_b"], "out": ["cmp", "out"]},
    }))
    tile = load_composed_tile(path)
    user_lib = ComposedTileLibrary(parent=composed_tile_library)
    user_lib.register(tile)

    src = """
    program shadow_test {
        place p as sentinel at (0, 0) {
            in_a: n
            in_b: w
            out: e
            cmp.threshold: 5
        }
    }
    """
    icm, diags = compile_source(src, composed_library=user_lib)
    assert diags == []
    assert {r.core for r in icm.records} == {"adder", "comparator"}   # the USER's sentinel, not the built-in


def test_unshadowed_names_still_fall_through_to_builtin_library(tmp_path):
    # register an unrelated user tile -- the built-in 'sentinel' must
    # still resolve correctly via the parent-chain fallback
    path = _write(str(tmp_path), "other.json", json.dumps({
        "name": "totally_different_tile",
        "subcells": [{"name": "a", "offset": [0, 0], "tile_name": "ram_constant",
                       "internal_directions": {}}],
        "external_ports": {"out": ["a", "out"]},
    }))
    tile = load_composed_tile(path)
    user_lib = ComposedTileLibrary(parent=composed_tile_library)
    user_lib.register(tile)

    src = """
    program uses_builtin {
        place s as sentinel at (0, 0) {
            inc: n
            dec: s
            clear: s
            out: e
            cmp.threshold: 8
        }
    }
    """
    icm, diags = compile_source(src, composed_library=user_lib)
    assert diags == []
    assert {r.core for r in icm.records} == {"accumulator", "comparator", "latch"}   # the real built-in


# ── The real CLI, invoked as an actual subprocess ──────────────────────

def test_cli_compiles_a_program_using_a_user_model(tmp_path):
    tmp = str(tmp_path)
    model_path = _write(tmp, "my_pair.json", json.dumps({
        "name": "my_pair",
        "subcells": [
            {"name": "add", "offset": [0, 0], "tile_name": "adder", "internal_directions": {"out": "e"}},
            {"name": "cmp", "offset": [0, 1], "tile_name": "comparator", "internal_directions": {"in": "w"}},
        ],
        "external_ports": {"in_a": ["add", "in_a"], "in_b": ["add", "in_b"], "out": ["cmp", "out"]},
    }))
    source_path = _write(tmp, "prog.uc", """
    program uses_my_pair {
        place p as my_pair at (0, 0) {
            in_a: n
            in_b: w
            out: e
            cmp.threshold: 10
        }
    }
    """)
    output_path = os.path.join(tmp, "out.icm")

    result = subprocess.run(
        [sys.executable, CLI_PATH, source_path, "--model", model_path, "-o", output_path],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "loaded user model 'my_pair'" in result.stderr
    assert os.path.exists(output_path)
    with open(output_path) as f:
        data = json.load(f)
    assert {r["core"] for r in data["records"]} == {"adder", "comparator"}


def test_cli_reports_missing_model_file_with_nonzero_exit(tmp_path):
    tmp = str(tmp_path)
    source_path = _write(tmp, "prog.uc", "program x { place r as ram_constant at (0,0) { out: e\n init_data: 1 } }")
    result = subprocess.run(
        [sys.executable, CLI_PATH, source_path, "--model", "/tmp/nope_12345.json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "not found" in result.stderr


def test_cli_reports_compile_errors_with_nonzero_exit_and_no_output_file(tmp_path):
    tmp = str(tmp_path)
    source_path = _write(tmp, "broken.uc", """
    program broken {
        place r as ram_constant at (0, 0) {
            init_data: 1
        }
    }
    """)
    output_path = os.path.join(tmp, "should_not_exist.icm")
    result = subprocess.run(
        [sys.executable, CLI_PATH, source_path, "-o", output_path],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "compile failed" in result.stderr
    assert not os.path.exists(output_path)


def test_cli_without_model_flag_uses_the_real_builtin_sentinel(tmp_path):
    tmp = str(tmp_path)
    source_path = _write(tmp, "prog.uc", """
    program my_sentinel {
        place s as sentinel at (0, 0) {
            inc: n
            dec: s
            clear: s
            out: e
            cmp.threshold: 8
        }
    }
    """)
    output_path = os.path.join(tmp, "out.icm")
    result = subprocess.run(
        [sys.executable, CLI_PATH, source_path, "-o", output_path],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    with open(output_path) as f:
        data = json.load(f)
    assert {r["core"] for r in data["records"]} == {"accumulator", "comparator", "latch"}


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
