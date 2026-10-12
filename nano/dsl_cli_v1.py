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


def _uses_family(source_text):
    """True when a `place` carries a `family:` field (read from the parsed program, so a comment that mentions it does not count)."""
    from dsl_lexer_v1 import tokenize
    from dsl_parser_v1 import parse_source
    tokens, diags = tokenize(source_text)
    if diags:
        return False
    prog, _ = parse_source(tokens)
    return prog is not None and any(f.key == "family" for st in prog.statements for f in getattr(st, "fields", []))


def _compile_vix(args, source_text, program_name):
    """ledger #1115: the VIX backend. Writes ICM-VIX (placements carry the family tags)."""
    from dsl_lexer_v1 import tokenize
    from dsl_parser_v1 import parse_source
    from vix_compiler_v1 import compile_program_ir_vix
    lines = source_text.splitlines()
    tokens, diags = tokenize(source_text)
    prog = None
    if not diags:
        prog, diags = parse_source(tokens)
    if prog is not None and not any(d.severity == "error" for d in diags):
        icm, d2 = compile_program_ir_vix(prog, program_name_hint=program_name, target=args.target)
        diags = list(diags) + list(d2)
    else:
        icm = None
    for d in diags:
        print(d.format(lines), file=sys.stderr)
        print(file=sys.stderr)
    if icm is None:
        print(f"compile failed: {sum(1 for d in diags if d.severity == 'error')} error(s)", file=sys.stderr)
        return 1
    out = args.output or (os.path.splitext(args.source)[0] + ".icm-hier.json")
    icm.save(out)
    fams = sorted({p.family for p in icm.placements if p.family})
    print(f"compiled '{program_name}' -> {out} ({len(icm.flatten()[0])} cell(s); VIX backend" + (f"; families: {', '.join(fams)}" if fams else "") + ")")
    return 0


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
    parser.add_argument("--target", choices=["std", "vixen", "flex", "sub"], default=None,
                         help="ledger #1115: compile with the VIX backend and write an ICM-VIX file (.icm-hier.json), the form that can carry `family: flex|sub` on a place "
                              "(a block built from the sub or flex cells; the assembler inserts the sub bridge where two families meet). The named target decides which optional "
                              "features are refused at compile time. A program that uses `family:` is compiled this way even without --target.")
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
    if args.target or _uses_family(source_text):
        return _compile_vix(args, source_text, program_name)
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
