# Mathematical Frontend Design

## Goal
Accept mathematical problem descriptions (PDEs, linear systems, 
graph operations) and compile them to cell configurations automatically.
Scientists write equations; the fabric runs them.

## Architecture

```
User Input (SymPy / Python math notation)
    ↓
Discretiser (continuous → discrete, fixed-point scaling)
    ↓
Pattern Matcher (identifies mathematical primitives)
    ↓
Pattern Library (minimal cell templates per primitive)
    ↓
Tiler (stamps patterns across fabric for N instances)
    ↓
Wirer (connects boundary conditions between tiles)
    ↓
Existing compiler_int32 / IR pipeline
    ↓
Cell configurations → DMA → fabric
```

## Fixed-Point Strategy
Scientific problems use floats; UniCell is int32.
Solution: fixed-point arithmetic with configurable scale factor.
- Q16 format: scale by 65536, shift results appropriately
- User specifies domain range; frontend chooses scale
- Stability conditions (CFL etc.) enforced at compile time

## Pattern Library (initial entries)

### 1D Laplacian Stencil (heat/diffusion equation)
```
u_new[i] = u[i] + alpha * (u[i-1] - 2*u[i] + u[i+1])
```
With alpha=1/4 (stable, power-of-2 shift):
- 5 cells per grid point: SUB, SUB, ADD, SHR, ADD
- Pure int32, no floats
- N points → 5N cells, all parallel

### 2D Laplacian Stencil
```
u_new[i,j] = u[i,j] + alpha*(u[i-1,j]+u[i+1,j]+u[i,j-1]+u[i,j+1]-4*u[i,j])
```
- 8 cells per grid point: 4x SUB, ADD, ADD, SHR, ADD
- N×M grid → 8NM cells

### Inner Product (matrix row × column)
```
result = sum(a[i] * b[i] for i in range(N))
```
- 2 cells per element: MUL, accumulate via wired-OR
- N elements → 2N cells

### Graph Neighbour Aggregation
```
v_new[i] = f(v[i], sum(v[j] for j in neighbours(i)))
```
- Wired-OR bus does aggregation natively — 0 extra cells
- f() maps to 1-3 cells depending on function

### Threshold / SIS Epidemic Step
```
if infected_neighbours > threshold: state = INFECTED
else: state = SUSCEPTIBLE  
```
- 2 cells: comparator + latch
- Maps directly to two-arrival model

## SymPy Integration
SymPy already installed (v1.14.0). Can:
- Parse mathematical expressions symbolically
- Identify operation types (Add, Mul, Pow, Function)
- Generate C code via codegen (for LLVM path)
- Perform fixed-point scaling automatically

## Path to Implementation
1. Fixed-point scalar arithmetic (INT32 with scale factor) — SHORT
2. Pattern matcher for common stencils — SHORT  
3. 1D Laplacian demo on VM — validates approach
4. 2D extension — MEDIUM
5. SymPy notebook frontend — MEDIUM
6. Graph/network problems — MEDIUM
7. Float support (if needed) — LONG

## Existing Infrastructure
- compiler_int32.py: INT32 ADD/SUB/MUL/AND/OR/NOT/EQ/LT etc.
- llvm_frontend.py: parses LLVM IR → cell configs
- llvm_ir_mapper.py: maps IR constructs to tiles
- All comparison ops, zero-compare fast path — all working

The mathematical frontend sits on top of this stack.
Integer arithmetic primitives are all there.
Main gaps: MUL tile (future), SHR tile (future), float→fixed conversion.

---

## Float and Complex Support via Paired/Triplet Cells

No new hardware needed — extends the existing paired-cell mechanism
already used for signed 64-bit integers. Type flag already in place.

### Float32 — single INT32 cell (raw bit manipulation)
IEEE 754 float32 fits in 32 bits. Operations implemented as bit
manipulation chains using existing INT32 primitives:

| Operation      | Cells | Notes |
|---------------|-------|-------|
| FLOAT32_ADD   | 5     | exp compare, mantissa align(SHR), add, normalise, pack |
| FLOAT32_SUB   | 5     | negate sign bit + ADD |
| FLOAT32_MUL   | 4     | add exponents, multiply mantissas, normalise, pack |
| FLOAT32_DIV   | 8     | subtract exponents, divide mantissas, normalise, pack |
| FLOAT32_CMP   | 2     | compare signs, compare as int32 if same sign |
| FLOAT32_ABS   | 1     | mask sign bit to 0 |
| FLOAT32_NEG   | 1     | flip sign bit |
| FLOAT32_CVT   | 2     | convert to/from INT32 |

### Float64 — paired INT32 cells
52-bit mantissa spans two cells. Two-arrival model handles pair
synchronisation natively — pair waits for both halves before firing.

| Operation      | Cells | Notes |
|---------------|-------|-------|
| FLOAT64_ADD   | 7     | same as F32 but wider mantissa pair |
| FLOAT64_MUL   | 6     | same as F32 MUL but wider |

### Complex Numbers — triplet cells
Natural fit for the triplet concept:
- Cell 0: real part (F32 or F64 pair)
- Cell 1: imaginary part (F32 or F64 pair)  
- Cell 2: derived quantity (magnitude/phase) fires when both arrive

| Type          | Cells | Notes |
|--------------|-------|-------|
| COMPLEX32    | 3     | real(F32) + imag(F32) + magnitude |
| COMPLEX64    | 5     | real(F64) + imag(F64) + phase |

**Key insight:** The Calderón problem (complex parallel transport) =
COMPLEX triplets tiled across the manifold. Each point on the manifold
is a triplet; the transport equation is the wiring between triplets.

### Revised Pattern Library Cell Counts
With paired/triplet cells:
- 1D Laplacian grid point: 2 paired cells (not 5)
- Float32 ADD: 5 cells
- Complex operation: 3-5 cells
- Full float32+float64+complex library: ~49 pattern cells total

Float support moves from "LONG future" to "natural extension" —
no new hardware, no new gate states, just topology.

---

## Frontend UI Design

### Layout
Mirror the composer workflow — simple and effective, nothing flashy.
- **Left panel:** Math input
- **Right panel:** Derived model / cell topology
- **Bottom:** Validate → Export → Upload workflow

### Left Panel — Math Input

**Equation editor** — as natural as possible:
- LaTeX notation: `\nabla^2 u = \frac{\partial u}{\partial t}`
- Python/SymPy: `laplacian(u) == diff(u, t)`
- Plain text for simple cases: `u_new = u + alpha*(u_left - 2*u + u_right)`

**Problem parameters** — simple form fields:
- Grid size: `N = 100`
- Time steps: `T = 1000`
- Boundary conditions: dropdown (Dirichlet, Neumann, periodic)
- Data type: dropdown (INT32, FLOAT32, FLOAT64, COMPLEX)
- Precision/scale: slider or auto

**Presets** — one-click common problems:
- 1D/2D Heat equation
- Wave equation
- SIS epidemic
- Matrix multiply
- Graph Laplacian
- N-body gravity

Presets are key for researcher outreach — physicist sees "Wave equation",
selects it, enters grid size, hits validate. No cells, no bus addresses.

### Right Panel — Derived Model
- Visual cell pattern generated from equation
- Cell count and zone allocation
- Topology diagram showing pairs/triplets and connections
- Estimated execution time

### Bottom Workflow (same as composer)
1. **Validate** — run on VM, check results against known solution
2. **Export** — generate cell configuration file
3. **Upload** — push to fabric via DMA

Validate step is key for scientific users — verify results match
published data before committing to hardware. Pre-validated pattern
library means validation is mostly checking boundary conditions
and scale factor. Fast feedback loop.

### User Never Sees
- Cell addresses
- Bus topology
- Gate states
- Compiler internals

The math IS the program. The frontend IS the compiler interface.

---

## MathTrix — Demo Problem Library

Nine built-in demos covering major scientific domains.
Each one visually compelling in the VM visualiser.

### 1. Gray-Scott Reaction-Diffusion (Turing Patterns)
```
du/dt = Du*∇²u - u*v² + F*(1-u)
dv/dt = Dv*∇²v + u*v² - (F+k)*v
```
Patterns: Laplacian stencil, MUL, ADD, SUB
Audience: computational biology, chemistry
Visual: stunning self-organising patterns

### 2. Ising Model (Spin Lattice)
```
h = sum(neighbours(s))
s_new = sign(h)
```
Patterns: neighbour aggregation (wired-OR), comparator, sign
Audience: statistical physics, materials science
Visual: magnetic domain formation

### 3. 2D Wave Equation
```
u_next = 2*u - u_prev + c² * ∇²u
```
Patterns: Laplacian, ADD, SUB, MUL
Audience: physics, engineering
Visual: ripple propagation across grid

### 4. PageRank (Graph Diffusion)
```
PR_new = alpha * sum(PR[j]/deg[j] for j in neighbours) + (1-alpha)
```
Patterns: neighbour aggregation, MUL, ADD, DIV
Audience: computer science, data science
Visual: importance flowing through network

### 5. Belief Propagation (Message Passing)
```
m[i][j] = f(x[i], [m[k][i] for k in neighbours if k != j])
```
Patterns: neighbour aggregation, nonlinear f() (2-3 cells), state update
Audience: ML, communications, coding theory
Visual: messages converging across graph

### 6. Fast Marching Method (Level-Set)
```
T_new = min(T_left, T_right, T_up, T_down) + 1/F
```
Patterns: MIN (2 cells), ADD, constant injection
Audience: robotics, medical imaging, geometry
Visual: expanding wavefronts

### 7. N-Body Gravity (Softened Potential)
```
F = sum(m[i]*m[j] * (x[j]-x[i]) / (dist(i,j)³ + eps) for j in bodies)
```
Patterns: neighbour aggregation, MUL, DIV, POW chains
Audience: astrophysics, molecular dynamics
Visual: orbital mechanics, clustering

### 8. Boids / Flocking (Reynolds)
```
v_new = w1*separation() + w2*alignment() + w3*cohesion()
```
Patterns: neighbour aggregation, vector ops (paired cells), weighted sums
Audience: games, simulation, emergence
Visual: emergent flocking behaviour

### 9. Continuous Conway (Smooth Game of Life)
```
u_new = sigmoid(alpha * sum(neighbours(u)) - beta)
```
Patterns: neighbour aggregation, MUL, SUB, sigmoid (3-4 cells)
Audience: complexity science, general
Visual: smooth evolving patterns

---
All 9 demos ship as presets in the MathTrix frontend.
Each generates a personalised researcher demo package:
equation → cell pattern → VM animation → results.
