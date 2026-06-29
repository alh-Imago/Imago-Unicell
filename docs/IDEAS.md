# Forward Projects & Framings — park here, act AFTER the core is complete

Captured from design sessions. These are NOT current work. The core comes first
(methodology set complete + silicon-proven, then Python shrunk to load-and-run against
the final field set). Each item below is gated on that. Writing them down so they're not
lost — and so they're not started prematurely and made to starve the core.

## FORWARD PROJECT: HLL-to-FPGA compiler (community on-ramp) — SEPARATE PROJECT, post-core

What: retarget the EXISTING compiler front-end (program -> logic graph; the expensive,
already-built part) with a new BACK-END that emits an FPGA circuit DIRECTLY instead of a
cell topology. High-level language -> silicon, "load and try", skipping the brutal
hand-Verilog / timing-closure gauntlet.

Why it's nearly free: the hard part (language -> logic) is done for the cell target. A
direct-to-FPGA back-end is a back-end swap, not a new compiler. Alan already has most of
the tooling.

Strategic value — the "onion compactor" playbook: a tool that is IMMEDIATELY USEFUL ON ITS
OWN TERMS becomes the doorway through which people discover the deeper thing. The FPGA
community has a real, felt pain (the toolchain is brutal; HLL->circuit is underserved). Give
them a tool they want for its own sake, no UniCell buy-in required; in using it they
encounter the substrate concept as a side effect of utility. Released FREE, the community
would jump on it. Exposure-by-usefulness compounds; exposure-by-pitch does not.

GATING (important): it is an ENTIRE SEPARATE PROJECT, a forward project, started ONLY after
the core is established and complete. Reasons:
- A community tool is an ongoing COMMITMENT (docs, packaging, support, issues, releases) —
  it can quietly become a second job and starve the core. The substrate is mid-bring-up.
- The back-end retarget is cheap ONLY once the compiler is settled against a PROVEN substrate;
  doing it against a moving target builds the spin-off on sand.
- The doorway is only worth opening if the thing behind it is FINISHED and demonstrable
  (shift+mask on die DONE; packed adder + FlowTrix demo to come). The offshoot's pull is
  bounded by how impressive the thing it exposes is. Finish the core -> the doorway delivers
  people to something real.
NOTE: this is NOT "compile to the LUT surface to replace the substrate" — that surrenders
load-and-run (back to synthesise-and-reflash per program) and would be a worse path to the
thing the UniCell exists to escape. It is a STANDALONE accessibility tool that happens to
share the front-end.

## FRAMING: the substrate as a SPATIAL DATAFLOW machine (positioning, not a task)

The UniCell is NOT a fast processor; it is a spatial dataflow fabric. The whole program is
RESIDENT in space simultaneously, every cell live at once, data flows through the standing
structure. Therefore CLOCK SPEED is largely irrelevant to throughput: once the pipe is full,
ONE RESULT PER TICK regardless of program depth, because depth is SPATIAL and therefore free.
A CPU re-fetches/re-executes every instruction for every datum (fast but narrow); the fabric
IS the program standing still while only data moves. For STREAMING workloads a "slow" spatial
machine can out-THROUGHPUT a GHz CPU — it competes on a different axis (throughput-per-result
on a continuous stream), and wins MORE the deeper/more-complex the program. The "1 Hz complex
program eating a constant data stream, one result per tick" is the regime the architecture is
BEST at, not a degraded mode. (This is the FlowTrix LBM intuition: whole stencil resident,
lattice streams through.) DSP/hybrid helps by collapsing deep slow arithmetic stages into
shallow fast ones — raising per-tick work without raising the clock.
One-line positioning: "not a fast processor — a spatial dataflow fabric where depth is free
and throughput beats clock-rate on streaming workloads."

## FRAMING: fabric-on-a-fabric, one abstraction level UP from the FPGA

The FPGA configures at the GATE/ROUTING level (LUT + routing matrix), built ONCE and FROZEN
for the run — you are a circuit-builder. The UniCell keeps its structure FIXED and uniform
and configures TOPOLOGY + METHODOLOGY as DATA, re-targetable LIVE — you are a topology-loader.
The trade: spend FPGA density (~510 ALMs per cell, hundreds of LUTs) to buy LOAD-AND-RUN
reconfiguration without a recompile (ms streaming an .icm vs minutes-to-hours of
synth/place/route/reflash). The slow circuit-building happens ONCE when the cell substrate is
placed; everything after is loading graphs into a running fabric.
One-line positioning: "a runtime-reconfigurable graph fabric hosted on a gate-reconfigurable
circuit fabric."

## FAR-HORIZON (many years out; noted, not planned)
- Die-level DSP separation: on a future full custom CARD, keep CELL dies 100% pure NOR and
  intermix separate DSP dies (e.g. ~1 in 5) — purity at the die, heterogeneity at the card,
  mix ratio a packaging decision not a silicon respin. Two clean die types, not one
  compromised die. Made SAFE by the dual-reference .icm (fabric fallback always exists).
  Gated on cage profiling showing arithmetic is the real bottleneck — a MEASURED workload
  specialisation, never a default, never at the cost of the pure substrate existing as a
  product.
