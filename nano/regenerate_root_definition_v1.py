#!/usr/bin/env python3
"""
regenerate_root_definition_v1.py — regenerates `nano/root_definition.json`
from the RTL's own field-map comments, and/or checks that the persisted
file is still up to date with them. Run this whenever the RTL's own
field-map comments change (`points.md #216` item 1's own framing: "the
VM reads, or HAS GENERATED, a file that reflects the actual base cell's
Verilog exactly" -- this is that generation step, made real and
re-runnable, not a one-off manual JSON dump).

Usage:
    python3 nano/regenerate_root_definition_v1.py            # regenerate
    python3 nano/regenerate_root_definition_v1.py --check    # verify only,
                                                               # non-zero exit
                                                               # if stale
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from root_definition_extractor_v1 import extract_all

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "root_definition.json")


def build_json(repo_root: str) -> dict:
    result = extract_all(repo_root)
    out = {}
    for core, rd in result.items():
        out[core] = {
            "source_file": rd.source_file,
            "fields": [
                {"name": f.name, "hi": f.hi, "lo": f.lo, "description": f.description}
                for f in rd.fields
            ],
        }
    return out


def main(argv=None) -> int:
    check_only = "--check" in (argv if argv is not None else sys.argv[1:])
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    fresh = build_json(repo_root)

    if check_only:
        try:
            with open(OUTPUT_PATH) as f:
                current = json.load(f)
        except FileNotFoundError:
            print(f"STALE: {OUTPUT_PATH} does not exist -- run without --check to generate it")
            return 1
        if current != fresh:
            print(f"STALE: {OUTPUT_PATH} no longer matches the RTL's own field-map comments -- "
                  f"run without --check to regenerate")
            return 1
        print(f"OK: {OUTPUT_PATH} matches the RTL exactly")
        return 0

    with open(OUTPUT_PATH, "w") as f:
        json.dump(fresh, f, indent=2)
    print(f"wrote {OUTPUT_PATH} ({sum(len(v['fields']) for v in fresh.values())} fields total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
