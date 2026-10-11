#!/usr/bin/env python3
"""Capture REAL outputs of the compiler stages, placers and tightener for the teaching manual's
Compiler and Tightener & Placer tabs. Writes docs/teaching/compiler_data.json (embedded by the builder).
Nothing in the JSON is typed by hand except the program sources.  Run: python3 docs/teaching/capture_compiler_v1.py
"""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(REPO, "nano"), os.path.join(REPO, "tools"), REPO):
    sys.path.insert(0, p)

import itertools
from llvm_dag_frontend_v1 import (compile_llvm_via_dag, run_in_vm, extract_llvm_function, resolve_symbols)
from dsl_lexer_v1 import tokenize
from dsl_parser_v1 import parse_source
from dsl_compiler_v1 import compile_source
from vix_convergence_shapes_v1 import choose_convergence_shape
import vix_opcode_library_v1 as opl
from card_fit_v1 import target_from_man
import vix_tile_library_v1 as vtl, icm_vix_v1 as vix
from unicell_super_automaton_v1 import SuperGrid
from rats_nest_router_v1 import manhattan_route
from rats_nest_tighten_v1 import tighten_leaf_connection, tighten_leaf_connection_fast, find_nexus_points

out = {}
tmp = tempfile.mkdtemp()

ARITH = """define i32 @f(i32 %a, i32 %b, i32 %c) {
entry:
  %s = add i32 %a, %b
  %p = mul i32 %s, %c
  %r = sub i32 %p, 3
  ret i32 %r
}
"""
MAXIR = """define i32 @max(i32 %a, i32 %b) {
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
"""
BITS = """define i32 @g(i32 %a, i32 %b) {
entry:
  %x = and i32 %a, %b
  %y = shl i32 %x, 2
  %z = xor i32 %y, %a
  ret i32 %z
}
"""
LOOP = """define i32 @f(i32 %x) {
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
"""

def role(cid):
    n = cid.split(".", 1)[-1]
    if "dynq_" in n: return "arg"
    if n.startswith("const_"): return "const"
    if n.startswith("pri_"): return "order"
    if n.startswith("rt"): return "relay"
    return "op"

def cells_of(r):
    return [{"id": x.cell_id, "row": x.row, "col": x.col, "core": x.core, "role": role(x.cell_id)} for x in r.records]

def extent(r):
    rs = [x.row for x in r.records]; cs = [x.col for x in r.records]
    return [max(rs) - min(rs) + 1, max(cs) - min(cs) + 1]

def opfmt(o):
    return ("%" + o.name) if o.kind == "name" else str(o.value)

# ------------------------------------------------------------ the stages, on the arithmetic example
st = {"ir": ARITH}
fn, d = extract_llvm_function(ARITH)
st["parse"] = {"function": fn.function_name, "arguments": fn.arguments, "result": fn.result_name,
               "instrs": [{"name": i.name, "opcode": i.opcode, "operands": [opfmt(o) for o in i.operands]} for i in fn.instrs]}
res, d = resolve_symbols(fn.arguments, fn.instrs)
def dagop(o):
    return {"const": str(o.value), "ref": "result of %" + str(o.ref_name), "dynamic": "input %" + str(o.ref_name)}[o.kind]
st["resolve"] = [{"name": x.name, "opcode": x.opcode, "operands": [dagop(o) for o in x.operands]} for x in res.dag]
r, d = compile_llvm_via_dag(ARITH)
st["rewrite"] = {"rewrites": list(r.rewrites),
                 "ordering": [{"name": o.name, "opcode": o.opcode, "order_sensitive": o.order_sensitive,
                               "ingestion": o.ingestion, "guarantee": o.guarantee, "reason": o.reason} for o in r.ordering]}
st["place"] = {"placer": r.placer, "positions": {k: list(v) for k, v in r.positions.items()},
               "cells": cells_of(r), "extent": extent(r)}
st["emit"] = {"cells": len(r.records), "format": r.icm.format_version if hasattr(r.icm, "format_version") else "icm-vix",
              "result_cell": r.result_name, "result_core": r.result_core, "arg_injections": {k: list(map(list, v)) for k, v in r.arg_injections.items()}}
out["stages"] = st

# ------------------------------------------------------------ the DSL path
SEVEN = open(os.path.join(HERE, "programming_data.json")).read()
SEVEN = json.loads(SEVEN)["dsl"]["seven_source"]
toks, d1 = tokenize(SEVEN)
pir, d2 = parse_source(toks)
dp = {"source": SEVEN, "token_count": len(toks),
      "tokens_head": [f"{t.kind} {t.value}" for t in toks[:14]],
      "program": pir.name,
      "places": [{"name": p.name, "tile": p.tile_name, "row": p.row, "col": p.col,
                  "fields": [[f.key, f.value] for f in p.fields]} for p in pir.statements if hasattr(p, "tile_name")] if hasattr(pir, "statements") else []}
icm, d3 = compile_source(SEVEN)
dp["records"] = len(icm.records)
out["dsl_path"] = dp

# ------------------------------------------------------------ every problem at once
from dsl_cli_v1 import main as dsl_main
MULTI = """program broken {
    place a1 as addr at (0, 0) { out: e }
    place a2 as adder at (0, 1) { in_a: w inn_b: s out: e }
    place a3 as ram_constant at (0, 2) { out: x init_data: 1 }
}
"""
p = os.path.join(tmp, "m.uc"); open(p, "w").write(MULTI)
rr = subprocess.run([sys.executable, os.path.join(REPO, "nano", "dsl_cli_v1.py"), p, "-o", os.path.join(tmp, "m.icm")], capture_output=True, text=True)
out["multi_error"] = {"source": MULTI, "output": (rr.stdout + rr.stderr).strip()}
BADLL = """define i32 @f(i32 %a) {
entry:
  %x = add i32 %a, %q
  %y = mul i32 %x, %zz
  ret i32 %y
}
"""
rb, db = compile_llvm_via_dag(BADLL)
out["multi_error_llvm"] = {"ir": BADLL, "diagnostics": [{"what": x.what, "problem": x.problem, "why": x.why, "suggestion": x.suggestion} for x in db]}

# ------------------------------------------------------------ the decision rule, run for real
rows = []
for conv, comm, known in itertools.product([False, True], [True, False], [True, False]):
    rows.append({"convergence": conv, "commutative": comm, "knowable": known,
                 "shape": choose_convergence_shape(conv, comm, known).value})
out["shape_rule"] = rows

# ------------------------------------------------------------ the opcode library
lib = []
for t in ["add", "sub", "mul", "and", "or", "xor", "shl", "lshr", "cmp_ge", "copy", "mul_dsp"]:
    e = opl.lookup(t)
    lib.append({"target": t, "tile": e.tile.name, "core": e.tile.core, "commutative": e.is_commutative, "arity": e.arity})
out["opcode_library"] = lib

# ------------------------------------------------------------ does it fit a card?
man = json.load(open(os.path.join(REPO, "docs", "man", "mustang-f100-a10.man.json")))
fits = []
for n in (3, 5, 8, 9, 10, 12):
    t = target_from_man(man, rows=n, cols=n)
    rf, df = compile_llvm_via_dag(ARITH, target=t)
    if rf:
        fits.append({"grid": n, "fits": True, "report": rf.fit.format(), "answer": run_in_vm(rf, {"a": 2, "b": 3, "c": 4}), "cells": len(rf.records)})
    else:
        fits.append({"grid": n, "fits": False, "report": df[0].problem, "answer": None, "cells": None})
out["fit"] = {"card": man.get("card_id"), "budget": t.cell_budget, "rows": fits}

# ------------------------------------------------------------ placers side by side
pl = []
for key, title, ir, args in (("arith", "Sum, product, subtract", ARITH, {"a": 2, "b": 3, "c": 4}),
                             ("bits", "Bits", BITS, {"a": 12, "b": 10}),
                             ("max", "Larger of two", MAXIR, {"a": 3, "b": 9}),
                             ("loop", "Loop of four", LOOP, {"x": 3})):
    row = {"key": key, "title": title}
    for placer in ("growth", "routed", "auto"):
        rp, dd = compile_llvm_via_dag(ir, placer=placer)
        if rp:
            row[placer] = {"ok": True, "cells": cells_of(rp), "extent": extent(rp), "used": rp.placer,
                           "answer": run_in_vm(rp, args)}
        else:
            row[placer] = {"ok": False, "problem": dd[0].problem}
    pl.append(row)
out["placers"] = pl

# ------------------------------------------------------------ spacing and fold sweeps (routed placer)
def sweep(ir, args, **kw):
    rp, dd = compile_llvm_via_dag(ir, placer="routed", **kw)
    if not rp: return {"ok": False, "problem": dd[0].problem}
    return {"ok": True, "cells": cells_of(rp), "extent": extent(rp), "answer": run_in_vm(rp, args)}
sp = []
for s in range(1, 9):
    e = sweep(ARITH, {"a": 2, "b": 3, "c": 4}, spacing=s); e["spacing"] = s; sp.append(e)
fo = []
for f in (2, 3, 4, 6):
    e = sweep(ARITH, {"a": 2, "b": 3, "c": 4}, fold_width=f); e["fold"] = f; fo.append(e)
out["spacing_sweep"] = sp
out["fold_sweep"] = fo
out["default_spacings"] = list(__import__("vix_virtual_layout_v1").DEFAULT_SPACINGS)

# ------------------------------------------------------------ the rat's nest: loose route, then tighten
def combine_unit(row, col, uid, out_dir="e"):
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                    params={"priority_rank_n": 0, "priority_rank_s": 1, "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                    cell_id=f"pri_{uid}", rel_row=row, rel_col=col)
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": out_dir}, cell_id=f"add_{uid}", rel_row=row, rel_col=col + 1)
    return [pri, add]
fixed = combine_unit(5, 20, "L1a")
occ0 = {(c.rel_row, c.rel_col): c.cell_id for c in fixed}
nex = find_nexus_points(fixed)
# loose: the leaf stays where it was put, a straight-then-turn chain of relays reaches the target
start = (0, 0); target = (4, 20)
leaf_out = "e"
occ = dict(occ0); occ[start] = "leaf"
loose = manhattan_route(start, leaf_out, target, "s", "loose", occ)
steps = [{"leaf": list(start), "cells": 1 + len(loose), "route": [[c.rel_row, c.rel_col] for c in loose]}]
# every position the tightener tries, in its own order (close the column gap first, then the row gap)
r_, c_ = start
while True:
    if c_ != target[1]: c_ += 1 if target[1] > c_ else -1
    elif r_ != target[0]: r_ += 1 if target[0] > r_ else -1
    else: break
    if (r_, c_) == target: break
    so = "e" if c_ != target[1] and target[1] > c_ else ("w" if c_ != target[1] else ("s" if target[0] > r_ else "n"))
    o2 = dict(occ0); o2[(r_, c_)] = "leaf"
    try:
        rt = manhattan_route((r_, c_), so, target, "s", "t", o2)
    except Exception:
        break
    steps.append({"leaf": [r_, c_], "cells": 1 + len(rt), "route": [[c.rel_row, c.rel_col] for c in rt]})
occ_a = dict(occ0); occ_b = dict(occ0)
fin_vm, chain_vm = tighten_leaf_connection(10, start, target, "s", occ_a, "leaf0")
fin_fast, chain_fast = tighten_leaf_connection_fast(10, start, target, "s", occ_b, "leaf0")
# run the tightened design in the VM and read what arrives
icm_t = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=fixed + chain_vm)},
                       placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="t")
recs, _ = icm_t.flatten(); g = SuperGrid(recs)
for _ in range(40): g.tick()
out["rats_nest"] = {
    "nexus": [c.cell_id for c in nex], "target": list(target), "start": list(start),
    "loose_cells": 1 + len(loose), "tight_cells": len(chain_vm), "tight_leaf": list(fin_vm),
    "fast_same": (fin_vm == fin_fast and [(c.rel_row, c.rel_col) for c in chain_vm] == [(c.rel_row, c.rel_col) for c in chain_fast]),
    "steps_count": len(steps), "steps": steps,
    "delivered": g.cells[(5, 21)].adder_a_reg,
    "loose_positions": [[c.rel_row, c.rel_col] for c in loose], "tight_positions": [[c.rel_row, c.rel_col] for c in chain_vm],
    "fixed_positions": [[c.rel_row, c.rel_col, c.core] for c in fixed]}

json.dump(out, open(os.path.join(HERE, "compiler_data.json"), "w"), indent=1)
print("wrote", os.path.join(HERE, "compiler_data.json"))
