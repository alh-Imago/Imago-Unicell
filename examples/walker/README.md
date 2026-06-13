# Tile Walker

`walk_tiles.py` expands UniCell tiles — or your own models — into raw `.icm`
files you can load directly into the composer
(`composer/unicell_composer.html` → **load**) to see their cell-level format
and wire them into larger designs.

## Why a walker, not a static dump

The composer already loads raw `.icm`, so embedding every tile in the HTML
would just bloat it (the FP/MIF tiles especially). A walker ships the *tool*
instead: generate exactly what you want, when you want — the built-in tiles, a
subset, or **your own** tile builder — and regenerate after any change.
Static example files go stale; a walker doesn't.

## Usage

```bash
# functional tiles -> examples/tiles/  (handlers skipped, see below)
python3 examples/walker/walk_tiles.py

# see what would be emitted, with cell counts and depths
python3 examples/walker/walk_tiles.py --list

# a single tile
python3 examples/walker/walk_tiles.py --tile MIF_MUX

# only the small ones (e.g. under 1000 cells)
python3 examples/walker/walk_tiles.py --max-cells 1000

# include the big I/O handler tiles too
python3 examples/walker/walk_tiles.py --all

# expand YOUR OWN tile: a no-arg builder returning a Tile
python3 examples/walker/walk_tiles.py --builder mymodule:make_my_tile

# expand a whole LIBRARY FILE of builders (the fp_tiles.py way) in one go
python3 examples/walker/walk_tiles.py --module examples/walker/example_user_models.py
```

## Two authoring routes

This is the lower-level of two ways to reach an `.icm`:

- **Compiler route** — write a high-level program; the compiler lowers it
  through `fp_tiles` to an `.icm`. For full programs.
- **Builder route (this)** — hand-craft tiles with the `NORBuilder`
  primitives, the same way `fp_tiles.py` builds the built-ins, then the walker
  emits the `.icm` directly. A whole file of `make_*` builders becomes a
  portable model library (`--module`), and that `.py` is itself shareable.
  See `example_user_models.py` for the pattern.

## record_hash

Every emitted `.icm` carries a `record_hash` (SHA-256 over the canonical
records), computed to match the composer's `canonR` exactly — fields
`{gs, in, init, out}` in that order, no whitespace. So the strict/runtime
loader accepts the file and the composer verifies it clean ("hash verified ✓")
rather than warning "no hash".

## What it emits by default

The **functional** tiles: arithmetic (`INT32_ADD`, `MIF_ADD`, `MIF_MUL`, …),
compare (`MIF_CMP_*`), select (`INT32_MUX`, `MIF_MUX`), shifts, counters, and
latches. The large I/O **handler** tiles (`DISPLAY_HANDLER` ≈ 18,600 cells,
audio/keyboard/network/storage/sensor) are skipped — they're big, not useful
as building blocks, and would only bloat the repo. Pass `--all` to include
them. The deprecated `INT32_ADD_CLA` is also skipped (use `INT32_ADD`).

The bulk output directory (`examples/tiles/*.icm`) is git-ignored — generate
locally rather than committing it. A few committed samples live in
`examples/tiles/samples/`.

## Format note

Each `.icm` captures the tile's NOR-cell network (gates, addresses, i/o) and
loads into the composer as an inspectable grid of cells. Tiles built from
preloaded-A selection (the MUX family) also carry a `preload_map`, but preload
resolution happens at composition/run time — so a `.icm` here is faithful for
**inspection and wiring**, and a lone tile is a *building block*, not a
standalone runnable program (it needs inputs fed).
