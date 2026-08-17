"""
test_gpu_array.py — GPU/NumPy array backend tests

Tests the GPUArrayBackend (Stage 1) which replaces the Python cell loop
with a vectorised NumPy/CuPy operation. Runs on CPU via NumPy when no
GPU is present — same code path, different backend.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from gpu_array import GPUArrayBackend, benchmark, CELL_STRIDE, FLAG_ARMED

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


# =============================================================================
print("\n=== Backend detection ===\n")
# =============================================================================

from gpu_array import _HAS_GPU, _DEVICE_NAME, _xp
check("Backend detected",         _DEVICE_NAME is not None)
check("NumPy/CuPy module loaded", _xp is not None)
print(f"  Device: {_DEVICE_NAME}")
print(f"  GPU:    {_HAS_GPU}")


# =============================================================================
print("\n=== GPUArrayBackend: creation ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=1000)
check("backend: created",           backend is not None)
check_eq("backend: cell_count",     backend.cell_count, 1000)
check_eq("backend: no cells yet",   backend._next_idx, 0)
check_eq("backend: tick = 0",       backend._tick, 0)
check_eq("backend: armed = 0",      backend.armed_count(), 0)

s = backend.stats()
check("stats: returns dict",         isinstance(s, dict))
check("stats: has device",           "device" in s)
check("stats: has cells_loaded",     "cells_loaded" in s)
check_eq("stats: tick = 0",          s["tick"], 0)


# =============================================================================
print("\n=== Cell allocation and configuration ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=100)

idx0 = backend.allocate(0x1000)
idx1 = backend.allocate(0x2000)
check_eq("allocate: first cell = 0",  idx0, 0)
check_eq("allocate: second cell = 1", idx1, 1)

# Same address returns same idx
idx0_again = backend.allocate(0x1000)
check_eq("allocate: idempotent",      idx0_again, idx0)

# Configure a PASS cell
from gate_states import GS_PASS, GS_NOT
backend.configure_cell(0x1000, GS_PASS, 0x0FFF, 0x1001, start_flag=True)
backend.configure_cell(0x2000, GS_NOT,  0x1FFF, 0x2001, start_flag=False)

# Armed count
check_eq("armed_count after config",  backend.armed_count(), 1)


# =============================================================================
print("\n=== Tick: PASS cell fires when input present ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=50)
backend.configure_cell(0x1000, GS_PASS, 0x0FFF, 0x2000, start_flag=True)

# No input — should not fire
fired, updates = backend.tick()
check_eq("tick: no input → no fire",   fired, 0)
check_eq("tick: no bus updates",       len(updates), 0)

# Provide input
backend._bus[0x0FFF] = (1, 0)
fired2, updates2 = backend.tick()
check("tick: with input → fires",      fired2 > 0)
check("tick: bus updated",             len(updates2) > 0)
check("tick: output address in bus",   0x2000 in updates2)


# =============================================================================
print("\n=== Tick: NOT cell inverts ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=50)
backend.configure_cell(0x1000, GS_NOT, 0x0FFF, 0x2000, start_flag=True)
backend._bus[0x0FFF] = (0, 0)   # input = 0 → NOT should give 1

fired, updates = backend.tick()
check("NOT: fires on input",       fired > 0)
if 0x2000 in updates:
    val = updates[0x2000]
    result = val[0] if isinstance(val, tuple) else val
    check_eq("NOT(0) = 1",         result, 1)
else:
    check("NOT: output in bus",    False)


# =============================================================================
print("\n=== Tick: armed count changes ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=50)
for i in range(10):
    backend.configure_cell(0x1000 + i, GS_PASS,
                           0x0FFF + i, 0x2000 + i,
                           start_flag=True)
check_eq("10 cells armed",    backend.armed_count(), 10)

# Tick without input
backend.tick()
check_eq("still 10 armed",    backend.armed_count(), 10)


# =============================================================================
print("\n=== Load from UniCellArray ===\n")
# =============================================================================

from unicell_array import UniCellArray
from controller import ImagoController, CellMapRecord

ctrl = ImagoController(cell_count=50)
arr  = ctrl.array

# Load a few cells
for _ in range(5):
    ctrl.load_map([CellMapRecord(GS_PASS, 0x100, 0x200)], "test")

backend2 = GPUArrayBackend(cell_count=200)
loaded = backend2.load_from_unicell_array(arr)
check("load_from_unicell_array: loads cells", loaded > 0)
check_eq("cells loaded = cells in array", loaded, len(arr.cells))


# =============================================================================
print("\n=== Tick counter advances ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=50)
check_eq("tick 0 initially", backend._tick, 0)
backend.tick()
check_eq("tick 1 after tick()", backend._tick, 1)
backend.tick()
backend.tick()
check_eq("tick 3 after 3 ticks", backend._tick, 3)


# =============================================================================
print("\n=== repr ===\n")
# =============================================================================

backend = GPUArrayBackend(cell_count=100)
r = repr(backend)
check("repr: contains device name",  _DEVICE_NAME.split()[0][:3] in r or "GPU" in r or "CPU" in r)
check("repr: contains cell count",   "100" in r)


# =============================================================================
print("\n=== Benchmark smoke test ===\n")
# =============================================================================

result = benchmark(cell_count=1000, ticks=50)
check("benchmark: returns dict",        isinstance(result, dict))
check("benchmark: has ticks_per_sec",   "ticks_per_sec" in result)
check("benchmark: ticks_per_sec > 0",   result["ticks_per_sec"] > 0)
check("benchmark: cells_per_sec > 0",   result["cells_per_sec"] > 0)
print(f"  ticks/sec: {result['ticks_per_sec']:,}")
print(f"  cells/sec: {result['cells_per_sec']:,}")


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
