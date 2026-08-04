# Compiler tile_config — Strategy Selection

*Added: 2026-06-07*

## Overview

The `tile_config` parameter lets frontends control which tile implementation
strategy the compiler uses, without touching compiler internals.

The compiler stays dumb. The frontend makes the choice.

---

## API

All three public compiler entry points accept `tile_config`:

```python
# Constructor form
compiler = Int32Compiler(
    tile_library=lib,
    tile_config={"MIF_DIV": "low_latency"}
)

# Convenience function
result = run_int32_function(
    source, function_name, operands, lib,
    tile_config={"MIF_DIV": "low_latency"}
)

# Load/run form (A preloaded, B injected later)
fn = load_int32_function(
    source, function_name, a_operands, lib,
    tile_config={"MIF_DIV": "const_divisor"}
)
result = fn.run(b_operands)
```

`tile_config` is a plain Python dict: `{tile_name: strategy_string}`.
Default is `None` or `{}` — all tiles use their standard strategy.
Fully backward compatible: all existing calls work without change.

---

## How it works

Internally, all tile lookups go through `_get_tile(name)`:

```python
def _get_tile(self, tile_name: str):
    strategy = self._tile_config.get(tile_name)
    if strategy is not None:
        return self._tile_library.get(tile_name, strategy=strategy)
    return self._tile_library.get(tile_name)
```

If `tile_name` is in `tile_config`, the strategy is passed to
`TileLibrary.get()`. Otherwise the library default is used.
Non-strategy tiles (MIF_ADD, INT32_ADD, etc.) silently ignore the
strategy parameter — safe to include unused keys in the config.

---

## Available strategies

Strategies apply to tiles that support them. Currently: MIF_DIV,
MIF_SQRT, MIF_RECIP. All other tiles ignore the strategy parameter.

| Strategy | Description |
|----------|-------------|
| `"auto"` | Default. Resolves to `cell_budget` now. Future: context-aware. |
| `"cell_budget"` | Digit-by-digit. Fewest cells, deep pipeline (~depth 1177). |
| `"low_latency"` | Newton-Raphson. More cells, ~half depth. Best for tight pipelines. |
| `"const_divisor"` | MIF_DIV only. Returns MIF_MUL — caller pre-computes 1/divisor. |

See `TileLibrary.strategies_for(tile_name)` for the full list per tile.

---

## Canonical frontend configs

These are the recommended tile_config values for each MathTrix demo type.
Other Trix frontends should define their own configs similarly.

```python
# Laplacian, wave, Ising, Conway — no DIV/SQRT, no config needed
MATHTRIX_STENCIL = {}

# Fast Marching — MIF_MIN only, no config needed
MATHTRIX_FAST_MARCHING = {}

# Gray-Scott — reaction terms use MUL not DIV, no config needed
MATHTRIX_GRAY_SCOTT = {}

# PageRank — degree is fixed at compile time, use const_divisor
MATHTRIX_PAGERANK = {
    "MIF_DIV": "const_divisor",
}

# N-body — pairwise DIV+SQRT are on the critical path, use low_latency
MATHTRIX_NBODY = {
    "MIF_DIV":  "low_latency",
    "MIF_SQRT": "low_latency",
}

# Boids — same as N-body (distance normalisation per pair)
MATHTRIX_BOIDS = {
    "MIF_DIV":  "low_latency",
    "MIF_SQRT": "low_latency",
}
```

---

## Writing a new Trix frontend

A new domain frontend (BioTrix, ChemTrix, AstroTrix, etc.) should:

1. Define its own `tile_config` dict based on its computational needs
2. Pass it to `run_int32_function` or `Int32Compiler` as usual
3. Not modify the compiler or tile library

```python
# BioTrix — sequence alignment with division for scoring
BIOTRIX_CONFIG = {
    "MIF_DIV": "low_latency",   # scoring normalisation on critical path
}

result = run_int32_function(
    alignment_source, "score", operands, lib,
    tile_config=BIOTRIX_CONFIG
)
```

The compiler is tile-config-agnostic. It applies whatever strategy the
frontend specifies, for whatever tiles appear in the compiled function.

---

## Future: auto strategy selection

The `strategy="auto"` value in `TileLibrary.get()` is reserved for
context-aware selection. When the MathTrix pattern matcher is built, it
will inspect the surrounding expression graph:

- How deep is the surrounding pipeline?
- How many cells does this pond have remaining?
- How many times does this division appear in the loop?

Based on that analysis, it will populate `tile_config` automatically
instead of the frontend supplying it by hand. No compiler changes needed:
the calling code already passes `tile_config`, only the value changes from
hand-coded to computed.

---
*See also: MIF_FORMAT.md, fp_tiles.py (_STRATEGY_BUILDERS, _STRATEGY_DOCS)*

---

## CANONICAL COMPILER/PLACER RULE: pentacross placement (2026-07-07)

This is a standing rule the placer MUST apply to every model, not a property of
any one model. It was derived building the routing_mask packed shift-adder
(points.md #14, #16, #17) and verified to resolve the placement constraint
problem that brute-force search could not.

### The rule

A cluster is a plus-pentomino (Greek cross): a centre cell plus four cardinal
arm tips (N/S/E/W). Placement of a model's cells into clusters follows:

1. **Only arm tips cross boundaries.** A cell that must SEND a value across a
   cluster boundary is placed on the arm facing its receiver; the RECEIVER is
   placed on the arm of its cluster facing the sender. Sender and receiver are
   arm-tenants, pointing at each other.

2. **routing_mask is simultaneous multicast, not pick-one.** The four
   routing_mask bits (cmd_latch[14:11], one per cardinal) all fire in the same
   event. One arm cell's single fire pushes to several cardinal directions at
   once. A producer reaching multiple clusters therefore needs NO relay chain
   and NO serial re-firing -- it sets several bits in one fire.

3. **Internal (non-crossing) cells are free.** A cell that only talks to others
   in its own cluster can occupy any free slot (centre or an unused arm),
   ordered only by the computation's stage sequence, not by geometry.

4. **KEY RULE -- fan-out/checkpoint cells ride their producer, never a hub.**
   A cell whose job is to hold or forward a value to multiple consumers
   (checkpoints, fan-out relays) is placed in the SAME cluster as the cell that
   PRODUCES its value, and multicasts to its consumers via routing_mask. It is
   NEVER pooled with other such cells into a shared "hub" cluster. Pooling them
   concentrates fan-out into one cluster and blows the 4-cardinal port limit
   (verified: pooling the adder's REQ cells drove one cluster to 11 required
   neighbours; riding-the-producer dropped max neighbours to 3).

### Why it works

These rules convert the port-degree constraint from a GLOBAL emergent property
(only discoverable after placing everything -- which defeats greedy placement
and makes backtracking expensive) into a LOCAL, per-cluster check ("does this
cross have a free arm facing the right way?"). Placement then falls out of the
dataflow graph's own structure with no search. Verified on the packed adder:
12 clusters, 37 cells, all constraints satisfied, 10000/10000 correct with zero
same-cluster collisions in the event-driven placement simulator.

### Placer obligations (checklist)

- [ ] Group cells so no two cells of the same dataflow DEPTH share a cluster
      (they would fire the same cycle -> local wired-OR bus collision).
- [ ] Keep each cluster <= 5 cells (the pentomino has 5 slots).
- [ ] Keep each cluster's distinct-neighbour count <= 4 (four cardinal arms).
- [ ] Place every cross-boundary sender/receiver on facing arm tips.
- [ ] Place fan-out/checkpoint cells with their producer; express their reach
      as routing_mask bits, not extra relay cells.
- [ ] Validate the result in the event-driven sim (two-arrival firing +
      one-transaction-per-cluster-per-cycle + simultaneous multicast) BEFORE
      generating RTL.

*See also: points.md #14/#16/#17, VERILOG_SPEC.md (routing_mask / METH_SET_ROUTING),
and the event-driven placement simulator.*

---

## PLACER REFINEMENT: physical mesh embeddability + transit for long-range edges (2026-07-07)

Revisiting the pentacross placement rule on the completed substrate (transit
primitive built, points.md #18) surfaced a real gap in the original rule and its
resolution.

### The gap

The pentacross rule as first written checked neighbour COUNT (<=4 cardinal) and
same-depth collision-freedom. Those are necessary but NOT sufficient: a cluster
adjacency graph can have max-degree <=4 and still fail to embed on a physical
NSEW mesh, where each cluster has four specific cardinal slots and neighbours
must occupy distinct directions without the connections needing to cross
non-adjacent clusters. The placer must additionally check EMBEDDABILITY: can the
cluster graph be laid on a 2D grid with every dataflow edge at unit (NSEW-
adjacent) distance?

### The resolution (verified on the packed adder)

1. **Interleaved embedding.** For a two-chain structure like the adder (a P-spine
   and a G-spine linked by per-stage rungs), place each cluster of one chain
   DIRECTLY ADJACENT to its rung-partner in the other chain -- e.g. P-cluster k
   in the row above G-cluster k. This makes all the per-stage rung edges
   unit-distance simultaneously, which a naive "one chain per row, in order"
   layout does not (its rungs span the inter-row gap). On the adder this took the
   non-unit edges from 6 down to 1.

2. **Transit for the genuine long-range edge.** After a good embedding, any edge
   that STILL spans distance is a genuinely long-range connection -- a value that
   must travel from one end of the computation to the other. On the adder exactly
   one such edge remains: REQ1 -> SUM_XOR (the P0 low-bit carried from chain start
   to the final sum XOR, structurally start-to-end and unavoidable). This is
   handled by a TRANSIT PATH (points.md #18): the value routes THROUGH the
   intervening clusters' spare arms via transit cells (route-across-only, never
   presenting locally), reaching the far cluster without demanding direct
   physical adjacency. This is the transit primitive's first real use, arising
   organically from the placement rather than contrived.

### Placer obligation (added to the #17 checklist)

- [ ] After grouping and neighbour-count checks, EMBED the cluster graph on a 2D
      NSEW grid. Use interleaved placement for paired chains so rung edges are
      unit-distance.
- [ ] Any edge that remains non-unit after a good embedding is a long-range edge:
      route it via a TRANSIT PATH (transit cells through intervening clusters'
      spare arms), not by demanding adjacency. Verify the transit path's safety
      condition (points.md #18: suppress-local on exit, address unique to each
      pass-through cluster, free bus cycle there).

The two capabilities compose: pentacross placement + interleaved embedding
minimise and localise crossings; the transit primitive handles the residual
genuinely-long edges. Neither alone places the adder on a real mesh; together
they do.
