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

1. **Tier-1 COMPOSED tiles are NOT covered here.** Confirmed directly
   against `tile_source_registry_v1.py`'s own docstring, not assumed:
   Tier-1 tiles (`composed_tile_library_v1.py` -- `sentinel`, `dual_
   threshold_monitor`, `twin_sentinel`, the loop tiles) are a
   genuinely separate library, never registered into the generic
   `tile_source_registry_v1` hook at all ("Tier-1 composed tiles...
   remain super-tile-only sub-cells for now"). Exporting them
   generically needs real, separate design work -- multi-cell
   auto-placement plus a way to pick canonical parameter values per
   tile (the same class of problem `composer_full_editor_scope.md`
   already flagged for a different reason) -- real, future work, not
   attempted in this first slice.

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
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tile_source_registry_v1 import all_sources, TileSource
from vm_ai_port_v1 import VMSession, CompileFailure
from unicell_super_automaton_v1 import SuperGrid, SuperCell
from unicell_automaton_v1 import N, S, E, W
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
    """Writes one real JSON file per tile/demo into `output_dir/tiles/`
    and `output_dir/demos/`, plus a real `manifest.json` index,
    regenerated fresh every run -- never hand-maintained, matching
    `#680`'s own real area-partition decision."""
    tiles_dir = os.path.join(output_dir, "tiles")
    demos_dir = os.path.join(output_dir, "demos")
    os.makedirs(tiles_dir, exist_ok=True)
    os.makedirs(demos_dir, exist_ok=True)

    manifest: Dict[str, Any] = {"tiles": [], "demos": []}

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
    print(f"Wrote {len(result['tiles'])} tile buckets and "
          f"{len(result['demos'])} demo buckets to {out}/")
