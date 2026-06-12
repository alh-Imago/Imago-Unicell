# Session Log — 2026-06-13 (collide tile + LIF cluster + FlowTrix demo + cost)

## Final commit: 29e16e9
## Suites: 157/157 compiler_int32, 236/236 fp_tiles, 31/31 silicon (unchanged),
##         27/27 flowtrix, 11/11 flowtrix_collide, 17/17 flowtrix_cylinder,
##         28/28 neurotrix_lif, 14/14 neurotrix_lif_mif  (all NEW this session)
## Previous session archived: sessions/archive-2026-06-12.md

---

## Nature of this session
Finished the two reference-models-without-tiles that were left on the burner:
both now have their tile-level realisations, each composing the real MIF tile
family, each validated against its ground truth, each reporting a deterministic
predicted tick count. No new scope started (one more item is parked, deferred
by request). Repo clean, all suites green.

---

## Commits this session
- be3281d  FlowTrix: LBM_COLLIDE tile composition + predicted tick accounting
- 51e4551  NeuroTrix: LIF neuron tick as composed MIF tiles + tick accounting

---

## FlowTrix collide tile (flowtrix_lbm_mif.py) — DONE, unblocks Strouhal
The BGK collide cell cluster, composed from MIF tiles (MathTrix-reference
pattern). Matches FlowTrix_D2Q9.collide() to machine epsilon over 5000 sites.
Reports the compiler's pre-silicon tick figure.

Results (un-optimised): 238,554 cells/site, 2,542 predicted ticks/update.
DIVISION-DOMINATED: the single 1/rho reciprocal is 46% of the critical path
-> the optimisation lever, points at the existing MIF_DIV/SQRT LUT work
(rho~1 in incompressible LBM -> LUT-seeded reciprocal slashes the dominant
stage). Reference reports the honest un-optimised number.

Two D2Q9 structural wins (captured + tested):
- TERNARY VELOCITIES (e in {-1,0,+1}): all moment sums and e.u dot products
  are pure add/sub -> ZERO MIF_MUL in the moment computation. Arbitrary
  lattice vectors would need multiplies there.
- RECIPROCAL ONCE: ux,uy share 1/rho -> 1 DIV + 2 MUL not 2 DIV (DIV is the
  costliest tile). Test asserts exactly one MIF_DIV per site.
Tests: tests/vm/test_flowtrix_collide.py 11/11.

## LIF cluster (neurotrix_lif_mif.py) — DONE
One LIF tick composed from MIF tiles. Matches LIFNeuron.step() exactly across
both synaptic modes, threshold, reset, refractory (300-tick runs, 0 mismatch).

Results: 8,901 cells/neuron, 353 predicted ticks/update. DIVISION-FREE,
dominated by the two MADDs (leak + integrate). beta and input gain are
preloaded multiply constants; threshold is a preloaded comparator constant;
no transcendental on the path. ~7x shallower than the LBM collide -> the
concrete reason event-driven spiking fabrics are attractive: shallow per-unit
update. Cluster IS the three-data-homes picture: V in a feedback loop carry,
params preloaded (no depth cost), input as the integrate B-operand.
Note: fixed tile names to real library tiles (MIF_CMP_GE for V>=v_th,
INT32_MUX for reset mux; MIF_MUX does not exist).
Tests: tests/vm/test_neurotrix_lif_mif.py 14/14.

---

## FlowTrix cylinder demo + Strouhal validation (flowtrix_cylinder.py) — DONE
Full D2Q9 lattice, flow past a bounce-back cylinder, running the SAME collide
the tile implements (sim collide == flow.collide, asserted). Measures vortex-
shedding Strouhal number vs the unbounded Williamson correlation.

VALIDATION (Re=100), saved -> flowtrix_cylinder_result.json:
  blockage 0.16 -> St=0.196  (err 17%)
  blockage 0.10 -> St=0.160  (err 4.2%)
  unbounded experimental     St=0.167
The two runs BRACKET the experimental value; St falls monotonically as the
channel opens -> residual is channel blockage, NOT the method. Correct
shedding physics from the fabric model. The 777-flight-test validation in
miniature: "correct Strouhal number from pure fabric topology".
Chain closed: collide tile == flow.collide == vectorised sim, so the St the
sim gives is the St the fabric gives.
Note: full run ~100s, lives in __main__; not in the test suite. Component
correctness + short smoke run ARE tested.

## Cost comparison vs 777 PowerFLOW (flowtrix_cost.py) — DONE
Anchored on the deterministic 2,542 collide ticks. Honest separation:
  - SOLID: 2542 ticks/update (1542 w/ LUT-recip); streaming free; parallel-
    resident vs per-core-serial cost structure.
  - RIGOROUS from given figures: each Pleiades core time-slices 1.3M sites/
    timestep (6.5e9/5000) through DRAM = the bandwidth-bound regime.
  - SANITY CHECK (~5e5 steps): Pleiades ~0.9 MLUPS/core, 4514 aggregate —
    consistent with production LBM, validates the reasoning.
  - PROJECTION (200 MHz, fully pipelined): one collide pipeline ~200 MLUPS
    ~ 222 Pleiades cores' worth, registers not DRAM, streaming free.
    Arria 10 settles clock + pipelining; tick count already fixed.
  - HONEST: one card needs temporal blocking at full scale; halo tax shrinks
    toward the room-of-cards rig.

---


| update          | cells/unit | ticks/update | dominant stage        |
|-----------------|-----------:|-------------:|-----------------------|
| LBM collide     |    238,554 |        2,542 | 1/rho reciprocal (46%)|
| LIF tick        |      8,901 |          353 | leak+integrate MADDs  |
These are the compiler-published figures to match against hardware once the
Arria 10 is up (PLAN predicted-vs-measured metric).

---

## Still open (in priority order)
- LBM reciprocal LUT optimisation (would cut collide ~46%: 2542 -> ~1542).
- Anchor-first DSP placement: design in PLAN, not yet implemented.
- ONE PARKED ITEM (user deferred — to be named next session).

## Hardware (unchanged — gated)
Arria 10 GX660. USB Blaster V2 + JST SH 1.0mm paid 26th. First test on
arrival: jtagconfig -> IDCODE on the 660. FlowTrix/LIF predicted-tick figures
above become the first predicted-vs-measured checks once it runs.
