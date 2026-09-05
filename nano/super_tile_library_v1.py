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

TARGET TAGGING (`points.md #339`, added after a real crossed-wire
conversation with Alan worth stating precisely): a tile's `target`
records which hardware it can run on, and the vocabulary is grounded in
an actual RTL fact, not a guess -- `unicell_super_v1.v`'s own nano-core
reconstruction (lines 150-156) exposes ONLY `topology`/`ready`/
`routing_mask`/`cardinal_edge` (the "basic" subset); a standalone
Unicell-n cell (`unicell_stripped_v1.v` directly, no super shell) has
the FULL nano feature set (`hold_in`, `fb_internal_in`, `is_command_
cell`, the whole reprogramming channel) that Unicell-S's shell never
wires through at all. So:
  - `"universal"`  -- uses only the basic subset. Genuinely runs on
    EITHER a plain Unicell-n grid (`CAGrid`) or a Unicell-S grid
    (`SuperGrid`, core_select=nano). `place_on_nano()` proves this is a
    real functional guarantee, not just a label, by actually building a
    working `CACell` from the same tile/port/param contract `place()`
    uses for Unicell-S.
  - `"super-only"` -- uses one of the 5 extra cores (RAM/adder/
    accumulator/comparator/latch). No equivalent exists on a plain
    Unicell-n grid at all -- there's nothing to select. Unicell-S only.
  - `"nano-full"`  -- RESERVED, unused by any tile today. Would cover a
    tile using nano's full feature set (hold/feedback/command-cell) --
    Unicell-n only, since Unicell-S's shell doesn't expose those ports
    at all. No standalone Unicell-n ICM format exists yet to build such
    a tile against (checked directly -- confirmed absent from the repo
    before writing this), so this value is aspirational, not yet usable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import icm_v3 as v3
from unicell_gate_core import TOPO_PASS_A

# ── Target tags (points.md #339) ─────────────────────────────────────
TARGET_UNICELL_N = "unicell-n"   # plain nano grid -- unicell_stripped_v1.v, no super shell
TARGET_UNICELL_S = "unicell-s"   # the super cell -- unicell_super_v1.v

_TARGET_COMPAT = {
    "universal": frozenset({TARGET_UNICELL_N, TARGET_UNICELL_S}),
    "super-only": frozenset({TARGET_UNICELL_S}),
    "nano-full": frozenset({TARGET_UNICELL_N}),   # reserved, see module docstring
}


def valid_targets(tile: "SuperTileSpec") -> frozenset:
    return _TARGET_COMPAT[tile.target]


@dataclass
class TilePort:
    """One named, physically-directional port on a tile. `field` names
    the core_config field this port's chosen direction feeds into
    (matching `icm_v3.CORE_FIELD_TABLES[core]`'s own field names exactly
    -- never invented ad hoc). Points.md #652: `field` may be a single
    name (every tile registered so far) OR several -- a genuine
    generalization, not a special case, of the SAME OR-combine grouping
    `_resolve()` already used for "multiple ports, one shared field"
    (the adder's own `in_a`/`in_b`, points.md #338), now also covering
    "one port, multiple fields it contributes to" -- needed for a real
    case with no other clean expression: `nano_loop_ctrl`'s own
    continue/exit output ports each need to set their OWN dedicated
    comparator-pattern field (`pattern_high`/`pattern_equal`) AND
    contribute their chosen direction into the SHARED `routing_mask`
    every real offer is gated through -- a field genuinely DERIVED from
    more than one port's own independent choice, not something any
    single port could express alone under the old one-field-per-port
    shape."""
    name: str
    kind: str          # "in" or "out" -- documentation/validation only
    field: Union[str, Tuple[str, ...]]

    def field_names(self) -> Tuple[str, ...]:
        return (self.field,) if isinstance(self.field, str) else tuple(self.field)


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
    target: str = "super-only"   # "universal" | "super-only" | "nano-full" -- see module docstring

    def port_names(self) -> List[str]:
        return [p.name for p in self.ports]


def _resolve(tile: SuperTileSpec, port_directions: Dict[str, str],
             params: Optional[dict]) -> Tuple[Dict[str, List[str]], dict]:
    """Shared validation + resolution used by both `place()` (Unicell-S)
    and `place_on_nano()` (Unicell-n) -- the port/param contract is
    identical either way, only what gets BUILT from it differs."""
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

    field_dirs: Dict[str, List[str]] = {}
    for port in tile.ports:
        raw = port_directions[port.name]
        # A port normally resolves to ONE direction, but MAY fan out to
        # several -- a single "out" port covering more than one physical
        # neighbor (e.g. one accumulator feeding two independent
        # downstream chains). Same OR-combine-into-one-field mechanism
        # the adder's shared in_a/in_b already uses (points.md #338),
        # generalized here (points.md #341) from "two ports, one
        # direction each, same field" to "one port, several directions,
        # same field" -- the field-grouping logic below is unchanged
        # either way, only how many directions a single port contributes
        # is new.
        dirs = [raw] if isinstance(raw, str) else list(raw)
        if not dirs:
            raise ValueError(f"port {port.name!r}: at least one direction required, got empty")
        for d in dirs:
            d = d.lower()
            if d not in ("n", "s", "e", "w"):
                raise ValueError(f"port {port.name!r}: direction must be n/s/e/w, got {d!r}")
            for fname in port.field_names():
                field_dirs.setdefault(fname, [])
                if d not in field_dirs[fname]:
                    field_dirs[fname].append(d)
    for k in field_dirs:
        field_dirs[k].sort()

    return field_dirs, params


def place(tile: SuperTileSpec, row: int, col: int,
          port_directions: Dict[str, str],
          params: Optional[dict] = None,
          cell_id: Optional[str] = None,
          addon_config: Optional[dict] = None) -> v3.IcmV3Record:
    """Resolve a tile + a chosen physical direction per port + any
    required parameters into one real `IcmV3Record`, ready to feed to
    `SuperGrid`/`icm_v3.encode_super_latch()`. Targets Unicell-S --
    every tile (`universal` or `super-only`) is valid here, since
    Unicell-S is the strict superset.

    `port_directions`: {port_name: 'n'|'s'|'e'|'w'}, one entry per port
    this tile declares. Two ports sharing the same `field` (the adder's
    `in_a`/`in_b` case) simply OR-combine into that field's dirmask --
    no special-casing needed here, the grouping does it generically.
    """
    field_dirs, params = _resolve(tile, port_directions, params)
    core_config = dict(tile.fixed_core_config)
    core_config.update(field_dirs)
    core_config.update(params)

    return v3.IcmV3Record(
        cell_id=cell_id or f"{tile.name}@{row},{col}",
        row=row, col=col, core=tile.core,
        core_config=core_config, addon_config=addon_config or {},
    )


def place_on_nano(tile: SuperTileSpec, row: int, col: int,
                   port_directions: Dict[str, str],
                   params: Optional[dict] = None):
    """Resolve a `target='universal'` tile onto a plain Unicell-n grid
    (`CAGrid`) instead -- the same port/param contract as `place()`,
    proving "universal" is a real, functional guarantee rather than a
    label. Returns a real `CACell`, ready to be dropped straight into a
    `CAGrid.cells` dict.

    Rejects anything that isn't genuinely universal with a clear error,
    rather than guessing: a `super-only` tile has no meaning on a plain
    Unicell-n grid at all (there's no RAM/adder/accumulator/comparator/
    latch core there to select)."""
    if TARGET_UNICELL_N not in valid_targets(tile):
        raise ValueError(
            f"tile {tile.name!r} (target={tile.target!r}) has no Unicell-n equivalent -- "
            f"only target='universal' tiles can be placed on a plain Unicell-n grid"
        )
    if tile.core != "nano":
        # Should be unreachable today (every universal tile is core="nano"
        # by construction) -- kept as a real check, not a silent assumption,
        # in case a future universal tile is ever mistagged.
        raise ValueError(f"tile {tile.name!r} is tagged universal but core={tile.core!r}, "
                          f"not 'nano' -- no Unicell-n equivalent exists for this core type")

    field_dirs, params = _resolve(tile, port_directions, params)
    from unicell_automaton_v1 import CACell

    routing_mask = v3.pack_dirmask(field_dirs.get("routing_mask", []))
    topology = params.get("topology", 0)
    return CACell(row=row, col=col, topology=topology, start_flag=True,
                  routing_mask=routing_mask, cardinal_edge=0)


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

    def for_target(self, target: str) -> List[str]:
        """Which registered tiles can actually run on `target`
        (`TARGET_UNICELL_N`/`TARGET_UNICELL_S`) -- the "vm knows which
        to use from the library" lookup Alan asked for."""
        return sorted(n for n in self._tiles if target in valid_targets(self._tiles[n]))


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
    target="universal",
))

# points.md #652: real loop-construction tiles, the tile-library-level
# counterpart to `#638`'s own real bounded-loop-ring RTL and `#649`'s
# own confirmed-working VM composition of the exact same shape.
# Together with a plain `ram_flowing` cell closing the physical ring
# (the real, load-bearing 4th-cell reason `#637`'s own design note
# already found: this mesh is bipartite, a genuine 3-cell ring cannot
# close under pure N/S/E/W hops), these two tiles are everything the
# ring needs beyond the already-registered `adder`/`subtractor`.
super_tile_library.register(SuperTileSpec(
    name="nano_loop_var", core="nano",
    description="A real loop-carried variable's own storage cell -- "
                 "PASS_A topology (fixed), hold_in=1 (fixed, #522) so "
                 "its own held value survives indefinitely across real "
                 "a_update_in/a_reemit_in events instead of resetting "
                 "after the first two-arrival fire, matching #638's own "
                 "real LOOPVAR exactly. Only the forward offer is a "
                 "named port -- a_update_in/a_reemit_in stay real,  "
                 "testbench/control-plane-driven control signals, not "
                 "tile parameters (matching #636's own established "
                 "honest scope: no real command-core/control source "
                 "exists yet to drive them from within the fabric).",
    ports=[TilePort("out", "out", "routing_mask")],
    param_names=[],
    fixed_core_config={"topology": TOPO_PASS_A, "hold_in": 1, "ready": 1},
    # points.md #652: target="super-only", not "universal" -- real,
    # honest correction, caught by testing before this claim shipped.
    # place_on_nano() (the Unicell-n path) is hardcoded to wire only
    # topology+routing_mask into the CACell it builds; hold_in is
    # silently dropped (confirmed directly: place_on_nano() on this
    # exact tile produced hold_in=False despite fixed_core_config
    # saying 1). Real, separate, later fix: extend place_on_nano() to
    # match from_record()'s own real field coverage.
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="nano_loop_ctrl", core="nano",
    description="A real loop-exit decision cell -- PASS_A topology "
                 "(fixed) so the routed value is always the loop "
                 "variable itself regardless of outcome, dynamic_"
                 "route_en=1 (fixed, #140/#650) so the SAME real "
                 "comparator that decides the route also determines "
                 "which of `continue_out`/`exit_out` actually fires. "
                 "Points.md #652's own real, necessary TilePort "
                 "generalization in action: `continue_out` sets its own "
                 "dedicated `pattern_high` field AND contributes its "
                 "chosen direction into the shared `routing_mask` every "
                 "real offer is gated through; `exit_out` does the same "
                 "for `pattern_equal` -- `routing_mask` ends up as the "
                 "real, correct OR of both, DERIVED from two different "
                 "ports' own independent choices, with no separate "
                 "field or special-casing needed. `pattern_low` "
                 "(the degenerate N<i safety case) is deliberately tied "
                 "to the SAME direction as `exit_out` via `params`, not "
                 "a fourth port -- matching #638's own real, stated "
                 "safety reasoning (route it out rather than let it "
                 "silently hang) without inventing a redundant port for "
                 "a case that should always resolve the same way "
                 "`exit_out` does.",
    ports=[
        TilePort("continue_out", "out", ("pattern_high", "routing_mask")),
        TilePort("exit_out", "out", ("pattern_equal", "routing_mask")),
    ],
    param_names=["pattern_low"],
    fixed_core_config={"topology": TOPO_PASS_A, "dynamic_route_en": 1, "ready": 1},
    # points.md #652: real, honest correction, caught by testing before
    # this claim shipped -- place_on_nano() (the Unicell-n path) is
    # hardcoded to wire only topology+routing_mask into the CACell it
    # builds; hold_in/dynamic_route_en/pattern_* are silently dropped.
    # Confirmed directly: place_on_nano() on nano_loop_var produced
    # hold_in=False despite the tile's own fixed_core_config saying 1.
    # target="super-only" until place_on_nano() is genuinely extended
    # to match from_record()'s own real field coverage -- a real,
    # separate, later fix, not claimed done here.
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="ram_constant", core="ram",
    description="A fixed-value RAM cell -- offers a permanent, "
                 "never-recaptured constant (ROM-style). Has NO 'in' port "
                 "at all; the value is a parameter, not a wired input.",
    ports=[TilePort("out", "out", "downstream_mask")],
    param_names=["init_data"],
    fixed_core_config={"fixed_mode": 1, "load_data_valid": 1},
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="ram_flowing", core="ram",
    description="A single-slot, consume-and-refill RAM cell -- captures "
                 "one value, offers it, then re-opens once drained.",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    fixed_core_config={"fixed_mode": 0, "load_data_valid": 0},
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="adder", core="adder",
    description="A two-operand 32-bit adder. in_a and in_b share the SAME "
                 "underlying upstream_mask field (the real RTL has no "
                 "per-operand field at all) -- whichever configured "
                 "direction's arrival lands FIRST becomes A, the second B.",
    ports=[TilePort("in_a", "in", "upstream_mask"), TilePort("in_b", "in", "upstream_mask"),
           TilePort("out", "out", "downstream_mask")],
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="subtractor", core="adder",
    description="points.md #611: the SAME real adder core, with the "
                 "real RTL's own subtract_mode bit fixed on -- computes "
                 "A-B via the same real carry chain (invert B, cin=1), "
                 "confirmed directly against adder_cell_v1.v's own real "
                 "comment (\"subtraction is nearly free on top of the "
                 "existing carry chain\"). A separate tile, not an "
                 "optional param on \"adder\" -- this tile system's own "
                 "params are always required, so a genuinely optional "
                 "toggle needs its own tile, same real pattern "
                 "\"ram_constant\"/\"ram_flowing\" already established.",
    ports=[TilePort("in_a", "in", "upstream_mask"), TilePort("in_b", "in", "upstream_mask"),
           TilePort("out", "out", "downstream_mask")],
    fixed_core_config={"subtract_mode": 1},
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="accumulator", core="accumulator",
    description="A continuously-live running total. inc/dec are genuinely "
                 "separate fields (unlike the adder's shared field) -- "
                 "arrivals on each direction always mean +step_amount/"
                 "-step_amount respectively (#515), regardless of arrival "
                 "order. pulse_mode/threshold (#515's own reset-after-fire "
                 "pulse generator) are NOT yet exposed via this tile -- "
                 "direct core_config construction only, for now.",
    ports=[TilePort("inc", "in", "inc_dir"), TilePort("dec", "in", "dec_dir"),
           TilePort("out", "out", "downstream_mask")],
    param_names=["step_amount"],
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="comparator", core="comparator",
    description="A stateless signed comparison against a configured "
                 "threshold: result = 1 if input >= threshold else 0.",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    param_names=["threshold"],
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="latch", core="latch",
    description="A continuously-live sticky SET/CLEAR bit. CLEAR takes "
                 "priority if both arrive the same tick.",
    ports=[TilePort("set", "in", "set_dir"), TilePort("clear", "in", "clear_dir"),
           TilePort("out", "out", "downstream_mask")],
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="sequencer", core="sequencer",
    description="A real, config-fixed cyclic sequence of up to 4 "
                 "8-bit values (points.md #609), offered in order, "
                 "advancing to the next value only once the current "
                 "offer is genuinely acked -- wrapping after "
                 "SEQUENCE_LEN+1 values. Genuinely no 'in' port at all "
                 "(confirmed directly against the real RTL: this core "
                 "never captures anything, ack_out is tied low on "
                 "every direction). Real, deliberate choice, matching "
                 "every other tile's own direct-field-value convention "
                 "(no smoothing layer): param names and casing match "
                 "the real, mechanically-extracted RTL field names "
                 "exactly (VALUE_0.../SEQUENCE_LEN, uppercase -- this "
                 "one core's own real RTL comment style, confirmed not "
                 "an inconsistency to silently 'fix'). SEQUENCE_LEN is "
                 "stored as the real sequence length MINUS ONE (0 means "
                 "a length-1 sequence), matching the real hardware "
                 "encoding directly, same as the RTL's own comment.",
    ports=[TilePort("out", "out", "downstream_mask")],
    param_names=["VALUE_0", "VALUE_1", "VALUE_2", "VALUE_3", "SEQUENCE_LEN"],
    target="super-only",
))

super_tile_library.register(SuperTileSpec(
    name="branch", core="branch",
    description="A real, three-way held-reference router (points.md "
                 "#608): captures the FIRST arrived value as a real "
                 "reference (or continuously updates it if rolling_mode "
                 "is set), then routes each subsequent arrival's own "
                 "value out route_low/route_equal/route_high depending "
                 "on how it compares against that reference. Real, "
                 "necessary default, found while testing this tile, not "
                 "assumed: the real RTL only ever offers a result "
                 "downstream when emit_low/emit_equal/emit_high are set "
                 "-- WITHOUT them, a branch cell classifies but never "
                 "emits anything at all, silently. Fixed here to always "
                 "emit on every real outcome (a genuine, useful "
                 "always-route default), passing the real arrived value "
                 "through rather than a fixed override (the "
                 "value_source_*/fixed_value_* override isn't yet "
                 "exposed via this tile, same real precedent as the "
                 "accumulator tile's own deferred pulse_mode/threshold).",
    ports=[TilePort("in", "in", "upstream_dir"),
           TilePort("route_low", "out", "route_low"),
           TilePort("route_equal", "out", "route_equal"),
           TilePort("route_high", "out", "route_high")],
    param_names=["rolling_mode"],
    fixed_core_config={"emit_low": 1, "emit_equal": 1, "emit_high": 1},
    target="super-only",
))

# ── Self-registration into the real, generic compiler hook
# (points.md #485, tile_source_registry_v1.py) -- makes this,
# pre-existing library the first real proof the hook covers what
# already worked, not just the new dsp_wrapper_tile_library_v1.py
# kind it was built alongside. Zero behavior change for anything
# already using `super_tile_library`/`place()` directly. ──────────
from tile_source_registry_v1 import TileSource, register_tile_source  # noqa: E402

register_tile_source(TileSource(
    kind="super-tier0", library=super_tile_library,
    place_fn=place, bucket="super_records",
))
