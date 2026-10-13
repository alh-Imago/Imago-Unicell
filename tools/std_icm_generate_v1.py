#!/usr/bin/env python3
"""tools/std_icm_generate_v1.py -- ledger #1123: the ICM drives the STANDARD line (the v4 standalone shells, or the VIXeN carrier).
Same contract as the flex/sub ICM generators: an ICM map in, Verilog out.  `-s std` = standalone shells (standalone_grid_v1), `-s carrier` = the VIXeN carrier trimmed to the
cores the ICM uses (carrier_grid_v3 + make_carrier_subset_v3).  A design with a feedback ring is refused unless --allow-rings and --ring-steps N are given; then the ring
control (counter + branch + join gate, nano/std_ring_control_v1.py) is generated INTO the map.  The io map (ld cell indices, release, stopped, tap) is written to GRID.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "nano"), os.path.join(ROOT, "nano", "examples")):
    if p not in sys.path:
        sys.path.insert(0, p)

KEEP_NAME = {"ram": "ram", "adder": "adder", "branch": "branch", "accumulator": "accum"}


def has_ring(recs):
    import std_ring_control_v1 as C
    pos, succ = C._graph(recs)
    for r in recs:
        if C._scc_of(succ, r.cell_id) - {r.cell_id} or r.cell_id in succ[r.cell_id]:
            return True
    return False


def generate(icm, out, family="std", top=None, rings=False, ring_steps=None, result_io="result", input_io="z_input"):
    import std_ring_control_v1 as C
    from hierarchical_icm_prototype_loader import load_hierarchical, flatten
    if family not in ("std", "carrier"):
        raise ValueError("family must be std or carrier")
    recs = flatten(load_hierarchical(icm))[0]
    bad = sorted({r.core for r in recs} - set(KEEP_NAME))
    if bad:
        raise ValueError("the standard line has no grid shell for core(s): %s (supported: %s)" % (", ".join(bad), ", ".join(sorted(KEEP_NAME))))
    info = None
    ring = has_ring(recs)
    if ring and not rings:
        raise ValueError("the design has a feedback ring; pass --allow-rings and --ring-steps N (a ring without control runs away)")
    if rings and not ring:
        raise ValueError("--allow-rings given but the design has no ring")
    if ring:
        if not ring_steps or ring_steps < 1:
            raise ValueError("--allow-rings needs --ring-steps N (N >= 1)")
        try:
            recs, info = C.insert_ring_control(recs, ring_steps, input_io=input_io, result_io=result_io)
        except C.RingError as e:
            raise ValueError(str(e))
    elif ring_steps:
        raise ValueError("--ring-steps applies only to a design with a ring")
    res = [r for r in recs if r.io_name == result_io]
    if not res:
        raise ValueError("no cell is named io_name '%s' (the observation point)" % result_io)
    tap = res[0].cell_id
    top = top or ("std_top" if family == "std" else "carrier_top")
    os.makedirs(out, exist_ok=True)
    if family == "std":
        import standalone_grid_v1 as S
        meta = S.generate(recs, out, top, tap)
    else:
        import carrier_grid_v3 as G
        keep = tuple(sorted({KEEP_NAME[r.core] for r in recs}))
        meta = G.generate(recs, out, top, tap, keep=keep)
        meta["keep"] = list(keep)
    idx = {c["cell_id"]: c["index"] for c in meta["cells"]}
    meta["io"] = {r.io_name: idx[r.cell_id] for r in recs if r.io_name}
    meta["ring"] = info
    json.dump(meta, open(os.path.join(out, "GRID.json"), "w"), indent=1)
    files = sorted(f for f in os.listdir(out) if f.endswith(".v"))
    return {"family": family, "top": top, "cells": len(recs), "files": files, "ring": info, "io": meta["io"], "tap": tap}
