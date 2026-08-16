# Super-cell tile library — design scope (CONCEPT, not yet built)

*Captured 2026-08-16, per Alan: "the compiler... will need the library
before we get there as it uses and touches so many things." Same
discipline as `modular_cell_builds_and_capability_aware_icm.md`'s own
"idea stage... needs careful planning" framing -- this file exists so
the shape survives intact until deliberately picked up, not a spec to
build against yet.*

## Why the old library doesn't carry over

`fp_tiles.py` (93 tiles, `TileLibrary`/`TilePlacer`) and `model_library.py`
(`ModelSpec`) are both built on the FULL cell's own model: a "tile" is a
list of `CellMapRecord`s, one per single-bit NOR-gate cell, wired
together via bus addresses from a `TileAddressAllocator`. `INT32_ADD` is
dozens of individually-addressed cells. That model is structurally tied
to the addressed-bus fabric -- exactly the thing `#107`'s fork, and now
the super cell, moved away from.

The super cell inverts the unit of composition entirely: `adder_cell_v1`
does a full 32-bit add in ONE cell (`points.md #248`/`#251`). A "tile" in
this world isn't a bag of single-bit gates anymore -- it's closer to
**one core-select choice plus its wiring**, or a small handful of
super-cells wired to physical neighbors (nano/`unicell_automaton_v1.py`'s
own "no addressing, no shared bus" model, which `icm_v3.py`'s own design
note already committed to for the same reason -- see `ICM_V3_FORMAT.md`).

So this is a new catalog, not a port. Worth stating that plainly rather
than trying to force-fit the old shape and finding out later it doesn't
hold, the way `#263`'s own logged ICM-portability collapse happened once
already on this project.

## What a "super tile" actually is

A named, reusable fragment of a `SuperGrid` -- one or more
`icm_v3.IcmV3Record`s, with:
- a **relative** wiring pattern (position offsets from some anchor cell,
  not absolute `row`/`col` -- a tile has to be placeable anywhere in a
  real program's grid, the same way `model_library.py`'s own `ModelSpec`
  is base-address-relocatable rather than baked to one fixed address)
- **named ports**: which cell + which cardinal direction is this tile's
  logical "in_a", "in_b", "out" -- the compiler-facing contract, same
  role `ModelSpec.inputs`/`outputs` play today, but expressed as
  (relative position, direction) instead of a bus address
- real metadata: cell count, core types used, whether it's been
  Quartus-confirmed or sim-only (mirroring `CORES_AND_WRAPPERS_
  REFERENCE.md`'s own honest proven/sim-only distinction, which this
  library should probably absorb rather than duplicate)

## The two real tiers, not one flat list

**Tier 0 -- single-cell primitives.** Each of the 6 cores, as a
1-record tile with named ports. Genuinely almost free to build now --
`icm_v3.py` already has every core's field table, and
`unicell_super_automaton_v1.py` already runs every one of them. This
tier is close to "the library IS the core catalog," barely more than a
thin naming/port-declaration layer on top of what already exists.

**Tier 1 -- composed multi-cell tiles.** Real wiring patterns built from
several super-cells -- e.g. the sentinel's own accumulator+comparator+
latch composition (`points.md #291`-`#298`, already proven as a
monolithic top-level, `top_sentinel_discrete_test_v2.v`, 78 ALM real
Quartus data) is the first obvious candidate: it already exists as a
proven pattern, "just" needs re-expressing as a placeable, named,
relocatable tile instead of a fixed top-level test file. This tier is
where the real design work lives (relative addressing, port contracts,
composing wiring across cells that must land on real physical neighbors
in whatever grid the compiler eventually places them into).

## Open questions, not resolved -- what "careful planning" should cover

- **Storage format.** `imago/library.py`'s `~/.imago/library/*.icm`
  filesystem convention is a real, working precedent (scan-at-startup,
  category subdirectories) -- does a super-cell library reuse that
  exact mechanism with icm-v3 files, or does something about relative
  positioning/port contracts need a genuinely different file shape
  `icm_v3.py`'s current record format doesn't have?
- **Category taxonomy.** `imago/library.py`'s existing categories
  (logic/arithmetic/neural/sorting/custom) predate the super cell
  entirely -- do they still make sense, or does a core-type-first
  taxonomy (ram/adder/accumulator/comparator/latch/nano, then composed)
  fit this new unit of composition better?
- **Relative-position representation.** Simplest option: offsets
  `(dr, dc)` from a declared anchor cell, matching how `CAGrid`/
  `SuperGrid` already think in `(row, col)` terms natively. Needs a real
  placement/collision check once the compiler actually instantiates a
  tile into a live grid (two tiles placed so their footprints overlap is
  a real error class, not yet handled anywhere).
- **Where Tier 1 tiles come from first.** The sentinel composition above
  is the one existing, already-proven candidate. Worth deciding whether
  Tier 1 starts there specifically, or whether a smaller, fresh
  from-scratch composed tile (e.g. a 2-cell running total: accumulator
  feeding a comparator) is a better first proof of the FORMAT before
  porting something as involved as the sentinel.
- **Registration API shape.** `model_library.py`'s
  `model_library.register(ModelSpec(...))` pattern (register at import
  time, no changes to the library file itself needed) is a real,
  reusable precedent independent of the bus-address baggage -- likely
  worth keeping the API shape even though the tile CONTENTS look
  completely different.

## Suggested first, low-risk step whenever this is picked up

Don't design the full format up front. Build Tier 0 first -- six
single-cell primitive tiles, one per core, with named ports -- as a
real, working, minimal proof of the port-contract idea, sim-verified
against `unicell_super_automaton_v1.py`'s own `SuperGrid`. That answers
the storage-format and port-representation questions with something
real and small before Tier 1's genuinely harder relative-placement
problem gets designed against it.
