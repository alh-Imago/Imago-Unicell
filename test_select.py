"""
test_select.py — GS_SELECT Primitive Tests

Validates the SELECT gate state added in Layer 1 of the pointer model
(Compiler System Definition v0.2, Section 2, Option C).

The SELECT cell is the conditional fork primitive:
  - Receives a condition bit on its input_address
  - Routes to output_address     when condition == 1  (true branch)
  - Routes to output_address_alt when condition == 0  (false branch)
  - Passes the value unchanged to whichever address is chosen
  - Fires once then clears start_flag (same as a compute cell)

These tests operate at the cell and array level — no compiler involved.
The map is built directly from CellMapRecord entries, which is the correct
layer for validating a hardware primitive.

Coverage:
  - GS_SELECT constant value and presence in gate_states
  - CellMapRecord with output_address_alt
  - Security gate checks on alt address
  - UniCell config: output_address_alt set correctly via write_config
  - tick() routing: condition=1 → output_address
  - tick() routing: condition=0 → output_address_alt
  - Value passed unchanged (condition bit preserved in downstream bus)
  - start_flag cleared after firing (fires exactly once)
  - Chain: compute cell → SELECT → two independent downstream cells
  - Chain: condition=1 path reaches its downstream; condition=0 path idle
  - Chain: condition=0 path reaches its downstream; condition=1 path idle
  - SELECT with no output_address_alt falls back to output_address
  - CellMapRecord repr includes alt address
  - SELECT cell repr shows correct mode

Run with: python3 test_select.py
"""

from unicell import UniCell
from unicell_array import UniCellArray
from controller import ImagoController, CellMapRecord
from gate_states import GS_PASS, GS_NOT, GS_SELECT

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

def make_ctrl(cells=20):
    return ImagoController(cell_count=cells)

def run(ctrl, rid, inputs, ticks=10):
    """
    Run for up to `ticks` cycles.
    Returns a merged dict of every address that appeared on the bus
    during the run — because each tick replaces the bus, we accumulate
    across all active cycles to catch transient SELECT routing results.
    """
    ctrl.start(rid, inputs=inputs)
    seen = {}
    for _ in range(ticks):
        active = ctrl.array.tick()
        for addr, val in ctrl.array.bus.items():
            seen[addr] = val
        if active == 0:
            break
    return seen

def bus_has(bus, addr):
    return addr in bus

def bus_val(bus, addr):
    v = bus.get(addr)
    if v is None: return None
    return v[0] if isinstance(v, tuple) else v


# =============================================================================
print("\n=== GS_SELECT constant ===\n")

check("GS_SELECT exists in gate_states",  GS_SELECT == 0x200)
check("GS_SELECT is distinct from GS_PASS", GS_SELECT != GS_PASS)
check("GS_SELECT is distinct from GS_NOT",  GS_SELECT != GS_NOT)
check("GS_SELECT > 9-bit NOR range",     GS_SELECT > 0x1FF)


# =============================================================================
print("\n=== CellMapRecord with output_address_alt ===\n")

rec_normal = CellMapRecord(GS_PASS, 0x1000, 0x2000)
check("Normal record: output_address_alt is None",
      rec_normal.output_address_alt is None)

rec_select = CellMapRecord(GS_SELECT, 0x1000, 0x2000, output_address_alt=0x3000)
check_eq("SELECT record: gate_state stored",       rec_select.gate_state,         GS_SELECT)
check_eq("SELECT record: input_address stored",    rec_select.input_address,      0x1000)
check_eq("SELECT record: output_address stored",   rec_select.output_address,     0x2000)
check_eq("SELECT record: output_address_alt stored", rec_select.output_address_alt, 0x3000)

check("SELECT repr contains 'alt'",  "alt" in repr(rec_select))
check("Normal repr has no 'alt'",    "alt" not in repr(rec_normal))

# 32-bit mask on alt address
rec_masked = CellMapRecord(GS_SELECT, 0, 0x1000, output_address_alt=0x1_DEADBEEF)
check_eq("Alt address masked to 32 bits", rec_masked.output_address_alt, 0xDEADBEEF)


# =============================================================================
print("\n=== Security gate — alt address checked ===\n")

from unicell import FUNCTION_LOAD_PATTERN
from controller import ADDR_NULL

ctrl_sg = make_ctrl(50)

# FUNCTION_LOAD_PATTERN in alt address should be rejected
bad_alt = CellMapRecord(GS_SELECT, 0x1000, 0x2000,
                        output_address_alt=FUNCTION_LOAD_PATTERN)
rid_bad = ctrl_sg.load_map([bad_alt], "bad_alt")
check("Security gate rejects FUNCTION_LOAD_PATTERN in alt address",
      rid_bad is None)

# ADDR_NULL (0x00000000) in alt address should be rejected
null_alt = CellMapRecord(GS_SELECT, 0x1000, 0x2000,
                         output_address_alt=ADDR_NULL)
rid_null = ctrl_sg.load_map([null_alt], "null_alt")
check("Security gate rejects ADDR_NULL in alt address", rid_null is None)

# Valid alt address should pass
good = CellMapRecord(GS_SELECT, 0x1000, 0x2000, output_address_alt=0x3000)
rid_good = ctrl_sg.load_map([good], "good_select")
check("Security gate accepts valid alt address", rid_good is not None)


# =============================================================================
print("\n=== UniCell config — output_address_alt register ===\n")

cell = UniCell(0xABCD)
# Manually drive the 5-field config sequence
cell.receive(FUNCTION_LOAD_PATTERN)          # trigger config mode
cell.receive(GS_SELECT)                      # gate_state
cell.receive(0x1000)                         # input_address
cell.receive(0x2000)                         # output_address (stays in config for SELECT)
cell.receive(0x3000)                         # output_address_alt

check_eq("Cell gate_state = GS_SELECT",         cell.gate_state,         GS_SELECT)
check_eq("Cell input_address set",              cell.input_address,      0x1000)
check_eq("Cell output_address set",             cell.output_address,     0x2000)
check_eq("Cell output_address_alt set",         cell.output_address_alt, 0x3000)
check("Cell config_mode cleared after 5 fields", not cell._config_mode)


# =============================================================================
print("\n=== SELECT routing — condition=1 → output_address ===\n")

ctrl1 = make_ctrl(10)
records = [CellMapRecord(GS_SELECT, 0x1000, 0x3000, output_address_alt=0x4000)]
rid1 = ctrl1.load_map(records, "sel_true")
bus1 = run(ctrl1, rid1, inputs={0x1000: 1})

check("condition=1: true address (0x3000) receives value",  bus_has(bus1, 0x3000))
check("condition=1: false address (0x4000) is silent",      not bus_has(bus1, 0x4000))
check_eq("condition=1: value at true address = 1",          bus_val(bus1, 0x3000), 1)


# =============================================================================
print("\n=== SELECT routing — condition=0 → output_address_alt ===\n")

ctrl0 = make_ctrl(10)
records0 = [CellMapRecord(GS_SELECT, 0x1000, 0x3000, output_address_alt=0x4000)]
rid0 = ctrl0.load_map(records0, "sel_false")
bus0 = run(ctrl0, rid0, inputs={0x1000: 0})

check("condition=0: false address (0x4000) receives value",  bus_has(bus0, 0x4000))
check("condition=0: true address (0x3000) is silent",        not bus_has(bus0, 0x3000))
check_eq("condition=0: value at false address = 0",          bus_val(bus0, 0x4000), 0)


# =============================================================================
print("\n=== SELECT fires exactly once ===\n")

ctrl_once = make_ctrl(10)
records_once = [CellMapRecord(GS_SELECT, 0x1000, 0x3000, output_address_alt=0x4000)]
rid_once = ctrl_once.load_map(records_once, "sel_once")
ctrl_once.start(rid_once, inputs={0x1000: 1})

active1 = ctrl_once.array.tick()   # SELECT fires
active2 = ctrl_once.array.tick()   # should be silent
active3 = ctrl_once.array.tick()   # definitely silent

check("SELECT fires on tick 1",          active1 == 1)
check("SELECT is silent on tick 2",      active2 == 0)
check("SELECT is silent on tick 3",      active3 == 0)

# Confirm start_flag is cleared
sel_cell = list(ctrl_once.array.cells.values())[0]
check("SELECT cell start_flag cleared after firing", not sel_cell.start_flag)


# =============================================================================
print("\n=== SELECT no alt address — falls back to output_address ===\n")

ctrl_nalt = make_ctrl(10)
# output_address_alt=None — missing alt means both paths go to output_address
records_nalt = [CellMapRecord(GS_SELECT, 0x1000, 0x5000)]
rid_nalt = ctrl_nalt.load_map(records_nalt, "sel_no_alt")

# condition=0 with no alt → should still route to output_address
bus_nalt = run(ctrl_nalt, rid_nalt, inputs={0x1000: 0})
check("No alt: condition=0 routes to output_address", bus_has(bus_nalt, 0x5000))


# =============================================================================
print("\n=== Chain: NOT cell → SELECT → two downstream cells ===\n")

# Full conditional fork chain:
#   0x1000 (input) → NOT cell → SELECT cell → 0x3000 (true) or 0x4000 (false)
#   When input=0: NOT produces 1 → SELECT routes to true (0x3000)
#   When input=1: NOT produces 0 → SELECT routes to false (0x4000)

def run_chain(input_val):
    ctrl = make_ctrl(20)
    records = [
        CellMapRecord(GS_NOT,    0x1000, 0x2000),                           # NOT cell
        CellMapRecord(GS_SELECT, 0x2000, 0x3000, output_address_alt=0x4000), # SELECT
        CellMapRecord(GS_PASS,   0x3000, 0x5000),                           # true path
        CellMapRecord(GS_PASS,   0x4000, 0x6000),                           # false path
    ]
    rid = ctrl.load_map(records, "chain")
    bus = run(ctrl, rid, inputs={0x1000: input_val}, ticks=5)
    return bus

bus_chain0 = run_chain(0)
check("Chain input=0: NOT→1, SELECT→true(0x3000)", bus_has(bus_chain0, 0x5000))
check("Chain input=0: false path (0x4000) idle",   not bus_has(bus_chain0, 0x6000))

bus_chain1 = run_chain(1)
check("Chain input=1: NOT→0, SELECT→false(0x4000)", bus_has(bus_chain1, 0x6000))
check("Chain input=1: true path (0x3000) idle",     not bus_has(bus_chain1, 0x5000))


# =============================================================================
print("\n=== Chain: both paths are spatially present, only one active ===\n")

# Both downstream cells exist in the array. When condition routes to true,
# the false-path PASS cell simply never receives data and never fires.
# This confirms the Option C model: both paths are placed, only one carries data.

ctrl_both = make_ctrl(20)
records_both = [
    CellMapRecord(GS_SELECT, 0x1000, 0x2000, output_address_alt=0x3000),
    CellMapRecord(GS_PASS,   0x2000, 0x5000),   # true path cell
    CellMapRecord(GS_PASS,   0x3000, 0x6000),   # false path cell — present but idle
]
rid_both = ctrl_both.load_map(records_both, "both_paths")

# Accumulate bus across all active ticks (bus replaces itself each cycle)
ctrl_both.start(rid_both, inputs={0x1000: 1})
seen_both = {}
for _ in range(5):
    active = ctrl_both.array.tick()
    for addr, val in ctrl_both.array.bus.items():
        seen_both[addr] = val
    if active == 0:
        break

check("Both paths present: true path reached 0x5000", bus_has(seen_both, 0x5000))
check("Both paths present: false path cell idle",     not bus_has(seen_both, 0x6000))

# Confirm false path cell still exists in array (placed but did not fire)
all_cells = list(ctrl_both.array.cells.values())
false_cell = next(
    (c for c in all_cells if c.input_address == 0x3000), None
)
check("False path cell exists in array", false_cell is not None)
# The false path cell was armed by assert_start_flag but never received data,
# so it never fired — it remains start_flag=True but data=None.
check("False path cell has no data (never received)",
      false_cell is not None and false_cell.data is None)


# =============================================================================
print("\n=== CellMapRecord repr ===\n")

r = CellMapRecord(GS_SELECT, 0x1000, 0x2000, output_address_alt=0x3000)
r_repr = repr(r)
check("repr contains gate_state",          "0b" in r_repr)
check("repr contains input address",       "00001000" in r_repr.lower())
check("repr contains output address",      "00002000" in r_repr.lower())
check("repr contains alt address",         "00003000" in r_repr.lower())


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
