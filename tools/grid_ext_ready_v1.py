#!/usr/bin/env python3
"""tools/grid_ext_ready_v1.py -- ledger #1162: give a GENERATED standard / carrier grid (standalone_grid_v1 / carrier_grid_v3 output) one more output port, `ext_ready`, one bit per outside face (same index k as
ext_arrived / ext_fire in GRID.json): the `ready_out` of the cell that owns that face. The generators leave every cell's `ready_out()` unconnected; the flex -> std adapter needs it (a std cell takes a word only
when ready). Pure text post-processing of the generated file; the generators are not changed. Returns the new port's name."""
import json, os, re


def add_ext_ready(vfile, meta):
    t = open(vfile).read()
    if "ext_ready" in t:
        return "ext_ready"
    idx = {c["cell_id"]: c["index"] for c in meta["cells"]}
    ext = meta["ext"]
    if not ext:
        return None
    n = len(ext)
    if not re.search(r"ext_data_out\s*\n\s*\);", t):
        raise ValueError("%s: the module header is not in the shape this tool knows" % vfile)
    t = re.sub(r"(ext_data_out)(\s*\n\s*\);)", r"\1,\n    output wire [%d:0] ext_ready\2" % (n - 1), t, count=1)
    for i in sorted({idx[e["cell"]] for e in ext}):
        pat = re.compile(r"(\bC%d \(.*?)\.ready_out\(\)," % i, re.S)
        if not pat.search(t):
            raise ValueError("%s: cell C%d has no unconnected ready_out" % (vfile, i))
        t = pat.sub(lambda m: m.group(1) + ".ready_out(rdy%d)," % i, t, count=1)
        t = t.replace("    wire cfg_boot", "    wire rdy%d;\n    wire cfg_boot" % i, 1) if "wire cfg_boot" in t else t
    assigns = "".join("    assign ext_ready[%d] = rdy%d;\n" % (e["k"], idx[e["cell"]]) for e in ext)
    t = t.replace("endmodule", assigns + "endmodule", 1)
    open(vfile, "w").write(t)
    return "ext_ready"
