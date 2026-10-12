#!/usr/bin/env python3
"""flex_busy_port_v1.py -- ledger #1098: add `output wire busy_any` to an assembled flex design (the `<top>_fz.v` of flex_freeze_net_v1): high while ANY non-constant cell is holding a word
(its valid_out is high; for a branch, either of its two). Constants (always valid by design) are left out, using ASSEMBLY.json's `constants` list. This is the host's "the grid is quiet, nothing is in flight,
so the loop-closing register holds the whole state" signal. Needs no change to any cell.

  python3 tools/flex_busy_port_v1.py ASSEMBLED_DIR TOP    ->  rewrites ASSEMBLED_DIR/TOP_fz.v in place (new port busy_any, and says how many cells it watches)
"""
import json
import os
import re
import sys


def ident(n):
    return "c_" + re.sub(r"[^A-Za-z0-9_]", "_", n)


def add(dirpath, top):
    path = os.path.join(dirpath, top + "_fz.v")
    src = open(path).read()
    consts = {ident(c) for c in json.load(open(os.path.join(dirpath, "ASSEMBLY.json")))["constants"]}
    watch = []
    for m in re.finditer(r"^(\w+)_cell_v4sa #\(.*?\) (c_\w+) \((.*)$", src, re.M):
        name, line = m.group(2), m.group(3)
        if name in consts:
            continue
        ports = re.findall(r"\.valid_out(?:_1|_2)?\(([A-Za-z0-9_]+)\)", line)
        if not ports:
            raise SystemExit(f"flex_busy_port_v1: no valid_out on {name}")
        watch += ports
    if not watch or "busy_any" in src:
        raise SystemExit("flex_busy_port_v1: nothing to watch, or already added")
    src = src.replace("module %s_fz (" % top, "module %s_fz (\n    output wire busy_any," % top, 1)
    src = src.replace("endmodule", "assign busy_any = |{%s};\nendmodule" % ", ".join(watch), 1)
    open(path, "w").write(src)
    return len(watch)


if __name__ == "__main__":
    print("busy_any watches %d valid lines" % add(sys.argv[1], sys.argv[2]))
