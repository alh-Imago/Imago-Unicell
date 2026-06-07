# MIF — MathTrix Internal Float

*Added: 2026-06-07*

## Overview

MIF (MathTrix Internal Float) is a floating-point working format used
exclusively within MathTrix computation regions. It is **not** a general
replacement for IEEE-754 — it is a pipeline-internal optimisation.

**IEEE-754 is the wire format at region boundaries.**
MIF pairs flow through all internal arithmetic without repacking.

```
User / hardware input
        │
   MIF_UNPACK  ← boundary, paid once per region input
        │
   MIF_ADD ─── MIF_MUL ─── MIF_MADD ─── MIF_CMP_LT ─── ...
        │
   MIF_PACK    ← boundary, paid once per region output
        │
User / hardware output
```

---

## Format — the MIF pair

Each MIF float is two 32-bit cells travelling together as a matched pair:

### Control cell [31:0]

```
[31:24]  exponent   8 bits, 2 nibbles — biased-127, same encoding as IEEE-754
[23]     sign       1 bit  — 0=positive, 1=negative
[22]     is_nan     1 bit  — special flag
[21]     is_inf     1 bit  — special flag
[20]     is_zero    1 bit  — special flag
[19:16]  guard      4 bits — round/sticky bits (reserved, future use)
[15:0]   unused     zero
```

### Mantissa cell [31:0]

```
[23:0]   significand  24 bits — implicit-1 always expanded (bit 23 = 1 for normal)
[31:24]  unused       zero
```

### Why this layout

- **Exponent on nibble boundary** — the cell's native nibble granularity
  aligns with the field boundary. Exponent read/compare = nibble select,
  no shift-and-mask logic.
- **Sign + flags in one nibble** — [23:20] is one nibble. All control
  decisions (sign, NaN, Inf, zero) are in a single ctrl-cell nibble read.
- **Mantissa cell untouched for routing** — operations that only need the
  exponent or sign (comparisons, branching, routing decisions) never fire
  the mantissa cell. The pair travels together; only the needed cell fires.
- **Implicit-1 always expanded** — no pack/unpack of the significand within
  a computation chain. The 24-bit mantissa is always ready for arithmetic.

---

## Tile family (19 tiles)

### Boundary tiles — paid once per region

| Tile        | Cells | Depth | Notes |
|-------------|-------|-------|-------|
| MIF_UNPACK  |    74 |    25 | IEEE-754 FP32 → MIF pair. Detects NaN/Inf/zero, expands implicit-1. |
| MIF_PACK    |   126 |     4 | MIF pair → IEEE-754 FP32. Re-encodes specials, drops implicit-1. |

### Arithmetic tiles

| Tile        | Cells | Depth | Notes |
|-------------|-------|-------|-------|
| MIF_ADD     |   814 |    79 | FP add. Wired-OR barrel (240c/barrel, theoretical minimum). |
| MIF_SUB     |   810 |    79 | A-B = negate B sign (1 cell) + MIF_ADD. |
| MIF_MUL     |  3066 |    89 | FP multiply. 24×24 partial products. |
| MIF_MADD    |  3875 |   107 | Fused A×B+C. MUL result stays MIF, feeds ADD with no mid-pack. |
| MIF_NEG     |     1 |     1 | Flip ctrl[23]. Starkest MIF win: IEEE needs full decompose. |
| MIF_ABS     |     0 |     0 | Force ctrl[23]=0. Pure wiring — zero logic cells. |
| MIF_DIV     |  4789 |  1177 | 24-stage restoring binary long division. See strategy variants. |
| MIF_SQRT    |  5317 |  1177 | 24-stage digit-by-digit DDSRT. See strategy variants. |

### Comparison tiles — operate on ctrl cell, no mantissa needed

| Tile        | Cells | Depth | Notes |
|-------------|-------|-------|-------|
| MIF_CMP_EQ  |    98 |    26 | A == B. Compare sign + exp + mantissa. |
| MIF_CMP_LT  |   212 |    56 | A < B. Signed. Exponent compare on ctrl cell first. |
| MIF_CMP_GT  |   212 |    56 | A > B. CMP_LT with operands swapped. |
| MIF_CMP_LE  |   213 |    57 | A <= B. NOT(CMP_GT). |
| MIF_CMP_GE  |   213 |    57 | A >= B. NOT(CMP_LT). |

### Selection tiles

| Tile        | Cells | Depth | Notes |
|-------------|-------|-------|-------|
| MIF_MIN     |   468 |    59 | Inline CMP_LT + 64-bit pair MUX. Output is full MIF pair. |
| MIF_MAX     |   468 |    59 | Inline CMP_GT + 64-bit pair MUX. |

---

## Strategy variants for MIF_DIV and MIF_SQRT

The default digit-by-digit tiles (depth 1177) are correct and cell-efficient.
Newton-Raphson variants offer much shallower depth at higher cell cost.

Access via `TileLibrary.get(name, strategy=...)`:

```python
lib.get("MIF_DIV")                           # cell_budget default: 4789c, depth 1177
lib.get("MIF_DIV",  strategy="low_latency")  # NR: 23916c, depth 536
lib.get("MIF_DIV",  strategy="const_divisor")# → MIF_MUL: 3066c, depth 89
lib.get("MIF_SQRT", strategy="low_latency")  # NR: 42325c, depth 818
lib.get("MIF_RECIP",strategy="low_latency")  # 1/B only: 20850c, depth 489
```

### Strategy selection guide

| Use case | Strategy | Why |
|----------|----------|-----|
| Single division per timestep (Laplacian, wave) | `cell_budget` | depth irrelevant, save cells |
| N-body pairwise forces (many DIV+SQRT per step) | `low_latency` | depth matters for pipeline throughput |
| PageRank degree (fixed at compile time) | `const_divisor` | becomes a MIF_MUL, cheapest possible |
| Convergence ratio (computed once, not on critical path) | `cell_budget` | save cells |
| Tight iterative pipeline where DIV is gating | `low_latency` | halve the depth bottleneck |

### NR convergence

Newton-Raphson for 1/B: `x_{n+1} = x_n × (2 - B × x_n)`
Starting guess from exponent negation on ctrl cell (~1 bit accuracy).
3 iterations → 24-bit precision (quadratic convergence).

Newton-Raphson for 1/√B: `x_{n+1} = x_n × (1.5 - 0.5 × B × x_n²)`
Starting guess from exponent halving (~1 bit accuracy).
3 iterations → 24-bit precision.

---

## Compiler integration — tile_config

Frontends pass `tile_config` to the compiler without touching internals:

```python
from compiler_int32 import run_int32_function
from fp_tiles import TileLibrary

lib = TileLibrary()

# Standard — no config needed
result = run_int32_function(src, 'stencil', ops, lib)

# N-body: fast pairwise forces
result = run_int32_function(src, 'force', ops, lib,
    tile_config={"MIF_DIV": "low_latency", "MIF_SQRT": "low_latency"})

# PageRank: degree known at compile time
result = run_int32_function(src, 'rank_step', ops, lib,
    tile_config={"MIF_DIV": "const_divisor"})
```

The compiler's `_get_tile(name)` method applies tile_config transparently.
Any tile name not in tile_config uses the library default.
Non-strategy tiles (MIF_ADD, MIF_MUL, etc.) ignore the strategy parameter.

**Future:** MathTrix pattern matcher will auto-populate tile_config from
expression analysis (chain depth, cell budget, operation count).
The `strategy="auto"` hook in `TileLibrary.get()` is the landing point.
No compiler changes needed when this lands.

---

## Design rationale

### Why not just use IEEE-754 throughout?

In a MathTrix computation chain, every intermediate result in IEEE-754
format is an opaque 32-bit word. To branch on the sign, compare two values,
or detect overflow mid-chain, you need a full FP comparison tile that
internally decomposes the packed word first.

In a MIF chain, the exponent and sign are sitting on the ctrl cell **at every
wire point in the fabric**. Branching on sign is a single AND gate on ctrl[23].
Exponent comparison for sorting or ordering costs no decompose step.

### Why not a completely new cell design?

The cell hasn't changed. MIF is purely a software convention about how to
pack and interpret the 32-bit values in the two cells of a matched pair.
The same UniCell hardware runs MIF and IEEE-754 identically — the difference
is only in what values the compiler and runtime load into the cells.

### MIF_ABS and MIF_NEG at 0 and 1 cells

These are the clearest demonstration of the architectural advantage. In
IEEE-754, negating a float requires: decompose → flip sign bit → repack.
In MIF, the sign bit is ctrl[23] — directly accessible with a single NOT.
ABS is even cheaper: wire ctrl[23] to a constant zero. No gate needed.

### Wired-OR barrel shifter

The barrel shifter inside MIF_ADD uses the wired-OR bus natively:

```
Cell A: AND_V2(a_data=sel,  B=src[i-amount]) → out[i]
Cell B: AND_V2(a_data=nsel, B=src[i]       ) → out[i]
```

Both cells write to the same `out[i]` address. The bus OR combines them.
When sel=1: Cell A passes shifted source, Cell B writes 0 (harmless).
When sel=0: Cell A writes 0 (harmless), Cell B passes current source.

Cost: 2 cells per bit per stage — theoretical minimum for a conditional shift.
No NOT gate needed (nsel preloaded alongside sel).

---

## MathTrix demo coverage

All 9 MathTrix demos use MIF format throughout:

| Demo | Key MIF tiles | Physics |
|------|--------------|---------|
| 1D Laplacian | ADD, SUB, MADD | Heat diffusion |
| 2D Laplacian | ADD, SUB, MADD | Radial diffusion |
| Ising model | ADD, CMP_LT | Domain coarsening |
| Fast Marching | MIN | Geodesic wavefront |
| Gray-Scott | MUL, MADD | Turing patterns |
| Wave equation | ADD, SUB, MADD | Gaussian pulse |
| PageRank | DIV (const_divisor) | Graph diffusion |
| N-body | SQRT, DIV (low_latency) | Gravity clustering |
| Boids | SQRT, DIV, MADD | Flocking |
| Continuous Conway | MADD, SUB | Smooth Game of Life |

---

## Usage outside MathTrix

MIF tiles are available for use outside MathTrix with caution. The
ctrl+mant pair convention must be maintained throughout — you cannot mix
IEEE-754 words and MIF pairs on the same bus addresses without explicit
UNPACK/PACK boundaries.

Appropriate uses:
- Any FP computation chain where the same float value is used multiple times
- Pipelines where mid-chain sign or magnitude comparisons are needed
- Domains where ABS/NEG appear frequently (signal processing, physics)

Inappropriate uses:
- Single isolated FP operations (boundary cost exceeds savings)
- Mixed INT32/FP pipelines (type confusion risk)
- Contexts where the pair convention cannot be enforced by the frontend

---
*See also: fp_tiles.py (implementation), mathtrix_laplacian_1d_mif.py (reference demo)*
