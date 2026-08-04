# Island-hierarchy interconnect: contention-free by recursive local isolation (PONDER → DESIGN)

Derived by following the bus-contention problem honestly to the bottom. NOT YET BUILT. Resolves
"shared-bus contention kills scaling" not by eliminating contention but by BOUNDING it to small
local islands and recursing.

## The problem it solves
A single shared wired-OR bus tolerates exactly ONE emission per cycle — two cells firing the same
cycle collide (data OR-merges, addresses clash). A parallel fabric's whole point is many cells
firing at once, so the shared bus is fundamentally contention-limited. Latent while tests were
narrow chains (a chain fires one cell/cycle -> no contention AT ANY LENGTH); the wide adder
prefix stages expose it. Cheap fixes DON'T solve it: address gating filters the RECEIVER (solves
address-collision, not contention — data still on the wire); wall cells isolate but cost per-
PERIMETER (a chain is worst-case: ~perimeter >> cells) and still don't unshare the medium.
CONCLUSION: contention is a property of the shared MEDIUM; only NOT sharing the medium removes it.

## The architecture (recursive / fractal, fat-tree class)
- 4x4 = 16 cells = one ISLAND, with its OWN local bus. Contention bounded to 16-wide (tractable:
  tiny local bus, or schedule the 16).
- 4x4 islands = a GROUP; 4x4 groups = next level; ... up to full fabric. SELF-SIMILAR at every
  level.
- RULE at every level: each unit computes LOCALLY; only RESULTS pass up; the level above never
  sees internal traffic, only the passed results. => contention contained at every scale.
- ADDRESS GATING enforces the island boundary: island-aligned high bits => "is this address in MY
  island? yes -> local bus; no -> it's inter-island (goes to bridge)". ONE mechanism does both
  jobs: enforce locality AND identify bridge traffic. (16-cell island aligns to the low 4 address
  bits — the addressing structure and the island size agree, justifying 16 by TWO reasons.)
- FULL-WIDTH GLOBAL BUS RETAINED but re-roled: no longer carries compute traffic (that's local
  now) — only sparse INTER-ISLAND BRIDGE traffic. Unloaded, so no longer the bottleneck. Bridges
  are the per-island straddling elements (local-bus <-> global-bus, gated/translated).

## Time-slice = physical realisation of staggered scheduling
Earlier idea: stagger chains by cycles so outputs don't collide in time (systolic / modulo
scheduling). The island hierarchy is the SPATIAL embodiment: separate in SPACE (which local bus)
instead of TIME (which cycle). Where results DO converge (fan-in to an accumulator), stagger the
feeders by a cycle each so arrivals are sequential -> convergence stays contention-free. A CHAIN
never contends at ANY length; only SIMULTANEOUS fires (width) do -> the whole game is bounding
simultaneity, which islands (space) + staggering (time) do together.

## Honest scope — the load-bearing assumption
Contention-free AT EVERY LEVEL *iff* the model is HIERARCHICALLY LOCAL (most traffic local, only
a thin trickle crosses each boundary). The recursion RELOCATES contention to the boundary-
crossings; it wins only if crossings are SPARSE. So this is a CONTRACT WITH THE PARTITIONER: "if
you can cluster the model hierarchically-locally, I give contention-free execution at any scale."
- GREAT fit: local-stencil / neighbour-communicating models. POOR fit: densely-connected (fully-
  connected NN) — those funnel dense traffic through the crossings and still contend (hard on ANY
  interconnect). The difficulty moves from HARDWARE (interconnect) to SOFTWARE (partitioner) —
  the right place to put it.
- Latency for cross-boundary traffic grows with hierarchy depth (~log fabric size). Fine for
  pipelined throughput; a cost for latency-sensitive long-range deps. Placement (keep coupled
  cells in one island) is load-bearing — the loader's job.

## Why it's well-founded: the workloads ARE this shape
Both major target workloads are locally-connected and fit ONE unit per 16-cell island:
- LIF spiking net: cluster = 9-15 cells = one island; SPIKES (sparse, event-driven) pass up;
  ACCUMULATOR island does neural fan-in (3 LIF islands + 1 accumulator = a quad = 4 islands; 4
  quads = a 16-island group). Time-slice staggers the 3 feeders so the accumulator sees them in
  order. NB the leaky-INTEGRATOR (9-15 cell circuit) is still UNBUILT — the harder half; the
  island is a ready container awaiting the neuron.
- MIF / grid-PDE calculus (Gray-Scott, fast-marching, reaction-diffusion): 16 cells = one MIF
  unit = one island EXACTLY. Grid patches in islands; HALO exchange (sparse boundary values) is
  the inter-island traffic up the hierarchy. (~5-8 cells per grid point -> a few points per
  island; halo = the sparse crossing.)
Both are local-dense / sparse-boundary — the exact shape the hierarchy wants. Brains and PDE
solvers solved the same "can't wire everything to everything" problem the same way (local
clusters + sparse long-range + hierarchy). Arriving here by following contention is convergent
evidence it's right.

## Build order (smallest real unit first, as always)
1. TEST THE CURRENT (shared-bus) ARCHITECTURE ON THE FPGA first — the decoder + relocated auth
   are proven in SIM only; get them on silicon before new interconnect work.
2. Minimal TWO-ISLAND test: two 4x4 islands, each a local bus, address-gated, a bridge each, on a
   retained global bus. Prove: intra-island stays local; inter-island crosses ONLY via bridge;
   two islands compute simultaneously WITHOUT contending.
3. First real workload proof: a MIF/grid-stencil patch in one island + HALO exchange to a
   neighbour (regular, deterministic — cleaner first proof than LIF, which needs the integrator).
4. Then LIF: build the leaky-integrator cluster, then a quad (3 + accumulator, time-sliced fan-
   in), then replicate up the hierarchy.

## Status
PONDER -> DESIGN. Strong, internally-consistent, fits two real workloads at one-unit-per-island,
justified by multiple independent reasons (addressing alignment + workload unit size). Honest
scope: local/clusterable models only; dense models stay hard; difficulty moves to the partitioner.
Gated on: (a) current architecture proven on silicon, (b) the two-island minimal test.
