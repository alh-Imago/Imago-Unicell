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
