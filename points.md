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

## 18. Transit cells (suppress-local routing waypoints) -- BUILT & PROVEN ON SILICON

**Status: PROVEN ON SILICON 2026-07-09 (Arria 10 GX660, die readback).**
  transit=1 -> EAST bridge seen=1 (0xaa @ 0x200), LOCAL bus seen=0  [suppressed]
  transit=0 -> EAST bridge seen=1 (0xaa @ 0x200), LOCAL bus seen=1  [control]
Single-bit difference, exactly the designed behaviour. The primitive routes a
value across a cluster boundary without ever presenting it on the host cluster's
local bus. Stage 2 substrate proof COMPLETE (for EAST -- see below for the
remaining three directions).

**PREPARED FOR SILICON (2026-07-10), NOT YET FLASHED — the other three
cardinals.** Only EAST was ever brought out to observable capture; PLAN's
near-term Step 1 calls for all four. `top_arria10_zone1_v3.v` and
`pcie/unicell_issp_bridge.v` extended: N/S/W bridge sticky capture added
(same latch-since-reset pattern as the existing EAST one), ISSP probe selector
widened `[2:0]`->`[3:0]` (113-bit `PRB_W` unchanged, only the selector's
meaning widened) for new views 7=NORTH, 8=SOUTH, 9=WEST alongside 5=EAST,
6=LOCAL-BUS. `fpga/zone1_cardinals.tcl` written: runs the exact transit-only
sequence that already proved EAST, once per direction. Both files elaborate
cleanly against port-matched stubs (real `issp` megafunction is Quartus-only,
same limitation as every top-level file here); full v3 regression unaffected
(these files sit above the array/zone/cell level the testbenches exercise).
NEXT: Quartus rebuild + reflash + JTAG run — the concrete remaining step,
requires the Windows toolchain.

**Was: BUILT AND VERIFIED IN SIM 2026-07-07 (Stage 0 complete). Was: idea
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

## 20. Unified map+composer frontend — one spatial authoring surface (Alan, 2026-07-08)

**Status: product/UX decision for Stage 5. Extends #19 (the substrate map). Not
built.**

The map-authoring frontend (#19's requirement 2) and the composer are ONE tool,
not two. Concretely:

- **Single standalone HTML page**, same style as the other frontends (self-
  contained, no build chain -- consistent with the existing workbench pages).
- **Map mode**: lay out cells, mark out the pentacross GROUPS (clusters). This is
  the substrate-map authoring from #19 -- the artifact that drives synthesis.
- **Composer mode**: import that same map as the BACKDROP and build the model ON
  it. The map is not a separate document to cross-reference; it is the literal
  canvas the model is drawn onto.
- **Two arrow types drawn in the SAME place:**
  - CARDINAL ROUTING arrows (RTL side) -- cross-cluster N/S/E/W bridge hops that
    become routing_mask bits.
  - CELL-TO-CELL connections -- the model's dataflow wiring.
  Drawing both on one map makes the spatial relationship VISIBLE: you can see a
  cell-to-cell edge cross a cluster boundary and therefore see that it NEEDS a
  cardinal routing arrow. The RTL-routing view and the dataflow view can't drift
  apart because they share one picture. (This is the seam #17/#18 formalised --
  minimise crossings, transit-hop the long ones -- made directly authorable.)

**The STEP feature is the verification payoff.** The composer steps the
computation one tick at a time, which surfaces -- visually, at the tick they
occur -- the exact two failure modes this project has fought:
  - COLLISIONS: two cells firing to the same cluster on the same tick (the same-
    depth placement problem). Step through and watch two arrows light the same
    cluster on one step.
  - BUS CONTENTION: the one-transaction-per-cluster-per-cycle limit. A cluster
    asked to carry two things in one tick shows the conflict AT that step.
This is exactly what the Python event-driven sim does today (the tool that caught
collisions before RTL), but made VISUAL and INTERACTIVE -- the user sees the
collision in space and time, on the map, instead of reading a log. It turns the
placement-correctness check from an offline batch into something you watch unfold.

**Full flow:** one HTML canvas -> author the map (mark groups) -> import as
composer backdrop -> draw cardinal routing + cell-to-cell dataflow on the same
surface -> step through to watch collisions/contention appear. The map drives
synthesis (#19); the SAME map is where the model is built and verified. Design,
place, route, validate -- one spatial view.

Roadmap: this is the concrete shape of Stage 5's composer. The map format (#19)
is the shared artifact; this frontend is both its authoring tool and the
composer's canvas. Ties to the event-sim (reuse its collision/contention model
as the step engine).

## 21. Map runs in the VM + address-agnostic root-relative loader (Alan, 2026-07-08)

**Status: two architectural decisions extending #19/#20. Not built. Both
simplify the loader and tighten design->silicon fidelity.**

### 21a. The map runs in the VM too, not just the FPGA
The composer already exports the ICM; it now ALSO exports the map file (#19). Key
consequence: if the map can drive the FPGA, it can drive the VM -- same artifact,
both targets. Flow:
  author map -> export -> load map into VM -> SEE your substrate (the shape you
  designed) -> load your ICM -> WATCH it flow through that map, tick by tick,
  exactly as it will on silicon.
This closes the design->silicon gap that cost this whole session: the pain was
discovering the difference between "what I designed" and "what the silicon does"
through JTAG round-trips. If the VM runs the SAME map the FPGA will, the VM
becomes a faithful preview -- validate the model flowing through your actual
custom substrate BEFORE synthesizing. The #20 step-through becomes a true
simulation of the real thing (it's the real map), not just a design aid.

### 21b. The loader is address-agnostic: root cell + relative placement
The loader does NOT care about absolute addresses. It is handed a ROOT CELL and
places everything RELATIVE to that root. The map describes RELATIONSHIPS (this
cell east of root, this cluster two north); the loader resolves them against
wherever the root lands. This is the relocatable-models / root+offset principle
made the loader's core model.

Why this removes so much pain (directly relevant to this session's losses):
  - The CELL_ID-vs-input_address tangle that cost hours largely DISSOLVES. That
    was error-prone BECAUSE of absolute addressing ("config targets CELL_ID 0,
    inject targets input_address 0x100" -- every absolute a chance to mismatch).
    With relative-to-root placement, the loader computes absolutes from the map's
    relative structure; humans and the tcl-generator never hand-write them. "tcl
    assumed 0x100 but cell is at 0" cannot happen -- nobody asserts absolutes.
  - Models are truly relocatable for free: the same ICM loads at any root, loader
    just shifts the base. Cell stays absolute internally; loader owns the
    relative<->absolute seam.
  - The map describes SHAPE + RELATIONSHIPS, not a fixed address grid. A custom
    substrate (#19) is just a different relative structure with a root; the
    loader handles it identically.

Net: the loader stops being a fussy absolute-address matcher and becomes a
RELATIVE PLACER -- give it a root and a map, it lays everything down. Smaller,
more robust job, and the whole addressing model gets easier because
relative-from-root is inherently less brittle than absolute.

Together 21a+21b mean: design in the composer on your map, watch it in the VM on
that same map, compile to a fixed bitstream, load the ICM relative to a root --
and the thing that runs on silicon is the thing you already watched run in the VM.

## 22. Directional single-cell fabric — measured, and it's a COMPLEMENT not a replacement (2026-07-08)

**Status: experiment run (Python, on the verified 37-cell adder). Result: viable,
and the right substrate for LOCAL/dense models. Not a replacement for pentacross.**

Alan's proposal: shrink the cluster to a single cell. Each cell is its own unit
with 4 cardinal faces; connections are purely directional cell-to-cell; the
listening/push addresses demote to remote-use-only.

### Measured on the 37-cell packed adder (worst case for this fabric)
- **Cells: 37 -> ~62 (≈1.7x)**, the extra being relay/transit cells. (Placement
  search was mediocre; a good placer beats this, but it cannot reach 1.0x.)
- **Fan-out is FREE**: max fan-out in the adder is 3, a cell has 4 faces. No
  split/duplicate cells ever needed. (The fan-out-explosion worry was unfounded.)
- **Collisions do NOT vanish -- they MOVE.** No shared cluster bus => no bus
  contention BY CONSTRUCTION. But relay squares become the shared resource: two
  different values crossing the same square on the same tick collide. Crucially
  this is now a ROUTING problem (reroute / retime) not a placement CSP -- a
  strictly better class of problem.
- No unroutable edges once placement leaves routing channels.

### The structural reason pentacross wins ON THE ADDER
A 5-cell pentacross cluster gives 10 FREE internal connections (any cell to any
other on the shared local bus, zero routing). A directional single-cell fabric
has ZERO free connections -- every edge is a physical adjacency you must pay for
in placement. The adder has 50 edges; the cluster model absorbs most of them
inside clusters for nothing.

### Why the adder is the WORST case (and Alan's instinct is right)
Kogge-Stone is a tree with long-range shifts (spans 1,2,4,8,16) -- inherently
non-local, hence relay-heavy. Flip to models whose dataflow is NEAREST-NEIGHBOUR
-- systolic arrays, stencils, convolution, cellular automata, and specifically
LBM/D2Q9 (already on the roadmap for FlowTrix) -- and nearly every edge is
naturally adjacent. Almost no relays. There the cluster bus is PURE OVERHEAD and
the directional fabric is IDEAL: maximum density, no bus, no placement CSP.

### Conclusion: two substrates, model locality decides
- Long-range / tree-structured dataflow (adders, reductions, FFT butterflies)
  -> PENTACROSS CLUSTERS. The shared bus buys free non-local connections.
- Nearest-neighbour / stencil dataflow (LBM, convolution, systolic, CA)
  -> DIRECTIONAL SINGLE-CELL FABRIC. Max density, no bus overhead, no CSP.

This lands exactly on #19's custom-shaped substrates: the directional fabric is a
SECOND SUBSTRATE SHAPE, authored as a different map, compiled to its own
bitstream. **The map format needs no change** -- a directional fabric is simply a
map where every cluster is one cell. Alan's "possible map for the more intricate
type of model, where density is essential" is precisely correct.

### Open RTL questions if we build it
- Does a receiving cell need to know WHICH FACE a value arrived on? If yes, the
  ibus needs per-direction tagging (contained RTL change) and cells could get
  FACE-AWARE OPERANDS (north=A, west=B) -- which would remove arrival-order
  fragility and the SWAP_AB priming dance entirely. Cleaner cell, and the
  composer's arrows become literally the operand wiring.
- Transit (#18) safety changes: today a pass-through value is harmless because
  address-uniqueness filters it. With local addressing demoted, an arriving value
  hits every cell on that face -- so selectivity must become POSITIONAL (only the
  facing arm accepts) rather than address-based.

## 23. The four artifacts, the SHAPE BINDER stage, and the loud-failure contract (Alan, 2026-07-08)

**Status: architectural decision completing the #19–#22 arc. Not built.**

### The four artifacts per model
1. **MAN file** — describes the TARGET CARD: device part, pin assignments, clock
   source, resources (ALMs/DSPs/BRAM), JTAG IDCODE. Today this lives scattered
   across a QSF, a comment in the top-level, and human memory — and its absence
   cost this session hours (the missing `set_location_assignment PIN_E23`).
   It is the card's identity, as DATA.
2. **ICM** — the MODEL itself. Shape-NEUTRAL and card-neutral. Portable,
   root-relative (#21b). This is the artifact you share, version, publish.
3. **SHAPE file** — the substrate map (#19): which cells exist, how (or whether)
   they cluster, the cardinal adjacencies. Pentacross, directional (#22), or a
   user's custom shape.
4. **BITSTREAM (.sof)** — generated for a specific card from SHAPE + MAN, in a
   SINGLE run. No hand-edited QSFs, no lost pin assignments.

Relationships: `SHAPE + MAN -> bitstream` (one generation run). `ICM + SHAPE ->
VM/composer` (faithful preview, #21a, guaranteed to match the card because the
same shape generated the bitstream). MAN matches shape to card — the safety
interlock that makes "did I flash the right bitstream?" answerable by
construction rather than by readback archaeology.

### The SHAPE BINDER — an explicit stage between ICM and loader
The ICM stays shape-neutral (portability > pre-baked placement). But something
must bind model to shape. That is NOT the loader's job — asking the loader to
place makes it a placer. So:

**model (composer) -> ICM (shape-neutral, portable) -> [BINDER] -> placement ->
loader (root-relative, dumb) -> silicon**

BINDER input: shape-neutral ICM + shape file. Output: a concrete placement (which
model cell at which substrate position, routing/transit resolved for that
geometry). ALL shape-specific work lives here:
  - pentacross placement rule (#17) if the shape has clusters;
  - directional grid placement + relay insertion (#22) if it does not;
  - compute routing_mask bits for the actual adjacencies;
  - insert transit hops (#18) for edges the geometry can't make adjacent;
  - VERIFY: collisions, bus contention, capacity — via the event-sim.

Consequences:
  - **The loader stays genuinely dumb** (#21b's goal): receives a placement + a
    root, lays cells relative to root. No placement logic, no shape awareness, no
    address arithmetic.
  - **Shape optimisation lives in the binder, and is OPTIONAL.** A naive binder
    places and works; a good one minimises hops, packs clusters, picks transit
    paths well. Improve it forever without touching ICM format, loader, or
    bitstream. The one stage where being smarter has no downstream cost.
  - **Shape becomes an empirical tunable**: bind the same ICM against pentacross,
    measure; against directional, measure; pick the winner. The binder produces
    the numbers (cells, hops, ticks, collisions) the VM shows you.
  - Alan's recommended flow: check in the COMPOSER first, then run in the VM to
    confirm the model still works on that shape. The binder is the thing that can
    fail, so the composer check and VM run ARE the binder's output being
    inspected before committing to silicon.

### The loud-failure contract (Alan)
User feedback on fails/problems must be EXPLICIT and deliberately VERBOSE — the
same standard as a compiler telling you "undeclared variable", "nested loop 25
deep, clean it up". The binder is better placed than a compiler to be helpful
because IT KNOWS THE GEOMETRY: it can suggest the fix, not merely name the fault.

Error taxonomy (each names the thing, the place, the tick, and where possible the
remedy):
  - CAPACITY: "needs 62 cells; this shape has 40. Overflow is 25 relay cells from
    18 non-adjacent edges. Pentacross would need 37."
  - UNROUTABLE EDGE: "REQ1 -> SUM_XOR cannot route on this geometry; nearest
    routable placement adds 4 relays."
  - COLLISION: "AND_P2 and OR_G3 both fire into cluster 7 on tick 9 (same-depth
    conflict). Move one, or free an arm here."
  - BUS CONTENTION: "cluster 4 must carry 2 transactions on tick 6 (own fire +
    transit hop). One will be dropped."
  - SHAPE MISMATCH: "fan-out reaches 6; this shape gives 4 faces/cell. Needs split
    cells this binder cannot insert."
  - WARNING (not error), the compiler-analogy case: "model is correct but on this
    shape costs 1.7x cells and 240 extra ticks — you are fighting the geometry."
    This IS the shape-selection feedback loop made concrete.

**Why this is non-negotiable here:** every hour lost in the 2026-07-08 silicon
session came from the system FAILING SILENTLY — dead clock, wrong auth token,
stale input_address, out_seen-vs-bus_valid confusion. None announced itself;
`0xa0000000` told us nothing. The whole session was reconstructing what the
machine could simply have SAID. Loud, specific failure is the direct lesson of
this session, and the binder is the natural place to enforce it: the last stage
that still understands INTENT before everything becomes bits on a die.

## 24. First interconnect data — the shared bus is cheap in cells, expensive in routing (2026-07-09)

**Status: observation from the Arria 10 single-zone smoke-test fit. First real
interconnect measurement. Bears directly on the two-substrate story (#22).**

Quartus Fitter, single-zone build (25 cells, 7% ALM):
```
Router estimated average interconnect usage is 2% of available device resources
Router estimated peak interconnect usage is 36% ... in the region extending from
location X99_Y59 to location X110_Y70
```

**Reading it:**
- **2% average** -- the fabric is almost entirely LOCAL. Exactly what a cell array
  whose thesis is neighbour-to-neighbour communication should look like. No
  long-haul signalling sprawling across the die.
- **36% peak in one ~12x12 tile region** -- a genuine hot spot, ~4x the average,
  and it sits where the array is. Almost certainly the WIRED-OR BUS plus the
  command fan-out: every cell must see cmd_bus/cmd_data/cmd_valid (one-to-many),
  and every cell's out_* must converge into the array's or_valid aggregation
  (many-to-one). That convergence is what Quartus is paying for.

**The finding that matters:** the pentacross cluster's SHARED BUS -- the very
thing that gives 10 free internal connections and let the adder fit in 37 cells
(#22) -- is PRECISELY what creates that 36% peak. The shared bus is free in CELLS
but expensive in INTERCONNECT. The cell-count comparison in #22 did not show this
cost.

**Consequence for #22's two-substrate story:** the directional single-cell fabric
has NO shared bus at all -- every connection is a point-to-point neighbour link.
No many-to-one convergence, no broadcast bus. So it should trade its 1.7x cell
overhead for a dramatically FLATTER interconnect profile. On real silicon that may
matter more than cell count: routing congestion is what actually limits how
densely a fabric can be packed and what Fmax it can close at. The directional
fabric's cost is cells (cheap here: 7% ALM); its saving is routing (the thing that
will bind first).

**Scale note:** at 7% ALM / 2% average interconnect we are nowhere near stressing
this device. But scale to 16 zones, or the full 12-cluster adder mesh, and the 36%
peak is the number that moves FIRST. Interconnect, not logic, is the likely
binding constraint. Useful to have learned this from a smoke test rather than at
the point of trying to fill the chip.

**Feeds #23's binder warnings:** alongside "this shape costs 1.7x cells", a mature
binder should be able to say "this shape costs 36% peak interconnect in the bus
region; the directional shape trades cells for routing headroom." Exactly the
concrete, geometry-aware advice the loud-failure contract calls for. Worth
capturing post-fit interconnect numbers per shape as part of the shape library's
advertised characteristics (alongside cell capacity), so shape selection can be
made on routing headroom as well as cell count.

## 25. DSP integration — chain length, bridges, and delays belong in the MAN file (Alan, 2026-07-09)

**Status: design. Next build after the silicon-proven substrate (#18). Orthogonal
to the shape story (#22) -- leaves that route open.**

Gate satisfied: PLAN.md said "do NOT resolve the DSP open questions until
single-card Arria 10 is stable." The transit proof on die (#18) satisfies that.
Current usage: **0 / 1,687 DSP blocks** -- paid-for silicon sitting idle.

Three concerns, and they are distinct:

### 1. Set chain length
Arria 10 DSP blocks CASCADE (adder trees, MAC chains), but a chain is not
free-form: there is a fixed maximum length, and a chain of length N has a known
structure. The fabric cannot merely "ask for a multiply" -- it asks for a chain
of a SPECIFIC length, and the allocator must know which lengths are legal on this
card.

### 2. Bridges for the individual units
A cell-to-DSP boundary, the same pattern as a cardinal zone bridge: the cell
hands a value across, the DSP result returns into a cell. This is PLAN.md's
`HARD_MUL` boundary tile. It is a BRIDGE rather than an opcode precisely because
it crosses a latency domain, exactly as a zone bridge crosses a spatial one.

### 3. Their delays — THE CRUCIAL ONE
A DSP block has a fixed pipeline latency (input->result); a CHAIN of them has a
cumulative latency. The fabric's entire timing model is TWO-ARRIVAL FIRING: a
cell fires when both operands land. If a DSP result returns N ticks later than a
fabric-computed operand, the two-arrival ordering BREAKS unless the compiler
knows N and schedules around it (delay cells, #5, are the existing realignment
technique).

### Where this lives: the MAN file (#23)
DSP latency, legal chain lengths, and block coordinates are **card properties,
not model properties**. An Arria 10 GX660 differs from a GX1150, a Cyclone, or a
future card. So they belong in the MAN file, which already describes the target
card. This keeps the layering intact:
  - **ICM** stays shape- and card-neutral (#23). It says "multiply", not "use DSP
    column 7 with 3-tick latency".
  - **MAN** says: on THIS card, a DSP MAC costs N ticks, chains up to L, and the
    blocks sit at these coordinates.
  - **BINDER** (#23) reads both. It was already going to need the MAN file to
    place against a card; now it also needs it to SCHEDULE -- inserting delay
    compensation so a DSP result arrives in the correct tick for two-arrival
    firing.

That is the piece that keeps everything consistent: DSP timing becomes binder
scheduling data, not a model concern and not a hardcoded RTL constant.

### Orthogonal to shapes (#22)
DSP blocks sit at FIXED PHYSICAL COORDINATES on the die. The shape file describes
CELL layout. The binder's anchor-first placement pins DSP-consuming tiles at those
coordinates (most-constrained-first) and grows outward along dataflow edges. The
DSP anchors are identical whether the shape is pentacross or directional. So DSP
integration does not touch the shape story at all -- it leaves that route open,
as Alan noted.

### Principle preserved (from PLAN.md)
The pure-fabric path stays the REFERENCE (ground truth). Hybrid is an OPTIMISATION
layer for deployment scale, never the foundation. A tile should be expressible
BOTH ways, with the binder selecting soft-vs-hard per tile from the MAN file's
target profile (proving = soft, deployment = hybrid). DSP does the multiply;
fabric does what only the fabric can do (topology, routing, control).

### Note for whoever builds it
The existing `pcie/axi_unicell_bridge.v` command format is STALE -- it encodes an
8-bit auth at axi_wdata[23:16]. The current RTL uses 11-bit auth at cmd_bus[29:19]
(this week's silicon lesson). Any new bridge (DSP or PCIe) must be derived against
the live v3 command contract, or it will silently refuse every config exactly as
the tcl did.

## 26. DSP hard facts, sourced (Arria 10 handbook 683461, 2026.04.28)

**Status: authoritative device facts for #25. From Intel's "Arria 10 Core Fabric
and General Purpose I/Os Handbook", ch.3 Variable Precision DSP Blocks. These are
the MAN-file entries.**

### Capacity (GX 660 -- our part)
1,687 variable-precision DSP blocks. Per block, one of:
  - 18x19 multiplier (x2 -> 3,374 independent 18x19 multiplications)
  - 27x27 multiplier
  - 18x18 multiplier-adder, or 18x18 summed with 36-bit input
Matches the Fitter's "0 / 1,687 DSP Blocks" exactly.

### 1. CHAIN LENGTH = 27  (Alan's "set chain length")
> "The spine clock region limits the number of DSP blocks cascade. For Arria 10
> devices, you can cascade up to 27 DSP blocks."  (sec 3.3.5, p46)

The REASON matters more than the number: the limit is the **spine clock region**,
so it is a SPATIAL/PLACEMENT constraint, not an arithmetic one. A cascade cannot
cross a spine boundary. This lands directly in the binder's anchor-first
placement: DSP chains must be placed WITHIN a spine region. Chain length is
therefore a placement-feasibility question, not just a budget.

### 2. BRIDGE SHAPE  (Alan's "bridges for the individual units")
Block architecture (sec 3.4, p46-48):
  - Input register bank
  - Pre-adder (+/-), internal coefficients
  - Multiplier
  - Pipeline register
  - Chainout Adder / Accumulator (with 64-bit double-accumulation register)
  - Output register bank
  - `chainin[63:0]` / `chainout[63:0]` for cascading
  - Systolic registers (bypassed unless in fixed-point systolic FIR mode)

So the cell<->DSP bridge has a defined shape: hand operands into the INPUT
register bank; take `result` from the OUTPUT register bank. **Cascade via
chainin/chainout, NOT back through the fabric** -- the chain is internal to the
DSP column, which is why the spine limit applies and why a chain costs no fabric
routing.

### 3. DELAYS -- CONFIGURABLE, and Intel names our exact problem
Latency is NOT a fixed constant: each register stage (input bank / pipeline
register / output bank) is OPTIONAL. A block is 0-3 cycles deep depending on
which are enabled. The binder CHOOSES the configuration and therefore chooses N.

Critically (sec 3.4.1, p49):
> "In fixed-point arithmetic 18 x 19 mode, you can use the delay registers to
> balance the latency requirements when you use both the input cascade and
> chainout features."

That is EXACTLY the two-arrival skew problem (#25 concern 3), in Intel's words,
with Intel's solution: cascade + chainout makes results from different chain
positions arrive at different times, and the block carries **built-in delay
registers** to rebalance. It is the delay-cell realignment technique (#5) done
INSIDE the DSP block rather than in the fabric.

**Consequence for the MAN file:** the DSP entry is not a single latency number.
It is a small table -- *for this mode, with these register banks enabled, at this
chain position, latency = N*. The binder picks the configuration, reads N, and
inserts fabric delay compensation only for the residual skew the DSP's own delay
registers cannot absorb.

### What this document does NOT contain
Board-level wiring. It is a DEVICE handbook. The Mustang-F100's PCIe refclk pin
and transceiver-lane mapping are IEI board facts (schematic/pinout), not Intel
device facts. Still outstanding for the PCIe work.

## 27. What JTAG-only actually costs (measured, 2026-07-09)

**Status: assessment. Corrects an over-pessimistic reading of the PCIe loss (#26,
docs/PCIE_ARRIA10_NOTES.md). Three feared limits are not real; two are.**

With PCIe blocked on the EOL Mustang, the working assumption became "JTAG-only, so
we are down to small models, one zone, no workbench, and the roadmap stalls until a
new card." Checked against the repo and the Fitter, most of that does not hold.

### NOT actually limits

**1. "The workbench/composer won't run over JTAG."**
They were never meant to. They are **VM-side tools** (#21a): load the map into the
VM, load the ICM, watch it flow, step it (#20). The card is where you CONFIRM, not
where you design. Stage 5 is unaffected.

**2. "Feeding 40 MB of RAM over JTAG takes forever."**
The block memory is **43,642,880 bits = 5.20 MiB**, not 40 MB. And it is not fed
over JTAG: `docs/MIF_FORMAT.md` + `bram_dp_v3.v` give a **MIF preload** path -- the
ICM is initialised into BRAM at *configuration* time from the bitstream, then
streamed into the fabric by the on-chip loader FSM at full 25 MHz fabric speed.
JTAG is out of that loop entirely. (Caveat: MIF-baking makes a model a
synthesis-time artifact, in tension with the "no per-target rebuilds" principle. Fine
for development/testing; the load-time path stays canonical.)

**3. "Probably stick with one zone."**
`fpga/verilog/top_card_2zone_v3.v` already instantiates ZONE_ID 0 and 1 and passes
regression (`tb_card_2zone_v3`). Single-zone was a **bring-up harness choice**, not a
JTAG limit. The command path is broadcast-with-self-gating and `CELL_BASE =
ZONE_ID << 5` already encodes the zone in every CELL_ID -- **zone count does not
change the command path at all.** Only readback observability needs extending (the
ISSP probe currently exposes Z00).

Zone count is bounded by ALMs and interconnect, not JTAG. At **7% ALM** for one zone
+ harness, the binding constraint is likely the **36% peak interconnect** from #24 --
and that is a measurement obtainable ON THIS CARD (build 4 zones, read the router
estimate). Genuinely valuable silicon data.

### REAL limits (these two stand)

**1. Iteration is slow.** Every silicon check is a `quartus_stp` round trip. The
2026-07-08 session lost most of a day to exactly this. Real, ongoing friction.

**2. FlowTrix / LBM at scale is blocked.** DDR streaming, temporal blocking, N-deep
halos -- that plan assumed a fast host link. That demo waits for a card with a
documented PCIe path. This is the one roadmap item that genuinely stops.

### Model-load cost over ISSP, for scale
The packed adder is 37 cells. Per cell ~7 commands (SET_TARGET, RECONFIGURE,
SET_OUTPUT, SET_TARGET, ROUTING, SET_TARGET, TRANSIT). ~260 commands total. Even at a
pessimistic 100 commands/sec that is **seconds, not "forever."** Small and mid-size
models load fine over JTAG; MIF preload covers the large ones.

### Net
**What is lost: bandwidth-hungry demos and fast iteration. What is kept: the entire
near roadmap.** Stage 1 (adder RTL), Stage 3 (migration), Stage 4 (compiler, pure
software), Stage 5 (workbench/composer, VM-side), Stage 6, and DSP integration
(#25/#26) all fit on the card in hand over the interface in hand.

The cross-die link (#--, the two-card plan) is also NOT dead: a zone bridge is
**49 signals** (valid + 16-bit addr + 32-bit data). At a slowed demo clock that is
plain-GPIO territory. Two small FPGAs (an iCEBreaker is already in hand) wired
PMOD-to-PMOD would prove the claim that actually mattered -- **the fabric extends past
the die edge** -- without PCIe, peer-to-peer DMA, an IOMMU, or a GBP1k card. Arguably
a *better* demonstration: no host in the loop, two fabrics behaving as one.

## 28. CANONICAL: the .pin file is the MAN file's device half (Alan, 2026-07-09)

**Status: method. Generalises the PCIe pinout hunt into a repeatable step. Feeds
#23 (the four artifacts / MAN file).**

Quartus writes `output_files/<revision>.pin` on every Fitter run. It lists **every
ball on the package** -- used and unused -- with its name and function, for the
**exact target part**, generated from Quartus's own device database.

**That is the pinout document, produced by your own machine.** No vendor website,
no PDF, no BSDL hunt, no dependence on whether the manufacturer still exists or has
retired the product pages. Run the Fitter once and the tool tells you the pinout.
It works for an EOL Mustang, a current dev kit, or a card built years from now.

### It cleanly splits the MAN file in two
- **DEVICE FACTS** -- every ball, its name and function; which transceiver banks are
  bonded out; refclk pin locations; DSP block coordinates and latencies (#26).
  **All obtainable LOCALLY**: the `.pin` file plus the device handbook.
- **BOARD FACTS** -- what the board designer actually wired to which pin.
  **Only the board vendor knows.**

The entire PCIe ordeal (docs/PCIE_ARRIA10_NOTES.md) came from conflating these. We
hunted "the pinout" as one thing while the device half sat in a build artifact. And
once the device half was in hand it *nearly solved* the board half: F34 bonds only 4
transceiver banks -> 8 refclk pairs -> Gen2 x8 spans two adjacent banks -> 3
pairings. The device half did not merely inform the board half; it collapsed it.

### The canonical step
> Generate the device half from your own machine (`.pin` + handbook). The board half
> is then a small, bounded question, often answerable by inference or a handful of
> guarded builds -- and Quartus rejects ILLEGAL assignments at compile, so wrong
> answers are caught before flashing.

### Consequence: the MAN file has a GENERATOR, not just an author
Point it at a device, run a fit, parse the `.pin` file, pull the DSP table from the
handbook -> the device half is produced automatically. The human supplies only what
the board did with those pins.

### Consequence: a whole failure class closes
`PIN_E23` went missing and killed the fabric clock for a build cycle (2026-07-08).
If the MAN file is GENERATED from the `.pin` file, pin assignments stop being things
a human types into a QSF and hopes survive a folder rebuild. They become **derived
data, checked against the device's own database.** That class of silent failure ends.

Roadmap: this is part of Stage 4's MAN-file/synthesis-application work (#19/#23).

## 29. Generalising #28: the MAN file's device half has a VENDOR-AGNOSTIC generator (Alan, 2026-07-09)

**Status: architecture. Generalises #28 from "a trick that saved the Mustang" into
infrastructure. Feeds #19/#23 (Stage 4).**

The `.pin` file is not special to the Mustang, to Arria 10, or to a device family.
**Every Quartus target emits one** -- same format, same semantics: every ball, its
name, its function, for whatever part the Fitter was aimed at. A parser written once
reads a Cyclone, an Agilex, a Stratix, a card that does not exist yet.

And the *shape* generalises past Intel. Xilinx/AMD emits its own package pin files;
Lattice does too. Different formats, identical ROLE: **the tool knows the die, and
will tell you if you ask.**

### Three layers, not two
```
vendor tool   -> emits its native pin/device description
reader        -> parses it into the MAN file's DEVICE section   (one per vendor)
MAN file      -> the single schema everything downstream reads
```
The binder (#23) never learns what an Arria 10 is. It reads a MAN file. Whether that
file came from Quartus, Vivado, or a human typing it for a board they soldered is
irrelevant to everything downstream. Same move as the shape file (#19): **one
authoritative artifact, many producers.**

### What the generator can and cannot produce
- **DEVICE section (generated)**: every ball + function; bonded transceiver banks;
  clock/refclk pin locations; DSP block coordinates, chain limits (#26), latencies;
  memory. All from the vendor tool, locally.
- **BOARD section (human)**: what the PCB actually wired to which pin. No tool knows
  this. BUT -- as the PCIe hunt showed -- once the device section constrains it, the
  board section is often a **short list of possibilities**, not an open question.

### The bigger payoff: hardware facts become CHECKABLE
A generated MAN file is verifiable. Before a build you can ask:
- Does this pin assignment exist on this device?
- Is this pin actually a refclk?
- Does this DSP chain exceed the spine limit (27, #26)?
- Does this shape's cell count fit the fabric?

All static checks against generated data, instead of silent failures found on a die.
This extends **#23's loud-failure contract down into the hardware layer**: the binder
can refuse a bad MAN file exactly as it refuses a model that will not fit a shape.

### Net
The generation step does three jobs at once:
1. **New cards become cheap to onboard** (write nothing; run a fit, parse the file).
2. **EOL cards become survivable** (vendor deletes the docs; the tool still knows).
3. **Hardware facts become verifiable rather than trusted** (the `PIN_E23` class of
   silent failure closes -- see #28).

## 30. The CLOCK WALK — measuring the board half (Alan, 2026-07-09)

**Status: proposed diagnostic. Generalises the boot-walk / `cycle_count` technique
from cells to PINS. Would convert the last PCIe inference into a measurement.**

Alan's observation: `cycle_count` diagnosed the dead `CLK_100M` by asking "is this
counter ticking?" over JTAG. The same feature can find the PCIe refclk pin.

### Why it works
Two facts from PCG-01017 combine:
1. `REFCLK_GXB` **doubles as a dedicated clock input with fPLL for core clock
   generation, even when the transceiver channel is unused.** So a refclk pin can
   reach the fabric with **no transceiver instantiated**.
2. **Unused refclk pins are tied to GND on the board.**

Therefore on the Mustang, IEI grounded the seven refclk pins they did not use. Only
the pin wired to the edge connector carries the host's free-running 100 MHz.
**Seven dead flat, exactly one alive.** The test discriminates perfectly. (If TWO
light up, IEI wired something else to a refclk pin -- and we learn that too.)

### Design (a throwaway diagnostic bitstream -- the whole 113-bit ISSP probe is free)
- **Option A -- counters.** 8 refclk inputs, each clocking an 8-bit counter; 64 bits
  on the probe. Read twice ~80ms apart; whichever CHANGED has a clock. Exactly the
  `cycle_count` pattern.
- **Option B -- PLL lock (preferred).** Instantiate 8 fPLLs, one per refclk; read the
  8 `locked` bits. A PLL locks only on a valid clock. 8 probe bits, no counters, no
  cross-domain sampling, unambiguous. Arria 10 has 32 fPLLs; 8 is trivial. This is
  also the path Intel *documents* (refclk -> fPLL), so Quartus will not refuse it.

One build, one flash, one readback, and the pin identifies itself.

### Honest failure modes
- **I/O standard.** PCIe REFCLK is HCSL; PCG-01017 permits DC-coupling only if the
  standard is HCSL, else AC-couple with correct input biasing. Wrong setting gives a
  **FALSE NEGATIVE**. So: *if all eight read static, the conclusion is "check the I/O
  standard", NOT "none of them".*
- **Direct refclk -> core logic may be refused by Quartus.** Hence Option B.
- **Card must be in a powered PCIe slot with JTAG attached.** REFCLK comes from the
  motherboard clock generator. We know it is present -- the card enumerates under
  IEI's firmware.
- **8 fPLLs may not all place** if refclk pins bind to PLLs within their own bank.
  Fall back to two builds of four.

### The bigger point: the BOARD half is partly MEASURABLE
#28/#29 established that the MAN file's **device** half is generated locally from the
`.pin` file. This shows **part of the BOARD half can be interrogated on the card
itself.** Not everything about a board lives in a vendor schematic -- some of it the
hardware will tell you if you ask. A "clock walk" over candidate pins is the
hardware analogue of the boot-walk over cell IDs.

Feeds #23/#28/#29 (MAN file). Turns the one remaining PCIe INFERENCE (that IEI used
`REFCLK_GXBL1D_CHB`) into a MEASUREMENT.

## 31. LIF neuron on the pentacross — recurrence changes the placement problem (2026-07-09)

**Status: experiment run (Python) at Alan's suggestion. Proposed cell decomposition
-- Alan to confirm the op breakdown. Hits his stated 9 / 15 counts exactly.**

### The decomposition (one op per cell)
**LIF 9 (no learning):** SYN_MUL, V_STATE(DELAY), V_LEAK(SHIFT), V_INT(ADD),
V_CMP(SUB), SPIKE(SIGN), NOT_SPK(XOR), V_NEXT(AND), AXON(RELAY).
**LIF 15 (+learning):** + PRE_STATE(DELAY), PRE_DEC(SHIFT), PRE_TRACE(ADD),
DW(MULT), W_STATE(DELAY), W_NEXT(ADD); SYN_MUL's weight now comes from W_STATE.

### Finding 1: recurrence -- DELAY cells are the state boundary
LIF is **not a DAG**. Depth is undefined on a cycle, and #17's placement rule is
built on depth. Resolution: **DELAY cells are the timestep boundary** (exactly like
a register in synchronous RTL). Cut the feedback edges and both variants become a
per-timestep DAG of **depth 6**. Learning adds WIDTH, not depth.
Feedback edges: LIF9 has 1 (V), LIF15 has 3 (V, pre-trace, weight).

### Finding 2: the packing
| Model | Cells | Clusters | Slot use | Adjacency | Feedback free |
|---|---|---|---|---|---|
| LIF 9  |  9 | 2 |  90% | path | 1/1 |
| LIF 15 | 15 | 3 | **100%** | path (C0-C2-C1) | 2/3 |
LIF15 is an **exact fit**: 15 cells = 3 full pentacrosses. Alan's number lands
precisely on a cluster boundary. The one crossing feedback edge is the weight loop
`W_NEXT -> W_STATE`; it needs one routing_mask bit (adjacent, so no transit).

Collisions are **zero by construction**: no cluster holds two cells of the same
depth, and same-depth cells fire on the same tick. The depth constraint IS the
collision guarantee.

### Finding 3 (the important one): recurrence makes EMBEDDABILITY the binding constraint
Of **12,960** valid LIF15 placements (satisfying <=5 cells, no same-depth, <=4
neighbours), only **246 (1.9%) are grid-embeddable.**

Why: **feedback creates CYCLES in the cluster adjacency graph.** A square NSEW mesh
is **bipartite** (colour by (x+y) parity), so it contains **no odd cycles**. A
3-cluster triangle cannot embed at all. The first placement our greedy found *was* a
triangle -- valid on every #17 constraint, and physically unrealisable.

The adder never showed this: it is a pure DAG, so its cluster graph had no
feedback-induced cycles. **For recurrent models, embeddability is not a corner case
-- it is the constraint that rejects 98% of otherwise-valid placements.** This
sharpens the #17 embeddability refinement from "worth checking" to "check first".

### Finding 4: a new placement rule, parallel to #17's rule 4
> **STATE CELLS RIDE THEIR FEEDER.** Place a DELAY cell in the same cluster as the
> cell that feeds it; the feedback edge becomes intra-cluster and **free** (local
> bus, no routing bit, no crossing).

Direct analogue of #17 rule 4 ("fan-out/checkpoint cells ride their producer").
Both say: *co-locate the thing that closes a loop with the thing that opens it.*

### Finding 5: neuron models pack BETTER than arithmetic trees
| Model | Cells | Clusters | Slot use |
|---|---|---|---|
| packed adder | 37 | 12 | **62%** |
| LIF 15 | 15 | 3 | **100%** |

The adder is a **wide** Kogge-Stone tree -- many cells at the same depth, which must
be spread across clusters, wasting slots. LIF is **deep and narrow**, almost no
same-depth cells, so it fills pentacrosses exactly. **Same-depth population is the
real driver of cluster count**, not cell count.

Connects to #22: the adder is tree-structured (bad for the directional fabric,
1.7x cells); LIF is chain-with-feedback (a ring). Worth measuring LIF on the
directional fabric too -- a ring may lay out naturally there.

### Caveat
The decomposition above is a *proposal* that happens to hit 9 and 15 exactly. That is
a consistency check with Alan's numbers, not proof the op breakdown matches his.

## 32. The wired-OR bus IS a free N-way OR reduction (2026-07-09)

**Status: SIM-VERIFIED 2026-07-10 (`tb_v3_wired_or.v`, both predictions confirmed —
see the dated entry below). Originally read from RTL (`unicell_array64_v3.v` line
308); relaxes #17's central placement constraint and corrects an overstatement in
#31. Silicon confirmation is PLAN's near-term Step 1 (bundled, no extra flash).**

Came out of Alan's suggestion to try a **3-2-1 pyramid** cluster shape for the
shift-adder.

### What the RTL actually does
```verilog
for (i = 0; i < NUM_CELLS; i = i + 1)
    if (cell_out_valid[i]) begin
        or_addr = cell_out_addr[i];                 // LAST firer's address
        or_data = or_data | cell_out_data[i];       // WIRED-OR of ALL firers
        ...
```
The data of **every simultaneously-firing cell is OR'd together.** The address is
taken from whichever fired last.

### Therefore a same-tick "collision" is two different things
- **Same depth, SAME output address** -> the bus delivers `OR(all their data)` to
  that address. **A free N-way OR reduction in ONE tick.** Not a collision.
- **Same depth, DIFFERENT output addresses** -> data still OR'd, address from the
  last firer. **This** is the corruption.

### The placement rule is too strong
#17 enforces *"no two same-depth cells in a cluster."* It should be:
> **No two same-depth cells in a cluster with DIFFERENT output addresses.**

Same-depth cells sharing an output address are not colliding -- they are **reducing**.

### Consequence for shapes: the bus is both broadcast AND combine
- **PENTACROSS = fan-out.** One fire, many listeners, ONE transaction. The shared
  bus is free for broadcast. (#17 rule 4, "fan-out rides its producer", is the
  pentacross shape stated as a rule.)
- **THE BUS ITSELF = fan-in.** Many fires, one address, ONE transaction. The shared
  bus is free for OR-reduction.

A 3-2-1 pyramid exists to reduce 3->2->1 over three ticks. **The wired-OR bus already
reduces N->1 in one tick.** A 5-cell pentacross can OR-reduce all five of its cells
in a single transaction. The pyramid's motif is *already present* in the substrate;
we were forbidding it by rule. Shape and bus-model are coupled -- and this bus does
both directions.

### Corrections to earlier entries
- **#31 overstated**: "same-depth population, not cell count, drives cluster count."
  True for LIF15 (both bounds = 3). **False for the adder**: max same-depth
  population is **3**, but 37 cells / 5 = **8**. **Size binds, not depth.**
- The adder's actual placement uses **12** clusters (62% slot use) against a
  theoretical minimum of **8** (92%). The structural rule (REQ rides producer,
  P-stage / G-stage groups) costs four clusters. **There is real headroom.**

### Possible optimisation (unverified)
`OR_Gk = OR(DELAY_Gk, AND_PGk)`. If those two fired on the same tick to the same
address, **the bus would compute the OR and the `OR_Gk` cell would be unnecessary.**
They sit at different depths (d6 vs d8), so aligning them costs a delay cell --
net zero cells, but saves a tick per stage (5 ticks over the adder). Worth testing.

### VERIFIED IN SIM (2026-07-10) — `tb_v3_wired_or.v`
Built the required testbench: 3 cells (`unicell_array64_v3`, `NUM_CELLS=3`), booted onto
a shared listen address so ONE host injection triggers all three simultaneously
(same tick), topology=PASS_A on each so output = the cell's own preloaded `a_data`
(the trigger's value is irrelevant, only its address-match matters).

- **RUN 1 (all three -> output_address 100, data 0x1/0x2/0x4):** exactly one
  `out_valid` pulse, `out_addr==100`, `out_data==0x7`. Confirms the free N-way OR
  reduction, exactly as predicted.
- **RUN 2 (cell0,1 -> 100, cell2 -> 101, same data):** exactly one `out_valid`
  pulse (no fault flag, no double-pulse), `out_addr==101` (the LAST firer's
  address, cell2's — NOT cell0/1's intended 100), `out_data==0x7` STILL. Confirms
  the exact corruption mode: cell0/1's data silently bleeds into cell2's address.

Both predictions in this section are now **sim-proven, not just RTL-read**. Full
11-testbench regression re-run clean alongside it (twoslot/auth_relocate/bank/
load_done/three_cycle_load/transit/transit_obs/array_reset/obs_contam/shl_cell/
wired_or) — nothing else affected, this was read-only observation, no RTL touched.

**#17's constraint is now safe to relax** to: *"no two same-depth cells in a
cluster with DIFFERENT output addresses"* — same-address same-depth cells are a
reduction, not a collision, on real (simulated) fabric behaviour, not just a
reading of the `always @(*)` block.

### SILICON-CONFIRMED (2026-07-10) — `fpga/zone1_wired_or.tcl`, Arria 10 GX660
Both predictions now hold on the die, exactly matching the sim result above:
- **Same-address run:** `out_count=1`, `out_addr=100`, `out_data=0x7`. Free N-way
  OR reduction, real silicon, bit-for-bit match to `tb_v3_wired_or.v`.
- **Different-address run:** `out_count=1`, `out_addr=101` (LAST firer wins,
  silently), `out_data=0x7` STILL (cell0/1's bits contaminating cell2's
  address). Corruption mode confirmed exactly as predicted.

(First silicon attempt used `CMD_RECONFIGURE`, which broadcasts and silently
wiped each earlier cell's armed state — a live demonstration of the exact
anti-pattern `CMD_LOAD_AT` exists to prevent. Fixed by switching the TCL's
topology-write opcode to `CMD_LOAD_AT`, matching the sim testbench; the
corrected run is what's reported above.)

**#32 is now both sim- and silicon-proven, not just RTL-read.** #17's placement
constraint stands relaxed: *"no two same-depth cells in a cluster with
DIFFERENT output addresses"* — same-address same-depth cells are a genuine free
reduction on real hardware.

## 33. DSP results to BRAM — the fabric becomes a control plane (Alan, 2026-07-09)

**Status: architectural decision. Kills PLAN's DSP caveat 4 (interconnect). Refines
the save-state invariant. Reuses `bram_dp_v3.v`, which is already dual-port.**

Alan: rather than spend many cells gathering DSP results and controlling the chain,
**write the results to BRAM.** The fabric only needs to know *where* they are and
*that they are ready*.

### The number
A 27-block DSP chain, dynamically partitioned (PLAN step 3):
| Segments | Tap `result` ports into cells | Write to BRAM + tell fabric | Saving |
|---|---|---|---|
| 3  | 3 x 64 = **192** wires | 1 ready + 16-bit addr = **17** | 91% |
| 9  | 9 x 64 = **576** wires | **17** | **97%** |
| 27 | 27 x 64 = **1728** wires | **17** | 99% |

#24 measured **36% peak interconnect** where the fabric bus converges. Routing binds
before logic. **This is exactly the resource being saved.**

### What it becomes: CONTROL PLANE / DATA PLANE
- Fabric fires **"go"**.
- DSP chain computes; an address generator streams results into BRAM.
- A **"ready"** value lands on a watching cell's input address.
- That is an **arrival**. The two-arrival model absorbs it with **no new mechanism** --
  the cell fires when results are ready, exactly as for any other value.

The fabric needs two things: *where*, and *are they there yet*. Not N wide buses.
`bram_dp_v3.v` is already dual-port ("Port A -- write side"): DSP writes A, fabric or
loader reads B. No arbitration.

Honours PLAN's principle -- *"DSP does the multiply; fabric does what only the fabric
can do (topology, routing, control)"* -- and extends it: **BRAM does the buffering;
the fabric does the dispatch.**

### Consequence 1 (a real change): the SAVE-STATE INVARIANT refines
We held: *"DSP states carry no persistent state -- cell states alone are the complete
save-state."* With results in BRAM that is no longer true. It becomes:

> **cell states + declared STATEFUL BRAM regions = the complete save-state.**

The shape/MAN file must mark each BRAM region **scratch** (recomputable, discard on
checkpoint) or **stateful** (weights, lattice, accumulators -- must be saved). A clean
refinement, not a breakage; slots into the three-ICM-states model.

### Consequence 2: an address generator is needed
Base, stride, count, done. A small FSM inside the DSP bridge -- **RTL, not cells.**
Deterministic, because DSP latency is countable (position-dependent, #26).

### Consequence 3: a BRAM->cell read bridge, only if the fabric consumes results
Another latency-domain crossing, same shape as the DSP bridge. But for math-heavy
pipelines (LBM, convolution, matmul) results feed the **next DSP pass** and never
leave BRAM. That is where this design wins hardest.

### Consequence 4: the PHILOSOPHICAL GUARD
This gives the fabric a memory-mapped coprocessor, and there is a genuine drift risk
toward Von Neumann. Alan's own principle applies: *"Python papers over what the fabric
cannot do; silicon forces the rewrite."* **BRAM+DSP can paper over it just as easily.**

The guard is already in PLAN.md: **the pure-fabric path stays the REFERENCE**, and
every tile must be expressible BOTH ways. As long as *control* stays topological
(two-arrival firing), the philosophy holds: the DSP+BRAM block is a **leaf operator
that happens to be large**, not a CPU the fabric obeys.

### Fits an existing pattern
"Results region + ready flag" is precisely a **Shore** entry (Shore = purely tables
and address space). The fabric consults the table; the data plane fills it.

## 34. Why the hybrid is a correct FACTORING, not a compromise (Alan, 2026-07-09)

**Status: architecture + resource economics. Supports #25/#26/#33 and PLAN's
"hybrid is an optimisation layer, never the foundation".**

Alan: *"the logic and control stay on the UniCell side... programs aren't just math,
they have logic and choice... leveraging these DSP units is a bonus, as the cell
resource is tight on these cards."*

### The resource profile of the GX660 (ESTIMATE -- see "measurement needed" below)
| Resource | Count | Character |
|---|---|---|
| Cells | **~387** (ALM-bound) | soft logic, **~646 ALM each** |
| DSP blocks | **1,687** | hard, dense, currently **0 used** |
| ratio | **~4.4 DSP : 1 cell** | |

One 25-cell zone + harness = 17,655 ALM (Fitter, measured). The packed adder is 37
cells -- **ten adders and the card is full.** Cell resource IS tight, exactly as Alan
says. And #24 says interconnect binds before logic, so ~387 is an upper bound.

### The factoring is structural, not pragmatic
What a cell is **natively** good at -- and none of it is arithmetic:
- **Free OR-reduction** on the wired-OR bus: N->1 in ONE tick, zero cells (#32).
- **Free multicast**: one fire -> four cardinal directions (#17).
- **Choice and join**: the **two-arrival firing rule IS a synchronisation
  primitive.** Branching is topology.

What a cell is bad at:
- 32-bit ADD = **37 cells** (#17, verified).
- 32-bit MULT = a Wallace/Booth tree of adders. Far more.
- A DSP does either in **1 block, 0 cells.**

> **Cells are cheap at control and expensive at arithmetic.**
> **DSPs are cheap at arithmetic and incapable of control.**
> They are not competing for the same job -- they are two halves of one.

### Concretely: LIF (#31)
Of its 15 cells, ~8 are arithmetic (SYN_MUL, V_LEAK, V_INT, V_CMP, DW, W_NEXT,
PRE_DEC, PRE_TRACE) and ~7 are control/state (threshold, SPIKE, reset, the DELAY
cells, AXON). Move the arithmetic to DSP and the neuron's **cell** cost roughly
halves. Since cells are the binding resource, that **roughly doubles neuron density**
on the card. (Rough: the DSP bridge itself costs cells, and latency changes. But the
direction and magnitude are real.)

### The point that strengthens the existing principle
This resource profile -- **cells scarce, hard arithmetic blocks abundant** -- is an
artifact of **hosting UniCell on an FPGA**, not a property of UniCell. A
silicon-native cell would be tiny, and there would be no separate DSP column to
borrow from.

So the hybrid is not a concession to a weakness in the architecture; it is the right
answer **for this substrate**. That is exactly PLAN.md's "hybrid is an optimisation
layer for deployment scale, never the foundation" -- now with a **resource-economics**
argument behind it rather than a purity one. And it is why the pure-fabric path must
remain the REFERENCE: it is the substrate-independent statement of the model.

### Measurement needed (replaces the estimate)
Build a **2-zone** design and subtract from the 1-zone fit. That gives:
1. the true **marginal ALM cost per cell** (harness cancels), and
2. the **interconnect scaling** #27 asked for (does the 36% peak grow?).
**One build, two numbers.** Both currently unknown and both load-bearing.

## 35. Soft = visible, hybrid = fast: the ICM carries both (Alan, 2026-07-09)

**Status: clarifies #23/#25/#33/#34. Confirms the three-ICM-states model.**

Alan: *"this design is for the hybrid models, and that's why I build both -- the full
model and test it, then optimise for the hybrid... one of the ICM functions is
recognise it's being loaded into an FPGA, so it uses those resources, and the
fallback is the full model. While in the VM it just uses the full model, so the user
can see it fully, but on a card get good fast results."*

### The ICM carries BOTH lowerings
- **Soft reference**: pure-fabric, cell-only. Card-agnostic, portable, verifiable.
- **Hybrid substitutions**: arithmetic tiles mapped to DSP + BRAM (#33), keyed to
  declared resources.

This IS the three-ICM-states model: portable/soft-only (correctness proof,
card-agnostic); card-tailored/hybrid runtime (card-stamped, carries a refuse-to-load
guard for the wrong card); save-back checkpoint.

### REFINEMENT: the BINDER recognises, not the ICM
If the ICM *detects* its host it becomes card-aware and stops being the portable
artifact #23 requires. Cleaner seam:
> The **ICM offers** both lowerings. The **binder chooses**, because the binder
> already reads the MAN file and already knows what DSPs exist, how many, and at what
> latency (#26).

The ICM **declares a capability**; it does not sniff its environment. Same behaviour,
correct layering. The refuse-to-load guard then sits on the **card-stamped hybrid
artifact**, not on the portable model.

### Why the VM runs the SOFT model -- a better reason than "fallback"
**A DSP block is opaque.** You cannot watch a multiply happen inside hard IP. The
soft model is **observable** -- every cell, every fire, every tick -- which is exactly
what #20's step feature needs in order to show collisions and bus contention.

> **Soft = visible. Hybrid = fast.**

The VM is not running the slow path because it cannot run the fast one. It is running
the path you can **see**.

### And the soft model is the CORRECTNESS ORACLE
Not merely a fallback. The hybrid must produce **bit-identical** results, and the soft
path is what you diff against. This is the same discipline as sim-before-silicon: the
thing you trust is the thing you can inspect. Alan's sequence -- *build both, test the
full model, then optimise for the hybrid* -- is differential testing with the
verifiable artifact as reference.

Reinforces PLAN's principle from a third angle (after #34's resource economics):
**the pure-fabric path stays the REFERENCE** because it is (a) substrate-independent,
(b) observable, and (c) the oracle.

## 36. Scalability is the one thing that cannot be proven small (2026-07-09)

**Status: framing + a concrete experiment ladder. The project's central open question,
made measurable.**

Alan: *"most of this was on the iceBreaker -- even the 8 cells firing in parallel, the
round-robin tests, the chain and cascade of data without a control sequence. All have
had some degree of confirmation. This is just larger. Scalability is the one thing
not fully proven."*

Correct on the primitives. But **"just larger" understates what changes.**

### Collision, contention and congestion are EMERGENT
They do not exist at 8 cells. They require enough cells sharing a bus, enough clusters
competing for a cycle, enough nets converging on a region. At iceBreaker scale these
phenomena **cannot occur**. So the Arria 10 is not a bigger version of a proven
thing -- it is the **first place these phenomena can exist at all.**

This is why #24's number matters more than it looked: **2% average interconnect, 36%
peak.** That is the first sighting of a scale-only phenomenon, and it says **routing,
not logic, binds.** Nobody could have seen it on an iceBreaker. It was not there.

### So scalability is a CURVE, not a yes/no
- Does it still **work** at N zones?  (primitives say yes; bridges proven in sim)
- Does it **fit**?  (ALM/cell ~646 -- an ESTIMATE, #34)
- Does it **close timing**?  (Fmax vs zone count -- unmeasured)
- Does the **routing** hold?  (36% peak -- exactly ONE data point)

### The experiment ladder (3 builds)
Build **1, 2, and 4 zones**. Record for each: ALM, average + peak interconnect, Fmax,
and correctness of a cross-zone model.

- **Marginal ALM/cell** falls out of (2-zone - 1-zone); the harness cancels. Replaces
  the #34 estimate.
- **Interconnect scaling** is the headline. If peak grows **linearly or sublinearly**,
  the pentacross scales. If it grows **superlinearly**, the shared bus is the limit --
  and #22's directional single-cell fabric stops being an interesting alternative and
  **becomes the answer.**
- **Fmax vs N** shows whether the wired-OR aggregation (an N-way combinational OR
  across cells, #32) degrades with cluster occupancy.

Three builds, and the central open question of the architecture becomes a plotted
curve rather than a worry. The instrument already exists.

### Note
This also decides #22 empirically rather than by argument. The directional fabric's
1.7x cell overhead is only a bad trade **if** the pentacross's shared bus scales. The
36% peak is the first hint that it may not.
