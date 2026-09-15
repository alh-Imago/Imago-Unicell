"""
test_icm_vix_v1.py — verifies nano/icm_vix_v1.py, the real, formalized
hierarchical ICM format (points.md #737-#742, formalized #747).

The three real example files under nano/examples/ (small relay chain,
parallel reduction tree, CORDIC z-convergence) are used here as real
regression fixtures, not just historical design-note artifacts --
each was independently proven correct (against a known-good expected
value) before this test suite existed, and this suite exists to keep
them proven as the module evolves.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "nano", "examples")


def _example(name):
    return os.path.join(EXAMPLES_DIR, name)


# ---- loading the three real, proven examples ----

def test_small_relay_chain_loads_clean():
    icm = vix.IcmVixFile.load(_example("small_relay_chain.icm-hier.json"))
    assert set(icm.patterns.keys()) == {"entry", "relay", "exit"}
    assert len(icm.placements) == 5
    records, _ = icm.flatten()
    assert len(records) == 8
    assert icm.header() == {"cores_used": ["ram"], "cell_count": 8}
    assert icm.check_connections() == []


def test_parallel_reduction_tree_loads_clean():
    icm = vix.IcmVixFile.load(_example("parallel_reduction_tree.icm-hier.json"))
    records, _ = icm.flatten()
    assert len(records) == 12
    assert icm.header() == {"cores_used": ["adder", "ram"], "cell_count": 12}
    assert icm.check_connections() == []


def test_cordic_z_convergence_loads_clean():
    icm = vix.IcmVixFile.load(_example("cordic_z_convergence.icm-hier.json"))
    records, _ = icm.flatten()
    assert len(records) == 40
    assert icm.header() == {"cores_used": ["adder", "branch", "ram"], "cell_count": 40}
    assert icm.check_connections() == []
    # 4 genuinely distinct patterns -- confirms "every shape is its own
    # pattern" holds even when NOTHING repeats (#738/#742).
    assert len(icm.patterns) == 4


# ---- real execution, against known-correct results, not just "it loads" ----

def test_small_relay_chain_runs_correctly():
    icm = vix.IcmVixFile.load(_example("small_relay_chain.icm-hier.json"))
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    input_cell = next(r for r in records if r.io_name == "input")
    output_cell = next(r for r in records if r.io_name == "output")
    grid.inject(input_cell.row, input_cell.col, 10)
    for _ in range(8):
        grid.tick()
    out = grid.cells[(output_cell.row, output_cell.col)]
    assert out.ram_data_valid and out.ram_data_reg == 10


def test_parallel_reduction_tree_sums_correctly():
    icm = vix.IcmVixFile.load(_example("parallel_reduction_tree.icm-hier.json"))
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    inputs = sorted((r for r in records if r.io_name and r.io_name.startswith("input")),
                    key=lambda r: r.io_name)
    output = next(r for r in records if r.io_name == "output")
    for cell, val in zip(inputs, [10, 20, 30, 40]):
        grid.inject(cell.row, cell.col, val)
    for _ in range(6):
        grid.tick()
    out = grid.cells[(output.row, output.col)]
    assert out.adder_data_valid and out.adder_out_buffer == 100


def test_cordic_converges_to_known_correct_value():
    """Independently computed in plain Python (see #742's own note):
    z0=50000, iterating z -= sign(z)*atan_i for atan_i in
    [45000, 26565, 14036, 7125] converges to exactly -404."""
    icm = vix.IcmVixFile.load(_example("cordic_z_convergence.icm-hier.json"))
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    input_cell = next(r for r in records if r.io_name == "z_input")
    output_cell = next(r for r in records if r.io_name == "z_output")
    for _ in range(6):
        grid.tick()
    grid.inject(input_cell.row, input_cell.col, 50000 & 0xFFFFFFFF)
    for _ in range(20):
        grid.tick()
    out = grid.cells[(output_cell.row, output_cell.col)]
    got = out.ram_data_reg - (1 << 32) if out.ram_data_reg >= (1 << 31) else out.ram_data_reg
    assert out.ram_data_valid and got == -404


# ---- the advisory connection check: both the happy path and catching a real, deliberate break ----

def test_advisory_check_catches_broken_shared_pattern():
    """Real, deliberate negative test (#740/#741's own established
    discipline): breaking a pattern used more than once must flag
    EVERY real, affected instance, not just one."""
    icm = vix.IcmVixFile.load(_example("parallel_reduction_tree.icm-hier.json"))
    icm.patterns["spine_middle"].cells[0].core_config["upstream_mask"] = ["N"]  # drop "W"
    warnings = icm.check_connections()
    assert len(warnings) == 2
    assert any("spine_1" in w for w in warnings)
    assert any("spine_2" in w for w in warnings)


def test_advisory_check_catches_false_nc_claim():
    """A cell claiming NC (deliberately not connected) that actually
    has that face configured should be flagged -- NC is a real,
    checkable claim, not an unchecked escape hatch."""
    icm = vix.IcmVixFile(
        patterns={"p": vix.HierPattern(cells=[
            vix.HierCell(cell_id="a", rel_row=0, rel_col=0, core="ram",
                         core_config={"downstream_mask": ["E"]}),
        ])},
        placements=[vix.HierPlacement(instance="i1", pattern="p", at=(0, 0))],
        connections=[vix.HierConnection(from_=("i1", 0, 0, "E"), to="NC")],
    )
    warnings = icm.check_connections()
    assert len(warnings) == 1
    assert "NC" in warnings[0]


# ---- the real, static known-gotcha check (#749) ----

def test_known_gotchas_clean_on_all_three_real_examples():
    """All three real, proven examples should show ZERO known-gotcha
    warnings -- confirms the check doesn't false-positive on CORDIC's
    own correct flowing-mode+preload_value constant pattern, which
    looks superficially similar to the fixed_mode hazard it's checking
    for but genuinely isn't one."""
    for name in ("small_relay_chain.icm-hier.json", "parallel_reduction_tree.icm-hier.json",
                 "cordic_z_convergence.icm-hier.json"):
        icm = vix.IcmVixFile.load(_example(name))
        assert icm.check_known_gotchas() == [], f"{name} should have zero known-gotcha warnings"


def test_known_gotchas_catches_branch_as_external_entry_point():
    icm = vix.IcmVixFile(
        patterns={"p": vix.HierPattern(cells=[
            vix.HierCell(cell_id="b", rel_row=0, rel_col=0, core="branch",
                         core_config={"upstream_dir": ["w"]}, io_name="bad_entry"),
        ])},
        placements=[vix.HierPlacement(instance="i1", pattern="p", at=(0, 0))],
    )
    warnings = icm.check_known_gotchas()
    assert len(warnings) == 1
    assert "branch" in warnings[0] and "io_name" in warnings[0]


def test_known_gotchas_catches_fixed_mode_feeding_adder():
    icm = vix.IcmVixFile(
        patterns={"p": vix.HierPattern(cells=[
            vix.HierCell(cell_id="const", rel_row=0, rel_col=0, core="ram",
                         core_config={"downstream_mask": ["E"], "fixed_mode": 1,
                                      "init_data": 5, "load_data_valid": 1}),
            vix.HierCell(cell_id="add", rel_row=0, rel_col=1, core="adder",
                         core_config={"upstream_mask": ["W", "N"]}),
        ])},
        placements=[vix.HierPlacement(instance="i1", pattern="p", at=(0, 0))],
    )
    warnings = icm.check_known_gotchas()
    assert len(warnings) == 1
    assert "fixed_mode" in warnings[0]


def test_known_gotchas_does_not_flag_flowing_mode_preload_constant():
    """The CORRECT constant pattern (flowing-mode ram, preload_value)
    must NOT be flagged -- confirms the check targets the real hazard
    specifically (fixed_mode), not "ram feeding an adder" generally."""
    icm = vix.IcmVixFile(
        patterns={"p": vix.HierPattern(cells=[
            vix.HierCell(cell_id="const", rel_row=0, rel_col=0, core="ram",
                         core_config={"downstream_mask": ["E"], "fixed_mode": 0},
                         preload_value=5),
            vix.HierCell(cell_id="add", rel_row=0, rel_col=1, core="adder",
                         core_config={"upstream_mask": ["W", "N"]}),
        ])},
        placements=[vix.HierPlacement(instance="i1", pattern="p", at=(0, 0))],
    )
    assert icm.check_known_gotchas() == []


# ---- per-instance overrides (io_name/preload_value can't live in a shared pattern) ----

def test_per_instance_overrides_apply_correctly():
    icm = vix.IcmVixFile.load(_example("parallel_reduction_tree.icm-hier.json"))
    records, _ = icm.flatten()
    names = sorted(r.io_name for r in records if r.io_name and r.io_name.startswith("input"))
    assert names == ["input_0", "input_1", "input_2", "input_3"]


# ---- structural integrity: unknown pattern reference, position collision ----

def test_flatten_raises_on_unknown_pattern_reference():
    icm = vix.IcmVixFile(
        patterns={},
        placements=[vix.HierPlacement(instance="i1", pattern="does_not_exist", at=(0, 0))],
    )
    try:
        icm.flatten()
        assert False, "expected IcmVixFormatError"
    except vix.IcmVixFormatError:
        pass


# ---- structure file save/load round trip, with real integrity checking ----

def test_structure_save_load_round_trip(tmp_path):
    icm = vix.IcmVixFile.load(_example("cordic_z_convergence.icm-hier.json"))
    path = str(tmp_path / "roundtrip.icm-vix.json")
    icm.save(path)
    reloaded = vix.IcmVixFile.load(path)
    r1, _ = icm.flatten()
    r2, _ = reloaded.flatten()
    assert [(r.cell_id, r.row, r.col, r.core) for r in r1] == \
           [(r.cell_id, r.row, r.col, r.core) for r in r2]


def test_record_hash_catches_hand_edited_file(tmp_path):
    icm = vix.IcmVixFile.load(_example("small_relay_chain.icm-hier.json"))
    path = str(tmp_path / "corrupt.icm-vix.json")
    icm.save(path)
    d = json.load(open(path))
    d["patterns"]["relay"]["cells"][0]["core_config"]["upstream_mask"] = ["X"]
    json.dump(d, open(path, "w"))
    try:
        vix.IcmVixFile.load(path)
        assert False, "expected ValueError for record_hash mismatch"
    except ValueError as e:
        assert "record_hash" in str(e)


# ---- the real, full state save/restore round trip (#744's own named, never-attempted piece) ----

def test_full_state_save_and_restore_round_trip(tmp_path):
    """The real, complete round trip: run the CORDIC pipeline partway,
    save (structure reference + diff), then load the diff, load the
    ORIGINAL structure fresh from disk, build a completely FRESH grid,
    and replay the diff onto it -- confirming the exact same, known-
    correct result reappears on a grid that never ran anything."""
    structure_path = str(tmp_path / "structure.icm-vix.json")
    diff_path = str(tmp_path / "state.diff.json")

    icm = vix.IcmVixFile.load(_example("cordic_z_convergence.icm-hier.json"))
    icm.save(structure_path)
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    input_cell = next(r for r in records if r.io_name == "z_input")
    output_cell = next(r for r in records if r.io_name == "z_output")
    for _ in range(6):
        grid.tick()
    grid.inject(input_cell.row, input_cell.col, 50000 & 0xFFFFFFFF)
    for _ in range(20):
        grid.tick()

    vix.save_state(structure_path, diff_path, records, grid)

    icm2, records2, diff = vix.load_state(diff_path)
    grid2 = SuperGrid(records2)
    missing = vix.apply_diff(records2, grid2, diff)
    assert missing == []

    out2 = grid2.cells[(output_cell.row, output_cell.col)]
    got = out2.ram_data_reg - (1 << 32) if out2.ram_data_reg >= (1 << 31) else out2.ram_data_reg
    assert out2.ram_data_valid and got == -404


def test_apply_diff_reports_missing_cell_id_honestly(tmp_path):
    """If the diff references a cell_id the (possibly-since-changed)
    structure no longer has, apply_diff() reports it rather than
    silently dropping or raising -- every OTHER real entry still
    applies."""
    icm = vix.IcmVixFile.load(_example("small_relay_chain.icm-hier.json"))
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    missing = vix.apply_diff(records, grid, {"does.not.exist": 42})
    assert missing == ["does.not.exist"]
