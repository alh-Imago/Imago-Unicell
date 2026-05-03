from test_helpers import CELL_LATENCY, chain_latency
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
ctrl2.array.tick_drain()

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
ctrl2.array.tick_drain()
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
ctrl3.array.tick_drain()   # PASS fires: 0x2000=1 on bus

# Freeze the whole region
frozen = ctrl3.freeze(region_id=rid3)
check_eq("freeze(region): all cells frozen", frozen, 2)

# Confirm no cells fire
active_after_freeze = ctrl3.array.tick()
check("After region freeze: bus empty (no cells fire)", active_after_freeze == 0)

# Thaw and resume
thawed = ctrl3.thaw(region_id=rid3)
check_eq("thaw(region): all cells thawed", thawed, 2)

# NOT cell needs data — re-inject the intermediate value
ctrl3.array.bus = {0x2000: (1, 0)}
ctrl3.array.tick_drain()
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
ctrl5.array.tick_drain()
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
ctrl7.array.tick_drain()   # only stage 1 fires; drain so 0x2000 visible

check("Debug freeze: stage 1 output present", 0x2000 in ctrl7.array.bus)
check("Debug freeze: stage 2 output absent",  0x3000 not in ctrl7.array.bus)
check("Debug freeze: stage 3 output absent",  0x4000 not in ctrl7.array.bus)

# Inspect: stage 2 cell hasn't fired — its data is in transit (on bus, not received)
# Thaw stage 2 only, run one tick
ctrl7.thaw([stage2_cell])
ctrl7.array.tick_drain()   # stage 2 fires; drain so 0x3000 visible
check("After thaw stage 2: its output present", 0x3000 in ctrl7.array.bus)
check("Stage 3 still frozen: no 0x4000",        0x4000 not in ctrl7.array.bus)

# Thaw stage 3, run to completion
ctrl7.thaw([stage3_cell])
ctrl7.array.tick_drain()
check("All thawed: stage 3 fires", 0x4000 in ctrl7.array.bus)
check_eq("Final output: NOT(PASS(PASS(1))) = NOT(1) = 0",
         ctrl7.array.bus.get(0x4000, (None,))[0], 0)


# =============================================================================
print("\n=== Role 4 — snapshot() for mid-computation inspection ===\n")

ctrl8 = make_ctrl(20)
# Non-loopback storage: separate input (0x1000) and output (0x2000)
# so injecting a new value to 0x1000 doesn't conflict with the cell's output
recs8 = [CellMapRecord(GS_PASS, 0x1000, 0x2000, storage_mode=True)]
rid8 = ctrl8.load_map(recs8, "stor_inspect")
ctrl8.start(rid8, inputs={0x1000: 1})
ctrl8.array.tick()   # storage cell computes; _stored_value=1 this tick

# Snapshot without freezing (live inspection)
# _stored_value is updated during compute tick, readable immediately
states8 = ctrl8.snapshot(region_id=rid8)
check_eq("Live snapshot: stored_value=1", states8[0]["stored_value"], 1)
check_eq("Live snapshot: start_flag=True", states8[0]["start_flag"], True)

# Inject new value — drain output latch first so old result clears, then inject 0
ctrl8.array.tick()               # drain output latch (0x2000=1) into bus
ctrl8.array.bus[0x1000] = (0, 0) # new input
ctrl8.array.tick()               # cell receives 0, _stored_value updated

# Snapshot again — stored value updated
states8b = ctrl8.snapshot(region_id=rid8)
check_eq("Updated snapshot: stored_value=0", states8b[0]["stored_value"], 0)


# =============================================================================
print("\n=== FREEZE/MOVE — output_latch captured in snapshot ===\n")
#
# Scenario: a cell has fired the gate tree and the result is sitting in
# _output_latch, waiting to be drained to the bus next tick.
# At this exact moment the pond is frozen and snapshotted.
# The snapshot must capture _output_latch so that when the pond is restored
# on a new substrate, the first tick after thaw drives the correct result —
# no pipeline bubble, no lost result.
#
# Without this fix: restore_snapshot would leave _output_latch=None.
# The downstream cell would miss the result entirely and the pipeline
# would stall or produce a wrong answer.

ctrl9 = make_ctrl(20)
recs9 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid9 = ctrl9.load_map(recs9, "inflight_cell")
ctrl9.start(rid9, inputs={0x1000: 0})

# Tick once: cell receives input, fires gate tree → result in _output_latch
# The result has NOT yet been drained to the bus.
ctrl9.array.tick()

cell9 = list(ctrl9.array.cells.values())[0]
check("Pre-snapshot: _output_latch is set (result in flight)",
      cell9._output_latch is not None)
check("Pre-snapshot: result not yet on bus",
      0x2000 not in ctrl9.array.bus)

# Freeze and snapshot at this exact moment
ctrl9.freeze(region_id=rid9)
states9 = ctrl9.snapshot(region_id=rid9)
s9 = states9[0]

check("Snapshot includes output_latch key", "output_latch" in s9)
check("Snapshot: output_latch is not None (captured in-flight result)",
      s9["output_latch"] is not None)
# NOT(0) = 1, so output should be (0x2000, 1, 0)
check_eq("Snapshot: output_latch has correct result",
         s9["output_latch"][1], 1)

# =============================================================================
print("\n=== FREEZE/MOVE — restore_snapshot restores output_latch ===\n")
#
# Simulate migration: restore the snapshot onto a fresh array.
# After restore + thaw, the first drain tick should produce the result
# that was in-flight at freeze time — exactly as if the cell never moved.

ctrl10 = make_ctrl(20)
recs10 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid10 = ctrl10.load_map(recs10, "restore_target")

# Restore the snapshot from ctrl9 (cell was mid-pipeline at freeze time)
restored10 = ctrl10.restore_snapshot(states9)
check_eq("restore_snapshot: 1 cell restored", restored10, 1)

cell10 = list(ctrl10.array.cells.values())[0]
check("Restored: _output_latch is not None (in-flight result preserved)",
      cell10._output_latch is not None)
check_eq("Restored: _output_latch has correct result",
         cell10._output_latch[1], 1)

# Thaw and run one drain tick — the in-flight result should appear on bus
ctrl10.thaw(region_id=rid10)
ctrl10.array.tick()  # Phase 1: drain _output_latch → bus

check("After restore+thaw+tick: result on bus at 0x2000",
      0x2000 in ctrl10.array.bus)
if 0x2000 in ctrl10.array.bus:
    entry10 = ctrl10.array.bus[0x2000]
    val10 = entry10[0] if isinstance(entry10, tuple) else entry10
    check_eq("Restored result: NOT(0) = 1, no pipeline bubble", val10, 1)

# =============================================================================
print("\n=== FREEZE/MOVE — snapshot with empty output_latch ===\n")
#
# A cell that has NOT computed anything yet (output_latch=None) should
# snapshot output_latch=None, and restore correctly without any side effects.

ctrl11 = make_ctrl(20)
recs11 = [CellMapRecord(GS_PASS, 0x1000, 0x2000)]
rid11 = ctrl11.load_map(recs11, "idle_cell")
# Start but do NOT tick — cell is armed but has no input, output_latch empty
ctrl11.start(rid11)
ctrl11.freeze(region_id=rid11)
states11 = ctrl11.snapshot(region_id=rid11)

check("Idle cell snapshot: output_latch key present", "output_latch" in states11[0])
check("Idle cell snapshot: output_latch is None", states11[0]["output_latch"] is None)

# Restore onto fresh array — no output should appear on next tick
ctrl12 = make_ctrl(20)
recs12 = [CellMapRecord(GS_PASS, 0x1000, 0x2000)]
rid12 = ctrl12.load_map(recs12, "idle_restore")
ctrl12.restore_snapshot(states11)
ctrl12.thaw(region_id=rid12)
ctrl12.array.tick()
check("Idle restore: no spurious output on bus", 0x2000 not in ctrl12.array.bus)

# =============================================================================
print("\n=== FREEZE/MOVE — input_latch captured and restored ===\n")
#
# A cell that has received input (input_latch loaded) but not yet fired
# the gate tree (still waiting — perhaps start_flag was cleared before
# the compute phase). The input_latch must survive migration.

ctrl13 = make_ctrl(20)
recs13 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid13 = ctrl13.load_map(recs13, "input_pending")
# Inject input directly onto bus (not via start()) so the cell loads
# the value into _input_latch. Then immediately freeze before it fires.
ctrl13.start(rid13)
ctrl13.array.bus[0x1000] = (1, 0)   # deliver A=1 to the cell's input_address

# Run Phase 2 only: deliver bus → input_latch, but don't fire
# We achieve this by delivering the bus value and immediately freezing
# before the compute phase (freeze clears start_flag)
cell13 = list(ctrl13.array.cells.values())[0]
cell13.receive(1)           # simulate Phase 2 delivery directly
cell13.start_flag = False   # freeze before compute
check("Pre-snapshot: _input_latch holds pending value",
      cell13._input_latch == 1)

states13 = ctrl13.snapshot(region_id=rid13)
check("Snapshot: input_latch captured", states13[0].get("input_latch") == 1)

# Restore onto fresh array — rearm and tick to completion
ctrl14 = make_ctrl(20)
recs14 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid14 = ctrl14.load_map(recs14, "input_restore")
ctrl14.restore_snapshot(states13)
ctrl14.thaw(region_id=rid14)

# Cell should fire the gate tree using the restored _input_latch (NOT(1) = 0)
ctrl14.array.tick()   # compute: NOT(1) → _output_latch
ctrl14.array.tick()   # drain: _output_latch → bus

check("Input restore: result on bus", 0x2000 in ctrl14.array.bus)
if 0x2000 in ctrl14.array.bus:
    entry14 = ctrl14.array.bus[0x2000]
    val14 = entry14[0] if isinstance(entry14, tuple) else entry14
    check_eq("Input restore: NOT(1) = 0 (pending input preserved)", val14, 0)


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
