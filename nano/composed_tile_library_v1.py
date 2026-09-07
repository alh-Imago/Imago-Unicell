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

MULTI-KIND SUB-CELLS (`points.md #486`): a composed tile's sub-cells
can now be drawn from ANY tile kind registered into `tile_source_
registry_v1.py` (`#485`) -- not just `super_tile_library`'s own Tier-0
primitives. `place_composed()` still returns a plain, FLAT list
(unchanged return TYPE, real backward compatibility for every existing
caller/test), but the items inside it may now be a real MIX of
`v3.IcmV3Record` and `icm_v4.DspWrapperRecord` -- every pre-existing
composed tile (built entirely from super-cell sub-cells) produces the
exact same flat `IcmV3Record`-only list it always did, since nothing
about ITS OWN resolution changed. Bucketing a mixed list into
`icm_v4.IcmV4File`'s own `super_records`/`dsp_wrapper_records` shape
happens one layer up, by real `isinstance()` dispatch -- the same
pattern `mixed_grid_checkpoint_v1.py` already uses for its own
checkpoint records, not a new convention invented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import icm_v3 as v3
from super_tile_library_v1 import super_tile_library, place, SuperTileLibrary
from tile_source_registry_v1 import find_source_for


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
    fixed_params: Dict[str, object] = field(default_factory=dict)
    # A param this sub-cell's tile needs, baked into the DEFINITION
    # itself rather than left for the caller to supply (`points.md
    # #347`). A fixed param is REMOVED from what the composed tile
    # requires from its own caller (`ComposedTileSpec`'s own namespaced-
    # param collection skips anything in here) -- the whole point is the
    # caller never even sees it. Always wins over any same-named
    # caller-supplied namespaced value if one is somehow still given
    # (`place_composed()` applies fixed_params AFTER any caller-supplied
    # merge, deliberately, not the other way around) -- "fixed" means
    # fixed.
    preload_fixed_value: Optional[int] = None
    preload_param_name: Optional[str] = None
    # points.md #686, per Alan's own direct design: marks this sub-cell
    # as PRELOAD-ONLY -- a compile-time-known constant seeded directly
    # into its own captured-value register while the whole tile is held
    # frozen (`SuperGrid.freeze_all()`/`preload_ram_flowing()`), rather
    # than delivered as a live, precisely-timed event. Real, necessary
    # reason, not a shortcut: `ram_constant` (the obvious alternative)
    # is a continuously-live source that races against a dynamically-
    # computed operand and corrupts the result -- confirmed, the exact
    # trap `#611` already found and avoided for the whole-program case.
    # Genuinely different from `fixed_params`: this value is written
    # directly to the CELL OBJECT after construction, bypassing
    # `deliver()`/`core_config` entirely (`ram_flowing` has no params
    # of its own to even receive a value through). Exactly ONE of the
    # two fields above may be set on a preload-only sub-cell -- a
    # literal, tile-authored constant, or the (bare, NOT namespaced --
    # this is a whole-tile-scope value, not a per-subcell one) name of
    # a param the composed tile's own caller must supply. A sub-cell
    # with either field set must resolve to the real `ram_flowing` tile
    # specifically, and must NOT appear in `internal_directions` or
    # `external_ports` for its own `in` port -- checked, not assumed,
    # at placement time (see `place_composed()`).


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
                    composed_library: Optional["ComposedTileLibrary"] = None,
                    _chain: Tuple[str, ...] = (),
                    preloads: Optional[List[Tuple[int, int, int]]] = None) -> List[object]:
    """Resolve a composed tile at anchor (row, col) into real, LEAF-level
    placement records -- one per leaf sub-cell, each ultimately placed
    via its own real tile kind's `place()` function. Per-kind buckets
    (Alan's own choice, `points.md #486`, extending `#485`'s registry):
    the returned list is a genuine MIX of `v3.IcmV3Record` and (if any
    sub-cell resolves to a non-super kind) `icm_v4.DspWrapperRecord` --
    for every PRE-EXISTING composed tile (built entirely from
    super-cell sub-cells) it's exactly the same `IcmV3Record`-only
    list as always, since nothing about their own resolution changed.
    A composed tile's records are exactly what hand-placing each leaf
    piece yourself would produce, just assembled from one call.
    `params` is namespaced `"{subcell_name}.{param_name}"` (e.g.
    `"cmp.threshold"`), since each sub-cell keeps its own unmodified
    param contract.

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

    CIRCULAR REFERENCE GUARD (`points.md #350`, per Alan: "nested
    infinite loops... a nest in a nested calling the outer one"):
    `#347`'s own DSL-level `define` mechanism can't construct a cycle by
    construction (a define can only reference an EARLIER define, so a
    true A->B->A cycle can never be built through it) -- but a
    hand-crafted `--model`-loaded JSON tile (`#345`) skips that
    protection entirely, since `user_tile_loader_v1.py` builds a
    `ComposedTileSpec` directly with no cycle check at all. Confirmed
    this was a REAL, exploitable gap before fixing it (not assumed): a
    self-referencing tile crafted directly and placed here produced a
    genuine `RecursionError` after ~1000 frames, no clear diagnostic.
    `_chain` (private, internal-only -- never pass this yourself) tracks
    which tile names are currently being expanded on this call stack;
    recursing into a name already in it raises a real `ValueError`
    naming the exact cycle, at the point it's first detected, instead of
    silently recursing until the interpreter gives up.

    PRELOAD-ONLY SUB-CELLS (`points.md #686`): if this tile (or any
    nested tile inside it) contains a `SubCellPlacement` with
    `preload_fixed_value`/`preload_param_name` set, the caller MUST
    pass a real, mutable `preloads` list -- every preload-only
    sub-cell's own resolved `(absolute_row, absolute_col, value)`
    triple gets appended to it (nested tiles append to the SAME list,
    not a separate one per level). Omitting `preloads` while such a
    sub-cell exists is a real error, not a silent no-op -- a
    compile-time constant that never gets seeded is a correctness bug,
    not a cosmetic gap. The caller is responsible for the real,
    necessary sequence around this call: freeze the grid, construct
    cells from these records, apply every returned preload via
    `SuperGrid.preload_ram_flowing()`, THEN unfreeze."""
    if composed_library is None:
        composed_library = composed_tile_library
    if tile.name in _chain:
        cycle = " -> ".join((*_chain, tile.name))
        raise ValueError(f"circular composed-tile reference: {cycle} -- "
                          f"a tile can never (directly or indirectly) contain itself")
    _chain = (*_chain, tile.name)

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
        if nested is not None:
            sub_tile, sub_place_fn = nested, None
        else:
            sub_tile, sub_place_fn = _resolve_subcell_leaf(sub.tile_name, library)
        sub_port_names = sub_tile.port_names()

        is_preload = sub.preload_fixed_value is not None or sub.preload_param_name is not None
        if is_preload:
            if nested is not None or sub.tile_name != "ram_flowing":
                raise ValueError(
                    f"composed tile {tile.name!r}: sub-cell {sub.name!r} sets a "
                    f"preload value but resolves to {sub.tile_name!r}, not the real "
                    f"'ram_flowing' tile -- preload-only sub-cells are scoped to "
                    f"ram_flowing specifically (#686)"
                )
            if sub.preload_fixed_value is not None and sub.preload_param_name is not None:
                raise ValueError(
                    f"composed tile {tile.name!r}: sub-cell {sub.name!r} sets BOTH "
                    f"preload_fixed_value and preload_param_name -- exactly one, not both"
                )
            if preloads is None:
                raise ValueError(
                    f"composed tile {tile.name!r}: sub-cell {sub.name!r} is preload-only, "
                    f"but no `preloads` list was passed to place_composed() -- a "
                    f"compile-time constant that never gets seeded is a real "
                    f"correctness bug, not something to silently skip"
                )

        sub_directions = dict(sub.internal_directions)
        for port in sub_port_names:
            if port in sub_directions:
                continue
            if is_preload and port == "in":
                # Real, deliberate placeholder, not a functional wire:
                # `place()` itself still requires every declared port to
                # have SOME direction (a generic, per-tile completeness
                # check, unaware of preload-only sub-cells) -- but
                # ram_flowing's own "in" wiring is just the
                # `upstream_mask` config field, and once preloaded (and
                # frozen->unfrozen), `ram_data_valid` is already True,
                # so `deliver()` rejects any further arrival regardless
                # of direction (its own real "doubly-full-guarded"
                # behavior) -- there is no physical neighbor at this
                # direction and none is needed. 'n' is arbitrary and
                # inert, not a real connection.
                sub_directions[port] = "n"
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
        sub_params.update(sub.fixed_params)   # fixed always wins -- "fixed" means fixed (#347)

        dr, dc = sub.offset
        if nested is not None:
            records.extend(place_composed(nested, row + dr, col + dc, sub_directions, sub_params,
                                           library=library, composed_library=composed_library,
                                           _chain=_chain, preloads=preloads))
        else:
            records.append(sub_place_fn(sub_tile, row + dr, col + dc, sub_directions, sub_params,
                                         cell_id=f"{tile.name}.{sub.name}@{row + dr},{col + dc}"))

        if is_preload:
            if sub.preload_fixed_value is not None:
                value = sub.preload_fixed_value
            else:
                if sub.preload_param_name not in params:
                    raise ValueError(
                        f"composed tile {tile.name!r}: sub-cell {sub.name!r} needs "
                        f"top-level param {sub.preload_param_name!r}, not supplied"
                    )
                value = params[sub.preload_param_name]
                seen_params.add(sub.preload_param_name)
            preloads.append((row + dr, col + dc, value))

    unknown_params = set(params) - seen_params
    if unknown_params:
        raise ValueError(f"composed tile {tile.name!r}: unknown param(s) {sorted(unknown_params)}")

    return records


def apply_preloads_to_records(records: List[object], preloads: List[Tuple[int, int, int]]) -> None:
    """Real, file-format-level bridge (`points.md #687`), per Alan's
    own direct design: folds `place_composed()`'s own in-memory
    `preloads` list (row, col, value triples) directly into the
    matching records' own `IcmV3Record.preload_value` field, mutating
    in place. Once applied, the preload travels with the records
    themselves -- through `IcmV3File.save()`/`load()`, through a plain
    `SuperGrid(records)` construction, anywhere -- rather than needing
    a separate, ephemeral list threaded through by hand at every call
    site. `SuperGrid.__init__()` and `IcmV3File`'s own save/load round
    trip both already handle `preload_value` natively; this is the one
    real, small step connecting `place_composed()`'s own output to
    that already-real mechanism, not a new mechanism of its own."""
    by_pos = {(r.row, r.col): r for r in records}
    for row, col, value in preloads:
        if (row, col) not in by_pos:
            raise ValueError(
                f"apply_preloads_to_records: no record at ({row}, {col}) to "
                f"apply preload {value!r} to -- a real mismatch between "
                f"place_composed()'s own records and its own preloads list, "
                f"not something to silently ignore"
            )
        by_pos[(row, col)].preload_value = value


def _resolve_subcell_leaf(tile_name: str, library: SuperTileLibrary):
    """Resolves a non-nested (leaf) sub-cell tile name to its real
    `(tile_obj, place_fn)` pair -- `points.md #486`'s own real
    generalization. Checks the explicit `library` param FIRST (exact
    backward compatibility with any caller that ever passed a custom
    override there -- untouched behavior, same object, same `place()`
    function this codebase has always used for it), THEN falls
    through to the generic `tile_source_registry_v1.find_source_for()`
    lookup for any OTHER registered kind (DSP wrapper today, whatever
    comes next tomorrow, with zero further changes needed here)."""
    if tile_name in library.names():
        return library.get(tile_name), place
    source = find_source_for(tile_name)
    if source is not None:
        return source.library.get(tile_name), source.place_fn
    raise ValueError(
        f"no tile named {tile_name!r} in the composed library, the given Tier-0 "
        f"library, or any registered tile source"
    )


class ComposedTileLibrary:
    """Same `register()`/`get()` shape as `SuperTileLibrary`, deliberately
    a separate registry (a Tier-1 tile references Tier-0 tiles by name,
    not by object identity, so the two catalogs stay decoupled).

    OPTIONAL `parent` (`points.md #345`): lets a per-run, user-supplied
    library defer to the built-in one for anything it doesn't itself
    define, without ever mutating the built-in registry. This is the
    real mechanism behind `--model FILE` on the CLI (`dsl_cli_v1.py`):
    a fresh `ComposedTileLibrary(parent=composed_tile_library)` gets the
    user's own tiles registered into it, `get()`/`names()` fall back to
    `parent` for everything else, and a user tile SHADOWS a same-named
    built-in one (checked first, `#345`'s own explicit precedence
    choice: an explicit `--model` load is a deliberate override, not an
    accident, so it should win)."""

    def __init__(self, parent: Optional["ComposedTileLibrary"] = None):
        self._tiles: Dict[str, ComposedTileSpec] = {}
        self._parent = parent

    def register(self, tile: ComposedTileSpec) -> None:
        if tile.name in self._tiles:
            raise ValueError(f"composed tile {tile.name!r} already registered")
        self._tiles[tile.name] = tile

    def get(self, name: str) -> ComposedTileSpec:
        if name in self._tiles:
            return self._tiles[name]
        if self._parent is not None and name in self._parent.names():
            return self._parent.get(name)
        raise KeyError(f"no composed tile named {name!r} (have: {sorted(self.names())})")

    def names(self) -> List[str]:
        own = set(self._tiles)
        parent_names = set(self._parent.names()) if self._parent is not None else set()
        return sorted(own | parent_names)


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
                          internal_directions={"out": "e"},
                          fixed_params={"step_amount": 1}),   # #515: magnitude now data-driven,
                                                               # fixed here at the classic +1/-1
                                                               # event-counter semantics this
                                                               # tile was originally designed around
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
                          internal_directions={"out": ["s", "e"]},   # FAN-OUT
                          fixed_params={"step_amount": 1}),   # #515: see sentinel's own note above
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

# ── Real, multi-KIND composition proof (points.md #486): the first
# composed tile whose own sub-cells are NOT all drawn from
# super_tile_library -- "adder" is a real DSP wrapper tile
# (dsp_wrapper_tile_library_v1's "dsp_add"), "sink" is an ordinary
# super-cell RAM tile. place_composed() itself needed no per-kind
# special casing to make this work; it resolves "dsp_add" through the
# same tile_source_registry_v1 lookup every OTHER non-composed
# sub-cell tile name goes through (#485). ────────────────────────────
composed_tile_library.register(ComposedTileSpec(
    name="dsp_add_and_hold",
    description="A real DSP wrapper ADD feeding a super-cell RAM sink "
                 "-- the composed-tile analog of the direct-Python "
                 "'dsp_add -> ram_flowing' pattern already proven end "
                 "to end in icm_v4/#485. 'in_a'/'in_b' feed the real "
                 "DSP wrapper directly; 'out' is the RAM sink's own "
                 "offered (captured) value once the DSP wrapper's real "
                 "result arrives.",
    subcells=[
        SubCellPlacement(name="adder", offset=(0, 0), tile_name="dsp_add",
                          internal_directions={"out": "e"}),
        SubCellPlacement(name="sink", offset=(0, 1), tile_name="ram_flowing",
                          internal_directions={"in": "w"}),
    ],
    external_ports={
        "in_a": ("adder", "in_a"), "in_b": ("adder", "in_b"),
        "out": ("sink", "out"),
    },
    proven="sim-only",
))

# ── select (points.md #686): the real LLVM-ternary composition
# (`select i1 %cond, %true, %false`) originally built inline in
# `llvm_ir_frontend_v1.py` (#674), promoted to a real, reusable Tier-1
# tile per Alan's own direct design. Genuinely the SAME proven internal
# topology as #674's own original (mask/not_mask/and_true/and_false/
# relay/or, identical relative offsets and hop-count relationships) --
# only the CONSTANT-DELIVERY mechanism changed, from a precisely-timed
# live `inject()` sequence to `#686`'s own freeze/preload/unfreeze
# pattern. Deliberately conservative: the internal topology (which
# already has empirically-necessary, load-bearing UNEQUAL hop counts
# between the and_true->or and and_false->relay->or paths) is left
# exactly as proven, not re-simplified in the same change -- only the
# fragile part (caller-side injection timing) is what this promotion
# actually fixes.
#
#   cond(external, "in_a") --\
#                              MASK(1,0) -e-> AND_TRUE(1,1) -e-> OR(1,2)
#   zero_const(0,0) --------/         \
#                                       s
#                                       v
#                               NOT_MASK(2,0) -e-> AND_FALSE(2,1) -\
#   notmask_const(3,0) ----------------/                            (relay(2,2)->n->OR)
#   true_const(0,1) --s--> AND_TRUE's own north input
#   false_const(3,1) --n--> AND_FALSE's own north input
#
# mask = 0 - cond (broadcasts a bare 0/1 boolean to a full 0x0/
# 0xFFFFFFFF word). not_mask = XOR(mask, 0xFFFFFFFF) -- an exact
# boolean/bitwise complement since mask is already a full word.
# and_true/and_false gate true_val/false_val by mask/not_mask; or
# combines them.
composed_tile_library.register(ComposedTileSpec(
    name="select",
    description="LLVM's own ternary -- select i1 cond, true_val, "
                 "false_val. 'cond' is a real, dynamic external input "
                 "(wire it to whatever computed the boolean); "
                 "'true_val'/'false_val' are real, caller-supplied "
                 "32-bit constants, seeded directly into their own "
                 "ram_flowing registers while frozen (#686) -- not "
                 "live inputs. 'out' is the real, computed ternary "
                 "result.",
    subcells=[
        SubCellPlacement(name="zero_const", offset=(0, 0), tile_name="ram_flowing",
                          internal_directions={"out": "s"}, preload_fixed_value=0),
        SubCellPlacement(name="mask", offset=(1, 0), tile_name="subtractor",
                          internal_directions={"in_b": "n", "out": ["e", "s"]}),
        SubCellPlacement(name="not_mask", offset=(2, 0), tile_name="nano_gate",
                          internal_directions={"out": "e"}, fixed_params={"topology": 0x0BC}),
        SubCellPlacement(name="notmask_const", offset=(3, 0), tile_name="ram_flowing",
                          internal_directions={"out": "n"}, preload_fixed_value=0xFFFFFFFF),
        SubCellPlacement(name="true_const", offset=(0, 1), tile_name="ram_flowing",
                          internal_directions={"out": "s"}, preload_param_name="true_val"),
        SubCellPlacement(name="and_true", offset=(1, 1), tile_name="nano_gate",
                          internal_directions={"out": "e"}, fixed_params={"topology": 0x007}),
        SubCellPlacement(name="and_false", offset=(2, 1), tile_name="nano_gate",
                          internal_directions={"out": "e"}, fixed_params={"topology": 0x007}),
        SubCellPlacement(name="false_const", offset=(3, 1), tile_name="ram_flowing",
                          internal_directions={"out": "n"}, preload_param_name="false_val"),
        SubCellPlacement(name="relay", offset=(2, 2), tile_name="ram_flowing",
                          internal_directions={"in": "w", "out": "n"}),
        SubCellPlacement(name="or_gate", offset=(1, 2), tile_name="nano_gate",
                          internal_directions={}, fixed_params={"topology": 0x024}),
    ],
    external_ports={
        "cond": ("mask", "in_a"),
        "out": ("or_gate", "out"),
    },
    proven="sim-only",
))

# ── icmp eq/ne (points.md #686): the real 6-cell comparator-pair
# composition originally built inline in `llvm_ir_frontend_v1.py`
# (#668), promoted the same way as `select` above. Genuinely the SAME
# proven topology (two comparators against threshold 0/1, XOR'd, with
# CMP1's own path deliberately routed two hops longer so its
# contribution reaches the XOR one tick after CMP0's -- #668's own
# real, load-bearing timing finding, left exactly as proven) -- ne
# adds one more real XOR against a preloaded constant 1 (an exact
# boolean NOT, not a bitwise one).
#
#   diff(external, in_a/in_b) --e--> CMP0(0,1) --s--> XOR(1,1) [--e--> NE_XOR(1,2), if ne]
#      |                                                ^                    ^
#      s                                                n                    |
#      v                                                |             one_const(2,2)
#   CMP1(1,0) --s--> RELAY_A(2,0) --e--> RELAY_B(2,1)----/
#   CMP0=threshold 0 (diff==0 test), CMP1=threshold 1 (diff>=1 test) --
#   diff fans out to both; XOR(CMP0, CMP1) is 1 exactly when diff==0
#   (both agree=0) or... in this exact original design CMP0/CMP1's own
#   real relationship is preserved unchanged from #668, not re-derived
#   here.
composed_tile_library.register(ComposedTileSpec(
    name="icmp_eq",
    description="LLVM's icmp eq -- a == b, real 1/0 result. 'in_a'/"
                 "'in_b' are real, dynamic external inputs; 'out' is "
                 "the real, computed boolean result.",
    subcells=[
        SubCellPlacement(name="diff", offset=(0, 0), tile_name="subtractor",
                          internal_directions={"out": ["e", "s"]}),
        SubCellPlacement(name="cmp0", offset=(0, 1), tile_name="comparator",
                          internal_directions={"in": "w", "out": "s"}, fixed_params={"threshold": 0}),
        SubCellPlacement(name="cmp1", offset=(1, 0), tile_name="comparator",
                          internal_directions={"in": "n", "out": "s"}, fixed_params={"threshold": 1}),
        SubCellPlacement(name="relay_a", offset=(2, 0), tile_name="ram_flowing",
                          internal_directions={"in": "n", "out": "e"}),
        SubCellPlacement(name="relay_b", offset=(2, 1), tile_name="ram_flowing",
                          internal_directions={"in": "w", "out": "n"}),
        SubCellPlacement(name="xor_gate", offset=(1, 1), tile_name="nano_gate",
                          internal_directions={}, fixed_params={"topology": 0x0BC}),
    ],
    external_ports={
        "in_a": ("diff", "in_a"), "in_b": ("diff", "in_b"),
        "out": ("xor_gate", "out"),
    },
    proven="sim-only",
))

composed_tile_library.register(ComposedTileSpec(
    name="icmp_ne",
    description="LLVM's icmp ne -- a != b, real 1/0 result. Same real "
                 "topology as icmp_eq, plus one more real XOR against "
                 "a preloaded constant 1 -- an exact boolean NOT "
                 "(1^1=0, 0^1=1), not a bitwise one. 'in_a'/'in_b' are "
                 "real, dynamic external inputs; 'out' is the real, "
                 "computed boolean result.",
    subcells=[
        SubCellPlacement(name="diff", offset=(0, 0), tile_name="subtractor",
                          internal_directions={"out": ["e", "s"]}),
        SubCellPlacement(name="cmp0", offset=(0, 1), tile_name="comparator",
                          internal_directions={"in": "w", "out": "s"}, fixed_params={"threshold": 0}),
        SubCellPlacement(name="cmp1", offset=(1, 0), tile_name="comparator",
                          internal_directions={"in": "n", "out": "s"}, fixed_params={"threshold": 1}),
        SubCellPlacement(name="relay_a", offset=(2, 0), tile_name="ram_flowing",
                          internal_directions={"in": "n", "out": "e"}),
        SubCellPlacement(name="relay_b", offset=(2, 1), tile_name="ram_flowing",
                          internal_directions={"in": "w", "out": "n"}),
        SubCellPlacement(name="eq_xor", offset=(1, 1), tile_name="nano_gate",
                          internal_directions={"out": "e"}, fixed_params={"topology": 0x0BC}),
        SubCellPlacement(name="one_const", offset=(2, 2), tile_name="ram_flowing",
                          internal_directions={"out": "n"}, preload_fixed_value=1),
        SubCellPlacement(name="ne_xor", offset=(1, 2), tile_name="nano_gate",
                          internal_directions={}, fixed_params={"topology": 0x0BC}),
    ],
    external_ports={
        "in_a": ("diff", "in_a"), "in_b": ("diff", "in_b"),
        "out": ("ne_xor", "out"),
    },
    proven="sim-only",
))
