# Tile `.icm` examples

Raw `.icm` files for individual tiles — load them into the composer
(`composer/unicell_composer.html` → **load**) to see a tile's cell-level format
and wire it into a design.

## Generate them

These are produced by the walker, not committed in bulk (that would bloat the
repo). To populate this directory:

```bash
python3 examples/walker/walk_tiles.py            # the functional tile set
python3 examples/walker/walk_tiles.py --list     # see what's available first
python3 examples/walker/walk_tiles.py --tile MIF_DIV   # one big one on demand
```

Generated `*.icm` here are git-ignored (see `.gitignore`).

## Samples

`samples/` holds a small committed palette so you can load one immediately
without running anything: `INT32_ADD`, `INT32_MUX`, `MIF_MUX`, `MIF_CMP_LT`.

## Sharing

A raw tile `.icm` is a model *outside* the Trix format system (no
`FormatDefinition`, no domain). The community pathway is being extended to let
these be registered and exchanged alongside Trix-domain contributions — see
the "non-Trix community exchange" note in `PLAN.md`.
