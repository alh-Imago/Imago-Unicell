# Modular/composable cell builds + capability-aware `.icm` (CONCEPT — not implemented)

**Status: idea stage, captured 2026-08-04 per Alan: "this may have legs,
but it needs careful planning, and currently the ideas are way ahead of
what's in the git." Nothing described here is built. This file exists
so the idea survives intact until it's deliberately picked up — not a
spec, not a commitment, not verified against anything (there's nothing
built yet to verify against). Mirrors the naming convention of
`archeology/full-cell/docs/design-notes/manifest_board_mapping.md`, a
close cousin concept, itself tagged "(CONCEPT)".**

## Where this came from

Started from a real, measured result: `points.md` #170 gated the #140
comparator behind a compile-time parameter (`ENABLE_DYNAMIC_ROUTING`,
default off) after real Quartus timing data showed it was the dominant
cost on the 750-cell zone's critical path. The 25-cell isolation build
(#171) confirmed it dramatically — 71% ALM reduction, 46% Fmax increase.

That single win prompted the actual idea: if ONE mechanism can become an
independent build-time toggle, paying zero cost when off and full cost
only when a specific deployment actually needs it, more mechanisms could
get the same treatment — hold/memory, freeze, the OR-combine, is_command_cell's
underlying logic, potentially all of them.

## The core idea

Once every mechanism is its own `ENABLE_*` parameter, the meaningful
unit of "what a card can do" stops being "the STRIPPED cell" (a single
fixed design) and becomes **the specific combination of flags baked
into a given `.sof`**. This is a genuinely different axis from the
existing FULL-cell/STRIPPED-cell fork — FULL vs STRIPPED is already an
extreme, coarse-grained version of this same idea (two curated points
in a much larger possible space), but making the granularity a real,
deliberate choice rather than a fixed fork is new.

## The combinatorial-explosion problem, and the answer

N independent toggles = 2^N possible bitstreams. Nobody builds all of
them. The answer is curation: a small, deliberate set of **profiles** —
candidates discussed so far:
- **minimal** — base gate computation + cardinal wiring + ready/ack only
  (roughly what the 25-cell result just measured)
- **with-routing** — + the #140 comparator
- **with-memory** — + hold/feedback mechanisms (#115-120)
- **full-featured** — everything on (the overnight all-capabilities
  build currently running as of this note)

Not a final list — just the shape of the answer. Choosing the actual
profile set is itself a real design decision, not yet made.

## Three real, separate technical pieces this implies

Alan named these directly; recorded here with the honest scope of each,
since none are trivial even though none are individually huge:

### 1. A capability manifest per `.sof`

Once more than one variant exists, something needs to record which
`ENABLE_*` flags a specific compiled bitstream actually has — a small
feature vector, not a full resource map (distinct from the `.man`
board-manifest concept, which describes board HARDWARE differences, a
different axis entirely — see "Relationship to `.man`" below).

**Open question, not resolved:** where does this manifest actually
live? `.sof`/`.qpf` files are themselves NOT committed to git (per
`MANIFEST.in`'s existing convention — they're regenerated build
artifacts). A capability manifest that's hand-maintained separately
from the actual build risks the exact "summary drifted stale" failure
mode this project has already hit TWICE this session (`unicell64_v3.v`'s
own header comment admitting it drifted once; `#169`'s finding while
building `docs/full-cell/CELL_INTERNALS.md`). The manifest should
probably be **generated automatically by whatever build script produces
the `.sof`**, derived directly from the actual parameter values passed
to the top-level module for that specific build — never hand-written,
never allowed to exist independently of the thing it describes.

### 2. A `requires` field in `.icm`

Extends `docs/shared/ICM_FORMAT.md` (which currently declares itself
"runs on the Python VM, any supported FPGA, and future ASIC without
modification" — this doesn't contradict that, it refines it the same
way a portable script can declare its own package dependencies without
ceasing to be portable in format). Something like:
```json
"requires": ["dynamic_routing", "hold_memory"]
```
naming the same capability vocabulary as the `ENABLE_*` build
parameters — implying the vocabulary needs to be a single, shared,
deliberately-named list, not independently invented on the compiler
side and the RTL side.

**Open question, not resolved:** should FULL cell and STRIPPED cell
share the exact same capability vocabulary? `docs/shared/
SYSTEM_MECHANICS.md` already established some mechanisms occupy the
same `cmd_latch` slot on both cells while being wired differently (e.g.
`cardinal_edge`'s per-incoming vs. per-outgoing meaning) — a shared name
like `"dynamic_routing"` might need to mean subtly different things per
cell type, or might need cell-scoped naming
(`"stripped.dynamic_routing"` vs. `"full.dynamic_routing"`) to stay
honest. Not decided.

### 3. Compiler-side requirement inference — the hard, safety-critical part

This is the real work, and the one place a shortcut would be actively
dangerous: the compiler must *notice* when a model it's compiling ends
up using a gateable mechanism (any cell gets `dynamic_route_en=1`, any
cell uses `hold_in`/`fb_internal_in`, etc.) and emit the corresponding
`requires` entry automatically. A silently-incomplete requirements list
is worse than no requirements list at all — it would look safe while
not being safe. Nothing about how to implement this inference has been
designed yet.

### 4. Loader-side validation — the actual payoff

Reads a target zone's real capability manifest (piece 1) and checks it
against an `.icm`'s declared `requires` (piece 2, populated correctly
because of piece 3) *before* attempting to load — reject cleanly with a
clear reason, rather than silently sending config bits that land on
hardware that was never built. This is what turns "might silently
misbehave on the mismatched build" into "refuses immediately and says
why." No loader currently does anything like this; whether an existing
loader component could be extended for it, or whether this needs
building from scratch, is not yet investigated.

## Relationship to `.man` (`manifest_board_mapping.md`) — related, not the same

Worth being precise about this rather than conflating the two: `.man`
describes **board hardware differences** (DSP/BRAM counts, addresses,
comms interfaces) so the compiler can retarget across physically
different boards without hardcoding board knowledge into RTL. This
concept describes **compiled-in feature choices on the same board** —
which optional mechanisms a specific bitstream build happened to
include. Same *shape* of problem (a small, honest, shippable
description of "what does this specific thing actually have or offer"),
genuinely different axis. A future unified "everything about what this
specific deployment can do" description might eventually want to cover
both together — not proposed here, just noted as a possibility.

## What "careful planning" should mean before this gets built

Not a commitment to do these in order, just the honest list of what's
genuinely unresolved:
- The actual capability-name vocabulary (and whether it's shared or
  cell-scoped between FULL and STRIPPED)
- Where the per-`.sof` manifest lives and how it's generated
  automatically rather than hand-maintained
- The compiler's inference strategy — automatic-only, or does it need
  an escape hatch for a human to declare a requirement the compiler
  can't infer (e.g. a model reserving a capability it doesn't yet use)?
- Whether an existing loader component is extensible for the validation
  step, or whether this is new
- Which profile set is actually worth curating first, and whether
  "minimal" (no optional mechanisms at all) is itself a useful shippable
  profile or purely a measurement baseline

## Suggested first, low-risk step whenever this is picked up

Don't build the pipeline. Hand-write ONE capability manifest for the
750-cell zone rebuild (once it exists) as a pure format proof-of-concept
— no compiler inference, no loader validation, just confirming the
manifest shape itself is sensible before building anything that depends
on it existing.
