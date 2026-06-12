"""
test_flowtrix.py — FlowTrix D2Q9 Lattice Boltzmann Format Tests

Validates the FlowTrix_D2Q9 FormatDefinition (cell_format.py): the single-site
reference physics (equilibrium, moments, collision, bounce-back) that the
LBM_* tiles must reproduce, the lattice constants, and the FlowTrix->PhysTrix
viscosity/Reynolds bridge.

Physics invariants checked:
  - equilibrium at rest reduces to the lattice weights, sums to rho
  - moments round-trip: feq(rho,u) recovers (rho,u) exactly
  - BGK collision conserves mass and momentum (its collision invariants)
  - bounce-back is an involution; the OPPOSITE table is self-inverse
  - nu = cs2*(tau-1/2) and Re = U L / nu invert consistently
  - the format declares no LBM_STREAM tile (streaming is topology)
  - the viscosity bridge is discovered and grounded on the viscosity concept

Run with: python3 test_flowtrix.py
"""

import random
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cell_format import FormatRegistry, FlowTrix_D2Q9

results = []

def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")

def approx(a, b, eps=1e-12):
    return abs(a - b) < eps

reg  = FormatRegistry.get_default()
flow = reg.get("FlowTrix_D2Q9")

print("FlowTrix D2Q9 — registration & constants")
check("registered in default registry",
      "FlowTrix_D2Q9" in [f["name"] for f in reg.list()])
check("FlowTrix domain present", "FlowTrix" in reg.domains())
check("9 distributions declared", flow.cell_words == 9)
check("weights sum to 1",
      approx(sum(flow.WEIGHTS[i] for i in range(9)), 1.0))
check("velocity set sums to zero (isotropy)",
      sum(flow.VELOCITIES[i][0] for i in range(9)) == 0 and
      sum(flow.VELOCITIES[i][1] for i in range(9)) == 0)
check("cs2 == 1/3", approx(flow.CS2, 1/3))

print("\nStreaming is topology, not a tile")
check("no LBM_STREAM in valid_tiles",
      "LBM_STREAM" not in flow.valid_tiles)
check("LBM_COLLIDE is a valid tile",
      flow.validate_tile("LBM_COLLIDE")[0])
check("rest population f0 has zero velocity (self-loop)",
      flow.VELOCITIES[0] == (0, 0))

print("\nEquilibrium")
feq_rest = flow.equilibrium(1.0, 0.0, 0.0)
check("rest feq == lattice weights",
      all(approx(feq_rest[i], flow.WEIGHTS[i]) for i in range(9)))
check("rest feq sums to rho", approx(sum(feq_rest), 1.0))
rho, ux, uy = 1.2, 0.05, -0.03
feq = flow.equilibrium(rho, ux, uy)
r2, x2, y2 = flow.moments(feq)
check("moments round-trip recovers rho", approx(r2, rho))
check("moments round-trip recovers ux", approx(x2, ux))
check("moments round-trip recovers uy", approx(y2, uy))

print("\nCollision invariants (BGK)")
random.seed(1)
f = [random.uniform(0.05, 0.20) for _ in range(9)]
before = flow.moments(f)
fc = flow.collide(f, tau=0.8)
after = flow.moments(fc)
check("collision conserves mass (rho)", approx(before[0], after[0]))
check("collision conserves x-momentum",
      approx(before[0] * before[1], after[0] * after[1]))
check("collision conserves y-momentum",
      approx(before[0] * before[2], after[0] * after[2]))
# Collision relaxes toward equilibrium: an equilibrium state is a fixed point.
feq_state = flow.equilibrium(1.0, 0.04, 0.02)
fc_eq = flow.collide(feq_state, tau=0.8)
check("equilibrium is a collision fixed point",
      all(approx(fc_eq[i], feq_state[i]) for i in range(9)))

print("\nBounce-back (obstacle as permutation)")
check("OPPOSITE table self-inverse",
      all(flow.OPPOSITE[flow.OPPOSITE[i]] == i for i in range(9)))
check("each opposite negates its velocity vector",
      all(flow.VELOCITIES[flow.OPPOSITE[i]] ==
          (-flow.VELOCITIES[i][0], -flow.VELOCITIES[i][1]) for i in range(9)))
fb = flow.bounceback(flow.bounceback(f))
check("bounce-back is an involution",
      all(approx(fb[i], f[i], 1e-15) for i in range(9)))

print("\nViscosity / Reynolds mapping")
tau = flow.tau_for_reynolds(150.0, u_char=0.1, l_char=40.0)
re_back = flow.reynolds(0.1, 40.0, tau)
check("tau->Re round-trip exact", approx(re_back, 150.0, 1e-9))
check("nu = cs2*(tau-1/2) positive for valid tau",
      flow.viscosity_from_tau(tau) > 0)
raised = False
try:
    flow.reynolds(0.1, 40.0, 0.5)   # tau=0.5 -> nu=0 -> undefined Re
except ValueError:
    raised = True
check("tau=0.5 (nu=0) rejected", raised)

print("\nFlowTrix <-> PhysTrix bridge")
res = reg.discover_bridges("SI_Physics", "FlowTrix_D2Q9")
bridge_names = [b.name for b in res["bridges"]]
check("LBM_VISCOSITY_TAU bridge discovered",
      "LBM_VISCOSITY_TAU" in bridge_names)
check("bridge grounded on viscosity concept",
      "viscosity" in res.get("shared_concepts", []))
lbm_bridge = next((b for b in res["bridges"]
                   if b.name == "LBM_VISCOSITY_TAU"), None)
check("bridge confidence is honest 0.95 (unit-mapping caveat)",
      lbm_bridge is not None and approx(lbm_bridge.semantic_confidence, 0.95))

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*55}")
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
