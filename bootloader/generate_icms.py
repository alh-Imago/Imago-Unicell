#!/usr/bin/env python3
"""
bootloader/generate_icms.py — Compile sentinel_core.py and ward_core.py
to .icm files and write them into bootloader/icm/.

Run from the repo root:
    python3 bootloader/generate_icms.py

Each function in sentinel_core.py and ward_core.py becomes its own .icm file:
    bootloader/icm/sentinel_<fn>.icm
    bootloader/icm/ward_<fn>.icm

The .icm format is JSON:
{
  "program_id":  "<name>_<hex timestamp>",
  "name":        "<fn_name>",
  "source":      "sentinel_core" | "ward_core",
  "os_name":     "Imago",
  "os_version":  "1.0",
  "created_at":  <unix timestamp>,
  "inputs":      {param_name: first_bit_address, ...},
  "outputs":     [bit_address, ...],
  "cell_count":  <int>,
  "records": [
    {"gs": <gate_state>, "in": <input_addr>, "out": <output_addr>,
     "inB": <input_b_addr|null>, "init": <initial_value|null>},
    ...
  ]
}
"""

import sys
import os
import ast
import json
import time

# Allow imports from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compiler_int32 import Int32Compiler
from fp_tiles import TileLibrary

ICM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icm")


def records_to_dicts(records):
    """Convert CellMapRecord list to JSON-serialisable dicts."""
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


def compile_source(src_path: str, prefix: str, lib: TileLibrary) -> list[dict]:
    """
    Compile every top-level function in src_path.
    Returns list of result dicts (one per function).
    """
    src = open(src_path).read()
    tree = ast.parse(src)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]

    results = []
    for fn in fns:
        name = fn.name
        icm_name = f"{prefix}_{name}"
        try:
            c = Int32Compiler(tile_library=lib)
            result = c.compile_int32_function(src, name)
            records, graph, input_map, output_addrs = result[0], result[1], result[2], result[3]

            # input_map: {param: [bit_addrs]} for int32, {param: addr} for 1-bit
            # Flatten to {param: first_addr} for the ICM header
            inputs_header = {}
            for param, val in input_map.items():
                if isinstance(val, list):
                    inputs_header[param] = val[0]
                else:
                    inputs_header[param] = val

            icm = {
                "program_id":  icm_name + "_" + hex(int(time.time()))[-6:],
                "name":        icm_name,
                "fn_name":     name,
                "source":      prefix,
                "os_name":     "Imago",
                "os_version":  "1.0",
                "created_at":  time.time(),
                "inputs":      inputs_header,
                "outputs":     output_addrs,
                "cell_count":  len(records),
                "records":     records_to_dicts(records),
            }
            results.append({"ok": True, "name": icm_name, "icm": icm,
                            "cell_count": len(records)})
        except Exception as e:
            results.append({"ok": False, "name": icm_name, "error": str(e)})

    return results


def main():
    os.makedirs(ICM_DIR, exist_ok=True)
    lib = TileLibrary()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sources = [
        (os.path.join(root, "sentinel_core.py"), "sentinel"),
        (os.path.join(root, "ward_core.py"),     "ward"),
    ]

    total_ok = 0
    total_err = 0

    for src_path, prefix in sources:
        print(f"\n── {prefix}_core.py ──────────────────────────────────")
        results = compile_source(src_path, prefix, lib)
        for r in results:
            if r["ok"]:
                icm_path = os.path.join(ICM_DIR, r["name"] + ".icm")
                with open(icm_path, "w") as f:
                    json.dump(r["icm"], f, indent=2)
                print(f"  OK   {r['name']:<40s}  {r['cell_count']:5d} cells  → {os.path.basename(icm_path)}")
                total_ok += 1
            else:
                print(f"  ERR  {r['name']:<40s}  {r['error']}")
                total_err += 1

    print(f"\n{'─'*60}")
    print(f"Generated {total_ok} ICM files  ({total_err} errors)")
    print(f"Output dir: {ICM_DIR}")

    if total_err:
        sys.exit(1)


if __name__ == "__main__":
    main()
