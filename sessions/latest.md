# First BRAM loader test PASSES; caught + fixed a real top-level addressing bug (Alan/session)

tb_bram_loader_v3.v: 3 heterogeneous cells (XOR/AND/OR) loaded into a real unicell_zone64_v3
through the SAME top-level transport top_arria10_zone1_v3.v uses (mirrored, not duplicated by
luck -- this mirror is what surfaced the bug below). Behavioural BRAM (icmP records: SET_TARGET,
CMD_LOAD_AT, cycle-2 methodology pad, CMD_LOAD_DONE per cell), loader task walks it, and --
the actual point of the test -- only advances to the next cell on the REAL completion pulse
(zone.emit_count incrementing), not a fixed delay. All PASS.

BUG FOUND (and fixed in top_arria10_zone1_v3.v, not just worked around in the test): the
cpu_addr_w mux's whitelist (opcodes that read the held SET_TARGET latch instead of raw cpu_data)
listed CMD_SET_METHOD (opcode 25) for cycle 2 -- but opcode 25 has NO case match in the v3.1
cell any more; cycle 2 dispatches directly on the self-describing METH_SET_MASK/SHIFT_IN/
SHIFT_OUT/LANE opcodes (30-33) as cmd_opcode itself. Any REAL cycle-2 word therefore fell
through to cpu_data[15:0], silently clobbering bus_addr the moment a second cell's cycle-2
word was issued -- topology (cycle 1) still landed correctly, but cell1/cell2's completion
pulses fired on the STALE (cell0's) address instead. Fixed: added opcodes 30/31/32/33 to the
whitelist. Confirmed via a targeted $monitor trace before fixing (bus_addr_r visibly reverting
to 0 between cycle-1 and cycle-3 for cell 1). All 6 v3 testbenches green after the fix.

Also fixed the same test-authoring trap myself: an earlier draft used a bare CMD_NOP (opcode 0)
as the "no methodology needed" cycle-2 pad -- opcode 0 was never going to be in the address
whitelist either way (it's meant as a genuine idle/no-op, not a protocol word), so any zone-load
test that treats "no methodology" as literally opcode 0 will reproduce this bug. Real fix for
that case: use METH_SET_LANE(33) with payload 0 as the pad -- it's a genuine cycle-2 opcode, has
no side-effect enable bit, and correctly participates in target-address preservation.

NEXT (per Alan): PCI(e) model -- fast loads + data retrieval. Scope for next session: a
behavioural PCIe-DMA stand-in (host read/write tasks hitting BRAM the way real PCIe DMA would;
the real hard IP only exists in Quartus's catalog, can't be modelled in iverilog) driving the
same BRAM-as-config-source path proven here, then extending BRAM's role to the inter-zone data
buffer (2-zone model) per the original session plan.
# Fixed 3-cycle load protocol — RTL DONE + sim-proven; icmP/icmS format split (Alan)

CMD_LOAD_DONE (opcode 27, added this session) + CMD_LOAD_AT extended with an optional
bank-2 methodology slot are now the complete wire-level implementation of the "Programming
protocol FINALISED" design from earlier this session. Full canon + bit-layout resolution +
file-format split in docs/design-notes/bram_load_protocol.md.

BIT LAYOUT (resolved, no collisions): auth stays at cmd_bus[29:19] (unchanged, tested),
arm stays at cmd_bus[18] (unchanged, methodology-word-only), completion flag = cmd_bus[17]
(the already-verified-free bit, and the SAME bit the cell sets in its own emitted confirm
pulse -- one meaning throughout). Alan's literal bank1/bank2/flag/auth/complete/spare packing
would have put auth on [27:17], eating bit 18 (arm) on cycle-2's SET_METHOD word -- exactly
the auth-collision bug pattern from earlier this project. Caught before it was built.

CMD_LOAD_AT bank-2 extension: cycle 1 = topology (existing LOAD_AT payload, cmd_data[22:0])
+ optional methodology-1 via cmd_bus[16] (valid) + cmd_bus[15:8] (meth opcode) + cmd_data[30:23]
(8-bit payload -- LOAD_AT's own payload never uses this range post-boot; different offset than
CMD_SET_METHOD's slot B at [23:16], which was already fully claimed here). Only active when
!physical_mode (boot's LOAD_AT keeps [30:20] for auth; loader protocol runs post-boot, so no
collision in practice).

Two new testbenches, both PASS, all prior v3 regressions (twoslot/auth_relocate/bank) still
green -- purely additive:
- tb_v3_load_done.v: CMD_LOAD_DONE alone -- one-cycle-wide emit pulse, flag bit, opcode=NOP,
  target==push address, auth gate holds (wrong token = no emit), debug bit set.
- tb_v3_three_cycle_load.v: the FULL sequence on one cell -- boot, set push address, then
  EXACTLY 3 words (LOAD_AT+bank2-mask, SET_METHOD shift_in+shift_out, LOAD_DONE) -- topology,
  all 3 methodologies, and the completion pulse all land correctly, no other opcodes issued.

FILE FORMAT SPLIT (Alan) -- icmP (pure program: target + cycle1 + cycle2 per cell, exactly what
the loader consumes, no live state) vs icmS (save/state: cmd_latch lower+upper, watching address,
push address, A-data latch contents -- 5 fields, same order for save and restore). icmS's restore
path is icmP's 3 opcodes plus SET_INPUT_ADDR/SET_OUTPUT_ADDR/CMD_SWAP_AB (confirmed: opcode 18,
auth-gated only, NOT physical_mode-restricted, works fine in RUN state). Root+offset addressing
(ARCHITECTURE.md canon, unchanged) means icmS's "identity" field is CELL_ID-minus-model-root, not
a bare absolute ID -- keeps relocatability. The icmS-shape-reused-for-cell-move overlap Alan flagged
as "not clean" is actually the BRAM-as-universal-primitive pattern one level up: one state schema,
two transports (file vs direct cell-to-cell write) -- not a smell, as long as the two FILE KINDS
(icmP vs icmS) stay distinct.

DEFERRED (explicitly): the actual Ward move operation: next question. icmS Python read/write
tooling: format specified, not built -- next concrete build is the icmP BRAM-driven loader FSM
for one zone, then scale to two zones with BRAM as inter-zone buffer, then a PCIe sim stand-in.
# Programming protocol FINALISED (Alan) — fixed 3-cycle per cell, in-band self-confirm

Deterministic 3-cycle sequence to program each cell (cleaner than variable-length "up to 3 sets"):
  CYCLE 1: topology + methodology 1.
  CYCLE 2: methodology 2 + methodology 3 (METH_NONE=0 fills unused methodology slots).
  CYCLE 3: "I'm finished" CONFIRM marker (a completion opcode).
On CYCLE 3, the cell SETS a command-bus completion FLAG and pushes it via its PUSH-ADDRESS LATCH to
the programming counter -> write counter advances to the next cell.

Why fixed-3 is cleaner than variable: deterministic — every cell = exactly 3 cycles, cycle 3 ALWAYS
the confirm. No variable-length parsing, no "another set or terminator?" ambiguity. Capacity fits
the cell's full config (topology + up to 3 methodologies across cycles 1-2 covers mask/shift-in/
shift-out/lane). Simple cells send METH_NONE in unused slots — fixed length costs a couple no-op
cycles but buys deterministic sequencing (cheap at load-time).

COMPLETION FLAG = a COMMAND-BUS bit. VERIFIED free command-bus bits: [17], [30], [31] (THREE free,
not 2 as recalled — in our favour). Use ONE for the completion flag. KEEP IT A BUS BIT — do NOT
conflate with cmd_latch free bits ([11:19]+[52]); that bus-vs-latch mix-up is exactly what caused
today's transient-wire collision bugs. Add one COMPLETION OPCODE (plenty of the 256 codes free) to
mark cycle 3.

TWO COUNTERS (each gated on its op actually completing — same principle both directions):
- READ counter: steps BRAM addresses fetching config; advances on BRIDGE-OUT (data valid+delivered,
  latency-agnostic).
- WRITE counter: steps which cell is programmed; advances on the CYCLE-3 completion flag.
Coupling: for load-time programming, LOCK-STEPPED (fetch config -> apply 3-cycle -> cell confirms ->
advance both) is simplest, no buffer, no race. Pipelining (fetch-ahead + buffer) is a later
optimisation only if program time becomes a bottleneck.

I/O: programming path = 2 ins / 2 outs per model (config data + address, each way). Program TIME
scales with #cells x 3 cycles — load-time cost, matters for reconfigure-via-BRAM model-swap latency.
BUILD: verify in a zone-level sim that models BRAM registered read latency (bridge-out trigger
should be robust by construction; confirm).
# BRAM addressing — self-clocking read/apply pipeline, trigger on BRIDGE-OUT (Alan)

Answers the earlier "who owns address generation for a BRAM bridge" open question: the CELLS, self-
clocked. Design:

READ/FETCH pipeline (self-clocking, dataflow-native):
- Command cell PUSHES a read address into BRAM ("get this for me").
- Address-driver cell holds/STEPS the address (a second cell updates the push target).
- BRAM presents read data at its output (after its registered read latency, 1-2 cyc).
- BRIDGE cell watches the BRAM output, captures + passes the data. Its OUTPUT = the "valid and
  delivered" signal.
- COUNTER cell advances the address, TRIGGERED ON THE BRIDGE-OUT (corrected from BRAM-out).
- Next cell consumes the bridge output.

WHY trigger on BRIDGE-OUT not BRAM-OUT (the key correction): the bridge sits DOWNSTREAM of the
BRAM's registered read, so data at the bridge output has NECESSARILY already cleared the BRAM read
latency AND been delivered. Triggering there = LATENCY-AGNOSTIC: you don't need to know/match the
BRAM read latency (1 vs 2 cyc), the bridge-out only asserts AFTER it. Structurally CAN'T over-run
(no off-by-one/two), and also absorbs any latency the BRIDGE itself adds (translation/width/mask) —
the trigger is at the END of the whole read-and-translate chain, the one unambiguous "done+valid"
point. Dataflow principle: don't TIME things, WAIT for them to happen.

WRITE/PROGRAM side (config application):
- Bridge-out carries CONFIG DATA (what to write) + a second out carries the ADDRESS to write to.
- Next cells = "command out to program": take (data-as-config) + (target address) and perform the
  write. => ONE config write delivers TWO things (data + address) = "two config cycles".
- Each additional TOPOLOGY/methodology = another write pass (2nd topology -> 3rd write cycle, etc).
- So the PROGRAMMING PATH needs TWO INS / TWO OUTS per model (data+address each way).

NOTES:
- Program TIME scales with config complexity (#topologies x write cycles). Load-time cost, not
  run-time — but reprogramming a card to a new model has a load latency proportional to config
  complexity (relevant to reconfigure-via-BRAM model-swap flexibility).
- BUILD: a zone-level testbench that MODELS the BRAM registered read latency confirms the trigger
  fires on the right (data-valid) edge. Sim catches this; diagram-reasoning misses it. With the
  bridge-out trigger it should be robust by construction, but verify in sim.
# Loading efficiency (Alan) — single zone ~6%, full 16-zone card 74% (~4.6%/zone): it packs tighter loaded

Confirmed real effect (not a measurement quirk). A lone zone measures ~6%; 16 zones = 74% not 96%
(16x6). Card GAINS efficiency as loaded (~22% of card recovered vs naive extrapolation). Sources:
1. AMORTISED FIXED OVERHEAD — top wrapper, command interface, clock/reset, I/O framing, debug
   scaffolding DON'T replicate 16x. A single-zone build attributes ALL that fixed cost to one zone
   (inflating it to 6%); the full build spreads it across 16 (dropping per-zone share).
2. FITTER PACKING — full fabric lets the fitter pack ALMs tighter (an ALM holds multiple LUTs/regs;
   fuller design fills them), share common logic, optimise across zones. A lone zone leaves ALMs
   partly filled.
3. BOUNDARY EFFECTS — interior zones share boundaries; a lone zone has all edges exposed.

IMPLICATION (corrects how to reason): the TRUE marginal per-zone cost at scale is ~4.6%, NOT 6%.
Use the LOADED 4.6% for budgeting, not the single-zone 6% (which is inflated by unamortised
overhead — THIS is why the 6% cross-check mis-predicted ~12 zones). The single-zone figure is a
PESSIMISTIC estimator; the real card is ROOMIER than it implies. Good for hybrid headroom.

CAVEAT: gain is NOT unlimited — mostly amortising FIXED overhead, already ~captured at 16 zones;
diminishing returns beyond. And FMAX/routing are the real ceilings before logic runs out. Don't
extrapolate to "more zones ~free."

Strengthens hybrid: a well-loaded hybrid rebuild benefits from the same packing; hybrid cells
(smaller, math offloaded) + amortisation should land logic % comfortably below 74% for equivalent
capability.
# CORRECTION (Alan) — it IS 16 zones, not 12. My cross-check anchored on a stale 6%/zone figure.

Real: 16 zones x 25 cells = 400 cells at 74% logic (185,445 ALMs). So per-zone = 74%/16 = ~4.6%
(~11,600 ALMs/zone), NOT the 6% I used. The stale 6% is what made my arithmetic say "~12 zones" —
wrong. 16 zones confirmed.
- Per-CELL cost = ~464 ALMs (11,600/25), LOWER than the ~615 pure-cell figure we'd carried. Current
  cells are cheaper than the old estimate -> cell budget more comfortable; hybrid cell (math
  offloaded) cheaper still.
- Café spec = 16 zones/card x 8 cards = 128 models/café (the original 16-zone assumption was RIGHT;
  my "96/12-zone" reconciliation was wrong — disregard it).
- FMAX 56.2 MHz reading STANDS (that's independent of the zone-count error) — still the number to
  watch, still likely wired-OR-bus-limited, island separation still doubly motivated.

# REAL fitted figures (full card, standalone64 / top_arria10_64, 25 cells/zone, Quartus 25.1, 2026-06-28)

Measured (replaces remembered/inferred numbers):
- Logic: 185,445 / 251,680 ALMs = 74% (full card, fitter-sweet-spot; ~72.3% remembered = confirmed).
- DSP 0/1687, BRAM 0 bits, PLLs 0/64, HSSI 0/24 — all hardened silicon IDLE (hybrid spends genuinely
  free resources).
- 25 cells/zone (real; earlier "28" was off).
- ZONE COUNT: 74% / ~6%-per-zone => ~12 zones, NOT 16. Confirms the earlier cross-check (6%x16=96%
  didn't match 72%). Café/product spec should use ~12 zones/card (12x8=96 models/café, not 128).
  Confirm exact zone count from the build, but arithmetic says ~12.
- Registers 157,856; pins 5/604.

FMAX = 56.2 MHz (main clk) — THE NUMBER TO WATCH, matters MORE than logic %.
- Low for Arria 10 (fabric can do hundreds of MHz). Something has a long combinational path.
- LIKELY CULPRIT: the wired-OR bus (every cell's contribution OR'd = long comb path) — classic
  FMAX limiter in bus-based fabrics.
- This is the REAL performance ceiling + the REAL constraint (not logic %). Hybrid bridges could
  LOWER it (longer paths); island/zone-separation could RAISE it (shorter LOCAL buses).
- => the separated-zone redesign is doubly motivated: helps ROUTING (local connectivity, sparse
  bridges) AND likely helps FMAX (shorter local buses). Track FMAX across design changes, not just
  logic %.
- Caveat: 56 MHz may be intentional/fine for a demo/correctness-first design. Flagged as "the number
  that matters + worth understanding," not "broken." Determine what sets it (wired-OR vs a specific
  path) — if the bus, island separation is strongly motivated.

ACTION when pulling more figures: get FULL-card routing %, exact zone count, timing/FMAX, and
whether the build includes debug/ISSP (strip for production headroom). FMAX is the metric that
decides if architecture changes are working.
# I/O via BRAM-direct (Alan) — PCIe DMAs to BRAM, cells never handle raw lanes (eliminates I/O cells)

Long-chain / self-feed / tap pattern (confirmed feasible, verify routing in a small fit):
- Bake long cascades up to ~128 (a handful fit in ~1687 DSPs).
- SELF-FEED: chain output cascades back to its own input (accumulate path) -> a 128-chain processes
  128*N effective terms over N passes. Trades LATENCY (wait for passes) for effective depth without
  128*N physical blocks. Real space/time trade.
- TAP PARTWAY: inject operands / read results at intermediate points of a baked long cascade -> one
  baked chain serves many effective lengths (4/8/16...).
- CAVEAT: mid-chain tap + feedback routing is PLAUSIBLE from the block diagram but VERIFY in a small
  fitted test (Quartus routing/timing of intermediate taps). Concept holds; confirm the routing.

CELL BUDGET: ~448 cells/16 zones = 28/zone is a TARGET (exact number vague/forgotten, and that's
fine — the premise holds at 448 or 350 or 500, just proportionally more/fewer zones). 448 is
optimistic-edge on GX660, comfortable on GX1150. CONFIRM by fitting one HYBRID cell (smaller than
the 615-ALM pure cell because math offloads to DSP). Don't build load-bearing math on 448 unfit.

KEY SIMPLIFICATION (Alan): PCIe works with BRAM DIRECT -> ELIMINATES cells-for-card-I/O.
- Card has 24 lanes in / 24 out. The naive plan spent ~2 zones (~40 cells) turning cells into
  lane-handlers (~20 cells -> ~19 lanes, a mismatch).
- INSTEAD: PCIe HARD IP DMAs directly to/from BRAM; cells only ever touch BRAM. The fabric NEVER
  handles raw PCIe lanes — the 24-in/24-out is the PCIe IP's job, not the fabric's. No cell-per-lane,
  no lane-count mismatch, and the ~2 I/O zones return to compute/routing.
- This IS how FPGA PCIe actually works (hard block DMAs to on-chip memory) — BRAM-direct is the
  device's grain; making cells marshal lanes would fight the hardware.
- BRAM = the MEMBRANE between host world (PCIe) and fabric world (cells) — the "BRAM as universal
  contact point" principle applied to delete the I/O cells.
- COST paid in the RIGHT currency: hard PCIe IP + DMA glue logic (standard, well-trodden, Alan's
  Windows/PCIe-transport work), NOT precious compute cells. Not free, but not paid in cells.

Net: no cells on I/O; PCIe<->BRAM DMA; cells<->BRAM; freed zones -> compute. Cleaner + matches the
silicon's grain.
# Card as a SPECTRUM (Alan) — one model, many lab uses; math-heavy is one valid end

Key realisation: the DSP-array use isn't a different architecture — it's the HYBRID DIALLED to its
math-heavy end. Same card, same model, same mechanisms (cells/bridges/DSP/BRAM), different RATIO of
cell-logic to DSP-math per workload:
- PURE CELL end: all logic, demonstrates the thesis (spatial/dataflow computing).
- BALANCED hybrid: cells for topology/control, DSP for arithmetic in a dataflow computation.
- MATH-HEAVY end: cells mostly just ROUTE data to DSPs; card = a fabric-marshalled FP32 array.
ONE card spans logic-heavy -> math-heavy by CONFIGURATION, not by building different hardware.

RESOURCE LOGIC (Alan): bridge = 1 cell (32 bits). You run OUT OF CELLS before exhausting the ~1687
DSPs -> DSP array is over-provisioned relative to feeding capacity -> never waste DSPs, "half the
card for bridges" fear dissolves (bridges cheap, you stop when cells run out, long before DSPs do).
Cells = scarce resource; DSPs = effectively unlimited from the fabric's view. Cells do
translation/control, DSP does math. Clean one-sided constraint. (DSP/BRAM are hardened silicon, cost
NO ALMs — only the 1-cell bridges cost fabric.)

MATH-HEAVY USES (real, esp. for uni labs): dense linear algebra (matmul, dot products,
convolution), signal processing (FIR/IIR/FFT — DSP blocks' home turf), stencil/grid math (fluid
dynamics, PDE, reaction-diffusion), embarrassingly-parallel FP (Monte Carlo). CAVEAT (arithmetic
intensity): sustained rate is gated by FEEDING (PCIe/BRAM bandwidth), not DSP count. Fast on
HIGH-arithmetic-intensity / high-reuse work (matmul reuses operands on-chip -> DSPs stay busy);
FEED-LIMITED on low-reuse streaming (each operand used once). Compute-bound vs memory-bound is the
standard roofline line — you're on the good side for dense linear algebra.

PRODUCT STRENGTH = the SPECTRUM. One café (8 cards, ~£1k) serves parallel-computing, numerical-
methods, DSP, and computer-architecture courses from the SAME hardware by configuring the
cell:DSP ratio. Breadth-from-one-device is exactly what makes a good lab tool (limited budget/shelf).

POSITIONING (honest, de-risked):
- FLOOR: even cells-as-pure-routing gives a usable ~£1k lab FP compute cluster. The product's value
  does NOT depend on the novel part landing — the commodity baseline alone justifies the buy.
- DIFFERENTIATOR: the cell fabric (dataflow/spatial computing you can't get elsewhere at this price)
  is what makes it MORE than a commodity FP box.
- KEEP STRAIGHT: don't let the FP-cluster floor become the HEADLINE — as a pure FP cluster on 8 EOL
  cards you'd lose a throughput/tooling war vs GPUs. Lead with BREADTH + FABRIC; use the FP-cluster
  as reassuring BASELINE, not competitive claim. "Cheap approachable parallel platform, baseline =
  usable FP cluster, distinctive = teaches the cell/dataflow model." Stay out of the throughput war.
# Pond concept EXPANDED (Alan) — from single-program region to physical-card tier (generalisation, not redefinition)

The café shift GENERALISES the Pond (doesn't contradict it):
- WAS: a single PROGRAM-bounded region — one model, boundary = program isolation.
- NOW: a single CARD running MULTIPLE models, each in a zone, which MAY OR MAY NOT be connected.
  Boundary = the physical card / co-managed unit.

WHY generalisation not contradiction: the Pond was never really "one program" — it was "a bounded
region with coherent identity + a controlled boundary". Single-program was just the SIMPLEST case
(one occupant). Card-as-Pond is the GENERAL case (many zones). The single-program Pond = a Pond
with one zone; the card = a Pond with 16. Occupant-count generalised 1 -> many. Mark of a good
abstraction: the specific-case definition was secretly more general; widening CLARIFIES it. Boundary
was always essential; "one program" was incidental, now dropped.

CONTAINMENT HIERARCHY (the Pond found its natural LEVEL — the middle tier):
- ZONE  = one model (was: the whole Pond). Unit of a single computation.
- POND (card) = bounded collection of zones, may/may-not be connected. Unit of CO-LOCATED,
  CO-MANAGED computation — one card, one health domain, one PTT. The PHYSICAL-UNIT boundary.
- CAFÉ = collection of Ponds coordinated by the SBC. Unit of the CLUSTER.
Pond boundary now COINCIDES with something REAL (the card edge) not abstract (a program's extent):
it's where ward monitors health, where the PTT lives, where DSP/BRAM are shared, where the physical
edge is. Abstraction and physical reality line up.

"MAY OR MAY NOT BE CONNECTED" — proves the boundary's worth. Zones inside a card-Pond can be:
- FULLY INDEPENDENT (16 unrelated models sharing a card for physical/admin convenience) -> boundary
  provides ISOLATION.
- SELECTIVELY CONNECTED (some feed others via BRAM, some independent) -> boundary provides MANAGED
  CONNECTION (bridges control what connects).
- FULLY CONNECTED (whole card = one big model spanning zones) -> boundary provides CONTAINMENT.
The SAME boundary serves isolation OR managed-connection OR containment per how zones relate. A
boundary doing only isolation (one program) is less proven than one flexibly doing all three. The
card-Pond exercises the boundary HARDER and it holds — that's proving its worth.

WARD/PTT scope now lines up: ward watches a Pond = a card = the right health granularity (a card
fails/power-cycles/swaps as a UNIT); zones inside = the PTT entries. Abstraction meets physical
reality.

EXPANDED DEFINITION: a Pond is a bounded, co-managed region (one card) hosting one-or-more zones
(models) that may be independent / selectively-connected / fully-connected, the boundary providing
isolation / managed-connection / containment as required, and serving as the natural scope for
health (ward) and identity (PTT). Single-program Pond = the one-zone special case.
# Two-tier hardware strategy (Alan) — EOL GX660 to SEED, current GX1150 to SUSTAIN

The GX1150 at £100 (STILL CURRENT) answers the EOL supply caveat. Two tiers, two needs:

TIER 1 — GX660 EOL @ £20: cheapest demonstrator / limited lab kit.
  ~350-410 cells/card, full 8-card café ~£430-500. Absurd value, perfect to seed labs NOW and prove
  the concept. Finite supply — fine for seeding, can't reorder forever.

TIER 2 — GX1150 CURRENT @ £100: sustainable + more capable.
  ~1.75x the GX660 fabric (~1.15M LE vs 660K, more DSP/BRAM) AND a real supply chain (in
  production, reorderable). 8-card GX1150 café ~£1,050-1,100 (cards ~£800 + backplane/PSU/cage/SBC)
  — around the original "under £1k" target and REORDERABLE. Bigger fabric -> the ~448 cells/card
  target becomes EASY (likely 600-700+/card, more after DSP offload shrinks cells). £100 buys
  headroom + continuity, not just continuity.

WHY BOTH > EITHER: a product needs a cheap entry to PROVE/SEED (EOL £20) AND a sustainable version
to SUSTAIN (current £100). Lead cheap to get traction; the current tier answers "can I buy fifty?"
— the question the EOL-only story couldn't. Per-cell the EOL is still cheaper (£20/~380 vs
£100/~650); GX1150 wins on AVAILABILITY + per-card capability, which matter more for a real product
than value-per-cell.

CLEAN UPGRADE PATH (if RTL is device-portable — SHOULD be, both Arria 10, same primitives just more
of them): SAME café software/workbench/VM serve both tiers. A lab starts on cheap EOL cards,
upgrades to GX1150 by changing only the BITSTREAM TARGET, nothing else. Design targets the Arria 10
FAMILY, not one device. CONFIRM RTL portability GX660<->GX1150 (device-target change only).

Both tiers under-or-around £1k for a full 8-card café. EOL to seed, current to sustain.
# Café BOM (Alan) — real costs: full 8-card cluster ~£430-500 (EOL arbitrage)

Actual bill of materials (dominated by EOL card pricing):
- FPGA cards ~£20 each (EOL — Mustang-F100 / Arria 10 GX660 class, 251K ALM/1687 DSP/2131 BRAM
  each, dumping cheap because end-of-life). 8 cards = ~£160.
- Backplane unit (Compaq?) ~£50.
- PSU ~£50 — 1200W SERVER PSU with 16x PCIe 6-pin connectors, designed for exactly this backplane
  (mining/GPU-server-era surplus, cheap + right connectors).
- Cage ~£100.
- SBC ~£50-80 (Pi-class coordinator).
- TOTAL ~£430-500 for a COMPLETE 8-card parallel cluster. Not "under £1k as a stretch" — UNDER £500
  for the whole café. Absurd value: 8x Arria10-class FPGAs + server power + enclosure + coordinator.

THE ENABLER — EOL ARBITRAGE (honest both edges):
+ UPSIDE: serious silicon (real ALM/DSP/BRAM) at scrap prices because the market moved on (these
  were inference accelerators, superseded). The ENTIRE cost advantage rests on this, and it's real
  and legitimate. A dept buys a full 8-card parallel cluster for the price of a decent laptop —
  DISRUPTIVELY cheap for real parallel hardware. A lab that can't justify a £5k FPGA cluster easily
  justifies £450.
- CAVEAT: EOL = FINITE, unpredictable supply. Can build cafés while stock lasts; can't reorder
  indefinitely. PERFECT for a limited-run LAB KIT / demonstrator NOW (can source enough). NOT a
  sustainable supply chain for a perpetual high-volume product. Know which is pitched: brilliant
  limited-availability lab kit (honest, valuable) vs perpetual product (needs a supply answer —
  newer cheap card / custom board / accept limited run) when the EOL well dries.

PEDAGOGICAL BONUS: building real parallel hardware from cheap repurposed EOL parts is itself a
lesson (systems engineering, EOL-silicon economics, use-what's-available). Hacker-ethos platform —
approachable, repairable, demystifies the hardware. Labs like that.

Entry (1 card + SBC + minimal) = well under £200. Full café ~£430-500. Both far under £1k.
# PRODUCT direction (Alan) — university-lab parallel-computing platform, ~£1k entry

First time the project points at a CONCRETE EXTERNAL USER (uni labs) not just internal architecture
— a real milestone. Design decisions now have a customer to be honest against.

THE GAP IT FILLS: labs teaching/researching parallel/dataflow/neuromorphic computing currently face
expensive FPGA dev boards (must teach Verilog+Quartus before parallelism), GPU clusters (teach GPU
not spatial/dataflow), or sim-only. A purpose-built parallel dataflow engine with a clean
abstraction (Ponds/zones/bridges) + a workbench that SHOWS computation happening, cheap enough to
buy several = a genuine entry point. The café (cards + SBC) IS the lab: a self-contained parallel
cluster a student can hold, program, watch.

KEY SELLING POINTS:
- CELLS do logic/topology, DSP does the math — teaches the REAL lesson (control-as-topology vs
  compute-as-dedicated-units, how modern accelerators actually work). Hybrid is pedagogically
  BETTER, not a compromise.
- VM-to-card path: learn on the FREE pure-cell VM (no hardware), deploy to the card, SAME workbench
  (one interface, two views). Learn in sim -> run on real parallel hardware. THIS is the teaching-
  platform core, not just a board. Lead with it.

HONEST CAVEATS (so the pitch survives contact):
- ~448 CELLS/CARD is a TARGET, not confirmed. Real fit was ~615 ALM/cell -> ~330-410 cells on
  GX660. 448 is optimistic-end BUT the DSP offload SHRINKS cells (math leaves the fabric) -> cheaper
  cells -> more fit. So 448 is plausible BECAUSE of the hybrid — number + architecture reinforce.
  Hold as "target ~400-450, confirm by fitting the HYBRID cell", don't promise an unfit number.
- "UNDER £1k FOR WHAT?" one card+SBC vs 8-card café are very different price points. Arria10-class
  FPGA cards are not £100 items -> 8-card café under £1k is hard. Compelling entry = ONE card + SBC
  under £1k as the STARTER, scaling to a café as the dept buys more cards. Better commercial story
  (low entry, grows with the lab). Be precise which £1k.
- Software (workbench + VM + compiler) IS the value — it's what makes it approachable vs a raw FPGA
  board. Students program parallelism, not Verilog. If the software isn't easy, the price advantage
  evaporates. The VM (runs free, no hardware) is a huge pedagogical asset.

HONEST PITCH: parallel dataflow computing platform for education/research — learn on the free VM,
deploy to real FPGA hardware, watch computation in the workbench, cells do logic + DSP does math
like real accelerators. Entry ~£1k (card + SBC), scales to a café cluster. Every claim traces to
real capability. Cells/card = confirm by fitting the hybrid.
# CAFÉ MODEL (Alan) — the deployment shape: 8 cards + an SBC coordinator

Resolution of "stop making one FPGA be silicon": DON'T make one card huge and fully-interconnected
(needs silicon). COMPOSE several honest cards. The café model:
- 8 FPGA CARDS — each does COMPUTE + LOGIC: cells + DSP + BRAM used as intended, within the card's
  real limits. Each card = a POND.
- 1 SBC (Raspberry-Pi-class) ALONGSIDE — the HOST/coordinator: runs the WARD + PTT, presents to the
  workbench. Cheap, real, does the administrative job in Python at negligible cost.
Division: CARDS COMPUTE, SBC COORDINATES. Cards don't waste fabric on bookkeeping; SBC doesn't do
math (coordination point, not compute point — keep math off it or it bottlenecks).

WHY IT'S RIGHT (not a retreat):
- Plays to the FPGA's real strength (each card runs its zones/DSP/BRAM cleanly within limits)
  instead of its weakness (no dense global interconnect at scale). "Compose several possible cards"
  vs "make one impossible card" — how real systems scale anyway.
- Makes the host-side PTT/ward split CONCRETE (the SBC IS the host).
- Demonstrates the thesis STRONGER: 8 coordinated cards proves the architecture is COMPOSABLE
  ACROSS PHYSICAL UNITS via the same Pond/PTT/bridge abstractions — a stronger claim than "zones
  coexist on one chip". Abstractions hold at CLUSTER scale, not just chip scale.

SELF-SIMILAR (the pattern recurses again): inter-card comms is slower/looser than inter-zone (via
the SBC/backbone, not BRAM-fast). Same LOCALITY CONTRACT one level up: tightly-coupled work stays
WITHIN a card; only loosely-coupled RESULTS-level traffic crosses between cards. Cards are the new
islands; SBC-mediated links are the new bridges. Architecture self-similar at cluster level (good
sign).

MATURE MOVE: spent real effort trying to make one FPGA run as it would in silicon, concluded it
can't, and instead of forcing it CHANGED THE SHAPE OF THE SYSTEM to fit the hardware's real grain.
Vision survives intact, just DISTRIBUTED: 8 cards + SBC, same abstractions (Pond/PTT/ward/bridge/
BRAM-buffer/freeze-backpressure) one level up, thesis proven at cluster scale. DSP+BRAM act as they
should within each card; SBC coordinates across cards.

This is now the DEPLOYMENT TARGET the hybrid architecture builds toward.
# Emergent backpressure (Alan) — freeze propagates BACKWARDS through the fabric; self-regulating

Consequence of the freeze-watchdog: if zone C freezes (buffer full, waiting on PCIe), it stops
READING zone B's output -> B's buffer fills -> B's watchdog freezes B -> B stops reading A -> A
fills -> A freezes. The STALL PROPAGATES UPSTREAM, zone by zone, against the dataflow (data flows
downstream, backpressure flows upstream). AUTOMATIC — each watchdog watches ONLY its own output
buffer; global backpressure EMERGES from the local rule. No central scheduler. The whole pipeline
self-throttles to the speed of its slowest consumer (ultimately PCIe). This is credit-based /
systolic flow control: the data-dependency graph IS the control structure. Deepest "topology is
computation" — even flow control is topological, carried by the same buffers, NO separate control
plane.

HONEST BOUNDARY — DEADLOCK ON CYCLES: backpressure-by-freeze is safe ONLY for feed-forward (DAG)
dataflow. If there's a FEEDBACK LOOP (A->B->A), backpressure can chase itself round: A waits on B's
buffer, B waits on A's, both frozen forever = DEADLOCK. Some models HAVE cycles (LIF integrator
loops, iterative solvers, reaction-diffusion feedback).
RESOLUTION (fits the island principle): KEEP FEEDBACK LOOPS INSIDE A SINGLE ZONE (local, no
inter-zone buffer in the loop). Then inter-zone backpressure only ever crosses FEED-FORWARD (acyclic)
links -> always safe. The locality principle does double duty: keeping tightly-coupled/cyclic
computation local is good for contention AND keeps loops out of the backpressure graph (no deadlock).
Local loops, feed-forward between zones. (Alternatives if a loop MUST cross zones: buffer sized > loop
working set so it never fills; or a designated drop/overwrite point breaking the cycle.)

COMPLETE: emergent upstream backpressure (local rule -> global throttle to PCIe, no controller),
safe for DAG inter-zone flow, cycles kept zone-local to avoid deadlock. Flow control is topological
and self-regulating.
# Hybrid flow-control (Alan) — BRAM as universal primitive + freeze-watchdog backpressure (no interrupts)

THREE unifications, all on the SAME resource (dual-port BRAM) — the economy that signals a good
architecture:

1. BRAM AS UNIVERSAL BUFFER: zone<->zone handoff via true-dual-port BRAM (one writes, one reads,
   two independent ports, no arbiter/contention). ONE interaction primitive (read/write a buffer).

2. PCIe AS JUST THE HOST'S BRAM PORT: extend the same mechanism — the host is another reader/writer
   of shared BRAM. SINGLE point of contact for the whole hybrid; PCIe has no special protocol, it
   reads/writes buffers. And BRAM decouples producer rate (fast fabric) from consumer rate (slower
   PCIe) — a RATE-MATCHING buffer that absorbs the flood we projected. Fabric never waits on PCIe
   (writes local BRAM fast); PCIe drains async.

3. RECONFIGURE-VIA-BRAM: zones read their PROGRAM from BRAM -> rewriting BRAM reprograms the zone
   (stored-program flexibility, the CMD_RECONFIGURE idea data-driven through memory). Zones become
   reprogrammable-by-memory-write, not fixed-function.

BACKPRESSURE (Alan) — buffering absorbs bursts but a SUSTAINED overrun fills the buffer; need a
policy. Solution uses the COMMAND CELL structure (already have it), NO new mechanism:
- A command cell = WATCHDOG watching the output BRAM level.
- HIGH-WATER MARK (below full) -> emit CMD_FREEZE(5) to the zone. Zone halts CLEAN, state held.
- LOW-WATER MARK (above empty, hysteresis) -> emit CMD_RELEASE(6). Zone resumes.
- "Like data control, but NO INTERRUPTS" — freeze is DATAFLOW-NATIVE: not interrupt-and-handle,
  just the flow stops so the cell stops firing (nothing to fire on). Interrupts are control-flow,
  antithetical to this dataflow fabric; freeze keeps backpressure INSIDE the dataflow paradigm.
  This is the deep-right call — freeze where an interrupt would be wrong.

CRITICAL DESIGN DETAIL (where this kind of scheme usually leaks): freeze must trigger EARLY enough.
Latency: threshold-hit -> watchdog notices -> freeze reaches zone -> zone stops. Zone keeps
producing during that gap. So HIGH-WATER = full - (production_rate x freeze_latency) - safety
margin. Release at LOW-WATER for hysteresis (avoid freeze/release thrash). Get the margin wrong ->
overflow in the gap.

COMPLETE flooding story: BRAM absorbs rate-mismatch/bursts; freeze-watchdog GUARANTEES no overflow
(producer halted before buffer fills) and resumes as PCIe drains. Bursty AND sustained-overload
both graceful, no drops, no interrupts. ALL from existing primitives: BRAM + freeze/release
(silicon-proven) + command cell (watchdog). Nothing new invented — flow control falls out of the
primitives already built. True-dual-port BRAM for zone<->zone may REPLACE the earlier data-mux
backbone idea entirely (cleaner, no arbiter).
# Workbench unification (Alan) — ONE interface, a switch changes FOCUS LEVEL, both worlds

The two versions do NOT fork into two workbenches. ONE workbench, a SWITCH between whatever's
running:
- VM / pure-cell mode  -> focus at the CELL LEVEL (individual cells, topologies, logic in flow —
  the full visible mechanism, fine grain). Matches the pure-cell version's PURPOSE: legibility /
  see-the-thesis-work.
- Card / hybrid mode    -> focus at the PTT LEVEL (zones as PTT entries, health, results —
  coordinated picture, coarse grain). Matches the card version's PURPOSE: operational overview,
  not mechanism-gazing.

Same workbench, different ALTITUDE. Architecturally sound (not just UI convenience) because the
card presents as a POND and a Pond surfaces through the PTT — so card mode is the workbench doing
what it ALREADY does for any Pond (read the PTT), pointed at the card-Pond. VM mode = workbench at
cell granularity; card mode = workbench at Pond/PTT granularity. Both are NATIVE workbench views;
the switch just picks the observation resolution.

The focus-level the switch changes is NOT arbitrary — it matches what each version is FOR:
pure-cell wants you watching cells (its value = mechanism visible); card wants you watching PTT
(its reality = operational status, you don't cell-gaze a deployed card). Switch aligns observation
granularity to version purpose.

"WHICHEVER WAS STARTED": the workbench adapts to what's running — start the VM, it focuses on cells;
connect a card, it switches to PTT view. Doesn't fork into two codebases; RE-POINTS at a different
data source (VM cell-state vs card PTT) and adjusts view granularity. Mark of a well-factored
interface.

Closes the day's architecture loop: card=Pond -> Pond surfaces via PTT -> PTT host-side ->
workbench reads PTT as local resource -> ONE workbench switches focus between VM cell-view and card
PTT-view. Shared foundation (re-synced command interface) under both; two views matched to two
purposes; one tool over both worlds.
# STRUCTURAL CLARIFICATION (Alan) — two versions, a data prerequisite, and an HLL->LUT spin-off

Not scope creep — scope CLARIFICATION. Two genuinely different products were tangled under "the
system". Separating them is honest:

VERSION 1 — PURE CELLS (standalone cell system). Everything is cells: arithmetic = cell topologies,
full logic in flow, nothing external. DEMONSTRATES THE THESIS ("topology is computation") as a
complete self-contained substrate. Hosts the compiler + Tier-2 models. Optimised for CONCEPTUAL
PURITY / legibility. Natural home = the VM (no FPGA resource fight -> can show FULL math models end
to end). This is the reference/demonstrator.

VERSION 2 — HYBRID (the card unit). Cells for topology/control; arithmetic + storage OFFLOADED to
real DSP + BRAM via bridges. Optimised for EFFICIENCY / DEPLOYABILITY. Demonstrates the bridge
system connecting to real resources. This is what SHIPS.

WHY TWO not one: optimised for OPPOSITE things. Pure does math "the hard way" to prove it CAN
(showing off is the point); hybrid does it "the efficient way" because in production showing off is
waste. Different products, different purposes. Standard reference-vs-production split. Recognising
it now avoids building a muddled thing that does neither well.

PREREQUISITE for the hybrid (real dependency): ACCURATE Arria 10 DSP + BRAM capability data — DSP
block modes, multiplier widths, latencies, count; BRAM depths/widths/ports/count. Can't bridge to a
resource not characterised. Modelling the hybrid on GUESSED DSP behaviour = new drift (like the auth
drift). Data-gathering task, genuine gate before honest hybrid VM modelling.

SPIN-OFF (future direction, NOT now): HLL -> LUT compiler. Roots ARE in this system: already have a
compiler (HLL -> cell topologies), and the hybrid work FORCES accurate FPGA-primitive
characterisation (LUT/DSP/BRAM). Those are exactly the foundation stones of a LUT-targeting synthesis
flow. So it's a legitimate CONSEQUENCE, not a distraction — doing the hybrid properly builds the
substrate an HLL->LUT flow would stand on. HONEST CAUTION: HLL->LUT is a full synthesis toolchain
(compiler + place-and-route) = big project. Recognise as a future direction the current work ENABLES;
the roots are here, the tree is later. Named to keep in view without pulling focus.

Impact on build order: the VM-outward rebuild now branches — the command_interface re-sync +
pure-cell path serve BOTH versions (shared foundation); the DSP/BRAM-bridge modelling is
HYBRID-ONLY and gated on the card-capability data. Pure-cell VM demo can proceed on the shared
foundation WITHOUT waiting for card data; hybrid waits for accurate DSP/BRAM specs.
# Architecture refinement (Alan) — PTT/ward HOST-SIDE; zones bridge to DSP+BRAM (real bridge demo, no mux)

TWO decisions that lean the card lean and make the demo prove the real thesis:

1. PTT + WARD MOVE TO THE HOST (not on the card). The card just EMITS raw data (as it normally
   would); the HOST maintains the PTT tables + runs the ward system against them. Workbench
   references those host-side tables as a LOCAL resource (no round-trip to card). Rationale: card
   fabric is resource-scarce, host is resource-rich; PTT/ward is ADMINISTRATIVE work (bookkeeping,
   health-monitoring, presentation) not COMPUTE — belongs where resources are cheap. Card = compute
   + emit; host = coordinate + monitor + present. Cleaner split, frees card cells, moves complexity
   from the hard-to-debug fabric to easy-to-debug host Python.
   GOOD NEWS: ward already exists host-side (ward.py: WardStatus, Ward, make_ward(pond)) and is
   Pond-attached. So this is REPOINTING (feed it card-emitted data via PTT) not building new.

2. ZONES BRIDGE TO DSP + BRAM — the real bridge demo, NOT a contrived mux. Rather than build a mux
   backbone whose only job is shuffling data between zones (infrastructure that exists only to move
   data = waste), let each zone use the FPGA's ACTUAL resources: DSP blocks + BRAM (Arria 10 has
   1,687 DSP + 2,131 RAM blocks, ALL at 0% in the last fit — free-standing, cost no cell budget).
   The BRIDGE SYSTEM connects zone<->DSP (arithmetic) and zone<->BRAM (storage). This DEMONSTRATES
   THE BRIDGE SYSTEM DOING ITS ACTUAL JOB (bridges as connective tissue to real resources) instead
   of proving the mildly-interesting "we can move data between zones." Uses idle hardware, no wasted
   mux, no wasted cells.

NEW-TO-VM (must model before building, per VM-outward): DSP/BRAM as explicit BRIDGE TARGETS is NOT
modelled. Current VM does arithmetic as COMPOSED CELL topologies (FP32_MULTIPLIER from cells in
fp_tiles.py/model_library.py). Using a hardware DSP means a zone HANDS OFF the op to a DSP block via
a bridge — different, and far more efficient (1 DSP vs dozens of cells). Real capability shift, good
one (it's why DSPs exist), but new to model.

BUILD ORDER (this pivot, VM-outward, after the command_interface re-sync foundation):
1. command_interface.py re-sync to v3 (foundation — see v3_command_contract.md).
2. Host-side PTT + ward: repoint existing ward.py/Pond-PTT to consume card-emitted data (card =
   data source). Workbench reads host tables locally.
3. Model DSP/BRAM bridge access in the VM (new: zone bridges to DSP for arithmetic, BRAM for
   storage).
4. Card RTL: 16 zones with DSP/BRAM bridge connections, emit raw data to host over PCIe.

DECISION NEEDED (later): how a zone addresses/hands-off to a DSP vs BRAM via the bridge — the
bridge contract for a hardware resource target (vs a cell target). That is the crux of modelling
step 3.
# PIVOT + rebuild plan — VM outward, re-synced to current v3 Verilog. Card = a Pond.

STRATEGIC PIVOT (Alan): stop forcing the FPGA to do what needs silicon. The FPGA's honest role =
demonstrate the parallel thesis within the card's limits: 16 independent zones, each a self-
contained model, connected by an ARBITRATED MUX backbone (results-only routing: a model completes,
passes its result to the next process or to the user), sharing ONE PCIe channel (16 of 24 channels
used, 4-bit zone select — aligns to the island addressing). Tests the CARD's limits, not the
system's contention wall. A working 16-zone muxed demo proves parallelism convincingly.

KEY UNIFICATION (Alan): a CARD = a single POND. The workbench already reads Ponds (via the PTT).
So the card needs NO bespoke PCIe/JSON interface — it presents as a Pond: out = health data +
results (PTT entries, each zone = a bridge = a PTT entry carrying health flags stalled/spiked/
anomaly + result, serialized via to_dict() -> JSON, the existing path). in = each zone needs an
entry point (whether data comes from another zone or the user direct). PCIe is just the TRANSPORT
under the Pond abstraction.

FOUNDATION PROBLEM found: the VM is STALE vs the current v3 Verilog. command_interface.py header:
"Ground truth: unicell.v Protocol v2.3, last updated 2026-05-30" — that's the OLD cell, pre-dating
ALL the Stage-1 auth relocation + Stage-2 two-slot decoder work. It describes THREE conflicting
auth schemes (8-bit [28:21], 11-bit [14:4], 8-bit again), none matching current v3 (11-bit auth at
cmd_bus[29:19], stored cmd_latch[63:53], two-slot decoder). THIS DRIFT IS LIKELY WHY OUR FPGA TCL'S
AUTH FRAMING WAS WRONG — the VM and Verilog diverged on auth. Building anything on the stale VM just
propagates the drift.

BUILD ORDER (VM outward, current Verilog is ground truth):
1. RE-SYNC command_interface.py to unicell64_v3.v EXACTLY. Method: first extract the authoritative
   field map from the v3 Verilog (every opcode, bit position, 11-bit auth [29:19]/[63:53], two-slot
   decoder slot A[7:0]/B[15:8]/B_valid[16]/arm[18], METH_SET_MASK=30/SHIFT_IN=31/SHIFT_OUT=32/
   LANE=33) into a single verified reference, THEN rewrite to match. Reference-first, no re-drift.
   Retire: transient preload_sel[18:17]/shift_sel[20:19] (decoder replaced them). Verify field-by-
   field against the Verilog.
2. Card-as-Pond VM model: 16 zones as bridge/PTT entries, health + result, reads as a Pond via
   existing to_dict()/JSON. Prove the workbench reads it with NO new interface.
3. Arbitrated mux backbone (RTL): start 2-zone + mux (result records {zone_id,dest,data}, arbitrate,
   route to another zone OR out to Pond port), prove no contention, widen to 16.
4. PCIe as transport (Alan's Windows side) carrying the Pond PTT host<->card.

This is FRESH-SESSION work — the command re-sync is the FOUNDATION everything rebuilds on; needs a
clear head and field-by-field verification against the Verilog, not the tail of a long night.
# Principles (Alan) — two standing rules from the silicon-auth chase

1. WHEN IN DOUBT, RUN icm64_readstate.tcl FIRST (known-good baseline). It authenticates correctly,
   lands config, reads back a real latch, AND has a built-in snapshot-health check (cycle_count
   must tick). Running it isolates "build/fabric/readback fine" from "my new test is wrong" in one
   shot. Tonight it would have told us in 10 min that the build was fine and our tcl's auth framing
   was the bug. Make it the reflex: establish the baseline before chasing the specific test.

2. THE DEBUG/READBACK PATH IS A SECURITY DOOR — CLOSE IT IN PRODUCTION. The ISSP bridge +
   DEBUG_SELECT + selector-3 latch view + bank switch let an external JTAG host read internal cell
   state, INCLUDING topology (which IS the program) and potentially auth state. On a security
   product (ECU/HSM/access-control/SCADA) that is an attack surface straight through the
   root-of-trust ("topology is the root of trust" -> a port that reads topology defeats it).
   Production hardening (beyond dev's DEBUG_SELECT=1):
     - DEBUG_SELECT=0 (already the production default — no per-cell readback mux synthesised).
     - REMOVE unicell_issp_bridge entirely from production bitstreams (not just gated — absent).
     - Fuse-off / lock JTAG at the Arria 10 device level (raw JTAG is an entry point even without
       our bridge).
     - auth-write-once-at-boot must be genuinely one-shot and NEVER exposable through any port
       after boot.
   Tension resolved by BUILDING DIFFERENTLY: dev builds = observable (debug bridge + DEBUG_SELECT);
   production builds = opaque (bridge stripped, JTAG locked). The topology-is-computation model
   HELPS: no readable code memory, so once the readback door is shut there is very little left to
   extract — the device becomes genuinely opaque, which is what a root-of-trust needs.

Bonus validated result tonight: the AUTH GATE WORKS ON SILICON — wrong-token config commands were
REFUSED (that IS why our mis-framed tcl left cells unconfigured). An accidental but real negative
test of the auth refusal. For a security fabric, "refuses mis-authed config" is the property you
most need true, and it is, on the die.
# BREAKTHROUGH — build/readback/config ALL WORK. Our tcl's command framing was the bug all along.

icm64_readstate.tcl (the EXISTING working test) proved it:
- snapshot LIVE: cycle_count ticks (1262568049 -> 1264938214) => build fine, fabric clocking.
- cell-0 latch reads 0x0040002c (topology=0x02c, armed=1), input=0x0100, output=0x0001,
  armed_count=25 => a REAL configured cell, readback WORKS, config LANDS and is VISIBLE.
- So: build fine, DEBUG/selector-3 readback fine, config path fine. The 0xa0000000 from OUR tcl
  was NEVER the build or the decoder — it's OUR tcl's COMMAND FRAMING that fails to authenticate/land.

THE DIFFERENCE (our tcl vs working readstate tcl):
- Working config commands carry prefix 0x14A0xxxx: auth_token[29:19] = 0x294, on EVERY config cmd.
  BOOT_COMMIT 0x00000007/0x00A50100; SET_TARGET 0x18(=24); config ops use 0x14A00003/4/19 form.
- Our tcl used auth token 0xA5 (mword <<19) and bare opcodes. Token 0x294 (working) vs 0xA5 (ours)
  — our auth doesn't match what this silicon's boot leaves, so config is REJECTED -> cell stays
  near-empty -> 0xa0000000 = just boot side-effect bits (loopback/breakpoint), NOT our config.
- This EXACTLY matches Alan's original auth suspicion: config was being auth-rejected. Cause =
  wrong auth token / framing in our tcl, confirmed by the working tcl using a different token.

RESOLUTION (next session): rebuild our two-slot decoder silicon test on the PROVEN framing from
icm64_readstate.tcl — same BOOT_COMMIT, same SET_TARGET(0x18), same 0x14A0-style auth prefix
(token 0x294, or whatever this bitstream's boot actually stores — VERIFY by reading mask after
boot). Then issue our METH_SET_MASK/SHIFT/LANE two-slot commands WITH that correct auth token, and
read back via readstate's selector-3. The decoder should then show correctly (it's sim-proven).

NB the DECODER, AUTH RELOCATION, BANK SWITCH, DEBUG_SELECT — none were ever shown broken on
silicon. Every failure traced to observation then to OUR tcl's auth framing. No RTL change needed;
align the test tcl to the working auth framing. HUGE cycle-saver: run icm64_readstate.tcl as the
reference for what this silicon accepts.
# Note — readback STILL 0xa0000000; readback bits CONTRADICT the sent command => build isn't the one we think

Definitive finding: BOOT_COMMIT sends cmd_data=0x00A50100 -> would write one_shot=1, loopback=0,
breakpoint=0. Readback lower half 0xa0000000 = loopback=1, one_shot=0, breakpoint=1 — the OPPOSITE.
So the readback does NOT reflect the command we sent. Combined with both banks IDENTICAL, the
flashed build does NOT contain the active DEBUG_SELECT per-cell mux + bank switch, DESPITE:
  - v3 top has .DEBUG_SELECT(1) (verified in file)
  - v3 QSF now points at top_arria10_zone1_v3.v (fixed, verified)
  - tcl source word + view-select + probe extraction all verified correct

CONCLUSION: the problem is now almost certainly on the QUARTUS BUILD/FLASH side, not the RTL or
tcl. The chip does not have the debug path the files describe. Likely: (1) Quartus reused cached
synthesis / didn't fully recompile; (2) wrong project open (Unicell-Q-zone1.qsf old vs -v3);
(3) programmer flashed a STALE .sof not the fresh build.

VERIFICATION (do this rather than more RTL changes):
1. ALM COUNT CHECK: DEBUG_SELECT=1 makes the design NOTABLY BIGGER (per-cell readback mux). Compare
   this build's ALM count to the prior (~15,372). If UNCHANGED, DEBUG_SELECT did NOT take -> wrong
   project/cached build. If JUMPED, it took.
2. Confirm Quartus has the -v3 QSF open (Files pane shows unicell64_v3.v, top_arria10_zone1_v3.v).
3. Do a full clean compile (Processing > Start > Start Analysis & Synthesis after removing db/
   incremental_db, or Project > Clean), not incremental.
4. Confirm the programmer .sof path is the freshly-built output, not a cached older one.

The DECODER remains sim-proven; every silicon 'failure' has traced to the observation/build path,
never shown to be the decoder logic. Do NOT change more RTL until the build is confirmed to contain
DEBUG_SELECT (ALM jump is the tell).
# Note (Alan, take-away) — the cell is ALREADY in RUN, never reset to boot between tcl runs. LIKELY the real auth issue.

Key realisation: the silicon cell is NOT freshly booted each tcl run. It's already configured, in
RUN state (physical_mode=0) from a PRIOR run's BOOT_COMMIT, and nothing resets it — the global
authenticated array-reset (opcode 8) that reinitialises all cells to BOOT state is NEVER issued by
the tcl. Volatile SRAM holds the cell's state between runs (until power-cycle or explicit reset).

WHY THIS EXPLAINS THE FAILURE (and Alan's auth question):
- LOAD_AT's boot auth-write is gated `if (physical_mode)`. The cell is already PAST physical_mode
  (in RUN), so the 0x0A5 boot-auth write is SILENTLY SKIPPED.
- The cell keeps whatever auth mask a prior run left in it (NOT necessarily 0x0A5).
- Methodology commands carry token 0x0A5 -> mismatches the stale mask -> config REJECTED -> cell
  reads near-empty/stale (the 0xa0000000 / auth 0x500 we saw). Config genuinely not taking, exactly
  as Alan suspected — but the cause is missing RESET, not an auth-logic bug.
- SIM PASSED because the testbench asserts rst every time -> cell always in BOOT when LOAD_AT runs.
  Silicon persists state -> NOT in boot -> boot-write skipped. Classic sim/silicon divergence
  (sim resets implicitly; silicon doesn't).

FIX (first thing next session, host-side, no reflash): issue the global array-reset (opcode 8,
authenticated) at the START of the tcl to force all cells back to BOOT state before the boot
sequence. Then LOAD_AT's `if (physical_mode)` write fires, auth 0x0A5 actually stores, BOOT_COMMIT
flips to RUN with the correct mask, methodology tokens match, config takes. THEN re-check the
readback (still has the separate bank-view opcode-3 collision issue to resolve, but config taking
is the prerequisite). A behavioural test remains the cleanest final proof.

# Note — silicon readback: cycle-counter bug FIXED (readback now STABLE), but 2 open issues

Progress: rd_latch (snap with cpu_bus[2:0]=3, read probe[79:48]) fixed the churn — readback is now
STABLE (P1==P2). We were reading snap_cycle (a free-running counter) the whole time; decoder was
never in view. BUT the read now shows 0xa0000000 on BOTH banks (identical) with auth field = 0x500
not 0x0A5. Two open issues:

1. BANK SWITCH not differentiating in this path: both banks read identical 0xa0000000. The bridge
   snapshot uses cpu_bus[2:0]==3 to select the "cell-0 latch view" — but opcode 3 is also the
   cell's SET_OUTPUT_ADDR. So snapping with cpu_bus=3 may issue a spurious cell command AND/OR the
   op26 bank-set isn't preserved across the snap. The snapshot-view-select COLLIDES with a real
   cell opcode. Need to reconcile: the ISSP bridge's view selector (cpu_bus[2:0]) vs real cell
   opcodes, and ensure op26 bank state survives to the snapshot.

2. Alan's AUTH question (open): is the config actually being REJECTED on silicon (auth mismatch ->
   cell never reconfigures -> reads near-empty)? LOAD_AT(boot) writes mask 0x0A5; BOOT_COMMIT
   writes {3'b0,cmd_data[23:16]}=0x0A5; methodology token=0x0A5 -> SHOULD match (auth_token=
   cmd_bus[29:19], auth_ok=auth_boot||token==mask). Logic looks consistent, but the 0x500 readback
   is ambiguous — could be config-rejected OR readback-still-wrong (issue 1). CANNOT distinguish
   from latch readback alone.

RESOLUTION PATH: a BEHAVIOURAL test separates the two — configure via decoder, run DATA through the
cell, check the OUTPUT reflects the methodology (shift/mask). Output path (out_data, probe[79:48]
via default snap view) is already wired and doesn't need the latch-view or bank. If output shows
the config working, config succeeded regardless of latch-readback bugs. This sidesteps BOTH open
issues. Build the behavioural tcl next session.

Decoder remains SIM-PROVEN (tb_v3_twoslot 15/15). Silicon: fighting the ISSP readback path, not
(yet shown to be) the decoder. No reflash done for these — all host-side tcl so far.

# Note — bank select via OPCODE not bus bits (Alan): extend debug opcode 26

Better than spending bus bits: bank-select is an ACTION, so it belongs in an OPCODE (free until
used), keeping the 3 spare cmd_bus bits (17,30,31) free. And the pattern ALREADY EXISTS: opcode 26
(array, DEBUG_SELECT gate) reads cpu_data to pick WHICH CELL the debug port shows
(dbg_sel <= cpu_data[DBG_W-1:0]). Extend it to carry CELL + BANK: put the bank number in the upper
bits of the same data word, and mux dbg0_cmd_latch to show cmd_latch[bank*32 +: 32] of the selected
cell. One opcode, one data word, no new bus fields, no 5-file widen. Same mechanism unifies:
- DEBUG: read a bank of the 64-bit latch (closes the silicon verification gap for decoder+auth).
- SAVE: loop the bank number through the read opcode, collect each 32-bit bank (~5 banks = full
  cell state: cmd_latch 64=2, data_reg 32=1, out_buf_data/addr 64=2).
- MOVE: save-then-restore banks at the new location.
Cost note: opcode 26 path is DEBUG_SELECT-gated (dev builds, area-costly). Fine for silicon
verification NOW (dev build anyway); save/move in production would need it outside the debug gate.
Also pending: stale transient wires (preload_sel[18:17], t_shift[19:20]) still OVERLAP auth_token
[29:19] in the RTL — decoder made them redundant but the declarations remain; clean them up so
bit 17 is genuinely free and [19:20] unambiguous.

# Note — debug readback: use a BANK SWITCH (Alan), not a 64-bit widen

The 32-bit dbg_cmd_latch can't see the upper latch half (methodology [51:32], auth [63:53]).
Widening to 64-bit touches 5 files (cell/array/zone/top/ISSP probe). BETTER (Alan's call): a BANK
SWITCH — keep the 32-bit path, add a 1-bit host-settable select at the cell's dbg source:
  dbg_cmd_latch = bank ? cmd_latch[63:32] : cmd_latch[31:0];
One mux, one control bit (from a spare cmd_bus bit / debug opcode — room exists post-decoder).
tcl reads lower half, flips bank, reads upper half -> full 64-bit visible through the 32-bit
window, probe width (113) untouched, no 5-file widen. Small job next session: add the mux, route
the bank bit, update the silicon tcl to read both banks. Then behavioural OR bank-read verification
of the decoder+auth on silicon is possible.

# ════════════════════════════════════════════════════════════════════════════
# NEXT-SESSION CATCH-UP  (read this block, then the canon sections it points to)
# Last session: 2026-06-27 — addressing model reconciled + per-cell config on silicon
# ════════════════════════════════════════════════════════════════════════════

## WHERE WE ARE (one breath)
The morning's blocker — RECONFIGURE broadcasts, so heterogeneous per-cell config was
impossible — is GONE, proven on the Arria 10. A cell is now individually addressable:
target on the full-width address lane, the cell's own addr_match gates it, auth-verified.
On top of that, the whole block→die→card→128-bit addressing model got reconciled into
canon. Clean stopping point: silicon green, canon coherent, git == remote (HEAD 0db4646).

## SILICON-PROVEN (on the die today)
- CMD_LOAD_AT (opcode 23): per-cell targeted reconfigure. zone_target.tcl PASS —
  LOAD_AT cell0=XOR → latch 0x0BC; LOAD_AT cell1=AND → cell0 STILL 0x0BC (exclusion).
- TARGET LATCH in top_arria10.v: SET_TARGET (opcode 24, cells ignore it) holds the
  address lane; LOAD_AT lands on it. The ICM transport primitive. zone_target proves it.
- Regressions green on the new build: gate+chain, command-emit. Reflash was clean.

## READ THESE CANON SECTIONS FIRST (resolved this session — do NOT re-derive)
docs/ARCHITECTURE.md:
  - "Addressing & Command Authority — INVARIANT" — one comparator gates both lanes;
    target on the address lane NEVER the command word (cmd_bus-target anti-pattern is
    named + permanently rejected); auth write-once boot-only; opcodes the only post-boot
    authority. READ THIS BEFORE touching addressing / auth / targeting.
  - "Relocatable models — root + offset" — models are position-independent; offsets in
    the artifact, loader/saver do the root arithmetic, cell stays absolute. Bridge is the
    relative↔absolute seam. Save/load/move (Ward) = one offset mechanism.
  - "Cell view — 32-bit space, 16-bit local" — the partition: low16=cell_id (intra-block,
    the cell's bus), high16=block_id (the BRIDGE's field). Pond fits-in-block or
    spans-blocks via the bridge. Shore-side climb 32→40→44→128 via bridge blocks.

## NEXT (in order)
1. ICM-file streaming: loop (SET_TARGET, LOAD_AT) pairs from a file. Build it
   OFFSET-NATIVE per the relocatable-models canon (records hold offsets from a root;
   loader forms root+offset → absolute; never bake in absolute-only). Block-local 16-bit
   offsets first (adder fits a block); reserve format room to widen. This is the
   compiler↔silicon bridge — the compiler already knows each cell's addr+config.
   >> DONE (2026-06-28, sim): fpga/icm_stream.py streams (SET_TARGET, LOAD_AT) pairs,
      offset-native, transport-pluggable. Triple-verified (oracle + RTL replay + byte-match
      to zone_target.tcl) on examples/icm/xor_and_or.icm. STREAMS topology+arm only on the
      flashed bitstream; arbitrary in/out addressing needs step 1b below.
   1b. Address-targeting reflash: route load_target into cpu_addr_w for opcodes 2/3 +
      cell addr_match-gates SET_INPUT/SET_OUTPUT (mirrors CMD_LOAD_AT). Then full
      (target, topology, in, out) records stream. Spec against the INVARIANT first.
2. Packed adder as the FIRST heterogeneous ICM on silicon (the 22-cell Kogge-Stone adder
   — the thing the whole 2026-06-27 thread was aimed at). Needs per-cell addresses too
   (SET_INPUT_ADDR/SET_OUTPUT_ADDR are already targeted) — a full record is
   (target, topology, in_addr, out_addr), so several pairs per cell, not one.
3. Loose end (small, do while in the cell): bring CMD_RECONFIGURE's auth-write under the
   physical_mode gate so clause 3 of the invariant holds everywhere (CMD_LOAD_AT already
   does it; RECONFIGURE still writes auth in run mode). Sim-testable immediately.

## FILED FOR LATER (thought through, not built — see canon)
- Host-as-allocator (hosted multi-model): used/free map per model, host assigns roots —
  a bookkeeping layer ABOVE the loader. Flat-offset ICM makes it drop in.
- Pond base+offset; PCIe = "another bridge" (windowed BAR, host-physical↔fabric in Shore,
  NOT a 128-bit address carrier). When we reach the PCIe/bus work.

## DRIFT NOTE (the session tax — avoid repeating)
The cmd_bus target side-door happened because a NEW mechanism was proposed instead of
reaching for the address comparator that already existed. Discipline: before adding any
command/auth/targeting mechanism, READ the invariant FIRST and STATE which existing
mechanism the new one duplicates. The address is identity and is full-width — it never
goes in the command word. Alan sets direction; the canon now holds the shape so it
doesn't have to be re-derived from the chat.

# ════════════════════════════════════════════════════════════════════════════
# (detailed session entries below)
# ════════════════════════════════════════════════════════════════════════════

# Session Point — Two-slot decoder proven (sim); island-hierarchy interconnect designed. NEED SILICON TEST.

## Built + proven THIS session (SIM only — silicon still pending)
- STAGE 1: 11-bit auth RELOCATED to upper latch [63:53], lower [18:11] freed. tb_v3_auth_relocate.v
  all PASS (stores at new home, survives BOOT_COMMIT, right-auth applies, wrong-auth rejected).
- STAGE 2: TWO-SLOT DECODER, collapsed encoding (Alan's simplification — the two type-flags were
  overkill). Self-describing opcodes: slot A [7:0] IS the opcode (no CMD_SET_METHOD wrapper — that
  removed the slot-A/selector collision); slot B [15:8] optional 2nd methodology; ONE bit B_valid
  [16] ("decode B" — the one thing opcodes can't self-describe); arm [18] kept. Guard: topology op
  in B refused. Methodology opcodes METH_SET_MASK/SHIFT_IN/SHIFT_OUT/LANE, each writes its field
  [51:32], NEVER auth [63:53]. tb_v3_twoslot.v 15/15 PASS. Supersedes the two-flag four-state spec.
- Grounding: unicell64_v3.v CONFIRMED canonical, all features verified in LOGIC (shift/mask/lanes/
  addressing-split/push-latch/command-cell). Comments matched to logic. Per-cell targeting via
  cmd_bus[8]/[16:9] confirmed DROPPED — those bits genuinely free.

## Big architectural result: ISLAND-HIERARCHY INTERCONNECT (docs/design-notes/island_hierarchy_interconnect.md)
Followed the bus-contention problem to the bottom. Shared wired-OR tolerates ONE emission/cycle;
parallel fabric needs many -> fundamental limit. Cheap fixes (gating, wall cells) solve adjacent
problems, NOT contention (contention = shared MEDIUM; only NOT sharing it helps). ANSWER: recursive
4x4 islands (16 cells = 1 island, own local bus, contention bounded to 16-wide), address-gated to
enforce locality + identify bridge traffic (one mechanism), global bus RETAINED but re-roled to
sparse inter-island bridging only (unloaded). Recurse: islands->groups->... fat-tree. Time-slice =
spatial staggering (separate in space not cycles); stagger fan-in feeders so convergence stays
contention-free. SCOPE (honest): contention-free IFF model is hierarchically LOCAL — a contract
with the partitioner; dense-connected models stay hard (any hardware). Difficulty moves HW->SW
(partitioner), the right place. FITS both workloads at 1 unit/island: LIF cluster (9-15 cells;
spikes pass up; accumulator fan-in; integrator still UNBUILT) and MIF/grid-PDE (16 cells exactly;
halo exchange passes up). 16 justified by TWO independent reasons (address alignment + workload
unit size) = real sweet spot.

## IMMEDIATE NEXT (Alan's call): TEST CURRENT ARCHITECTURE ON THE FPGA
The decoder + relocated auth are SIM-proven only. Before ANY interconnect work, get the current v3
(two-slot decoder, 11-bit auth) onto SILICON (Arria 10 GX660). Need: silicon tcl for the two-slot
decoder + auth-relocate (mirror tb_v3_twoslot / tb_v3_auth_relocate on the die). Then the two-
island minimal interconnect test. Also still pending from before: repoint tests/QSFs to v3, archive
old chain (move not delete), wall-cell reconsidered as island-boundary (may be subsumed by address-
gating + local buses).

## Repo state
unicell64_v3.v canonical, decoder + auth proven in sim, compiles clean, repo green. Latest commits:
c224e13 (Stage 2), de89297 (Stage 1), plus this note. Design notes current: island_hierarchy_
interconnect.md (new), cmd_latch_64bit.md (collapsed encoding), cell_v3_addressing_and_auth.md,
tiled_interconnect.md.

# Session Point — STAGE 1 DONE: 11-bit auth relocated to upper latch [63:53], proven in isolation

Building the two-slot decoder in TWO isolated stages (isolate-the-variable). STAGE 1 = auth
relocation ONLY, no decoder, tested and green before Stage 2.

STAGE 1 (this point): the stored auth_mask MOVED as one contiguous 11-bit lump into the upper
methodology latch [63:53], freeing lower latch [18:11] (Alan has a reason for freeing those 8
bits, to be confirmed). Bus auth_token widened to 11-bit [29:19] (position tested clean on auth
transactions; full transient-bit retirement is Stage 2's job). Touched every auth site: read wire
(->[63:53]), three boot/reconfigure write sites (693/723/747 -> [63:53], 11-bit source
cmd_data[30:20]), the ICM debug/zeroing (dbg_cmd_latch now lower-half only; upper-half auth-zero
for ICM lands with the wall-cell ICM format work — Alan confirmed ICM format evolves there anyway).
Comments updated to match.

TEST: tb_v3_auth_relocate.v — all PASS: mask resets zero (boot-open); 11-bit 0x5A5 stores at
[63:53]; survives BOOT_COMMIT; RUN-mode RIGHT auth applies; WRONG auth rejected. Auth works from
its new home, gate intact. Isolated from the decoder.

NEXT — STAGE 2: the two-slot four-state decoder (dual opcode inputs). Replaces the CMD_SET_METHOD
placeholder (op25); reads slot A [7:0] / slot B [15:8] + flags [16][17] four states; one-function
guard; retires the transient preload_sel[18:17]/t_shift[19:20] (freeing the bus for the 11-bit
token that now overlaps them). FLAG: the array uses cmd_bus[8]/[16:9] as per-cell target
(target_en/target_addr) — slot B at [15:8] collides with that; must reconcile the array's
targeting vs slot B before/while building the decoder. Then test 4 states + guard, repoint QSFs/
tests to v3, archive old chain, wall cell, wild idea.

# Session Log — verification pass: v3 is canonical; comments grounded to logic; two-slot decoder is the next build

## What this session did (grounding, not feature work)
DRIFT had crept in (comments vs logic, file versions, intent vs implementation). Stopped feature
work and RE-GROUNDED against the tested Verilog. Key outcome: **unicell64_v3.v is confirmed the
CANONICAL cell**, and it already contains everything believed, EXCEPT the two-slot decoder.

## VERIFIED PRESENT in unicell64_v3.v (checked against logic, not comments)
- Shift in/out, 32-bit: m_in_shift_en[47], m_out_shift_en[48], m_shift_amt[46:41]; stored OR'd
  with transient (L612-613). CONFIRMED.
- Nibble-level gating (mask): m_nibble_mask[39:32], m_mask_en[40], nibble_keep (L454-458). CONFIRMED.
- Lanes AFTER the shift (drops shifted-out part): m_lane_cut[51:49], lane_kill from shift amount
  (L534-540), applied post-shift. CONFIRMED.
- ADDRESSING SPLIT (v3 core, commit 60f137b): addr_match=(bus_addr==input_address) MUTABLE LISTEN;
  config_match=(bus_addr==CELL_ID) PERMANENT IDENTITY (L559-560). Config targets CELL_ID; the in is
  just a watching point. Identity is the cell id, not the in. CONFIRMED — matches the model exactly.
- PUSH latch: output_address is the push target (default CELL_ID+1); CMD_SET_OUTPUT_ADDR sets it;
  cell emits targeted by output_address. CONFIRMED.
- COMMAND cell: is_command_cell=cmd_latch[10]; emits cmd_emit_bus FROM a_data (the in latch),
  targeted by output_address -> reconfigures other cells (L214-215,334). CONFIRMED.

## NOT yet in v3 (the agreed next build)
- The TWO-SLOT FOUR-STATE decoder. Still the placeholder CMD_SET_METHOD (op25) writing
  cmd_latch[63:32] wholesale (L735-744). The datapath it drives is proven; only the front-end
  decode is missing.
- Spec (settled, cmd_latch_64bit.md): [7:0] opcode A, [15:8] opcode B, [16] A_is_methodology,
  [17] B_to_methodology, [18] arm, [29:19] auth_token (11-bit), [31:30] spare. Four states:
  00 topology-only / 01 topology+meth(B) / 10 meth-lower8(A) / 11 meth-16bit(both). ONE-FUNCTION
  GUARD: a pass names at most one FUNCTION (topology mutually exclusive); methodologies (shift,
  mask, lanes) COMPOSE. Slot B self-describing by its opcode (no selector bit).
- AUTH DECISION (reversed to 11-bit, deliberate — a separate security discussion): auth_token
  11 bits on the bus [29:19]; stored mask = {cmd_latch[63:61], cmd_latch[18:11]} = 11 bits (3 new
  bits at the TOP of the upper latch [63:61], leaving [60:52]=9 contiguous free for future
  methodology growth below the auth bits). Upper latch used bits verified: [51:32] methodology;
  [63:52] free (12).

## Comments updated (this session, comments-only, compiles clean)
unicell64_v3.v header: RUN-state now describes the addr_match/config_match split truthfully;
command-bus map now shows ACTUAL layout (bits 8 and 16:9 marked FREE — old group-filter removed;
transient preload/shift; auth 8-bit) PLUS a clearly-labelled PLANNED two-slot block pointing at
cmd_latch_64bit.md. No logic changed.

## ORDER agreed for what follows
1. Build the two-slot four-state decoder into v3 (replace op25 placeholder; both opcode slots
   work; 11-bit auth; one-function guard).
2. TEST: all four states + the guard + 11-bit auth match, in sim.
3. Repoint tests + QSFs off the non-v3 (unicell.v / unicell64.v chains) onto v3.
4. ARCHIVE the old chain (move to archive/, NOT delete — they are the dev history; NOT purged
   from git history). Only after nothing references them.
5. Build the WALL CELL on the correct v3 (tackles bus contention).
6. THEN Alan's wild idea (needs the cell correct first).

## Repo state
unicell64_v3.v = canonical. Comments grounded to logic, compiles clean. Old cell files still live
in tree (retirement is step 4, after v3 complete). Nothing broken. Design notes current:
cmd_latch_64bit.md (settled two-slot spec), tiled_interconnect.md, cell_v3_addressing_and_auth.md,
adder_graph_placement.md.

# Session Log — 2026-06-30 — Adder ENTRY proven on SILICON. Big addressing insight (cell v3). Path mapped.

## Done this session
- ADDER ENTRY proven ON SILICON (icm64_add_entry.tcl, GX660): present a=0x1234,b=0xABCD at the
  two entry-point cells -> P=a^b=0x0000B9F9 read back (seen=1) on the die. (Probe shows last-fired;
  both G,P fire; use single-zone DEBUG_SELECT build + icm64_readstate to see each cell.) Entry now
  proven in sim AND silicon. Also passes in sim (tb_zone64_add_entry.v).
- KEY load discipline confirmed: per-cell gates via LOAD_AT (op23, addr-gated) NOT broadcast
  RECONFIGURE (which smears one gate over all); FREEZE then RELEASE-as-one = controller->physics
  handoff; then present operands.

## BIG INSIGHT (post-break): cell v3 addressing — identity is the OUT, not the IN
Banked in docs/design-notes/cell_v3_addressing_and_auth.md. Summary:
- addr_match currently conflates config + data on input_address (the fusion cause, RTL line 552).
- Fix: 3 roles — IN latch (mutable listen), IDENTITY=CELL_ID (fixed; boot walks the OUTs/IDs),
  PUSH latch (old out latch repurposed to emit-address-only; dormant for compute, used by command
  cells; keeps ONE cell type). Split addr_match: config-match=CELL_ID, data-match=input_address.
  -> IN fully mutable, fusion impossible, clean sentinel taps. Cell stays dumb+absolute; loader/
  saver do the offset arithmetic.
- TRIGGER-PUSH primitive (push-on-condition): sentinel alert / ward signal / sensor / LIF spike
  emit (LIF = ~15-cell cluster; integrate-and-leak are extra cells, separate mechanism).
- Cross-connection = the already-confirmed command cell (auth travels with reconfigure). Highest-
  stakes seam; command cells should be trusted-base-only so user models can't reach the cmd bus.
- WIDENED SPLIT AUTH: 8-bit token today (cmd_bus 28:21); widen using ~15 cmd-bus spare + spill into
  the 12 reserved method-latch bits; own latch, validated independently, write-protected (aligns
  write-once-boot-auth). Hardens vs GUESSING; leak/replay still covered by asymmetric/fused-key.

## ENTRY/EXIT POINT model (resolved the inject confusion)
Banked in adder_graph_placement.md. The host INJECT can't deliver 32-bit data to a non-zero addr
(addr+data share the command word) — but that's a HOST-INTERFACE issue, NOT the fabric (the fabric
bus already separates bus_addr/bus_data lanes — Alan's instinct confirmed). RESOLUTION: a model
declares ENTRY POINTS (input seams) + EXIT POINTS; host feeds entry points, NEVER interior cells
(they receive from upstream flow). The workbench already exposed entry points = it was showing the
deployment architecture. Unifies with freeze/release: PRELOAD entry operands under freeze, RELEASE
triggers the flow. Function-execution model (perfect for the adder); streaming needs a separate
live-input path. Same concept as pond bridges, at model scope.

## Adder cell-count reality (banked earlier this period)
Fan-out to differently-addressed consumers needs DUPLICATORS -> adder is ~34 cells (18 compute +
~16 dup), MULTI-ZONE. Shared-address fan-out REJECTED (fuses cells: only separable in physical
mode -> global reset -> lose everything; logical-address uniqueness is an INVARIANT). Keep
duplicators. (Cell v3's identity!=dataflow may let shared-listen fan-out be safe -> revisit whether
it shrinks the adder back toward 18 — a v3 space-saving question.)

## WHERE WE ARE / NEXT BITS (in order)
1. STAGE 1 of the adder, BUS-CONNECTED — the real next build. Entry cells feed the prefix cells
   over the bus (cell-to-cell, separate lanes); Gp1=P&(G<<1) join, G1=G|Gp1, P1=P&(P<<1) self-join
   (P-duplicator); A-operands established via preload, RELEASE triggers flow. Each stage = its own
   file (regression-friendly) + its own silicon tcl.
2. STAGES 2-5 (same pattern, different shift span), then FULL ~34-cell graph end-to-end = the
   composition proof (a,b at entry -> SUM at exit, driven by physics).
3. PCIe side — develop QUICK in ONE ZONE first, then a full-card build.
4. THEN cell v3 on a NEW cloned variant in the single zone — the "where does it save space"
   question, adder as test case (does identity-as-out reduce duplicators/wiring?).
5. Further out: DSP/hybrid; model rewrites against the proven cell.

## THE LIGHT AT THE END (Alan's framing)
Once the CARD is done: it's the REPO + TESTING of all the functions, then FINALLY the DOCS. The
far-end TIDY ties together the banked threads (community loop, 3-tier capability, table-as-RTL-
projection, manifest/.man, entry-exit model, cell v3). It goes on, but there's light there.

## Repo state
All green, pushed. Entry proven sim+silicon. Many design notes banked this period:
cell_v3_addressing_and_auth.md, adder_graph_placement.md (+entry/exit + duplicator + invariant
+ inject findings), manifest_board_mapping.md, addressing_v2_relative.md, VISION.md (community
loop), IDEAS.md (edge accelerator, Tang Nano, product family, compiler offshoot refinement).
cell_capability_table.html (single source of truth, RTL-verified). Latest commit 4fd43fe area.

# Session Log — 2026-06-29c — ✅ FULL-DIE FEATURE-COMPLETE CELL PASSES. Cell-building phase DONE. Debug-select parameterised for lean production builds.

## Full card (top_arria10_64, 16 zones x 25 cells = 400, GX660) — basic tests PASS
The complete methodology stack proven at FULL SCALE across all 400 cells: in-shift, out-shift,
nibble mask, lanes — all computing correctly on the real substrate (not just single-zone).
clk_div 41.76 MHz (1.67x the 25 MHz operating clock); CLK_100M now a clean 331 MHz (constraint
holding — no more degenerate tmin). The cell is feature-complete and silicon-proven at scale.

## Debug-select parameterised (DEBUG_SELECT, default OFF)
The 92% fit / 3h+ compile was the per-cell readback mux (NUM_CELLS:1 x4 buses x16 zones) —
observability, a DEV feature. Now: single-zone top_arria10_zone1 = DEBUG_SELECT=1 (full
cell-walk where debugging happens, cheap at one zone); full die top_arria10_64 = default 0
(dbg0 hardwired to cell 0, no mux) -> reclaims ~40K ALMs (back toward 70s) + faster fit. Both
proven in sim. THIS 92% build was pre-change; next full-die rebuild is the lean fast version.

## CELL-BUILDING PHASE COMPLETE — milestone
Nothing unproven left in the cell. Methodology set frozen: nibble_mask(8) mask_en(1)
shift_amt(6) in_shift_en(1) out_shift_en(1) lane_cut(3) = 20/32 upper bits, 12 reserved.
Two-speed workflow established: develop+prove on single-zone (12-min loop), integrate on full
die overnight.

## NEXT (confirmed order)
1. CELL CAPABILITY TABLE — one source of truth (machine fields + human prose + cost), compiler
   imports it, renderer emits human doc from same records, RTL cross-check vs drift. Field set
   is now FROZEN -> right moment to build it.
2. SHIFT-ADDER full capability (new cell functions, 21 cells/one zone) — the composition proof.
   Develop on single-zone fast loop.
3. PCIe bridge — opens most up: fast host path + speeds model-rewrite testing.
4. DSP/HYBRID (committed, not optional — the £1000 lab-cage product requires it). After PCIe.
   Develop cheap on Tang Nano (DSP+SDRAM on board), lift to cage (allocation scale-invariant).
Product family: one core (substrate/.icm/hybrid) from £35 edge board to £1000 cage.
(possible: check per-nibble A/B masked-merge reachable by stacking, else a small add.)

# Session Log — 2026-06-29b — ✅ LANES PROVEN ON SILICON, TIMING-FREE. Methodology stack COMPLETE on the die. Cell feature-complete.

## Lane stage result (single-zone build top_arria10_zone1, GX660)
- icm64_lanes.tcl: inject 0x01002340, out-shift>>4 + all 3 byte boundaries cut (4x 8-bit
  lanes) -> out_data=0x00000204. PASS. Bytes [01][00][23][40] each >>4 in-lane ->
  [00][00][02][04], no cross-boundary. Breakable-boundary shifter confirmed on silicon.
- TIMING: clk_div 62.17 MHz WITH lanes, vs 61.26 MHz pre-lanes baseline (same single-zone
  build). Lanes cost ZERO — the 0.9 MHz is fitter noise. Alan's "4 shifters, breakable
  boundaries, shared amount, SAME PATH DEPTH" design confirmed: kill-mask is parallel to the
  shift (one AND), not added series depth. 62 MHz vs 25 MHz operating = 2.5x margin with the
  FULL stack active.
- Regression: lanes-off is bit-identical to proven out-shift, so shift/outshift/mask tests
  still hold (0x10023400 / 0x00100234 / 0x00002340).

## SINGLE-ZONE VEHICLE proven useful: top_arria10_zone1
Full command path + ISSP + UART, one zone, ~12-min compile. Built lanes, fit, flashed,
tested in one tight loop instead of a 2h full-die cycle. Reusable for every future feature.

## METHODOLOGY STACK COMPLETE ON SILICON — cell feature-complete
in-shift (0x10023400) + out-shift (0x00100234) + nibble mask (0x00002340) + lanes
(0x00000204), all proven on die, all timing-free, all composable. Latch usage: 20/32 upper
bits (nibble_mask 8, mask_en 1, shift_amt 6, in_shift_en 1, out_shift_en 1, lane_cut 3);
12 reserved. No unproven methodology feature remains.

## DECISION PENDING (pre-table): add anything, or freeze the field set?
Analysis: the four stages + two-cycle stacking (topology + 3 simultaneous methods) already
give the compiler a rich COMBINATION space — most new capability should come from compiler
COMBINATIONS (field-extract = out-shift+lane-cut; field-insert = in-shift+mask+gate-OR),
NOT new opcodes/hardware. Promote a combo to a named opcode ONLY when profiling shows it hot.
ONE possible genuine gap to check: per-nibble A/B MASKED-MERGE (predicated blend / choice
cell) — is it reachable by stacking the current gate+mask, or a real gap? If reachable: add
nothing, build the table. If not: a small addition may be worth it. (To trace next.)

## NEXT
1. (optional) trace whether per-nibble A/B masked-merge is already expressible.
2. Build the CELL CAPABILITY TABLE — ONE source of truth (machine facts + human prose + a
   COST field per capability), compiler imports it, a renderer emits the human doc from the
   SAME records (no drift, like the ICM direct-viewer). Cross-check field bit-ranges against
   the RTL so table and silicon can't drift. Build it now that the field set is FROZEN.
3. Full-die rebuild carrying the complete cell (+ debug-select) -> test all -> Python rewrites
   against the final proven field set (load-and-run).

# Session Log — 2026-06-29a — CORRECTION: out-shift was NEVER a stub — it is wired in unicell64 and ALREADY ON THE DIE. Sim-proven; runs on the current bitstream.

## Correction to earlier "stub" claim
Prior logs said m_out_shift_en was "defined/selected but no post-gate shift stage wired."
WRONG. unicell64.v has the full out-shift stage: computed_shifted (line ~511) right-shifts
computed_output by m_shift_amt when shift_out_en (= m_out_shift_en | t_shift_out_en); line
~953 emits computed_shifted as the fired out_buf_data. Internal state (data_reg, a_data /
loop_back / latch_in) keeps the UNSHIFTED computed_output, so out-shift is a clean bus-side
output modifier that never corrupts feedback. It was complete all along — just never exercised.

## Consequence: out-shift needs NO rebuild — it's in the flashed bitstream
The current top_arria10_64 flash uses this unicell64, so out-shift is already on the GX660.
Prove it on the CURRENT bitstream like the mask test (no reflash):
  icm64_outshift.tcl: SET_METHOD out_shift_en + shift_amt=4 (cmd_data=0x00010800), inject
  0x01002340 -> expect fired out_data=0x00100234 (result >>4). Distinct from in-shift's
  0x10023400 and from the raw 0x01002340 — unambiguous.
Sim-proven end-to-end through zone64: tb_zone64_outshift.v -> 0x00100234. PASS.
Field map (SET_METHOD writes cmd_latch[63:32] from cmd_data): nibble_mask=cd[7:0],
mask_en=cd[8], shift_amt=cd[14:9], in_shift_en=cd[15], out_shift_en=cd[16].

## Revised roadmap (out-shift collapses into "already done once tcl run")
1. ✅ in-shift on die (icm64_shift -> 0x10023400). DONE.
2. ✅ nibble mask on die (icm64_mask -> 0x00002340). DONE.
3. ✅ out-shift on die (icm64_outshift -> 0x00100234). DONE on silicon.
   >>> FULL BUILT METHODOLOGY SET PROVEN ON THE GX660: in-shift (0x10023400), out-shift
       (0x00100234), nibble mask (0x00002340) — same cell/bitstream/inject, only SET_METHOD
       config differs, three distinct correct outputs. Upper half of the 64-bit cell complete.
   Double-ended (in+out) under the address constraint is a clean ROUND-TRIP (<<n>>n identity,
   correct); the two independent single-stage proofs are what establish both stages exist.
4. The only genuinely NEW RTL before the full rebuild is LANES (adds a stage — watch timing
   on the small sample). Debug-select (op26) already in unicell_array64.
5. Then full rebuild (all features + debug-select) -> test all on die -> Python rewrites.

# Session Log — 2026-06-28g — ✅ STORED SHIFT PROVEN ON SILICON. Root cause of the dead bring-up was the missing clock constraint (not the ISSP, not the cell); clean-project rebuild fixed it; 64-bit methodology datapath confirmed on the GX660.

## RESULT: icm64_shift.tcl on top_arria10_64 (GX660)
  fired=1  out_addr=0x0200  out_data=0x10023400   (= 0x01002340 << 4)
  >>> PASS: stored shift applied on silicon — 64-bit methodology datapath confirmed.
The 64-bit cell's methodology half computes correctly in hardware: widened cmd_latch,
SET_METHOD (op25) on the held target lane, stored shift folded into the operand pipeline,
addressing, fire — all end-to-end on die, bit-exact to sim.

## icm64_readstate.tcl (just before): whole substrate alive
cycle_count ticking (796,075,261 -> 798,481,969); 0xDA7A marker reads 0xDA7A (snapshot
latching); cell0 cmd_latch=0x0040002c topo=0x02c armed=1 in=0x0100 out=0x0200; armed_count=400
(ALL 400 cells armed). Clock + command path + addressing + arming + snapshot readback all good.

## ROOT CAUSE of the whole dead bring-up: missing clock constraint (Alan's memory was right)
The earlier projects had NO .sdc/.qsf in the project, so CLK_100M was never promoted to a
global clock network — the fabric never clocked, cycle_count sat at 0, every probe field read
0. NOT the ISSP, NOT the 64-bit cell. Confirmed by the fitter on the good build:
"div_cnt[1]~CLKENA0 (150867 fanout) drives Global Clock Region" — clk_div promoted global,
reaching the whole fabric; clocks table CLK_100M=100MHz, clk_div=25MHz (sane, vs the earlier
degenerate 645MHz-1.5GHz tmin nonsense = unconstrained clock). The ISSP regenerations / probe
width / source-clock were real fixes but never the blocker.

## FIX that worked: clean single-folder project from the proven build
Quartus project had lost its database (clicking any report regenerated from just the .sof;
ISSP scattered under output_files4\). Rebuilt as ONE clean folder with: Unicell64.qsf +
Unicell64.sdc (clock constraint — the missing piece), the PROVEN issp.qsys (21/06, NOT
regenerated), full *64.v chain + unicell64.v + both bridges. One clean compile -> fabric
clocked -> shift passed first try. Lesson (again): clone the working project, change the
minimum; don't assemble fresh. Constraints already banked in fpga/quartus/.

## STATUS vs roadmap
Step 1 (prove the BUILT methodology set on die) = ✅ DONE — BOTH features confirmed:
  - icm64_shift.tcl: inject 0x01002340 -> 0x10023400 (stored shift <<4). PASS on silicon.
  - icm64_mask.tcl:  inject 0x01002340 -> 0x00002340 (nibble_mask 0xF0, hi nibbles zeroed). PASS on silicon.
  Clean A/B: same bitstream, same cell, same inject — only SET_METHOD config differs, output
  differs accordingly. The methodology stack applies the configured op on command, on die. The agreed order continues:
2. Small-sample OUT-SHIFT (the one stubbed cell field) + tests + fit/timing.
3. Small-sample LANES + tests + fit/timing.
4. Full rebuild (all features + debug-select op26, already in unicell_array64) -> test all on die.
5. THEN Python rewrites against the final silicon-proven field set (load-and-run).
Note: nibble MASK is built+sim-proven but not yet separately silicon-confirmed — a one-line
tcl variant (SET_METHOD mask_en+nibble_mask, check masked output) confirms it on THIS bitstream.

# Session Log — 2026-06-28f — Silicon bring-up blocked at the SNAPSHOT TRIGGER (regenerated ISSP source path), not the fabric; target-addressed debug-select wired for next build.

## Where the 64-bit flash stands (top_arria10_64, GX660)
Full die fit GOOD: 185,445 ALM (74%), 157,856 reg, FMAX clk_div 56.2 MHz (target 50 — fine).
Constraints now correct (CLK_100M @ E23 took; clk_div recognised). Probe width fixed to 113
(reads len=29 clean). BUT every snapshot reads ALL ZERO.

## DECISIVE diagnosis: snapshot trigger not firing (NOT clock, NOT cells)
icm64_readstate.tcl selector-4 reads the bridge's HARDCODED 0xDA7A marker as 0x0000. That
constant is wired into the snapshot mux and does not depend on clock/cells/config — the ONLY
way it reads zero is if the snapshot NEVER LATCHES (snap_pulse never fires). So snap_req
(source[65]) edge is not reaching the bridge. cycle_count also static 0 (same cause).
- PROVEN build (top_arria10) TICKS cycle_count on THIS board THIS session (1BD9D5B0->1C033BFA->
  1C2CA20A). So board clock + snapshot mechanism + tcl are all fine when driven by the proven
  ISSP. The fault is isolated to the 64-bit build's FRESHLY-GENERATED ISSP source path.
- Likely cause: source SYNCHRONISATION/pipeline registers not enabled on the regen (bridge
  header warns: "without source clock + sync regs the edge-detects glitch"; snap_req/cmd_go
  are edge-detects). Probe=113, source=66, source-clock-on, enable-off were all set — the
  sync-register option is the remaining suspect.

## FIX for Alan (overnight / morning): copy the PROVEN ISSP IP, do not regenerate
The proven Unicell-Q build's ISSP works on this board right now (ticks). Copy its generated
ISSP IP files (.qsys/.ip/.qip + generated dir) into the 64-bit project wholesale instead of
the freshly-parameterised instance — it already has probe=113, source=66, source clock, and
the correct source registration the bridge was written against. Re-fit, reflash, re-run
icm64_readstate.tcl: the 0xDA7A marker should read 0xDA7A and cycle_count should tick = snapshot
alive. THEN icm64_shift.tcl -> want out_data=0x10023400 (stored shift on die).

## DONE this session (rides the NEXT build): target-addressed debug-select (Alan's idea)
"Use the target address to read just the programmed cells." Wired into unicell_array64.v:
new opcode CMD_DBG_SELECT=26 latches dbg_sel (clog2(NUM_CELLS) bits) from cpu_data; dbg0_*
ports now mux cell_*[dbg_sel] instead of hardwired [0]. Cells have NO decode for op 26 ->
pure side-effect-free debug write. Lets the host walk every cell of zone 0 on die and read
its real config. PROVEN in sim (fpga/verilog/tb_dbgsel64.v): configured cell0 topo=0x0BC,
cell2 topo=0x024; DBG_SELECT 0 reads 0x0BC, DBG_SELECT 2 reads 0x024. PASS.
NOTE: bridge currently wires only zone-0 dbg0 to ISSP, so this reads zone 0's 25 cells;
reading OTHER zones needs a top-level zone-mux (later). This is committed but NOT in the
flashed bitstream yet — rides the next reflash.

## Pending / order unchanged
1. Alan: copy proven ISSP IP -> reflash -> probe-sanity (0xDA7A + cycle tick) -> icm64_shift
   (0x10023400 = in-shift on die).
2. Then small-sample OUT-SHIFT + tests; then small-sample LANES + tests; then full rebuild
   (now also carrying debug-select); then test all features; THEN the Python rewrites against
   the final silicon-proven field set.
Design notes banked today: security_portability.md, hybrid_hard_ip.md.

# Session Log — 2026-06-28e — Silicon bring-up of the 64-bit variant: dead-clock root-caused (missing pin constraint, NOT the cell); constraints banked; agreed feature-completion roadmap before the Python rewrite.

## Silicon session (top_arria10_64, GX660)
- Zone synth (registered I/O): 14,270 ALM / 10,517 reg / 131.68 MHz in-fabric. vs 50 MHz
  target = 2.6x margin. Timing NOT the constraint; density is (~510 ALM/cell).
- Chose 25 cells/zone (400 total). Built top_arria10_64 (16x unicell_zone64, op25 routed).
- FIRST flash: icm64_shift.tcl -> fired=0, all-zero probe. DIAG (icm64_probe_sanity.tcl):
  raw probe len=33 but ALL ZEROS, cycle_count stuck 0 -> FABRIC NOT CLOCKING. Root cause:
  fresh project had NO .qsf/.sdc -> CLK_100M unconstrained, never reached E23, /4 divider
  never ticked. NOT the 64-bit cell. (Same failure as the very first card bring-up.)
- FIX (banked, permanent): fpga/quartus/Unicell-Q.sdc (CLK_100M 100MHz @ E23, clk_div /4),
  Unicell-Q64.qsf (top_arria10_64 + *64.v chain + bridges + PIN_E23), Unicell-Q.qsf (proven
  32-bit fallback). Constraints now IN-REPO so the clock never wanders on a fresh project.
- Re-flashing now (2h build). On completion: run icm64_probe_sanity (cycle_count must TICK),
  then icm64_shift.tcl -> want out_data=0x10023400 (0x01002340<<4 = stored shift on die).

## Cell audit (unicell64.v methodology half)
WIRED + proven in sim: m_in_shift_en + m_shift_amt (input shift), m_mask_en + m_nibble_mask.
STUB: m_out_shift_en — field defined and selected into shift_amt, but NO post-gate output-
shift stage is wired (bus_data_shifted shifts INPUT only). Out-shift is the one cell gap.
The shift test uses a hand-written tcl (SET_METHOD op25 poked directly) — does NOT need the
loader; loader does not emit op25 yet.

## AGREED ROADMAP (Alan) — complete + silicon-prove the cell BEFORE the Python rewrite
1. Finish THIS flash; probe-sanity (clock alive), then icm64_shift (in-shift on die).
2. Rebuild a SMALL sample with OUT-SHIFT wired + tests; confirm pass + fit + timing.
3. Rebuild a SMALL sample with LANES + tests; confirm pass + fit + timing.
4. If all pass and fit/timing hold -> FULL load rebuild (all features, 16 zones).
5. Test ALL features on the full die.
6. THEN the Python rewrites (loader SET_METHOD emission, ICM methodology fields, two-slot
   decoder, format/HMAC) — written ONCE against the FINAL, silicon-proven field set, not a
   moving target. Tested as we go against a fully-specced running substrate: "load and run."
Rationale: writing the loader/format against in-shift-only and again when out-shift/lanes
land is exactly the churn the "prove the cell first, then point Python at it" rule avoids.
The two-slot decoder stays deferred until the field set is final (it's encoding, not feature).

## Open cell items before full rebuild
- Wire out-shift (post-gate right-shift stage mirroring the input shift). Small, low-risk
  (mirrors proven logic). Next small-sample build.
- Lanes (by-source splice default; by-arrival intra-die-only flagged). Reserved bits +
  1 opcode; FIRST in the operand pipeline. Synth-time it (single-cycle ceiling). Next sample.
- Hold the line at 3 operand stages (lane/shift/mask); further features via opcode
  combinations, not new depth (the measured timing-cost rule).

# Session Log — 2026-06-28d — Zone synth measured; 25 cells/zone chosen; FOCUSED datapath-confirm reflash prepared (decoder deferred).

## Zone synth result (top_zone_synth, CELL64=1, registered I/O, 4 pins)
14,270 ALMs / 10,517 registers / FMAX 131.68 MHz for a 28-cell variant zone (real
fabric-internal path: wired-OR bus + routing). vs 50 MHz target = 2.6x margin — timing
is NOT the constraint. ~510 ALM/cell; full 16-zone die of the variant ~228k ALMs (~90%)
at 28 cells — DENSITY is the constraint, not speed.

## Decision: 25 cells/zone (Alan)
25 x 16 = 400 cells, ~81% ALM, comfortable router headroom, plenty to test every feature.
top_zone_synth NUM_CELLS -> 25. (Real reflash top set to 25 too.)

## Decision: lanes DEFERRED (Alan) — "is it needed at this stage? no"
Lanes are a NEW methodology stage = additive capability, not confirmation of what's built.
This reflash CONFIRMS the already-built upper half (stored shift + mask) on silicon. Add
lanes later against a proven base, with clean isolated synth-timing. Don't debug new RTL +
first-silicon shift/mask together (isolate the variable).

## Decision: two-slot decoder DEFERRED to AFTER datapath confirm (Alan)
The placeholder CMD_SET_METHOD (op 25) is SUFFICIENT to silicon-prove shift+mask (same
pattern as CMD_LOAD_AT proving targeting before the streaming loader optimised it). The
real two-slot four-state decoder is an ENCODING optimisation with an under-pinned piece
(writer-opcode cmd_data packing) — write it on a proven datapath, not rushed into the
first-silicon bitstream.

## Reflash prepared (FOCUSED datapath confirm)
- pcie/top_arria10_64.v — variant top (copy of proven top): 16x unicell_zone64, NUM_CELLS=25,
  cpu_addr_w routes load_target for op 25 (CMD_SET_METHOD) like ops 2/3/23. Proven top
  untouched as the known-good fallback. (Quartus-validated by Alan; too large for iverilog
  full-elaborate here — the three surgical edits grep-verified.)
- fpga/verilog/tb_zone64_method.v — PROVES end-to-end in sim: SET_METHOD stored shift<<4
  on the held target through a full zone64, inject 0x01002340 -> fired out_data 0x10023400.
- fpga/icm64_shift.tcl — silicon test mirroring the sim: same sequence, reads fired out_data
  at probe selector 0 (snap_out_data=out_data_l, out_seen@[96]). PASS if out_data=0x10023400.
  No ISSP-bridge change needed (uses the existing fired-output readback).

## NEXT
1. Alan: synth top_zone_synth at 25 (confirm fit ~81%), then build+flash top_arria10_64,
   run icm64_shift.tcl — fired out_data=0x10023400 = stored shift proven on the GX660.
   (A mask variant tcl is a trivial follow: SET_METHOD mask_en+nibble_mask, check masked out.)
2. THEN the real two-slot decoder (four states + arm + one-function guard) on the proven
   datapath; pin the writer-opcode cmd_data packing first.
3. THEN lanes as an isolated stage; then loader format bump + golden ICM; then compiler.

# Session Log — 2026-06-28c — 64-bit cmd_latch: datapath variant built + encoding spec settled.

## What landed
- CMD_RECONFIGURE auth-write now boot-only (clause 3) — committed d70dc1b, tb_reconfig_auth.v.
- Adder dependency check: packed KS needs the cut (stored shift); wide KS (548c) doesn't
  fit the 448-cell die; 16-bit wide KS (~270c) is a no-cut no-reflash option.
- fpga/verilog/unicell64.v — 64-bit cmd_latch VARIANT (proven cell untouched). Upper-half
  methodology fields wired (nibble_mask[39:32], mask_en[40], shift_amount[46:41],
  in_shift_en[47], out_shift_en[48]); stored shift folded into the fixed ladder as
  stored-OR-transient; stored nibble-mask spliced before the gate. Loaded via PLACEHOLDER
  CMD_SET_METHOD (op 25, addr_match-gated) — NOT the real encoding, just a testable write.
  tb_unicell64.v PROVES stored shift (<<4) + nibble-mask (block high 16) drive the datapath.
- docs/design-notes/cmd_latch_64bit.md — RESOLVED section appended: auth 8-bit both sides
  (option a); two-slot opcode encoding settled (8 slot-A + 8 slot-B + 2 flags + arm + 8 auth,
  5 bus spare); opcode implies payload type so NO selector bit; one-function/many-methodology
  as an ENFORCED guard (two-function pass illegal, must refuse); two-pool budget (bus=
  expressivity guard / latch=area don't carve); reserved-means-zero enforced.

## Encoding decisions settled this session (Alan)
- Auth 8-bit both sides — binding constraint is the BUS not the latch; returns 2 bits to
  bus spare (5 total). Methodology latch has 15 reserved (cmd_latch[63:49]).
- Two-slot word = two independent opcode slots; flags gate which are live; cell applies both.
  00 topology-only / 01 function+methodology / 10 function (B ignored) / 11 both methodology.
- Slot B's function is read from its OPCODE, not a selector bit. One function per cell
  (enforced), multiple composable methodologies per pass (the reason the word exists).

## NEXT (named)
1. SYNTH one zone of unicell64 — measure stored-state + mask/shift area vs the 70% fitter
   hang, BEFORE any full die build. (Alan to run between sessions.)
2. Replace placeholder CMD_SET_METHOD with the REAL two-slot decoder (four states + arm +
   at-most-one-function guard). Datapath underneath is proven, doesn't change.
3. Loader/serialiser format-version bump (32->64) + refuse-to-load guard; golden 64-bit ICM
   proven on the die BEFORE pointing the compiler at it.

# Session Log — 2026-06-28b — Address-targeting reflash (Option A): SET_INPUT/SET_OUTPUT addr_match-gated on the held target. Loader now streams full (target, topology, in, out) records. Sim-proven (oracle + RTL); awaiting reflash for silicon. NEXT item 1b DONE in sim.

## The change (3 RTL files — this is the reflash set)
Chosen Option A (Alan): SET_INPUT_ADDR/SET_OUTPUT_ADDR become addr_match-gated in the
CELL, exactly like CMD_LOAD_AT — one comparator gates everything (invariant clause 1/4),
the same mechanism used in normal run-mode addressing, not a boot-only special case. Host
cycles at load time are cheap; correctness is what matters.
- pcie/top_arria10.v: cpu_addr_w now reads the held load_target for opcodes 2 and 3 as
  well as 23. Target (latch) and the new-address value (cpu_data) stop colliding.
- unicell_array.v: SET_INPUT_ADDR(2) dropped from cmd_is_boot_targeted — it (and op 3)
  now BROADCAST and the cell self-gates on addr_match. No parallel array comparator.
  SET_LOGICAL(14) STAYS array-targeted (the boot walk is untouched).
- unicell.v: CMD_SET_INPUT_ADDR / CMD_SET_OUTPUT_ADDR gate on (addr_match && auth_ok).
Per-cell record (all on one held target): SET_TARGET(slot); SET_INPUT(in); SET_OUTPUT(out);
LOAD_AT(topo|arm). 4 transactions/cell.

## Loader (fpga/icm_stream.py) — full-record streaming
build_stream now emits SET_INPUT/SET_OUTPUT per record (stream_addr default ON;
--no-stream-addr for the pre-reflash bitstream). Oracle models the addr_match-gated
SET_IN/OUT. emit_tb checks input_address+output_address per cell. emit_tcl reads cell-0
topology + in + out at probe selector 3 (the bridge packs dbg0_input_addr@[95:80],
dbg0_output_addr@[47:32] alongside cmd_latch@[79:48] — a single snapshot shows all three).

## New test: arbitrary wiring (examples/icm/wired3.icm)
Three cells whose in/out are deliberately NOT the physical defaults; cell0+cell1 both
emit to 0x50 (a wired-OR fan-in the default chain can't express), cell2 to 0x51.
- ORACLE: ALL PASS (topology + in/out per cell; unused cell at defaults = exclusion).
- RTL replay (tb_icm_wired3.v, real unicell): 3/3 cells match topology AND in/out.
  cell2 out=0x51 while cell0/1 out=0x50 by itself disproves broadcast.
- Silicon (fpga/icm_wired3.tcl, needs the reflash): reads cell0 topo=0x0BC, in=0x40,
  out=0x50 at selector 3.

## Regressions (all green on the edited RTL)
tb_top_target, tb_zone_target, tb_zone_chain, tb_zone_inject, tb_zone_adder, tb_zone_emit,
tb_die_boot (boot walk intact), tb_v23_oracle, tb_icm_xor_and_or, tb_icm_wired3 — PASS.
tb_v23_oracle UPDATED to the new model: it now presents the target on the address lane
before SET_OUTPUT (was relying on old broadcast). tb_zone_inject byte-identical original
vs edited. PRE-EXISTING fails (NOT this change, identical on original RTL): tb_cmd_emit
(stale standalone, superseded by tb_zone_emit), tb_bridge_chain (documented all-armed
ripple synthetic artifact).

## NEXT
1. DONE (SILICON, 2026-06-28): reflashed top/array/cell. zone_target / zone_adder /
   zone_emit regressions passed on the die, then icm_wired3.tcl read back cell0
   topo=0x0BC, in=0x40, out=0x50 at probe selector 3 — per-cell address streaming proven
   on the GX660. 0x50 is the wired-OR fan-in (cell0+cell1 → one output), a wiring shape the
   physical-default chain can't express, so arbitrary topology + arbitrary wiring are both
   silicon-confirmed loadable. Ledger limit: cell0 is probe-visible; cell1/cell2 distinct
   in/out are oracle/sim-verified (cell2 out=0x51 vs cell0/1 out=0x50 disproves broadcast),
   not directly read on the die — same read-scope as zone_target. The addressing invariant
   is now a measured property of the fabric, not only a doc claim.
2. Packed Kogge-Stone adder as the first heterogeneous ICM with REAL wiring on silicon
   — now buildable (full (target, topology, in, out) records proven loadable on the die).
   This is the next live target.
3. Loose end still open: CMD_RECONFIGURE auth-write under physical_mode (invariant clause 3).
4. Horizon (deferred to full-silicon era, years out): inter-card comms. Seam is already
   clean — block_id (high 16) + declared-latency handoff; nothing inside a cage may assume a
   free cross-cage wire. Linked bridge-buffer reorder + selective-repeat ARQ sketched (see
   below) but parked; cross-card transport to be written against the real die's transports,
   not designed ahead. Single-card and two-card-federation work between now and then feeds it.

## Architectural notes banked this session (not yet RTL)
- 64-bit cmd_latch cut: its hardest prerequisite (per-cell targetable setup writes) is now
  done — SET_SHIFT/SET_MASK are the same addr_match-gated shape as the proven SET_*/LOAD_AT.
  Remaining: widen latch, stored shift+mask upper half, auth option (a) 8-bit both sides,
  format-version bump + refuse-to-load guard, stack rewrite (serialiser/VM/compiler).
  Risk is area not logic: synth ONE zone with the 64-bit cell before the full build (the
  70% fitter hang was the variable barrel shifter; check the stored-state cost early).
  Build order: hand-write one golden 64-bit ICM, prove it on the die, THEN point the
  compiler at it — don't co-evolve the compiler with unproven RTL.
- Distributed timing: "known latency" must mean ENFORCED bound or confirmed arrival, never
  the typical/average. Bridge latency profile = a portable sidecar (like the .isi DSP table),
  read by the scheduler; wrong interconnect profile is a refuse-to-load hazard like wrong
  cell depths. Card-to-card: GT-direct for tight determinism, SmartNIC/host for coarse
  latency-tolerant handoffs — chosen per bridge.
- Linked bridge-buffer cells (reorder + reliable delivery, parked for the silicon era):
  address-as-sequence-number makes reorder = the addressing (packet N self-files into slot
  base+N); "all slots filled" = N-way AND (fabric-native); gap = unfilled slot (loss detect
  free). Count→address arithmetic belongs at the BRIDGE EDGE (like the loader's root+offset),
  not crammed into auth (auth is the trust gate at the boundary — never repurpose it). The
  per-packet sequence is a travelling FIELD (the old repurposed-CRC slot, born in the command
  word, resolved to a slot address on arrival, then gone). The WINDOW number is a separate
  HELD loop_back cell at each end (persists across buffer clears; carries set-tagging,
  wraparound anti-aliasing — keep sequence space >= 2x window — and duplicate-suppression).
  Resend/confirm = selective-repeat ARQ: sender-side retransmit buffer (the easy-to-forget
  half), NAK via CLZ/gap-bitmap over the occupancy vector, end-of-window marker for prompt
  NAK + staleness timer (Ward's stall_ticks shape) for the marker's own loss, BOTH ends
  carry timers (lost ACK = deadlock otherwise). Integrity: NOT a per-cell CRC (350 cells /
  depth 20 — XOR is the fabric's worst primitive in a serial chain, too costly inline). The
  cross-network transport framing (Aurora/Interlaken/Ethernet FCS) already carries CRC and
  turns corruption into a MISSING frame, which the loss path already handles. Residual
  tamper-evidence = a MAC (mask primitive / security module), not a polynomial. New cell
  (stored shift + loop_back) could build a cheaper CRC if ever truly needed, but the better
  outcome is not spending those cells in fabric at all.

## NEXT (original, superseded above)

## Files (additive + 3 RTL edits + 1 test update)
NEW: examples/icm/wired3.icm, fpga/icm_wired3.tcl, fpga/verilog/tb_icm_wired3.v.
EDITED: pcie/top_arria10.v, fpga/verilog/unicell_array.v, fpga/verilog/unicell.v,
fpga/icm_stream.py, fpga/verilog/tb_v23_oracle.v.

# Session Log — 2026-06-28 — ICM-file streaming loader built on the (SET_TARGET, CMD_LOAD_AT) transport (NEXT item 1). Offset-native, transport-pluggable, triple-verified. Additive — no RTL/existing file touched.

## What was built (the compiler<->silicon bridge, step 1)
fpga/icm_stream.py — streams an ICM as ordered (SET_TARGET addr, CMD_LOAD_AT config)
pairs through the proven address-lane target latch. Offset-native per the relocatable
canon: records hold block-local 16-bit OFFSETS, loader forms root+offset, never bakes
absolute-only. Transport sits behind a Transaction layer (ISSP/UART now, PCIe BAR later
swaps the carrier, not the stream). gs->LOAD_AT config-word translation verified against
the unicell.v decode (topology[9:0] + arm@[11] the proven subset; richer gs<->cmd_data
flag mapping deferred to the 64-bit cut, with a warn-on-unmapped-bits guard so nothing
drops silently).

examples/icm/xor_and_or.icm — first streamed heterogeneous ICM: 3 cells, XOR/AND/OR
(0x0BC/0x007/0x024), contiguous so the physical-default wiring chains them. Same shape
tb_top_target.v proves.

## Triple verification (all agree)
1. Built-in ORACLE (faithful model of top load_target latch + cell CMD_LOAD_AT decode):
   cell0=0x0BC cell1=0x007 cell2=0x024 all armed; unused cell3 stays unconfigured
   (exclusion). ALL PASS.
2. Real RTL replay: --emit tb generates tb_icm_xor_and_or.v that drives the loader's OWN
   stream into unicell_zone/array/cell through the real latch logic. iverilog: 3/3 cells
   match. >>> PASS.
3. Byte-identical to silicon-proven zone_target.tcl: cfg words 0x8BC/0x807/0x824 =
   topology|(1<<11). Generated fpga/icm_xor_and_or.tcl runs on the Arria as-is.

## HONEST SCOPE on the currently-flashed bitstream
Streams per-cell TOPOLOGY+flags+arm (the CMD_LOAD_AT win). Does NOT yet stream arbitrary
per-cell IN/OUT addresses: SET_INPUT_ADDR(2)/SET_OUTPUT_ADDR(3) still take cpu_addr from
cpu_data[15:0] (target==value dual-use), so they only set in/out to the physical CELL_ID.
This ICM relies on physical defaults (in=CELL_ID, out=CELL_ID+1); loader WARNS if a
record's offsets diverge. Per-cell offsets ride in the stream regardless — same file
loads unchanged once the address-targeting reflash lands.

## NEXT (natural step 1b, then 2)
- Address-targeting reflash: route load_target into cpu_addr_w for opcodes 2/3 (top) +
  have the cell addr_match-gate SET_INPUT/SET_OUTPUT — mirrors exactly what CMD_LOAD_AT
  already does. Then the loader streams full (target, topology, in, out) records and the
  packed adder's irregular wiring becomes loadable. Spec against the INVARIANT first.
- Then: packed Kogge-Stone adder as the first heterogeneous ICM with real wiring on silicon.

## Files added (4, additive)
fpga/icm_stream.py, examples/icm/xor_and_or.icm, fpga/icm_xor_and_or.tcl,
fpga/verilog/tb_icm_xor_and_or.v. No existing file modified -> no regression surface.

# Session Log — 2026-06-23 — RESOLVED: within-zone OR-chain works on Arria 10 (28 cells, value intact). Root cause of the "no output" was a STALE-SNAPSHOT readback bug in or_chain.tcl, not the fabric.

## Flat cell addressing + serial boot walk (aligning RTL to ARCHITECTURE.md)
Read docs/ARCHITECTURE.md + addressing_note.md (should have first). Corrected
model: cell address is ONE flat point per block (block boundary = bus boundary);
zones are physical routing only, not an address level. Bridges are dumb physical
wire — routing is done by the destination ADDRESS carried in the cell, not by the
wire. Hierarchy block->die->card->backplane (128-bit) stacks above; Shore owns
everything above the local cell address; the cell latch never grows.

RTL deviations fixed:
1. CELL_ID was zone-local (0..27 x16); ZONE_ID was dead. Added CELL_BASE param to
   unicell_array (zone passes ZONE_ID*NUM_CELLS); CELL_ID = CELL_BASE + c, and
   boot targeting compares cpu_addr against the global flat ID. Zone N now owns
   flat IDs N*NUM_CELLS .. +NUM_CELLS-1. Address is one flat point, no zone field.
2. Reverted the za_out_remote bridge gate I had added — wrong layer. Bridges are
   pure physical wiring; correct cell addressing does all routing.
3. The real missing step was BOOT: nothing laid the flat address map over the
   fabric, so cells came up on physical defaults and a broadcast BOOT_COMMIT set
   EVERY cell to one address ("all cells same in/out address" = no boot walk ran).
   Made CMD_BOOT_COMMIT a per-cell TARGETED command (added opcode 7 to
   cmd_is_boot_targeted). Boot now WALKS: for each flat CELL_ID, BOOT_COMMIT
   targeted -> that cell's logical input_address := ID, auth := token, ->RUN; next.
   Serial (~1 transaction/cell) but lays the correct map. For basic testing
   logical==physical (cpu_addr selector == address payload), which is fine.

SIM PROOF (tb_boot_walk.v, 2 zones/56 cells): after the walk, every cell holds
logical input_address == its flat physical ID, all in RUN, auth set. cell0=0x0000,
cell27=0x001b, cell28=0x001c, cell55=0x0037 — contiguous straight across the zone
boundary. The bootstrap handoff from ARCHITECTURE.md, working.

CONSEQUENCE (action needed before next silicon flash): making BOOT_COMMIT targeted
removes the broadcast BOOT_COMMIT pattern. Any script that did one broadcast
BOOT_COMMIT to set all cells (shift_diag_v3.tcl, or_chain_diag.tcl PART A,
bringup_v23.py) must switch to the walk (BOOT_COMMIT per cell) OR target the
specific cell under test. tb_zone_inject.v already converted (walk-target cell 0,
logical=0) and passes. The silicon tcl scripts are NOT yet updated.

Regressions after all changes: tb_zone_chain fires=15 (physical-mode chain,
unaffected); tb_zone_inject walk-target cell0 out=0x2340@0x200; tb_boot_walk 56/56.

NOTE on the all-armed bridge ripple (tb_bridge_chain): with flat addressing the
token DOES cross the zone boundary (Z0->Z1 confirmed), but an all-cells-armed
ripple floods the next zone's ibus (every fire hits the dumb bridge; non-matching
addresses still assert cpu_valid and interrupt the in-zone or_valid ripple),
stalling mid-zone. This is a synthetic-test artifact (real programs are sparse/
directed, not a full ripple). Separable from addressing — the address map is
correct (proven by tb_boot_walk). Revisit with a sparse directed cross-zone test.


## RESOLUTION (the actual answer)
or_chain_diag.tcl PART B on silicon:
  after inject: out_count=28  out_addr=0x001c  out_data=0x00002340
=> FULL within-zone chain: cell0->cell27 rippled, B passed through OR(0,B)=B
   intact, out_addr reached 0x001c (=28, zone's last cell emits to 28).
PART A (proven PASS_B) gave out_count=1, out_data=0x01002340 => ISSP output
capture was working all along.

The fabric was firing and chaining correctly the WHOLE time. The "out_count=0,
out_data=0, arrived->0 (impossible)" readings were a readback ordering bug in
or_chain.tcl's `show`: it called `rd` (read probe) BEFORE the snapshot, so every
line displayed the PREVIOUS step's snapshot. "after inject" was showing the
"after preload" (pre-fire) state = zeros. Fix: take a fresh view-0 snapshot in
`show` before reading out_* (committed to or_chain.tcl). JTAG shift latency (ms)
>> ripple (~4.5us) so the fresh snapshot always lands after the wave settles.

Consequences:
- The double-drive fix (zone arbiter) was a real cleanup but NOT this bug; it
  neither caused nor fixed the visible symptom. Keep it (cleaner single-drive).
- The per-cell addressing-encoding finding still stands for FUTURE arbitrary
  (irregular) addressing; physical-mode CELL_ID+1 default chain is proven.
- Decode gotchas for the readback: output_set is a SEPARATE reg, NOT cmd_latch[19]
  (dump's outset19=0 is meaningless; 28 fires prove output_set=1). out_data_l is
  NOT cleared on reset (only out_count is) -> stale out_data display when count=0.

## BRIDGE round-robin (cross-zone) — bug found + fixed in sim
Built tb_bridge_chain.v: N zones in a row wired exactly like top_arria10's bh
chain (zone[i].bridge_w_out -> bh[i] -> zone[i+1].bridge_e_in, forward-only).
Config broadcasts to all zones (RECONFIGURE OR, SET_OUTPUT=0 so the active cell
re-emits on the same index, preload A=0). TRIGGER injected into ZONE 0 ONLY, so
any other zone firing can only be the bridge delivering the token.

FOUND (cross-zone delivery was silently broken): a bridge token reaches the
receiving zone's ibus correctly (traced: ibus_valid=1, ibus_addr=0, data intact,
cell0 a_arrived=1) but the cell never fired. Root cause in unicell_array.v line
215: on cpu_valid, `bus_valid <= (cmd_code==8'd1)?1:0`. The bridge token rides
ibus->cpu with the COMMAND bus idle/stale (cmd_code != 1 at the receiving zone),
so bus_valid stayed 0 and the token never reached the cell bus. In-zone chaining
works because it uses the or_valid->bus path, which bypasses this gate; cross-zone
is the only path that hits it -> never exercised until now.

FIX: bus_valid <= !cmd_valid (drive the data bus for any data-carrying cpu cycle
-- host DATA_WRITE or inbound bridge token -- but not for commands, which pulse
cmd_valid). Covers all three cases: host inject (cmd_valid=0)->1, host command
(cmd_valid=1)->0, bridge token (cmd_valid=0)->1.

SIM RESULT (8-zone row): token injected into Z0 only reaches all 8 zones via
bridges, data 0x00002340 intact at every hop, deterministic 8 cycles/hop
(Z0@28 ... Z7@84 = 56 cyc / 7 hops). Regressions pass: single-zone chain
(fires=15, arrived->13) and proven inject (out=0x01002340@0x200, arrived->0).
Per-hop budget ~8 cyc = bridge-out reg + ibus reg + cpu->bus + bus_addr_r +
fire/drain. Vertical (bv, s_out->n_in) uses the identical mechanism.

NEXT (silicon): only unicell_array.v changed -> rebuild + reflash. Cross-zone
chain then extends the within-zone chain past the zone boundary (out_addr will
climb past 0x001c when the token bridges into the next zone). Multi-zone read:
use the per-zone z_out probes / ISSP view, watch out_addr cross the boundary.
Asset: fpga/verilog/tb_bridge_chain.v (parametric N, extensible to the 2x8 grid).

## NEXT (real frontier now): cross-zone bridge handoff
out_addr stops at 0x001c because cell 27 emits to addr 28 and no cell 28 exists
in the zone. Going deeper = the inter-zone BRIDGE path (bh/bv registered handoff),
the least-tested path. Build that chain in sim (multi-zone tb), then silicon.

## (superseded) earlier framing this session

## Root cause of the chain failure (FIX committed)
Instrumented tb_zone_chain. Chain DOES ripple in sim (15 fires, out_addr climbs
1->15, value 0x2340 intact) but only cell 0 cleared a_arrived; every cell
triggered by FEEDBACK fired and then RE-ARMED. Bus trace showed why: every fired
address is driven onto the internal bus TWICE —
  (1) by the array's own or_valid->bus chaining (unicell_array.v ~line 216), and
  (2) by the zone re-injecting the same local fired output via
      `else if (za_out_valid) -> ibus -> array.cpu_*` (unicell_zone.v ~line 176).
The second (lingering) exposure hits the first-arrival store AFTER a_arrived has
cleared, re-arming the just-fired cell. That zone re-injection is redundant — the
array already chains its own output internally, and bridges get za_out on a
separate path — so it does nothing useful and double-drives the bus.

Same family as the ibus_addr skew: a timing-sensitive double-drive that nets one
way in zero-delay sim (arrived stuck HIGH, output surfaces) and the other way on
silicon (arrived->0, no output). FIX: delete the `else if (za_out_valid)`
re-injection branch in the zone arbiter. Host-inject + bridge paths retained.

Sim-verified on the real file (no IP regen, only unicell_zone.v changed):
- tb_zone_chain: fires=15, value intact, arrived 28->13 (was 28->27 with the bug)
- tb_zone_chain_probe: cells 0..14 cleared cleanly, wavefront at cell 15
- tb_zone_inject (proven single-cell): NO regression — out=0x01002340 @ 0x0200, arrived->0

## NEXT (silicon): reflash with this fix, run fpga/or_chain.tcl
Tell = arrived drops on inject AND out_count ticks >1 AND out_data=0x00002340
with out_addr advancing past 0x0001. This is the divergence-resolved test.
If it STILL shows no output: next suspects are the cross-zone bridge handoff
(bh/bv registered path, barely exercised) then the out_count capture in the ISSP
bridge.

## Per-cell addressing — encoding gap (CONFIRMED in sim, design decision pending)
Verified the canonical bring-up order (bringup_v23.py): BOOT_COMMIT sets the
INPUT (logical) addr + auth + flips to RUN; SET_OUTPUT_ADDR sets the OUTPUT addr
SEPARATELY; RECONFIGURE sets topology + arm. Not one sweep. Then found the deeper
issue — the runtime command word cannot set arbitrary per-cell addresses:
- For any non-inject command, cpu_addr = cpu_data[15:0] AND the address payload
  is also cmd_data[15:0] — the SAME 16 bits are both "which cell" and "what
  address" (the array's documented cpu_addr dual-use problem).
- => targeted SET_INPUT_ADDR/SET_LOGICAL can only write input = CELL_ID (identity)
- => SET_OUTPUT_ADDR (opcode 3) is NOT in the boot-targeted list -> it BROADCASTS;
  every cell collapses to one output address.
- => BOOT_COMMIT also broadcasts (all inputs to one value).
Sim proof (tb_target-style dump): SET_INPUT can't move a cell off its CELL_ID;
SET_OUTPUT 0x2000 set ALL cells' output to 0x2000. So today the ONLY source of
distinct per-cell addresses is the synthesis defaults (in=CELL_ID, out=CELL_ID+1)
in physical mode — which is exactly the physical-mode chain shortcut.

## Addressing model correction (Alan) — the real design
ICM carries the payload: configs, latches, AND the per-cell OUT address. The IN
address is NOT stored absolute — it's an offset the loader resolves. Load = create
pond -> assign ward + PTT -> drop ICM at an origin; every address inside is
relative to the pond origin (position-independent; CELL_ID+1 default is just the
origin-0 degenerate case). So per-cell out addresses arrive as ICM offsets, never
as 448 individual targeted SET_OUTPUTs — the command dual-use problem only bites
for IRREGULAR per-cell addresses set after the fact (fan-out trees), not for
relocatable blocks.

## Direction to spec (NOT built — freeze on paper first)
Generalise boot from single-broadcast-address to RANGE/BLOCK boot: carry
[block_start_id, block_end_id] + origin; each cell in window sets base =
origin + (CELL_ID - block_start); ICM offsets ride on top. Range-addressed (a
block, not per-cell) so it sidesteps the cpu_addr collision. Add an assign +
read-back handshake: loader assigns origin, block confirms realised start/end =
the programming info needed later (also where DSP-anchor / .isi seed-coords plug
in). Irregular non-structural per-cell out addresses still need the decoupled
target/payload encoding (take address payload from cmd_data[31:16], target stays
[15:0]; add opcode 3 to boot-targeted) — DEMOTED to "for irregular topologies",
bank it. The block-origin boot extension touches the ICM header (origin binding)
and the loader — design on paper, freeze once, then RTL.

## Verification assets added/used (reusable, iverilog seconds)
- fpga/verilog/tb_zone_chain_probe.v — per-cell a_arrived dump + per-fire address
  log. Proves the re-arm bug and its fix. (bus-trace + addr-target dumps were
  scratch; re-derivable from this.)

## Commits this session
- (this commit) fix: drop redundant local re-injection in zone arbiter
  (double-drive re-arm) + tb_zone_chain_probe.v + session log

## Standing notes (unchanged)
- Sim-first proven again: the re-arm was invisible at the counter level; only the
  per-cell arrived dump + bus trace exposed it.
- Build = 6 Verilog files, no IP regen for this change. Push via PAT URL (rotate
  after). git status "ahead N" is a false alarm — ls-remote is ground truth.

## CORRECTION + preliminary full-die boot model
Refined the boot model per the architecture intent (two earlier missteps fixed):
- Address is a flat BIT-FIELD: (block<<5)|cell — cell in [4:0] (32/block), block in
  [8:5] (16 blocks), 9 bits inside the 16-bit local address. CELL_BASE = ZONE_ID<<5
  (was ZONE_ID*NUM_CELLS). Block N owns N*32..N*32+27.
- REVERTED BOOT_COMMIT to BROADCAST. It is the final AUTH COMMIT (auth is 0000
  during the walk, so one broadcast BOOT_COMMIT sends the auth code to all cells
  and flips good cells to RUN). The per-cell walk is health-check + address, using
  the targeted address opcodes, NOT BOOT_COMMIT. So broadcast BOOT_COMMIT is NOT a
  bug to remove — it has a real job as the last bootstrap step. (Earlier note about
  updating shore/silicon tcl for targeted BOOT_COMMIT is withdrawn.)
- Removed tb_boot_walk.v (used targeted BOOT_COMMIT) — superseded by tb_die_boot.v.

tb_die_boot.v — PRELIMINARY model of the silicon full-die bring-up (4 blocks x 28
cells in sim, scales to 16x28=448): PHASE 1 walks every cell in flat-address order,
probes it (readback = health check), builds the flat block map and a BAD-CELL TABLE
in the boot-RAM area (one simulated defect @ 0x0022 tabled + skipped, 111/112 good);
PHASE 2 broadcast BOOT_COMMIT auth commit -> all cells RUN. Result: flat map
0x0000..0x007b, defect skipped, authed+RUN.

Still TODO (next): relocatable block-base as a RUNTIME register (controller assigns
each block its base in one op; cells offset by local index) for multi-card / block-
granularity relocation — currently the base is the synthesis position ZONE_ID<<5.
The bad-cell skip is modelled at the controller (boot RAM) level, which is correct;
wiring the skip into address assignment is the relocatable version's job.

Regressions green: tb_zone_chain fires=15; tb_zone_inject out=0x01002340@0x200
(broadcast BOOT_COMMIT restored); tb_die_boot 111/112 + auth commit.

## Single-zone adder + chaining + addressing test (no rebuild)
"It's a bootloader change, test one set of cells" — for ONE zone, zone-0 physical
addressing is flat 0..27, identical to the flashed bitstream, so NO FPGA rebuild:
it's all in the test/boot tcl. Built sim + silicon tcl:

- tb_zone_adder.v (sim, PASS): half-adder primitive on cell 0 + OR chain.
  XOR(0x0C,0x0A)=0x6 (sum), AND(0x0C,0x0A)=0x8 (carry), chain ripples fires>=2
  data 0x2340 intact. Key: arbitrary operands come from TWO INJECTS (inject A =
  1st arrival -> stored; inject B = 2nd arrival -> fires topology(A,B)). The
  preload sel field writes only fixed 0x0/0xFFFFFFFF patterns, NOT cmd_data.
- fpga/zone_adder.tcl (silicon, existing bitstream): same sequence on cell 0.
  Topology in RECONFIGURE low bits: XOR=0x0BC AND=0x007 OR=0x024, base 0x52800800.

Adder note: a cell does a BITWISE 2-input boolean op across the 32-bit word, so a
single XOR cell = 32 parallel half-adder sum bits, AND cell = 32 carry bits. The
full multi-bit adder (carry propagation / Kogge-Stone) is a multi-cell structure
chained by address — the building blocks (XOR sum, AND carry) are now proven.

Reminder for silicon: only unicell_array.v/unicell_zone.v changed since the proven
bitstream (bus_valid<=!cmd_valid bridge fix + flat CELL_BASE), both no-ops for
zone 0. zone_adder.tcl runs on the CURRENT card with no reflash.

## zone_adder.tcl — rewritten to proven preload+trigger (silicon run #1 failed)
First silicon run of zone_adder.tcl gave out_count=0 on all three sub-tests. Root
cause: it used TWO self-stored arrivals (inject A, then inject B) for arbitrary
operands — the exact pattern shift_primitive_v2.tcl flags as UNPROVEN over ISSP
(no cell fires). Confirmed preload can only load 0x0 (sel=01) or 0xFFFFFFFF
(sel=10), never an arbitrary a_data, so mixed-operand sums can't run over ISSP.

Rewrote zone_adder.tcl to the PROVEN preload->single-trigger pattern:
  CHAIN: OR(0,B)=B ripples (or_chain pattern, default output).
  XOR gate: preload A=0xFFFFFFFF, trigger B=0x0A -> ~B = 0xFFFFFFF5 (genuine flip).
  AND gate: preload A=0xFFFFFFFF, trigger B=0x0A ->  B = 0x0000000A.
  XOR vs AND give different outputs for the same B => topology select proven.
Each sub-test self-contained (own reset) — the earlier run's chain also failed,
likely accumulated state + lingering SET_OUTPUT 0x200 across shared sub-tests.
Sim-verified the gate values (tb_gate): XOR->0xFFFFFFF5, AND->0x0000000A.

No reflash needed (PC restart only drops the JTAG session; bitstream intact).
NOTE: tb_zone_adder.v (sim) keeps the two-inject mixed-operand version (0x0C+0x0A
-> sum 0x6 / carry 0x8) — it proves the adder MATH is correct in RTL. The ISSP
two-arrival limitation is a separate silicon/probe issue, and real multi-operand
arithmetic is where the packed shift adder (packed_shift_adder.py) takes over.

## SILICON PASS: single-zone gate + chain (zone_adder.tcl) — 3/3
Reflashed Unicell-Q.sof from Quartus (PC restart had wiped the volatile SRAM
config — slot-powered Mustang). Re-ran zone_adder.tcl, all PASS on the Arria 10:
  chain   armed=448 out_count=28 out_addr=0x001c out_data=0x00002340  PASS
  XOR ~B  armed=448 out_count=1  out_addr=0x0200 out_data=0xfffffff5   PASS
  AND B   armed=448 out_count=1  out_addr=0x0200 out_data=0x0000000a   PASS
Chain rippled full 28 cells, value intact (chaining + addressing confirmed). XOR
(0xFFFFFFF5) vs AND (0x0000000A) for the SAME B => topology select genuinely works
on the fabric — gates compute, not passthrough. Adder building blocks proven.

REFLASH-FIRST LESSON: Mustang-F100 config is volatile SRAM, powered from the PCIe
slot. Any host power event (restart/sleep/PCIe re-enumeration) drops the design;
ISSP still enumerates the device IDCODE (hardwired) but armed=0 / all reads zero.
Symptom of lost config = armed=0 after a RECONFIGURE that should arm 448. Fix:
reflash Unicell-Q.sof before any silicon session.

PROVEN ON SILICON now: OR chain (28-cell ripple), XOR gate, AND gate, addressing,
preload->single-trigger path.
STILL SIM-ONLY: mixed-operand add 0x0C+0x0A (ISSP two-arrival limit), flat
CELL_BASE / bus_valid (never recompiled - needs Windows node-locked Quartus),
packed shift adder (needs sub-nibble shift).

## Sub-nibble shift primitive (barrel shifter) — sim proven
Replaced the cell's nibble-only shift ladders (bus_data_shifted / computed_shifted)
with a barrel shifter. Encoding stays backward-compatible: shift_amt =
cmd_data[3:0]*4 + cmd_data[5:4], so cmd_data[5:4]==0 reproduces the proven nibble
shifts exactly, and [5:4]=1..3 adds the sub-nibble bits the packed KS adder needs
for spans 1 and 2. Range 0..31 bits.
Sim proof (tb_shift, shift_out on A=0xFFFFFFFF): >>1=0x7FFFFFFF, >>2=0x3FFFFFFF,
>>4=0x0FFFFFFF, >>8=0x00FFFFFF, >>16=0x0000FFFF, >>5=0x07FFFFFF. All pass.
Regressions green: zone_chain fires=15, zone_inject out=0x01002340, zone_adder OK.
RTL-only (not recompiled to .sof yet) — silicon still has nibble ladder until reflash.

## DESIGN WALL surfaced — shift amount is coupled to the data value
Running the packed adder as a fabric STRUCTURE (not just the primitive) hits two
things the sub-nibble shift alone does not solve:
1. shift_amt lives in cmd_data[5:0] — the SAME 32-bit field as the data value on a
   shift_IN inject. So a LEFT shift (shift_in_en) of an ARBITRARY value collides:
   the value's low 6 bits ARE the shift amount. shift_OUT (right) is clean because
   the value sits in a_data (PASS_A) and the amount rides the ignored trigger B.
   But the packed KS prefix uses LEFT shifts (G << span) on arbitrary words.
2. shift is TRANSIENT (per-command), not stored per-cell. Autonomous cell-to-cell
   chain flow (or_valid->bus) carries no command, so a chain cell can't apply a
   per-cell shift on data passing through it.
=> To run the 22-cell packed adder as a structure, the shift amount should move to
   spare cmd_bus bits (decoupling it from the data word) AND/OR become a stored
   per-cell config field (so each SHL cell holds its span). That is a command-
   encoding design decision — flagged for Alan, not guessed. The primitive is in;
   the orchestration needs this next.

## Command-emit cell — the fabric can command itself (root hole closed)
Root problem surfaced: cells only DRIVE the data bus (out_addr/out_data/out_valid);
nothing in-fabric drives cmd_bus/cmd_data/cmd_valid — those are external-pin-only.
So "the controller generates commands" was circular (Shore/tiles ARE cells). And
making cells emit commands does NOT make them ALUs *provided the command content
arrives as data*: the cell holds no program flow, the richness (opcode/gating/auth)
is assembled as data upstream, ordering is the fabric topology.

DESIGN (Alan): command-emit is a CELL TYPE, not a new latch bit (cmd_latch is full,
all 32 bits allocated). Reserved topology code TOPO_COMMAND_EMIT=0x3C0 (outside the
gate space 0x000..0x0BC). An emit cell on fire drives a_data -> cmd_bus and
output_address -> cmd_data (the target), instead of a gate result onto the data bus.
Auth is the cell's own stored auth_mask (nothing transmitted in). The trigger is the
SECOND data arrival (value ignored) — so the command lands in sync with the data
wave that feeds the commanded cell; ordering solves itself via tree placement.
Command-emit is sparse/local (only transient cells need it; the rest just flows).

RTL (unicell.v): added outputs cmd_emit_bus/cmd_emit_data/cmd_emit_valid + a
cmd_emit buffer mirroring out_buf. On new_data, is_command_cell routes to the
emit buffer (a_data, {0,output_address}) instead of out_buf; drains on odd_phase.
Existing instantiations leave the new outputs unconnected (no array/zone plumbing).

PROOF (tb_cmd_emit.v): cell0 = COMMAND_EMIT, a_data=SET_LOGICAL(0x0E), output_addr=7;
trigger arrival -> cell0 emits cmd_bus=0x0E cmd_data=0x07; cell1 (its cmd bus fed by
cell0's emit) reconfigures itself: input_addr 1->7, physical_mode 1->0. NO controller
in the loop. Regressions green (zone_chain/inject/adder).

REMAINING (design, not blockers): command-bus ARBITRATION in the zone (multiple
emitters + external pin need cpu>n>s>e>w-style discipline); the emit currently fits
TARGETED commands (cmd_data={0,target}) — commands needing a separate payload need a
second stored word or a second emit cell; and the AUTH lockdown for who may hold
topology 0x3C0 (highest privilege). Conduit is proven; zone-level routing is next.

## v3.0 cell — COMMAND_EMIT opcode + review tightening (external review applied)
Bumped unicell.v to Protocol v3.0 (major: command-emit cells). Added the missing
opcode (external review caught that nothing set topology 0x3C0):
  CMD_TOPO_COMMAND_EMIT_COLD = 0x46 (disarmed), CMD_TOPO_COMMAND_EMIT = 0x47 (armed)
sets topology=0x3C0 the same cold/armed way as the other CMD_TOPO_* presets. Proven:
opcode 0x47 turns a cell into an emitter and tb_cmd_emit passes via the opcode path
(cell1 addr 1->7, phys 1->0). Topology 0x3C0 via RECONFIGURE still works too.

Review points applied (the relevant ones):
- group_tag documented in BOOT_COMMIT header (cmd_data[31:24] = gate-filter group).
- bus_hit/cmd_valid time-multiplex rule made explicit ("commands and data are
  time-multiplexed, not concurrent; a same-cycle command suppresses the fire").
- shift comment unified to bit-granular (sub-nibble) in the v3.0 header note.
- emit-path SECURITY comment: a_data only writable under auth_ok; any future
  raw-write-to-a_data opcode must stay auth-guarded.
- dbg_armed clarified (= start_flag only, not full fire-readiness).
- ARRAY_RESET / COMMAND_EMIT documented in header.
Deferred (optional niceties, noted not done): ENABLE_COMMAND_EMIT parameter to
strip the emit path for tiny fabrics; dbg_is_command_cell scan bit. Both are array-
port plumbing; worth doing when the zone-level emit routing is built.

Docs: added "Command-Emit Cells \u2014 The Fabric Commands Itself (v3.0)" section to
ARCHITECTURE.md (root problem, mechanism, why-not-an-ALU, auth, what it unlocks,
open design surface: arbitration / payload-vs-target / auth lockdown).
Regressions green: zone_chain, zone_inject, zone_adder, cmd_emit (opcode + RECONFIGURE).

## Command-emit ROUTED through the fabric (v3.0) — silicon-ready
Wired the emit path through the hierarchy so a COMMAND_EMIT cell actually commands
other cells (previously the emit outputs dangled in the array):
- unicell_array.v: collect each cell's cmd_emit_*; FIRST-CUT priority arbiter
  (lowest index wins, simultaneous emitters dropped — real queue/fairness is a
  later decision); winner muxed into an EFFECTIVE command (eff_cmd_bus/data/valid,
  eff_cpu_addr) that drives the same targeting/decode as a host command; emit_count
  counter output.
- unicell_zone.v: emit_count passthrough.
- top_arria10.v: z_emit[16], .emit_count on all 16 zones, total_emit aggregation,
  connected to issp_host.
- unicell_issp_bridge.v: emit_count input; readable via the EXISTING snap_armed mux
  at selector 3 (src_cpu_bus[1:0]==3) — NO probe-width change, NO IP regen.

SIM PROOF (tb_zone_emit.v): cell0=COMMAND_EMIT (opcode 0x47), a_data loaded via
CMD_SWAP_AB (ISSP-friendly, no two-arrival), single trigger -> cell0 emits
SET_LOGICAL to cell5; cell5 reconfigures (phys 1->0), cell6 UNTOUCHED (targeting
works), emit_count=1. Regressions green (zone_chain/inject/adder).

SILICON: fpga/zone_emit.tcl — configures cell0 emitter, SWAP_AB-loads a_data,
triggers, reads emit_count via probe selector 3. emit_count>0 = fabric commanded
itself on the Arria. (Probe only surfaces cell0, so emit_count is the silicon
observable; full target-reconfigure is sim-proven.)

REBUILD SET (Windows Quartus): unicell.v, unicell_array.v, unicell_zone.v,
top_arria10.v, unicell_issp_bridge.v. All elaborate clean (only external issp/
uart_bridge IP unresolved in the iverilog sandbox). This bitstream tests BOTH
sub-nibble shift AND command-emit. After this passes on silicon, the Verilog truth
includes the fabric commanding itself -> VM/compiler/composer/Trix re-cost + rewrite.

## v3.1 cell — edge model removed, command-cell flag on bit 10
Settled change (the sure thing, landed with regression proof):
- EDGE MODEL REMOVED entirely. The pos/neg-edge path is gone; the latched
  two-arrival model is the only model. Deleted: edge_mode wire, edge_detected,
  prev_data reg (+reset +update), the edge branch in input_val and new_data, the
  !edge_mode gate on first-arrival store. invert_out STAYS (real standard-mode
  output invert at drain); only its edge-polarity use went.
- COMMAND-CELL FLAG moved to cmd_latch[10] (the freed edge_mode bit):
  is_command_cell = cmd_latch[10] — a single-bit tap, NO comparator. Sits directly
  above topology[9:0]. The topology==0x3C0 comparator (448 of them) is deleted.
  TOPO_COMMAND_EMIT localparam retired; 0x3C0 no longer special.
- Two writers, both verified: opcode CMD_TOPO_COMMAND_EMIT (0x46/0x47) sets bit 10;
  RECONFIGURE/ICM lays bit 10 in the config word directly (cmd_data[10], with
  start_flag at cmd_data[11]). May become opcode-only later — cell side unaffected
  (detection stays one tap).
Tests: tb_zone_emit PASS via BOTH the opcode path and the direct RECONFIGURE path
(cell5 commanded phys 1->0, cell6 untouched, emit_count=1). Regressions green
(chain/inject/adder); shift 5/5 supported amounts.

NEXT (proposed, test-first — NOT yet built): gating acts on incoming DATA as a
positional mask (0=pass,1=block), gate selects ONE contiguous nibble-aligned field
(contiguity made unrepresentable in the encoding), shifter aligns it (compact-
left/right, wiring-only). Open: mask-on-data as input stage FEEDING the gate tree
vs REPLACING it — the worked packed Kogge-Stone stage decides it (one-operand select
vs two-operand compute). byte-spread (both shift bits) flagged weakest, needs a named
consumer. First artifact is a sim, not a commit.

## v3.1 PROVEN ON SILICON + 64-bit setup-model design settled (session 2026-06-27)

### SILICON PASS (Arria 10 GX660, USB-Blaster, IDCODE 0x02E250DD)
Full 16-zone build fit CLEAN (the barrel-shifter hang is gone): Auto Fit, router
avg 23% / peak 46% interconnect, hold timing met with 1.6% pad. .sof flashed.
- zone_adder.tcl: armed=448, chain out_count=28 @0x001c=0x00002340 PASS;
  XOR(0xFFFFFFFF,0x0A)=0xFFFFFFF5 PASS; AND=0x0000000A PASS. XOR!=AND => topology
  select works on silicon. v3.1 cell (edge removed, comparator removed, bit-10
  command flag, fixed-ladder shifter) came up clean, NO regressions.
- zone_emit.tcl: emit_count 1->5 on probe selector 3. Command-emit routed THROUGH
  the array arbiter, firing on real silicon — fabric commands itself. HEADLINE PASS.
  (Note: emit_count is free-running, not zeroed on array-reset, so read the DELTA;
   armed=0 at start is just pre-arm reset state, not lost config.)

=> v3.0 + v3.1 cell model now stands on TESTED VERILOG TRUTH.

### CELL MODEL SETTLED THIS SESSION (all committed)
- v3.1: edge model REMOVED entirely (latched two-arrival is the only model);
  command-cell flag = cmd_latch[10] single tap (was edge_mode) — deletes the
  448 topology==0x3C0 comparators. Both writers verified (opcode + RECONFIGURE).
- shift reverted to fixed-pattern ladder (constant shifts = free rewiring);
  variable barrel shifter was the fitter-hang cause. Set {1,2,4,8,12,16,20,24,28}.
- shift framing corrected: NOT left/right but IN-shift (always left, before gate)
  and OUT-shift (always right, after gate); two position bits = 4 states
  {none,in,out,both}; both@same amount = edge-TRIM (free band-pass). One shared
  amount in cmd_data[5:0]. KS adder PROVEN to need input-side shift (test in
  tests/design/test_ks_needs_input_shift.py: input 20000/20000 vs output-only 7/20000).
- gating reworked (DESIGN, test-first, NOT built): data mask is a per-NIBBLE
  positional mask (8 bits, 0=pass/1=block) on the INPUT operand, BEFORE the gate
  tree (feeds it, does NOT replace it). Contiguity enforced at LOAD time, not in
  the cell. The old gate_enable/gate_set were a COMMAND group-filter (drift) —
  being dropped (option 2), the cell keeps address targeting only.

### NEXT POINT TO BE DONE — the 64-bit setup-model cut (design DONE, RTL not started)
Design note: docs/design-notes/cmd_latch_64bit.md (canonical).
- cmd_latch grows 32 -> 64. Lower 32 unchanged; upper 32 holds the SETUP that moves
  off the per-fire bus: nibble_mask[7:0]@[39:32], mask_en@[40], shift_amount[5:0]
  @[46:41], in_shift_en@[47], out_shift_en@[48]. 17 used, [63:49] reserved (15 bits).
- Shift + mask become STORED SETUP (written once via opcode/RECONFIGURE), not per-fire
  bus modifiers. A configured cell then fires on a bare trigger. cmd_bus[8:20]
  modifier band is RELEASED. Runtime bus -> opcode + auth; cmd_data -> address/auth,
  carrying setup payload only during a SET_* write.
- Command-word (setup) encoding: two 8-bit opcode slots [7:0]=A, [15:8]=B;
  bit16 = slot A is topology(0)/methodology(1); bit17 = slot B extends methodology
  to 16-bit; bit18 = arm (asserted only on the completing pass). auth = 8 bits
  (DECIDED: keep 8, NOT 11 — lower 32 is full, no reshuffle). Four write states with
  topology written only when bit16=0, methodology only when bit16/17 set — blank-slot
  zero-wipe structurally impossible.
- Pass cost: topology / topology+shift / topology+mask = ONE pass. Only
  topology + (shift AND mask together) = two passes. Never three.
- REQUIRED before RTL: format-version bump + refuse-to-load guard (32-bit artifact
  vs 64-bit cell = silent corruption); ICM serialiser + VM cell model + compiler
  config-word writer all widen to 64. This is the "everything on tested Verilog
  truth" rewrite, now triggered.

### AFTER 64-BIT: lanes (SIMD), design-scoped only
- 3-bit lane field in reserved space: 1x32 / 2x16 / 4x8 / 8x4 sub-lane subdivision,
  affects data flow. ORDER DECIDED: SHIFT-THEN-LANE (full-width shift stays untouched
  and proven; lane control is a cheap post-shift boundary MASK/clear, not 8 shifters).
  Gives TRUNCATE semantics for free; cross-lane carry only in 1x32 mode (which is
  where the add runs, so nothing lost). Keep lanes REGULAR/binary; irregular semantic
  fields (date ymd) stay an interpretation layer, NOT silicon. Boundary muxes may
  DELETE the adder's mask-faked lane separation — prove on one worked KS stage.
- Branch table may collapse into the command-emit primitive (single-pass
  configure-and-arm = "become this then run") — explore later, not now.

### STEPPED ORDER (each proven before the next leans on it)
1. v3.1 silicon  ✅ DONE this session
2. 64-bit setup-model cut  <- NEXT
3. lanes (shift-then-lane SIMD)  <- after 2 is silicon-proven

## Packed-adder-on-silicon attempt — exposed two real blockers (added to design note)
Tried to build the packed KS adder as an ISSP test before the 64-bit cut. Could not
build it on the current command path; the attempt surfaced (now in cmd_latch_64bit.md):
  1. RECONFIGURE(4) is BROADCAST — only SET_INPUT_ADDR(2)/SET_LOGICAL(14) target one
     cell. You can target a cell's ADDRESS but NOT its TOPOLOGY. So a heterogeneous
     21-cell circuit can't be configured via commands (each RECONFIGURE overwrites all).
     => NEW REQUIREMENT on the cut: SET_* setup opcodes must be per-cell TARGETABLE.
        Without it the fabric can't self-reconfigure into a heterogeneous shape, which
        is what command-emit is for. RECONFIGURE-broadcast is the thing to fix.
  2. Shift amount entangled with operand (shift_amt=cmd_data[5:0]=the inject value's
     low bits). Already fixed by setup model (shift becomes stored config).
  3. Shift itself CONFIRMED CORRECT single-cell: 0x041<<4=0x410, shift_amt=4. The
     fixed ladder is sound. (Multi-cell 0x4100 was the broadcast collision, not a bug.)
CONSEQUENCE: packed adder proves on silicon only AFTER the cut (targetable config +
stored shift). Pre-cut ISSP harness = single-cell/uniform only. Strong evidence FOR
the cut — its two blockers are exactly what the setup model removes.
RUNNABLE NOW on the flashed bitstream: shift_diag_v3.tcl (single-cell shift on silicon).

## Per-cell TARGETED config — the broadcast blocker FIXED (array + cell)
Implemented the targeting fix the packed-adder attempt demanded. Now ANY command
can target a single cell:
  cmd_bus[8]    = target_en   (0 = broadcast as before, 1 = targeted)
  cmd_bus[16:9] = target_addr (the reclaimed gate_enable/gate_set bits)
The cell's old gate_match command group-filter is REMOVED (option-2 reclaim done in
the cell too) — the cell now just obeys the array's cmd_valid; the array does all
address gating. So the reclaimed bits become a real per-cell target instead of a
vague group filter.
PROVEN (sim): targeted RECONFIGURE cell0->XOR(0x0BC), cell1->AND(0x007), cell2
untouched — two DIFFERENT topologies on two cells, impossible this morning. Broadcast
(target_en=0) still reaches all; ALL regressions green (chain/inject/adder/emit).
Files changed: unicell.v (gate_match/group_tag removed), unicell_array.v (target
decode + cell_cmd_valid gating). Needs a REPROGRAM. Silicon test: fpga/zone_target.tcl
(targeted cell0->XOR, then target cell1->AND, confirm cell0 still XOR = exclusion).

This is the loader primitive: an ICM file = a list of (target_addr, config) records,
each a targeted RECONFIGURE. Heterogeneous circuits (the packed adder's 21 cells) are
now command-loadable. Separable from the 64-bit cut (targeting, not width); carries
forward unchanged. NEXT after reprogram: ISSP/UART ICM-file streaming on this primitive.

## CMD_LOAD_AT — per-cell targeting done RIGHT (address lane), + canon hardened
Replaced the wrong cmd_bus side-door with Alan's model and made it canon so it can't
drift again.
- CMD_LOAD_AT (opcode 23): the cell's OWN addr_match gates a targeted reconfigure.
  Target on the full-width ADDRESS LANE (bus_addr), config in cmd_data, auth in cmd_bus.
  auth_mask write boot-only (physical_mode). PROVEN sim: cell0->XOR, cell1->AND, cell2
  untouched (tb_zone_target). Security PROVEN (tb_sec): auth_mask=0x5A cell rejects
  unauthed reconfigure, accepts auth-matched. Regressions green (additive).
- Side-door (cmd_bus[8]/[16:9] target) REVERTED earlier this session. gate_match
  command group-filter removed from the cell (option-2 reclaim).
- CANON: docs/ARCHITECTURE.md now carries "Addressing & Command Authority — INVARIANT"
  (one comparator gates both lanes; target on the address lane never the command word;
  auth write-once boot-only; opcodes the only post-boot authority; the cmd_bus-target
  anti-pattern is named + permanently rejected). Also fixed a stale spot: command-emit
  flag is cmd_latch[10] bit tap, NOT topology 0x3C0 comparator.

### DRIFT NOTE (for next session — do not repeat)
The cmd_bus side-door happened because the assistant proposed a NEW targeting path
instead of reaching for the address comparator that already existed. The fix: before
adding any command/auth/targeting mechanism, READ the ARCHITECTURE.md invariant FIRST
and state which existing mechanism the new one duplicates. The address is identity and
is full-width — it never goes in the command word. This is settled; see the invariant.

### NEXT (stepped, each proven before the next)
1. Alan reflashing v3.1 + CMD_LOAD_AT build (unicell.v changed; unicell_array.v reverted
   to broadcast/boot-targeted). Confirm zone_adder/zone_emit regressions on silicon.
2. Bring CMD_RECONFIGURE auth-write under the physical_mode gate (clause 3 everywhere).
3. TARGET LATCH in top_arria10.v + ISSP bridge: SET_TARGET(addr) holds the address lane,
   CMD_LOAD_AT(config) lands on it. = ICM-streaming primitive (two-word pairs, no IP regen).
4. zone_target.tcl on silicon (per-cell config), then ICM-direct streaming, then the
   packed adder becomes loadable on silicon (its 21 heterogeneous topologies).

## TARGET LATCH built (top) — CMD_LOAD_AT transport, ICM-streaming primitive (sim)
The transport that lights up CMD_LOAD_AT on silicon. TOP-ONLY change; cell untouched.
- top_arria10.v: load_target reg + SET_TARGET (opcode 24, cells ignore it) latches
  cpu_data[15:0] and HOLDS it; cpu_addr_w for CMD_LOAD_AT(23) reads load_target, not
  cpu_data — so target (held) and config (cpu_data) never collide. The hold also fixes
  the registered-bus skew for free (address settled between the two pulses).
- PROVEN (tb_top_target.v): ICM stream of (SET_TARGET addr, LOAD_AT config) pairs
  configured cell0->XOR, cell1->AND, cell5->OR through the real latch logic. This is
  the ICM-file primitive: an ICM = a list of (target_addr, config) pairs.
- Silicon test fpga/zone_target.tcl: reads cell-0 cmd_latch via probe view selector 3
  (bridge already exposes dbg0_cmd_latch there). target cell0=XOR -> latch 0x0BC;
  target cell1=AND -> cell0 latch STILL 0x0BC (exclusion). NEEDS A REFLASH (top changed).
- Canon updated: ARCHITECTURE.md invariant status — target latch DONE(sim), was TODO.

### NEXT
1. Reflash with the target-latch build (top_arria10.v changed; cell/array unchanged
   from the CMD_LOAD_AT flash). Run zone_adder/zone_emit (regression) then zone_target.
2. Then ICM-file streaming over UART/ISSP (loop (SET_TARGET,LOAD_AT) pairs from a file).
3. Then the packed adder loads as a heterogeneous ICM -> silicon proof of the 22-cell adder.
4. Still open: bring CMD_RECONFIGURE auth-write under physical_mode (clause 3 everywhere).

## SILICON PASS — target latch + CMD_LOAD_AT per-cell config on the Arria 10
Reflashed with the target-latch build; all three tcls green on hardware:
- gate+chain: chain out_count=28, XOR=0xFFFFFFF5, AND=0x0000000A (XOR!=AND) — PASS
- command-emit: emit_count 1->5 — PASS (no regression from the top change)
- zone_target (NEW): LOAD_AT cell0=XOR -> cell0 latch=0x0BC PASS; then LOAD_AT cell1=AND
  -> cell0 latch STILL 0x0BC PASS. Per-cell config + EXCLUSION proven on silicon.
=> CMD_LOAD_AT + target latch move from sim-proven to SILICON-PROVEN. The morning's
   broadcast blocker is gone on hardware: addressing is the gate, a command to cell 1
   cannot disturb cell 0. Bottom level of the addressing hierarchy proven on the die.

NEXT (unchanged): ICM-file streaming (loop (SET_TARGET,LOAD_AT) pairs, offset-native per
the relocatable-models canon) -> packed adder as first heterogeneous ICM on silicon.
Loose end: CMD_RECONFIGURE auth-write under physical_mode (clause 3 everywhere).
