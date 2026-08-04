# Tiled interconnect: bounded local buses as the answer to shared-bus contention

## The problem (real, was latent)
The fabric is ONE shared bus collected by WIRED-OR (array64 ~line 267: all firing cells' data
OR'd, last address wins). A single shared medium CANNOT carry parallel outputs: two cells firing
the same cycle — even to DIFFERENT addresses — merge their data and collide their addresses. In a
fabric whose whole premise is massive parallelism, same-cycle multi-fire is the EXPECTED state,
not an edge case. Latent so far only because tests were NARROW (chains fire one cell/cycle, wired-
OR never collides); the ADDER is the first WIDE structure (a whole prefix stage wants to fire
together) — which is why it surfaces now.

Dead ends (both kill the parallel dynamic AND scale): timed/serialised shared bus; per-cell bus-
contention arbitration. On a single shared medium there is no good option.

## The answer: TILES (the unit Alan named long ago = the solution)
A TILE = a model + its support, self-contained = a BOUNDED LOCAL BUS. A POND = a collection of
tiles. So: cells -> TILE (bounded local bus, one model) -> POND (tiles) -> block/die -> up via
bridges. Two tiles computing simultaneously are on SEPARATE buses -> cannot contend. Parallelism
lives BETWEEN tiles (many independent local buses firing at once, no shared medium); contention is
bounded WITHIN a tile (small, local, the model's own scheduling). The tile was ALWAYS the
isolation unit — the concept pre-existed; what was missing was the interconnect enforcing it.

The gap is ENFORCEMENT, not redesign: the current RTL implements a FLAT zone-wide wired-OR that
leaks across tile boundaries. The fix = make the interconnect honour the tile wall.

## The enabling primitive: "the wire stops here unless connected"
A configurable BUS BOUNDARY / segmentation gate: the shared medium TERMINATES at a boundary;
adjacent segments join ONLY if explicitly configured. Same SHAPE as the breakable-boundary
shifter (lanes) — a boundary cut by default, connected on purpose — now at INTERCONNECT level
instead of bit level. (Breakable-boundary is becoming a recurring primitive: bits, and now buses.)
Bridges are the ONLY sanctioned crossing between local buses. The per-pond bridge (already
mandated) is this at pond scope; now bring the boundary+bridge DOWN to the tile.

## LIF clusters -> one cluster per tile
A LIF cluster (~15 cells) is a dense knot of activity that MUST sit on its own tile (bounded bus),
or it would contend constantly on a shared bus. One cluster = one tile -> each cluster's internal
traffic stays local + independent; clusters talk only via bridges. The tile model SOLVES the
neural contention problem (many neurons fire in parallel, no shared-bus meltdown).

## Structural plasticity — TWO TIERS (Alan's key distinction)
Bridges lived at POND level (the scope that owns inter-tile connectivity). Any change requires the
target tile to FREEZE first (all reconfiguration is under freeze). Two very different operations:

1. **Widen / prune an EXISTING bridge** (CAPACITY, low stakes). More data needs to flow -> widen
   the bridge; stale/unused -> remove it. Changes CAPACITY, NOT reachability — connections that
   exist still exist, tile can't reach anywhere new. Local, bounded, housekeeping/GC. The WARD can
   mediate this readily (frequent, cheap). Most useful adaptive plasticity lives HERE, safely.
2. **Request connection to a DIFFERENT tile** (REACHABILITY, high stakes). Creates NEW reachability
   — tile A can now reach tile B where it couldn't. That's TOPOLOGY change = the security-critical
   act (exactly what an escaping/misbehaving component would request). A much HIGHER-level call,
   authorised at POND level or above (the scope that can SEE the tiles and legitimately decide
   connectivity). A tile CANNOT grant ITSELF a new connection (self-rewiring hazard); the POND
   grants it. Rare, elevated, heavily gated.

Principle: CAPACITY changes to existing links = local/low-authority; REACHABILITY changes (new
links) = high-authority. Splitting them isolates the safe, frequent operation from the rare, risky
one — most adaptive benefit at low risk; the dangerous part walled behind pond authority.

The ward-mediated dynamic path enables LEARNABLE TOPOLOGY (structural plasticity, not just weights)
for LIF nets. Caveats: it's MEDIATED / SCHEDULED / UNDER-FREEZE, NOT spontaneous real-time (adding
a bridge is a reconfiguration — takes time, resources, freeze); and the AUTHORISATION path
(cluster REQUESTS -> ward EVALUATES/authorises -> Shore EXECUTES under auth) must be tight,
especially for tier-2 (new connections).

## NEAR-TERM TESTABLE RTL (the concrete next build)
Minimal TWO-TILE bounded-bus test: two small local buses, a breakable wall between them, a bridge
as the only crossing. Prove: (a) two tiles compute INDEPENDENTLY without contending; (b) traffic
crosses ONLY through the bridge; (c) same-cycle fires in different tiles don't collide. Single-zone
sized. This turns "tiles are the answer" from architecture into proven mechanism, and makes the
adder "a tile" and each LIF cluster "a tile". THEN the loader allocates TILES (bounded segment +
bridge), not loose cells.

## Honest costs
Segmentation gates are silicon (each boundary = a configurable switch); boundary GRANULARITY is a
real trade (coarse=cheap but a model must fit; fine=flexible but more switches). Local/routed
interconnect costs more than a wired-OR bus — the trade is cheap-but-serial vs costly-but-parallel,
and the parallel option (tiles) is the one that scales. The bus, not the cell, was the scaling
bottleneck.
