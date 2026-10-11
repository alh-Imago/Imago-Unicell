#!/usr/bin/env python3
"""Capture REAL outputs of the compilers for the teaching manual's Programming tabs.

Runs the DSL / Python-AST / LLVM front ends and the VM and writes docs/teaching/programming_data.json,
which build_teaching_manual.py embeds in the pages. Nothing in the JSON is typed by hand except the
program sources. Run from anywhere:  python3 docs/teaching/capture_programming_v1.py
"""
import json, os, subprocess, sys, tempfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "nano")); sys.path.insert(0, REPO)

from vm_ai_port_v1 import VMSession
from dsl_compiler_v1 import compile_source
from python_ast_frontend_v1 import compile_python_source
import super_tile_library_v1 as stl
from llvm_dag_frontend_v1 import compile_llvm_via_dag, run_in_vm

out = {}
tmp = tempfile.mkdtemp()

def cli_text(src):
    p = os.path.join(tmp, "x.uc"); open(p, "w").write(src)
    r = subprocess.run([sys.executable, os.path.join(REPO, "nano", "dsl_cli_v1.py"), p, "-o", os.path.join(tmp, "x.icm")],
                       capture_output=True, text=True)
    return (r.stdout + r.stderr).strip(), r.returncode

def recs(icm):
    rows = []
    for r in icm.records:
        cc = r.core_config
        rows.append({"id": r.cell_id, "row": r.row, "col": r.col, "core": r.core,
                     "up": cc.get("upstream_mask", []), "down": cc.get("downstream_mask", []),
                     "preload": r.preload_value})
    return rows

# ---------------------------------------------------------------- DSL
dsl = {}
SEVEN = """program seven_plus_five {
    place x as ram_flowing at (0, 0) {
        in: w
        out: e
    }
    place y as ram_flowing at (1, 1) {
        in: s
        out: n
    }
    place add as adder at (0, 1) {
        in_a: w
        in_b: s
        out: e
    }
    place sink as ram_flowing at (0, 2) {
        in: w
        out: e
    }
}
"""
dsl["seven_source"] = SEVEN
icm, d = compile_source(SEVEN)
assert not [x for x in d if x.severity == "error"], d
dsl["seven_cells"] = recs(icm)

def trace(stagger):
    s = VMSession.from_dsl(SEVEN)
    rows = []
    def snap(t, note):
        c = s.describe()["cells"]
        a = c["0,1"]["adder"]; k = c["0,2"]["ram"]
        rows.append({"tick": t, "note": note, "a_reg": a["a_reg"], "a_arrived": a["a_arrived"],
                     "out_buffer": a["out_buffer"], "adder_valid": a["data_valid"],
                     "sink": k["data_reg"], "sink_valid": k["data_valid"]})
    t = 0
    s.inject(0, 0, 7); snap(t, "inject 7 into x")
    if stagger:
        for _ in range(3):
            s.tick(1); t += 1; snap(t, "")
        s.inject(1, 1, 5); snap(t, "inject 5 into y")
    else:
        s.inject(1, 1, 5); snap(t, "inject 5 into y")
    for _ in range(6):
        s.tick(1); t += 1; snap(t, "")
    return rows
dsl["trace_staggered"] = trace(True)
dsl["trace_together"] = trace(False)

errs = []
for title, src in [
    ("A misspelt tile name", "program p { place a1 as addr at (0, 0) { out: e } }\n"),
    ("A misspelt field name", "program p {\n    place a1 as adder at (0, 0) {\n        in_a: n\n        inn_b: w\n        out: e\n    }\n}\n"),
    ("A direction that does not exist", "program p { place a1 as adder at (0, 0) { in_a: n in_b: w out: x } }\n"),
    ("Two cells on one square", "program p {\n    place a1 as ram_constant at (0, 0) { out: e init_data: 1 }\n    place a2 as ram_constant at (0, 0) { out: s init_data: 2 }\n}\n"),
    ("A missing closing brace", "program p {\n    place a1 as ram_constant at (0, 0) {\n        out: e\n        init_data: 1\n"),
]:
    text, rc = cli_text(src)
    errs.append({"title": title, "source": src, "output": text, "exit": rc})
dsl["errors"] = errs

tiles = []
for n in sorted(stl.super_tile_library.names()):
    sp = stl.super_tile_library.get(n)
    tiles.append({"name": n, "core": sp.core,
                  "ports": [[p.name, p.kind] for p in sp.ports], "params": list(sp.param_names),
                  "description": sp.description})
dsl["tiles"] = tiles
# the full list of names the compiler accepts (includes composed and DSP tiles)
text, _ = cli_text("program p { place a1 as nosuch at (0, 0) { out: e } }\n")
dsl["all_tile_names"] = [l.split("known tiles:")[1].strip().split(", ") for l in text.splitlines() if "known tiles:" in l][0]

SENT = """program s {
    place s1 as sentinel at (0, 0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
"""
icm_s, ds = compile_source(SENT)
dsl["sentinel_source"] = SENT
dsl["sentinel_cells"] = recs(icm_s)

PYSRC = 'def seven_plus_five():\n    place("x", "ram_flowing", (0, 0), **{"in": "w", "out": "e"})\n'
PYSRC = '''def adder_pair():
    place("a1", "adder", (0, 0), in_a="n", in_b="w", out="e")
'''
DSLSRC = '''program adder_pair {
    place a1 as adder at (0, 0) {
        in_a: n
        in_b: w
        out: e
    }
}
'''
ia, da = compile_python_source(PYSRC); ib, db = compile_source(DSLSRC)
same = (json.dumps(recs(ia), sort_keys=True) == json.dumps(recs(ib), sort_keys=True)) and \
       [str(r.super_latch) for r in ia.records] == [str(r.super_latch) for r in ib.records]
dsl["python"] = {"python_source": PYSRC, "dsl_source": DSLSRC, "same_records": bool(same),
                 "hash_python": str(ia.record_hash() if callable(ia.record_hash) else ia.record_hash), "hash_dsl": str(ib.record_hash() if callable(ib.record_hash) else ib.record_hash)}
out["dsl"] = dsl

# ---------------------------------------------------------------- LLVM IR
def role(cid):
    n = cid.split(".", 1)[-1]
    if "dynq_" in n: return "arg"
    if n.startswith("const_"): return "const"
    if n.startswith("pri_"): return "order"
    if n.startswith("rt"): return "relay"
    return "op"

def llvm_case(key, title, ir, arg_names, runs, py):
    r, d = compile_llvm_via_dag(ir)
    case = {"key": key, "title": title, "ir": ir}
    if r is None:
        case["refused"] = [{"what": x.what, "problem": x.problem, "why": x.why, "suggestion": x.suggestion} for x in d]
        return case
    case["cells"] = [{"id": x.cell_id, "row": x.row, "col": x.col, "core": x.core, "role": role(x.cell_id)} for x in r.records]
    case["rewrites"] = list(r.rewrites); case["caveats"] = list(r.caveats)
    case["args"] = arg_names
    rr = []
    for vals in runs:
        got = run_in_vm(r, dict(zip(arg_names, vals)))
        exp = py(*vals) & 0xFFFFFFFF
        rr.append({"in": list(vals), "vm": got, "expected": exp, "ok": got == exp})
    case["runs"] = rr
    case["result_name"] = r.result_name
    return case

L = []
L.append(llvm_case("arith", "A sum, a product and a subtraction",
"""define i32 @f(i32 %a, i32 %b, i32 %c) {
entry:
  %s = add i32 %a, %b
  %p = mul i32 %s, %c
  %r = sub i32 %p, 3
  ret i32 %r
}
""", ["a", "b", "c"], [(2, 3, 4), (10, 5, 2), (0, 0, 9), (100, -1, 7), (-1, 1, 100), (123456, 654321, 3)],
    lambda a, b, c: (a + b) * c - 3))
L.append(llvm_case("bits", "Bits: and, shift, xor",
"""define i32 @g(i32 %a, i32 %b) {
entry:
  %x = and i32 %a, %b
  %y = shl i32 %x, 2
  %z = xor i32 %y, %a
  ret i32 %z
}
""", ["a", "b"], [(3, 9), (9, 3), (-4, 2), (12, 10), (255, 15)],
    lambda a, b: (((a & b) << 2) ^ a)))
L.append(llvm_case("max", "A choice: the larger of two numbers",
"""define i32 @max(i32 %a, i32 %b) {
entry:
  %c = icmp sgt i32 %a, %b
  br i1 %c, label %yes, label %no
yes:
  br label %done
no:
  br label %done
done:
  %r = phi i32 [ %a, %yes ], [ %b, %no ]
  ret i32 %r
}
""", ["a", "b"], [(3, 9), (9, 3), (-4, 2), (12, 10), (7, 7)],
    lambda a, b: max(a, b)))
L.append(llvm_case("loop", "A loop that runs four times",
"""define i32 @f(i32 %x) {
entry:
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %i2, %loop ]
  %s = phi i32 [ 0, %entry ], [ %s2, %loop ]
  %s2 = add i32 %s, %x
  %i2 = add i32 %i, 1
  %c = icmp slt i32 %i2, 4
  br i1 %c, label %loop, label %exit
exit:
  ret i32 %s2
}
""", ["x"], [(3,), (10,), (-2,), (0,)], lambda x: 4 * x))
refused = []
for key, title, ir in [
    ("sdiv", "A division", "define i32 @f(i32 %a, i32 %b) {\nentry:\n  %r = sdiv i32 %a, %b\n  ret i32 %r\n}\n"),
    ("runtime_loop", "A loop whose length depends on an input", """define i32 @f(i32 %x, i32 %n) {
entry:
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %i2, %loop ]
  %s = phi i32 [ 0, %entry ], [ %s2, %loop ]
  %s2 = add i32 %s, %x
  %i2 = add i32 %i, 1
  %c = icmp slt i32 %i2, %n
  br i1 %c, label %loop, label %exit
exit:
  ret i32 %s2
}
"""),
]:
    refused.append(llvm_case(key, title, ir, [], [], None))
out["llvm"] = {"cases": L, "refused": refused}

# the pipeline to the flex family
ll = os.path.join(tmp, "f.ll"); open(ll, "w").write(L[0]["ir"])
icm_std = os.path.join(tmp, "f.icm"); icm_flex = os.path.join(tmp, "f_flex.icm")
r1 = subprocess.run([sys.executable, os.path.join(REPO, "nano", "llvm_cli_v1.py"), ll, "-o", icm_std], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, os.path.join(REPO, "tools", "flexsub_compile_v1.py"), ll, "-o", icm_flex], capture_output=True, text=True)
build = os.path.join(tmp, "build")
r3 = subprocess.run([sys.executable, os.path.join(REPO, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm_flex,
                     "--man", os.path.join(REPO, "docs", "man", "tang-nano-20k.man.json"), "--output", build], capture_output=True, text=True)
out["pipeline"] = {"llvm_cli": (r1.stdout + r1.stderr).strip(), "flexsub": (r2.stdout + r2.stderr).strip(),
                   "assemble": (r3.stdout + r3.stderr).strip(), "files": sorted(os.listdir(build)) if os.path.isdir(build) else []}
json.dump(out, open(os.path.join(HERE, "programming_data.json"), "w"), indent=1)
print("wrote", os.path.join(HERE, "programming_data.json"))
