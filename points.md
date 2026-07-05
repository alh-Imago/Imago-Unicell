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

## 4. Zone bridge address-decode (built)

**Status: built and confirmed working in isolation; exposed a real conflict (§6).**

`unicell_zone64_v3.v`'s bridge outputs used to broadcast every fire to every connected
neighbor unconditionally (`bridge_X_out_valid <= za_out_valid`) — harmless with exactly
one bridge partner (everything built before this session), genuine structural
contention with 2-4 active neighbors. Fixed: each direction now takes
`{DIR}_ZONE`/`{DIR}_ACTIVE` parameters and only asserts when the fired address's own
zone (`addr[15:5]`, since CELL_BASE = ZONE_ID<<5) matches that direction's configured
neighbor. Confirmed via trace: a real cross-cluster delivery now routes cleanly, zero
contamination from unrelated traffic.

**Important placement-vs-portability principle established while deciding where this
lives:** the address decode belongs in the zone *wrapper*, never the cell. A cell only
ever knows logical addresses (`input_address`/`output_address`); it has no concept of
"which physical cluster is my neighbor." That knowledge is placement-specific and
belongs exactly where `ZONE_ID` already lives — the layer that's expected to vary per
deployment. Keeping it there means the ICM stays a transportable, pure-logical
artifact (composer → VM → FPGA → ASIC, unchanged) with nothing new becoming
ICM-visible that would later need pulling back out. Same relationship as a network
packet (topology-agnostic) versus a router's routing table (topology-specific, varies
per deployment without changing the packet format).

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

## 6. Shared-broadcast fan-out vs smart address-decode routing — real conflict, open

**Status: precisely diagnosed, fix identified, not yet applied. Read this before
touching either the relay-insertion algorithm or the bridge router again.**

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

---

*Cross-reference: docs/design-notes/packed_adder_cluster_mesh.md has the full,
detailed write-up for everything touching the packed adder specifically (§3, §4, §5,
§6, §7, §8, §11). This file is the higher-level index across all of it, plus the
threads that aren't specific to that one design (§1, §2, §9, §10).*
