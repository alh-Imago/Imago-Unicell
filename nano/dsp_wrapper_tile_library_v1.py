"""
dsp_wrapper_tile_library_v1.py — a real, dedicated tile ("model")
library for the DSP wrapper family (`icm_v4.DspWrapperRecord`),
mirroring `super_tile_library_v1.py`'s own Tier-0 named-port/param
pattern deliberately, so `tile_source_registry_v1.py`'s generic
resolver can treat both libraries THE SAME WAY (points.md #485) --
this file is the real, concrete proof that the registry hook actually
works for a second kind, not just the original super-cell one.

WHY A SEPARATE LIBRARY, NOT A NEW `super_tile_library` ENTRY: DSP
wrapper cells are a real, deliberate, SEPARATE hardware class from
`unicell_super_v1.v` (`#453`/`#474`) -- no `core_select` value, no
`IcmV3Record` shape at all (`icm_v4.py`'s own module docstring). Their
real port shape also genuinely differs: `a_dir`/`b_dir` are real,
DISTINCT SINGLE cardinal directions each (`DspWrapperCell.__post_
init__`'s own real `a_dir != b_dir` constraint) -- never a dirmask a
port can fan out across, unlike `downstream_mask`/`upstream_mask` on
every super-cell core. Reusing `super_tile_library_v1.py`'s own
generic field-grouping resolver would either silently allow an
illegal multi-direction `a_dir`, or need DSP-wrapper-specific
special-casing bolted onto that already-proven, already-tested
module -- a small, honest, parallel library with its own resolve
logic suited to its own real constraint is the more honest choice.

`TilePort` itself IS reused directly from `super_tile_library_v1.py`
-- the named-port SHAPE (name/kind/field) is genuinely the same idea
here, only the resolve function underneath needs to differ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import icm_v4 as v4
from dsp_wrapper_automaton_v1 import ALL_OPS
from super_tile_library_v1 import TilePort


def _default_ports() -> List[TilePort]:
    return [
        TilePort("in_a", "in", "a_dir"),
        TilePort("in_b", "in", "b_dir"),
        TilePort("out", "out", "downstream_mask"),
    ]


@dataclass
class DspWrapperTileSpec:
    """One DSP wrapper tile -- a fixed real `op`, named ports over
    `icm_v4.DspWrapperRecord`'s own real fields. `watchdog_threshold`
    is the one real OPTIONAL param (omit it, or pass `None`
    explicitly, to leave the watchdog disabled -- matches
    `DspWrapperCell`'s own real default)."""
    name: str
    op: str
    description: str
    ports: List[TilePort] = field(default_factory=_default_ports)
    param_names: List[str] = field(default_factory=lambda: ["watchdog_threshold"])
    proven: str = "sim-only"   # matches dsp_wrapper_timing.md's own real proven/sim-only vocabulary

    def __post_init__(self) -> None:
        if self.op not in ALL_OPS:
            raise ValueError(f"DspWrapperTileSpec {self.name!r}: unknown op {self.op!r} "
                              f"-- real, confirmed ops are {sorted(ALL_OPS)}")

    def port_names(self) -> List[str]:
        return [p.name for p in self.ports]


def _single_dir(tile_name: str, port_name: str, raw) -> str:
    if isinstance(raw, (list, tuple, set)):
        raise ValueError(
            f"tile {tile_name!r}: port {port_name!r} must be a single real cardinal "
            f"direction, not a list -- only 'out' can fan out (matches DspWrapperCell's "
            f"own real, single-direction a_dir/b_dir constructor fields)"
        )
    d = str(raw).lower()
    if d not in ("n", "s", "e", "w"):
        raise ValueError(f"port {port_name!r}: direction must be n/s/e/w, got {raw!r}")
    return d


def place(tile: DspWrapperTileSpec, row: int, col: int,
          port_directions: Dict[str, object], params: Optional[dict] = None,
          cell_id: Optional[str] = None) -> "v4.DspWrapperRecord":
    """Resolve a DSP wrapper tile + a chosen direction per port + any
    params into one real `icm_v4.DspWrapperRecord`. Same real
    `(tile, row, col, port_directions, params, cell_id=...) -> record`
    call shape `super_tile_library_v1.place()` already uses -- the
    contract `tile_source_registry_v1.TileSource.place_fn` expects."""
    declared = set(tile.port_names())
    given = set(port_directions.keys())
    if declared != given:
        missing = declared - given
        extra = given - declared
        raise ValueError(
            f"tile {tile.name!r}: port directions mismatch"
            + (f", missing {sorted(missing)}" if missing else "")
            + (f", unexpected {sorted(extra)}" if extra else "")
        )

    params = params or {}
    unknown_params = set(params) - set(tile.param_names)
    if unknown_params:
        raise ValueError(f"tile {tile.name!r}: unknown param(s) {sorted(unknown_params)} "
                          f"(expected {sorted(tile.param_names)})")

    a_dir = _single_dir(tile.name, "in_a", port_directions["in_a"])
    b_dir = _single_dir(tile.name, "in_b", port_directions["in_b"])
    if a_dir == b_dir:
        raise ValueError(f"tile {tile.name!r}: in_a and in_b must be real, distinct "
                          f"cardinal directions, both got {a_dir!r}")

    out_raw = port_directions["out"]
    out_dirs = [out_raw] if isinstance(out_raw, str) else list(out_raw)
    if not out_dirs:
        raise ValueError(f"port 'out': at least one direction required, got empty")
    out_dirs = [str(d).lower() for d in out_dirs]
    for d in out_dirs:
        if d not in ("n", "s", "e", "w"):
            raise ValueError(f"port 'out': direction must be n/s/e/w, got {d!r}")

    return v4.DspWrapperRecord(
        cell_id=cell_id or f"{tile.name}@{row},{col}",
        row=row, col=col, op=tile.op,
        a_dir=a_dir, b_dir=b_dir, downstream_mask=out_dirs,
        watchdog_threshold=params.get("watchdog_threshold"),
    )


class DspWrapperTileLibrary:
    """Same real `register()`/`get()`/`names()` shape as
    `SuperTileLibrary` and `ComposedTileLibrary`, deliberately -- lets
    `tile_source_registry_v1.py`'s generic resolver treat every
    library uniformly."""

    def __init__(self):
        self._tiles: Dict[str, DspWrapperTileSpec] = {}

    def register(self, tile: DspWrapperTileSpec) -> None:
        if tile.name in self._tiles:
            raise ValueError(f"tile {tile.name!r} already registered")
        self._tiles[tile.name] = tile

    def get(self, name: str) -> DspWrapperTileSpec:
        if name not in self._tiles:
            raise KeyError(f"no tile named {name!r} (have: {sorted(self._tiles)})")
        return self._tiles[name]

    def names(self) -> List[str]:
        return sorted(self._tiles)


dsp_wrapper_tile_library = DspWrapperTileLibrary()

# ── Real, confirmed ops (dsp_wrapper_automaton_v1.ALL_OPS, itself
# grounded in Intel's own real, confirmed per-`n` table, #469) -- one
# tile per op, real hardware-confirmed status noted honestly per op
# (dsp_wrapper_timing.md's own real, current status table). ──────────

dsp_wrapper_tile_library.register(DspWrapperTileSpec(
    name="dsp_add", op="ADD",
    description="Real, HARDWARE-CONFIRMED IEEE-754 single-precision "
                 "float add (#472) -- fire/ACK/re-arming all correct "
                 "on actual silicon.",
    proven="silicon-proven",
))
dsp_wrapper_tile_library.register(DspWrapperTileSpec(
    name="dsp_sub", op="SUB",
    description="Real IEEE-754 float subtract (in_a - in_b). Same "
                 "real protocol/entity as dsp_add; sim-verified only.",
))
dsp_wrapper_tile_library.register(DspWrapperTileSpec(
    name="dsp_mul", op="MUL",
    description="Real IEEE-754 float multiply. Same real protocol/"
                 "entity as dsp_add; sim-verified only.",
))
dsp_wrapper_tile_library.register(DspWrapperTileSpec(
    name="dsp_ge", op="GE",
    description="Real float >= comparison, result is 1 or 0. Sim-only "
                 "-- real IP entity name is a reasoned placeholder "
                 "pending real generation (#475).",
))
dsp_wrapper_tile_library.register(DspWrapperTileSpec(
    name="dsp_le", op="LE",
    description="Real float <= comparison, result is 1 or 0. Sim-only, "
                 "same real caveat as dsp_ge.",
))
dsp_wrapper_tile_library.register(DspWrapperTileSpec(
    name="dsp_neq", op="NEQ",
    description="Real float != comparison, result is 1 or 0. Sim-only, "
                 "same real caveat as dsp_ge.",
))

# ── Self-registration into the real, generic compiler hook
# (points.md #485) -- this IS the entire integration step, per Alan's
# own direct request: the compiler needs no code of its own naming
# "dsp_wrapper" anywhere in its resolve/place/emit logic. ──────────
from tile_source_registry_v1 import TileSource, register_tile_source  # noqa: E402

register_tile_source(TileSource(
    kind="dsp-wrapper", library=dsp_wrapper_tile_library,
    place_fn=place, bucket="dsp_wrapper_records",
))
