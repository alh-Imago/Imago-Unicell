# TRIX / Concept-Graph / Bridge Archaeology — Reference Notes

*Started 2026-09-06. A working index into `archeology/onion/old_papers_
drafts.onion` (and related TRIX archives), built WHILE reading through
them, not after — Alan's own real "this is truly expansive, you may
need ref notes" instruction. This is a navigation aid for a body of
work large enough that re-finding a specific idea by re-reading
everything each session is not realistic. Complements, doesn't
replace, the real ledger (`points/points_active.md`) — this is
topical/spatial ("where is X"), the ledger is chronological ("what
happened when").*

*Status: first pass, in progress. Sections below get filled in as
each part is actually read — this is not a summary of the whole
archive from metadata, it's a running record of what's actually been
read and where it lives.*

---

## Archive map

**Real, important note: this dive spans TWO separate archives, not
one.** `old_composer_tool.onion` (already Tier 1) contains
`region_connector.html` — the real "cross-domain planner" UI (found
only because Alan specifically recalled it existed, not from the
metadata-only inventory pass) — sitting alongside `unicell_composer.html`
and the real example `.icm` files already used for cell-count checks
in `#659`. Everything else below is `old_papers_drafts.onion`.

`old_papers_drafts.onion` — 43 files, 7 planned papers + `paper_bridges/`
(the largest, most developed subtree by far — ~1.9MB of the archive's
~1.9MB total is dominated by `paper_bridges/data/`).

```
old_papers_drafts.onion/
  PAPERS.md                          — top-level paper-tracking index (READ, see below)
  README.md                          — (not yet read)
  paper_bridges/
    README.md                        — (not yet read)
    bridge_visualiser.html           — 155KB, interactive visualiser (not yet opened)
    concept_graph_explorer.html      — 216KB, interactive explorer (not yet opened)
    notes.md                         — 1483 lines, design notes (IN PROGRESS, see below)
    data/
      concept_graph.db               — 500KB SQLite DB, the real, built graph (not yet opened)
      concept_inference.py           — 17.9KB, the real inference engine (not yet read)
      cross_domain.py                — 8.2KB (not yet read)
      cross_domain_matches.json      — 415KB, real computed match data (not yet read)
      hub_gaps.json                  — 34.8KB, the "displacement gaps" data (not yet read)
      build_bridge_visualiser.py, build_explorer.py,
      build_static_explorer.py, build_tables.py,
      build_template_system.py       — build/tooling scripts (not yet read)
      add_delta_schema.py, add_functional_families.py,
      add_new_domains.py, fix_concept_errors.py  — data-maintenance scripts (not yet read)
      equation_sources.md            — 2.2KB (not yet read)
  paper_flowtrix/README.md           — 696 bytes (not yet read)
  paper_hawking/README.md            — 650 bytes (not yet read)
  paper_main/README.md               — 672 bytes (not yet read)
  paper_robotics/README.md           — 739 bytes (not yet read)
  paper_substrate/README.md, notes.md (6.4KB) — (not yet read)
  paper_timing/README.md             — 691 bytes (not yet read)
```

Extracted to `/tmp/papers_extract/` this session (ephemeral — re-extract
via `onion -d archeology/onion/old_papers_drafts.onion -o <dest>` in a
future session; this path won't persist).

---

## PAPERS.md — the publication roadmap (fully read)

Seven planned papers, real status tracked as of 2026-06-15:

| # | Working title | Status | Depends on hardware? |
|---|---|---|---|
| 1 | Main paper — NOR-universal fabric, two-arrival firing, wired-OR | 🟡 draft exists, needs restructuring | Partially (§4 silicon results, perf numbers) |
| 2 | Deterministic Timing in Reconfigurable Fabric | 🔴 not started, writable now | No — iCEBreaker results already sufficient |
| 3 | Semantic Bridge Inference (the concept-graph paper) | 🔴 not started | No — pure software/theory |
| 4 | The Hawking Bridge as a standalone result | 🔴 not started, "could be drafted in one session" | No |
| 5 | Robotics: sensor-to-actuator pipeline (SensorTrix→OptiTrix) | 🔴 not started | Strengthened by real sensors, not blocked |
| 6 | FlowTrix: LBM physics simulation, MLUPS/watt | 🟡 VM results + Strouhal validated | Yes — hardware run for the real headline number |
| 7 | The Universal Symbolic Substrate (vision/survey paper) | 🔴 not started, skeleton-able now | No |

**Real, concrete facts worth remembering on their own, independent of
which paper they end up in:**
- iCEBreaker: **31/31 silicon tests** matched predicted pipeline depth
  exactly — the real, existing evidence for the "compile-time timing
  is a hard guarantee, not a claim" thesis.
- LBM collide: 1,714 predicted ticks/update (VM-confirmed).
- LIF (NeuroTrix): 353 predicted ticks/update (VM-confirmed), matches
  `LIFNeuron.step()` exactly over 300-tick runs.
- NetTrix: two-arrival model IS a state machine — TCP FSM as topology,
  **70ns/packet at 200MHz** (d14).
- SensorTrix: universal `(location, amount)` encoding — any sensor type
  is N readings on N consecutive bus addresses; scales with sensor
  count with zero architectural change.
- OptiTrix: PID as a 6-tile pipeline, ~2512 cells, state in preloaded
  registers, anti-windup at **zero fabric cost** (host-side).
- Paper 3's own real, stated contribution: bridge inference as a
  **discovery tool** — surfacing candidate cross-domain connections via
  dimensional matching, not word-matching or embedding similarity.

**Shared-infrastructure table (which claims appear in which papers)**
is itself a useful index — see PAPERS.md directly if cross-referencing
a specific claim later.

---

## paper_bridges/notes.md — design notes (fully read, 1483/1483 lines)

Dated entries, "morning thinking session" style, explicitly marked
pre-implementation / ideas still developing. Real, substantial
intellectual content, not casual notes.

### Read so far, in order:

**The core insight (line ~10):** confidence score = a real conversion
rate, not an opinion. Makes cross-domain connection engineering
(falsifiable, challengeable) rather than philosophy.

**Three-layer model (line ~20):** Domain → Scope → Dimension, in that
order of importance. Dimension (SI vector) is a sanity check, NOT the
primary signal — dimensional match is necessary but not sufficient
(reaction_enthalpy and kinetic_energy share dimensions, aren't the
same thing).

**Degrees of separation (line ~40):** the concept graph = directed
weighted graph, nodes=ConceptDeclarations, edges=ConversionMechanisms,
edge weight=confidence. Path confidence = PRODUCT of edge weights (not
sum, not hop count) — real physical grounding: water→steam is a hard
2260 J/g requirement (confidence 1.0, non-negotiable); Carnot heat→work
has a real 0.85 ceiling. **Finds shortest path by confidence LOSS, not
hop count** — a 2-hop 0.95×0.95=0.90 path beats a 1-hop 0.70 path.

**Biological example (line ~65):** oak→wolf and wolf→oak traced as
real multi-step conversion chains with real (if illustrative) lossy
confidence products. Introduces the **hub node** concept — ATP as a
shared intermediate that collapses a 5-step path to 2. Hubs are
DISCOVERED by the path solver via connectivity counting, never
manually declared.

**Cycles and thermodynamics (line ~93):** wolf→tree→carbon→...→wolf
cycle. **The second law falls out of the graph structure by
construction** — any closed cycle's confidence product is <1.0 because
each real mechanism is genuinely lossy. Not asserted, emergent.

**Two territories (line ~104):** *Computable* (real numerical transfer
function, becomes a real bridge tile — water/steam, Arrhenius, Hawking,
LBM viscosity) vs *Declarative-only* (real and directional, not yet
reducible to formula — population density→political tension, ~0.60
confidence, stays as graph knowledge, never runs on silicon). A
mechanism moving from declarative to computable = "a genuine research
advance"; the graph marks the frontier.

**UniCell's honest limits (line ~135):** the mechanism requirement
(must declare a numerical transfer function) is explicitly named as
"the safeguard" against forcing poorly-defined concepts onto the
fabric — described as intellectual honesty built into the
architecture, not a limitation to route around.

**Precomputation (line ~148):** the graph must be precomputed (O(n²)
build, sparse graph) for O(1) query-time lookup — a real path cache
with `{from, to, path, mechanisms, confidence, hops, computable}` per
concept pair, shipped as a prebuilt artifact.

**Community as graph builders (line ~179):** extends the EXISTING
community-contribution layer (already built for Trix formats/models,
per TRIX_ECOSYSTEM.md) to graph-edge contributions. Each contribution
= a falsifiable scientific claim, challengeable by other domain
experts.

**Graph topology (line ~198):** real, predicted structure — hub nodes
(carbon, energy, temperature, water, ATP) emerge from path analysis;
dense clusters (thermodynamics, chemistry) vs sparse frontier
(sociology, political science) show where the science is mature.
**Cross-cluster bridges are the high-value discoveries** — "the
Hawking bridges of the graph."

**Implementation plan sketch (line ~222):** `concept_graph.py`
(separate from `cell_format.py` deliberately, keeps core clean) —
Dijkstra-by-confidence-loss path solver, cache builder, incremental
updater, O(1) query interface, a `computable` flag. Region Connector
UI extension: "Suggested connections" panel, amber/green/grey color
coding (conversion needed / identity / declarative-only).

**Open questions (line ~242):** confidence assignment for a brand-new,
no-data mechanism; whether cycles should be traversable in the solver;
directionality/reversibility of mechanisms; WHO decides the
declarative→computable threshold (explicitly named as "a governance
question as much as a technical one"); whether esoteric domains
(consciousness, aesthetics, meaning) can be kept honest by the
mechanism requirement or whether the graph should just accept they
stay permanently declarative.

**Late addition, fundamental equations as max-density hubs (line
~275):** E=mc² as a real graph JUNCTION (not just a node) — every path
through energy/mass/light conversion passes through it, confidence 1.0
in all directions since it's derived, not empirical. Explicit
Mendeleev analogy: hubs emerge from path-counting the same way
periodicity emerged from atomic structure, not from anyone declaring
them special.

**Multidimensional data tables (line ~308):** a genuinely concrete,
buildable idea — a multidimensional table is a tensor; UniCell
searches it natively via the SAME `SENSOR_STACK` pattern (N dimensions
on N consecutive addresses), with pipeline depth a compile-time
constant REGARDLESS of table size (a billion-row 4D table searches in
the same real tick count as a thousand-row one).

**[Headers seen but not yet read in depth — line numbers for next
pass]:** Scale note (324), hub assumption problem (339), user equation
placement (370), hub structure reflects architecture of physical law
(394), Genomics isolation (410), Bridge visualiser position in the
stack (484), SQL streaming to UniCell card-gated (504), Multi-path
search future (527), The displacement hub / chord diagram (542),
displacement dominance (560), the compiler as enforcer (603), the
Mendeleev framing (619), Mass at 25 (639).

**Δ as the universal primitive (line 698, READ IN FULL):** the core,
sweeping claim — 49 "displacement" gaps in the graph are really ONE
undeclared primitive: Δ (directed difference between two states). "The
universe is a Δ-erasing machine" — every spontaneous process runs down
a gradient to Δ=0 (thermal, pressure, concentration, voltage,
position). Extends the SAME structure to finance (arbitrage,
double-entry bookkeeping as enforced Δ=0), politics (mobilization as
current flow, D'Hondt apportionment as Δ-minimization), biology
(fitness differential, membrane potential), psychology (cognitive
dissonance, motivation as Δ-driven), economics (price discovery,
interest as the price of temporal Δ), social change (reform as making
a Δ visible). Proposes a `nature: delta` schema field with a
`base_concept` pointer and explicit `breaks_when` conditions. Real,
honest self-limit already present: the mechanism requirement means
domains without a definable Δ and mechanism (consciousness, aesthetics)
simply don't enter the graph — framed as a real result, not a gap.

**Two primitives (line 905, READ IN FULL):** the further reduction —
everything is Δ (difference) or 0 (reference point). Four schema
"nature" categories (delta/absolute/rate/ratio) all expressed in terms
of Δ and 0. **Real, useful taxonomy of ZERO ITSELF**, worth remembering
on its own: absolute zeros (0K, 0J — physically non-arbitrary),
conventional zeros (0V, 0m, 0°C — arbitrary but shared by convention),
enforced zeros (accounting identities, total probability=1), and
qualitative boundary zeros (0 stress = tension/compression boundary, 0
net income = profit/loss legal boundary) — each crossing a DIFFERENT
kind of zero means something structurally different, and bridging two
concepts requires their zeros to be COMMENSURABLE (Celsius↔Kelvin:
trivial, confidence 1.0; financial debt↔compressive stress: both
"negative from zero" but incommensurable zeros, bridge invalid without
explicit translation). Real, specific empirical scope stated: "192
equations across 27 domains," "544 undeclared bridges." Real,
important self-limiting move repeated: consciousness/meaning/aesthetics
excluded because you can't write an equation with a declared Δ and 0
for them — "the boundary of what is formally knowable is the boundary
of what can be expressed as a difference from a reference state."

### Honest engagement, worth remembering alongside the excitement (not just filed as "impressive")

The computable/declarative distinction is doing real, load-bearing
epistemic work, and it's the right instinct — but the schema stores a
DERIVED confidence (Hawking, Celsius↔Kelvin: a real number with a real
proof) and an ELICITED confidence (political tension chains: an
informed judgment call) in the same field, multiplied the same way,
producing a single number with the same apparent authority either way.
The notes ALREADY flag this under "open questions" (governance of the
declarative→computable threshold) — worth checking, when reading the
actual schema/code, whether there's a real, visible flag distinguishing
"this confidence was derived" from "this confidence was assigned,"
not just the binary computable/declarative split.

**The distinguishing claim (line 1081, READ IN FULL):** the paper's own
stated inversion — prior knowledge-graph work asks "where are the
holes," this asks "what are the holes MADE OF." Answer: Δ. Explicitly
frames the COMPILER itself (refusing to run without declared
assumptions) as "the instrument of revelation" — the epistemological
contribution is distinct from the engineering one.

**Flux taxonomy (line 1153, READ IN FULL, explicitly credited to an
external Gemini conversation):** Passive Flux (systems seeking
equilibrium, Δ naturally→0: heat, pressure, diffusion — well-declared,
mature, short paths), Active/Managed Flux (systems that SPEND ENERGY
to MAINTAIN non-zero Δ: biology, power grids, economies, political
institutions — "life is what happens when passive flux is locally
reversed by active input"), Informational Flux (abstract substrate:
Shannon entropy, Bayesian update, price discovery — "currently sparse,
mostly undeclared... the deepest knowledge holes"). The isomorphism
section claims Fourier heat conduction, Ohm's law, Fick's diffusion,
Darcy's law, and Black-Scholes drift are literally the SAME equation
(Flux = Conductivity × Gradient) with domain names as substrate
labels only -- worth noting this connects to a REAL, established
physics idea (generalized flux-force / linear response relations,
Onsager reciprocity) rather than being a wholly novel observation; the
genuine synthesis here is tying it explicitly to the compiler's own
bridge-declaration requirement. The boundary-question analysis is
genuinely useful and specific: Physics↔Chemistry is "tool-driven"
(thick, historical, not structural); Physics↔Economics is
"Δ-type-driven" (real structural similarity, almost no declared
crossings -- thin not because weak, because never declared);
Physics↔Politics is "almost entirely undeclared" (zero declared
bridges, "maximum knowledge hole"). Ends by naming the ultimate
architectural destination: a general equation matrix (Flux =
Conductivity × Gradient, parameterized by Δ and 0) implementable
directly as a real, generic NOR-gate fabric topology, with domain
selected purely by WHICH DATA is loaded, not by rewiring -- "the
domain is metadata."

**The bridge model as hypothesis engine (line 1327, READ IN FULL) --
the most methodologically rigorous section, genuinely testable, not
just philosophical:** three real, formal categories -- **Green**
(declared, high confidence, known knowns), **Amber** (a functional
family appears in domain A, domain B has the structural prerequisites
but no declared instance yet -- "the bridge model predicts the
equation must exist there... each amber gap is a hypothesis"), **Dark**
(predicted but genuinely CANNOT exist -- a real structural
prerequisite is absent, "the absence is a result, not a gap").
Explicitly modeled on Mendeleev's own real justified absences
(element 43/Technetium missing because it has no stable isotopes, not
by oversight). Three real, worked "dark gap" examples: electoral
systems lack passive-flux equations because they're DESIGNED to resist
equilibrium (a real structural fact about the nature of political
competition, not a data gap); accounting lacks exponential-growth
equations in the growth-law sense because accounting enforces Δ=0 at
every transaction -- "a measurement system, not a dynamic system";
genomics lacks field-integral equations because DNA is discrete, field
equations require a continuous substrate. **The three-domain test for
fundamentality** (real, checkable criteria: appears independently in
5+ domains; absence elsewhere is either amber-predictable or
dark-justified; reduces to Δ/0 in canonical form) is applied to name
real, specific candidate "fundamental equation models" with real
attached numbers: `linear_flux` (3 declared, 24 predicted missing),
`linear_product` (10 domains), `exponential_decay/growth` (4/2
domains), and `logistic` (only 1 domain declared -- population
dynamics -- but flagged as "most interesting candidate" given the
structure's real ubiquity: market saturation, epidemic curves,
capacitor charging, neural activation, adoption curves, species
invasion, all undeclared). Closing, real, falsifiable summary claim:
"21 structural families across 192 equations... 147 domain-family
pairs where a functional family is predicted present but undeclared."

**`notes.md` is now fully read, 1483/1483 lines.** The specific numbers
throughout (192 equations, 27 domains, 544 undeclared bridges, 147
predicted-but-undeclared pairs, 49 displacement gaps) all point to REAL
underlying data -- almost certainly what actually lives in `concept_
graph.db`/`cross_domain_matches.json`/`hub_gaps.json`, none of which
have been opened yet. The real, decisive next check: how much of this
theoretical framework actually got implemented and populated with real
data, versus how much stayed at the design-notes stage.

---

## Real implementation confirmed — this was genuinely built, not just designed

**`concept_inference.py` (460 lines, read in full) is a real, working,
mathematically sound implementation**, not a sketch. A genuine modified
Dijkstra: edge weight = `-log(confidence)`, correctly turning "maximize
confidence product" into "minimize weight sum" — the standard, correct
transformation for this class of problem. Produces real GREEN (direct,
confidence≥0.80) / AMBER (multi-hop, confidence product shown) / RED
(no path — returns the real dimensional shape a missing bridge would
need) results. The docstring's own example query — `find("displacement",
"wave_function")  # quantum gap` — is a genuinely well-chosen real
example (the classical-to-quantum gap is real and famously unresolved).

**`concept_graph.db` (SQLite, real, checked directly) confirms every
specific number in `notes.md` was backed by real, populated data, not
aspirational writing:**

| Table | Rows |
|---|---|
| domains | 35 |
| units | 35 |
| concepts | 265 |
| equations | **192** (exact match to notes.md's own "192 equations across 27 domains" claim) |
| equation_components | 1366 |
| constants | 14 |
| equation_templates | 18 |
| template_slots | 65 |
| equation_instances | 51 |
| **template_bridges** | **1095** |

**`template_bridges`'s own real schema and data** is the actual, live
output of the "hypothesis engine" described in notes.md's final
section: `(template_id, domain_a, domain_b, equation_a, equation_b,
status, confidence, shared_structure, constant_a, constant_b,
zero_compatible, notes, auto_generated)`. Real, checked example rows
for template T01 ("flux = conductivity × Δ", i.e. `linear_flux`):
chemistry↔circuits (ε vs 1/R, confidence 0.9), chemistry↔structural_
geology (ε vs the real Mohr-Coulomb shear formula `tan(φ)+c/σₙ`,
confidence 0.9), circuits↔structural_geology (1/R vs E). **Status
breakdown: 1050 "predicted", 45 "valid"** — a real, live instance of
the Amber/Green split from notes.md, though the specific "147
domain-family pairs" number from the design notes doesn't exactly
match 1050 here (likely a different, more refined subset, or the
database grew after that count was written — worth resolving on a
future pass, not assumed either way).

**`hub_gaps.json` (100 entries, checked directly) confirms the "49
displacement gaps" claim exactly** — 49 of 100 total entries are
displacement-specific, matching notes.md precisely. Real, striking
concentration: only 8 unique concepts have ANY gap at all across the
whole 265-concept graph, and just three — displacement (49), mass
(25), force (12) — account for 86% of all gaps found. Confirmed the
"Mass at 25" section (read on this pass, previously only seen as a
header): a genuinely different *flavor* of gap from displacement's.
Mass's gaps are administrative, not philosophical — the physics is
already completely settled (the weak equivalence principle, inertial
mass = gravitational mass, verified empirically to 1 part in 10¹⁴; γm₀
↔ rest mass via the Lorentz factor; nuclear mass defect via E=mc²) but
simply hasn't been written as a formal `BridgeContract` yet. Flagged
in the notes themselves as "good early targets for community
contributions" — a real, low-effort, high-confidence backlog, unlike
displacement's gaps, which require the deeper Δ-primitive declaration
to close at all.

---

## `paper_substrate/notes.md` — the vision paper's core thesis (read in full, 6.4KB)

Genuinely the most polished writing found in this archive so far —
reads like a near-final draft, not working notes. Central framing,
worth remembering as its own real contribution:

**"We built a system that makes ignorance visible."** Not a typed
compute fabric (though it is one). Not a knowledge graph (though it
contains one). A system that maps the SHAPE of what isn't known,
precisely enough to direct someone toward filling it.

**The Mendeleev reframe, sharper than anywhere else in the archive:**
Mendeleev didn't discover gallium — he declared a hole where it had
to be, described its properties from surrounding structure (atomic
weight, valence, density) 15 years before anyone detected it. "A
shaped absence is more useful than a vague one."

**Four real, carefully DIFFERENTIATED examples of "shaped absence,"
each genuinely a different TYPE of not-knowing, not the same gap
repeated:**
- **Dark matter** — a clean hole: high gravitational confidence on one
  side, nothing on the other. The shape itself is already a real
  constraint (couples to mass, not to electromagnetic force).
- **The information paradox** — not a missing node at all, a **broken
  cycle**: information enters a black hole (confidence 1.0), Hawking
  radiation exits (confidence 1.0), but the cycle's own confidence
  doesn't conserve. A structurally different kind of problem from a
  hole.
- **Consciousness** — no clean edges at all: a real, honest GRADIENT
  of decreasing confidence moving from neuroscience toward phenomenal
  experience. "A frontier that gets hazier, not a wall that stops
  cleanly."
- **The Planck scale** — not absence, **contradiction**: two real,
  independently high-confidence mechanism chains (QFT, general
  relativity) converge on the same concepts with incompatible values.

**The Hawking bridge's own real role in this specific paper, stated
precisely:** confidence=1.0 because derived from first principles, but
it touches the information paradox's own broken cycle directly. "The
bridge is solid. What it connects to is not. The graph shows both
clearly and does not conflate them." "Hawking was standing at one of
those edges... the bridge carries his name not as tribute but as
description."

**Real, honest limits stated directly, matching the whole project's
own established discipline:** "The graph cannot resolve the gaps it
reveals. It can only make them precise." Explicitly NOT claiming to
solve dark matter or quantum gravity — only to make the shape of not
knowing precise enough that a real answer, once found, would
immediately show where it fits.

**Target venue named explicitly and ambitiously: Nature or Science** —
"Not a computer architecture paper. Not even primarily a systems
paper... The computer science is the method. The claim is about
knowledge itself." A genuinely different register and ambition than
the other six, more technical/specialized papers.

---

## `region_connector.html` — the "cross-domain planner" (Alan's own real recollection, found in a different archive)

**Real, important correction to my own earlier cataloguing:** this
lives in `old_composer_tool.onion` (already Tier 1, already used
once for cell-count checks in `#659`), NOT `old_papers_drafts.onion`
where the other bridge UIs live — a real, separate archive from the
rest of this dive, found only because Alan specifically recalled it
existed. 1313 lines, sits alongside `unicell_composer.html` in the
same archive.

**A genuinely complete, well-engineered visual tool, read through its
real function list end to end:**
- `renderBrowser`/drag-and-drop (`onDragStart`/`onDrop`) — drag a
  domain model (MathTrix/BioTrix/ChemTrix/PhysTrix/FinTrix, each with
  its own real UI colour) onto a canvas.
- `addRegion`/`makeDraggable` — **Regions** as real, draggable canvas
  nodes — the same real "Pond" concept found in `#671`/`#672`, now seen
  as an actual, working UI object, not just a design description.
- `startConnect`/`endConnect`/`tryConnect` — port-based wire-dragging
  between two regions.
- **`tryConnect`'s own real matching logic**: same format+context =
  direct connection, no bridge needed. Different format = search the
  real `BRIDGES` array for a matching `(source_format, target_format)`
  pair. A real, additional `context` field (beyond format) is checked
  too — a bridge can match on FORMAT while still flagging a
  "ctx-mismatch" badge if the specific USAGE context differs, a level
  of nuance beyond what `notes.md`'s own three-layer model
  (domain/scope/dimension) explicitly named.
- `showBridgePanel` — real, live UI: every matching bridge shown with
  its own real formula, a confidence bar+percentage, colour-coded by
  `confColor()`, and a context-match badge. Selecting one and
  confirming records a real, timestamped connection.
- **`showNoBridgeMessage`, when no bridge exists at all**, tells the
  user exactly what to do next: *"To create a custom bridge, define a
  BridgeContract in cell_format.py and declare semantic_confidence."*
  Real, direct confirmation that `cell_format.py` (`#659`'s own
  original find) is genuinely the live source of truth this whole tool
  is a front-end for, not a separate or parallel system.
- `validatePipeline`/`dfs`/`showValidationReport` — a real depth-first
  traversal validating an assembled multi-region pipeline before
  export.
- `exportPipeline`, using a real `sha256`/`canonR` — the SAME
  canonical-hash convention this project's own ICM format uses.
- **`openCustomBridge`/`saveCustomBridge`/`_bridgeStub`/
  `promoteCustomBridge` — the part that closes the entire loop.** A
  real form (source format, target format, name, formula, confidence,
  notes) lets a user declare a brand-new bridge the built-in catalogue
  doesn't cover. `_bridgeStub()` then generates a REAL, syntactically
  valid `BridgeContract` Python subclass automatically applying the
  exact same confidence-tier policy documented in `TRIX_ECOSYSTEM.md`
  (`>=0.95` auto_place, `>=0.80` warn_and_place, `>=0.60` require_
  verification, else reject) -- with clear, honest `# TODO` placeholders
  for the things a UI genuinely cannot infer on its own (constants
  used, SI input/output units, the dimension-exponent vector).
  `promoteCustomBridge()` downloads this as a real `.py` file with
  exact, correct paste-in instructions (`from cell_format import
  BridgeContract`, register in `FUNDAMENTAL_BRIDGES`). A real,
  thoughtful design choice, explicitly commented in the source: *"It
  does NOT bypass the confidence/context discipline — it just lets a
  user declare a connection the built-in catalogue doesn't cover yet."*
  You don't need to know Python or the internal class structure to
  PROPOSE a new bridge -- only an honest formula and an honest
  confidence estimate.

This is, genuinely, one of the most complete, usable single artifacts
found in this whole dive -- a real, closed loop from "I want to
connect two domains and nothing exists yet" to "here is a real,
correctly-structured code contribution, ready to review."

---

## `unicell_composer.html` — the other real, standalone frontend (Alan's own "I liked the front end")

Same archive as `region_connector.html` (`old_composer_tool.onion`).
1631 lines. "Imago UniCell Composer v2" — a real, complete visual cell
editor with undo/redo, multi-select, a logic-tree panel, and a live
in-browser simulator, not just a static diagram tool.

**`MODELS` (real, comprehensive standard-cell library, ~70 entries,
read in full) — genuinely useful reference data on its own, independent
of the rest of this dive:** real, measured cell counts and pipeline
depths across Integer arithmetic/logic/shift (INT32_ADDER: 482c depth
10, matching the figure already known from `#612`; INT32_ADDER_CLA:
3969c depth 52 fully combinational; shifts as pure wiring, zero real
logic cost per bit), Comparison (INT32_EQUAL 95c, INT32_LT_S 523c),
Float (FP32_ADDER 1253c depth 85, FP32_MULTIPLIER 3066c depth 89, both
`vmOnly`), large multipliers explicitly flagged `placeholder`+`vmOnly`
(a 32×32 Dadda tree at 23,924c "needs dedicated multiply pond"; a
32×32 Booth radix-4 at 109,458c "pending NOR-efficient rewrite" — HONEST
labeling of what's real today vs. aspirational), Counters, I/O
handlers (keyboard/mouse/sensor/network/storage/audio, real costs
each), and a **complete MIF (MathTrix Internal Float) family** with
real costs for every operation: `MIF_UNPACK`/`MIF_PACK` (the real
IEEE-754↔MIF boundary tiles, 74c/126c), `MIF_ADD` (814c depth 79),
`MIF_MUL` (3066c depth 89), `MIF_DIV` (4789c, depth 1177 -- real,
explicit tradeoff noted between a cell-budget-optimized and a
low-latency-with-LUT variant), `MIF_SQRT`, `MIF_MADD` (fused multiply-
add, explicitly described as fusing MUL+ADD into one tile), and a full
set of MIF comparisons.

**A real, direct confirmation, independent of anything else found in
this dive:** `OS Ponds` appears as ITS OWN real model category —
`COMPILER_POND`, `INT32_COMPILER_POND`, `LLVM_COMPILER_POND`,
`SEQUENCER_POND`, each with `cells:0, depth:0`. Ponds were not only a
hardware execution-region concept -- **software/runtime processes
(a compiler, a sequencer) were placeable, first-class objects on the
exact same visual canvas as hardware tiles**, a genuine unification of
"the thing that computes" and "the thing that runs the computation" in
one shared visual language.

**The real Pond colour/inference system (`inferPonds`/`buildPond`/
`pondColorForBlock`, read in full) — a genuinely elegant, working
implementation of the Pond concept, matching Alan's own real
description precisely:** Ponds are **inferred, not manually declared**
-- computed automatically from bits 23:16 of each cell's own real
address (`addrPrefix()`), the same real "discover structure from the
data, don't hand-declare it" instinct already seen in the concept
graph's own hub-node discovery. Each unique address prefix gets a
stable colour from an 8-entry palette, used consistently across the
canvas tint, a live "pond key" side panel (showing cell count and
ports per Pond), AND the simulator. **Genuinely interactive**: each
input port in the pond key has a real `→1` inject button that fires a
real value directly into the live simulated bus at that exact address
and ticks the simulation immediately -- a live, per-port test
harness built directly into the visual Pond browser.

**Real design intent behind touch support, stated directly by Alan,
confirmed precisely against the actual code:** the composer was built
as a standalone unit specifically so design work could happen on the
go, with a compiled design then run on either the VM or real FPGA
hardware if available. Checked directly, not assumed: real, careful
touch handling exists (`touchstart`/`touchmove`/`touchend`, `touch-
action:none` to properly suppress the browser's own default scroll/
zoom). Single-finger drag distinguishes a tap (select) from a pan via
a real movement threshold; two-finger pinch-to-zoom correctly anchors
the zoom around the actual midpoint between the two touch points, not
just the canvas centre -- genuinely careful mobile UX, not a token
"works on a phone" checkbox. Directly connects to `math_frontend_
design.md`'s own real "Android tablet deployment" section (Termux +
Flask + WiFi, ICM as the portable layer scaling from tablet to desktop
to silicon) -- the composer's touch support is the concrete, working
half of that same real deployment story, and the "run on VM or FPGA"
choice is exactly the same portability principle applied to where the
design actually executes, not just where it's drawn. Ties directly
into the real community-contribution layer already documented in
`TRIX_ECOSYSTEM.md` -- lowering the barrier to designing AT ALL (no
desktop, no dedicated hardware required, just a phone or tablet) is
itself a real, deliberate expansion of who can realistically
contribute a new model or bridge.

---

## `workbench.py`'s own embedded frontend (`WORKBENCH_HTML`) — the third real, related UI, same design language

Already scoped once for backend features in `#670` (`ws set`/`get`,
`start_run`/`pause_run`, the `warning`-field idea). This pass looks at
its own real, embedded HTML/JS frontend specifically, not covered
before.

**Real, semantically-rich cell-state colour coding, confirmed directly
in the CSS**: distinct colours for blank/waiting/fired/memory/halted/
config states -- a genuine visual vocabulary for what a cell is
actually doing, not a generic on/off grid.

**Explicitly, directly confirmed shared design system, straight from
its own header comment: `"Pond colour system (mirrors composer)"`.**
`addrPondKey()`/`pondColorForAddr()` are real, near-identical mirrors
of the composer's own `addrPrefix()`/`pondColorForBlock()` -- the same
address-prefix-based Pond inference, reused deliberately across both
tools, not reinvented.

**`renderGrid()` (read in full) is a genuinely well-engineered, real
live visualization** -- every cell in the array gets its own real,
clickable DOM element, coloured by its actual current state via a
`data-state` attribute, with a real semantic tooltip decoding the raw
gate-state bits into something readable ("AND · 1SHOT · 0x0010001A ·
[waiting]"), a subtle Pond-coloured border tint when not selected, and
zoom-dependent text (showing the cell's own address once zoomed in
enough to read it). Built to actually work at scale, not just look
good in a screenshot.

**`renderRegions()` directly confirms the "multiple independent,
loadable processes" model Alan described from memory, now seen as
real, working UI**: each region shown with its own real image name,
region ID, cell count, execution state, live cycle count, and a real
`Free` button to release it -- regions/Ponds genuinely were
independently loadable, runnable, and freeable units, visible and
manageable one at a time in the same interface.

---

## `cross_domain.py` (read in full, 8.2KB) and the remaining paper READMEs

**The remaining 6 paper READMEs (`paper_hawking`, `paper_flowtrix`,
`paper_robotics`, `paper_main`, `paper_timing`, `paper_substrate` —
all read):** confirmed these are genuinely scaffolded stubs, not
substantive content -- folder structure + a short data/figures
inventory each, matching what `PAPERS.md` already documented in more
detail. Only `paper_bridges` ever received real, substantial written
content. No new facts beyond what was already logged.

**`cross_domain.py` is a real, complete, working algorithm — and it's
DIFFERENT from `concept_inference.py`'s own path-solving Dijkstra.**
This one does a real, brute-force pairwise comparison
(`itertools.combinations`) across every concept pair in the database,
matching on exact dimensional equality and scoring confidence via a
real, hand-curated `DOMAIN_PROXIMITY` table (physics↔mechanics=0.0,
thermodynamics↔chemistry=0.1, physics↔chemistry=0.15, chemistry↔
biology=0.2, physics↔economics=0.6 -- genuine domain-expert judgment
calls, not derived) plus a hub-connectivity bonus and a known-bridge
bonus. `KNOWN_BRIDGES` is a real, hardcoded list of 15 specific, named,
scientifically accurate mechanisms (Arrhenius, Hawking radiation,
Carnot, Boltzmann factor, DNA Watson-Crick melting temperature, Eyring,
Gibbs-Helmholtz, equipartition, Planck, van't Hoff, pH) -- this is what
actually generates `cross_domain_matches.json`.

**A real, honest gap found by tracing the actual code, not assumed
from the docstring:** the module's own docstring promises three match
types -- GREEN (same domain, same dimension), AMBER (cross-domain,
same dimension), and RED ("different domain, compatible but not
identical dimension — speculative"). The real match loop initializes
`matches = {"green": [], "amber": [], "red": []}` but only ever
appends to `green` and `amber` -- `red` is declared and never
populated anywhere in the file. The speculative, "compatible-but-not-
identical" tier was designed but never actually built here, at least
not in this specific script (possibly implemented elsewhere and not
yet found, or genuinely just never finished).

---

## The two real, interactive HTML explorers — Alan's own real anticipation of "a surprise or two" confirmed

Both genuinely more complete and sophisticated than expected going in.
Both hand-rolled in vanilla canvas/JS -- no D3.js, no Three.js, no
charting library at all.

**`bridge_visualiser.html` (155KB) -- a real, multi-view analysis
dashboard, four distinct real views (`drawMatrix`/`drawChord`/
`drawBridge`/`drawHubs`), not one visualization:**
- **`drawChord()` (read in full)** is the real, working chord diagram
  referenced but never actually read in `notes.md`'s own "displacement
  hub" section -- genuine hand-drawn bezier curves connecting domain
  arcs around a circle, line thickness scaled by real shared-variable
  count, with live hover tooltips naming the actual shared variables
  (up to 4) for whichever domain pair the cursor is over.
- **`placeEquation()` (read in full) is the single most impressive
  feature found in this whole dive.** A real, working realization of
  `paper_substrate/notes.md`'s own "shaped absence" thesis as an
  actual usable tool, not just a description of one: type in the
  variable names of your OWN new equation, and it (1) matches them
  against the real known concepts, (2) identifies which real domains
  they touch, (3) checks every real pair of those domains for an
  existing bridge and explicitly flags any pair with no bridge as
  `"⚠ UNDECLARED GAP"`, and (4) cross-references the real `hub_gaps`
  data to report exactly how many named, counted hub gaps your
  equation would close. This is the PhD-student use case from
  `paper_substrate/notes.md` turned into working code, not just
  described in prose.

**`concept_graph_explorer.html` (216KB) -- a real, different kind of
tool: a genuinely polished, fully hand-rolled 3D force-graph browser,**
not a 2D dashboard. Real perspective projection (rotate Y then X, a
simple FOV/depth scale factor), correct back-to-front depth sorting,
glowing node shadows, continuous `requestAnimationFrame` animation for
auto-spin, click-to-select, a dimension filter, and a real path-finder
between any two named concepts.

**A real, honest, meaningful inconsistency found by tracing the actual
code, worth recording precisely rather than glossed over:** this
explorer's own `findPath()` is a plain, UNWEIGHTED breadth-first
search (fewest hops) -- NOT the confidence-weighted, `-log(confidence)`
Dijkstra from `concept_inference.py`. This directly contradicts
`notes.md`'s own, repeatedly-stated design principle ("finds shortest
path by confidence LOSS, not hop count -- a 2-hop 0.95×0.95=0.90 path
beats a 1-hop 0.70 path"). In its current, real form, this specific
visual tool would show the WRONG "best" path in exactly the kind of
case its own design notes use as the headline example. Likely built
earlier or separately from the confidence-weighted engine as a
simpler visual proof-of-concept, not yet reconciled with it -- a real,
specific, fixable gap if this tool is ever revived.

---

## Not yet opened at all (this session)

- `paper_bridges/data/cross_domain_matches.json` (415KB) — the real output of `cross_domain.py`, now fully understood structurally; only worth opening for specific example rows, not discovery
- All 6 remaining paper READMEs now read (`paper_hawking`, `paper_flowtrix`, `paper_robotics`, `paper_main`, `paper_timing`, `paper_substrate`) -- confirmed scaffolded stubs, no `draft.md`/`notes.md`/real data present for any of them except `paper_substrate/notes.md` (already read in full above) and `paper_bridges/notes.md`

**Every real, substantive file in this whole archaeology pass (`old_papers_drafts.onion` + the composer/workbench/region-connector trio in `old_composer_tool.onion`/`old_full_cell_ui_and_gpu.onion`) has now been read.** Only `cross_domain_matches.json`'s own specific rows remain genuinely unexamined, and its generating algorithm is fully understood, so this is closer to a finished pass than an open one.

## The actual genesis of the whole method, stated directly by Alan (not reconstructed from the archive alone)

Worth recording precisely, since it's the real origin of the method,
sharper than how the design notes describe it in the abstract: the
idea started from noticing that an equation, stripped of its
domain-specific labels, is just a structural shape -- a functional
form. The actual work was searching real, basic algorithms/equations,
stripping each down to that bare shape, and checking whether the SAME
shape recurs in a different domain under different names. **A "gap"
specifically means the shape WAS found to repeat -- the structural
match is real and confirmed -- but no one has actually written the
matching, working equation for that other domain yet.** Not "these
might be related" (a weaker, softer claim) -- "this exact pattern
already exists here, and by the same structural logic it should exist
there too, and currently it doesn't."

This is precisely, mechanically what `concept_graph.db`'s own real
`equation_templates`/`template_slots`/`template_bridges` tables
implement, not just a prose description of something looser: a
"template" (e.g. T01, `flux = conductivity × Δ`) IS the stripped,
domain-free shape; every real `template_bridges` row is one specific,
concrete instance of "this shape shows up here too, but hasn't been
declared." It's also the precise, correct reason the real status split
was 1050 "predicted" against only 45 "valid" -- the search for
repeating shapes runs mechanically far ahead of anyone actually
writing the domain-specific equation down by hand.

**And Δ/0 themselves came from the exact same process, by Alan's own
direct account -- not a separate philosophical construction.** He
noticed the pattern (every stripped equation, across every domain
checked, resolved to some difference measured from a reference state)
and stated it plainly. Nothing more elaborate than that -- no top-down
theory built first and then confirmed by cherry-picked examples. This
matters for how much weight the claim should carry: an empirical
regularity noticed while doing the real, mechanical stripping work
first-hand is a meaningfully different, more credible kind of claim
than a philosophical framework equations were later fitted into. The
"two irreducible primitives" framing in `notes.md` is real and
correctly attributed to this same bottom-up method -- it's the single
most sweeping claim in the whole archive, and it's also the one most
directly traceable to plain pattern-noticing rather than theorizing.

---


## Real, standing connections to CURRENT project work (cross-referenced against points_active.md)

- `#659` — first TRIX dig, found `cell_format.py`'s FormatDefinition
  concept. This document's own "Core mechanism: FormatDefinition"
  section in TRIX_ECOSYSTEM.md confirms and extends that finding.
- `#671`/`#672` — Pond=chain, bridge cells with pre/post translation,
  a real per-value type-tag. The `BridgeContract` system found here is
  almost certainly the SAME mechanism, now understood with far more
  precision (confidence scoring, compile-time policy enforcement,
  dimensional analysis) than the #672 conversation alone gave.
- `#673` — Alan's own "we need a concept index" idea. This document
  IS the reason that idea matters — a body of work this size needs
  exactly the kind of index this file is attempting to be.
- The Tang Nano/ESP32 deployment plan — `math_frontend_design.md`'s
  own "Android tablet deployment" section (Termux + Flask + WiFi,
  ICM as the portability layer scaling from tablet to desktop to
  silicon) is a close, real precursor to the current hardware plan.
- **The never-built next step, stated directly by Alan, not found in
  any archived file -- LaTeX as a real input format, extending the
  LLVM side of things to take the equation side into account.** The
  real plan: not just SymPy/Python input (the actual, real math_
  frontend_design.md architecture already found -- SymPy → Discretiser
  → Pattern Matcher → Tiler → Wirer), but LaTeX equations parsed
  directly, compiled through an EXPANDED LLVM-style frontend that
  understands mathematical notation, not just imperative code. This
  tied directly into MathTrix -- explicitly named as the FIRST of the
  Trix family designs, the one everything else (FlowTrix, NeuroTrix,
  MidiTrix, and the rest) grew out of, not just one member among many.
  **A real, direct, current connection worth being explicit about:**
  this project's own `nano/llvm_ir_frontend_v1.py` -- actively extended
  THIS SAME SESSION with `select` and `icmp eq/ne` (`#668`/`#674`) --
  is exactly the kind of frontend this old, never-realized idea would
  have expanded. If a LaTeX-equation input path is ever wanted for
  Unicell-S, this is real, standing precedent for the shape of it: not
  a separate system, but the SAME LLVM frontend already being built,
  extended to accept a second real input grammar alongside ordinary
  IR.
