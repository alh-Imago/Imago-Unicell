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
