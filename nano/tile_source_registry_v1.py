"""
tile_source_registry_v1.py — the real, generic "hook" mechanism
(points.md #485) letting the compiler grow new, dedicated tile
("model") libraries -- each targeting its own real output record
shape -- WITHOUT rewriting `dsl_compiler_v1.py`'s own resolve/place/
emit logic every time. Per Alan's own direct request ("a dsl library,
and a model library both to can be hooked/used by the compiler...
allows them to expand without having to rewrite the entire compiler
each time"): a new tile library module registers ONE `TileSource`
here, at its own import time, and the compiler's top-level `place`
resolution (`dsl_compiler_v1.py`'s own `_resolve_and_place()`) walks
this registry generically via `find_source_for()` -- it has no
per-kind knowledge baked into its own control flow at all.

DELIBERATE, NARROW CONTRACT (kept intentionally tiny, on purpose --
the whole point is that a new kind never needs this file to change):
`library` is any object exposing `names()`/`get(name)` (every real
tile library in this codebase already shares this shape --
`SuperTileLibrary`, `DspWrapperTileLibrary`, `ComposedTileLibrary`).
`place_fn` matches the real, established `place(tile, row, col,
port_directions, params, cell_id=...) -> record` signature every
Tier-0-shaped `place()` function in this codebase already uses -- ONE
record per call, not a list. `bucket` names which real output list a
resolved record belongs in when the final mixed program gets
assembled (`icm_v4.IcmV4File`'s own `super_records`/`dsp_wrapper_
records` field names).

REAL, DELIBERATE SCOPE, stated honestly: this registry covers
TOP-LEVEL `place` statement resolution only. Tier-1 composed tiles
(`define`/`place_composed()`) remain super-tile-only sub-cells for
now -- `place_composed()` itself (`composed_tile_library_v1.py`) still
only knows how to emit `IcmV3Record`s, so a `define` block cannot yet
mix a DSP-wrapper (or any future non-super kind) primitive in as a
sub-cell. This is real, separate, unbuilt future work, flagged plainly
here rather than silently half-supported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class TileSource:
    kind: str
    library: object
    place_fn: Callable
    bucket: str


_SOURCES: List[TileSource] = []


def register_tile_source(source: TileSource) -> None:
    if any(s.kind == source.kind for s in _SOURCES):
        raise ValueError(f"tile source kind {source.kind!r} already registered")
    _SOURCES.append(source)


def all_sources() -> List[TileSource]:
    return list(_SOURCES)


def find_source_for(tile_name: str) -> Optional[TileSource]:
    """First real registered source (REGISTRATION order) whose
    library has a tile by this name -- registration order acts as
    real, simple precedence, the same "check order decides precedence"
    convention `place_composed()` already uses elsewhere (composed
    checked before Tier-0), not a new one invented here."""
    for source in _SOURCES:
        if tile_name in source.library.names():
            return source
    return None


def all_known_tile_names() -> List[str]:
    names = set()
    for source in _SOURCES:
        names |= set(source.library.names())
    return sorted(names)
