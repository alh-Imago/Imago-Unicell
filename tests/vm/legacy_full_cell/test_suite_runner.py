"""
test_suite_runner.py — pytest wrapper for script-style VM tests.

Many VM tests use a check()/PASS/FAIL pattern rather than pytest assertions.
This runner executes each script in its own namespace and asserts that
zero checks failed. This means `pytest` picks them all up automatically.

Adding a new script test: just add it to SCRIPT_TESTS below.
"""
import sys, os, importlib.util, types, pytest

# Ensure repo root is importable
_repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo not in sys.path:
    sys.path.insert(0, _repo)

# All script-style test files to wrap.
# Format: (pytest_id, filename_relative_to_tests/vm/)
SCRIPT_TESTS = [
    ("fp_tiles",            "test_fp_tiles.py"),
    ("branch",              "test_branch.py"),
    ("compiler_v2",         "test_compiler_v2.py"),
    ("controller",          "test_controller.py"),
    ("compiler_tile_lib",   "test_compiler_tile_library.py"),
    ("compiler_int32",      "test_compiler_int32.py"),
    ("cla",                 "test_cla.py"),
    # archived — UniCell.tick() removed in v2.2:
    # ("freeze",              "test_freeze.py"),
    ("new_tiles",           "test_new_tiles.py"),
    ("counter_tiles",       "test_counter_tiles.py"),
    ("pond",                "test_pond.py"),
    ("pond_ptt",            "test_pond_ptt.py"),
    ("pond_connect",        "test_pond_connect.py"),
    ("pond_bootstrap",      "test_pond_bootstrap.py"),
    ("pond_region_scope",   "test_pond_region_scope.py"),
    ("conditional_pond",    "test_conditional_pond.py"),
    ("workspace_pond",      "test_workspace_pond.py"),
    ("standalone_preload",  "test_standalone_preload.py"),  # Case 1+2: no Python sim
    ("ward",                "test_ward.py"),
    ("shore",               "test_shore.py"),
    ("shorekeeper",         "test_shorekeeper.py"),
    ("ptt_sentry",          "test_ptt_sentry.py"),
    ("program_builder",     "test_program_builder.py"),
    ("program_image",       "test_program_image.py"),
    ("tile_library",        "test_tile_library.py"),
    # archived — internal _stored_value removed:
    # ("migration",           "test_migration.py"),
    ("for_loop",            "test_for_loop.py"),
    # archived — UniCell.tick() removed in v2.2:
    # ("while_loop",          "test_while.py"),
    # archived — output_address_alt retired in v2:
    # ("select",              "test_select.py"),
    # archived — uses retired v1 handshake protocol (PondBridge scope constants):
    # ("handshake",           "test_handshake.py"),
    ("gpu_array",           "test_gpu_array.py"),
    ("display_pond",        "test_display_pond.py"),
    ("fs_search",           "test_fs_search.py"),
    ("flowtrix",            "test_flowtrix.py"),
    ("flowtrix_collide",    "test_flowtrix_collide.py"),
    ("flowtrix_cylinder",   "test_flowtrix_cylinder.py"),
    ("neurotrix_lif",       "test_neurotrix_lif.py"),
    ("neurotrix_lif_mif",   "test_neurotrix_lif_mif.py"),
    ("miditrix",            "test_miditrix.py"),
    ("mif_mux",             "test_mif_mux.py"),
    ("mif_recip",           "test_mif_recip.py"),
    ("mif_rsqrt",           "test_mif_rsqrt.py"),
    ("walker",              "test_walker.py"),
    ("community_raw",       "test_community_raw.py"),
    # archived — MultiDimmController.write_config() retired in v2.2:
    # ("multi_dimm",          "test_multi_dimm.py"),
    # archived — internal _stored_value removed:
    # ("vm_image",            "test_vm_image.py"),
    # archived — tests v1 gate_state bit positions, all changed in v2:
    # ("gate_state_32",       "test_gate_state_32.py"),
]

_tests_vm_dir = os.path.dirname(os.path.abspath(__file__))


def _run_script(filename):
    """
    Execute a script-style test file in a fresh namespace.
    Returns (passed, failed, total) counts extracted from output,
    or raises AssertionError if the script exits with non-zero failures.
    """
    path = os.path.join(_tests_vm_dir, filename)
    if not os.path.exists(path):
        pytest.skip(f"Test file not found: {filename}")

    # Execute in fresh namespace with repo root imports available
    ns = {"__file__": path, "__name__": "__main__",
          "__builtins__": __builtins__}
    import builtins as _bi
    # Temporarily make __file__ resolve correctly for tests that call
    # os.path.dirname(__file__) to add their directory to sys.path
    test_dir = os.path.dirname(path)
    if test_dir not in sys.path:
        sys.path.insert(0, test_dir)
        _added_test_dir = True
    else:
        _added_test_dir = False
    import io, contextlib
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            with open(path) as f:
                exec(compile(f.read(), path, 'exec'), ns)
    except SystemExit as e:
        if _added_test_dir and test_dir in sys.path:
            sys.path.remove(test_dir)
        if e.code and e.code != 0:
            output = out.getvalue()
            raise AssertionError(
                f"{filename} exited with code {e.code}\n{output[-2000:]}"
            )
    except Exception as e:
        output = out.getvalue()
        raise AssertionError(
            f"{filename} raised {type(e).__name__}: {e}\n{output[-1000:]}"
        )

    output = out.getvalue()

    # Parse "Results: N passed, M failed" line
    import re
    m = re.search(r'Results:\s*(\d+)\s*passed,\s*(\d+)\s*failed', output)
    if m:
        passed, failed = int(m.group(1)), int(m.group(2))
        if failed > 0:
            # Extract FAIL lines for context
            fail_lines = [l for l in output.splitlines() if 'FAIL' in l]
            raise AssertionError(
                f"{filename}: {failed} checks failed, {passed} passed\n" +
                "\n".join(fail_lines[:20])
            )
        return passed, failed

    # Fallback: check for any [FAIL] markers in output
    fail_lines = [l for l in output.splitlines() if '[FAIL]' in l or 'FAIL:' in l]
    if fail_lines:
        raise AssertionError(
            f"{filename}: failures detected\n" + "\n".join(fail_lines[:20])
        )


# Generate one pytest test function per script
def _make_test(script_file):
    def test_fn():
        _run_script(script_file)
    test_fn.__name__ = f"test_script_{os.path.splitext(script_file)[0]}"
    return test_fn


for _id, _file in SCRIPT_TESTS:
    _fn = _make_test(_file)
    _fn.__name__ = f"test_{_id}"
    globals()[f"test_{_id}"] = _fn
