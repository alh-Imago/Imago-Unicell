# Session Log — 2026-06-13 (collide tile + LIF cluster + FlowTrix demo + cost)

## Final commit: cfb59d3
## Suites: 238/238 fp_tiles (+MIF_MUX), 157/157 compiler_int32, 31/31 silicon,
##         27/27 flowtrix, 11/11 flowtrix_collide, 17/17 flowtrix_cylinder,
##         28/28 neurotrix_lif, 14/14 neurotrix_lif_mif, 14/14 mif_mux,
##         21/21 -> 29/29 walker, 14/14 community_raw (NEW)
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

## MIF_MUX tile + LIF reset fix (fp_tiles.py) — DONE
Built the missing MIF_MUX primitive: 64-bit 2:1 mux on a full MIF pair
(ctrl+mant), sel ? A : B. The correct primitive for conditional select on MIF
data (LIF reset, LBM boundary selects, masked updates) — INT32_MUX covers
only 32 of 64 bits, so using it on a MIF value silently muxes HALF the value.
That was a real (latent) bug in the LIF cluster's reset.

- Shared NOT(sel) across all 64 bits (barrel-shifter trick): 193 cells vs 256
  naive (saves 63/instance). Depth 3. Registered in builders + TIER table.
- LIF cluster reset(mux)+refractory(clamp) now use MIF_MUX. Cells 8,901 ->
  8,966; predicted ticks UNCHANGED at 353 (both muxes depth 3) — pure
  correctness fix, all 200 correctness ticks still match ground truth.
- Tests: tests/vm/test_mif_mux.py 14/14. fp_tiles 236 -> 238 (no regression).

### Debugging note (root cause worth remembering)
First cut returned B for BOTH selector values. Not the logic, not the shared-
nsel, not width: the Tile was missing preload_map. MUX2 emits preloaded-A AND
gates; run_tile cannot evaluate them without the map. make_int32_mux threads
preload_map=getattr(bld,'preload_map',{}); min/max use a different
construction that does not need it. Fix = thread the preload_map. Lesson: any
tile built from MUX2/AND_V2 must pass preload_map or it silently mis-evaluates
in run_tile.

---


- LBM reciprocal LUT optimisation (would cut collide ~46%: 2542 -> ~1542).
- MIF_MIN/MAX could adopt the shared-NOT(sel) pair-mux (~63 cells each);
  trivial now MIF_MUX exists. Optional/low-value.
- Anchor-first DSP placement: design in PLAN, not yet implemented.
- ONE PARKED ITEM (user deferred — to be named next session).
- NEXT SESSION (PLAN.md "NEXT SESSION" section):
  (1) per-tile .icm examples — DONE this session via examples/walker/
      walk_tiles.py (walker ships the tool; functional set, handlers skipped,
      composer-loadable .icm, bulk git-ignored, 4 committed samples). 21/21.
  (2) DONE (cfb59d3): community/ now exchanges NON-Trix models. Added a
      contribution "kind"; raw-model needs no format.py/domain/bridges, just
      models/*.icm validated by validate_icm (schema + record_hash recomputed
      with the SAME canonR the walker writes). cmd_new --kind raw-model
      scaffolds it. kind optional -> existing 7 trix contributions unchanged.
- WALKER FOLLOW-UPS — DONE (d370493):
  (A) --module FILE walks a whole user builder library (one fp_tiles-style .py
      in, a set of hashed .icm out). example_user_models.py is the pattern +
      fixture. (B) record_hash AT THE BASE — every .icm carries a SHA-256
      matching the composer canonR exactly ({gs,in,init,out}, no whitespace);
      strict loader accepts, composer verifies clean. walker test 21->29.

THE TWO-ROUTE AUTHORING PICTURE IS NOW REAL END TO END: hand-craft tiles with
NORBuilder -> walker -> hashed .icm -> raw-model community contribution. No
Trix format, no full compiler required. (Route A = compiler for full programs;
Route B = builder + walker for models/libraries.)

## Hardware (unchanged — gated)
Arria 10 GX660. USB Blaster V2 + JST SH 1.0mm paid 26th. First test on
arrival: jtagconfig -> IDCODE on the 660. FlowTrix/LIF predicted-tick figures
above become the first predicted-vs-measured checks once it runs.

---

## Continuation — 2026-06-13 (paper positioning + PsychTrix sketch + reciprocal LUT)

### Commits since cfb59d3
- a1e316a  paper: expand §8 Related Work into a grounded positioning section
- 1b21b3f  paper: expand Discussion (§9) and Future Work (§10)
- a49e3ea  sketches: PsychTrix fuzzy meta-hub (FMH) data-structure sketch (+Grok guard)
- (this)   fp_tiles: expose MIF_RECIP; apply to LBM collide; examine other models

### Reciprocal LUT optimisation (the doable-now lever, now done)
- Exposed the previously-private LUT-NR reciprocal as first-class **MIF_RECIP**
  (builder + _TILE_TIERS + MIF valid_tiles). Depth ~349 vs MIF_DIV ~1177
  (3.4x shallower) at ~15.3k cells vs ~4.8k — a depth-for-cells trade.
- Swapped the LBM collide 1/rho stage MIF_DIV -> MIF_RECIP:
  collide critical path **2,542 -> 1,714 ticks (~33% off)**, numeric match vs
  FlowTrix_D2Q9.collide unchanged (max abs err 2.2e-16). Equilibrium is now the
  dominant stage, not division.
- flowtrix_cost.py restructured: COLLIDE_TICKS now the optimised figure;
  COLLIDE_TICKS_BASELINE=2542 kept for provenance/auditability. Removed the now-
  realised COLLIDE_TICKS_OPT projection.
- Honesty: MIF_RECIP is a structural/cost tile at the MIF family's level (depth+
  cells modelled; numeric reference in float). NR mantissa path not run_tile-
  validated — same status as MIF_DIV, flagged in the tile notes.

### Examination — other models that could benefit
- **boids**: dx/dist, dy/dist share 1/dist -> clean reciprocal-reuse, MIF_RECIP
  applies (DIV 1177 -> RECIP+MUL ~438). BUT MIF_SQRT (1177) sits beside it and
  becomes dominant -> the *real* lever is a fused reciprocal-sqrt.
- **n-body**: mass*mass/r3 (f reused for fx,fy) and force/mass (1/mass reused
  x,y) -> MIF_RECIP applies; same MIF_SQRT-dominates caveat.
- **PageRank**: PR[j]/deg[j] — deg is a FIXED graph property, so 1/deg is a
  *constant*; strongest lever is precompute/const_divisor, beating per-iteration
  RECIP. MIF_RECIP helps only if not precomputed.
- **NeuroTrix LIF**: division-free, no benefit (confirmed).
- NEXT LEVER (recommended, not built): **MIF_RSQRT** (1/sqrt via LUT-NR) would
  collapse sqrt+div in the geometric models (boids, n-body) — bigger win there
  than MIF_RECIP alone.

### Suites (this session)
- 240/240 fp_tiles, 16/16 mif_recip (NEW), 240/240 mif_mux, 27/27 flowtrix,
  13/13 flowtrix_collide, 18/18 flowtrix_cylinder. Division models smoke-OK.
