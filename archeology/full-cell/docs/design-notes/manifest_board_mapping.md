# The Manifest (.man) — board-type description for portable binding + retarget (CONCEPT)

Concept stage. A refinement of the hybrid/portability model: capture per-board knowledge in a
light, shareable, version-controlled file instead of hard-coding it into Shore RTL.

## What it is
A `.man` file is a PURE BOARD-TYPE DESCRIPTION — only hardware facts intrinsic to the board
type, identical for everyone who owns that board, so the whole file is community-shareable
(one Tang Nano manifest serves every Tang Nano owner). It carries:
- **Resource map**: logical resource (DSP_MUL, BRAM_BANK, ...) -> physical address / bridge
  gate-id, plus COUNT and ACTION-LATENCY per resource. (Latency is mandatory — the fabric's
  determinism depends on it; an address-only map would break the timing model.)
- **Comms interfaces the board OFFERS**: the channels the board presents (PCIe / USB / UART /
  SPI / ...). Multiple per card is normal. This is BOARD knowledge (the silicon exposes these),
  not user preference. The runtime DISCOVERS which offered path is actually wired up and selects
  it — selection isn't stored, it's discovered.

## What it is NOT (clean scope — three concerns, three owners)
- NOT language/front-end preference — the COMPILER owns language selection. Keeps personal
  settings out of the board file entirely.
- NOT per-user / per-installation config — the file is board-TYPE truth, fully shareable. (The
  earlier idea of bundling comms/language/user-overlay was rejected: it would tangle shared
  hardware facts with personal settings and pollute the crowdsourced artifact.)
- NOT a compiler controller — it DESCRIBES the board; it does not steer compiler behaviour.

## Relation to existing architecture (not a new parallel system)
This is the SERIALISED, per-card, community-ownable FORM of the hybrid ALLOCATION TABLE already
designed (resource -> address + location-anchor + action-latency, scale-invariant). Same data,
now a shippable file with a schema. Device-Tree precedent (Linux): board knowledge external,
core unchanged per board.
- Hosted system: the host does the binding pass (easy).
- Standalone: the Shore/boot-loader reads the `.man` from local flash at startup, iterates the
  table, populates the bridge-cell registers once. (= existing load-time binding, sourced from
  flash instead of host.) So: MANIFEST, not table-hard-coded-into-Shore — hard-coding would make
  the core RTL board-specific and violate the portability invariant. Core RTL stays identical
  across all boards; board-specificity lives in the swappable file.

## Two wrinkles the manifest alone does NOT solve (keep the existing mechanisms)
1. CAPACITY / CAPABILITY: a manifest maps WHERE a resource is, not WHETHER there's enough. A
   model needing 64 DSP_MUL cannot bind on a small board. The DUAL-REFERENCE `.icm` FALLBACK
   (pure-fabric subgraph, already in the model) handles can't-bind — the loader degrades to
   fabric instead of failing. Manifest = half the story; fallback = the other half.
2. The manifest binds to the UNICELL ABSTRACTION (cells/bridges), never raw vendor LUTs.

## Dual purpose (the genuinely new vector)
The same board description serves TWO stages:
- RUNTIME BINDING: place a portable model's resources on this board (above).
- COMPILE-TIME RETARGET: a manifest-driven / parameterised BACK-END so retargeting the UniCell
  substrate (and HLL->UniCell) to a new board = "write a manifest", no compiler/RTL change.
  FEASIBLE because the substrate IS the abstraction layer — the back-end's job is "place
  cells/bridges", and cells are uniform, so the board-specific part really is just the manifest
  (resource counts/addresses/latencies/comms).
- BOUNDARY (keeps it out of the reverse-engineering trap): manifest-generates-back-end works
  when the back-end targets the UNICELL ABSTRACTION. It does NOT work for HLL->raw-LUT bitstreams
  on undocumented fabric — a manifest can describe a board but cannot carry a proprietary
  bitstream format. So this steers toward the SOUND compiler-offshoot (target the substrate) and
  away from the hazardous one (raw fabric).

## Community property (the real win — framed as openness, not lock-in)
Porting a new Gowin/Efinix/Lattice/etc. board = write a `.man` mapping local resources to the
logical definitions. No compiler change, no core-RTL gate change. A GitHub repo of `.man` files
IS the "community database": light, version-controlled, additive. The win is that board support
is DISTRIBUTABLE (no central bottleneck), consistent with the open project — not a moat/lock-in.

## Status
CONCEPT only. Forward of the core. Slots under the hybrid model (docs/design-notes/
hybrid_hard_ip.md) and the compiler offshoot (docs/IDEAS.md). Picked up at the far-end tidy with
the other threads. Boards would each ship a `.man` (with their multiple comms interface types);
the core stays card-agnostic.
