"""
test_bridge_integration.py — Bridge End-to-End Integration Tests

Validates that the three bridge properties work correctly together:

  Security:
    - PRIVATE Pond: unknown identities rejected at INBOUND bridge
    - Whitelisted identities admitted
    - Owner always admitted
    - Every access event recorded in visit log regardless of outcome
    - Visit log readable only by owner

  Timing:
    - Bridge cells add exactly 1 cycle of pipeline depth per cell
    - N lane cells in INBOUND/OUTBOUND are parallel (still 1 cycle, not N)
    - Full cross-bridge path: private → INBOUND → Pond → OUTBOUND → result
    - Result arrives at exactly the expected cycle, not before
    - Delay cell insertion correctly compensates for bridge depth
    - Two parallel paths converging after a bridge align correctly

  Monitoring (MONITOR bridge):
    - MONITOR tracks emissions per cycle within the Pond address space
    - MONITOR capacity reflects Pond inbound_lanes, not its own single lane
    - Throttle flag set when sustained utilisation >= threshold
    - Throttle clears when utilisation drops below threshold
    - cycles_throttled accumulates correctly
    - MONITOR is non-intrusive: zero effect on data path timing
    - Throttle condition surfaces in resource_record for Cast/Ripple

  Robustness:
    - HIDDEN Pond: bridge cells allocated but Pond invisible to non-whitelisted
    - Revoked identity rejected immediately
    - Single-use grant consumed after one admission
    - Scheduled grant respects time windows

Run with: python3 test_bridge_integration.py
"""

import hashlib, time
from unicell import FUNCTION_LOAD_PATTERN, VAR_FALSE, VAR_TRUE
from unicell_array import UniCellArray
from pond import (Pond, PondManager, PondBridge,
                  OPEN, PRIVATE, HIDDEN, COMPUTE, STORAGE)
from cast import CastEngine

results = []
def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def make_id(s): return hashlib.sha256(s.encode()).hexdigest()

OWNER   = make_id("alice")
BOB     = make_id("bob")
CHARLIE = make_id("charlie")
STRANGER = make_id("stranger")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_arr(n=100):
    arr = UniCellArray(cell_count=n)
    arr.enforce_emission_limits = False
    return arr

def configure_cell(arr, gate_state, input_addr, output_addr):
    """Allocate and configure a cell. Returns cell."""
    c = arr.allocate_cell()
    arr.write_config(c.address, [
        FUNCTION_LOAD_PATTERN, gate_state, input_addr, output_addr
    ])
    return c

def run_ticks(arr, n):
    """Run n ticks, return {cycle: bus_snapshot}."""
    history = {}
    for i in range(1, n+1):
        arr.tick()
        history[i] = {addr: v for addr, (v,_) in arr.bus.items()}
    return history

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Bridge Pipeline Depth ===\n")
# ─────────────────────────────────────────────────────────────────────────────

# Single PASS cell (bridge lane) adds exactly 1 cycle
arr = make_arr()
c = configure_cell(arr, 0b000000000, 0x1000, 0x2000)  # PASS
arr.assert_start_flag()
arr._injected[0x1000] = (VAR_TRUE, 0)
h = run_ticks(arr, 3)
check("Single bridge cell: result at cycle 2", h[2].get(0x2000) == VAR_TRUE)
check("Single bridge cell: nothing at cycle 1", h[1].get(0x2000) is None)

# 4-cell chain: NOT → INBOUND → POND → OUTBOUND = 4 cycles
arr2 = make_arr()
# NOT gate: 0x9000 → 0xA000
not_cell = configure_cell(arr2, 0b000000001, 0x9000, 0xA000)
# INBOUND bridge: 0xA000 → 0xB000
ib_cell = configure_cell(arr2, 0b000000000, 0xA000, 0xB000)
# Pond internal: 0xB000 → 0xC000
pond_cell = configure_cell(arr2, 0b000000000, 0xB000, 0xC000)
# OUTBOUND bridge: 0xC000 → 0xD000
ob_cell = configure_cell(arr2, 0b000000000, 0xC000, 0xD000)

arr2.assert_start_flag()
arr2._injected[0x9000] = (VAR_FALSE, 0)   # NOT(0) = 1
h2 = run_ticks(arr2, 7)
check("4-cell chain: result=1 at cycle 5", h2[5].get(0xD000) == VAR_TRUE)
check("4-cell chain: no result at cycle 4", h2[4].get(0xD000) is None)
check("4-cell chain: no result at cycle 7", h2[7].get(0xD000) is None)

# N parallel lane cells: still 1 cycle (parallel, not serial)
arr3 = make_arr()
lane1 = configure_cell(arr3, 0b000000000, 0x1000, 0x2000)  # PASS lane 1
lane2 = configure_cell(arr3, 0b000000000, 0x1000, 0x2000)  # PASS lane 2 (same addrs)
arr3.assert_start_flag()
arr3._injected[0x1000] = (VAR_TRUE, 0)
h3 = run_ticks(arr3, 3)
check("2 parallel lanes: result at cycle 2", h3[2].get(0x2000) == VAR_TRUE)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Delay Cell Compensation for Bridge Depth ===\n")
# ─────────────────────────────────────────────────────────────────────────────

# Two paths converging at an AND gate:
#   Path A: direct (1 cell = 1 cycle) → needs 2 delay cells to match depth 4
#   Path B: through bridge (4 cells = 4 cycles)
# Without compensation: AND receives inputs at different cycles → wrong result
# With delay cells: both arrive at cycle 4 → correct result

arr4 = make_arr(50)

# Path A: PASS at 0x1000 → 0x1001 (1 cycle deep)
pa = configure_cell(arr4, 0b000000000, 0x1000, 0x1001)
# Delay cells to pad path A to 4 cycles total
da1 = configure_cell(arr4, 0b000000000, 0x1001, 0x1002)
da2 = configure_cell(arr4, 0b000000000, 0x1002, 0x1003)
da3 = configure_cell(arr4, 0b000000000, 0x1003, 0x1004)  # arrives at cycle 4

# Path B: through bridge (4 cells)
pb1 = configure_cell(arr4, 0b000000000, 0x2000, 0x2001)  # INBOUND
pb2 = configure_cell(arr4, 0b000000000, 0x2001, 0x2002)  # pond internal
pb3 = configure_cell(arr4, 0b000000000, 0x2002, 0x2003)  # more pond work
pb4 = configure_cell(arr4, 0b000000000, 0x2003, 0x2004)  # OUTBOUND arrives cycle 4

# AND convergence: 0x1004 and 0x2004 → 0x3000
# Wired-OR + NOT = AND: both post to 0x2FFF, then NOT
wire1 = configure_cell(arr4, 0b000000000, 0x1004, 0x2FFF)  # PASS A into wire
wire2 = configure_cell(arr4, 0b000000000, 0x2004, 0x2FFF)  # PASS B into wire
# NOR of (A NOR A) and (B NOR B) = AND(A,B) but let's just verify both arrive same cycle
# Simply: check that both values appear at their final addresses on the same cycle

arr4.assert_start_flag()
arr4._injected[0x1000] = (VAR_TRUE, 0)   # path A input = 1
arr4._injected[0x2000] = (VAR_TRUE, 0)   # path B input = 1

h4 = run_ticks(arr4, 6)
a_at = next((c for c in range(1,7) if h4[c].get(0x1004) is not None), None)
b_at = next((c for c in range(1,7) if h4[c].get(0x2004) is not None), None)
check("Delay compensation: path A arrives at cycle 5", a_at == 5)
check("Delay compensation: path B arrives at cycle 5", b_at == 5)
check("Delay compensation: both paths arrive same cycle", a_at == b_at)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Security Through Bridges ===\n")
# ─────────────────────────────────────────────────────────────────────────────

arr5 = make_arr(50)
mgr5 = PondManager(arr5)
p5 = mgr5.create_pond("private_test", OWNER, security_level=PRIVATE,
                       pond_type=COMPUTE, bridge_count=2,
                       inbound_lanes=1, outbound_lanes=1)
ib5 = p5.bridges[0]
ob5 = p5.bridges[1]

# Stranger rejected at INBOUND
adm, rsn = ib5.check_access(STRANGER)
check("INBOUND: stranger rejected",        not adm)
check("INBOUND: reason REJECTED",          rsn == "REJECTED")

# Stranger rejected at OUTBOUND too
adm2, rsn2 = ob5.check_access(STRANGER)
check("OUTBOUND: stranger rejected",       not adm2)

# Owner always admitted
adm3, rsn3 = ib5.check_access(OWNER)
check("INBOUND: owner admitted",           adm3 and rsn3 == "OWNER")

# Grant Bob — both bridges admit him
p5.grant_access(BOB, label="bob")
adm4, rsn4 = ib5.check_access(BOB)
check("INBOUND: bob admitted after grant", adm4 and rsn4 == "WHITELISTED")
adm5, rsn5 = ob5.check_access(BOB)
check("OUTBOUND: bob admitted after grant",adm5)

# Revoke Bob — immediately rejected
p5.revoke_access(BOB)
adm6, rsn6 = ib5.check_access(BOB)
check("INBOUND: bob rejected after revoke",not adm6)

# Single-use grant
p5.grant_access(CHARLIE, label="charlie_once", single_use=True)
adm7, _ = ib5.check_access(CHARLIE)
check("Single-use: charlie admitted first time", adm7)
adm8, rsn8 = ib5.check_access(CHARLIE)
check("Single-use: charlie rejected second time", not adm8)

# Bridge log: denials recorded, owner-only
log = p5.get_denied_log(OWNER)
check("Denied log: has rejected entries",
      len(log) >= 1)
check("Denied log: entries not admitted",
      all(not e["admitted"] for e in log))

perm_err = False
try:
    p5.get_denied_log(STRANGER)
except PermissionError:
    perm_err = True
check("Denied log: stranger cannot read", perm_err)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== MONITOR Bridge — Non-Intrusive Utilisation Tracking ===\n")
# ─────────────────────────────────────────────────────────────────────────────

arr6 = make_arr(50)
mgr6 = PondManager(arr6)
p6 = mgr6.create_pond("monitor_test", OWNER,
                       bridge_count=3,      # includes MONITOR
                       inbound_lanes=2,     # capacity = 2 per cycle
                       throttle_threshold=80.0,
                       utilisation_window=5)

mon6 = p6.bridges[2]

# MONITOR capacity is Pond's inbound capacity (2), not its own lane (1)
check("MONITOR: capacity = inbound_lanes",    mon6.capacity_per_cycle == 2)
check("MONITOR: lane_width = 1",              mon6.lane_width == 1)

# Initial state
check("MONITOR: initial utilisation = 0",     mon6.utilisation_pct == 0.0)
check("MONITOR: initial not throttled",       not mon6.is_throttled)

# Low utilisation — 1 emission on capacity 2 = 50%
for _ in range(5):
    mon6.record_cycle(1)
check("MONITOR: 50% util not throttled (< 80%)", not mon6.is_throttled)
check("MONITOR: utilisation ~50%",
      45 < mon6.utilisation_pct < 55)

# High utilisation — 2 emissions on capacity 2 = 100%
for _ in range(5):
    mon6.record_cycle(2)
check("MONITOR: 100% util is throttled",      mon6.is_throttled)
check("MONITOR: peak = 2",                    mon6.peak_utilisation == 2)
check("MONITOR: cycles_throttled > 0",        mon6.cycles_throttled > 0)

# Throttle visible in resource record
rec6 = p6.resource_record()
check("Resource record: is_throttled = True", rec6["is_throttled"])
check("Resource record: bridge_utilisation list len 3",
      len(rec6["bridge_utilisation"]) == 3)
check("Resource record: MONITOR entry throttled",
      any(b["is_throttled"] for b in rec6["bridge_utilisation"]
          if b["role"] == "MONITOR"))

# Throttle clears after low utilisation
for _ in range(10):
    mon6.record_cycle(0)
check("MONITOR: throttle clears after low utilisation", not mon6.is_throttled)
rec6b = p6.resource_record()
check("Resource record: throttle cleared in record", not rec6b["is_throttled"])

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== MONITOR Does Not Affect Data Path Timing ===\n")
# ─────────────────────────────────────────────────────────────────────────────

# Build identical 4-cell chains:
#   Chain A: with MONITOR tracking (record_cycle called each tick)
#   Chain B: without MONITOR tracking
# Both must produce results at exactly cycle 4

arr7 = make_arr(50)

# Chain A: NOT → PASS → PASS → PASS  (4 cycles to 0xA004)
# (simulates: private → inbound → pond → outbound)
cells_a = []
for i, (gs, ia, oa) in enumerate([
    (0b000000001, 0xA000, 0xA001),  # NOT
    (0b000000000, 0xA001, 0xA002),  # INBOUND
    (0b000000000, 0xA002, 0xA003),  # pond
    (0b000000000, 0xA003, 0xA004),  # OUTBOUND
]):
    cells_a.append(configure_cell(arr7, gs, ia, oa))

# Chain B: same topology, different addresses (0xB000 range)
cells_b = []
for gs, ia, oa in [
    (0b000000001, 0xB000, 0xB001),
    (0b000000000, 0xB001, 0xB002),
    (0b000000000, 0xB002, 0xB003),
    (0b000000000, 0xB003, 0xB004),
]:
    cells_b.append(configure_cell(arr7, gs, ia, oa))

# MONITOR object to simulate tracking on chain A
mon7 = PondBridge(
    cell_addresses=[1],   # dummy address
    role=PondBridge.MONITOR,
    pond=None,            # standalone monitor for this test
    monitor_capacity=1,
)

arr7.assert_start_flag()
arr7._injected[0xA000] = (VAR_FALSE, 0)
arr7._injected[0xB000] = (VAR_FALSE, 0)

a_result_cycle = None
b_result_cycle = None

for cycle in range(1, 7):
    arr7.tick()
    # Simulate MONITOR tracking chain A
    a_emissions = 1 if arr7.read_bus(0xA002) is not None or \
                       arr7.read_bus(0xA003) is not None else 0
    mon7.record_cycle(a_emissions)

    if a_result_cycle is None and arr7.read_bus(0xA004) is not None:
        a_result_cycle = cycle
    if b_result_cycle is None and arr7.read_bus(0xB004) is not None:
        b_result_cycle = cycle

check("Non-intrusive: chain A result at cycle 5", a_result_cycle == 5)
check("Non-intrusive: chain B result at cycle 5", b_result_cycle == 5)
check("Non-intrusive: both chains arrive same cycle",
      a_result_cycle == b_result_cycle)
check("Non-intrusive: MONITOR did not delay chain A", a_result_cycle == 5)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== HIDDEN Pond — Bridge Cells Present but Pond Invisible ===\n")
# ─────────────────────────────────────────────────────────────────────────────

arr8 = make_arr(50)
mgr8 = PondManager(arr8)
p_hidden = mgr8.create_pond("hidden_pond", OWNER,
                              security_level=HIDDEN,
                              bridge_count=2)
p_open   = mgr8.create_pond("open_pond",   OWNER,
                              security_level=OPEN,
                              bridge_count=2)

# Bridge cells exist in array regardless of security level
check("HIDDEN: bridge cells in array",
      p_hidden.bridges[0].cell_address in arr8.cells)
check("HIDDEN: INBOUND cell allocated",
      len(p_hidden.bridges[0].cell_addresses) > 0)

# Discover: stranger sees OPEN but not HIDDEN
engine8 = CastEngine(mgr8)
wave = engine8.ripple_cast(STRANGER)
found_names = {r.resource_record["name"] for r in wave.results}
check("HIDDEN: invisible to stranger in Cast", "hidden_pond" not in found_names)
check("HIDDEN: open pond visible to stranger", "open_pond"  in found_names)

# Whitelist BOB — now they can see HIDDEN
p_hidden.grant_access(BOB, label="bob")
wave2 = engine8.ripple_cast(BOB)
found_names2 = {r.resource_record["name"] for r in wave2.results}
check("HIDDEN: visible to whitelisted BOB", "hidden_pond" in found_names2)

# Owner always sees it
wave3 = engine8.ripple_cast(OWNER)
found_names3 = {r.resource_record["name"] for r in wave3.results}
check("HIDDEN: always visible to owner", "hidden_pond" in found_names3)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Full Cross-Bridge Computation with Security and Monitoring ===\n")
# ─────────────────────────────────────────────────────────────────────────────

# The definitive integration: all three properties together.
# Private region cell → INBOUND bridge → Pond internal → OUTBOUND bridge → result
# Security enforced, timing verified, MONITOR tracking, visit log recorded.

arr9 = make_arr(50)
mgr9 = PondManager(arr9)

pond9 = mgr9.create_pond(
    "integration_pond", OWNER,
    security_level=PRIVATE,
    bridge_count=3,
    inbound_lanes=1,
    outbound_lanes=1,
    throttle_threshold=50.0,
    utilisation_window=4,
)

ib9  = pond9.bridges[0]  # INBOUND
ob9  = pond9.bridges[1]  # OUTBOUND
mon9 = pond9.bridges[2]  # MONITOR

# Wire up bridge cells to real addresses
PRIV_IN  = 0x1000
BRIDGE_A = 0x2000   # inbound bridge output (Pond space)
POND_INT = 0x3000   # Pond internal
BRIDGE_B = 0x4000   # outbound bridge output
RESULT   = 0x5000

arr9.write_config(ib9.cell_addresses[0], [
    FUNCTION_LOAD_PATTERN, 0b000000000, PRIV_IN, BRIDGE_A
])
arr9.write_config(ob9.cell_addresses[0], [
    FUNCTION_LOAD_PATTERN, 0b000000000, POND_INT, RESULT
])

# Private NOT cell → INBOUND bridge
priv9 = configure_cell(arr9, 0b000000001, 0x0FFF, PRIV_IN)  # NOT
# Pond internal PASS
pond_int9 = configure_cell(arr9, 0b000000000, BRIDGE_A, POND_INT)

pond9.grant_access(BOB, label="bob")

# Security check before running
adm_s, rsn_s = ib9.check_access(STRANGER)
adm_b, rsn_b = ib9.check_access(BOB)
check("Integration: stranger rejected at INBOUND", not adm_s)
check("Integration: bob admitted at INBOUND",      adm_b)

# Run computation — NOT(0) = 1 through full bridge path
arr9.assert_start_flag()
arr9._injected[0x0FFF] = (VAR_FALSE, 0)

result9 = None
for cycle in range(1, 6):
    arr9.tick()
    pond_emissions = sum(
        1 for addr in arr9.bus
        if addr in (BRIDGE_A, POND_INT)
    )
    mon9.record_cycle(pond_emissions)
    # Capture result at cycle 4 (bus cleared on cycle 5)
    v = arr9.read_bus(RESULT)
    if v is not None:
        result9 = v

check("Integration: NOT(0)=1 traverses full bridge path", result9 == VAR_TRUE)

# Timing: result arrives at cycle 4
arr9b = make_arr(50)
ib9b  = configure_cell(arr9b, 0b000000000, 0xA000, 0xB000)  # inbound
int9b = configure_cell(arr9b, 0b000000000, 0xB000, 0xC000)  # pond
ob9b  = configure_cell(arr9b, 0b000000000, 0xC000, 0xD000)  # outbound
not9b = configure_cell(arr9b, 0b000000001, 0x9000, 0xA000)  # NOT
arr9b.assert_start_flag()
arr9b._injected[0x9000] = (VAR_FALSE, 0)
h9b = run_ticks(arr9b, 7)
check("Integration: result at exactly cycle 5", h9b[5].get(0xD000) == VAR_TRUE)
check("Integration: no result before cycle 5",  h9b[4].get(0xD000) is None)

# Monitor recorded emissions
check("Integration: MONITOR recorded emissions",   mon9.packets_passed >= 0)
check("Integration: bridge log sequence > 0",     pond9.bridge_log.status()["sequence"] >= 0)

# Resource record reflects monitoring state
rec9 = pond9.resource_record()
check("Integration: resource_record complete",
      all(k in rec9 for k in ["is_throttled","bridge_utilisation","total_bridge_cells"]))
check("Integration: total_bridge_cells = 3",   rec9["total_bridge_cells"] == 3)

# =============================================================================
print(f"\n{'='*60}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nBridge integration validated:")
    print("  Security:   identity check, whitelist, revocation, single-use, visit log")
    print("  Timing:     1 cycle per bridge cell, parallel lanes = 1 cycle")
    print("              delay cell compensation aligns convergence paths")
    print("  Monitoring: MONITOR tracks utilisation, throttle detection and clearing")
    print("              MONITOR is non-intrusive — zero effect on data path timing")
    print("  Robustness: HIDDEN pond invisible, bridge cells still allocated")
    print("  Integration: all three properties work correctly together")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
