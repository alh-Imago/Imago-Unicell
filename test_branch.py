"""
test_branch.py — BranchPoint and DataTable Tests

Validates the runtime-volatile dispatch mechanism in branch.py.

BranchPoint (Mode 2 — PTT dispatch):
  - 1-cell layout: XNOR + latch_in
  - A preloaded into a_data. B injected as trigger.
  - Result (0xFFFFFFFF=equal, 0=not equal) fires to ptt_addr.
  - dispatch() marks addr_true or addr_false on bus so callers can observe.
  - lock/load/run: freeze → preload A → thaw → inject B

DataTable:
  - Named rows of {label, a, b, addr_true, addr_false}
  - Volatile: rows can be added, updated, removed at runtime

Run with: python3 test_branch.py
"""

from branch import BranchPoint, DataTable, DataRow
from controller import ImagoController

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

def make_bp():
    ctrl = ImagoController(cell_count=200)
    bp = BranchPoint.build(ctrl, "bp")
    return ctrl, bp

def dispatch(ctrl, bp, a, b, addr_true=0x9000, addr_false=0xA000, max_ticks=30):
    """Load and run one dispatch, return (true_hit, false_hit)."""
    # Clear stale bus and carry from previous dispatch
    for addr in (addr_true, addr_false, bp.ptt_addr):
        ctrl.array.bus.pop(addr, None)
        ctrl.array._carry.pop(addr, None)
    bp.load(ctrl, a=a, b=b, addr_true=addr_true, addr_false=addr_false)
    # Inject B
    ctrl.array._injected[bp.cell_a_in] = (b & 0xFFFFFFFF, 0)
    # Run until PTT fires
    for _ in range(max_ticks):
        ctrl.array.tick()
        if bp.ptt_addr in ctrl.array.bus:
            result = ctrl.array.bus[bp.ptt_addr][0]
            bp.dispatch(result, ctrl)
            # One more tick to let dispatch injection land
            ctrl.array.tick()
            break
    return addr_true in ctrl.array.bus, addr_false in ctrl.array.bus


# =============================================================================
print("\n=== DataTable — structure ===\n")

t = DataTable("routing")
check_eq("Empty table has 0 rows", len(t), 0)

r1 = t.add("r1", a=0, b=0, addr_true=0x1000, addr_false=0x2000)
r2 = t.add("r2", a=1, b=1, addr_true=0x3000, addr_false=0x4000)
check_eq("After two adds: len=2", len(t), 2)
check_eq("get('r1') returns row",  t.get("r1").label, "r1")
check_eq("get('r2') returns row",  t.get("r2").label, "r2")
check("get('missing') returns None", t.get("missing") is None)

check_eq("r1.a", r1.a, 0)
check_eq("r1.b", r1.b, 0)
check_eq("r1.addr_true",  hex(r1.addr_true),  hex(0x1000))
check_eq("r1.addr_false", hex(r1.addr_false), hex(0x2000))

t.update("r1", a=1, b=0)
check_eq("update: r1.a changed to 1", t.get("r1").a, 1)
check_eq("update: r1.b changed to 0", t.get("r1").b, 0)

t.remove("r2")
check_eq("After remove: len=1", len(t), 1)
check("Removed row not found",  t.get("r2") is None)

d = r1.to_dict()
check("to_dict has required keys",
      all(k in d for k in ("label","a","b","addr_true","addr_false")))

dump = t.dump()
check("dump contains table name",    "routing" in dump)
check("dump contains row label",     "r1" in dump)


# =============================================================================
print("\n=== BranchPoint — build ===\n")

ctrl, bp = make_bp()
check("BranchPoint builds successfully", bp is not None)
check("region_id assigned",             bp.region_id is not None)
check("cell_addresses non-empty",       len(bp.cell_addresses) > 0)
check("cell_a_in allocated",            bp.cell_a_in > 0)
check("ptt_addr allocated",             bp.ptt_addr > 0)
check("current_row is None (unloaded)", bp.current_row is None)

# Starts frozen — no cells fire
ctrl.array.tick()
check("BranchPoint starts frozen: no bus activity", len(ctrl.array.bus) == 0)


# =============================================================================
print("\n=== BranchPoint — comparator all four cases ===\n")

for a, b, expect_true, label in [
    (0, 0, True,  "0==0"),
    (1, 1, True,  "1==1"),
    (0, 1, False, "0!=1"),
    (1, 0, False, "1!=0"),
]:
    ctrl_c, bp_c = make_bp()
    t_hit, f_hit = dispatch(ctrl_c, bp_c, a, b)
    check(f"Comparator {label}: true={expect_true}",
          t_hit == expect_true and f_hit == (not expect_true))


# =============================================================================
print("\n=== BranchPoint — routing destinations ===\n")

ctrl2, bp2 = make_bp()
t, f = dispatch(ctrl2, bp2, 1, 1, addr_true=0xABCD, addr_false=0xDEF0)
check("true branch routes to addr_true (0xABCD)", t)
check("false branch stays silent",                not f)

ctrl3, bp3 = make_bp()
t, f = dispatch(ctrl3, bp3, 0, 1, addr_true=0xABCD, addr_false=0xDEF0)
check("false branch routes to addr_false (0xDEF0)", f)
check("true branch stays silent",                   not t)


# =============================================================================
print("\n=== BranchPoint — load updates current_row ===\n")

ctrl4, bp4 = make_bp()
table4 = DataTable("t4")
row4 = table4.add("test", a=1, b=1, addr_true=0x1000, addr_false=0x2000)
bp4.load_row(row4, ctrl4)

check("current_row set after load_row", bp4.current_row is not None)
check_eq("current_row label", bp4.current_row.label, "test")
check_eq("current_row.a",     bp4.current_row.a,     1)


# =============================================================================
print("\n=== BranchPoint — volatile re-load ===\n")

ctrl5, bp5 = make_bp()

cases5 = [
    (1, 1, True,  "re: 1==1"),
    (0, 1, False, "re: 0!=1"),
    (0, 0, True,  "re: 0==0"),
    (1, 0, False, "re: 1!=0"),
    (1, 1, True,  "re: 1==1 again"),
]
for a, b, expect_true, label in cases5:
    t_hit, f_hit = dispatch(ctrl5, bp5, a, b)
    check(f"Volatile re-load {label}: correct routing",
          t_hit == expect_true and f_hit == (not expect_true))


# =============================================================================
print("\n=== BranchPoint — stale data flushed on reload ===\n")

ctrl7, bp7 = make_bp()

# First run
dispatch(ctrl7, bp7, 1, 1)
for _ in range(3): ctrl7.array.tick()

# Reload with opposite values
t7, f7 = dispatch(ctrl7, bp7, 0, 1)
check("After flush: 0!=1 routes to false correctly", f7 and not t7)

t7b, f7b = dispatch(ctrl7, bp7, 0, 0)
check("After flush: 0==0 routes to true correctly", t7b and not f7b)


# =============================================================================
print("\n=== BranchPoint — freeze/thaw API ===\n")

ctrl8, bp8 = make_bp()
dispatch(ctrl8, bp8, 1, 1)

frozen = bp8.freeze(ctrl8)
check("freeze() returns cell count", frozen > 0)
ctrl8.array.bus.clear()
ctrl8.array._carry.clear()
ctrl8.array._injected.clear()
active_after_freeze = ctrl8.array.tick()
check("After freeze: no bus activity", active_after_freeze == 0)

thawed = bp8.thaw(ctrl8)
check("thaw() returns cell count", thawed > 0)


# =============================================================================
print("\n=== DataTable — drives BranchPoint via load_row ===\n")

ctrl9, bp9 = make_bp()
table9 = DataTable("dispatch_table")
table9.add("go_left",  a=0, b=0, addr_true=0xAAAA, addr_false=0xBBBB)
table9.add("go_right", a=0, b=1, addr_true=0xCCCC, addr_false=0xDDDD)

t9, _ = dispatch(ctrl9, bp9, 0, 0, addr_true=0xAAAA, addr_false=0xBBBB)
check("DataTable row 'go_left' (0==0) -> 0xAAAA", t9)

_, f9 = dispatch(ctrl9, bp9, 0, 1, addr_true=0xCCCC, addr_false=0xDDDD)
check("DataTable row 'go_right' (0!=1) -> 0xDDDD", f9)


# =============================================================================
print("\n=== DataTable — update row changes dispatch ===\n")

ctrl10, bp10 = make_bp()
table10 = DataTable("mutable")
table10.add("row", a=1, b=1, addr_true=0x1000, addr_false=0x2000)

t10, _ = dispatch(ctrl10, bp10, 1, 1, addr_true=0x1000, addr_false=0x2000)
check("Before update: 1==1 -> 0x1000", t10)

table10.update("row", a=0, b=1)
_, f10 = dispatch(ctrl10, bp10, 0, 1, addr_true=0x1000, addr_false=0x2000)
check("After update: 0!=1 -> 0x2000", f10)


# =============================================================================
print("\n=== BranchPoint status ===\n")

ctrl11, bp11 = make_bp()
st = bp11.status()
check("status has region_id",        "region_id"    in st)
check("status has cell_a_in",        "cell_a_in"    in st)
check("status has ptt_addr",         "ptt_addr"     in st)
check("status has total_cells",      "total_cells"  in st)
check("status has current_row=None", st["current_row"] is None)
check("total_cells > 0",             st["total_cells"] > 0)

bp11.load(ctrl11, a=1, b=0, addr_true=0x100, addr_false=0x200)
st2 = bp11.status()
check("After load: current_row in status",  st2["current_row"] is not None)
check("After load: row has label",          "label" in st2["current_row"])


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
