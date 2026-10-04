#!/usr/bin/env python3
"""
flexsub_icm_generate_v1.py -- STEP 2, SECOND SLICE of the Flex-Sub assembler plan: read an ICM-VIX file as
a map and emit the design it describes as Verilog, into a flat self-contained folder. `sub` family only
(`*_cell_v4s.v`: straight wiring, fixed 1-cycle latency, no ack -- Alan's ruling #924, "just physics").

Reached through project_assemble_v1.py:   -s sub --icm FILE.icm-hier.json --output DIR [--no-align]

HOW IT TRANSLATES (each rule below was read from the real cells / the VM, then checked by simulation):
  * wiring comes from the cells' masks + grid positions (flexsub_icm_netlist_v1), NOT from the advisory
    `connections` list.
  * every v4s cell has exactly ONE cycle of latency (adder_cell_v4s registers its sum, ram_cell_v4s registers
    its data) -- the same as one VM tick per hop, so hop depth IS cycle count.
  * the v4s adder has a single valid_in for BOTH operands, so the operands of ONE item must be present in the
    same cycle. For a single one-shot value this happens by itself: a flowing ram_cell_v4s HOLDS its data_reg
    until the next valid, so an early operand just sits on its wire (checked: an unaligned one-shot is still
    right). It breaks for BACK-TO-BACK items: item n+1's early operand overwrites the held one before item n's
    late operand arrives, mixing items (checked: unaligned back-to-back results were 4321/7210/9100 instead of
    10/100/1000). So the EARLIER operand's path is padded with (depth difference) flowing ram relay cells --
    the project's own "delay cells" (#5, reused by dsp_latency_v1.py in the VM) -- never new hardware. Aligned,
    the design is a full pipeline: one result per cycle. `--no-align` omits the padding (the negative control).
  * operand roles follow the VM's arrival-order rule: A = the first (earlier) arrival, B = the second. The
    static hop-depth estimate matched the real VM on 7/7 adders (tests/test_flexsub_icm_netlist_v1.py).
  * valid_in of an adder is operand B's valid (aligned, so identical to A's) -- wiring, not control.

SCOPE OF THIS SLICE (refused with the reason, never guessed): cores ram and adder only; acyclic; every adder
has exactly two sources at DIFFERENT arrival times; no merges, no constants, no addon_config. Not yet built:
merges (gated OR, Alan: "a free OR"), constants, branch (no v4s branch exists), single-stream operand pairs,
and the whole flex family (ack join on fan-out).

Output folder: <top>.v (the design), the cell files + dependencies, <top>.ys (synth_gowin), ASSEMBLY.json.
The top has ports clk, rst, cfg_valid (one pulse after reset arms every cell), and for each io_name:
in_<name>_data[31:0] / in_<name>_valid, out_<name>_data[31:0] / out_<name>_valid.
"""
import json
import os
import re
import shutil
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import flexsub_assemble_v1 as fsa  # noqa: E402

SUPPORTED_CORES = {"ram", "adder"}


class IcmGenError(ValueError):
    pass


def _ident(cid):
    return "c_" + re.sub(r"[^A-Za-z0-9_]", "_", cid)


def plan(icm_path, align=True):
    """Everything the emitter needs, with every refusal raised here. Returns a plain dict."""
    doc, recs, cells, edges, inputs, outputs, ext_out, warnings = nl.extract(icm_path)
    problems = []
    # priority arbiters that only serialised two operands onto one input are eliminated (dedicated ports replace them)
    cells, inputs, outputs, tiekeys, eliminated, pri_problems = nl.eliminate_priority(cells, inputs, outputs)
    problems += pri_problems
    edges = [(src, dst) for dst, roles in inputs.items() for lst in roles.values() for src, _ in lst]
    depth, cyclic = nl.hop_depths(cells, [(s_, d_, None, None, ()) for s_, d_ in edges])
    if cyclic:
        problems.append("the design has a cycle (feedback) -- the fixed-latency translation has no rule for it yet")
    for r in cells.values():
        if r.core not in SUPPORTED_CORES:
            why = ("no v4s branch cell exists (branch_cell_v4sa is flex-only)" if r.core == "branch"
                   else "arbiter that could not be eliminated (see above)" if r.core == "priority" else "not in this slice")
            problems.append(f"{r.cell_id}: core {r.core!r} unsupported on sub -- {why}")
        if r.addon_config:
            problems.append(f"{r.cell_id}: addon_config present -- needs shift/mask graph expansion (#905), not in this slice")
        if r.preload_value is not None:
            problems.append(f"{r.cell_id}: preload_value (a constant source) -- constants are not in this slice")
        for role, srcs in inputs.get(r.cell_id, {}).items():
            if r.core == "adder" and role == "in":
                if len(srcs) != 2:
                    problems.append(f"{r.cell_id}: adder has {len(srcs)} source(s), need exactly 2 "
                                    f"(one stream carrying both operands needs a stagger spec -- not in this slice)")
            elif len(srcs) > 1:
                problems.append(f"{r.cell_id}: {len(srcs)} sources on one input (a merge) -- gated-OR merge not in this slice")
    if problems:
        raise IcmGenError("cannot generate sub Verilog from %s:\n  - " % os.path.basename(icm_path) + "\n  - ".join(problems))

    def role_key(c, src, t_out):
        # earlier arrival first; on an arrival tie, the arbiter's own rule (lower rank, then N>S>E>W) if one existed
        return (t_out[src], tiekeys.get((c, src), (0, 0)))

    # arrival time (cycles) at each cell's OUTPUT; entries (no incoming edge) are fed by a top-level port at t=0
    t_out, order = {}, []
    preds = {c: [src for src, _ in (e for lst in inputs.get(c, {}).values() for e in lst)] for c in cells}
    remaining = set(cells)
    while remaining:
        ready = [c for c in sorted(remaining) if all(q in t_out for q in preds[c])]
        if not ready:
            raise IcmGenError("internal: dependency order could not be resolved")
        for c in ready:
            order.append(c)
            t_in = max((t_out[q] for q in preds[c]), default=0)
            if cells[c].core == "adder":
                (sa, _), (sb, _) = sorted(inputs[c]["in"], key=lambda sf: role_key(c, sf[0], t_out))
                if t_out[sa] == t_out[sb] and tiekeys.get((c, sa)) is None:
                    raise IcmGenError(f"{c}: both adder sources arrive at cycle {t_out[sa]} with no arbiter to order them -- a same-time "
                                      f"pair is an OR-combined single arrival in the VM; no operand order exists. Not in this slice.")
            t_out[c] = t_in + 1
            remaining.discard(c)

    adder_roles = {}
    for c in order:
        if cells[c].core == "adder":
            srcs = [src for src, _ in inputs[c]["in"]]
            tks = [tiekeys.get((c, src)) for src in srcs]
            if all(t is not None for t in tks) and tks[0][0] != tks[1][0]:
                # DIFFERENT ranks (a file written by flexsub_compile_v1, #929): rank DEFINES operand identity -- A = lower
                # rank -- regardless of which source is earlier, because this assembler equalises arrival itself.
                sa, sb = sorted(srcs, key=lambda q: tiekeys[(c, q)])
                identity_by = "rank"
            else:
                sa, sb = sorted(srcs, key=lambda q: role_key(c, q, t_out))
                identity_by = "arbiter tie-break" if (tiekeys.get((c, sa)) is not None and t_out[sa] == t_out[sb]) else "arrival order"
            diff = t_out[sb] - t_out[sa]                         # >0: A is earlier -> pad A; <0: B is earlier -> pad B
            adder_roles[c] = {"A": sa, "B": sb, "identity_by": identity_by,
                              "pad_A": max(0, diff) if align else 0, "pad_B": max(0, -diff) if align else 0}
    return {"doc": doc, "recs": recs, "cells": cells, "edges": edges, "inputs": inputs, "outputs": outputs,
            "t_out": t_out, "order": order, "adder_roles": adder_roles, "align": align, "warnings": warnings,
            "eliminated_priority": eliminated}


def emit_top(top, p, width=32):
    cells, inputs, outputs, t_out, roles = p["cells"], p["inputs"], p["outputs"], p["t_out"], p["adder_roles"]
    L = []
    a = L.append
    a(f"// {top}.v -- GENERATED by tools/flexsub_icm_generate_v1.py (-s sub --icm); do not hand-edit.")
    a(f"// Source ICM-VIX: {p['doc'].name or '(unnamed)'}; {len(cells)} cells; align={'on' if p['align'] else 'OFF (negative control)'}.")
    a("// Straight wiring, fixed 1-cycle cells, no ack (Alan #924). Early adder operands are padded with relay cells.")
    a("`default_nettype none")
    a("`timescale 1ns / 1ps")
    entries = [c for c in p["order"] if not inputs.get(c)]
    exits = [c for c in p["order"] if not outputs.get(c)]

    def pname(io, cid):
        return re.sub(r"[^A-Za-z0-9_]", "_", io or cid)
    a(f"module {top} (")
    a("    input  wire clk,")
    a("    input  wire rst,")
    a("    input  wire cfg_valid,")
    ports = []
    for c in entries:
        n = pname(cells[c].io_name, c)
        ports += [f"    input  wire [31:0] in_{n}_data", f"    input  wire        in_{n}_valid"]
    for c in exits:
        n = pname(cells[c].io_name, c)
        ports += [f"    output wire [31:0] out_{n}_data", f"    output wire        out_{n}_valid"]
    a(",\n".join(ports))
    a(");")
    for c in p["order"]:
        i = _ident(c)
        a(f"wire [31:0] {i}_d; wire {i}_v;")
    a("")

    def src_nets(cid, srcid):
        i = _ident(srcid)
        return f"{i}_d", f"{i}_v"

    pad_count = 0
    for c in p["order"]:
        r, i = cells[c], _ident(c)
        cfg = r.core_config or {}
        if r.core == "ram":
            if not inputs.get(c):
                n = pname(r.io_name, c)
                din, vin = f"in_{n}_data", f"in_{n}_valid"
            else:
                (s, _), = inputs[c]["in"]
                din, vin = src_nets(c, s)
            a(f"ram_cell_v4s #(.CELL_ID(16'd{p['order'].index(c)})) {i} (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), "
              f".cfg_data(32'h0), .cfg_fixed_mode(1'b{int(bool(cfg.get('fixed_mode', 0)))}), "
              f".data_in({din}), .valid_in({vin}), .data_out({i}_d), .valid_out({i}_v));")
        else:   # adder
            role = roles[c]
            ad, av = src_nets(c, role["A"])
            bd, bv = src_nets(c, role["B"])
            for side in ("A", "B"):                             # delay the EARLY operand with flowing relay cells
                nets_d, nets_v = (ad, av) if side == "A" else (bd, bv)
                for k in range(role[f"pad_{side}"]):
                    pad_count += 1
                    pi = f"{i}_pad{side}{k}"
                    a(f"wire [31:0] {pi}_d; wire {pi}_v;")
                    a(f"ram_cell_v4s #(.CELL_ID(16'd{1000 + pad_count})) {pi} (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), "
                      f".cfg_data(32'h0), .cfg_fixed_mode(1'b0), .data_in({nets_d}), .valid_in({nets_v}), "
                      f".data_out({pi}_d), .valid_out({pi}_v));")
                    nets_d, nets_v = f"{pi}_d", f"{pi}_v"
                if side == "A":
                    ad, av = nets_d, nets_v
                else:
                    bd, bv = nets_d, nets_v
            sub = int(bool(cfg.get("subtract_mode", 0)))
            a(f"adder_cell_v4s #(.CELL_ID(16'd{p['order'].index(c)})) {i} (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), "
              f".cfg_data(32'h{sub}), .in_a({ad}), .in_b({bd}), .valid_in({bv}), .data_out({i}_d), .valid_out({i}_v));")
    for c in exits:
        n, i = pname(cells[c].io_name, c), _ident(c)
        a(f"assign out_{n}_data = {i}_d;")
        a(f"assign out_{n}_valid = {i}_v;")
    a("endmodule")
    return "\n".join(L) + "\n", pad_count


def generate(icm_path, output, top=None, align=True, cell_dir=None):
    p = plan(icm_path, align)
    stem = re.sub(r"[^A-Za-z0-9_]", "_", os.path.basename(icm_path).split(".")[0])
    top = top or f"icm_{stem}_sub"
    cell_dir = cell_dir or fsa.DEFAULT_CELL_DIR
    os.makedirs(output, exist_ok=True)
    text, pad_count = emit_top(top, p)
    top_path = os.path.join(output, f"{top}.v")
    open(top_path, "w").write(text)
    dep_pairs = fsa._derive_deps(top_path, cell_dir)
    for fname, src in dep_pairs:
        shutil.copy2(os.path.join(src, fname), os.path.join(output, fname))
    files = [f"{top}.v"] + [f for f, _ in dep_pairs]
    open(os.path.join(output, f"{top}.ys"), "w").write(
        f"read_verilog -sv {' '.join(files)}\nhierarchy -top {top}\nsynth_gowin -top {top} -json {top}.json\nstat\n")
    rec = {"generator": "tools/flexsub_icm_generate_v1.py", "family": "sub", "source": os.path.basename(icm_path),
           "top": top, "cells": len(p["cells"]), "pad_relay_cells": pad_count, "align": p["align"],
           "output_latency_cycles": {c: p["t_out"][c] for c in p["order"] if not p["outputs"].get(c)},
           "adder_roles": p["adder_roles"], "eliminated_priority_cells": p["eliminated_priority"], "files": files + [f"{top}.ys"]}
    json.dump(rec, open(os.path.join(output, "ASSEMBLY.json"), "w"), indent=2)
    return rec
