"""
test_fpga_bridge.py — Tests for fpga_bridge.py SimBridge
Claudette v2.1 / unicell-latch variant

Tests the SimBridge (VM-backed) end-to-end. FPGABridge (hardware) is not
tested here — it requires a physical iCEBreaker.

Run: python test_fpga_bridge.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fpga_bridge import SimBridge, CMD_SET_FLAGS, RESP_FLAGS_ACK
from gate_states import GS_NOT, GS_PASS, GS_NOR

results = []

def check(name, cond):
    status = "PASS" if cond else "FAIL"
    results.append((status, name))
    if status == "FAIL":
        print(f"  [FAIL] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    results.append((status, name))
    if not ok:
        print(f"  [FAIL] {name}: got {got!r}, expected {expected!r}")


# =============================================================================
print("\n=== SimBridge: NOT gate ===\n")
# =============================================================================

b = SimBridge(num_cells=8)
b.configure(0, GS_NOT, 0x1000, 0x1001)
b.inject(0x1000, 1)
r = b.read_output()
check("NOT(1): result not None",    r is not None)
check_eq("NOT(1): out_addr",        r[0] if r else None, 0x1001)
check_eq("NOT(1): out_data = 0",    r[1] if r else None, 0)

b.reset()
b.configure(0, GS_NOT, 0x1000, 0x1001)
b.inject(0x1000, 0)
r = b.read_output()
check("NOT(0): result not None",    r is not None)
check_eq("NOT(0): out_addr",        r[0] if r else None, 0x1001)
check_eq("NOT(0): out_data = 1",    r[1] if r else None, 1)


# =============================================================================
print("\n=== SimBridge: PASS gate ===\n")
# =============================================================================

b = SimBridge(num_cells=8)
b.configure(0, GS_PASS, 0x2000, 0x2001)
b.inject(0x2000, 42)
r = b.read_output()
check("PASS(42): result not None",  r is not None)
check_eq("PASS(42): out_addr",      r[0] if r else None, 0x2001)
check_eq("PASS(42): out_data = 42", r[1] if r else None, 42)


# =============================================================================
print("\n=== SimBridge: set_flags ===\n")
# =============================================================================

# Arm all 8
b = SimBridge(num_cells=8)
echoed = b.set_flags(0xFF)
check_eq("set_flags(0xFF): echoed",  echoed, 0xFF)
armed, _ = b.status()
check_eq("set_flags(0xFF): armed=8", armed, 8)

# Arm none
b = SimBridge(num_cells=8)
echoed = b.set_flags(0x00)
check_eq("set_flags(0x00): echoed",  echoed, 0x00)
armed, _ = b.status()
check_eq("set_flags(0x00): armed=0", armed, 0)

# Arm cells 0 and 2 only (mask=0b0101)
b = SimBridge(num_cells=4)
echoed = b.set_flags(0b0101)
check_eq("set_flags(0b0101): echoed", echoed, 0b0101)
armed, _ = b.status()
check_eq("set_flags(0b0101): armed=2", armed, 2)

# Arm then disarm
b = SimBridge(num_cells=8)
b.set_flags(0xFF)
b.set_flags(0x00)
armed, _ = b.status()
check_eq("set_flags disarm: armed=0", armed, 0)

# Mask clipped to num_cells
b = SimBridge(num_cells=4)
echoed = b.set_flags(0xFF)
check_eq("set_flags clipped to 4 bits", echoed, 0x0F)


# =============================================================================
print("\n=== SimBridge: configure auto-arms ===\n")
# =============================================================================

b = SimBridge(num_cells=8)
b.configure(0, GS_PASS, 0x3000, 0x3001)
armed, _ = b.status()
check_eq("configure auto-arms: armed=1", armed, 1)

b.configure(1, GS_NOT, 0x3002, 0x3003)
armed, _ = b.status()
check_eq("configure 2 cells: armed=2", armed, 2)


# =============================================================================
print("\n=== SimBridge: reset ===\n")
# =============================================================================

b = SimBridge(num_cells=8)
b.configure(0, GS_NOT, 0x4000, 0x4001)
b.reset()
armed, _ = b.status()
check_eq("reset clears armed cells", armed, 0)
check_eq("reset clears cell_addrs",  len(b._cell_addrs), 0)
check_eq("reset clears pending",     len(b._pending), 0)

# Re-configure after reset works
b.configure(0, GS_NOT, 0x4000, 0x4001)
b.inject(0x4000, 1)
r = b.read_output()
check("post-reset configure works",  r is not None and r[1] == 0)


# =============================================================================
print("\n=== SimBridge: drain ===\n")
# =============================================================================

b = SimBridge(num_cells=8)
b.configure(0, GS_NOT, 0x5000, 0x5001)
b.inject(0x5000, 1)
results_drain = b.drain()
check_eq("drain: 1 result",       len(results_drain), 1)
check_eq("drain: correct addr",   results_drain[0][0], 0x5001)
check_eq("drain: correct data",   results_drain[0][1], 0)
check_eq("drain: queue empty",    len(b._pending), 0)

# drain when empty returns []
b2 = SimBridge(num_cells=8)
check_eq("drain empty: []", b2.drain(), [])


# =============================================================================
print("\n=== SimBridge: read_output_full ===\n")
# =============================================================================

b = SimBridge(num_cells=8)
b.configure(0, GS_NOT, 0x6000, 0x6001)
b.inject(0x6000, 0)
r = b.read_output_full()
check("read_output_full: not None",  r is not None)
check_eq("read_output_full: 3-tuple", len(r) if r else 0, 3)
check_eq("read_output_full: addr",    r[0] if r else None, 0x6001)
check_eq("read_output_full: data",    r[1] if r else None, 1)
check_eq("read_output_full: hs=0",    r[2] if r else None, 0)


# =============================================================================
print("\n=== SimBridge: context manager ===\n")
# =============================================================================

with SimBridge(num_cells=8) as b:
    b.configure(0, GS_NOT, 0x7000, 0x7001)
    b.inject(0x7000, 1)
    r = b.read_output()
    check("context manager: result",  r is not None and r[1] == 0)


# =============================================================================
print("\n=== Protocol constants ===\n")
# =============================================================================

check_eq("CMD_SET_FLAGS == 0x08",   CMD_SET_FLAGS, 0x08)
check_eq("RESP_FLAGS_ACK == 0x15",  RESP_FLAGS_ACK, 0x15)


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
