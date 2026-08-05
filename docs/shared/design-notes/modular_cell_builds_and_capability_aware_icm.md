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

## Loop mechanism vs. shift -- resolved: cannot substitute for it, and why that matters more than expected (2026-08-04)

Raised and resolved in conversation: could `#166`'s internal-feedback
loop (`fb_internal_in`) recover shift capability for free, now that
it's already built, without needing a dedicated shift addon at all?

**No -- and the reason is structural, not just a missing feature.** All
12 of the nano cell's topology codes are pure bitwise operations
(AND/OR/XOR/NAND/NOR/XNOR/NOT/PASS/ZERO/ONE), every one position-aligned
(output bit `i` depends only on input bit `i`). Looping any of them
against a held value, any number of cycles, still only ever combines
bits at the SAME position -- nothing in the gate set can move a bit from
position `i` to `i+1`. The standard bitwise-addition identity
(`sum=A^B; carry=(A&B)<<1; repeat`) is circular here: it needs shift as
part of the algorithm, so it can't be the thing that produces shift.

**The real, still-open, genuinely valuable experiment this points at
instead:** whether the loop can let a SMALL number of cells take on
MULTIPLE bit-positions' worth of ripple-adder work over several cycles
-- closer in spirit to how addressing let the FULL-cell Kogge-Stone
adder drop from 482 cells to 3 reused ones (`#72`/`#73`), just via
looping instead of addressing. Not yet tried. The ripple adder (`#75`,
2026-08-02) predates the loop mechanism (`#166`, 2026-08-04) by two
days -- it was built the dedicated-cell-per-role way because the loop
literally didn't exist yet, not because it was tried and rejected.

## Whether shift belongs in the base "Shell" core -- resolved: addon, not core, but a strong one (2026-08-04)

Given the above, Alan asked whether a single FIXED shift (not a full
variable barrel shifter) is worth adding to the core cell itself, even
at the cost of growing it, to move the system closer to a real ALU.

**Cost side: likely cheap, much cheaper than the comparator #170 just
removed.** A fixed-amount shift is fundamentally a WIRING operation
(bit `i` connects to position `i+1`), not a computation -- structurally
different from the comparator's real subtract/compare tree (6 LUT
levels, measured). The FULL cell's own design history already validated
the "scoped, not general" instinct here: `points.md` #106 confirms even
the FULL cell deliberately used a small fixed-pattern shift mux rather
than a full barrel shifter.

**But "grow the core, universal" repeats the exact mistake #170 just
fixed -- present-and-costing-something on every cell whether that cell
uses it or not.** Resolved: shift should be an ADDON like everything
else in Shell's established pattern (build-time gated, per-cell), not
unconditionally baked into the bare minimal core -- likely a strong
candidate for "default-included in most profiles" given what it
unlocks, but still opt-in at the mechanism level, not exempted from it.

**The finding that actually elevates this beyond "nice efficiency win":**
shift isn't just more efficient than the alternative -- for some
computations, it may be the ONLY thing standing between "buildable" and
"structurally unreachable at any cell count," per the loop-mechanism
finding above. Worth being precise that shift alone does not make a
cell an ALU (there's still no arithmetic ADD primitive in the topology
set) -- but it's the specific missing piece between "pure bitwise logic
fabric" and "a compact ALU becomes buildable out of a reasonable number
of cells." This is now the strongest-motivated addon candidate
identified so far, stronger than the comparator was before #170's fix,
precisely because its absence isn't just a cost, it may be a genuine
capability ceiling.

## Methodology for what comes next: costed baseline + addon deltas (2026-08-04)

**Concrete plan, recorded per Alan as session usage runs low — this is
what a fresh session should pick up first, in this order.**

**Step 0 (do first): fix nano's own open problem before building
anything on top of it.** `points.md` #176 — the `rst_sr`/`cmd_arrived`
global fanout failure found in the 750-cell rebuild — is still unfixed.
Nano needs to be genuinely stable before it's trustworthy as the
reference point everything else gets measured against.

**Step 1: establish one real, current 50-cell baseline build.** Not the
25-cell scale used for `#170`/`#171`'s comparator proof -- 50-cell is
already the agreed standard iteration scale (large enough to show real
congestion/interaction effects per Alan's own "bare shell will barely
move the needle" point; small enough to iterate quickly). One clean
Quartus measurement (ALMs, registers, Fmax) becomes THE reference every
addon gets compared against, not re-derived per addon.

**Step 2: every future addon gets a real, measured delta against that
baseline, not an estimate.** Exactly the method `#170`/`#171` already
proved works: build with the addon's `ENABLE_*` parameter off (matches
baseline exactly, confirms zero regression), then on, measure the ACTUAL
delta (extra ALMs, Fmax impact) at 50-cell scale. This turns "shift is a
strong addon candidate" (the earlier finding) from a reasoned argument
into an actual number.

**Step 3, a genuinely new axis raised by Alan, not previously
considered: placement, not just presence.** Even for an addon that's
confirmed worth including, WHERE it sits in the logic chain may change
its cost independent of whether it exists at all — e.g. does a shift
mechanism cost more feeding directly into the gate computation (early in
the critical path) versus appended after it (late)? This needs its own
measured comparison per addon, not assumed either way. Every addon's
entry in the eventual costed catalog should record both "cost if
included" AND "cost by placement variant," where more than one
placement is architecturally sensible.

**The end product this builds toward:** a real, measured catalog --
each addon's ALM/Fmax cost, and its cost by placement where relevant --
turning "which addons should a given Shell profile include" from
reasoned argument into actual comparable numbers. This is also what
gives the capability-manifest/`.icm` `requires` idea (above) something
concrete to mean -- a build's manifest can eventually cite real costed
tradeoffs, not just "this addon exists or doesn't."

## Suggested first, low-risk step whenever this is picked up

Don't build the pipeline. Hand-write ONE capability manifest for the
750-cell zone rebuild (once it exists) as a pure format proof-of-concept
— no compiler inference, no loader validation, just confirming the
manifest shape itself is sensible before building anything that depends
on it existing.

## Unicell-Shell: the authoring surface (points.md #180-182, 2026-08-05)

Everything above describes the capability-manifest/`.icm` machinery.
This section is the missing piece: how a person actually assembles one.
Single HTML page, same pattern as the composer/region-connector tools —

1. Start from the base cell.
2. Pick capabilities (this doc's `ENABLE_*` addons) and, where relevant,
   their **placement** (see below).
3. Pick a target: VM, or card.
4. If card — pick the specific board from the available `.man` files
   (`manifest_board_mapping.md`'s board-type description).
5. That selection becomes a **base file** — deliberately a DIFFERENT
   artifact from the per-`.sof` capability manifest described above.
   The capability manifest is DERIVED (auto-generated from an actual
   build, never hand-authored, to avoid drift). The base file is
   AUTHORED FIRST and DRIVES generation — opposite direction, same
   general shape. Keep the names distinct on purpose; conflating them
   would repeat the exact class of mistake #173 caught for
   `data_reg`/`a_data`.
6. The base file builds the VM directly, or (much more work) generates
   Verilog — the parts library has to compose without collision, which
   is where #173's register-footprint/field-ID accounting stops being
   tidy bookkeeping and becomes load-bearing: the generator needs a
   real, checkable table (part name → field IDs it claims → bit width)
   before it can be trusted to pack an arbitrary user-chosen combination
   into the unified latch.
7. The Composer works against the base file as its own ground truth —
   a layered extension of "Verilog is ground truth": the base file is
   ground truth for what it generates; the generated artifact is ground
   truth for whatever's built on top of it. Each layer trusts only the
   layer directly below it.

### Placement is sometimes a correctness axis, not just a cost axis (#181)

The existing "placement, not just presence" item above (from #179) only
considered COST — where an addon sits in the chain might change its
ALM/Fmax price. It can also change WHAT'S COMPUTED: a shift applied
before the core NOR computation vs. after it are not two cost variants
of the same function, they're two different functions.

Proposed classification, to be verified per-addon against real RTL, not
assumed from a mechanism's name or intent:
- **Position-invariant** — commutes with the core; placement is a pure
  cost/routing decision (the original #179 framing is correct here).
- **Position-sensitive** — placement changes the function. For these,
  placement is part of the capability's IDENTITY, not a knob on top of
  it — `requires` needs the placement baked into the entry name itself
  (`"shift_pre"` vs. `"shift_post"` as genuinely distinct capabilities),
  so a loader mismatch is caught rather than silently building the wrong
  function.

Not yet done: walking the real mechanism list (same scope as `#155`'s
parked "cell mechanics deep dive") to actually sort existing/candidate
addons into these two buckets.

### Per-addon cost data belongs on the .man file, card-specific and crowdsourced (#182)

Shell's UI should show a predicted LUT/ALM and Fmax cost for the user's
SPECIFIC card when they pick a capability — not a generic number, since
the same addon costs a different fraction of the die on a GX660 than a
GX1150 or any other board. This closes the loop from the costed-baseline
methodology already agreed (build off, build on, measure the real
delta, per `#170`/`#171`, extended into a standing practice by `#179`):
that measurement process is exactly what generates the numbers Shell
would display. "Measure addon costs" and "populate Shell's cost display"
are the same work, not two separate items.

Once the community starts contributing `.man` files for their own
boards, they can add their own measured cost figures the same way —
turning `.man` into the natural crowdsourced home for "what does this
addon actually cost on this board," not just "where are this board's
resources."

Scope note, precise rather than assumed: `manifest_board_mapping.md`
currently defines `.man` as pure board-hardware fact (resource map +
comms interfaces) and explicitly "NOT a compiler controller." A
per-addon cost table is a genuinely new field — doesn't violate that
rule (it informs a human's choice in Shell's UI, doesn't steer the
compiler), but deserves stating rather than silently folding in.
Proposed shape, not decided: a `measured_costs` section per capability
name (matching the `requires` vocabulary, including #181's
position-sensitive variants), each entry roughly
`{alm_delta, fmax_mhz_baseline, fmax_mhz_with, cell_scale_measured_at}`
— the scale field matters, since a delta measured at 25-cell scale and
one measured at 750-cell scale are not directly comparable, the same
discipline the hybrid `.icm` model already applies to card-stamping.
