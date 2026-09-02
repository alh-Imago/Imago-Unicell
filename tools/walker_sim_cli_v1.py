#!/usr/bin/env python3
"""walker_sim_cli_v1.py — points.md #602: the real CLI for the
simulated Walker, matching this project's own established convention
(every frontend action has a real, equivalent command-line tool, not
just a web-only feature).

REAL JOB: MAN file + cell count + a program (DSL source file or an
existing .icm file) -> a real, VM-mirrored session
(`vm_mirror_v1.VMSession.from_man()`, #601) -> the real ping-protocol
discovery walk (`walker_sim_v1.walk()`, #501/#602) -> a real SHAPE file
on disk, in the same format `shape_extract_v1.py`'s own static
extraction produces.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nano"))
import vm_ai_port_v1  # noqa: E402
import walker_sim_v1  # noqa: E402


def run(man_path, cells, output, dsl_file=None, icm_path=None, start=(0, 0)):
    if bool(dsl_file) == bool(icm_path):
        raise ValueError("exactly one of dsl_file or icm_path must be given")

    if dsl_file:
        with open(dsl_file) as f:
            session = vm_ai_port_v1.VMSession.from_man(man_path, cells, dsl=f.read())
    else:
        session = vm_ai_port_v1.VMSession.from_man(man_path, cells, icm_path=icm_path)

    result = walker_sim_v1.walk(session, start=start)
    shape = walker_sim_v1.to_shape(result, session.mirror_bounds.card_id)
    with open(output, "w") as f:
        json.dump(shape, f, indent=2)

    return {
        "card_id": session.mirror_bounds.card_id,
        "cells_discovered": len(result.discovered),
        "edges_discovered": len(result.edges),
        "ping_count": result.ping_count,
        "output": output,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--man", required=True, help="Path to a MAN file (real card capabilities)")
    ap.add_argument("--cells", required=True, type=int, help="Real cell count -- must match the ICM/DSL program's own real placements")
    ap.add_argument("--dsl-file", default=None, help="Path to a Unicell-S DSL source file to compile and load")
    ap.add_argument("--icm", default=None, help="Path to an existing, already-compiled .icm file to load instead of DSL")
    ap.add_argument("--start-row", type=int, default=0)
    ap.add_argument("--start-col", type=int, default=0)
    ap.add_argument("-o", "--output", required=True, help="Output path for the real SHAPE file")
    args = ap.parse_args()

    try:
        result = run(args.man, args.cells, args.output, dsl_file=args.dsl_file, icm_path=args.icm,
                     start=(args.start_row, args.start_col))
    except (ValueError, FileNotFoundError, walker_sim_v1.NoTargetError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except vm_ai_port_v1.CompileFailure as e:
        print(f"error: program did not compile:\n{e.format()}", file=sys.stderr)
        return 1

    print(f"Card:    {result['card_id']}")
    print(f"Cells discovered: {result['cells_discovered']}")
    print(f"Edges discovered: {result['edges_discovered']}")
    print(f"Real pings taken: {result['ping_count']}")
    print(f"SHAPE written to: {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
