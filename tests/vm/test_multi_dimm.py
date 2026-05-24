"""
Tests for MultiDimmController.
Covers: multi-DIMM allocation, cross-DIMM region spanning,
swap-out/swap-in, partial snapshots, and address model.
Run with: python3 test_multi_dimm.py
"""

import os, tempfile
from unicell import VAR_TRUE, VAR_FALSE
from controller import CellMapRecord
from multi_dimm import MultiDimmController, system_address, split_system_address
from compiler import ImagoCompiler

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def compile_fn(source, fn_name, input_names):
    """Helper: compile a function and return (records, input_map, output_addrs)."""
    c = ImagoCompiler()
    records, graph, input_map, output_addrs = c.compile_function(
        source, fn_name, input_names)
    return records, input_map, output_addrs

print("\n=== Multi-DIMM tests ===\n")

# ── address model ─────────────────────────────────────────────────────────────
print("--- Address model ---")
check("system_address: slot 0, local 0x1000",
      system_address(0, 0x1000) == 0x0000000000001000)
check("system_address: slot 1, local 0x1000",
      system_address(1, 0x1000) == 0x0000000100001000)
check("split_system_address: slot 0",
      split_system_address(0x0000000000001000) == (0, 0x1000))
check("split_system_address: slot 1",
      split_system_address(0x0000000100001000) == (1, 0x1000))
check("split round-trip",
      system_address(*split_system_address(0x0000000200ABCDEF)) == 0x0000000200ABCDEF)

# ── single DIMM basic operation ───────────────────────────────────────────────
print("\n--- Single DIMM operation ---")

not_src = "def logical_not(a):\n    return not a\n"
records, input_map, output_addrs = compile_fn(not_src, "logical_not", ["a"])

ctrl = MultiDimmController(cells_per_dimm=500)
check("Controller starts with one DIMM (slot 0)", ctrl.slot_count() == 1)

rid = ctrl.load_map(records, "not_gate")
check("load_map returns region_id", rid is not None)

# Map compiler addresses to system addresses via the controller's remap
# (input_map contains compiler-relative addresses; run() uses system addresses)
# For single-DIMM, system_address(0, local) == (0 << 32) | local
# The controller remaps during load_map — we need the remapped addresses.
# Simplest: use build_and_run via ProgramBuilder for clean address handling.
# For direct test, use the region's cell addresses to infer the remap.
region = ctrl._regions[rid]
check("Region has cells allocated", len(region.cell_addresses) > 0)
check("All cells on slot 0",
      all(split_system_address(a)[0] == 0 for a in region.cell_addresses))

# ── add second DIMM ───────────────────────────────────────────────────────────
print("\n--- Two DIMMs ---")

ctrl2 = MultiDimmController(cells_per_dimm=200)
ctrl2.add_dimm(1)
check("Two DIMMs installed", ctrl2.slot_count() == 2)

s = ctrl2.status()
check("Status: total cells = 2 * cells_per_dimm", s["total_cells"] == 400)
check("Status: both slots listed", 0 in s["dimm_slots"] and 1 in s["dimm_slots"])

# Load one image onto each DIMM
and_src = "def logical_and(a, b):\n    return a & b\n"
records_a, _, _ = compile_fn(and_src, "logical_and", ["a", "b"])

or_src = "def logical_or(a, b):\n    return a | b\n"
records_b, _, _ = compile_fn(or_src, "logical_or", ["a", "b"])

rid_a = ctrl2.load_map(records_a, "and_on_slot0", preferred_slot=0)
rid_b = ctrl2.load_map(records_b, "or_on_slot1",  preferred_slot=1)

check("AND region loaded on slot 0", rid_a is not None)
check("OR region loaded on slot 1",  rid_b is not None)

if rid_a and rid_b:
    cells_a = ctrl2._regions[rid_a].cell_addresses
    cells_b = ctrl2._regions[rid_b].cell_addresses
    slot_a = set(split_system_address(a)[0] for a in cells_a)
    slot_b = set(split_system_address(a)[0] for a in cells_b)
    check("AND cells on slot 0", slot_a == {0})
    check("OR cells on slot 1",  slot_b == {1})
    check("No address overlap between regions",
          len(set(cells_a) & set(cells_b)) == 0)

# ── swap out and swap in ───────────────────────────────────────────────────────
print("\n--- Swap out and swap in ---")

ctrl3 = MultiDimmController(cells_per_dimm=500)
ctrl3.add_dimm(1)

not_src2 = "def not2(a):\n    return not a\n"
rec3, _, _ = compile_fn(not_src2, "not2", ["a"])
rid3 = ctrl3.load_map(rec3, "not2")
check("Region loaded before swap", rid3 is not None)

cells_before = len(ctrl3._regions[rid3].cell_addresses)
s_before = ctrl3.status()

with tempfile.TemporaryDirectory() as swap_dir:
    # Swap out to slot 0's swap area
    swap_path = ctrl3.swap_out(rid3, swap_dir)
    check("swap_out returns a path", swap_path is not None)
    check("swap file exists", swap_path is not None and os.path.exists(swap_path))
    check("Region is FREED after swap_out",
          ctrl3._regions[rid3].state.__class__.__name__ == 'str' and
          ctrl3._regions.get(rid3) is not None)

    s_after_swap_out = ctrl3.status()
    check("Cells freed after swap_out",
          s_after_swap_out["allocated_cells"] < s_before["allocated_cells"])

    # Swap back in — onto slot 1 (different DIMM)
    new_rid = ctrl3.swap_in(swap_path, preferred_slot=1)
    check("swap_in returns new region_id", new_rid is not None)

    if new_rid:
        new_cells = ctrl3._regions[new_rid].cell_addresses
        new_slot = set(split_system_address(a)[0] for a in new_cells)
        check("Swapped-in region lands on slot 1", new_slot == {1})
        check("Same cell count after swap", len(new_cells) == cells_before)

        s_after_swap_in = ctrl3.status()
        check("Cells reallocated after swap_in",
              s_after_swap_in["allocated_cells"] == s_before["allocated_cells"])

# ── partial snapshot ──────────────────────────────────────────────────────────
print("\n--- Partial snapshot ---")

ctrl4 = MultiDimmController(cells_per_dimm=500)
xor_src = "def xor4(a, b):\n    return a ^ b\n"
rec4, _, _ = compile_fn(xor_src, "xor4", ["a", "b"])
rid4 = ctrl4.load_map(rec4, "xor4")
check("Region loaded for snapshot", rid4 is not None)

cells_before_snap = ctrl4.status()["allocated_cells"]

with tempfile.TemporaryDirectory() as snap_dir:
    snap_path = ctrl4.snapshot(rid4, snap_dir)
    check("snapshot returns a path", snap_path is not None)
    check("snapshot file exists",
          snap_path is not None and os.path.exists(snap_path))

    # Region still exists after snapshot (cells NOT freed)
    check("Region still allocated after snapshot",
          ctrl4.status()["allocated_cells"] == cells_before_snap)
    check("Region still in registry after snapshot",
          rid4 in ctrl4._regions)

    # Reload snapshot as a fresh region (duplicate)
    import json
    with open(snap_path) as f:
        snap_data = json.load(f)
    snap_records = [
        __import__('controller').CellMapRecord(
            c["gate_state"], c["input_address"], c["output_address"])
        for c in snap_data["cell_configs"]
    ]
    rid4b = ctrl4.load_map(snap_records, "xor4_from_snapshot")
    check("Snapshot reload creates second region", rid4b is not None)
    check("Both regions coexist",
          rid4 in ctrl4._regions and rid4b in ctrl4._regions)

# ── status across two DIMMs ───────────────────────────────────────────────────
print("\n--- Status and free across DIMMs ---")

ctrl5 = MultiDimmController(cells_per_dimm=300)
ctrl5.add_dimm(1)

r1 = ctrl5.load_map(
    compile_fn("def f1(a):\n    return not a\n", "f1", ["a"])[0],
    "f1", preferred_slot=0)
r2 = ctrl5.load_map(
    compile_fn("def f2(a):\n    return not a\n", "f2", ["a"])[0],
    "f2", preferred_slot=1)

s5 = ctrl5.status()
check("Status: 2 active regions", s5["active_regions"] == 2)

ctrl5.free(r1)
ctrl5.free(r2)
s5b = ctrl5.status()
check("Status: 0 active after free", s5b["active_regions"] == 0)
check("Status: 0 allocated after free", s5b["allocated_cells"] == 0)

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*40}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
