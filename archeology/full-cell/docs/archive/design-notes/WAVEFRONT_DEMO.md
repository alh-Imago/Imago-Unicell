# Wavefront / Voronoi Demo — Parallel Spatial Computation

*Recorded 2026-05-31. Design concept from cross-AI collaboration.*
*A parallel demo that is UniCell-native — not a cvN simulation.*

---

## The concept

A 2D UniCell fabric where multiple wavefronts spread from source points
simultaneously, collide, and the collision boundaries form naturally from
local cell interactions alone. No global controller. No loops. No program
counter.

Think: Voronoi diagram computed in parallel in hardware.
Think: Go board territory, but the fabric IS the board.

Why this is UniCell-native:
- Every cell participates — not a few ALUs, the whole fabric
- Local rules only — no global state, no central authority  
- Wavefront propagation — pure two-arrival logic
- Emergent boundaries — not computed top-down, formed bottom-up
- Massively parallel — all active cells fire in the same tick
- Spatial computation — the board IS the program

A cvN machine must simulate this with nested loops, arrays, turn-based
updates, global state scans. UniCell just IS the computation.

---

## Single cell logic (Python — the repeatable rule)

Each cell holds: dist (distance from nearest source), src (source ID),
active (claimed or not).

```python
def update_cell(dist, src, active, neighbours):
    """
    neighbours = list of (n_dist, n_src)
    Local rule only — no global knowledge needed.
    """
    if not active:
        # Unclaimed — look for nearest neighbour
        best = None
        for n_dist, n_src in neighbours:
            if n_dist is None:
                continue
            cand = n_dist + 1
            if best is None or cand < best[0]:
                best = (cand, n_src)
        if best is not None:
            return best[0], best[1], True
        return dist, src, active

    # Already claimed — check for closer wave or collision
    best_dist = dist
    best_src  = src
    for n_dist, n_src in neighbours:
        if n_dist is None:
            continue
        cand = n_dist + 1
        if cand == best_dist and n_src != best_src:
            return best_dist, -1, True   # boundary — two sources tie
        if cand < best_dist:
            best_dist = cand
            best_src  = n_src
    return best_dist, best_src, True
```

---

## UniCell mapping — 3 cells per logical grid cell

```
Cell 0: DIST_IN   — PASS topology, receives neighbour distance
Cell 1: DIST_ADD1 — XOR with preloaded 0x00000001, LATCH_IN
Cell 2: SRC_LATCH — PASS with LATCH_IN, holds source ID
```

### Gate states (v2.3 corrected bit positions)

| Cell | Role | gate_state | Notes |
|------|------|-----------|-------|
| 0 | DIST_IN | `GS_PASS = 0x000` | Pure pass, no latch |
| 1 | DIST_ADD1 | `GS_XOR \| GS_LATCH_IN = 0x040000BC` | XOR(dist, 1) = dist+1 for low bits |
| 2 | SRC_LATCH | `GS_PASS \| GS_LATCH_IN = 0x04000000` | Holds source ID |

**v2.3 note:** `GS_LATCH_IN = 0x04000000` (bit 26). The other AI's
examples used `0x02000000` (old bit 25) — corrected above.

### Preload (preload_sel or init value)

Cell 1 needs `a_data = 0x00000001` preloaded (the constant to XOR with).
This is NOT one of the two standard preload_sel constants (0x00 or 0xFF).
Use CMD_RECONFIGURE with the init field, or a direct data injection during
the freeze/configure phase.

**Note:** XOR(dist, 1) only gives dist+1 for the lowest bit — it toggles
bit 0. For a true increment across all bits, use the INT32_ADDER tile
(19 cells, packed shift-chain) with preloaded A=1. For small distance values (0-15)
the nibble approach works and is much cheaper.

### Wiring pattern (address layout)

For a logical grid cell at position (x, y):

```
cell[x][y].dist_out → cell[x-1][y].dist_in  (West)
cell[x][y].dist_out → cell[x+1][y].dist_in  (East)
cell[x][y].dist_out → cell[x][y-1].dist_in  (North)
cell[x][y].dist_out → cell[x][y+1].dist_in  (South)

cell[x][y].src_out  → same four neighbours' src_in
```

Each cell listens on one input_address. Neighbours write to it.
Fan-out handled by sending the same output to multiple addresses
(one DATA_WRITE per neighbour direction).

---

## Scalability

| Grid | Logical cells | UniCells (3/cell) | Notes |
|------|-------------|------------------|-------|
| 8×8 | 64 | 192 | iCEBreaker: no (4 cell limit) |
| 8×8 | 64 | 192 | Kintex-7 100-cell: partial |
| 16×16 | 256 | 768 | Kintex-7 100-cell: no |
| 16×16 | 256 | 768 | Kintex-7 500-cell: yes |
| 32×32 | 1024 | 3072 | Large FPGA / GPU VM |
| 128×128 | 16384 | 49152 | GPU VM |

For iCEBreaker bring-up: test a single cell (3 UniCells), verify
dist+1 propagation and src latch, then scale.

---

## What to test immediately

1. Single cell: preload dist=0, inject src=1, verify dist_out=1, src_out=1
2. Two cells in chain: verify dist propagates as 0→1→2
3. Two sources: inject from opposite corners, verify boundary cell fires
   with src=-1 (boundary marker)
4. 8×8 on Kintex-7: watch wavefronts in cycle count timing

---

## Why this demo matters

This is the program that makes people stop saying "ALU pieces in a line."

It cannot be expressed linearly. It requires a spatial, reactive fabric.
A cvN machine must fake it with loops. UniCell just runs it.

The Go analogy is apt: local rules, global consequences, territory
emerging from interactions, boundaries forming where forces collide.
But UniCell doesn't simulate Go — it IS the game board.

---

## Next steps

- [ ] Implement single-cell test in bringup_v23.py
- [ ] Wire 8-cell chain test (2×4 grid)
- [ ] PCIe injection harness for source placement
- [ ] Visualisation: map src_id → colour, stream boundary cells to host
- [ ] Scale to Kintex-7 500-cell build

*Parked 2026-05-31. Build after PCIe bridge is complete.*
