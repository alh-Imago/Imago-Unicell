# Concept Graph — Design Notes
*Captured: 2026-06-16 — morning thinking session*
*Status: pre-implementation, ideas still developing*

---

## The core insight

Everything is connected. But the connection only means something if you can
declare the mechanism that makes it real. Without a mechanism it's philosophy.
With a mechanism it becomes engineering — falsifiable, challengeable, improvable.

**The confidence score IS the conversion rate.** Not an abstract opinion — a
real physical quantity describing how much of what goes in comes out the other
side at each step.

---

## The three-layer model

Before any connection can be suggested, three things must align:

1. **Domain** — what field of knowledge does this concept belong to?
   (thermodynamics, mechanics, chemistry, ecology, political science...)

2. **Scope** — what specific quantity within that domain?
   reaction_enthalpy and kinetic_energy are both [2,1,-2,0,0,0,0] joules
   but different things. Dimensional match is necessary but not sufficient.

3. **Dimension** — SI vector as a sanity check, not the primary signal.
   Catches obvious mismatches. Does not confirm a valid connection.

All three must be respected. Dimension alone is not enough.

---

## Degrees of separation

The concept graph is a directed weighted graph where:
- **Nodes** = ConceptDeclarations (known physical/abstract concepts)
- **Edges** = ConversionMechanisms (declared physical processes)
- **Edge weight** = confidence_max of the mechanism (conversion rate)

Path confidence = product of edge weights along the route.
This is not arbitrary — it mirrors real physical conversion rates:
  - Water → steam: 2260 J/g input required. Confidence 1.0. Non-negotiable.
  - Thermal energy → mechanical work (Carnot): confidence ceiling 0.85.
    Real engines always below this. Second law enforced by the graph.
  - Reaction enthalpy → mechanical work: two steps, ceiling ~0.85.

The system finds **shortest path by confidence loss** — not by hop count.
A two-hop path at 0.95 × 0.95 = 0.90 is better than a one-hop path at 0.70.

---

## The biological example

**Oak tree → Wolf: what's the path?**

  Oak → glucose (photosynthesis, C fixation)
  Glucose → ATP (cellular respiration)          ← shared node
  ATP → wolf tissue (metabolic conversion)

**Wolf → Oak: what's the path?**

  Wolf dies → decomposition (bacteria, fungi)
  Decomposition → nitrogen/carbon compounds (soil chemistry)
  Compounds → root uptake (plant biology)
  Root uptake → oak biomass (growth)

Each step has a real, measurable conversion rate. Maybe 10% of wolf biomass
reaches soil in bioavailable form. Maybe 40% gets taken up by roots. Maybe
60% becomes structural tissue. 0.10 × 0.40 × 0.60 = 0.024 path confidence.

That's not a weakness — that's the honest truth about how lossy the
wolf→oak path is. And it tells you exactly where to look if you want to
improve it (the decomposition step is doing most of the damage).

**The hub node:** ATP. Oak and wolf both run on it. What looks like five
steps reduces to two when you find the shared intermediate. The inference
engine discovers hubs like this naturally — high-connectivity nodes that
appear on many shortest paths. Carbon. Energy. Water. Temperature. These
will emerge from path analysis without anyone declaring them special.

---

## Cycles and thermodynamics

Wolf → tree → carbon → atmosphere → photosynthesis → tree → deer → wolf.

The cycle closes. The confidence of the full cycle is the product of all
conversion rates around the loop. That product is always less than 1.0.

**The second law of thermodynamics falls out of the graph structure by
construction.** You don't assert it — it emerges. Any closed cycle loses
energy at each step, so the round-trip confidence is always < 1.0.

There are no shortcut paths. Water to steam requires exactly 2260 J/g.
The graph cannot be fooled into finding a cheaper route because the
mechanisms are declared facts, not suggestions.

---

## Two territories

The graph spans two fundamentally different kinds of knowledge:

**Computable territory**
Mechanisms with defined numerical transfer functions. These can become
bridge tiles on UniCell fabric. The conversion rate is a real number,
the formula is executable, the output is deterministic.

Examples: water→steam (enthalpy), Arrhenius (activation energy→rate),
Hawking (mass→temperature), LBM (relaxation→viscosity).

**Declarative-only territory**
Mechanisms that are real and directional but not reducible to a formula —
or not yet. These live in the graph as knowledge. They inform and connect.
They do not run on silicon.

Examples: population density → resource competition (measurable but
context-dependent), resource competition → political tension (historical
correlation, ~0.60 confidence), political tension → policy outcome (~0.40).

Multiply: 0.85 × 0.60 × 0.40 = 0.20. The system honestly tells you that
four fifths of the signal is lost. And it shows you exactly which step is
the weak link (tension→outcome). That's where the research needs to go.

**A mechanism moving from declarative to computable is a genuine research
advance.** The graph marks the frontier. UniCell runs behind the frontier
where the physics is solid.

---

## UniCell's honest limits

UniCell needs fact, logic, or numbers. That's its strength and its limit.

Forcing ephemeral or poorly-defined concepts onto the fabric would break
the honesty guarantee. The mechanism requirement is the safeguard — if you
cannot declare a numerical transfer function, the connection stays in the
declarative layer. It does not become a bridge tile.

This is not a weakness. It's intellectual honesty built into the architecture.

---

## Precomputation

The graph must be precomputed. At query time you want O(1) lookup, not
a graph traversal multiplying confidence scores on the fly.

**Precomputed path cache** — for each concept pair, store:
```json
{
  "from": "reaction_enthalpy",
  "to": "mechanical_work",
  "path": ["reaction_enthalpy", "thermal_energy", "mechanical_work"],
  "mechanisms": ["enthalpy_identity", "carnot_heat_engine"],
  "confidence": 0.85,
  "hops": 2,
  "computable": true
}
```

Build time: O(n²) on concept count — manageable because the graph is
sparse. Most concepts have no direct mechanism to most others.

Rebuild trigger: any change to KNOWN_CONCEPTS or CONVERSION_MECHANISMS.
Same pattern as rebuilding the manual — one command, runs in background.

The cache ships as a prebuilt artifact alongside KNOWN_CONCEPTS and
CONVERSION_MECHANISMS. Community members get the graph without running
the solver. When they add a mechanism they run the incremental update
and submit the diff to REGISTRY.

---

## Community as graph builders

The community contribution layer already exists for Trix formats and models.
This extends it to a different kind of contribution — declaring edges in the
ontological graph. Each contribution is:

- A ConceptDeclaration (new node)
- A ConversionMechanism (new edge with confidence ceiling)
- A path cache update (incremental recompute)

Each contribution is a **falsifiable scientific claim**, not just code.
Other domain experts can challenge a mechanism. A bad confidence ceiling
gets corrected. A shorter path gets discovered. The graph improves.

This is how science works. The graph makes the structure explicit and
computable.

---

## Graph topology

The concept graph will have natural structure that emerges from path
analysis:

**Hub nodes** — high connectivity, appear on many shortest paths.
Carbon, energy, temperature, water, ATP. No one declares these special —
the path solver reveals them.

**Dense clusters** — thermodynamics, chemistry, fluid dynamics are
mature sciences with many declared mechanisms and short high-confidence
paths between their concepts.

**Sparse frontier** — sociology, political science, ecology have longer
paths, lower confidence ceilings, fewer declared mechanisms. The graph
shows where the science is mature and where it isn't.

**Cross-cluster bridges** — the high-value discoveries. A mechanism
connecting thermodynamics to genomics (Tm formula). A mechanism connecting
fluid dynamics to chemistry (LBM viscosity). These are the Hawking bridges
of the graph — unexpected connections with real physical grounding.

---

## Implementation plan (sketch)

**`concept_graph.py`** — separate from cell_format.py, keeps core clean:
  - Path solver (Dijkstra by confidence loss)
  - Cache builder (full precompute from KNOWN_CONCEPTS + CONVERSION_MECHANISMS)
  - Incremental updater (recompute affected paths on graph change)
  - Query interface (O(1) lookup: get_path, get_confidence, get_hops)
  - computable flag: True if all mechanisms on path have numerical formulae

**Region Connector extension:**
  - "Suggested connections" panel — cache lookup, not live traversal
  - Shows path, hop count, confidence, computable flag
  - Amber = conversion needed, Green = identity, Grey = declarative only

**Community tooling extension:**
  - community_tools.py: validate_concept, validate_mechanism, update_cache
  - CONCEPT_REGISTRY.md alongside REGISTRY.md

---

## Open questions (let these develop)

- How do you assign confidence to a *newly declared* mechanism with no
  empirical data yet? Prior from domain maturity? Expert elicitation?

- Cycles: do you allow the solver to traverse cycles? Need a visited-node
  guard but cycles are real and meaningful (biogeochemical cycles).

- Directionality: some mechanisms are reversible (water↔steam with energy
  input/output). Others are not (Carnot — heat→work is lossy, work→heat
  is trivial). How does directionality affect path finding?

- The declarative/computable boundary: who decides when a mechanism is
  well-defined enough to become computable? Peer review? Confidence
  threshold? This is a governance question as much as a technical one.

- Esoteric domains: consciousness, aesthetics, meaning. Can the mechanism
  requirement keep these honest or does the graph break down entirely?
  Possibly the honest answer is: these stay permanently declarative, and
  that's fine.

---

## One sentence for the paper

"The same principle that makes the fabric work — irreducibly simple
primitives composing into universal expressibility — makes the knowledge
graph work. One cell, one gate, one cycle. One concept, one mechanism,
one confidence. Both compose. Both are honest about what they cannot do."


---

## Late addition — 2026-06-16 evening

### Fundamental equations as maximum-density hub nodes

E=mc² has three elements: E, m, c. Each connects to dozens of other
fundamental equations. Each of those connects to dozens more.

E → thermal energy (Boltzmann), Hawking temperature, reaction enthalpy,
    kinetic energy, photon energy (E=hf), binding energy...

m → gravitational mass (Schwarzschild), inertia (F=ma), rest mass,
    relativistic mass, Higgs coupling, Planck mass...

c → wavelength/frequency (c=λf), fine structure constant, permittivity
    and permeability (c=1/√(ε₀μ₀)), Planck units, Lorentz factor...

E=mc² is not just a node. It is a junction — a place where the graph
becomes maximally dense. Every path through energy-mass-light conversion
passes through it. Confidence 1.0 in all directions — derived, not
empirical.

**The graph reveals hub nodes by path analysis, not by declaration.**
Count how many shortest paths pass through each concept. The fundamental
equations emerge as hubs automatically. This is the same pattern
Mendeleev saw — certain elements sat at crossroads, more connected than
their neighbours, and those turned out to be the most chemically
significant.

Fundamental physics is the densest region of the concept graph. Short
paths everywhere. High confidence throughout. Maximum connectivity.
Also the region closest to the knowledge holes — the information paradox,
quantum gravity, dark matter all sit adjacent to this dense core.

### Multidimensional data tables

A multidimensional data table is a tensor. Each dimension is a concept
axis. A search is a reduce operation across one or more axes.

UniCell is the natural search engine for this:
- Each dimension streams through a parallel pipeline
- SENSOR_STACK pattern: N dimensions on N consecutive addresses
- Pipeline depth is compile-time constant regardless of table size
- A billion-row 4D table searches in the same ticks as a thousand-row one
- Onion wrapper declares dimensional schema (concept IDs per dimension)
  so the compiler builds the right search pipeline before first row arrives

The multidimensional search problem and UniCell streaming architecture
were made for each other.

### Scale note

E=mc² alone — three concepts, each connecting to dozens, each of those
to dozens more — makes the graph tangled fast around the fundamental
equations. This is not a problem. It is the point. The tangle IS the
structure of physics. Making it navigable, searchable, and gap-revealing
is the contribution.

The graph will be large. It will be worth it.
