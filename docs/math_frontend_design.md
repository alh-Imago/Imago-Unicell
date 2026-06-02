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
