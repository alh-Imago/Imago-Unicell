#!/usr/bin/env python3
"""latex_cli_v1.py -- ledger #1066: compile a LaTeX formula to a UniCell design from the command line.

    python3 nano/latex_cli_v1.py "y = (a + b)^2 - 3c"
    python3 nano/latex_cli_v1.py "2xy + x^3" -o poly.icm --set x=3 --set y=5
    python3 nano/latex_cli_v1.py "(a+b)^2" --show-ir

Exit codes: 0 compiled and the built-in check passed; 1 the formula is outside the supported subset or the compiler refused it; 3 the design disagreed with the Python evaluation
(never written out); 2 usage/file errors. Whole numbers only, 32-bit wrap-around, see latex_frontend_v1.py."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import latex_frontend_v1 as L  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="latex_cli_v1.py", description="Compile a LaTeX integer formula to a checked UniCell design.")
    ap.add_argument("formula", help="the formula, e.g. \"y = (a+b)^2 - 3c\" (quote it)")
    ap.add_argument("-o", "--output", metavar="FILE", help="write the compiled .icm file here")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="also run the design on these values and print the answer (repeatable)")
    ap.add_argument("--show-ir", action="store_true", help="print the LLVM IR the formula became")
    ap.add_argument("--polynomial", choices=["auto", "horner", "direct"], default="auto",
                    help="a one-variable polynomial of degree 2 or more: 'auto' (default) builds it as written and as the Horner plan and keeps the design with fewer cells; 'horner' / 'direct' force one")
    ap.add_argument("--div-steps", type=int, default=0, metavar="K",
                    help="speed versus size of each division cell: K quotient bits per clock, 1..32 (latency ceil(32/K) clocks; bigger K = more logic). Default: each family's own (flex 1, sub 32). Written into the .icm; the flex generator builds it, sub accepts only 32")
    ap.add_argument("--division", choices=["unrolled", "core"], default="core",
                    help="how a general division is built: 'core' (default) with the division core, one cell each; or 'unrolled' from add/sub/mul cells, about 23,000 cells, one per formula, for a target without the core")
    ap.add_argument("--no-check", action="store_true", help="skip the built-in comparison with the Python evaluation (not recommended)")
    ap.add_argument("--full-check", action="store_true", help="run the compiled design in the VM even when it is large (can take many minutes per value)")
    args = ap.parse_args(argv)

    try:
        r = L.compile_latex(args.formula, check=False if args.no_check else ("full" if args.full_check else True), division=args.division, div_steps=args.div_steps, polynomial=args.polynomial)
    except L.LatexError as e:
        print(e.format(), file=sys.stderr)
        return 1
    except L.LatexCheckError as e:
        print(f"CHECK FAILED: {e}", file=sys.stderr)
        return 3

    if args.show_ir:
        print(r.ir)
    print(f"compiled: {r.cells} cells; inputs, in order: {', '.join(r.args)}")
    if r.ir_checked:
        print(f"the generated operations agree with the Python evaluation on {r.ir_checked} test values")
    if r.checked:
        print(f"the compiled design, run in the VM, agrees on {r.checked} test values")
    if r.hw_skipped:
        print(f"NOTE: {r.hw_skipped}")
    if not r.ir_checked and not r.checked:
        print("NOT checked (--no-check)")
    if r.notes:
        print("simplified: " + "; ".join(r.notes))
    if args.set:
        vals = {}
        for item in args.set:
            if "=" not in item:
                print(f"error: --set wants NAME=VALUE, got {item!r}", file=sys.stderr)
                return 2
            k, v = item.split("=", 1)
            try:
                vals[k.strip()] = int(v, 0)
            except ValueError:
                print(f"error: {v!r} is not a whole number", file=sys.stderr)
                return 2
        missing = [a for a in r.args if a not in vals]
        if missing:
            print(f"error: no value for {', '.join(missing)}", file=sys.stderr)
            return 2
        got = r.run(vals)
        print(f"result: {got}  (signed {L.as_signed(got)}); Python says {r.reference(vals)}")
    if args.output:
        try:
            IcmV3File(name="formula", records=r.result.records).save(args.output)
        except OSError as e:
            print(f"error: could not write {args.output!r}: {e}", file=sys.stderr)
            return 2
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
