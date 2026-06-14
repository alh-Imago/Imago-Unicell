"""
test_optitrix.py — OptiTrix PID controller tile and runner tests

Tests:
  - OptiTrix FormatDefinition registered, domain, boundary tiles, 6 valid tiles
  - Q16.16 fixed-point helpers (to_fixed, from_fixed, gain_shift)
  - Six tile costs and depths, all within 900c budget
  - Reference tile implementations (36 cases from runner)
  - PID step response: motor velocity settles within 45 ticks
  - PID cascade demo: position settled within 60 ticks
  - SensorTrix → OptiTrix bridge: sensor amount feeds OPT_ERROR

Run: python3 tests/vm/test_optitrix.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatRegistry, OptiTrix, SensorTrix
from fp_tiles import TileLibrary
from optitrix_runner import (
    PIDController, to_q, from_q,
    ref_error, ref_p_term, ref_i_acc, ref_d_term, ref_sum_pi, ref_sum_pid,
    run_validation, demo_motor_velocity, demo_cascade
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

BUDGET = 900
fmt = OptiTrix()
reg = FormatRegistry.get_default()
lib = TileLibrary()

def tile_cost(name):
    t = lib.get(name)
    return t.metadata.cell_count, t.metadata.pipeline_depth

print("\n=== OptiTrix FormatDefinition ===")
check("OptiTrix registered",          reg.get("OptiTrix") is not None)
check("domain is OptiTrix",           fmt.domain == "OptiTrix")
check("boundary_in is OPT_ERROR",     fmt.boundary_in == "OPT_ERROR")
check("boundary_out is OPT_SUM_PID",  fmt.boundary_out == "OPT_SUM_PID")
check("6 valid tiles",                len(fmt.valid_tiles) == 6)
for tile in ["OPT_ERROR","OPT_P_TERM","OPT_I_ACC",
             "OPT_D_TERM","OPT_SUM_PI","OPT_SUM_PID"]:
    check(f"valid_tiles includes {tile}", tile in fmt.valid_tiles)

print("\n=== Q16.16 fixed-point helpers ===")
for v in [0.0, 1.0, -1.0, 0.5, 100.0, -50.25, 0.0625]:
    rt = from_q(to_q(v))
    check(f"round-trip {v}", abs(rt - v) < 0.0002, f"got {rt}")

check("gain_shift(0.5) == 1",  fmt.gain_shift(0.5)  == 1)
check("gain_shift(0.25) == 2", fmt.gain_shift(0.25) == 2)
check("gain_shift(1.0) == 0",  fmt.gain_shift(1.0)  == 0)
check("gain_shift(0.125) == 3",fmt.gain_shift(0.125)== 3)

print("\n=== Tile costs and budget ===")
EXPECTED = {
    "OPT_ERROR":   (517, 12),
    "OPT_P_TERM":  ( 32,  1),
    "OPT_I_ACC":   (482, 10),
    "OPT_D_TERM":  (517, 12),
    "OPT_SUM_PI":  (482, 10),
    "OPT_SUM_PID": (482, 10),
}
total_cells = 0
for name, (exp_c, exp_d) in EXPECTED.items():
    c, d = tile_cost(name)
    check(f"{name}: cells={exp_c}", c == exp_c, f"got {c}")
    check(f"{name}: depth={exp_d}", d == exp_d, f"got {d}")
    check(f"{name}: fits {BUDGET}c", c <= BUDGET, f"{c}c > {BUDGET}c")
    total_cells += c
check(f"full pipeline total = 2512c", total_cells == 2512, f"got {total_cells}")

print("\n=== Reference tile implementations ===")
ok = run_validation()
check("run_validation() 36/36", ok)

print("\n=== PID step response (motor velocity) ===")
r1 = demo_motor_velocity()
check("motor: settled within 45 ticks",  r1['settled_tick'] is not None and r1['settled_tick'] < 45,
      f"settled at {r1['settled_tick']}")
check("motor: no overshoot (monotonic plant)", r1['max_overshoot_pct'] < 1.0,
      f"{r1['max_overshoot_pct']:.1f}%")
check("motor: final velocity > 97 RPM", r1['final_velocity'] > 97.0,
      f"{r1['final_velocity']:.2f}")

print("\n=== Cascade PID (position → velocity) ===")
r3 = demo_cascade()
check("cascade: settled within 55 ticks", r3['settled_tick'] is not None and r3['settled_tick'] < 55,
      f"settled at {r3['settled_tick']}")

print("\n=== SensorTrix → OptiTrix bridge ===")
sfmt = SensorTrix()
# Sensor word: location=0 (motor axis), amount=3200 (scaled velocity reading)
word = sfmt.pack(0, 3200)
loc, amt = sfmt.unpack(word)
check("sensor pack/unpack (loc=0, amt=3200)", (loc, amt) == (0, 3200))
# Feed amount into OPT_ERROR as measurement
sp_q   = to_q(100.0)
meas_q = to_q(amt / 100.0)   # scale: 3200 → 32.0 RPM
err_q  = ref_error(sp_q, meas_q)
check("SensorTrix amount → OPT_ERROR: error ≈ 68.0 RPM",
      abs(from_q(err_q) - 68.0) < 0.1,
      f"got {from_q(err_q):.3f}")

print(f"\n{'='*55}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
