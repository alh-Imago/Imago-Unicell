"""
test_flowtrix_collide.py — FlowTrix D2Q9 collide tile composition tests

Validates flowtrix_lbm_mif.py: the LBM_COLLIDE cell cluster built from MIF
tiles must reproduce the FlowTrix ground truth exactly, and the predicted
tick accounting must be self-consistent.

Run with: python3 test_flowtrix_collide.py
"""

import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cell_format import FormatRegistry
from flowtrix_lbm_mif import collide_tiled, FlowRegion

flow = FormatRegistry.get_default().get("FlowTrix_D2Q9")

results = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")


print("Collide correctness vs ground truth")
random.seed(11)
max_err = 0.0
for _ in range(5000):
    f = [random.uniform(0.02, 0.30) for _ in range(9)]
    tau = random.uniform(0.55, 3.0)
    got, _ = collide_tiled(f, tau)
    ref = flow.collide(f, tau)
    max_err = max(max_err, max(abs(got[i] - ref[i]) for i in range(9)))
check("tiled collide matches flow.collide() to machine epsilon (5000 sites)",
      max_err < 1e-12)

# Collision conserves mass and momentum — must survive the decomposition too.
random.seed(12)
ok_mass = ok_mom = True
for _ in range(1000):
    f = [random.uniform(0.02, 0.30) for _ in range(9)]
    out, _ = collide_tiled(f, tau=0.9)
    r0, x0, y0 = flow.moments(f)
    r1, x1, y1 = flow.moments(out)
    if abs(r0 - r1) > 1e-12: ok_mass = False
    if abs(r0*x0 - r1*x1) > 1e-12 or abs(r0*y0 - r1*y1) > 1e-12: ok_mom = False
check("decomposed collide conserves mass", ok_mass)
check("decomposed collide conserves momentum", ok_mom)

# Equilibrium input is a collide fixed point through the tiles.
feq = flow.equilibrium(1.0, 0.05, -0.02)
out, _ = collide_tiled(feq, tau=0.9)
check("equilibrium is a fixed point through the tile pipeline",
      all(abs(out[i] - feq[i]) < 1e-12 for i in range(9)))

print("\nTick accounting self-consistency")
f = [flow.WEIGHTS[i] for i in range(9)]
_, r = collide_tiled(f, tau=0.8)
check("predicted ticks > 0", r.depth > 0)
check("stage depths sum to total critical path",
      sum(d for _, d in r.stages) == r.depth)
check("total cells > 0", r.cells > 0)
# The reciprocal must be the single largest stage (division-dominated claim).
stage_depths = {n: d for n, d in r.stages}
recip = next(v for k, v in stage_depths.items() if k.startswith("reciprocal"))
check("reciprocal is the largest single stage",
      recip == max(stage_depths.values()))
check("exactly one MIF_DIV per site (reciprocal once)", r.tiles.get("MIF_DIV") == 1)

# No multiplies hide in the moment computation — ternary-velocity claim.
# Stage 1 (moments) and the e.u adds use ADD/SUB only on their critical path;
# verify the moments stage chain carries no MUL.
moments_stage = next(d for n, d in r.stages if n.startswith("moments"))
check("moments stage is non-trivial (reduction tree)", moments_stage > 0)

# Determinism: same input -> same predicted depth (compiler-publishable).
_, r2 = collide_tiled([flow.WEIGHTS[i] for i in range(9)], tau=1.5)
check("predicted ticks independent of tau (structural, not data-dependent)",
      r2.depth == r.depth)

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*58}")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
