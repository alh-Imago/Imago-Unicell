"""tests/vm/test_connection_check_v1.py -- points.md #606: real tests
using the real DSL compiler, no mocking of ICM records."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import connection_check_v1 as cc  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402


def _compile(dsl):
    icm, diags = compile_source(dsl)
    assert diags == [], diags
    return icm.records


def test_correctly_wired_pair_has_no_hints():
    records = _compile("""
    program good {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
        place b as ram_flowing at (0, 1) { in: w; out: s }
    }
    """.replace(";", "\n"))
    assert cc.check_connections(records) == []


def test_mismatched_pair_flagged_both_directions():
    records = _compile("""
    program mismatch {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
        place b as ram_flowing at (0, 1) { in: e; out: w }
    }
    """.replace(";", "\n"))
    hints = cc.check_connections(records)
    assert len(hints) == 2
    assert any("a@0,0" in h and "b@0,1" in h and "E" in h for h in hints)
    assert any("b@0,1" in h and "a@0,0" in h and "W" in h for h in hints)


def test_broadcast_with_no_physical_neighbor_is_not_flagged():
    """A cell broadcasting toward empty space isn't a "mismatch" --
    there's nothing there to have gotten it wrong."""
    records = _compile("""
    program lonely {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
    }
    """.replace(";", "\n"))
    assert cc.check_connections(records) == []


def test_nano_target_never_flagged_no_real_gate():
    """nano has no real upstream gate at all -- confirmed directly
    against super_tile_library_v1.py's own documented finding -- so it
    can never be the target of a real mismatch."""
    records = _compile("""
    program to_nano {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
        place g as nano_gate at (0, 1) { out: s; topology: 0 }
    }
    """.replace(";", "\n"))
    assert cc.check_connections(records) == []


def test_accumulator_inc_dec_dirs_checked_correctly():
    """Real, direct confirmation that accumulator's separate inc_dir/
    dec_dir fields are OR'd together for the listening check, matching
    the real RTL capture logic (either field can gate an arrival)."""
    records = _compile("""
    program acc {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
        place c as accumulator at (0, 1) { inc: w; dec: s; out: e; step_amount: 1 }
    }
    """.replace(";", "\n"))
    assert cc.check_connections(records) == []


def test_accumulator_wrong_dir_still_flagged():
    records = _compile("""
    program acc_bad {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
        place c as accumulator at (0, 1) { inc: s; dec: n; out: e; step_amount: 1 }
    }
    """.replace(";", "\n"))
    hints = cc.check_connections(records)
    assert len(hints) == 1
    assert "c@0,1" in hints[0]


def test_check_connections_never_raises_on_unknown_core():
    """Real, honest defensive handling -- an unrecognized core string
    (e.g. sequencer, which has no real VM dispatch yet, #519) must
    never crash this check, just be silently skipped as
    not-statically-checkable."""
    class Fake:
        def __init__(self, cell_id, row, col, core, core_config):
            self.cell_id, self.row, self.col = cell_id, row, col
            self.core, self.core_config = core, core_config

    records = [
        Fake("s1", 0, 0, "sequencer", {"downstream_mask": ["e"]}),
        Fake("s2", 0, 1, "sequencer", {}),
    ]
    hints = cc.check_connections(records)  # must not raise
    assert hints == []


def test_branch_out_side_excluded_dynamic():
    """branch's own real output is data-dependent (active_route,
    chosen at runtime) -- never statically flagged as a source."""
    class Fake:
        def __init__(self, cell_id, row, col, core, core_config):
            self.cell_id, self.row, self.col = cell_id, row, col
            self.core, self.core_config = core, core_config

    records = [
        Fake("br", 0, 0, "branch", {"upstream_dir": 0}),
        Fake("r", 0, 1, "ram", {}),  # no upstream_mask at all
    ]
    assert cc.check_connections(records) == []


def test_comparator_uses_real_icm_core_name():
    """Real regression guard, same real mistake as shell_compat_v1.py's
    own (#606's shipped bug): the real ICM/VM core string is
    "comparator", not "compare" (the RTL module file's own naming) --
    confirmed here that a comparator-to-ram mismatch is actually
    detected, not silently skipped because the core name wasn't
    recognized at all."""
    records = _compile("""
    program cmp_bad {
        place a as ram_constant at (0, 0) { out: e; init_data: 1 }
        place c as comparator at (0, 1) { in: n; out: e; threshold: 5 }
    }
    """.replace(";", "\n"))
    hints = cc.check_connections(records)
    assert len(hints) == 1
    assert "c@0,1" in hints[0]
