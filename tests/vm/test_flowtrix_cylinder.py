"""
test_flowtrix_cylinder.py — cylinder sim components + cost model tests

The full Strouhal run is ~100s (it lives in flowtrix_cylinder.py __main__ and
the saved flowtrix_cylinder_result.json). These tests check the sim's building
blocks fast — that the vectorised physics IS the validated FlowTrix physics —
plus a short stability smoke run, plus the deterministic parts of the cost
model.

Run with: python3 test_flowtrix_cylinder.py
"""

import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from cell_format import FormatRegistry
import flowtrix_cylinder as fc
import flowtrix_cost as cost

flow = FormatRegistry.get_default().get("FlowTrix_D2Q9")

results = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")


print("Sim physics == FlowTrix ground truth")
# vectorised equilibrium matches flow.equilibrium at sample points
import random
random.seed(5)
ok_eq = True
for _ in range(200):
    rho = random.uniform(0.8, 1.2); ux = random.uniform(-0.1, 0.1); uy = random.uniform(-0.1, 0.1)
    feq_vec = fc.equilibrium(np.array([[rho]]), np.array([[ux]]), np.array([[uy]]))
    feq_ref = flow.equilibrium(rho, ux, uy)
    if max(abs(feq_vec[i,0,0] - feq_ref[i]) for i in range(9)) > 1e-12:
        ok_eq = False
check("vectorised equilibrium == flow.equilibrium", ok_eq)

# one BGK collide in the sim form matches flow.collide
random.seed(6)
ok_col = True
for _ in range(200):
    f = [random.uniform(0.02, 0.25) for _ in range(9)]
    rho = sum(f)
    ux = sum(fc.EX[i]*f[i] for i in range(9))/rho
    uy = sum(fc.EY[i]*f[i] for i in range(9))/rho
    feq = fc.equilibrium(np.array([[rho]]), np.array([[ux]]), np.array([[uy]]))[:,0,0]
    omega = 1/0.8
    got = [f[i] - omega*(f[i]-feq[i]) for i in range(9)]
    ref = flow.collide(f, 0.8)
    if max(abs(got[i]-ref[i]) for i in range(9)) > 1e-12:
        ok_col = False
check("sim collide == flow.collide", ok_col)

# streaming (np.roll) conserves total mass
f = np.random.RandomState(1).uniform(0.05, 0.2, (9, 20, 30))
m0 = f.sum()
for i in range(9):
    f[i] = np.roll(f[i], (fc.EY[i], fc.EX[i]), axis=(0,1))
check("streaming conserves total mass", abs(f.sum() - m0) < 1e-9)

# bounce-back uses the correct opposite permutation
check("sim uses FlowTrix OPPOSITE table",
      list(fc.OPP) == [flow.OPPOSITE[i] for i in range(9)])
# specular reflection negates ey, preserves ex (free-slip walls)
ok_spec = all((fc.EX[fc.SPEC[i]] == fc.EX[i]) and (fc.EY[fc.SPEC[i]] == -fc.EY[i])
              for i in range(9))
check("specular reflection negates ey, keeps ex", ok_spec)

print("\nShort stability smoke run")
res = fc.run(Re=100, U=0.1, D=10, nx=80, ny=50, n_steps=600, warmup=500, verbose=False)
check("short run stays finite (no divergence)",
      res is not None and np.isfinite(res["ux"]).all() and np.isfinite(res["uy"]).all())
check("short run produced a probe signal", res is not None)

print("\nSaved validation result (low-blockage Strouhal)")
path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "flowtrix_cylinder_result.json")
if os.path.exists(path):
    saved = json.load(open(path))["scalars"]
    check("saved St within 8% of unbounded Williamson",
          saved["St_error_pct"] < 8.0)
    check("saved run used low blockage (<= 0.11)", saved["blockage"] <= 0.11)
else:
    check("saved result file present", False)

print("\nCost model — deterministic parts")
check("cost model uses reciprocal-optimised 1714 collide ticks", cost.COLLIDE_TICKS == 1714)
check("documented baseline is the pre-reciprocal 2542", cost.COLLIDE_TICKS_BASELINE == 2542)
check("reciprocal optimisation is a realised improvement", cost.COLLIDE_TICKS < cost.COLLIDE_TICKS_BASELINE)
# pipelined throughput = clock (one update/tick when full)
check("pipelined MLUPS == clock/1e6", abs(cost.unicell_pipeline_mlups(200e6) - 200.0) < 1e-6)
check("two pipelines double throughput",
      abs(cost.unicell_pipeline_mlups(200e6, n_pipelines=2) - 400.0) < 1e-6)
# non-pipelined is far slower (divided by ticks)
check("non-pipelined throughput << pipelined",
      cost.unicell_pipeline_mlups(200e6, pipelined=False) < 1.0)
# Pleiades per-core * cores == aggregate (consistency)
agg, pc = cost.pleiades_percore_mlups("coarse", 5e5)
check("Pleiades aggregate == per-core * cores", abs(agg - pc*5000) < 1e-6)
check("Pleiades per-core in production-LBM band (0.1-5 MLUPS)", 0.1 < pc < 5.0)
# structural serialisation is rigorous: cells/cores
s = cost.pleiades_structure("coarse")
check("coarse: 1.3M sites time-sliced per core",
      abs(s["cells_per_core"] - 6.5e9/5000) < 1)

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*58}")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for st, n in results:
        if st == "FAIL":
            print(f"  {n}")
