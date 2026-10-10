#!/usr/bin/env python3
"""tools/alu_ladder_v1.py -- the measured tables of docs/measurements/ALU_LADDER.md, generated from the source files (ledger #1036 addendum 47; the NOR-adder table added in addendum 48).

    python3 tools/alu_ladder_v1.py            print the two tables
    python3 tools/alu_ladder_v1.py --write    put them into docs/measurements/ALU_LADDER.md (between the BEGIN/END markers)
    python3 tools/alu_ladder_v1.py --check    exit 1 if the document's tables differ from what the source files give now

Sources (nothing is typed in by hand here):
  1. docs/measurements/flex_width_sweep_975/costs.json     per-cell yosys synth_gowin cost at 32 bits (SYNTHESIS ONLY: no place-and-route, no timing)
  2. fpga/build/unit_{relay,tree,cordic}_v1/unit_top_report.json   place-and-route reports of the bitstreams that ran on the board
  3. docs/measurements/nor_adder_v1.json                   written by tools/nor_adder_v1.py --measure (synthesis only; VM ticks)
Everything else in the document (cell counts of the floating-point units, which come from ledger entries) is written by hand there
with its ledger number, and is NOT touched by this tool."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "measurements", "ALU_LADDER.md")
BEGIN, END = "<!-- BEGIN GENERATED: {0} -->", "<!-- END GENERATED: {0} -->"

CELLS = [  # (cell key, label in the table, what it is)
    ("nano", "nano", "the NOR-tree gate cell (topology word picks the function)"),
    ("latch", "latch", "holds one word"),
    ("router", "router", "fixed split"),
    ("shift_stage", "shift stage", "one conditional shift"),
    ("mask", "mask", "bit mask"),
    ("compare", "compare", "magnitude compare"),
    ("adder", "adder", "word add with carry out"),
    ("accumulator", "accumulator", "add into a held word"),
    ("branch", "branch", "compare and steer"),
    ("mul", "mul (logic)", "32x32 multiplier built from LUTs"),
    ("mul_dsp", "mul (DSP block)", "the same multiplier on a Gowin DSP"),
]
UNITS = [("unit_relay_v1", "small relay chain", "near-empty design: the baseline (SD card + SPI unit + a few relays)"),
         ("unit_tree_v1", "4-input reduction tree", "adds four SensorTrix words"),
         ("unit_cordic_v1", "CORDIC (36 cells)", "24 relays, 8 adders, 4 branches")]


def cell_table():
    d = json.load(open(os.path.join(ROOT, "docs", "measurements", "flex_width_sweep_975", "costs.json")))
    out = ["| cell (flex, 32-bit word) | what it is | LUT4 | carry-chain (ALU) | flip-flops | DSP |",
           "|---|---|---:|---:|---:|---:|"]
    for key, label, what in CELLS:
        lut, alu, dff, mult = d["cells"][key]["single_nowidelut"]["32"]
        out.append(f"| {label} | {what} | {lut:,} | {alu:,} | {dff:,} | {mult} |")
    return "\n".join(out)


def unit_table():
    rows, base = [], None
    for dirname, label, what in UNITS:
        r = json.load(open(os.path.join(ROOT, "fpga", "build", dirname, "unit_top_report.json")))
        u = r["utilization"]
        v = (u["LUT4"]["used"], u["ALU"]["used"], u["DFF"]["used"], r["fmax"]["clk"]["achieved"])
        base = base or v
        rows.append((label, what, v))
    out = ["| design on the Tang Nano 20K (whole unit) | what it is | LUT4 | ALU | flip-flops | Fmax (MHz) | LUT4 over baseline |",
           "|---|---|---:|---:|---:|---:|---:|"]
    for label, what, v in rows:
        diff = "baseline" if v == base else f"+{v[0] - base[0]:,}"
        out.append(f"| {label} | {what} | {v[0]:,} | {v[1]:,} | {v[2]:,} | {v[3]:.1f} | {diff} |")
    return "\n".join(out)


def nor_table():
    m = json.load(open(os.path.join(ROOT, "docs", "measurements", "nor_adder_v1.json")))
    n, a = m["nor_adder"], m["adder_cell"]
    out = ["| 32-bit adder (mod 2^32), flex line, whole design | placed cells | of which NOR gates (nano) | LUT4 | carry-chain (ALU) | flip-flops | FlexGrid ticks, A and B in to sum out |",
           "|---|---:|---:|---:|---:|---:|---:|",
           f"| dedicated adder cell | {a['placed_cells']} | 0 | {a['LUT4']:,} | {a['ALU']} | {a['DFF']:,} | {a['ticks_flexgrid']} |",
           f"| built from nano gates and shift cells only | {n['placed_cells']} | {n['logic_cells']} | {n['LUT4']:,} | {n['ALU']} | {n['DFF']:,} | {n['ticks_flexgrid']} |",
           f"| ratio (NOR-built / dedicated) | {n['placed_cells'] / a['placed_cells']:.0f}x | | {n['LUT4'] / a['LUT4']:.0f}x | | {n['DFF'] / a['DFF']:.0f}x | {n['ticks_flexgrid'] / a['ticks_flexgrid']:.0f}x |"]
    return "\n".join(out)


def carrier_table():
    c = json.load(open(os.path.join(ROOT, "docs", "measurements", "nor_adder_v1.json")))["carrier"]
    out = ["| 32-bit adder on the carrier line (Arria 10 reference) | cells used | positions the toolchain builds | ALM at 1,030.52 per position | share of the card (251,680 ALM) | standard-mode VM ticks |",
           "|---|---:|---:|---:|---:|---:|"]
    for key, label in (("dedicated_adder", "dedicated adder cell"), ("nor_built_folded", "from nano gates and shift cells, folded into a near-square block"),
                       ("nor_built_long_and_thin", "the same, laid out long and thin (as in Table C)")):
        r = c[key]
        out.append(f"| {label} | {r['cells_used']} | {r['positions']} | {r['alm']:,} | {r['percent_of_card']}% | {r['ticks_std_vm']} |")
    return "\n".join(out)


def block(name, text):
    return BEGIN.format(name) + "\n" + text + "\n" + END.format(name)


def splice(doc, name, text):
    b, e = BEGIN.format(name), END.format(name)
    i, j = doc.index(b), doc.index(e) + len(e)
    return doc[:i] + block(name, text) + doc[j:]


def main():
    tables = {"cells": cell_table(), "units": unit_table(), "nor": nor_table(), "carrier": carrier_table()}
    if len(sys.argv) < 2:
        print(tables["cells"]); print(); print(tables["units"]); print(); print(tables["nor"]); print(); print(tables["carrier"]); return 0
    doc = open(DOC, encoding="utf-8").read()
    new = doc
    for k, t in tables.items():
        new = splice(new, k, t)
    if sys.argv[1] == "--write":
        open(DOC, "w", encoding="utf-8").write(new)
        print("written:", os.path.relpath(DOC, ROOT)); return 0
    if sys.argv[1] == "--check":
        ok = new == doc
        print("ALU_LADDER.md tables match the source files" if ok else "ALU_LADDER.md tables are OUT OF DATE: run tools/alu_ladder_v1.py --write")
        return 0 if ok else 1
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
