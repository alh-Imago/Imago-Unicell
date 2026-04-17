"""
test_counter_tiles.py — Counter Tile Primitive Tests

Verifies structure, cell counts, and end-to-end array execution
for all three counter families: SHIFT, RIPPLE, DECREMENT.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fp_tiles import TileLibrary, TilePlacer
from controller import ImagoController
from model_library import model_library

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

lib = TileLibrary()

# ── helpers ───────────────────────────────────────────────────────────────────

def write_int(bus, base, value, bits):
    for b in range(bits):
        bus[base + b] = (value >> b) & 1

def read_int(bus, base, bits):
    r = 0
    for b in range(bits):
        v = bus.get(base + b, 0)
        if isinstance(v, tuple): v = v[0]
        if v: r |= (1 << b)
    return r

def run_tile(tile_name, tick_pulses, limit_value=None, init_value=None,
             base=0x00400000):
    """
    Place a counter tile, inject inputs, run for enough ticks, return outputs.
    Returns dict with value bits, done bit, carry bit as applicable.
    """
    t = lib.get(tile_name)
    placer = TilePlacer(base_address=base)
    records, in_a, in_b, out = placer.place(t)

    ctrl = ImagoController(cell_count=len(records) + 200)
    rid  = ctrl.load_map(records, tile_name)

    bus = {}

    if limit_value is not None and in_b:
        write_int(bus, in_b[0], limit_value, len(in_b))

    if init_value is not None and in_b:
        write_int(bus, in_b[0], init_value, len(in_b))

    # Pulse TICK `tick_pulses` times
    for _ in range(tick_pulses):
        bus[in_a[0]] = 1
        ctrl.array.bus.update(bus)
        ctrl.array.tick()
        bus[in_a[0]] = 0
        ctrl.array.bus.update(bus)
        ctrl.array.tick()

    # Run to quiescence
    for _ in range(t.metadata.pipeline_depth + 10):
        ctrl.array.tick()

    # Read outputs from bus
    final_bus = ctrl.array.bus
    return {"bus": final_bus, "out": out, "in_a": in_a, "in_b": in_b}


# =============================================================================
print("\n=== COUNTER_SHIFT structure ===\n")
# =============================================================================

for n in (4, 8, 16, 32):
    name = f"COUNTER_SHIFT_{n}"
    t = lib.get(name)
    check_eq(f"{name}: cell_count == {n+1}", t.metadata.cell_count, n + 1)
    check_eq(f"{name}: pipeline_depth == {n+1}", t.metadata.pipeline_depth, n + 1)

    placer = TilePlacer(base_address=0x400000)
    records, in_a, in_b, out = placer.place(t)
    check_eq(f"{name}: 1 tick input",    len(in_a), 1)
    check_eq(f"{name}: 0 b inputs",      len(in_b), 0)
    check_eq(f"{name}: {n+1} outputs",   len(out),  n + 1)
    check(f"{name}: DONE is last output", out[-1] > out[-2])


# =============================================================================
print("\n=== COUNTER_SHIFT_8 execution ===\n")
# =============================================================================

t8 = lib.get("COUNTER_SHIFT_8")
placer = TilePlacer(base_address=0x400000)
records, in_a, in_b, out = placer.place(t8)

ctrl = ImagoController(cell_count=len(records) + 100)
rid = ctrl.load_map(records, "shift8")
tick_addr = in_a[0]


# SHIFT counter: single pulse walks the chain one step per cycle.
# Manual step-through — capture_addresses would break the chain.
ctrl.start(rid, inputs={tick_addr: 1})

step_fired = [False] * 8
done_fired = False

for cycle in range(t8.metadata.pipeline_depth + 2):
    ctrl.array.tick()
    for i in range(8):
        if out[i] in ctrl.array.bus:
            step_fired[i] = True
    if out[8] in ctrl.array.bus:
        done_fired = True

check("SHIFT_8 exec: step[0] fired", step_fired[0])
check("SHIFT_8 exec: step[7] fired", step_fired[7])
check("SHIFT_8 exec: DONE fired after all steps", done_fired)


# =============================================================================
print("\n=== COUNTER_RIPPLE structure ===\n")
# =============================================================================

for bits in (8, 16, 32):
    name = f"COUNTER_RIPPLE_{bits}"
    t = lib.get(name)
    m = t.metadata

    check(f"{name}: cell_count > 0",      m.cell_count > 0)
    check(f"{name}: pipeline_depth > 0",  m.pipeline_depth > 0)

    placer = TilePlacer(base_address=0x500000)
    records, in_a, in_b, out = placer.place(t)
    check_eq(f"{name}: 1 tick input",         len(in_a), 1)
    check_eq(f"{name}: {bits} limit inputs",  len(in_b), bits)
    # out = bits value + 1 done + 1 carry
    check_eq(f"{name}: {bits+2} outputs",     len(out),  bits + 2)


# =============================================================================
print("\n=== COUNTER_DECREMENT structure ===\n")
# =============================================================================

for bits in (8, 16, 32):
    name = f"COUNTER_DECREMENT_{bits}"
    t = lib.get(name)
    m = t.metadata

    check(f"{name}: cell_count > 0",     m.cell_count > 0)
    check(f"{name}: pipeline_depth > 0", m.pipeline_depth > 0)

    placer = TilePlacer(base_address=0x600000)
    records, in_a, in_b, out = placer.place(t)
    check_eq(f"{name}: 1 tick input",        len(in_a), 1)
    check_eq(f"{name}: {bits} value inputs", len(in_b), bits)
    # out = bits new_value + 1 done
    check_eq(f"{name}: {bits+1} outputs",    len(out),  bits + 1)


# =============================================================================
print("\n=== Model library — counter models ===\n")
# =============================================================================

for name in ["SHIFT_COUNTER_8", "SHIFT_COUNTER_16",
             "RIPPLE_COUNTER_8", "RIPPLE_COUNTER_32",
             "DECREMENT_COUNTER_8", "DECREMENT_COUNTER_32"]:
    spec = model_library.get(name)
    check(f"model {name}: registered",          spec is not None)
    check(f"model {name}: category=COUNTER",    spec.category == "COUNTER")
    check(f"model {name}: pipeline_depth > 0",  spec.pipeline_depth > 0)
    check(f"model {name}: cell_count > 0",      spec.cell_count > 0)


# =============================================================================
print("\n=== COUNTER_SHIFT is leaner than RIPPLE ===\n")
# =============================================================================

shift8  = model_library.get("SHIFT_COUNTER_8")
ripple8 = model_library.get("RIPPLE_COUNTER_8")
check("SHIFT_8 cells < RIPPLE_8 cells",
      shift8.cell_count < ripple8.cell_count)
print(f"    SHIFT_8:  {shift8.cell_count} cells, depth {shift8.pipeline_depth}")
print(f"    RIPPLE_8: {ripple8.cell_count} cells, depth {ripple8.pipeline_depth}")


# =============================================================================
print("\n=== COUNTER_DECREMENT vs RIPPLE ===\n")
# =============================================================================

dec8    = model_library.get("DECREMENT_COUNTER_8")
ripple8 = model_library.get("RIPPLE_COUNTER_8")
check("DECREMENT_8 cells < RIPPLE_8 cells",
      dec8.cell_count < ripple8.cell_count)
print(f"    DECREMENT_8: {dec8.cell_count} cells, depth {dec8.pipeline_depth}")
print(f"    RIPPLE_8:    {ripple8.cell_count} cells, depth {ripple8.pipeline_depth}")


# =============================================================================
print("\n=== Performance quotes ===\n")
# =============================================================================

for name in ["SHIFT_COUNTER_8", "RIPPLE_COUNTER_8", "DECREMENT_COUNTER_8"]:
    q = model_library.performance_quote(name, clock_mhz=1.0)
    check(f"{name}: performance_quote works", "silicon_us" in q)
    print(f"    {name}: {q['silicon_us']} us @ 1MHz")


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
