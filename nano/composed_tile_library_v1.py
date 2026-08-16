"""
composed_tile_library_v1.py — Tier 1 of the super-cell tile library:
multi-cell composed tiles with relative placement, built FROM Tier-0
primitives (`super_tile_library_v1.py`), per `docs/stripped-cell/
design-notes/super_tile_library_scope.md`'s own "two real tiers"
section. First real tile: the sentinel (accumulator -> comparator ->
latch), the one composition this project already has a proven,
real-hardware-confirmed topology for -- Alan's own explicit choice to
start Tier 1 here rather than a from-scratch design
(`top_sentinel_discrete_test_v2.v`, points.md #291-#298, #306-#308: 78
ALM, `clk_div` 272.26 MHz, SDC-confirmed, no failing paths).

A REAL, DELIBERATE ADAPTATION from the proven artifact, stated plainly
rather than left implicit: `top_sentinel_discrete_test_v2.v` hand-wires
its three cells directly in Verilog (ACC's `data_out_e` tied straight
into CMP's own `data_in_n`/`arrived_n` ports) -- it does NOT go through
real cardinal-grid physical adjacency at all; there is no genuine
multi-cell fabric in that testbed, just three standalone module
instances wired point-to-point however was convenient for one
self-contained top level. A real `SuperGrid` placement, by contrast,
MUST respect physical adjacency -- a cell offering east can only be
received by whatever's physically placed one column to its east,
arriving on that neighbor's WEST side (the `_OPPOSITE` convention
already established in `unicell_super_automaton_v1.py`). So this tile's
INTERNAL wiring uses w/e directions where the original testbed used n/e
labels for the SAME two internal links -- the computational topology
(acc -> cmp -> lat, threshold configurable, same field roles) is
unchanged and still traces to the same proven design; only the specific
cardinal labels differ, because this version is placed into a real grid
and the original was never placed into anything at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import icm_v3 as v3
from super_tile_library_v1 import super_tile_library, place, SuperTileLibrary


@dataclass
class SubCellPlacement:
    """One Tier-0 tile instance inside a composed tile, at a fixed
    relative offset from the composed tile's own anchor (0,0)."""
    name: str                      # local name within this composed tile, e.g. "acc"
    offset: Tuple[int, int]        # (dr, dc) relative to the tile's own anchor
    tile_name: str                 # a Tier-0 tile registered in super_tile_library
    internal_directions: Dict[str, str] = field(default_factory=dict)
    # Ports of `tile_name` NOT listed here must appear in the composed
    # tile's own `external_ports` mapping -- every port must resolve one
    # way or the other, checked (not assumed) at placement time.


@dataclass
class ComposedTileSpec:
    """A Tier-1 tile: several Tier-0 sub-cells at fixed relative
    offsets, some ports wired internally (fixed direction, never
    caller-chosen -- these are the links BETWEEN sub-cells), the rest
    exposed as this tile's own named ports (the links to the OUTSIDE)."""
    name: str
    description: str
    subcells: List[SubCellPlacement]
    external_ports: Dict[str, Tuple[str, str]]   # composed port name -> (subcell_name, subcell_port_name)
    target: str = "super-only"
    proven: str = "sim-only"

    def port_names(self) -> List[str]:
        return sorted(self.external_ports)


def place_composed(tile: ComposedTileSpec, row: int, col: int,
                    port_directions: Dict[str, str],
                    params: Optional[dict] = None,
                    library: SuperTileLibrary = super_tile_library,
                    composed_library: Optional["ComposedTileLibrary"] = None) -> List[v3.IcmV3Record]:
    """Resolve a composed tile at anchor (row, col) into real
    `IcmV3Record`s, one per LEAF sub-cell, each ultimately placed via
    Tier 0's own `place()` -- a composed tile's records are exactly what
    hand-placing each Tier-0 piece yourself would produce, just
    assembled from one call. `params` is namespaced
    `"{subcell_name}.{param_name}"` (e.g. `"cmp.threshold"`), since each
    sub-cell keeps its own unmodified param contract.

    NESTED COMPOSITION (`points.md #342`, per Alan's own explicit "yes"):
    a `SubCellPlacement.tile_name` may reference EITHER a Tier-0 tile
    (`library`, checked second) OR another registered `ComposedTileSpec`
    (`composed_library`, checked FIRST -- a nested tile takes precedence
    over a same-named Tier-0 tile, since Tier-1 tiles are the more
    specific/deliberate choice when both exist). A nested reference
    recurses: `place_composed()` calls itself for that sub-tile at the
    resolved absolute offset, and its own records are folded into the
    parent's result -- so a composed tile containing a nested composed
    tile still just returns one flat list of real, leaf-level
    `IcmV3Record`s, indistinguishable from a hand-assembled equivalent.
    Nested params double-namespace naturally (`"s1.cmp.threshold"` at
    the grandparent level becomes `"cmp.threshold"` by the time it
    reaches the nested tile's own `place_composed()` call) -- no special
    casing needed, the existing prefix-strip-per-level logic already
    does this correctly at any depth.
    """
    if composed_library is None:
        composed_library = composed_tile_library

    declared = set(tile.port_names())
    given = set(port_directions.keys())
    if declared != given:
        missing = declared - given
        extra = given - declared
        raise ValueError(
            f"composed tile {tile.name!r}: port directions mismatch"
            + (f", missing {sorted(missing)}" if missing else "")
            + (f", unexpected {sorted(extra)}" if extra else "")
        )

    params = params or {}
    records: List[v3.IcmV3Record] = []
    seen_params = set()

    for sub in tile.subcells:
        nested = composed_library.get(sub.tile_name) if sub.tile_name in composed_library.names() else None
        sub_tile = nested if nested is not None else library.get(sub.tile_name)
        sub_port_names = sub_tile.port_names()

        sub_directions = dict(sub.internal_directions)
        for port in sub_port_names:
            if port in sub_directions:
                continue
            match = None
            for ext_name, (sc_name, sc_port) in tile.external_ports.items():
                if sc_name == sub.name and sc_port == port:
                    match = ext_name
                    break
            if match is None:
                raise ValueError(
                    f"composed tile {tile.name!r}: sub-cell {sub.name!r}'s port {port!r} "
                    f"is neither internally wired nor exposed as an external port -- "
                    f"a real gap in this tile's own definition, not a caller error"
                )
            sub_directions[port] = port_directions[match]

        prefix = f"{sub.name}."
        sub_params = {}
        for k, v in params.items():
            if k.startswith(prefix):
                sub_params[k[len(prefix):]] = v
                seen_params.add(k)

        dr, dc = sub.offset
        if nested is not None:
            records.extend(place_composed(nested, row + dr, col + dc, sub_directions, sub_params,
                                           library=library, composed_library=composed_library))
        else:
            records.append(place(sub_tile, row + dr, col + dc, sub_directions, sub_params,
                                  cell_id=f"{tile.name}.{sub.name}@{row + dr},{col + dc}"))

    unknown_params = set(params) - seen_params
    if unknown_params:
        raise ValueError(f"composed tile {tile.name!r}: unknown param(s) {sorted(unknown_params)}")

    return records


class ComposedTileLibrary:
    """Same `register()`/`get()` shape as `SuperTileLibrary`, deliberately
    a separate registry (a Tier-1 tile references Tier-0 tiles by name,
    not by object identity, so the two catalogs stay decoupled)."""

    def __init__(self):
        self._tiles: Dict[str, ComposedTileSpec] = {}

    def register(self, tile: ComposedTileSpec) -> None:
        if tile.name in self._tiles:
            raise ValueError(f"composed tile {tile.name!r} already registered")
        self._tiles[tile.name] = tile

    def get(self, name: str) -> ComposedTileSpec:
        if name not in self._tiles:
            raise KeyError(f"no composed tile named {name!r} (have: {sorted(self._tiles)})")
        return self._tiles[name]

    def names(self) -> List[str]:
        return sorted(self._tiles)


composed_tile_library = ComposedTileLibrary()

composed_tile_library.register(ComposedTileSpec(
    name="sentinel",
    description="accumulator -> comparator -> latch, the proven sentinel "
                 "topology (points.md #291-#298/#306-#308, real Quartus-"
                 "confirmed as a monolithic top-level: 78 ALM, 272.26 MHz, "
                 "top_sentinel_discrete_test_v2.v). 'inc'/'dec' feed the "
                 "accumulator; 'cmp.threshold' (a required param) is the "
                 "comparator's configured reference; 'clear' is the "
                 "latch's external unfreeze control (independent of the "
                 "internal chain, matching the proven design's own "
                 "sticky-until-explicitly-cleared behavior); 'out' is the "
                 "latch's own offered bit.",
    subcells=[
        SubCellPlacement(name="acc", offset=(0, 0), tile_name="accumulator",
                          internal_directions={"out": "e"}),
        SubCellPlacement(name="cmp", offset=(0, 1), tile_name="comparator",
                          internal_directions={"in": "w", "out": "e"}),
        SubCellPlacement(name="lat", offset=(0, 2), tile_name="latch",
                          internal_directions={"set": "w"}),
    ],
    external_ports={
        "inc": ("acc", "inc"), "dec": ("acc", "dec"),
        "clear": ("lat", "clear"), "out": ("lat", "out"),
    },
    proven="sim-only",   # this exact grid-adjacency-respecting layout is
                          # NEW -- proven at the level of "same field roles,
                          # real Quartus data for the monolithic hand-wired
                          # version," not yet independently Quartus-built
                          # as this specific composed-tile placement.
))

# ── Second Tier-1 tile (points.md #341): stresses generality --
# FAN-OUT (one accumulator feeding two independent downstream chains,
# not sentinel's single straight line) and NON-LINEAR placement (an
# L-shape: one branch goes south, the other east). Neither mechanism
# was exercised by the sentinel. Built to test place_composed()'s own
# generality, not because this specific monitor was independently
# requested -- a dual low/high threshold alarm is a real, plausible
# building block in its own right (the shape a Ward-layer health
# monitor with separate under/over-threshold alarms would want), not
# an arbitrary synthetic example. ──────────────────────────────────────
composed_tile_library.register(ComposedTileSpec(
    name="dual_threshold_monitor",
    description="One accumulator FANS OUT to two independent "
                 "comparator->latch chains -- a low-threshold alarm "
                 "(south branch) and a high-threshold alarm (east "
                 "branch), each sticky-latched independently. inc/dec "
                 "feed the shared accumulator; cmp_low.threshold/"
                 "cmp_high.threshold are the two required params; "
                 "clear_low/clear_high are each latch's own external "
                 "unfreeze control; out_low/out_high are each latch's "
                 "own offered bit.",
    subcells=[
        SubCellPlacement(name="acc", offset=(0, 0), tile_name="accumulator",
                          internal_directions={"out": ["s", "e"]}),   # FAN-OUT
        SubCellPlacement(name="cmp_low", offset=(1, 0), tile_name="comparator",
                          internal_directions={"in": "n", "out": "e"}),
        SubCellPlacement(name="lat_low", offset=(1, 1), tile_name="latch",
                          internal_directions={"set": "w"}),
        SubCellPlacement(name="cmp_high", offset=(0, 1), tile_name="comparator",
                          internal_directions={"in": "w", "out": "e"}),
        SubCellPlacement(name="lat_high", offset=(0, 2), tile_name="latch",
                          internal_directions={"set": "w"}),
    ],
    external_ports={
        "inc": ("acc", "inc"), "dec": ("acc", "dec"),
        "clear_low": ("lat_low", "clear"), "out_low": ("lat_low", "out"),
        "clear_high": ("lat_high", "clear"), "out_high": ("lat_high", "out"),
    },
    proven="sim-only",
))

# ── Nested composition proof (points.md #342), per Alan's own explicit
# "yes" to generalizing Tier 1 recursively: a composed tile whose own
# sub-cells are THEMSELVES composed tiles, not just Tier-0 primitives.
# `twin_sentinel` is deliberately the simplest possible proof -- two
# wholly independent `sentinel` instances, side by side, sharing
# nothing -- to isolate "does the recursive placement/namespacing
# machinery work at all" from any question about whether nesting two
# INTERCONNECTED sub-programs is a good idea (a separate, harder design
# question, not addressed here). ────────────────────────────────────────
composed_tile_library.register(ComposedTileSpec(
    name="twin_sentinel",
    description="Two wholly independent 'sentinel' instances placed "
                 "side by side (offset by 2 rows to avoid colliding with "
                 "the first sentinel's own 3-cell-wide footprint) -- "
                 "proves nested composition (a composed tile built from "
                 "other composed tiles, not just Tier-0 primitives) "
                 "actually works, including double-namespaced params "
                 "('s1.cmp.threshold' at this level becomes "
                 "'cmp.threshold' by the time it reaches s1's own "
                 "internal comparator).",
    subcells=[
        SubCellPlacement(name="s1", offset=(0, 0), tile_name="sentinel"),
        SubCellPlacement(name="s2", offset=(2, 0), tile_name="sentinel"),
    ],
    external_ports={
        "s1_inc": ("s1", "inc"), "s1_dec": ("s1", "dec"),
        "s1_clear": ("s1", "clear"), "s1_out": ("s1", "out"),
        "s2_inc": ("s2", "inc"), "s2_dec": ("s2", "dec"),
        "s2_clear": ("s2", "clear"), "s2_out": ("s2", "out"),
    },
    proven="sim-only",
))
