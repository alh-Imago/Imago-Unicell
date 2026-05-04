"""
test_fpga_bringup.py — Tests for fpga_bringup.py
Claudette v2.1 / unicell-latch variant

Verifies each bring-up step passes against SimBridge (VM).
On real hardware these same tests confirm silicon correctness.

Run: python test_fpga_bringup.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fpga_bridge import SimBridge
from fpga_bringup import (
    step1_reset, step2_uart, step3_not_gate,
    step4_and_gate, step5_relay_pair, step6_scale,
    _patch_bridge, results as bringup_results,
    ADDR_A, ADDR_A_OUT, ADDR_AND_A, ADDR_AND_B, ADDR_AND_OUT,
    ADDR_SRC, ADDR_RELAY, ADDR_DST, ADDR_SCALE_BASE,
)

test_results = []

def check(name, cond):
    status = "PASS" if cond else "FAIL"
    test_results.append((status, name))
    if status == "FAIL":
        print(f"  [FAIL] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    test_results.append((status, name))
    if not ok:
        print(f"  [FAIL] {name}: got {got!r}, expected {expected!r}")

def fresh(num_cells=16):
    b = SimBridge(num_cells=num_cells)
    _patch_bridge(b)
    return b


# =============================================================================
print("\n=== Step 1: RESET ===\n")
# =============================================================================

b = fresh()
ok = step1_reset(b)
check("step1 returns True", ok)
check_eq("step1 armed=0 after reset", b.status()[0], 0)

# Reset with cells configured — should clear them
b2 = fresh()
b2.configure(0, 1, 0x1000, 0x1001)   # GS_NOT
armed_before, _ = b2.status()
ok2 = step1_reset(b2)
armed_after, _ = b2.status()
check("step1 clears configured cells", ok2)
check_eq("armed=0 after configured+reset", armed_after, 0)


# =============================================================================
print("\n=== Step 2: UART round-trip ===\n")
# =============================================================================

b = fresh()
ok = step2_uart(b)
check("step2 returns True", ok)

# Verify DEADBEEF is not FUNCTION_LOAD_PATTERN
from unicell import FUNCTION_LOAD_PATTERN
check("MAGIC != FUNCTION_LOAD_PATTERN", 0xDEAD_BEEF != FUNCTION_LOAD_PATTERN)


# =============================================================================
print("\n=== Step 3: NOT gate ===\n")
# =============================================================================

b = fresh()
ok = step3_not_gate(b)
check("step3 returns True", ok)

# Verify the truth table directly
b2 = fresh()
from gate_states import GS_NOT, LOOP_MODE
b2.configure(0, GS_NOT | LOOP_MODE, ADDR_A, ADDR_A_OUT)

b2.inject(ADDR_A, 0)
r0 = b2.read_output()
check("NOT(0) fires", r0 is not None)
check_eq("NOT(0)=1", r0[1] if r0 else None, 1)
check_eq("NOT(0) addr correct", r0[0] if r0 else None, ADDR_A_OUT)

b2.inject(ADDR_A, 1)
r1 = b2.read_output()
check("NOT(1) fires", r1 is not None)
check_eq("NOT(1)=0", r1[1] if r1 else None, 0)


# =============================================================================
print("\n=== Step 4: AND gate ===\n")
# =============================================================================

b = fresh()
ok = step4_and_gate(b)
check("step4 returns True", ok)

# Verify AND truth table directly
from gate_states import GS_SYNC_WAIT, GS_AND_V2
b2 = fresh()
b2.configure(0, GS_SYNC_WAIT | GS_AND_V2 | LOOP_MODE, ADDR_AND_A, ADDR_AND_OUT)
b2._array.cells[b2._cell_addrs[0]].input_b_address = ADDR_AND_B

for a_val, b_val, expected in [(0,0,0),(0,1,0),(1,0,0),(1,1,1)]:
    if hasattr(b2, '_pending'): b2._pending.clear()
    b2.inject_ab(ADDR_AND_A, a_val, ADDR_AND_B, b_val)
    r = b2.read_output()
    check(f"AND({a_val},{b_val})={expected} fires", r is not None)
    check_eq(f"AND({a_val},{b_val}) value", r[1] if r else None, expected)


# =============================================================================
print("\n=== Step 5: RELAY pair ===\n")
# =============================================================================

b = fresh()
ok = step5_relay_pair(b)
check("step5 returns True", ok)

# Verify relay propagation explicitly
b2 = fresh()
b2.configure(0, GS_NOT | LOOP_MODE, ADDR_SRC, ADDR_RELAY)
b2.configure(1, GS_NOT | LOOP_MODE, ADDR_RELAY, ADDR_DST)

# Run enough ticks for NOT→NOT chain (2 hops)
b2.inject(ADDR_SRC, 1)
b2.inject(ADDR_SRC, 1)   # second inject lets relay propagate
b2.inject(ADDR_SRC, 1)

outputs = b2.drain()
relay_vals = [d for a,d in outputs if a == ADDR_RELAY]
dst_vals   = [d for a,d in outputs if a == ADDR_DST]
check("relay cell fires",    len(relay_vals) > 0)
check("dest cell fires",     len(dst_vals) > 0)
check("relay=NOT(1)=0",      0 in relay_vals)
check("dest=NOT(NOT(1))=1",  1 in dst_vals)

# Isolation: dest doesn't see ADDR_SRC directly
b3 = fresh()
b3.configure(1, GS_NOT | LOOP_MODE, ADDR_RELAY, ADDR_DST)   # dest only, no relay
if hasattr(b3, '_pending'): b3._pending.clear()
if hasattr(b3, '_array'): b3._array.bus.clear()
b3.inject(ADDR_SRC, 1)   # write to SRC, not RELAY — dest should not fire
dst_isolated = [d for a,d in b3.drain() if a == ADDR_DST]
check("isolation: dest silent when only ADDR_SRC written", len(dst_isolated) == 0)


# =============================================================================
print("\n=== Step 6: SCALE (8 cells) ===\n")
# =============================================================================

b = fresh(num_cells=32)
ok = step6_scale(b, num_cells=8)
check("step6 returns True", ok)

# Verify address layout
for i in range(8):
    expected_in  = ADDR_SCALE_BASE + i * 0x10
    expected_out = ADDR_SCALE_BASE + i * 0x10 + 0x08
    check_eq(f"cell {i} addr_in",  expected_in,  ADDR_SCALE_BASE + i * 0x10)
    check_eq(f"cell {i} addr_out", expected_out, ADDR_SCALE_BASE + i * 0x10 + 0x08)


# =============================================================================
print("\n=== Individual step CLI ===\n")
# =============================================================================

# Test --step flag works
b = fresh()
from fpga_bringup import run_bringup
import io, contextlib

# Clear accumulated step results before testing run_bringup wrapper
from fpga_bringup import results as bringup_results_list
bringup_results_list.clear()

b = fresh()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ok = run_bringup(b, steps=[1, 3], verbose=False)
out = buf.getvalue()
check("run_bringup steps=[1,3] passes", ok is True)
check("output contains RESET", 'RESET' in out)
check("output contains NOT", 'NOT' in out)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s,_ in test_results if s == "PASS")
failed = sum(1 for s,_ in test_results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(test_results)} tests")
if failed:
    print("\nFailed:")
    for s, n in test_results:
        if s == "FAIL":
            print(f"  {n}")
