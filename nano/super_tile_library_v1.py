"""
super_tile_library_v1.py — Tier 0 of the super-cell tile library
(`docs/stripped-cell/design-notes/super_tile_library_scope.md`, per
Alan's own framing: the compiler needs this BEFORE it can be built,
"as it uses and touches so many things"). Scoped deliberately small
per Alan's own decision: single-cell primitives ONLY, one per core
type, proving the named-port/placement contract before Tier 1's
harder multi-cell relative-placement problem gets designed against it.

WHY THIS IS A NEW CATALOG, NOT A PORT of `fp_tiles.py`/`model_library.py`:
those are built on the FULL cell's bit-serial, addressed-bus model --
`INT32_ADD` there is dozens of individually-addressed single-bit gate
cells. The super cell inverts the unit of composition: `adder_cell_v1`
does a full 32-bit add in ONE cell. A "tile" here is a placement recipe
for `icm_v3.IcmV3Record`s with NAMED PORTS (logical name -> which
core_config field + physical cardinal direction), not a bag of gates at
bus addresses. See the design note above for the full reasoning.

A REAL, DOCUMENTED ASYMMETRY, found while building this (not assumed
going in): nano's own "in" side isn't a named port at all the way the
other 5 cores' inputs are. Checked directly against
`unicell_automaton_v1.py`'s `CACell.deliver()`: nano has NO upstream_mask
-- it accepts an arrival from ANY physically-wired neighbor
unconditionally (only `cardinal_edge` distinguishes relay-vs-consume PER
INCOMING direction, it doesn't gate whether an arrival is accepted at
all). Every one of the other 5 cores gates capture on a real
upstream_mask/inc_dir/dec_dir/set_dir/clear_dir field -- an arrival from
an unconfigured direction is simply never captured. So `TILE_NANO_GATE`
below declares only an "out" port; there is no "in" port to declare,
which is a genuine architectural difference, not an oversight.

A REAL, DOCUMENTED SHARED-FIELD NUANCE, also confirmed directly against
RTL rather than assumed: the adder's two logical operands (`in_a`/
`in_b`) are NOT two separate fields -- `adder_cell_v1.v` has exactly ONE
`upstream_mask`, and whichever configured direction arrives FIRST becomes
A, the second becomes B (direction does not determine role). So
`TILE_ADDER`'s two ports both map to the SAME `upstream_mask` field,
their direction bits OR-combined at placement time -- `place()` handles
this generically (grouping ports by field, not assuming one port = one
field), not as an adder-specific special case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import icm_v3 as v3


@dataclass
class TilePort:
    """One named, physically-directional port on a tile. `field` names
    the core_config field this port's chosen direction feeds into
    (matching `icm_v3.CORE_FIELD_TABLES[core]`'s own field names exactly
    -- never invented ad hoc)."""
    name: str
    kind: str          # "in" or "out" -- documentation/validation only
    field: str          # which core_config field this port drives


@dataclass
class SuperTileSpec:
    """A Tier-0, single-cell tile: one core type, named ports, named
    parameters. Tier 1 (multi-cell, relative-position composed tiles)
    is explicitly out of scope here -- see the design note's own
    "two real tiers" section."""
    name: str
    core: str
    description: str
    ports: List[TilePort] = field(default_factory=list)
    param_names: List[str] = field(default_factory=list)   # required core_config params, non-directional
    fixed_core_config: dict = field(default_factory=dict)  # always-set fields, e.g. ready=1
    proven: str = "sim-only"   # matches CORES_AND_WRAPPERS_REFERENCE.md's own proven/sim-only vocabulary

    def port_names(self) -> List[str]:
        return [p.name for p in self.ports]


def place(tile: SuperTileSpec, row: int, col: int,
          port_directions: Dict[str, str],
          params: Optional[dict] = None,
          cell_id: Optional[str] = None,
          addon_config: Optional[dict] = None) -> v3.IcmV3Record:
    """Resolve a tile + a chosen physical direction per port + any
    required parameters into one real `IcmV3Record`, ready to feed to
    `SuperGrid`/`icm_v3.encode_super_latch()`.

    `port_directions`: {port_name: 'n'|'s'|'e'|'w'}, one entry per port
    this tile declares. Two ports sharing the same `field` (the adder's
    `in_a`/`in_b` case) simply OR-combine into that field's dirmask --
    no special-casing needed here, the grouping does it generically.
    """
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
    missing_params = set(tile.param_names) - set(params)
    if missing_params:
        raise ValueError(f"tile {tile.name!r}: missing required param(s) {sorted(missing_params)}")
    unknown_params = set(params) - set(tile.param_names)
    if unknown_params:
        raise ValueError(f"tile {tile.name!r}: unknown param(s) {sorted(unknown_params)} "
                          f"(expected {sorted(tile.param_names)})")

    field_dirs: Dict[str, set] = {}
    for port in tile.ports:
        d = port_directions[port.name].lower()
        if d not in ("n", "s", "e", "w"):
            raise ValueError(f"port {port.name!r}: direction must be n/s/e/w, got {d!r}")
        field_dirs.setdefault(port.field, set()).add(d)

    core_config = dict(tile.fixed_core_config)
    for field_name, dirs in field_dirs.items():
        core_config[field_name] = sorted(dirs)
    core_config.update(params)

    return v3.IcmV3Record(
        cell_id=cell_id or f"{tile.name}@{row},{col}",
        row=row, col=col, core=tile.core,
        core_config=core_config, addon_config=addon_config or {},
    )


class SuperTileLibrary:
    """Mirrors `model_library.py`'s own `register()`/`get()` API shape
    deliberately (a real, reusable precedent independent of that file's
    bus-address baggage) -- register at import time, no changes needed
    to this file itself to add a tile elsewhere."""

    def __init__(self):
        self._tiles: Dict[str, SuperTileSpec] = {}

    def register(self, tile: SuperTileSpec) -> None:
        if tile.name in self._tiles:
            raise ValueError(f"tile {tile.name!r} already registered")
        self._tiles[tile.name] = tile

    def get(self, name: str) -> SuperTileSpec:
        if name not in self._tiles:
            raise KeyError(f"no tile named {name!r} (have: {sorted(self._tiles)})")
        return self._tiles[name]

    def names(self) -> List[str]:
        return sorted(self._tiles)


super_tile_library = SuperTileLibrary()

# ── Tier 0: one primitive per core, real port/field tables checked
# directly against icm_v3.CORE_FIELD_TABLES (which is itself checked
# directly against RTL) before being written here. ──────────────────

super_tile_library.register(SuperTileSpec(
    name="nano_gate", core="nano",
    description="A single two-arrival NOR-tree gate cell. Accepts input "
                 "from ANY physically wired neighbor (no upstream_mask on "
                 "this core at all -- see module docstring); only the "
                 "OUTPUT side is a real named port.",
    ports=[TilePort("out", "out", "routing_mask")],
    param_names=["topology"],
    fixed_core_config={"ready": 1},
))

super_tile_library.register(SuperTileSpec(
    name="ram_constant", core="ram",
    description="A fixed-value RAM cell -- offers a permanent, "
                 "never-recaptured constant (ROM-style). Has NO 'in' port "
                 "at all; the value is a parameter, not a wired input.",
    ports=[TilePort("out", "out", "downstream_mask")],
    param_names=["init_data"],
    fixed_core_config={"fixed_mode": 1, "load_data_valid": 1},
))

super_tile_library.register(SuperTileSpec(
    name="ram_flowing", core="ram",
    description="A single-slot, consume-and-refill RAM cell -- captures "
                 "one value, offers it, then re-opens once drained.",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    fixed_core_config={"fixed_mode": 0, "load_data_valid": 0},
))

super_tile_library.register(SuperTileSpec(
    name="adder", core="adder",
    description="A two-operand 32-bit adder. in_a and in_b share the SAME "
                 "underlying upstream_mask field (the real RTL has no "
                 "per-operand field at all) -- whichever configured "
                 "direction's arrival lands FIRST becomes A, the second B.",
    ports=[TilePort("in_a", "in", "upstream_mask"), TilePort("in_b", "in", "upstream_mask"),
           TilePort("out", "out", "downstream_mask")],
))

super_tile_library.register(SuperTileSpec(
    name="accumulator", core="accumulator",
    description="A continuously-live running total. inc/dec are genuinely "
                 "separate fields (unlike the adder's shared field) -- "
                 "arrivals on each direction always mean +1/-1 "
                 "respectively, regardless of arrival order.",
    ports=[TilePort("inc", "in", "inc_dir"), TilePort("dec", "in", "dec_dir"),
           TilePort("out", "out", "downstream_mask")],
))

super_tile_library.register(SuperTileSpec(
    name="comparator", core="comparator",
    description="A stateless signed comparison against a configured "
                 "threshold: result = 1 if input >= threshold else 0.",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    param_names=["threshold"],
))

super_tile_library.register(SuperTileSpec(
    name="latch", core="latch",
    description="A continuously-live sticky SET/CLEAR bit. CLEAR takes "
                 "priority if both arrive the same tick.",
    ports=[TilePort("set", "in", "set_dir"), TilePort("clear", "in", "clear_dir"),
           TilePort("out", "out", "downstream_mask")],
))
