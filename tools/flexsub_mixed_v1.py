#!/usr/bin/env python3
"""flexsub_mixed_v1.py -- ledger #1114: MIXED-family designs with the sub bridge inserted AUTOMATICALLY (Alan, 12 Oct 2026: the bridge "feeds into the compiler and assembler systems ... and the composer as an
automatic insert when using mixed blocks that use the sub family").

A hierarchical ICM (icm-vix-v1) may tag a block (placement) with `"family": "flex"` or `"sub"` (optional; absent = --default-family, flex). This tool

  1. flattens the design and groups the cells into REGIONS: a region is a connected set of cells of one family;
  2. for every edge between two regions (a "crossing"), cuts it: the sending region gets an exit port (io_name `bx<k>_out`), the receiving region a synthetic entry relay (io_name `bx<k>_in`) placed where the
     sending cell was, so each region is an ordinary stand-alone design for the EXISTING generators (flexsub_icm_flex_v1 for flex, flexsub_icm_generate_v1 for sub) -- no cell emitter is changed;
  3. generates each region, and writes a top module that instantiates the regions and puts `flex_to_sub_v1` / `sub_to_flex_v1` (sub/verilog/flex_sub_bridge_v1.v) on every crossing, with the `done` line of a
     sub region's exit bridge opening its entry bridge (one word in flight per sub region: a sub block cannot refuse or queue a word, ledger #1112).

Stage-1 limits (each refused with its reason, never guessed): a crossing's sending cell has exactly one consumer; a sub region has exactly one entry crossing and one exit crossing and no host port of its own
(the host reaches it only through the bridge); 32-bit data; a flex region may be a ring only through the existing flex flags (not passed through here).
"""
import argparse
import collections
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "nano"))
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import flexsub_icm_generate_v1 as fig  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402

BRIDGE = os.path.join(HERE, "..", "sub", "verilog", "flex_sub_bridge_v1.v")


class MixedError(ValueError):
    pass


def _inst(cid):
    return cid.split(".", 1)[0]


def is_mixed(path):
    """True when the file is an ICM-VIX whose placements name a family (ledger #1114): the assembler then builds it as separate regions with bridges."""
    try:
        with open(path) as f:
            head = json.load(f)
    except (OSError, ValueError):
        return False
    if not str(head.get("format_version", "")).startswith("icm-vix"):
        return False
    return any(p.get("family") for p in head.get("design_map", {}).get("placements", []))


def plan(path, default_family="flex"):
    """Regions, crossings and the region ICM dicts. No files written."""
    doc = vix.IcmVixFile.load(path)
    fam_of = {p.instance: (p.family or default_family) for p in doc.placements}
    for inst, f in fam_of.items():
        if f not in ("flex", "sub"):
            raise MixedError(f"block {inst!r}: family {f!r} is not 'flex' or 'sub'")
    _, _recs, cells, edges, inputs, outputs, ext_out, _w = nl.extract(path)
    fam = {c: fam_of[_inst(c)] for c in cells}
    parent = {c: c for c in cells}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for s, d, *_ in edges:
        if fam[s] == fam[d]:
            parent[find(s)] = find(d)
    groups = collections.defaultdict(list)
    for c in sorted(cells):
        groups[find(c)].append(c)
    regions = []                                      # stable order: by first cell id
    for k, (_root, members) in enumerate(sorted(groups.items(), key=lambda kv: kv[1][0])):
        regions.append({"name": f"{fam[members[0]]}{k}", "family": fam[members[0]], "cells": members})
    region_of = {c: r["name"] for r in regions for c in r["cells"]}
    crossings = []
    for s, d, face, role, oc in edges:
        if region_of[s] == region_of[d]:
            continue
        if len(outputs.get(s, [])) != 1 or ext_out.get(s):
            raise MixedError(f"{s}: a cell that sends across a family boundary must have exactly one consumer and no other output (it feeds {outputs.get(s)} and faces {ext_out.get(s)})")
        if cells[s].io_name:
            raise MixedError(f"{s}: a cell that sends across a family boundary cannot also carry the host name {cells[s].io_name!r}")
        crossings.append({"k": len(crossings), "src": s, "dst": d, "face": face, "from": region_of[s], "to": region_of[d]})
    by_name = {r["name"]: r for r in regions}
    for r in regions:
        r["ins"] = [x for x in crossings if x["to"] == r["name"]]
        r["outs"] = [x for x in crossings if x["from"] == r["name"]]
        if r["family"] == "sub":
            if len(r["ins"]) != 1 or len(r["outs"]) != 1:
                raise MixedError(f"sub region {r['name']} ({r['cells'][0]}...): needs exactly ONE entry crossing and ONE exit crossing (one word in flight, #1112); it has {len(r['ins'])} in, {len(r['outs'])} out")
            host = [c for c in r["cells"] if cells[c].io_name]
            if host:
                raise MixedError(f"sub region {r['name']}: cells {host} carry host names; a sub region is reached only through the bridge")
    # region ICM documents (flat: one pattern at the origin, absolute cells)
    for r in regions:
        cl = []
        for c in r["cells"]:
            rec = cells[c]
            io = rec.io_name
            for x in r["outs"]:
                if x["src"] == c:
                    io = f"bx{x['k']}_out"
            cl.append({"cell_id": c, "rel_row": rec.row, "rel_col": rec.col, "core": rec.core, "core_config": dict(rec.core_config or {}),
                       "addon_config": dict(rec.addon_config or {}), "io_name": io, "preload_value": rec.preload_value})
        for x in r["ins"]:
            sr = cells[x["src"]]
            cl.append({"cell_id": f"bx{x['k']}_in", "rel_row": sr.row, "rel_col": sr.col, "core": "ram",
                       "core_config": {"downstream_mask": [x["face"]], "fixed_mode": 0}, "addon_config": {}, "io_name": f"bx{x['k']}_in", "preload_value": None})
        cores = sorted({c["core"] for c in cl})
        r["doc"] = {"format_version": "icm-vix-v1", "description": f"region {r['name']} ({r['family']}) of {os.path.basename(path)}, cut by flexsub_mixed_v1",
                    "header": {"cores_used": cores, "cell_count": len(cl)},
                    "patterns": {"region": {"cells": [{k: v for k, v in c.items() if v is not None} for c in cl]}},
                    "design_map": {"placements": [{"instance": "r", "pattern": "region", "at": [0, 0]}], "connections": []}}
    return {"regions": regions, "crossings": crossings, "cells": cells, "by_name": by_name}


def _ports(vtext, top):
    m = re.search(r"module\s+" + re.escape(top) + r"\s*\((.*?)\);", vtext, re.S)
    ports = {}
    for d, w, n in re.findall(r"(input|output)\s+wire\s*(\[[^\]]*\])?\s*(\w+)", m.group(1)):
        ports[n] = (d, w.strip())
    return ports


def generate(path, output, top="mixed_top", default_family="flex", man_path=None):
    p = plan(path, default_family)
    os.makedirs(output, exist_ok=True)
    files = set()
    for r in p["regions"]:
        rp = os.path.join(output, f"{r['name']}.icm-hier.json")
        json.dump(r["doc"], open(rp, "w"), indent=1)
        mod = f"{top}_{r['name']}"
        r["module"] = mod
        if r["family"] == "flex":
            import flexsub_icm_flex_v1 as ff
            rec = ff.generate_flex(rp, output, top=mod, man_path=man_path)
        else:
            rec = fig.generate(rp, output, top=mod, family="sub", man_path=man_path)
        r["rec"] = rec
        r["ports"] = _ports(open(os.path.join(output, f"{mod}.v")).read(), mod)
        files.update(f for f in rec["files"] if f.endswith(".v"))
    shutil.copy2(BRIDGE, os.path.join(output, "flex_sub_bridge_v1.v"))
    files.add("flex_sub_bridge_v1.v")
    L, a = [], None
    L.append(f"// {top}.v -- GENERATED by tools/flexsub_mixed_v1.py; do not hand-edit. Source: {os.path.basename(path)}; regions: " + ", ".join(f"{r['name']}({r['family']})" for r in p["regions"]) + f"; bridges: {len(p['crossings'])}")
    L.append("`default_nettype none\n`timescale 1ns / 1ps")
    top_ports, body = [], []
    cross_ports = {f"bx{x['k']}_{d}" for x in p["crossings"] for d in ("in", "out")}
    taken = set()
    for r in p["regions"]:
        for n, (d, w) in r["ports"].items():
            base = re.sub(r"^(in|out)_(.*?)(_data|_valid|_ack)$", r"\2", n)
            if base in cross_ports or n in ("clk", "rst", "cfg_valid"):
                continue
            if n in taken:
                raise MixedError(f"host port {n} appears in two regions")
            taken.add(n)
            top_ports.append(f"    {d} wire {w + ' ' if w else ''}{n}")
    L.append(f"module {top} (\n    input wire clk,\n    input wire rst,\n    input wire cfg_valid" + "".join(",\n" + t for t in top_ports) + "\n);")
    for r in p["regions"]:
        for x in r["outs"]:
            n = f"bx{x['k']}_out"
            if r["family"] == "flex":
                L.append(f"wire [31:0] {n}_data; wire {n}_valid, {n}_ack;")
            else:
                L.append(f"wire [31:0] {n}_data; wire {n}_valid;")
        for x in r["ins"]:
            n = f"bx{x['k']}_in"
            if r["family"] == "flex":
                L.append(f"wire [31:0] {n}_data; wire {n}_valid, {n}_ack;")
            else:
                L.append(f"wire [31:0] {n}_data; wire {n}_valid;")
    for r in p["regions"]:
        if r["family"] == "sub":
            L.append(f"wire {r['name']}_done;   // exit bridge -> entry bridge: the held word has left, the next may enter")
    for x in p["crossings"]:
        f_from, f_to = p["by_name"][x["from"]]["family"], p["by_name"][x["to"]]["family"]
        k = x["k"]
        if f_from == "flex" and f_to == "sub":
            L.append(f"flex_to_sub_v1 #(.WIDTH(32)) bridge{k} (.clk(clk), .rst(rst), .in_data(bx{k}_out_data), .in_valid(bx{k}_out_valid), .in_ack(bx{k}_out_ack), "
                     f".sub_data(bx{k}_in_data), .sub_valid(bx{k}_in_valid), .done({x['to']}_done));   // flex {x['from']} -> sub {x['to']}")
        elif f_from == "sub" and f_to == "flex":
            L.append(f"sub_to_flex_v1 #(.WIDTH(32)) bridge{k} (.clk(clk), .rst(rst), .sub_data(bx{k}_out_data), .sub_valid(bx{k}_out_valid), "
                     f".out_data(bx{k}_in_data), .out_valid(bx{k}_in_valid), .out_ack(bx{k}_in_ack), .done({x['from']}_done));   // sub {x['from']} -> flex {x['to']}")
        else:
            raise MixedError("internal: a crossing between two regions of one family")
    for r in p["regions"]:
        conn = ["    .clk(clk)", "    .rst(rst)", "    .cfg_valid(cfg_valid)"]
        for n, (d, w) in r["ports"].items():
            if n in ("clk", "rst", "cfg_valid"):
                continue
            base = re.sub(r"^(in|out)_(.*?)(_data|_valid|_ack)$", r"\2", n)
            wire = (n[3:] if n.startswith("in_") else n[4:]) if base in cross_ports else n      # a crossing port joins the bridge net of the same name; a host port keeps its name
            conn.append(f"    .{n}({wire})")
        L.append(f"{r['module']} u_{r['name']} (\n" + ",\n".join(conn) + "\n);")
    L.append("endmodule")
    open(os.path.join(output, f"{top}.v"), "w").write("\n".join(L) + "\n")
    rec = {"generator": "tools/flexsub_mixed_v1.py", "top": top, "source": os.path.basename(path), "default_family": default_family,
           "regions": [{"name": r["name"], "family": r["family"], "cells": len(r["cells"]), "module": r["module"]} for r in p["regions"]],
           "bridges": [{"k": x["k"], "from": x["from"], "to": x["to"], "src_cell": x["src"], "dst_cell": x["dst"]} for x in p["crossings"]],
           "files": sorted(files) + [f"{top}.v"]}
    json.dump(rec, open(os.path.join(output, "ASSEMBLY_mixed.json"), "w"), indent=2)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("icm")
    ap.add_argument("--output", required=True)
    ap.add_argument("--top", default="mixed_top")
    ap.add_argument("--default-family", default="flex", choices=["flex", "sub"])
    ap.add_argument("--man")
    a = ap.parse_args(argv)
    try:
        r = generate(a.icm, a.output, top=a.top, default_family=a.default_family, man_path=a.man)
    except (MixedError, ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"Mixed: {len(r['regions'])} regions ({', '.join(x['family'] for x in r['regions'])}), {len(r['bridges'])} bridges inserted -> {a.output} (top {r['top']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
