"""
test_pond_restart.py — Tests for pond restart, checkpoint, freeze_pond,
                       and PondBridge bidirectional mask check.

Covers:
  - pond.restart(): freeze/drain/reset/re-arm sequence
  - pond.checkpoint(): state manifest
  - pond.freeze_pond(): debug snapshot freeze
  - COMPANION ACTION_RESTART calling pond.restart()
  - PondBridge.access_mask field
  - PondBridge.check_mask(): bidirectional O(1) check
  - PondBridge.check_access(): mask check before whitelist
  - Mask inheritance placeholder (structural check)
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))

from pond import (
    Pond, PondManager, PondBridge,
    OPEN, PRIVATE, HIDDEN, PROCESS, WORKSPACE,
)
from unicell_array import UniCellArray

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if not ok:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [PASS] {name}")

OWNER = "owner_001"

def make_pond(name="test_pond", pond_type=PROCESS, security=OPEN):
    arr = UniCellArray(cell_count=200)
    arr.enforce_emission_limits = False
    mgr = PondManager(arr)
    p = mgr.create_pond(name, OWNER,
                        security_level=security,
                        pond_type=pond_type)
    return p, arr, mgr


# =============================================================================
print("\n=== PondBridge.access_mask ===\n")
# =============================================================================

p, arr, mgr = make_pond()
inbound = p._get_bridge(PondBridge.INBOUND)

check_eq("access_mask default = 0xFFFFFFFF",
         inbound.access_mask, 0xFFFFFFFF)

inbound.set_access_mask(0b00000110)
check_eq("set_access_mask: stored correctly",
         inbound.access_mask, 0b00000110)

inbound.set_access_mask(0xFFFFFFFF)  # restore


# =============================================================================
print("\n=== PondBridge.check_mask() — bidirectional ===\n")
# =============================================================================

p, arr, mgr = make_pond()
inbound = p._get_bridge(PondBridge.INBOUND)

# Open bridge (0xFFFFFFFF) — everything passes
check("open mask: zero process passes",    inbound.check_mask(0x00000000))
check("open mask: any process passes",     inbound.check_mask(0xDEADBEEF))

# Restricted bridge
inbound.set_access_mask(0b00000110)   # bits 1+2

check("restricted: matching mask passes",  inbound.check_mask(0b00000010))
check("restricted: overlapping passes",    inbound.check_mask(0b11111110))
check("restricted: no overlap blocked",    not inbound.check_mask(0b00000001))
check("restricted: zero mask blocked",     not inbound.check_mask(0b00000000))
check("restricted: disjoint blocked",      not inbound.check_mask(0b11111001))

# Restore
inbound.set_access_mask(0xFFFFFFFF)


# =============================================================================
print("\n=== PondBridge.check_access() with process_mask ===\n")
# =============================================================================

p, arr, mgr = make_pond(security=OPEN)
inbound = p._get_bridge(PondBridge.INBOUND)
inbound.set_access_mask(0b00000110)

# Open pond — whitelist not enforced, only mask matters
admitted, reason = inbound.check_access(OWNER, process_mask=0b00000010)
check("check_access: matching mask admitted",     admitted)

admitted2, reason2 = inbound.check_access(OWNER, process_mask=0b00000001)
check("check_access: non-matching mask rejected", not admitted2)
check_eq("check_access: rejection reason",        reason2, "MASK_MISMATCH")

# Denied log records the rejection
log = p.get_denied_log(OWNER)
check("denied log: mask rejection recorded",
      any(e.get('reason') == 'MASK_MISMATCH' for e in log))

# Default process_mask = 0xFFFFFFFF (backward compat)
inbound.set_access_mask(0b00000110)
admitted3, _ = inbound.check_access(OWNER)  # no process_mask arg
check("check_access: default mask 0xFFFFFFFF passes", admitted3)

# Restore
inbound.set_access_mask(0xFFFFFFFF)


# =============================================================================
print("\n=== Bidirectional: outbound also checked ===\n")
# =============================================================================

p, arr, mgr = make_pond(security=OPEN)
outbound = p._get_bridge(PondBridge.OUTBOUND)
outbound.set_access_mask(0b00001000)   # bit 3 only

# Process with bit 3 — allowed outbound
admitted_out, _ = outbound.check_access(OWNER, process_mask=0b00001000)
check("outbound: matching mask admitted",  admitted_out)

# Process without bit 3 — blocked outbound
admitted_out2, reason_out2 = outbound.check_access(OWNER, process_mask=0b00000110)
check("outbound: non-matching blocked",    not admitted_out2)
check_eq("outbound: MASK_MISMATCH",        reason_out2, "MASK_MISMATCH")

outbound.set_access_mask(0xFFFFFFFF)


# =============================================================================
print("\n=== pond.restart() ===\n")
# =============================================================================

p, arr, mgr = make_pond()

# Arm all bridge cells
for bridge in p.bridges:
    for addr in bridge.cell_addresses:
        cell = arr.cells.get(addr)
        if cell:
            cell.start_flag = True

# Put something on the bus at bridge addresses
for bridge in p.bridges:
    for addr in bridge.cell_addresses:
        arr._injected[addr] = (1, 0)

# Inject some anomaly state
inbound = p._get_bridge(PondBridge.INBOUND)
inbound._consecutive_zeros = 42
inbound._emission_history = [1, 2, 3]

class _BusWrapper:
    def __init__(self, array): self.array = array
result = p.restart(controller=_BusWrapper(arr), shore=None)

check("restart: returns True",              result)

# Bridge cells should be re-armed
all_armed = all(
    arr.cells[addr].start_flag
    for bridge in p.bridges
    for addr in bridge.cell_addresses
    if addr in arr.cells
)
check("restart: bridge cells re-armed",     all_armed)

# Bus should be drained
bus_clear = all(
    addr not in arr.bus
    for bridge in p.bridges
    for addr in bridge.cell_addresses
)
check("restart: bus drained at bridges",    bus_clear)

# Anomaly counters reset
check("restart: consecutive_zeros reset",
      inbound._consecutive_zeros == 0)
check("restart: emission_history cleared",
      len(inbound._emission_history) == 0)

# Restart count incremented
check("restart: restart_count = 1",
      getattr(p, '_restart_count', 0) == 1)

# Second restart
p.restart()
check("restart: restart_count = 2",
      getattr(p, '_restart_count', 0) == 2)


# =============================================================================
print("\n=== pond.restart() with Shore update ===\n")
# =============================================================================

class MockShore:
    def __init__(self):
        self.updates = {}
    def lookup(self, name):
        return True
    def update(self, name, **kwargs):
        self.updates[name] = kwargs

p2, arr2, mgr2 = make_pond(name="shore_test")
shore = MockShore()
p2.restart(shore=shore)

check("restart: Shore updated",
      any('ward_state' in v for v in shore.updates.values()))
check("restart: Shore ward_state = HEALTHY",
      any(v.get('ward_state') == 'HEALTHY' for v in shore.updates.values()))


# =============================================================================
print("\n=== pond.checkpoint() ===\n")
# =============================================================================

p, arr, mgr = make_pond(name="checkpoint_test")
cp = p.checkpoint()

check("checkpoint: returns dict",          isinstance(cp, dict))
check_eq("checkpoint: correct name",       cp['name'], "checkpoint_test")
check_eq("checkpoint: correct owner",      cp['owner_id'], OWNER)
check("checkpoint: bridges captured",      len(cp['bridges']) >= 2)
check("checkpoint: has checkpointed_at",   'checkpointed_at' in cp)
check("checkpoint: has created_at",        'created_at' in cp)
check("checkpoint: restart_count = 0",     cp['restart_count'] == 0)

# Bridge info correct
b_info = cp['bridges'][0]
check("checkpoint: bridge has role",       'role' in b_info)
check("checkpoint: bridge has addresses",  'lane_addresses' in b_info)
check("checkpoint: bridge has capacity",   'capacity' in b_info)

# After restart, checkpoint shows updated count
p.restart()
cp2 = p.checkpoint()
check("checkpoint: restart_count after restart", cp2['restart_count'] == 1)


# =============================================================================
print("\n=== pond.freeze_pond() ===\n")
# =============================================================================

p, arr, mgr = make_pond()

# Arm bridge cells
for bridge in p.bridges:
    for addr in bridge.cell_addresses:
        cell = arr.cells.get(addr)
        if cell:
            cell.start_flag = True

p.freeze_pond(controller=None)  # no controller — just structural

# With controller
p2, arr2, mgr2 = make_pond(name="freeze_test")
from controller import ImagoController
ctrl = ImagoController(cell_count=100)

# Arm cells in controller
for bridge in p2.bridges:
    for addr in bridge.cell_addresses:
        cell = arr2.cells.get(addr)
        if cell:
            cell.start_flag = True
        # Also arm in the main controller array if present
        if addr in ctrl.array.cells:
            ctrl.array.cells[addr].start_flag = True

p2.freeze_pond(controller=None)
check("freeze_pond: runs without error", True)

# With command interface
from command_interface import make_system_interface
p3, arr3, mgr3 = make_pond(name="freeze_cmd_test")
ctrl3 = ImagoController(cell_count=200)

sys_cmd = make_system_interface(ctrl3, 0xA3F)
p3.freeze_pond(command_interface=sys_cmd)
check("freeze_pond: runs with command_interface", True)


# =============================================================================
print("\n=== COMPANION ACTION_RESTART integration ===\n")
# =============================================================================

# Test that COMPANION's _execute_action for ACTION_RESTART
# can find and call pond.restart() via pond_manager
try:
    from companion import Companion, ACTION_RESTART, EscalationAction

    class MockShore2:
        def lookup(self, name): return True
        def update(self, name, **kwargs): pass
        def clear_escalation(self, name): pass

    from controller import ImagoController as _IC
    shore2 = MockShore2()
    ctrl_c = _IC(cell_count=50)
    p_c, _, _ = make_pond(name="comp_pond")
    class _TL: pass
    comp = Companion(p_c, shore2, ctrl_c, _TL())

    # Inject a pond manager with a test pond
    p_test, arr_test, mgr_test = make_pond(name="companion_test")

    class MockPondManager:
        def get_pond(self, name):
            if name == "companion_test":
                return p_test
            return None

    comp._pond_manager = MockPondManager()

    action = EscalationAction(
        action=ACTION_RESTART,
        target="companion_test",
        reason="test restart",
        source="test",
    )
    comp._execute_action(action)

    check("COMPANION: ACTION_RESTART calls pond.restart()",
          getattr(p_test, '_restart_count', 0) >= 1)

except Exception as e:
    check(f"COMPANION: ACTION_RESTART integration: {e}", False)


# =============================================================================
print("\n=== Mask inheritance — structural check ===\n")
# =============================================================================

# Verify access_mask exists on all bridge types
p, arr, mgr = make_pond()
for bridge in p.bridges:
    check(f"bridge {bridge.role}: has access_mask",
          hasattr(bridge, 'access_mask'))
    check(f"bridge {bridge.role}: default = 0xFFFFFFFF",
          bridge.access_mask == 0xFFFFFFFF)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
