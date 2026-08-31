#!/usr/bin/env python3
"""
project_assemble_v1.py — points.md #552: the real "initial creator
tool" Alan asked for, distinct from both Composer (a visual placement-
*review* tool, `docs/stripped-cell/design-notes/composer_scope.md`,
explicitly NOT an RTL generator) and the Walker (`#501`, a live
hardware-discovery tool, gated on this build existing first).

REAL JOB: given a MAN file (real card capabilities) and a cell count,
generate one complete, self-contained folder -- every real Verilog
source file needed, a newly-generated top-level instantiating N real
`unicell_super_v3` cells in a grid with genuine cardinal wiring, a
matching `.qsf` (built on `#538`'s own PROVEN flat-file-path template,
the one that's actually worked every real time it was used), and a
matching `.sdc` -- ready to import directly into Quartus.

REAL, HONEST SCOPE, matching composer_scope.md's own discipline of
naming what's explicitly NOT here:
- No placement/routing optimization. Quartus's own fitter decides real
  physical placement regardless -- matches every build this project
  has run so far. Simple row-major grid tiling only.
- No DSL/program compilation. Unicell-S already owns that.
- No live host connectivity, JTAG burst mode, or ICM loading wired in
  yet -- Alan's own explicit sequencing: this build exists first, to
  get real dimensions/utilization; host connectivity is real, separate,
  later work.

A REAL, ALREADY-CONFIRMED RISK this design guards against directly,
not incidentally: Quartus prunes logic it can prove never reaches an
observable point -- confirmed concretely twice this session (#528,
#550) on single-core self-tests. At N cells, an ungated design (every
`cfg_valid`/`arrived_*` tied to a constant 0) risks Quartus proving
the WHOLE array dead and reporting a meaningless near-zero ALM count.
Guarded against here the same way every self-test this session already
did it (a real, unconstrained top-level input feeding in, a real
XOR-reduced output Quartus can't prove constant) -- just scaled to
cover the whole array via one entry cell and one XOR-tree, not one
core's own single probe.
"""

import argparse
import json
import math
import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERILOG_DIR = os.path.join(REPO_ROOT, "fpga", "verilog")

# Real, complete dependency set for unicell_super_v3.v -- every file
# it actually instantiates, confirmed directly against its own real
# QSF (fpga/quartus/top_super_v3_branch_test_v1.qsf, #548), not
# assumed.
V3_DEPENDENCIES = [
    "adder_v1.v",
    "ram_cell_v1.v",
    "adder_cell_v1.v",
    "accumulator_cell_v1.v",
    "compare_cell_v1.v",
    "latch_cell_v1.v",
    "nibble_mask_addon_v1.v",
    "shift_lane_addon_v1.v",
    "invert_addon_v1.v",
    "unicell_stripped_v1.v",
    "sequencer_cell_v1.v",
    "branch_cell_v1.v",
    "unicell_super_v3.v",
    "debug_issp_probe_v1.v",
]

QSF_BOILERPLATE = """set_global_assignment -name FAMILY "{family}"
set_global_assignment -name DEVICE {device}
set_global_assignment -name TOP_LEVEL_ENTITY {top}
set_global_assignment -name ORIGINAL_QUARTUS_VERSION 25.1STD.0
set_global_assignment -name LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name MIN_CORE_JUNCTION_TEMP 0
set_global_assignment -name MAX_CORE_JUNCTION_TEMP 100
set_global_assignment -name DEVICE_FILTER_PIN_COUNT 1152
set_global_assignment -name ERROR_CHECK_FREQUENCY_DIVISOR 2

set_location_assignment {clk_pin} -to CLK_100M
set_location_assignment {led0_pin} -to LED0_N
set_location_assignment {led1_pin} -to LED1_N

"""


def load_man(path):
    with open(path) as f:
        man = json.load(f)
    device = man["device"]
    board = man["board"]
    return {
        # Real, deliberate choice: NOT device["family"] directly (the
        # MAN file's own value is "Arria 10 GX", a real, accurate
        # human-readable description -- but every proven, actually-
        # working QSF this project has ever built uses the literal
        # string "Arria 10", confirmed directly against #538's own
        # template and every real build since. Found and fixed before
        # this ever reached a real Quartus project, not after.
        "family": "Arria 10",
        "device": device["part"],
        "alm_total": device["alm_total"],
        "dsp_total": device["dsp"]["total_blocks"],
        "clk_pin": board["clock"]["CLK_100M"]["pin"],
        "led0_pin": board["leds"]["LED0_N"],
        "led1_pin": board["leds"]["LED1_N"],
        "card_id": man["card_id"],
    }


def grid_dims(n):
    """Real, simple row-major grid -- roughly square, no placement
    optimization attempted (that's the fitter's real job, and later
    the Walker's for logical verification, not this tool's)."""
    rows = int(math.ceil(math.sqrt(n)))
    cols = int(math.ceil(n / rows))
    return rows, cols


def cell_positions(n, rows, cols):
    """Row-major fill, stopping at exactly n cells (the last row may
    be partial)."""
    positions = []
    for r in range(rows):
        for c in range(cols):
            if len(positions) >= n:
                return positions
            positions.append((r, c))
    return positions


def inst_name(r, c):
    return f"C_{r}_{c}"


def generate_top(top_name, n, rows, cols, cell_id_base=0x1000):
    positions = cell_positions(n, rows, cols)
    pos_set = set(positions)

    lines = []
    lines.append(f"// {top_name}.v — points.md #552/#554: real, generated {n}-cell array,")
    lines.append(f"// {rows}x{cols} row-major grid, unicell_super_v3 per cell.")
    lines.append("// Generated by tools/project_assemble_v1.py -- do not hand-edit;")
    lines.append("// regenerate from the same command instead.")
    lines.append("//")
    lines.append("// REAL FIX (#554), found from a real, honest Quartus result: the first")
    lines.append("// version of this generator tied cfg_valid=0 PERMANENTLY on every cell.")
    lines.append("// unicell_stripped_v1.v's own real config register only updates `if")
    lines.append("// (cfg_valid)` -- with cfg_valid permanently false, Quartus could PROVE")
    lines.append("// every cell's own SUPER_LATCH register never leaves its reset value")
    lines.append("// (nano, topology=0), for all 500 cells identically. That's not just")
    lines.append("// prunable dead logic -- it's a huge network of PROVABLY IDENTICAL,")
    lines.append("// fully-determined NOR-gate trees, exactly the shape Quartus's own")
    lines.append("// Boolean optimizer collapses aggressively (real result: 13 ALM for")
    lines.append("// 500 cells). Fixed here with a real, one-shot, broadcast config-load")
    lines.append("// pulse a few cycles after reset, loading a genuinely unconstrained")
    lines.append("// top-level input into every cell's own core_select field")
    lines.append("// simultaneously -- Quartus cannot prove which of the 8 real cores")
    lines.append("// ends up selected for any given cell, so it cannot collapse any of")
    lines.append("// them away.")
    lines.append("`default_nettype none")
    lines.append("`timescale 1ns / 1ps")
    lines.append("")
    lines.append(f"module {top_name} (")
    lines.append("    input  wire CLK_100M,")
    lines.append("    input  wire ENTRY_DATA,      // real, unconstrained -- feeds the array's own entry point")
    lines.append("    input  wire [4:0] CFG_SELECT, // real, unconstrained -- broadcast core_select, see header")
    lines.append("    output wire LED0_N,")
    lines.append("    output wire LED1_N")
    lines.append(");")
    lines.append("")
    lines.append("reg [1:0] div_cnt = 2'b00;")
    lines.append("always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;")
    lines.append("wire clk = div_cnt[1];   // 25 MHz")
    lines.append("")
    lines.append("reg [3:0] rst_sr = 4'hF;")
    lines.append("always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};")
    lines.append("wire rst = rst_sr[3];")
    lines.append("")
    lines.append("// Real, one-shot, broadcast config-load pulse -- fires exactly once,")
    lines.append("// a few cycles after reset, simultaneously to every cell in the array.")
    lines.append("reg [3:0] cfg_pulse_sr = 4'hF;")
    lines.append("always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};")
    lines.append("wire cfg_valid_bcast = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];   // one real cycle")
    lines.append("")
    lines.append("// Real, genuinely unconstrained SUPER_LATCH value broadcast to every")
    lines.append("// cell -- core_select from CFG_SELECT (real top-level input, cannot be")
    lines.append("// proven constant), remaining core_config/addon_config bits filled from")
    lines.append("// ENTRY_DATA repeated rather than left as a hardcoded, provably-known")
    lines.append("// constant (still not truly random, but no longer provably fixed).")
    lines.append("wire [79:0] cfg_data_bcast = {13'b0, {20{ENTRY_DATA}}, {42{ENTRY_DATA}}, CFG_SELECT};")
    lines.append("")
    lines.append("// Real entry point: ONE cell's own N-side arrival is driven from a")
    lines.append("// genuine, unconstrained top-level input.")
    lines.append("wire [31:0] entry_data = {31'b0, ENTRY_DATA};")
    lines.append("")

    # Per-cell wire declarations
    for (r, c) in positions:
        nm = inst_name(r, c)
        lines.append(f"wire [31:0] {nm}_dout_n, {nm}_dout_s, {nm}_dout_e, {nm}_dout_w;")
        lines.append(f"wire {nm}_fire_n, {nm}_fire_s, {nm}_fire_e, {nm}_fire_w;")
        lines.append(f"wire {nm}_ack_n, {nm}_ack_s, {nm}_ack_e, {nm}_ack_w;")
    lines.append("")

    # Instantiations
    for idx, (r, c) in enumerate(positions):
        nm = inst_name(r, c)
        cid = cell_id_base + idx

        def neighbor(nr, nc):
            return inst_name(nr, nc) if (nr, nc) in pos_set else None

        n_nb = neighbor(r - 1, c)
        s_nb = neighbor(r + 1, c)
        e_nb = neighbor(r, c + 1)
        w_nb = neighbor(r, c - 1)

        def data_in(direction, nb, opp):
            if nb is None:
                return "entry_data" if (direction == "n" and idx == 0) else "32'h0"
            return f"{nb}_dout_{opp}"

        def arrived_in(direction, nb, opp):
            if nb is None:
                return "ENTRY_DATA" if (direction == "n" and idx == 0) else "1'b0"
            return f"{nb}_fire_{opp}"

        def ack_in(direction, nb, opp):
            if nb is None:
                return "1'b0"
            return f"{nb}_ack_{opp}"

        def ready_in(nb):
            return "1'b1" if nb is None else "1'b1"

        lines.append(f"unicell_super_v3 #(.CELL_ID(16'h{cid:04X})) {nm} (")
        lines.append("    .clk(clk), .rst(rst),")
        lines.append(f"    .cfg_valid(cfg_valid_bcast), .cfg_data(cfg_data_bcast),")
        lines.append(f"    .data_in_n({data_in('n', n_nb, 's')}), .data_in_s({data_in('s', s_nb, 'n')}),")
        lines.append(f"    .data_in_e({data_in('e', e_nb, 'w')}), .data_in_w({data_in('w', w_nb, 'e')}),")
        lines.append(f"    .arrived_n({arrived_in('n', n_nb, 's')}), .arrived_s({arrived_in('s', s_nb, 'n')}),")
        lines.append(f"    .arrived_e({arrived_in('e', e_nb, 'w')}), .arrived_w({arrived_in('w', w_nb, 'e')}),")
        lines.append(f"    .data_out_n({nm}_dout_n), .data_out_s({nm}_dout_s), .data_out_e({nm}_dout_e), .data_out_w({nm}_dout_w),")
        lines.append(f"    .fire_n({nm}_fire_n), .fire_s({nm}_fire_s), .fire_e({nm}_fire_e), .fire_w({nm}_fire_w),")
        lines.append(f"    .ready_out(), .ready_in_n({ready_in(n_nb)}), .ready_in_s({ready_in(s_nb)}), .ready_in_e({ready_in(e_nb)}), .ready_in_w({ready_in(w_nb)}),")
        lines.append(f"    .ack_out_n({nm}_ack_n), .ack_out_s({nm}_ack_s), .ack_out_e({nm}_ack_e), .ack_out_w({nm}_ack_w),")
        lines.append(f"    .ack_in_n({ack_in('n', n_nb, 's')}), .ack_in_s({ack_in('s', s_nb, 'n')}), .ack_in_e({ack_in('e', e_nb, 'w')}), .ack_in_w({ack_in('w', w_nb, 'e')}),")
        lines.append("    .freeze_in(1'b0),")
        lines.append("    .program_in(1'b0), .program_done(),")
        lines.append("    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),")
        lines.append("    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),")
        lines.append("    .status_core_select()")
        lines.append(");")
        lines.append("")

    # Real XOR-tree reduction of every cell's own fire outputs into one
    # observable point -- the real anti-pruning guard, scaled to the
    # whole array.
    lines.append("// Real anti-pruning guard: every cell's own fire_* outputs XOR-reduced")
    lines.append("// into one real, observable signal -- Quartus cannot prove this")
    lines.append("// constant (it structurally depends on ENTRY_DATA's own real fanout),")
    lines.append("// so it cannot prune any contributing cell away.")
    terms = []
    for (r, c) in positions:
        nm = inst_name(r, c)
        terms.extend([f"{nm}_fire_n", f"{nm}_fire_s", f"{nm}_fire_e", f"{nm}_fire_w",
                      f"{nm}_dout_n[0]", f"{nm}_dout_s[0]", f"{nm}_dout_e[0]", f"{nm}_dout_w[0]"])
    xor_expr = " ^ ".join(terms)
    lines.append(f"wire array_alive = {xor_expr};")
    lines.append("")
    lines.append("reg [23:0] hb_cnt = 0;")
    lines.append("always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;")
    lines.append("")
    lines.append("assign LED0_N = ~hb_cnt[23];")
    lines.append("assign LED1_N = ~array_alive;   // real, observable, non-prunable")
    lines.append("")
    lines.append("// Real, JTAG-readable confirmation (points.md #529/#537's own proven")
    lines.append("// pattern) -- added BEFORE the first real build, not after, so a real")
    lines.append("// silicon check doesn't need a second ~2-hour rebuild just to add it.")
    lines.append("// probe[0]=array_alive (a real snapshot of the array's own current")
    lines.append("// state), probe[1]=heartbeat (continuously toggling, proves the design")
    lines.append("// is genuinely clocking -- use debug_issp_poll.tcl, not the older fixed-")
    lines.append("// gap script, per #537's own real aliasing finding).")
    lines.append("debug_issp_probe_v1 DEBUG_PROBE (")
    lines.append("    .err_sticky(array_alive),")
    lines.append("    .heartbeat(hb_cnt[23])")
    lines.append(");")
    lines.append("")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def generate_sdc(man):
    return (
        "# Generated by tools/project_assemble_v1.py -- points.md #552/#554.\n"
        "# Real clocking convention already established across this project.\n\n"
        "create_clock -name CLK_100M -period 10.000 [get_ports CLK_100M]\n\n"
        "create_generated_clock -name clk_div -source [get_ports CLK_100M] -divide_by 4 \\\n"
        "    [get_registers {div_cnt[1]}]\n\n"
        "derive_clock_uncertainty\n\n"
        "set_false_path -to [get_ports {LED0_N LED1_N}]\n"
        "set_false_path -from [get_ports {ENTRY_DATA}]\n"
        "set_false_path -from [get_ports {CFG_SELECT[*]}]\n"
    )


def generate_qsf(man, top_name):
    out = QSF_BOILERPLATE.format(
        family=man["family"], device=man["device"], top=top_name,
        clk_pin=man["clk_pin"], led0_pin=man["led0_pin"], led1_pin=man["led1_pin"],
    )
    for dep in V3_DEPENDENCIES:
        out += f"set_global_assignment -name VERILOG_FILE {dep}\n"
    out += f"set_global_assignment -name VERILOG_FILE {top_name}.v\n"
    out += "set_global_assignment -name QSYS_FILE issp.qsys\n"
    out += (
        "\n# points.md #529/#554: this project also needs the real, locally-\n"
        "# generated `issp` IP output (the actual .v/.qip Quartus produces from\n"
        "# issp.qsys via IP Catalog \"Generate HDL\" -- NOT the .qsys config file\n"
        "# alone). Add that generated .qip to this project before compiling --\n"
        "# not tracked in this repo, environment-specific generated output,\n"
        "# same convention issp.qsys itself already follows. The SAME already-\n"
        "# generated issp files used for earlier real builds this session work\n"
        "# here unmodified -- the probe's own bit layout never changes.\n\n"
    )
    out += f"set_global_assignment -name SDC_FILE {top_name}.sdc\n"
    return out


def assemble(man_path, cells, output, top=None):
    """The real, single implementation of this tool's own job --
    both main() (CLI) and any other caller (e.g. the frontend,
    points.md #557) call this directly, so there is exactly one real
    code path, never a duplicated copy that could drift out of sync."""
    if cells < 1:
        raise ValueError("cells must be >= 1")

    man = load_man(man_path)
    top_name = top or f"top_array_{cells}cells_v1"
    out_dir = output

    rows, cols = grid_dims(cells)
    os.makedirs(out_dir, exist_ok=True)

    for dep in V3_DEPENDENCIES:
        src = os.path.join(VERILOG_DIR, dep)
        if not os.path.exists(src):
            raise FileNotFoundError(f"missing real dependency {src}")
        shutil.copy(src, os.path.join(out_dir, dep))

    top_rtl = generate_top(top_name, cells, rows, cols)
    with open(os.path.join(out_dir, f"{top_name}.v"), "w") as f:
        f.write(top_rtl)

    with open(os.path.join(out_dir, f"{top_name}.sdc"), "w") as f:
        f.write(generate_sdc(man))

    with open(os.path.join(out_dir, f"{top_name}.qsf"), "w") as f:
        f.write(generate_qsf(man, top_name))

    return {
        "card_id": man["card_id"], "family": man["family"], "device": man["device"],
        "cells": cells, "rows": rows, "cols": cols, "alm_total": man["alm_total"],
        "output": out_dir, "top_name": top_name,
        "files_written": len(V3_DEPENDENCIES) + 3,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--man", required=True, help="Path to a MAN file (real card capabilities)")
    ap.add_argument("--cells", required=True, type=int, help="Number of unicell_super_v3 cells to generate")
    ap.add_argument("--output", required=True, help="Output folder for the generated project (required -- prevents build artifacts landing inside the tracked repo by accident)")
    ap.add_argument("--top", default=None, help="Top-level module name (default: top_array_<N>cells_v1)")
    args = ap.parse_args()

    try:
        result = assemble(args.man, args.cells, args.output, args.top)
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Card:   {result['card_id']} ({result['family']}, {result['device']})")
    print(f"Cells:  {result['cells']} (grid {result['rows']}x{result['cols']}, real ALM budget {result['alm_total']:,})")
    print(f"Output: {result['output']}")
    print(f"\nWrote {result['files_written']} real files (source + top-level RTL + .qsf + .sdc) to {result['output']}/")
    print(f"Import into Quartus using {result['top_name']}.qsf directly, matching #538's own proven flat-file template.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
