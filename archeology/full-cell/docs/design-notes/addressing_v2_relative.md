# Addressing v-next: fixed physical identity + relative (offset) dataflow + bridge scope-frames

PROPOSED change (not yet built). Converges several threads: the fusion problem, sentinel taps,
relocatable models, and the bridge model. Test AFTER the shift adder is confirmed; needs a NEW
CELL VARIANT (clone, never touch proven unicell64), proven cheaply on the SINGLE ZONE.

## The change
1. **Fixed physical identity**: a cell's physical address (CELL_ID) is its PERMANENT, unique
   identity, used throughout — for config, freeze, move, everything. Commands target the
   physical address. (Current model: logical address does double duty as identity AND data
   listen point — the conflation that caused the fusion trap.)
2. **Dataflow becomes relative (offsets)**: a cell's in/out addresses are OFFSETS from the pond
   root, not absolute. A cell's in=+0x010, out=+0x011; the next cell listens on +0x011 (proven
   chain pattern); cell 3 can also listen on +0x011 (fan-out). Position-independent wiring.
3. **Identity != dataflow**: separating these is the root fix. Sharing a DATA address no longer
   fuses cells, because config targets the distinct PHYSICAL identity. So:
   - Fusion problem GONE — shared-listen fan-out is now SAFE; duplicators may not be needed
     (could shrink the adder back toward 18).
   - Sentinel taps clean — a sentinel shares a data address (sees traffic) but keeps its own
     physical identity for config, so the watched cell can't disable/fuse it.

## Why auth survives (Alan's point — accepted)
Auth gates the COMMAND (every reconfiguration requires auth), not the MODE. So making physical
addressing always-on does NOT open a new hole — the gate travels with the command either way.
The CURRENT logical-addressing model already has the equivalent exposure (logical addrs reachable
in RUN, reconfig rides them). Fixed-physical-identity may make auth-gating MORE honest (gating a
fixed unique identity, not a reassignable logical one). Earlier worry (safety = mode-
inaccessibility) was too strong; safety = the auth check, which persists.

## The reference-frame resolution (the key insight)
"Pond or block/die as the frame?" -> NEITHER as a single global frame. Addresses are RELATIVE
WITHIN A SCOPE; the BRIDGE translates BETWEEN scopes:
- **Cell**: in/out = offset from POND root (pond-relative). Many ponds reuse the same offsets
  (e.g. +0x011) HARMLESSLY — pond-relative addrs never leave their pond.
- **Pond**: a reference frame; its BRIDGE is the seam. Every pond MUST have >=1 bridge pair (a
  given — no bridge, no outside comms). The bridge holds the pond's root-position in the block.
- **Block/die**: next frame up; ponds distinguished here. Pond->pond traffic is block-relative,
  translated back to pond-relative at the destination pond's bridge.
- Bigger (card/backplane): bridges all the way up. Each scope relative within itself; each
  boundary a translating bridge. = generalises the existing root+offset partition (low16=cell_id
  intra-block, high16=block_id) to N levels.
KEY: the bridge isn't just comms — it's the COORDINATE TRANSFORM between scope levels. The
"0x011 collides across ponds" worry DISSOLVES: pond-relative addrs are SUPPOSED to collide across
ponds (that's what makes them position-independent); the bridge keeps collisions from mattering.
So the "pond as reference frame" = mostly ALREADY BUILT — it IS the bridge (relative<->absolute
model, one level up). New work: the bridge carries the pond's block-position; the loader places
ponds-in-block by offset just as it places cells-in-pond by offset (recursive offset-placement at
each scale).

## Bridge also carries the WHITELIST (open: in-bridge or side cell?)
The bridge has an access-control/whitelist function (what may cross). UNCERTAIN whether the
whitelist lives IN the bridge or as a SIDE CELL alongside it (full model TBD). Note: a whitelist
is a gatekeeper -> like the sentinel, it may want to be a SEPARATE, independently-addressable cell
so it can't be reconfigured-around. SEPARATE the bridge's two jobs: TRANSLATE (coordinate
transform) and POLICE (whitelist). Test TRANSLATE first; the whitelist-placement question does
NOT block the addressing test.

## Test plan / sequencing (Alan)
1. Confirm the SHIFT ADDER on the CURRENT cell first. Its proof (two-arrival joins, stored-shift-
   in-graph, load-cold-release, duplicators) is about COMPUTATION/DATAFLOW and transfers
   UNCHANGED to the new addressing — not wasted. (Adder proves composition; addressing is
   orthogonal.)
2. THEN build a NEW-ADDRESSING CELL VARIANT (clone, never touch proven unicell64). Prove the
   addressing model on the SINGLE ZONE — cheap + fast (12-min loop), one zone is enough to
   confirm fixed-identity + offset-dataflow + individual-configurability + bridge translation.
3. THEN combine: re-place the adder on the new addressing as a known-good computation on a
   known-good addressing model. Prove computation, prove addressing, combine.

## Status
PROPOSED, post-adder. Strong direction — fixes fusion, safe taps, identity!=dataflow, simpler
loader, reuses the bridge as the scope-translator. Gating prerequisite: the new-addressing cell
variant proven in the single zone. Whitelist placement (in-bridge vs side cell) deferred.
