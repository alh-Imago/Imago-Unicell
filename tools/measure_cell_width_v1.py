#!/usr/bin/env python3
"""tools/measure_cell_width_v1.py -- what a cell costs on the Gowin fabric at 32 vs 18 bits, and what the nano's runtime-configurable topology costs.

Run: python3 tools/measure_cell_width_v1.py          (needs yosys; read-only, writes only /tmp)
Measured with `yosys synth_gowin` (synthesis only -- no place-and-route, no silicon). Two questions (Alan, #948):
  1. Do the flex (v4sa) cells shrink when built at the Tang's native 18 bits instead of 32? (They carry a WIDTH parameter; the sub v4s cells mostly do NOT.)
  2. How much of the nano cell's cost is the WIDTH, and how much is the topology being a REGISTER loaded at configuration (so synthesis cannot fold it)?
     Answered by a scratch copy whose topology is a CONSTANT -- what a fixed, generated design could use.
"""
import os
import re
import subprocess
import sys

SUB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sub", "verilog")
ADDER_DEP = os.path.join(os.path.dirname(SUB), "..", "fpga", "verilog", "adder_v1.v")


def synth(files, top, width):
    out = subprocess.run(["yosys", "-p", f"read_verilog -sv {' '.join(files)}; chparam -set WIDTH {width} {top}; hierarchy -top {top}; synth_gowin -top {top}; stat"],
                         capture_output=True, text=True).stdout
    blk = out.split("Number of cells")[-1]
    cnt = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s+(\w+)\s+(\d+)\s*$", blk, re.M)}
    return (sum(v for k, v in cnt.items() if re.fullmatch(r"LUT[1-4]", k)), cnt.get("ALU", 0), sum(v for k, v in cnt.items() if k.startswith("DFF")))


def main():
    print("flex (v4sa) cells at 32 vs 18 bits   [LUT1-4 / ALU / DFF]")
    for cell, extra in (("ram", []), ("nano", []), ("compare", []), ("adder", [ADDER_DEP]), ("mul", [])):
        f = [os.path.join(SUB, f"{cell}_cell_v4sa.v")] + extra
        a, b = synth(f, f"{cell}_cell_v4sa", 32), synth(f, f"{cell}_cell_v4sa", 18)
        print(f"  {cell:8s} W=32: {a[0]:>5} / {a[1]:>3} / {a[2]:>3}    W=18: {b[0]:>5} / {b[1]:>3} / {b[2]:>3}")
    src = open(os.path.join(SUB, "nano_cell_v4sa.v")).read()
    pinned = re.sub(r"^\s*topology\s+<=.*$", "", re.sub(r"reg \[9:0\]\s+topology\s+= 10'h0;", "wire [9:0] topology = TOPO;", src), flags=re.M)
    assert "TOPO" in pinned
    # gate names derived from the cell's own gate network (g0=~A g1=~B g2=A&B g3=~(A&B) g4=~(A|B) g5=A|B g8=XNOR g9=XOR)
    names = {0x000: "pass A", 0x02C: "pass B", 0x001: "NOT A", 0x002: "NOT B", 0x004: "NOR", 0x007: "AND", 0x024: "OR", 0x027: "NAND", 0x0BC: "XOR", 0x03C: "XNOR", 0x030: "const 0", 0x0B0: "const 1"}
    print("\nnano with the topology PINNED as a constant (scratch copy in /tmp)   [LUT1-4 / DFF]")
    scratch = "/tmp/nano_pinned_scratch.v"
    for code, nm in names.items():
        open(scratch, "w").write(pinned.replace("TOPO", f"10'h{code:03X}"))
        a, b = synth([scratch], "nano_cell_v4sa", 32), synth([scratch], "nano_cell_v4sa", 18)
        print(f"  0x{code:03X} {nm:7s} W=32: {a[0]:>4} / {a[2]:>3}    W=18: {b[0]:>4} / {b[2]:>3}")


if __name__ == "__main__":
    sys.exit(main())
