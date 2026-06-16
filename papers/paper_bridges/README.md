# Paper 3 — Typed Cross-Domain Computation and Bridge Inference

## Status: active development — inference engine next

---

## What exists

### Visualisations (open in browser)
- `bridge_visualiser.html` — four-tab tool:
  - MATRIX GRID: domains × variables, gaps visible as dark cells
  - CHORD DIAGRAM: domain connections by shared variable count
  - BRIDGE TABLE: domain × domain gap matrix with hover detail
  - HUB GAPS: bar chart of 17 hub concepts and their undeclared pairings
  - ⬡ PLACE EQUATION: user equation placement tool
- `concept_graph_explorer.html` — 3D sphere graph, 203 nodes, 332 edges
  - Click node → panel shows domain, SI dimension, connections, equations
  - Search, dimension filter, path finder, BRIDGES panel

### Data (`data/`)
- `concept_graph.db` — SQLite: 203 concepts, 164 equations, 1261 connections
- `build_tables.py` — rebuilds DB from source (run first after any changes)
- `build_static_explorer.py` — generates concept_graph_explorer.html
- `cross_domain.py` — cross-domain matcher (amber/green gap analysis)
- `cross_domain_matches.json` — 251 amber gaps (250 undeclared)
- `hub_gaps.json` — 156 hub concept cross-domain gaps
- `equation_sources.md` — Wikipedia source pages, processing notes

### Notes (`notes.md`)
- Three-layer inference model (domain, scope, dimension)
- Degrees of separation / confidence as conversion rate
- Computable vs declarative-only territory
- Hub assumption problem
- User equation placement workflow
- Genomics isolation as key result
- E=mc² as maximum-density hub node

---

## Key findings so far

**203 concepts across 22 domains, 164 equations, 1261 connections**

Top hub concepts (appear in most domains):
- displacement: 14 domains, 103 equations
- mass: 10 domains, 91 equations
- velocity: 8 domains, 76 equations
- temperature: 5 domains, 64 equations (underdeclared — should be 8+)

**250 undeclared cross-domain bridges** (amber gaps)
**156 hub concept cross-domain gaps** (concepts assumed connected, never declared)

**Genomics is almost completely isolated** — only one declared bridge
(Tm formula). Missing: Genomics→Thermodynamics, →Chemistry, →Information
theory, →Statistics, →Physics. All known to exist. None formalised.

This is the Mendeleev result: the graph makes assumed connections visible
as explicit gaps.

---

## What's missing from the equation corpus

Coverage is ~35-40% of the Wikipedia source pages. Still to import:
- Fluid mechanics (Navier-Stokes, continuity, vorticity transport)
- Photonics (laser, optical fiber, interference)
- Nuclear/particle (decay chains, cross-sections, fission/fusion)
- Constitutive equations (stress/strain, piezoelectric)
- Laws of science (conservation laws as formal equations)
- Biology (metabolic pathways, Hardy-Weinberg, Michaelis-Menten)
- Information theory (Shannon entropy — key Genomics bridge)
- Economics (supply/demand, compound interest)

Each page adds ~20-50 equations and more cross-domain bridge candidates.

---

## Next: Bridge Inference Engine

The inference engine (`concept_inference.py` — to build) will:

1. **Path finding** — BFS/Dijkstra on concept graph, shortest path by
   confidence product (not hop count)

2. **Gap surfacing** — for any two concepts, find:
   - Direct dimension match → suggest identity bridge
   - Indirect path via hub nodes → suggest conversion chain
   - No path → declare knowledge hole with dimensional constraints

3. **Candidate scoring**:
   - Dimension match: necessary but not sufficient
   - Domain proximity: closer domains → higher prior confidence
   - Hub connectivity: paths through high-degree nodes → lower novelty
   - Mechanism existence: known conversion → higher confidence ceiling

4. **Precomputed path cache** — all-pairs shortest paths stored as
   JSON/SQLite sidecar, O(1) query time

5. **Community contribution format** — YAML per mechanism declaration,
   one file per bridge, diff-friendly for git

The DB and visualisers here are the foundation. The inference engine
reads from concept_graph.db and writes to a path cache.

---

## Rebuild sequence

```bash
cd papers/paper_bridges/data
python3 build_tables.py        # rebuild DB
python3 cross_domain.py        # rerun gap analysis
python3 build_static_explorer.py  # rebuild 3D explorer
# bridge_visualiser.html reads DB data embedded at build time —
# rebuild by running the inline script in notes or from concept_graph/
```
