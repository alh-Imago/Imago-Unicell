# Hybrid Hard-IP — DSP, memory & devices as addressed fabric resources

Status: DESIGN / next-axis spec (2026-06-28). Banked while basic-cell silicon proof is
in flight. NOT built — paper-freeze first, per discipline. Pulls together the scattered
DSP-fungibility / max-not-sum / .isi / save-state threads into one model, plus Alan's
two completing pieces (bridge-pair connection, latency-in-the-table).

## The core move

The fabric is content-addressable: a resource is anything that owns an address and answers
when targeted (`addr_match`, proven on silicon). So make hard IP ADDRESSABLE: give each
DSP block (and each BRAM block, and eventually each device) an address, hold those addresses
in a loader-managed list, and a cell that needs a multiply does NOT build it in NOR-gates —
it targets a resource address, hands over operands, reads the result back. Hard IP becomes a
callable resource on the same bus, addressed the same way as a cell.

Why: a NOR-fabric multiply is huge and slow; a DSP does it in one hardened block at speed.
The GX660 has 1,687 DSP blocks, ZERO used so far — a vast idle reserve of dense compute the
fabric can reach by address. Keeps the fabric a fabric (topology, routing, two-arrival logic,
bit-level methodology) and OFFLOADS heavy arithmetic to hard IP. This is what makes the
substrate competitive on real workloads (FlowTrix-on-silicon gets its arithmetic horsepower):
a pure-NOR fabric is elegant but arithmetic-poor; a fabric that calls 1,687 DSPs by address
is elegant AND dense.

## Connection = a BRIDGE PAIR; the resource stays stock and fabric-ignorant (Alan)

The resource does NOT manage its own connectivity — a BRIDGE PAIR does (one bridge IN for
operands, one OUT for results). Same insight as the inter-cage bridge: the bridge speaks
fabric on one face and the resource's native interface on the other. Consequences:
- The DSP/BRAM is UNMODIFIED stock hard IP — it knows nothing of addressing, the wired-OR
  bus, two-arrival firing, or operand origin. The bridge carries all fabric-awareness.
- CONNECTION REMAINS CELL ACTIVITY: a cell targets the bridge address, the in-bridge feeds
  the resource, the result returns through the out-bridge to wherever the cell pointed. The
  resource never participates in the addressing model; it just computes.
- UNIVERSAL ADAPTER: this is IDENTICAL for any resource. Memory (M20K/BRAM) behind a bridge
  pair is an addressed resource that takes address-in, returns data-out — the fabric doesn't
  care it's RAM not a multiplier. Eventually SATA/USB controllers the same way. One pattern,
  all hard IP. (This is the SAME shape as Device-Pond = driver-inside + bridge for Shore
  registration — the hybrid hard-IP model and the device-driver model are one mechanism at
  different scales.)

## Allocation table = LOCATION **and** TIMING COST (Alan)

The list is not just "here are the addresses." Per resource it carries:
- ADDRESS — how the fabric targets it.
- LOCATION — physical anchor coordinate (DSP/BRAM column) for placement. This is the .isi
  seed-coordinate / anchor-first placement work already done — DSP-consuming tiles pin at
  known columns, rest grows outward BFS.
- ACTION LATENCY — ticks from operands-in to result-out, INCLUDING both bridge-pair
  crossings. THIS is what preserves determinism: you cannot hold compile-time timing closure
  knowing WHERE a resource is but not HOW LONG its action takes. A multiply is not "instant",
  it is "this DSP returns in N ticks" — a known edge in the timing graph, exactly like a
  bridge latency or a cell's one-tick. Same rule as the bridge profile: known latency is the
  invariant; the resource table carries action latencies the way the bridge sidecar carries
  its own.

## Determinism — exclusive allocation, not a free-for-all

A shared resource called by many cells is CONTENDED, and contention = variable latency =
the non-determinism the fixed-latency fabric exists to banish (two cells hitting one DSP in
one tick: one waits, "waits" breaks timing closure). So the address list is NOT "call freely":
- DEDICATED (default, start here): the loader assigns each resource to ONE consuming site at
  load time. Max-not-sum: allocate for PEAK concurrency (one DSP per concurrent multiply,
  one scan of the program table). A resource is then owned like a cell — no contention, fixed
  known latency, determinism holds. The "address list" is really an ALLOCATION TABLE (which
  resource serves which site), resolved at LOAD, not a runtime scramble. DSPs are plentiful
  (1,687) so start dedicated.
- SCHEDULED SHARING (only under resource pressure): time-multiplex with a COMPILE-TIME-FIXED
  schedule; each caller's latency is a known constant (its slot). Still deterministic, more
  complex. Defer until DSP pressure actually exists.

## Lifecycle — allocate-on-load, reclaim-on-unload (Alan)

On a hosted system programs come and go. The pool is a simple FREE-LIST the loader manages:
claim addresses on load, return them on unload. Reclaim is TRIVIAL — just mark free — because
of the save-state guarantee: DSPs/resources DRAIN at freeze and hold NO persistent state
("cell states yes, DSP states no" — save happens only after a freeze, every block drained by
construction). So:
- Unload happens at a freeze boundary -> everything drained -> no half-finished operation to
  flush, no cleanup beyond marking the address available.
- The hybrid adds dense compute WITHOUT adding checkpoint surface — addressing DSPs does not
  complicate save/restore at all. This is load-bearing: it is WHY the allocate/reclaim model
  stays simple, and why the address-list approach is clean rather than a state-management mess.

## The full model (one mechanism, all resource types)

Hard IP (DSP, memory, devices) wrapped in a BRIDGE PAIR -> an addressed fabric resource.
Connection is CELL ACTIVITY through the bridge; the resource stays stock and fabric-ignorant.
The loader holds an ALLOCATION TABLE: address + location-anchor + action-latency per resource.
ALLOCATE-on-load from the pool, RECLAIM-on-unload — trivial because everything drains at
freeze. Determinism preserved: allocation EXCLUSIVE (dedicated default), every action latency
a KNOWN constant. Generalises down the resource hierarchy: DSP first (1,687 idle, fungible,
max-not-sum), BRAM/M20K next (same model), devices (SATA/USB) later (same model).

## Build order (when basic cell is silicon-proven)
1. Paper-freeze this model (allocation table schema incl. latency, bridge-pair interface,
   free-list lifecycle). Freeze once, then RTL — per the established discipline.
2. DSP bridge-pair RTL + one DSP as an addressed multiply resource; prove the addressed
   handoff + measured action latency on silicon (smallest test first).
3. Loader allocation-table + free-list (allocate-on-load / reclaim-on-unload).
4. BRAM as the second pool (same bridge-pair + table model) — the packed-adder / FlowTrix
   workloads want both dense multiply (DSP) and dense storage (BRAM).
5. Devices later — Device-Pond reuses the identical bridge pattern.

## DUAL-REFERENCE hybrid .icm — DSP path + pure-fabric fallback (Alan)

The hybrid creates two machine classes: DSP-available vs not (smaller parts, DSPs allocated
out, or pure-fabric machines). A DSP-only .icm would run only on the first class — breaking
the portability invariant (same file runs everywhere). FIX: the hybrid .icm carries BOTH
references per accelerated unit:
- the HARD-IP reference (resource address + action latency), and
- the complete PURE-FABRIC FALLBACK subgraph (cells + wiring + its latency).
The loader SELECTS at load time on target resources: DSP path where available, fabric path
where not. Same file runs everywhere; faster where there's hardware. Portability invariant
PRESERVED across the hybrid boundary.

The fallback is REAL designed logic, not a stub — it is the implementation you build anyway.
Canonical example: a 32-bit add is EITHER a hardened/DSP add (one addressed resource, fixed
latency) OR the 21-cell packed Kogge-Stone adder (packed_shift_adder.py — fits in ONE zone of
25, leans entirely on the STORED SHIFT proven on silicon 2026-06-28). The hybrid add-unit
carries both: "add via DSP at address X, or instantiate these 21 cells here if no DSP."

Engineering reality (decide deliberately):
- The two paths are NOT symmetric in cost. DSP = one address, one latency. Fabric = 21 cells
  with area + placement + its own latency. So choosing the fallback ALLOCATES + PLACES the
  subgraph, changing footprint and timing of that region. The .icm therefore carries, per
  unit: hard-IP ref + latency, the full fabric subgraph, AND BOTH latency figures so the
  compiler's timing graph is correct either way. Bigger file, but honest for both targets.
- Reuses the relocatable-interface discipline: the two paths are two implementations behind
  ONE interface contract (operands in, result out, same in/out addresses, different
  internals). The rest of the program wires to the interface and doesn't care which was
  chosen. (Same abstraction as feature-licensing's clean-subgraph interface.)
- DETERMINISM: the paths have DIFFERENT latencies (N ticks DSP vs M ticks fabric, N≠M). Fine
  for a fixed-latency fabric ONLY because the choice is made at LOAD time and the whole timing
  graph is recomputed for the chosen path (placement+timing already happen at load). NOT a
  runtime hot-swap — implementation is fixed when the program is placed; the schedule is built
  around that choice. Compile-time-fixed per load, both latencies known.
