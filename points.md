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
