"""
test_freeze.py — Start-Flag Freeze / Thaw / Snapshot Tests

Validates the four architectural roles of the start_flag as documented
in the UniCell class:

  Role 1 — Configuration gate: cells are inert until start_flag is asserted.
            Configuration completes fully before any cell participates.

  Role 2 — Branch routing: freeze the unchosen branch, thaw the chosen one.
            Only the armed cells participate in computation.

  Role 3 — Pond freeze / snapshot: freeze a region, capture its complete
            state, restore it identically. Checkpoint and resume.

  Role 4 — Debug freeze: freeze a subset of cells mid-computation,
            inspect their stored values, thaw to resume.

The start_flag is a separate control line from the data bus — it is set
and cleared directly by the controller, never via the bus receive() path.

Run with: python3 test_freeze.py
"""

from unicell import UniCell, FUNCTION_LOAD_PATTERN
from unicell_array import UniCellArray
from controller import ImagoController, CellMapRecord
from gate_states import GS_PASS, GS_NOT, GS_SELECT, LOOP_MODE

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    if not ok:
        print(f"    got {got!r}, expected {expected!r}")
    check(name, ok)

def make_ctrl(cells=50):
    return ImagoController(cell_count=cells)


# =============================================================================
print("\n=== Role 1 — Configuration gate ===\n")

# A cell with start_flag=False must not fire even if data arrives.
cell = UniCell(0x100)
cell.receive(FUNCTION_LOAD_PATTERN)
cell.receive(GS_NOT)
cell.receive(0x1000)
cell.receive(0x2000)
cell.data = 1          # data present
cell.start_flag = False

result = cell.tick()
check("start_flag=False: cell does not fire despite data", result is None)
check("start_flag=False: data not consumed", cell.data == 1)

# After asserting start_flag, cell fires on next tick
cell.start_flag = True
result2 = cell.tick()
check("start_flag=True: cell fires", result2 is not None)
check_eq("start_flag=True: correct output address", result2[0], 0x2000)
check_eq("start_flag=True: NOT(1)=0", result2[1], 0)

# Configuration sequence: cell remains inert during config, fires after
cell2 = UniCell(0x200)
cell2.receive(FUNCTION_LOAD_PATTERN)   # enters config mode — start_flag irrelevant
cell2.receive(GS_PASS)
cell2.receive(0x3000)
cell2.receive(0x4000)
# Config complete. start_flag still False (not set by config).
check("After config: start_flag still False", not cell2.start_flag)
cell2.data = 1
check("After config, before arm: cell does not fire", cell2.tick() is None)
cell2.start_flag = True
cell2.data = 1
check("After arm: cell fires", cell2.tick() is not None)


# =============================================================================
print("\n=== Role 2 — Branch routing via freeze/thaw ===\n")

# Two branches of cells. Freeze one, thaw the other, confirm only one fires.
ctrl2 = make_ctrl(30)

# Branch A: PASS 0x1000 → 0x2000
# Branch B: NOT  0x1000 → 0x3000
recs = [
    CellMapRecord(GS_PASS, 0x1000, 0x2000),   # branch A cell
    CellMapRecord(GS_NOT,  0x1000, 0x3000),   # branch B cell
]
rid2 = ctrl2.load_map(recs, "branches")
region2 = ctrl2._regions[rid2]
branch_a = region2.cell_addresses[0]
branch_b = region2.cell_addresses[1]

# Route to branch A: arm A, freeze B
ctrl2.array.assert_start_flag([branch_a])
ctrl2.array.clear_start_flag([branch_b])   # B is frozen

ctrl2.array.bus = {0x1000: (1, 0)}
ctrl2.array.tick()

bus_a = ctrl2.array.bus
check("Branch A armed: 0x2000 receives PASS(1)=1",  0x2000 in bus_a)
check("Branch B frozen: 0x3000 receives nothing",   0x3000 not in bus_a)
check_eq("Branch A value correct (PASS 1=1)",       bus_a.get(0x2000, (None,))[0], 1)

# Now freeze A, thaw B — same input, different output
frozen_a = ctrl2.freeze([branch_a])
thawed_b = ctrl2.thaw([branch_b])
check_eq("freeze() returns 1", frozen_a, 1)
check_eq("thaw() returns 1",   thawed_b, 1)

ctrl2.array.bus = {0x1000: (1, 0)}
ctrl2.array.tick()
bus_b = ctrl2.array.bus
check("Branch B now armed: 0x3000 receives NOT(1)=0", 0x3000 in bus_b)
check("Branch A frozen: 0x2000 silent",               0x2000 not in bus_b)
check_eq("Branch B value correct (NOT 1=0)",           bus_b.get(0x3000, (None,))[0], 0)


# =============================================================================
print("\n=== freeze() / thaw() — region-level ===\n")

ctrl3 = make_ctrl(30)
recs3 = [
    CellMapRecord(GS_PASS, 0x1000, 0x2000),
    CellMapRecord(GS_NOT,  0x2000, 0x3000),
]
rid3 = ctrl3.load_map(recs3, "chain")
ctrl3.start(rid3, inputs={0x1000: 1})
ctrl3.array.tick()   # PASS fires: 0x2000=1 on bus

# Freeze the whole region
frozen = ctrl3.freeze(region_id=rid3)
check_eq("freeze(region): all cells frozen", frozen, 2)

# Confirm no cells fire
ctrl3.array.tick()
check("After region freeze: bus empty (no cells fire)", len(ctrl3.array.bus) == 0)

# Thaw and resume
thawed = ctrl3.thaw(region_id=rid3)
check_eq("thaw(region): all cells thawed", thawed, 2)

# NOT cell needs data — re-inject the intermediate value
ctrl3.array.bus = {0x2000: (1, 0)}
ctrl3.array.tick()
check("After thaw: NOT cell fires", 0x3000 in ctrl3.array.bus)
check_eq("After thaw: NOT(1)=0", ctrl3.array.bus.get(0x3000, (None,))[0], 0)


# =============================================================================
print("\n=== Role 3 — Snapshot: capture complete cell state ===\n")

ctrl4 = make_ctrl(30)

# Storage cell holding a value
recs4 = [CellMapRecord(GS_PASS, 0x1000, 0x2000, storage_mode=True)]
rid4 = ctrl4.load_map(recs4, "stor")
ctrl4.start(rid4, inputs={0x1000: 1})
ctrl4.array.tick()   # storage cell reads 1, stores it

# Freeze then snapshot
ctrl4.freeze(region_id=rid4)
states = ctrl4.snapshot(region_id=rid4)

check_eq("snapshot: returns 1 state", len(states), 1)
state = states[0]
check("snapshot: has all required keys",
      all(k in state for k in ("gate_state", "input_address", "output_address",
                                "storage_mode", "stored_value", "start_flag",
                                "loop_mode", "ecc_enabled", "data_in_transit")))
check_eq("snapshot: gate_state correct",    state["gate_state"],    GS_PASS)
check_eq("snapshot: input_address correct", state["input_address"], 0x1000)
check_eq("snapshot: storage_mode=True",     state["storage_mode"],  True)
check_eq("snapshot: stored_value=1",        state["stored_value"],  1)
check_eq("snapshot: start_flag=False (frozen)", state["start_flag"], False)


# =============================================================================
print("\n=== Role 3 — Restore: reload snapshot onto fresh array ===\n")

# Create a fresh controller with the same layout
ctrl5 = make_ctrl(30)
recs5 = [CellMapRecord(GS_PASS, 0x1000, 0x2000, storage_mode=True)]
rid5 = ctrl5.load_map(recs5, "restore_target")
# Don't inject or run — cells are blank

# Restore the snapshot from ctrl4
restored = ctrl5.restore_snapshot(states)
check_eq("restore_snapshot: 1 cell restored", restored, 1)

# Check the restored cell has the right stored value
restored_cell = list(ctrl5.array.cells.values())[0]
check_eq("Restored cell: stored_value=1", restored_cell._stored_value, 1)
check_eq("Restored cell: storage_mode=True", restored_cell.storage_mode, True)
check_eq("Restored cell: start_flag=False (as frozen)", restored_cell.start_flag, False)

# Thaw and confirm re-emits
ctrl5.thaw(region_id=rid5)
ctrl5.array.tick()
check("Restored cell re-emits after thaw", 0x2000 in ctrl5.array.bus)
check_eq("Restored cell re-emits stored value",
         ctrl5.array.bus.get(0x2000, (None,))[0], 1)


# =============================================================================
print("\n=== Role 3 — Snapshot preserves loop_mode and alt address ===\n")

ctrl6 = make_ctrl(20)
# SELECT cell with loop_mode
recs6 = [CellMapRecord(GS_SELECT | LOOP_MODE, 0x1000, 0x2000,
                        output_address_alt=0x3000)]
rid6 = ctrl6.load_map(recs6, "sel_loop")
ctrl6.start(rid6, inputs={0x1000: 1})
ctrl6.array.tick()   # fires once

ctrl6.freeze(region_id=rid6)
states6 = ctrl6.snapshot(region_id=rid6)
s6 = states6[0]

check_eq("Snapshot: SELECT gate_state",          s6["gate_state"],         GS_SELECT)
check_eq("Snapshot: loop_mode captured",         s6["loop_mode"],          True)
check_eq("Snapshot: output_address_alt captured", s6["output_address_alt"], 0x3000)


# =============================================================================
print("\n=== Role 4 — Debug freeze: pause mid-computation ===\n")

ctrl7 = make_ctrl(30)
recs7 = [
    CellMapRecord(GS_PASS, 0x1000, 0x2000),
    CellMapRecord(GS_PASS, 0x2000, 0x3000),  # stage 2 — freeze this
    CellMapRecord(GS_NOT,  0x3000, 0x4000),  # stage 3
]
rid7 = ctrl7.load_map(recs7, "pipeline")
region7 = ctrl7._regions[rid7]
stage2_cell = region7.cell_addresses[1]
stage3_cell = region7.cell_addresses[2]

# Run stage 1 only
ctrl7.start(rid7, inputs={0x1000: 1})
# Freeze stages 2 and 3 before running
ctrl7.freeze([stage2_cell, stage3_cell])
ctrl7.array.tick()   # only stage 1 fires

check("Debug freeze: stage 1 output present", 0x2000 in ctrl7.array.bus)
check("Debug freeze: stage 2 output absent",  0x3000 not in ctrl7.array.bus)
check("Debug freeze: stage 3 output absent",  0x4000 not in ctrl7.array.bus)

# Inspect: stage 2 cell hasn't fired — its data is in transit (on bus, not received)
# Thaw stage 2 only, run one tick
ctrl7.thaw([stage2_cell])
ctrl7.array.tick()   # stage 2 fires
check("After thaw stage 2: its output present", 0x3000 in ctrl7.array.bus)
check("Stage 3 still frozen: no 0x4000",        0x4000 not in ctrl7.array.bus)

# Thaw stage 3, run to completion
ctrl7.thaw([stage3_cell])
ctrl7.array.tick()
check("All thawed: stage 3 fires", 0x4000 in ctrl7.array.bus)
check_eq("Final output: NOT(PASS(PASS(1))) = NOT(1) = 0",
         ctrl7.array.bus.get(0x4000, (None,))[0], 0)


# =============================================================================
print("\n=== Role 4 — snapshot() for mid-computation inspection ===\n")

ctrl8 = make_ctrl(20)
recs8 = [CellMapRecord(GS_PASS, 0x1000, 0x1000, storage_mode=True)]
rid8 = ctrl8.load_map(recs8, "stor_inspect")
ctrl8.start(rid8, inputs={0x1000: 1})
ctrl8.array.tick()   # storage cell holds 1

# Snapshot without freezing (live inspection)
states8 = ctrl8.snapshot(region_id=rid8)
check_eq("Live snapshot: stored_value=1", states8[0]["stored_value"], 1)
check_eq("Live snapshot: start_flag=True", states8[0]["start_flag"], True)

# Inject new value and tick
ctrl8.array.bus = {0x1000: (0, 0)}
ctrl8.array.tick()

# Snapshot again — stored value updated
states8b = ctrl8.snapshot(region_id=rid8)
check_eq("Updated snapshot: stored_value=0", states8b[0]["stored_value"], 0)


# =============================================================================
print("\n=== Results ===\n")

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  [FAIL] {name}")
