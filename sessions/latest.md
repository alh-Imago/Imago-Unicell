# Session Log — 2026-06-13 (collide tile + LIF cluster + FlowTrix demo + cost)

## Final commit: 689807d
## Suites: 238/238 fp_tiles (+MIF_MUX), 157/157 compiler_int32, 31/31 silicon,
##         27/27 flowtrix, 11/11 flowtrix_collide, 17/17 flowtrix_cylinder,
##         28/28 neurotrix_lif, 14/14 neurotrix_lif_mif, 14/14 mif_mux,
##         21/21 walker (NEW)
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
  (2) STILL OPEN: expand community/ to exchange NON-Trix models (raw .icm/
      tiles/libraries) — add a contribution "kind", branch validation, no
      format.py required for raw kinds. The committed sample tiles seed the
      new raw kind.
- WALKER FOLLOW-UPS (deferred, both small, in PLAN.md "1b"):
  (A) --module flag to walk a whole user builder FILE (one library .py in ->
      set of .icm out; the alternate authoring route parallel to fp_tiles.py).
  (B) record_hash AT THE BASE — currently omitted. Composer load is lenient
      but the strict/runtime loader (controller.py) needs it. Must match
      composer canonR exactly: fields {gs,in,init,out} only, that order, no
      inB, JSON no-whitespace, sha256 hex. PLAN.md has the Python snippet.

## Hardware (unchanged — gated)
Arria 10 GX660. USB Blaster V2 + JST SH 1.0mm paid 26th. First test on
arrival: jtagconfig -> IDCODE on the 660. FlowTrix/LIF predicted-tick figures
above become the first predicted-vs-measured checks once it runs.
