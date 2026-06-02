# UniCell Benchmark Targets

Papers and problem domains where UniCell's parallel fabric architecture
offers fundamental advantages over Von Neumann / OpenMP / GPU approaches.

The common thread: problems that are embarrassingly parallel but bounded
by Amdahl's Law on conventional hardware. UniCell's cells fire in parallel
by default — no scheduler, no thread overhead, no memory bus contention.

---

## 1. Fractional Hyperbolic PDE Simulation (3D)

**Title:** An easy-to-implement parallel algorithm to simulate complex
instabilities in three-dimensional (fractional) hyperbolic systems

**Author:** J.E. Macías-Díaz  
**Journal:** Computer Physics Communications (2020)  
**DOI:** https://doi.org/10.1016/j.cpc.2020.107383

**Problem:** Solving fractional PDEs in 3D where every spatial point
depends non-locally on every other point. Brutal on Von Neumann —
can't march sequentially because of global coupling.

**Current approach:** Explicit finite difference + OpenMP parallelism
on shared memory. Fortran implementation.

**UniCell fit:**
- Each spatial grid point → one cell
- Fractional derivative coupling → wired-OR bus aggregates influence naturally
- Turing pattern formation (inhibitor-activator) → emergent behaviour
  from local rules, exactly what UniCell does natively
- No OpenMP pragmas, no thread management — topology IS the algorithm

---

## 2. Type I Error Probability Simulation (Statistical)

**Title:** Implementation of a Parallel Algorithm to Simulate the
Type I Error Probability

**Author:** Francisco Novoa-Muñoz  
**Journal:** Mathematics, 12(11), 1686 (2024)  
**DOI:** https://doi.org/10.3390/math12111686

**Problem:** Monte Carlo simulation of Type I error for goodness-of-fit
tests on bivariate Poisson distributions. Very long execution times
on single core.

**Current approach:** R parallel packages (parRapply, boot).
50-90% reduction with 2-12 processors. Scales as power law y=a*p^b
with R²≈0.999 — predictable Amdahl ceiling.

**UniCell fit:**
- Thousands of independent test evaluations → cells fire simultaneously
- Sequential fraction is only RNG + final aggregation
- Scaling curve would be much steeper than p^b — cells don't coordinate
- Application domain: medical statistics, clinical trials, epidemiology

---

## Problem Domains to Watch

- Hyperspectral imaging — thousands of wavelength bands, same ops on each
- Radar signal processing — range/doppler bin parallelism
- Seismic analysis — correlation across large sensor arrays
- Financial risk (Monte Carlo) — thousands of independent scenarios
- Genomics — sequence alignment across full genome
- Reaction-diffusion / Turing patterns — self-organising spatial systems
- Lattice gauge theory (QCD) — massively parallel physics simulation

---

*Add papers by pasting links — each entry should note the problem,
current approach, speedup achieved, and why UniCell fits.*

---

## 3. Calderón Problem for Systems via Complex Parallel Transport

**Title:** Calderón problem for systems via complex parallel transport

**Author:** Mihajlo Cekić  
**Source:** arXiv (mathematics)  
**Link:** https://arxiv.org/search/math?searchtype=author&query=Cekić,+M

**Problem:** Reconstructing internal properties (connection matrix,
matrix potential) of a Riemannian manifold from boundary measurements
(Dirichlet-to-Neumann map). Classic inverse problem — infer what's
inside from what comes out at the edges.

**UniCell fit:**
- Complex parallel transport = signals propagating simultaneously along
  paths through a manifold → direct map to cell fabric topology
- Each cell is a point on the manifold, connections are the metric
- Wired-OR bus performs boundary measurement naturally — outputs appear
  on bus, internal state (gate topology, a_data) is the hidden structure
- Numerical solution of this class requires massive parallel path
  integration — embarrassingly parallel on UniCell
- Theoretical resonance: the Calderón problem asks "what is the internal
  topology from boundary signals?" — which is also the UniCell security
  model (fabric topology as unrecoverable internal state)


---

## 4. Massively Parallel SAT Solving

**Title:** Massively Parallel Solving of Math Problems

**Author:** Marijn Heule (TU Wien / Carnegie Mellon)  
**Event:** VCLA Talk, TU Wien, January 2019  
**Notable results:**
- Boolean Pythagorean Triples proof: 200 terabytes (largest math proof ever)
- Schur Number Five proof: 2 petabytes

**Problem:** SAT solving — searching enormous combinatorial boolean spaces.
Parallelizes poorly on Von Neumann because clause learning creates
dependencies forcing synchronisation across threads.

**UniCell fit:**
- Each SAT clause → one cell
- Variables → bus addresses
- Unit propagation (core of CDCL) = two-arrival model naturally:
  cell fires when inputs are determined
- Conflict detection → wired-OR surfaces contradictions without
  central conflict database
- Clause learning → reconfigure fabric topology dynamically
- No synchronisation barrier needed — clauses propagate independently
  until conflict, physics handles arbitration

**Significance:** SAT is backbone of formal verification, chip design,
cryptanalysis, scheduling. Every EDA tool (including Vivado) uses SAT
solvers internally. UniCell accelerating SAT would be foundational.


---

## 5. Parallel Learning of Dynamics in Complex Systems (Graph Neural ODE)

**Title:** Parallel Learning of Dynamics in Complex Systems

**Authors:** Xueqin Huang, Xianqiang Zhu et al.  
**Journal:** Systems, 10(6), 259 (2022)  
**DOI:** https://doi.org/10.3390/systems10060259  
**Code:** https://github.com/Huangbuffer/PGNDL

**Problem:** Learning and predicting dynamics on large complex graphs
(epidemic spread, gene regulation, mutualistic ecology). Current methods
slow on large graphs due to NP-complete graph structure + nonlinear dynamics.

**Current approach:** D-METIS graph partitioning + Partitioned Graph Neural
Dynamics Learner (PGNDL) with neural ODEs. 2-4× faster than baseline NDCN.
Space complexity reduced to 1/C of baseline (C = number of subgraphs).

**UniCell fit:**
- Each graph vertex → one cell, edges → bus address connections
- Dynamics propagation = cell firing cascade through topology
- Graph partitioning (D-METIS) is essentially what Pblocks do physically —
  partition the compute fabric to match the problem structure
- Neural ODE continuous-time integration → two-arrival model naturally
  handles asynchronous state updates without discrete time steps
- SIS epidemic dynamics: susceptible/infected state = cell armed/fired state
- The wired-OR bus aggregates neighbour influence exactly as the
  graph Laplacian Φ does in the GNN formulation
- No GNN training needed — topology IS the learned dynamics model

**Key insight:** Their D-METIS balances both vertex count AND dynamic
change rate across subgraphs. UniCell zones could do this natively —
cells with high firing rates naturally belong in the same zone to
minimise cross-boundary bridge traffic.

**Applications noted in paper:** epidemic prevention, computer virus
spread, terrorist network disruption, power grid robustness,
public opinion monitoring, climate modelling, healthcare.


---

## 6. Reliability of Parallel and Series-Parallel Systems via Algebraic Inequalities

**Title:** Improving the Reliability of Parallel and Series-Parallel Systems
by Reverse Engineering of Algebraic Inequalities

**Author:** Michael Todinov, Oxford Brookes University  
**Journal:** (preprint/paper)

**Problem:** Improving system reliability without knowing individual
component reliability values.

**Key findings:**
- Parallel systems: symmetric arrangement of interchangeable components
  ALWAYS gives higher reliability than asymmetric — regardless of
  individual component reliabilities
- Series-parallel systems: asymmetric redundancy arrangement is superior

**UniCell fit:**
- All cells are NOR-universal and identical = interchangeable components
- Equal cells per zone + equal Pblock sizes = symmetric parallel arrangement
- Mathematical proof that this is optimal WITHOUT needing to characterise
  individual cells — structural reliability, not component reliability
- Bridge lanes between zones = series-parallel topology — asymmetric
  lane counts may improve overall fabric reliability per the second finding
- Directly applicable to UniCell zone architecture design decisions

**Significance:** Provides mathematical foundation for the zone layout
decisions — equal cell counts per zone is provably optimal, not just
convenient.


---

## 7. Parallel Programming Models for Dense Linear Algebra on Heterogeneous Systems

**Title:** Parallel Programming Models for Dense Linear Algebra on
Heterogeneous Systems

**Authors:** Abalenkovs, Abdelfattah, Dongarra et al. (Manchester/Tennessee/ORNL)  
**Journal:** Supercomputing Frontiers and Innovations, 2(4), 67-86 (2015)  
**DOI:** https://doi.org/10.14529/jsfi150405

**Problem:** Dense linear algebra (DLA) on CPU+GPU heterogeneous systems.
Entire paper motivated by one fact: compute-network bandwidth gap is
2-3 orders of magnitude and widening. All complexity (BLAS, DAGs,
fork-join, batched scheduling) exists to minimise data movement.

**Current state of the art:** PLASMA (multicore), MAGMA (GPU+CPU),
task-based DAG scheduling, batched BLAS for small problems.
Still fundamentally limited by memory hierarchy latency.

**UniCell fit:**
- Gate state IS the data AND the computation — no data movement by design
- The entire BLAS/LAPACK/PLASMA stack exists to work around a problem
  UniCell doesn't have
- Matrix tiles → zones; tile operations → cell firing cascades
- BLAS-3 matrix-matrix multiply: each output element is an inner product
  of a row and column — maps to a cell receiving two bus arrivals
- DAG task dependencies → two-arrival model naturally enforces ordering
  without explicit dependency tracking
- Batched small problems (O(100) matrices) → ideal for UniCell where
  each small problem maps to a few cells, all firing simultaneously
- The paper's "future direction" of tensor contractions maps directly
  to multi-dimensional address matching in the UniCell bus

**Key quote:** "an algorithm that is computation-bound and running close
to peak today may be communication-bound in the near future"
→ UniCell is never communication-bound; communication IS computation.


---

## 8. Parallel Computing in Multibody System Dynamics

**Title:** Parallel Computing in Multibody System Dynamics: Why, When, and How

**Authors:** Dan Negrut, Radu Serban, Hammad Mazhar, Toby Heyn  
**Journal:** J. Comput. Nonlinear Dynam., 9(4), 041007 (2014)  
**DOI:** https://doi.org/10.1115/1.4027313

**Problem:** Multibody dynamics (MBD) simulation — N bodies interacting
through forces, constraints, contacts. Large sets of equations crossing
disciplinary boundaries (multi-physics). Scales badly on serial hardware.

**Current approach:** GPU/multicore parallelism. Paper argues parallel
computing is the main source of speed improvement in MBD for the
coming decade.

**UniCell fit:**
- Each body → one cell (or small group of cells)
- Force interactions between bodies → wired-OR bus aggregation
  naturally computes net force on each body from all neighbours
- N-body interaction: O(N²) on Von Neumann, O(1) on UniCell —
  all pairwise interactions happen in one bus cycle
- Constraint equations → cell firing conditions (gate state encodes
  the constraint type)
- Multi-physics coupling → zone bridge architecture naturally
  separates physics domains while allowing interaction

**Domain note:** Connects to robotics, vehicle dynamics, granular
material simulation, biomechanics, planetary/orbital mechanics.


---

## Ideas to Explore

### Mathematical Problem Compiler (Tier 2 Frontend)

A frontend that accepts mathematical notation (PDEs, linear systems,
graph Laplacians, N-body potentials) and compiles directly to cell
configurations. Scientists write equations, fabric runs them.
No CUDA, no MPI, no thread management.

**Pattern Library concept:**
- Each mathematical primitive (Laplacian stencil, inner product,
  threshold, propagation rule) maps to a minimal cell pattern
- Library of pre-characterised patterns — "standard mathematical cells"
- Compiler selects patterns from library, tiles across fabric, wires boundaries
- Optimisation reduces to placement/routing on known-good patterns
  rather than general search — tractable problem
- Results are just a configuration pattern, not a program

**Flow:**
Problem description → pattern matching → minimal cell topology →
DMA → fabric → results

**Why scientists would engage:**
- Write equations as normal (SymPy frontend?)
- Submit to fabric, get results orders of magnitude faster than cluster
- Each benchmark paper in this doc represents a research group
  that would immediately understand the value
- Publishable as a new programming model for scientific computing
  independent of the hardware story

**Connection to self-optimisation:**
Fabric could tune its own pattern placement based on runtime firing
rates — cells that fire together get placed together, minimising
bridge crossings. Self-organising layout.

