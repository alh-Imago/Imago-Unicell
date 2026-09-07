"""
training_bucket_export_v1.py — the real, minimal first slice of the AI
training buckets (`points.md #510`/`#511`, scoped in `docs/stripped-
cell/design-notes/ai_training_buckets_scope.md`, `#676`-`#680`).

Walks already-existing, already-tested registries -- `tile_source_
registry_v1.py`'s own self-registering tile sources, and `workbench_
v1.py`'s own `DEMOS` dict -- and emits ONE canonical, model-consumable
JSON record PER TILE/DEMO, one file per bucket, matching `#680`'s own
real area-partition decision: a new tile that registers itself becomes
a new bucket file automatically, next export run, with zero changes
needed here; an existing tile's own changed behavior only ever
regenerates its own one file.

REAL, HONEST SCOPE, stated plainly rather than silently overreached:

1. **Tier-1 composed tiles ARE now covered** (`export_tier1_tile()`,
   `points.md #682`) — in their own separate `tiles_composed/` bucket
   area, not mixed into Tier-0's `tiles/`, since `composed_tile_
   library_v1.py` is a genuinely different registry/resolution
   mechanism (confirmed directly against `tile_source_registry_v1.py`'s
   own docstring: Tier-1 tiles are never registered into that generic
   hook at all). A composed tile whose own subcells resolve entirely
   through `bucket == "super_records"` sources (recursively, through
   any real nesting) gets a real, actually-executed, multi-cell VM
   trace; one that transitively includes any other bucket kind (e.g.
   `dsp_add_and_hold`'s own real DSP-wrapper subcell) gets real, static
   metadata only, same honest-scope discipline as Tier-0's own
   `dsp-wrapper` sources.

2. **Only "super_records"-bucket tile sources get a REAL, actually-
   executed VM trace.** A tile source's own `bucket` field (`#485`)
   names which real output list it belongs to -- `super_records`
   (runnable through the plain `SuperGrid`/`VMSession`, e.g. Tier-0
   primitives) vs. `dsp_wrapper_records` (a genuinely different
   execution model, real hard-IP, `DspWrapperGrid`). Only the former
   gets a real trace here; the latter gets real, static metadata only,
   with an explicit, honest note why -- not a silently faked trace.

3. **Demos get real, static metadata plus a real, actually-compiled
   ICM record (proving the source genuinely still compiles), but NOT
   a generic injected runtime trace.** `workbench_v1.py`'s own `DEMOS`
   entries expose named ports via `expose()`, and there is no generic
   name-to-injection mechanism for arbitrary demos yet (the same real
   gap `AutoSizedVM.inject_named()`, `#667`/`#669`, only solves for
   ICM-derived single-program sessions, not multi-cell demo programs
   in general) -- real, separate, unbuilt future work.

Real, deliberate choice, matching every other tool in this project:
stdlib-only, no external dependency.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tile_source_registry_v1 import all_sources, find_source_for, TileSource
from vm_ai_port_v1 import VMSession, CompileFailure
from unicell_super_automaton_v1 import SuperGrid, SuperCell
from unicell_automaton_v1 import N, S, E, W
from super_tile_library_v1 import super_tile_library
from composed_tile_library_v1 import (
    composed_tile_library, ComposedTileSpec, place_composed, _resolve_subcell_leaf,
)
import workbench_v1

_DIR_LETTERS = ["n", "s", "e", "w"]
_DIR_CONST = {"n": N, "s": S, "e": E, "w": W}

# Real, small, deterministic, mutually-distinguishable test values --
# not random, so a bucket's own trace is exactly reproducible run to
# run (the same real discipline every VM test in this project already
# uses: a fixed injection sequence, not a randomized one).
_TEST_VALUES = [5, 3, 7, 2]


def _assign_directions(port_names: List[str]) -> Dict[str, str]:
    """Real, honest, generic direction assignment -- cycles n/s/e/w by
    port order. Every real Tier-0 tile registered today has at most 4
    ports (branch, the widest, has exactly 4) -- a genuine, physical
    ceiling this function makes explicit rather than silently
    truncating past it."""
    if len(port_names) > 4:
        raise ValueError(
            f"cannot auto-assign directions for {len(port_names)} ports "
            f"(a real physical cell has only 4 cardinal neighbors): {port_names}"
        )
    return {name: _DIR_LETTERS[i] for i, name in enumerate(port_names)}


def _default_param_value(_param_name: str) -> int:
    """Real, honest, simple default -- checked directly against every
    real `SuperTileSpec.param_names` use in this project today (all
    numeric/hex, e.g. `topology`, `init_data`, `threshold`, `rolling_
    mode`): 0 is a valid value for every one of them. Not claimed to
    be a MEANINGFUL default (a tile's own description explains what
    each param actually does), only a real, valid, always-safe one."""
    return 0


def export_tier0_tile(source: TileSource, tile_name: str) -> Dict[str, Any]:
    """One real, complete bucket record for a single tile-registry
    entry -- static metadata always; a real, actually-executed VM
    trace only for `bucket == "super_records"` sources (see module
    docstring, point 2)."""
    tile = source.library.get(tile_name)
    port_names = tile.port_names()
    directions = _assign_directions(port_names)
    params = {name: _default_param_value(name) for name in tile.param_names}

    record: Dict[str, Any] = {
        "bucket": "tiles",
        "source_kind": source.kind,
        "name": tile.name,
        "core": getattr(tile, "core", None),
        "description": tile.description,
        "ports": [
            {"name": p.name, "kind": p.kind, "direction": directions[p.name]}
            for p in tile.ports
        ],
        "params": params,
        "proven": getattr(tile, "proven", None),
        "target": getattr(tile, "target", None),
    }

    if source.bucket != "super_records":
        record["trace"] = None
        record["trace_note"] = (
            f"real, honest scope: bucket {source.bucket!r} isn't runnable "
            "through the plain SuperGrid/VMSession this exporter drives -- "
            "static metadata only; a real VM trace for this bucket kind is "
            "separate, unbuilt future work, not silently faked here."
        )
        return record

    icm_record = source.place_fn(tile, 0, 0, directions, params or None)
    # Real, deliberate choice, found while building this exporter:
    # `icm_record.to_dict()` packs into the compact SUPER_LATCH hex
    # format via `pack_core_config()`, which only converts a field's
    # own direction-LIST value into a mask for fields listed in
    # `icm_v3._DIR_FIELDS[core_select]` -- nano's own `routing_mask`/
    # `cardinal_edge` (6-bit, 3D-ready) and branch's `route_low`/
    # `route_equal`/`route_high` are deliberately NOT in that list
    # (they need a different packing than a plain 4-bit one-hot), so
    # calling `to_dict()` directly on a raw `place()` result -- before
    # the normal DSL-compiler pipeline's own `dm()` normalization runs
    # -- fails for exactly those tiles. `SuperCell.from_record()`
    # (below) already does its own correct normalization internally,
    # confirmed working for every tile including these; this exporter
    # doesn't need the packed hex at all, only the real, human/model-
    # readable field values, so it reads them directly rather than
    # routing through `to_dict()`'s own narrower real assumption.
    session = VMSession(SuperGrid([]))
    session.grid.cells[(0, 0)] = SuperCell.from_record(icm_record)

    trace: List[Dict[str, Any]] = []
    trace.append({"step": "initial", "state": session.describe_cell(0, 0)})

    in_ports = [p for p in tile.ports if p.kind == "in"]
    for i, port in enumerate(in_ports):
        value = _TEST_VALUES[i % len(_TEST_VALUES)]
        direction = directions[port.name]
        accepted, _forward = session.deliver(
            0, 0, {_DIR_CONST[direction]: value}, None
        )
        trace.append({
            "step": f"deliver {port.name} (dir={direction}) = {value}",
            "accepted": accepted,
            "state": session.describe_cell(0, 0),
        })
        # Real, deliberate choice: a real tick after EACH delivered
        # port, not just at the end. Several real cores (accumulator
        # in particular) treat same-tick arrivals on two different
        # ports as a genuine simultaneous event with its own real,
        # different semantics (inc+dec in the same tick nets to zero,
        # per `UNICELL_S_DSL_MANUAL.md` -- confirmed directly while
        # building this exporter, not assumed). Ticking between
        # deliveries keeps this first slice's own trace legible --
        # one port's own real, isolated effect per step -- and defers
        # deliberately exercising the simultaneous-arrival edge case
        # to real, separate future bucket work, rather than producing
        # a trace whose own numbers look wrong without that context.
        session.tick(1)
        trace.append({"step": f"tick after {port.name}", "state": session.describe_cell(0, 0)})

    # A few real settle ticks after every input has arrived -- real,
    # bounded (not run_to_quiescence(), since a continuously-live core
    # like accumulator/latch never quiesces by construction, `#676`'s
    # own real finding, and this exporter must never hang).
    for t in range(3):
        session.tick(1)
        trace.append({"step": f"tick {t + 1}", "state": session.describe_cell(0, 0)})

    record["icm_record"] = {
        "cell_id": icm_record.cell_id,
        "row": icm_record.row,
        "col": icm_record.col,
        "core": icm_record.core,
        "core_config": icm_record.core_config,
        "addon_config": icm_record.addon_config,
    }
    record["trace"] = trace
    return record


# ── Tier-1 composed tiles (`points.md #682`) ─────────────────────────

def _leaf_bucket(tile_name: str) -> str:
    """Mirrors `composed_tile_library_v1._resolve_subcell_leaf()`'s own
    real resolution order exactly (Tier-0 library checked first, then
    the generic tile-source registry) -- but returns the real `bucket`
    name instead of the resolved tile, since that's all a leaf-bucket
    check needs."""
    if tile_name in super_tile_library.names():
        return "super_records"
    source = find_source_for(tile_name)
    if source is not None:
        return source.bucket
    raise ValueError(f"unknown leaf tile {tile_name!r}")


def _composed_tile_buckets(tile: ComposedTileSpec) -> Set[str]:
    """Recursively collects every real bucket kind used anywhere inside
    a composed tile, through any real nesting -- the generic, correct
    way to answer "is this whole tile runnable through the plain
    SuperGrid/VMSession," matching Tier-0's own per-source bucket
    check, generalized to a tree instead of one leaf."""
    buckets: Set[str] = set()
    for sub in tile.subcells:
        nested = (composed_tile_library.get(sub.tile_name)
                  if sub.tile_name in composed_tile_library.names() else None)
        if nested is not None:
            buckets |= _composed_tile_buckets(nested)
        else:
            buckets.add(_leaf_bucket(sub.tile_name))
    return buckets


def _required_composed_params(tile: ComposedTileSpec) -> List[str]:
    """Recursively computes every real, still-required namespaced
    param name a composed tile needs from its own caller -- walking
    the exact same subcell tree `place_composed()` itself walks, real
    nesting included, so a nested composed sub-cell's own required
    inner params surface correctly double-namespaced (matching
    `#342`'s own real 's1.cmp.threshold' precedent). A `fixed_params`
    entry on any subcell (leaf or nested) removes exactly the param it
    names, the same real "fixed always wins" rule `place_composed()`
    itself applies.

    Real, necessary extension (`#686`): a PRELOAD-ONLY sub-cell
    (`preload_param_name` set) contributes its own required param too
    -- but BARE, not namespaced, matching `place_composed()`'s own real
    convention that a preload param is whole-tile-scope (`select`'s
    `true_val`/`false_val`), not per-subcell. A sub-cell with `preload_
    fixed_value` set instead needs nothing from the caller at all."""
    required: List[str] = []
    for sub in tile.subcells:
        if sub.preload_param_name is not None:
            required.append(sub.preload_param_name)
            continue
        if sub.preload_fixed_value is not None:
            continue
        nested = (composed_tile_library.get(sub.tile_name)
                  if sub.tile_name in composed_tile_library.names() else None)
        if nested is not None:
            inner_names = _required_composed_params(nested)
        else:
            leaf_tile, _place_fn = _resolve_subcell_leaf(sub.tile_name, super_tile_library)
            inner_names = list(leaf_tile.param_names)
        for name in inner_names:
            if name in sub.fixed_params:
                continue
            required.append(f"{sub.name}.{name}")
    return required


def _assign_composed_directions(tile: ComposedTileSpec) -> Dict[str, str]:
    """Real, generic direction assignment for a composed tile's own
    EXTERNAL ports -- grouped by which immediate subcell each port
    belongs to (`tile.external_ports[name] = (subcell_name, ...)`),
    cycling n/s/e/w WITHIN each group. Unlike a single Tier-0 cell, a
    composed tile's total external port count isn't capped at 4 (real
    example: `dual_threshold_monitor` has 6) -- different subcells are
    different physical cells, so directions may genuinely repeat
    ACROSS groups. Confirmed correct against every composed tile
    registered today: no single subcell exposes more than 4 of its own
    ports externally (the same real per-cell ceiling `#676`'s own
    Tier-0 exporter already found), so within-group cycling never
    exceeds it.

    Real, necessary correction (`#686`): a subcell can ALSO have real,
    internally-fixed directions (`SubCellPlacement.internal_
    directions`, e.g. `select`'s own `mask` subcell fixes `in_b` to
    face its real north neighbor, `zero_const`) -- those directions are
    already spoken for on THIS subcell and must be excluded from the
    cycle, or an external port could collide with an internal one onto
    the very same physical side (confirmed as a real bug while building
    `select`'s own export: `cond` was auto-assigned 'n', the exact same
    side `mask`'s own fixed `in_b` already used, corrupting the
    two-stage capture entirely)."""
    by_subcell: Dict[str, List[str]] = {}
    for port_name, (subcell_name, _subcell_port) in tile.external_ports.items():
        by_subcell.setdefault(subcell_name, []).append(port_name)

    subcells_by_name = {s.name: s for s in tile.subcells}

    directions: Dict[str, str] = {}
    for subcell_name, port_names in by_subcell.items():
        used = set()
        for value in subcells_by_name[subcell_name].internal_directions.values():
            if isinstance(value, list):
                used.update(value)
            else:
                used.add(value)
        available = [d for d in _DIR_LETTERS if d not in used]
        if len(port_names) > len(available):
            raise ValueError(
                f"composed tile {tile.name!r}: subcell {subcell_name!r} exposes "
                f"{len(port_names)} external ports but only {len(available)} real "
                f"cardinal sides remain free ({used} already internally fixed): "
                f"{sorted(port_names)}"
            )
        for i, name in enumerate(sorted(port_names)):
            directions[name] = available[i]
    return directions


def _resolve_port_absolute(
    tile: ComposedTileSpec, port_name: str, anchor_row: int, anchor_col: int,
    direction: str,
) -> Tuple[int, int, str, str]:
    """Real, recursive resolution of one composed tile's own external
    port to an absolute (row, col, direction, in/out-kind) -- recurses
    through nested composed sub-cells exactly the way `place_composed()`
    itself does when wiring a nested tile's own directions through,
    so a `twin_sentinel`-style port (mapping into a NESTED sentinel,
    not a leaf cell directly) resolves correctly to the real leaf cell
    underneath it, not the intermediate composed sub-cell."""
    subcell_name, subcell_port = tile.external_ports[port_name]
    sub = next(s for s in tile.subcells if s.name == subcell_name)
    abs_row, abs_col = anchor_row + sub.offset[0], anchor_col + sub.offset[1]

    nested = (composed_tile_library.get(sub.tile_name)
              if sub.tile_name in composed_tile_library.names() else None)
    if nested is not None:
        return _resolve_port_absolute(nested, subcell_port, abs_row, abs_col, direction)

    leaf_tile, _place_fn = _resolve_subcell_leaf(sub.tile_name, super_tile_library)
    kind = next(p.kind for p in leaf_tile.ports if p.name == subcell_port)
    return abs_row, abs_col, direction, kind


def export_tier1_tile(tile_name: str) -> Dict[str, Any]:
    """One real, complete bucket record for a single Tier-1 composed-
    tile entry -- static metadata always; a real, actually-executed,
    genuinely multi-cell VM trace only when every real leaf underneath
    it (through any nesting) resolves to a `super_records` bucket (see
    module docstring, point 1)."""
    tile = composed_tile_library.get(tile_name)
    directions = _assign_composed_directions(tile)
    required_params = _required_composed_params(tile)
    params = {name: _default_param_value(name) for name in required_params}

    record: Dict[str, Any] = {
        "bucket": "tiles_composed",
        "name": tile.name,
        "description": tile.description,
        "external_ports": [
            {"name": name, "subcell": tile.external_ports[name][0],
             "subcell_port": tile.external_ports[name][1], "direction": directions[name]}
            for name in tile.port_names()
        ],
        "params": params,
        "proven": tile.proven,
        "target": tile.target,
        "subcell_tile_names": sorted({s.tile_name for s in tile.subcells}),
    }

    used_buckets = _composed_tile_buckets(tile)
    if used_buckets != {"super_records"}:
        record["trace"] = None
        record["trace_note"] = (
            f"real, honest scope: this composed tile transitively uses bucket "
            f"kind(s) {sorted(used_buckets)}, not just 'super_records' -- not "
            "runnable through the plain SuperGrid/VMSession this exporter "
            "drives; static metadata only, same honest-scope discipline as "
            "Tier-0's own non-super_records sources."
        )
        return record

    preloads: List[Tuple[int, int, int]] = []
    records = place_composed(tile, 0, 0, directions, params or None, preloads=preloads)
    session = VMSession(SuperGrid([]))
    for rec in records:
        session.grid.cells[(rec.row, rec.col)] = SuperCell.from_record(rec)

    trace: List[Dict[str, Any]] = []
    if preloads:
        # Real, necessary sequence (#686): freeze the whole grid, seed
        # every preload-only sub-cell directly, unfreeze, then let the
        # preloaded constants fully settle -- one tick only OFFERS a
        # preloaded value, a second is needed for a real neighbor to
        # actually CAPTURE it (confirmed empirically while building
        # `select`/`icmp_eq`/`icmp_ne`) -- BEFORE any live/dynamic
        # external port gets delivered below, so a live operand never
        # races a still-in-flight constant.
        session.grid.freeze_all()
        for r, c, v in preloads:
            session.grid.preload_ram_flowing(r, c, v)
        session.grid.unfreeze_all()
        session.tick(2)
        trace.append({"step": "preload+unfreeze+settle", "state": session.describe()})
    else:
        trace.append({"step": "initial", "state": session.describe()})

    resolved_ports = [
        (name, *_resolve_port_absolute(tile, name, 0, 0, directions[name]))
        for name in tile.external_ports  # real dict insertion (declaration) order --
                                          # more legible trace narrative than
                                          # port_names()'s own alphabetical sort,
                                          # which is still used for the metadata
                                          # listing above (a stable, sorted index
                                          # is the right shape there, declaration
                                          # order is the right shape for a trace).
    ]
    in_ports = [(name, row, col, direction) for name, row, col, direction, kind in resolved_ports
                if kind == "in"]
    for i, (name, row, col, direction) in enumerate(in_ports):
        value = _TEST_VALUES[i % len(_TEST_VALUES)]
        accepted, _forward = session.deliver(row, col, {_DIR_CONST[direction]: value}, None)
        trace.append({
            "step": f"deliver {name} (at {row},{col} dir={direction}) = {value}",
            "accepted": accepted,
            "state": session.describe(),
        })
        # Real, bounded settle window after EACH injected port, not
        # just one tick -- a multi-cell composed tile needs a real
        # tick per physical hop for a change to propagate (acc -> cmp
        # -> lat is two real hops), confirmed empirically while
        # building this exporter: one tick alone left later stages
        # mid-flight when the NEXT port's own injection landed,
        # producing a real but confusing chain-timing artifact. Three
        # ticks is enough for every composed tile registered today
        # (none deeper than two real hops); still bounded, never
        # run_to_quiescence().
        for t in range(3):
            session.tick(1)
        trace.append({"step": f"settle after {name}", "state": session.describe()})

    # Real, bounded settle ticks, same real reason as Tier-0: several
    # of these tiles (sentinel, dual_threshold_monitor) contain real,
    # continuously-live cores (accumulator/latch) that never quiesce
    # by construction -- run_to_quiescence() would hang, so this stays
    # a fixed, bounded loop.
    for t in range(5):
        session.tick(1)
        trace.append({"step": f"tick {t + 1}", "state": session.describe()})

    record["records"] = [
        {"cell_id": r.cell_id, "row": r.row, "col": r.col, "core": r.core,
         "core_config": r.core_config, "addon_config": r.addon_config}
        for r in records
    ]
    record["trace"] = trace
    return record


def export_demo(name: str) -> Dict[str, Any]:
    """One real bucket record for a `workbench_v1.DEMOS` entry --
    real, static metadata plus a real, actually-compiled ICM record
    (proving the source still genuinely compiles), no generic injected
    trace (see module docstring, point 3)."""
    demo = workbench_v1.DEMOS[name]
    record: Dict[str, Any] = {
        "bucket": "demos",
        "name": name,
        "description": demo["description"],
        "language": demo["language"],
        "source": demo["source"],
    }
    try:
        if demo["language"] == "dsl":
            session = VMSession.from_dsl(demo["source"])
        else:
            session = VMSession.from_python(demo["source"])
        record["compiles"] = True
        record["cell_count"] = session.describe()["cell_count"]
    except CompileFailure as exc:
        record["compiles"] = False
        record["compile_error"] = [d.problem for d in exc.diagnostics]
    return record


def export_all(output_dir: str) -> Dict[str, Any]:
    """Writes one real JSON file per tile/composed-tile/demo into
    `output_dir/tiles/`, `output_dir/tiles_composed/`, and `output_dir/
    demos/`, plus a real `manifest.json` index, regenerated fresh every
    run -- never hand-maintained, matching `#680`'s own real
    area-partition decision."""
    tiles_dir = os.path.join(output_dir, "tiles")
    tiles_composed_dir = os.path.join(output_dir, "tiles_composed")
    demos_dir = os.path.join(output_dir, "demos")
    os.makedirs(tiles_dir, exist_ok=True)
    os.makedirs(tiles_composed_dir, exist_ok=True)
    os.makedirs(demos_dir, exist_ok=True)

    manifest: Dict[str, Any] = {"tiles": [], "tiles_composed": [], "demos": []}

    for source in all_sources():
        for tile_name in sorted(source.library.names()):
            record = export_tier0_tile(source, tile_name)
            path = os.path.join(tiles_dir, f"{tile_name}.json")
            with open(path, "w") as f:
                json.dump(record, f, indent=2, default=str)
            manifest["tiles"].append({
                "name": tile_name, "source_kind": source.kind,
                "file": os.path.relpath(path, output_dir),
            })

    for tile_name in sorted(composed_tile_library.names()):
        record = export_tier1_tile(tile_name)
        path = os.path.join(tiles_composed_dir, f"{tile_name}.json")
        with open(path, "w") as f:
            json.dump(record, f, indent=2, default=str)
        manifest["tiles_composed"].append({
            "name": tile_name, "file": os.path.relpath(path, output_dir),
        })

    for demo_name in sorted(workbench_v1.DEMOS):
        record = export_demo(demo_name)
        path = os.path.join(demos_dir, f"{demo_name}.json")
        with open(path, "w") as f:
            json.dump(record, f, indent=2, default=str)
        manifest["demos"].append({
            "name": demo_name, "file": os.path.relpath(path, output_dir),
        })

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "training_buckets"
    result = export_all(out)
    print(f"Wrote {len(result['tiles'])} tile buckets, "
          f"{len(result['tiles_composed'])} composed-tile buckets, and "
          f"{len(result['demos'])} demo buckets to {out}/")
