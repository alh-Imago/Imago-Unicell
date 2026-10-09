#!/usr/bin/env python3
# STATUS (docs/STATUS_MAP.md, 9 Oct 2026): MEASUREMENT script; results are in the ledger. Re-runnable, not tested. Moved here from tools/.
"""tools/measure_cell_width_v1.py -- what a flex cell costs on the Gowin fabric at 32 vs 18 bits, in BOTH synthesis flows.

Run: python3 tools/measure_cell_width_v1.py          (needs yosys; read-only, writes only /tmp)
CORRECTED (ledger #949): the first version (#948) counted only LUT1-4 and used only the DEFAULT `synth_gowin` flow. In that flow the mapper builds
huge MUX2_LUT5..8 trees for some cells (the nano, the LUT multiplier, and the comparator at most widths), which it did not count and which inflated both.
This version counts MUX2_LUT cells too and measures the default flow AND `-nowidelut` (no wide-LUT muxes). Synthesis only: no P&R here (see
tools/measure_synth_flow_v1.py for real place-and-route), no silicon.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/experimental/ -> repo root
SUB = os.path.join(ROOT, "sub", "verilog")
ADDER_DEP = os.path.join(ROOT, "fpga", "verilog", "adder_v1.v")


def synth(files, top, width, flags=""):
    out = subprocess.run(["yosys", "-p", f"read_verilog -sv {' '.join(files)}; chparam -set WIDTH {width} {top}; hierarchy -top {top}; synth_gowin -top {top} {flags}; stat"],
                         capture_output=True, text=True).stdout
    c = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s+(\w+)\s+(\d+)\s*$", out.split("Number of cells")[-1], re.M)}
    return (sum(v for k, v in c.items() if re.fullmatch(r"LUT[1-4]", k)), sum(v for k, v in c.items() if k.startswith("MUX2_LUT")), c.get("ALU", 0),
            sum(v for k, v in c.items() if k.startswith("DFF")))


def main():
    print("flex (v4sa) cells, 32 vs 18 bits, default flow vs -nowidelut      [LUT1-4 / MUX2_LUT / ALU / DFF]")
    for cell, extra in (("ram", []), ("nano", []), ("compare", []), ("adder", [ADDER_DEP]), ("mul", [])):
        f = [os.path.join(SUB, f"{cell}_cell_v4sa.v")] + extra
        for flags, lab in (("", "default   "), ("-nowidelut", "-nowidelut")):
            a, b = synth(f, f"{cell}_cell_v4sa", 32, flags), synth(f, f"{cell}_cell_v4sa", 18, flags)
            chg = f"{(b[0] - a[0]) / a[0]:+.0%}" if a[0] else "n/a"
            print(f"  {cell:8s} {lab}  W=32: {a[0]:>5}/{a[1]:>4}/{a[2]:>3}/{a[3]:>3}   W=18: {b[0]:>5}/{b[1]:>4}/{b[2]:>3}/{b[3]:>3}   LUT change {chg}")
    src = open(os.path.join(SUB, "nano_cell_v4sa.v")).read()
    pinned = re.sub(r"^\s*topology\s+<=.*$", "", re.sub(r"reg \[9:0\]\s+topology\s+= 10'h0;", "wire [9:0] topology = TOPO;", src), flags=re.M)
    assert "TOPO" in pinned
    print("\nnano with the topology PINNED as a constant (scratch copy in /tmp); AND and XOR     [LUT1-4 / MUX2 / ALU / DFF]")
    scratch = "/tmp/nano_pinned_scratch.v"
    for code, nm in ((0x007, "AND"), (0x0BC, "XOR")):
        open(scratch, "w").write(pinned.replace("TOPO", f"10'h{code:03X}"))
        for flags, lab in (("", "default   "), ("-nowidelut", "-nowidelut")):
            print(f"  {nm}  {lab}  W=32: {synth([scratch], 'nano_cell_v4sa', 32, flags)}   W=18: {synth([scratch], 'nano_cell_v4sa', 18, flags)}")
    print("\nNOTE: in a GENERATED design the nano's cfg_data is a constant, so synthesis folds the always-zero topology bits itself: a whole flex `and` design is ~50 LUTs.")


if __name__ == "__main__":
    sys.exit(main())
