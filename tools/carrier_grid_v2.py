#!/usr/bin/env python3
"""tools/carrier_grid_v2.py -- ledger #1105: a CLONE of carrier_grid_v1.py (#1102, untouched) that can target VIXeN (unicell_vixen_v1, the default) as well as the v1d carrier, and writes join_mode (cfg_data[40]) for adder cells. ORIGINAL: ledger #1102: turn flat ICM records (the same records the VM loads) into a GRID OF VIX CARRIERS as Verilog -- one carrier per cell,
neighbours wired face to face, each carrier configured (core_select + core_config in its 160-bit VIX_LATCH word) from its record. This is the standard-mode (non-mirrored)
line: the carrier is one general cell that becomes a ram / adder / branch ... by configuration, not by which file was synthesised.

  python3 tools/carrier_grid_v2.py --icm nano/examples/looped_cordic_v1.icm-hier.json --out DIR --top NAME [--keep ram,adder,branch]

Writes DIR/NAME.v (the grid), DIR/carrier_sub.v (the carrier cut to the cores the design uses; the carrier file itself is untouched) and DIR/GRID.json (cell -> position,
core, VIX_LATCH word). Ports of the grid:
  clk, rst
  ld_valid, ld_cell (index of a cell), ld_word  -- re-commit ONE cell's configuration with its ram preload replaced by ld_word (how a saved value is loaded)
  tap_valid, tap_data                           -- the word arriving at the TAP cell (a relay chosen by --tap CELL_ID; steps are counted there)
  ext_*                                         -- the faces that lead out of the grid (data_in/arrived/ack) so a wrapper can feed or take
Direction bits in every mask: bit0 N, bit1 S, bit2 E, bit3 W (checked against the cores' own ready_in gating).
Honest limits: ram, adder and branch only (the cores the CORDIC needs); ready_in is tied high as in the generated arrays (proven pattern); no programming channel
is used (program_in tied 0): the grid is configured through cfg_valid/cfg_data only.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "nano", "examples"))

CARRIERS = {"vixen": ("unicell_vixen_v1m", True), "v1d": ("unicell_vix_carrier_v1dm", False)}
SEL = {"adder": 1, "ram": 2, "branch": 4}
FACE = {"N": 0, "S": 1, "E": 2, "W": 3}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


def mask(faces):
    m = 0
    for f in faces or []:
        m |= 1 << FACE[f]
    return m


def core_word(rec):
    """core_config bits [127:0] for a record (field maps from the _v4c RTL headers)."""
    c = rec.core_config
    if rec.core == "ram":
        w = mask(c.get("downstream_mask")) | (mask(c.get("upstream_mask")) << 6) | ((c.get("fixed_mode", 0) & 1) << 12)
        if rec.preload_value is not None:
            w |= (1 << 13) | ((rec.preload_value & 0xFFFFFFFF) << 14)
        return w
    if rec.core == "adder":
        w = mask(c.get("downstream_mask")) | (mask(c.get("upstream_mask")) << 6) | ((c.get("subtract_mode", 0) & 1) << 12)
        if c.get("join_mode", 0):
            w |= 1 << 40            # VIXeN only (adder_cell_v4e cfg_data[40]); the v1d carrier ignores the bit
        return w
    if rec.core == "branch":
        ud = c["upstream_dir"]
        ud = ud[0] if isinstance(ud, list) else ud
        w = FACE[ud]
        w |= (c.get("value_source_low", 0) & 1) << 3 | (c.get("value_source_equal", 0) & 1) << 4 | (c.get("value_source_high", 0) & 1) << 5
        w |= (c.get("fixed_value_low", 0) & 0x7F) << 6 | (c.get("fixed_value_equal", 0) & 0x7F) << 13 | (c.get("fixed_value_high", 0) & 0x7F) << 20
        w |= (c.get("emit_low", 0) & 1) << 27 | (c.get("emit_equal", 0) & 1) << 28 | (c.get("emit_high", 0) & 1) << 29
        w |= mask(c.get("route_low")) << 30 | mask(c.get("route_equal")) << 36 | mask(c.get("route_high")) << 42
        w |= (c.get("rolling_mode", 0) & 1) << 48
        return w
    raise SystemExit("core %r is not handled by the carrier grid generator (ram, adder, branch only)" % rec.core)


def vix_word(rec, ld_word=None):
    """the 160-bit VIX_LATCH word: [4:0] core_select, [132:5] core_config, add-on chain left at zero (pass-through)."""
    if ld_word is not None:
        if rec.core != "ram":
            raise SystemExit("a load word goes into a ram relay only")
        import copy
        r = copy.copy(rec)
        r.preload_value = ld_word & 0xFFFFFFFF
        rec = r
    return SEL[rec.core] | (core_word(rec) << 5)


def generate(records, out, top, tap_id, keep=("ram", "adder", "branch"), carrier="vixen"):
    import make_carrier_subset_v3 as sub
    mod, is_e = CARRIERS[carrier]
    os.makedirs(out, exist_ok=True)
    cv, removed = sub.make(list(keep), sub.SRC_VIXEN if is_e else sub.SRC)
    open(os.path.join(out, "carrier_sub.v"), "w").write(cv)
    pos = {(r.row, r.col): i for i, r in enumerate(records)}
    n = len(records)
    ids = [r.cell_id for r in records]
    if tap_id not in ids:
        raise SystemExit("tap cell %r not in the design" % tap_id)
    tap_i = ids.index(tap_id)
    L = []
    w = L.append
    w("// GENERATED by tools/carrier_grid_v1.py (ledger #1102) -- a grid of %d VIX carriers (module %s, cores kept: %s). Do not hand-edit." % (n, mod, ",".join(sorted(keep))))
    w("`default_nettype none\n`timescale 1ns / 1ps\n")
    ext = []  # faces that lead out of the grid
    for i, r in enumerate(records):
        for f, (dr, dc) in DELTA.items():
            if (r.row + dr, r.col + dc) not in pos:
                ext.append((i, f))
    w("module %s (" % top)
    w("    input  wire clk, input wire rst,")
    w("    input  wire ld_valid, input wire [15:0] ld_cell, input wire [31:0] ld_word,")
    w("    output wire tap_valid, output wire [31:0] tap_data,")
    w("    input  wire [%d:0] ext_arrived, input wire [%d:0] ext_ack_in," % (len(ext) - 1, len(ext) - 1))
    w("    input  wire [%d:0] ext_data_in," % (32 * len(ext) - 1))
    w("    output wire [%d:0] ext_fire, output wire [%d:0] ext_data_out" % (len(ext) - 1, 32 * len(ext) - 1))
    w(");")
    w("    reg boot_q = 1'b0; reg [3:0] rst_q = 4'hF;")
    w("    always @(posedge clk) begin rst_q <= {rst_q[2:0], rst}; boot_q <= (rst_q[3] && !rst); end")
    w("    wire cfg_boot = boot_q;   // one clock after reset is released")
    for i, r in enumerate(records):
        w("    wire [31:0] d%d_n, d%d_s, d%d_e, d%d_w; wire f%d_n, f%d_s, f%d_e, f%d_w; wire a%d_n, a%d_s, a%d_e, a%d_w;" % ((i,) * 12))
    extidx = {}
    for k, (i, f) in enumerate(ext):
        extidx[(i, f)] = k
    for i, r in enumerate(records):
        base = vix_word(r)
        ld = vix_word(r, 0) if r.core == "ram" else base
        cv_ = "(cfg_boot || (ld_valid && ld_cell == 16'd%d))" % i
        if r.core == "ram":
            cfgd = "(ld_valid && ld_cell == 16'd%d) ? ((160'h%x & ~(160'h1FFFFFFFF << 18)) | (160'h1 << 18) | ({128'b0, ld_word} << 19)) : 160'h%x" % (i, ld, base)
        else:
            cfgd = "160'h%x" % base
        # note: core bit 13 (load_data_valid) is VIX_LATCH bit 5+13 = 18; init_data[31:0] is VIX_LATCH [50:19]
        ins = []
        for f in "NSEW":
            dr, dc = DELTA[f]
            j = pos.get((r.row + dr, r.col + dc))
            fl = f.lower()
            if j is None:
                k = extidx[(i, f)]
                ins.append(".data_in_%s(ext_data_in[%d:%d]), .arrived_%s(ext_arrived[%d]), .ack_in_%s(ext_ack_in[%d])" % (fl, 32 * k + 31, 32 * k, fl, k, fl, k))
            else:
                o = OPP[f].lower()
                ins.append(".data_in_%s(d%d_%s), .arrived_%s(f%d_%s), .ack_in_%s(a%d_%s)" % (fl, j, o, fl, j, o, fl, j, o))
        outs = []
        for f in "nsew":
            outs.append(".data_out_%s(d%d_%s), .fire_%s(f%d_%s), .ack_out_%s(a%d_%s)" % (f, i, f, f, i, f, f, i, f))
        w("    %s #(.CELL_ID(16'h%04x)) C%d (   // %s (%d,%d) %s" % (mod, i, i, r.cell_id, r.row, r.col, r.core))
        w("        .clk(clk), .rst(rst),")
        w("        .active_in_n(1'b1), .active_in_s(1'b1), .active_in_e(1'b1), .active_in_w(1'b1),")
        w("        .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),")
        w("        .cfg_valid(%s), .cfg_data(%s)," % (cv_, cfgd))
        w("        " + ", ".join(ins) + ",")
        w("        " + ", ".join(outs) + ",")
        w("        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),")
        w("        .program_in(1'b0), .program_done(), .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),")
        w("        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),")
        w("        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),")
        w("        .freeze_out_n(), .freeze_out_s(), .freeze_out_e(), .freeze_out_w(),")
        w("        .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(),")
        w("        .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(),")
        w("        .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(),")
        w("        .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),")
        w("        .status_core_select()")
        w("    );")
    # external outputs
    for k, (i, f) in enumerate(ext):
        fl = f.lower()
        w("    assign ext_fire[%d] = f%d_%s; assign ext_data_out[%d:%d] = d%d_%s;" % (k, i, fl, 32 * k + 31, 32 * k, i, fl))
    # the tap: whichever neighbour feeds the tap cell (first arrival face)
    r = records[tap_i]
    terms_v, terms_d = [], []
    for f in "NSEW":
        dr, dc = DELTA[f]
        j = pos.get((r.row + dr, r.col + dc))
        if j is not None:
            o = OPP[f].lower()
            terms_v.append("f%d_%s" % (j, o))
            terms_d.append("(f%d_%s ? d%d_%s : 32'h0)" % (j, o, j, o))
    w("    assign tap_valid = %s;" % " | ".join(terms_v))
    w("    assign tap_data = %s;" % " | ".join(terms_d))
    w("endmodule")
    open(os.path.join(out, top + ".v"), "w").write("\n".join(L) + "\n")
    meta = {"top": top, "cells": [{"index": i, "cell_id": r.cell_id, "row": r.row, "col": r.col, "core": r.core, "vix_word": "%x" % vix_word(r), "io_name": r.io_name} for i, r in enumerate(records)],
            "ext": [{"k": k, "cell": records[i].cell_id, "face": f} for k, (i, f) in enumerate(ext)], "tap": tap_id}
    json.dump(meta, open(os.path.join(out, "GRID.json"), "w"), indent=1)
    return meta


def _faces(m):
    return [f for f, b in FACE.items() if (m >> b) & 1]


def records_from_latch(grid_json):
    """The reverse direction (card -> VM): rebuild flat ICM records from the VIX_LATCH words in GRID.json alone (ram / adder / branch), so a VM can be started from latch states only.
    Cell ids, positions and io names come from the same file; everything else (cores, masks, modes, constants, preloads) is decoded from the 160-bit word."""
    from icm_v3 import IcmV3Record as Rec
    d = grid_json if isinstance(grid_json, dict) else json.load(open(grid_json))
    inv = {v: k for k, v in SEL.items()}
    out = []
    for c in d["cells"]:
        w = int(c["vix_word"], 16) if isinstance(c["vix_word"], str) else c["vix_word"]
        core = inv[w & 0x1F]
        cw = (w >> 5) & ((1 << 128) - 1)
        pre = None
        if core == "ram":
            cfg = {"downstream_mask": _faces(cw & 0xF), "upstream_mask": _faces((cw >> 6) & 0xF), "fixed_mode": (cw >> 12) & 1}
            if (cw >> 13) & 1:
                pre = (cw >> 14) & 0xFFFFFFFF
        elif core == "adder":
            cfg = {"downstream_mask": _faces(cw & 0xF), "upstream_mask": _faces((cw >> 6) & 0xF)}
            if (cw >> 12) & 1:
                cfg["subtract_mode"] = 1
            if (cw >> 40) & 1:
                cfg["join_mode"] = 1
        else:
            inv_face = {v: k for k, v in FACE.items()}
            cfg = {"upstream_dir": [inv_face[cw & 7]],
                   "value_source_low": (cw >> 3) & 1, "value_source_equal": (cw >> 4) & 1, "value_source_high": (cw >> 5) & 1,
                   "fixed_value_low": (cw >> 6) & 0x7F, "fixed_value_equal": (cw >> 13) & 0x7F, "fixed_value_high": (cw >> 20) & 0x7F,
                   "emit_low": (cw >> 27) & 1, "emit_equal": (cw >> 28) & 1, "emit_high": (cw >> 29) & 1,
                   "route_low": _faces((cw >> 30) & 0xF), "route_equal": _faces((cw >> 36) & 0xF), "route_high": _faces((cw >> 42) & 0xF),
                   "rolling_mode": (cw >> 48) & 1}
        out.append(Rec(cell_id=c["cell_id"], row=c["row"], col=c["col"], core=core, core_config=cfg, addon_config={}, io_name=c.get("io_name"), preload_value=pre))
    return out


def simulate(records, tap_id, clocks, loads=(), workdir=None, top="carrier_grid_sim", keep=("ram", "adder", "branch"), carrier="vixen"):
    """Generate the grid, compile it with iverilog and run `clocks` clocks after the boot configuration. `loads` = [(clock, cell_id, word)]: re-commit that ram cell with its preload replaced.
    Returns [(clock, signed_value)] for every clock the TAP cell is being offered a word (one word = one such clock in the loop)."""
    import subprocess, tempfile, verilog_deps_v1 as vd
    work = workdir or tempfile.mkdtemp(prefix="cgrid_")
    meta = generate(records, work, top, tap_id, keep, carrier)
    mod, is_e = CARRIERS[carrier]
    n = len(meta["ext"])
    idx = {c["cell_id"]: c["index"] for c in meta["cells"]}
    ld = "".join("        wait_clk(%d); ld_cell = 16'd%d; ld_word = 32'd%d; ld_valid = 1; @(posedge clk); ld_valid = 0;\n" % (c, idx[cid], w & 0xFFFFFFFF) for c, cid, w in sorted(loads))
    tb = """`timescale 1ns/1ps
module tb;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg ld_valid = 0; reg [15:0] ld_cell = 0; reg [31:0] ld_word = 0;
    wire tap_valid; wire [31:0] tap_data;
    wire [%(n)d-1:0] ef; wire [%(nb)d-1:0] eo;
    %(top)s g(.clk(clk), .rst(rst), .ld_valid(ld_valid), .ld_cell(ld_cell), .ld_word(ld_word), .tap_valid(tap_valid), .tap_data(tap_data),
        .ext_arrived(%(n)d'b0), .ext_ack_in(%(n)d'b0), .ext_data_in({%(nb)d{1'b0}}), .ext_fire(ef), .ext_data_out(eo));
    integer c = 0;
    always @(posedge clk) begin c <= c + 1; if (tap_valid) $display("TAP %%0d %%0d", c, $signed(tap_data)); end
    task wait_clk(input integer k); begin while (c < k) @(posedge clk); end endtask
    initial begin
        repeat (4) @(posedge clk); rst = 0;
%(ld)s        wait_clk(%(clocks)d); $finish;
    end
endmodule
""" % dict(n=n, nb=32 * n, top=top, ld=ld, clocks=clocks)
    open(os.path.join(work, "tb.v"), "w").write(tb)
    deps = sorted(vd.deps(mod, [work, os.path.join(ROOT, "fpga", "verilog")]))
    deps = [os.path.relpath(d, work) if d.startswith(work) else d for d in deps]
    r = subprocess.run(["iverilog", "-g2012", "-o", "t.vvp", "tb.v", top + ".v"] + deps, cwd=work, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("iverilog: " + r.stderr[-800:])
    o = subprocess.run(["vvp", "t.vvp"], cwd=work, capture_output=True, text=True, timeout=1800).stdout
    return [(int(p[1]), int(p[2])) for p in (l.split() for l in o.splitlines()) if p and p[0] == "TAP"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--icm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", required=True)
    ap.add_argument("--tap", default="lp.fb19")
    ap.add_argument("--keep", default="ram,adder,branch")
    ap.add_argument("--carrier", default="vixen", choices=sorted(CARRIERS))
    a = ap.parse_args()
    from hierarchical_icm_prototype_loader import load_hierarchical, flatten
    recs, _ = flatten(load_hierarchical(a.icm))
    m = generate(recs, a.out, a.top, a.tap, a.keep.split(","), a.carrier)
    print("wrote", os.path.join(a.out, a.top + ".v"), "cells:", len(m["cells"]), "outside faces:", len(m["ext"]))


if __name__ == "__main__":
    main()
