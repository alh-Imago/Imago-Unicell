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

## Field addressability — resolved, not just speculated (2026-08-04)

One piece of the "careful planning" list above is no longer open: whether
individual fields in a unified/widened latch could be directly
addressable for writes. Yes — and it's not speculative, it's the
existing STRIPPED-cell programming mechanism (`points.md` #123/#140)
already doing exactly this: a small ID selects one field per word,
without touching the rest of the latch. Proven cheap, specifically
because the write-decode logic only runs while `program_in` is held —
mutually exclusive with normal fire logic, off the critical path
entirely (the opposite of the comparator's problem in #170, which was
expensive because it ran on every fire). Scaling the ID field wider
(3 bits/8 slots today -> e.g. 5 bits/32 slots for a fuller addon set)
is a trivial cost, not a new category of expense.

**Recommendation, not yet acted on:** STRIPPED's ID-tagged scheme is the
better pattern to unify Shell around, not FULL's — FULL's field-writing
grew more ad-hoc over time (whole-latch `CMD_RECONFIGURE` plus later
per-field `METH_SET_*` opcodes bolted on as needs arose); STRIPPED's is
uniform from the start.

**Two pieces still genuinely open:**
- **Reads.** Whether the wrapper's `DIAG`/`COLLECT` readback path is
  field-addressable the same way writes are, or reads back a coarser
  chunk, hasn't been checked. Don't assume symmetry with the write side
  until confirmed against the real RTL.
- **What happens when an ID names a field whose logic isn't compiled in
  for a given build (an addon that's off)?** Two options: (a) the write
  lands in storage and is simply never read by anything — simplest,
  matches "Shell always has the space, logic is optional" cleanly; or
  (b) that ID is excluded from the valid set entirely for that build, so
  using it is a detectable error rather than a silent no-op — safer, but
  needs per-build ID-validity tracking, which is really the SAME problem
  as the capability-manifest idea above, just applied at the field level
  instead of the whole-cell level. Not decided.

## Register footprint, as it actually stands today (2026-08-04)

Pulled directly from both files' real `reg` declarations, not
estimated — the concrete starting point for sizing a unified block:

| | STRIPPED (core config state) | FULL (core config state) |
|---|---|---|
| Main latch | `cmd_latch` — 128 | `cmd_latch` — 128 |
| Addressing | none | `input_address`(16) + `output_address`(16) |
| "A" operand | `data_reg` — 32 | `a_data` — 32 |
| Extra working reg | none | `data_reg` — 32 (DIFFERENT purpose, see below) |
| Small flags | `a_arrived`/`pending_ack`(6)/`program_done_r`/`error_frozen`/`armed` | `frozen`/`physical_mode`/`output_set`/`a_arrived`/`one_shot_fired` |
| **Total** | **170 bits** | **230 bits** |

A 256-bit unified block comfortably fits either side with real room to
spare. (FULL cell's TOTAL register footprint including pure pipeline/
staging registers -- `out_buf_*`, `cmd_emit_buf_*`, registered bus
inputs, debug readback staging -- is 452 bits, but more than half of
that is FULL-cell-specific internal sequencing with no STRIPPED
equivalent and arguably shouldn't need to be part of a shared map at
all.)

**A real naming trap found while doing this accounting, worth fixing
deliberately rather than by accident:** STRIPPED's `data_reg` and FULL's
`a_data` play the IDENTICAL role (the held "A" operand from the first
arrival). FULL cell ALSO has its OWN separate `data_reg`, used only for
`latch_in`'s re-emission buffering — a genuinely different register that
happens to share a name with STRIPPED's *different* register. A naive
unification by name would silently collide these. Same category of
mistake as the stale `auth_mask` header trap (`#169`) — caught here
before it could happen, not after.

## Addon delivery mechanism -- resolved: per-cell built-in, not a shared "bag" (2026-08-04)

Raised and worked through in conversation (Alan, "bag of resources"
idea): could addon hardware live in one shared pool that cells reach
into on demand, rather than each cell carrying its own copy?

**Resolved: no free lunch, and that's fine -- addon hardware must
physically exist, per-cell, wherever it's used.** Two real reasons, not
just convention:
- **A genuinely shared pool reintroduces exactly the contention problem
  #107's fork exists to escape.** The FULL cell's shared-bus contention
  is why it caps out around 25 cells/zone; anything multiple cells
  reach into needs arbitration, or enough parallel copies to avoid
  contention -- at which point per-cell copies were simpler to begin
  with.
- **Reaching a shared resource costs interconnect, and interconnect is
  already known to be expensive.** The 750-cell timing report (#170's
  own root cause) found a single hop to an IMMEDIATE NEIGHBOR was 43% of
  the whole critical path. A shared resource, by definition further
  away than a neighbor, would likely be worse for anything on the hot
  path.

**A genuinely useful exception, not yet built:** low-frequency, latency-
tolerant addons (the debug/DIAG readback path; the stub fields with no
real logic yet -- `trace`, `breakpoint`, `dtype`) are a real candidate
for pooling, since nothing time-critical is waiting on them. Hot-path
addons (the comparator, anything evaluated every fire) should stay
per-cell, generate-gated, exactly like #170's proven pattern.

**A second, orthogonal question resolved along the way: build-time vs.
runtime switching are NOT the same thing, and conflating them would
silently reintroduce the problem #170 just fixed.** `ENABLE_DYNAMIC_ROUTING`
(build-time, decided when Quartus compiles) is what saved 71% of the
area in #171 -- the hardware genuinely doesn't exist for cells built
without it. `dynamic_route_en` (runtime, a `cmd_latch` bit) saved
NOTHING on its own, because static timing analysis can't distinguish
"off" from "might turn on any cycle" -- the hardware has to exist
either way for there to be anything to switch. The correct combined
pattern, already proven today: build-time parameter decides PRESENCE;
an optional runtime bit on top of already-present hardware decides
ACTIVE USE this cycle. `ENABLE_DYNAMIC_ROUTING=1` + `dynamic_route_en`
toggling live is this pattern exactly.

**Confirms the "baked-in parts connect like the command cell structure"
instinct is correct, not a new mechanism to invent:** dedicated point-
to-point wires per addon module (`cell_wrapper_v2.v`/`cell_command_v1.v`'s
existing pattern), not a shared/arbitrated bus.

**Consequence, not eliminated by this resolution:** per-cell duplication
means every addon's cost multiplies by however many cells are in the
grid -- a cheap addon at 1x becomes real area at 750x. Curating which
addons are "baked-in core" vs. "optional, built in only for profiles
that need it" (the profile-set idea earlier in this note) still matters
even with the delivery mechanism settled.

## Suggested first, low-risk step whenever this is picked up

Don't build the pipeline. Hand-write ONE capability manifest for the
750-cell zone rebuild (once it exists) as a pure format proof-of-concept
— no compiler inference, no loader validation, just confirming the
manifest shape itself is sensible before building anything that depends
on it existing.
