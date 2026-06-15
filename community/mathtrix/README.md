# MathTrix

The reference domain for UniCell — floating-point stencil computation
using the MIF (MathTrix Internal Float) format. MathTrix was the first
domain implemented and the pattern from which all other format definitions
were abstracted. If you are learning the UniCell format system, start here.

MathTrix is the native compute language of the fabric. Every other domain
ultimately converts to MIF at its boundaries for arithmetic.

---

## Format

### MIF (MathTrix Internal Float)
IEEE-754 split across **two cell words** — control cell and mantissa cell.

**Why split:** exponent arithmetic (the most common operation in floating-point
pipelines) lives entirely in the control cell. The mantissa cell is untouched
for routing and compare-only operations — zero fanout cost for pure comparisons.

**Cell layout:**
```
Control cell [31:0]:
  [31:24]  exponent (biased-127)
  [23]     sign
  [22]     is_nan
  [21]     is_inf
  [20]     is_zero
  [19:16]  guard bits
  [15:0]   unused

Mantissa cell [31:0]:
  [23:0]   significand (implicit-1 expanded)
  [31:24]  unused
```

Boundary cost paid once at MIF region entry/exit.
All internal arithmetic runs in MIF. LUT initial guesses used in
MIF_DIV/SQRT for faster Newton-Raphson convergence.

---

## Available Tiles

### Arithmetic
| Tile | Operation | Approx cells | Depth |
|------|-----------|-------------|-------|
| `MIF_ADD` | floating-point add | ~120c | d5 |
| `MIF_SUB` | floating-point subtract | ~120c | d5 |
| `MIF_MUL` | floating-point multiply | ~200c | d7 |
| `MIF_DIV` | divide (LUT-seeded NR) | 536c | d12 (optimised) |
| `MIF_SQRT` | square root (LUT-seeded NR) | 584c | d14 (optimised) |
| `MIF_RECIP` | reciprocal 1/x | ~180c | d6 |
| `MIF_RSQRT` | reciprocal sqrt 1/√x | ~250c | d8 |
| `MIF_MADD` | fused multiply-add a×b+c | ~300c | d9 |
| `MIF_ABS` | absolute value | ~20c | d1 |
| `MIF_NEG` | negate | ~20c | d1 |
| `MIF_MIN` | minimum of two values | ~60c | d3 |
| `MIF_MAX` | maximum of two values | ~60c | d3 |

### Comparison (1-bit result)
| Tile | Operation |
|------|-----------|
| `MIF_CMP_EQ` | equal |
| `MIF_CMP_LT` | less than |
| `MIF_CMP_GT` | greater than |
| `MIF_CMP_LE` | less than or equal |
| `MIF_CMP_GE` | greater than or equal |

### Boundary
| Tile | Direction |
|------|-----------|
| `MIF_PACK` | float → MIF (entry) |
| `MIF_UNPACK` | MIF → float (exit) |

---

## Worked Examples

### 1. Gray-Scott Reaction-Diffusion (Turing patterns)
Two chemical species U and V diffuse and react.
∂U/∂t = Du∇²U − UV² + f(1−U)
∂V/∂t = Dv∇²V + UV² − (f+k)V

Each grid cell is a UniCell pipeline computing one update step.
The Laplacian (∇²) is a stencil over 4 neighbours — cell fires when
all 4 neighbour values arrive (two-arrival model, 2 pairs).

```
Neighbours → MIF_ADD (sum) → MIF_MUL(Du) → reaction terms → next U
```

Parameters f (feed rate) and k (kill rate) are preloaded constants.
Changing f and k changes the pattern — spots, stripes, labyrinth —
without recompiling. Pure preloaded-A reconfiguration.

Model: `community/mathtrix/models/gray_scott.json`
Output: `mathtrix_animate.py` renders MP4/GIF of pattern evolution.

### 2. 2D Heat Equation (Laplacian diffusion)
∂T/∂t = α∇²T — temperature diffuses from hot spots.
Same stencil structure as Gray-Scott but single species, no reaction.

```
4 neighbours → MIF_ADD → MIF_MUL(α/4) → next T
```

Depth: 2 tiles. Trivially fits any cell budget.
Validation: point source decays as 1/√t. Gaussian initial condition
remains Gaussian (broadening).

Model: `community/mathtrix/models/laplacian_2d.json`

### 3. N-Body Gravity
Pairwise gravitational forces: F = Gm₁m₂/r²
Each pair (i,j) is one pipeline computing force contribution.
N bodies → N(N-1)/2 pipelines running in parallel.

```
positions(i,j) → MIF_SUB(Δx,Δy,Δz) → MIF_MUL → MIF_ADD(r²) →
MIF_RSQRT(1/r) → MIF_MUL(Gm₁m₂/r²) → force accumulator
```

At 448 cells: fits ~8–10 bodies in a single fabric load.
DDR streaming: pipeline reconfiguration extends to arbitrary N.

Model: `community/mathtrix/models/nbody.json`

### 4. Boids Flocking
Reynolds boids — three rules: separation, alignment, cohesion.
Each boid checks its neighbours; the three force contributions fire
in parallel pipelines and sum to a steering vector.

```
Neighbour positions → separation force  ┐
Neighbour velocities → alignment force  ├→ MIF_ADD → steering → new velocity
Neighbour positions → cohesion force    ┘
```

Emergent flocking behaviour from 3 simple local rules — exactly the
kind of parallel local computation UniCell is designed for.

Model: `community/mathtrix/models/boids.json`

### 5. PageRank
Graph diffusion / PageRank iteration.
Each node receives weighted contributions from its in-links.
r(i) = (1−d)/N + d × Σ r(j)/out_degree(j)

```
In-link values → MIF_MUL(weight) → MIF_ADD → MIF_MADD(damping) → new rank
```

Damping factor d preloaded. Converges in O(log N) depth with parallel
update across all nodes simultaneously.

Model: `community/mathtrix/models/pagerank.json`

---

## Adding a New MathTrix Model

MathTrix is the most common contribution type — any numerical stencil
or iterative computation maps naturally.

```json
{
  "id":          "my_stencil",
  "name":        "My Stencil",
  "domain":      "MathTrix",
  "format":      "MIF",
  "description": "What this computes",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-15",
  "tags":        ["mathtrix", "stencil"],
  "parameters": {
    "alpha": {"type": "float", "default": 0.1, "label": "Diffusion coefficient"}
  },
  "pipeline": [
    {"tile": "MIF_ADD",  "note": "sum 4 neighbours"},
    {"tile": "MIF_MUL",  "note": "multiply by α/4 (preloaded)"}
  ],
  "expected_output": "next grid value (MIF float)",
  "validation": "point source decays as 1/√t"
}
```

**Good MathTrix candidates:**
- Any PDE stencil (heat, wave, diffusion, advection)
- Iterative solvers (Jacobi, Gauss-Seidel, conjugate gradient)
- Cellular automata (Conway, Ising, Gray-Scott variants)
- Graph algorithms (PageRank, shortest path, centrality)
- Particle systems (N-body, SPH, DEM)
- Signal processing filters (FIR, IIR — see SigTrix for dedicated support)

---

## MIF as the Universal Intermediate

Every other domain converts to MIF at its arithmetic boundary:

```
BioTrix (DNA counts) → MIF_ADD (accumulate GC) → result
ChemTrix (atomic masses) → MIF_ADD (molecular weight) → result
PhysTrix (SI values) → MIF_MUL (unit arithmetic) → SI_CHECK → result
FinTrix (Q16.16) → MIF_COMPOUND (interest) → result
```

MIF is not just MathTrix's format — it is the shared arithmetic substrate
of the entire Trix ecosystem. When in doubt, compute in MIF.

---

## Running MathTrix Models

```python
from mathtrix import mathtrix   # domain frontend
result = mathtrix("gray_scott", {"size": 64, "steps": 100, "f": 0.055, "k": 0.062})

# Or via the animation frontend
from mathtrix_animate import animate
animate("gray_scott", output="pattern.mp4", steps=200)
```

Via server: start `unicell_server.py` and all MathTrix models appear
in the browser frontend. The Region Connector lets you chain models
visually and export the combined pipeline as a single `.icm`.

---

## Bridge Connections

MathTrix connects to PhysTrix via several high-confidence bridges:

| Bridge | Connection | Confidence |
|--------|-----------|-----------|
| `Bridge_Hawking` | PhysTrix → MIF | 1.0 |
| `Bridge_Navier_Stokes_Temp` | MIF → PhysTrix | 0.9 |
| `Bridge_Stefan_Boltzmann` | PhysTrix → MIF | 1.0 |
| `Bridge_LBM_Viscosity` | MIF → PhysTrix | 0.95 |

The FlowTrix LBM demo (see `PLAN.md`) is MathTrix extended with
lattice-Boltzmann specific tiles — it uses the same MIF format and
bridges directly to PhysTrix for viscosity and temperature.

---

*See also:*
- `cell_format.py` — MIF_Format class definition
- `mathtrix.py` — domain frontend (10 runners)
- `mathtrix_animate.py` — GPU-rendered video output
- `composer/unicell_composer.html` — visual pipeline builder
- `community/README.md` — contribution guide and bridge tile reference
