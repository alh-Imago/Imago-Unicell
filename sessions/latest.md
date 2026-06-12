# Session Log — 2026-06-12 (FlowTrix LBM format + loader placement design)

## Final commit: e1eb39a
## Suites: 157/157 compiler_int32, 236/236 fp_tiles, 31/31 silicon (unchanged),
##         + 27/27 flowtrix (NEW)
## Previous session archived: sessions/archive-2026-06-11.md

---

## Nature of this session
Two design decisions captured to PLAN, then a real code deliverable: the
FlowTrix D2Q9 lattice-Boltzmann FormatDefinition built and tested in the VM.
This is the first concrete piece of the flagship physics demo. Back at the
desk after several jobs; Arria 10 still gated on the USB Blaster (paid 26th).

---

## Commits this session
- bd757d1  PLAN: FlowTrix LBM demo section + anchor-first DSP placement
- e1eb39a  FlowTrix: D2Q9 FormatDefinition + viscosity bridge + tests

---

## FlowTrix D2Q9 FormatDefinition (cell_format.py) — BUILT

The flagship "topology IS computation" demo, started from the algorithm side.
LBM = collide (local arithmetic) + stream (one-hop neighbour move). On the
fabric, STREAM is wiring, not an operation.

Implementation:
- Domain "FlowTrix". 9 distributions/site, Q8.24 fixed-point, 9 cells/site.
- Lattice constants preloaded (decode-table pattern, same as SI CODATA):
  WEIGHTS (4/9,1/9,1/36), VELOCITIES (D2Q9 set), OPPOSITE permutation, cs2=1/3.
- valid_tiles: COLLIDE, EQUILIBRIUM, DENSITY, VELOCITY, BOUNCEBACK, INLET,
  OUTLET, VORTICITY. DELIBERATELY NO LBM_STREAM TILE -- its absence is the
  architectural point (streaming is fabric topology).
- Single-site reference physics in Python (equilibrium / moments / collide /
  bounceback + viscosity_from_tau / reynolds / tau_for_reynolds) so the format
  self-validates and gives the eventual NOR tiles their ground truth.
- Bridge_LBM_VISCOSITY_TAU (SI_Physics -> FlowTrix): nu=cs2*(tau-1/2), Re=UL/nu.
- Added 'viscosity' to SI_Physics.produces so the bridge grounds on viscosity,
  not incidentally via velocity.

Tests: tests/vm/test_flowtrix.py, 27/27. Registered in test_suite_runner.py.
Covers constants/isotropy, streaming-is-not-a-tile, equilibrium, moments
round-trip, BGK collision invariants (mass/momentum + equilibrium fixed point),
bounce-back involution + velocity negation, Reynolds<->tau inversion, bridge
discovery + confidence.

### Insights surfaced during the build (worth keeping)
1. BOUNCE-BACK AND STREAMING ARE THE SAME TOPOLOGICAL OBJECT. OPPOSITE is the
   negation of the velocity set (test-confirmed: VEL[OPP[i]] == -VEL[i]). A
   wall cell and a fluid cell differ ONLY in which neighbour each output wire
   targets -- same 9 cells, same collide logic. Obstacle = rewiring of stream
   destinations. Strongest form of "obstacle is wiring" yet.
2. BRIDGE CONFIDENCE LOWERED 1.0 -> 0.95 (revises the earlier PLAN note). The
   identity nu=cs2*(tau-1/2) is exact (Chapman-Enskog), but the BRIDGE spans
   unit systems: physical viscosity -> lattice tau needs dx,dt, a modelling
   choice not a law. Exact part lives in-format; boundary contract is 0.95.
   This is semantic_confidence doing its actual job. (Open to overrule.)
3. PRECISION IS A LEVER ON MLUPS, NOT COSMETIC. Chose fixed-point (9 cells)
   over MIF pairs (18). Fewer cells/site -> more sites resident -> fewer
   temporal-blocking swaps -> lower halo tax -> better MLUPS/watt. State it
   deliberately in the paper.
4. STABILITY TUNING HEADS-UP. tau_for_reynolds(150, U=0.1, L=40) ~= 0.58 --
   close to the 0.5 floor (twitchy over-relaxation). For a stable shedding
   demo nudge tau into ~0.6-1.0 by lowering U or raising L. The bridge makes
   this constraint explicit before a wasted synthesis cycle.

---

## PLAN updates this session (bd757d1)
- NEW SECTION "FlowTrix Demo (LBM)": D2Q9 FormatDefinition, cylinder at
  Re~100-200 validated vs published Strouhal number, bounce-back obstacle as
  fabric config, temporal blocking (N-deep halo / N timesteps) to exceed
  physical cell count via DDR streaming. Metrics: predicted vs measured
  ticks/update, MLUPS/watt vs CPU/GPU, honest halo-recompute tax. VM build
  now; hardware MLUPS gated on Arria 10 (cross-ref in hardware-gated list).
- ANCHOR-FIRST DSP PLACEMENT (added to Hybrid section, after ALLOCATION FLOW):
  invert placement -- pin DSP-consuming tiles at known DSP columns FIRST
  (most-constrained-first, ASIC macro-floorplan principle), grow rest outward
  BFS along dataflow edges, cost = hops = ticks. Path tiles between anchors;
  collision tie-break on total-hops-added. Locality table from Quartus
  post-fit ships as .isi sidecar (seed coords, declared-not-discovered).
  Mechanism Tier 2; anchor-tight vs spread strategy Tier 3 (multi-tenant
  hotspot concern). NUMA-allocation analogy: DSP columns = NUMA nodes.
  Composes with last session's DSP resource table + max-not-sum allocator:
  the table says WHICH blocks are free, the embedding says WHICH to take.

---

## Next moves (when fresh)
- COLLIDE TILE: the NOR-network implementation of LBM_COLLIDE that must match
  flow.collide() ground truth. Wants the compiler -- a proper sitting-down
  task, not end-of-day. The single-site Python reference is ready to check
  against.
- Then: LBM_EQUILIBRIUM, moments tiles (DENSITY = OR-reduction sum,
  VELOCITY = weighted sum), bounce-back wiring.
- Strouhal validation in the VM once the tiles assemble into a lattice.
- Hardware MLUPS = one of the first Arria 10 workloads after USB Blaster.

## Hardware status (unchanged -- gated)
Arria 10 GX660: likely recoverable. USB Blaster V2 (£32) + JST SH 1.0mm (£14)
paid 26th. First test on arrival: jtagconfig -> read IDCODE on the 660.
Everything still routes to that first clean IDCODE read.
