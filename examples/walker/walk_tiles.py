#!/usr/bin/env python3
"""
walk_tiles.py — expand UniCell tiles (or your own models) into raw .icm files

Walks the TileLibrary, compiles each tile to its NOR-cell network, and writes a
raw .icm (JSON) per tile into examples/tiles/. Those .icm files load directly
into the composer (composer/unicell_composer.html -> "load") as an inspectable
grid of cells — a palette of primitives you can see the format of and wire
together. No HTML embedding, so the composer stays lean.

WHY A WALKER, NOT A STATIC DUMP: ship the tool and you can expand whatever you
want, whenever you want — the built-in tiles, a subset, or your OWN tile
builder — and regenerate after any change. Static files go stale; a walker
does not.

By default it emits only the FUNCTIONAL tiles (arithmetic, compare, select,
counters, latches). The big I/O handler tiles (DISPLAY_HANDLER ~18,600 cells,
audio/keyboard/network/storage/sensor handlers) are skipped — they are large,
not useful as composer building blocks, and would just bloat the repo. Use
--all to include them.

USAGE
    python3 examples/walker/walk_tiles.py                # functional tiles -> examples/tiles/
    python3 examples/walker/walk_tiles.py --list         # list what would be emitted
    python3 examples/walker/walk_tiles.py --tile MIF_MUX # one tile
    python3 examples/walker/walk_tiles.py --all          # include I/O handlers
    python3 examples/walker/walk_tiles.py --max-cells 1000   # only tiles under N cells
    python3 examples/walker/walk_tiles.py --out path/    # custom output dir
    python3 examples/walker/walk_tiles.py --builder mymod:make_my_tile  # YOUR own tile

Caveat: tiles built from preloaded-A selection (the MUX family) carry their
records and a preload_map, but preload resolution happens at composition/run
time. These .icm are faithful for INSPECTION and WIRING; a lone tile is a
building block, not a standalone runnable program (it needs inputs fed).
"""

import os
import sys
import json
import time
import hashlib
import argparse
import importlib

# repo root = two levels up from this file (examples/walker/walk_tiles.py)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from fp_tiles import TileLibrary

# Tiles skipped by default: big I/O handlers (bloat, not building blocks) and
# the deprecated CLA adder (use INT32_ADD / Kogge-Stone instead).
SKIP_SUFFIXES = ("_HANDLER",)
SKIP_NAMES = {"INT32_ADD_CLA"}


def records_to_dicts(records):
    """CellMapRecord list -> JSON dicts. Mirrors bootloader/generate_icms.py."""
    out = []
    for r in records:
        out.append({
            "gs":   getattr(r, "gate_state",      0),
            "in":   getattr(r, "input_address",   0),
            "out":  getattr(r, "output_address",  0),
            "inB":  getattr(r, "input_b_address", None),
            "init": getattr(r, "initial_value",   None),
        })
    return out


def canon_records(rec_dicts):
    """
    Canonical record string, byte-for-byte identical to the composer's canonR
    (composer/unicell_composer.html):
        JSON.stringify(recs.map(r=>({gs:r.gs,in:r.in,init:r.init,out:r.out})))
    Field SUBSET and ORDER are {gs, in, init, out} — note: NO inB, and init
    before out. JS JSON.stringify emits no whitespace, so separators must be
    (",", ":"). init=None serialises to null, matching JS.
    """
    canon = [{"gs": r["gs"], "in": r["in"], "init": r["init"], "out": r["out"]}
             for r in rec_dicts]
    return json.dumps(canon, separators=(",", ":"))


def record_hash(rec_dicts):
    """SHA-256 hex of the canonical record string — matches the composer + the
    runtime loader (controller.py) so strict loaders accept the .icm and the
    composer verifies clean ('hash verified ✓')."""
    return hashlib.sha256(canon_records(rec_dicts).encode("utf-8")).hexdigest()


def tile_to_icm(name, tile, budget=None):
    """Serialise a compiled tile to a raw .icm dict the composer can load."""
    records = tile.records
    in_a = list(getattr(tile, "in_a", []) or [])
    in_b = list(getattr(tile, "in_b", []) or [])
    out  = list(getattr(tile, "out", []) or [])

    # inputs/outputs as {name: first_bit_address} — what portRestoreFromICM wants.
    inputs = {}
    if in_a:
        inputs["a"] = in_a[0]
    if in_b:
        inputs["b"] = in_b[0]
    outputs = {"out": out[0]} if out else {}

    cell_count = len(records)
    rec_dicts = records_to_dicts(records)
    icm = {
        "format_version": 2,
        "address_width":  32,
        "program_id":     f"{name.lower()}_{format(int(time.time()), 'x')}",
        "name":           name,
        "source":         "tile_library",
        "os_name":        "Imago",
        "os_version":     "1.0",
        "created_at":     int(time.time()),
        "vm_only":        bool(budget) and cell_count > budget,
        "inputs":         inputs,
        "outputs":        outputs,
        "cell_count":     cell_count,
        "records":        rec_dicts,
        "record_hash":    record_hash(rec_dicts),
        "security_context": None,
        # Extra (composer ignores unknown fields): full i/o bit lists + preloads,
        # so nothing is lost for tiles that need preload resolution.
        "tile_meta": {
            "in_a": in_a, "in_b": in_b, "out": out,
            "pipeline_depth": getattr(tile.metadata, "pipeline_depth", None),
            "operation": getattr(tile.metadata, "operation", name),
        },
        "preload_map": getattr(tile, "preload_map", {}) or {},
    }
    return icm


def selectable_tiles(lib, include_handlers):
    names = sorted(lib._builders.keys())
    for n in names:
        if n in SKIP_NAMES:
            continue
        if not include_handlers and any(n.endswith(s) for s in SKIP_SUFFIXES):
            continue
        yield n


def _import_module(spec):
    """Import a module by dotted name OR by .py file path."""
    if spec.endswith(".py") or os.path.sep in spec:
        import importlib.util
        mod_name = os.path.splitext(os.path.basename(spec))[0]
        s = importlib.util.spec_from_file_location(mod_name, spec)
        mod = importlib.util.module_from_spec(s)
        s.loader.exec_module(mod)
        return mod
    return importlib.import_module(spec)


def _emit_tile(name, tile, out_dir, budget):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.icm")
    with open(path, "w") as f:
        json.dump(tile_to_icm(name, tile, budget), f, indent=2)
    return path, len(tile.records)


def _is_tile(obj):
    """A Tile quacks like one: has records + metadata."""
    return hasattr(obj, "records") and hasattr(obj, "metadata")


def main(argv=None):
    p = argparse.ArgumentParser(description="Expand UniCell tiles into raw .icm files.")
    p.add_argument("--out", default=os.path.join(REPO_ROOT, "examples", "tiles"),
                   help="output directory (default: examples/tiles/)")
    p.add_argument("--tile", help="emit a single named tile")
    p.add_argument("--all", action="store_true", help="include I/O handler tiles")
    p.add_argument("--max-cells", type=int, default=None,
                   help="only emit tiles with fewer than N cells")
    p.add_argument("--budget", type=int, default=None,
                   help="mark vm_only when cell_count exceeds this budget")
    p.add_argument("--list", action="store_true", help="list tiles, do not write")
    p.add_argument("--builder", help="expand YOUR own tile: module:function (no-arg builder returning a Tile)")
    p.add_argument("--module", help="expand a whole library FILE: import the module and emit an .icm for every make_* that returns a Tile (parallel to fp_tiles.py)")
    args = p.parse_args(argv)

    lib = TileLibrary()

    # User-supplied single builder: expand a model you wrote yourself.
    if args.builder:
        mod_name, _, fn_name = args.builder.partition(":")
        if not fn_name:
            p.error("--builder must be module:function")
        mod = _import_module(mod_name)
        tile = getattr(mod, fn_name)()
        name = getattr(tile.metadata, "operation", fn_name)
        path, cells = _emit_tile(name, tile, args.out, args.budget)
        print(f"wrote {path}  ({cells} cells)")
        return

    # User-supplied library FILE: emit an .icm for every make_* returning a Tile.
    # This is the alternate authoring route — one fp_tiles-style .py in, a set
    # of models out, no full compiler needed.
    if args.module:
        mod = _import_module(args.module)
        builders = [getattr(mod, n) for n in dir(mod)
                    if n.startswith("make_") and callable(getattr(mod, n))]
        written = 0
        for fn in builders:
            try:
                tile = fn()
            except TypeError:
                continue            # builder needs args — skip, not a no-arg model
            if not _is_tile(tile):
                continue
            name = getattr(tile.metadata, "operation", fn.__name__.replace("make_", ""))
            if args.list:
                print(f"  {name:24} {len(tile.records):7,} cells")
                continue
            path, cells = _emit_tile(name, tile, args.out, args.budget)
            written += 1
        if not args.list:
            print(f"wrote {written} model(s) from {args.module} to {args.out}")
        return

    if args.tile:
        names = [args.tile]
    else:
        names = list(selectable_tiles(lib, args.all))

    os.makedirs(args.out, exist_ok=True)
    written, skipped = 0, 0
    for name in names:
        try:
            tile = lib.get(name)
        except Exception as e:
            print(f"  skip {name}: {e}")
            continue
        cells = len(tile.records)
        if args.max_cells is not None and cells >= args.max_cells:
            skipped += 1
            continue
        if args.list:
            print(f"  {name:24} {cells:7,} cells  depth {getattr(tile.metadata,'pipeline_depth','?')}")
            continue
        path = os.path.join(args.out, f"{name}.icm")
        with open(path, "w") as f:
            json.dump(tile_to_icm(name, tile, args.budget), f, indent=2)
        written += 1

    if not args.list:
        print(f"wrote {written} .icm file(s) to {args.out}" +
              (f"  ({skipped} skipped over max-cells)" if skipped else ""))


if __name__ == "__main__":
    main()
