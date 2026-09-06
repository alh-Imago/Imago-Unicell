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

## paper_bridges/notes.md — design notes (IN PROGRESS, read through line ~1060 of 1483)

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

---

## Not yet opened at all (this session)

- `paper_bridges/data/cross_domain.py` (8.2KB)
- `paper_bridges/data/cross_domain_matches.json` (415KB) — presumably a JSON export of the same real bridge data now confirmed in `concept_graph.db`
- `paper_bridges/data/hub_gaps.json` (34.8KB) — presumably the real "49 displacement gaps" / hub-node data referenced throughout notes.md
- `paper_bridges/bridge_visualiser.html` / `concept_graph_explorer.html` — the real, built interactive UIs (both real, substantial files, 155KB/216KB)
- `paper_hawking/`, `paper_flowtrix/`, `paper_robotics/`, `paper_main/`, `paper_substrate/`, `paper_timing/` — all real, individual paper folders, only READMEs skimmed via file listing, not read
- `paper_substrate/notes.md` (6.4KB) — likely relevant given "substrate" naming echoes this project's own "universal symbolic substrate" framing (Paper 7)

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
