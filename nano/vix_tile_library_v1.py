"""
vix_tile_library_v1.py — Tier 0 of a real tile library for the VIX
Carrier lineage (points.md #746's own real, named gap; built #748).

WHY A NEW, SEPARATE LIBRARY, NOT A FOURTH `target=` VALUE ON
`SuperTileSpec`: confirmed directly before building anything (#746) --
`super_tile_library_v1.py`'s own `target` field ("universal" |
"super-only" | "nano-full") already distinguishes real sub-variants of
the SAME old lineage's own unified, 42-bit `core_config` union. VIX
Carrier's own `_v4c` cores have genuinely different `cfg_data` widths
per core (64/80/128 bits, confirmed directly from each core's own real
RTL header comment below) and, for several cores, entirely different
field semantics -- shoehorning a fourth `target` value onto
`SuperTileSpec` would blur two real, structurally different families
under one shared dataclass. A separate `VixTileSpec`/`VixTileLibrary`
keeps the same real, proven port/param CONTRACT (`_resolve()`'s own
shape, directly reused) without pretending the two lineages share one
underlying record format.

WHAT `place()` PRODUCES HERE, AND WHY IT DIFFERS FROM `super_tile_
library_v1.py`'s OWN `place()`: the old library's `place()` returns a
real `icm_v3.IcmV3Record` directly, with ABSOLUTE `row`/`col` -- correct
for that flat format. This format's own real placement unit is a
`icm_vix_v1.HierCell`, addressed in LOCAL `rel_row`/`rel_col`
coordinates relative to whichever pattern it ends up inside (#737-
#742) -- a VIX tile's own `place()` returns a `HierCell`, at `(0,0)` by
default (the natural, single-cell case), or at an explicit local offset
if composing more than one tile into a real, multi-cell pattern by
hand. Wrapping that returned cell in a real `HierPattern` and a
`HierPlacement` (`icm_vix_v1.py`) is the caller's own job, same
division of labor `super_tile_library_v1.py`'s own `place()` already
has with whatever assembles a full `IcmV3File` from its output.

REAL FIELD MAPS BELOW, each confirmed directly against the actual
`_v4c` RTL header comment (`fpga/verilog/<core>_v4c.v`), not assumed
from the old lineage's own field names, matching `ICM_V3_FORMAT.md`'s
own established verification discipline:

- `ram` (`ram_cell_v4c.v`): 80-bit cfg_data -- downstream_mask[5:0],
  upstream_mask[11:6], fixed_mode[12], load_data_valid[13],
  init_data[45:14].
- `adder` (`adder_cell_v4c.v`): 64-bit -- downstream_mask[5:0],
  upstream_mask[11:6], subtract_mode[12].
- `comparator` (`compare_cell_v4c.v`, dispatched via the VM's own real
  `core="comparator"` string -- the RTL's own SEL_COMPARE localparam is
  a Verilog-side label only, confirmed directly against `SuperCell.
  from_record()`'s own real dispatch, not assumed): 64-bit --
  downstream_mask[5:0], upstream_mask[11:6], threshold[43:12] (32-bit
  signed).
- `branch` (`branch_cell_v4c.v`): 80-bit, IDENTICAL to the old
  lineage's own real, established fields (`upstream_dir` is a SINGLE
  direction, not a mask -- confirmed directly, #742's own real finding,
  carried forward here) -- upstream_dir[2:0], value_source_low/equal/
  high[3][4][5], fixed_value_low/equal/high[12:6][19:13][26:20] (7-bit
  each), emit_low/equal/high[27][28][29]. `route_low/equal/high` and
  `rolling_mode` are real, separate fields this header excerpt didn't
  show bit positions for -- ADDED here as tile ports/params matching
  `#742`'s own real, working CORDIC usage directly, not guessed.
- `accumulator` (`accumulator_cell_v4c.v`): 64-bit -- inc_dir[5:0],
  dec_dir[11:6], downstream_mask[17:12], step_amount[25:18] (unsigned).
  `pulse_mode`/`threshold` deliberately NOT exposed as tile params yet
  -- matching the exact same real, stated scope limit the old lineage's
  own `TILE_ACCUMULATOR` already carries ("direct core_config
  construction only, for now").
- `latch` (`latch_cell_v4c.v`): 64-bit -- set_dir[5:0], clear_dir
  [11:6], downstream_mask[17:12], toggle_dir[23:18].
- `sequencer` (`sequencer_cell_v4c.v`): 64-bit -- VALUE_0..3 (8 bits
  each), SEQUENCE_LEN[33:32] (stored as length-1), downstream_mask
  [39:34].
- `mul` (`mul_cell_v4c.v`, points.md #724): 64-bit -- downstream_mask
  [5:0], upstream_mask[11:6]. No subtract-mode equivalent (multiply has
  none) -- confirmed directly, bit [12] is real, genuine reserved
  headroom, not a field this tile needs to expose.
- `priority` (`priority_cell_v4c.v`, points.md #730): 64-bit --
  upstream_mask[5:0], downstream_mask[11:6], priority_rank_n/s/e/w
  (2 bits each), scheduling_mode[20].
- `nano` (`nano_gate_v4c.v`): 128-bit `cmd_latch`, IDENTICAL real field
  shape to the old lineage's own nano (`topology`, `routing_mask`,
  `cardinal_edge`, etc.) -- same real, documented asymmetry carried
  forward from `super_tile_library_v1.py`'s own real, confirmed finding:
  nano has no real "in" port at all (accepts from any physically-wired
  neighbor unconditionally; only `cardinal_edge` distinguishes relay-
  vs-consume per direction, it doesn't gate acceptance).

REAL, DELIBERATE SCOPE LIMIT, stated honestly, not silently omitted:
`command` (the 9th/11th unified-carrier core, mode-selected, deployed
as two simultaneous instances in a real topology) is genuinely more
complex than every other core here -- a programming/routing core, not
a data-flow computation core, and not needed for the kind of straight-
line/loop compiler output this whole line of work (`#737`-`#747`) has
been built and tested against. Real, separate, deferred work, not
attempted here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

from icm_vix_v1 import HierCell
from super_tile_library_v1 import TilePort, _resolve as _resolve_ports  # noqa: F401 -- real, direct reuse


@dataclass
class VixTileSpec:
    """A Tier-0, single-cell VIX tile: one `_v4c` core type, named
    ports, named parameters -- the same real port/param CONTRACT
    `super_tile_library_v1.SuperTileSpec` already establishes, applied
    to the VIX Carrier lineage's own, structurally different core_config
    shapes rather than shoehorned into that same dataclass.

    `arrivals_needed` (points.md #757) is the real, third contract
    field a placement algorithm needs alongside shape and ports --
    Alan's own original design principle, established at the very
    start of this whole project (`points.md` #17, 2026-07-07): "zero
    same-depth co-locations" -- two cells at the same real dataflow
    depth fire on the same tick, colliding if they share a consumer.
    Depth itself is a per-PLACEMENT property (computed from the real
    graph, not the tile), but computing it correctly requires knowing
    each tile's own real, fixed CONSUMPTION count first -- how many
    separate real arrival events a tile needs before it produces real
    output, confirmed directly against each core's own actual
    `_deliver_*()` implementation, not assumed from its own name or
    port count:
    - Most cores (`ram`, `comparator`, `accumulator`, `latch`,
      `nano_gate`, `priority`) need exactly 1 real arrival -- their
      own real output becomes valid on the SAME tick that arrival is
      processed.
    - `adder`/`subtractor`/`mul` need 2 -- a real, sequential "capture
      A, then capture B" shape (`#513`'s own "matched pair" framing),
      confirmed directly against `_deliver_adder()`.
    - `branch` is a real, honest special case: its FIRST-ever real use
      needs 2 (the first arrival only establishes its held reference,
      producing no real output at all; only the second genuinely
      compares and emits) -- but every SUBSEQUENT real comparison,
      once that reference is already held, needs only 1. Recorded here
      as 2 (the real, worst-case, first-use shape) since a placement
      algorithm needs to know about the one-time reference-settling
      cost when scheduling a branch-based convergence point (the exact
      real "settle" phase `#742`'s own CORDIC build already needed by
      hand).
    - `sequencer` needs 0 -- its own real output is already live from
      the moment it's configured, never arrival-triggered at all.
    """
    name: str
    core: str
    description: str
    ports: List[TilePort] = field(default_factory=list)
    param_names: List[str] = field(default_factory=list)
    fixed_core_config: dict = field(default_factory=dict)
    proven: str = "sim-only"  # matches CORES_AND_WRAPPERS_REFERENCE.md's own vocabulary
    arrivals_needed: int = 1

    def port_names(self) -> List[str]:
        return [p.name for p in self.ports]


def place(tile: VixTileSpec, port_directions: Dict[str, str],
          params: Optional[dict] = None,
          cell_id: str = "c0",
          rel_row: int = 0, rel_col: int = 0,
          addon_config: Optional[dict] = None,
          io_name: Optional[str] = None,
          preload_value: Optional[int] = None) -> HierCell:
    """Resolve a VIX tile + a chosen physical direction per port + any
    required parameters into one real `HierCell` -- local coordinates
    (`rel_row`/`rel_col`, default `(0,0)`, the natural single-cell tile
    placement), ready to drop directly into a `HierPattern`'s own
    `cells` list (`icm_vix_v1.py`). Reuses `super_tile_library_v1.
    _resolve()` directly for port/param validation and direction-
    grouping -- the same real contract, not a re-derived one."""
    field_dirs, resolved_params = _resolve_ports(tile, port_directions, params)  # type: ignore[arg-type]
    core_config = dict(tile.fixed_core_config)
    core_config.update(field_dirs)
    core_config.update(resolved_params)
    return HierCell(
        cell_id=cell_id, rel_row=rel_row, rel_col=rel_col, core=tile.core,
        core_config=core_config, addon_config=addon_config or {},
        io_name=io_name, preload_value=preload_value,
    )


# ---- the real, registered tiles ----

vix_tile_library: Dict[str, VixTileSpec] = {}


def register(tile: VixTileSpec) -> VixTileSpec:
    vix_tile_library[tile.name] = tile
    return tile


TILE_NANO_GATE = register(VixTileSpec(
    name="nano_gate", core="nano",
    description="Confirmed directly against nano_gate_v4c.v's own real "
                 "cmd_latch field map -- IDENTICAL real shape to the old "
                 "lineage's own nano (topology/routing_mask/cardinal_edge). "
                 "No real 'in' port -- nano accepts from any physically-"
                 "wired neighbor unconditionally, the same real, documented "
                 "asymmetry super_tile_library_v1.py's own TILE_NANO_GATE "
                 "already establishes.",
    ports=[TilePort("out", "out", "routing_mask")],
    param_names=["topology"],
    fixed_core_config={"ready": 1},
))

TILE_RAM_FLOWING = register(VixTileSpec(
    name="ram_flowing", core="ram",
    description="Single-arrival capture, held until drained, then "
                 "re-armed -- fixed_mode=0. Confirmed against ram_cell_"
                 "v4c.v's own real 80-bit field map.",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    fixed_core_config={"fixed_mode": 0},
))

TILE_RAM_CONSTANT = register(VixTileSpec(
    name="ram_constant", core="ram",
    description="Permanent, continuously-offering ROM-style source -- "
                 "fixed_mode=1. Real, deliberate warning, confirmed the "
                 "hard way building a real CORDIC pipeline (#742): a "
                 "continuously-live constant double-counts if fed into a "
                 "two-arrival capture core (adder/mul/etc.) and the real, "
                 "dynamic operand is even one tick late -- prefer a real, "
                 "one-shot preload_value on a ram_flowing cell instead "
                 "for feeding a compile-time constant into such a core.",
    ports=[TilePort("out", "out", "downstream_mask")],
    param_names=["init_data"],
    fixed_core_config={"fixed_mode": 1, "load_data_valid": 1},
))

TILE_RAM_PRELOAD = register(VixTileSpec(
    name="ram_preload", core="ram",
    description="Points.md #756: a real, dedicated, ONE-SHOT constant "
                 "source -- flowing-mode (fixed_mode=0), no real 'in' "
                 "port at all (a genuine compile-time constant has no "
                 "real upstream to wire), seeded via HierCell's own "
                 "real preload_value field, not a core_config param. "
                 "Offers exactly once, then goes quiet until re-captured "
                 "-- the real, correct default for feeding a compile-"
                 "time constant into a two-arrival core (adder/mul), "
                 "confirmed directly (#750): even TWO such preloaded "
                 "cells converging on the same real consumer still need "
                 "a genuinely different real path length each, since "
                 "both are already 'ready' from tick zero -- this tile "
                 "fixes RE-CONTAMINATION, not simultaneous first "
                 "arrival, which stays a real, separate placement "
                 "concern. Real, honest distinction from ram_constant: "
                 "that one is fixed_mode=1 (continuously re-offering,"
                 " never safe feeding a two-arrival core directly); this "
                 "one is fixed_mode=0, preloaded, one-shot.",
    ports=[TilePort("out", "out", "downstream_mask")],
    fixed_core_config={"fixed_mode": 0},
))

TILE_ADDER = register(VixTileSpec(
    name="adder", core="adder",
    description="Two-operand 32-bit adder. in_a/in_b share the SAME "
                 "real upstream_mask field (adder_cell_v4c.v has no "
                 "per-operand field) -- whichever configured direction's "
                 "arrival lands FIRST becomes A, the second B.",
    ports=[TilePort("in_a", "in", "upstream_mask"), TilePort("in_b", "in", "upstream_mask"),
           TilePort("out", "out", "downstream_mask")],
    arrivals_needed=2,
))

TILE_SUBTRACTOR = register(VixTileSpec(
    name="subtractor", core="adder",
    description="The SAME real adder_v4c core, subtract_mode fixed on "
                 "-- computes A-B (whichever arrival lands first is A).",
    ports=[TilePort("in_a", "in", "upstream_mask"), TilePort("in_b", "in", "upstream_mask"),
           TilePort("out", "out", "downstream_mask")],
    fixed_core_config={"subtract_mode": 1},
    arrivals_needed=2,
))

TILE_MUL = register(VixTileSpec(
    name="mul", core="mul",
    description="Points.md #724: combinational 32-bit multiply, "
                 "truncated product (Product[31:0] only, matching LLVM "
                 "IR's own mul truncation semantics). Same real shared-"
                 "upstream_mask shape as adder -- confirmed against "
                 "mul_cell_v4c.v directly: no subtract-mode equivalent "
                 "exists (bit [12] is genuine reserved headroom).",
    ports=[TilePort("in_a", "in", "upstream_mask"), TilePort("in_b", "in", "upstream_mask"),
           TilePort("out", "out", "downstream_mask")],
    arrivals_needed=2,
))

TILE_COMPARATOR = register(VixTileSpec(
    name="comparator", core="comparator",
    description="Single-arrival, stateless: captures a value, compares "
                 "against a real, statically-configured threshold, "
                 "offers a boolean result. Confirmed against compare_"
                 "cell_v4c.v directly (the RTL's own SEL_COMPARE "
                 "localparam is a Verilog-internal label; the real, "
                 "dispatched core string is 'comparator', confirmed "
                 "against SuperCell.from_record()'s own real dispatch). "
                 "The right default tool for 'compare a dynamic value "
                 "against a compile-time constant' -- branch needs a "
                 "real, separate, sequenced reference-establishing "
                 "delivery instead (#742's own real finding).",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    param_names=["threshold"],
))

TILE_BRANCH = register(VixTileSpec(
    name="branch", core="branch",
    description="Real, genuinely different shape from every other tile "
                 "here, confirmed directly (#742): upstream_dir is a "
                 "SINGLE fixed direction, not a mask -- this tile cannot "
                 "be a direct external entry point (its own real "
                 "delivery logic never accepts injection, only a "
                 "genuine cardinal arrival, CELL_GOTCHAS.md's own real, "
                 "recorded fact). The held comparison reference is "
                 "whatever arrives FIRST on upstream_dir -- establishing "
                 "it against a known constant needs a real, separate, "
                 "sequenced delivery (a dedicated zero-source cell, "
                 "settled BEFORE the real, dynamic value arrives), not "
                 "simultaneous delivery. value_source_low/equal/high: "
                 "0=emit the original captured value, 1=emit the "
                 "matching fixed_value_* (7-bit) instead.",
    ports=[TilePort("in", "in", "upstream_dir"),
           TilePort("route_low", "out", "route_low"),
           TilePort("route_equal", "out", "route_equal"),
           TilePort("route_high", "out", "route_high")],
    param_names=["value_source_low", "value_source_equal", "value_source_high",
                 "emit_low", "emit_equal", "emit_high", "rolling_mode"],
    arrivals_needed=2,  # real, worst-case first-use shape (#757) -- see VixTileSpec's own docstring
))

TILE_ACCUMULATOR = register(VixTileSpec(
    name="accumulator", core="accumulator",
    description="A continuously-live running total. inc/dec are "
                 "genuinely separate fields (unlike adder's shared "
                 "field) -- arrivals on each direction always mean "
                 "+step_amount/-step_amount respectively, regardless of "
                 "arrival order. pulse_mode/threshold NOT yet exposed "
                 "via this tile -- direct core_config construction only, "
                 "for now (the same real, stated scope limit the old "
                 "lineage's own TILE_ACCUMULATOR already carries).",
    ports=[TilePort("inc", "in", "inc_dir"), TilePort("dec", "in", "dec_dir"),
           TilePort("out", "out", "downstream_mask")],
    param_names=["step_amount"],
))

TILE_LATCH = register(VixTileSpec(
    name="latch", core="latch",
    description="Set/clear/toggle real state, confirmed against "
                 "latch_cell_v4c.v's own real 64-bit field map.",
    ports=[TilePort("set", "in", "set_dir"), TilePort("clear", "in", "clear_dir"),
           TilePort("toggle", "in", "toggle_dir"), TilePort("out", "out", "downstream_mask")],
))

TILE_SEQUENCER = register(VixTileSpec(
    name="sequencer", core="sequencer",
    description="A real, fixed, 4-value sequence, replayed on each "
                 "matching arrival (SEQUENCE_LEN stored as length-1). No "
                 "real 'in' port to declare here -- confirmed against "
                 "sequencer_cell_v4c.v's own real field map: nothing in "
                 "it names an upstream field at all.",
    ports=[TilePort("out", "out", "downstream_mask")],
    param_names=["VALUE_0", "VALUE_1", "VALUE_2", "VALUE_3", "SEQUENCE_LEN"],
    arrivals_needed=0,  # continuously live from config, never arrival-triggered (#757)
))

TILE_PRIORITY = register(VixTileSpec(
    name="priority", core="priority",
    description="Points.md #730: arbitrates competing arrivals across "
                 "up to 4 real directions -- strict rank (scheduling_"
                 "mode=0, 0=highest) or weighted round-robin "
                 "(scheduling_mode=1, higher=more weight). Confirmed "
                 "against priority_cell_v4c.v directly: upstream_mask "
                 "and downstream_mask are swapped in bit position "
                 "relative to every OTHER core's own convention "
                 "([5:0]=upstream here, not downstream) -- a real, "
                 "confirmed fact from the actual RTL, not an assumption "
                 "carried over from the other tiles' own shape. One "
                 "real 'in' port, fanned out to however many real "
                 "directions this instance actually arbitrates between "
                 "(e.g. [\"n\",\"s\"]) -- the same real, generic "
                 "one-port-several-directions mechanism `_resolve()` "
                 "already provides, not four separate, redundant ports "
                 "for what is really one shared field.",
    ports=[TilePort("in", "in", "upstream_mask"), TilePort("out", "out", "downstream_mask")],
    param_names=["priority_rank_n", "priority_rank_s", "priority_rank_e", "priority_rank_w",
                 "scheduling_mode"],
))
