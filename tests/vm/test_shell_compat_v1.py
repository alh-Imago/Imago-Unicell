"""tests/vm/test_shell_compat_v1.py -- points.md #606: real tests
against the actual .v files in this repo, no mocking. Confirms the
real, hard hardware facts this whole feature exists to surface."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import shell_compat_v1 as sc  # noqa: E402


def test_discover_shell_versions_finds_v1_through_v8():
    versions = sc.discover_shell_versions()
    assert set(versions.keys()) >= {f"v{n}" for n in range(1, 9)}
    for path in versions.values():
        assert os.path.exists(path)


def test_discover_shell_versions_excludes_experimental_variant():
    versions = sc.discover_shell_versions()
    for path in versions.values():
        assert "experimental" not in path
        assert "wrapped" not in path


def test_v1_lacks_sequencer_and_branch():
    """The real, hard hardware fact motivating this whole module --
    checked directly against unicell_super_v1.v."""
    versions = sc.discover_shell_versions()
    cores = sc.supported_cores(versions["v1"])
    assert "sequencer" not in cores
    assert "branch" not in cores
    assert "ram" in cores


def test_v2_has_sequencer_but_not_branch():
    versions = sc.discover_shell_versions()
    cores = sc.supported_cores(versions["v2"])
    assert "sequencer" in cores
    assert "branch" not in cores


def test_v3_has_both_sequencer_and_branch():
    versions = sc.discover_shell_versions()
    cores = sc.supported_cores(versions["v3"])
    assert "sequencer" in cores
    assert "branch" in cores


def test_all_versions_have_nano():
    """nano's own ready-bit-broadcasts-unconditionally structural
    property (CELL_GOTCHAS.md) means it's always physically present --
    confirmed here as a real, checkable fact across every real shell."""
    matrix = sc.compatibility_matrix()
    for v, cores in matrix.items():
        assert "nano" in cores, f"{v} is missing nano"


def test_supported_cores_reports_real_module_version():
    versions = sc.discover_shell_versions()
    cores = sc.supported_cores(versions["v4"])
    assert cores["ram"] == ["ram_cell_v2"]  # v4 uses the shared-storage v2 core modules


def test_check_core_compatible_true_case():
    versions = sc.discover_shell_versions()
    ok, reason = sc.check_core_compatible(versions["v3"], "branch")
    assert ok is True
    assert reason is None


def test_check_core_compatible_false_case_names_available_cores():
    versions = sc.discover_shell_versions()
    ok, reason = sc.check_core_compatible(versions["v1"], "branch")
    assert ok is False
    assert "v1" in reason or "unicell_super_v1.v" in reason
    assert "ram" in reason  # lists what IS available


def test_compatibility_matrix_covers_every_discovered_version():
    matrix = sc.compatibility_matrix()
    versions = sc.discover_shell_versions()
    assert set(matrix.keys()) == set(versions.keys())


def test_comparator_uses_real_icm_core_name_not_rtl_module_prefix():
    """Real regression guard: the real ICM/VM-level core string for
    this tile is "comparator" (matching SuperCell.from_record()'s own
    dispatch key and super_tile_library_v1.py's own tile registration
    -- checked directly), NOT "compare" (the RTL module file's own
    naming convention, compare_cell_v1.v). A real bug shipped in #606
    used "compare" as the lookup key, which meant check_core_compatible
    would ALWAYS reject a real "comparator" core, on every shell,
    silently -- caught only when actually exercised, not by any test at
    the time. This test exists so that exact mistake can't come back."""
    versions = sc.discover_shell_versions()
    ok, reason = sc.check_core_compatible(versions["v3"], "comparator")
    assert ok is True
    assert reason is None
    ok2, reason2 = sc.check_core_compatible(versions["v3"], "compare")
    assert ok2 is False  # "compare" is not a real core name at this layer
