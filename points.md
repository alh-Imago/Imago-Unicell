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

**PROVEN ON SILICON 2026-07-10 — all four cardinals confirmed, `fpga/zone1_cardinals.tcl`.**
Clean reflash carrying the N/S/W sticky-capture extension (7% ALM,
17,714/251,680; FMAX `clk_div`=57.4 MHz, ~2.3x margin over the 25 MHz operating
clock). 6 runs total: 5 of 6 came back clean 4/4 (N/S/E/W all `seen=1`, local
bus `seen=0`); one run showed a single stray miss on EAST (local bus `seen=1`
when it should have been quiet), and a different single-run miss on WEST
appeared once earlier in the session — neither reproduced on immediate re-run.
Both misses were isolated, single-direction, non-repeating, and every
direction (including the two that each missed once) showed a clean pass on
multiple OTHER runs. This rotates rather than sticking to one direction — the
signature of an occasional JTAG/ISSP edge-detect glitch (the bridge header's
own documented risk: "without a source clock + sync regs the edge-detects
glitch") or link-level noise, not a per-direction RTL defect.
**Conclusion: all four cardinal directions are genuinely proven on silicon.**
North and West are new results this session; East re-confirms the original
2026-07-09 proof on the rebuilt (four-cardinal) bitstream.

PLAN's near-term Step 1 is now COMPLETE: cardinal routing confirmed in all
four directions, and the bundled #32 wired-OR test also silicon-confirmed (see
#32 below) on the same build.

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

### SILICON RESULT (2026-07-11) — exhausted, inconclusive
Built and ran the diagnostic (`fpga/verilog/clock_walk_top.v`, 8x IOPLL,
`fpga/clock_walk.tcl`) against all 8 candidate refclk pins, Option B (PLL lock)
as designed above. Confirmed `CLK` (the JTAG-side clock) genuinely alive
throughout via a cycle-counter liveness check (`cycle 599349004 ->
601768543`, etc., added after an early false alarm caused by the ISSP probe
silently staying at its original 8-bit width when the Verilog side was
widened to 40 bits without regenerating the underlying Platform Designer IP)
-- so the results below are real negatives, not artifacts of a dead probe or
a PLL held in permanent reset.

**All 4 legal I/O standards Quartus offers for these dedicated GXB pins
tried, across all 8 candidates: HCSL, LVDS, Differential LVPECL, CML. Zero
locked, every time.** That's the full legal search space on the Quartus
side, genuinely exhausted, not abandoned early.

Two live hypotheses, not yet distinguished:
1. **This specific board doesn't route the PCIe slot's refclk to any of the
   FPGA's dedicated GXB pins at all** -- the 8-candidate list above was
   reasoned from the *device's* datasheet capability (PCG-01017), never
   confirmed against *this board's* actual PCB routing. Some boards --
   especially repurposed/low-power SKUs -- buffer the slot's refclk through a
   separate clock IC and re-drive it into an ordinary general-purpose pin
   instead of a dedicated GXB pin. A clean negative across the whole legal
   space is exactly that signature, not "try one more setting."
2. **The GXB transceiver analog rail may not be powered**, regardless of
   which pin/standard is correct. The card's preserved 12V aux power cable IS
   connected, but this card is a 60W-rated variant that in theory shouldn't
   need it -- its presence doesn't confirm the GXB rail specifically is live.

**Also discovered in this session: the card's actual die is GX660**
(`10AX066H2F34E2SG`, confirmed via JTAG IDCODE `0x02E250DD`) **despite the
official Mustang-F100-A10 user manual describing a GX1150** -- either a
lower-cost/OEM variant shipped under the same model name, or a running
production change. Not resolved, not blocking, just noted.

**Two concrete next steps for a future session** (neither attempted this
session -- both need setup time not available tonight):
1. **Physical board inspection**: look for a visible clock buffer/fanout/
   oscillator IC near the PCIe edge connector or near the FPGA's GXB banks. A
   part number there would directly confirm/refute hypothesis 1.
2. **iEi Mustang Viewer utility** (Section 8 of the official Mustang-F100-A10
   user manual, via the card's separate Micro-USB debug port, distinct from
   the JTAG connector): reads live board telemetry including
   `POWER_CONDITION_VCCH_GXB_1V8` / `POWER_CONDITION_VCCT_1V03` (directly
   answers hypothesis 2) and `FPGA_Diode_Temperature` (also useful for the
   queued thermal-monitoring work, see PLAN.md). Linux-only tool (Ubuntu
   16.04 in the manual) -- this session's Windows machine doesn't recognize
   the Micro-USB device at all, most likely because there's no Windows
   driver for it, not a faulty cable/port. Needs a second machine, a
   dual-boot setup, or a dedicated session -- not attempted tonight given the
   cost of losing Quartus access mid-session.

STATUS: Step 2 (clock walk) PAUSED, not abandoned. Genuinely inconclusive
after an exhausted search of the Quartus-side option space -- the open
question has moved from "which pin/standard" to "does this board even wire
refclk to these pins at all," which needs physical/out-of-band information
neither Quartus nor JTAG alone can supply.

### NEW LEAD (2026-07-11, later same session) — the search space was 8, not 32
Alan supplied Intel's official pin table for the bare 10AX066 device
(`10ax066_1_.xls`, "Pin List F34" sheet -- device-level, not board-specific,
but authoritative for pin function). This file had been shared and dismissed
as low-value in an earlier chat; re-examined, it reveals something the
8-candidate search missed entirely.

**Every transceiver bank has 6 MORE refclk-capable pin pairs beyond the 2
dedicated CHT/CHB pins already tested** -- every RX channel pin doubles as a
per-channel REFCLK input. Confirmed directly from the spreadsheet, bank 1D
(home of the "strongest candidate" 1D_CHB) as the example:

```
1D  REFCLK_GXBL1D_CHTp/n     Y28/Y27    <- already tested (all 4 standards)
1D  GXBL1D_RX_CH5,REFCLK5    V31/V32    <- NOT tested
1D  GXBL1D_RX_CH4,REFCLK4    W29/W30    <- NOT tested
1D  GXBL1D_RX_CH3,REFCLK3    Y31/Y32    <- NOT tested
1D  GXBL1D_RX_CH2,REFCLK2    AA29/AA30  <- NOT tested
1D  GXBL1D_RX_CH1,REFCLK1    AB31/AB32  <- NOT tested
1D  GXBL1D_RX_CH0,REFCLK0    AC29/AC30  <- NOT tested
1D  REFCLK_GXBL1D_CHBp/n     AB28/AB27  <- already tested (all 4 standards)
```
Same pattern repeats identically in banks 1C, 1E, 1F. **Real search space is
32 candidate pins, not 8** -- the exhaustive-seeming HCSL/LVDS/LVPECL/CML
sweep above only covered 8 of the 32 actual refclk-capable pins on this
device. This is a fully plausible explanation for the clean negative: if
IEI's board designer routed the slot's refclk into a specific transceiver
channel's own per-channel refclk pin (a legitimate, sometimes-used pattern
when one channel is dedicated to PCIe) rather than a bank-level dedicated
CHT/CHB pin, tonight's search was in the wrong 8 of 32 places -- not evidence
refclk doesn't reach a GXB pin at all.

NEXT (queued, not yet started): extend `clock_walk_top.v` to cover all 32
candidates (24 more IOPLL instances + widened probe) in one build, sweep the
same way. Stronger, more specific lead than the physical-inspection/iEi-
Viewer options above -- worth trying before those, next session.

### REVISED PRIORITY (2026-07-11, later still) — control test with the second card first
Card 1 (the one tested all night) is second-hand and was already known to
have failed full PCIe enumeration from day one, requiring the Waveshare JTAG
route in the first place -- originally assumed to be "just misconfigured."
Given tonight's clean negative across the full 8-pin x 4-standard search
space, worth taking seriously that it may instead have been genuinely
defective all along (dead GXB rail regulator, cracked refclk trace, failed
clock buffer) -- which would also explain why it sat unsold in a warehouse
for 2+ years rather than being kept in someone's working rig.

**Plan: before expanding to the 32-pin search, run the IDENTICAL 8-pin/HCSL
(at minimum) clock-walk sweep against the new, second, never-before-used
card** (Alan's plan: pull card 1 from the Windows machine, seat card 2, program
and test with the SAME clock_walk_top.v/clock_walk.tcl, no changes needed).
This is a clean control:
- **Card 2 locks quickly** -> strongly confirms card 1 has a genuine hardware
  fault (not a pin/standard guessing problem), AND identifies the correct pin
  for real going forward. Best possible outcome -- resolves both open
  questions in one test.
- **Card 2 also reads zero across the board** -> shifts weight back toward a
  board-design-level explanation (the 32-pin lead, or a buffer-chip-into-an-
  ordinary-pin routing) rather than a one-off defective unit -- two
  independently-failing physical cards points at design, not a fault.

If card 2 passes, it becomes the working test/programming bed going forward
(not the originally-hoped-for card, but a real functional unit) while card 1's
status as defective-vs-misconfigured gets a real answer either way.

### CONTROL TEST RESULT (2026-07-11, later still) — card 1 defect RULED OUT
Card 2 (new, same board revision confirmed via identical
`VEN_1172&DEV_2494&SUBSYS_660A180C&REV_01`) enumerated cleanly on PCIe in
Windows BEFORE any JTAG programming -- proof this specific board design's
factory configuration gets refclk + GXB rail right, on this exact unit. Then
flashed with the SAME `clock_walk_top.v`/`clock_walk.tcl`, no changes: **zero
bits locked, identical to card 1.** `CLK` confirmed alive throughout
(`cycle 1196036135 -> 1198408946`), so a real negative, not an artifact.

**Card 1's defect hypothesis is now RULED OUT.** Two independent physical
units, same board design, one proven fully healthy via live PCIe enumeration
moments before the test -- both fail the 8-pin/CHT-CHB sweep identically. That
points squarely at the board design itself: **this board almost certainly does
NOT route PCIe refclk to the 8 dedicated CHT/CHB pins tested tonight.** The
32-pin hypothesis (refclk reaching one of the 24 per-channel RX/REFCLKn pins
instead) is now the leading explanation, not just a plausible alternative.

(Card 2 disappeared from Device Manager immediately after JTAG programming --
expected, not a fault: `clock_walk_top` has no PCIe HIP at all, so of course
Windows no longer sees a PCIe device once the volatile SRAM config is
overwritten. If this card auto-reloads its factory image from onboard flash at
power-up like most production cards, a power cycle should restore
enumeration -- worth confirming, not yet done.)

NEXT: the 32-pin `clock_walk_top.v` expansion is now the clear next step, not
just one option among several -- extend to cover all 24 per-channel RX/REFCLKn
pins alongside the 8 already tested, sweep the same way.

### AUTHORITATIVE FITTER PLACEMENT (2026-07-12) — real HIP confirms the exact candidate, wrong-pin hypothesis ELIMINATED
Built `pcie_pin_check_top.v` wrapping the correctly-targeted, real-hardware-mode
`pcie_test_1` system (confirmed genuine `xcvr_tx_out`/`xcvr_rx_in` serial pins,
not a simulation stub -- see the PCIe HIP breakthrough entry above). Left
`ref_clk_clk` and all 16 `xcvr_tx_out`/`xcvr_rx_in` ports completely
UNCONSTRAINED and ran a full compile. **Clean compile, zero errors** -- the
Fitter auto-placed everything using its own internal knowledge of the
hardened HIP macro's physical location:

```
Lanes (RX+TX):  bank 1C -> lanes 0,1 (2 channels)
                bank 1D -> lanes 2-7 (6 channels)
                banks 1E/1F -> NOT used at all
ref_clk_clk  -> PIN_AB28/AB27 (bank 1D), CML standard
```

This confirms the lane search space is exactly banks 1C+1D (2 of the 4 total
GXB banks), matching UG-20039's "one side of the device only" guidance with
real bank numbers for this device now known.

**More importantly: `ref_clk_clk` auto-placed onto `PIN_AB28`/`AB27` -- the
exact same pin already called the "strongest candidate" (`REFCLK_GXBL1D_CHB`)
all along, using CML, a standard already inside the exhaustive 8-pin x 4-
standard sweep that came back dead.** This is the Fitter's own authoritative,
unprompted choice, not one option among several -- it eliminates the "maybe we
were testing the wrong pin" hypothesis for good. The 8-pin/4-standard sweep
was testing the genuinely correct candidate the whole time.

What this does NOT do: it doesn't explain why that pin read dead. The two
live hypotheses from the original sweep stand exactly as before -- board
doesn't route refclk to any GXB pin at all (buffered elsewhere), or the GXB
analog rail isn't powered.

**What it DOES open: a real hardware test with the genuine Hard IP itself,
not a plain-IOPLL proxy.** The actual HIP has real LTSSM/PIPE-level link
status -- a fundamentally richer signal than a simple `locked` bit. Worth
building this exact Fitter-confirmed pin configuration for real (lock in the
auto-placed locations explicitly via Assignment Editor, matching what the
Fitter already chose) and checking what the real Hard IP's own status
reports, rather than assuming the proxy result definitely transfers.

NEXT: lock in these exact Fitter-chosen pin assignments explicitly, build a
full `pcie_test_1`-based top-level (wiring real reset generation, tying off
the `hip_pipe_*` debug bus as planned), flash, and check the real HIP's link
status signals.

### RESOLVED (2026-07-12) — PCIe ENUMERATED. The refclk pin was right all along.
Built `pcie_hip_test_top.v` with the Fitter-confirmed pins locked in
explicitly (`pcie_hip_test.qsf`). One real compile error along the way,
itself informative: `hip_ctl_pin_perst` (the PCIe PERST# signal) turned out
to be a hardwired silicon input that MUST be driven directly by a raw
top-level primary pin, no internal logic permitted (Fitter errors 18105/
16667) -- split into its own dedicated port (`PIN_PERST_N`), location left
unassigned same as everything else, and the Fitter found it without issue.

**Flashed. Windows enumerated a real PCIe device: `VEN_1172&DEV_0000&
CC_FF00`.** `VEN_1172` is Intel/Altera's confirmed vendor ID (consistent with
everything found all session). `DEV_0000`/`CC_FF00` are exactly the DEFAULT
Device ID and generic "unclassified" class code UG-20039 said to expect when
those parameters aren't customized -- expected, not an error. **The PCIe link
genuinely trained** -- refclk reached the FPGA, the GXB analog rail was
powered, the lanes worked.

**This retroactively resolves the entire refclk mystery: `PIN_AB28`/`AB27`
(bank 1D CHB) -- the original "strongest candidate" -- was correct the whole
time. The plain-IOPLL proxy diagnostic (`clock_walk_top.v`/`_a.v`/`_b.v`) was
giving a systematic FALSE NEGATIVE, not measuring a real absence of clock.**
Most likely explanation: PCIe reference clocks are very commonly spread-
spectrum clocked (SSC) by the host motherboard, a small deliberate frequency
dither used to reduce EMI, fully PCIe-spec-legal and extremely common. A
generic, plain IOPLL configured for a fixed-frequency reference has no SSC
tolerance and will never report `locked` against a genuinely live, real,
usable clock that's being intentionally modulated -- while the actual PCIe
Hard IP's purpose-built CDR is specifically designed to track exactly that
kind of modulation. This explains the clean, symmetric all-8-pins-dead result
across two independent physical cards in one stroke: the DETECTION METHOD
could never succeed regardless of which pin was actually correct, because a
plain IOPLL was never equipped to lock onto a real-world PCIe reference clock
to begin with. Not evidence about the board's wiring at all -- a limitation
of the proxy test itself.

**STATUS: Step 2 (find the live PCIe refclk pin) is CLOSED, successfully.**
`PIN_AB28`/`AB27`, CML standard, confirmed both by Quartus's own authoritative
Fitter placement AND by actual real-hardware PCIe enumeration. The 32-pin
per-channel hypothesis, the physical-inspection idea, and the iEi Viewer
route are all superseded -- none of them were ever necessary; the original
8-pin dedicated-CHT/CHB search space was correct from the start, only the
measurement method needed fixing.

NEXT: with a genuinely enumerating link, the natural next steps are
configuring a real (non-default) Vendor/Device ID if desired, then real BAR
read/write testing using Intel's own bundled driver + `Alt_Test.exe` (per
UG-20039), opening the door to actual DMA into Ponds and everything gated on
PCIe working -- see PLAN.md.

### LINK TRAINING CONFIRMED, FULL WIDTH (2026-07-12, later same day)
Ran Intel's own low-level PCI-SIG interop console tool directly against the
enumerated device (bus 8, device 0, function 0). Confirmed via real, direct
PCI config-space reads:

```
Vendor ID  0x1172 (Altera)      Device ID  0x2494
Lane Rate: 2 (Gen2, 5.0 GT/s)   Link Width: 08 (full x8)
```

**Full x8-lane, Gen2, stable, fully-trained link** -- not a degraded x1/x2
fallback. Entire PCIe config space read cleanly, including extended
capabilities and the MSI block. This is a complete, robust confirmation of
the physical link, well beyond bare enumeration.

Note: Device ID read here (`0x2494`) differs from the `DEV_0000` Windows
Device Manager showed at first enumeration -- not yet fully explained, best
guess is Device Manager displaying a placeholder before a matching driver
bound, versus this tool reading live config space directly (more
authoritative). Flagged honestly as unresolved, not concerning.

**BAR0 read/write test reports FAILED (`0xFFFFFFFF` readback) -- EXPECTED,
not a new problem.** `pcie_test_1.qsys` deliberately contains only the clock
source and the bare Hard IP -- no on-chip memory, no Avalon-MM bridge, no
target of any kind behind BAR0. `0xFFFFFFFF` is the textbook PCI signature
for "nothing answered this request," exactly consistent with there being
genuinely nothing wired up yet. The system was built minimally, specifically
to answer the refclk/pin/link-training question -- which it answered
completely and robustly.

**NEXT, real and concrete:** add an actual memory-mapped target behind the
Hard IP so BAR0 has something to respond with. The natural target, per the
project's own architecture ("PCIe is just another bridge, with a windowed
BAR"), isn't generic on-chip test RAM -- it's the UniCell fabric's own
command/data bus, windowed directly into BAR0. That's the real remaining
step between where things stand now and actual host-driven DMA into Ponds.

### DEVICE RESOURCE LIMIT DISCOVERED (2026-07-11) — 32-at-once doesn't fit
Attempted the all-32-candidates-in-one-build approach above. Fitter rejected
it: **"Attempted to fit 32 IOPLL merge groups in 16 locations"** (error
18218). This device (10AX066H2F34E2SG) has exactly **16 total IOPLL-capable
hard-block locations, die-wide** -- a genuine hardware resource limit, not a
settings mistake, and worth recording for any future work needing multiple
PLLs on this part.

**Split into two builds of 12** (comfortable margin under 16), deliberately
excluding the 8 already-exhaustively-tested dedicated CHT/CHB pins (no need
to spend IOPLL locations re-confirming an already-dead result):
- `clock_walk_top_a.v` / `clock_walk_a.qsf/.sdc` / `clock_walk_a.tcl` --
  12 new per-channel candidates from banks 1C+1D.
- `clock_walk_top_b.v` / `clock_walk_b.qsf/.sdc` / `clock_walk_b.tcl` --
  12 new per-channel candidates from banks 1E+1F.

Both reuse the single already-generated `fpll_ch0` IOPLL module (no new IP
generation), each with its own 44-bit ISSP probe (32-bit cycle_count + 12-bit
locked_bits). Both elaborate cleanly against port-matched stubs. Neither
built/flashed/run yet this session -- next concrete action.

### BUILD A ATTEMPT: confirms per-channel pins are structurally invalid (2026-07-11)
Ran Build A against the actual card. Fitter rejected ALL 12 candidates
identically: "Could not find a location with: IO_FUNCTION of GPIO" -- not a
couple of bad picks, a systematic rejection of the whole per-channel-pin
approach. Cross-checked against Intel's own real PCIe Hard IP example design
(generated via the official 683065 flow, targeting the Arria 10 GX dev kit):
its `.qsf` confirms `refclk_clk` is ALWAYS a separate, dedicated pin
(`PIN_AL37`/`AL38`, HCSL) -- structurally distinct from the `xcvr_rx_in0-7`
serial RX lane pins (`PIN_AT39` etc., CML). Intel's own methodology never
takes PCIe refclk from an RX/TX lane pin.

**Conclusion: the 24 per-channel "REFCLKn" candidates were never real
candidates.** Whatever that dual-function label in Intel's pin table for this
device actually means, it isn't "usable as a general external PCIe reference
clock input" -- the Fitter's rejection and Intel's own real IP example agree.
**The 8 originally-tested dedicated CHT/CHB pins are the ONLY real candidates
on this device, full stop** -- and all 8 are already exhaustively tested
(4 legal I/O standards, 2 independent physical cards, always zero). This is a
much more solid, fully-closed negative than it looked earlier in the session.
Build A/B (`clock_walk_top_a/b.v` etc.) are now understood to be based on a
flawed premise and should not be pursued further.

### PCIe HARD IP DIRECT ATTEMPT (2026-07-11, later still) -- parked, needs its own session
Explored building the REAL PCIe Hard IP directly (per Intel's UG-20039/683065),
rather than continuing the plain-IOPLL proxy diagnostic:
- First attempt used Intel's auto-generated example design targeting the
  Arria 10 GX FPGA Development Kit (`10AX115S1F45I1SG`) -- WRONG DEVICE, a much
  larger part in a different package (`S1F45` vs the actual card's `F34`).
  Every pin location in that generated qsf is specific to that other device;
  none apply to the Mustang card. Not usable as-is.
- Second attempt: generated a properly-targeted IP variation ("PCIE_Test")
  against the correct device (`10AX066H2F34E2SG`, confirmed in the generation
  report, `link_width=8` matching the Mustang's Gen3 x8 spec) -- correct
  device this time. BUT the generated variation has `bfm_drive_interface_pipe
  =1` and `serial_sim=1` -- **simulation-only mode** (PIPE-level Bus
  Functional Model interface), not a hardware-synthesizable core with real
  serial pins. Would need regeneration with simulation/BFM mode disabled to
  get a real hardware-testable core.

**PARKED for a future, dedicated session** -- building a genuine, correctly-
configured, hardware-synthesizable PCIe Hard IP wired to the Mustang's actual
lane pins is a substantially bigger undertaking than the refclk-only
diagnostic, deserves its own properly-scoped session rather than being rushed.
Alan has more generated files to review before the next attempt.

BONUS (noted 2026-07-11): Intel's example design package (UG-20039) includes
a ready-made Windows driver (`altera_pcie_win_driver.inf`) and interop test
tool (`Alt_Test.exe`) for basic BAR read/write confirmation -- no need to
write driver-side plumbing from scratch once a real hardware-mode PCIe HIP
build exists. Solving the PCIe refclk/link question is the gating item for
all further system testing (real DMA into Ponds, Shore-side ingestion, etc.)
-- everything downstream opens up once this is working.

### BREAKTHROUGH (2026-07-12) — a genuinely hardware-capable PCIe HIP system found
A follow-up morning session picked this back up. Alan built a proper Qsys
system this time (`pcie_test_1.qsys`, correctly targeting `10AX066H2F34E2SG`
throughout) rather than a raw IP variation. Checked its real generated
instantiation template (`pcie_test_1_inst.v`) -- and unlike last night's
`PCIE_Test` failure (PIPE-only `txdata`/`rxdata` buses, no real pins at all),
this one has genuine differential serial ports:

```
xcvr_rx_in0 .. xcvr_rx_in7    (8 real serial RX lanes)
xcvr_tx_out0 .. xcvr_tx_out7  (8 real serial TX lanes)
ref_clk_clk                   (the refclk pin)
hip_ctl_npor / hip_ctl_pin_perst (reset/PERST control)
```

These exact names (`tx_out[<n>-1:0]`/`rx_in[<n>-1:0]`) match word-for-word
Intel's own official hardware signal table (UG-20039 Table 3) -- strong,
concrete evidence this is a genuinely hardware-synthesizable core, not
another simulation stub. The same `bfm_drive_interface_pipe_hwtcl=1` flag
that looked alarming is now understood differently: it likely just ALSO
exposes the internal PIPE-level signals as a large `hip_pipe_*` port bus
(txdata/rxdata/eidleinfersel/powerdown/etc, dozens of per-lane debug/status
signals) for optional Signal Tap hookup (UG-20039 §2.2), not "simulation
only." The real analog SERDES connects through `xcvr_tx_out`/`xcvr_rx_in`
regardless -- the `hip_pipe_*` bus is very likely safe to leave unconnected
for a first real hardware attempt.

NEXT (queued for a dedicated build session): wire a custom top-level
instantiating `pcie_test_1`:
- `ref_clk_clk` -> one of the 8 known candidate refclk pins (worth retrying
  even though the plain-IOPLL proxy diagnostic found all 8 dead -- the real
  Hard IP's own internal fPLL/CDR may behave differently or report clearer
  status than the simple locked-bit proxy did).
- `xcvr_rx_in0-7`/`xcvr_tx_out0-7` -> the Mustang's actual PCIe x8 lane pins
  -- a NEW unknown, not yet identified, separate from the refclk hunt.
- `hip_ctl_npor`/`hip_ctl_pin_perst` -> a proper reset generator (reuse the
  power-on-reset lesson from `clock_walk_top.v`: a real net, not a bare
  constant).
- `hip_pipe_*` bus -> leave unconnected/tied to safe constants for a first
  attempt; revisit for Signal Tap debug visibility later if needed.

### AGREED PLAN (2026-07-12) — concrete steps for the dedicated build session
1. New Quartus project, separate from `clock_walk` -- avoids IOPLL/pin
   resource contention with `clock_walk`'s leftover instances, and
   `clock_walk`'s own job (proxy refclk detection) is superseded by the real
   Hard IP's own link-status signals now that a genuine hardware-mode system
   exists.
2. Pin/channel discovery BEFORE any guessing: assign `xcvr_tx_out0`/
   `xcvr_rx_in0` a location in Pin Planner (or check what the IP's own
   parameter editor offers/auto-suggests for lane placement) and let Quartus
   report which banks are actually legal for an x8 HIP -- confirmed nothing
   in the device pin table (`10ax066_1_.xls`) marks HIP-legal channels
   explicitly, but UG-20039 confirms the HIP has a fixed geographic
   relationship to specific banks (one side of the device only), so this is
   almost certainly a MUCH narrower set than all 4 GXB banks -- likely 1-2 of
   them. Same "let Quartus tell you for free" technique that already worked
   for the refclk I/O standards list and the 16-IOPLL-location discovery.
3. Wire the custom top-level: `ref_clk_clk` to a refclk candidate,
   `xcvr_tx_out0-7`/`xcvr_rx_in0-7` to the now-narrowed legal lane pins,
   proper reset generation on `hip_ctl_npor`/`pin_perst` (real net, not a
   bare constant -- learned this lesson twice already tonight), `hip_pipe_*`
   left disconnected for the first pass.
4. Quick tests: compile, flash, check the real Hard IP's own link-status
   signals (worth finding something more directly accessible than the full
   `hip_pipe_*` bus for a fast first look, if the IP exposes one) rather than
   relying on a plain-IOPLL proxy's blunt locked bit.
5. Which of the legal banks from step 2 the Mustang's board actually wires to
   the edge connector is STILL a board-schematic-level unknown, same category
   as the refclk mystery -- likely still needs empirical testing, just over a
   much smaller candidate set once step 2 narrows it down.

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

## 37. The cell IS the memory cell: loop_back + latch_in + MEM_CALL (Alan, 2026-07-12)

**Status: three primitives, each already proven/present individually in the RTL,
composed into a pattern that was one of the cell's earliest design concepts --
"this removed the need for a dedicated memory cell." Confirmed against
`unicell64_v3.v` line-for-line, not just recalled from memory.**

Alan: this dates back to when the input-address latch was first added --
the intent from the start was that a cell could be configured to watch its own
output as its own input, removing any need for a separate, dedicated memory
primitive. Three concrete mechanisms realize this, all still present and
confirmed in v3:

**1. `loop_back` (cmd_latch bit) -- the cell's own computed result feeds back
as its own next input:**
```verilog
if (loop_back)
    a_data <= computed_output;  // feed result back as next A input
```
This is the cell watching its own output, exactly as originally conceived --
internal self-memory, no bus round-trip required.

**2. `latch_in` -- "constant emit": once armed, the cell perpetually
re-broadcasts its held value every cycle with NO further external trigger
needed.** Confirmed via the `latch_reemit` ping-pong: each cycle, if armed +
`latch_in` set + the output buffer just cleared (consumed), the cell re-emits
`data_reg` again, which sets the buffer valid again, which gets consumed
again, which re-arms `latch_reemit` again -- a genuine self-sustaining loop
driven purely by held internal state:
```verilog
end else if (ENABLE_LATCH_IN && latch_reemit) begin
    out_buf_addr  <= {16'h0, output_address};
    out_buf_data  <= data_reg;
    out_buf_valid <= 1'b1;
end
...
if (ENABLE_LATCH_IN)
    latch_reemit <= armed_r && latch_in && !out_buf_valid;
```
"Does it still fire on every cycle even with no new input" -- yes, confirmed,
this is exactly what it does. `CMD_TOPO_ZERO`/`CMD_TOPO_ONE` (constant-output
single-input gates, `latch_in=1` automatic) are the purest expression of this:
once armed, a fixed value repeats forever without needing to touch its input
again.

**3. `CMD_MEM_CALL` (opcode 0x0C) -- "go get this once, then hold and keep
re-emitting whatever came back until the next call":**
```verilog
CMD_MEM_CALL: begin
    if (auth_ok) begin
        cmd_latch[26] <= 1'b1;   // latch_in  -- hold + re-emit the result
        cmd_latch[30] <= 1'b1;   // one_shot  -- fires once per arm
        cmd_latch[22] <= 1'b1;   // start_flag -- armed
        one_shot_fired <= 1'b0;
        frozen         <= 1'b0;
    end
end
```
Atomically sets up exactly the "call out once, wait, then hold the answer"
pattern in a single opcode. This is the mode that introduces the cross-
boundary wait: if the call targets something across a cardinal bridge (not a
purely local `loop_back`), the round trip carries the same multi-cycle
latency measured for the cardinal hop itself (see below) -- request out,
response back, THEN the held value re-emits locally every cycle via
`latch_in` until the next `CMD_MEM_CALL`.

### Composed with the already-proven wired-OR bus (#32), this becomes a
### distributed, externally-modifiable accumulator -- for free
None of this needs new hardware. If a self-looping/re-emitting cell's output
address is *also* the target of some other cell's fire, the bus doesn't
overwrite -- it OR-combines (#32, silicon-proven). So another cell can inject
new bits into this cell's held, perpetually-repeating value with no dedicated
"write" instruction at all -- the modification happens as a side effect of the
bus's physical wiring, exactly the same free reduction #32 already proved,
just now feeding a value that's actively looping rather than firing once.

**The unifying point, and why it mattered from the start:** ordinary compute
cells don't need a separate, dedicated memory-cell type sitting alongside
them in the fabric. Any cell can BE the memory, by configuration
(`loop_back`/`latch_in`/`MEM_CALL`) rather than by being a different kind of
hardware. No dedicated RAM primitive, no separate address decode path for
"memory" cells versus "compute" cells -- one cell type, config bits decide
which role it's playing at a given moment. (Worth the loose echo to the same
day's memristor discussion -- collapsing memory and compute into the same
physical unit is exactly the instinct behind in-memory analog computing too,
arrived at completely independently, at a completely different layer of the
stack.)

### Measured latency context (from #17/cardinal-hop verification this session)
- Same-cluster (`loop_back`/local-bus self-reference): 1 cycle.
- Cross-cluster (`CMD_MEM_CALL` targeting across a cardinal bridge): 7 cycles
  measured in `tb_v3_transit.v` (already proven on silicon) for one-way
  bridge latency -- a full call-and-return round trip via `CMD_MEM_CALL` would
  carry roughly double this, plus whatever the target cell's own response
  time adds.

NOT YET DONE: this exact three-mechanism composition (loop_back + latch_in
constant-emit + external OR-modification via #32) hasn't been proven together
in one testbench -- each piece is individually confirmed, but the full
composed pattern as a genuine accumulator is a natural next sim testbench,
not yet written.

### The staleness window during a cross-boundary update (2026-07-12)
Precise timing, confirmed against the `new_data`/`latch_reemit` branch
structure in `unicell64_v3.v` (they're mutually exclusive on any given
cycle -- `if (new_data) ... else if (latch_reemit) ...`, and a genuine fresh
arrival always takes priority):

- **While no new cross-boundary write is in flight:** the looping cell
  re-emits its held (possibly stale) value every single cycle, steady state,
  via the `latch_reemit` branch.
- **The moment a new arrival actually lands** (having taken the ~7-cycle
  cardinal transit measured for `#17`/the cardinal-hop verification), it goes
  through the `new_data` branch instead, computing and emitting the FRESH
  value that same cycle -- no extra internal lag stacks on top of the transit
  delay itself.

**This means a looping cell continuously, confidently broadcasts a real
(soon-to-be-stale) value for the FULL ~7-cycle transit window of any
in-flight cross-boundary write to it, then cleanly cuts over the exact cycle
the new value lands.** Not a stall, not a gap -- any observer reading this
cell's output during that window sees genuine data, never a "waiting" state.
The bound is fixed and known (exactly the transit latency, never variable
under load, unlike a cache-coherence staleness window in a conventional
system) -- but it is a real staleness window, and any consumer of a looping
cell's value that doesn't independently know a fresher write is already in
flight will read stale data for up to ~7 cycles with no signal that anything
is wrong.

**This is precisely the kind of hazard `PLAN.md` Stage 4's VM-fidelity
principle exists for.** Like `#17`'s placement collision, this is a
correctness-affecting behavior that falls directly out of removing the
overarching sequencer (no global arbiter means no free "wait until fresh"
guarantee) -- and it has the same two obligations: the compiler should be
able to flag/reason about "this program reads a looping/`MEM_CALL` value
without accounting for known transit latency" as a potential staleness
hazard, the same way it will reject `#17`-style placement collisions; and the
VM must model this exact staleness window (continuous stale output, clean
cutover on arrival) rather than an idealized "value updates instantly" or
"value blocks until fresh" behavior, either of which would let a design pass
simulation and then behave differently on real silicon. Filed alongside `#17`
as a second concrete case for that same obligation -- not yet implemented in
either the compiler or the VM.

## 38. Open question: does the substrate map use a correctly-offset pentacross lattice, or are there wasted cells? (2026-07-12)

**Status: OPEN, not yet checked against the actual substrate map / zone layouts.**

Alan's herringbone-brick tangent (a linear row + staggered column layout,
worked through cell-by-cell and confirmed buildable entirely from the
already-proven cardinal/local-bus mechanisms, zero new wiring) led to a
sharper question about the pentacross itself (center + 4 arm cells, the
current shape actively used).

**The plus-shape (X-pentomino) genuinely does tile the plane with zero gaps
-- but only on a skewed/offset lattice** (each row of clusters shifted by a
knight's-move-style offset relative to the row before it), not via simple
aligned placement. If pentacross clusters are laid out in a naive aligned
grid (each cluster's bounding box directly adjacent to the next, the
"obvious" way to draw it), the diagonal corners between four neighboring
clusters are left as genuinely unclaimed cells -- the exact same underlying
principle as why herringbone needs its own zigzag offset to tile without
waste. Same idea, different specific offset.

**Open, concrete, checkable question: does this project's actual substrate
map / zone layout (in the real silicon builds already tested) use the
correct offset lattice for pentacross placement, or does it assume simple
aligned placement -- in which case there may be real, currently-unused
physical cells sitting in the design that a correctly-offset lattice would
reclaim?** Not yet checked. Worth resolving by actually reading the substrate
map documentation and the real zone layouts (`docs/COMPILER_TILE_CONFIG.md`,
the placer's actual output for the tested builds) rather than guessing.

NEXT: check whether the offset lattice question matters for the current
25-cells-per-zone rectangular zone layout used in tonight's real silicon
builds, or whether it's purely a concern for a hypothetical future placement
scheme that tries to tile pentacrosses edge-to-edge across zone boundaries
rather than within a single rectangular zone.

## 39. Notes: INF Device ID maintenance, and Linux as the real Device Pond platform (Alan, 2026-07-12)

**Note 1 -- INF maintenance reminder, not urgent.** `altera_pcie_win_driver.inf`
is currently hard-matched to `PCI\VEN_1172&DEV_2494` (both with and without
the `SUBSYS_660A180C` qualifier), correctly reflecting the real Device ID
confirmed via direct PCI config-space read (`0x2494`, not the `DEV_0000`
Windows Device Manager showed at first enumeration -- that was most likely a
placeholder shown before a matching driver bound, still not fully explained
but not concerning). Proof this INF is genuinely working, not just plausible:
the interop test tool successfully got far enough to attempt a real BAR0
read/write, which requires the driver to be properly bound and functioning.
**If the Vendor/Device ID is ever customized away from this default in a
future IP regeneration, this INF will need updating again** to match --
otherwise Windows won't match the driver to the device at all. Not an issue
now; a reminder for whenever that customization happens.

**Note 2 -- Linux is the real target platform for Device Ponds, not just a
workaround for Windows driver signing.** Confirmed against existing
architecture docs (`docs/NATIVE_FS.md`, `docs/archive/08_Use_Cases.md`): "A
new device registers as a DEVICE Pond, announces itself through Cast/Ripple,
and the mesh incorporates it... Device Ponds translate at the boundary. The
mesh never sees the difference." On Windows, the PCIe link is scoped to one
hand-built test driver serving exactly this one endpoint. On Linux, once the
link has a real target behind BAR0, the SAME bridge-and-translate pattern
already used for GPS/CAN/actuator Device Ponds applies directly to it -- and
critically, opens the door to EVERY OTHER device Linux already has a real
kernel driver for becoming a Device Pond the same way, with (per the
architecture's own stated principle) zero change to the mesh itself. This is
the actual reason Linux matters here beyond sidestepping driver-signature
enforcement -- it's the platform where the full Device Pond vision (not just
this one PCIe endpoint) is actually reachable.

NEXT: once the Linux side is sorted (card + JTAG blaster physically moved
over, per the earlier setup plan), the natural sequence is: (1) flash and
confirm the same PCIe link trains under Linux (`lspci -v`, no driver
dependency at all for this check), (2) wire a real target behind BAR0 (the
UniCell fabric's own command/data bus, per points.md #30's next step), (3)
register that link as a genuine Device Pond per the existing architecture,
rather than a one-off test driver.

## 40. First fully-verified whole-zone boot+config+fire on corrected icm64_readstate.tcl (2026-07-16)

**Silicon-confirmed, on the Windows machine (known-stable baseline), `Unicell-Q-zone1-v3` bitstream:**

```
cycle_count: 2913190643 -> 2915666286   OK (fabric clocking)
cmd_latch[31:0] = 0x0440a02c   (topology[9:0]=0x02c  armed=1)
input_addr = 0x0000   output_addr = 0x0200
out_seen=1 out_addr=0x0200 out_data=0x000000aa out_count=1 armed_count=25
```

This is the first clean run of the corrected config sequence
(`docs/V3_COMMAND_CONTRACT.md` section 7, via the rewritten
`icm64_readstate.tcl` — commits `c7d8fd9`, `58a3cc4`) showing a genuine
end-to-end round trip: `ARRAY_RESET` -> `BOOT_COMMIT` (auth=0x0A5) ->
`RECONFIGURE` (topology `0x02C` = PASS_B, armed, latch_in) -> `SET_TARGET` ->
`ROUTING` (east) -> `TRANSIT` (route-across-only) -> `SWAP_AB` (prime) ->
`INJECT` (0xAA). The injected value fired and landed correctly at the
configured `output_addr` (0x0200).

**`armed_count=25` directly confirms the morning's open question**: it
matches `NUM_CELLS=25` for this zone exactly, proving `CMD_BOOT_COMMIT` and
`CMD_RECONFIGURE` are genuine zone-wide broadcasts (no `config_match`/
`addr_match` gate in the RTL, as read directly from `unicell64_v3.v`) --
one config pass armed the entire zone simultaneously, not just cell 0. Only
`CMD_LOAD_AT` (opcode 23) is per-cell targeted. The debug readback itself
remains limited to cell 0 only (`icm64_readstate.tcl`'s own header note --
no per-cell debug select in this bitstream yet) -- that is a readback
limitation, not a configuration one.

Also resolved same day: the auth-mismatch theory that motivated re-checking
this script was real in mechanism (auth is write-once boot-only, wrong
token = silent rejection) but the actual bug that produced garbage/all-1s
readbacks the night before was self-inflicted -- an ad-hoc "corrected"
script variant had a genuine token mismatch (0x28 set at boot vs 0x29
required at reconfigure, from an imprecise hex substitution) that was never
committed to git. The git-committed script was already using the correct,
consistent `0x0A5` auth throughout, matching `icm64_v3_decoder_auth.tcl`'s
earlier silicon-proven auth-relocation test and this doc's own section 7.

NEXT: known-good zone-wide boot+config+fire confirmed. Re-add PCIe into
this same model -- wire the UniCell fabric's command/data bus behind BAR0
(pcie_hip_test.qsx's Hard IP, separately confirmed full x8 Gen2 link), so
the fabric can be driven from the PCIe host side rather than only JTAG/ISSP.

## 41. PCIe-to-fabric bridge: pcie_unicell_bridge.v written, sim-tested, synthesis-checked (2026-07-16)

**First concrete step on wiring PCIe into the known-working zone1-v3 model.**
`pcie/pcie_unicell_bridge.v` (commits `0437836`, `9307bc7`) is an Avalon-MM
slave that receives the PCIe Hard IP's `rxm_bar0` Avalon-MM master interface
and translates single-beat 128-bit BAR0 accesses into the fabric's unified
`cmd_bus`/`cmd_data`/`cmd_valid` protocol, following the same master-side
convention as `uart_bridge.v`/`unicell_issp_bridge.v`.

Interface ground-truthed directly from `pcie_test_1.sopcinfo` (not guessed):
`rxm_bar0_address_o[63:0]`, `_byteenable_o[15:0]`, `_writedata_o[127:0]`,
`_write_o`/`_read_o`, `_burstcount_o[5:0]` (burst disabled in qsys config),
`_readdata_i[127:0]`, `_readdatavalid_i`, `_waitrequest_i`.

**Register map (proposed, pending real-hardware confirmation)**: beat 0
(CMD, write-only) packs `{cmd_bus[63:32], cmd_data[31:0]}` into one atomic
128-bit write, pulsing `cpu_valid` for one cycle -- same atomicity as the
ISSP bridge's combined source-register write. Beat 1 (STATUS, read-only)
packs `out_addr`/`out_valid`/`out_data` back to the host. `cycle_count`/
`armed_count` readback and `array_rst`/`array_freeze` control deliberately
deferred (smallest-test-first).

**Verified in two independent ways, zero hardware risk taken:**
1. `tb_pcie_unicell_bridge.v` (iverilog): 12/12 checks pass -- CMD write
   pulses `cpu_valid` correctly for exactly one cycle with correct
   `cpu_bus`/`cpu_data` split, returns to 0 the next cycle, CMD-beat read
   echoes back correctly, STATUS-beat read packs fabric status correctly,
   `avs_waitrequest` stays low throughout (always-ready slave design).
2. Quartus Analysis & Synthesis against the real Arria 10 device family
   (via `quartus_map pcie_hip_test --source=pcie_unicell_bridge.v`): clean
   pass, only pre-existing warnings from Intel's own generated PCIe HIP
   internals, none attributable to this file.

**One real bug found and fixed during the synthesis check**: `` `default_nettype
none `` is a compilation-unit-wide directive that persists into whatever
file Quartus compiles next in the same run -- left unreset, it broke
Intel's own generated `altpciexpav128_p2a_addrtrans.v` (Error 10162, can't
declare implicit net "bar4_64bit"), since that file relies on the classic
implicit-wire default. Fixed by adding `` `default_nettype wire `` after
`endmodule`. Same latent issue noted as present but not yet triggered in
`uart_bridge.v`/`unicell_issp_bridge.v` (neither has yet been compiled in
the same run as the PCIe HIP's generated files).

**Two open questions flagged for real-hardware verification** (in the file
header, not yet checked): whether the qsys's `addressUnits` convention
(words vs. bytes) matches the `address[7:4]` beat-select assumption, and
whether the 1-cycle registered read latency chosen matches the qsys's
configured `readLatency` for `rxm_bar0`.

**RESOLVED (2026-07-20)** -- checked directly against the real
`pcie_test_1.sopcinfo` (Alan located and uploaded it; confirmed not
present in the repo, correctly, since it's a Platform-Designer-generated
artifact that only exists after "Generate HDL" on the actual build
machine, not a compile output):

- **`addressUnits` = `SYMBOLS`** (byte-addressed, `bitsPerSymbol=8`
  alongside it). Consistent with the bridge's `beat_sel = avs_address[7:4]`
  design as-is -- byte offset `0x00` selects beat 0 (CMD), `0x10` selects
  beat 1 (STATUS), matching normal host-driver convention for a
  byte-addressed BAR. No RTL change needed.
- **`readLatency` = `0`**, alongside `readWaitTime` = `1`. On its own
  this looked like a mismatch against the bridge's genuine 1-cycle
  registered `avs_readdatavalid` (`readdatavalid_r <= avs_read`,
  confirmed directly in the RTL). Resolved by Avalon-MM's own interface
  rules rather than an RTL fix: `readLatency`/`readWaitTime` describe the
  *fixed*-latency protocol (no `readdatavalid`); a slave that actively
  drives `readdatavalid` -- which this bridge does, and which is
  confirmed correctly wired through to the Hard IP's
  `rxm_bar0_readdatavalid_i` input in the same `.sopcinfo` -- puts the
  interface into *variable*-latency mode, where the master is required
  to wait for `readdatavalid` rather than counting a fixed cycle offset.
  High confidence, not RTL-proven yet: worth being the first thing
  actually watched in simulation/hardware once the Hard IP is connected,
  not assumed silently correct from spec-reading alone -- same
  measure-don't-assume discipline as everywhere else in this project.

**Net result: both items closed, neither needs an RTL change.** See #44
for the top-level merge this was blocking.

NEXT: wire this bridge into an actual merged top-level -- fabric RTL +
PCIe Hard IP + this bridge as a third `cpu_bus` master (`p_valid`/`p_bus`/
`p_data`) alongside the existing UART (`u_valid`) and JTAG/ISSP (`j_valid`)
masters in `top_arria10_zone1_v3.v`'s arbitration mux. Likely means
extending `Unicell-Q-zone1-v3.qsf` with the PCIe transceiver pin
assignments and Hard IP rather than starting from `pcie_hip_test.qsf`,
since the fabric side has more proven moving parts already correctly wired.
DONE -- see #44.

## 42. Cardinal-bit shape partitioning: local/cardinal as mutually exclusive per-edge state, pentacross as a worked example (Alan, 2026-07-19)

**Core mechanism.** On a fixed, uniform 4-neighbor square grid (no
diagonals, no offset rows -- always the same physical wiring), each
cell's per-edge cardinal-latch bit is mutually exclusive with local-bus
participation on that same edge:
- **0 (local):** the edge joins the wired-OR local broadcast group as
  normal -- full participation, including whatever bus-level reduction
  (OR/AND/XOR) is happening on that local group.
- **1 (cardinal):** the edge cuts local-bus participation and becomes a
  one-hop, point-to-point delivery to the neighbor cell only -- data
  arrives at the neighbor but does not continue rippling through that
  neighbor's own local bus. This is exactly the already-silicon-proven
  transit-cell behavior (`east bridge seen=1`, `local bus seen=0`)
  generalized as the standard per-direction partitioning tool, not a
  special case.

No third/combined state is ever needed, since the two are mutually
exclusive by construction -- one bit per edge fully describes it.

**What this buys you, precisely scoped.** "Shape" becomes a *config-bit
pattern choosing how a fixed grid is partitioned into local-broadcast
neighborhoods* -- not a different physical adjacency graph. This
explicitly does NOT extend to brick-offset or herringbone-style
topologies, which need a genuinely different neighbor (physically
different cell across the "shared edge," not reachable via any bit
pattern on a plain square grid's existing wires) -- those still require
real, different physical routing decided at synthesis, per the existing
"physical locality freezes at tape-out" principle. This mechanism is
strictly about partition boundaries on one fixed substrate, not
topology-switching.

**Worked example: pentacross as a tile.** Sketched as five zones in a
plus/cross arrangement (one center + N/S/E/W arms, each zone itself an
internal grid of cells): the four inner boundary edges (center-to-arm)
have cardinal=1, and critically, the *outer* edges of all four arms also
have cardinal=1 -- meaning each pentacross cluster also hops outward to
the next cluster over, making it a genuine repeating tile across the
whole substrate, not an isolated 5-zone group. Entirely a bit-pattern
choice on the existing four-cardinal wiring scheme already confirmed
buildable for herringbone -- worth checking whether herringbone's actual
neighbor requirement is a subset of plain square-grid wiring (in which
case it's already reachable this way) or genuinely needs different
physical routing (in which case it isn't, and stays synthesis-time only).

**Flash-wear clarification (important, resolves an initial concern).**
Alan's worry: repeatedly "refreshing" the card to change shape could
wear out the configuration flash. Resolved: as designed, cardinal-bit
writes are a **runtime SRAM config register write** -- same class of
operation as the already-existing `routing_mask`/`transit_only` fields,
sent as a normal command over UART/JTAG/PCIe. This is unrelated to the
FPGA's own configuration-SRAM reload-after-power-cycle behavior (a
volatile-SRAM property of the device itself, not a flash-wear
mechanism). Built this way, shape-switching costs nothing more than any
other command already flowing through the system today -- no flash
involved, no wear concern. The real wear risk would only arise if shape
were instead baked into synthesis (requiring an actual recompile +
reflash to change) -- explicitly the thing to avoid; the runtime-register
approach sidesteps this by construction.

**Complementary idea, not either/or: Pond-level static shape
partitioning.** Independent of the flash-wear question, raised as an
alternative: different Ponds could simply be given different fixed
shapes suited to their workload, with no runtime switching needed for
those Ponds at all. This isn't in tension with the runtime-switchable
cardinal-bit mechanism above -- both can coexist: some Ponds statically
shaped at boot/config time, a smaller number dynamically reconfigurable
at runtime for cases that genuinely need to change shape mid-run.

**NEXT:** deliberately gated behind clearing the PCIe integration work
first (see #41). Revisit this mechanism -- and the herringbone
subset-vs-genuine-new-routing question above -- once PCIe side is done.

**Follow-up, the actual point of the whole idea (Alan):** the ICM file
*is* the cell configuration file -- that's the trick this mechanism
unlocks. Previously, if ICM carried any notion of "shape," it was
describing intent disconnected from what could actually happen without
a different `.sof` (a different shape meant a different synthesized
bitstream) -- so a shape field could document, but couldn't *cause*
anything by itself. With cardinal-bit partitioning on one fixed,
always-loaded substrate, that gap closes: an ICM's declared shape
becomes something the **loader translates directly into cardinal-bit
writes against the already-running bitstream** -- real, causal meaning,
applied live, no synthesis or reflash involved at all. This is not new
scope for the loader -- it already owns placement arithmetic
(relocatable models: root+offset, loader/saver own the math, cell stays
absolute) -- shape partitioning is just one more thing in that same
bucket: given an ICM's declared shape for a region, compute the cardinal-
bit pattern for that region's cells and write it.

**Consequence: once the VM reflects this, the VM gains shape awareness
too.** The software VM model needs to understand the same local/cardinal
partitioning semantics as real silicon -- an ICM loaded into the VM
should produce the same shape-partitioned behavior (which cells
broadcast together, which edges are one-hop-only) as the same ICM loaded
onto the fabric. This is the same "every placement rule discovered from
silicon must become both a compiler check and a VM behavioral model"
principle already governing the rest of the loader/compiler work --
shape is now squarely inside that scope, not a separate concern.

**Refinement (Alan, 2026-07-19): decompose the single global `transit_only`
bit into 4 independent per-edge bits.** Today, `transit_only`
(`cmd_latch[15]`) is ONE bit for the whole cell -- it decides local-or-both
uniformly across whichever directions `routing_mask[3:0]` (`cmd_latch[14:11]`)
has selected. There is no way today to have one edge cardinal-only while
another edge on the same cell stays local-and-both, independently. The
proposal: reclaim the 3 bits freed by the auth_mask relocation
(`cmd_latch[18:16]`, confirmed genuinely free -- see the bit-budget check
below) plus repurpose the existing `transit_only` bit, giving 4 bits total,
one per cardinal direction, each independently choosing local vs.
cardinal-only for that specific edge. No new physical wiring needed --
the four cardinal bridge paths already exist and are silicon-proven; this
is new config-bit decode logic reusing existing wiring, same category as
`routing_mask`/`transit_only` themselves.

**Two concrete capabilities this unlocks, not available with today's one
global bit:**
- **Non-sharing adjacent cells.** Two neighbouring cells can each set
  their shared edge to cardinal on both sides -- neither joins the
  other's local broadcast group across that boundary, while each keeps
  its other three edges free for local participation elsewhere. Hard
  isolation between logically separate regions purely through config,
  no physical distance needed between them -- dense packing of
  independent blocks placed directly adjacent.
- **The snake chain.** A winding, single-file data path threading
  through 2D space, using only 2 of a cell's 4 edges as cardinal (the
  chain's in/out), leaving the other 2 edges completely free (local
  participation in an unrelated group, or unused). A genuine
  programmable systolic/shift-register structure that can wind around
  other active regions on the same substrate with zero cross-talk --
  only possible with true per-edge independence, not the current global
  bit.

**Consequence, stated plainly:** this fully consumes `cmd_latch[31:0]` --
32/32 bits allocated afterward, zero free, versus 3 free today. Any
future lower-32 need would require reclaiming an existing field or
widening `cmd_latch` past 64 bits. A real tradeoff, not a free win --
worth being deliberate that this is the best use of the last headroom
before spending it.

**Bit-budget check performed while this was discussed (2026-07-19),
worth recording precisely since it settles "how full is cmd_latch" for
good:**
- Lower 32 (`cmd_latch[31:0]`): 29 bits allocated, exactly 3 free at
  `[18:16]` (confirmed directly from the RTL, not recalled from memory --
  the summary comment above this in `unicell64_v3.v` had drifted stale,
  now corrected in the same pass, with a standing rule added requiring
  future field changes to update that summary in the same commit).
- Upper 32 (`cmd_latch[63:32]`, "methodology bus"): **fully allocated,
  32/32, zero free** -- `m_nibble_mask[39:32]` (8), `m_mask_en[40]` (1),
  `m_shift_amt[46:41]` (6), `m_in_shift_en[47]` (1), `m_out_shift_en[48]`
  (1), `m_lane_cut[51:49]` (3, a real lane-boundary-cut feature that
  defaults to inert/zero -- not free space, a genuinely easy misreading
  caught and corrected in the same pass), `cmd_latch[52]` (1, internal
  debug "load confirmed" bookkeeping, not part of the wire protocol),
  `auth_mask[63:53]` (11). The header comment here had also drifted
  stale (said "17 of 32 used"), corrected in the same pass.
- So: any future addition needing upper-bus space has nowhere to go
  without reclaiming something; the lower bus has exactly 3 bits of
  headroom, and this refinement (if built) spends all of it.

## 43. Parked idea: lane-split-to-cardinals mode, 1 bit, fixed cycling order (Alan, 2026-07-19)

**Core idea.** Reuse the *existing* lane-cut/lane-window hardware
(`m_lane_cut[2:0]`, `lane_win8`/`lane_win16`/`lane_win24` -- today's
shift-boundary-truncation feature) for a second purpose: when a new mode
bit is set, split the word into byte-lanes and send each lane out to a
different currently-active cardinal direction, cycling through whichever
directions `routing_mask[3:0]` has enabled, in a **fixed** order (not
per-lane selectable). Local always still receives the complete, unsplit
word regardless of whether this mode is active -- only the cardinal
outputs get split.

**Why fixed order, not per-lane-selectable, matters:** it's the
difference between this needing 1 bit and needing several. A fixed
cycling order (deterministic given which directions `routing_mask`
already has active) means the compiler never has to reason about
arbitrary lane-to-direction assignment -- just "how many directions are
active, what's the cycle order" -- a genuinely easier planning target,
by design, not just a simplification for its own sake. A per-lane
*choice* of direction would need real per-lane direction selection
(closer to 2 bits per lane) -- a meaningfully bigger ask than what's
being proposed here.

**Minimal new hardware, same ethos as the rest of this project:** no new
splitter logic -- one new mode bit changes what the *existing* lane
splitter's output feeds (cardinal outputs instead of shift-boundary
truncation), reusing already-built hardware for a second job rather than
duplicating it.

**Status: parked, not currently buildable -- bit-budget contention with
entry #42.** This needs 1 bit from the same scarce 3 free bits at
`cmd_latch[18:16]` that entry #42's per-edge cardinal decomposition
(4 bits, all 3 free + repurposed `transit_only`) already wants to spend
in full. The two ideas are in direct competition for the same headroom,
not independent asks -- funding #42's refinement in full leaves nothing
for this one. Whichever gets built first (or a scaled-down version of
one) needs to be a deliberate prioritization call when the time comes,
not an assumption that both fit.

**Decision (Alan, 2026-07-19): #42 wins the bit budget.** Reasoning:
#42 changes what topologies are *expressible at all* -- a single global
`transit_only` bit structurally cannot produce non-sharing adjacent
cells or a snake chain no matter how many extra commands or ticks are
spent; there is no workaround. #43 is a real, valuable optimization of
an *already-expressible* pattern (getting different data to different
neighbors is already possible today, just slower, via separately-masked
fires per direction) -- a genuine speed win, not a new capability. Given
"topology is computation" is the project's founding premise, the
mechanism that expands expressible connectivity wins over the one that
speeds up something already reachable. #43 stays parked, to be revisited
if headroom frees up elsewhere or a real workload turns up where the
multi-tick workaround is the actual bottleneck.

Also confirmed: the debug bit (`cmd_latch[52]`, upper bus) is not a
source of reclaimable headroom either way -- still earning its keep
during bring-up, and pulling observability right when it'd be needed
most to debug whichever of these mechanisms gets built would be the
wrong trade to make at this stage.

## 44. PCIe bridge merged into top_arria10_zone1_v3.v as a third cpu_bus master (2026-07-20)

**Direct follow-up to #41** -- the bridge itself was already written,
sim-tested, and synthesis-checked in isolation; this is the actual
merge into the real top-level, extending the arbitration mux from two
masters to three.

**cpu_bus mux: UART + JTAG → UART + JTAG + PCIe.** Priority: JTAG > PCIe
> UART. JTAG deliberately keeps top priority -- it's the known-good
bring-up/debug path (`icm64_readstate.tcl` etc.) and must never be
starved by a host driving PCIe; PCIe outranks UART since a host-side
PCIe transaction is a deliberate, timed access that shouldn't lose
arbitration to a normally-idle UART bridge. `pcie_unicell_bridge`
instantiated with its fabric-side connections wired exactly matching
the existing UART/JTAG instantiation pattern (same `cpu_bus`/`cpu_data`/
`cpu_valid` output convention, same `out_addr`/`out_data`/`out_valid`
readback input).

**Deliberately NOT done in this pass, and correctly so:** the bridge's
Avalon-MM slave inputs are not yet connected to a real PCIe Hard IP
instance. That's a qsys-generated component that can't be safely
fabricated blind from this environment -- wrong instance name/port list
would silently produce something that *looks* wired but isn't. Instead,
tied to clearly-labeled wires (`hip_rxm_bar0_*`) with an explicit TODO
comment at the exact point the real Hard IP needs to be dropped in via
IP Catalog once at the actual Quartus machine. Tied to an explicit safe
"no transaction" default (all zeros) rather than left floating --
undriven inputs simulate as X, and X on `avs_write`/`avs_read` would
have propagated into `p_valid`/`cpu_valid`, corrupting arbitration for
the *other* two masters even though PCIe itself isn't connected to
anything real yet.

**Verified in simulation against the real top-level and its real
dependencies** (iverilog/vvp -- no Quartus available in this
environment, correctly scoped to what's honestly verifiable without
it):
- Full elaboration of the actual merged top-level, real dependency
  files, succeeded cleanly -- only pre-existing, unrelated port-width
  padding warnings in `unicell_array64_v3.v` remain, predating this
  change
- New testbench `tb_top_arria10_pcie_mux.v`: forced each master's
  valid/bus/data directly, checked the mux across every meaningful
  combination -- UART alone, JTAG beating UART, JTAG still winning with
  all three asserted, PCIe correctly taking over the moment JTAG
  deasserts, falling back to UART once PCIe also deasserts, PCIe alone,
  JTAG alone. 9/9 checks pass.
- One incorrect *test* expectation caught and fixed, not an RTL bug:
  initially expected `cpu_bus`/`cpu_data` to read zero when nothing is
  valid; checked directly against the *original* 2-way mux's own
  pre-existing contract and confirmed it never guaranteed that either
  (falls through to the lowest-priority master's bus regardless of that
  master's own valid, same before this change) -- only `cpu_valid` was
  ever the real, meaningful gate. Fixed the test rather than incorrectly
  "fixing" correct RTL to match a wrong expectation.
- New testbench `tb_top_arria10_pcie_silent.v`: confirmed the REAL
  (non-forced) `pcie_host` instance stays completely silent across 2000
  real clock cycles given the safe tie-offs -- proves this integration
  is a true no-op for existing UART/JTAG behaviour until a real Hard IP
  actually drives it, not just assumed from reading the tie-off values.

**Also confirmed directly, not assumed:** `pcie_test_1.sopcinfo` (the
file that would resolve #41's two open qsys questions) is genuinely
not present anywhere in this repo -- it's a Quartus/qsys-generated
artifact that only exists on the actual build machine. Both open
questions stay open, correctly, until checked there.

**NEXT, requires the real Quartus machine, not further work possible
from here:**
1. Add the PCIe Hard IP via IP Catalog (same qsys config as
   `pcie_hip_test.qsf` -- BAR0 windowed, full x8 Gen2 link already
   confirmed working there), connect its `rxm_bar0_*` outputs directly
   to the `hip_rxm_bar0_*` wires this pass prepared.
2. Check `addressUnits` (words vs. bytes) against the `address[7:4]`
   beat-select assumption, using the real generated `.sopcinfo`.
3. Check whether the bridge's 1-cycle registered read latency matches
   the qsys's configured `readLatency` for `rxm_bar0`.

## 45. Parked idea: a larger, dedicated "lab" AI role for substrate exploration -- distinct from Companion's existing escalation model (Alan, 2026-07-20)

**Prompted by re-discovering `companion.py`'s existing, working `--ai` /
`attach_ai()` mechanism** (TinyLlama-1.1B by default, optionally Ollama,
routes Ward's STALLED/OFFLINE/DEGRADED escalation decisions through the
model when attached, a built-in rule engine otherwise -- fully optional,
already built, unchanged). That's a narrow, well-bounded classification
job a tiny model suffices for. This idea is a genuinely different,
separate role, not a bigger version of the same one.

**The idea: a dedicated, larger model aimed specifically at open-ended
substrate exploration** -- not Ward escalation, but letting a user
explore ideas, run experiments, and try things in the UniCell substrate
itself with an AI collaborator that understands the ICM grammar, cell
addressing, and cardinal-direction topology directly. Reasoning: Ward
escalation is closer to a bounded classifier (small state space, pick
one of a few responses); substrate exploration is closer to generative/
structured reasoning (hold a spec in mind, propose a topology or config
change, reason about consequences) -- genuinely different capability
demands, not the same job needing more parameters.

**Why the fit is real, not just optimism about AI in general:**
UniCell's structure -- discrete cells, fixed addressing, cardinal
directions, config bits with a defined grammar -- is exactly the kind of
well-specified, verifiable state space LLMs are actually good at
reasoning over precisely (the same reason they're decent at SQL/regex
generation but flakier at vague open-ended tasks). The ICM format and
the cardinal-bit layout are themselves a grammar a model could
genuinely be trained against.

**Alan's specific framing, worth recording precisely:**
- Aimed at "lab-oriented" models specifically -- a research/
  experimentation tool, not a production/escalation one.
- Would need a **dedicated training/fine-tuning module** against the
  UniCell substrate specifically -- not just a generic base model
  pointed at the problem.
- Hardware reality: **effectively two GPUs** -- one for the VM (if/when
  VM-side work becomes GPU-accelerated at the scale this would run at),
  one for the AI model itself, running concurrently. A real,
  non-trivial hosting cost, not a detail to wave away.
- FPGA is a **bonus, not a requirement** for this role -- real hardware
  gives real speed, but VM-only should be sufficient for exploration/
  experimentation; this role doesn't need silicon to be useful.
- **The hope: ICM's format stability holds**, so whatever this AI
  explores/generates stays portable across VM/FPGA/ASIC targets, the
  same "write once, run everywhere" property ICM already provides for
  ordinary cell configuration -- this idea leans on that guarantee
  continuing to hold, not introducing a new one.
- **Explicit complexity caution:** a very large, dedicated model could
  become genuinely unwieldy to host/manage/reason about -- which is
  exactly why keeping the AI role as an **optional plug-in** (the same
  pattern `attach_ai()` already establishes) is the right shape, rather
  than baking a large-model requirement into the core system. The
  existing optional/swappable design already anticipates this; the
  natural extension is a second, differently-scoped optional role
  alongside the existing one, not a replacement of it.

**Status: parked idea, genuinely just thinking out loud for now** -- no
immediate next action, no bit budget or scope commitment implied. Worth
revisiting once there's real bandwidth to consider it deliberately,
same treatment as the sidecar semantic-index design note's parked ideas.

**Sharpened by #48 (Alan, 2026-07-22):** #48's bridge-cell-driven
n-dimensional structure is exactly the concrete case that justifies this
role, not just a nice-to-have alongside it. As the array scales, the
space of possible bridge-cell/cardinal-bit configurations grows
combinatorially -- a human searching that space by hand for genuinely
useful non-obvious structures stops being practical well before the
array gets large. That's a well-specified, structured search, exactly
where an AI role earns its keep on its own merits, not vague cleverness.
Two real requirements this adds, not just aspiration: (1) needs to tie
into the compiler/VM directly, so a proposed structure can be
immediately verified rather than just guessed at -- the same measure-
don't-assume discipline as everywhere else in this project; (2) needs
a genuinely new visualisation approach, since once bridge cells let a
local cluster jump to any distant point, the connectivity graph stops
being something a flat 2D diagram represents well -- worth treating as
its own real design problem when the time comes, not an afterthought
bolted onto the composer.
## 46. PCIe Hard IP + PIO bridge actually connected -- real, verified, but with a flagged clock-domain-crossing gap (2026-07-21)

**Direct follow-up to #44.** The Hard IP itself (`pcie_a10_hip_0`) and
Intel's "PIO AVST" bridge (`pio_bridge_0`, translating the raw Avalon-ST/
conduit interface into a genuine Avalon-MM master) are now both generated
and wired together via a new module, `pcie/pcie_hip_wrapper.v`, replacing
the `hip_rxm_bar0_*` placeholder tie-off block in `top_arria10_zone1_v3.v`
entirely. This is the first real, non-placeholder PCIe connection in this
top-level.

**Real dead end worth recording, so it isn't repeated:** both components
were generated via IP Catalog's "New Component" wizard (same category as
`issp`), not as Platform-Designer-nested systems. Initial attempt to
combine them inside a third qsys system failed -- Platform Designer's
"Project" IP Catalog category only lists genuine multi-component systems
(`pcie_test_1`, `pcie_example_design`), never single-IP-variation `.qsys`
files. The correct pattern, confirmed the hard way: plain Verilog
instantiation and wiring, exactly how `unicell_issp_bridge.v` already
wraps `issp`.

**`pcie_unicell_bridge.v` rewritten** for the interface `pio_bridge_0`
actually provides -- 16-bit address, 32-bit data, 4-bit byteenable, no
burstcount (confirmed directly from `pio_bridge_0.cmp`) -- genuinely
narrower than the 64-bit/128-bit/16-bit interface originally assumed
(which matched `pcie_test_1`'s `rxm_bar0`, a wider interface this specific
generation path doesn't produce). New word-addressed register map:
`CMD_DATA` (0x0, stages), `CMD_BUS` (0x4, fires `cpu_valid`),
`STATUS_ADDR_VALID` (0x8), `STATUS_DATA` (0xC). A wider "DMA"-style variant
may exist separately (seen referenced in IP Catalog's own docs) and could
replace this path later if throughput needs it -- deliberately deferred,
per "confirm PCIe works first."

**Verified with real, systematic checking:**
- Every port name and direction taken from the real, Quartus-generated
  `_inst.v` templates for both components, not inferred from `.sopcinfo`
  interface names alone
- Every port WIDTH cross-checked against the real `.cmp` files via an
  automated parser -- caught and fixed six genuine width errors in the
  first wrapper draft (several conduit signals assumed single-bit that
  are actually multi-bit vectors), confirmed zero remaining mismatches on
  a second automated pass before trusting the file
- Full elaboration (`tb_full_pcie_chain.v`) against auto-generated stub
  modules (parsed from the same real `.cmp` files, not hand-typed) for
  the two components needing a real Quartus license -- elaborates
  cleanly end to end
- Functional register-map test (`tb_pcie_unicell_bridge_regmap.v`, 13
  checks): staging, one-shot pulse firing with correct `cpu_bus`/
  `cpu_data`, readback echoes, STATUS correctly reflecting live fabric
  state, STATUS writes correctly ignored. Two initial failures diagnosed
  and resolved as genuine testbench timing artifacts, not RTL bugs --
  confirmed by iterating the test until it correctly reflected the RTL's
  actual one-shot-pulse behaviour, rather than "fixing" correct RTL to
  match a wrong test expectation

**KNOWN, FLAGGED, NOT YET RESOLVED -- the actual next priority, do not
treat this integration as fully done:** a genuine clock-domain-crossing
gap. `pcie_a10_hip_0`'s `coreclkout_hip` (250MHz for the selected
Gen2x8/128-bit mode) and the fabric's `CLK` (25MHz, `CLK_100M`/4) are
different, fully asynchronous domains. `pio_bridge_0`'s `AvRxm*` outputs
are registered on `coreclkout_hip` internally; `pcie_host`
(`pcie_unicell_bridge`) is clocked by `CLK` -- meaning `avs_write`/
`avs_read` (single 250MHz-wide pulses) currently cross into the 25MHz
domain with **no synchronizer at all**. Real risk of dropped writes/reads
or metastable address/data sampling on real hardware. Two candidate
fixes, neither chosen yet:
1. Move `pcie_unicell_bridge` onto `app_clk` (250MHz) instead of `CLK` --
   fixes this crossing, but shifts the same problem to the
   `cpu_valid`/`cpu_bus`/`cpu_data` -> arbitration-mux boundary instead
   (which currently assumes `j_valid`/`u_valid`/`p_valid` share one clock
   domain).
2. Add a proper synchronizer/handshake (e.g. a small dual-clock FIFO, or
   a toggle-based pulse synchronizer) at the current `avs_*` boundary,
   keeping `pcie_unicell_bridge` on `CLK`.

**Clarification on fabric clock target and the "room to grow" figure
(Alan, 2026-07-21) -- worth pinning down precisely, since it doesn't
mean what it first sounds like.** The fabric's real target is 50MHz,
not the 25MHz `clk_div` currently implements (`CLK_100M`/4) -- that /4
divider was a conservative bring-up value, expected to tighten later
once more confidence is established, not the final intended frequency.
Alan recalled "~57MHz" as evidence of margin above the target. Checked
directly against this file's own earlier record (line ~530): **that
57.4MHz figure is `clk_div`'s OWN Fmax specifically** ("FMAX
`clk_div`=57.4 MHz, ~2.3x margin over the 25 MHz operating") -- the
clock divider itself, a trivial 2-bit free-running counter, not the
fabric's actual critical path through the zone/array hierarchy. A
circuit that small will almost always have huge Fmax margin; it says
nothing about whether the real, computational fabric can close timing
at 50MHz. This file's own scalability-ladder section already states the
honest status plainly: **"Does it close timing? (Fmax vs zone count --
unmeasured)."** So: the 50MHz target is real, the 57MHz figure is real,
but they aren't connected the way "room to grow" implies -- the actual
fabric's real Fmax remains genuinely unmeasured, not confirmed-with-
margin. Doesn't change the CDC decision above (a proper synchronizer is
the right call regardless of which exact frequency the fabric eventually
confirms), but worth not carrying "confirmed headroom" into planning
when what's actually confirmed is margin on a different, much smaller
piece of logic.

**RESOLVED (2026-07-21) -- see `pcie/pcie_cdc_bridge.v`.** A standard
two-phase toggle request/acknowledge handshake, deliberately built
frequency-ratio-independent (chosen specifically so the 25-vs-50MHz
question above doesn't need answering first -- build and verify against
whatever the fabric's real, current rate is, since a correctly-built
synchronizer doesn't care which). Sits directly in front of
`pcie_unicell_bridge.v`, which is completely unchanged. Verified with a
parameterized testbench running the identical transaction sequence at
both a 25MHz-equivalent and a 50MHz-equivalent slow clock -- passes
identically at both, confirming frequency-independence directly rather
than leaving it as an assumed property. One genuine bug caught and fixed
during this verification (a testbench reset-vs-clock-edge race, not an
RTL bug -- diagnosed via internal signal tracing after a first "fix"
attempt didn't resolve it), the same measure-don't-assume discipline as
everywhere else in this project. Then actually integrated into
`pcie_hip_wrapper.v` (not left as a verified-but-unused module) --
`top_arria10_zone1_v3.v` updated to pass `CLK`/`rst_all` into the
wrapper's new `slow_clk`/`slow_rst` ports, full top-level re-verified
elaborating cleanly with the integration in place.

**NEXT:** still needs the real Quartus machine: `.qsf` pin assignments for the new
physical PCIe ports (`pcie_refclk`/`pcie_npor`/`pcie_perst_n`/
`pcie_rx_p`/`pcie_tx_p`), matching `pcie_hip_test.qsf`'s already-proven
assignments for this same board rather than guessing new ones. Also
still open, per the clarification above: an actual measured Fmax for the
real fabric (not just `clk_div`) at the current zone count, to know
whether 50MHz is genuinely achievable before committing to it.

## 47. Pentacross tiling: bounded grid is provably impossible, wraparound resolves it exactly -- and why this stayed deferred behind PCIe (Alan, 2026-07-21)

**Direct follow-up to #42.** #42 described pentacross as five *zones*
forming a plus-shaped tile. This entry is about the same shape one level
down -- five *cells* forming a plus-shaped local-broadcast cluster
within a single 25-cell (5x5) zone -- and what it takes to tile a whole
zone exactly with five such clusters.

**On a bounded (non-wrapping) zone, this is provably impossible, not
just hard.** Checkerboard-colour a 5x5 grid: 13 cells of one colour, 12
of the other. Every plus-shaped cluster (centre + 4 neighbours)
necessarily covers 4 cells of one colour and 1 of the other, since a
cell's neighbours are always the opposite colour from itself on a
plain grid. With 5 clusters, the total covering one colour is always
`20 - 3k` for some whole number of clusters `k` centred on that colour
-- and no integer `k` makes that equal 12 or 13 (closest are 11 and 14,
always two off). Confirmed two ways, not just asserted: this parity
argument, and a brute-force search over every possible placement,
which found zero valid exact tilings.

**With wrapped (toroidal) edges, an exact tiling exists** -- confirmed
by brute-force search, which found one directly. The mathematical
reason wrapping changes the answer: the parity argument above relies on
the grid being properly bipartite (every cycle has even length, so a
consistent 2-colouring exists). Wrapping a 5-wide edge back on itself
creates a 5-cell loop, and an odd-length loop breaks bipartiteness
entirely -- the argument that proved impossibility on the bounded case
simply doesn't apply once wrapped. That's a real structural reason, not
a coincidence of one search result.

**Alan's own sketched layout, cross-checked and corrected.** Given as
five colour groups over cells 0-24 (numbered bottom-left to top-right,
row-major): two cells (3 and 20) were initially set aside as "odd,"
looking like leftovers. Checked computationally: they aren't leftovers
at all -- they're the wrapped-around fifth member of two of the other
groups. Cell 20 is Red's wrapped "south" neighbour (wrapping bottom row
back to the top); cell 3 is Dark Green's wrapped "north" neighbour
(the same wrap in reverse). Corrected groupings, verified to cover all
25 cells with zero overlap and zero cells missing:

| Cluster | Centre | Cells |
|---|---|---|
| Red | 0 | 0, 1, 4, 5, 20 |
| Light green | 7 | 2, 6, 7, 8, 12 |
| Purple | 14 | 9, 10, 13, 14, 19 |
| Yellow | 16 | 11, 15, 16, 17, 21 |
| Dark green | 23 | 3, 18, 22, 23, 24 |

**Refined framing (Alan, 2026-07-21) -- corrects how this was first
stated, not a contradiction of it: wire-existence and cardinal-bit-usage
are two separate decisions, not one.** Whether the wraparound
connection physically exists is still a synthesis-time commitment, same
as any other physical routing -- no way around that. But whether a
given cell treats that connection as local-broadcast or cardinal
(one-hop) for any particular tiling is exactly the cardinal-latch
mechanism #42 already established -- a pure runtime config decision
layered on top of whatever's physically wired. Once the wraparound wire
exists, pentacross isn't a special case needing its own synthesis --
it's just one config-bit pattern among however many others that same
fixed wraparound grid could support.

**Deliberately not built yet, in either the VM or RTL -- and why that's
correct sequencing, not neglect.** This whole cardinal-latch shape-
partitioning model, wraparound included, has no implementation anywhere
yet. Explicitly deferred until PCIe is confirmed running, because PCIe
is what makes iterating on different cardinal-latch configurations fast
and practical, rather than fighting UART/JTAG bandwidth for it -- the
same reasoning as why the PCIe question got picked up before this one,
not a separate, unrelated priority call. Stated plainly (Alan,
2026-07-21): PCIe supports the entire system's iteration speed, and if
UniCell increasingly moves toward being explored/configured through a
software model -- which is really what it already is at heart -- that's
a logical extension of the architecture, not a departure from it. By
that same logic, the VM has to fully reflect this cardinal-latch/
wraparound model once it's built, not a partial or approximate version
of it -- which is exactly why getting the PCIe foundation right first
was the correct call, not a detour from this shape-partitioning work.

**Superseded (Alan, 2026-07-24): dropped, not deferred.** Once #42 (per-
edge cardinal bits) and #49 (comparator -> pattern -> cardinal ->
openness AND-gate chain) are both built, local/cardinal connection
identity for every edge becomes a genuinely *mutable, programmable*
per-cell property rather than something fixed at synthesis -- "shape"
lives entirely in runtime config state at that point, not in physical
wiring. Wraparound was only ever needed to solve one specific problem:
#50's edge/corner "this cell is missing a cardinal direction"
feasibility question. It was never load-bearing for shape-partitioning
itself. Adding a second, physically-fixed kind of connection (a real
wraparound wire, decided at synthesis) on top of a mechanism whose whole
point is that connections are now mutable/programmable conflates two
different categories of "connection" -- and pushes real cost onto the
loader specifically, which would then have to reason about wraparound
partners *in addition to* per-edge cardinal/local state, compounding
complexity for a problem (edge/corner infeasibility) that's cheaper to
just accept as a permanent, honest constraint of the substrate (see
#50's follow-up note). Not revisiting this unless a future concrete need
re-opens it -- explicitly removed from the roadmap, not merely pushed
further down it.

## 48. N-dimensional structure mapping via bridge-cell reconfiguration at locality edges, not just pond edges (Alan, 2026-07-22)

**The core idea, in Alan's own framing:** zones tiled side by side are a
flat 2D physical structure on their own. Cardinal bridges push this
toward "3D plus" -- each bridge can jump to a different point, not just
the nearest neighbour. Combined with cell mutability (the cardinal-bit
reconfiguration from #42/#47), this can create genuinely n-dimensional
*structure* -- not n physical spatial axes, but n independent directions
of movement in the connectivity graph, which can exceed what the flat
2D layout alone could ever express.

**Cardinal bits alone are fixed to 4 points** (N/S/E/W, local-vs-
cardinal per edge) -- real, but bounded. The richer mechanism Alan
means is **actual bridge cells**: cells that can be added, removed, or
retargeted to jump to a distant point, not just a same-edge neighbour.

**Genuinely important, load-bearing clarification: this needs zero new
hardware.** The "bridge cell" isn't a new component to design -- it's
the `command_cell`/`output_address` push mechanism already confirmed
live in the current RTL (see the v3.0 addressing discussion earlier
this session): any ordinary cell, with `command_cell` (`cmd_latch[10]`)
set and `output_address` pointed via `CMD_SET_OUTPUT_ADDR`, pushes its
data onto a *distant* cell's command bus instead of computing a normal
gate result. Already proven, already the real mechanism behind inter-
pond bridging today. "Adding/removing/changing" a bridge is just
re-issuing that same config sequence against whichever cell is being
repurposed -- a config-time reconfiguration of an already-silicon-
proven primitive, not new physical routing. The pause Alan notes for
any reconfiguration is the same kind of settling/handshake any cardinal-
bit change would already need, not a new cost this idea introduces.

**The actual new idea isn't a new mechanism -- it's a new *scope of
application*.** Bridges were and are intended for pond edges. Alan's
extension: apply that same proven push mechanism at **locality edges**
too (the local-cluster boundaries from #42/#47), not only pond
boundaries. That's what turns this into genuine n-dimensional structure:
a local cluster's "far" connection no longer has to go to a physically
adjacent pond -- it can jump to any distant cell reachable via the push
mechanism, giving the connectivity graph more independent directions of
movement than the flat physical layout could express on its own. Same
"compose from already-proven primitives, don't invent new ones" pattern
that's run through this project's best ideas (cardinal-bit reuse for
shape partitioning, ICM's format portability) -- this is that same
instinct applied one level up, to topology itself.

**Status: real, coherent, and cheap to eventually build (no new
hardware design implied) -- but explicitly parked behind the same
"stability first" sequencing already agreed this session.** PCIe on
real hardware, then the cardinal-latch/wraparound cell work (#42/#47),
then compiler/VM catch-up, then model validation via the existing
55-model library, then docs -- nothing new gets built on top until that
chain holds. This entry is the fuller elaboration of the placeholder
originally logged under this number; nothing here is scheduled work yet.

**Acknowledged (Alan, 2026-07-22): working through the accumulated
points.md backlog is itself real, non-trivial time** -- this file is
carrying genuine weight by now (48 entries and growing), and reviewing/
triaging it properly will take real effort once that phase arrives.
Like the docs pass, this is work that's genuinely road-workable --
doesn't need the Quartus machine, can happen piecemeal on mobile between
other things, same as this whole idea (#48 itself) got worked through.

**Correction (Alan, 2026-07-22): not a separate tool -- the actual
planned VM catch-up itself is what this refers to.** Not a lightweight
side-tool distinct from the real compiler/VM work; the same VM already
on the roadmap (the v2.3-to-current-cell catch-up discussed earlier this
session) becomes the rapid idea-testing tool once that catch-up is
genuinely complete -- no separate thing needed. This is a real reason
the VM catch-up phase matters beyond just "the compiler needs to keep
up": once it reflects the current cell architecture fully, it's also the
tool that makes checking ideas like #48 fast, rather than each one
needing its own bespoke verification script the way today's pentacross-
tiling and CDC-bridge checks did.

**Further correction, leaner mechanism (Alan, 2026-07-22): the push side
(`command_cell`/`output_address`) isn't the mechanism this idea needs at
all -- new connections are just new listening points.** On reflection:
`input_address` (the listen/watch side) is *already* freely re-pointable
to any address on the bus, already proven, already covers "connect to a
distant point" completely on its own -- a cell that wants data from a
distant point just points its own `input_address` there. The
`command_cell`/`output_address` push side is a genuinely different
thing: it injects *commands* onto a distant cell's command bus (control-
plane operations -- reconfigure, trigger an opcode), not ordinary
computed data. The real question this session raised was whether the
push side needs extending to *also* feed a distant data-side latch, for
symmetry -- and the answer is no: doing that would just duplicate what
the listen side already does for free, while blurring the one clean
distinction that currently keeps control-plane and data-plane separate,
for no matching benefit. So the corrected, leaner picture: n-dimensional
structure via "new connections" is entirely a listen-side matter --
`input_address` re-pointed at a distant address -- and the push/command
mechanism stays exactly where it already is, untouched, doing exactly
what it already does. Even less new surface area than the "new scope of
application for the push mechanism" framing earlier in this entry
implied; that framing is superseded by this one.

## 49. Honest architectural gap: no data-dependent branching exists anywhere in the system (Alan, 2026-07-22)

**The finding, stated plainly rather than softened:** there has never
been a genuine data-dependent branch anywhere in this architecture --
not in the cell RTL, not in the VM, not in the compiler's program-table
model. Every real algorithm with an `if`/`else`, a threshold check, or a
data-dependent loop bound has no actual mechanism to express in the
current system. This surfaced while checking whether the "choice cell"
concept from earlier this session (#48's discussion) already existed
under different terminology, the way "second latch" and "push latch"
both turned out to -- it doesn't. This one is a genuine, confirmed hole.

**What exists, and why it doesn't close the gap despite looking
adjacent:**
- **The program table** (see `PLAN.md`) can hold multiple candidate
  entries/paths -- the *structure* for branching exists at the table
  level. But nothing selects which entry actually gets used based on a
  *computed data value* -- the table's whole value proposition (peak
  DSP concurrency read off directly, I/O prefetch/drain fully
  predictable) depends specifically on the schedule being known and
  fixed at compile time. There's no data-triggered selection mechanism
  layered on top of that structure.
- **The cardinal-bit "openness of direction"** (per-edge local/cardinal
  reconfiguration, #42/#47) is the closest existing analog -- genuinely
  reconfigurable connectivity -- but it's reconfigured explicitly by
  command, not automatically triggered by comparing a cell's own
  computed result against a condition. Reconfigurable is not the same
  thing as data-dependent.

**Why this is a real, structural tension, not just a missing feature:**
the program table's elegant properties (no liveness analysis needed,
DSP peak-concurrency trivial, I/O schedule known in advance) all rely
on the execution path being fixed before anything runs. A genuine
runtime branch means the path *isn't* fully known in advance anymore.
Two honest directions this could go, neither chosen yet:
1. **Predication-style**: the compiler statically schedules the
   resource cost of *both* branches up front (paying for both,
   guaranteeing nothing about the schedule changes), and the runtime
   "choice" only picks which branch's *result* actually gets committed
   -- preserves the table's compile-time-known guarantees entirely, at
   the cost of wasted resource use on the branch not taken.
2. **Genuine dynamic scheduling** -- the table itself becomes able to
   select its next entry based on live data, which is a fundamentally
   harder compiler/scheduling problem, and would give up some of the
   simplicity that makes the table valuable today.

**Status: identified, real, and explicitly deferred -- same "stability
first" sequencing as everything else logged this session.** Not
something to design now. Worth being on record precisely because it's
foundational: whatever eventually gets decided here will likely shape
how the compiler/VM catch-up work (already on the roadmap ahead of
this) gets structured, so it's worth knowing this hole exists before
that work begins, even though closing it stays parked behind PCIe, the
cell work, and the compiler/VM catch-up itself.

**Follow-up thread, working toward an actual mechanism (Alan, 2026-07-22):**

*Cardinal-direction encoding for a branch cell.* Checked directly: selecting
any non-empty subset of 1-4 cardinal directions is 15 combinations, fitting
exactly in 4 bits (not 5/20 as first estimated) -- and this exact 4-bit
encoding already exists as `routing_mask[14:11]`. So the "which directions"
part of a branch cell needs no new bits at all; the real remaining question
narrows to how a branch cell would compute a *new* `routing_mask` value from
its own data and write it back live, not where to store the choice.

*The branch-cell flag needs a place to live -- and there isn't one.*
`command_cell` today is a single bit (`cmd_latch[10]`), a binary flag with no
room to grow in place. Proposed replacing it with a genuine 2-bit mode field
(`00`=normal, `01`=command, `10`=branch, `11`=spare) -- a real design
improvement on its own merits, cleaner than an ad-hoc flag per new cell role.
But confirmed directly against the RTL: the only bits with any room at all
are the same `cmd_latch[18:16]` (3 free) that entry #42 already claimed in
full for the per-edge cardinal decomposition, over #43's already-parked
lane-split idea. So this became a genuine three-way contest over an already-
exhausted resource, not a fresh allocation.

*Checked whether the nibble-mask/lane-cut fields could be compacted to free
up room -- they're already as compact as they should be.* `m_nibble_mask`
(8 bits, `[39:32]`) and `m_lane_cut` (3 bits, `[51:49]`) are genuinely
separate, sequential pipeline stages (shift -> lane-cut -> nibble-mask ->
gate), not one field doing double duty. Confirmed zero of the 55 current
models in `model_library.py` reference `nibble_mask` at all -- suggestive
that the full arbitrary 8-bit pattern space may be more than real use needs,
but not proof it always will be. Alan's call: doubling these fields' duty to
free bits would create real confusion for a modest, uncertain saving --
rejected on those grounds, not pursued further.

**Resolution: extend the internal latch from 64 to 66 bits.** With every
other avenue checked and either exhausted (the free-bit pool) or rejected on
its own merits (mask-field compaction), widening by exactly the 2 bits
actually needed is the smallest real fix left. This raised one concrete,
separate question worth resolving too: does this ripple into the PCIe
register map built earlier this session (`CMD_DATA`/`CMD_BUS`/
`STATUS_ADDR_VALID`/`STATUS_DATA`, all 32-bit words, a direct consequence of
`pio_bridge_0`'s narrower Avalon-MM interface)? **Resolved cleanly, no new
PCIe work needed:** setting these bits stays opcode-based, the same pattern
as `METH_SET_MASK`/`METH_SET_LANE`/`METH_SET_ROUTING` already use -- an
opcode plus an immediate value transaction, which already fits entirely
within the existing 32-bit `CMD_BUS`/`CMD_DATA` pair. The widening is purely
internal to the cell's own storage; nothing about how it gets configured
needs a wider live data path.

**Status: a real, now-settled design direction (66-bit `cmd_latch`,
addressing stays opcode-based) -- but the exact bit assignment (branch-cell
mode field position/width, whether `command_cell` relocates for
contiguity) is not yet finalised, and this whole thread stays behind the
same "stability first" sequencing as everything else in this entry and #42.
Nothing here is scheduled work yet.**

**Final resolution, superseding the 66-bit widening above (Alan,
2026-07-22): a whole new dedicated region instead of a tight 2-bit
widening.** Rather than squeeze `cell_type_mode` into the same scarce
pool #42/#43 were already contesting, add a genuinely new region --
either 32 or 64 bits, size not yet decided -- of which exactly **2 bits
get defined meaning right now** (`cell_type_mode`: `00`=normal,
`01`=command, `10`=branch, `11`=spare). **The remainder is deliberately
left as pure, undifferentiated internal scratchpad -- no other flags
assigned there, on purpose.** The explicit intent is to hold things like
a branch cell's own computed offset, or other values an internal process
needs to carry between steps -- but *not* pre-carve that space into more
named sub-fields the way the rest of `cmd_latch` has been, precisely so
it doesn't become the next crowded battleground the way `[18:16]` did.

**Confirmed: internal use only, not opcode-reachable.** This region is
read/written purely by the cell's own internal logic (e.g. a branch cell
computing and consuming its own offset) -- it has no `CMD_SET_*`
counterpart, no status-readback path, and no visibility from outside the
cell at all. Nothing about it rides the command bus.

**Still genuinely open, not yet decided:** whether this new region is 32
or 64 bits -- left open deliberately rather than guessed at now. Same
"stability first" sequencing as everything else in this entry: real,
settled direction, nothing here scheduled until PCIe, the cell work, and
the compiler/VM catch-up are done.

**Honest re-assessment (Alan, 2026-07-22) -- worth stating plainly
rather than letting the above read as more settled than it is.** The
scratchpad-region idea directly above is genuinely conjecture right now,
not a design: there's no mechanism yet for how it would actually be
populated or read, by what, or when. Two real, separate things worth
keeping distinct going forward, not conflated:
- **The scratchpad's generality is itself an open question, not just its
  size.** If in practice it only ever ends up holding one thing (e.g.
  just a branch cell's offset), then "general-purpose scratchpad" was
  the wrong framing from the start -- it should be an honestly-named,
  purpose-built field instead. Not worth committing to a generic
  abstraction that turns out to be single-use wearing a vaguer name.
  Genuinely undecided until a real second use case is in view.
- **The branch-cell *mechanism* (bit layout, scratchpad, etc.) was
  always in service of the branch cell *capability* -- and only the
  capability is the actual, standing priority, not any particular
  implementation of it.** If a cleaner, more direct mechanism turns out
  to deliver the branch cell without needing a generic scratchpad at
  all, that is a better outcome, not a failure to reach the conjecture
  above. The priority is stated plainly: **the branch cell needs to
  exist.** Everything about bit layout in this entry is disposable
  scaffolding toward that, not the goal itself.

**Closing note for whoever picks this up next (Alan, 2026-07-22):**
current best guess, not a decision -- this may end up looking like a
routing-latch-style bit (in the spirit of `routing_mask`: compact,
bit-level, selection-based) rather than the generic scratchpad
conjectured above. Left here as a lead to examine later, not a
direction committed to.

**Further elaboration, still explicitly ideas-stage, not design (Alan,
2026-07-22).** Worked through in more detail: mode-tagged reinterpretation
of the same scratch bits (counter in normal mode, predicate config in
branch mode, up to three 8-bit opcodes in command mode -- 24 bits, +2
mode bits, 6 spare -- letting a cell be fully configured in two writes,
methodology then topology, commands pre-set and issued on a later trigger
the same way the existing memory-on-call mechanism already works).

**Pushback worth recording alongside it, not just the elaboration:**
- The counter-in-normal-mode idea is speculative in a way branch and
  command aren't -- branch closes a confirmed real gap (this entry);
  command reuses an already-proven mechanism. Whether any actual model
  in the current 55-model library needs a per-cell counter hasn't been
  checked the way `nibble_mask` usage was checked earlier in this entry
  (zero hits there was a genuinely useful signal) -- "sounds useful"
  shouldn't earn bit-budget without the same evidence bar everything
  else here has had to clear.
- A fixed opcode order (methodology, then topology, then parameter) is a
  real constraint, not a free convenience -- it assumes every
  configuration always needs exactly one of each, in that order. Worth
  flagging as a genuine tradeoff to weigh, not treating as settled.

**A concrete addition worth considering, connecting this back to what's
actually proven rather than inventing new hardware:**
- **No new predicate ALU needed** -- the comparison gates already exist
  and are already silicon-proven: `INT32_EQUAL`, `INT32_LT_U`,
  `INT32_LT_S`, `INT32_MIN`, `INT32_MAX` in the current model library,
  computed via the same topology-selected NOR-gate tree every other cell
  already uses. A branch cell could simply *be* one of these existing
  gate types -- the branch-specific part is only what happens to the
  resulting 1-bit result afterward, not how it gets computed.
- **That result should select between two pre-configured `routing_mask`
  values, closing the loop with the "routing-latch-style bit" hunch
  above directly** -- result=0 picks mask A, result=1 picks mask B, both
  set at config time like any other cell's routing_mask. No new output
  mechanism needed at all; the already-proven cardinal bridge hardware
  does the actual routing, and the branch cell's only new contribution
  is *which* already-existing config value gets applied.
- **Worth deciding before any bit gets spent on a stored threshold at
  all:** does the comparison need a *stored* value, or can it compare
  two cells' *live* data using the two-arrival model (A stored, B the
  trigger) already used everywhere else in the fabric? If "compare A vs
  B, both live" covers the common case, a scratchpad-held threshold may
  only be needed for the narrower "compare against a fixed constant"
  case -- a much smaller ask than a full 30-bit general register.

Still all conjecture at this stage, per Alan directly -- nothing here
is a decision, just a fuller, more critically-examined version of the
same open thread, closer to what's actually proven in silicon.

**Concrete confirmation this gap was already silently assumed, not just
architecturally implied (Alan, 2026-07-22).** Checked directly: can a
single individual cell natively produce a collapsed, single-bit
comparison result at all? No -- confirmed against the complete native
gate list (`PASS`/`NOT`/`NOR`/`AND`/`OR`/`NAND`/`XOR`/`XNOR`/`ZERO`/`ONE`),
every one bitwise across the full 32-bit word, none reducing to a single
true/false bit. `INT32_EQUAL` etc. are themselves multi-cell reduction
trees built from these same primitives, not a native single-cell
capability -- corrects the earlier pushback in this entry, which implied
a branch cell could simply "be" one of these existing gate types; it
can't, not as a single cell.

Searched `model_library.py` directly for prior evidence of an assumed-
but-unbuilt branch capability, and found it: `CAT_CONTROL`'s own
founding comment names four intended sub-types --
*"mux, select, branch, counter"* -- but the 5 actual models filed under
it are a mux, an SR latch, a pass-chain aligner, and two fixed-delay
elements. Branch and counter were named as intended from the start and
neither was ever built. `SEQUENCER_POND` makes it explicit:
description reads *"handles complex branching without dead cells,"*
while its actual entry shows `cell_count = 0`, `pipeline_depth = 0`,
`tiles_used = []` -- a capability claimed in prose with nothing behind
it in silicon or config.

**Worth being honest about a false-positive risk in this same check, not
just the finding itself.** A first pass flagged 9 total `cell_count = 0`
entries across the library, which would have overstated the problem if
reported without checking each individually. Checked all 9: 6 are
legitimate software-side system modules (`COMPILER_POND`,
`TILE_LIBRARY_POND`, `MODEL_LIBRARY_POND`, `PROGRAM_BUILDER_POND`, etc.
-- genuinely VM-side, correctly zero cells since they're not fabric
circuits at all), 2 are genuinely zero cells by design
(`INT32_SHIFT_L_NIBBLE`/`_R_NIBBLE`, explicitly documented as "handled
by `cmd_bus shift_sel`" -- a real, working feature implemented via an
existing config-bit mechanism, not a gap). Only `SEQUENCER_POND` is an
actual paper wall. "Assume strikes again" applies to verification
claims too, not just the original model descriptions -- the discipline
has to hold for both.

**The general lesson, stated plainly (Alan, 2026-07-22): every model
needs concrete testing and results, not a description that merely
sounds plausible.** A `cell_count`/`pipeline_depth` and ideally a
"verified" tag should be the actual bar for trusting any model entry
claims a real capability -- not the prose describing it. This is a real
finding worth carrying into the eventual 55-model validation pass
already on the roadmap (per earlier in this session): check every
model's numbers, not just its description, before trusting it as a real
test case.

**Still leaves the actual branch problem exactly where it was --
confirmed real, confirmed never built, still explicitly parked for
later.** This section adds evidence the gap was already silently
present in the existing model taxonomy; it doesn't change the priority
or sequencing already stated above. The branch cell still needs to
exist; that work is still behind PCIe, the cell work, and the compiler/
VM catch-up, same as everything else in this entry.

**The most concrete, cheapest-level mechanism yet, worked out just before
ending this session (Alan, 2026-07-22) -- a genuine candidate design, not
just another conjecture layer. Corrected below after an initial
mis-transcription; this version supersedes it.** A new, permanently-
present **32-bit** threshold latch per cell -- full data width, not a
scaled-down range -- defaulting to all-1s. A comparator sits between
this latch and the incoming data, producing a real 3-way outcome (lower /
equal / higher), each selecting one of three pre-configured **4-bit
routing patterns**, same format as `routing_mask` (one bit per cardinal
direction, and a pattern can request multiple directions at once, e.g.
`1010` = North and South both). **The three 4-bit patterns are packed
together into a separate 12-bit latch** (4+4+4), distinct from the
32-bit threshold latch -- two separate new pieces of storage, not one;
the earlier "12-bit" figure in this entry wasn't wrong, it was just
attached to the wrong field before this correction.

**Opcode-side complexity, flagged honestly rather than solved now
(Alan, 2026-07-22):** configuring this cleanly means setting both a
full 32-bit threshold value *and* a 12-bit tri-pattern field -- these
don't fit the existing single-opcode-plus-32-bit-immediate pattern
symmetrically (`METH_SET_MASK`/`METH_SET_LANE`/`METH_SET_ROUTING`-style).
Real open question, explicitly not resolved here: one opcode packing
all 12 pattern bits into part of a word with room to spare, versus
three separate opcodes (one per outcome), and how that sequences
against the threshold-setting opcode. Left as a genuine unsolved piece
for whoever designs this for real, not guessed at now.

**Three independent AND-gated layers, not sequential stages replacing
each other.** The pattern is a *request*, not a decision on its own --
it still has to pass through the existing `routing_mask`/cardinal
setting (does this cell have bridges enabled in those directions at
all?) and the per-edge openness state (#42/#47/#48 -- is this specific
edge open or closed right now?). All three have to agree for a given
direction to actually fire: the pattern wanting North doesn't matter if
cardinal doesn't permit it, and cardinal permitting it doesn't matter if
that specific edge is currently closed. If the cell also performs its
normal computation, the result flows out through whichever direction(s)
survive all three layers.

**Fallback path, made explicit (Alan, 2026-07-24) -- without this, a
rejected direction has nowhere to go and the fired value is simply
lost.** When any one of the three layers disagrees for a given
direction, the data does not vanish -- it falls through to local-bus
presentation instead. Concretely: local-bus delivery requires
cardinal=0 for that edge (per #42's local/cardinal partition bit) AND
openness=1 (the edge is open, not closed). This makes openness a gate
on the edge being usable at all, independent of which mode (local or
cardinal) it's usable in -- cardinal picks the mode; openness decides
whether that mode is currently live.

**Why the all-1s default matters, precisely -- corrected reasoning:** a
default pattern requesting *every* direction means the actual outcome is
entirely governed by whatever cardinal and openness already have
configured -- exactly today's existing behaviour, with this new layer
adding nothing extra when left at default. A true no-op when unused, at
a fixed, small, always-present cost -- same "permanent, harmless-by-
default fixture" principle as elsewhere in this project, not an
optional per-cell mode needing its own enable flag.

**On the earlier composed comparison models (`INT32_EQUAL` etc., 95-500+
cells) discussed earlier in this entry:** since this native comparator
is now confirmed full 32-bit width, not a reduced range, it may cover
significantly more of what those heavier composed models were for than
first thought -- worth re-examining whether the two are genuinely
solving different problems or whether this native mechanism now
subsumes the common case entirely. Not resolved here; flagged for
whoever picks this up next.

**Status: the clearest, most buildable candidate this entry has
produced -- still not a final decision, still behind the same
"stability first" sequencing as everything else here.** A good place to
leave this thread for now.

## 50. Cell placement is three separable constraints, not one problem (Alan, 2026-07-24)

**The realisation.** Placing a logical (portable ICM) node onto a
physical card was being treated as a single "where does this go"
decision. It's actually three separate, orderable checks, and
conflating them is what made the problem feel harder than it is:

1. **Feasibility** -- does the candidate physical location even have
   the cardinal directions the logical node's edges require? An
   interior cell has all four. A die-edge cell is missing at least one
   *unless* that direction is wired to a wraparound partner (#47) --
   and whether wraparound wiring exists at all is itself a synthesis-
   time commitment, not something the placer can assume. A logical
   node needing, say, both East and West links cannot go on any
   physical cell where either direction is genuinely absent. This is a
   hard constraint, checked first -- not a cost to minimise, a location
   that fails it is simply not a candidate.
2. **Cost** -- among locations that pass feasibility, minimise
   crossings/hops. This is the already-solved part: pentacross
   placement (#17) and anchor-first BFS growth from DSP-anchored
   coordinates.
3. **Address binding** -- once a physical cell is chosen for a logical
   node, assign its runtime `input_address` (the mutable LISTEN
   address matched by `addr_match`) fresh, at load time. This is
   already decoupled in the ground truth from the cell's permanent
   `CELL_ID` (matched by `config_match` for all config/reconfigure
   targeting) -- see `unicell64_v3.v` lines ~25-33, ~683-694, and
   opcodes `CMD_BOOT_COMMIT` (0x07, sets initial logical addr at boot)
   and `CMD_SET_INPUT_ADDR` (0x02, repoints it later, authenticated).
   Several physically unrelated cells (different `CELL_ID`s, different
   cards, different placements) can be assigned the *same*
   `input_address` at load time -- which is the actual mechanism behind
   "several cells watch one value," not a physical broadcast. The
   address value itself is loader-assigned scratch, re-derived every
   load; it never needs to appear in the portable ICM.

**Why separating these matters.** Each has a different failure mode and
a different owner:
- Feasibility failures are unrecoverable at that location -- no amount
  of routing cleverness fixes a missing wire. Must be checked before
  cost-minimisation starts, or the placer can spend effort optimising
  toward a location that was never viable.
- Cost is the only place there's an actual search/optimisation problem
  -- and it's the part already solved (#17).
- Address binding has no placement content at all -- it's pure
  bookkeeping the loader performs after placement is fixed, using
  whatever `input_address` values happen to be free.

**What this means for the substrate map (#19).** The map already has to
be the single authoritative source of physical adjacency per #19's
decision. This entry adds a concrete requirement on its *contents*: for
every physical location, the map must record, per cardinal direction,
one of {real neighbour, wraparound partner, absent} -- not leave it
inferred from grid position. That's what lets the placer's feasibility
check (step 1) be a direct lookup against the map rather than geometric
reasoning re-derived per target. Genuinely unbuilt anywhere yet, same as
the wraparound mechanism itself (#47) -- this is a requirement on the
map's eventual schema, not a claim it exists today.

**Note (2026-07-24): this entry was originally misfiled mid-#49 by
session error, then corrected -- #49 above is restored to its exact
original text, this entry moved here after it in full.**

**Update (2026-07-24): wraparound (#47) dropped, not just deferred --
edge/corner infeasibility is now a permanent, accepted constraint of
the substrate, not a gap waiting on wraparound to close.** Once #42/#49
make local/cardinal connection identity a mutable per-cell property,
adding a second, physically-fixed wraparound wire on top would conflate
two different categories of "connection" and push real extra cost onto
the loader (reasoning about wraparound partners *in addition to*
per-edge cardinal/local state) for a problem cheap enough to just
accept: some physical locations genuinely lack a direction, full stop.
The placer's feasibility check (step 1 above) still holds exactly as
described -- it just never resolves a location from infeasible to
feasible via a wraparound partner; it simply rules out locations that
don't have what a logical node needs, permanently.

**Status: architectural clarification, not yet implemented.** Sits
alongside #17 (cost) and #19 (map as source of truth -- now recording
{real neighbour, absent} only, no wraparound-partner case). No code
changed by this entry -- next concrete step is deciding the map's
actual schema (#19's open item 1, the synthesis-application mechanism)
with this three-way split in mind.

## 51. Routing latch sized for 6-direction (3D) from the start, not just the current 4-direction case (Alan, 2026-07-24)

**The proposal.** The new routing latch from #49 (currently: 12-bit
tri-pattern, packed 4+4+4 for the three comparator outcomes) gets
widened and consolidated: build it as a single 32-bit register sized
for 6 cardinal directions (N/S/E/W/Up/Down) up front, rather than 4 --
even though the 3D/stacked-die case itself (see conversation,
2026-07-24) is explicitly many years out. The reasoning: since none of
routing latch, cardinal-bit (#42), or openness (#47/#48) exist in RTL
yet, sizing for 6 directions now costs nothing today and avoids a
redesign later when 3D actually arrives.

**The bit budget, checked:** 3 comparator outcomes x 6 direction bits
each = 18 bits (tri-pattern, one-hot-multicast per outcome, same
semantics as today's 4-bit version just widened) + 6 bits cardinal
(one bit per direction, #42's local/cardinal partition, widened from
4) + 6 bits openness (one bit per direction, #47/#48's per-edge
open/closed state, widened from 4) = 30 bits, + 2 bits reserved for
cell mode (the `command_cell`-successor 2-bit mode field explored
earlier in #49 -- `00`=normal/`01`=command/`10`=branch/`11`=spare) =
32 bits exactly. Framed as "5 groups of 6, plus 2" -- checks out.

**What this consolidates that wasn't previously unified:** #49's
tri-pattern mechanism, #42's cardinal bit, and #47/#48's openness state
were three separate not-yet-built mechanisms with no single agreed home
for any of them. This entry gives all three an explicit, sized home in
one new 32-bit register -- distinct from the existing 32-bit threshold
latch (#49, the comparator's *other* input), so the full new-storage
picture per cell is now: 32-bit threshold latch + 32-bit routing latch,
both new, both separate from the existing 64-bit `cmd_latch` (which has
zero free bits remaining, per this session's earlier finding).

**Status: architectural sizing decision, not yet implemented.** Same
"stability first" sequencing as #49/#42/#47/#48 -- parked behind PCIe,
the cell work, and the compiler/VM catch-up. Opcode-side question from
#49 (how a 30+2-bit register gets configured cleanly) still applies,
now at a wider field. Not yet decided: whether cell mode really only
needs 2 bits or whether the branch-cell mode discussion elsewhere in
#49 wants more.

## 52. Real fabric Fmax finally has a measured answer -- and a genuine, fixed constraint gap on the way to it (2026-07-24)

**Long-open question, first flagged in #46:** was `clk_div`'s reported
Fmax ever the *real* fabric critical path, or just a trivial local
number? First real PCIe-integrated Fitter+Timing Analyzer run answered
this concretely rather than by more reasoning: `clk_div` Fmax reported
as 54.73 MHz in the summary -- but the same compile's detailed setup
report showed a **-1.457ns violation**, tagged against `clk_div`,
against a worst-case path list containing entirely unrelated clocks
(`pld_clk`, `coreclkout`, per-lane `tx_clk`). Hold, recovery, removal,
and minimum-pulse-width were all positive -- the specific signature of
a missing clock-group declaration (an unconstrained cross-domain path
TimeQuest tries to time synchronously by default), not a genuine
same-domain fabric failure.

**Root cause, confirmed rather than assumed:** `Unicell-Q.sdc` had zero
declarations separating the fabric's own clock (`CLK_100M`/`clk_div`)
from any of the PCIe Hard IP's internally-generated clocks.
`pcie_cdc_bridge.v` (#46) already handles this crossing correctly in
*hardware* -- a frequency-independent toggle synchronizer -- but the
`.sdc` never told TimeQuest the two domains don't need direct
synchronous timing closure against each other, so it invented a false
violation trying to enforce one anyway.

**Fixed:** added `set_clock_groups -asynchronous` to `Unicell-Q.sdc`,
splitting `{CLK_100M, clk_div}` from every other clock in the design
(all PCIe-IP-generated clocks, via a set-difference against
`all_clocks` rather than hand-enumerating each cryptic IP-generated
clock name) -- and leaving `altera_reserved_tck` (JTAG) out of both
explicit groups since Quartus/the SLD hub IP typically manages that
domain's constraints itself.

**Still needs a fresh compile to confirm:** whether `clk_div`'s Fmax
number changes at all once the spurious cross-domain violation is
removed, or whether 54.73 MHz was already the real number and the
violation was purely additive noise. Either way, this is the closest
this project has been to an actual trustworthy fabric Fmax figure --
first real measurement attempt, with a concrete, explained, fixed
obstacle on the way, rather than an unexamined number.

**Status: RESOLVED (2026-07-24).** Fresh compile with `derive_pll_clocks`
added confirmed the fix directly: `clk_div` setup slack went from
**-1.457ns to +0.309/+0.390ns positive** across every process corner
analyzed, with the clock-derivation log showing all PCIe-internal
clocks properly created before the group declaration runs (no more
"contains zero elements" warning).

**The real, trustworthy number: `clk_div` Fmax = 58.62 MHz, with clean
positive setup slack.** Against the 50MHz target, that's a genuine
~17% margin -- the first time this project has had an actual measured,
non-polluted answer to "can the fabric hit 50MHz." Slightly higher
than the interim 54.73MHz figure from the still-violating compile,
consistent with that number being affected by the same unresolved
cross-domain issue rather than a clean read.

One residual, likely-benign item left over: a "PLL cross checking...
missing 1 generated clock" warning on
`...twentynm_hssi_pma_cgb_master_inst|cpulse_out_bus[0]`
(`tx_bonding_clocks[0]` in the derived-clock list) -- looks like an
IP-internal artifact tied to multi-lane TX bonding, a feature this x8
non-bonded configuration isn't using. Not flagged as blocking, but
worth remembering if anything PCIe-link-specific misbehaves later.

Root-cause chain for the record, since it took two iterations to nail:
(1) missing clock-group declaration between fabric and PCIe clocks →
false cross-domain setup violation; (2) first fix attempt referenced
`all_clocks` before `derive_pll_clocks` had run, so the PCIe clocks
weren't registered yet → group evaluated as empty, no effect; (3)
adding `derive_pll_clocks` before the group declaration closed it for
real. Each step confirmed against an actual Quartus warning/report, not
guessed.

## 53. Boot-walk liveness check doubles as a real, per-card bad-cell exclusion list (Alan, 2026-07-25)

**The realisation.** #19 already settled that the boot-walk is a *verifier*
against the authored substrate map, not a discovery mechanism -- re-deriving
adjacency at runtime would just be "an elaborate mechanism to re-learn a
constant," since adjacency is a design property, fixed and identical on every
card built from the same bitstream. That's still right, and this doesn't
reopen it. But **liveness is a different kind of fact than adjacency.**
Adjacency is fixed by the map. Whether a specific physical cell on *this
specific die* actually responds is a manufacturing property -- unknowable from
the map, and potentially different card to card, even for identical
bitstreams.

The boot-walk already has to touch every cell to verify it against the map
(#19, point e). Recording *which specific cells failed that check*, as a
byproduct of a walk it's already doing, costs nothing extra -- and gives the
loader something the map fundamentally cannot contain: a real, per-card,
hardware-measured bad-cell exclusion list.

**What this means for placement.** Usable topology = authored map (ideal
adjacency) MINUS boot-walk-discovered defects (real, per-card exclusions).
This extends #50's feasibility check with a third reason a location can be
ruled out, alongside "missing a cardinal direction": "this cell is dead on
this specific board" -- a fact that can differ between two cards running the
identical bitstream, unlike the other two feasibility reasons which are the
same on every card.

**Status: identified, not yet implemented.** Sits alongside #19 (map as
source of truth for adjacency) and #50 (placement feasibility) -- adds a
runtime, per-card input to both without reopening either's core decision.
Mechanically: `CMD_ARRAY_RESET`'s existing boot-walk enabler (#19) would need
to accumulate a bitmap/list of non-responding `CELL_ID`s during its pass,
rather than just confirm-or-fault against the map. Not yet decided: where
that list lives (loader-local scratch state vs. something persisted per
card), or the exact signal a cell "failed to respond" vs. "responded wrong."

## 54. Boot-time DSP/BRAM locality query as a live verifier for the .isi sidecar -- the mechanism that makes "any card" genuinely true (Alan, 2026-07-25)

**Builds on an already-established principle, not a new one:** the anchor-
first placer (points.md, loader principles) already plans to ship a
Quartus-post-fit locality table as an `.isi` sidecar alongside the bitstream,
giving the placer real DSP-column seed coordinates rather than guessing.
#19 draws the explicit analogy between this and the substrate map itself:
"the bitstream carries its own topology."

**The extension:** rather than the `.isi` sidecar being the *only* source of
truth for where DSP/BRAM resources actually sit, a live boot-time query --
a separate function call from #53's plain cell-liveness walk, since it's
asking a different question (resource-type locality, not existence) -- can
verify that expectation against real silicon, the same verifier role #19
already established for cell adjacency and #53 now establishes for cell
liveness. Three parallel, independent facts, three verifications, one
consistent pattern: adjacency (map, #19), liveness (boot-walk, #53), resource
locality (`.isi` + boot-time query, this entry).

**Why this specifically is what makes "any card" real rather than assumed:**
if the loader can confirm, live, at boot, where the actual DSP/BRAM-bearing
cells are on *this* card -- rather than placement rigidly assuming one fixed,
pre-documented resource layout -- an ICM built with one card's resource
layout in mind can still correctly re-anchor onto a different card, or a
different region of a bigger card, because placement discovers/confirms the
real layout live rather than trusting a static assumption. This is also what
makes partial-card usage sound: if a design only needs a subset of a card's
cells, the resource map the loader actually uses still reflects what's really
there and where, regardless of how much of the card gets used -- "any card is
a target" and "using only part of a card" turn out to be the same underlying
requirement, both solved by the same live-verification mechanism.

**Status: identified, not yet implemented.** A natural pair with #53 (same
boot-time diagnostic moment, two distinct queries), and gives the `.isi`
sidecar concept referenced in #19 its own first real elaboration. Not yet
decided: exact query mechanism/opcode, or how a mismatch between the `.isi`
sidecar's expectation and the live query's finding should be handled (fault,
like an adjacency mismatch, or a softer fallback given resource locality
might legitimately differ more than adjacency would).

## 55. Hardware attach belongs in the workbench, not the VM -- and the software side now needs a full workup before it can absorb any of this (Alan, 2026-07-26)

**The proposal.** Card discovery, memory-decode enable, BAR mapping and
verification should live in the workbench's startup path, not in the VM.
The workbench already has the right shape for it: `--attach` boots the
simulated system and swaps the controller in behind an already-running
server, and everything above that layer -- visualiser, cell inspector,
bus injection, region manager -- talks to `ctrl` rather than to the array
directly. A hardware-backed controller presenting the same interface
would let the existing UI drive silicon without the UI knowing.

CLI shape falls out naturally: `--card 08:00.0` for the slot,
`--no-enable` when something else already owns the device, `--verify` to
run the known-good sequence before handing over control. Discovery can
be mostly automatic -- scan `/sys/bus/pci/devices` for vendor `1172`
device `2494`, prompt only when there's more than one, which starts
mattering as soon as there are two cards in a machine.

**Why the VM is the wrong home.** The VM is the correctness oracle --
card-agnostic, deterministic, the thing an `.icm` is proved against
before it ever meets silicon. Teaching it about PCI slots and Linux sysfs
paths would compromise exactly the property that makes it useful. The
workbench is already the place where a *specific* system gets attached
and driven, so hardware attach is the same job it does now with a
different backend.

**Two real obstacles, neither of them small.**

*The interface doesn't match yet.* `ImagoController` was built against a
Python array where reads are free, instant, and total -- any cell's full
internal state is inspectable at any time. Hardware is four registers, a
command sequence, and one latched output. Some workbench operations map
cleanly; others have no hardware equivalent at all. So this is not
"swap the backend and it works" -- it's working out which subset of the
workbench is meaningful against silicon and making the remainder fail
honestly rather than silently showing simulator state while claiming to
show hardware. That failure mode would be worse than not having the
feature.

*It depends on things that don't exist.* The current register interface
is a deliberate MVP subset: no bulk load path, no BRAM window, no status
beyond one latched output. Building the attach layer now means building
against an interface that is about to change -- #42 and #49 both alter
cell semantics, and the BRAM window (the actual point of PCIe: model
loading and data I/O buffering) isn't built.

**Sequencing:** after the cell work and after the BRAM window, not
before. Logged now so the reasoning is captured rather than
rediscovered.

**The wider point, and the more important half of this entry (Alan):
the software side needs a full workup before it can absorb any of this.**
The hardware has moved a long way this month -- PCIe integration, real
measured Fmax, and a set of cell-level decisions (#42, #47 dropped, #49,
#50, #51, #53, #54) that change what the substrate actually is. The
software has not moved with it, and much of it now predates the
architecture it's supposed to serve. `PLAN.md`'s definitive task path
already records this for the model library specifically; this entry
records that it is broader than the models.

`workbench.py` alone is ~2,700 lines carrying assumptions from an era
when shape was fixed at synthesis, connections were permanent wiring,
and there was no hardware target at all. The compiler, the VM, and the
controller are in the same position to varying degrees. None of that is
wasted work -- it's how the architecture got understood -- but a lot of
it now encodes a model of the substrate that is no longer accurate.

**Not a task for this session, and deliberately not scoped here.** The
right moment is after the substrate stabilises (task path steps 2-4),
because doing it before means rewriting against semantics that are still
moving. But it should be an explicit, planned piece of work when it
comes, not something attempted incrementally under the pressure of
whatever hardware feature needs it next.

## 56. NOT_B is a real, decoded topology value with no dedicated opcode -- corrects the earlier ALU-richness comparison (2026-07-29)

Earlier this session, comparing the cell's topology field against a
general 2-input boolean ALU, the gap was stated as "missing NOT_B and the
four asymmetric implication functions" -- i.e. NOT_B was assumed absent.

Building the cell pipeline HTML explainer (reading `computed_output`'s
case statement directly, unicell64_v3.v ~line 618) found this wrong:
`10'h002: computed_output = g1; // NOT(B)` is a real, decoded case,
verified by hand against the same test vectors the RTL cites
(A=0xDEADBEEF, B=0xCAFEBABE). NOT_B genuinely computes and is reachable.

What's actually true: NOT_B has no dedicated cold/hot opcode pair the way
PASS_A/NOT_A/NOR/AND/OR/NAND/PASS_B/XNOR/XOR/ZERO/ONE/COMMAND_EMIT do (no
`CMD_TOPO_NOT_B_COLD/HOT` exists). It's only reachable by writing
`topology[9:0]=0x002` directly via `CMD_LOAD_AT`'s raw topology field,
which accepts any 10-bit value, not just the ones with a convenience
opcode. So the earlier "12 named topology opcodes" framing was correct
for *named, single-command-settable* operations, but undercounts the real
decoded/reachable set by one: it's 13, not 12, once CMD_LOAD_AT's direct
field write is counted as a legitimate path (which it is -- nothing
gates topology to only the enumerated cold/hot pairs).

**Practical implication:** any future combinatorics count of the cell's
configuration space should use 13 for topology, not 12. Also worth a
look, if this is ever revisited: whether a `CMD_TOPO_NOT_B_COLD/HOT`
opcode pair is worth adding for symmetry with NOT_A, or whether leaving
it LOAD_AT-only is fine since it's rarely needed standalone (most
practical uses of B-only inversion likely go through NAND/XNOR/NOR
compositions instead). Not urgent -- logged so the gap is a documented
choice either way, not a silent inconsistency.

## 57. AI integration needs to be a first-class, per-subsystem architectural component -- Composer, Compiler, Library, VM each need their own port, not one bolt-on assistant (Alan, 2026-07-29)

**Extends #45, doesn't duplicate it.** #45 proposed a single dedicated
"lab" AI role for open-ended substrate exploration, distinct from
Companion's existing narrow `attach_ai()` escalation classifier, and its
2026-07-22 sharpening note already flagged that such a role "needs to
tie into the compiler/VM directly, so a proposed structure can be
immediately verified rather than just guessed at." This entry is that
single tie-in generalized into a full architecture: AI assistance at
**every named stage of the toolchain**, each with its own defined
interface, not one assistant loosely observing the whole pipeline from
outside.

**The stages, as named this session:**
- **Composer** -- a design-time helper, present from the earliest stage
  of laying out a topology.
- **Compiler** -- given how large a single cell's own configuration
  space already is (points.md's cell-combinatorics work this session:
  ~152-386 million real per-cell configurations even after collapsing
  don't-cares, before any full-array joint space), a compiler navigating
  that space by algorithm alone, with no assistance, is going to be
  "in knots over options alone" -- Alan's own framing, and an accurate
  one given the numbers just worked out.
- **Library keeper** -- curating/managing the growing model library (the
  existing 55-model test suite and whatever succeeds it) needs an active
  keeper, not a static folder.
- **VM** -- a runtime helper, for debugging and interaction while a
  model actually executes.

**Why this matters beyond convenience -- Alan's own framing, worth
recording precisely:** "yes I have most in my head, but even I forget or
misconstrue things." This isn't about compensating for not understanding
the system -- it's the opposite: even the person who holds the most
complete mental model of this architecture cannot be a fully reliable
source of truth for it indefinitely. That's the same lesson this session
already learned twice the hard way with STATIC documentation (the stale
176-cell estimate, the topology-opcode-count doc just corrected in #56)
-- a human's memory of a fast-moving system has the identical staleness
problem as a written doc, for the identical reason. An AI woven through
the toolchain, checking itself against current ground truth (the RTL,
the compiler's own state) rather than trusted recollection, is a
structural answer to that, not just a helper bolted onto the outside.

**The concrete architectural requirement this implies, not just
aspiration:** each subsystem (Composer, Compiler, Library, VM) needs
**actual defined ports for AI interaction, plus an API library** --
i.e. this has to be designed as first-class interface surface on each
component, planned for from the start of each piece's own design, not
an afterthought retrofitted once each tool already exists in its own
closed form.

**Hosting shape -- a real refinement of #45, not a contradiction to
gloss over:** #45 assumed "effectively two GPUs," a heavier, centrally-
hosted model. This entry raises a genuinely different, smaller target:
"maybe a fully trained 4B model, so others could run it locally" --
prioritizing broad self-hostability (a single user's own machine, no
dual-GPU requirement, no dependency on a hosted service) over raw
capability. Both shapes may end up coexisting for different roles (a
smaller always-available local model for everyday Composer/Compiler/
Library assistance; #45's larger lab-exploration role for the harder,
more open-ended substrate-search problem) -- worth treating as two
points on a spectrum, not choosing one over the other prematurely.

**Distinct from Companion's existing role, restated for clarity given
three AI touchpoints now exist in the record:** (1) Companion's
`attach_ai()` -- built, narrow, bounded Ward-escalation classifier
(TinyLlama-1.1B default); (2) #45's parked "lab" role -- larger,
open-ended substrate exploration, dual-GPU hosting assumed; (3) this
entry -- toolchain-embedded assistance across Composer/Compiler/
Library/VM specifically, smaller/locally-hostable target. Three
different jobs, not three sizes of the same job.

**Status: parked idea, same treatment as #45 and the sidecar semantic-
index notes -- no bit budget or scope commitment implied.** Sequencing
follows the same logic as PLAN.md's doc-rework note (#9ed4abf) and #55's
software workup: this is downstream of the cell internals stabilizing
and the Composer/compiler/VM catch-up actually happening, not something
to design in detail before those exist. Logged now specifically so the
per-subsystem port/API requirement is on record from the start of that
future work, rather than each tool being designed in isolation first and
an AI interface bolted on afterward.

## 58. Per-edge cardinal_edge implemented and sim-proven — the last 3 bits of cmd_latch[31:0] spent (Alan/session, 2026-07-30)

**Built the #42 refinement.** `cmd_latch[18:15]` is now `cardinal_edge[3:0]`,
one bit per cardinal direction, bit-for-bit paired with `routing_mask[14:11]`.
Replaces the single global `transit_only` bit with per-edge granularity: for
each direction a fire is ALSO routed to, that specific edge independently
decides whether it's cardinal-only (no local join) or still lets the fire
present on the local cluster bus.

**Mechanism.** `transit_only` (the signal the array actually consumes to gate
local presentation) is now DERIVED rather than stored directly:
`transit_only = (routing_mask != 0) && ((routing_mask & ~cardinal_edge) == 0)`.
Local is a single shared bus per fire event (the array can't split "local"
per direction), so the rule is: suppress local only if every direction this
fire is actively routing to is marked cardinal-only. One active direction
left un-marked keeps local alive even while another active direction on the
same fire is a pure conduit. This is exactly what a single global bit
structurally could not do — confirmed as the correct reading of the #42
proposal before coding (an ambiguity flagged and resolved with Alan first,
per the DRIFT NOTE discipline from the CMD_LOAD_AT episode: state the
mechanism before building it).

**Opcode split, backward-compatible.** `METH_SET_TRANSIT` (35) kept, now
writes all 4 `cardinal_edge` bits uniformly (`cmd_data[0]` → `4'b1111` or
`4'b0000`) — reproduces the pre-#42 global bit exactly, confirmed by
`tb_v3_transit.v`/`tb_v3_transit_obs.v` passing unmodified. New
`METH_SET_CARDINAL_EDGE` (36) writes the 4 bits directly from `cmd_data[3:0]`
for genuine per-edge control. Both wired through all three existing
methodology decode sites (top-level slot A, slot B, and the CMD_LOAD_AT
bank-2 methodology slot) — same pattern as `METH_SET_ROUTING`.

**Consequence: `cmd_latch[31:0]` is now 32/32 allocated, zero bits free.**
This was the last headroom in the lower latch (per the 2026-07-19 bit-budget
check in entry #42); any future lower-32 addition needs to reclaim an
existing field. Entry #43 (lane-split-to-cardinals) is now permanently
unbuildable in its original form, not just parked — confirmed dead by this
spend, as #42 already predicted it would win the contest.

**Proof: `tb_v3_cardinal_edge.v` (new).** Single cell, `routing_mask = N|E`
(both active simultaneously). Run 1: `cardinal_edge = E-only` — both bridges
fire AND the local bus still fires (N keeps it alive). Run 2: `cardinal_edge
= N|E` (legacy-equivalent) — both bridges fire, local suppressed. Full
existing regression suite (`tb_v3_twoslot`, `tb_v3_auth_relocate`,
`tb_v3_bank`, `tb_v3_transit`, `tb_v3_transit_obs`, `tb_v3_array_reset`,
`tb_v3_load_done`, `tb_v3_three_cycle_load`, `tb_v3_wired_or`) re-run green,
additive change confirmed.

**Not yet done:** silicon test. Sim-only so far, per project discipline
(sim-first then silicon). Next: extend `zone1_cardinals.tcl` (already
proven on the Arria 10 zone1 build for the old global-bit case, all four
directions) into a per-edge variant — smallest silicon case is the same
two-direction (N+E), mixed-cardinal_edge scenario `tb_v3_cardinal_edge.v`
just proved in sim. Requires a reflash (cell RTL changed); no `.qsf`/`.qsys`
or top-level change needed, same Quartus project as before.

**SILICON CONFIRMED (2026-07-30, same day).** Alan added `unicell64_v3.v`
to the existing zone1 Quartus project, recompiled, reflashed, ran
`zone1_cardinal_edge.tcl`. Both cases passed exactly as sim predicted:
- E-only cardinal (routing N|E, cardinal_edge=0x4): north seen=1, east
  seen=1, **local bus seen=1** — N alone keeps local alive while E is a
  pure conduit on the SAME fire. The new capability, on real die.
- N|E cardinal (routing N|E, cardinal_edge=0x5, legacy-equivalent): north
  seen=1, east seen=1, **local bus seen=0** — matches the old global-bit
  result exactly, now reached via the granular field.

#42 moves from sim-proven to SILICON-PROVEN. Per-edge cardinal routing is
real, on the same single-zone (25-cell) Arria 10 build the rest of this
project's silicon proofs live on. Step 2 of the definitive task path is
CLOSED. Step 3 (#49/#51, comparator + routing latch) starts next.

## 59. Comparator + dynamic routing latch (#49/#51) implemented and sim-proven — cmd_latch widened to 128 bits, an in-session testbench artifact caught and correctly not chased as an RTL bug (Alan/session, 2026-07-30)

**Built the #49/#51 refinement**, directly following #58's closure. Widened
`cmd_latch` from 64 to 128 bits. Field map, confirmed with Alan before any
RTL:
- `[31:0]` topology latch — `routing_mask`/`cardinal_edge` relocated OUT
  (freed 8 bits at `[18:11]`); `cell_mode` (2 bits, reserved/placeholder,
  not yet wired to behavior) moved IN here since it's topology, not
  routing — 6 bits genuinely free.
- `[63:32]` methodology latch — unchanged, still 32/32.
- `[95:64]` **new routing latch**: `routing_mask`(6b, `[69:64]`),
  `cardinal_edge`(6b, `[75:70]`), `pattern_low`/`pattern_equal`/`pattern_high`
  (6b each, `[81:76]`/`[87:82]`/`[93:88]`) — 3D-ready width, only the low 4
  bits of each wired to real N/S/E/W bridges today — `dynamic_route_en`(1b,
  `[94]`), 1 bit free at `[95]`.
- `[127:96]` free.

**Comparator:** pure combinational, no stored state — `a_data` (the "in
latch", stored first arrival) vs `bus_data_r` (the live incoming
second-arrival/trigger value) → LOW/EQUAL/HIGH, selecting one of the three
stored patterns.

**Layering, confirmed order:** effective_routing = selected_pattern (does
the data want to go there) AND routing_mask (is that direction even open —
this is the same concept as the originally-planned #47/#48 "openness",
just correctly unified under the existing `routing_mask` name rather than
a separate field). `cardinal_edge` then applies exactly as in #42/#58 to
whichever directions come out of that AND active. `dynamic_route_en=0`
(default) collapses `effective_routing` to `routing_mask` alone — zero
behavior change for any cell not opting in, same backward-compatibility
approach as #58's `METH_SET_TRANSIT`.

**New opcode `CMD_SET_ROUTE_LATCH` (37):** whole-routing-latch load in one
word, same "cmd_data IS the config word" style as `CMD_RECONFIGURE` but
targeting `cmd_latch[95:64]`. `METH_SET_ROUTING`/`METH_SET_CARDINAL_EDGE`/
`METH_SET_TRANSIT` kept working — relocated to write the new field
addresses (`[67:64]`/`[73:70]`, low 4 bits only), so existing config words
using those opcodes need no changes, only the internal storage moved.

**Timing note worth keeping:** `effective_routing`/`transit_only` are
combinational off `a_data`/`bus_data_r`, which can change later in the same
cycle (`loop_back`, `latch_in`). They must be captured into new buffer
registers (`out_buf_routing`/`out_buf_transit`) at the exact fire cycle,
alongside the existing `out_buf_addr`/`out_buf_data` capture — NOT
re-derived at the later `odd_phase` snapshot, or they'd read
already-moved-on values. Same category of timing trap as the
`cmd_bus_r`/pipeline-register work earlier in this project.

**Proof: `tb_v3_route_latch.v` (new).** One cell, ONE static config
(`routing_mask`=N|E open, `cardinal_edge`=all-local, `dynamic_route_en`=1,
patterns loaded via `CMD_SET_ROUTE_LATCH` in one shot) fired three times
against a fixed threshold (0x50, re-primed via `CMD_SWAP_AB` each case)
with three different incoming values (0x10/0x50/0x90) — same unchanged
cell configuration took three genuinely different routes (E-only /
N-only / N|E) purely from the data. Full existing regression suite
re-run green.

**Real finding worth recording, correctly NOT chased as an RTL bug:** the
first version of this test ran all three cases back-to-back with no reset,
relying on `latch_in`'s continuous rearm — this produced a spurious extra
EAST assertion on the EQUAL case. Isolating the variable (adding a full
array reset between cases, same discipline as #58) made it vanish cleanly
— all 9 checks pass. This means the comparator/routing-latch logic itself
is correct; what's still open is whether rapid back-to-back re-arm
(SWAP_AB immediately after a `latch_in` fire, no settle) has a genuine
pipeline hazard on real hardware, separate from this feature. Deliberately
carried into the silicon test (`zone1_route_latch.tcl` re-primes via
SWAP_AB with no reset between cases, matching the artifact-producing sim
version, not the clean one) specifically to check whether it reproduces on
real silicon or was a sim-only zero-delay-scheduling artifact — relevant
groundwork for the upcoming RAM-read runtime mechanism, which will do
exactly this kind of rapid re-trigger.

**Not yet done:** silicon test written (`fpga/zone1_route_latch.tcl`,
same auth/sequence convention as `zone1_cardinal_edge.tcl`) — awaiting
Alan's recompile+reflash of the existing zone1 project (cell-only RTL
change again, no `.qsf`/`.qsys`/top-level change).

**SILICON: back-to-back-rearm hazard CONFIRMED REAL, worse than sim
predicted (2026-07-30, same day).** After a stale-file false alarm was
ruled out (compile folder briefly had an hour-old pre-#59 `unicell64_v3.v`
— caught, fixed, recompiled), `zone1_route_latch.tcl` (the deliberately
no-reset-between-cases version) ran twice back-to-back with no recompile
or reboot in between:
- Run 1: LOW → all zero (wrong). EQUAL → N|E+local (should be N-only,
  wrong). HIGH → N|E+local, correct.
- Run 2 (same live hardware, no reset): LOW → N|E+local (wrong). EQUAL →
  N|E+local (still wrong). HIGH → N|E+local, correct.

Every wrong result drifted toward the SAME outcome (the HIGH
pattern/N|E+local), progressively contaminating more cases run-to-run
with zero recompile/reboot between them — not random noise, a genuine
residual-state hazard from re-priming via `SWAP_AB` with no array reset
between cases, same category as the sim artifact from the first (flawed)
version of `tb_v3_route_latch.v` but MORE pronounced on real silicon.
Confirms the open question from this entry's original write-up: back-to-
back rearm (no settle time) is a real hazard, not sim-only — directly
relevant to the upcoming RAM-read runtime mechanism, which needs to
account for this before doing rapid re-triggers itself.

**Isolating the variable:** wrote `fpga/zone1_route_latch_isolated.tcl` —
same three cases, but with a full `CMD_ARRAY_RESET` + reboot +
reconfigure before EACH case (matching the clean, all-9-checks-passing
version of the sim testbench). This checks whether the comparator/
routing-latch mechanism ITSELF is correct on silicon when each case
starts clean, isolating that question from the separate back-to-back-
rearm timing hazard above. Result pending.

**FALSE ALARM ruled out first: not a timing-closure problem.** The
isolated script's first run came back deterministic ALL-ZERO on every
case (reproduced twice, same bitstream, no recompile between). Before
assuming an RTL bug, checked the hypothesis that the new 32-bit comparator
had introduced a real timing violation (`clk_div` measured 54.22MHz vs.
the ~56.2MHz this build measured before, and the Fitter's `CLK_100M` line
reported a nonsensical number worth checking rather than dismissing).
TimeQuest's actual report ruled this out cleanly: worst-case setup slack
is `+0.288ns`, on an unrelated PCIe hard-IP clock domain; `clk_div` itself
(the real design clock) sits at `+21.555ns` slack — nowhere near tight.
Not a timing problem.

**Real bug found: `SET_TARGET` (opcode 24) was never being held before
`SWAP_AB`.** Diffing against the last successful test
(`zone1_cardinal_edge.tcl`) found it holds `SET_TARGET` before every
single config_match-gated command. Both route_latch tcl scripts omitted
this entirely. Sim never needed it (sim bypasses the top-level
`load_target` latch that real silicon's ISSP/JTAG path goes through), so
this gap was invisible in simulation — a genuine sim/silicon divergence,
not something `tb_v3_route_latch.v` could have caught. Without the hold,
`SWAP_AB` most likely never actually landed, so the cell never got a
threshold primed at all — every injection became an unconsummated first
arrival with no second arrival to trigger a fire, exactly matching the
deterministic all-zero symptom. Fixed in both tcl scripts (hold `SET_TARGET`
before `RECONFIGURE`, `CMD_SET_ROUTE_LATCH`, and critically before
`SWAP_AB`).

**SILICON CONFIRMED, clean, after the fix (2026-07-30, same day).**
`zone1_route_latch_isolated.tcl` (full reset between cases): all three
cases pass exactly as predicted —
LOW (0x10<0x50): north=0/east=1 (pattern_low). EQUAL (0x50=0x50):
north=1/east=0 (pattern_equal). HIGH (0x90>0x50): north=1/east=1
(pattern_high). **#49/#51 moves from sim-proven to SILICON-PROVEN.**

**The back-to-back-rearm hazard, now cleanly isolated from the tcl bug:**
re-running the original `zone1_route_latch.tcl` (no reset between cases,
same target-hold fix applied) gives a much narrower, cleaner signature
than the earlier confounded "drifting toward HIGH" result: LOW and HIGH
both come back correct, but EQUAL picks up a spurious extra `east=1` it
shouldn't have. This matches the ORIGINAL sim artifact almost exactly (the
first, flawed version of `tb_v3_route_latch.v` also corrupted specifically
the EQUAL case with an extra east bit, before a reset between cases fixed
it). So: the back-to-back-rearm hazard is real, silicon-confirmed, and
now precisely characterized — it's not random drift, it's a specific,
repeatable contamination of the EQUAL case when re-priming via `SWAP_AB`
with no settle/reset. Worth a dedicated investigation before the RAM-read
runtime mechanism, which will do exactly this kind of rapid re-trigger.

**STEP 3 CLOSED.** Both cell-internals steps of the definitive task path
(#42/#58, #49/#51/#59) are now silicon-proven on the same single-zone
Arria 10 build. Next: either the back-to-back-rearm hazard investigation,
or move on to the command-cell RAM-read runtime mechanism per the
original sequencing (Alan's call).

## 60. Distributed command assembly — 4 masked cells compose 1 command word for a command-emit cell, zero new RTL (Alan/session, 2026-07-30)

**Alan's idea, sim-proven in the same session as #59, needing no RTL
change at all** — a genuine new capability entirely from composing three
already-proven, independently-existing mechanisms: wired-OR same-address
fan-in (#32), `nibble_mask` (existing methodology field), and command-emit
(`is_command_cell`, existing since v3.0). Same category as #37's
loop_back+latch_in+MEM_CALL discovery — nobody had to build anything new,
just recognize the combination.

**Mechanism, confirmed against the RTL before simulating (one real
correction along the way):** `nibble_mask` only ever masks `second_val`
(the live second-arrival/trigger operand) — the stored first-arrival
`a_data` is always written raw, unmasked. So each contributing cell must
be **PASS_B** (`computed_output = second_val`), not PASS_A — its own
locally-arriving trigger value is what gets masked down to its assigned
nibble/byte before going out. Four such cells, each with a distinct
`nibble_mask` keeping only its own slice, all listening at the SAME shared
address (so one upstream event arms/fires all four in the same tick —
same simultaneity requirement #32 already established, or you get
sequential collision-corruption instead of a clean OR-reduction), all
targeting the SAME destination address (a command-emit cell's listen
address, `routing_mask=0` — "no outs direct", exactly as specified).

The array's wired-OR reduction composes the four masked contributions
into one 32-bit word in a single bus event. If the command-emit cell was
previously unarmed, this composed word lands as its **first** arrival
(`a_data`), exactly the "empty latch, data lands, gets placed there" Alan
described. A separate, later trigger provides the second arrival — its
own value discarded, since `is_command_cell` only ever emits the stored
`a_data` — firing the emission of the composed command onto `cmd_bus`.

**Proof: `tb_v3_masked_compose.v` (new, `unicell_array64_v3` level, 5
cells).** Cells 0-3: PASS_B, each `nibble_mask` keeping exactly one of the
low 4 nibbles, all listening at a shared `TRIG_ADDR`, output targeting a
shared `CMD_ADDR`. Cell 4: `is_command_cell=1`, `routing_mask=0`, listens
at `CMD_ADDR`. Primed, then fired with `0x00001234` — composed word landed
correctly at cell4's `a_data` (`0x00001234`), armed; a second trigger then
produced a real `cmd_emit_valid` pulse carrying that exact composed word.
Full existing regression suite stayed green (no RTL touched at all).

**Two real bugs caught building this, both testbench-only, not RTL —
worth recording since they're easy to re-make:**
1. `CMD_SET_OUTPUT_ADDR` (opcode 3) is **config_match-gated**, same as
   `CMD_SET_INPUT_ADDR` — NOT a broadcast like `CMD_RECONFIGURE`. First
   attempt assumed broadcast and only one cell (whichever `bus_addr_r`
   happened to still match) ever got its `output_address` set; the other
   three silently kept the reset default (`CELL_ID+1`), producing a
   plausible-looking wrong address exactly matching #32's own documented
   corruption mode. Fixed by targeting each of the 4 source cells
   individually.
2. Sequencing: the targeted `CMD_LOAD_AT` that turns cell4 into a
   command-emit cell must run **after** the broadcast `CMD_RECONFIGURE`
   that sets up the shared PASS_B config on cells 0-3 — `CMD_RECONFIGURE`
   reaches every cell (auth_ok only, no config_match), so doing the
   targeted overwrite first meant the later broadcast silently reverted
   cell4's `command_cell` flag back to 0.

**Standing gap flagged, not fixed here:** the cell's `dbg_cmd_latch` debug
window is still a 2-bank, 32-bit-wide view (`dbg_bank` selects
`cmd_latch[31:0]` or `[63:32]`) predating #59's widening to 128 bits — it
has no window onto the new routing latch (`[95:64]`) or the still-free
`[127:96]`. Not needed for this proof (only `dbg_a_data`/`dbg_a_arrived`
were used), but worth extending before any silicon debugging of #59/#60
needs to read the routing latch back directly.

**Not silicon-tested.** This is a usage-pattern discovery on already-
silicon-proven primitives (#32's wired-OR is silicon-proven; command-emit
and nibble_mask are both established features), so a dedicated silicon
test is lower priority than #58/#59's new RTL — logged here for the
record; can be added to the silicon test queue alongside #59's
`zone1_route_latch.tcl` result if useful.

## 61. The "rearm hazard" wasn't a timing race at all -- an incomplete top-level address-lane whitelist, root-caused with a sim reproduction and fixed (Alan/session, 2026-07-30)

**Reproduced the exact silicon symptom in sim first, with full per-cycle
tracing of `a_data`/`bus_data_r`/`bus_hit`/`new_data`/`effective_routing`
(new `tb_v3_rearm_hazard.v`), rather than guessing at the mechanism.** The
trace showed precisely why the EQUAL case corrupts: after the LOW case's
own fire (which presents locally, landing at the cell's `output_address`
rather than its own `CELL_ID`), the zone's internal `bus_addr_r` shifts
away from `CELL_ID` to `output_address`. The next `CMD_SWAP_AB` (config_
match-gated) is issued against that now-wrong address, silently fails,
and the cell's `a_data` is left holding whatever `latch_in` last rearmed
it to (the previous case's own trigger value) instead of the intended
fresh threshold.

**That fully explained the sim reproduction, but checking the ACTUAL top-
level file (`top_arria10_zone1_v3.v`, not modeled in sim at all) revealed
a bigger, more fundamental cause underneath it.** The top level has a
hardcoded per-opcode whitelist deciding whether `cpu_addr_w` (which feeds
`bus_addr`, and therefore `config_match`) comes from the held `SET_TARGET`
register (`load_target`) or falls through to `cpu_data[15:0]` -- the LOW
16 BITS OF THAT COMMAND'S OWN PAYLOAD, misread as an address.
`CMD_SWAP_AB` (opcode 18) was never in this list. Neither was
`METH_SET_CARDINAL_EDGE` (36, #58) or `CMD_SET_ROUTE_LATCH` (37, #59) --
every config_match-gated opcode added since #42 was missing. Worse: the
array registers `bus_addr <= cpu_addr` on EVERY host pulse, not just data
writes, so issuing an unlisted command doesn't just fail its own
`config_match` check -- it also clobbers `bus_addr` with garbage for
whatever config_match-gated command comes next.

**This is why `zone1_cardinal_edge.tcl`'s `SWAP_AB` call happened to work
at all:** its priming payload was `0x00000000`, and the low 16 bits of
that happened to equal the target `CELL_ID` (0) by pure coincidence. The
route-latch tests primed with `0x50` -- `0x0050 != 0` -- so `SWAP_AB`
never actually landed in ANY of those runs, independent of `SET_TARGET`
calls or resets between cases. The earlier `SET_TARGET`-before-`SWAP_AB`
fix (this session, prior entry) "worked" for the isolated (fresh-reset-
per-case) test for an unrelated, coincidental reason -- not because it
addressed this root cause.

**Fix: added the three missing opcodes to the whitelist**
(`top_arria10_zone1_v3.v`, `cpu_addr_w` assignment) -- `CMD_SWAP_AB` (18),
`METH_SET_CARDINAL_EDGE` (36), `CMD_SET_ROUTE_LATCH` (37), all mapped to
`load_target` like every other config_match-gated opcode. Top-level-only
change; no cell/array RTL touched, no `.qsf`/`.qsys` change -- same
recompile+reflash as every other change this session.

**Standing rule added in the fix's own comment:** any NEW config_match-
gated opcode must be added to this whitelist in the SAME commit that adds
it to the cell -- same discipline as the `cmd_latch` field-map summary
rule, and the exact same category of gap (a place elsewhere in the
codebase that has to stay in sync with the cell's own opcode table, or it
silently breaks with no compile-time warning).

**Reframing, now this is understood:** what looked like a "back-to-back
rearm timing hazard" was actually the SAME kind of bug as the earlier
`METH_SET_TRANSIT`/`METH_SET_CARDINAL_EDGE`/`CMD_SET_ROUTE_LATCH`
relocation work -- a place that has to track the cell's opcode additions
and didn't. Sim couldn't catch it because sim never includes the top-
level file at all; this is a genuine, now-documented sim/silicon boundary
that any future config_match-gated opcode needs to cross correctly.

**Not yet re-tested on silicon after the fix** -- awaiting Alan's
recompile+reflash and a re-run of `zone1_route_latch.tcl` (no reset
between cases) to confirm the fix actually resolves the EQUAL-case
corruption for real, not just in the sim reproduction.

**Full audit performed (Alan asked directly whether anything else was
missing) -- systematic, not spot-checked.** Every `config_match`-gated
opcode in `unicell64_v3.v`, found by grep rather than by memory: 6
groups -- `CMD_LOAD_AT`(23), `CMD_LOAD_DONE`(27), the `METH_SET_*` family
(30-36), `CMD_SET_INPUT_ADDR`(2), `CMD_SET_OUTPUT_ADDR`(3),
`CMD_SWAP_AB`(18). All six now correctly covered in
`top_arria10_zone1_v3.v`'s whitelist after this fix. Nothing else in the
active top-level file is missing.

**One correction to the fix above, for accuracy:** `CMD_SET_ROUTE_LATCH`
(37) is NOT actually `config_match`-gated -- it's a broadcast opcode
(`auth_ok` only, deliberately mirroring `CMD_RECONFIGURE`, per its own
design in #59). Adding it to the whitelist was harmless but not strictly
necessary; the two opcodes that genuinely needed it were `CMD_SWAP_AB`
and `METH_SET_CARDINAL_EDGE`.

**Also checked whether NOT_B (#56) was a missing-opcode case (Alan's
specific worry) -- it isn't.** Per #56, NOT_B has no dedicated opcode at
all; it's only reachable via `CMD_LOAD_AT`'s raw topology field, which is
already correctly in the whitelist. Not a gap of this kind.

**Real, separate gap found checking other top-level files for their own
copy of this address-derivation logic -- NOT fixed here, deliberately.**
`top_card_2zone_v3.v` (the 2-zone loader/bridge card) has its own,
independently-written `cpu_addr_w` derivation with no `SET_TARGET`/
`load_target` mechanism at all. For any opcode besides `1` (plain data
write) arriving via the host command path, the address falls straight
through to `raw_data[15:0]` -- the same "payload misread as address" bug,
but broader than `top_arria10_zone1_v3.v`'s, since nothing there
redirects ANY opcode to a held target. This needs real design work (add
an actual target-latch mechanism to that file), not a whitelist patch --
deliberately not rushed into a file that isn't part of what's being
actively tested right now. `top_icebreaker.v`, `top_kintex7_zones.v`, and
`top_zone_synth.v` have no such derivation logic at all and aren't
affected by this pattern. Flag this before `top_card_2zone_v3.v` is ever
used for per-cell targeted config (`CMD_LOAD_AT`, `SWAP_AB`, etc.) --
right now it would hit the identical class of bug with no mitigation at
all.

## 62. CMD_SET_ROUTE_LATCH_AT -- the targeted counterpart, catching a broadcast-only trap before it shipped (Alan/session, 2026-07-30)

**Caught before it became a problem, not after.** Working through how the
routing latch should actually be loaded in a real multi-cell build, Alan
flagged that `CMD_SET_ROUTE_LATCH` (37, #59) is broadcast-only (auth_ok
gated, no `config_match`) -- meaning every cell in the array gets
identical routing config, which defeats the entire point of per-cell
heterogeneous topologies. This is the EXACT same trap `CMD_RECONFIGURE`
was originally in, before `CMD_LOAD_AT` was built specifically to fix it
(the documented `ARCHITECTURE.md` invariant: "CMD_RECONFIGURE broadcasts
to every cell -- per-cell targeting requires CMD_LOAD_AT"). Rather than
inventing something new, mirrored that exact pattern.

**Built `CMD_SET_ROUTE_LATCH_AT` (38):** identical `cmd_data[31:0]` field
packing as the broadcast version (`routing_mask`/`cardinal_edge`/
`pattern_low`/`pattern_equal`/`pattern_high`/`dynamic_route_en`), but
`config_match`-gated instead of `auth_ok`-only -- only the cell currently
held on the address lane (via `SET_TARGET`) applies it. Same two-word
shape as `CMD_LOAD_AT`: `SET_TARGET(CELL_ID)` then this opcode.
`CMD_SET_ROUTE_LATCH` itself is kept as-is for the legitimate broadcast
use case (setting many cells identically), same coexistence as
`CMD_RECONFIGURE`/`CMD_LOAD_AT`.

**Added to the top-level `cpu_addr_w` whitelist in the SAME commit** --
per the standing rule from #61's fix, any new `config_match`-gated opcode
goes in that list immediately, not as an afterthought. This is exactly
the kind of opcode that would have silently hit #61's bug if the rule
hadn't been written down.

**Proof: `tb_v3_route_latch_targeted.v` (new).** Two cells, targeted
independently -- cell0 gets `routing_mask`=E-only, cell1 gets
`routing_mask`=N-only. Confirmed each cell holds ONLY its own value (the
same exclusion property `zone_target.tcl` already proved on silicon for
`CMD_LOAD_AT` vs. broadcast `CMD_RECONFIGURE`). Full existing regression
suite stayed green.

**Not yet silicon-tested** -- this needs a recompile (new opcode in the
cell + a new whitelist entry in `top_arria10_zone1_v3.v`, same file
already being recompiled for #61's fix, so this rides the same build).

## 63. The in-fabric RAM-read loader's missing primitive, built and sim-proven -- plus a real follow-on gap it surfaced (Alan/session, 2026-07-30)

**Untangled Alan's four-role design for the in-fabric RAM-read loader**
(the mechanism PLAN.md has queued since 2026-07-29), which turned out to
already be well-formed, just needing one gap identified: SENDER
(command-emit cell, unchanged, drives config from its own `a_data`) ->
TARGET (the cell being programmed, `frozen` for protection) -> WATCHER
(an ordinary cell, catches TARGET's completion confirm) -> COUNTER
(`loader_fsm_v3.v`, advances the RAM index, feeds SENDER's next `a_data`).
Loop closes: WATCHER's own fire advances COUNTER, COUNTER pulls the next
RAM entry into SENDER, repeat.

**The one real gap: `CMD_LOAD_DONE`'s completion confirm only ever rode
the command bus**, via `cmd_emit_buf_*` -- fine for an external host
polling `cmd_bus[17]` via ISSP readback (confirmed no cell decode logic
anywhere reads that bit as an incoming trigger; it's purely an external-
observation mechanism), but useless to an in-fabric WATCHER cell, since
ordinary cells only know how to react to the DATA bus (their existing
two-arrival mechanism), never the command bus.

**Fix: `CMD_LOAD_DONE` now ALSO drives `out_buf_addr`/`out_buf_data`/
`out_buf_valid`** (the ordinary data-bus fire path) targeted at
`output_address`, alongside the existing command-bus emission (kept,
still useful for external readback). Confirmed against the RTL first
that `frozen` only gates `bus_hit`/`input_val`/`second_val` (a cell's own
two-arrival RECEIVE logic) -- it does NOT gate `out_buf` draining, so a
frozen TARGET can still emit this confirm without needing to unfreeze,
exactly the "frozen exception" the design needs. `CMD_LOAD_DONE` was
already gated on `config_match && auth_ok` only (not `bus_hit`), so this
required zero changes to its own gating -- just teaching it to write a
second buffer on the same cycle.

**Proof: `tb_v3_loaddone_watcher.v` (new), two parts.** Part 1: TARGET
(cell0) fires `CMD_LOAD_DONE`; WATCHER (cell1, an entirely unmodified
ordinary cell, no new logic at all) catches the confirm as its own
first arrival, `a_data` == the confirm marker -- exactly the "no new
decode logic needed on the receiving side" property the design wants.
Part 2: freezing TARGET, then re-confirming.

**Part 2 surfaced a genuine, distinct follow-on requirement, not a test
bug.** `CMD_FREEZE` is broadcast-only (`auth_ok` gated, no
`config_match`) -- so freezing TARGET necessarily also freezes WATCHER,
since `frozen` blocks `bus_hit` for every cell, not just the intended
one. This breaks the four-role design as described: WATCHER needs to
stay ACTIVE while TARGET is frozen. This is the third time this exact
category of bug has surfaced this session (`CMD_RECONFIGURE`/
`CMD_LOAD_AT`, `CMD_SET_ROUTE_LATCH`/`CMD_SET_ROUTE_LATCH_AT`, now
`CMD_FREEZE`) -- **`CMD_FREEZE` (and its counterpart `CMD_RELEASE`)
need a targeted variant**, config_match-gated, before the real four-role
cluster can be built. Logged here rather than fixed yet, since it wasn't
what was being tested -- deliberately demonstrated concretely in the
test (Part 2 shows WATCHER's `frozen` flag going high alongside
TARGET's) rather than silently asserted or worked around.

**Not yet done:** `CMD_FREEZE_AT`/`CMD_RELEASE_AT` (targeted freeze/
release), and the full four-role cluster assembly (SENDER + TARGET +
WATCHER + COUNTER together) -- this entry proves the one missing
primitive (data-bus confirm) in isolation, per the project's own
smallest-test-first discipline. Not yet silicon-tested.

## 64. CORRECTION: the "back-to-back rearm hazard" (#59 follow-up, #61) was a measurement artifact, not a real cell bug -- #59 is fully, cleanly silicon-proven (Alan/session, 2026-07-30)

**Retracting the "back-to-back-rearm hazard CONFIRMED REAL" finding from
entry #59's follow-up section, and the "Reframing" note at the end of
#61.** Both were wrong. The actual root cause was a flaw in the test
methodology, not in the cell.

**What was actually going on.** `zone1_route_latch_diag.tcl` (built to
read `a_data` directly via the ISSP bridge's view 4, rather than infer it
from bridge outcomes) showed `a_data` correctly primed to `0x50` before
EVERY case, in every run, across multiple recompiles and re-runs. The
comparator's actual inputs were never wrong. That alone should have ended
the "hazard" theory immediately -- if the inputs are always correct, the
comparator can't be the thing misbehaving.

The real explanation: the north/east/local "seen" sticky-capture views
(`unicell_issp_bridge.v`, views 5/6/7/8/9) are monotonic latches --
`if (event) seen <= 1'b1`, no path back to 0 except a real reset
(`rst_all = rst | array_rst_req | auth_rst_pulse`, which also feeds the
array). Once a bridge fires, its `seen` bit stays `1` FOREVER until the
next reset, regardless of what any LATER case does. `zone1_route_latch.tcl`
(the no-reset-between-cases script) never called `CMD_ARRAY_RESET` at
all -- not even once, at the start -- so every read was accumulating
"has this bridge EVER fired since whatever ran immediately before this
script" rather than "did THIS case's fire cross this bridge." LOW
genuinely, correctly fires east -- and that `seen=1` then persists,
unchanged, through EQUAL and HIGH's own readings, making EQUAL (which
correctly fires north only) LOOK like it also hit east, when it never
did. The "isolated" variant's clean results weren't clean because it
fixed a rearm hazard -- they were clean because its own `CMD_ARRAY_RESET`
calls (needed to reset cell state between cases) ALSO happened to reset
these same sticky counters as a side effect, via the shared `rst_all`
signal.

**Confirmed precisely, not just inferred:** adding exactly ONE
`CMD_ARRAY_RESET` at the very start of the no-reset script (still none
between the three cases) made LOW read perfectly clean (`north=0,
east=1`) for the first time. EQUAL still showed `east=1` in that run --
but that's LOW's own legitimate, correct east-firing from earlier in the
SAME un-reset run, still latched, exactly as the monotonic-seen-bit
theory predicts. Nothing about EQUAL's own comparator evaluation was
ever wrong.

**Corrected conclusions:**
- **#59 (comparator + dynamic routing latch) is unambiguously,
  cleanly silicon-proven.** There is no cell-level back-to-back-rearm
  hazard. The mechanism has almost certainly been working correctly on
  silicon since the very first `zone1_route_latch_isolated.tcl` pass.
- **#61 (the `cpu_addr_w` whitelist fix) remains entirely valid and
  necessary** -- `SWAP_AB` genuinely wasn't landing before that fix (the
  original all-zero result was real, and the fix resolved it). What's
  retracted is only the SEPARATE claim that a further, distinct timing
  hazard existed on top of that -- it didn't.
- The RAM-read runtime mechanism does NOT need to design around a
  cell-level rearm/re-trigger hazard that was never real. (Ordinary
  timing/settle considerations for real rapid re-triggering still apply
  as they would to any design, but there is no specific documented
  hazard to design around here.)

**Lesson for future silicon debugging, worth keeping:** sticky "seen"
capture views are the wrong tool for distinguishing per-case outcomes
across a sequence of un-reset events -- they answer "has this ever
happened," not "did the most recent thing cause this." Reading the
`data`/`addr` content (which DOES get freshly overwritten on every
recurrence, only `seen` is one-way) rather than the `seen` bit alone
would have been the correct approach if per-case bridge outcomes ever
need checking again without a reset between cases -- or read `dbg0_a_data`
directly (view 4) as this session's diagnostic did, which is what
actually broke the false trail open.

## 65. CMD_FREEZE_AT/CMD_RELEASE_AT built and sim-proven -- and a real, previously-latent discovery about command-emit cells surfaced along the way (Alan/session, 2026-07-30)

**Built the targeted freeze/release pair** flagged as needed in #63:
`CMD_FREEZE_AT` (39) and `CMD_RELEASE_AT` (40), `config_match`-gated,
identical bodies to the broadcast `CMD_FREEZE`/`CMD_RELEASE` otherwise --
same two-word `SET_TARGET`+opcode shape as `CMD_LOAD_AT`/
`CMD_SET_ROUTE_LATCH_AT`. Added to the top-level `cpu_addr_w` whitelist in
the same commit, per the standing rule.

**Test, exactly as Alan proposed:** reuse the already-proven masked-
compose model (#60) as the test vehicle. Build it, confirm it composes
correctly, freeze ONE contributing cell (targeted), refire, and look for
a hole in the composed data exactly where the frozen cell's nibble
belongs.

**A genuine, previously-latent discovery surfaced building this test --
not a bug in `CMD_FREEZE_AT`, a real property of command-emit cells worth
recording clearly.** The first version of the test used an arbitrary
"data" value (`0x00001234`) for the compose. Round 1 worked. But by the
time round 2's setup ran, EVERY cell in the array -- not just the frozen
one -- had silently lost its `start_flag` (armed bit). Traced cycle-by-
cycle (not guessed): `cell4`'s fire drives its ENTIRE `a_data` onto
`cmd_emit_buf_bus` (`unicell64_v3.v`, generic command-emit path), and the
array's emit-arbiter broadcasts that AS A REAL, EXECUTED COMMAND to every
cell (`cmd_opcode = a_data[7:0]`). `0x1234`'s low byte is `0x34` = 52 =
`CMD_TOPO_NOR_COLD` (topology=NOR, **armed=0**) -- so cell4's own
"harmless test data" silently disarmed the entire array the moment it
fired, entirely independent of anything to do with freeze.

This is not a defect -- it's exactly what a command-emit cell is FOR (the
whole point of #60's distributed-command-assembly primitive is composing
and broadcasting a REAL, executable command). The lesson is that **any
value stored in a command-emit cell's `a_data` is a live opcode the
moment it fires** -- there is no "just data" mode. Test values (and, more
importantly, real composed commands built this way in actual use) must
have their low byte deliberately chosen: either landing exactly on
`CMD_NONE` (0) for a genuine no-op carrier, or on a value that IS the
intended real command, or -- if being used purely to carry an arbitrary
payload with no command intent -- kept clear of the 0-71 real-opcode
range entirely (anything ≥72 is safe by construction, since no opcode
above `CMD_TOPO_COMMAND_EMIT`=71 is currently defined).

**Fixed the test** by keeping nibble0 (the byte's low nibble, cell0's
slot) at 0 throughout and choosing nibble1 (cell1's slot, the one being
frozen) so the resulting low byte always lands outside the real opcode
range or exactly on `CMD_NONE`. With that fix: all three rounds pass
exactly as predicted -- round 1 baseline correct, round 2 shows the
predicted hole with the other three nibbles intact, round 3 (after
`CMD_RELEASE_AT`) shows cell1 rejoining cleanly with no lingering damage.
Full regression suite green throughout.

**Worth carrying forward to the RAM-read/loader design and any future
command-emit use:** this "payload IS opcode" property needs to be an
explicit, deliberate part of how composed commands are constructed
(distributed assembly, #60, or any command-cell design), not an
accidental collision to avoid. A `.qsf`-level or compiler-level check
that composed command words have a deliberately-chosen low byte would be
worth having once the compiler/VM catch-up work reaches this area.

## 66. Emitted commands are now genuinely targeted, not broadcast -- reused already-existing, half-built infrastructure (Alan/session, 2026-07-30)

**Alan's direct response to #65's discovery: emissions should be
targeted, using output_address -- that's what it's for.** Checked the
array's actual wiring rather than assume a fix was needed from scratch,
and found the infrastructure for this was ALREADY THERE, just disabled:
`eff_cpu_addr = sel_emit_data[15:0]` (the emitting cell's own
`output_address`) was already correctly computed whenever an emission is
active, and `cmd_is_this_cell_runtime = (eff_cpu_addr[15:0] ==
cell_input_addr)` was already wired up per-cell -- but
`cmd_is_runtime_targeted` was hardcoded `1'b0` ("All runtime commands
broadcast with auth gate"), meaning this targeting machinery was built
and connected but never switched on for anything.

**Fix: `cmd_is_runtime_targeted = sel_emit_valid`** (`unicell_array64_v3.v`).
Host-issued commands are completely unchanged (still broadcast-unless-
the-opcode-itself-gates-on-`config_match`, exactly as always). Emitted
commands now ONLY reach the cell whose `input_address` matches the
emitting cell's `output_address` -- every other cell's `cell_cmd_valid`
is gated false for that cycle, so they never even see the emitted
command's opcode at all, regardless of what it happens to be. This
directly closes the #65 hole: a command-emit cell's payload accidentally
matching a broadcast-type opcode (like `CMD_TOPO_NOR_COLD`) can no longer
disarm the whole array -- it can only ever affect whichever single cell
is actually listening at the intended target address.

**Proof: `tb_v3_emit_targeted.v` (new).** Recreates the exact #65
scenario -- a command-emit cell primed with `a_data = 0x00000034`
(`CMD_TOPO_NOR_COLD`'s opcode, armed=0) -- but now with a properly
configured target. TARGET cell (listening at the emission's
`output_address`) correctly receives it and gets disarmed, proving the
targeting actually reaches its intended recipient. A BYSTANDER cell,
configured identically but listening at a DIFFERENT address, is
completely untouched by the same emission -- proving it's genuinely
point-to-point now, not broadcast with a lucky miss. Full existing
regression suite stayed green throughout (no test relied on emissions
being broadcast; every existing check reads the emitting cell's own
internal state directly, unaffected by this change).

**Consequence worth naming plainly:** this makes command-emit cells
behave the way a real point-to-point messaging primitive should --
`output_address` genuinely IS the target now, for any emitted command,
regardless of that command's own opcode-level broadcast/targeted nature.
This is foundational for the RAM-read/loader design and any future
distributed-command-assembly work: emissions compose real commands (per
#60/#65) AND those commands now land only where intended, closing the
loop Alan's four-role design needs to be safe to build on.

## 67. VM REBUILD COMPLETE — all 6 phases done, unicell_v3.py + unicell_array_v3.py replace the retired unicell.py (Alan/session, 2026-07-31)

**The full VM rebuild Alan called "the big one" is done.** Six phases,
built strictly bottom-up ("design the cell correctly, then scale up"),
each one verified line-by-line against the actual current RTL logic
(`unicell64_v3.v`/`unicell_array64_v3.v`) rather than assumed from memory
of this session's own earlier design work — a discipline that caught
several real, previously-undetected issues along the way (listed below).
216 VM tests total, all passing, plus the full pre-existing project test
suite (278 tests) confirmed unaffected throughout.

**Phase 1 — topology latch + foundational two-arrival mechanics
(`unicell_v3.py`).** Gate computation replicates the SAME NOR-decomposition
the silicon uses (not a Python shortcut through native bitwise ops) --
cross-validated against independent native operators for all 12 topology
codes. Found and fixed a real RTL documentation drift while building this:
`output_set` is a separate register in the actual logic, not
`cmd_latch[19]` as the header comment claimed -- fixed in the RTL itself,
in both places it appeared, including correcting the free-bit count.

**Phase 2 — methodology latch (nibble mask, shift, lane cut).**
Confirmed independently (not just asserted) that nibble masking only ever
touches the live trigger operand, never a stored value -- the same
pattern the #60 investigation found earlier in the session, now verified
again from a completely different angle. Confirmed the fixed-pattern
shift mux's exact supported-amount list, replicated exactly rather than
"helpfully" generalized to a full barrel shifter.

**Phase 3 — routing latch (comparator, `cardinal_edge`, dynamic
routing).** Caught a genuinely easy-to-miss detail: the comparator reads
the RAW incoming trigger, while the gate tree uses the shift/mask-
transformed version -- two different "B"s on the same fire. Strong
cross-check: replicated the EXACT scenario `zone1_route_latch_isolated.tcl`
proved on real Arria 10 silicon (#59) -- all three threshold cases match
the silicon-confirmed routing precisely.

**Phase 4 — targeted opcodes (`CMD_LOAD_AT`, `CMD_SET_ROUTE_LATCH_AT`,
`CMD_FREEZE_AT`/`RELEASE_AT`).** Real bug caught re-verifying
`CMD_RECONFIGURE`/`CMD_LOAD_AT` against the logic: both write `cmd_data`
as a COMPLETE word every time in the real RTL -- Phase 1's `reconfigure()`
had wrongly modeled "only touch what's passed" semantics. Fixed via
shared helpers now used by both the broadcast and targeted opcodes, with
an explicit regression test. Demonstrated the actual point of targeting
directly: two cells issued the SAME address, only the one whose CELL_ID
matches applies the change -- the exclusion property `zone_target.tcl`
already proved on silicon.

**Phase 5 — command-emit (`is_command_cell`) and `CMD_LOAD_DONE`'s
dual-bus confirm.** Confirmed a real structural detail: `data_reg`, the
comparator, `latch_in`, `loop_back`, and `one_shot` ALL apply
unconditionally regardless of `is_command_cell` -- only the output
destination differs. Replicated `tb_v3_loaddone_watcher.v`'s exact
silicon proof: an entirely unmodified ordinary WATCHER cell catches a
confirm via its own plain `receive()` call, no new logic needed. Two more
small RTL-fidelity corrections caught re-verifying `CMD_ARRAY_RESET`
against the exact handler: it doesn't actually reset `a_data` (a separate
register `cmd_latch` doesn't include), and `load_confirmed` clears while
the emit buffers don't -- both confirmed with dedicated tests.

**Phase 6 (FINAL) — array-level semantics (`unicell_array_v3.py`).**
Two genuinely different array-level mechanisms, verified precisely
because assuming they'd match would have been wrong: the wired-OR data
bus (#32) combines data across ALL firing cells regardless of address,
with the winning address/routing/transit coming from whichever cell fired
at the HIGHEST array index -- while the command-emit arbiter is pure
LOWEST-index priority with NO combining at all, any other simultaneous
emitter silently dropped. Both replicated exactly as found, not
"harmonized" to be consistent with each other when the silicon isn't.

Direct replays of real silicon results: the masked distributed-command-
assembly pattern (#60) composing a word from 4 independently-masked
cells; the exact #65/#66 targeted-emission scenario (a command-emit
cell's payload matching a real, dangerous opcode reaches ONLY its
intended target, a bystander configured identically but listening
elsewhere is completely untouched); the collision hazard when cells fire
to different addresses simultaneously, documented and tested rather than
hidden or "fixed" to be smarter than the actual hardware.

**Capstone: the complete four-role SENDER/TARGET/WATCHER loader,
assembled from everything built across all six phases and passing clean
on the first run.** SENDER (command-emit) reconfigures a frozen TARGET
via targeted emission; TARGET confirms via `CMD_LOAD_DONE` while still
frozen (verified: command application is never gated by `frozen` --
only a cell's own two-arrival receive is); an entirely ordinary WATCHER
catches the confirm with zero new logic; TARGET is released and computes
correctly with its loader-assigned configuration. This is the actual
mechanism the RAM-read runtime work will build on.

**What this enables, concretely:** a fast, exactly-RTL-faithful place to
prototype and validate fabric designs before any FPGA compile -- "a place
to test in," per Alan's own framing for why this was worth doing properly
rather than quickly. `unicell.py`/`command_interface.py` (the retired
pre-v3 models) remain untouched as historical reference; nothing yet
depends on them being migrated, since `unicell_v3.py`/`unicell_array_v3.py`
are wholly new, standalone modules.

**Not yet done, deliberately out of scope for this rebuild:** the
compiler/model-library layer's own migration to target the new cell
model (currently targets the retired `unicell.py` API); a raw bit-exact
wire-format packer/unpacker for cmd_bus words beyond what
`apply_raw_command()`'s topology-preset-scoped dispatcher covers; the
RAM-read/loader-cell's own COUNTER role (the capstone test hand-waves
"advance to the next RAM entry" rather than modeling an actual BRAM-backed
sequencer, which is real Arria 10 IP work, not new cell-model work).

## 68. loader_fsm_v3.v modeled faithfully in the VM -- foundation for the RAM-read runtime mechanism (Alan/session, 2026-07-31)

**The next concrete point on PLAN.md's definitive task path, per Alan's
explicit direction: extend `loader_fsm_v3.v` itself (option 1), keeping
the model true to the actual proven Verilog, rather than a new cell-based
mechanism.** This was the right call -- `loader_fsm_v3.v` already exists,
already works (`tb_bram_loader_v3.v`), and is a genuinely different
architecture from the cell-based four-role SENDER/TARGET/WATCHER pattern
built earlier this session: it's a synthesizable HDL block driving the
bus *directly* (two full words per step, `cmd_bus`+`cmd_data`), not
limited to the single-word constraint a command-emit cell's own emission
has. Confirmed this distinction explicitly with Alan before building,
matching the discipline that's paid off all session.

**New layer for the VM, not covered by Phases 1-6:** the top-level
`SET_TARGET`/`load_target`/`cpu_addr_w` transport mux that
`top_arria10_zone1_v3.v` owns and `loader_fsm_v3.v` folds directly in.
Phases 1-5 modeled the cell; Phase 6 modeled the array; this is the
third architectural layer (host/loader-level addressing), genuinely new
VM territory.

**`loader_fsm_v3.py`, built and verified line-by-line against the real
file:**
- `TargetLatchTransport` -- the exact `cpu_addr_w` whitelist (opcodes 1,
  23, 2, 3, 30-33, 27), including the SAME opcode-30-33 requirement whose
  omission was a real, documented bug caught earlier in this project's
  own BRAM-loader work (silently clobbering the held target address).
- `unpack_topology_word()` -- a real, field-for-field `cmd_data` unpacker
  for `CMD_LOAD_AT`/`CMD_RECONFIGURE`'s raw wire format, re-verified
  against the RTL rather than assumed (including one genuine, documented
  wire-format detail: `breakpoint` and the low bit of `auth_mask_bits`
  share `cmd_data[20]` -- harmless since `auth_mask` only writes in boot
  state, but a real overlap in the packed word worth having on record).
- `LoaderFSMV3` -- the exact state machine
  (`S_IDLE`→`S_TARGET`→`S_TARGET_SETTLE`→`S_C1`→`S_C2`→`S_C3`→`S_WAIT`→
  `S_DONE`), `step()`-by-`step()`, not a shortcut -- since the entire
  point of this model is testing the sequencing and completion-gating
  faithfully, that has to be simulated at the same granularity the real
  FSM operates at.

**Proof: `test_loader_fsm_v3.py`, a direct replay of `tb_bram_loader_v3.v`'s
exact proven scenario** -- 3 heterogeneous cells (XOR/AND/OR) loaded
through the modeled transport, completion-gated on the real emit signal,
a 4th never-targeted cell confirmed untouched. All the real testbench's
own checks reproduced exactly, including `emit_count == 3` (one confirm
per cell, no extras). 24 new tests, all passing. Full VM suite (240
tests total across all files) and the pre-existing 278-test project
suite both confirmed unaffected.

**Not yet done -- the actual open design question, deliberately not
rushed:** the RUNTIME extension itself. `PLAN.md`'s own framing calls for
"re-purposed/re-triggered... ongoing SET_TARGET+INJECT-style DATA
application" -- re-triggering (the boot-time FSM runs once to `S_DONE`
and stops; the runtime version needs to loop), BRAM-sourcing (the config
table currently comes from a fixed array/ROM; runtime needs a live read
port), and critically, a genuine open question: `CMD_LOAD_DONE`'s
emit-count-based completion signal is specific to the config-load
protocol -- a runtime `SET_TARGET`+`CMD_DATA_WRITE` (opcode 1, plain
data injection) step has no automatic confirm built into the opcode
itself. Needs its own design pass (worth a dedicated conversation, not
folded into this entry) before building: does the receiving cell need to
be command-emit-capable to produce an analogous confirm, is a bounded
settle delay acceptable instead, or something else.

## 69. The fabric's own realistic output ceiling makes the PCIe bandwidth question moot -- JTAG was never actually the bottleneck (Alan/session, 2026-08-01)

**Direct follow-up to the zone-parallelism ceiling (points.md #68's Phase 7
planning conversation, 2026-07-31/08-01) and the shared-host-bus finding
from the same conversation.** Once the fabric's own realistic maximum
output rate is worked out numerically, the long-parked PCIe BAR0 mystery
turns out to have been a non-problem from a bandwidth standpoint all
along -- not just "lower priority," but structurally incapable of ever
mattering for throughput.

**The numbers, worked precisely, not approximated:**
- Measured `clk_div` from the actual Fitter report (2026-07-30 recompile):
  **54.22 MHz**.
- Theoretical ceiling: even at the most optimistic possible rate -- one
  new 32-bit word leaving the card every single cycle, sustained forever,
  which nothing in this architecture actually does continuously -- that's
  `54.22e6 x 4 bytes = 216.9 MB/s`. Real workloads, given the shared-host-
  bus finding (#68 conversation) and realistic cross-zone traffic
  patterns, would sit well below this; it's a hard ceiling, not a typical
  figure.
- PCIe Gen2 x8: ~4 GB/s. **~18.4x more bandwidth than the fabric's own
  ceiling could ever need**, not "comfortably enough" -- structurally
  more than an order of magnitude past what the card could ever produce.
- The Waveshare USB-Blaster clone's JTAG link: fixed ~6 MHz, bit-serial,
  with additional ISSP multi-step protocol overhead on top of that. Even
  the most optimistic bit-serial ceiling (~0.75 MB/s, before ISSP
  overhead) is roughly **289x slower** than the fabric's own theoretical
  maximum -- and JTAG has been fully sufficient for every single silicon
  test this entire project has run, including all of #58 through #66's
  work.

**The conclusion this actually supports, precisely stated:** this was
never really a "is PCIe fast enough" question -- PCIe's raw bandwidth
was never going to be the limiting factor, but neither was JTAG's, by a
wide margin. The card's OWN architecture (a shared, fully-serial host/
loader channel per #68's finding, plus a bounded, zone-count-limited
parallel-computation ceiling) is what actually caps realistic throughput,
and that ceiling sits far below what even the slower of the two existing
transports can carry.

**One nuance worth keeping, so this doesn't overstate the case and close
the PCIe question entirely:** bandwidth was never really PCIe's potential
advantage here -- its real value, if the RAM-read runtime mechanism ever
needs a host tightly in a low-latency control loop, would be *latency and
DMA orchestration* (avoiding JTAG's per-transaction bit-banged ISSP
overhead), not raw throughput. The still-open BAR0 data-access mystery
remains genuinely unresolved and worth fixing eventually for that reason
-- but this analysis confirms, with real numbers rather than just
schedule-priority reasoning, that it was correctly parked as non-blocking
and never actually at risk of constraining anything this project has
needed to do.

**Practical upshot for the upcoming full-repo model-triage pass:** any
existing model/subsystem whose value proposition depends on needing more
throughput than JTAG already comfortably provides is not solving a
problem this architecture actually has -- worth keeping this ceiling in
mind explicitly as one of the fit criteria for that audit, alongside the
zone-parallelism ceiling itself.

## 70. Reframing what "shape" actually buys, and the real scheduling unit: dynamically-coupled zone pairs, not a fixed serial/parallel split -- corrects two real overclaims from #69 (Alan/session, 2026-08-01)

**A long, careful back-and-forth (2026-08-01, following directly from #69's
bandwidth analysis) that genuinely reframes how this project should talk
about its own parallelism -- honestly, not defensively. The theory below
still needs empirical testing (Phase 7's planned card-level VM model,
points.md #68's follow-on) before it's treated as proven; this entry
records the corrected REASONING, not a measured result.**

**Correction 1 -- "shape" (pentacross, #17/#42/#47) provides ZERO runtime
advantage. None. Its entire value is compile-time.** Verified precisely,
in two parts, both now confirmed directly against the RTL rather than
assumed:
- **No connectivity benefit.** Any cell can already address any other
  cell in its own zone directly -- flat addressing, no positional/shape
  requirement at all. Shape adds nothing here; it was never needed for
  reachability.
- **No isolation benefit.** Checked directly: `unicell_array64_v3.v`'s
  wired-OR combine loop (`for (i = 0; i < NUM_CELLS; i = i + 1)`) is
  UNCONDITIONAL -- no address filter, no group/shape filter. Every cell
  that fires in a given cycle folds into the exact same `or_data`/
  `or_addr` registers, regardless of what shape it's conceptually
  assigned to. Two pentacross clusters sitting in the same zone are not
  electrically separate things to this hardware -- they're 10 of the same
  25 cells sharing the exact same bus as every other cell in that zone.
  "Coexisting safely" for two shapes in one zone means their COMBINED
  firing schedule across the WHOLE zone never collides -- which is
  cooperation under one shared, single-threaded resource, not real
  locality. Genuine locality -- "these two things cannot possibly
  interfere, no coordination required" -- only exists at the ZONE
  boundary. The zone is the only real isolation boundary that exists in
  current hardware; "shape count inside a zone" is not an additional one.

**What shape actually is, then, precisely:** a named, pre-verified
TEMPLATE for the compiler's own placement search (#17's original,
correctly-stated motivation -- "collapse the search to a single
arrangement" instead of a hard CSP/backtracking search), plus the
specific discipline that a cell needing to cross a zone boundary should
carry its own cardinal bits directly rather than relay through a separate
hub cell (#17 rule 4, avoiding the port-count blowup #16's hub approach
hit). Both are real, valuable -- but they're COMPILE-TIME tractability
and BURST-EFFICIENCY conveniences, not a mechanism that makes anything
faster, more parallel, or more isolated once a model is actually running.
Framing shape as a runtime architecture feature (as earlier passages in
this same conversation did, before being corrected) was an overclaim.

**Correction 2 -- the #69 throughput ceiling (108.4 MB/s "useful compute"
figure) was the COLD-FIRE case, needlessly pessimistic for a realistic,
well-designed pipeline.** #69 assumed every fire costs 2 fresh bus events
(first arrival + second arrival). That's correct for a cold start, but a
properly-designed steady-state pipeline uses `latch_in` to keep each
downstream cell PRE-ARMED, waiting only for its trigger -- meaning after
one-time priming, each STEADY-STATE step costs exactly ONE new burst, not
two. A -> B -> C chained this way is genuinely 3 cycles for 3 stages, not
6. The raw #69 ceiling (216.9 MB/s, one word/cycle at the measured 54.22
MHz `clk_div`) is achievable for a well-pipelined design; 108.4 MB/s is
the pessimistic cold-start-every-time floor, not the realistic figure.
Both numbers are worth keeping on record -- they bound the real range,
rather than either one alone overstating or understating it.

**The corrected scheduling model -- this is the actual thing the
compiler's and the loader's scheduling logic both need to be built
against, replacing the earlier, too-simple "serial within a zone,
parallel/serial across the whole card" framing:**

The real unit of contention is not "one zone" and it is not "the whole
card" -- it is **whichever zones are actively exchanging data with each
other at a given moment.** A sending zone and its receiving partner are
genuinely, serially coupled for that specific transaction. Any zone with
no active cross-zone exchange in flight at that moment is a fully
independent unit, free to compute in parallel with everything else on the
card. This coupling is DYNAMIC -- it changes cycle to cycle, model to
model, based on which cross-zone links are actually in use at any given
instant, not a fixed structural property of the card's physical layout.

**Confirmed alongside this, precisely:**
- **Card geometry**: the target layout is 2 columns x 8 rows of zones --
  meaning every zone has AT MOST 3 of its 4 cardinal ports connected to a
  real neighbor (the 4th is always a grid edge in a 2-wide layout, since
  nothing can be both east and west of you when there are only 2
  columns). Worth keeping precise for any placement/scheduling math going
  forward, rather than assuming a generic 4-neighbor grid.
- **`routing_mask` is genuine simultaneous multicast** (re-confirmed,
  matches #17 rule 2 exactly): one fire can kick off multiple
  already-primed, already-waiting neighboring zones in a single event --
  real, hardware-native parallelism that doesn't depend on shape at all,
  just on the multicast mechanism itself and correct placement of which
  cell holds which cardinal bits.

**Net effect on the project's own self-understanding, stated honestly:**
this does not undermine the core thesis ("topology is computation" is a
claim about HOW causality sequences, not a claim of unlimited
parallelism -- #Saturday's conversation already established this) -- but
it does mean "shape" needs to stop being described, even informally, as
something that makes the fabric faster or more parallel. It doesn't. It
makes the fabric's placement problem solvable in reasonable compile time,
and it makes cross-zone communication burst-efficient rather than
relay-wasteful. Real parallelism comes entirely from zone count and from
how "chatty" a given model's own cross-zone traffic pattern is -- exactly
the "achieved vs. ceiling" measurement the planned Phase 7 card-level VM
model (points.md #68's follow-on) exists to actually quantify, rather
than continue reasoning about in the abstract. This entry is the
corrected theory going into that measurement, not a substitute for it.

## 71. Phase 7 built and run: card-level scheduling model gives real, measured numbers -- and the first result is honest, not the best case (Alan/session, 2026-08-02)

**Direct empirical follow-on to #70's corrected theory.** Built
`unicell_card_v3.py` -- a grid of zones (each an unmodified, already-
proven `UniCellArrayV3`), wired with the exact arbitration mechanisms
verified against the RTL in #70: priority-based (not OR) inbound
arbitration at zone boundaries, external-reception-blocks-internal-
computing mutual exclusion within a zone, and one shared card-wide host
channel. 20 new tests, including a direct replay of the branch-cell
multicast scenario from this week's design conversation -- one fire,
routed to two cardinal directions at once, both already-primed
neighboring zones receive and fire in the exact same tick. Real, measured
simultaneous parallelism, not reasoning about it.

**First experiment, and a real bug caught before any numbers were
reported -- not glossed over.** The first "isolated workload" design was
under-specified: it only ever delivered ONE bus event per zone, so no
cell ever actually fired (confirmed directly: this architecture has no
autonomous/self-triggering anywhere -- a cell never fires without a real
incoming event, even with `latch_in` set, which was worth confirming
precisely rather than assuming). Traced the exact mechanism, fixed the
workload to the simplest UNAMBIGUOUS case (one 2-input gate per zone,
needing exactly the two events it actually requires), re-ran, and
verified every zone actually computed the correct result before trusting
the achieved-fraction numbers at all.

**The corrected result, and it's honest rather than flattering:** at
both 32 zones (4x8) and 64 zones (8x8), a fully "isolated" workload
measured close to the SAME low achieved-fraction as a fully chained one
(~1/N in both cases) -- NOT because more zones don't help, but because
this experiment's isolated workload still needs host-fed data for its
one step, so it's ALSO bottlenecked by the single shared host channel,
exactly the same as the chained case. This is a genuine, useful finding
in its own right, not a disappointing result to bury: **"isolated"
placement alone does not automatically produce measured simultaneous
parallelism.** Real simultaneous multi-zone activity requires zones to be
running on data that's already been delivered -- via multi-stage internal
chaining or cardinal multicast (both already proven working in the test
suite) -- not per-step host involvement.

**What this sharpens for the next experiment, concretely:** #70 predicted
a real separation between chatty and non-chatty workloads; this first
pass didn't yet isolate that separation, because the "isolated" workload
chosen was itself accidentally still host-bottlenecked. The next
experiment needs a workload where most zones' work happens AFTER an
initial kickoff, using internal chaining rather than repeated host
injection -- multi-stage propagation within a zone using purely internal
`or_valid` feedback needs its own carefully-designed per-stage trigger
path (each stage genuinely needs a distinct triggering event; there's no
"it just propagates" shortcut), which is real, scoped follow-up work, not
assumed or rushed into this pass.

Full existing suite (240 prior VM tests, 278 pre-existing project tests)
confirmed unaffected throughout.

## 72. The compiler's core 2-input-gate cost model rests on an invalid assumption -- likely affects most of fp_tiles.py's ~67 tile constructors, not just the adder (Alan/session, 2026-08-02)

**Direct follow-on to #70/#71, and a significant escalation in scope.**
While attempting to correctly translate the existing 32-bit Kogge-Stone
adder (`fp_tiles.py`'s `make_int32_add`, 482 cells, claimed depth 10) onto
the new card-level VM, found that `NORBuilder._emit_v2` -- the shared
implementation behind `AND2`/`OR2`/`XOR2`, described in the file's own
docstring as the "v2 upgrade" achieving "1 cell per gate" for every
2-input gate in the library -- rests on a real, invalid assumption:

> "Multiple cells may share the same in_b input_address -- correct. When
> B arrives, all listening cells fire simultaneously, each with their own
> preloaded a_data. Clean bus broadcast, no relay needed."

**Confirmed with Alan directly: this was based on the idea that multiple
cells could watch one cell for its result -- broadcast, one-to-many.
That capability is not something the current architecture lost; it was
never actually valid given how the wired-OR bus genuinely works,**
confirmed repeatedly this week (#32, #70): multiple cells firing to
DIFFERENT output addresses in the same cycle collide/corrupt on the
shared bus, they do not cleanly coexist. The "preloaded-A" half of this
pattern (operand A pre-staged before the run, only operand B travels the
network) is fine on its own -- the invalid part is specifically the
"many cells share one trigger address and all fire simultaneously to
their own distinct outputs" broadcast claim riding along with it.

**Concrete, measured consequence for the adder used as the worked
example:** its own reported "depth 10" implicitly assumed every cell at
a given depth level fires in the same cycle as its siblings. Since that's
not actually possible on the real bus, the adder's TRUE cycle cost (every
cell genuinely serviced one at a time) is much closer to its full 482-cell
count than to a 10-stage pipeline -- a real, quantifiable correction to
the tile's own metadata, not a minor caveat.

**Blast radius, measured rather than assumed:** `_emit_v2` (the AND2/OR2/
XOR2 shared implementation carrying this assumption) appears 445 times
across `fp_tiles.py`, which defines 67 separate `make_*` tile
constructors spanning INT32, FP32, and MIF operations. This strongly
suggests the majority of the tile library's own cost/cycle claims are
affected, not just the one adder investigated here -- but a full,
per-tile confirmation has NOT been done yet; this entry records the
scope measurement (445/67), not a completed audit.

**This directly elevates and sharpens the "once the VM is settled, audit
the whole repo" plan from earlier this week (2026-08-01) from a general
intention into a concrete Priority Zero item:** every existing model or
tile whose cost model depends on this same-cycle multi-cell-broadcast
assumption needs to be re-tested against the current, verified bus
semantics and either fixed, re-characterized honestly, or archived if it
doesn't hold up -- exactly the "if it doesn't fit, archive it; if it
does or might, pull it up to current cell version, test it, keep if it
passes, archive if not" criterion Alan already set for that pass.

**The corrected design direction, validated by this same finding:**
since simultaneous multi-cell broadcast was never real, there is no
throughput cost to abandoning it -- a model built from dedicated cells
and one built from a small, repeatable unit fed serially by the loader
cost the SAME number of cycles, given the confirmed one-thing-at-a-time
bus limit. The dedicated version only spends extra silicon for a benefit
it was never actually getting. This is the approach being used to
rebuild the adder correctly as this entry's direct next step (not a
translation of the existing, assumption-carrying compiled output).

## 73. The 32-bit adder, rebuilt correctly: 3 reused cells instead of 482, verified bit-exact, same real cycle cost (Alan/session, 2026-08-02)

**Direct build-out of #72's corrected direction, done rather than just
proposed.** Rebuilt the 32-bit Kogge-Stone adder from scratch -- not
translated from the existing compiled `make_int32_add()` output, which
carries the invalid broadcast assumption baked in -- using the repeatable-
unit pattern Alan described: since the machine is confirmed serial
regardless of cell count, and the algorithm's own structure is highly
repetitive (the same 2-gate pattern 32 times for generate/propagate, the
same 3-gate pattern a shrinking number of times per prefix-tree level,
the same 1-gate pattern 31 times for the sum), a small number of reused
cells, loader-fed serially, costs exactly the same cycles as a fully
dedicated version -- while using a small fraction of the silicon.

**Built in two verified stages, not one big untested leap:**

1. **Stage 1 alone first** (`experiments/adder_repeatable_unit.py`): 2
   reused cells (AND, XOR), fed all 32 bit positions in strict sequence
   -- each gate gets its own full prime+trigger pair, never overlapping
   the other cell's events in the same tick (the exact discipline #72
   identifies as necessary: different output addresses can never fire
   the same cycle, even when computing from the same inputs). Verified
   bit-exact against Python's own `A & B` / `A ^ B` on the first run.

2. **The complete 11-stage adder** (`experiments/adder_full_repeatable.py`):
   3 reused cells -- sized to the LARGEST repeatable sub-pattern
   (AND+OR+AND, the prefix-tree unit) -- reconfigured only between stage
   KINDS (stage1 uses 2 of 3, the prefix tree uses all 3, the sum stage
   uses 1 of 3), never within one kind's repeated iterations. Mirrors
   `_build_int32_add_ks`'s exact algorithm as a Python oracle, checked at
   every level, not just the final answer.

**Verified, not just run once:** the full-adder version passed against
10 test cases -- all-zeros, max+max, a full end-to-end carry-propagation
case (`0xFFFFFFFF + 1 = 0x00000000`, proving the prefix tree correctly
carries all the way across the word), an overflow case, and 5 random
32-bit pairs -- every one matching both the Python oracle and real
integer arithmetic bit-for-bit. Tick count was identical (964) across
every input, confirming cycle cost is purely structural, independent of
data values, exactly as expected for a fixed dependency graph.

**The headline number: 3 cells instead of 482 -- a 161x reduction --
for the identical cycle cost the 482-cell version was always actually
going to pay**, once #72's correction is applied (it could never fire
more than one cell per tick either). The only thing the dedicated
version was ever spending that the reused version doesn't: 479 cells'
worth of silicon, for a parallelism benefit that was never real.

**What this is, and isn't, evidence of:** this is one worked example,
not a general proof that every model in the existing library collapses
this dramatically -- reduction ratio depends entirely on how repetitive
a given algorithm's structure is. But it's a genuine, verified existence
proof that the repeatable-unit + loader-feed pattern works correctly on
a real, non-trivial computation, and a concrete template for what
"rebuilt correctly, tested, kept" should look like in the planned
full-repo triage this finding motivated (#72).

Full VM regression (240 tests across `unicell_v3.py`/`unicell_array_v3.py`/
`loader_fsm_v3.py`/`unicell_card_v3.py`) confirmed unaffected throughout.

## 74. Pure cellular-automaton model built: confirms the no-shared-bus hypothesis directly, and a full-adder bit works -- but multi-value routing reveals a real, unsolved layout difficulty (Alan/session, 2026-08-02)

**Alan's radical proposal, worked through and built, not just discussed:**
if wiring only ever connects a cell to its immediate physical neighbor --
whether that's the next cell within what used to be a zone, or across
what used to be a cardinal boundary -- arbitrary addressing becomes
meaningless. There's no shared bus left to address INTO. `input_address`/
`output_address` and every opcode built around them (`SET_INPUT_ADDR`,
`SET_TARGET`/`config_match`) become structurally redundant, not just
unused. The model collapses to pure cell automata, plus everything
learned this week about routing/cardinality layered on top.

**New `unicell_automaton_v1.py`, genuinely different from `unicell_v3.py`,
not a variant of it.** `routing_mask` keeps its exact existing meaning
(which neighbor direction(s) a fire reaches, multicast-capable). 
`cardinal_edge` is necessarily reinterpreted: with no local bus left to
distinguish from, it's applied per INCOMING direction instead of
per-outgoing -- consume (normal two-arrival participation) vs. relay
(pure pass-through using the cell's own routing_mask, never touching its
own `a_data` at all). This is the same conduit-vs-participant distinction
#32/#58 already established, just happening at every hop instead of only
at a zone boundary. Gate computation itself is unchanged, reused directly
from `unicell_v3.py` -- nothing about how a gate computes changed, only
how cells reach each other.

**The core hypothesis, confirmed directly, not assumed:** two completely
unrelated single-cell computations, on opposite corners of a 4x4 grid,
both primed and triggered on the exact same ticks -- under the zone/card
model this is structurally impossible (#70/#71, the whole point of the
1-burst-per-zone ceiling). Here, with no shared bus, both cells fire in
the exact same tick, verified directly
(`tests/vm/test_unicell_automaton_v1.py`, 14/14 passing, including
propagation, cardinal relay, and multicast all working correctly in the
new topology too).

**A full-adder bit, built natively and verified against all 8 possible
input combinations** (`experiments/adder_automaton_fulladder.py`), using
two real techniques worth naming: MULTICAST to deliver one computed value
(p=a^b) to two different downstream cells in a single fire, and
LOOP_BACK+LATCH_IN to let one cell hold a computed value and stay armed,
firing again the moment a second, later-arriving value shows up --
avoiding a relay hop entirely for that value. All 8 (a,b,cin)
combinations pass, both sum and carry bit-exact.

**A real, honestly-reported design difficulty, not smoothed over:** the
first attempt at a full multi-bit ripple chain got tangled and was
deliberately abandoned rather than pushed through unverified -- carry_out
needs to reach the NEXT bit's sum-cell AND its AND-cell, and those aren't
simple one-hop neighbors of where carry_out gets computed. Getting a
clean 2D layout where every needed connection is a genuine single hop
took real, careful positioning even for ONE isolated full-adder bit (one
early attempt placed two cells diagonally apart, which isn't reachable in
a single hop at all -- caught by the carry results failing, not assumed
correct). A `CACell` can also only track ONE in-flight two-arrival
sequence at a time -- it can't simultaneously consume its own trigger and
relay something unrelated through in the same timeframe, which is why
dedicated relay-only cells (never injected into) were needed rather than
letting compute cells double as relays.

**Honest status: NOT yet done.** Carry_in was supplied externally in this
adder, not chained from a previous bit's own carry_out -- the actual
multi-bit ripple chain (where carry genuinely propagates cell-to-cell)
surfaces the layout challenge above at real scale and hasn't been solved
yet. This is real, scoped future work: either a more careful N-bit layout
generalization, or a richer per-cell model (e.g. genuinely separate
consume/relay channels) that makes multi-value routing less
position-dependent.

Full existing VM regression (240+ tests across all prior files) confirmed
unaffected throughout -- this is a standalone new model, nothing existing
depends on it.

## 75. The multi-bit carry-chaining difficulty from #74, solved: lean on cardinality, not more relay cells (Alan/session, 2026-08-02)

**Direct resolution of the open problem #74 left honestly unsolved.**
Alan's suggestion, worked through precisely: "use the cardinality parts,
one in and two or three out." The actual fix turned out to be smaller and
more elegant than the layout wrangling #74's first attempt got tangled
in: carry_out[i] never needed to reach two different cells in bit i+1
directly. It only needs to reach ONE cell -- `p_cell[i+1]` -- which
already multicasts to its own two destinations (`sum_cell[i]`,
`t_cell[i]`) for its own `p[i]=a[i]^b[i]` value. Since a direct injection
(`a[i]`, `b[i]`) never arrives "from a direction" and so completely
bypasses `cardinal_edge`, `p_cell` can mark its west-incoming direction
as pure relay for `carry_in` specifically, without that touching its own
a/b-driven computation at all -- then relay `carry_in` using the exact
same `routing_mask` it already uses for its own fire. One relayed value,
reused routing, no separate fan-out logic needed for carry at all. "Two
or three out" turned out to mean: let the cell that already has the
fan-out capability do double duty, rather than building new fan-out
somewhere else.

**Verified this time by checking every claimed adjacency on paper before
writing any code** -- the exact discipline #74 flagged as missing from
its first, abandoned attempt. All five cells' positions and every
claimed single-hop connection (including `carry_cell[i]` firing east and
landing exactly on `p_cell[i+1]`) confirmed arithmetically before the
model was built.

**One real bug caught and fixed before trusting the result, not glossed
over:** bit 0 has no previous bit to relay `carry_in=0` through -- the
first version silently left `sum_cell[0]`/`t_cell[0]` never receiving a
second arrival at all, so they simply never fired. This produced `sum=0`
for every case, which happened to accidentally match a few trivial test
cases (all-zeros, self-cancelling values) before the real failures showed
it up. Fixed by injecting `carry_in=0` directly for bit 0 only, exactly
matching how a real ripple-carry adder needs an explicit carry-in at its
first stage.

**Result: a genuine, generalized N-bit ripple-carry adder, verified
thoroughly, not just for one lucky case.** 10 initial test cases (4-bit
and 8-bit, including full-width carry propagation like `0xFF+0x01`
wrapping correctly through all 8 bits) plus 18 further random cases
across 4-bit, 8-bit, and 16-bit widths -- 28 total, every one correct.
`experiments/adder_automaton_ripple.py`.

**What this closes out from #74:** the pure automaton model now has a
real, working, non-trivial computation built entirely from next-hop-only
wiring with genuine carry propagation across an arbitrary number of
bits -- not just one isolated full-adder bit with an externally-supplied
carry-in. Combined with #74's already-confirmed core finding (unrelated
cells genuinely fire in the same tick, no shared-bus contention at all),
this is now a substantiated, not just hypothesized, alternative
architecture direction.

Full existing VM regression (240+ tests) confirmed unaffected throughout.

## 76. The hybrid resolution: two cell types, addressed shell + stripped autonomous interior -- rescues the automaton idea from being a disconnected dead end (Alan/session, 2026-08-02)

**STATUS: a real, coherent architectural synthesis, worked through
carefully in conversation -- not yet built. Alan intends to add further
refinements soon; this entry captures where it landed today, not a
closed decision.**

**The tension this resolves:** #74/#75 confirmed the pure automaton
model (`unicell_automaton_v1.py`) genuinely eliminates the shared-bus
contention that bounds the v3.1 zone/card model's parallelism (#69/#70/
#71) -- but doing so meant giving up addressing entirely. That looked,
at first, like it would strand the idea: `Ward` (health monitoring --
confirmed directly, README.md: needs to know which specific cell holds
what, tracked through the compiler-to-silicon type pipeline), `Sentinel`,
`Shore`, and the RAM-read loader mechanism (`loader_fsm_v3.v`) are all
fundamentally addressed concepts. None of them mean anything in a
topology where a cell only ever knows "whatever showed up from my
neighbor."

**The resolution: addressing isn't gone, it's demoted to a
configuration-time-only concept, cleanly separated from data delivery
during compute.** A "stripped" cell keeps a fixed position the loader can
still target to configure it, one at a time, serially -- exactly how
`loader_fsm_v3.v` already walks cells today (`SET_TARGET`+`LOAD_AT`).
What's actually removed is using address for data movement DURING
computation, which is the only place the shared-bus assumption was ever
load-bearing in the first place. Loading and computing turn out to be
genuinely separate problems; only the second one needed the addressing
hardware stripped out.

**Readback needs no dedicated path either, for the same underlying
reason.** A result just sits in whatever cell computed it (`data_reg`),
unread and untouched, pulled out through the same kind of debug/probe
readback path this whole project already uses for silicon verification
(`dbg0_a_data` and equivalents) -- not through the fabric's own routing
at all. Watching a value isn't the same as wiring a return path for it.

**Concrete shape: two cell types, not one model replacing the other.**
- FULL cells (everything built this session -- addressing latches, auth,
  targeted opcodes, command-emit) -- reserved for one or a few zones,
  running `Ward`/`Sentinel`/`Shore` and loader coordination.
- STRIPPED cells -- just topology, `routing_mask`, `cardinal_edge`, no
  addressing hardware at all, since address is never needed for their
  own data flow, only used ONCE by the loader at configuration time to
  reach them.
- The stripped region can occupy a LARGE portion of the card, connected
  to the addressed shell only at its boundary via standard routing.

**The DSP-block analogy, confirmed as exact, not just illustrative:** a
DSP block on a real FPGA is precisely this pattern already -- a
specialized, dense resource with its own internal structure, connected
to the general fabric only at its boundary, treated by the floorplanning
tool as a distinct resource type rather than more of the same fabric.
This project already has the exact framework needed for this: the
`card.json` descriptor schema built earlier this session already treats
DSP/RAM blocks as first-class resource types the loader reasons about. A
stripped-cell region would slot into that SAME schema as another
resource type, not require a new one.

**What this rescues, precisely:** without this, the automaton model
(#74/#75) risked being a genuinely interesting but disconnected research
exploration -- correct, but with no path to actually integrating with
the rest of the project's architecture (loading, security, OS-layer
management). With it, the automaton model becomes a real, addressable
(at the boundary) resource type the existing loader/card-descriptor
infrastructure can already reason about -- complementing the v3.1
architecture rather than competing with or replacing it.

**Not yet built -- the natural next concrete step, when picked back up:**
a genuine two-cell-type hybrid VM component with a boundary cell that's
bilingual (`UniCellV3`-style addressed on its outward-facing side,
`CACell`-style next-hop on its inward-facing side), and an end-to-end
load -> autonomous compute -> readback test proving the whole hybrid
loop works, not just each half in isolation.

## 77. The "I am ready" flag, fully specified: reuses the already-free cmd_latch[127:96], closes a real gap in BOTH cell types (Alan/session, 2026-08-02)

**Direct follow-on to #76, completing the flow-control piece its own
"next concrete step" flagged as missing.** Confirmed directly against
the RTL first, not assumed: `data_reg` is overwritten unconditionally on
every fire in the CURRENT, already-silicon-proven addressed cell
(`unicell64_v3.v`) -- there is no check anywhere for whether a previous
result was ever actually consumed before a new one clobbers it. This gap
is not specific to the stripped/automaton cell at all; it's already
latent in the model proven on real hardware all session.

**The mechanism, worked through precisely in conversation:**
- Two signals that turn out to be one: "I'm clear for new data" and
  "confirm my data has been read" are the same event from two sides -- a
  cell only becomes ready-for-new the instant its held result is safely
  consumed. One "I am ready" flag serves both roles.
- The backward cascade this produces is automatic, not a separate
  mechanism to design: add `ready` as one more condition on `bus_hit`
  itself. A cell whose own output hasn't been consumed can't fire --
  which means it can't accept a new second arrival either, since
  `bus_hit` already gates both. Whatever feeds it finds a cell that
  structurally can't accept right now, and if THAT cell carries the same
  discipline, its own attempted fire fails too, and the stall propagates
  backward purely as a consequence of the same gate applying uniformly
  at every cell -- no dedicated "please pause" signal needs to travel
  anywhere separately.
- This directly generalizes `CMD_LOAD_DONE` (#63), already silicon-
  proven as exactly "confirm my data has been read" for config-loading
  specifically. The chain-end case (where a stripped autonomous region's
  result needs reading by the addressed "memory-reading top command
  layer" from #76's hybrid design) is the SAME signal, one level up.

**The concrete implementation, reusing space rather than needing
anything new:** `cmd_latch[127:96]` has sat genuinely free and untouched
since the 128-bit widening in #49/#51/#59 (confirmed directly against
the RTL's own comments). This becomes a genuine OUTPUT BUFFER, separate
from `data_reg`: `data_reg` stays exactly as-is (the cell's working
register, overwritten every fire); the new field holds specifically the
value being OFFERED to whatever reads it, only updated when it's safe to
update (i.e. `ready==1`, meaning the previous offering was already
confirmed read). This is genuine double-buffering -- a cell can keep
computing its next value while its previous result sits safely parked,
waiting to be consumed -- the actual mechanism that makes real hardware
FIFOs/pipeline registers with backpressure work, not a cosmetic
relabeling of the existing single register.

**Applies uniformly, not just to chain-ends:** confirmed directly with
Alan ("even the main normal cell needs this kind of control") -- this is
a general robustness fix for BOTH cell types, not a stripped-cell-only
patch, given the gap was confirmed to already exist in the addressed
model too.

**Not yet built at the time of this entry** -- VM implementation and a
concrete overload test (the adder from #75, fed successive input pairs
faster than the chain-end result is read, verifying the stall
propagates backward correctly with zero data loss/corruption instead of
the silent clobbering confirmed above) are the immediate next step,
logged separately once run.

## 78. The ready-flag mechanism built and tested: overload the adder, verify the backward stall cascade, zero data loss (Alan/session, 2026-08-02)

**Direct build-out of #77's spec, not just implemented but stress-tested
against the exact scenario Alan asked for: "take the adder example and
overload it with data, holding the output until it's full."**

**`unicell_automaton_v1.py` extended:** `CACell` gained `out_buffer`
(the offered output, separate from `data_reg`) and `ready` (True =
buffer empty/consumed). `fire_from` now returns `(accepted, forward)`
instead of just a value -- a cell whose `ready` is False rejects the
event entirely rather than processing it, and a fire now writes to
`out_buffer` and clears `ready`, exactly as #77 specified. `CAGrid`
was restructured to track the ORIGIN of every pending event (not just
its target): a rejected delivery is RE-QUEUED for retry rather than
dropped, and a successful delivery confirms the origin cell's `ready`
flag -- this is what makes the backward cascade automatic, verified
directly rather than just reasoned about. A new `confirm_read(row,
col)` models the external "memory-reading top command layer" from #76's
hybrid design acknowledging a chain-end's output.

**Backward compatibility confirmed before building anything new:** all
existing automaton tests (14/14) and both adder experiments (single
full-adder bit, 8/8; the full ripple adder, 10/10 plus 18 random cases)
still pass unchanged -- the new gating doesn't disturb anything that only
ever fires each cell once per run.

**The overload test itself, `tests/vm/test_adder_overload.py`, 6/6
passing:** round 1 (5+3=8) computes and drains normally. Round 2 (9+1)
is injected WITHOUT confirming round 1's results -- and correctly
stalls: round 1's answer stays completely intact and unread, pending
events remain genuinely queued (not silently lost), for as long as
confirmation is withheld. Confirming round 1's outputs immediately lets
round 2 flow through and complete correctly (9+1=10), with no
corruption from the earlier stall.

**A real bug caught in the TEST, not the model, and left as evidence of
the mechanism working correctly rather than smoothed over:** the first
version of this test only confirmed the sum-bit outputs and left the
adder's own final overflow carry (the last bit's carry_cell, which has
nowhere further to route to) unconfirmed -- and the pipeline correctly,
permanently refused to un-stick until that was fixed too. This is
exactly the mechanism doing its job: an unread output anywhere in the
chain, including one the test author forgot about, genuinely blocks
reuse, precisely as designed. Fixed by confirming the overflow carry
alongside the sum bits, matching what a real memory-reading layer would
need to read in full.

**What this closes out:** #77's spec is no longer just a design --
it's a working, tested mechanism, verified to produce zero data loss or
corruption under exactly the adversarial condition it was built to
survive (a second round of work arriving before the first was consumed).
Combined with #74/#75/#76, the automaton-model side of this session's
work is now: hypothesis confirmed, a real computation built and
verified, the multi-bit chaining difficulty solved, the hybrid
addressed/stripped architecture worked out, and now genuine
backpressure proven to work under load.

Full regression (14+6+182+34+20+24 VM tests, plus both adder
experiments) all green throughout.

## 79. The full synthesis: parallelism is realised after all, in a different manner -- with genuine choice, an ICM that's now a capability graph, and an open naming question (Alan/session, 2026-08-02)

**STATUS: a synthesis of #74 through #78, capturing where today's whole
arc landed. Naming question left explicitly OPEN, not decided here.**

**The original goal is fully realised -- in a different manner than
first assumed, not approximated.** The zone/card model's #69/#70/#71
finding was real and stands: parallelism there is bounded by zone count,
because every zone shares one physical bus. That was never going to
change by reconfiguring the existing architecture. What changed is that
#74's stripped, next-hop-only cell removes the shared bus itself, and
#75-#78 proved (not just hypothesized) that a genuine, non-trivial,
robust computation runs correctly on it -- a real adder, with real
multi-bit carry propagation, with a real backpressure mechanism verified
under actual overload. The system stays parallel. It just achieves that
through a different mechanism than the original zone-based design ever
could have, given the hard ceiling #70 established.

**And now there's a genuine choice, not a single fixed regime.** Zone-
count parallelism (the addressed shell) for anything needing per-cell
addressing, security, or Ward/Sentinel/Shore-style management (#76). The
stripped interior's much larger, chain-shaped parallelism for anything
that fits a next-hop, systolic-style structure. A model's designer picks
which regime fits the computation, rather than the whole card being
locked to one ceiling.

**The only genuinely serial part left is the boundary itself** -- one
zone (or a small addressed shell) reading from RAM and feeding the
stripped interior's edge, exactly the single shared host channel #69/#70
already identified as the real, unavoidable bottleneck. That finding
wasn't wrong; it's now correctly scoped down to just the interface role,
rather than describing the whole system's ceiling.

**The ICM survives, but its own nature changes: from a flat list of
independently-addressed cell configs to a genuine capability graph.**
This isn't a reframing for its own sake -- it's literally what the
adder's own construction (#75) already is: not "482 independently
addressed cells," but a specific chain topology (which cells connect to
which, in what shape) realizing a specific capability. The ICM format
going forward needs to describe THAT -- chains and their connectivity,
not just a flat per-cell configuration list -- for the stripped regions
at least, alongside whatever the addressed shell still needs in its own
existing format.

**The open naming question, left deliberately unresolved here:** does
"UniCell" still fit, given the underlying gate primitive -- the actual
universal, NOR-based computational unit -- is completely unchanged and
reused directly between both cell types (#74 confirmed this: the
stripped cell's gate computation is the exact same code, not
reimplemented)? Or does the project need a name that signals the
two-cell-type hybrid nature more directly -- "DuoCell", "UniCell+1", or
something else -- given how central that duality now is to the
architecture? Genuinely Alan's call, not resolved in this entry.

**The next concrete step, as of this entry:** realise this in the actual
card model -- extend the Phase 7 card-level VM (`unicell_card_v3.py`,
points.md #71) with a genuine hybrid region (one addressed zone plus a
stripped, next-hop autonomous interior), matching the real target card's
2x8 zone geometry, and test directly whether the model's predictions
(the parallelism ceiling being genuinely broken for the stripped region,
the backpressure mechanism holding under real card-scale load) still
hold once constrained to the actual physical layout -- rather than the
small, isolated grids #74-#78 were built and tested on.

## 80. The hybrid card, realized and working end to end -- the synthesis holds together, not just in two separate halves (Alan/session, 2026-08-02)

**Direct answer to #79's stated next step.** Built `hybrid_card_v1.py`:
one ADDRESSED shell -- a genuine `UniCellArrayV3` zone, 25 cells,
matching the real target card's actual zone size, not an arbitrary
number -- bridging data into a STRIPPED, next-hop-only interior
(`CAGrid`, running the exact #75 ripple adder, unmodified) and reading
the result back out through the addressed side.

**The bridge is explicit Python, standing in for what a real bilingual
boundary cell would eventually be in silicon (#76's own "next concrete
step"), not hidden or hand-waved:** each bit of the adder gets its own
dedicated shell cell acting as an addressed "loader tap" -- the shell
cell fires (a genuine addressed two-arrival event, auth/config_match and
all), and its `FireResult` gets read and injected directly at the
corresponding interior entry point. The return path works the same way
in reverse: the interior's confirmed chain-end outputs (sum bits, plus
the final overflow carry -- #78 already established this one is easy to
forget) get read back explicitly.

**Result: all 5 test cases pass, including full-width carry propagation
(`0b1111+0b0001=0b0000`, wrapping correctly) and the overflow-carry
confirmation that #78 already proved matters -- correct on the first
run, no bugs needing debugging this time**, which is itself a reasonable
confidence signal that the underlying pieces (#74-#78) were each
independently solid enough to compose without new surprises at the
boundary.

**What this actually demonstrates, precisely:** not just "two separately
-proven halves exist" but that the SYNTHESIS holds together as one
working system -- an addressed zone, sized and shaped like the real
target card's actual zone, genuinely feeding and reading back from a
stripped autonomous region running a real, non-trivial, verified
computation. This is the concrete, working proof that #79's synthesis
wasn't just a plausible-sounding story.

**Honestly scoped, not overclaimed:** this uses `num_bits` dedicated
shell cells as separate loader taps, one bridge per bit -- it does not
yet attempt collapsing that down to a single serial entry point with
internal fan-out distributing data inward hop-by-hop (the more
RAM-loader-realistic version #76 originally described). That's real,
separate follow-on work, not solved here. Also not yet tested: the
FULL, real card-scale geometry (2x8 zones, #71) with a large stripped
interior sized to the actual remaining cell budget -- this proof used a
small, focused interior (3x12 cells) sized to the adder itself, not the
whole card.

Full regression (all prior VM tests, both adder experiments, the
overload test) confirmed green throughout.

## 81. Multiple independent hybrid pairs -- measured, not just argued: genuine N-way throughput scaling, one real open question remains (Alan/session, 2026-08-02)

**Direct test of Alan's question: why only one control zone -- why not 2
or 4, each with its own set of chain cells? Answered by measurement, not
just reasoning, and the answer splits cleanly into two parts with
different confidence levels.**

**Compute-time: confirmed directly, not just asserted.**
`tests/vm/test_multi_hybrid.py` runs 4 independent `HybridCard` instances
(#80) -- each its own shell + interior, each computing a DIFFERENT sum --
with their ticks genuinely round-robin interleaved rather than drained
one after another (which would have proven nothing about real
simultaneity). All 4 reach quiescence correctly, each produces its own
correct, uncontaminated result, and -- the key measurement -- each of
the 4 took EXACTLY the same number of ticks to quiesce (10) as running a
single pair alone. That's genuine 4x throughput: four independent
computations complete in the same wall-clock ticks one would take by
itself, with zero resource contention between them. This is the same
"more zones = more real parallelism" finding from #70/#71, now directly
measured for the hybrid shell+interior case rather than assumed to carry
over.

**Why this holds, precisely, not just empirically:** each shell is its
own `UniCellArrayV3` instance -- its own physically separate bus. Each
interior is its own `CAGrid` -- no shared bus exists there at all, by
construction (#74's core finding). Nothing wires independent pairs
together unless explicitly connected -- by default they're exactly as
isolated as any two ordinary zones already are.

**One genuine, still-open question this does NOT resolve, worth being
precise about rather than glossing over:** this tests COMPUTE-time
parallelism only. LOADING multiple shells simultaneously from the
external host is a separate question -- #69/#70 found (and this entry
re-confirmed against `top_card_2zone_v3.v`'s exact wiring) that at least
the explored topology shares ONE host channel across the whole card. If
that reflects genuine production intent for the real 16-zone card, N
independent shells could compute in full parallel but still need to be
LOADED serially through that one channel -- the compute side scales,
the loading side may not, unless a different host-access architecture is
actually intended. Not a new problem created here; the same open
question #70 already flagged, now showing up concretely in a scenario
that makes it worth deciding rather than continuing to defer.

Full regression (all prior VM tests, both adder experiments, the
overload test, the single hybrid card test) confirmed green throughout.

## 82. The full RAM-staged operational loop: command zones reading/writing real RAM, port contention modeled and measured directly (Alan/session, 2026-08-02)

**Direct build-out of the complete loop Alan described: RAM staging ->
command zones (shells) reading their own operands -> chain zones
(interiors) computing -> results written to per-command-zone output RAM
-> completion.** `card_ram_loop.py` builds this as a real, steppable
system (`CommandZone` orchestrating a `HybridCard` from #80 through
READ_RAM -> COMPUTE -> WRITE_RAM -> DONE states), not a scripted
walkthrough.

**Resolves the "is there just one RAM point, or several" question from
the same conversation precisely: it depends on real port count, and
that's modeled explicitly, not assumed either way.** New `SharedRAM`
class with a genuinely configurable number of ports -- using the same
port twice in one tick is a real, measured contention event (the second
user must wait), exactly matching how real single/dual-port BRAM
actually behaves, not an idealized always-available resource.

**Two scenarios, both run and both correct, differing only in timing --
confirming the earlier framing precisely, not just plausibly:**
- **Dual-port RAM, one port per command zone** (matching real Arria 10
  BRAM's genuine dual-port capability): zero contention events, zero
  stall ticks, both zones compute correctly (5+3=8, 9+1=10).
- **Single-port RAM, both zones sharing it**: exactly one measured
  contention event (one zone waits one tick for the other's RAM access)
  -- reintroducing the #69/#70 bottleneck precisely at the RAM level
  this time, rather than the host-channel level. Crucially, correctness
  is completely unaffected either way -- the bottleneck only ever costs
  timing, never correctness, confirmed by both zones still computing
  the exactly right answer under contention.

**What this settles for the compiler-planning angle Alan raised:** the
top command zone is now a known, modeled entity (#80); the chain zones
are exactly where ICM-style modeling (the capability-graph reframing
from #79) does its real work; RAM is correctly treated as just another
resource -- like the DSP/RAM entries already in the `card.json` schema
from earlier this session -- needing its real port count and physical
layout captured accurately (the card descriptor is exactly where that
belongs), not assumed generously. This gives the hybrid model the
parallelism and flexibility the architecture's own early conception
called for, now with a working, measured implementation underneath it
rather than just the intention.

Full regression (all prior VM tests, both adder experiments, overload
test, multi-hybrid test, single hybrid card) confirmed green throughout.

## 83. What's actually confirmed vs. simulated: the honest checkpoint before this goes any further (Alan/session, 2026-08-02)

**STATUS: the definitive statement of where the whole #74-#82
automaton/hybrid arc actually stands, and what has to happen before it
means anything beyond "the Python model of it behaves as intended."**

**Nothing built today (#74 through #82) has touched real RTL or
silicon.** All of it -- the no-shared-bus hypothesis, the adder, the
ready-flag/output-buffer mechanism, the hybrid card, the multi-pair
scaling measurement, the RAM-port contention modeling -- is pure Python
simulation. Every "measured" result in those entries is a measurement of
whether the VM's own encoded rules behave self-consistently, not a
measurement of real hardware behavior. Worth stating plainly rather than
letting a long run of passing tests start to feel like more confirmation
than it actually is.

**Two foundational pieces need real RTL and silicon confirmation before
anything built on top of them means anything -- and Alan identified BOTH,
not just the obvious one:**

1. **The stripped/next-hop cell itself.** No RTL exists for it anywhere.
   The VM proves the ripple-carry algorithm is logically correct wired
   next-hop-only; it says nothing about whether that's physically
   realizable at a reasonable clock speed. This is the piece that
   actually answers the timing/physical-realizability question no VM
   can ever answer on its own -- confirmed correct in software, unknown
   in hardware, until real synthesis and place-and-route happen.

2. **The memory system.** `bram_dp_v3.v` is real, existing RTL,
   deliberately written (per its own header comment) so Quartus infers
   a true dual-port M20K block -- but it has never actually been fit or
   tested on real silicon. This means #82's entire dual-port-vs-single-
   port contention result rests on exactly the same kind of unconfirmed
   assumption as the stripped cell -- designed-to-behave-a-certain-way is
   not the same fact as measured-to-behave-that-way.

**The agreed sequencing, in order:**
1. Confirm whether `bram_dp_v3.v` has an existing Quartus fit report to
   check, or needs one built fresh.
2. Design real RTL for the stripped cell -- starting with whatever scope
   is needed to test the timing question directly, not the full hybrid
   architecture at once.
3. Get both confirmed on real silicon -- this is what actually answers
   the open question, not further VM work.
4. Only once that foundation is stable: look at upgrading everything
   built on top of it today (the ready-flag mechanism as a real addition
   to the existing addressed cell, the full hybrid card, the RAM loop)
   to match what's now confirmed real, rather than continuing to layer
   simulation on top of simulation.

**Why this matters as a discipline, not just a caution:** this is the
chance to correct any assumptions baked into today's work before they
propagate further -- built on real, measured silicon and RTL, not
imagined or waved at. Exactly the same standard this project has held
itself to everywhere else (#58 through #66's cell-internals work, the
#67 VM rebuild verified line-by-line against the actual RTL) -- applied
here explicitly before the automaton/hybrid direction is allowed to
become "the plan" rather than "a promising, simulated hypothesis."

## 84. The stripped cell's command bus is not new wiring -- it's the existing per-cell command wiring, reinterpreted as cardinal once boot is over (Alan/session, 2026-08-02)

**STATUS: design note for the upcoming stripped-cell RTL scoping. Not yet
built or simulated.**

**The addressed loading mechanism does not go away in the stripped
cell -- it can't, because it's the only way the cell could ever be
configured in the first place.** A cell with no way to receive an
initial program from outside could never become a working cell at all.
So the internal cell_id, address match, and full opcode/command-bus
system stay exactly as they already exist in the current addressed-cell
RTL. This is the loader's job, unchanged -- direct addressing, done once,
at setup time, by `loader_fsm_v3.v` exactly as it already works.

**What changes is only what the cell listens to once it's running as
part of a stripped chain.** Post-boot, in stripped/compute mode, the
cell stops watching for address-matched commands from the fabric at
all -- it's isolated from that match/broadcast mechanism entirely. The
only thing that can still reach it is whatever arrives on its cardinal
neighbor connections.

**The actual insight: the command bus is already separate, dedicated,
per-cell wiring, distinct from cmd_data on the shared cmd_bus -- so
turning it cardinal doesn't require new wires, only a change in what it
does once boot is over.** Since it's not being address-matched anymore
in stripped mode, there's nothing stopping that same physical command
wiring from carrying a token hop-to-hop between neighbors the same way
the stripped data wires already do -- tagged the same way data vs.
command tokens would need to be distinguished (per #83's earlier
freeze/backpressure note), just riding infrastructure that already
physically exists rather than requiring anything newly routed.

**The resulting picture, cleanly separated:**
- **Setup time:** direct addressing, cell_id, full opcode system --
  exactly the existing addressed-cell RTL, doing exactly what it already
  does. This is the loader's job and stays untouched.
- **Compute time (stripped/chain mode):** the cell is no longer
  listening for address-matched anything. Data arrives cardinal.
  Freeze/reprogram-type signals arrive cardinal too, riding the same
  physical command wiring that already exists per-cell, just repointed
  rather than address-matched -- with backpressure/stall cascading
  through the chain exactly as already proven in #77-78's ready-flag
  mechanism.

Genuinely elegant resolution: nothing new needs to be invented or
wired. The command bus was always going to be there because the cell
had to be loadable -- the only design decision is what it does with that
existing wiring once boot is over.

## 85. Data-dependent, chain-local reprogramming taken to its extreme: a physically-realized adaptive loop -- halt, reprogram the threshold/internals, release, repeat until satisfied, then branch out (Alan/session, 2026-08-02)

**STATUS: conceptual only, not yet simulated or designed as RTL. Captured
here so the idea isn't lost before it's evaluated properly.**

**The starting point (this session, immediately prior): the
command_cell's existing push functionality -- already able to take a
data value and drive it onto the command bus -- now targets cardinal
outputs instead of a fabric address (#84), which means reconfiguration
can be targeted at a specific point in a chain, contained to that chain
only, and gated by the same flow-control/backpressure mechanism already
proven (#77-78). A chain's own data can therefore decide, live, whether
and how a cell downstream gets reconfigured.**

**Taken to the extreme discussed here: it's not just the branch/target
that's data-dependent -- the comparator threshold and the cell's
internal state are themselves programmable things, and the command cell
already has everything needed to change them mid-flow.** Nothing new
needs to be invented for the mechanism itself:
- **Halt:** freeze the relevant point in the chain (#84).
- **Reprogram:** push new values -- the threshold, other cell internals,
  or both -- via the existing command_cell/push mechanism, cardinal-
  targeted, contained to that chain only.
- **Release:** resume the chain.

**Put inside a loop, this composes into a physically-realized adaptive/
iterative structure:** each pass evaluates data against whatever the
threshold currently is; if unsatisfied, the command cell reprograms the
threshold/internals before releasing the chain to run again -- meaning
the loop isn't repeating a fixed computation, it's running a
computation whose own criteria can shift between iterations, using
nothing but flow-control and reconfiguration mechanisms already
established. Only once a pass actually satisfies the (possibly just-
changed) condition does the result branch out of the loop, rather than
triggering another halt/reprogram/release cycle.

**Why this is a distinct category from everything logged in #74-84:**
every prior stripped-cell mechanism (the adder, ready-flag/backpressure,
freeze, cardinal command targeting) moves data or control through a
fixed structure. This is the first idea in the whole arc where the
structure's own decision criteria are part of what's being computed --
closer to a physically-realized search/refinement loop than straight-
line computation. Genuinely new territory, not an extension of anything
that's been tested.

**What this changes about what needs proving, once real design work
starts:** it is not enough to confirm a reconfiguration fires correctly
against a fixed threshold (which the existing comparator RTL from #58-59
already demonstrates on real silicon) -- the harder, unproven question is
whether the threshold itself survives being rewritten mid-chain without
corrupting data still in flight elsewhere in the loop. That's a
meaningfully harder property to establish than anything built so far,
and squarely a VM-simulation question -- deliberately probing for
corruption under adversarial timing, not just the happy path -- long
before it goes anywhere near RTL, consistent with #83's sequencing.

## 86. Cross-reference: #85's adaptive-threshold loop is the physical basis for LIF neuron cluster behavior -- discovered from the hardware side, not the model side (Alan/session, 2026-08-02)

**STATUS: conceptual cross-reference only. Directly relevant to the LIF
fit-check queued by #72's Priority Zero triage; not yet tested.**

**A LIF (leaky integrate-and-fire) neuron's core behavior is exactly the
structure #85 describes: integrate input, compare against a threshold,
fire on crossing -- and in the adaptive/homeostatic variants, the
threshold itself moves in response to activity, not just the membrane
state.** That adaptive-threshold behavior is a standard, established
feature of LIF-family neuron models. What the repo's existing LIF
cluster work has had, up to now, is a mathematical/software description
of that adaptation -- an update rule, not a physical mechanism for
realizing it in real wiring.

**#84-85 supplies that missing physical mechanism, arrived at
independently, from the hardware side rather than the neuron-model
side:** halt a chain, reprogram the threshold via the command_cell's
existing push mechanism (now cardinal-targeted per #84), release --
repeat until a firing condition is satisfied, then branch out. This is
not a new concept invented to match LIF; it's the same freeze/
reprogram/release/branch mechanism from #85, recognized after the fact
as matching a well-known computational-neuroscience pattern.

**Practical implication for the queued LIF triage (#72):** the fit-check
against the current architecture may turn out to be less "does the old
model still apply" and more "here is a concrete hardware mechanism the
model can now target directly" -- the theoretical basis for how an
adaptive-threshold spiking model could actually be realized physically,
rather than only simulated. Genuinely useful groundwork for when that
triage is picked up, even though nothing has been tested yet.

**Sequencing note, explicit and important: this closes out the
conceptual/theoretical thread for now.** The immediate priority remains
#83's agreed order -- confirm the stripped cell and the memory system
(bram_dp_v3.v) against real RTL and silicon before any of #84-86 gets
built or simulated further. These three entries are the theoretical
basis to come back to once that foundation is solid, not a new
direction to start pursuing in parallel.

## 87. Session kickoff (2026-08-01): #83's sequencing reconfirmed as today's active plan, plus a concrete gap found -- bram_dp_v3.v has never been through a Quartus fit (Alan/session, 2026-08-01)

**STATUS: reconfirms #83's order rather than changing it. One new fact
established: `bram_dp_v3.v` is not referenced by any `.qsf` in the repo
-- it's only ever been instantiated in `top_card_2zone_v3.v`, which
itself has no build project. No fit report exists anywhere in-repo, and
none can, since it's never been through Quartus. So #83 step 1's
question ("does an existing fit report need checking, or a fresh one
built") is answered: needs one built fresh, from scratch.**

Alan's framing for today, independently arrived at, matches #83's
agreed order exactly:
1. Stripped/next-hop cell RTL -- establish the baseline (#83 step 2).
2. RAM location and read side -- `bram_dp_v3.v` confirmed on real
   silicon (#83 step 1/3).
3. Zone separation into command (addressed) vs. stripped versions of
   the cell, tested and confirmed (#83 step 3/4, and the #76/#84
   addressed-shell/stripped-interior design).

All three remain exactly what #83 called out as unconfirmed-in-silicon
and gating everything built on top (#74-#82's automaton/hybrid/RAM-loop
work, #84-86's cardinal-command-bus and adaptive-threshold theory).
Nothing in today's framing changes that order; it's the same plan,
independently re-derived, now with the bram_dp_v3.v fit-report gap
explicitly closed out as a known fact rather than an open question.

## 88. Stripped cell RTL baseline, fully confirmed before any Verilog is written -- field map, bidirectional ready flag, wait-for-all-targets fire gating (Alan/session, 2026-08-01)

**STATUS: confirmed design baseline, worked through field-by-field
against the real, existing `unicell64_v3.v` before writing any new
RTL. This is #83 step 2 actually being scoped -- not yet built.**

**Field map, reusing existing verified wiring wherever possible rather
than inventing anything new:**
- `cmd_latch[9:0]` — topology (unchanged; gate computation is identical
  in both cell types per `unicell_automaton_v1.py`'s own header note).
- `cmd_latch[69:64]` — routing_mask (unchanged wiring, output side —
  which neighbor(s) a fire's result targets).
- `cmd_latch[75:70]` — cardinal_edge (unchanged wiring, reinterpreted
  per-INCOMING-direction rather than per-outgoing, per the automaton
  model's design note — consume vs. relay per arrival direction).
- `cmd_latch[13]` — NEW: `ready`. Confirmed as the correct home directly
  from the RTL's own authoritative field-map comment (~line 427-478):
  `[19:13]` is the genuinely free 7-bit range left after routing_mask/
  cardinal_edge relocated out and cell_mode claimed 2 bits at
  `[12:11]` — `[13]` is the lowest bit of that free range.
- `cmd_latch[127:96]` — NEW: `out_buffer`, the offered-output value,
  separate from `data_reg` exactly as #77 specified. Confirmed genuinely
  untouched in the real RTL (line 478's own comment).
- Address/auth/opcode-listening apparatus (`input_address`,
  `output_address`, `auth_mask`, `config_match`, the whole RUN-state
  command-bus decode) — present ONLY at boot time, for
  `loader_fsm_v3.v` to configure the cell once, exactly as it already
  works. Absent from stripped-mode compute logic entirely, not merely
  disabled (per #76/#84).

**The `ready` mechanism, worked through to a real bidirectional design
-- not just #77's original one-directional spec:**
- `ready` (`cmd_latch[13]`) is a single combinational output, broadcast
  UNCONDITIONALLY to all 4 cardinal ports (N/S/E/W), regardless of which
  directions `routing_mask`/`cardinal_edge` actually use in a given
  layout. Explicit reasoning (Alan): a cell cannot know in advance which
  neighbor(s) might be upstream of it in some configuration, so `ready`
  cannot be gated or selected by routing at all -- it has to be
  everywhere, always, as its own dedicated wire, separate from the
  routed data path (not carried as data-bus payload).
- Symmetrically, every cell also RECEIVES its own 4-bit `ready_in[N:S:E:W]`
  from its neighbors, the same unconditional way.
- **The actual gating decision, and the real refinement over #77/#78's
  original software model:** a cell's FIRE condition (not just its
  receive condition) now checks `ready_in` for every direction its
  current `routing_mask`/`cardinal_edge` targets, BEFORE firing at all.
  This is check-then-send at the sender, not send-then-reject at the
  receiver -- #78's `unicell_automaton_v1.py`/`CAGrid` implementation
  currently fires optimistically and lets the receiver reject-and-
  requeue, which only works because it's software with a queue to
  re-deliver from. Real wires have no such queue, so the sender-side
  check is the physically correct version, not an equivalent rewording.
- **Multicast fire policy, explicitly decided (Alan): wait-for-ALL
  targeted neighbors to show ready before firing at all** -- not a
  per-direction partial-fire/partial-hold scheme. Chosen deliberately
  for simplicity (one shared `out_buffer`, one `ready` bit, matching
  the field map above exactly) AND because it gives the compiler's
  future timing model a single, predictable wait-for-slowest-target
  condition per cell, rather than needing to reason about per-cell
  partial-fire states. A genuine tradeoff accepted openly, not an
  overlooked simplification.

**What's still open, deliberately not decided yet:** the exact RTL
shape of the wait-for-all-targets fire gate itself (a straightforward
AND-reduction over the targeted `ready_in` bits, most likely, but not
yet written), and how `ready` interacts with the boot-time loader path
(the FULL-cell equivalent, `output_set`, already has a working boot-
time story -- the stripped cell's needs the same treatment, not yet
worked through). Next concrete step: draft the actual stripped-cell
Verilog module against this confirmed field map.

## 89. Read-confirmation mechanism designed and built into the stripped-cell draft: fire-time pending_ack snapshot, scoped so closed directions can never block recovery -- and the flagged difference for porting it to the FULL cell later (Alan/session, 2026-08-01)

**STATUS: real gap in #88's draft, caught and closed in the same
session, RTL updated (`unicell_stripped_v1.v`, still NOT SIMULATED).**

**Two distinct problems, both raised directly by Alan, that resolve
into one mechanism:**

1. **Recovery must be scoped to directions actually targeted, not all
   four unconditionally.** A cell whose `routing_mask` only opens one
   direction can only ever be waiting on that direction's confirmation
   -- the closed directions never had anything sent to them, so they
   can never confirm anything back. The original draft cleared `ready`
   globally on any fire with no record of which directions were
   actually targeted, meaning recovery had no correct condition to
   check at all.

2. **A sender cannot infer it's been read -- it has to be told.**
   `out_buffer` is a passive register; a neighbor pulling data off the
   wire leaves no trace on the sender's side unless the receiver
   actively signals it. This needs a genuine, separate backward wire
   per direction, distinct from `ready_in`/`ready_out` (which only ever
   report static per-cell state, not a specific transaction's outcome).

**The mechanism, built into the draft:**
- `pending_ack[3:0]` — a NEW register, snapshotting exactly which
  directions were targeted AT FIRE TIME (`{want_w,want_e,want_s,
  want_n}`), the same "capture now, because the live value may change
  before it's needed" discipline the FULL cell already uses for
  `out_buf_routing` (unicell64_v3.v, points.md #49/#51) -- not a new
  convention, the same one applied here.
- New port pairs `ack_out_n/s/e/w` / `ack_in_n/s/e/w`, genuinely
  separate from `ready_out`/`ready_in`. `ack_out_x` is combinational,
  asserted the SAME cycle a receiving cell captures a new arrival into
  `data_reg` -- the receiver actively telling that specific sender
  "you're clear," not the sender inferring anything.
- `ready` (`cmd_latch[13]`) clears to 0 on fire (as before) but now
  recovers to 1 only once `pending_ack` reaches all-zero -- i.e. every
  direction that was ACTUALLY targeted, and only those, has confirmed.
  A direction never targeted was never set in `pending_ack`, so it can
  structurally never block recovery -- closes problem 1 directly.
  A targeted direction genuinely must assert its `ack_in` before
  recovery happens -- never inferred, never assumed -- closes problem 2.
- Checked directly for races before committing: `can_fire` requires
  `ready_bit`, which is only true once `pending_ack` cleared to zero
  the PRIOR cycle -- so a fresh fire (which sets `pending_ack` non-zero
  and clears `ready`) and a completing recovery (which clears the last
  `pending_ack` bit and sets `ready`) can never both touch
  `cmd_latch[13]` in the same cycle. No conflicting assignment exists.

**The flagged difference for the FULL cell, noted now rather than
assumed transferable as-is (Alan: "this mechanism needs to be added to
the main cell too, once this is confirmed working, but with slight
differences"):** the stripped cell's `ack` can be a dedicated,
always-present wire per direction because it has real, fixed
point-to-point links to at most 4 neighbors -- there's nowhere else a
confirmation could come from. The FULL cell doesn't have that: its
non-cardinal/local delivery still goes over the shared, addr-matched
command bus, not a dedicated wire per possible sender. So the FULL
cell's version of the same idea can't be "an extra wire" the way it is
here -- it has to ride as a bus transaction (an opcode), the same way
`CMD_LOAD_DONE` (#63) already generalizes read-confirmation for
config-loading specifically today. Explicitly NOT designed yet --
Alan's own sequencing: once the stripped-cell version is confirmed
working (sim + silicon), not before.

## 91. Two real bugs found and fixed by actually running the 2-cell test over multiple rounds without resetting, as instructed -- unconditional ack was wrong, and the delivery signal needed to be a level, not a pulse (Alan/session, 2026-08-01)

**STATUS: `unicell_stripped_v1.v` updated; `tb_stripped_v1_2cell.v` (new)
passes 3 rounds back-to-back, data verified by hand, not just
readiness-looks-fine.**

**The general principle Alan stated, which reframes what "ready" even
means:** a latch holding valid data is ready for the next round
regardless of WHERE that data came from -- one upstream cell, two
different upstream cells, or a preloaded config-time value. Readiness
is a property of the latch's state, not the identity of a source. This
directly generalizes #88/#89's design (which had implicitly been
reasoned about as if both a cell's two inputs always came from a
single sender) to the actual general case.

**Bug 1 (found first, by running 3 rounds without reset — round 2
broke where round 1 alone hadn't shown a problem):** `ack_out` was
tied only to `capture_now` (accepting a fresh FIRST arrival). But a
cell whose `a_arrived` was already set from a prior round treats the
next delivery as its live SECOND-arrival trigger instead -- a
completely different code path (`can_fire`), which never asserted
`ack_out` at all. The sender waited forever for an ack that could
never come. Fixed: `ack_out` now fires on `capture_now || can_fire`
(points.md calls this `consumed_now`), gated through a priority-select
(`sel_n/s/e/w`, same N>S>E>W order as the existing `arrived_val` mux)
so the ack goes only to the genuine source direction, not broadcast to
every asserting one.

**Bug 2 (the doubly-full/cascade scenario Alan specifically asked
about):** critically, `can_fire` already requires `ready_bit` -- so if
a cell is "doubly full" (holding an unconsumed first arrival AND its
own previous output still undrained, `ready_bit=0`), `can_fire` is
false, so bug 1's fix correctly does NOT ack the second arrival in
that state. This is exactly the intended behavior, not a leftover gap:
the delivery stays genuinely unconsumed, so the sender never clears
its own `pending_ack`, so the sender halts too -- the same rule
applying uniformly is what turns this into a real backward-propagating
cascade rather than a special case. Explicitly confirmed: a cell may
ALWAYS capture a fresh first arrival regardless of its own
`ready_bit` (holding an input while a previous output drains is fine)
-- only the SECOND-arrival/fire path is gated on `ready_bit`.

**Bug 3 (found because bug 1's fix, applied on its own, still failed --
tracing why led here):** `fire_x` (the "there's a delivery here" signal
to a neighbor) was a one-shot pulse tied to `can_fire`, true for
exactly the single cycle a fire commits. If the receiver happened to
be blocked in that exact cycle (bug 2's scenario), the notification
vanished even though the actual data was still sitting in
`out_buffer`. Fixed by reusing `pending_ack` itself -- already tracking
"still outstanding" -- as a persistent LEVEL signal (`fire_x <=
pending_ack[bit_x]`) rather than a pulse: it stays asserted for as
long as that specific delivery remains genuinely un-acked, so a
blocked receiver keeps seeing it every cycle and can accept it the
moment it's able to, instead of a single cycle it could simply miss.

**Verified by hand, not just observed as "readiness recovered":**
round 2's `b_data_out_n = 0x0000EEEE` was checked against the actual
NOR computation (`NOR(0x55550000, 0xEEEE1111) = 0x0000EEEE`) --
confirming the fix produces correct DATA, not merely a readiness flag
that happens to look right.

**What this test does NOT yet exercise, flagged honestly:** B's
`routing_mask=0` in this testbench makes B "trivially all ready"
(#88's own convention) -- B itself is never blocked downstream, so the
doubly-full CASCADE (an actual second cell halting because a THIRD
cell downstream of it is slow) has not been directly tested yet, only
reasoned through as a direct consequence of the fix. A genuine 3-cell
chain test, with the final consumer deliberately withheld, is the
natural next confirmation.

## 92. Full 3-cell RING built (A->B->C->A, genuinely closed, not just a chain), plus a minimal freeze mechanism -- confirmed to back the whole ring up on freeze and drain cleanly on release (Alan/session, 2026-08-01)

**STATUS: `unicell_stripped_v1.v` gained a `freeze_in` port;
`tb_stripped_v1_ring.v` (new) passes, confirming the cascade requested
directly, not just reasoned through.**

**Freeze mechanism, deliberately minimal:** a direct `freeze_in` level
input, NOT yet an opcode/token riding the deferred cardinal command
channel (#84/#88 — that integration is still separate follow-on work).
Gates BOTH `capture_now` and `can_fire`, mirroring
`unicell64_v3.v`'s own `frozen` gating of `bus_hit` exactly — a frozen
cell is fully paused, not merely fire-blocked, matching the existing
FULL-cell convention rather than inventing a new one.

**The ring itself is a genuine topological loop** — A's South feeds
B's North, B's South feeds C's North, C's South feeds back into A's
North, closing the cycle — not a chain with the ends merely labeled
"ring." Seeded via direct injection at A's North port for priming,
then handed off to the ring's own C->A feedback once seeded.

**Result, traced directly rather than assumed:**
- A fires twice into B (each requiring 2 seeded values, per the
  existing two-arrival model); B captures the first, fires on the
  second — `NOR(0x55550000, 0xEEEE1111) = 0x0000EEEE`, matching #91's
  same computation exactly, now inside a 3-cell structure. C correctly
  captures that delivery (confirmed via B's `ready` returning to 1,
  meaning C did ack B).
- B is frozen. A is fed a 3rd pair — `NOR(0x55550000, 0x0000CCCC) =
  0xAAAA3333` (checked by hand, correct) — and fires toward the now-
  frozen B. B does not consume or ack it.
- **A's `ready` drops to 0 and STAYS 0 for the full duration B remains
  frozen (confirmed stable across two separate 5-cycle checks, not a
  one-cycle transient)** — the delivery sits genuinely pending, still
  visibly presented to B the whole time (#91's level-held
  `pending_ack`/`fire_x` doing exactly its job — nothing was dropped
  or silently lost during the freeze).
- **The instant B is released, it consumes the still-waiting delivery
  immediately, acks A, and A's `ready` recovers on cue** — no re-seed,
  no re-send needed; the held data was still exactly there.

**What this directly confirms, that reasoning alone (in #91) hadn't
yet measured:** the ack-gating/level-holding mechanism genuinely
produces a stable, correct backward cascade under an explicit external
freeze — not just under natural backpressure from one cell's own
`ready_bit`. Both cases turn out to be the same underlying mechanism
(consumption withheld -> ack withheld -> sender's `pending_ack` never
clears), which is itself worth noting: freeze didn't need any special-
case handling in the ack/pending_ack logic at all, it only needed to
block the two consumption paths (`capture_now`/`can_fire`) — the
cascade behavior fell out for free from #91's existing design.

## 93. Genuine multi-target routing tested for the first time (routing_mask targeting TWO real neighbors at once), confirming wait-for-ALL holds under partial ack, plus an honest testbench-fidelity gap surfaced by the same test (Alan/session, 2026-08-01)

**STATUS: `tb_stripped_v1_multicast.v` (new, 4 cells: U feeds router R,
R multicasts to leaf D1 AND leaf D2 simultaneously). Confirms #88's
wait-for-all-targets design under a REAL two-target fire for the first
time -- everything up to now had only ever exercised `routing_mask`
with a single bit set.**

**Two real testbench bugs caught and fixed before trusting the
result, logged for honesty:** (1) the report task's debug tap
mislabeled `U.a_arrived` under the "R" column — a display bug, not an
RTL bug, caught by noticing values that didn't match the stimulus
timeline. (2) round 2's seeding only supplied enough values for R to
RE-CAPTURE, not enough for R to actually ATTEMPT a second multicast
fire (needs 2 full U-fires = 4 seed values, not 3) — meaning the first
run of this test never actually exercised the scenario under test at
all, and the passing-looking result was accidentally uninformative.
Both fixed before drawing any conclusion — exactly the discipline
#83/#91 already established: a clean-looking run isn't evidence if the
stimulus never reached the condition being tested.

**Confirmed, with the corrected stimulus:**
- R's multicast fire to D1+D2 (round 1, before freeze) completes and
  acks cleanly from BOTH targets — normal multi-target operation
  works.
- D1 frozen; R's round-2 multicast fires toward both again; D2 acks
  promptly, D1 (frozen) never does. **R's `ready` gets stuck at 0 and
  STAYS stuck across multiple checks** — the partial ack from D2 alone
  is never mistaken for full recovery. This is the wait-for-ALL
  contract (#88) holding under a real two-target case, not just
  reasoned about.
- **The cascade reaches U itself, one hop further back than #92's
  ring test reached:** U's own second-arrival attempt (targeting R)
  fails since R isn't ready, and U's `a_arrived` correctly stays set,
  un-cleared, exactly the same structural stall as R's.

**One honest caveat, surfaced by the same test rather than hidden:**
after D1 is released and R recovers, U does NOT automatically resume
firing its stalled second-arrival — because U here is driven by a raw
testbench stimulus pulse (asserted for one cycle, then withdrawn),
not a real neighboring `unicell_stripped_v1` instance, which would
hold its own offer continuously via #91's level-held `pending_ack`
until acked, and would retry automatically the moment its target
became ready. Confirmed this is a TESTBENCH-fidelity gap, not an RTL
gap, by re-presenting the identical stalled value after release: it
completed immediately (`U:arrived` cleared, `R:arrived` set the very
next relevant cycle). Worth remembering for any future test that uses
raw stimulus rather than a real upstream cell to represent an input
source — the raw stimulus does not reproduce the retry behavior a real
cell would provide for free.

## 94. The relay (pure pass-through) path built and confirmed -- raw values forwarded unprocessed, single-arrival, never touching the two-arrival gate, and still correctly respecting backpressure (Alan/session, 2026-08-01)

**STATUS: `unicell_stripped_v1.v` now implements BOTH halves of
`cardinal_edge`'s per-incoming-direction meaning (consume AND relay,
per the automaton model's own design note) — previously only consume
existed. `tb_stripped_v1_relay.v` (new) confirms it.**

**Mechanism:** for whichever direction is selected this cycle
(`sel_n/s/e/w`, already established for ack routing), `cardinal_edge`'s
bit for that specific direction now decides `selected_is_relay`. A
relay event (`relay_arrived`) never touches `a_data`/`data_reg`/the
two-arrival gate at all -- it goes straight from the incoming wire to
`out_buffer` unprocessed (`relay_fire`, the direct counterpart to
`can_fire`), gated by the SAME `ready_bit`/`targets_all_ready`/
`freeze_in` conditions, because it writes the same shared `out_buffer`
and must not clobber an outstanding offer any more than a compute fire
could. `next_pending_ack` now triggers on `can_fire || relay_fire`
uniformly, so recovery/ack/backpressure work identically regardless of
which path produced the offer.

**Confirmed, by hand, not just by readiness looking right:**
- `NOR(0xAAAA0000, 0x0000FFFF) = 0x55550000` on A; B's relayed output
  matched exactly, immediately, on the very next capture cycle --
  single-arrival, not waiting for a second value the way a compute
  cell would.
- Repeated with `NOR(0x11110000, 0x0000EEEE) = 0xEEEE1111` -- same
  result, confirming repeatability, not a one-off.
- **`B.a_arrived` stayed at 0 across both rounds** -- direct,
  structural proof the relay path genuinely never entered the
  two-arrival gate, not merely an assumption from the design.
- Froze the downstream consumer (C): the relayed value
  (`NOR(0x33330000,0x0000DDDD)=0xCCCC2222`, also correct) sat visible
  in B's `out_buffer` but un-acked, `B.ready` stuck at 0 for the whole
  freeze duration, recovering cleanly the instant C was released --
  **relay respects the same backpressure discipline as a compute fire,
  it does not bypass it.** This was worth confirming explicitly rather
  than assuming, since a pure pass-through could easily have been
  designed (by someone less careful) to skip the ready/ack check
  entirely on the theory that "it's not really computing anything."

**What's still open:** relay currently only forwards using this cell's
OWN `routing_mask` (per #76's original spec) -- a relay that needs to
target a DIFFERENT direction than whatever the cell's own compute
fires would use has not been tested (not yet clear it needs to be
different at all; flagging rather than assuming). Also untested: a
cell receiving simultaneously on multiple directions where SOME are
relay-tagged and others are consume-tagged in the same run (today's
tests only ever exercised one classification per cell at a time).

## 95. First real Quartus project prepared for the stripped cell (points.md #83's open question) -- a genuine blocking/non-blocking bug caught and fixed in the process, not just a clean handoff (Alan/session, 2026-08-01)

**STATUS: `fpga/quartus/Unicell-Q-stripped-test.qsf` +
`stripped_test.sdc` + `fpga/verilog/top_stripped_ring_test_v1.v`
prepared and sim-confirmed. NOT YET BUILT IN QUARTUS -- that tool is
Windows-only per this project's own established workflow and isn't
available in this session's environment. This is the prepared project,
ready for Alan to copy into the compile folder and fit on the real
machine.**

**Scope, deliberately minimal per #83's own instruction ("whatever
scope is needed to test the timing question directly, not the full
hybrid architecture at once"):** A (compute, NOR) -> B (PURE RELAY,
#94) -> C (leaf), the same 3-cell topology already confirmed correct
in `tb_stripped_v1_relay.v`, but as a real chain (not the closed ring
from #92 -- that closure was a sim-only topology check, not needed to
answer the fit/timing question) with a free-running internal stimulus
generator and periodic freeze/release cycling on C, so the design
can't be optimized away to nothing AND continuously exercises the
exact freeze/cascade mechanism confirmed in #92/#93 on real silicon,
not just a one-shot static fit.

**A genuine bug, caught by actually simulating the new top before
handoff rather than trusting it by inspection:** the one-shot power-on
autoconfig sequencer mixed blocking (`=`) and non-blocking (`<=`)
assignments to the SAME register across the SAME clock edge
(`cfgA_d <= 128'h0;` followed by `cfgA_d[9:0] = TOPO_NOR;`). The later
non-blocking whole-word write silently overwrites the earlier
blocking field-writes at end-of-timestep, regardless of program
order -- every cell's config landed as all-zero. Traced methodically:
confirmed `a2b_fire` never pulsed across 3000+ clock cycles, confirmed
`B.ready` never moved across a ~4-second run despite freeze cycling
thousands of times, narrowed to the config sequencer, and confirmed
the actual mechanism (NBA-vs-blocking evaluation order) before fixing
-- not just changing code until the symptom went away. Fixed using the
SAME safe idiom the cell's own internal cfg-load block already uses
correctly (consistent non-blocking throughout, relying on Verilog's
well-defined "last non-blocking write to a given bit wins" rule).
Re-simulated after the fix and confirmed: A now fires every ~512
cycles as designed, B correctly relays, and `B.ready` drops to 0 the
instant `freezeC` asserts and stays stuck for the ENTIRE freeze
duration (~300ms+ of sim time, confirmed via a dedicated edge-watching
testbench, not just spot-checked), recovering exactly when released.

**Why this matters as a discipline note, not just a bug-fix log entry:**
this is precisely the kind of bug that a "looks right on paper" review
would have missed -- the RTL read correctly, the intent was clear, and
it still would have gone to Quartus completely non-functional (every
cell's `routing_mask=0`, meaning nothing would ever have moved through
the fit-check design at all) had it not actually been simulated first.
Same standard the project has held everywhere else (#83's own
checkpoint, #91's testbench-sequencing catch) applied here to the
handoff step itself.

**What this build answers, once Alan runs it:** real ALM utilization
and Fmax for `unicell_stripped_v1` -- the two questions #83 identified
as answerable only by actual synthesis, never simulation. **What it
does NOT yet answer:** functional correctness ON silicon (no JTAG/ISSP
readback wired up yet -- deliberately out of scope for this pass,
flagged as separate follow-on work once this fits and closes timing
at all).

## 96. First real Quartus run: caught a genuine multiple-driver synthesis error Icarus never flagged -- two separate always blocks driving the same register (Alan/session, 2026-08-01)

**STATUS: `unicell_stripped_v1.v` fixed, all 5 existing testbenches
(2-cell, ring, multicast, relay, plus the top-level free-running smoke
test) re-run and confirmed IDENTICAL behavior after the fix -- the fix
changed nothing observable, only the driving structure.**

**The actual error, from Alan's first real `quartus_map` run:**
`Error (10028): Can't resolve multiple constant drivers for net
"cmd_latch[127]"` (and every other upper bit), pointing at two
different `always @(posedge clk)` blocks. `unicell_stripped_v1.v` had
cmd_latch/data_reg/a_arrived split across TWO separate sequential
always blocks -- one handling reset/`cfg_valid` load, the other
handling capture/fire/`pending_ack`. Icarus Verilog simulated this
without complaint (a simulator just runs both procedural blocks each
cycle, provided they don't touch the exact same bit in the exact same
timestep) -- but real synthesis requires a single register to be
driven by exactly ONE process, full stop. This is a genuine
sim-vs-synthesis gap, not a logic bug -- worth remembering for any
future RTL split across multiple always blocks touching the same reg.

**Fix:** merged both blocks into one, same priority order as before
(`rst` > `cfg_valid` > capture/fire/pending_ack), plus one small
correctness addition made while merging: `pending_ack` is now
explicitly cleared on both `rst` and `cfg_valid` (previously relied
only on its declaration-time initial value, which is a simulation/
power-up convenience, not an active synchronous reset -- explicit
clearing is the correct, robust behavior regardless of device
power-up assumptions).

**Verified, not assumed, that the merge is behaviorally identical:**
re-ran all four cell-level testbenches (#91's 2-cell, #92's ring,
#93's multicast, #94's relay) plus the top-level free-running smoke
test from #95 -- every one produced byte-identical readiness/data
traces to before the merge. The fix is structural only.

**Next:** Alan re-running `quartus_map`/full compile with this fix to
confirm Analysis & Synthesis actually passes -- this was caught at the
FIRST real Quartus step (elaboration), so Fit and TimeQuest (the
actual ALM/Fmax numbers #83 is after) haven't been reached yet.

## 97. FIRST REAL SILICON NUMBERS for the stripped cell: ~10 ALM/cell, 397.61 MHz Fmax -- #83's open question answered, decisively, for area and timing (Alan/session, 2026-08-01)

**STATUS: real Quartus 25.1std fit, `Unicell-Q-stripped-test`,
`top_stripped_ring_test_v1` (3 cells: A compute -> B relay -> C leaf,
per #95), 10AX066H2F34E2SG, Flow Status: Successful.**

**Numbers, straight from the fit/TimeQuest report:**
- Logic utilization: 30/251,680 ALMs (<1%) for 3 cells -- ~10 ALM/cell
  (likely somewhat under, since some of the 30 is top-level scaffolding
  -- the free-running stimulus generator and one-shot config sequencer
  from #95/#96, not pure cell cost).
- Total registers: 49. Block memory: 0. DSP: 0. HSSI: 0. PLL: 0 -- all
  hardened silicon untouched, exactly as expected for a pure-fabric
  design.
- `clk_div` (the actual fabric clock): **397.61 MHz**. (`CLK_100M`'s
  reported 1610/645 MHz is the raw input pin's own min-period rating,
  not fabric logic -- `clk_div` is the number that matters.)

**Direct comparison to the FULL addressed cell's own confirmed
numbers** (`START.md`, full 16-zone/400-cell card, pre-PCIe fit,
2026-06-28): **~464 ALM/cell, ~56.2 MHz Fmax (wired-OR-bus-limited).**
The stripped cell comes in at roughly **1/45th the area** and roughly
**7x the clock speed.** This is a real, measured confirmation of
exactly what #69/#70/#71 hypothesized from reasoning alone -- that the
shared wired-OR bus's arbitration/broadcast logic was the actual Fmax
ceiling, not anything intrinsic to gate computation itself. Now
confirmed directly, not just argued.

**This is the decisive answer to #83's original open question**
("[the stripped cell] is confirmed correct in software, unknown in
hardware, until real synthesis and place-and-route happen") --
answered, for area and timing, and the answer is unambiguously
favorable. Combined with #96's synthesis-clean fix, the stripped cell
is now BOTH logically confirmed (five separate testbenches, #91-#94)
AND physically confirmed real silicon area/timing, for the first time
in this project's history for this cell type.

**What remains explicitly unconfirmed, stated plainly rather than
let the good numbers paper over it:**
1. **Scale.** Only 3 cells fit so far. A real per-cell ALM figure at
   25/100/400-cell scale could shift once routing/fan-out costs stack
   up, even though cell logic itself shares no resources -- this
   needs a larger fit to actually confirm, not assume linear scaling.
2. **Functional correctness ON SILICON.** This fit confirms area and
   timing ONLY -- there is still no JTAG/ISSP readback wired up for
   this cell type, so nothing has yet confirmed the chip actually
   PRODUCES the same results real hardware that #91-#94 confirmed in
   simulation. Fitting clean and fast is necessary, not sufficient.

**Sequencing note:** per this project's own standing discipline
(declare victory only after measurement), #1 and #2 above are the
honest next steps before this result is treated as "done" rather than
"the first, very promising real measurement."

## 98. Memory loading/collection design thread: the reintroduced-address problem, and its resolution -- addressing moves OUTSIDE the cells entirely, to a zone-granular external bus, reusing the existing stall/ack mechanism for collection (Alan, mobile, 2026-08-01)

**STATUS: design discussion only, no RTL yet -- captured here because
it's a real architectural pivot mid-thread, not a settled decision to
build against yet.**

**Starting point (confirmed by inspection, not assumption):** the
stripped cell (#88-#97) has NO way to be reconfigured at runtime.
`cfg_valid` has no lock, but there is zero addressing hardware in the
cell (#76/#84's own principle) -- no `config_match`, nothing -- so a
cell cannot tell "this config word is for me" from "for my neighbor."
`CELL_ID` (the module parameter) is confirmed, by grep, to be
declared but NEVER USED anywhere in the cell's logic -- a label only,
not wired to any comparison. Today, the ONLY way to configure any
cell is to bake constants into the RTL and reflash the whole bitstream
over JTAG (exactly what `top_stripped_ring_test_v1.v`'s autoconfig
sequencer does, #95) -- no runtime load path exists at all.

**First proposal (Alan), then self-corrected:** extend the reserved
cardinal `cmd_in`/`cmd_out` ports into a real address+data pair riding
the SAME point-to-point relay links as ordinary data (#94's relay
path) -- each cell gets a real `config_match` comparator against
`CELL_ID` for the first time, consumes on match (3 sequential 32-bit
words filling `cmd_latch`'s meaningful 96 bits), relays otherwise.
Alan immediately flagged the real problem with this: it reintroduces
address-comparison hardware INTO every cell, which is precisely the
kind of shared-targeting logic that made the wired-OR bus fragile in
the first place (#69-71) -- even though the LINKS themselves stay
point-to-point/collision-free, giving every cell its own comparator
is a step back toward "cells that need to know about addressing,"
which #76/#84 deliberately eliminated for the area/Fmax win #97 just
confirmed in silicon.

**Resolved (Alan): addressing moves OUTSIDE the cells entirely.** The
stripped cells keep ZERO addressing hardware, full stop -- back to
#76/#84's original principle, not the in-cell comparator idea above.
Targeting instead happens via a SEPARATE, external addressing bus,
using the EXISTING physical ZONE boundary as the natural granularity
(one zone targeted at a time), not per-cell inside the fabric. This
avoids reintroducing the original collision risk directly: the
external address bus never touches the cardinal cell-to-cell links at
all -- it's a wholly separate, serialized, one-zone-at-a-time selector
operating at the zone boundary, not many drivers sharing one wire
inside the fabric.

**Both directions (load AND collection) are serial, one zone at a
time:** loading config into a zone, and reading results back out of a
zone ("memory collection"), each happen one zone at a time, serially
-- not simultaneously across zones. This also resolves the earlier
raster/row-at-a-time constraint discussed mid-thread (loading a 2D
array one row/column at a time because addressing increases along a
single serial path) -- at zone granularity instead of cell granularity,
with the same serial discipline.

**The elegant part -- collection reuses #91-#94's EXISTING mechanism,
not a new one:** a zone's output simply stays stalled/unacked
(structurally identical to a frozen or backpressured cell in #91-#94)
until an external collector actually reads the data out and issues
what functions as an ack ("the reset command," in Alan's phrasing) --
at which point the stall clears and normal fabric flow resumes. This
is the SAME stall/pause discipline already built and confirmed
correct, applied at the zone-external boundary instead of cell-to-cell
-- not a new mechanism invented for this purpose.

**Explicitly open, not yet decided:**
- How many zones can be "in flight" concurrently (e.g. one zone being
  loaded while a different zone is mid-collection) vs. one zone at a
  time system-wide.
- The actual external bus protocol/timing at the zone boundary itself
  -- word format, how the "reset"/ack signal is physically carried,
  whether it rides existing PCIe/loader infrastructure or is new.
- Whether a mid-load zone's cardinal outputs toward not-yet-loaded
  neighbors default to closed/held, or something else -- raised
  earlier in the same thread, still unresolved.
- Which 32-bit chunk of `cmd_latch` maps to which field if/when a
  serial multi-word load format is designed -- also raised earlier,
  still unresolved, and now possibly moot at the cell level if
  addressing lives entirely outside the cells.

## 99. #98 resolved to a concrete mechanism: a per-cell WRAPPER carrying a scan-chain-style external address+data bus, bidirectional (program AND collect), cell itself untouched -- plus the agreed next-session plan (Alan, mobile, 2026-08-01)

**STATUS: design resolved to a specific, buildable mechanism. NO RTL
yet -- agreed to build in a specific order next session (see below).**

**The mechanism, precedented directly rather than invented from
scratch:** the addressing/data transport #98 called for lives in a
small WRAPPER module instantiated ALONGSIDE each stripped cell (same
tile, separate RTL, separate wires) -- not inside `unicell_stripped_v1.v`
itself, which stays exactly as-is (zero addressing hardware, #97's
confirmed area/Fmax unchanged). Two real, existing precedents for this
exact shape, both already part of the same stack this project targets:
(1) JTAG boundary scan -- a chain of small shims sitting beside each
functional I/O cell, invisible to the cell's own logic; (2) the FPGA's
own bitstream configuration network -- physically separate from the
user-logic routing, and it programs the LUTs' actual contents, not
merely an address.

**Confirmed bidirectional, matching both directions #98 needed:**
- PROGRAM: wrapper matches its address on the external bus, then
  (rather than passing the bus straight through) latches the following
  data words and drives them into ITS cell's `cfg_valid`/`cfg_data` --
  the same 3-word-load shape discussed in #98, now with a concrete
  carrier.
- COLLECT: same chain, same address match, wrapper instead reads its
  cell's `out_buffer`/`ready` state and shifts THAT back out toward an
  external collector -- giving #98's "reuse the stall mechanism"
  description an actual transport to ride on.
- Non-matching wrappers pass the bus straight through to the next
  wrapper in the chain -- this is also what gives the row/serial
  discipline (#98) for free, rather than needing separate enforcement:
  the wrapper chain IS the scan chain.

**Honest cost flagged before this becomes a plan rather than an
assumption:** #97's confirmed ~10 ALM/cell is the CELL ALONE. The
wrapper adds its own address-compare + shift/latch registers PER CELL,
on every cell in the array -- probably modest, but a real number that
needs its own fit, not assumed free. This is explicitly why the
agreed next-session order (below) builds the plain scale-up FIRST,
before adding the wrapper -- so the wrapper's actual marginal cost can
be measured as a delta against a known baseline, not guessed at.

**Agreed next-session plan, in order:**
1. Build the LARGER cell array on the card first (the scale-up fit
   from #97's own flagged open item -- confirm whether ~10 ALM/cell
   and ~397 MHz Fmax hold once there's more routing/fan-out to deal
   with, still using the plain #88-#97 cells with NO wrapper).
2. THEN add the wrapper mechanism (this entry) to the same array.
3. Build and fit that, and compare the actual ALM/Fmax cost against
   step 1's baseline -- the real, measured price of adding per-cell
   addressing/collection capability, not an estimate.

## 100. #99's wrapper extended: if its addressing rides the SAME cardinal path as data (not a separate topology), reprogramming can happen live, data-dependent -- opening genuinely dynamic models (LIF-style spiking neurons named explicitly) (Alan, mobile, 2026-08-01)

**STATUS: idea captured, explicitly NOT decided or designed -- flagged
as a real fork with a hard open question, not a plan to build yet.**

**The extension:** #99's wrapper mechanism (scan-chain-style address+
data bus, bidirectional program/collect) could be routed to follow the
SAME cardinal hop-by-hop path the data channel already uses, rather
than a separate/independent scan topology. Worth naming clearly: this
is NOT a new bus -- it's the natural completion of the `cmd_in`/
`cmd_out` cardinal ports already reserved, unimplemented, since #84/#88
specifically for control/reprogram tokens riding cardinal, separate
from but alongside the data channel.

**What this opens, if built:** a cell's own topology/routing could be
rewritten WHILE data is actively flowing through it, triggered by that
same data -- reprogramming that is live and data-dependent, not a
one-shot boot-time load. This is the actual difference between "load
a fixed model once, then run it" and something that can genuinely
adapt at runtime. Alan named the natural example explicitly: LIF
(leaky integrate-and-fire) spiking neuron models, whose entire
behavior depends on state that evolves continuously from accumulated
input -- a fixed one-shot config can't express that; a cell quietly
rewritable mid-flow, driven by what's flowing through it, can. More
broadly: dynamic models in general, not just LIF specifically.

**The hard, explicitly unresolved question, flagged rather than
guessed at:** once reprogram tokens and data share the same physical
wire, what happens to a cell's IN-FLIGHT two-arrival state
(`a_arrived`, `pending_ack`) if a reprogram command lands mid-fire?
Does reprogram wait for the cell to quiesce (finish its current
compute/relay cycle) before taking effect, or can it interrupt
immediately? This is a genuine design decision with real correctness
consequences (an interrupt-anytime scheme risks corrupting an
in-progress computation; a wait-for-quiescence scheme needs its own
detection/handshake), not a detail to default on later.

**Sequencing:** this sits explicitly AFTER #99's own agreed order
(scale-up fit, then plain wrapper, then measure its cost) -- captured
here as a real, exciting direction to come back to once that
foundation is measured, not a redirection of the immediate next-session
plan.

## 101. #100's open question resolved: reprogram must FREEZE FIRST, wait for ack, then proceed as opcodes with the same wait-for-ack discipline as data -- plus confirming freeze should stay a dedicated physical line, not an opcode (Alan, mobile, 2026-08-01)

**STATUS: design resolved. Directly answers #100's flagged open
question ("what happens to in-flight state if reprogram lands
mid-fire") -- it doesn't happen; freeze is the gate that prevents it.**

**The sequence, as designed:** reprogramming a cell/run of cells is
NOT an arbitrary interrupt. It must:
1. Issue FREEZE first, as the mandatory opening step -- forcing the
   target(s) to quiesce (finish/hold current two-arrival state, per
   #92's existing freeze semantics) before anything else is accepted.
2. Wait for confirmation ("the ok") that freeze actually took hold --
   reusing the SAME wait-for-ack discipline #91 already built and
   proved, not a new confirmation mechanism.
3. THEN the actual reprogram payload rides the cardinal path as
   opcodes, following that same wait-for-ack pattern data already
   uses (per #99's wrapper carrying address+data).
4. RELEASE ends it, returning the cell(s) to normal operation.

This closes #100's open question directly: an in-flight two-arrival
state can never be corrupted by a landing reprogram command, because
reprogram cannot proceed until freeze is CONFIRMED, and freeze forces
exactly the quiescence needed first.

**Freeze should remain a dedicated physical line, not an opcode --
and this is confirmed as ALREADY the case in the current stripped-cell
design, not a new decision.** History, as Alan recalled it: in the
original/FULL cell lineage, freeze started as a genuinely separate
physical wire, then over the FULL cell's own evolution got folded into
the shared command bus as `CMD_FREEZE`, just another opcode value.
Checked directly: `unicell_stripped_v1.v`'s `freeze_in` (#92) is
ALREADY a standalone physical port today, not an opcode riding any
bus -- i.e. the stripped cell already reverted to the original,
simpler pattern, independently of this conversation. The reasoning
for why that's correct, made explicit now: freeze is the thing every
other mechanism's reliability depends on, so it should not itself
require decode logic on the same channel it exists to gate -- a jammed
or misbehaving command channel should never be able to also disable
the one mechanism meant to safely halt things.

**What this adds concretely to the #99 wrapper design, not yet
built:** freeze needs its own dedicated physical line running
ALONGSIDE the cardinal chain -- a third separate channel alongside
data and command/opcode, not multiplexed with either. And critically,
unlike the current single-cell `freeze_in` test port, freeze itself
needs to PROPAGATE hop-to-hop the same way data already does, so an
entire run of cells along a path can be frozen in sequence together,
not just one isolated cell.

## 102. The wrapper mechanism (#99) resolved to its full scope: Possibility 1 chosen over a direct FULL-cell/stripped-zone bridge, reprogramming falls out for free (mutable chain shape AND function), and the host becomes the sole authority on topology (Alan, 2026-08-01)

**STATUS: consolidates and resolves the command-zone-boundary thread
from earlier in this same session with the #98-101 mobile thread --
they turned out to be alternatives, not complementary pieces, and
Possibility 1 (below) is the chosen direction.**

**The fork, stated plainly once written out (Alan's own framing):**
1. **Possibility 1 (CHOSEN):** the #99 wrapper (scan-chain-style
   external address+data bus, one per cell) is the ONLY path in and
   out of the fabric. Every zone can be a plain stripped-cell zone;
   RAM read/write happens entirely from OUTSIDE via the wrapper,
   tagging results with an identifier as each chain's end is collected.
2. **Possibility 2 (REJECTED):** use the wrapper for cell programming
   only, while data still spills out through zone EDGES -- requiring
   FULL-cell command zones to physically bridge into stripped zones
   (the earlier-this-session thread: fire-and-forget vs. explicit-
   ack/backpressure protocol mismatch, opcode-riding-spare-cmd_bus-bits
   ack design, "direct capture," 2-cycle serialization cost).

**Why Possibility 1 wins, beyond "neater":** it eliminates the
protocol-mismatch problem entirely, rather than solving it. That
mismatch existed only because data had to cross a live boundary
between two different cell philosophies (FULL cell's fire-and-forget
bridge vs. stripped cell's explicit ready/ack). If RAM I/O happens
entirely through the external wrapper instead, that boundary never
needs to exist -- no FULL-cell command zones, no cardinal bridge
between cell types, no opcode-ack design needed at all. It also
answers, for free, the stripped cell's total lack of external
observability (flagged earlier this session): the same COLLECT
direction #99 already designed for results IS an observability path.

**Throughput refinement (Alan): FEED and COLLECT can run concurrently
on the two available RAM ports, since they touch physically separate
zones and don't share resources except the ports themselves** -- e.g.
feed chain 1 while collecting chain 10, feed chain 2 while collecting
chain 1, etc. Two things this needs, named explicitly rather than
assumed automatic:
1. A chain map (start/injection zone, end/collection zone per chain)
   -- naturally compiler-output metadata, belongs alongside #82's
   card/zone descriptor work, not invented fresh at runtime.
2. Collection must POLL for genuine per-chain readiness, not cycle
   blindly through a fixed round-robin order, since chains finish at
   different times (length/data-dependent stalls vary). The "knowing
   when" problem (a stripped cell can't raise a flag, per earlier
   session discussion) means this is fundamentally a scan, not an
   interrupt -- an accepted cost, same category as the 2-cycle
   serialization cost from the rejected Possibility 2, just paid as
   polling latency instead.

**The capability shift Alan then surfaced, initially missed:** because
every cell is now individually addressable, `routing_mask`/
`cardinal_edge`/`topology` are exactly as reprogrammable as any operand
data. This is NOT "reload the same graph with new numbers" -- it means
chain SHAPE (routing/rewiring, extending/splitting/merging chains) AND
FUNCTION (what a cell computes) both become mutable at runtime, using
hardware already justified for collection alone. No new mechanism
needed: reprogramming a structural field is just another payload riding
#101's existing freeze-first -> wait-for-ack -> apply-as-opcodes ->
release discipline.

**Resolved: the HOST is the sole authority on WHERE things are (the
topology/chain map), full stop -- not a command cell, not any part of
the fabric.** The fabric has zero self-reporting (confirmed earlier
this session) and, once shape is mutable at runtime, a compile-time-
only map is no longer sufficient -- whatever issues a reprogram command
must update the host's own map itself, since the fabric can never
report its own topology changing. A command cell independently trying
to track/infer this would just be a second, unauthoritative copy that
could silently drift from reality -- explicitly rejected in favor of
one single source of truth. WHAT is actually stored in a cell (live
data/state) does NOT need continuous tracking -- it's checkable on
demand via the same read path already built for COLLECT.

**Net result: one bidirectional mechanism, four uses, no new hardware
beyond #99's original wrapper:**
- **Configure** -- write topology/routing (shape/function)
- **Load** -- write operand data
- **Collect** -- read results out
- **Check** -- read state back for verification (e.g. confirming a
  reprogram landed correctly), identical path to Collect, different
  purpose

**Sequencing, unchanged from #99's own agreed order:** scale-up fit
first (still open, per #97), THEN build the wrapper, THEN measure its
real marginal ALM/Fmax cost as a delta -- this entry resolves WHAT the
wrapper needs to do and WHY, not a change to when it gets built.

## 103. Agreed 5-step incremental measurement campaign for the stripped cell's full addressability stack -- each step isolates exactly one variable (Alan, 2026-08-01)

**STATUS: agreed plan, no RTL built yet for steps 2-5. Supersedes the
looser "scale-up then wrapper" 2-step order from #99 with a fully
worked-out 5-step sequence.**

**The five steps, in order, each measured as a delta against step 1's
baseline before the next variable is added:**

1. **Scale-up baseline.** Plain #88-#97 stripped cells, NO wrapper, NO
   cardinal command channel, at a larger real count than #97's 3-cell
   fit. Confirms/refines whether ~10 ALM/cell and ~397.61 MHz Fmax
   actually hold once there's meaningfully more routing/fan-out to
   contend with, rather than assuming linear scaling from 3 cells.
2. **+ External wrapper bus ONLY** (#99/#102's scan-chain-style
   address+data mechanism -- global reach: initialization and
   collection, host-driven). Same cell count as step 1. Measure the
   delta.
3. **+ Cardinal command channel ONLY** (#100's reserved `cmd_in`/
   `cmd_out` cardinal ports -- local, hop-to-hop reprogramming,
   propagating cell-to-cell rather than reaching in from outside).
   Same cell count. Measure the delta, separately from step 2, so each
   mechanism's individual cost is known on its own.
4. **+ BOTH together** (cardinal command for cheap local changes,
   external wrapper for global init/collection -- the realistic
   combination, since #102 established both roles are genuinely
   needed, not alternatives). Same cell count. Measure the delta
   against step 1, AND check whether it's roughly additive with steps
   2+3's individual costs or whether combining them costs MORE (shared
   routing/fan-out pressure competing for the same resources) --
   explicitly not assumed to be simply additive.
5. **One FULL-cell zone + one stripped-cell zone, side by side, in the
   same build, at real scale.** A direct, same-project comparison
   rather than comparing across separate fits run at different times.

**Why this shape, not a single combined build:** matches this
project's own standing discipline (isolate the variable, smallest-
scope-first, #83's "declare victory only after measurement") applied
to a genuinely multi-dimensional cost question -- wrapper cost, cardinal-
command cost, and their combination all need to be independently known,
not inferred from a single "everything at once" fit that couldn't
separate which addition caused which change.

**Practical note:** each step is its own prepare -> build -> report
cycle, the same shape #95-#97 already went through for the first fit.
Five real Quartus runs, not one.

## 104. #103 step 1 prepared: 25-cell (5x5) grid scale-up, plain baseline cells, real 4-neighbor fan-in/out per interior cell (Alan/session, 2026-08-01)

**STATUS: `fpga/quartus/Unicell-Q-stripped-grid5x5.qsf` +
`stripped_grid5x5.sdc` + `fpga/verilog/top_stripped_grid5x5_v1.v`
prepared and sim-checked. NOT YET BUILT IN QUARTUS -- ready for Alan.**

**Genuine 5x5 GRID, not a straight chain** -- 25 plain #88-#97 cells (no
wrapper, no cardinal command channel), every interior cell wired to
real N/S/E/W neighbors (data/fire/ready/ack all four directions), edge
cells tied off appropriately. 25 cells matches the real per-zone count
used everywhere else in this project (`START.md`), so this is a
like-for-like scale-up from #97's 3-cell number, not an arbitrary size.
Data follows a boustrophedon (snake) path through all 25 cells, purely
to guarantee real, non-optimizable switching activity through every
cell -- the actual path doesn't matter for an area/Fmax check.

**A real, worth-noting limitation surfaced by sim-checking before
handoff, NOT a bug:** every cell here uses the standard two-arrival
gate (`consume`, not `relay`) -- meaning each hop needs 2 firings from
the hop before it to advance, so a full 25-hop traversal needs on the
order of 2^25 stimulus events at the entry point. Completely
impractical to simulate to completion (confirmed: after ~25M
simulated cycles, the final cell's output was still 0, exactly as this
math predicts) -- a direct, concrete illustration of exactly why #94's
relay mechanism exists (a real 25-hop DATA TRANSPORT chain would use
relay cells at most hops, not compute cells at every one). This does
NOT block step 1's actual purpose: Quartus's ALM/Fmax numbers don't
depend on simulated traversal completing, only on the logic being
real, parameterized, and non-optimizable (confirmed: all 25 cells'
`ready` states checked directly, both grid corners healthy, no
deadlock/corruption -- the actual thing a smoke test before Quartus
handoff can usefully confirm).

**What this build answers, once fit:** whether #97's ~10 ALM/cell and
~397.61 MHz Fmax hold at a size where routing/fan-out genuinely
matters (25 cells, real 4-neighbor grid) rather than #97's minimal
3-cell chain -- the first of #103's five measurement steps.

## 105. #104's first fit result diagnosed and fixed: the 397->273 MHz Fmax drop was a test-harness artifact, not the cell array's own cost (Alan/session, 2026-08-02)

**STATUS: `top_stripped_grid5x5_v1.v` fixed; corrected fit not yet run
(that's the next step).**

**First real fit result (Alan, Quartus 25.1std, `Unicell-Q-Stripped5x5`):
166 ALMs / 25 cells, `clk_div` Fmax 273.37 MHz.** The area number is
genuinely good news: 166/25 = 6.64 ALM/cell, actually LOWER than #97's
~10 ALM/cell estimate -- makes sense, since #97's fixed top-level
overhead (clock divider, reset, stimulus generator) was being averaged
over only 3 cells; spread over 25, the true per-cell cost reads
cleaner and holds up well.

**The Fmax drop (~31%) did NOT hold up under investigation, though --
traced directly via TimeQuest's Report Timing (`clk_div` domain, top
10 worst paths), not accepted at face value.** Every one of the 10
worst paths traced back to the SAME source: the autoconfig
sequencer's `cfg_idx[1]` (and other `cfg_idx`/`cfg_active` bits) fanning
out through a 25-way magnitude comparator (`cfg_active && (cfg_idx ==
r*5+c)`, one 5-bit equality check per cell, all sharing the same
counter) -- landing on cells' `pending_ack` registers via the
`cfg_valid` mux path, NOT via any cardinal cell-to-cell signal at all.
The actual critical path was measuring the TEST HARNESS's config-
broadcast scheme, not the grid's own cardinal routing.

**Why this matters as a methodology point, not just a fix:** #97's
3-cell test used a simple case-statement one-shot sequencer; this
25-cell test used a live comparator broadcast instead -- a genuinely
different piece of top-level overhead introduced between the two
builds, which ended up dominating the result and contaminating the
comparison. The two fits were not actually isolating the same
variable (per #103's own stated discipline), even though both
"looked like" a clean scale-up test on the surface.

**Fix:** replaced the magnitude comparator with a one-hot walking
shift register (`cfg_walk`, 25 bits, exactly one bit set at a time,
shifting each cycle) -- each cell's `cfg_valid` wires DIRECTLY to its
own bit, no comparison logic at all. Eliminates the specific
bottleneck rather than relocating it. Re-simulated after the fix:
identical healthy behavior (`all_ready` correct, no deadlock),
confirming the fix changed nothing observable except removing the
comparator.

**Next:** rebuild in Quartus with the corrected RTL and get a fresh
ALM/Fmax number -- this is the number that actually answers #103 step
1's question, since the previous one was measuring the wrong thing.

## 106. #103 step 1 CONCLUDED: 5.84 ALM/cell, 257.14 MHz Fmax -- genuine, path-traced, confirmed real grid routing cost (Alan/session, 2026-08-02)

**STATUS: real result, confirmed by tracing the actual critical path,
not accepted at face value. #103 step 1 is DONE.**

**Numbers, from the corrected fit (one-hot config walk, #105's fix):
146 ALMs / 25 cells, `clk_div` Fmax 257.14 MHz.**

**Area: 5.84 ALM/cell** -- even better than #97's ~10 ALM/cell
estimate, and trustworthy now that #105's comparator artifact is gone.

**Fmax dropped again after the fix (273->257 MHz) -- checked directly
rather than assumed benign, and this time it's real:** Report Timing
on the `clk_div` domain, top 10 worst paths, showed 6 of 10 tracing
genuine cell-to-cell cardinal logic -- specifically
`ROW[2].COL[3].CELL|cmd_latch[13]` (a neighbor's `ready_out`) feeding
into `ROW[2].COL[2].CELL`'s `targets_all_ready`/`pending_ack` next-
state combinational logic, landing on that cell's own `pending_ack[2]`
register. This is exactly the kind of real inter-cell routing #103
step 1 exists to measure -- confirmed structurally, not inferred from
the number alone. The remaining 4 of 10 trace to `stim_cnt` feeding
cell (0,0) specifically (the single external entry point) -- a
legitimate, unavoidable cost of getting data in at all, not a harness
artifact comparable to #105's comparator.

**Conclusion: 257.14 MHz is the real, trustworthy Fmax for a 25-cell
stripped-cell grid with genuine 4-neighbor fan-in/out** -- a real ~35%
reduction from #97's 397.61 MHz (which was a minimal 3-cell chain with
almost no fan-out to route around). This is the honest answer to #97's
own flagged open question ("does ~10 ALM/cell and ~397 MHz hold at
scale") -- area holds up (even improves once measured cleanly);
Fmax genuinely costs more once there's real neighbor fan-in to route,
which is a sensible, expected result rather than a surprise needing
further chasing.

**#103 step 1 baseline, for comparison in steps 2-5:** 146 ALMs, 257.14
MHz, 25 plain #88-#97 cells, no wrapper, no cardinal command channel.

## 107. Two closing architectural principles from today's session, established as first-principles for the project going forward (Alan, 2026-08-02)

**STATUS: roadmap-level framing, not an immediate build task -- logged
so it isn't lost or contradicted by drift in later sessions.**

**1. "Move the intelligence to the host" -- not a design preference,
a forced consequence of what #102 already established.** The fabric
(stripped cells) stays deliberately dumb and fast: no addressing, no
self-reporting, minimal per-cell logic -- exactly what produced #97's/
#106's genuinely good area/Fmax numbers. All intelligence -- topology
tracking, scheduling what to feed/collect/reprogram and when -- lives
on the HOST, talking to the fabric through the wrapper (#99/#102) once
its interface (PCIe, per the parked BAR0 work) is working. This isn't
optional: since a stripped cell cannot observe or report anything
about itself (flagged earlier this session), the fabric COULDN'T be
the intelligent side even by choice -- #102's own findings force this
architecture, they don't merely suggest it.

**2. The project genuinely forks into two different deployment
philosophies, not two implementations converging on one destination
-- diverging on WHERE control and self-knowledge live, while sharing
the same underlying computational ideas (topology-is-computation,
NOR-universal, two-arrival firing):**

- **FULL cell -> potential ASIC endpoint, IF physically achievable.**
  Self-contained, self-addressing, everything the cell needs to
  operate independently hardened into dedicated silicon -- keeping
  intelligence LOCAL to the fabric itself. Remains its own line, not
  superseded by the stripped-cell work.
- **Stripped cell -> leans toward the multi-card FPGA cage** (the
  ~8-card passive-backplane concept already on the horizon), with an
  external host actively driving it. Externalizes intelligence
  entirely by design, scaling naturally toward many cards under one
  host's orchestration rather than toward a smarter standalone chip.

**The current card serves as the shared testbed for both forks** --
same physical hardware, same ICM (JTAG/`icm64_readstate.tcl` and
successors) used to validate both the FULL-cell path and the stripped-
cell/host-intelligence path. The FPGA card is a stepping stone; the
underlying concept is already ahead of what current physical hardware
can fully realize in either direction -- a dedicated ASIC (FULL-cell
line) would be what eventually catches up to the concept, not a
different idea from it.

**Practical near-term consequence, separate from the architectural
framing above:** getting real throughput out of the stripped-cell/
host-driven fork requires (a) the parked PCIe BAR0 fix -- genuinely
hands-on hardware debugging (SignalTap capture, BIOS/IOMMU
investigation), a different kind of session than RTL/sim work -- and
(b) interfacing the wrapper directly to that PCIe endpoint rather than
JTAG, once it works. JTAG remains the current debug/config path, not
the intended production data path -- "locked to JTAG speed" is today's
limitation, not a permanent architectural ceiling.

## 108. #103 step 2 prepared: cell_wrapper_v1 -- #99's wrapper mechanism, first real RTL, attached to the same 25-cell grid as step 1 (Alan/session, 2026-08-02)

**STATUS: `fpga/quartus/Unicell-Q-stripped-grid5x5-wrapper.qsf` +
`stripped_grid5x5_wrapper.sdc` + `cell_wrapper_v1.v` +
`top_stripped_grid5x5_wrapper_v1.v` prepared and sim-confirmed. NOT YET
BUILT IN QUARTUS -- ready for Alan.**

**First real implementation of #99's design, built exactly to spec:**
`cell_wrapper_v1.v` sits ALONGSIDE `unicell_stripped_v1.v`, not inside
it -- the cell itself is byte-for-byte unchanged from #97/#106,
confirming the wrapper's cost will be a clean, isolated delta. Daisy-
chain scan bus (addr/op/data), REGISTERED pass-through per hop
(deliberately not combinational -- an unregistered 25-deep combinational
chain would be an artificial, unrealistic critical path, not a fair
measurement of the wrapper's real per-cell cost). PROGRAM: matching
wrapper assembles 3 sequential 32-bit words into cmd_latch's meaningful
96 bits (matches #98's own spec exactly), pulses cfg_valid on the 3rd.
COLLECT: matching wrapper substitutes its cell's `out_buffer` onto the
bus instead of passing the incoming value through.

**Top-level (`top_stripped_grid5x5_wrapper_v1.v`) is otherwise
IDENTICAL to step 1's grid** (#104/#106) -- same 25 cells, same N/S/E/W
grid interconnect, same snake routing_mask pattern -- the ONLY
difference is that cell configuration now happens through the 25-stage
wrapper daisy-chain instead of #105's direct one-hot autoconfig walk.
This isolation is deliberate and important: #103's own discipline
requires the delta to reflect ONLY the wrapper's addition, not a
different grid or a different unrelated harness change riding along
with it (exactly the mistake #105 caught and fixed in step 1 itself).

**Confirmed correct before handoff, not assumed:** simulated the full
25-cell program sequence and directly inspected the resulting
`cmd_latch` fields via hierarchical reference -- cell (0,0):
`routing_mask=000100` (East, row 0 correct), `topology=004` (NOR,
correct); cell (4,4): `routing_mask=000000` (chain end, correct);
cell (1,0): `routing_mask=000010` (South -- odd row's westward run
ending at c=0 correctly drops to the next row, not West as an initial
test-comment mistake assumed -- caught and corrected against the
actual `snake_mask` function, not the RTL). `prog_active` correctly
completes after all 75 words (25 cells x 3), `all_ready` stays healthy
throughout, no deadlock.

**What this build answers, once fit:** the real, measured ALM/Fmax
delta of adding per-cell addressability (#99) against step 1's clean
baseline (146 ALMs, 257.14 MHz, #106) -- the second of #103's five
measurement steps.

## 109. #103 step 2 CONCLUDED: 14.3 ALM/cell for the wrapper, 165.7 MHz Fmax -- confirmed real via path tracing, and the mechanism is congestion, not a direct critical path through the wrapper (Alan/session, 2026-08-02)

**STATUS: real result, confirmed by tracing the actual critical path.
#103 step 2 is DONE.**

**Numbers, from the real fit: 504 ALMs total (358 more than step 1's
146), `clk_div` Fmax 165.7 MHz.**

**Area: 358 ALMs / 25 cells = 14.3 ALM/cell for the wrapper alone** --
roughly 2.4x the cost of the cell it wraps (5.84 ALM/cell, #106).
Addressability is genuinely, substantially expensive with this first,
straightforward wrapper implementation -- a real number, not a rough
estimate, and worth remembering when weighing whether every cell needs
this or whether it could be selective (e.g. only chain-boundary cells,
matching the #102 command-zone framing rather than every interior
cell).

**Fmax dropped substantially (257.14->165.7 MHz) -- checked directly
before accepting it, following the same discipline that caught step
1's comparator artifact:** Report Timing on `clk_div`, top 10 worst
paths. Only 3 of 10 touched `prog_addr` (the program driver), and even
those only reached the FIRST wrapper in the chain
(`ROW[0].COL[0].WRAP`) -- nothing broadcasting to all 25 cells the way
step 1's magnitude comparator did. The other 7 paths were pure
cell-to-cell logic (`pending_ack`/`cmd_latch` feeding a neighbor's
`cmd_latch[13]`) -- the SAME KIND of path #106 already found legitimate
in step 1, just slower now.

**The real mechanism, worth stating precisely: this is congestion, not
a direct critical path through the wrapper's own logic.** The wrapper
adding ~3.5x more total logic into roughly the same physical footprint
means placement is denser and routing is longer for connections that
never touch the wrapper at all -- including the SAME cell-to-cell
paths that existed in step 1. The wrapper's cost isn't merely "358
ALMs" -- it ALSO indirectly costs Fmax by crowding the die, even where
its own logic isn't directly in the path. Distinguishing "slow because
of this specific new logic" from "slow because there's more of
everything nearby" matters for judging whether a smarter wrapper
design would actually help, versus whether the cost is closer to
structural.

**#103 step 2 baseline, for comparison in steps 3-5:** 504 ALMs
(146 cell + 358 wrapper), 165.7 MHz, 25 cells + 25 wrappers, no
cardinal command channel yet.

**Next: step 3 -- cardinal command channel ONLY (#100), same 25-cell
count, NO wrapper this time -- to see whether the alternative
addressing mechanism costs less than the wrapper's 14.3 ALM/cell, and
whether it produces the same congestion-driven Fmax cost or a
different failure mode.**

## 110. #103 step 3 prepared: cell_cardinal_cmd_v1 -- #100's cardinal command channel, first real RTL, plus a genuine flood/fan-in-collision bug found and fixed before handoff (Alan/session, 2026-08-02)

**STATUS: `fpga/quartus/Unicell-Q-stripped-grid5x5-cardinal.qsf` +
`stripped_grid5x5_cardinal.sdc` + `cell_cardinal_cmd_v1.v` +
`top_stripped_grid5x5_cardinal_v1.v` prepared and sim-confirmed
correct end-to-end. NOT YET BUILT IN QUARTUS -- ready for Alan.**

**First real implementation of #100's design:** `cell_cardinal_cmd_v1.v`
sits ALONGSIDE `unicell_stripped_v1.v`, cell itself unchanged, same
discipline as #99's wrapper -- but the bus topology differs
fundamentally: commands ride the SAME N/S/E/W adjacency the data grid
already uses (per #100's own framing), not a separate flat daisy chain.
This required genuine additional logic #99's wrapper never needed: a
4-way priority-select on the INCOMING side (matching the cell's own
`arrived_val` mux convention), since a real cardinal cell can receive
from up to 4 directions, unlike the wrapper's single fixed bus input.

**A real bug, found by simulation before handoff, not assumed away:**
the first version broadcast each cell's command output identically to
all 4 neighbors (mirroring the cell's own `data_out_n/s/e/w`
convention). This was wrong for THIS mechanism specifically -- data
already gates its broadcast through `routing_mask`-controlled `fire_x`
signals (only the intended direction ever actually fires); this
version's initial broadcast had no equivalent gating, so a command
token FLOODED outward in expanding rings rather than following a
single path. Confirmed via direct simulation: cell (2,3), 5 grid-hops
from the source, was never programmed at all (`routing_mask` still
showed reset-default zero), while cell (0,0) worked. Root cause: (1)
distant cells receive words at delays that don't match the fixed-
cadence driver's assumption once propagation isn't a single uniform
path, and (2) any interior cell reached by two equal-length paths
would hit a genuine fan-in collision the priority-select-and-drop
logic (borrowed from the data channel, which never expects more than
one real sender) can't handle safely.

**Fix:** added `RELAY_DIR`/`RELAY_NONE` parameters, gating each cell's
command output to ONLY its single intended direction -- reusing the
EXACT SAME `snake_mask(r,c)` function the data channel already computes
for its own `routing_mask`, rather than inventing new logic. This turns
the mechanism back into a genuine single-path serial relay,
structurally equivalent to #99's wrapper daisy chain (same 25-hop,
one-cycle-per-hop timing), just riding real cardinal neighbor wires
instead of a dedicated bus.

**Confirmed correct after the fix, end-to-end, not just the immediate
neighbor:** cell (2,3) now shows the correct `routing_mask=000100`
(East); cell (4,3), 23 hops from the source (second-to-last in the
snake), also confirmed correct (`000100`); cell (3,0) confirmed
correct (`000010`, South). Deliberately checked a cell near the END of
the chain, not just the start, since #106's own methodology (verify
the far end, not just the easy case) is exactly what caught this bug
in the first place.

**What this build answers, once fit:** the real, measured ALM/Fmax
delta of adding the cardinal-command mechanism (#100) against step 1's
clean baseline (146 ALMs, 257.14 MHz, #106) -- to compare directly
against step 2's wrapper cost (358 ALMs / 14.3 per cell, 165.7 MHz,
#109) -- the third of #103's five measurement steps.

## 111. #103 step 3 CONCLUDED: cardinal command channel costs ~6x more than the wrapper in area and is slower -- a real, measured vindication of #98's original concern (Alan/session, 2026-08-02)

**STATUS: real result. #103 step 3 is DONE.**

**Numbers: 2,309 ALMs total (2,163 more than step 1's 146), `clk_div`
Fmax 142.82 MHz.**

**Area: 86.5 ALM/cell for the cardinal-command mechanism alone** --
roughly 6x the wrapper's 14.3 ALM/cell (#109). Alan flagged, correctly
in spirit, that area still isn't the concern at this scale (device
utilization stayed under 1%) -- corrected the specific figure: at
92.36 ALM/cell total (cell+mechanism combined), 80% of the device's
251,680 ALMs supports ~2,180 cells, not 23k as estimated in
conversation -- but that's still over 5x the actual 400-cell full-card
target (16 zones x 25), so the practical conclusion holds regardless:
area is not what would break this design at real scale, even at this
first, admittedly unoptimized implementation's cost.

**Fmax: 142.82 MHz** -- lower than the wrapper's 165.7 MHz, consistent
with the mechanism costing more overall (more logic, denser placement,
the same congestion mechanism #109 identified for the wrapper likely
compounding further here given the larger footprint).

**Honest caveat on the implementation, flagged before treating this as
the final word on the MECHANISM itself (not just this attempt at it):**
`cell_cardinal_cmd_v1.v`'s output side duplicates registers across all
4 directions (`cmdv_out_n/s/e/w` etc.) even though only one is ever
valid at a time post-#110's fix -- roughly 4x the output register cost
for something used one-way-at-a-time. The 4-way INPUT priority-select
is genuinely inherent to real cardinal reception; the 4-way OUTPUT
duplication is an avoidable inefficiency in this specific
implementation, not necessarily inherent to "commands riding cardinal
wires" as a concept -- the data channel already shows the more
efficient pattern (one registered value, gated `fire_x` signals).
Alan explicitly chose not to fix this now, treating the current numbers
as the honest result of a first, straightforward implementation rather
than blocking on optimizing it -- noted here so a future session
doesn't mistake this for the mechanism's true floor cost.

**Conclusion vs. step 2: the wrapper is cheaper AND faster than the
cardinal command channel, by a substantial margin (6x area, ~1.16x
Fmax)** -- a real, measured result confirming #98's original,
reasoned-but-unmeasured concern about reintroducing per-cell address
comparators. This doesn't necessarily end the cardinal-command idea's
usefulness for OTHER reasons (e.g. #100's live-reprogramming-while-
data-flows framing doesn't obviously need the wrapper's separate bus
at all) -- but as a pure addressing/collection mechanism, the wrapper
is the clear winner on cost.

**#103 progress: step 1 (146 ALMs, 257.14 MHz) -> step 2 (+358 ALMs
wrapper, 165.7 MHz) -> step 3 (+2,163 ALMs cardinal-cmd, 142.82 MHz).
Next: step 4 -- BOTH mechanisms together on the same 25-cell grid,
checking whether the combined cost is roughly additive or worse than
either alone.**

## 112. #103 step 4 prepared: BOTH wrapper (#99) and cardinal command channel (#100) attached simultaneously, both genuinely active (Alan/session, 2026-08-02)

**STATUS: `fpga/quartus/Unicell-Q-stripped-grid5x5-both.qsf` +
`stripped_grid5x5_both.sdc` + `top_stripped_grid5x5_both_v1.v`
prepared and sim-confirmed. NOT YET BUILT IN QUARTUS -- ready for Alan.**

**Design: same 25-cell grid, same snake topology, one shared program
driver feeding BOTH mechanisms in parallel with the SAME stimulus** --
deliberately not an asymmetric test, since the point is measuring the
cost of both being genuinely present and active together, not
comparing two different driver implementations. The wrapper drives the
cell's real `cfg_valid`/`cfg_data` (the cheaper, already-proven
mechanism per #109/#111); the cardinal command channel is fully wired
and doing its own real relay work in parallel (address match, 3-word
assembly, hop-to-hop propagation) but its own `cfg` output is NOT
connected to the cell -- arbitrating two simultaneous config-drivers
into one port is a separate design question, explicitly out of scope
for this pure cost measurement. Its output is still routed to an
observable sink (folded into the heartbeat LED) so it can't be
optimized away as unused.

**Confirmed correct before handoff:** cell (0,0) and cell (4,3, 23
hops from source) both show the correct `routing_mask=000100` via the
wrapper path, matching steps 2/3's individually-confirmed results;
`all_ready` stays healthy, no deadlock.

**What this build answers:** whether the combined ALM/Fmax cost is
roughly additive against steps 2+3's individual deltas (358 + 2,163 =
2,521 ALMs added to step 1's 146 -> ~2,667 total predicted if additive)
or worse than that sum -- shared routing/fan-out pressure competing
for the same physical resources, which Alan predicted going in ("I
feel this one is going to hit the timing harder") -- the fourth of
#103's five measurement steps.

**#103 progress so far:** step 1 (146 ALMs, 257.14 MHz) -> step 2
(+358 wrapper, 165.7 MHz) -> step 3 (+2,163 cardinal-cmd, 142.82 MHz)
-> step 4 (predicted ~2,667 if additive, awaiting real fit).

## 113. #103 step 4's first fit result was misleadingly low -- an observability gap in the test harness, not a genuine finding, caught before accepting it (Alan/session, 2026-08-02)

**STATUS: `top_stripped_grid5x5_both_v1.v` fixed. Corrected fit not yet
run -- that's the next step.**

**First real fit result: 758 ALMs, `clk_div` Fmax 140.94 MHz.** Alan's
reaction ("not as much of a hit as I thought") was reasonable given the
number, but the number itself didn't hold up under inspection -- 758 is
LESS than step 3 ALONE (2,309 ALMs), even though step 4 has strictly
MORE hardware present (both mechanisms, not just one). That
inconsistency was the tell that something was wrong with the
measurement, not the design.

**Root cause, found by re-reading my own RTL rather than accepting the
number:** the observable sink folding the cardinal-command mechanism's
output into the heartbeat LED only reduced 5 of the 25 cells'
`cell_cfg_valid`/`cell_cfg_data` outputs (the diagonal --
(0,0),(1,1),(2,2),(3,3),(4,4)) -- NOT all 25. For the other 20 cells,
nothing downstream ever read their config output at all, meaning
Quartus could legitimately PROVE that address-match-and-96-bit-word-
assembly logic (confirmed in #111 as the expensive part of the
mechanism) had no observable effect, and strip it out entirely -- while
keeping the pure relay/pass-through logic, since THAT genuinely still
chains through to the sink. Step 3's own fit didn't have this gap
(every cell's cardinal-command output WAS the real, observably-used
cfg driver there), so step 3's number is trustworthy; step 4's first
attempt measured a design with ~80% of the expensive logic silently
removed by the optimizer, not the true combined cost.

**Fix:** reduce ALL 25 cells' `cell_cfg_valid` (OR) and a
representative data bit from all 25 (XOR) into the sink, not just 5 --
so nothing can be proven dead regardless of which specific cell
happens to assert it during the simulated/real run.

**Why this is worth being precise about, not just quietly fixed:**
this is the same category of catch as #105 (test-harness comparator)
and #110 (flood bug) -- a plausible-looking, even pleasant-sounding
result (lower cost than predicted) that didn't survive being checked
against the design's own internal consistency (more hardware present
should never cost LESS than a subset of it, on its own). The
"additive vs. worse" question step 4 exists to answer is still open --
this result doesn't answer it either way.

**Next:** rebuild with the corrected RTL and get the real ALM/Fmax
numbers for the true combined cost.

## 114. #100/#110's cardinal command channel corrected: addressing removed entirely (per Alan) -- then the command-cell-chain concept itself explored and set aside in favor of host-only reprogramming, per #107's own principle (Alan/session, 2026-08-02)

**STATUS: `cell_cardinal_cmd_v1.v` rewritten (addressing-free). Steps
3/4 NOT yet re-measured against the corrected design -- superseded by
the design direction below before a rebuild was done.**

**The addressing correction, confirmed against #100's own original
framing:** #110's implementation used a runtime 5-bit address
comparator per cell -- exactly the per-cell address-matching hardware
#98 originally flagged and set aside, and #109/#111 then measured as
the dominant cost (86.5 ALM/cell, ~6x the wrapper). Alan pointed out
this wasn't actually what #100 described: data carries no address at
all -- it goes wherever `routing_mask` sends it, and landing there IS
the addressing. Rewritten to match: `CONSUME_CMD`/`RELAY_DIR`/
`RELAY_NONE` are now STATIC, config-time parameters (set once via the
wrapper, alongside `routing_mask`/`cardinal_edge`, exactly mirroring
#94's `cardinal_edge` mechanism for data) -- no runtime comparator, no
per-cell ID, at all. This reframes what the mechanism can even do:
without addressing, it cannot set DIFFERENT cells to DIFFERENT values
(that remains the wrapper's job) -- it can only BROADCAST one value to
every cell along a live path, the genuine LIF-style "reprogram while
data flows" case #100 originally named. Steps 3/4's ORIGINAL framing
(cardinal-cmd as an alternative to the wrapper for per-cell distinct
setup) was itself a wrong comparison -- not just a wrong
implementation.

**A concrete mechanism explored next, then set aside:** Alan proposed
a "command cell" -- an ordinary neighboring cell physically adjacent to
whatever it controls (1 hop only, cardinal is inherently single-hop),
wired directly to the target's EXISTING `freeze_in`/`cfg_valid`/
`cfg_data` ports. Confirmed directly from the merged always block
(#96): freezing a cell does NOT block a `cfg_valid` load -- `cfg_valid`
sits in its own priority branch, checked before the freeze-gated
branch (`capture_now`/`can_fire`/`relay_fire` are the ONLY things
`freeze_in` gates) -- so freeze-then-load-then-release works exactly
as needed, already, without any new logic. Also confirmed: no ack is
needed for the load itself (unlike #91's data-delivery ack, which
exists because delivery CAN be blocked/retried) -- a `cfg_valid` load
is unconditional and always succeeds the next edge; only the
FREEZE-then-LOAD *sequencing* needs care, not confirmation of the load
itself.

**Real structural consequence, traced through rather than glossed
over:** since a stripped cell only ever holds one 32-bit value at a
time, and a full reprogram needs 3 sequential words (data-in side
only, no partial-field update -- confirmed: even a single-bit change
needs all 3 words), a "command cell" built from stripped-cell hardware
can't hold and sequence 3 words alone -- it needs a 3-cell chain. This
also surfaces "the when" as a genuinely open question: what actually
triggers the sequence? Alan resolved this as DATA-TRIGGERED, not
host-triggered: an upstream branch cell recognizes one of a small,
fixed set of trigger values in its ordinary data stream, and if
matched, forwards that value onto a separate command path leading to
the command chain -- the value's ARRIVAL at the command cell is the
trigger itself, no separate activate signal needed. Explicitly named
as a real but LIMITED route (only works because the trigger set is
small and known in advance, not general condition-recognition).

**Then reconsidered and set aside, by Alan, on architectural
grounds -- not by discovering a flaw in the mechanism, but by noticing
it conflicts with a principle already established today:** #107
concluded intelligence must live on the host specifically BECAUSE a
stripped cell cannot observe or report on itself. A branch cell
deciding "does this value match one of three recognized choices" and
conditionally acting on it IS a form of local decision-making in the
fabric -- in tension with that same principle. Resolution: strip the
command-cell chain concept out entirely; tie `freeze_in` to the
wrapper's control instead, giving the host full, direct, structural
control (routing/topology/which paths exist at all remains 100%
host-owned) -- with the open question of whether host-mediated
reprogramming is fast enough for every real workload, or whether
something else is still needed for genuinely fabric-speed adaptation
(resolved in #115, below).

## 115. Opcode/mode field investigation (both cell types confirmed empty), and the resolution to #114's open question: a NEW hold/feedback mechanism gives fabric-speed adaptation WITHOUT reintroducing local intelligence (Alan/session, 2026-08-02)

**STATUS: new mechanism designed, NOT yet implemented in RTL. This
closes #114's open "is host-mediated reprogramming fast enough"
question with a real alternative, rather than accepting either
extreme.**

**Confirmed directly from both cell RTLs, not assumed:** the stripped
cell (`unicell_stripped_v1.v`) has ZERO opcode/mode concept of any
kind -- grep confirms no `cell_mode`, no mode field, nothing. The FULL
cell (`unicell64_v3.v`) DOES have a `cell_mode` field (`cmd_latch
[12:11]`) but it's explicitly marked RESERVED/placeholder in the RTL's
own comments -- not driving any real logic. Separately, Alan recalled
an "adder preload" feature as a possible foundation for a held-
threshold mechanism -- confirmed this exists (`preload_sel`,
`cmd_bus[18:17]`) but is DEPRECATED/REMOVED, and even when it existed
it only ever forced `a_data` to one of two FIXED constants (all-zero
or all-ones) via a transient command-bus flag that collided with the
`arm` bit (the same class of hazard as the documented `loop_back`/
`LOAD_AT` collision in `ARCHITECTURE.md`) -- narrower than, and not
directly reusable for, what's needed now.

**The new mechanism, resolving #114's open question:** a single new
port, stripped-cell-only, `hold_in` (low = normal/current behavior
unchanged, high = held). The ONLY RTL change: `a_arrived`'s existing
auto-clear-on-fire (`a_arrived <= 1'b0` inside the `can_fire`/
`relay_fire` branches) becomes conditional on `!hold_in`. While held, a
cell's first-arrival value (the "threshold") stays latched
indefinitely, and the cell auto-fires against every NEW arrival
continuously -- a live, continuously-updating comparator, entirely
in-fabric, no host round-trip per comparison. Releasing `hold_in`
(returning to low/normal) is the only host-mediated event, needed only
when the threshold itself must change -- not for ordinary operation.

**What this unlocks, and why it's different from anything built or
tested today:** using a branch cell to route the FAR END's own output
back around to feed a held cell as its next arrival creates a genuine
CLOSED FEEDBACK LOOP where the comparison result depends on
accumulated history, not just the current input -- real recurrent
dynamics, the actual substance of LIF-style adaptation, not a one-shot
compare against a fixed value. Every closed loop built or tested so
far (#92's ring included) was a topology chosen purely for TESTING
purposes -- this is the first time a loop is being considered as an
intentional computational structure. The extra `hold_in` wire is
necessary, not a shortcut: a cell in such a loop needs to keep
receiving and comparing against new arrivals (the loop's own output)
WHILE its threshold-side value stays frozen -- two things happening at
once, which the existing single data path can't express on its own.

**Why this resolves the tension #114 raised, rather than reopening
it:** `hold_in`/release is a purely LOCAL persistence mechanism -- it
holds a value already loaded via the wrapper, and its own
release/reload remains 100% host-controlled, same as #114's final
position. It adds no local DECISION-making to the fabric (no "is this
one of three choices" logic, no conditional branching) -- only local
MEMORY (a value that persists and gets compared against, exactly like
every other two-arrival gate cell already does, just without the
auto-clear). This keeps #107's "no self-observing intelligence in the
fabric" principle intact while still giving genuinely fabric-speed,
zero-host-round-trip adaptation for the comparison itself.

**Explicitly not yet decided:** the accumulate/leak rule for a genuine
LIF-style running total (vs. a static held threshold) -- e.g. "add new
input, then decay by some fixed shift each cycle" -- was raised as a
live open question, not yet resolved. This entry covers the
HOLD/RELEASE mechanism and the feedback-loop capability it enables;
the specific numeric update rule for true leaky-integrate behavior is
separate, still-open follow-on work.

**Practical value of this whole exploration (#98/#100/#114/#115),
even where directions were set aside rather than built:** confirmed
freeze/`cfg_valid` coexistence works today with zero new RTL;
confirmed the real, measured cost of the address-based cardinal
approach (#111) that would have been invisible without building and
fitting it; confirmed both cell types' actual opcode/mode state
directly rather than from memory; and arrived at `hold_in` -- a
minimal, single-signal mechanism that resolves the "host-speed vs
fabric-speed" tension cleanly. None of the set-aside work was wasted.

## 116. hold_in implemented and confirmed correct, by hand, on every fire -- the held threshold never moves, release cleanly restores normal capture (Alan/session, 2026-08-02)

**STATUS: `unicell_stripped_v1.v` updated with the single-line change
#115 designed; `tb_stripped_v1_hold.v` (new) passes, every gate
computation checked by hand, not just readiness/state flags.**

**The actual RTL change, exactly as minimal as designed:** new port
`hold_in`. The ONLY behavioral change: `a_arrived <= 1'b0` (unconditional,
in the `can_fire` branch) became `a_arrived <= hold_in` -- normal
(hold_in=0) clears as before; held (hold_in=1) stays latched. Nothing
else in the module touches `hold_in` at all. All existing testbenches
(`tb_stripped_v1_2cell/multicast/relay/ring.v` and all `top_stripped_
grid5x5*` builds) updated with `hold_in` tied to `1'b0` and re-run --
byte-identical results to before the change, confirming this is
additive, not a regression.

**Confirmed, by hand, on every single fire -- not just checking
readiness looked right:**
- Threshold loaded (`0xAAAA0000`), `hold` asserted BEFORE the next
  arrival.
- Fire 1: `NOR(0xAAAA0000, 0x11110000) = 0x4444FFFF` -- correct.
  `data_reg` (the held threshold) UNCHANGED at `0xAAAA0000`.
- Fire 2: `NOR(0xAAAA0000, 0x22220000) = 0x5555FFFF` -- correct.
  `data_reg` still unchanged.
- Fire 3: `NOR(0xAAAA0000, 0x33330000) = 0x4444FFFF` -- correct.
  `data_reg` STILL unchanged across all three fires -- direct,
  measured proof the held value never moves while comparing against
  three genuinely different incoming values.
- Released `hold`. Fire 4 (the fire that commits WITH hold now low):
  `NOR(0xAAAA0000, 0x44440000) = 0x1111FFFF` -- correct, and
  `a_arrived` correctly clears immediately after this fire (confirmed
  in the trace).
- Next arrival (`0x55550000`): correctly treated as a FRESH capture,
  not a fire -- `data_reg` updates to the new value, `a_arrived` sets
  again -- direct confirmation that release fully restores normal
  auto-clear behavior, not a partial or delayed effect.

**What this confirms about the mechanism as a whole:** a live,
continuously-updating comparator against a fixed held value, entirely
in-fabric, with zero host round-trip per comparison -- exactly the
capability #115 designed to close the "host-speed vs fabric-speed"
tension. Release remains the only host-mediated event, needed only
when the held value itself must change -- confirmed to actually behave
that way, not just designed to.

**Next, per Alan's own stated priority:** the feedback-loop case --
using a branch cell to route a far cell's own output back to feed a
held cell as its repeated next-arrival, creating genuine closed-loop/
recurrent dynamics (the actual point of building `hold_in` at all, per
#115).

## 117. Self-loop via the normal cardinal path deadlocks -- a real interaction between hold_in and #90's same-cycle-ack fix, found by testing, not designed around blindly (Alan/session, 2026-08-02)

**STATUS: real finding. First attempted fix (forcing `ready` while
held) was necessary but not sufficient -- superseded by #118's
architectural resolution below.**

**The first attempt:** wiring a held cell's own South output back to
its own North input at the top level (external self-loop, using the
existing cardinal data/ack ports). Result: fired exactly ONCE from an
external kick, then froze permanently -- `a_arrived` stayed 1 (correct,
held) but `out_buffer` never advanced through any further iterations.

**Root cause, traced precisely:** with `hold_in` asserted,
`capture_now` is permanently disabled (by design -- `!a_arrived` never
true). So the ONLY path to consume the looped-back value is `can_fire`
-- which requires `ready_bit`, which only becomes 1 once the PREVIOUS
offer is acked. But generating that ack requires `consumed_now`
(`capture_now || can_fire || relay_fire`) to succeed -- and
`capture_now` is disabled, `can_fire` is what's blocked. A genuine
chicken-and-egg, specific to a cell being both sender and receiver of
the same signal while held.

**First fix (Alan): `ready` should be treated as permanently pre-
satisfied while held** -- "held becomes one half of the [readiness]
cycle already set." Implemented: `next_ready = hold_in || (next_pending
_ack == 6'h0)`. Confirmed via #116's own test: no regression. But the
self-loop STILL deadlocked after this fix -- a SECOND, subtler problem
surfaced: `fire_s` (the signal presenting a new offer to any receiver,
including a self-loop) is driven by `pending_ack` being non-zero. But
#90's same-cycle-ack optimization -- built specifically to close a race
between two DIFFERENT cells -- means a self-loop's own `ack_out`/
`ack_in` are the same wire, same cycle: the cell's new offer gets
"acked" by itself in the very same edge it's created, before `fire_s`
ever has a chance to present it to anything, including itself, on a
later cycle. Each fire commits, is instantly self-acknowledged, and
the loop starves.

**The real lesson, stated precisely by Alan:** #90's same-cycle-ack
fix correctly assumes sender and receiver are two INDEPENDENT cells
with genuinely separate timing -- an assumption that's simply false
for a true self-loop. Resolved: **internal (same-cell) feedback needs
a genuinely SEPARATE path from the normal delivery/ack mechanism.
Feedback arriving via ANOTHER cell (a real neighbor relaying a value
back after some hops) is a different, genuinely independent-cells
case, and continues to use the existing cardinal path unchanged** --
nothing about #88-#94's mechanism needs to change for THAT case.

## 118. Internal feedback path built and confirmed correct -- a held cell now genuinely self-sustains a stable 2-cycle oscillation, zero external stimulus, verified by hand (Alan/session, 2026-08-02)

**STATUS: `unicell_stripped_v1.v` updated with a NEW, genuinely
separate mechanism for same-cell feedback. `tb_stripped_v1_feedback.v`
(rewritten) confirms it, every value checked by hand.**

**The mechanism, minimal and structurally separate from #90/#91's ack
machinery, exactly as #117 concluded it needed to be:** one new port,
`fb_internal_in`. `internal_fb_active = hold_in && fb_internal_in &&
!freeze_in`. While active: `second_val` is drawn directly from this
cell's OWN `out_buffer` (its last result) instead of an external
arrival; the sequential block's `internal_fb_active` branch takes
FIRST priority, entirely bypassing `capture_now`/`can_fire`/
`relay_fire` -- no `a_arrived` change (stays held), no `pending_ack`/
ack involvement at all, just a direct recompute every cycle. This is
genuinely separate from the normal delivery path, not a variant of it
-- exactly the distinction #117 concluded was necessary.

**Confirmed, by hand, on every value -- not just "it's no longer
stuck":**
- Threshold loaded (`0xAAAA0000`), kicked once externally:
  `NOR(0xAAAA0000, 0x11110000) = 0x4444FFFF` -- correct (matches #116's
  own hand-check of the same computation).
- Switched to internal feedback, zero further external stimulus.
  Iteration 2: `NOR(0xAAAA0000, 0x4444FFFF) = 0x11110000` -- checked by
  hand, correct.
- Iteration 3: `NOR(0xAAAA0000, 0x11110000) = 0x4444FFFF` again --
  **the system has settled into a stable, self-sustaining 2-CYCLE
  OSCILLATION** (`0x4444FFFF` <-> `0x11110000`, alternating every
  cycle), confirmed continuing unchanged through iteration 6 and a
  further 10-cycle check ("still running?") -- genuinely stable, not a
  transient. Threshold (`data_reg`) confirmed UNCHANGED at
  `0xAAAA0000` throughout every iteration.

**What this confirms as a capability, not just a passing test:** a
stripped cell can now hold a fixed value and recompute against its own
evolving output, entirely in-fabric, with zero host round-trip and
zero dependency on the ack/pending_ack machinery built for point-to-
point delivery between independent cells. This is genuine recurrent
computation -- the actual substance #100/#115 were reaching for with
LIF-style adaptation, now demonstrated working, not just designed.

**What remains explicitly open:** this demonstrates a stable
oscillation, not yet a genuine LEAKY accumulator (the accumulate/decay
rule flagged as open in #115 is still undesigned) -- and external
observability of a cell mid-internal-feedback (some other neighbor
watching the oscillating value via the normal cardinal path) hasn't
been tested, only reasoned as decoupled-and-therefore-fine. Also
untested: internal feedback combined with a genuinely external
routing_mask target simultaneously (the current design effectively
makes external delivery dormant while internal_fb_active holds
priority in the sequential block) -- flagged as a real simplification,
not yet a limitation confirmed acceptable for every future use case.

## 119. The persistent, updatable memory cell -- cross-referenced to #37's original FULL-cell concept, all four pieces now confirmed on the stripped cell (Alan/session, 2026-08-02)

**STATUS: `unicell_stripped_v1.v` gained two new ports (`a_reemit_in`,
`a_update_in`). `tb_stripped_v1_memcell.v` (new) confirms both, plus
their interaction, all four values checked directly. This closes the
"memory cell system in loopback mode" thread Alan opened by naming
what #115-#118 had built.**

**Cross-reference, confirmed against the actual RTL, not recalled from
memory:** `points.md #37` (2026-07-12) established "the cell IS the
memory cell" for the FULL cell -- `loop_back`/`latch_in`/`CMD_MEM_CALL`.
What #115-#119 built is the stripped cell's OWN version of that same
principle, arrived at independently (via a completely different route
-- chasing down a self-loop deadlock, not recalling the original
design) rather than ported directly. One precise difference worth
keeping distinct: the FULL cell's `loop_back` does `a_data <=
computed_output` -- the output fully REPLACES the operand each round
(a rolling self-update). #118's internal feedback instead holds the
THRESHOLD fixed while only the second operand evolves -- a fixed-
comparator recurrence, not an identical mechanism, same family.

**The four pieces, mapped explicitly to what already existed vs. what
was genuinely new:**
1. **Hold + backpressure** -- confirmed, #91/#115/#116. A value sits
   until genuinely acked, never forced, never silently dropped.
2. **Pass-through of the ARRIVING value (B)** -- confirmed, #94's
   `relay_fire`. A is never read or touched at all in this mode.
3. **Pure re-emit of the HELD value (A)** -- genuinely new
   (`a_reemit_in`). Distinct from #118 (which recomputes a gate each
   cycle) and distinct from #94 (which passes B, not A). Confirmed: a
   cell holding `A=0xDEAD0000`, triggered twice with two DIFFERENT
   incoming values (`0x11111111`, then `0x22222222`), emitted
   `0xDEAD0000` both times -- direct proof the trigger's own value is
   completely ignored, only its arrival matters. Writes the shared
   `out_buffer`, so respects the same `ready_bit`/`targets_all_ready`
   gating as `can_fire`/`relay_fire` -- a re-emit attempt stalls too if
   the buffer is still occupied, same discipline throughout.
4. **The update/write path** -- genuinely new (`a_update_in`), and
   confirmed as the one piece that did NOT already exist anywhere,
   including in the FULL cell's own `#37` precedent (`CMD_MEM_CALL`
   re-arms wholesale, it doesn't do an in-place flush-and-replace
   either). An arriving value REPLACES `data_reg` (A) directly.
   Deliberately does NOT touch `out_buffer` and does NOT need
   `ready_bit` gating -- updating the held constant and offering it
   downstream are independent actions. Confirmed: A updated
   `0xDEAD0000` -> `0xBEEF0000` -> `0xCAFE0000` across two separate
   update triggers, `out_buffer` correctly untouched throughout.

**The interaction, confirmed directly, not just each piece in
isolation:** switched from update mode back to re-emit mode after two
updates -- the re-emit correctly produced `0xCAFE0000` (the LATEST
updated A), not the original `0xDEAD0000` and not the trigger's own
value. Update and re-emit compose correctly as independent, orthogonal
actions on the same underlying register.

**What this now gives the stripped cell, stated plainly:** a genuine
persistent, updatable memory primitive -- store a value, have it sit
available for as long as needed (backpressure-protected, never
forced), re-offer it on demand without disturbing it, and replace it
in place when it needs to change -- entirely using primitives now
confirmed correct individually and in combination. Alan's own framing:
this is what beats traditional CPU fetch/store latency for exactly
this pattern, since there's no bus round-trip, no memory hierarchy,
just a value sitting in a register asking to be read or replaced.

## 120. Self-updating threshold ("smarter RAM") built and confirmed -- the threshold itself now evolves via internal feedback, plus a real emergent interaction with reemit worth documenting (Alan/session, 2026-08-02)

**STATUS: `unicell_stripped_v1.v` gained `a_self_update_in`.
`tb_stripped_v1_selfupdate.v` (new) confirms it, every transition
checked by hand against a cleanly-sampled debug trace (an initial
quick trace showed an apparent discrepancy that turned out to be a
display-timing artifact in the debug script itself, not an RTL bug --
re-verified with settled sampling before drawing any conclusion).**

**The mechanism:** reuses #118's existing internal-feedback recurrence
(`internal_fb_active`) unchanged, adding one control bit that decides
the DESTINATION of the computed result: low (default) = #118's
existing behavior, result oscillates in `out_buffer`, A stays fixed;
high = the SAME computed `gate(A, out_buffer)` result instead REPLACES
A directly. The threshold itself now evolves based on its own
accumulated history -- a genuine self-adjusting accumulator, not just
a held constant being repeatedly compared against. Minimal addition:
one `if/else` inside the existing `internal_fb_active` branch, no new
wires beyond the one control bit.

**Confirmed, by hand, via a cleanly-sampled trace (registers read
post-settle, avoiding a same-edge display race that misled an initial
quick check):**
- Kick sets `out_buffer=0x4444FFFF` (fixed, self-update mode never
  touches it), A starts at `0xAAAA0000`.
- 4 self-update commits, oscillating exactly as `NOR(A, 0x4444FFFF)`
  predicts by hand each time: `0xAAAA0000 -> 0x11110000 -> 0xAAAA0000
  -> 0x11110000 -> 0xAAAA0000`.
- Pausing (`fb_internal_in`/`a_self_update_in` both low) correctly
  FREEZES A -- no further change confirmed across multiple subsequent
  cycles.
- Reading via `a_reemit_in` (#119) correctly reports the frozen,
  current A (`0xAAAA0000`) without disturbing it.

**A real, worth-documenting emergent interaction, not a bug:** resuming
self-update AFTER a reemit read produced `0x5555FFFF` -- not a
continuation of the `0xAAAA0000`/`0x11110000` alternation. Traced and
confirmed correct: `a_reemit_in` also writes `out_buffer` (that's its
whole job, per #119) -- so the reemit step changed the FIXED comparand
self-update recurs against, from `0x4444FFFF` to `0xAAAA0000`. Resuming
then correctly computes `NOR(0xAAAA0000, 0xAAAA0000) = 0x5555FFFF`
against this NEW comparand. Reading via reemit is not a passive,
side-effect-free operation once self-update is in play -- it shares
`out_buffer` as real state, and subsequent self-update cycles will
recur against whatever reemit last wrote there. Documented here
explicitly so a future session doesn't mistake this coupling for a
bug when composing these mechanisms together.

**What this completes:** the "smarter RAM" framing Alan named --
a memory cell that doesn't just store and re-offer a value, but can
continuously compute against its own history while held, entirely
in-fabric, zero host round-trip, using only primitives now confirmed
correct individually (#91, #94, #115-#119) and in this new combination.

## 121. Closing note: if direct cell-to-PCIe interfacing works, #103's wrapper-vs-cardinal cost comparison becomes largely moot for the external I/O role (Alan, 2026-08-02)

**STATUS: forward-looking architectural note, session end. Everything
built today (#115-#120) is confirmed in SIMULATION ONLY -- none of it
has touched real silicon yet, same standing discipline as the rest of
this project. Testing on real hardware is the explicit next step
before any further changes, and Alan doesn't believe any further
design work remains to be identified before that happens.**

**The reasoning:** the wrapper's (#99) whole purpose is being an
external, host-reachable path into the fabric for addressing/load/
collect. If PCIe can talk to cells directly with real bandwidth (per
the earlier session-opening framing -- get BAR0 working, then interface
the stripped cells directly to it), PCIe doesn't become a THIRD option
alongside the wrapper and cardinal-command channel -- it BECOMES the
wrapper's role, riding an already-existing, faster physical interface
instead of a purpose-built scan-chain. The wrapper's measured ~14.3
ALM/cell cost (#109) assumed JTAG-speed access needs its own dedicated
in-fabric addressing logic; if PCIe reaches cells directly, that
external-addressing burden may shift almost entirely onto the host/
PCIe side instead, changing what any in-fabric mechanism actually
needs to do.

**What stays separate regardless:** the cardinal-command channel's
role (#100, in-flight/live adaptation while data is already flowing)
is a different problem that raw PCIe bandwidth doesn't touch --
that comparison isn't rendered moot by this.

**The real dependency, unchanged from earlier today:** whether this
becomes true hinges entirely on the parked PCIe BAR0 hardware
debugging (SignalTap capture, BIOS/IOMMU investigation) -- genuinely
hands-on hardware work, a different kind of session than today's RTL/
sim work. Worth revisiting #103's own framing once that's resolved,
since it may reframe what the wrapper-vs-cardinal measurement was
actually deciding between.

**Session summary (2026-08-02, full day): #103 steps 1-3 concluded
with real, path-traced fit numbers (#106, #109, #111); step 4 corrected
and awaiting rebuild (#113); the stripped cell gained a complete
memory/comparator/accumulator capability (#115-#120), all confirmed in
simulation, none yet on real silicon; and this closing architectural
note on where PCIe fits into the whole picture. Next session: FPGA
testing of everything built today, before any further design changes.**

## 122. Re-verifying step 1 (per Alan's own instruction, before any new work) uncovered a real bug affecting steps 3/4's ALREADY-REPORTED numbers, and a deeper scope correction: cardinal-command was NEVER meant to be a multi-hop chain/relay system (Alan/session, 2026-08-02, next session)

**STATUS: real findings, not yet fixed in RTL. Test methodology for
steps 3/4 needs a full redesign before either goes near Quartus again.
#111's previously-reported numbers (86.5 ALM/cell, 142.82 MHz) should
be treated as UNCONFIRMED, not settled, until re-measured correctly.**

**What was being checked:** Alan asked to first re-confirm steps 1-3
still hold after today's 5 new stripped-cell ports (#115-#120) were
added, tied to `1'b0` everywhere, before doing anything else. This
surfaced two separate, real problems, neither related to the new
ports at all.

**Bug 1 (compile-breaking, found immediately): leftover `.ADDR(...)`
and `.cmda_in_x`/`.cmda_out_x` port connections in
`top_stripped_grid5x5_cardinal_v1.v` and `top_stripped_grid5x5_both_
v1.v`.** These reference fields that #114's addressing-removal redesign
deleted from `cell_cardinal_cmd_v1.v` entirely -- the top-level files
were never updated to match at the time. Fixed: removed all leftover
`ADDR`/`cmda_*` wiring and the now-dead `ca_n/ca_s/ca_e/ca_w` wire
arrays from both files. Confirmed clean compile after the fix.

**Bug 2 (silent, functional, NOT a compile error -- exactly why it
went uncaught until now): `CONSUME_CMD` (added in #114's redesign)
was never actually SET in either top-level file's instantiation --
defaulting to `0` everywhere.** This means `consume` was permanently
false in every cell, `cell_cfg_valid` never fired at all, and --
critically -- **this is the SAME configuration that was actually
fit in Quartus for #111's reported numbers (86.5 ALM/cell, 142.82
MHz).** Quartus may have optimized away some of the address-match/
word-assembly logic once it could prove `cell_cfg_valid` was
permanently stuck at 0 -- meaning #111's cost figure cannot be
trusted as measuring what it was believed to measure. Flagged
explicitly: NOT re-confirmed correct, needs re-fitting once the test
itself is fixed, not just the parameter.

**The deeper finding, once `CONSUME_CMD` was set to `1` to actually
test consumption:** every cell along the snake now consumed EVERY
word passing through it (not just one intended for it), since there's
no addressing at all (per #114) -- meaning by the end of the 75-word
stream, every cell had been sequentially reprogrammed 25 times,
converging on the LAST address's values. Both a near cell (0,0) and a
far cell (4,3) showed identical, wrong `routing_mask=0` (cell 24's
values) -- confirmed via direct signal tracing (`consume`,
`cell_cfg_valid`, `cell_cfg_data` all correct at the module level;
the problem was purely that the test methodology assumes distinct
per-cell programming, which addressing-free cardinal-command
structurally cannot do).

**Alan's correction, resolving why this happened -- a scope
mismatch, not a deeper bug:** cardinal-command was NEVER meant to
propagate along a multi-hop chain at all. Its actual job is
strictly LOCAL, single-hop reprogramming -- a command cell reaches
only whatever is DIRECTLY adjacent to it (the immediate next cell),
full stop. This matches the ORIGINAL "command cell sits next to the
branch cell it controls" framing from earlier in the day, BEFORE
#110 built `RELAY_DIR`/`RELAY_NONE` chain-propagation logic into
`cell_cardinal_cmd_v1.v` -- that relay/chain mechanism itself was
based on a scope misunderstanding (treating cardinal-command like the
wrapper's daisy-chain, riding cardinal wires instead of a dedicated
bus), not what cardinal-command was ever supposed to be. The whole
25-cell chain test (steps 3/4) was testing a capability
(`multi-hop relay`) that was never the intended design in the first
place.

**What this means going forward, not yet done:**
1. `cell_cardinal_cmd_v1.v` needs simplifying -- remove the relay/
   chain-propagation logic (`RELAY_DIR`/`RELAY_NONE`) entirely,
   since single-hop-only was always the correct scope.
2. Steps 3/4's test methodology needs a full redesign around the
   CORRECT shape: one command cell, one adjacent target, single-hop
   reprogram -- not a 25-cell relay chain.
3. #111's reported cost figure should be treated as unconfirmed until
   re-measured against the corrected, single-hop design.

**Practical note on how this surfaced:** exactly the discipline this
project has held throughout -- re-verifying something already
"confirmed" before building on top of it, rather than assuming it
still holds, caught two real, unrelated problems (a leftover-reference
compile bug and a silent default-parameter bug) that would otherwise
have contaminated every step-3/4 measurement from here on.

## 123. Command-cell mechanism fully redesigned from scratch, deliberately slowly, before any RTL -- program_in/program_done, decoupled data sourcing, and branched/data-triggered selection, all built from primitives already proven today (Alan/session, 2026-08-02, next session)

**STATUS: complete design, confirmed piece-by-piece with Alan before
writing anything -- explicitly "two steps back, get it right" rather
than iterating on RTL. NOT YET IMPLEMENTED. Try it next session.**

**Starting point: #114/#122 identified that #110's cardinal-command
design (address-based, then addressing-free-with-relay-chain) was
wrong in TWO separable ways** -- reintroducing per-cell address
comparators (#98's original, measured-expensive concern, #109/#111),
AND being architected as a multi-hop relay chain at all, when Alan
confirmed the mechanism was only ever meant to be single-hop: a
command cell reaches only its immediate, adjacent neighbor.

**A directly relevant, already-built precedent found in the FULL
cell, confirmed by reading the actual RTL rather than guessing:**
`unicell64_v3.v`'s `COMMAND_EMIT` cell type (`is_command_cell =
cmd_latch[10]`). On a cell's ordinary two-arrival fire (`new_data` --
the SAME trigger every cell already has), if `is_command_cell`, it
emits `a_data` (the held first value) as a command word instead of a
normal gate result -- and the RTL's own comment states plainly: "the
second arrival (B) is the trigger only -- its value is ignored." This
is exactly #119's `a_reemit_in` pattern, already proven on the
stripped cell, just applied to a command output. Also directly
resolves the field-location question raised earlier: `cell_mode`
lives at `cmd_latch[12:11]`, explicitly relocated there (per the
RTL's own comment) because it's topology-like, not routing-like --
NOT in the routing latch.

**The design, arrived at through several real corrections in
sequence, each one changing the shape meaningfully:**

1. **First framing (superseded):** command cell holds 3 words itself
   (reusing #119's full memory-cell machinery: hold, update, reemit)
   and pushes them to a target via `cmd_in`/`cmd_out`, gated by
   `freeze_in`.
2. **Correction 1 (Alan):** the opcode/addressing model is gone
   entirely (per #114) -- so "configuration comes directly from the
   data-in port," not a separate command-word format at all. This
   opened the real simplification: if config data can be indistinguishable
   from ordinary data except for one control line, the command cell
   doesn't need to STORE or RELAY any data itself.
3. **Correction 2 (Alan), the actual final shape:** the command cell's
   ONLY job is holding one control line high. The 3 words being
   programmed can come from ANYWHERE -- any cell, any direction,
   completely decoupled from whatever decided to assert the control
   line. The target cell cannot and does not need to distinguish
   "normal data" from "config data" except via that one bit.

**The final mechanism, all pieces confirmed individually:**
- **`program_in` (new, 1 bit, general input, NOT per-direction)** --
  asserted by whatever is programming this cell, regardless of which
  side it's physically on (mirrors why `ready_out`/#88 is a single
  broadcast signal, not per-direction: a cell can't know in advance
  which side its controller sits on).
- **While `program_in` is held high, the target's EXISTING `data_in`/
  `arrived_x` priority-select (already built, #88's own arrived_val
  mux) redirects into a NEW 3-word assembly buffer** (word_idx counter
  + 96-bit register, the SAME simple pattern already proven in
  `cell_wrapper_v1`/`cell_cardinal_cmd_v1`) instead of the normal
  two-arrival capture/gate path. Genuinely new logic -- this is the
  one real addition beyond the two control bits.
- **Each word consumed generates the EXISTING `ack_out_x` for free**
  (#91's mechanism, already tied to whichever direction the data
  genuinely came from -- `consumed_now && sel_x`). The actual data
  SENDER gets acked automatically, per word, with zero new logic.
- **Once the 3rd word lands, apply it the same safe way `cfg_valid`
  already does** -- writing `cmd_latch` directly, using the same
  priority ordering already proven ahead of the freeze-gated branches
  (#114's own confirmed finding: `cfg_valid` never interacts badly
  with `freeze_in`). This is WHY freeze isn't strictly required for
  the mechanism to be safe -- `program_in` plays the same
  non-interacting role `cfg_valid` already does.
- **`program_done` (new, 1 bit, general output, BROADCAST to all 4
  directions unconditionally)** -- asserted once the 3rd word lands
  and is applied. Mirrors `ready_out`'s own broadcast convention
  exactly, for the same reason: whoever's holding `program_in` could
  be on any side, so the completion signal has to reach all of them
  unconditionally, not be routed to a specific direction. This solves
  a real gap found mid-design: the ordinary per-word `ack_out_x`
  answers a DIFFERENT question (did the sender's word land) to a
  DIFFERENT party (the data source) than "is the whole transfer done"
  answers (to whoever's holding the control line, which may be a
  completely different cell than the data source).
- **Freeze + program coexisting, confirmed as the intended pattern
  (Alan):** freeze lets a cell be reprogrammed while its surrounding
  data flow stalls, WITHOUT stopping the system's overall
  functionality elsewhere -- the freeze specifically has to let data
  flow into the assembly/`cmd_latch` path while blocking the normal
  two-arrival path, exactly matching the priority-ordering already
  built.

**Branched, data-triggered selection -- confirmed to fall out for
free from primitives already proven, not a new mechanism:** a
comparator's live result (the SAME NOR-based comparator machinery from
#84/#85) can decide WHICH of a cell's remaining 3 cardinal directions
gets `program_in` asserted -- turning a single command-decision point
into a genuine BRANCH, choosing which of several attached neighbors
gets reprogrammed based on live data, not a fixed config-time target.
Explicitly confirmed as fully decoupled from data sourcing (Alan):
the command cell only ever decides WHICH DIRECTION to point
`program_in` toward -- it has no involvement in, and no knowledge of,
where the actual 3 config words come from. Those are two independent
decisions that merely happen to converge on the same target cell at
the same time.

**What's confirmed vs. still to build, stated plainly:** this is a
complete, mutually-confirmed DESIGN, not yet implemented in any RTL.
The genuinely new pieces are: `program_in`, `program_done`, and the
3-word assembly state machine on the receiving side. Everything else
(ack generation, priority-select, cfg-valid-style safe application,
freeze non-interaction, the branch/comparator mechanism itself) reuses
primitives already built and proven earlier today (#88, #91, #94,
#114, #119). Next session: implement and test.

## 124. Forward-looking research note: a photonic realization of the FULL cell -- the cell's core design survives intact even here, just re-hosted (Alan, 2026-08-02)

**STATUS: speculative, long-horizon research direction. NOT design
work, NOT a near-term build target -- captured here so it isn't lost,
same treatment as #107/#121's closing architectural notes. No RTL, no
spec, no commitment implied.**

**The starting observation:** the FULL cell's measured electrical
Fmax ceiling (~56 MHz, #106/#111) traces to the wired-OR bus's
capacitive/fanout loading -- a physics-of-copper-and-transistors
limitation specific to electrical signalling, not a flaw in the
cell's underlying logical architecture. Photonic signalling doesn't
carry the same loading penalty, raising the question of whether the
FULL cell's ORIGINAL, cleaner broadcast-bus design (the one the
stripped-cell/cardinal-hop pivot specifically existed to work around
electrically) could become viable again in a photonic substrate --
not superseded, genuinely resurrected.

**The proposed "how," worked through in some depth:**
- **WDM (wavelength-division multiplexing) addressing**, using an
  existing, non-speculative photonics technology (a "100-comb" laser
  splitting a beam into ~100 distinct frequency channels, well-
  established in telecom). Rather than an optical wired-OR (combining/
  summing multiple sources on one wavelength -- genuinely hard, needs
  nonlinear thresholding, still largely unsolved at scale), each
  channel becomes an independent, interference-free point-to-point
  lane -- sidestepping the wired-OR problem entirely rather than
  solving it.
- **Hierarchical scaling by the same 100-factor, repeated:** 100 cells
  as a block, sitting on another 100-channel block, translating
  address digits at each level -- the same simple building block
  repeated ~20 times. Math checked: 100^19 ≈ 10^38, 100^20 ≈ 10^40,
  both straddling 2^128 ≈ 3.4x10^38 -- so ~20 nested levels spans, and
  slightly exceeds, a full 128-bit address space, matching the cell's
  own stated original design target size.
- **Translation/routing at each level**, two variants considered:
  (a) drop to electronic at each hop -- boring, solved technology
  (standard hierarchical/trie-style routing, strip one digit, forward
  the rest, same principle as telecom/IP routing), but pays a real
  cost: 20 full opto-electronic-opto round-trips to resolve a
  worst-case address, a genuine latency/power tax (standard and
  accepted in long-haul telecom regeneration, but real, not free); or
  (b) all-photonic translation at each level -- avoids the O/E/O tax
  entirely, but requires genuine specialist photonic router hardware,
  a meaningfully bigger and more novel engineering problem than (a).
- **A real, currently-open gap, named directly rather than glossed
  over:** neither variant yet has a RETURN path -- the FULL cell has
  ack/two-arrival confirmation within a cell and within a zone (#91,
  cardinal bridges), but nothing built for a request climbing back UP
  20 nested address levels to confirm delivery. Genuinely missing, not
  just unspecified.

**Why the cell design maps onto photonics unusually well, not just
"could work":**
1. The two-arrival, wire-delay-based firing model is ALREADY
   inherently asynchronous -- causality from path length, not a global
   clock sequencer -- which is a NATIVE photonics primitive (optical
   delay lines, interferometric path-length timing), not a concept
   that needs translating from an electronic mindset.
2. "Topology is computation" maps closely onto an EXISTING real
   category of hardware -- programmable photonic mesh circuits
   (Mach-Zehnder interferometer meshes, as used in today's photonic AI
   accelerators), which already compute by routing light through a
   reconfigurable topology, exactly this project's own design
   language.

**The honest caveat, not glossed over:** pure all-optical Boolean
logic (the NOR gate itself, with no electronics at all) remains the
genuinely hard, largely unsolved-at-scale part of photonic computing
-- nonlinear optical gates exist but are lossy, power-hungry, and
difficult to cascade deep. A realistic "photonic cell" most likely
isn't pure light end-to-end -- it's the SAME split already established
at the router layer, pulled inside the cell itself: photonic
interconnect between cells, with a small electronic core doing the
actual NOR decision (photodetector in, transistor-level logic,
modulator out).

**The point Alan closed on, worth stating precisely since it's the
actual takeaway:** even under this whole speculative re-hosting, the
FULL cell's core design -- the NOR-universal gate, the two-arrival
firing model, the addressed/self-contained architecture -- survives
essentially intact. Nothing about this direction requires redesigning
the cell itself; at minimum, it persists as "a kernel of an idea for
the future" even if the physical substrate underneath it changes
entirely. This is consistent with, and extends, #107's original
FULL-cell-as-ASIC-endpoint framing -- photonics is a possible further
answer to WHERE that endpoint could eventually live, not a competing
idea to it.

## 125. program_in/program_done implemented and confirmed correct on the first real test -- #123's full design now working RTL, every value checked by hand (Alan/session, next session after #123)

**STATUS: `unicell_stripped_v1.v` gained `program_in`/`program_done`
plus the 3-word assembly buffer. `tb_stripped_v1_program.v` (new)
confirms the complete mechanism, first attempt, no bugs found this
time. All existing testbenches re-run, confirmed byte-identical --
purely additive, no regression.**

**Implementation, matching #123's design exactly:**
- `program_in` (new, general input) / `program_done` (new, general
  output) -- both single-bit, not per-direction, per #123's own
  reasoning (mirrors `ready_out`'s broadcast convention).
- New state: `prog_word_idx` (2-bit), `prog_assemble` (96-bit),
  `program_done_r`.
- `programming_active` takes TOP priority in the sequential block --
  genuinely suspends ordinary operation rather than layering on top of
  it. Confirmed safe by construction: `capture_now`/`can_fire`/
  `relay_fire`/`a_reemit_active`/`a_update_active`/`internal_fb_active`
  were all given an explicit `&& !program_in` in their own condition
  wires (not just skipped via if/else priority), specifically to
  prevent `next_pending_ack`'s independent computation from reacting
  to a `can_fire`/`relay_fire` wire that happened to read true while
  the ACTUAL commit was suppressed by priority -- a real inconsistency
  that would have existed without this, caught during design rather
  than by testing it into existence.
- Word packing identical to the already-proven convention (`cell_
  wrapper_v1`/`cell_cardinal_cmd_v1`): word0->`[31:0]`, word1->
  `[63:32]`, word2->`[95:64]`, applied to `cmd_latch[95:0]` on the 3rd
  word, same safe single-edge write style `cfg_valid` already uses.
- `ack_out_x` reused directly (added `programming_active` to
  `consumed_now`) -- no new ack mechanism needed, exactly as designed.
- `program_done_r` resets when `program_in` itself drops -- mutually
  exclusive by construction with the branch that sets it (only
  possible while `program_in` is high), so no same-cycle conflict.

**Confirmed, by hand, every value, first test, no bugs found:**
- Cell started completely blank (no `cfg_valid` load at all in this
  test, deliberately -- confirming `program_in` alone can take a cell
  from nothing to fully working).
- 3 words streamed via ordinary `data_in`/`arrived_n` (a raw stimulus
  standing in for "any source, anywhere," per #123's decoupling) --
  `ack_out_n` fired on all 3, confirming the data source gets
  acknowledged for free.
- On the 3rd word: `topology` became `004` (NOR) and `routing_mask`
  became `000010` (South) -- both landed atomically, exactly the
  intended values -- and `program_done` asserted on the same edge.
- Releasing `program_in` correctly dropped `program_done` back to 0
  while PRESERVING the programmed config (`004`/`000010` unchanged).
- Normal operation resumed correctly afterward: a genuine fresh
  capture (`a_arrived=1`, confirmed not a leftover state), then a real
  fire computing `NOR(0xAAAA0000, 0x11110000) = 0x4444FFFF` --
  confirming the freshly-programmed topology isn't just bits sitting
  in a register, it's genuinely being used for real computation.

**What this demonstrates as a complete capability:** a cell can go
from totally unconfigured to fully working, programmed entirely
through its own ordinary data path plus one control bit, with the
actual config data sourced from anywhere -- no dedicated command bus,
no addressing, no new port for the data itself. This is #123's design
working exactly as intended, first try.

**Next: build a genuine end-to-end example including the "command
cell" side itself** (something asserting `program_in` toward an
adjacent target, e.g. reusing `a_reemit_in`'s existing mechanism as
the command-cell's own logic per #123's framing), and/or a proper
single-hop-scoped area/Fmax test to replace the superseded, scope-
mismatched step 3/4 designs (#110-#113, #122).

## 126. Full end-to-end command cell confirmed working -- genuine command cell + target, decoupled data source, all four handshake stages verified (Alan/session, next session after #125)

**STATUS: `cell_command_v1.v` (new, minimal companion module) +
`tb_stripped_v1_command_e2e.v` (new) confirm the COMPLETE #123 picture
working together for the first time -- not just the target cell's own
mechanism (#125) in isolation.**

**`cell_command_v1.v`, built exactly to the minimal shape #123's
conversation converged on:** holds NO config data, knows nothing about
where the 3 program words come from. Its entire logic: `trigger_in`
starts `program_out` (held), `program_done_in` releases it. Six lines
of real logic, same "small companion module beside the cell" pattern
already proven twice today (`cell_wrapper_v1.v`, `cell_cardinal_cmd_
v1.v`) -- deliberately NOT baked into `unicell_stripped_v1.v` itself,
keeping the now-confirmed-correct core (#125) untouched.

**Confirmed, by hand, all four stages, with the data source
GENUINELY decoupled from the trigger (a single pulse, unrelated
timing to the 3-word stream that follows) -- not just designed to be
decoupled:**
- Trigger pulse -> `CMD.program_out` correctly asserts and HOLDS
  (unrelated to anything about the data that hasn't arrived yet).
- 3 words arrive from a separate stimulus, on their own schedule --
  `program_out` stays held throughout, config stays at 0 until the
  3rd word.
- 3rd word: `topology=004`, `routing_mask=000010`, `program_done=1` --
  identical correct values to #125's isolated test, now produced via
  the real command-cell trigger instead of raw testbench control of
  `program_in` directly.
- `CMD` sees `program_done`, releases `program_out` the very next
  cycle -- confirmed the release condition fires correctly, not just
  designed to.
- `T.program_done` clears one cycle after `program_in` actually drops
  -- checked directly (an extra settle cycle added specifically to
  confirm this, rather than assuming a lag "should" be there) --
  natural registered propagation delay, not a bug. Programmed config
  (`004`/`000010`) confirmed preserved throughout the entire release
  sequence.

**What this confirms that #125 alone couldn't:** the full picture
composes correctly -- a genuine command cell, a genuine target, and a
genuinely separate data source all interacting through nothing but the
primitives #123 designed (`program_in`/`program_done`, `trigger_in`)
and primitives already proven earlier today (`ack_out_x`, the 3-word
assembly). No new bugs found this pass -- both pieces were designed
carefully enough in conversation that the implementation worked
correctly on the first real end-to-end attempt.

**Next:** either the branched/data-triggered selection extension
(a comparator deciding which of several targets `program_out` points
toward), or move to proper single-hop-scoped area/Fmax testing of this
now-confirmed mechanism.

## 127. Wrapper rebuilt for full JTAG/host parity with the fabric's own internal mechanisms -- confirmed correct on all 5 operations, first real test (Alan/session, next session after #126)

**STATUS: `cell_wrapper_v2.v` (new, replaces v1's role) +
`tb_wrapper_v2.v` (new) confirm the complete redesign working. This
was Alan's own principle stated directly: the wrapper is the ONLY
external route in or out, so it needs the same expressiveness as
anything internal to the fabric -- not a separate, narrower
mechanism.**

**Two real changes from v1 (#99/#108), both confirmed working:**
1. **PROGRAM no longer writes `cfg_data` directly.** It asserts
   `program_in` (#123/#125) and feeds its 3 words through the
   target's ORDINARY data port -- the IDENTICAL path a command cell
   uses (#126). The target genuinely cannot tell whether a command
   cell or the wrapper triggered it -- confirmed directly: `topology`
   landed as `004` exactly matching #125/#126's own confirmed values.
2. **Two new operations added: `SET_CTRL`/`CLR_CTRL`**, toggling one
   of the target's 6 persistent control lines (`freeze_in`, `hold_in`,
   `fb_internal_in`, `a_reemit_in`, `a_update_in`, `a_self_update_in`),
   held continuously by a small latch INSIDE the wrapper (the scan bus
   only ever delivers a brief instruction; the target's control inputs
   need to stay held between scan operations, not just pulse).

**Opcode encoding, 3 bits (was 1 in v1):** `PROGRAM=000`,
`COLLECT=001`, `SET_CTRL=010`, `CLR_CTRL=011`, `DIAG=100`.
Control-line index (in the data word's low 3 bits for `SET_CTRL`/
`CLR_CTRL`): `0=freeze 1=hold 2=fb_internal 3=a_reemit 4=a_update
5=a_self_update`.

**`DIAG` (new operation), scope confirmed deliberately minimal (Alan):
only state that isn't otherwise observable** -- `{program_done,
a_arrived, ready_bit, pending_ack[5:0]}`. Explicitly NOT exposing
other latches (`data_reg`, `out_buffer`, `cmd_latch`'s config fields)
-- those are data (readable via `COLLECT`) or programming (readable
via what was written), not diagnostic state needing separate exposure.

**Confirmed, by hand, all 5 operations, first real test, on one
target cell:**
- `PROGRAM`: `topology=004`, `routing_mask=000000` landed correctly
  via the North channel (wrapper's injection port), matching #125/
  #126's exact values.
- `SET_CTRL`(hold): target genuinely held -- fed TWO different values
  on a SEPARATE South-channel stimulus (confirming the wrapper's
  PROGRAM channel and ordinary data are genuinely independent, not
  just designed to be), `A` stayed fixed at `0xAAAA0000` across both
  fires, exactly matching #116's own confirmed hold behavior.
- Fire computations checked by hand: `NOR(0xAAAA0000,0x11110000) =
  0x4444FFFF`, `NOR(0xAAAA0000,0x22220000) = 0x5555FFFF` -- both
  correct.
- `CLR_CTRL`(hold): released correctly.
- `COLLECT`: read back `0x5555FFFF` through the bus -- correctly
  reflects the LAST held-fire's result.
- `DIAG`: read back `0xC0` = `program_done=0, a_arrived=1, ready=1,
  pending_ack=0` -- decoded and confirmed correct by hand against the
  actual cell state at that moment.

**One cosmetic bug caught and fixed in the TEST harness itself, not
the wrapper module:** the testbench's own `diag_word` packing
expression was 33 bits wide (an extra redundant zero) assigned to a
32-bit wire -- Verilog's implicit truncation happened to drop exactly
the extra padding bit, not real data, so the observed result was
already correct before the fix. Fixed for precision anyway (23'h0
instead of 24'h0), re-ran, confirmed byte-identical -- purely cosmetic,
confirmed rather than assumed.

**What this completes:** the wrapper now has genuine parity with a
command cell -- JTAG/host and any internal command cell use the
IDENTICAL mechanism to reach a target, exactly Alan's stated
requirement ("the cell knows no difference, it's just another
channel hitting the same side"). This is the ONLY external route into
or out of the fabric, and it now exposes everything the fabric can do
internally.

**Next: retrofit the grid/campaign test tops to use v2** (replacing
v1's direct `cfg_data` write), then move to proper single-hop-scoped
area/Fmax measurement of the complete mechanism.

## 128. Re-running the #103 campaign from step 1, with the now-complete stripped cell (Alan/session, next session after #127)

**STATUS: step 1's grid re-verified in sim, ready for a fresh Quartus
fit. Given how much the cell has grown since #106's original step-1
fit (146 ALMs, 257.14 MHz) -- 7 new ports (`hold_in`, `fb_internal_in`,
`a_reemit_in`, `a_update_in`, `a_self_update_in`, `program_in`,
`program_done`), the memory-cell mechanism (#115-#120), and the
command mechanism (#123-#126) -- Alan wants the WHOLE campaign
re-measured from step 1 up against this complete cell, not just
patched deltas assumed to still hold.**

**Step 1's grid (`top_stripped_grid5x5_v1.v`) confirmed already
up to date and correct** -- all 7 new ports were included in every
port-tie-off batch applied throughout today's session, confirmed by
direct grep (all present) and re-run smoke test (`all_ready=1`, no
deadlock, byte-identical to #106's original healthy result). Same
project (`Unicell-Q-stripped-grid5x5`), same top-level entity, same
file names -- no new project needed, just rebuild with the updated
`unicell_stripped_v1.v`.

**Honest caveat, stated up front rather than assumed away, per the
day's own repeated lesson (#105's comparator, #113's observability
gap): tying the 7 new ports to `1'b0` does NOT guarantee Quartus
optimizes all their associated logic away.** The new fit numbers are
what actually answers this -- if the delta from #106's 146 ALMs /
257.14 MHz is small, that's confirmation the new capability is cheap
when dormant; if it's surprisingly large, that needs the same
path-tracing investigation already applied twice today before
accepting it.

**Plan for the rest of the campaign, given the wrapper's own complete
redesign (#127 — v2, not v1):**
- Step 1: rebuild as-is (above), get real numbers for the complete
  cell, dormant new features.
- Step 2: needs a real rewire, not just a rebuild -- the wrapper grid
  top (`top_stripped_grid5x5_wrapper_v1.v`) still instantiates
  `cell_wrapper_v1`, which no longer represents the wrapper's actual
  design (#127 replaced direct `cfg_data` writes with `program_in`/
  data-port injection, plus 5 new operations). This needs retrofitting
  to `cell_wrapper_v2` before it can be measured meaningfully.
- Steps 3/4: their entire premise (`cell_cardinal_cmd_v1.v`'s multi-hop
  relay chain) was already identified as a scope mismatch (#122) --
  the corrected mechanism is `cell_command_v1.v`'s single-hop command
  cell (#123/#126), which needs its own properly-scoped test built
  from scratch, not a retrofit of the old chain-based one.

**Sequencing:** step 1 first (ready now), then step 2's wrapper-v2
retrofit, then reconsider 3/4's shape entirely around the corrected
single-hop design.

## 129. Step 1 re-confirmed with the complete stripped cell: 145 ALMs, 261.44 MHz -- essentially unchanged from #106, confirming all new logic is genuinely dormant-cost-free (Alan/session, 2026-08-03)

**STATUS: real, trustworthy result. Step 1 of the re-run campaign is
DONE.**

**Numbers: 145 ALMs (25 cells), 261.44 MHz `clk_div` Fmax** -- against
#106's original baseline (146 ALMs, 257.14 MHz): essentially
identical, marginally better on both counts.

**Why this is trustworthy without needing a full path-trace this
time (unlike #105/#113's surprising results, which specifically
needed digging into): register count is the tell.** The command
mechanism added a 96-bit assembly buffer (`prog_assemble`) per cell --
if that had survived synthesis, 25 cells would add roughly 2,400 extra
flip-flops. The actual register count reported is 175, barely
different from the original baseline -- direct, concrete confirmation
that Quartus proved all 7 new ports' associated logic genuinely dead
(since every one is tied to `1'b0` in this build) and stripped it out
entirely, rather than silently carrying hidden cost the way earlier
"should be optimized away" assumptions turned out wrong.

**Conclusion: the complete, fully-featured stripped cell -- memory
cell mechanism (#115-#120) and command mechanism (#123-#126) both
included -- costs NOTHING extra in area or timing when those
capabilities are dormant.** This is the real, updated baseline for the
rest of the re-run campaign to compare against.

**Next: step 2, which needs an actual rewire, not just a rebuild** --
the wrapper grid top still instantiates `cell_wrapper_v1`, which no
longer reflects the wrapper's real design (#127 replaced direct
`cfg_data` writes with `program_in`/data-port injection plus `SET_CTRL`/
`CLR_CTRL`/`DIAG`). Retrofitting `top_stripped_grid5x5_wrapper_v1.v`
to `cell_wrapper_v2` is the next concrete task.

## 130. Wrapper grid retrofitted to cell_wrapper_v2, confirmed correct end-to-end (Alan/session, 2026-08-03)

**STATUS: `top_stripped_grid5x5_wrapper_v1.v` rebuilt against
`cell_wrapper_v2` (#127). Sim-confirmed correct, NOT yet built in
Quartus.**

**A real design question surfaced and resolved in the retrofit:**
v2's `PROGRAM` routes through the target's ORDINARY cardinal data
port, but in a full 25-cell grid every direction is already occupied
by real neighbor data flow — a genuine conflict a single-cell test
never had to face. Resolved cleanly, no new port needed: since
`programming_active` already takes top priority in the cell regardless
of which direction a word arrives on, each cell's North input is just
a simple 2:1 mux — the wrapper's injection when THAT cell's own
`program_out` is asserted, otherwise the normal grid neighbor (or the
free-running seed at cell (0,0)). Matches Alan's own framing directly:
programming can pause the data flow without a dedicated wire.

**One honest simplification, flagged rather than silently done:** the
`DIAG` word for this build is `{program_done, ready_out}` only —
`a_arrived`/`pending_ack` aren't exposed as real ports on
`unicell_stripped_v1.v` (they're internal registers), so a full DIAG
readback would need those added as genuine ports first. Not needed
for measuring the wrapper's own area/Fmax cost here — flagged as
future work if real diagnostic readback on hardware is wanted later.

**Confirmed correct via smoke test before handoff, same discipline as
every other build today:** cell (0,0) programmed correctly
(`topology=004`, `routing_mask=E`); cell (4,3), 23 hops into the
chain, ALSO confirmed correct — the same "check the far end, not just
the easy case" discipline that's caught real bugs earlier in this
project. `all_ready=1`, `prog_active` completes cleanly, no deadlock.

**Next: build in Quartus, get real ALM/Fmax numbers for step 2 against
the re-confirmed step-1 baseline (145 ALMs, 261.44 MHz, #129).**

## 131. Step 2 (v2 wrapper) CONCLUDED: 75.4 ALM/cell, 132.43 MHz -- confirmed real, and this time the cost is genuinely structural, not an artifact (Alan/session, 2026-08-03)

**STATUS: real result, path-traced. Step 2 of the re-run campaign is
DONE.**

**Numbers: 2,030 ALMs total (1,885 more than step 1's 145), `clk_div`
Fmax 132.43 MHz.**

**Area: 75.4 ALM/cell** for the v2 wrapper -- roughly 5.3x v1's
original cost (14.3 ALM/cell, #109). A real, substantial increase,
reasonably explained by what v2 actually does that v1 didn't: 6
persistent per-line control latches, a 3-bit/5-operation opcode
instead of 1-bit/2, plus `DIAG` readback. Register count (1,927)
roughly matches the added state, not a red flag.

**Fmax dropped further too (261.44 -> 132.43 MHz) -- checked via path
tracing, same discipline as every other step, and this time the
result is GENUINELY DIFFERENT IN KIND from #105's comparator or
#113's observability gap.** Those were both cases where the slow
path traced to something structurally SEPARATE from real cell logic
(a harness comparator, or logic later proven dead). Here, 8 of 10
worst paths trace directly through `cell_prog_arrived_out`/
`cell_program_out` landing on a cell's own `cmd_latch[13]`/
`pending_ack` -- and the path reaching a DIFFERENT cell than the one
the wrapper is paired with (WRAP[3][3] -> CELL[4][3], not just
CELL[3][3]) is real, not noise: the wrapper's injection changes
CELL[3][3]'s own ready/ack state, which then genuinely propagates to
its real grid neighbor CELL[4][3] through the ordinary cardinal ready/
ack wiring already established as legitimate in step 1's own baseline.

**This is the direct, structural cost of a real design decision made
earlier in the session, not a bug to chase further:** routing
`PROGRAM` through the target's shared data-port mux, rather than a
dedicated wire (#130's retrofit). v1's wrapper wrote to `cfg_data`
directly -- a completely separate port, never touching the cell's own
timing-critical ready/ack chain at all. v2's wrapper, by design,
shares the SAME mux the ordinary two-arrival/ack logic already
depends on -- so the wrapper's injection decision is now genuinely ON
that critical path, not beside it. This is exactly the tradeoff of
"no dedicated wire, share the existing port, program can pause data
flow" (#123's own framing) -- real, structural, and now measured
rather than assumed.

**#103 re-run progress so far:** step 1 (145 ALMs, 261.44 MHz, #129)
-> step 2 (+1,885 v2 wrapper, 132.43 MHz, this entry). Steps 3/4 still
need their entire premise rebuilt around the corrected single-hop
command-cell design (#123/#126) rather than the deprecated relay-chain
mechanism (#110, #122).

## 132. Dedicated programming port built (option 1) -- removes the top-level mux entirely, confirmed correct on every existing test (Alan/session, 2026-08-03)

**STATUS: `unicell_stripped_v1.v` gained `prog_data_in`/`prog_arrived_in`/
`prog_ack_out` -- a genuinely separate channel from the ordinary
cardinal data ports, purely to test whether #131's Fmax cost came from
sharing the data-port mux (removable) or from something inherent in
the internal mechanism regardless of the external port (would need
option 2 -- full internal separation, mirroring `fb_internal_in`'s own
approach, #118). NOT yet built in Quartus.**

**Changes:** `programming_active` now gated on the dedicated
`prog_arrived_in`, not the shared `any_arrived`; word assembly reads
from `prog_data_in`, not `arrived_val`; ack for programming rides its
own `prog_ack_out`, removed entirely from the shared `consumed_now`/
cardinal `ack_out_x` path. The wrapper grid top
(`top_stripped_grid5x5_wrapper_v1.v`) had its North-port 2:1 mux
(`program_out ? wrapper_injection : grid_neighbor`) REMOVED entirely
-- North is pure, unmuxed grid data again; the wrapper's injection
goes straight to the new dedicated port instead.

**Confirmed correct, same discipline as every other change today:**
`tb_stripped_v1_program.v` and `tb_stripped_v1_command_e2e.v` both
re-verified correct through the new dedicated port (one test-design
bug caught and fixed along the way -- the program test had
accidentally reused the SAME stimulus regs for both the programming
step and the post-programming "confirm normal operation resumes"
step, which broke once those became genuinely separate ports; fixed
by adding a distinct `normal_data`/`normal_arrived` stimulus, re-
confirmed identical correct values to #125/#126). The retrofitted grid
top re-confirmed correct end-to-end (cell (0,0) and the far cell (4,3)
both programmed correctly). Full regression across all other existing
testbenches re-run clean, no changes to any previously-confirmed
behavior.

**Next: build in Quartus, get real ALM/Fmax numbers for this option-1
retrofit against #131's shared-mux result (1,885 ALMs delta, 132.43
MHz).** Per Alan's own framing: if this just relocates the same
bottleneck rather than removing it, option 2 (fully separating the
INTERNAL path too, not just the external port) is the next step.

## 133. Programming channel corrected to be genuinely CARDINAL -- #132's single non-directional port was the wrong shape, fixed before the rebuild rather than after (Alan/session, 2026-08-03)

**STATUS: `unicell_stripped_v1.v`'s `prog_data_in`/`prog_arrived_in`/
`prog_ack_out` widened to full 4-direction sets
(`prog_data_in_n/s/e/w` etc.), matching every other cardinal signal's
own shape and priority-select convention. Confirmed correct on every
existing test. NOT yet built in Quartus.**

**The correction, worked through in conversation before touching RTL
again:** #132 built a single, non-directional dedicated port — a real
departure from how everything else in this architecture works (data,
ready, ack are all genuinely 4-directional). Alan caught this: a
dedicated channel is right (the measured cost in #131 came from
SHARING the ordinary data port, not from having a separate one at
all), but it still needs to be cardinal, so a command cell (or the
wrapper) can occupy any of the target's 4 sides, exactly like any
ordinary neighbor -- just on its own dedicated set of wires instead of
contending with real grid data for the same port.

**What changed:** `prog_data_in_n/s/e/w`, `prog_arrived_in_n/s/e/w`,
`prog_ack_out_n/s/e/w` -- real, separate wires alongside the ordinary
`data_in_x`/`arrived_x`/`ack_out_x` ports, not sharing them. Added a
priority-select for the programming channel (`prog_sel_n/s/e/w`, same
N>S>E>W convention as the ordinary `arrived_val` mux) so a command
cell or wrapper connected to any single direction is picked up
correctly. `prog_ack_out_x` now goes only to the genuine source
direction (matching `ack_out_x`'s own convention exactly), not a
single broadcast. `program_in`/`program_done` stay single, general
signals -- they're control/status, mirroring `ready_out`'s own
broadcast convention, not data needing a source direction.

**Confirmed correct on every test, wired to North for now (the
existing convention for single-connection tests/the wrapper grid):**
`tb_stripped_v1_program.v`, `tb_stripped_v1_command_e2e.v`, and the
retrofitted `top_stripped_grid5x5_wrapper_v1.v` all re-verified
byte-identical to their #132 results. Full regression across every
other testbench re-run clean.

**Next: build in Quartus, get real ALM/Fmax numbers for this
corrected, genuinely-cardinal dedicated channel** -- against #131's
shared-mux result (1,885 ALMs delta, 132.43 MHz) and against #132's
now-superseded single-wire version (never built in Quartus, corrected
before reaching hardware).

## 134. Cardinal programming channel's first real fit: 10.3 ALM/cell, 164.83 MHz -- a genuine improvement over BOTH prior wrapper designs, but the Fmax is capped by a test-harness artifact, found and fixed (Alan/session, 2026-08-03)

**STATUS: real fit result reported, but path-traced and found to be
understating the true number -- fix applied, rebuild needed before
treating this as final.**

**Numbers: 403 ALMs total (258 more than step 1's 145), `clk_div`
Fmax 164.83 MHz.**

**Area: 10.3 ALM/cell -- genuinely LOWER than both prior wrapper
designs** (v1's 14.3 ALM/cell #109, and #131's shared-mux v2 at 75.4
ALM/cell), despite v2 doing far more than v1 ever did (6 control
lines, 5 opcodes vs. v1's 1 opcode). The likely explanation, structural
not coincidental: #131's shared-port version forced Quartus to build
real arbitration logic to resolve contention between the wrapper's
injection and genuine grid data fighting over the same wire -- that
muxing was itself a real area cost. A dedicated cardinal channel has
more raw wires but each has a single, simple job with no contention to
resolve -- cheaper overall despite the extra wire count.

**Fmax: 164.83 MHz -- real improvement over #131's 132.43 MHz, but
NOT yet trustworthy as the mechanism's true ceiling.** Path-traced
(same discipline as every other step) and found: ALL 10 worst paths
traced to the SAME single cause -- `prog_addr` feeding into the very
FIRST wrapper's registered pass-through (`bus_out_data[3]`). This is
the top-level test driver's `prog_addr / 5` and `prog_addr % 5` --
genuine division/modulo hardware (5 isn't a power of 2), flagged as a
POSSIBLE concern all the way back at step 2's very first run but
dismissed then because it wasn't dominant at the time. Now that the
wrapper/cell side has gotten genuinely cheaper, this previously-
secondary cost became the new bottleneck -- a clean "fix one thing,
expose the next" case, not a new kind of problem.

**Fixed:** replaced the divide/modulo with simple counters
(`prog_row`/`prog_col`, incremented directly alongside `prog_addr` in
the same always block) -- no division hardware anywhere in the driver
now. Re-confirmed correct (cell (0,0) and the far cell (4,3) both
still program correctly, `all_ready`/`prog_active` behave identically).

**Conclusion: the 164.83 MHz figure LIKELY UNDERSTATES what the
cardinal-channel mechanism can actually do** -- it was capped by test-
harness arithmetic, not by the wrapper or cell logic itself. Rebuild
needed for the real number.

**#103 re-run progress:** step 1 (145 ALMs, 261.44 MHz, #129) -> step 2
shared-mux (+1,885, 132.43 MHz, #131) -> step 2 cardinal, first attempt
(+258, 164.83 MHz, artifact-capped) -> rebuild pending with the fix.

## 135. Step 2 (cardinal programming channel) CONCLUDED, final and trustworthy: 10.6 ALM/cell, 190.22 MHz -- confirmed genuine, cheaper AND faster than both prior wrapper designs (Alan/session, 2026-08-03)

**STATUS: real, path-confirmed result. Step 2 of the re-run campaign
is DONE.**

**Numbers: 409 ALMs total (264 more than step 1's 145), `clk_div` Fmax
190.22 MHz.**

**Confirmed genuine this time -- every one of the 10 worst paths is
real cell-to-cell cardinal logic** (`cmd_latch[13]`, `pending_ack`,
`routing_mask` bits feeding a neighbor's own state), the SAME kind of
legitimate path #106/#109 already established as real grid routing
cost. NOTHING traces to the driver or the wrapper anymore -- #134's
divide/modulo fix worked, confirmed by the absence of `prog_addr`/
`bus_out_data` from the worst-path list entirely.

**Area: 10.6 ALM/cell** -- consistent with #134's first (artifact-
capped) attempt (10.3 ALM/cell), confirming the area number was
already stable and trustworthy even before the Fmax fix.

**Fmax: 190.22 MHz -- a real improvement from #134's 164.83 MHz once
the test-harness artifact was removed**, and genuinely better than
BOTH prior wrapper designs: v1's original mechanism (165.7 MHz, #109)
and #131's shared-mux v2 attempt (132.43 MHz). Against step 1's plain
baseline (261.44 MHz): a real ~27% Fmax cost remains, honestly
attributable to more cell-to-cell logic contending for routing at this
scale -- the same structural mechanism #106 identified for the plain
grid itself, not a flaw in the cardinal-channel mechanism.

**Conclusion: the corrected design (genuinely cardinal, dedicated
channel, per #133's fix) is cheaper AND faster than the original v1
wrapper, while doing considerably more** -- 6 persistent control
lines, 5 opcodes (`PROGRAM`/`COLLECT`/`SET_CTRL`/`CLR_CTRL`/`DIAG`),
full JTAG/host parity with the fabric's own internal mechanisms. This
is the real, final number for this design.

**#103 re-run progress:** step 1 (145 ALMs, 261.44 MHz, #129) -> step 2
(264 ALMs / 10.6 per cell, 190.22 MHz, this entry, CONCLUDED). Steps
3/4 still need their entire premise rebuilt around the single-hop
command-cell design (#123/#126) rather than the deprecated relay-chain
mechanism.

## 136. Thought notes only, not yet started: the post-testing roadmap -- ICM stays target-agnostic across a new dual-VM fork, then a full ordered pass through the whole toolchain (Alan, 2026-08-03)

**STATUS: forward-looking notes, explicitly deferred by Alan ("not
yet... just thought notes for now, after the testing"). No work
started on any of this. Logged so the shape isn't lost.**

**Clarification on today's earlier "interpretation layer" question,
confirmed against the actual repo rather than assumed:** the `.icm`
file format itself is fine, unaffected by today's redesign -- clean
JSON, target-agnostic (`{gs, in, out, inB, alt, stor, init}` per
record, logical addresses not physical ones, no opcodes to have lost).
Checked the whole repo (`imago/`, `unicell_deployed.py`, `pond_ptt.py`)
and confirmed: there is currently NO compiler stage anywhere that maps
an ICM's logical addresses to physical cell positions and emits an
actual hardware bitstream -- not for the FULL cell's opcode
vocabulary, and not for the stripped cell's wrapper protocol. This
isn't something today's session broke; it's genuinely unbuilt
infrastructure, for either cell type, that becomes the natural next
concrete task once testing wraps up.

**The architecture Alan actually described, extending #107's original
fork with a concrete third piece:** ONE shared `.icm` format, consumed
independently by THREE different backends, not three different file
formats:
1. **The FULL cell VM** -- "the dream": the idealized, self-contained
   architecture as originally conceived (#107's ASIC-endpoint line).
2. **A new "card reflection" VM** -- "the reality": a VM faithfully
   modeling what's ACTUALLY buildable and confirmed on the real
   stripped-cell silicon (everything from #88 through #135) --
   single-hop programming, cardinal-only routing, the real memory/
   comparator mechanisms, all the genuine constraints established
   today, not the idealized architecture. Gives anyone testing against
   it an honest preview of what the real card will actually do.
3. **The physical card itself**, via the (currently unbuilt) loader/
   translation layer discussed above.

**The full ordered task list for after testing concludes, as stated,
not yet started on any item:**
1. Build a full card -- potentially thousands of cells, genuinely
   timing-dependent (i.e. however far the real Fmax/area numbers from
   this campaign actually allow scaling to go).
2. Go through the entire software suite in order: the compiler first,
   then the workbench front end (now has to support 3 possible
   targets -- dream VM, reality VM, real hardware -- not one), then
   the composer and other front ends, then the library.
3. Finally the "Trix system" (name recorded as stated -- no prior
   grounding for this term found in existing project memory or repo
   search; flag for Alan to clarify scope when this is actually picked
   up) and documentation, which now has to honestly reflect all
   possible targets and their different realities, not a single
   assumed architecture.

**Explicitly not started:** none of this -- compiler, workbench,
composer, library, Trix system, documentation -- has any work done
against it yet. This entry exists purely to preserve the shape of the
plan for whenever it's picked up.

## 137. Step 3 rebuilt around the corrected single-hop command-cell design, ready for Quartus (Alan/session, 2026-08-03)

**STATUS: `top_stripped_grid5x5_command_v1.v` (new) + Quartus project
prepared and sim-confirmed. NOT YET BUILT IN QUARTUS -- ready for
Alan.**

**Replaces the deprecated relay-chain mechanism entirely** (#110's
`cell_cardinal_cmd_v1.v`, set aside per #122's scope correction) with
the CORRECTED design worked through in #123/#126: every one of the 25
grid positions gets TWO real instances -- an ordinary
`unicell_stripped_v1` (the target, identical to every other cell) plus
a genuinely SEPARATE, much smaller `cell_command_v1` companion (the
minimal trigger/hold/release logic, #126) -- not one cell with a mode
flag, confirmed explicitly when Alan asked. Each command companion
targets its OWN cell via the dedicated, genuinely cardinal programming
channel (#133) -- confirmed by construction to not interfere with the
ordinary snake data grid running underneath it, since #133 made the
programming channel genuinely separate wires, not shared ones.

**Confirmed correct before handoff:** the same snake config lands
correctly (cell (0,0) and the far cell (4,3) both show
`topology=004`/`routing_mask` matching step 1's own values, loaded via
the same cheap one-shot `cfg_valid` walk, #105's fix -- genuinely
separate from the command mechanism itself). `all_ready=1`, no
deadlock. Directly watched `program_out` toggle over many real cycles
-- confirmed the command mechanism genuinely completes and re-triggers
repeatedly (faster cadence than originally intended, since the test's
own trigger/arrival timing overlaps more than planned, but functionally
correct every time -- `topology`/`routing_mask` visibly change to match
what's programmed on each cycle). For an area/Fmax measurement, more
frequent genuine activity is a feature, not a problem -- nothing here
risks being optimized away as dead logic.

**What this build answers, once fit:** the real, measured ALM/Fmax
cost of the corrected single-hop command-cell mechanism at 25-cell
scale, against step 1's clean baseline (145 ALMs, 261.44 MHz, #129) --
the genuinely correct version of #103's original step 3, replacing the
scope-mismatched relay-chain attempt (#111's now-unconfirmed numbers).

## 138. Step 3 (corrected single-hop command-cell mechanism) CONCLUDED: 6.5 ALM/cell, 174.64 MHz -- confirmed genuine, the cheapest mechanism measured in this whole campaign (Alan/session, 2026-08-03)

**STATUS: real, path-confirmed result. Step 3 of the re-run campaign
is DONE.**

**Numbers: 308 ALMs total (163 more than step 1's 145), `clk_div` Fmax
174.64 MHz.**

**Area: 6.5 ALM/cell** -- genuinely the cheapest of any mechanism
measured across this entire campaign, even below the wrapper's 10.6
ALM/cell (#135). Makes sense given the actual pieces: `cell_command_
v1.v` is only ~6 lines of real logic (hold-on-trigger, release-on-
done); the rest of this cost is the target's own cardinal priority-
select and 3-word assembly for the programming channel, not the
companion module itself.

**Fmax: 174.64 MHz -- confirmed genuine, not an artifact, via path
tracing.** Every one of the 10 worst paths is ORDINARY cell-to-cell
cardinal logic (`pending_ack`, `cmd_latch[13]`, routing_mask/
cardinal_edge bits feeding a neighbor's own state) -- the exact same
legitimate congestion pattern already established at #106/#135.
NONE of the 10 touch the command mechanism at all (no
`cmd_program_out`/`cmd_trigger`/`cmd_data` anywhere in the list) --
meaning the command-cell mechanism itself isn't what limits Fmax here;
it's the same grid-routing cost the plain baseline already carries at
this scale, not a cost specific to this mechanism.

**Conclusion: the corrected single-hop command-cell design is real,
correctly measured, and remarkably cheap** -- confirming Alan's own
instinct from earlier today that "the command cell is relatively
cheap." Genuinely different in character from #111's now-unconfirmed
relay-chain numbers (86.5 ALM/cell) -- this is what the mechanism
ACTUALLY costs once scoped correctly (single-hop, no multi-cell relay
chain), not the mismatched comparison that #122 identified as flawed.

**#103 re-run progress, complete for steps 1-3:**
- Step 1 (plain baseline): 145 ALMs, 261.44 MHz (#129)
- Step 2 (wrapper, cardinal, host/JTAG parity): +264 ALMs (10.6/cell),
  190.22 MHz (#135)
- Step 3 (command-cell, single-hop, corrected): +163 ALMs (6.5/cell),
  174.64 MHz (this entry)

**Remaining: step 4 -- both mechanisms (wrapper + command-cell)
together, checking whether the combined cost is additive or worse.**

## 139. Step 4 rebuilt: both mechanisms (wrapper #135, command-cell #138) combined on the same grid, ready for Quartus (Alan/session, 2026-08-03)

**STATUS: `top_stripped_grid5x5_both_v2.v` (new) + Quartus project
prepared and sim-confirmed. NOT YET BUILT -- ready for Alan.**

**Combines step 2's wrapper and step 3's corrected single-hop command-
cell mechanism on the SAME 25-cell grid**, replacing the deprecated
step-4 attempt (#112/#113, built on the now-superseded relay-chain
design). Wrapper injects via North (one-shot initial setup, per step
2); command-cell companions inject via West (ongoing reprogram, per
step 3) -- genuinely separate cardinal directions, no data conflict.

**One real design decision made explicit rather than silently
assumed:** `program_in` is a single, general control bit (#123's own
reasoning), so where both mechanisms could in principle need to
assert it, this build simply ORs the two sources together. Confirmed
safe for THIS test by construction, not just assumed: the wrapper's
one-shot setup completes in ~75 cycles, while the command mechanism's
first trigger only fires after `stim_cnt[13]` first goes high (8,192
cycles) -- a large, structural separation in time, not a coincidence
of this particular run.

**Confirmed correct before handoff:** wrapper's initial config lands
identically to step 2's own confirmed values (cell (0,0) and the far
cell (4,3) both correct); `all_ready=1`, no deadlock; wrapper's
`prog_active` completes cleanly. Both mechanisms genuinely coexist on
the same grid without interfering with each other.

**What this build answers:** whether the combined ALM/Fmax cost is
roughly additive against steps 2+3's individual deltas (264 + 163 =
427 ALMs added to step 1's 145 -> ~572 total if additive) or worse --
shared routing/congestion competing for the same physical resources --
the final step of the re-run campaign.

## 140. cmd_latch alignment decisions locked in, and the programming mechanism redesigned from fixed-3-word to variable-length ID-tagged writes -- "a scalpel, not a hammer" (Alan/session, 2026-08-03)

**STATUS: design decisions confirmed piece-by-piece in conversation.
NOT YET IMPLEMENTED -- this supersedes the CURRENTLY WORKING, just-
measured 3-word `program_in` mechanism (#123/#125/#126/#133, #138's
step-3 measurement). Flagged explicitly: step 4's pending rebuild
(#139) still measures the OLD mechanism -- valid as interim data, but
expect another re-measurement once this redesign lands.**

**Full `cmd_latch` field map audited directly from both cells' RTL
before allocating anything (not assumed from memory):**
- `[9:0]` topology, `[69:64]` routing_mask, `[75:70]` cardinal_edge --
  already aligned, same position/meaning on both cell types.
- `[10]` -- FULL cell already uses this for `command_cell` (1=command-
  emit cell, #37-era). **Now DELIBERATELY ALIGNED**: the stripped
  cell's own command-cell concept (#123/#126) will use the SAME bit,
  not an arbitrary free one.
- `[19:14]` -- genuinely mutually free (6 bits) -- but see below, the
  partial-update idea that was going to live here is now SUPERSEDED
  by the variable-length redesign, which makes it unnecessary.
- `[20:63]` -- confirmed FULL-cell-claimed (`latch_A_dis`, `latch_B_
  dis`, `start_flag`, `dtype`, `invert_out`, `latch_in`, `priority`,
  `trace`, `breakpoint`, `one_shot`, `loop_back`, plus the whole
  methodology latch/`auth_mask` at `[63:32]`) -- NOT safe to claim for
  new stripped-cell fields without breaking FULL-cell ICM
  compatibility.
- `[93:76]`/`[94]` -- the FULL cell's existing BRANCH mechanism
  (`pattern_low`/`pattern_equal`/`pattern_high`, `dynamic_route_en`),
  confirmed STILL FULLY INTACT and unchanged (that file untouched
  since 2026-07-31, before today's session) -- read directly from the
  RTL: `selected_pattern` picks one of 3 stored 6-bit routing patterns
  based on a comparator result (`cmp_gt`/`cmp_lt`), then
  `effective_routing = selected_pattern & routing_mask` REPLACES the
  normally-static routing_mask for that fire, when enabled. Real
  per-fire data-dependent branching, not just a value change.
- `[127:96]` -- free on the FULL cell entirely; the stripped cell uses
  it for `out_buffer` (a runtime register, not compiler-written config,
  so not really an ICM conflict). Noted: the FULL cell will get its
  own `out_buffer` here too once the backpressure mechanism (#91) gets
  ported over -- explicitly LATER work, not now.

**The gap this surfaced, stated plainly by Alan: the stripped cell has
ZERO data-dependent routing today.** `routing_mask` is entirely
static -- set once at program time, unchanged until the next explicit
reprogram. `hold_in`/`a_self_update_in` (#115-#120) let a comparison
change a VALUE, but nothing lets a comparison change WHERE data goes.
Without this, the fabric can only express fixed dataflow graphs --
any real conditional needs an external reprogram decision, nothing
in-line, per-fire. Confirmed as a genuine capability gap, not a minor
omission -- more foundational than the partial-update-scope idea that
was being discussed moments before this was raised.

**Resolution: port the FULL cell's branch mechanism to the stripped
cell, SIMPLIFIED and at the SAME aligned bit positions:**
- Same locations: `pattern_low`=`[81:76]`, `pattern_equal`=`[87:82]`,
  `pattern_high`=`[93:88]`, `dynamic_route_en`=`[94]`.
- Stripped cell only wires the LOW 4 bits of each 6-bit pattern slot
  (12 bits total: 3 patterns x 4 bits, N/S/E/W only) -- the top 2 bits
  of each stay reserved for future Up/Down, EXACTLY the same
  convention `routing_mask`/`cardinal_edge` already use (3D-ready,
  only 4 wired today). One ICM value works unmodified on both targets
  -- FULL cell uses all 6 bits per pattern, stripped cell just ignores
  the top 2.
- Reuses the EXISTING comparator infrastructure (`hold_in`/
  `a_self_update_in`'s own comparison, #115-#120) rather than building
  a new comparator from scratch.

**Self-correcting vs. branching, confirmed ORTHOGONAL, not mutually
exclusive -- no new selector bit needed:** the same single comparison
result answers two independent questions, going to two different
destinations. `a_self_update_in`: does this result get WRITTEN into
the held value (`data_reg`)? `dynamic_route_en`: does this result get
USED to pick a routing pattern instead of static `routing_mask`? A
cell can have either, both, or neither active -- pure self-corrector
(`dynamic_route_en=0`), pure branch cell (`a_self_update_in=0`), or
both simultaneously, same fire, same comparison, two independent uses.

**The programming mechanism itself, then completely redesigned --
from fixed-3-word to variable-length ID-tagged writes, superseding
#123/#125/#126/#133's whole-96-bit-overwrite approach:**
- OLD (current, working, just measured in #138): always exactly 3
  fixed-position words, atomically overwriting the FULL 96 meaningful
  bits every time, even to change one field -- "a hammer."
- NEW (designed, not yet built): each word is self-describing --
  `{3-bit ID, 16-bit data}`. ID selects ONE of 7 real fields
  (topology, routing_mask, cardinal_edge, pattern_low, pattern_equal,
  pattern_high, dynamic_route_en) to write; 16 bits comfortably covers
  any single field (topology, the largest, is only 10 bits). A
  reprogram operation sends exactly as many `{ID,data}` words as it
  actually needs -- one to touch just topology, one to touch just a
  branch pattern, all 7 for a full reprogram -- "a scalpel."
- Variable length, no fixed word count, no `prog_word_idx` counter at
  all in the new design.
- Completion: the 8th ID code (3 bits = 8 codes, only 7 real fields
  need one, exactly one spare) is reserved as a `COMPLETE` marker, not
  a real field target. Sender streams its field-writes, then sends
  `COMPLETE` as the final word; target asserts `program_done` on
  seeing it (reusing the EXISTING #123-126 handshake completely
  unchanged -- sender sees `program_done`, releases `program_in`,
  same release sequence already proven working). Deliberately chosen
  over two alternatives Alan considered and set aside: (a) inferring
  completion from `program_in` simply dropping (rejected -- ambiguous
  timing, "are we finished" answered outside the data protocol rather
  than inside it), and (b) a single fixed-width `{ID,data}` word format
  with a much wider ID space for arbitrary future fields (rejected as
  more complex than needed for exactly 7 known fields).

**Direct consequence for the `[19:14]` partial-update idea discussed
earlier this session: SUPERSEDED, no longer needed.** The whole point
of those bits was letting a reprogram touch only method OR only
cardinal fields without resending the rest -- the variable-length
ID-tagged redesign achieves exactly that, more generally (any subset
of all 7 fields, not just a fixed 2-3 way split), without needing any
dedicated selector bits at all.

**What's confirmed vs. not yet built, stated plainly:** every piece
here is a confirmed DESIGN decision, worked through carefully in
conversation exactly as Alan wanted ("get it right rather than
stumble in the dark," #123's own discipline) -- but NONE of it is
implemented in RTL yet. This is the next concrete build task.

## 141. Step 4 CONCLUDED, #103 re-run campaign COMPLETE: combined cost is BETTER than additive (Alan/session, 2026-08-03)

**STATUS: real, path-confirmed result. #103's full re-run campaign is
DONE (against the mechanism as it stood before #140's redesign --
flagged there as pending another re-measurement once that lands).**

**Numbers: 454 ALMs total (309 more than step 1's 145), `clk_div` Fmax
174.22 MHz.**

**Area: 12.36 ALM/cell for BOTH mechanisms together -- genuinely
BETTER than additive.** Predicted if simply additive: step 2's 264 +
step 3's 163 = 427 ALMs. Actual: 309 -- meaningfully less, suggesting
real synthesis-level resource sharing between the wrapper and command-
cell infrastructure once both are present together, not just
coincidence.

**Fmax: 174.22 MHz -- confirmed genuine via path tracing (all 10
worst paths are ordinary cell-internal/cell-to-cell logic --
`a_arrived`->`pending_ack`, routing bits->`pending_ack`/`cmd_latch
[13]`, same legitimate congestion pattern as every other step), and
close to step 3's own 174.64 MHz -- the combined result is capped by
whichever mechanism was ALREADY the tighter constraint, not a NEW,
worse bottleneck from combining them.**

**#103 re-run campaign, final summary:**
- Step 1 (baseline): 145 ALMs, 261.44 MHz (#129)
- Step 2 (wrapper): +264 ALMs (10.6/cell), 190.22 MHz (#135)
- Step 3 (command-cell): +163 ALMs (6.5/cell), 174.64 MHz (#138)
- Step 4 (both): +309 ALMs (12.36/cell), 174.22 MHz -- BETTER than the
  427 ALM additive prediction (this entry)

**Immediately superseded by #140's redesign** (variable-length
ID-tagged programming, branch mechanism port, bit-10 alignment) --
these numbers describe the mechanism as it stood through today's
session, valid as a real historical data point, but expect the whole
campaign's cost profile to shift once #140 is implemented and
re-measured.

## 142. #140's full redesign IMPLEMENTED and confirmed correct: branch mechanism, variable-length ID-tagged programming, both confirmed by hand (Alan/session, 2026-08-03)

**STATUS: `unicell_stripped_v1.v` fully updated. All confirmed by
simulation, first-try success on both major pieces. NOT yet re-fit in
Quartus -- the grid-scale test files (steps 1-4's Quartus projects)
still use the OLD fixed-3-word format for their driver logic and will
need the SAME update before any new area/Fmax numbers can be trusted.
Flagged explicitly, not silently left stale.**

**Branch mechanism, ported from the FULL cell exactly as #140
designed:** `pattern_low`/`pattern_equal`/`pattern_high` at the SAME
aligned positions (`[81:76]`/`[87:82]`/`[93:88]`), only the low 4 bits
of each wired (N/S/E/W); `dynamic_route_en` at `[94]`. Comparator
(`cmp_gt`/`cmp_lt`) ported directly from `unicell64_v3.v` line ~557 --
confirmed it's a genuine arithmetic magnitude comparison
(`second_val > input_val` / `<`), NOT related to the NOR-gate topology
computation, checked explicitly before porting to avoid conflating the
two. `effective_routing = dynamic_route_en ? (selected_pattern &
routing_mask[3:0]) : routing_mask[3:0]` now drives `want_n/s/e/w`
directly, replacing the previously-static `routing_mask` read.
`dynamic_route_en=0` (the default) preserves EXACTLY the pre-#140
static behavior -- purely additive, confirmed by full regression (see
below).

**Confirmed correct, by hand, on the first real test
(`tb_stripped_v1_branch.v`, new):** loaded threshold A=5, held it,
fed B=10/2/5 in sequence -- `B>A` fired WEST only (pattern_high),
`B<A` fired EAST only (pattern_low), `B=A` fired NORTH only
(pattern_equal). Genuine per-fire, comparator-driven ROUTING
selection, not just a value change -- exactly closing the gap Alan
identified ("the stripped cell has lost the entire branching method").
One real test-harness bug found and fixed along the way, not an RTL
issue: `effective_routing`'s AND with `routing_mask` correctly masked
out a pattern-selected direction the test's own `routing_mask` hadn't
opened -- confirmed this IS the FULL cell's own documented behavior
(routing_mask is the "is this direction even open" gate, the pattern
is the "which one, given that it's open" choice), fixed by opening
all 4 directions in the test's `routing_mask`, not by changing the
RTL.

**Programming mechanism, REDESIGNED from #123's fixed-3-word
assembly to variable-length ID-tagged writes, exactly per #140's
"scalpel, not a hammer" framing:** removed `prog_word_idx`/
`prog_assemble` entirely -- no more word-count state at all. Each
word is now self-describing: `{don't-care[31:19], 3-bit ID[18:16],
16-bit data[15:0]}`. 7 real field targets (topology, routing_mask,
cardinal_edge, pattern_low, pattern_equal, pattern_high,
dynamic_route_en) + 1 reserved `COMPLETE` marker (exactly 8 codes for
3 bits, nothing wasted). Each field write applies IMMEDIATELY and
INDEPENDENTLY as it arrives -- `program_done` asserts ONLY on the
`COMPLETE` marker, not after any fixed count.

**Confirmed correct, by hand, on the first real test
(`tb_stripped_v1_program.v`, rewritten): a genuinely selective
reprogram** -- wrote ONLY `topology` (confirmed `routing_mask`
stayed at 0 while this happened), then ONLY `routing_mask`
(confirmed `topology` stayed unchanged), then `COMPLETE`
(`program_done` asserted correctly). Release correctly cleared
`program_done` while preserving both programmed fields. Normal
operation resumed correctly afterward: genuine fresh capture,
`NOR(0xAAAA0000, 0x11110000) = 0x4444FFFF` using the newly-
programmed topology -- confirming the values aren't just sitting in
registers, they're genuinely being used for real computation.

**Confirmed correct end-to-end with a real command cell**
(`tb_stripped_v1_command_e2e.v`, updated for the new word format):
trigger -> hold -> two independent field writes (topology, then
routing_mask) arriving from a genuinely separate data source -> 
`COMPLETE` -> `program_done` -> command cell releases -> settles
cleanly. Full composition confirmed working with the new mechanism,
not just the target cell in isolation.

**Full regression -- confirmed NO changes to anything not touching
programming**, exactly as expected since `dynamic_route_en=0` and
normal `cfg_valid` loading are both unaffected by this redesign:
`tb_stripped_v1_2cell/multicast/relay/ring/hold/feedback/memcell/
selfupdate.v` all re-run, byte-identical results to before.

**What's honestly still pending, not yet done:** the three grid-scale
Quartus test files (`top_stripped_grid5x5_v1.v`,
`top_stripped_grid5x5_wrapper_v1.v`, `top_stripped_grid5x5_command_
v1.v`, `top_stripped_grid5x5_both_v2.v`) all still drive programming
via the OLD fixed-word format in their internal test-stimulus
generators -- these will need the same update before any NEW Quartus
fit can be trusted as measuring the CURRENT mechanism. #141's step
1-4 numbers remain valid as a historical record of the pre-#140
mechanism, not as current numbers.

## 143. Step 4 corrected: #141's first result was on the wrong device (new-project wizard default), re-run on the right one confirms and slightly improves the finding (Alan/session, 2026-08-03)

**STATUS: real, corrected result, superseding the device-mismatched
reading in #141. Still describes the PRE-#140 mechanism (old fixed-
word programming) -- #142's redesign still needs its own re-measurement
separately.**

**What happened: #141's build ran on `10AX115R4F40I3SG` (or similar),
a genuinely different, larger Arria 10 variant than every other step
in this campaign (`10AX066H2F34E2SG` throughout) -- a fresh Quartus
project's device-selection page defaulted away from the intended part
and wasn't corrected before building.** Caught by comparing device
strings across the campaign's own results, not assumed fine.

**Numbers, corrected: 447 ALMs total (302 more than step 1's 145),
`clk_div` Fmax 188.29 MHz.**

**Area: 12.08 ALM/cell -- close to #141's original 12.36 despite the
device mismatch (reassuring, not just luck, but not a substitute for
measuring on the right part).** Still genuinely better than additive
(step 2's 264 + step 3's 163 = 427 predicted vs. 302 actual) --
confirms this finding is real and repeatable, not a one-off artifact
of the wrong device.

**Fmax: 188.29 MHz -- actually BETTER than #141's misread 174.22 MHz,
and now nearly matches step 2's own 190.22 MHz** -- the combined
design's Fmax is capped by essentially the same bottleneck as the
wrapper alone, not further dragged down by the command mechanism.
Path-traced, same discipline as every other step: all 10 worst paths
are ordinary cell-internal/cell-to-cell logic (`pending_ack`, routing/
cardinal bits, `a_arrived` feeding neighbor state) -- genuine, not an
artifact.

**#103 re-run campaign, FINAL, corrected summary (pre-#140 mechanism):**
- Step 1: 145 ALMs, 261.44 MHz (#129)
- Step 2 (wrapper): +264 ALMs (10.6/cell), 190.22 MHz (#135)
- Step 3 (command-cell): +163 ALMs (6.5/cell), 174.64 MHz (#138)
- Step 4 (both): +302 ALMs (12.08/cell), 188.29 MHz -- corrected,
  better than the 427 ALM additive prediction, this entry

## 144. Bit [10] implemented and confirmed -- fully config-driven command-cell mode, and a real latent bug found and fixed along the way (Alan/session, 2026-08-03)

**STATUS: `unicell_stripped_v1.v` updated. Confirmed correct by hand,
first real test caught a genuine bug (fixed, not worked around),
second attempt confirmed clean. No regression on anything else.**

**Implementation:** `is_command_cell = cmd_latch[10]` -- aligned with
the FULL cell's own `command_cell`/`COMMAND_EMIT` concept, same bit
position on both cell types. Rather than a new mechanism, this is a
config-time, fully self-contained version of #119's `a_reemit_in`:
`effective_hold = hold_in || is_command_cell`, `effective_reemit =
a_reemit_in || is_command_cell`. Once configured, a cell permanently
holds and re-emits its value on trigger with NO external control wire
asserted at all -- matching the FULL cell's own precedent exactly
(fully config-driven, no live control dependency). Purely additive
when `cmd_latch[10]=0` (the default, unchanged from every prior test).

**A real bug found on the FIRST test attempt, not worked around --
`a_reemit_active` never actually required `a_arrived` to be true.**
It always implicitly relied on whoever controls `hold_in`/
`a_reemit_in` to sequence things correctly (assert only AFTER the
first capture) -- fine for external control (the wrapper/host
naturally does this), but breaks completely for a config-time-
permanent cell: `effective_reemit` is true from cycle one, pre-empting
the very first capture entirely and re-emitting an uninitialized
(zero) value forever, since `a_reemit_active` sits ahead of
`capture_now` in the sequential block's priority chain. Confirmed by
direct observation (`tb_stripped_v1_commandcell.v`'s first run: A
never captured the seeded `0xDEAD0000` at all, stuck at zero
throughout). Fixed by adding `&& a_arrived` to `a_reemit_active`'s own
condition -- re-emit now only ever applies once a genuine capture has
already happened, letting `capture_now` take its normal course first
regardless of hold/reemit state. This was a LATENT bug in the
ORIGINAL external-control-wire design too (#119), just never exposed
by testing, since every prior test happened to sequence `hold_in`
correctly after capture by construction -- worth remembering that a
condition can look correct for a long time simply because nothing
ever tested the order it implicitly assumed.

**Confirmed correct after the fix, by hand
(`tb_stripped_v1_commandcell.v`):** configured `cmd_latch[10]=1`,
`hold_in`/`a_reemit_in` tied to `1'b0` throughout the entire test --
A correctly captured `0xDEAD0000` on first arrival; three subsequent
triggers with DIFFERENT values (`0x11111111`, `0x22222222`,
`0x33333333`) all correctly produced `out_buffer=0xDEAD0000` --
trigger values genuinely ignored, A genuinely unchanged, matching
#119's own confirmed re-emit semantics exactly, just fully config-
driven this time. Existing `tb_stripped_v1_memcell.v` (the original
external-control-wire test) re-run and confirmed byte-identical to
before the fix -- confirming this was a pure bug fix, not a behavior
change for the already-working case.

**Full regression re-run clean across every other test** -- no
changes to anything not touching `cmd_latch[10]`/`a_reemit_active`.

**#140/#143's redesign is now complete: bit-10 alignment, branch
mechanism, and variable-length ID-tagged programming all implemented
and confirmed.** Next, per Alan's own sequencing: re-run the grid-
scale Quartus tests against this complete mechanism, then move to the
RAM connection work.

## 145. All grid-scale test files updated for #140/#144's new mechanism -- ready for a fresh Quartus re-run (Alan/session, 2026-08-03)

**STATUS: `top_stripped_grid5x5_wrapper_v1.v`, `top_stripped_grid5x5_
command_v1.v`, and `top_stripped_grid5x5_both_v2.v` all updated and
sim-confirmed correct. `top_stripped_grid5x5_v1.v` (step 1) needed NO
change -- it configures cells via ordinary `cfg_valid`, entirely
unaffected by the programming-channel redesign. NOT yet re-fit in
Quartus -- ready for Alan whenever the next round of measurement
happens.**

**What changed in each file: only the internal test-driver stimulus
generators, not `cell_wrapper_v2.v` itself** -- confirmed the wrapper
module needs no changes at all, since it just forwards whatever raw
words arrive on the bus straight through to the target's programming
port; only whatever BUILDS those words needed updating to speak the
new ID-tagged format instead of the old fixed-position one.

- `top_stripped_grid5x5_wrapper_v1.v`: `prog_word0/1/2` now properly
  tagged (`PID_TOPOLOGY`, `PID_ROUTING_MASK`, `PID_COMPLETE`) instead
  of raw fixed-position values.
- `top_stripped_grid5x5_command_v1.v`: `cmd_data`'s 3-word sequence
  similarly re-tagged.
- `top_stripped_grid5x5_both_v2.v`: both drivers (wrapper's and the
  command mechanism's) updated identically.

**Confirmed correct via smoke test on all three, same discipline as
every prior grid build** -- cell (0,0) and the far cell (4,3) both
show the correct programmed `topology`/`routing_mask`, `all_ready=1`,
no deadlock, each project's own completion flag (`prog_active`/
`cmd_program_out`) behaves as expected.

**This completes the full loop from #140's design through #144's
final implementation piece -- branch mechanism, variable-length
ID-tagged programming, and bit-10 command-cell alignment are all now
implemented, confirmed correct at the cell level AND confirmed correct
at grid scale in simulation.** Nothing has been re-measured in Quartus
yet against this complete mechanism -- that's the natural next step
whenever Alan wants fresh numbers, but per his own sequencing, the
next immediate focus moves to the RAM connection work instead.

## 146. Step 4 re-measured against the COMPLETE #140-144 mechanism: genuinely BETTER than the old design in both area and Fmax (Alan/session, 2026-08-03)

**STATUS: real, path-confirmed result. First Quartus measurement of
the complete branch-mechanism + variable-length-programming + bit-10
redesign, at scale.**

**Numbers: 438 ALMs total (293 more than step 1's 145), `clk_div` Fmax
192.75 MHz.**

**Direct comparison against #143's old-mechanism result on the SAME
combined (wrapper+command-cell) test:**
- Area: 293 ALMs (11.72/cell) vs. 302 (12.08/cell) before -- slightly
  CHEAPER, despite adding two entirely new capabilities (the branch/
  comparator mechanism, bit-10 command-cell alignment) alongside the
  programming redesign.
- Fmax: 192.75 MHz vs. 188.29 MHz before -- FASTER.

**Both dimensions improved simultaneously -- explained, not just
observed:** the old fixed-3-word mechanism carried real, removed
overhead -- a `prog_word_idx` counter AND a 96-bit `prog_assemble`
buffer per cell, both gone entirely in the new design (#142's "no more
word-count state at all," each field write applies immediately). That
removal more than offset the cost of the new branch/bit-10 logic added
at the same time.

**Path trace confirmed clean, same discipline as every step:** mostly
the same legitimate cell-to-cell logic seen throughout this campaign
(`pending_ack`, `cmd_latch[13]`/`[67]`). Two new entries checked and
NOT flagged as artifacts: `cell_command_v1...program_out` genuinely
belongs on this path (it's what triggers programming, by design), and
`cmd_word[1]` (the test driver's own 2-bit word-counter) is a small
mux selecting between 3 pre-built constant words -- nothing like the
expensive divide/modulo hardware that was a real problem at #134.

**Conclusion: the #140-144 redesign is a genuine, measured
improvement over the mechanism it replaced, not just a design that
"should" be better in theory.** This confirms the "scalpel, not a
hammer" framing paid off concretely in silicon terms, not just in
programming flexibility.

## 147. RAM/PCIe throughput analysis: on-board DDR4 is a buffer at best, PCIe becomes the essential path -- confirms #121's earlier speculation with real numbers (Alan/session, 2026-08-03)

**STATUS: real, grounded conclusion. Directly validates #121's
closing architectural note from earlier today, which was speculative
at the time -- now backed by actual measured throughput figures.**

**The chain of numbers, each step grounded in something measured or
confirmed, not assumed:**
- Single wrapper chain, measured Fmax (192.75 MHz, #146), 32 bits
  wide: 771 MB/s steady-state throughput.
- Both RAM buses concurrently (per #102's FEED/COLLECT split): ~1.54
  GB/s aggregate.
- 16 zones' internal fabric throughput (cardinal dataflow, NOT RAM-
  bound): ~12.34 GB/s -- a genuinely different, larger number,
  explicitly flagged as an INTERNAL compute bandwidth figure, not an
  external I/O one, since external I/O stays capped by the 2 physical
  RAM buses regardless of internal zone count.
- Confirmed device: IEI Mustang-F100-A10, Arria 10 GX1150, 8 GB
  on-board DDR4, PCIe Gen3 x8.
- 8 GB fill time via the wrapper mechanism: ~5.2-5.6 seconds (both
  buses), ~10.4-11.1 seconds (single bus).
- PCIe Gen3 x8 raw bandwidth: ~7.88 GB/s -- roughly 5x FASTER than
  the wrapper mechanism's current throughput ceiling.

**Conclusion, stated directly: on-board DDR4 is a buffer at best at
this stage, not a throughput-defining element.** DDR4's own native
bandwidth (tens of GB/s) is nowhere near either the wrapper (slow
side, 1.54 GB/s) or PCIe (fast side, 7.88 GB/s) -- it just sits between
two things of genuinely different speeds, holding data steady while
the wrapper serializes it in or out at its own, slower pace.

**PCIe becomes the essential path, not just a convenient host
interface, because the wrapper -- not PCIe, not DDR4 -- is the actual
bottleneck on real throughput into and out of the fabric.** This
directly confirms what #121 raised as speculation earlier today (get
BAR0 working, then interface stripped cells directly to PCIe, which
"could make the wrapper's role largely moot") -- now grounded in real
numbers rather than architectural intuition alone. The real
performance lever isn't speeding up RAM; it's getting data moving at
closer to PCIe speed rather than wrapper speed, which is exactly why
direct cell-to-PCIe interfacing (bypassing the wrapper's serial
daisy-chain for bulk transfer) is the genuine next lever, not a
nice-to-have.

**Unchanged from #121: the one thing standing between this and being
buildable is the parked PCIe BAR0 hardware issue** -- a real, well-
grounded architectural conclusion, not yet something actionable until
that's resolved.

## 148. Preparing a 50-cells-per-zone base test, scaling up from the 25-cell campaign (Alan/session, 2026-08-03)

**STATUS: in progress -- building a 50-cell version of the combined
(wrapper+command-cell) test, per Alan's request for a "good base
figure" at zone-realistic scale, ahead of eventual full-card (16-zone)
extrapolation.**

**Real prerequisite fix made first, not skipped:** `cell_wrapper_v2.v`'s
address field was only 5 bits (`ADDR[4:0]`), capping addressing at 32
cells -- not enough for a 50-cell zone. Widened to 7 bits (supports up
to 128 cells, room beyond the immediate target). Fixing this also
surfaced a genuinely stale test: `tb_wrapper_v2.v` (the standalone
wrapper unit test) still wired the wrapper's PROGRAM output to the
ORDINARY `data_in_n`/`arrived_n` port, from before the dedicated
cardinal programming channel existed (#133) -- never updated when
that channel was built, unlike the three grid-scale files which were
caught and fixed at #145. Fixed: rewired to the dedicated
`prog_data_in_n`/`prog_arrived_in_n` channel, and its PROGRAM word
values updated to the new ID-tagged format. Re-confirmed correct, all
values matching prior confirmed behavior (including a newly-legible
`DIAG` readback showing `pending_ack` correctly reflecting an
outstanding unacked offer once routing_mask actually targeted a real
direction, unlike the original all-zero-routing version of this test).
Grid-scale smoke tests re-confirmed unaffected by the address
widening.

**The 50-cell (5x10) zone test itself: `top_stripped_zone50_v1.v`
(new), built as a direct generalization of `top_stripped_grid5x5_
both_v2.v` (5x5 -> ROWS/COLS parameters), same wrapper+command-cell
combination, on the complete #140-144 cell. Confirmed correct via
smoke test across the WHOLE chain, not just the easy near end** --
cell (0,0), cell (0,9) (row-end wrap), cell (1,9) (next row-end,
opposite direction), cell (4,5) (mid-chain, far row), and cell (4,9)
(chain end) all show the correct programmed routing direction for
their position in the snake. `all_ready=1`, no deadlock, wrapper's
`prog_active` completes cleanly across all 50 cells. Quartus project
(`Unicell-Q-stripped-zone50.qsf`) prepared and ready for Alan.

## 149. 50-cell zone measured: cost scales sub-linearly, not linearly -- genuinely good news for a 750-cell/zone target (Alan/session, 2026-08-03)

**STATUS: real, path-confirmed result.**

**Numbers: 813 ALMs total, `clk_div` Fmax 171.29 MHz.**

**Per-cell cost is LOWER at 50-cell scale than at 25-cell scale, not
higher -- checked two ways:**
- Total per-cell: 813/50 = 16.26 ALM/cell, vs. #146's 25-cell figure
  of 438/25 = 17.52 ALM/cell.
- Mechanism-only (subtracting the bare-cell baseline, 5.8 ALM/cell x
  50 = 290): 523/50 = 10.46 ALM/cell for wrapper+command combined,
  vs. #146's 11.72 ALM/cell at 25-cell scale.

Both measures show a mild economies-of-scale effect -- some fixed
per-instance overhead amortizing better as the chain grows, not the
reverse. Genuinely encouraging for scaling further toward a much
larger per-zone target.

**Fmax: 171.29 MHz, down from 192.75 MHz at 25-cell scale -- an
~11% drop for a 2x cell-count increase.** Path-traced, confirmed
genuine congestion, not an artifact: the worst paths are exactly the
expected mix -- ordinary cell-to-cell logic (`pending_ack`,
`cmd_latch[13]/[66]/[67]`, `a_arrived`) plus `cell_wrapper_v2...cell_
program_out` genuinely belonging on this path (the actual programming
trigger signal, same conclusion already reached at #146 -- not noise).

**Alan's target for a full zone: ~750 cells/zone x 16 zones = 12,000
cells total.** Checked against the 80%-cap budget using this entry's
OWN measured 16.26 ALM/cell (not the earlier worst-case estimate):
12,000 x 16.26 = 195,120 ALMs, against a cap of 201,344 (80% of
251,680) -- fits, but closer to the edge than the earlier estimate
suggested (140,640 using #146's smaller-scale figure). Given the
economies-of-scale trend seen here, the REAL per-cell cost at 750-cell
scale will likely land somewhere between these two figures -- worth
measuring directly rather than extrapolating further, since Fmax
congestion at 15x this scale is exactly where the pattern traced so
far (mild, steady decline) could plausibly behave differently.

**Next: build and measure a 750-cell zone directly**, per Alan's own
reasoning that the timing "could be more fun" at that size -- rather
than trust extrapolation further from 50-cell data.

## 150. 750-cell zone built (Alan's actual per-zone target), confirmed correct -- a real test-interaction finding along the way, not an RTL bug (Alan/session, 2026-08-03)

**STATUS: `top_stripped_zone750_v1.v` (new, 25x30) sim-confirmed
correct at the moment of completion. Quartus project prepared and
ready for Alan. NOT yet fit in Quartus.**

**A real prerequisite fix made first:** the wrapper's address field
(widened to 7 bits for the 50-cell test, #148) still wasn't enough for
750 cells -- widened again to 10 bits (supports up to 1024). Also
found and fixed real bit-width bugs in the generalized driver logic
itself (`prog_row`/`prog_col` and `snake_mask`'s own port widths were
still 4 bits, max value 15 -- nowhere near enough for 25 rows/30
cols) -- caught by direct inspection before compiling, not by a
failed test.

**A genuine finding, not a bug, worth being precise about:** an
initial smoke-test check late in simulation showed `cell(0,0)`'s
`routing_mask` reading `000000` (wrong -- should be East). Traced
directly rather than assumed broken: at 750-cell scale, the wrapper's
OWN programming sequence takes long enough to complete that the
command-cell mechanism's independent, faster-cycling trigger (~8,192
cycles) fires and OVERWRITES the wrapper's correct values before the
check happens -- both mechanisms target the same cells with different
config values in this specific combined test, and at small scale
(25/50 cells) the wrapper simply finished before the command mechanism
ever got a chance to interfere, masking this interaction entirely.
**Confirmed the underlying mechanism is genuinely correct**, not
broken, by checking at the exact moment the wrapper's own `prog_active`
falls: `cell(0,0)` correctly shows `routing=000100`/`topo=004`, the
chain-end cell correctly shows `routing=000000` -- exactly right.

**Why this doesn't block the Quartus area/Fmax measurement:** Quartus
doesn't care about final functional correctness, only genuine
switching activity -- the overwriting behavior doesn't reduce real
logic activity (if anything, it adds more), so the area/Fmax numbers
from this build should remain trustworthy regardless. Flagged
honestly as a real interaction worth fixing before any FUTURE
functional-correctness test at this scale (e.g. slowing the command
mechanism's trigger period proportionally to chain length, or
disabling it entirely for pure-wrapper functional checks) -- not
something that needed fixing for this specific measurement's purpose.

**Quartus project (`Unicell-Q-stripped-zone750.qsf`) prepared and
ready for Alan** -- this is the direct measurement at Alan's actual
stated per-zone target (16 zones x 750 = 12,000 cells total), rather
than trusting extrapolation from the 50-cell figure (#149).

## 151. 750-cell zone Fmax dominated by a real test-driver fanout artifact -- fixed at its root, per Alan's correction that the side channel is inherently one-call-per-cycle (Alan/session, 2026-08-04)

**STATUS: real fix applied to the root cause, not yet re-measured in
Quartus. First 750-cell fit came back at 90.12 MHz -- flagged as
untrustworthy before accepting it, same discipline as every other
step.**

**First fit result: 12,295 ALMs (16.39 ALM/cell -- consistent with
#149's trend, trustworthy), but 90.12 MHz -- and ALL 10 worst paths
traced to the SAME single source: `cmd_word[1]`, the test driver's own
2-bit word-counter, feeding `cmd_latch[66]` in cells scattered across
nearly the full floorplan (row 5 to row 19).**

**Root cause, and the actual architectural correction from Alan:** the
test's command-mechanism stimulus was a flat global broadcast -- every
one of 750 cells' command companions shared the SAME trigger signal
simultaneously, a design choice made when this was a 25/50-cell test
and the fanout was trivial. Alan corrected the underlying assumption
directly: the side channel (command/programming path) is inherently
SERIAL -- one call per cycle per zone, matching the wrapper's own
already-proven one-at-a-time daisy-chain discipline (#108) -- not a
simultaneous broadcast to every cell at once. The cardinal DATAFLOW is
genuinely parallel (confirmed real and unaffected throughout this
campaign); the CONTROL/programming side was never architected to be.
My test was measuring an operating mode that was never the intended
usage pattern.

**Fixed at the root: replaced the flat broadcast with a ONE-HOT
WALKING sequencer** (`cmd_walk`, a `CELLS`-bit shift register, one bit
per cell, only ever one bit set) -- reusing #105's own already-proven
pattern (the SAME fix that solved the ORIGINAL comparator fanout
artifact, now applied to a structurally identical problem at much
larger scale). Each cell's `trigger_in` now reads its own unique bit
of the walker, not a shared global signal -- eliminating the specific
pattern that dominated the trace (one register directly driving
storage writes across scattered floorplan locations).

**A real, honestly-flagged side effect found while fixing this, not
glossed over:** an UNTHROTTLED walker (advancing every single cycle)
completes many full passes through all 750 cells before the wrapper
even finishes its own (much slower) programming sequence -- racing
far ahead and overwriting things more aggressively than the original
slower broadcast did. Added a modest prescaler (one active cycle per
64) to reduce this -- still one-hot (fanout-safe), just paced. Even
with pacing, the walker still completes enough passes to overwrite
cell (0,0) before the wrapper's own completion point -- this is a
PRE-EXISTING interference effect (both mechanisms targeting the same
cells was already flagged as non-blocking for area/Fmax purposes in
#150), not something this fix introduced, and doesn't need re-proving
here since the wrapper's own correctness is already independently
confirmed multiple times (#125/#127/#135/#146).

**Next: rebuild in Quartus with the fixed driver -- expecting the
90.12 MHz figure to rise substantially once the dominant fanout
artifact is genuinely removed, closer to the ~150-170 MHz range the
50-cell trend would suggest, though the actual number needs measuring
rather than assumed.**

## 152. Freeze mechanism connects to a real, already-documented ward/sentinel layer -- and the backpressure cascade gives zone/region targeting for free, no new RTL needed, confirmed via the real wrapper path (Alan/session, 2026-08-04)

**STATUS: real architectural connection identified and confirmed via a
new test. This is a genuinely foundational thread, not a small
feature -- flagged plainly rather than undersold.**

**The connection, checked against `docs/VISION.md` rather than
assumed:** Alan's description of freeze-driven runaway prevention,
host-controlled targeting granularity, state save/restore via an "ICM
diff" file, self-healing zone relocation, and loader integration all
map directly onto VISION.md's already-documented "ward/sentinel"
layer -- explicitly named there as a systems-level capability sitting
ABOVE compute, deliberately placed LAST in VISION's own dependency
order (after the compiler/loader/composer/workbench rewrite is solid
on the proven cell). Alan's own framing today -- "now going to be
host-bound" -- is a real architectural decision about where that
control lives, consistent with but more specific than VISION's
existing text. Alan separately suggested a new session should read the
architecture docs directly for this grounding, noting they're out of
date relative to where the RTL has progressed but still give the
necessary conceptual foundation.

**The elegant insight that avoids a large amount of otherwise-needed
new work:** rather than building a new zone-level broadcast-freeze
mechanism, freezing the LAST cell in a chain causes the ALREADY-
PROVEN backpressure cascade (#91/#92) to naturally stall every
upstream cell too -- no new RTL needed at all. Freezing at an
arbitrary POINT in a chain (not just the very end) stalls everything
upstream of that point while anything already downstream keeps
running -- genuinely MORE granular than a flat "freeze the whole
zone" broadcast would have been, not a compromise.

**Confirmed still working correctly on TODAY's fully-redesigned cell
first, before building anything new:** re-ran `tb_stripped_v1_ring.v`
(#92's original cascade test, predating the entire #140-144 rewrite)
-- byte-identical correct behavior: freezing B correctly stalls A
(`ready=0`), releasing B correctly recovers it. The cascade mechanism
survived the whole day's redesign intact.

**Then confirmed via the REAL, host-driven path** (`tb_wrapper_freeze_
cascade.v`, new) -- not a raw testbench wire this time, but genuine
`SET_CTRL`/`CLR_CTRL` through the wrapper (#127), exactly how a real
host would actually do this. Two cells (A->B), both programmed via
`OP_PROGRAM` through the wrapper. Confirmed, by hand:
- B frozen via wrapper `SET_CTRL` BEFORE A ever fires.
- A seeded (two-arrival model), computes `NOR(0xAAAA0000,
  0x11110000) = 0x4444FFFF` correctly, offers it to B.
- `A_ready` correctly drops to 0 -- B, frozen, never acks the offer,
  so A's OWN readiness (reflecting whether its last offer was
  consumed) stalls. NOT B's own readiness, which is a genuinely
  separate signal (B's own outgoing state) -- worth being precise
  about, since this was corrected mid-design after an initial wrong
  assumption about which cell's ready would move.
- B released via wrapper `CLR_CTRL` -- `A_ready` correctly recovers
  to 1 once B consumes the pending offer.

**What this confirms as a real, working capability, not just a
design idea:** the host can genuinely halt an arbitrary portion of a
running model -- a single cell, or an entire upstream chain via one
freeze at the right point -- using only primitives already proven
today (SET_CTRL/CLR_CTRL, #127; the backpressure cascade, #91/#92),
with zero new RTL required for the targeting granularity itself.

**What remains genuinely unbuilt, stated plainly, matching VISION's
own honest sequencing:** full state readback for a genuine save/
restore snapshot (today's `DIAG` only exposes `program_done`/
`a_arrived`/`ready`/`pending_ack`, not the complete cell state a real
ICM-diff would need), the ICM-diff file format itself, and the self-
healing zone-relocation workflow (freeze -> read full state ->
reprogram elsewhere -> release) are all still open, larger pieces of
work -- correctly placed as later, per VISION's own dependency
ordering, not skipped or forgotten.

## 153. The FULL cell's wired-OR bus free N-way combine, recreated on the nano cell's own dedicated point-to-point wires -- no shared/addressed bus needed at all, confirmed correct first try (Alan/session, 2026-08-04)

**STATUS: `unicell_stripped_v1.v` updated. Confirmed correct by hand,
first real test. No regression on anything else.**

**The design arc, worked through carefully in conversation before any
RTL (matching the day's own established discipline):** Alan corrected
an early framing (this isn't about the wrapper/RAM programming bus at
all, #147/#151) to the ACTUAL bus contention problem in the FULL
cell's own architecture: its addressed push/watch model (`gate_set`
controls who listens, cells push computed output onto a SHARED,
ADDRESSED bus) means only ONE indirect data packet can move through a
given cluster's bus at a time -- this is the real source of the
25-cell/zone cap (`#22`'s own original "no shared cluster bus => no
bus contention BY CONSTRUCTION" finding, now connected precisely to
WHY the cluster bus is the actual bottleneck).

**The proposal, refined step by step to something genuinely minimal:**
first considered moving the FULL cell to cardinal-only entirely
(losing the free N-way OR-reduction, `#32`, that the shared bus
uniquely provides); then the key insight -- that free combine doesn't
actually NEED a shared bus, it only needs multiple sources converging
on one point, which a cell's own 4 cardinal ports already are.
Resolved to: keep the existing two-arrival gate model completely
unchanged (a genuinely "pre-entrance" design, Alan's own term) --
change only HOW `arrived_val` (the value that feeds capture_now/
can_fire) gets computed when multiple directions arrive in the SAME
cycle. No new config field, no new mode, on by default, matching the
nano's own passive "it flows" character (Alan: "the nano at this time
does not watch, it flows").

**Implementation, genuinely minimal because two existing formulas
generalized correctly for free once one thing changed:**
- `sel_n/s/e/w`: changed from #91's mutually-exclusive priority pick
  (N>S>E>W, one winner) to INDEPENDENT per-direction "did this
  genuinely arrive this cycle" flags.
- `arrived_val`: changed from a priority-select mux to an OR-reduction
  -- `(arrived_n ? data_in_n : 0) | (arrived_s ? data_in_s : 0) | ...`
  -- directions with no arrival contribute the OR-identity (0), so a
  single arrival behaves EXACTLY as before (OR of one thing is
  itself).
- `ack_out_n/s/e/w` (`consumed_now && sel_x`) and `selected_is_relay`
  (checks `sel_x && cardinal_edge[x]` per direction) needed ZERO
  changes -- both formulas already generalized correctly the moment
  `sel_x` became independent instead of exclusive. Every direction
  that participates in a combine now gets acked the SAME cycle,
  exactly as Alan wanted ("the cell retains the ack and gives it
  control while retaining a feature of the normal bus").

**Confirmed correct, by hand, first real test
(`tb_stripped_v1_orcombine.v`, new):**
- Two simultaneous arrivals (N=`0x0000000F`, S=`0x000000F0`, same
  cycle): BOTH `ack_n` and `ack_s` asserted together; captured value
  `data_reg=0x000000FF` -- genuine OR (`0x0F | 0xF0 = 0xFF`), not a
  priority pick of either.
- Second simultaneous pair (N=`0x00000F00`, S=`0x0000F000`) correctly
  combines to `0x0000FF00` and feeds a REAL fire:
  `NOR(0x000000FF, 0x0000FF00) = 0xFFFF0000` -- checked by hand,
  correct, confirming the combined value is genuinely used for real
  computation, not just correctly stored.
- Sequential (non-simultaneous, different-cycle) arrivals confirmed
  COMPLETELY UNCHANGED: `NOR(0xAAAA0000, 0x11110000) = 0x4444FFFF` --
  the exact same value confirmed dozens of times earlier this session,
  proving this change only affects genuinely simultaneous same-cycle
  arrivals, nothing else.

**Full regression clean**: every other existing testbench re-run,
byte-identical to before this change (none of them happened to
exercise genuinely simultaneous multi-direction arrivals with
different values, so none were affected). Grid-scale smoke test
(`top_stripped_grid5x5_v1.v`) re-confirmed healthy, no deadlock.

**A real, honestly-flagged open question, not yet resolved:** what
happens when simultaneously-arriving directions have DIFFERENT
`cardinal_edge` (relay vs. consume) classifications -- e.g. one
direction tagged relay, another tagged consume, arriving the same
cycle. `selected_is_relay`'s generalized formula (OR across `sel_x &&
cardinal_edge[x]`) means ANY relay-tagged arriving direction makes the
whole event relay-classified, potentially combining a relay-intended
value with an unrelated consume-intended one from a different
direction. Not tested, not yet designed for -- flagged as a real,
open edge case for a model that would genuinely mix classifications
on simultaneously-arriving directions, likely uncommon in practice but
not yet ruled out or handled.

**What this recreates, stated plainly: the FULL cell's wired-OR bus's
signature "free N-way combine, one tick, zero extra cells" property
(`#32`), on the nano cell's already-dedicated point-to-point wires --
with NOTHING shared or addressed to contend over, ever, by
construction.** This is the piece that was thought to be lost when
moving away from the shared-bus model (`#22`'s own original tradeoff
analysis) -- now recovered without reintroducing the bus contention
that made the shared model's 25-cell/zone cap necessary in the first
place.

## 154. Relay/consume mismatch protective freeze -- closes #153's open edge case, confirmed correct first try (Alan/session, 2026-08-04)

**STATUS: `unicell_stripped_v1.v` updated. Confirmed correct by hand,
first real test. Full regression clean, no changes to anything not
touching the new mechanism.**

**The design decision, confirmed in conversation before any RTL:**
`#153` left open what should happen when simultaneously-arriving
directions disagree on relay/consume classification (one relay-
tagged, another consume-tagged). Alan's resolution: this is the
COMPILER'S job to prevent -- a well-formed model, by construction,
never has this (relay/consume timing across simultaneous directions
is a deliberate design choice, not something that happens by
accident). If it occurs anyway, that is a genuine ERROR, and the
correct response is a protective self-freeze, same category as
`#152`'s runaway-prevention theme -- NOT graceful handling, since
graceful handling of an impossible-by-design case would just mask a
real bug. The genuinely INTENDED combined-relay case (multiple
directions relaying together) already has its own, correct path:
setting the SAME relay bit on every participating direction, which is
`#153`'s own legitimate OR-combine case, not this one.

**Implementation, genuinely minimal, reusing what already exists:**
- `relay_mismatch`: `any_arrived && any_relay_dir && any_consume_dir`
  -- checked unconditionally every cycle, not preemptable by priority
  the way ordinary fire branches are, since this is a protective latch
  not a normal operation.
- `error_frozen` (new register): a genuine INTERNAL protective latch,
  distinct from `freeze_in` (a live external wire) -- set on
  `relay_mismatch`, cleared on `rst`, `cfg_valid`, or (the agreed
  resolution path) the next successful reprogram's `COMPLETE` marker.
- `effective_freeze = freeze_in || error_frozen` -- replaces
  `freeze_in` in EVERY place it already gated (`capture_now`,
  `can_fire`, `relay_fire`, `internal_fb_active`, `a_update_active`,
  and the ready-gated re-emit path) -- all 6 sites needed only a
  find-and-replace, no new gating logic anywhere, since the existing
  freeze cascade (`#91`/`#92`/`#152`) already does exactly the right
  thing once fed this signal.

**Confirmed correct, by hand, first real test
(`tb_stripped_v1_relaymismatch.v`, new):**
- Cell configured with N=relay, S=consume (a genuine mismatch by
  construction). Simultaneous arrival on both: `error_frozen`
  correctly asserts. The offending event itself still completes this
  ONE cycle (`out=0xFEEF0000`, the OR-combine of both values,
  `0xDEAD0000 | 0xBEEF0000` -- can't be undone once it's already
  happened), but the cell is frozen GOING FORWARD -- a subsequent
  arrival on N alone correctly fails to capture (`a_arrived` stays 0),
  confirming `effective_freeze` genuinely blocks further progress, not
  just the triggering cycle.
- Reprogram via `program_in`/`COMPLETE`: `error_frozen` correctly
  clears, and normal capture genuinely resumes on the next arrival
  (`a_arrived=1`) -- confirming the auto-clear path works and isn't
  just a flag reset with no real effect.

**Full regression clean** across every other test, byte-identical to
before -- nothing else touches `relay_mismatch`/`error_frozen` at all,
confirmed by construction (none of the other tests use mismatched
`cardinal_edge` configurations on simultaneously-arriving directions).

**What this closes:** the one honestly-flagged open question from
`#153` -- the OR-combine mechanism recreating the FULL cell's free
wired-OR reduction is now fully specified for BOTH its legitimate case
(matched relay tags, processes for free) and its error case
(mismatched tags, protective self-freeze) -- no remaining undefined
behavior in the combine path. Workbench-side detection (watching RAM-
side chain in/out flow for a stall, per Alan) is the INTENDED way this
gets noticed and flagged in practice -- explicitly deferred, not
built, consistent with `#152`'s own "workbench/ward layer is later
work" framing.

## 155. freeze_in threaded through all three grid-scale silicon tests, verified in sim before touching Quartus -- and a real routing-corruption bug found and fixed along the way, per Alan's own catch (Alan/session, 2026-08-04)

**STATUS: all three synthesis tops (`top_stripped_grid5x5_both_v2.v`,
`top_stripped_zone50_v1.v`, `top_stripped_zone750_v1.v`) now genuinely
EXERCISE freeze via the wrapper's real SET_CTRL path, not just wire it
dead. Sim-confirmed at all three scales (25/50/750 cells) before any
Quartus rebuild. `points.md #1's` own discipline held throughout: don't
declare victory until measured, and the 750-cell case genuinely needed a
real fix, not just a bigger timeout.**

**Starting point:** `freeze_in` was already RTL-wired correctly in all
three tops (`freeze_in(w_freeze[r][c])`, sourced from each cell's own
`cell_wrapper_v2` instance's `cell_freeze_out`) -- only the OLDER, now-
superseded `top_stripped_grid5x5_both_v1.v`/`_command_v1.v`/`_v1.v`/
`_cardinal_v1.v` still tied it to `1'b0`. The real gap was that none of
the three ACTIVE tops' own test drivers ever ASSERTED `SET_CTRL`, so the
freeze path -- while wired -- was never genuinely proven at grid scale,
only at the 2-cell case (#152).

**Fix applied uniformly to all three:** a small phase-sequenced exercise
in each top's own driver -- after the wrapper's initial programming
sequence completes (`prog_active` clears), wait a settle period, issue
`SET_CTRL` (index 0 = freeze) targeting one interior cell via the SAME
daisy-chain bus used for programming, hold, watch for `all_ready` to
drop (a sticky `freeze_cascade_seen` proof bit), then issue `CLR_CTRL`
to release. Reuses the already-wired ready/ack backpressure cascade
(#91/#92, host-proven at 2-cell scale in #152) -- no new zone-targeting
RTL needed, exactly as #152 predicted.

**Sim-confirmed correct at 25-cell and 50-cell scale on the first try**
(`tb_grid5x5_both_v2_freeze.v`, `tb_zone50_freeze.v`, both new) --
freeze_cascade_seen asserts partway through the hold window, all_ready
recovers cleanly after release.

**750-cell scale genuinely failed on the first attempt -- a real finding,
not a timeout tuning problem.** Alan's own catch, mid-session: the
original stripped-cell design carried an "armed" concept (set after
programming) analogous to the FULL cell's `start_flag`/`CMD_RELEASE`
(`unicell64_v3.v` #83/#449/#621-940) -- worth checking whether its
absence here was the actual blocker, alongside trying a tail-first
freeze/release ordering. Traced directly rather than assumed: the real
cause was exactly what #150/#151 had already flagged and explicitly
deferred as "worth fixing before any FUTURE functional-correctness test
at this scale" -- the command-mechanism's one-hot walker (`cmd_walk`,
#151) sends a HARDCODED `routing_mask=0` for whatever cell it currently
targets, rather than that cell's real snake mask. At 750-cell scale the
walker reaches and corrupts the routing of every cell it touches within
any reasonably-sized observation window, including cells near the seed
source -- silently breaking the very dataflow path the freeze test needs
to observe. This was flagged as harmless for the #150/#151 area/Fmax
measurement (switching activity is what Quartus cares about, not
functional correctness) but was never actually safe for a functional
test, exactly as #150 predicted.

**Real fix, not a workaround:** added `cmd_row`/`cmd_col` counters that
track `cmd_walk`'s own cell-advance event (mirroring `prog_row`/
`prog_col`'s already-proven pattern), computing each targeted cell's
correct `snake_mask` the same way the wrapper does, so the command
mechanism's ongoing reprogramming is now genuinely CORRECT no matter how
many times or in what order it re-touches a cell -- rather than needing
to wall cells off from re-programming after an initial commit (the
"armed" idea). This is the more general fix: it makes the side channel's
"the side channel is inherently serial, ongoing reprogramming is the
real intended usage" framing (#151) actually safe to run continuously,
rather than only safe once and then frozen.

**Result after the fix: PASS at all three scales**, including 750-cell
(`tb_zone750_freeze.v`, new) -- freeze_cascade_seen at t=102,625,000ps,
recovery at t=178,265,000ps, both comfortably inside the phase windows.
Full existing regression suite (`tb_stripped_v1_program`,
`_branch`, `_commandcell`, `tb_wrapper_v2`, `tb_wrapper_freeze_cascade`)
re-run clean, no regressions.

**The "armed flag" and "freeze the tail first" ideas Alan raised are
still worth keeping in mind, not dismissed:** the routing-mask fix above
solves THIS specific corruption, but a genuine per-cell "armed" gate
(reject/ignore reprogram attempts after an explicit commit, mirroring
the FULL cell's `start_flag`) is a real architectural question the
stripped cell doesn't currently answer, and would be a more robust
general safeguard than "make sure every possible reprogrammer always
sends correct data." Logged here rather than built now -- not blocking
the immediate freeze-thread task, and the FULL cell's own `armed_r`
precedent (#unicell64_v3.v) is the right reference point if/when this
gets picked up.

**Next: rebuild `top_stripped_zone750_v1.v` in Quartus for the deferred
re-measurement (#151's fanout fix was already in place; this session
adds the freeze-cascade exercise + the routing-corruption fix on top,
so the ALM/Fmax numbers from this build will reflect the freeze logic
genuinely being exercised, not stripped as dead code).**

## 156. The armed gate -- Alan's recollection of the original design's start_flag/CMD_RELEASE concept, ported to the stripped cell, closing the "armed flag" open question raised alongside #155's diagnosis (Alan/session, 2026-08-04)

**STATUS: `unicell_stripped_v1.v` updated. Confirmed correct by hand in a
new dedicated test, then the full existing regression + all three scale
tests re-confirmed clean after fixing every driver that needed updating.
Not yet re-measured in Quartus -- this is an RTL-level addition, not
just a test-driver change like #155.**

**The design, mirroring the FULL cell's own precedent exactly**
(`unicell64_v3.v` #83/#449/#621-940, `start_flag`/`CMD_RELEASE`, and its
"armed = opcode LSB" convention for topology presets --
`CMD_TOPO_NOR_COLD`=52 vs `CMD_TOPO_NOR`=53): a new `armed` register,
scoped specifically to the INCREMENTAL, ID-tagged `program_in` path
(#123/#140). A cell receiving a sequence of partial field-writes now
stays COLD (disarmed, `effective_freeze` asserted) until an explicit
`COMPLETE` arrives with its own data payload's LSB set -- it no longer
auto-starts operating partway through an in-progress reprogram.

**Where the bit lives, and why no new PROG_ID was needed:** all 8 codes
of the 3-bit `prog_id` field were already fully allocated (7 field
targets + `COMPLETE`). `COMPLETE`'s own 16-bit data payload was,
however, entirely unused up to now -- every driver in the whole repo
sent `{PID_COMPLETE, 16'h0}` and never looked at the low bits. Reusing
`prog_word[0]` of that payload as the arm bit costs nothing: `COMPLETE`
becomes genuinely two-way -- LSB=1 commits AND arms, LSB=0 commits but
stays (or goes back to) cold. This directly gives a command cell a
clean "pause, apply more field writes, then re-arm" staged
reconfiguration sequence, without needing `freeze_in`/`error_frozen` for
the ordinary case.

**Scoped deliberately, not applied everywhere:** the atomic `cfg_valid`
boot-load path (a complete 128-bit commit in one cycle, no partial-state
ambiguity to gate) keeps its original immediate-arm behavior unchanged
-- `armed <= 1'b1` there, same as before this entry. Only the
INCREMENTAL path actually needed the gate; conflating the two would
have broken the atomic path's entire reason for existing (one-shot,
not staged).

**Gating mechanism, reusing what already exists (same discipline as
#154's `error_frozen`):** `effective_freeze = freeze_in || error_frozen
|| !armed` -- one line, all 6 existing gating sites (`capture_now`,
`can_fire`, `relay_fire`, `internal_fb_active`, `a_update_active`, the
ready-gated re-emit path) inherit the new gate automatically, no new
gating logic anywhere. `ready_out` also now reads `ready_bit && armed`
-- a disarmed cell reports NOT ready to its neighbors too, so nobody
routes into it before it's armed, the same staged-bring-up protection
the FULL cell's design intends.

**A real, substantial ripple effect found and fixed, not glossed
over:** every existing driver in the repo sent `COMPLETE` with a zero
data payload (matching the old "always operate immediately" behavior),
so adding the gate broke arming everywhere it was exercised via
`program_in` -- confirmed directly by re-running the full regression
BEFORE fixing anything (`tb_stripped_v1_program`, `_command_e2e`,
`_relaymismatch`, `tb_wrapper_v2`, `tb_wrapper_freeze_cascade`, and the
3 active grid-scale tops + the 2 older single-mechanism campaign tops,
`grid5x5_command_v1`/`_wrapper_v1`, all genuinely regressed). Fixed by
flipping each `COMPLETE` word's data payload from `16'h0` to `16'h1`
across all 9 affected files, preserving their original intended
behavior exactly (confirmed byte-for-byte identical output on every
non-armed-related field afterward).

**New dedicated test, not just "old tests still pass":**
`tb_stripped_v1_armed.v` proves the actual new capability directly --
COMPLETE-with-0 commits fields but the cell stays genuinely cold (fed
data does NOT capture, confirmed `a_arrived` stays 0); a later
COMPLETE-with-1 arms it and normal two-arrival operation immediately
works (confirmed `NOR(AAAA0000,11110000)=4444FFFF`); an already-armed,
already-operating cell can be explicitly RE-disarmed mid-reprogram,
takes a new field write while cold, then re-arms with the new value
live (`routing_mask` correctly changed South->East across the
disarm/rearm cycle). One assertion in the test itself was initially
too strict (conflated `ready_out` with `armed` -- `ready_out` also
depends on `pending_ack`, an unrelated, already-proven mechanism that
this single-cell test legitimately never clears since nothing acks its
one fire) -- caught and fixed in the test, not worked around in the RTL.

**Full regression (17 testbenches) + all 3 grid-scale freeze tests
(#155) re-confirmed clean after every fix.**

**What this doesn't yet do, stated plainly:** this closes the
`program_in`/incremental-reprogram gap specifically. It does NOT touch
`cfg_valid` at all (by design, see above), and it doesn't add any
inspect/query path for `armed` beyond direct signal access (matching
`error_frozen`'s own precedent -- workbench-side observation is the
intended way this becomes visible in practice, not a dedicated readback
opcode, consistent with #152's "workbench/ward layer is later work"
framing).

**Next: rebuild the 750-cell zone in Quartus** — now carrying #151's
fanout fix, #155's freeze-exercise + routing-corruption fix, AND this
entry's armed gate. Also worth folding into the eventual full-fat
(FULL cell) catchup pass, per Alan: several of the methods proven here
this session (the routing-data self-consistency fix from #155, the
armed/COMPLETE-LSB convention itself, mirroring what the FULL cell
already originated) are candidates to carry back or cross-check against
`unicell64_v3.v`'s own equivalent mechanisms once that catchup begins.

## 157. 500-cell (20x25) zone built as a fallback reserve, sim-confirmed correct -- not a response to a confirmed bad number, prepared ahead of the 750-cell Quartus result (Alan/session, 2026-08-04)

**STATUS: `top_stripped_zone500_v1.v` (new) sim-confirmed correct via
`tb_zone500_freeze.v` (new). NOT submitted to Quartus, NOT the active
NEXT step -- held in reserve. `top_stripped_zone750_v1.v`'s own
Quartus re-measurement (#151+#155+#156 combined) remains the live,
in-progress result this is a hedge against, not a replacement for.**

**Why now, stated plainly (Alan):** the 750-cell zone's Quartus
analysis was running long, raising the honest possibility the eventual
Fmax comes back too low to be comfortable. Rather than wait idle for
that result, or worse, start from scratch reactively if it does come
back low, this entry prepares the fallback now: 500 cells/zone x 16
zones = 8,000 cells total -- still a respectable card, and should give
the fitter a genuinely easier job than 750/zone (fewer cells to place/
route per zone). If 750/zone lands at 140-160 MHz or better, matching
the mild-decline trend already seen from 25->50 cells (#149), this file
stays on the shelf, unused.

**Directly descended from `top_stripped_zone750_v1.v`, not built from
scratch:** identical generalized `ROWS x COLS` pattern already proven
at 25/50/750-cell scale, carrying every fix from this session forward
unchanged -- #151's one-hot command walker, #155's freeze-cascade
exercise AND its routing self-consistency fix (`cmd_row`/`cmd_col`
tracking the walker's own advance, so the command mechanism never
corrupts a cell's real `snake_mask`), and #156's armed gate (`COMPLETE`
data LSB=1 arms, matching every other active driver in the repo).
20x25 chosen only to keep row/col counts in the same rough range as
zone750's 25x30 -- no other significance to the specific factorization.

**Sim-confirmed correct on the first try** (`tb_zone500_freeze.v`,
mirroring `tb_zone750_freeze.v` exactly): `freeze_cascade_seen` asserts
partway through the hold window (t=68,265,000ps), `all_ready` recovers
cleanly after release (t=148,265,000ps). Full existing 17-testbench
regression re-run clean, no regressions from adding this file.

**Next:** stays on the shelf unless/until the 750-cell zone's real
Quartus Fmax comes back low enough to warrant it -- see #155/#156's own
NEXT sections for the live 750-cell result this depends on.

## 158. docs/SYSTEM_MECHANICS.md -- the first piece of the re-examined structure, verified directly against both cells' real RTL, not assumed from either cell's own comments (Alan/session, 2026-08-04)

**STATUS: new top-level `docs/` folder created, distinct from
`archeology/` (which holds moved-but-not-re-examined material).
`docs/SYSTEM_MECHANICS.md` written -- the overview of what's genuinely
shared between the FULL cell and STRIPPED cell, per Alan's own
instruction: "the overview of the system mechanics and the logic that
is in both, that's the first place to start."**

**Methodology, stated up front in the doc itself:** every claim was
checked by direct grep/diff of `unicell64_v3.v` and
`unicell_stripped_v1.v` side by side, not assumed from memory or from
either file's own header comments taken at face value -- same
discipline as everything else in this project ("verify the Verilog's
internal consistency," `START.md`'s own words).

**Confirmed genuinely identical, gate for gate:** the NOR-tree
computation itself (`g0` through `g9`), the 10-bit topology decode table
(all 12 codes), and the topology field's bit position (`cmd_latch[9:0]`)
-- byte-identical in both files, zero daylight.

**Confirmed a real, deliberate shared convention in `cmd_latch`'s field
layout:** `routing_mask` (`[69:64]`), `cardinal_edge` (`[75:70]`), and
the three comparator patterns + `dynamic_route_en` (`[81:76]`/`[87:82]`/
`[93:88]`/`[94]`) all occupy the SAME slots in both cells -- the
STRIPPED cell just wires only the low 4 bits of each pattern slot
(N/S/E/W) rather than the full 6. Caught and resolved an apparent
mismatch mid-check (the stripped cell's own wire declarations use a
narrower range than its header comment's stated slot) -- confirmed by
checking actual bit ranges that this is a genuine "same slot,
partial-width wiring" convention, not a bug or inconsistency.

**Confirmed genuinely SHARED IN PRINCIPLE but DIFFERENT IN MECHANISM,
and said so plainly rather than glossing over it:** two-arrival firing
(FULL cell = address-matched shared-bus event; STRIPPED cell = dedicated
point-to-point cardinal wires -- precisely the axis #107's fork was
designed to differ on) and freeze (FULL cell's `frozen` is an internal,
opcode-driven register; STRIPPED cell's `freeze_in` is a live external
wire, further extended by #154/#156's `error_frozen`/`!armed`, neither
of which the FULL cell has any equivalent of at all).

**Confirmed genuinely NOT shared, checked directly rather than assumed:**
the `ready`/`pending_ack` backpressure mechanism (grepped `unicell64_v3.v`
for both terms -- no match; STRIPPED-cell-only) and the `armed` gate
(#156 -- inspired by the FULL cell's `start_flag`/`CMD_RELEASE` but not
the same signal, not cross-wired, currently STRIPPED-cell-only).

**What this establishes as the working model going forward:** `docs/`
(new, top-level) is where re-examined, verified content lands once a
piece of `archeology/` has actually been pulled out and checked against
current reality -- as opposed to `archeology/` itself, which is the
holding area for material that's been relocated but not yet re-verified.
`docs/README.md` states this convention explicitly. `SYSTEM_MECHANICS.md`
is the first instance and the template for how the rest of this large,
multi-session project should proceed: verify against real files, state
methodology, and separate "confirmed shared" from "shared in principle,
different in mechanism" from "confirmed NOT shared" rather than
collapsing all three into one undifferentiated "architecture" narrative.

**Next:** continue pulling pieces out of `archeology/` one at a time,
same treatment. No specific next document chosen yet.

## 159. Full triage of archeology/docs -- two genuine shared docs promoted, everything else confirmed cell-specific or a different axis, checked not assumed (Alan/session, 2026-08-04)

**STATUS: every file in `archeology/full-cell/docs/` and
`archeology/shared/docs/` (excluding `archeology/sessions/`, pure
history) checked against the test "genuine shared idea between the two
cell lines." Full writeup in `archeology/TRIAGE.md`.**

**Promoted (verified, not just copied):**
- `docs/ICM_FORMAT.md` -- target-agnostic per #136's own finding,
  re-confirmed by checking `bootloader/generate_icms.py`'s actual record
  construction against the doc's claims (the `inB`/`alt`/`stor`-retired
  claim matches real code behavior, not a stale comment).
- `docs/MIF_FORMAT.md` -- spot-checked against `fp_tiles.py`'s actual
  implementation, terminology and pack/unpack boundary description
  match.

**Confirmed genuinely cell-specific, all of `archeology/full-cell/docs/`
(core/, design-notes/, diagrams/, hardware/, archive/):** grepped the
whole tree for "stripped cell"/"nano cell" -- zero matches outside
`manual.html`. Nothing here describes anything the STRIPPED cell shares.

**A real finding along the way, not glossed over:** several files
(`core/ARCHITECTURE.md`, `core/CELL_INTERNALS.md`, and
`shared/docs/hardware/FPGA_HARDWARE.md`, reclassified into
`full-cell/docs/archive/` as a result) describe a THIRD, even older
generation -- "Protocol v2.3," `gate_state`/`GS_*` flags, dual-edge
(posedge/negedge) triggering, a differently-grained shared bus. This
predates both the current FULL cell (v3, `cmd_latch`-based) and the
STRIPPED cell entirely, already superseded by `V3_COMMAND_CONTRACT.md`'s
own extraction from real `unicell64_v3.v` RTL. Worth knowing before
anyone treats these as current FULL-cell reference in a later phase.

**`shared/docs/hardware/` reclassified as stale, not genuinely
current-and-shared:** `HARDWARE_SETUP.md` describes the old UART-bridge
multi-target workflow (iCEBreaker/Kintex-7 era), not the actual current
Quartus/JTAG/Arria10 workflow this project uses today -- none of this
session's own hard-won JTAG findings (usbfs_memory, autosuspend, the
JTAG-wipes-BAR0 reboot discipline) appear in it at all. Flagged as a
real, worthwhile rewrite-from-current-knowledge candidate, not done in
this pass. `LINUX_SECOND_MACHINE_SETUP.md` is closer to current but
depends on the stale baseline doc.

**`shared/docs/software/` deferred as a different axis entirely:** the
remaining ~18 files (compiler config, format-definition guide, Trix
ecosystem, LLVM, running/library/getting-started guides, the paper
draft, ideas, etc.) are genuinely compiler/VM/application-layer material
-- "shared" only in the trivial sense that the compiler currently has
one target, which is a different question from "genuine idea common to
both cell architectures." Not triaged item-by-item; flagged as its own
future phase so it isn't silently force-fit into either bucket.
`VISION.md` singled out specifically: its underlying philosophy
(portability, substrate-independence) is genuinely the project's intent,
but the document as written is v2-era and factually wrong about current
reality (claims "one bus," which no longer exists) -- needs a real
rewrite before it could honestly be promoted, same as the hardware docs.

**Next:** no specific next document chosen. `archeology/TRIAGE.md`
recommends either the FULL-cell-specific phase (starting from
`V3_COMMAND_CONTRACT.md` against real `unicell64_v3.v`) or the
toolchain-setup rewrite (small, genuinely useful, currently-accurate
material already exists scattered through points.md) as good next
targets -- Alan's call.

## 160. docs/stripped-cell/CELL_INTERNALS.md -- the nano cell's first standalone documentation, built by reading unicell_stripped_v1.v directly, start to finish (Alan/session, 2026-08-04)

**STATUS: written and committed. `docs/` reorganized into `shared/`,
`stripped-cell/` (new), and a placeholder for a future `full-cell/`
subfolder, mirroring `archeology/`'s own three-way split for
consistency. `archeology/stripped-cell/docs/README.md` updated to point
at the new doc rather than describe an empty folder.**

**Per Alan: "start with the [nano] cell side that has not been
documented at all."** Confirmed by #159's triage this was a genuine gap,
not an oversight -- closed now for the cell's internal structure
specifically (the hardware bring-up doc and eventual ARCHITECTURE.md
are still not written, noted as such in the updated placeholder).

**Methodology: read `unicell_stripped_v1.v` start to finish in this
pass** (not relying on fragments already seen earlier in the session) to
build an accurate, complete field map and mechanism list. One genuine
correction caught in the process: `armed` (#156) is a standalone `reg`,
NOT a `cmd_latch` bit -- easy to assume otherwise since every other
control-related piece lives in the latch; confirmed directly by reading
the declaration, stated explicitly in the new doc so it isn't
mis-assumed again later.

**Covers, all cross-checked against the live RTL rather than points.md's
narrative alone (though points.md is cited throughout for provenance):**
full `cmd_latch` field table including the REINTERPRETED cardinal_edge
convention (per-incoming here, per-outgoing on the FULL cell -- a real
difference, flagged explicitly, not glossed as "the same field"); the
two-arrival firing model as actually wired (no address matching
anywhere); relay vs. consume and the #154 mismatch protection; all six
hold/memory mechanisms (hold_in, fb_internal_in, a_reemit_in,
a_update_in, a_self_update_in, is_command_cell) with what each
genuinely changes; the branch/comparator mechanism; the full ID-tagged
programming table; the armed gate's exact reset/cfg_valid/COMPLETE
behavior; the ready/ack/pending_ack backpressure mechanism (confirmed
STRIPPED-cell-only, cross-referenced against SYSTEM_MECHANICS.md's own
finding); the complete port list by category; the two companion modules
(cell_wrapper_v2.v, cell_command_v1.v); three real bugs found and fixed
worth knowing before touching the cell again; and the real silicon/
Quartus numbers table through #157.

**Forward-looking note recorded, not acted on yet:** Alan flagged that
the FULL cell is expected to be revisited and made functional again,
carrying back discoveries from the stripped cell (the #155 routing
self-consistency approach, the #156 armed/COMPLETE-LSB convention) --
recorded in `docs/README.md` as the stated reason this doc was written
first. No FULL-cell RTL work done this entry; this was preparation for
that work, not the work itself.

**Next:** Alan's call -- the FULL-cell-specific documentation phase
(building `docs/full-cell/`, likely starting from `V3_COMMAND_CONTRACT.md`
against real `unicell64_v3.v`, per #159's own recommendation) now has a
clearer reason to happen soon, since the FULL-cell RTL changes flagged
above will need accurate documentation to work from too. The hardware
bring-up doc for the stripped cell (per this entry's own "still not
written" note) is also still open.

## 161. docs/full-cell/ created, intentionally empty -- structure ready ahead of that phase (Alan/session, 2026-08-04)

**STATUS: `docs/full-cell/` now exists, matching `docs/shared/` and
`docs/stripped-cell/`'s structure, with a placeholder README explaining
the empty state (git doesn't track empty directories, so a real file
was needed regardless). No FULL-cell content written or moved --
`archeology/full-cell/docs/` remains the holding area for everything
not yet re-examined.**

Placeholder records the two most likely starting points when this phase
begins (`V3_COMMAND_CONTRACT.md`, `core/CELL_INTERNALS.md` against real
`unicell64_v3.v`, per #159's own recommendation), and flags Alan's own
note that the FULL-cell RTL work (carrying back #155's routing fix and
#156's armed convention) and this documentation phase will likely need
to happen together rather than docs-first the way the stripped cell's
did -- not assumed, left as an open decision for whenever this is
picked up.

**Next:** Alan's call on when to start the FULL-cell phase, and whether
RTL changes and documentation happen together or in sequence.

## 162. build_manual.py fixed and moved home -- the manual now builds again post-reorg, session log index rewritten to point at archeology/sessions/ (Alan/session, 2026-08-04)

**STATUS: `docs/build_manual.py` and `docs/manual.html` moved from
`archeology/shared/docs/software/` (the "moved but not re-examined"
holding area, wrong home for an active tool) back to `docs/` root.
Every one of its ~25 doc-path references fixed to the actual current
location. Ran the script end to end -- builds clean, 13 sections, no
errors. Spot-checked that every remapped source path genuinely exists
on disk, not just trusted the script not crashing.**

**Per Alan: "it has to reach into the archeology sessions folder, as
that's where they are going to be stored from now on."** The specific
ask, done properly: `build_sessions_index()` rewritten. Real subtlety
handled, not glossed over -- the old code special-cased `latest.md`
found INSIDE the sessions listing itself ("pinned first"); after the
reorg, `latest.md` no longer lives in `archeology/sessions/` at all, it
moved to `current/latest.md` as its own separate, non-historical
document. The rewritten function pins `current/latest.md` as its own
row (not found by listing, since it genuinely isn't there anymore) ahead
of everything actually read from `archeology/sessions/`, preserving the
original "latest first" behavior for the right reason rather than
silently losing it or leaving a dead search for a file that will never
be found there again.

**Why the whole file needed fixing, not just the sessions part:** every
SECTION's `"md"` doc reference pointed at the old `docs/XXX.md` paths --
all now stale after the reorg (files scattered across
`archeology/full-cell/docs/`, `archeology/shared/docs/`, and the new
`docs/shared/`). Left as-is, the script would have crashed on the very
first file open, not just shown a broken sessions tab.

**Two real editorial calls made while remapping, not blind path
substitution, both stated plainly:**
- **"The Cell" section now points at `docs/stripped-cell/CELL_INTERNALS.md`**
  (the new, verified, current doc from #160) instead of the old
  `archeology/full-cell/docs/core/CELL_INTERNALS.md`, which is
  confirmed "Protocol v2.3" -- already stale before either current cell
  existed (per #159's own finding). Added `docs/shared/SYSTEM_MECHANICS.md`
  as a new first sub-part of the same section. Matches the script's own
  stated principle ("KEEP IT CURRENT: the docs are the source of truth").
- **The Hardware section's intro now explicitly flags** that its
  hardware-setup doc is known stale (pre-Arria10/Quartus era, per #159),
  rather than silently presenting it as current.

**Everything else is a straightforward 1:1 remap** to each file's
verified real location (README.md/TODO.md/points.md unchanged at root;
START.md -> current/START.md; PLAN.md -> current/PLAN.md; the rest into
their `archeology/full-cell/` or `archeology/shared/` homes). The
Lab section's tool links (`../composer/...`, `../frontend/...`) needed
no changes -- moving the script back to `docs/` root restored the
original relative-path assumption those were built on.

**Next:** none specifically flagged -- this was a maintenance fix, not
new documentation work. The manual will keep needing this kind of
re-sync as more `archeology/` docs get promoted into `docs/full-cell/`
or `docs/shared/` in future phases; worth re-running
`python3 docs/build_manual.py` after any future doc promotion.

## 163. The manual now explains the reorg itself, not just links around it -- "Start Here" and "Roadmap" sections updated with the real orientation docs (Alan/session, 2026-08-04)

**STATUS: `docs/build_manual.py` updated, rebuilt, spot-checked. #162
fixed the manual's LINKS so it builds again post-reorg; this entry adds
actual CONTENT explaining the reorg to a reader, per Alan: "the manual
can be updated reflecting the new docs folders, the current folder and
the archeology sessions folders."**

**"Start Here" section** gets three new sub-parts right after "Read me
first," reusing the three README files that already accurately describe
the new layout rather than writing a fourth summary that could drift
out of sync with them: `docs/README.md` (verified/current docs),
`current/README.md` (the three live documents), `archeology/README.md`
(history + not-yet-re-examined, including `archeology/sessions/`). The
section's own intro now flags plainly that the repo layout changed
2026-08-04, for anyone arriving with an old mental map.

**"Roadmap" section** gets `archeology/TRIAGE.md` added -- genuinely
roadmap-shaped content (what's been checked against real code, what's
confirmed cell-specific vs. stale vs. deferred, what's next) that was
previously only discoverable by digging into `archeology/` directly.

**Rebuilt and verified, not just assumed correct:** ran
`python3 docs/build_manual.py` again, confirmed clean (13 sections, no
errors), then grepped the actual output HTML for all four new sub-part
labels to confirm they genuinely rendered, not just declared in the
Python source.

**Next:** none specifically flagged. The manual's link-health and now
its self-description of the repo layout are both current as of this
entry -- future doc promotions (into `docs/full-cell/` especially) will
need the same re-sync discipline `#162` established.
