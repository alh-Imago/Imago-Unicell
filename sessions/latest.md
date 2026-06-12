# Session Log — 2026-06-13 (collide tile + LIF cluster — burner items cleared)

## Final commit: 51e4551
## Suites: 157/157 compiler_int32, 236/236 fp_tiles, 31/31 silicon (unchanged),
##         27/27 flowtrix, 11/11 flowtrix_collide (NEW),
##         28/28 neurotrix_lif, 14/14 neurotrix_lif_mif (NEW)
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

## Predicted ticks/update table (pre-silicon, un-optimised)
| update          | cells/unit | ticks/update | dominant stage        |
|-----------------|-----------:|-------------:|-----------------------|
| LBM collide     |    238,554 |        2,542 | 1/rho reciprocal (46%)|
| LIF tick        |      8,901 |          353 | leak+integrate MADDs  |
These are the compiler-published figures to match against hardware once the
Arria 10 is up (PLAN predicted-vs-measured metric).

---

## Still open (in priority order)
- FlowTrix: assemble collide + bounce-back + streaming-topology into a full
  lattice, run flow-past-cylinder, validate Strouhal number in the VM.
  (Collide tile now exists -> this is unblocked.)
- LBM reciprocal LUT optimisation (would cut collide ~46%).
- Anchor-first DSP placement: design in PLAN, not yet implemented.
- ONE PARKED ITEM (user deferred — to be named next session).

## Hardware (unchanged — gated)
Arria 10 GX660. USB Blaster V2 + JST SH 1.0mm paid 26th. First test on
arrival: jtagconfig -> IDCODE on the 660. FlowTrix/LIF predicted-tick figures
above become the first predicted-vs-measured checks once it runs.
