"""
user_tile_loader_v1.py — loads a user-authored composed-tile definition
from a plain JSON file, per Alan (2026-08-16): "the design your own
tile system is the composer's job... but yes, it's a feature that needs
to be made part of the compiler side now, even just an open port via a
command line switch, 'use this model' kind of thing."

DELIBERATELY NARROW, matching what was actually asked for: this is NOT
the composer (Stage 5, a spatial/visual authoring surface -- real
project terminology, `points.md #20`, explicitly later work). This is
the plumbing that lets an externally-produced tile file -- hand-written
today, composer-exported later -- reach the compiler at all. The JSON
shape below is a direct, field-for-field mirror of
`composed_tile_library_v1.ComposedTileSpec`/`SubCellPlacement` (not a
new format invented for this) so a future composer export just needs to
produce this same shape, not a second thing this loader would also need
to understand.

Example file:
```json
{
    "name": "my_custom_tile",
    "description": "a user-authored composed tile",
    "subcells": [
        {"name": "acc", "offset": [0, 0], "tile_name": "accumulator",
         "internal_directions": {"out": "e"}},
        {"name": "cmp", "offset": [0, 1], "tile_name": "comparator",
         "internal_directions": {"in": "w"}}
    ],
    "external_ports": {
        "inc": ["acc", "inc"], "dec": ["acc", "dec"],
        "out": ["cmp", "out"]
    }
}
```
Only Tier-1 (composed) tiles are supported here -- a user-defined Tier-0
tile wouldn't mean anything (the 6 cores are fixed by the RTL itself,
`unicell_super_v1.v`'s own `core_select`), so there's nothing for a user
to define at that level.
"""

from __future__ import annotations

import json
from typing import List

from composed_tile_library_v1 import ComposedTileSpec, SubCellPlacement


def load_composed_tile(path: str) -> ComposedTileSpec:
    """Reads one JSON file, returns one real `ComposedTileSpec`. Raises
    `ValueError` with a plain-English reason on anything malformed --
    this is meant to be caught by `dsl_cli_v1.py` and reported the same
    way any other compile-time problem is, not to crash silently."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"model file not found: {path!r}")
    except json.JSONDecodeError as e:
        raise ValueError(f"model file {path!r} is not valid JSON: {e}")

    for required in ("name", "subcells", "external_ports"):
        if required not in data:
            raise ValueError(f"model file {path!r} is missing required key {required!r}")

    subcells: List[SubCellPlacement] = []
    for i, sc in enumerate(data["subcells"]):
        for required in ("name", "offset", "tile_name"):
            if required not in sc:
                raise ValueError(f"model file {path!r}: subcell #{i} is missing required key {required!r}")
        offset = sc["offset"]
        if not (isinstance(offset, list) and len(offset) == 2):
            raise ValueError(f"model file {path!r}: subcell {sc.get('name')!r}'s "
                              f"offset must be a 2-element [row, col] list, got {offset!r}")
        subcells.append(SubCellPlacement(
            name=sc["name"], offset=(offset[0], offset[1]), tile_name=sc["tile_name"],
            internal_directions=sc.get("internal_directions", {}),
        ))

    external_ports = {}
    for port_name, ref in data["external_ports"].items():
        if not (isinstance(ref, list) and len(ref) == 2):
            raise ValueError(f"model file {path!r}: external port {port_name!r} must "
                              f"map to a 2-element [subcell_name, subcell_port] list, got {ref!r}")
        external_ports[port_name] = (ref[0], ref[1])

    return ComposedTileSpec(
        name=data["name"],
        description=data.get("description", f"user-defined tile loaded from {path}"),
        subcells=subcells,
        external_ports=external_ports,
        target=data.get("target", "super-only"),
        proven=data.get("proven", "sim-only"),
    )
