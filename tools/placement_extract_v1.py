#!/usr/bin/env python3
"""
placement_extract_v1.py — points.md #456/#457: merges real Quartus
placement data into per-instance physical bounding boxes, closing the
"no physical placement" gap in `docs/shapes/README.md`.

REAL, DELIBERATE SCOPE: this does NOT attempt to give one X/Y per RTL
instance -- a real instance like `unicell_super_v1:H1` is built from
dozens of real primitives (registers/LUTs) that Quartus places across
many separate LAB/MLABCELL locations, since the super carrier shell
places all 6 of its possible cores simultaneously (confirmed directly
against Alan's own real Control Signals report -- H1 alone spans
roughly X101-114/Y2-13). What this tool computes instead, honestly:
for each hierarchy prefix (an RTL instance name), the real BOUNDING BOX
(min/max X, min/max Y) of every primitive found under that prefix in
the input report -- a real, useful approximation of "where this cell
physically lives," not a false claim of exact single-point placement.

INPUT: a Quartus "Control Signals" report (Fitter Report section),
saved as tab-separated text -- NOT a Back-Annotate Assignments export
(that mechanism was tried and found insufficient, #456's own real
finding: only 8 nodes, meant for preserving explicit assignments
across recompiles, not exporting a full floorplan). Real column
layout confirmed against Alan's own actual v3 report: Name, Location,
Fan-Out, Signal Type, Global?(yes/no), Global Clock Network, [unused],
[unused]. Lines starting with '#' or '##' are treated as comments.

Coverage caveat, stated honestly: a Control Signals report lists every
primitive that drives SOME control role (clock, clock-enable, sync/
async clear or load, write-enable) -- not literally every register in
the design. This is real, substantial coverage (confirmed: spans every
sub-core in every super-carrier cell, every connection-point cell, and
the host bridge's own internal ISSP hierarchy) but not 100% exhaustive.

Usage:
    python3 placement_extract_v1.py <control_signals.tsv> --shape <shape.json> [-o output.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

LOCATION_RE = re.compile(r"^(LABCELL|MLABCELL|FF|JTAG)_X(\d+)_Y(\d+)(?:_N(\d+))?$")


def parse_control_signals(path: Path):
    """Real extraction: for each row with a real fabric-grid location
    (LABCELL/MLABCELL/FF/JTAG -- excludes bare PIN_ locations, which
    aren't part of the internal placement grid), record hierarchy path
    -> (x, y). PIN_ rows (like CLK_100M itself) are skipped for bounding-
    box purposes but not treated as errors -- they're real, just not
    fabric-grid coordinates."""
    entries = []
    skipped_pins = 0
    unparsed = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 2:
            unparsed.append((line_no, line))
            continue
        name, location = fields[0], fields[1]
        if location.startswith("PIN_"):
            skipped_pins += 1
            continue
        m = LOCATION_RE.match(location)
        if not m:
            unparsed.append((line_no, line))
            continue
        block_type, x, y = m.group(1), int(m.group(2)), int(m.group(3))
        entries.append({"name": name, "location": location, "block_type": block_type, "x": x, "y": y})
    return entries, skipped_pins, unparsed


def hierarchy_prefix(name: str) -> str | None:
    """Real RTL instance prefix from a Control Signals row's own name,
    e.g. 'unicell_super_v1:H1|accumulator_cell_v1:CORE_ACC|accumulator[26]~0'
    -> 'H1'. Matches this project's own real naming convention
    (module_type:INSTANCE_NAME|...) confirmed against shape_extract_v1.py's
    own instance list -- takes the FIRST ':INSTANCE_NAME' segment before
    the first '|', not the module type itself."""
    if ":" not in name:
        return None
    first_seg = name.split("|", 1)[0]
    if ":" not in first_seg:
        return None
    return first_seg.split(":", 1)[1]


def aggregate_bounding_boxes(entries, known_instances):
    """For each known SHAPE instance, the real bounding box of every
    primitive found under its own hierarchy prefix. Instances with zero
    matching rows are reported explicitly as 'no_data', not silently
    omitted -- a real, honest gap (this instance's own control-signal-
    driving primitives, if any, weren't captured in this specific
    report) rather than an assumed-zero-footprint claim."""
    by_instance = {}
    for e in entries:
        prefix = hierarchy_prefix(e["name"])
        if prefix in known_instances:
            by_instance.setdefault(prefix, []).append(e)

    result = {}
    for inst in known_instances:
        rows = by_instance.get(inst, [])
        if not rows:
            result[inst] = {"status": "no_data", "sample_count": 0}
            continue
        xs = [r["x"] for r in rows]
        ys = [r["y"] for r in rows]
        result[inst] = {
            "status": "real_partial_coverage",
            "sample_count": len(rows),
            "x_range": [min(xs), max(xs)],
            "y_range": [min(ys), max(ys)],
            "block_types_seen": sorted({r["block_type"] for r in rows}),
        }
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("control_signals_file")
    ap.add_argument("--shape", required=True, help="a SHAPE file (shape_extract_v1.py output) to merge against")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args()

    cs_path = Path(args.control_signals_file)
    entries, skipped_pins, unparsed = parse_control_signals(cs_path)

    shape = json.loads(Path(args.shape).read_text())
    known_instances = [c["instance"] for c in shape["cells"]]

    placement = aggregate_bounding_boxes(entries, known_instances)

    result = {
        "placement_version": "1.0",
        "source_control_signals_file": str(cs_path),
        "source_shape_file": str(args.shape),
        "card_id": shape.get("card_id"),
        "real_rows_parsed": len(entries),
        "pin_rows_skipped": skipped_pins,
        "unparsed_rows": [{"line": ln, "content": c} for ln, c in unparsed],
        "coverage_note": "A Control Signals report lists primitives driving SOME control role "
                          "(clock/clock-enable/sync-or-async-clear-or-load/write-enable), not "
                          "every register in the design. Real, substantial, but not exhaustive "
                          "coverage -- see this tool's own module docstring.",
        "instances": placement,
    }

    out_text = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(out_text)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(out_text)


if __name__ == "__main__":
    main()
