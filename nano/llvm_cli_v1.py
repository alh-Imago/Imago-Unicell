#!/usr/bin/env python3
"""
llvm_cli_v1.py — command-line entry point for the LLVM IR -> DAG compiler (points.md #823: the LLVM path, used
throughout #805-#822's DSP/BRAM fixed-structures work, had no CLI of its own -- `dsl_cli_v1.py` is the DSL's CLI,
a genuinely separate frontend). Mirrors `dsl_cli_v1.py`'s own shape directly: same diagnostic printing, same exit
codes, same "compiled -> path (N cells)" summary -- so a scripted caller (CI, a build step) can treat either CLI
the same way.

Usage:
    python3 llvm_cli_v1.py program.ll
    python3 llvm_cli_v1.py program.ll -o out.icm
    python3 llvm_cli_v1.py program.ll --man docs/man/mustang-f100-a10.man.json --cells 64

`--man FILE --cells N` (points.md #601/#823) checks the compiled program against `vm_mirror_v1`'s real, honest
N-cell mirror layout for that card -- the SAME check `VMSession.from_man(..., llvm=...)` performs, exposed here as
a CLI flag. Both `--man` and `--cells` must be given together, or not at all. A design that does not fit the
mirror is a COMPILE FAILURE (non-zero exit, the mismatch printed) -- not a warning, since it means this exact
placement could not correspond to a real Quartus build of that size on that card. This is a TOPOLOGY check only
(is every cell where a real N-cell build would put one); it does not bind DSP/BRAM resources to real sites -- that
is `card_fit_v1`'s separate, existing job (`compile_llvm_via_dag(target=...)`, not wired into this CLI).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import vm_mirror_v1  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402
from llvm_dag_frontend_v1 import compile_llvm_via_dag  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="llvm_cli_v1.py",
        description="Compile an LLVM IR (.ll) function to a real ICM v3 file via the DAG frontend.",
    )
    parser.add_argument("source", help="path to the .ll LLVM IR source file")
    parser.add_argument("--man", metavar="FILE",
                         help="a card's MAN file -- with --cells, checks the compiled program against the real "
                             "N-cell mirror layout for that card (points.md #601)")
    parser.add_argument("--cells", type=int, metavar="N",
                         help="the cell count to mirror against (used only with --man)")
    parser.add_argument("-o", "--output", metavar="FILE",
                         help="where to write the compiled .icm file (default: <source>.icm)")
    args = parser.parse_args(argv)

    if bool(args.man) != bool(args.cells):
        print("error: --man and --cells must be given together, or not at all", file=sys.stderr)
        return 2

    try:
        with open(args.source) as f:
            source_text = f.read()
    except OSError as e:
        print(f"error: could not read {args.source!r}: {e}", file=sys.stderr)
        return 2

    result, diagnostics = compile_llvm_via_dag(source_text)

    source_lines = source_text.splitlines()
    for d in diagnostics:
        print(d.format(source_lines), file=sys.stderr)
        print(file=sys.stderr)

    if result is None:
        n = sum(1 for d in diagnostics if d.severity == "error")
        print(f"compile failed: {n} error(s)", file=sys.stderr)
        return 1

    if args.man:
        try:
            bounds = vm_mirror_v1.load_mirror_bounds(args.man, args.cells)
        except (OSError, ValueError) as e:
            print(f"error loading MAN file {args.man!r}: {e}", file=sys.stderr)
            return 2
        problems = vm_mirror_v1.check_records_fit(result.records, bounds)
        if problems:
            print(f"mirror check failed against '{bounds.card_id}' ({bounds.rows}x{bounds.cols}, "
                 f"{args.cells} cells) -- this placement could not correspond to a real Quartus build of that "
                 f"size on that card:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1
        print(f"mirror check passed: fits the real {bounds.rows}x{bounds.cols} layout for {args.cells} cells "
             f"on card '{bounds.card_id}'", file=sys.stderr)

    program_name = os.path.splitext(os.path.basename(args.source))[0]
    output_path = args.output or (os.path.splitext(args.source)[0] + ".icm")
    IcmV3File(name=program_name, records=result.records).save(output_path)
    print(f"compiled '{program_name}' -> {output_path} ({len(result.records)} cell(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
