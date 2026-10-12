#!/usr/bin/env python3
"""flex_freeze_net_v1.py -- ledger #1097: take a flex design the assembler has written (tools/project_assemble_v1.py -s flex) and join every cell's `freeze_in` to ONE new input port `freeze_all`.
The assembler ties every `freeze_in` to 1'b0 (proven behaviour, left untouched: this tool post-processes its output into a NEW file and module, <top>_fz).

  python3 tools/flex_freeze_net_v1.py ASSEMBLED_DIR TOP     ->  writes ASSEMBLED_DIR/TOP_fz.v (module TOP_fz, same ports + `input wire freeze_all`)

Refuses (exit 1) if a cell instance does not have the `.freeze_in(1'b0)` form, so a changed generator cannot slip through half-wired.
"""
import re
import sys
import os


def make(dirpath, top):
    src = open(os.path.join(dirpath, top + ".v")).read()
    n_inst = len(re.findall(r"^\w+_cell_v4sa #\(", src, re.M))
    n_fz = src.count(".freeze_in(1'b0)")
    if n_inst == 0 or n_inst != n_fz:
        raise SystemExit(f"flex_freeze_net_v1: {n_inst} cell instances but {n_fz} tied freeze_in(1'b0): not rewriting")
    out = src.replace(".freeze_in(1'b0)", ".freeze_in(freeze_all)")
    out = out.replace("module %s (" % top, "module %s_fz (\n    input  wire freeze_all," % top, 1)
    open(os.path.join(dirpath, top + "_fz.v"), "w").write(out)
    return n_inst


if __name__ == "__main__":
    print("freeze_all joined to %d cells" % make(sys.argv[1], sys.argv[2]))
