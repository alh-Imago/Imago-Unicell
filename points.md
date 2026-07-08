# POINTS.md — ideas raised this session, worth re-examining for the cluster-mesh version

Consolidated from sessions/latest.md (and the conversation it was drawn from) into one
place, since a lot of ground was covered and ideas surfaced throughout rather than in
one tidy pass. Organized by theme, not chronology. Each point notes its current status
(resolved / open / just an idea) so re-reading this later tells you where to pick up.

---

## 1. Core architectural principle: control logic is RTL, not fabric cells

**Status: established, applied twice, worth keeping as a standing rule.**

The loader (`loader_fsm_v3.v`, `adder_loader_v3.v`) and the backpressure watchdog
(`zone_watchdog_v3.v`) both started as candidate in-fabric designs and both moved to
RTL for the same reason: ALMs are a different resource pool from the 448-cell (or
ASIC-equivalent) budget. The backpressure design specifically would have cost ~128
cells (29% of budget) in-fabric, or a 32x serialization penalty if shared/time-
multiplexed to avoid that cost — RTL sidesteps the tradeoff rather than picking a side
of it. "Topology is computation" describes the *workload* the fabric runs, not a
requirement that scaffolding *around* the workload also be built from NOR cells.

Worth re-examining: are there other candidate "in-fabric by default" mechanisms in the
existing tile library or trix domains that should be re-scoped as RTL under this same
reasoning? The backpressure design almost wasn't — worth a deliberate pass rather than
assuming everything else was already correctly scoped.

## 2. The bus-vs-crossbar tradeoff, and what escapes it

**Status: understood, not yet acted on beyond the address-decode fix.**

Every level of the current architecture — the 5-cell local cluster, the inter-cluster
bridge mesh — is a bus: a shared line, broadcast (or filtered-broadcast), contended.
This is not a flaw unique to one model's placement; it's a property of the
architecture's choice, recursively applied at every level. FPGA routing economics push
toward bus-based interconnect (a small number of reusable wires beats a full N-way
crossbar's routing-congestion cost); ASIC economics make genuine dedicated
point-to-point paths (real NoC/crossbar) far more affordable, since custom metal layers
can be laid out for the design's actual connectivity rather than allocated from a
shared, generic pool.

Two escape hatches identified, not mutually exclusive:
- **BRAM** for bulk data movement — already a dedicated, high-bandwidth resource, not
  bus-contended cell-to-cell traffic. Likely part of why BRAM/DSP routing through
  top-level RTL (not the cell mesh) already made sense.
- **Zone-wrapper address-decode routing** (built this session, see §4) — doesn't turn
  the bus into a crossbar, but shrinks the *contention surface* by removing irrelevant
  broadcast traffic. Still a bus at heart; a smarter one.

Worth re-examining: if/when an ASIC target becomes real, this is the point where a
genuinely different interconnect (dedicated per-edge routing, not a shared bus at any
level) becomes affordable and might be worth designing for from the start, rather than
porting the bus-based mesh as-is.

## 3. Cluster mesh: the plus-pentomino tiling and its real connectivity

**Status: geometry verified, routing table computed, richer than either of us guessed.**

Small (5-cell) local clusters tiled via the plus-pentomino (Greek cross) self-tiling
pattern, replacing one flat wide arbiter (25-28 cells) with many small local arbiters
plus point-to-point mesh links between clusters. Verified computationally (not by eye):
81 clusters/405 cells tile with zero gaps or overlaps on the lattice with basis
(1,2)/(2,-1). Real connectivity is richer than a naive glance suggests: each cluster
has exactly 4 distinct neighbors, but each arm touches *two* of those neighbors via
its 3 exposed edges (not one), and each neighbor pair shares a 3-cell-wide interface,
not a single point-contact.

**Contention analysis, three distinct categories** (worth keeping as a checklist for
any future design placed on this mesh):
1. Same-cluster local arbiter collision — two cells in the same 5-cell cluster firing
   the same cycle. Fixed by cluster-*label* placement (keep genuinely-simultaneous
   pairs apart), not always avoidable by cluster geometry alone.
2. Cross-cluster broadcast noise — a cluster's own local fire (even one targeting a
   remote cluster) or a neighbor's *irrelevant* traffic clobbering the local bus_addr
   slot. Fixed by the address-decode routing (§4).
3. Genuine cross-cluster timing collision — two *relevant* deliveries landing at the
   same cluster in the same cycle. Not fully solved; needs either careful delay-cell
   timing (see §5) or a small input queue. Real work, but now a much smaller/more
   tractable problem once (2) is removed.

## 4. Zone bridge routing (built) — now load-time data, not synthesis parameters

**Status: built 2026-07-05 (address-decode by zone), rebuilt 2026-07-06
(routing_mask, replacing zone parameters entirely). Full regression clean.**

First pass (2026-07-05): `unicell_zone64_v3.v`'s bridge outputs went from
unconditional broadcast (`bridge_X_out_valid <= za_out_valid` — harmless
with one bridge partner, genuine contention with 2-4) to address-decode,
matching each fired address's zone field against per-direction
`N_ZONE`/`N_ACTIVE`-style parameters. Fixed the contention, but left a real
gap Alan caught directly: those were synthesis-time parameters, so a
different model's routing needs would require a full Quartus rebuild and
reflash — exactly the per-target rebuild the ICM exists to avoid. Routing
behaved like a hardware fact when it's actually data specific to wherever a
given model happened to place its cells.

**Fixed properly 2026-07-06:** routing now lives in each cell's own load-
time config. `unicell64_v3.v` gained `routing_mask[3:0]` at the freed
`cmd_latch[14:11]` (inside the documented-free `[18:11]` window), set via a
new methodology opcode `METH_SET_ROUTING` (8'd34) — same pattern as
`METH_SET_SHIFT_IN`/`METH_SET_MASK`/`METH_SET_LANE`, available via
`LOAD_AT`'s bank-2 slot, the direct cycle-2 opcode, or `CMD_SET_METHOD`'s
two slots. One bit per direction (N/S/E/W); the zone wrapper checks
`routing_mask` straight off the firing cell (carried through the array's
existing output-aggregation path as a new `out_routing` signal) instead of
comparing the fired address against a synthesis-time parameter.
`N_ZONE`/`S_ZONE`/etc. retired entirely.

This gets two things at once: routing is genuinely part of the ICM's own
per-cell load data now (loaded fresh per model, no rebuild for a different
model's connectivity), and it gives real multicast for free — a bitmask
means one fire can set two direction bits and reach two neighbor clusters
at once, which a single-target parameter could never express. Likely the
correct long-term resolution to the placement/collision problems found
building the packed adder (§6, §12) — a producer needing 3 genuinely
different destinations may not need a chain of relay cells at all anymore,
just one cell with the right routing_mask bits set. Not yet re-applied to
the adder's own placement/config generation — natural next step.

**Same placement-vs-portability principle as before, now even more clearly
upheld:** a cell only ever knows its own logical routing_mask — it has no
idea which physical neighbor a given direction bit corresponds to. That
mapping (which physical wire is "north" for this zone) still lives in the
zone wrapper's own physical wiring, unchanged per deployment, while the
*decision* of which directions to use is now genuinely part of the
portable ICM data. Same relationship as a network packet's destination
(portable) versus which physical port a router forwards it out of (varies
per deployment, same packet).

## 5. Delay cells as a deliberate timing-realignment technique

**Status: used once (in the adder), didn't fully resolve the issue it targeted, but
the technique itself is sound and worth keeping as a known tool.**

Alan's framing: this is a known compiler technique for realigning data timing, and the
two-arrival model makes it always safe to apply — adding latency to a faster path
never breaks correctness, since a cell just waits longer for its second operand rather
than seeing something stale or missing. Used to try to keep a fast local G-path from
outracing a slower cross-cluster P-path in the packed adder; genuinely correct in
principle, but a single hand-picked delay cell wasn't enough (the actual collision
turned out to involve a different cell than the one targeted) — needs the timing
worked out properly (real arrival-cycle accounting per path) rather than trial
insertion. Not to be confused with the address-decode fix (§4), which removes
*irrelevant* traffic; delay cells are for spacing out *genuinely relevant* concurrent
arrivals once irrelevant noise is already gone.

Worth re-examining: build this as a proper, checked methodology (compute real
hop/cycle latency per path into every cluster, size delays deliberately) rather than
insert-and-test, the next time it's needed.

## 6. Shared-broadcast fan-out vs smart address-decode routing — RESOLVED 2026-07-06

**Status: fixed. The specific conflict described below is resolved; see §12 for a
deeper, related hazard found while re-verifying the fix.**

Two mechanisms built independently, both individually correct, that conflict when
combined without a placement constraint neither of them enforces on its own:

- The automatic relay-insertion pass (for fan-out — see §7) sometimes has a relay cell
  listen at a *borrowed* address (its "natural" sibling's own address) so both catch
  the same producer's single broadcast. This only works if the broadcast genuinely
  reaches every listener, wherever they physically live.
- The address-decode fix (§4) makes exactly one address route to exactly one owning
  cluster (by CELL_BASE) — correctly *stops* broadcasting elsewhere.

Combined without a constraint: if a relay and its sibling land in *different*
clusters, the relay never receives anything (confirmed via trace — stays primed
forever). Neither mechanism is wrong; they were never checked for compatibility.

**Real fix, not yet applied:** add a placement constraint so any two cells sharing a
broadcast address always land in the *same* cluster. A change to the clustering/
bin-packing algorithm, not the router or the relay mechanism.

## 7. Fan-out requires explicit relay cells — a hardware constraint the whole tile library may not respect

**Status: fixed for this one design (verified via 10000 random cases, automatic
insertion not hand-reasoning); implication for the REST of the tile library is open.**

A cell has exactly one `output_address` per firing. Any value read by more than one
consumer needs an explicit relay cell (`PASS_B` + `latch_in`, `CMD_SWAP_AB`-primed) per
extra destination — this is structural to prefix-computation trees generally, not
specific to the packed adder. Got the relay placement wrong twice reasoning about it
by hand before building an automatic insertion pass and verifying it algorithmically.

**Open, larger implication:** the wide Kogge-Stone adder (482-548 cells) almost
certainly has values with the same fan-out pattern (a prefix-tree value feeding two
downstream stages) and has never been checked against this constraint. More broadly,
`packed_shift_adder.py`'s cell-plan function had a real *algorithm* bug (see §8) that
went uncaught because nothing ever ran it end-to-end — only the separate reference
function was tested. **No existing tile's cell count or correctness should be assumed
safe until it's been similarly re-verified: built as real cells (or simulated
cell-by-cell), not just checked algebraically.** This is the same finding flagged in
AUDIT.md and sessions/latest.md as sitting alongside the trix-files thread (§9) —
worth being one deliberate audit pass, not discovered piecemeal per tile as each one
happens to get used.

## 8. Real algorithm bug fixed in packed_shift_adder.py

**Status: fixed, standing, affects the shared codebase.**

`build_packed_adder_chain()` held P constant across all 5 Kogge-Stone stages, silently
diverging from the file's own reference function `packed_ks_add()` (which correctly
updates P every stage too). Never caught because the cell-plan function was never
actually run against real addition — only the separate reference was tested. Fixed;
docstring and cell-count corrected. Same "was this ever actually verified, or just
assumed correct because a related-but-different function was tested" question applies
elsewhere in the tile library (see §7).

## 9. Trix files should become .icm artifacts, not Python runtimes

**Status: flagged as a major thread in AUDIT.md and sessions/latest.md, not started.**

Every trix domain (FlowTrix, NeuroTrix, MathTrix's laplacian/mif variants, MidiTrix,
SensorTrix, NetTrix, OptiTrix) is currently a Python *program* that builds and runs a
cell graph — a bespoke per-domain runtime — not a `.icm` artifact the fabric loads and
executes on its own. Opposite of the project's own thesis (one `.icm` runs unchanged
across VM/FPGA/silicon). A category problem, not a packaging problem — the AUDIT.md
`trix/` package-layout proposal reorganizes *where* these files live, not *what* they
fundamentally are, and is now flagged premature until this is scoped.

**Why now, and why it connects to this session's cluster-mesh work:** `CMD_LOAD_DONE`
(this session) makes a real, hardware-native "this finished, safely advance" event
possible for the first time — the same event-driven shape that let the loader stop
polling with fixed delays generalizes past *loading* to a model's own *execution* step
also ending in a completion pulse. At that point a trix "runner" stops being the
runtime and becomes something that compiles to a `.icm` and reads back from it.

**Next step (not started):** pick one pilot domain (FlowTrix or the laplacian_1d_mif
base look smallest/cleanest) and work out concretely what its `.icm` shape and
completion-driven execution loop actually look like, before touching any other trix
file.

## 10. Host-triggerable control register (not started)

**Status: discussed, not built.**

Today `start_load` (in every top-level test file built this session) is a raw
testbench-driven pin. A real PCIe interface can't drive a raw pin — it needs to
*address* a register the same way it addresses BRAM data. Needed: a control register
(or small set of them) exposed through the same host_cmd_bus/data mechanism already
used for data writes, where writing a specific value to a specific address triggers
`start_load` (and presumably other control signals as they're needed) internally.
Small, well-scoped, natural next piece once picked back up.

## 11. Bridge/edge-count computation as a reusable design-analysis method

**Status: not a fix, a technique worth reusing.**

When Alan asked "how many bridges are needed," the useful move wasn't estimating —
it was computing precisely from the actual placement: count real cross-cluster edges
(not just cluster-*pairs*, which undercounts — two clusters can carry several distinct
edges between them), then take the max simultaneous in+out channel count on the
busiest cluster. For the 50-cell adder: 31 edges, 16 pairs, up to 8 simultaneous
channels on the busiest clusters — which is what revealed `NUM_BRIDGES` doesn't already
give independent channels (only pass-through slots), a genuine capacity finding, not a
guess. Worth applying this same computation up front for any future design on the mesh,
rather than discovering channel-count problems empirically.

## 12. Shared-broadcast relay can never safely share an address with a 2-operand cell

**Status: precisely diagnosed 2026-07-06, fix identified, not yet applied.**

Found while re-verifying the placement-constraint fix (§6): a relay wanting only
one producer's value can never safely share an address with a 2-operand cell
(`AND`/`OR`/`XOR`), because that cell's address is *by definition* fed by two
different producers. No renaming or relocating the shared address fixes this —
the contamination just moves wherever the address ends up, since the underlying
2-operand cell still needs both its real inputs regardless of the address number.
Confirmed the actual failure mode precisely: values don't just collide, they get
bitwise OR'd together (`unicell_array64_v3.v`'s `or_data = or_data |
cell_out_data[i]` — "wired-OR" is the literal mechanism here, not just the
architecture's name), producing a specific corrupted value rather than a clean
drop or an obvious garbage read.

**Why the earlier 10000/10000 verification (§7/§8) couldn't have caught this:**
that check simulated the algorithm by wire *name*, assuming perfect isolated
delivery per name. It proved the algorithm's math is correct; it never modeled
cells sharing a physical bus address, so a hazard that only exists at the
hardware-address-mapping layer was invisible to it. Worth remembering as a
general lesson: verifying an algorithm's data-flow correctness and verifying its
safety once mapped onto shared physical addressing are two different checks —
passing the first says nothing about the second.

**Real fix, not yet applied:** the relay-insertion pass needs to detect this
specific hazard (a pair's "natural" candidate has op in `{AND,OR,XOR}`) and
insert an *additional* relay cell automatically wherever it occurs, giving the
"wants-just-one-value" side a genuinely private address — the same way fan-out
itself was automated rather than hand-reasoned, once hand-reasoning it twice
proved unreliable (§7). Affects all 6 occurrences in the current adder design
(one per stage); cell count will grow again, roughly 50 → 56, once applied.

---

*Cross-reference: docs/design-notes/packed_adder_cluster_mesh.md has the full,
detailed write-up for everything touching the packed adder specifically (§3, §4, §5,
§6, §7, §8, §11, §12). This file is the higher-level index across all of it, plus the
threads that aren't specific to that one design (§1, §2, §9, §10).*

## 13. Open question: does MathTrix's 2-cell value-holding pattern work under the new substrate?

**Status: raised by Alan at session end, not yet investigated.**

Alan's concern: MathTrix (`mathtrix.py` and its `*_mif.py` variants — Gray-Scott,
fast-marching, N-body, PageRank, wave, Conway, Laplacian 2D) needs 2 cells to hold a
value, per his description. Not yet checked against the actual file, or against
today's findings (routing_mask, the relay/2-operand hazard, same-cluster-simultaneous-
fire collisions). Needs a real look at MathTrix's actual cell-holding mechanism before
answering either way — don't guess at compatibility next session, check the file.

Likely connects to §7's broader standing worry (no existing tile's cell count or
correctness should be assumed safe until verified the way the adder was) and to §9
(trix files becoming .icm artifacts) — MathTrix may be a good second candidate to
check once the pilot domain from §9 is worked out, given it's already flagged as
having a structural question mark.

## 14. Design rule for the routing_mask rebuild: routing bits go on working cells, not relays

**Status: agreed with Alan at session end, to apply when rebuilding the adder (and all
future models) on the routing_mask substrate. This is the explicit rule that should
guide the regeneration.**

Under the old synthesis-parameter routing, crossing a cluster boundary was a property
of the cluster wrapper, so a value reaching a neighbor effectively needed a dedicated
cell whose whole job was "sit at the edge and hand the value across." A large fraction
of the relay/anchor/spine/bridge cells that ballooned the adder (29 -> 85 over the
session) existed ONLY to move a value between clusters -- pure routing overhead, doing
no computation.

Under routing_mask, crossing is a property of the FIRING CELL itself. So the rule for
generating any model is:

1. **Set routing bits on the cell that already produced the value.** An ordinary
   working cell (AND, XOR, shift, etc.) carries its own result across a boundary by
   setting its own N/S/E/W routing bit(s) in the same fire. No separate hop cell in
   between. This is the common case and should be the default the generator reaches for.

2. **A dedicated relay cell is justified ONLY for genuinely multi-hop paths** -- reaching
   a cluster that is NOT a direct neighbor (A -> C where they don't share an edge).
   Since routing_mask is one hop only, spanning non-adjacent clusters needs an
   intermediate cell in a between-cluster to catch and re-fire. These relays have a
   specific, deliberate purpose in the model's overall geography -- they are NOT part
   of a chain or a group papering over ordinary fan-out, and should be rare.

3. **Multicast replaces most fan-out relays entirely.** A producer needing to reach
   several DIFFERENT neighbor clusters sets several routing bits at once (bitmask, not
   pick-one) -- one fire, multiple directions, no relay chain. This is exactly what
   collapsed under the old scheme into the anchor/spine/bridge machinery that kept
   hitting same-cluster-simultaneous-fire collisions all session.

Expected effect on the adder rebuild: dramatic cell-count reduction from 85, since
nearly all of that growth was cross-cluster fan-out workaround that routing_mask makes
unnecessary. Same-cluster contention (two cells sharing one cluster's local arbiter)
is unaffected and remains a real but much smaller, already-understood consideration.

Standing principle, not just for the adder: dedicated relay/bridge cells are reserved
for far-reaching multi-hop points with a specific purpose in the model's geography --
never as a default fan-out or cross-boundary mechanism, which now belongs on the
working cells themselves.

## 15. Caveat on routing_mask: it delivers to the neighbor cluster's BUS, acceptance is not guaranteed

**Status: verified against unicell_zone64_v3.v, 2026-07-07. Important constraint for the
routing_mask rebuild -- design around it rather than rediscover it.**

Setting a routing bit does NOT target a specific cell in the neighbor cluster, and does
NOT guarantee delivery. What actually happens (confirmed in the RTL, not assumed):

- A cardinal hop drops the value onto the *entire* neighbor cluster's internal bus
  (ibus), where every cell in that cluster can see it; whichever cells have a matching
  input_address pick it up, exactly like a local fire. So "goes to the next cell" is
  really "goes to the next CLUSTER's bus, and within it, whoever is watching that
  address."

- Crucially, each incoming bridge merges onto ibus gated by `!ibus_valid` -- it is only
  accepted IF that cluster's bus is free that cycle. This means it does NOT corrupt or
  wired-OR with existing traffic (good -- no silent data-mangling like the local bus).
  But if the receiving cluster's bus is already busy that cycle (its own local fire, or
  another bridge arriving the same cycle), the incoming hop is simply DROPPED. There is
  a fixed priority order N -> S -> E -> W deciding who wins when several arrive at once;
  the losers are lost, not queued.

- Contention is PER-CLUSTER, not global. Each cluster has its own independent ibus and
  its own `!ibus_valid` gate. Cluster 3 accepting a hop has no effect on cluster 7
  accepting one the same cycle -- they run in parallel. A 15-cluster design can have 15
  transactions happening simultaneously. The rule is "one transaction per cluster per
  cycle" (one local fire OR one accepted bridge hop), NOT "one transaction system-wide
  per cycle." This parallelism is exactly what the mesh-of-small-clusters buys over one
  big shared bus.

Design consequence for the rebuild: spreading work across clusters genuinely buys
parallelism, but any single cluster that becomes a CONVERGENCE POINT (several values
needing to arrive close in time) is where collisions concentrate. The design pressure
is not "minimize total transactions" but "avoid piling too many arrivals onto any one
cluster in the same cycle." routing_mask removes the fan-out RELAY overhead (§14) but
does not remove the need to think about arrival timing at convergence points -- that's
the same timing discipline (delay cells, §5; ladder scheduling) applied at the
receiving side.

## 16. routing_mask adder rebuild — real progress, placement is now a CSP (2026-07-07)

**Status: 37-cell design proven correct + collision-free in a Python event-sim;
only the joint placement constraint remains. Needs a proper solver, not more
hand-placement.**

Rebuilt the adder from scratch following the §14 rule (routing bits on working
cells, no fan-out relay chains). Big wins, all verified in Python before any RTL:

- **37 cells** (down from the 85 the relay-chain approach reached). No anchor/
  spine/bridge cells at all -- cross-cluster reach is just routing_mask bits on
  the producing cells.
- Built an **event-driven simulator** (validated placement, per Alan's call to
  stop declaring victory before checking): models two-arrival firing + one-
  transaction-per-cluster-per-cycle + routing_mask one-hop delivery. Runs in
  seconds, catches collisions Python-side instead of via multi-hour Verilog
  traces.
- **10000/10000 correct, ZERO same-cluster fire collisions** on the depth-aware
  placement -- first time all session the design is clean on both dimensions
  (algorithm AND hardware-timing) before touching RTL.

The remaining problem is placement as a genuine **constraint-satisfaction
problem** with three simultaneous constraints that pull against each other:
1. <=5 cells per cluster
2. no two same-DEPTH cells in one cluster (they'd fire the same cycle -> local
   bus collision)
3. cluster port-degree <=4 (NSEW) -- a cluster can only physically neighbor 4
   others

Hand-placement can satisfy any two but not all three at once for this graph:
- depth-aware greedy: clean depths + collisions, but one P-hub cluster wants 5
  neighbors (constraint 3 fails)
- structural stage-bundles: 4 neighbors max, but P-stage bundles put REQk and
  SHL_Pk at the same depth (constraint 2 fails)
- REQ cells pooled into one cluster (distinct depths, fixes 2): that cluster
  then touches 11 neighbors (constraint 3 fails hard -- it feeds the whole
  G-chain)

The REQ cells are the crux: they snapshot P for the G-side, so they're read by
every G-stage -- concentrating them concentrates ports, spreading them risks
depth collisions with whatever they land beside. This is exactly the kind of
coupled constraint a backtracking/CSP placer handles and hand-iteration
doesn't. Tried three hand-placements; a fourth isn't the answer.

**Next step:** write a proper placement search -- backtracking or a small CSP
(each cell -> cluster, constraints = the three above, objective = minimize
clusters then cross-edges). The event-sim already exists to validate whatever
it produces. Everything upstream (the 37-cell chain, correctness, the sim) is
done and solid; only the placer remains. Pickles: /tmp/raw_rmask.pkl (the
chain), and the event-sim code is in this session's history.

Note also: this same placer, once written, is the reusable tool §14 anticipated
-- it's what makes routing_mask practical for FUTURE models, not just this
adder. Worth building well rather than special-casing the adder.

## 17. RESOLVED — the placer problem, solved by Alan's pentacross placement rules (2026-07-07)

**Status: solved and verified. 12 clusters, 37 cells, all three constraints
satisfied, 10000/10000 correct + zero collisions in the event-sim.**

The CSP from §16 is resolved -- not by a backtracking search, but by Alan's
structural placement rules, which collapse the search to a single arrangement
that falls out of the computation's own shape. The rules:

1. A cluster is a plus-pentomino: centre + 4 cardinal arm tips. Only arm tips
   touch neighbours, so any cell that SENDS across a boundary sits on an arm
   facing its receiver; any RECEIVER sits on an arm facing its sender.
2. routing_mask's 4 bits are SIMULTANEOUS multicast, not pick-one -- one arm
   cell's single fire pushes to multiple cardinal directions at once. So a
   producer reaching several clusters needs no relay chain and no serial port
   use; it sets several bits in one fire.
3. Internal (non-crossing) cells are free -- any leftover slot, ordered by
   stage.
4. THE KEY MOVE: checkpoint/fan-out cells (the REQ cells here) ride their
   PRODUCER's cluster and multicast to consumers -- they are NOT pooled into a
   hub. Pooling them (§16) was what blew the port count to 11 neighbours;
   riding-the-producer spreads the crossings one-per-stage and drops max
   neighbours to 3.

Verified placement (12 clusters):
- P0+REQ1; G0; then per stage k=1..4: {SHL_Pk, AND_Pk, REQ(k+1)};
  per stage k=1..5: {DELAY_Gk, SHL_Gk, AND_PGk, OR_Gk}; final {CARRY_SHL, SUM_XOR}.
- Max cluster size 4 (room to spare), max neighbours 3 (under the 4-cardinal
  limit), zero same-depth co-locations.
- Event-sim (two-arrival + one-txn/cluster/cycle + multicast): 10000/10000
  correct, zero same-cluster collisions.

This is bigger than the adder: rule 4 -- "fan-out/checkpoint cells ride their
producer and multicast, never pool into a hub" -- is the reusable placement
principle that makes routing_mask practical for ALL future models, resolving
the open intent of §14 and §16. The pentacross geometry (arm tips = boundary
crossings, centre + free slots = internal) is the mental model for the
composer stage too (§ conversation trail).

REVISIT ON COMPLETE SUBSTRATE (2026-07-07, after transit primitive built):
Checked whether transit cells change the optimal placement. Finding: §17 as
first written had a real GAP -- it checked neighbour COUNT (<=4) and collision-
freedom but NOT physical MESH EMBEDDABILITY (can the cluster graph lay on an NSEW
grid with every edge unit-distance?). Max-degree-3 is necessary, not sufficient.
Resolution (now in docs/COMPILER_TILE_CONFIG.md): (a) INTERLEAVED EMBEDDING --
place each P-cluster directly adjacent to its G rung-partner, making all per-
stage rung edges unit-distance at once (took the adder's non-unit edges from 6
to 1); (b) the ONE remaining long edge, REQ1->SUM_XOR (P0 low-bit carried chain-
start to final-sum, structurally unavoidable start-to-end), is handled by a
TRANSIT PATH -- the transit primitive's (#18) first real use, routing through
intervening clusters' spare arms. The two capabilities compose: placement +
interleaved embedding localise crossings; transit handles the residual long edge.

NEXT: generate the RTL from this verified placement -- assign real cell IDs
(cluster<<5 + local), set routing_mask bits per the cross-boundary edges,
generate config + cluster wiring, compile, run in iverilog to confirm the
event-sim's prediction holds on the real substrate. Everything upstream is
proven; this is now a generation step, not a design search.

**Now canonical:** written up as a standing COMPILER/PLACER RULE in
docs/COMPILER_TILE_CONFIG.md ("pentacross placement") -- the placer must apply
it to every model, with a placer-obligations checklist. This is no longer just
an idea in this index; it is a rule the compiler enforces.

## 18. Transit cells (suppress-local routing waypoints) -- BUILT & VERIFIED

**Status: BUILT AND VERIFIED IN SIM 2026-07-07 (Stage 0 complete). Was: idea
from Alan, verified against RTL as not-yet-expressible. Now implemented: the
transit_only flag at cmd_latch[15], METH_SET_TRANSIT opcode (8'd35), out_transit
port cell->array->zone, and the local-vs-routing split in unicell_array64_v3.v.
Dedicated test tb_v3_transit.v proves it (transit=1 routes across without
driving the local bus; transit=0 control drives both), full 12-test regression
green. The design notes below are retained as the rationale/spec.**

Alan's observation: a cell placed in a cluster purely to occupy an arm and
carry a cross-border route ONWARD -- a pass-through waypoint whose own contents
the host cluster doesn't care about -- would turn every cluster's spare arms
into a routing fabric. A value could thread through several clusters' unused
arms to reach a distant (non-adjacent) point, one hop per cluster, WITHOUT that
value ever touching the host clusters' own computation. More than compaction:
multi-hop routing as a native fabric property, using spare capacity, not a
per-model relay hack.

The essential safety condition Alan attached: the transit value must forward
across the far boundary ONLY, and must NOT present onto its host cluster's
internal bus -- otherwise it injects foreign traffic into a cluster that has
nothing to do with it (exactly the convergence-point contention we spent the
session avoiding). So a transit cell must be write-ACROSS-only, never write-local.

RTL FINDING (checked, not assumed):
- As built, this is NOT expressible. In unicell_array64_v3.v (lines ~316-323)
  a single `or_valid` drives BOTH the local bus (bus_data/bus_addr) AND the
  routing output -- same signal, same winning cell. Any fire unavoidably
  presents on the host's local bus AND routes per its mask. There is no way to
  route-across-without-presenting-local today. So Alan's safety condition
  cannot be enforced: a transit cell would route correctly but ALSO dump its
  value onto the host bus, where a cell watching that address wrongly picks it up.
- The fire also consumes the host cluster's one-transaction-per-cycle slot
  regardless, so a transit cell competes with the host's own computation for
  that cycle (a real but bounded cost).

PIPELINE POSITION (confirmed in RTL 2026-07-07, per Alan): routing is tapped at
the END of the cell's datapath -- on the OUTPUT, after the ALU/shift/mask/lane
work. In unicell64_v3.v the output-buffer drain does `out_data <= ...` and
`out_routing <= routing_mask` together, downstream of out_buf_data (which already
carries any computed/shifted/masked result). So the flow is:
  input -> work (gate/shift/mask/lane) -> output drain (out_data + out_routing) -> local and/or across
This is exactly right and already built: because routing sits AFTER the work, one
mechanism serves both "pass through untouched" (a no-op cell whose input reaches
the output, then routes) and "work then pass" (a computing cell whose RESULT
routes) with no special-casing -- routing doesn't care whether the datapath
modified the value, it just takes whatever lands at the output. Tapping it BEFORE
the ALU would have needed separate route-the-input vs route-the-result logic;
tapping it after collapses both into one. CONSEQUENCE for Stage 0: the transit
build needs NO datapath reorganisation -- the routing tap point is already
correct. It is purely (a) add the transit flag, (b) at this one existing drain
point, gate whether the local-write happens (routing-write already there).

FLAG SEMANTICS (clarified by Alan 2026-07-07 -- the clean two-axis model):
The mechanism is TWO independent things, not one:
  - routing_mask = WHERE the fire goes (which N/S/E/W directions).
  - transit flag  = WHETHER the local cluster is included.
The transit flag reads as "route-only":
  - flag SET   -> data is ONLY passing through: route it out per routing_mask,
    do NOT present on the local cluster bus. Pure conduit (the transit cell).
  - flag CLEAR -> data is FOR HERE: present on the local bus as normal; and if
    routing_mask bits are also set, it goes across AS WELL (the both-local-and-
    across case the adder's ordinary working cells need).
This covers every case unambiguously:
  - normal working cell (flag clear, no routing) -> purely local
  - producer feeding own cluster AND a neighbour (flag clear, routing set) -> both
  - pure transit hop (flag set, routing set) -> across only, never touches host
Note WHY routing-presence ALONE can't be the switch: it can't distinguish
"across only" from "across AND also local" -- a producer often needs both. The
one transit flag is exactly the bit that distinguishes them. So this is the #18
suppress-local flag, but framed correctly as WHERE (routing_mask) vs WHETHER-HERE
(transit flag), not as a special "suppress" mode.

THE FIX (small, clean, reuses routing_mask's mechanism):
- Add a single "transit" / suppress-local flag on the cell, in the same freed
  cmd_latch window next to routing_mask, set by the same kind of methodology
  opcode (METH_SET_... pattern). When set, it gates OFF the local-bus
  presentation path (the local `or_valid` contribution) while leaving the
  routing path live. Semantics: "fire, route across per the mask, but do NOT
  present locally." That one flag turns this from impossible into a first-class
  primitive.
- Note this needs care in the array's or_valid logic: local presentation and
  cross-border routing, currently one signal, must be split so a transit cell
  contributes to routing but not to the local wired-OR / bus_addr.

WHY IT'S WORTH IT: makes multi-hop routing (reaching non-adjacent clusters) a
native, safe fabric capability rather than a per-model workaround, and lets
spare arm capacity anywhere on the fabric be used as routing. Complements the
pentacross placement rule (#17): that rule minimises crossings; this primitive
cleanly handles the crossings that genuinely must span distance. Reserved-relay
use from #14 becomes this primitive done properly.

SECOND-HALF FINDING (the border-IN path, checked 2026-07-07):
- An incoming bridge value does NOT go only to the targeted cell. In
  unicell_zone64_v3.v (~lines 202-232) an arrival is written onto the receiving
  cluster's SHARED ibus (ibus_addr/ibus_data/ibus_valid <= the bridge value),
  visible to every cell in that cluster; it's address-FILTERED at the receiving
  cells, not physically routed to one. So a transit value does splash onto the
  pass-through cluster's bus.
- BUT this is clean-ENOUGH by the addressing invariant: a bus value only affects
  a cell whose input_address matches. If the transit value carries an address
  that NOTHING in the pass-through cluster watches, it lands, matches nobody, and
  is ignored -- effectively a clean hop despite touching the shared bus.
- The real costs on the in-path: (a) even an ignored arrival occupies that
  cluster's ibus for the cycle (ibus_valid<=1 blocks anything else landing that
  cycle), and (b) if the pass-through cluster's OWN computation needed its bus
  that cycle, the transit arrival and local work contend for the one slot
  (N->S->E->W priority picks one, the other is dropped).

FULL SAFETY CONDITION for a transit hop (both halves together):
  1. suppress-local flag set on exit (the out-path fix above), so the transit
     fire routes across without presenting on its OWN cluster's bus; AND
  2. the transit address is unique to the pass-through cluster (nothing there
     watches it), so the border-in splash matches nobody; AND
  3. the pass-through cluster has a spare bus cycle (not contending for its own
     ibus that cycle).
So the rule is richer than "clean in, clean out": it's "suppress-local on exit,
route through clusters with a free bus cycle and no address clash." That's a
genuine placement constraint for the transit PATH, checkable by the placer, not
a free lunch -- but entirely workable.

ROUTING-HUB CONSEQUENCE (Alan): with the suppress-local flag, a single cluster
can host up to four transit cells -- one per arm -- each routing a different
value across a different boundary without any of them presenting on the host's
own bus. The cluster then acts as a genuine 4-way routing HUB: values enter on
one arm and leave on another, threading THROUGH the cluster, while the cluster's
own centre cell (or nothing) does its own work. Subject to the one-transaction-
per-cycle budget (a 4-way hub can physically route at most one hop per cycle, so
heavy hubs serialise) -- but structurally it turns any cluster into a
crossbar-like waypoint. This is the building block for genuine multi-hop
topologies and for the pentiform-cross migration's long-range routing.

NEXT (when picked up): design the flag + opcode, split the array's local-vs-
routing valid paths, verify a transit cell routes across WITHOUT local
presentation in sim, then regression. Not urgent -- the adder rebuild (#17)
doesn't need it -- but a high-value substrate addition for later models and for
genuine multi-hop topologies.

## 19. The substrate map — one authoritative artifact (Alan, 2026-07-08)

**Status: architectural decision. Not built. Sits at the seam of compiler
(Stage 4), loader, and composer (Stage 5).**

The question that forced this: does the loader need to be "shape-aware" and
test-map the substrate at runtime before loading any file? That would add a
whole extra level of difficulty (a discovery subsystem that must be correct
before anything loads; routing_mask bits no longer precomputable; every load
potentially different; the discovery itself has to be trusted). The resolution
collapses it.

**Key realisation:** the neighbour map is ALREADY fixed at synthesis time (bridge
wiring + CELL_ID arithmetic are compile-time constants baked into the bitstream;
they cannot change within a load). So runtime discovery would be an elaborate
mechanism to re-learn a constant. The map varies BETWEEN bitstreams, never
WITHIN a load -- even for a user's custom-shaped substrate (a deliberately
shaped fabric to streamline a particular process): the custom shape is still
compiled into a fixed bitstream.

**The decision:** the substrate map is a SINGLE AUTHORITATIVE ARTIFACT that:
  (a) the user AUTHORS to describe the desired shape (cluster layout, which
      cells exist, their adjacencies);
  (b) SYNTHESIS consumes to place cells and wire bridges -- so the silicon is
      generated FROM the map;
  (c) SHIPS WITH THE BITSTREAM as its descriptor (same pattern as the planned
      .isi DSP-locality sidecar -- generalised: the bitstream carries its own
      topology);
  (d) the COMPILER reads to precompute routing_mask bits OFFLINE (placement
      stays deterministic, no runtime resolution);
  (e) the LOADER's boot-walk VERIFIES against silicon.

**Why this unifies (the important part):** because the map DRIVES placement, it
IS the reality rather than a separate description that could drift. Three things
that were separate -- physical placement, the shipped descriptor, and the
CELL_ID/neighbour relationships -- collapse into ONE source. Consequences:
  - The boot-walk stops being "discover the topology" and becomes "confirm the
    fab faithfully realised the map." A mismatch = a fault (synthesis error or
    wrong-bitstream load), caught immediately, not an unknown to infer.
  - This is exactly the address-confirmation we wanted: the map gives the
    EXPECTED CELL_ID relationships; the silicon read CHECKS them. Any addressing
    error surfaces as a clean disagreement.
  - It kills a whole BUG CLASS. Today's silicon session lost hours to
    CELL_ID-vs-input_address confusion, stale-state addressing, and "which cell
    does config target" -- all symptoms of address relationships living
    IMPLICITLY in scattered places (RTL arithmetic, tcl assumptions, memory). If
    the map is the EXPLICIT authoritative source, loader/compiler/tcl-generator/
    verifier all read from ONE place, and "tcl assumes 0x100 but cell is at 0"
    cannot happen -- both come from the map.

**Two things this now requires (Alan):**
  1. A SYNTHESIS-APPLICATION mechanism: the map must actually drive cell
     placement and bridge wiring in the generated bitstream (not just describe
     it after the fact). This is the (b) above -- the generator that turns a map
     into placed RTL / constraints.
  2. A USER-FACING AUTHORING FRONTEND: a simple way for users to draw/describe
     the cell patterns as needed, without hand-writing coordinates. This is the
     composer's spatial view (Stage 5) taken to its natural conclusion -- "draw
     the shape, the tool emits the map." The map format is the contract between
     this frontend and the synthesis-application mechanism.

Runtime discovery (the boot-walk as SOURCE, not verifier) only earns its keep in
one edge case: handing the loader an UNKNOWN bitstream with NO map descriptor and
asking it to reverse-engineer the shape. That's a recovery/RE tool, not the
normal path -- and the boot-walk is exactly the mechanism for it. So the
boot-walk isn't wasted; it's the verifier on the normal path and the fallback on
the abnormal one, just never the everyday source of truth.

**Roadmap placement:** the map format + synthesis-application belong with Stage 4
(compiler) since the compiler precomputes routing against it; the authoring
frontend belongs with Stage 5 (composer). CMD_ARRAY_RESET (#18-adjacent, built
this session) is the boot-walk's enabler -- reset to boot state, walk CELL_IDs,
verify against the map.
