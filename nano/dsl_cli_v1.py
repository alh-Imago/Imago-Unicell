#!/usr/bin/env python3
"""
dsl_cli_v1.py — command-line entry point for the Unicell-S DSL
compiler. Per Alan (2026-08-16): the full "design your own tile" system
is the composer's job (Stage 5, later work) -- what's needed on the
compiler side NOW is "even just an open port via a command line switch,
'use this model' kind of thing." This is that switch: `--model FILE`.

Usage:
    python3 dsl_cli_v1.py program.uc
    python3 dsl_cli_v1.py program.uc --model my_tile.json -o out.icm
    python3 dsl_cli_v1.py program.uc --model a.json --model b.json

`--model` may be given more than once. Each file is loaded via
`user_tile_loader_v1.load_composed_tile()` (a plain JSON mirror of
`ComposedTileSpec`) and registered into a fresh `ComposedTileLibrary`
that falls back to the real built-in `composed_tile_library` for
everything it doesn't itself define (`#345`'s own parent-chaining) -- a
user model SHADOWS a same-named built-in, since an explicit `--model`
load is a deliberate override, not an accident.

Diagnostics print via `CompileDiagnostic.format()` with the real source
lines shown inline, and the process exits non-zero on any compile
error -- the CLI is meant to be scriptable (CI, a build step, whatever
composer eventually calls into), not just interactively friendly.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dsl_compiler_v1 import compile_source
from composed_tile_library_v1 import composed_tile_library, ComposedTileLibrary
from user_tile_loader_v1 import load_composed_tile


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="dsl_cli_v1.py",
        description="Compile a Unicell-S DSL program to a real ICM v3 file.",
    )
    parser.add_argument("source", help="path to the .uc DSL source file")
    parser.add_argument("--model", action="append", default=[], metavar="FILE",
                         help="load a user-authored composed-tile JSON file "
                              "(repeatable); shadows a same-named built-in tile")
    parser.add_argument("-o", "--output", metavar="FILE",
                         help="where to write the compiled .icm file "
                              "(default: <source>.icm)")
    args = parser.parse_args(argv)

    try:
        with open(args.source) as f:
            source_text = f.read()
    except OSError as e:
        print(f"error: could not read {args.source!r}: {e}", file=sys.stderr)
        return 2

    library = composed_tile_library
    if args.model:
        library = ComposedTileLibrary(parent=composed_tile_library)
        for model_path in args.model:
            try:
                tile = load_composed_tile(model_path)
            except ValueError as e:
                print(f"error loading model {model_path!r}: {e}", file=sys.stderr)
                return 2
            try:
                library.register(tile)
            except ValueError as e:
                print(f"error registering model {model_path!r}: {e}", file=sys.stderr)
                return 2
            print(f"loaded user model '{tile.name}' from {model_path}", file=sys.stderr)

    program_name = os.path.splitext(os.path.basename(args.source))[0]
    icm, diagnostics = compile_source(source_text, program_name_hint=program_name,
                                       composed_library=library)

    source_lines = source_text.splitlines()
    for d in diagnostics:
        print(d.format(source_lines), file=sys.stderr)
        print(file=sys.stderr)

    if icm is None:
        n = sum(1 for d in diagnostics if d.severity == "error")
        print(f"compile failed: {n} error(s)", file=sys.stderr)
        return 1

    output_path = args.output or (os.path.splitext(args.source)[0] + ".icm")
    icm.save(output_path)
    print(f"compiled '{program_name}' -> {output_path} ({len(icm.records)} cell(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
