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

## FORWARD PRODUCT: UniCell as a reconfigurable LOW-POWER EDGE ACCELERATOR for SoCs

The product hiding in the project. A small host (ESP32, Pi, any SoC) holds predefined models;
a mid-size FPGA card carries a STANDING UniCell substrate and acts as a load-run-reload
compute surface. Host streams an .icm (a model) -> fabric configures in MILLISECONDS -> data
flows through -> results return -> reload a different model or rerun on new data.

Why it's a real differentiator (uses exactly what was proven on silicon):
- IDLES COLD by construction. A configured-but-idle substrate sits STATIC ("if the cells are
  complete, they sit and use no resources"); between loads/bursts it's near-zero power.
  GPUs/NPUs idle HOT. A battery edge accelerator needs cold idle — this has it structurally.
- RECONFIGURATION IS THE FEATURE. It can BECOME any topology you load and swap models in ms,
  with no silicon respin. An NPU does one class fast; this does any loaded topology and changes
  its mind in milliseconds. Models are DATA.
- The whole project proved the enabling property: ms reconfiguration of a fixed substrate.

CRITICAL DISTINCTION (do not muddle): this is the UNICELL load path (stream .icm into a
standing substrate, ms), NOT the compile-to-FPGA offshoot (place-and-route + reflash, minutes).
The accelerator's magic is "fixed substrate, models as fast-loaded data". Reflashing the FPGA
per model would KILL the fast-swap that is the entire point. So this product = UniCell load
path; the HLL->FPGA tool is a separate thing.

THE HARD QUESTION (the actual product-engineering problem): PART SELECTION. Tension between
"large enough for a useful model" and "small/low-power enough for battery + SoC pairing".
- ~510 ALMs/cell. A decent starting model = ~25 cells (one zone) -> needs a part with real
  capacity but NOT an Arria-class power draw.
- iceBreaker (iCE40UP5K) = too small. Arria 10 = too power-hungry for battery.
- SWEET SPOT: a mid-size LOW-POWER FPGA balancing cell capacity (~25 cells / one zone as the
  starting target) against a battery budget, pairable with Pi / ESP32. Finding that part is
  the real work — candidates: low-power Lattice (ECP5, CrossLink-NX/Certus), small Efinix
  Trion/Titanium (notably power-efficient), low-end Gowin. Solvable; it's the decision that
  makes this a product vs a lab curiosity.

NEAR-TERM TESTABLE PIECE (same muscle as the ESP32 sensor-gateway work already noted): ESP
talks to a small FPGA card, streams data in, reads results out. Load a small model, stream
sensor data, get inference back = SensorTrix -> fabric -> result as a physical EDGE DEVICE.
A compelling first demo once the core is done; the ESP link is the bench-testable first step.

GATING: post-core, like the other forward items. The core (feature-complete proven cell ->
adder -> PCIe -> hybrid) comes first; this product reuses those proofs.
