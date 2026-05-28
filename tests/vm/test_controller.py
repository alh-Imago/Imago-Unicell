"""
Tests for ImagoController — M3 milestone from the Implementation Guide.
Covers map loading, region lifecycle, run-to-completion, and security gate.
Run with: python3 test_controller.py
"""

# Import canonical bus word values from unicell
from unicell import VAR_TRUE, VAR_FALSE
ADDR_NULL = 0x00000000
from controller import ImagoController, CellMapRecord, Region

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

# ── gate state constants (from Implementation Guide operation table) ───────────
GS_PASS = 0b000000000   # all bypassed — pass input through
GS_NOT  = 0b000000001   # gate 0 active — NOT
GS_NOR  = 0b000000100   # gate 2 active — NOR(g1,g2)

print("\n=== M3 — Controller tests ===\n")

# ── basic load and status ─────────────────────────────────────────────────────
ctrl = ImagoController(cell_count=500)

# Single NOT cell: listens at 0x1000, posts to 0x2000
map1 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid1 = ctrl.load_map(map1, image_name="not_gate")
check("load_map returns a region_id", rid1 is not None)
check("Region in CONFIGURED state after load", ctrl._regions[rid1].state == Region.CONFIGURED)

s = ctrl.status()
check("Status: 1 allocated cell after load", s["allocated_cells"] == 1)
check("Status: 1 active region", s["active_regions"] == 1)

# ── run a NOT gate ────────────────────────────────────────────────────────────
result = ctrl.run(rid1, inputs={0x1000: VAR_FALSE}, capture_addresses=[0x2000])
check("NOT(0) = 1 via controller.run()", result is not None and result.get(0x2000) == VAR_TRUE)
check("Region HALTED after run completes", ctrl._regions[rid1].state == Region.HALTED)
check("Region accumulated cycle count", ctrl._regions[rid1].cycles_run > 0)

# run again with different input (region is HALTED, run() re-starts it)
result2 = ctrl.run(rid1, inputs={0x1000: VAR_TRUE}, capture_addresses=[0x2000])
check("NOT(1) = 0 on second run of same region", result2 is not None and result2.get(0x2000) == VAR_FALSE)

# ── three-cell chain ──────────────────────────────────────────────────────────
ctrl2 = ImagoController(cell_count=500)

# NOT → PASS → PASS chain: input at 0x1000, output at 0x4000
chain_map = [
    CellMapRecord(GS_NOT,  0x1000, 0x2000),
    CellMapRecord(GS_PASS, 0x2000, 0x3000),
    CellMapRecord(GS_PASS, 0x3000, 0x4000),
]
rid2 = ctrl2.load_map(chain_map, image_name="not_chain")
result3 = ctrl2.run(rid2, inputs={0x1000: VAR_FALSE}, capture_addresses=[0x4000])
check("Three-cell NOT→PASS→PASS chain: NOT(0)=1 reaches end", result3.get(0x4000) == VAR_TRUE)

# ── halt and restart ──────────────────────────────────────────────────────────
ctrl3 = ImagoController(cell_count=500)
map3 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid3 = ctrl3.load_map(map3, "halt_test")

# start manually then halt
ctrl3.start(rid3, inputs={0x1000: VAR_FALSE})
check("Region RUNNING after start()", ctrl3._regions[rid3].state == Region.RUNNING)
ctrl3.halt(rid3)
check("Region HALTED after halt()", ctrl3._regions[rid3].state == Region.HALTED)

# restart with different input
result4 = ctrl3.run(rid3, inputs={0x1000: VAR_TRUE}, capture_addresses=[0x2000])
check("Restart after halt: NOT(1)=0 correct", result4.get(0x2000) == VAR_FALSE)

# ── free and cell return ──────────────────────────────────────────────────────
ctrl4 = ImagoController(cell_count=500)
map4a = [CellMapRecord(GS_NOT,  0x1000, 0x2000)]
map4b = [CellMapRecord(GS_PASS, 0x3000, 0x4000)]
rid4a = ctrl4.load_map(map4a, "image_a")
rid4b = ctrl4.load_map(map4b, "image_b")

s_before = ctrl4.status()
ctrl4.run(rid4a, inputs={0x1000: VAR_TRUE}, capture_addresses=[0x2000])
ctrl4.free(rid4a)
s_after = ctrl4.status()
check("Free: region moves to FREED state", ctrl4._regions[rid4a].state == Region.FREED)
check("Free: allocated cell count decreases", s_after["allocated_cells"] < s_before["allocated_cells"])
check("Free: image_b region unaffected", ctrl4._regions[rid4b].state != Region.FREED)

# cannot free a running region
ctrl5 = ImagoController(cell_count=100)
rid5 = ctrl5.load_map([CellMapRecord(GS_PASS, 0x1000, 0x2000)], "running_free_test")
ctrl5.start(rid5, inputs={0x1000: VAR_TRUE})
ok = ctrl5.free(rid5)
check("Cannot free a running region", ok == False)
ctrl5.halt(rid5)

# ── security gate ─────────────────────────────────────────────────────────────
ctrl6 = ImagoController(cell_count=100)

# empty map rejected
rid_empty = ctrl6.load_map([], "empty")
check("Security gate: empty map rejected", rid_empty is None)

# output address = 0x00000000 (ADDR_NULL) rejected
null_map = [CellMapRecord(GS_NOT, 0x1000, ADDR_NULL)]
rid_null = ctrl6.load_map(null_map, "null_output")
check("Security gate: null output address (0x0) rejected", rid_null is None)

# valid map accepted
good_map = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid_good = ctrl6.load_map(good_map, "good_map")
check("Security gate: valid map accepted", rid_good is not None)

# ── defect map integration ────────────────────────────────────────────────────
ctrl7 = ImagoController(cell_count=100)
ctrl7.load_defect_map([0x0001, 0x0002, 0x0003])
cell_map7 = [CellMapRecord(GS_NOT, 0x1000, 0x2000)]
rid7 = ctrl7.load_map(cell_map7, "defect_test")
check("Defect map: region loads successfully despite defects", rid7 is not None)
# allocated cell should be at 0x0004 or later (skipping defective addresses)
if rid7:
    region7 = ctrl7._regions[rid7]
    check("Defect map: cell allocated beyond defective addresses",
          all(addr >= 0x0004 for addr in region7.cell_addresses))

# ── multiple independent regions ──────────────────────────────────────────────
ctrl8 = ImagoController(cell_count=500)
# Load two independent NOT gates, different address spaces
rA = ctrl8.load_map([CellMapRecord(GS_NOT, 0x1000, 0x2000)], "not_A")
rB = ctrl8.load_map([CellMapRecord(GS_NOT, 0x3000, 0x4000)], "not_B")

resA = ctrl8.run(rA, inputs={0x1000: VAR_FALSE}, capture_addresses=[0x2000])
resB = ctrl8.run(rB, inputs={0x3000: VAR_TRUE},  capture_addresses=[0x4000])
check("Two independent regions: region A NOT(0)=1", resA.get(0x2000) == VAR_TRUE)
check("Two independent regions: region B NOT(1)=0", resB.get(0x4000) == VAR_FALSE)

# ── list_regions ──────────────────────────────────────────────────────────────
active = ctrl8.list_regions()
check("list_regions: returns non-freed regions", len(active) == 2)

# ── total cycles tracked ──────────────────────────────────────────────────────
check("Controller total_cycles accumulates across runs", ctrl8.total_cycles > 0)

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
