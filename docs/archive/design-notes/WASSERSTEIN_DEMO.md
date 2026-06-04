# Wasserstein Transport Demo

*Recorded 2026-05-31. Personal — handle with care.*

---

## Context

This demo is connected to research by Alan's eldest son — his PhD thesis
on geometric unmixing with basis variation in Wasserstein geometry:

  https://livrepository.liverpool.ac.uk/3190542/

The thesis tackles the hardest version of the unmixing problem:
mixed data = basis patterns + arbitrary variations + arbitrary mixing,
solved geometrically in arbitrary metric spaces using Wasserstein distance.

Currently his algorithms run overnight on university systems for 200-300
sample datasets. The core operations are local, iterative, and parallel —
exactly what UniCell is built for.

This demo is intended as a gift: a hardware embodiment of his research,
showing the mathematics as a live physical process rather than a simulation.

*"You are not 'playing around' with a side project. You are building a
machine that naturally solves the same class of problems he spends all
night computing."*

*"You two are working on the same mountain from opposite sides."*

---

## What Wasserstein transport is

Moving mass locally between cells to match a target distribution,
minimising total transport cost. The system relaxes to the optimal
transport plan through purely local interactions.

This is not a metaphor for UniCell — it is exactly how UniCell works.

---

## Discrete model (1D, integer, local)

Each cell holds:
- `mass`    — current mass (INT32, 0–65535)
- `target`  — target mass (fixed, preloaded)
- `surplus` — mass - target (positive = send, negative = receive)

Per tick, local rule:
```
surplus_i = mass_i - target_i
if surplus_i > 0:
    flow_out = min(surplus_i, q)   # q = flow quantum per tick
else:
    flow_out = 0

mass_i_new = mass_i - flow_out + sum(neighbour_flow_in)
```

In 2D: same rule with N/E/S/W neighbours.

---

## UniCell tile structure (per cell)

### Tile A — Surplus computation
```
SURPLUS = MASS - TARGET
```
- INT32_ADDER in subtract mode
- MASS preloaded as A, TARGET as B (negated)
- latch_in on SURPLUS output

### Tile B — Flow decision
```
if SURPLUS > 0 → FLOW_OUT = q
else            → FLOW_OUT = 0
```
- INT32_COMPARE → 1-bit positive flag
- MUX: select between constant q and 0
- latch_in on FLOW_OUT

### Tile C — Mass update
```
MASS_NEW = MASS - FLOW_OUT + FLOW_IN
```
- Neighbours' FLOW_OUT arrive as two-arrival inputs
- Sum into FLOW_IN via INT32_ADDERs
- MASS_TMP = MASS - FLOW_OUT
- MASS_NEW = MASS_TMP + FLOW_IN
- latch_in on MASS_NEW

---

## Wiring

1D:
```
cell[i].FLOW_OUT_RIGHT → cell[i+1].FLOW_IN_LEFT
cell[i].FLOW_OUT_LEFT  → cell[i-1].FLOW_IN_RIGHT
```

2D:
```
cell[x][y].FLOW_OUT_N/E/S/W → corresponding neighbours' FLOW_IN
```

---

## What you will see

- Source region: high mass, positive surplus → mass flows outward
- Target region: low mass, negative surplus → mass flows inward
- Mass field relaxes tick by tick toward target distribution
- Convergence: MASS ≈ TARGET everywhere

Visualisation: map MASS to colour (blue=deficit, red=surplus, white=matched).
Watch mass flow as a physical process — not plotted, not animated, running.

---

## Why this matters for the research

The thesis algorithms are:
- local (neighbour interactions)
- iterative (repeated relaxation)
- parallel (all cells update simultaneously)

UniCell is exactly that. The CPU simulates the mathematics.
UniCell IS the mathematics.

Potential speedup: not 2×. Orders of magnitude. Overnight → seconds.

---

## Scalability

| Grid  | Cells (3 tiles each) | Target hardware |
|-------|---------------------|-----------------|
| 8×8   | 192                 | Kintex-7 (500-cell build) |
| 16×16 | 768                 | Kintex-7 (500-cell build) |
| 32×32 | 3072                | GPU VM |
| 64×64 | 12288               | GPU VM |

---

## Extensions (after basic demo works)

- Variable q proportional to |surplus| (faster convergence)
- Cost term penalising long-range moves
- Barycenter: multiple TARGET fields with weights
- Basis variation: TARGET field shifts spatially each tick
- Full geometric unmixing: multiple source distributions

---

## Next steps

- [ ] Implement 1D version in Python VM first
- [ ] Verify convergence behaviour and tick count
- [ ] Compare timing against equivalent numpy/scipy solver
- [ ] Port to PCIe when bridge complete
- [ ] Visualisation layer
- [ ] Write-up mapping thesis concepts to UniCell tiles

*Build when PCIe bridge is ready. This one deserves to be done properly.*
