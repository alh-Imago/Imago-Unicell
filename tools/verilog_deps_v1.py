#!/usr/bin/env python3
"""tools/verilog_deps_v1.py -- list the Verilog files a top module needs (ledger #1086). Scans every non-testbench .v in the given directories for `module NAME` and for
instantiations, then walks from the top. Prints one path per line (the top file first). Refuses on a module defined in two files (it never picks one silently)."""
import os, re, sys

def scan(dirs):
    defs, text = {}, {}
    for d in dirs:
        for n in sorted(os.listdir(d)):
            if not n.endswith(".v") or n.startswith("tb_"):
                continue
            p = os.path.join(d, n)
            t = re.sub(r"/\*.*?\*/", "", re.sub(r"//.*", "", open(p, errors="replace").read()), flags=re.S)
            text[p] = t
            for m in re.finditer(r"^\s*module\s+(\w+)", t, re.M):
                defs.setdefault(m.group(1), []).append(p)
    return defs, text

KW = {"module", "input", "output", "wire", "reg", "assign", "always", "begin", "end", "if", "else", "case", "endcase", "function", "endfunction", "generate", "endgenerate", "for", "initial", "parameter", "localparam", "genvar", "integer", "default", "posedge", "negedge", "endmodule", "inout", "task", "endtask", "while", "signed", "casez", "casex", "defparam", "or", "and", "not", "xor", "nand", "nor", "buf", "return"}

def deps(top, dirs):
    defs, text = scan(dirs)
    seen, order, stack = set(), [], [top]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        if m not in defs:
            continue                      # a primitive or a library cell
        if len(defs[m]) > 1:
            raise SystemExit("module %s defined in several files: %s" % (m, defs[m]))
        p = defs[m][0]
        if p not in order:
            order.append(p)
        body = text[p]
        for im in re.finditer(r"^\s*(\w+)\s*(?:#\s*\([^;]*?\))?\s+\w+\s*\(", body, re.M):
            n = im.group(1)
            if n not in KW and n in defs:
                stack.append(n)
    return order

if __name__ == "__main__":
    top = sys.argv[1]
    print("\n".join(deps(top, sys.argv[2:])))
