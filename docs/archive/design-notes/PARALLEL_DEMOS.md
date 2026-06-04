# Parallel Demo Ideas — UniCell Native Programs

*Recorded 2026-05-31. Cross-AI collaboration on parallel spatial programs.*
*These are not simulations — they are UniCell-native computations.*

---

## Cellular Automata

### Brian's Brain (upgrade from GoL)
Three states: OFF, ON, DYING. ON→DYING→OFF. OFF→ON if exactly 2 neighbours ON.
Adds 2-bit state + second comparator to existing GoL tile.
Visual: exploding wavefronts, spirals, chaotic fronts.

### Cyclic Cellular Automata (CCA)
Each cell state 0…N-1. Increments if any neighbour is exactly +1 mod N.
Needs: equality comparators, mod-N increment, OR-reduce.
Visual: expanding colour rings, spirals, interference patterns. Looks like a GPU shader.

### Wireworld
States: empty, wire, electron head, electron tail. Local rules, digital logic CA.
Can literally build logic gates inside the grid.
Already have all primitives needed.

---

## Math — PDE / Numerical

### Heat Equation / Discrete Laplacian
```
new = (N + S + E + W - 4*center)   or   new = average(neighbours)
```
5 adders + 1 subtractor per tile. Backbone of Poisson solvers, image processing.
Embarrassingly parallel. Perfect first math demo.

### Wave Equation
```
new = 2*current - previous + c² * Laplacian(current)
```
2 registers per cell + Laplacian tile + 3 adders + 1 subtractor.
Visual: ripples, interference, standing waves, reflections, resonant modes.

### Reaction-Diffusion (Gray-Scott / Turing Patterns)
```
A' = A + Da*Lap(A) - A*B*B + f*(1-A)
B' = B + Db*Lap(B) + A*B*B - (k+f)*B
```
The demo that makes people say "this is not a CPU."
Produces: spots, stripes, spirals, self-organising structures.

### Jacobi Iteration (Poisson Solver)
```
x_new = average(neighbours)
```
Solves ∇²φ = 0. Electrostatic potentials, fluid pressure, harmonic interpolation.
Embarrassingly parallel — every cell updates simultaneously.

---

## Sorting Networks

### Bitonic Sort (king of hardware sorting)
Fixed wiring, fixed compare-swap pattern, no branches, no loops.
O(N log² N) comparators, O(log² N) depth.
Core tile: INT32_COMPARE → bit → MUX pair. ~6-8 UniCells per compare-swap.
Scale: 8, 16, 32, 64, 256-way sorters by tiling.

### Odd-Even Transposition Sort
Simplest parallel sorter. Alternating odd/even pair compare-swaps.
Trivial wiring, trivial tiling, perfect for 1D arrays. Easiest to implement first.

### Shear Sort (2D)
Sort rows L→R, then R→L, then columns T→B, repeat log N times.
Natural fit for 2D UniCell grid. All local compare-swap.

### Parallel Radix Sort
1-bit, 4-bit, or 8-bit digit-wise. Bit extract + bucket + prefix + scatter.
Extremely fast in hardware.

---

## Wavefront / Spatial Algorithms

### Parallel Distance Field + BFS
```
dist = min(neighbour_dist + 1)
```
Computes Manhattan distance, Voronoi regions, medial axes, skeletons.
Then add path extraction: follow decreasing distances = hardware BFS/A*.

### Phase-Coupled Oscillators
Each cell is a tiny oscillator. Neighbours pull phase. Clusters synchronise.
Mesmerising wave interference patterns. Shows emergent synchronisation.

### Lenia / SmoothLife (continuous CA)
Continuous values, smooth kernels (3×3 or 5×5), sigmoid threshold.
Produces gliders, amoebas, swimming organisms.

---

## Unmixing / Scientific Computing

*(See WASSERSTEIN_DEMO.md for the personal one — handle with care)*

### NMF (Non-Negative Matrix Factorisation)
```
H ← H * (Wᵀ X) / (Wᵀ W H)
W ← W * (X Hᵀ) / (W H Hᵀ)
```
Elementwise multiply/divide + dot products. Local fan-in.
Used in: hyperspectral imaging, audio source separation, blind unmixing.

### PCA via Power Iteration
```
v ← A v
v ← v / ||v||
```
Row-wise dot products + normalisation. Beautiful convergence visualisation.

### K-Means Clustering
Parallel distance fields + argmin + centroid update.
Visually spectacular in 2D — Voronoi regions solidifying.

### Gradient Descent on a Field
```
x ← x - α ∇f(x)
```
∇f via local differences. Backbone of optimisation and machine learning.

### Markov Random Field (MRF)
Each cell holds a label. Neighbourhood smoothness energy.
Local energy comparison + local label update + parallel relaxation.
UniCell is ideal for this.

---

## Implementation priority (suggested order)

1. Heat equation — simplest, validates the math tile pattern
2. Odd-even sort — validates compare-swap tile
3. Distance field — validates wavefront propagation
4. Brian's Brain — validates 2-bit state + transition
5. Bitonic sort — full hardware sorter demo
6. Wave equation — visually stunning
7. Reaction-diffusion — the showstopper
8. Wasserstein transport — the personal one, when the time is right

---

*All demos deferred until PCIe bridge complete. Build order flexible.*
*v2.3 gate states throughout — GS_LATCH_IN=0x04000000 (bit 26).*

---

## Display Architecture — Stream to GPU

**Design principle:** UniCell does the computation. The GPU does the display.
Don't emulate what has had decades of development already.

```
UniCell array (FPGA)
      ↓  fired cells → (addr, value) pairs
   PCIe / xdma  (/dev/xdma0_user)
      ↓
   Python receiver  (cell_addr → pixel_x, pixel_y mapping table)
      ↓
   GPU texture / framebuffer  (OpenGL / Vulkan / CUDA)
      ↓
   Display
```

Each component does exactly one job:
- FPGA: local rules, fires values — never touches display
- PCIe: moves the stream — nothing else
- Python: address→pixel mapping — one lookup table
- GPU: renders pixels — what it was built for
- Display: shows the result

### Why this is correct

The GPU display stack (OpenGL/Vulkan/CUDA) has had decades of optimisation.
A 128×128 reaction-diffusion grid fires up to 16,384 cells per tick.
At 125MHz on Kintex-7 that's a torrent — PCIe x8 Gen1 handles it easily,
GPU composites a full frame faster than the eye can see.

No bottleneck. No wasted effort. No reinventing the framebuffer.

### Display pond update

The display pond becomes a simple address→pixel mapping table.
Not a rendering engine. The heavy lifting moves to the GPU where it belongs.

```python
# Minimal receiver sketch
def on_fire(addr, value):
    x, y = addr_to_pixel[addr]        # lookup table
    framebuffer[y][x] = value_to_colour(value)   # map to RGB
    # GPU picks up framebuffer as texture — done
```

### Per-demo colour mapping

| Demo | Mapping |
|------|---------|
| Heat equation | value → blue→white→red (temperature) |
| Wave equation | value → signed → blue/red phase |
| Reaction-diffusion | A,B values → hue rotation |
| Wasserstein transport | surplus → blue=deficit, red=excess, white=matched |
| Wavefront/Voronoi | src_id → colour, boundary → black |
| Bitonic sort | value → brightness (watch values settle) |

*Display pond deferred — implement after PCIe bridge complete.*
*Use OpenGL/Vulkan texture streaming, not a custom renderer.*
