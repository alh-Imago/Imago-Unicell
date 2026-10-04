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

Constants: a constant source is a fixed-mode ram (always valid); its compiler-inserted relay chain just flows. The inputs must
not be presented until the constants have propagated -- ASSEMBLY.json `settle_cycles` says how many cycles after cfg_valid.

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

class IcmGenError(ValueError):
    pass


def _ident(cid):
    return "c_" + re.sub(r"[^A-Za-z0-9_]", "_", cid)


# Per-core translation table. "single": one data input; "pair": two operands (A first, B second, VM arrival-order rule).
# Every module's port list and timing was read from its source: each is exactly ONE cycle of latency.
CORES = {
    "ram": {"kind": "single", "module": "ram_cell_v4s"},
    "comparator": {"kind": "single", "module": "compare_cell_v4s"},    # signed(data) >= threshold -> 0/1, same as the VM
    "adder": {"kind": "pair", "module": "adder_cell_v4s"},
    "mul": {"kind": "pair", "module": "mul_cell_v4s"},                  # low 32 bits of the product
    # nano: first arrival = HELD operand A (registered, loaded by load_hold), second = FLOWING operand B. The held register
    # is loaded a cycle before the gate sees it, so A must arrive exactly ONE cycle before B (unlike adder/mul).
    "nano": {"kind": "pair", "module": "nano_cell_v4s", "hold_flow": True},
}
# The topology codes nano_cell_v4s actually implements (its `default` silently passes the held value -- never translate those).
NANO_TOPOLOGIES = {0x000, 0x02C, 0x001, 0x002, 0x004, 0x007, 0x024, 0x027, 0x0BC, 0x03C, 0x030, 0x0B0}
NANO_BENIGN_KEYS = {"ready", "routing_mask", "topology"}
SUPPORTED_CORES = set(CORES)
_SHIFT_COARSE = (1, 2, 4, 8, 12, 16, 20, 24, 28)    # the VM's/RTL's supported coarse taps (shift_lane_addon_v2)


def decode_addon(r):
    """(total_shift, direction, None) for an addon_config that is only a shift, (0, 0, None) for none, or
    (None, None, reason) when it needs something this translation does not have. Rules from the VM's own
    addon function: fine shift first, then the coarse shift only if its amount is one of the supported taps (an
    unsupported amount is a deliberate no-op); direction 0 = left, 1 = right (logical)."""
    ad = r.addon_config or {}
    if not ad:
        return 0, 0, None
    extra = {k: v for k, v in ad.items() if k not in ("shift_en", "direction", "shift_fine", "shift_amt") and v}
    if extra:
        return None, None, f"addon_config uses {sorted(extra)} -- only a plain shift is translated (mask/invert/lane_cut need their own cells)"
    if not ad.get("shift_en"):
        return 0, 0, None
    fine = ad.get("shift_fine", 0) & 3
    amt = ad.get("shift_amt", 0)
    coarse = amt if amt in _SHIFT_COARSE else 0
    return fine + coarse, 1 if ad.get("direction", 0) else 0, None


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
    srcs_of = {c: [src for lst in inputs.get(c, {}).values() for src, _ in lst] for c in cells}
    shifts = {}
    for r in cells.values():
        c = r.cell_id
        spec = CORES.get(r.core)
        if spec is None:
            why = ("no v4s branch cell exists (branch_cell_v4sa is flex-only)" if r.core == "branch"
                   else "arbiter that could not be eliminated (see above)" if r.core == "priority" else "not yet translated")
            problems.append(f"{c}: core {r.core!r} unsupported on sub -- {why}")
            continue
        total, direction, why = decode_addon(r)
        if why:
            problems.append(f"{c}: {why}")
        elif total:
            if r.core != "ram":
                problems.append(f"{c}: addon shift on a {r.core} cell -- only a ram relay's output shift is translated")
            else:
                shifts[c] = (total, direction)
        if r.core == "nano":
            cfgn = r.core_config or {}
            odd = sorted(k for k, v in cfgn.items() if k not in NANO_BENIGN_KEYS and v)
            if odd:
                problems.append(f"{c}: nano uses {odd} (relay/hold/update/one-shot modes) -- only the plain two-arrival gate is translated")
            if int(cfgn.get("topology", 0)) not in NANO_TOPOLOGIES:
                problems.append(f"{c}: nano topology {int(cfgn.get('topology', 0)):#x} is not implemented by nano_cell_v4s (its default would silently pass the held value)")
        is_source = not srcs_of[c]
        if r.preload_value is not None and not (r.core == "ram" and is_source):
            problems.append(f"{c}: preload_value on a cell that is not a source ram")
        if spec["kind"] == "pair" and len(srcs_of[c]) != 2:
            problems.append(f"{c}: {r.core} has {len(srcs_of[c])} source(s), needs exactly 2 "
                            f"(one stream carrying both operands needs a stagger spec -- not translated)")
        if spec["kind"] == "single":
            for role, lst in inputs.get(c, {}).items():
                if len(lst) > 1:
                    problems.append(f"{c}: {len(lst)} sources on one input (a merge) -- gated-OR merge not yet translated")
        if is_source and r.core != "ram":
            problems.append(f"{c}: {r.core} with no source is not a ram injection point or constant")
    if problems:
        raise IcmGenError("cannot generate sub Verilog from %s:\n  - " % os.path.basename(icm_path) + "\n  - ".join(problems))

    # constant-valued nodes: preloaded / fixed-mode source rams and anything fed only by them (always available)
    const = {c for c, r in cells.items() if not srcs_of[c] and (r.preload_value is not None or (r.core_config or {}).get("fixed_mode"))}
    grew = True
    while grew:
        grew = False
        for c in cells:
            if c not in const and srcs_of[c] and all(q in const for q in srcs_of[c]):
                const.add(c)
                grew = True

    order = []
    remaining = set(cells)
    while remaining:
        ready = [c for c in sorted(remaining) if all(q not in remaining for q in srcs_of[c])]
        if not ready:
            raise IcmGenError("internal: dependency order could not be resolved")
        order += ready
        remaining -= set(ready)

    t_vm, t_rtl, roles = {}, {}, {}

    def ident_key(c, q):
        return (t_vm[q], tiekeys.get((c, q), (0, 0)))

    for c in order:
        r, srcs = cells[c], srcs_of[c]
        extra = 1 if c in shifts else 0
        t_vm[c] = max((t_vm[q] for q in srcs), default=0) + 1            # the VM's hop-count time -- operand IDENTITY only
        if CORES[r.core]["kind"] == "pair":
            if all(q in const for q in srcs):
                raise IcmGenError(f"{c}: both operands are constants -- the compiler should have folded it")
            tks = [tiekeys.get((c, q)) for q in srcs]
            if all(t is not None for t in tks) and tks[0][0] != tks[1][0]:
                # DIFFERENT ranks (a file written by flexsub_compile_v1, #929): rank DEFINES operand identity, because this
                # assembler equalises arrival itself
                sa, sb = sorted(srcs, key=lambda q: tiekeys[(c, q)])
                identity_by = "rank"
            else:
                sa, sb = sorted(srcs, key=lambda q: ident_key(c, q))
                if t_vm[sa] == t_vm[sb] and tiekeys.get((c, sa)) is None:
                    raise IcmGenError(f"{c}: both operands arrive at hop {t_vm[sa]} with no arbiter to order them -- a same-time pair "
                                      f"is an OR-combined single arrival in the VM; no operand order exists. Not translated.")
                identity_by = "arbiter tie-break" if (tiekeys.get((c, sa)) is not None and t_vm[sa] == t_vm[sb]) else "arrival order"
            live = [q for q in (sa, sb) if q not in const]                  # constants never constrain timing
            pad = {sa: 0, sb: 0}
            hf = CORES[r.core].get("hold_flow")
            valid_from = "B" if sb not in const else "A"
            if hf:
                # the held operand A must arrive exactly ONE cycle before the flowing operand B
                if len(live) == 2:
                    tb = max(t_rtl[sb], t_rtl[sa] + 1)
                    if align:
                        pad = {sa: tb - 1 - t_rtl[sa], sb: tb - t_rtl[sb]}
                    t_in = tb
                elif sa not in const:                                         # A live, B constant: the gate sees A one cycle later
                    t_in = t_rtl[sa] + 1
                    valid_from = "A_delayed"                                  # valid_in must be A's valid delayed by one cycle
                else:                                                         # A constant (held for ever), B live
                    t_in = t_rtl[sb]
            else:
                if len(live) == 2 and align:
                    late = max(t_rtl[sa], t_rtl[sb])
                    pad = {sa: late - t_rtl[sa], sb: late - t_rtl[sb]}
                t_in = max((t_rtl[q] for q in live), default=0)
            roles[c] = {"A": sa, "B": sb, "identity_by": identity_by, "pad_A": pad[sa], "pad_B": pad[sb],
                        "valid_from": valid_from, "const_operands": [q for q in (sa, sb) if q in const]}
        else:
            live = [q for q in srcs if q not in const]
            t_in = max((t_rtl[q] for q in live), default=0)
        t_rtl[c] = None if c in const else t_in + 1 + extra
    return {"doc": doc, "recs": recs, "cells": cells, "edges": edges, "inputs": inputs, "outputs": outputs,
            "t_out": t_rtl, "t_vm": t_vm, "order": order, "adder_roles": roles, "align": align, "warnings": warnings,
            "eliminated_priority": eliminated, "const": const, "shifts": shifts}


def emit_top(top, p, width=32):
    cells, inputs, outputs, roles = p["cells"], p["inputs"], p["outputs"], p["adder_roles"]
    const, shifts = p["const"], p["shifts"]
    L = []
    a = L.append
    a(f"// {top}.v -- GENERATED by tools/flexsub_icm_generate_v1.py (-s sub --icm); do not hand-edit.")
    a(f"// Source ICM: {p['doc'].name or '(unnamed)'}; {len(cells)} cells; align={'on' if p['align'] else 'OFF (negative control)'}.")
    a("// Straight wiring, fixed 1-cycle cells, no ack (Alan #924). Early operands are padded with relay cells;")
    a("// constants are fixed-mode rams (always valid) and never constrain timing; shifts are separate shift_stage cells.")
    a("`default_nettype none")
    a("`timescale 1ns / 1ps")
    entries = [c for c in p["order"] if not inputs.get(c) and c not in const]
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
    idx = {c: k for k, c in enumerate(p["order"])}
    pad_count = [0]

    def cfg_args(data="32'h0", fixed=None):
        """Port-connection prefix every cell shares: clock, reset, config strobe and word (+ ram's fixed-mode port)."""
        t = ".clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(" + data + ")"
        return t + (", .cfg_fixed_mode(1'b" + str(int(fixed)) + ")" if fixed is not None else "")

    def hexw(v):
        return "32'h" + format(int(v) & 0xFFFFFFFF, "X")

    def padded(cid, d, v, n, tag):
        for k in range(n):                                      # delay with flowing ram relay cells
            pad_count[0] += 1
            pi = f"{_ident(cid)}_pad{tag}{k}"
            a(f"wire [31:0] {pi}_d; wire {pi}_v;")
            ca = cfg_args("32'h0", 0)
            a(f"ram_cell_v4s #(.CELL_ID(16'd{1000 + pad_count[0]})) {pi} ({ca}, "
              f".data_in({d}), .valid_in({v}), .data_out({pi}_d), .valid_out({pi}_v));")
            d, v = f"{pi}_d", f"{pi}_v"
        return d, v

    for c in p["order"]:
        r, i = cells[c], _ident(c)
        cfg = r.core_config or {}
        out_d, out_v = f"{i}_d", f"{i}_v"
        if c in shifts:                                         # the cell drives a private net; a shift_stage drives {i}_d/_v
            out_d, out_v = f"{i}_raw_d", f"{i}_raw_v"
            a(f"wire [31:0] {out_d}; wire {out_v};")
        srcs = [src for lst in inputs.get(c, {}).values() for src, _ in lst]
        kind = CORES[r.core]["kind"]
        mod = CORES[r.core]["module"]
        if kind == "pair":
            role = roles[c]
            ad, av = f"{_ident(role['A'])}_d", f"{_ident(role['A'])}_v"
            bd, bv = f"{_ident(role['B'])}_d", f"{_ident(role['B'])}_v"
            ad, av = padded(c, ad, av, role["pad_A"], "A")
            bd, bv = padded(c, bd, bv, role["pad_B"], "B")
            if CORES[r.core].get("hold_flow"):
                if role["valid_from"] == "A_delayed":                         # B is a constant: valid_in = A's valid, one cycle later
                    _, vin = padded(c, ad, av, 1, "V")
                else:
                    vin = bv
                ca = cfg_args(hexw(cfg.get("topology", 0)))
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, .hold_in_data({ad}), .load_hold({av}), "
                  f".flow_in_data({bd}), .valid_in({vin}), .data_out({out_d}), .valid_out({out_v}));")
            else:
                vin = bv if role["valid_from"] == "B" else av
                word = hexw(int(bool(cfg.get("subtract_mode", 0)))) if r.core == "adder" else "32'h0"
                ca = cfg_args(word)
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
                  f".in_a({ad}), .in_b({bd}), .valid_in({vin}), .data_out({out_d}), .valid_out({out_v}));")
        elif r.core == "comparator":
            ca = cfg_args(hexw(cfg.get("threshold", 0)))
            a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
              f".data_in({_ident(srcs[0])}_d), .valid_in({_ident(srcs[0])}_v), .data_out({out_d}), .valid_out({out_v}));")
        else:   # ram
            if c in const and not srcs:                          # a constant SOURCE: a fixed-mode ram, always valid (its relays just flow)
                val = r.preload_value if r.preload_value is not None else cfg.get("init_data", 0)
                ca = cfg_args(hexw(val), 1)
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
                  f".data_in(32'h0), .valid_in(1'b0), .data_out({out_d}), .valid_out({out_v}));")
            else:
                if srcs:
                    dd, vv = f"{_ident(srcs[0])}_d", f"{_ident(srcs[0])}_v"
                else:
                    n = pname(r.io_name, c)
                    dd, vv = f"in_{n}_data", f"in_{n}_valid"
                ca = cfg_args("32'h0", bool(cfg.get("fixed_mode", 0)))
                a(f"{mod} #(.CELL_ID(16'd{idx[c]})) {i} ({ca}, "
                  f".data_in({dd}), .valid_in({vv}), .data_out({out_d}), .valid_out({out_v}));")
        if c in shifts:
            amt, direction = shifts[c]
            ca = cfg_args("32'h0")
            a(f"shift_stage_v4s #(.CELL_ID(16'd{2000 + idx[c]}), .SHIFT_AMT(5'd{amt}), .DIRECTION(1'b{direction})) {i}_shift "
              f"({ca}, .data_in({out_d}), .valid_in({out_v}), .data_out({i}_d), .valid_out({i}_v));")
    for c in exits:
        n, i = pname(cells[c].io_name, c), _ident(c)
        a(f"assign out_{n}_data = {i}_d;")
        a(f"assign out_{n}_valid = {i}_v;")
    a("endmodule")
    return "\n".join(L) + "\n", pad_count[0]


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
           "constants": sorted(p["const"]), "settle_cycles": (max((p["t_vm"][c] for c in p["const"]), default=0) + 1) if p["const"] else 0, "shift_stages": {c: list(v) for c, v in p["shifts"].items()},
           "adder_roles": p["adder_roles"], "eliminated_priority_cells": p["eliminated_priority"], "files": files + [f"{top}.ys"]}
    json.dump(rec, open(os.path.join(output, "ASSEMBLY.json"), "w"), indent=2)
    return rec
