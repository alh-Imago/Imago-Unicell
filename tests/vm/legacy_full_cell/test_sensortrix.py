"""
test_sensortrix.py — SensorTrix format and tile tests

Tests:
  - SensorTrix FormatDefinition registered and correct
  - pack/unpack encoding correctness
  - pack_stack / unpack_stack round-trip
  - SENSOR_UNPACK tile: cells=144, depth=5
  - SENSOR_THRESHOLD tile: cells=518, depth=14
  - SENSOR_DELTA tile: cells=517, depth=12
  - SENSOR_STACK_MAX tile: cells=317, depth=66
  - SENSOR_STACK_SUM tile: cells=482, depth=10
  - All five tiles fit 900c budget
  - Reference implementations correct (21 cases)
  - Three sensor stack demos (touch, IMU, arm) produce expected results

Run: python3 tests/vm/test_sensortrix.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatRegistry, SensorTrix
from fp_tiles import TileLibrary
from sensortrix_runner import (
    ref_unpack, ref_threshold, ref_delta, ref_stack_max, ref_stack_sum,
    run_sensor_demo, run_validation
)

PASS, FAIL = 0, 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))

BUDGET = 900   # target cell budget

fmt = SensorTrix()
reg = FormatRegistry.get_default()
lib = TileLibrary()

def tile_cost(name):
    t = lib.get(name)
    return t.metadata.cell_count, t.metadata.pipeline_depth

print("\n=== SensorTrix FormatDefinition ===")
check("SensorTrix registered", reg.get("SensorTrix") is not None)
check("domain is SensorTrix", fmt.domain == "SensorTrix")
check("boundary_in is SENSOR_UNPACK", fmt.boundary_in == "SENSOR_UNPACK")
check("boundary_out is None (source-only)", fmt.boundary_out is None)
check("5 valid tiles", len(fmt.valid_tiles) == 5)
for tile in ["SENSOR_UNPACK","SENSOR_THRESHOLD","SENSOR_DELTA",
             "SENSOR_STACK_MAX","SENSOR_STACK_SUM"]:
    check(f"valid_tiles includes {tile}", tile in fmt.valid_tiles)

print("\n=== Encoding ===")
check("pack(0, 0) == 0",         fmt.pack(0, 0) == 0)
check("pack(0, 65535) == 0xFFFF0000",
       fmt.pack(0, 65535) == 0xFFFF0000)
check("pack(65535, 0) == 0x0000FFFF",
       fmt.pack(65535, 0) == 0x0000FFFF)
check("pack(3, 12800) round-trips",
       ref_unpack(fmt.pack(3, 12800)) == (3, 12800))
check("unpack(0xFFFF0000) == (0, 65535)",
       fmt.unpack(0xFFFF0000) == (0, 65535))
check("unpack(0x00010002) == (2, 1)",
       fmt.unpack(0x00010002) == (2, 1))

readings_8 = [(i, i*1000) for i in range(8)]
check("pack_stack/unpack_stack round-trip (8 elements)",
       fmt.unpack_stack(fmt.pack_stack(readings_8)) == readings_8)

print("\n=== Tile costs and budget ===")
EXPECTED = {
    "SENSOR_UNPACK":    (144,  5),
    "SENSOR_THRESHOLD": (518, 14),
    "SENSOR_DELTA":     (517, 12),
    "SENSOR_STACK_MAX": (317, 66),
    "SENSOR_STACK_SUM": (482, 10),
}
for name, (exp_c, exp_d) in EXPECTED.items():
    c, d = tile_cost(name)
    check(f"{name}: cells={exp_c}", c == exp_c, f"got {c}")
    check(f"{name}: depth={exp_d}", d == exp_d, f"got {d}")
    check(f"{name}: fits {BUDGET}c budget", c <= BUDGET, f"{c}c > {BUDGET}c")

print("\n=== Reference implementations ===")
# SENSOR_UNPACK
check("threshold(5000, 1000)==1",  ref_threshold(5000, 1000) == 1)
check("threshold(500,  1000)==0",  ref_threshold(500,  1000) == 0)
check("threshold(1000, 1000)==1",  ref_threshold(1000, 1000) == 1)
check("threshold(0,    0)   ==1",  ref_threshold(0, 0)       == 1)
check("threshold(0,    1)   ==0",  ref_threshold(0, 1)       == 0)
# SENSOR_DELTA
check("delta(100, 80)  == +20",   ref_delta(100, 80)   == 20)
check("delta(80,  100) == -20",   ref_delta(80,  100)  == -20)
check("delta(100, 100) == 0",     ref_delta(100, 100)  == 0)
check("delta(0, 65535) == +1",    ref_delta(0, 65535)  == 1)
# SENSOR_STACK_MAX
check("stack_max(100, 200)==200", ref_stack_max(100, 200) == 200)
check("stack_max(200, 100)==200", ref_stack_max(200, 100) == 200)
check("stack_max(0,   0)  ==0",   ref_stack_max(0, 0)     == 0)
# SENSOR_STACK_SUM
check("stack_sum(100, 200)==300", ref_stack_sum(100, 200) == 300)
check("stack_sum(65535, 1)==65536", ref_stack_sum(65535, 1) == 65536)

print("\n=== Sensor stack demos ===")
results = run_sensor_demo()
check("touch: peak pressure == 31000",  results['touch']['peak'] == 31000)
check("touch: 2 contacts detected",     results['touch']['contacts'] == 2)
check("touch: total force == 44300",    results['touch']['total'] == 44300)
check("IMU: peak axis == 32200 (az)",   results['imu']['peak'] == 32200)
check("arm: peak velocity == 200",      results['arm']['peak_velocity'] == 200)
check("arm: 6 deltas computed",         len(results['arm']['deltas']) == 6)
check("arm: joint 3 is still (delta=0)", results['arm']['deltas'][3] == 0)

print(f"\n{'='*55}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
