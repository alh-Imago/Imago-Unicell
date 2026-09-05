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
import re
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

# points.md #578: real, complete dependency set for unicell_super_v4.v
# (the shared-external-storage shell, #573) -- the v2 cores plus
# unicell_stripped_v3.v, confirmed directly against top_unicell_super_
# test_v4.qsf, the one real, already-working build this mirrors.
V4_DEPENDENCIES = [
    "adder_v1.v",
    "ram_cell_v2.v",
    "adder_cell_v2.v",
    "accumulator_cell_v2.v",
    "compare_cell_v2.v",
    "latch_cell_v2.v",
    "nibble_mask_addon_v1.v",
    "shift_lane_addon_v1.v",
    "invert_addon_v1.v",
    "unicell_stripped_v3.v",
    "sequencer_cell_v2.v",
    "branch_cell_v2.v",
    "unicell_super_v4.v",
    "debug_issp_probe_v1.v",
]

# points.md #578: real registry mapping a real, named shell version to
# its own real module name + dependency set -- generalizes generate_
# top()/generate_qsf()/assemble() from the original v3-only hardcoding
# to a real, explicit choice between the two shells now that a real
# comparative Quartus number is wanted at ARRAY scale (#575/#577's own
# comparison was N=1 only). v5 deliberately NOT included here -- #577
# already found it performs the same as v4, not better, so an array
# build of it wouldn't answer a new question.
# points.md #647: real, complete dependency set for unicell_vix_
# carrier_v1.v -- all 9 unified-carrier cores, all 9 real cardinal
# control shells (#639/#645/#646), the 3 addon modules, and adder_v1.v
# (adder_cell_v4's own internal dependency). Confirmed directly against
# the real iverilog regression command line used throughout #647's own
# session, not assumed.
VIX_DEPENDENCIES = [
    "adder_v1.v",
    "nibble_mask_addon_v1.v",
    "shift_lane_addon_v1.v",
    "invert_addon_v1.v",
    "nano_gate_v4.v",
    "adder_cell_v4.v",
    "ram_cell_v4.v",
    "compare_cell_v4.v",
    "branch_cell_v4.v",
    "accumulator_cell_v4.v",
    "latch_cell_v4.v",
    "sequencer_cell_v4.v",
    "command_cell_v4.v",
    "nano_shell_v1.v",
    "adder_shell_v1.v",
    "ram_shell_v1.v",
    "compare_shell_v1.v",
    "branch_shell_v1.v",
    "accumulator_shell_v1.v",
    "latch_shell_v1.v",
    "sequencer_shell_v1.v",
    "command_shell_v1.v",
    "unicell_vix_carrier_v1.v",
    "debug_issp_probe_v1.v",
]

SHELL_REGISTRY = {
    "v3": {"module": "unicell_super_v3", "dependencies": V3_DEPENDENCIES},
    "v4": {"module": "unicell_super_v4", "dependencies": V4_DEPENDENCIES},
    "vix": {"module": "unicell_vix_carrier_v1", "dependencies": VIX_DEPENDENCIES},
}

# points.md #590: real, custom-dependency-list support, per Alan's own
# direct request -- mixing and matching core versions (compare_cell_
# v3.v with 7 other v1 cores, #584; a hand-built moat tile, #588) has
# meant hand-writing a fresh QSF dependency list, or a whole new shell
# file, every single time. A real `--shell-file`/`--shell-module` pair
# lets `--shell` point at ANY real shell file (not just the two
# hardcoded in SHELL_REGISTRY), and `--file-list`/`--files` supplies
# its own real dependency list explicitly, overriding SHELL_REGISTRY
# entirely. Neither replaces hand-building a genuinely NEW shell file
# with a different per-slot core mix (unicell_super_v6.v/v7.v are
# still real, hand-written files, `#584`/`#587`) -- this only removes
# the SEPARATE, real, repeated chore of re-deriving that shell's own
# QSF file list by hand every time it's used in an array build.

MODULE_DECL_RE = re.compile(r'^\s*module\s+(\w+)', re.MULTILINE)
# Real, deliberately conservative heuristic for finding module
# INSTANTIATIONS in a shell file -- Verilog instantiation syntax is
# `IDENTIFIER [#(...)] IDENTIFIER (`, but so is a function/task call
# and several other constructs. This regex requires the pattern to
# start a statement (only whitespace/newline before it) and the
# module name to look like a real module (lowercase-led identifier,
# matching this project's own real naming convention throughout --
# confirmed against every real core/shell file already in this repo
# before writing this pattern, not guessed) to keep the real false-
# positive rate low. This is a real, useful, ADVISORY check -- it
# is NOT a substitute for a real compile (iverilog/Quartus remain the
# only real, authoritative confirmation), and is documented as such
# everywhere it's surfaced to the person using this tool.
INSTANTIATION_RE = re.compile(
    r'^\s*([a-z][a-zA-Z0-9_]*)\s*(?:#\s*\([^;]*?\))?\s+[A-Za-z_]\w*\s*\(',
    re.MULTILINE
)
# Real, known non-module keywords that can otherwise false-positive
# against INSTANTIATION_RE's own deliberately loose pattern.
VERILOG_KEYWORDS_NOT_MODULES = {
    "if", "else", "case", "casex", "casez", "for", "while", "repeat",
    "begin", "end", "function", "task", "always", "initial", "assign",
    "wire", "reg", "input", "output", "inout", "parameter", "localparam",
    "generate", "endgenerate", "module", "endmodule", "genvar",
}


def resolve_dependency_list(file_list_path=None, files_string=None):
    """points.md #590: resolve a real, explicit dependency list from
    EITHER a real text file (--file-list, one real filename per line,
    blank lines and #-comments ignored) OR a real inline comma-
    separated string (--files, e.g. "compare_cell_v3.v,latch_cell_v3.v").
    Returns None if neither is given (the caller should fall back to
    SHELL_REGISTRY's own real, existing default list in that case)."""
    if file_list_path:
        real_names = []
        with open(file_list_path) as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if line:
                    real_names.append(line)
        return real_names
    if files_string:
        return [n.strip() for n in files_string.split(",") if n.strip()]
    return None


def discover_declared_modules(src_dir, filenames):
    """points.md #590: for each real file in filenames, find every
    real `module <name>` declaration it contains (a file can declare
    more than one, e.g. adder_v1.v-style small helper modules bundled
    alongside a core). Returns {module_name: filename}. Raises a
    real, clear error immediately if a named file doesn't exist --
    better than a confusing Quartus-side "missing file" error later."""
    declared = {}
    for fname in filenames:
        path = os.path.join(src_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"real dependency file not found: {path}")
        with open(path) as f:
            text = f.read()
        for m in MODULE_DECL_RE.finditer(text):
            declared[m.group(1)] = fname
    return declared


def discover_instantiated_modules(shell_path):
    """points.md #590: real, best-effort scan of a shell file's own
    body for module instantiations, per INSTANTIATION_RE's own
    documented, deliberately conservative heuristic. Returns a set of
    real candidate module names -- NOT guaranteed complete or free of
    false positives, advisory only (see this function's own module-
    level comment for why)."""
    with open(shell_path) as f:
        text = f.read()
    found = set()
    for m in INSTANTIATION_RE.finditer(text):
        name = m.group(1)
        if name not in VERILOG_KEYWORDS_NOT_MODULES:
            found.add(name)
    return found


def check_dependency_compatibility(src_dir, shell_path, shell_module, dependency_filenames):
    """points.md #590: real, advisory compatibility check, per Alan's
    own real acknowledgment that mixing core versions "would have to
    check compatibility too." Confirms (a) the shell file itself
    really declares shell_module, and (b) every module the shell file
    appears to instantiate is declared somewhere in the real
    dependency list. Returns a list of real, human-readable warning
    strings (empty if nothing looked wrong) -- this NEVER raises or
    blocks generation on its own; it's a real, early, friendly signal,
    not a hard gate, since the heuristic instantiation scan can both
    miss real problems and flag real non-problems. The only real,
    authoritative confirmation remains a real compile."""
    warnings = []
    declared = discover_declared_modules(src_dir, dependency_filenames)

    if shell_module not in declared:
        # The shell file itself might not be IN dependency_filenames
        # (callers pass the shell separately) -- check it directly too.
        shell_declared = discover_declared_modules(src_dir, [os.path.basename(shell_path)])
        if shell_module not in shell_declared:
            warnings.append(
                f"shell module '{shell_module}' was not found declared in "
                f"{os.path.basename(shell_path)} -- check --shell-module matches "
                f"the real module name inside that file."
            )

    instantiated = discover_instantiated_modules(shell_path)
    missing = sorted(m for m in instantiated if m not in declared and m != shell_module)
    if missing:
        warnings.append(
            "the shell file appears to instantiate the following real module(s) "
            f"not found declared in the real dependency list: {', '.join(missing)}. "
            "This is a real, heuristic scan (not a full parser) -- it can miss "
            "real problems and flag real non-problems, so treat this as a "
            "prompt to double-check, not a guaranteed diagnosis. A real compile "
            "(iverilog or Quartus) remains the authoritative confirmation."
        )
    return warnings

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


# ── points.md #567: real registry of the 8 standalone core types,
# for single-core-type array generation. Port lists here are NOT
# guessed -- they're taken directly from the real, already-verified
# differential testbenches built in #563/#564/#566 (tb_*_v2_diff_v1.v/
# tb_nano_v3_diff_v1.v), which are already proven correct against each
# core's own real v1 behavior. ──────────────────────────────────────
CORE_REGISTRY = {
    "ram_cell":         {"cfg_width": 64, "extra_status": ["status_data_valid"], "nano_shaped": False, "extra_deps": []},
    "adder_cell":       {"cfg_width": 64, "extra_status": ["status_data_valid", "status_a_arrived"], "nano_shaped": False, "extra_deps": ["adder_v1.v"]},
    "accumulator_cell": {"cfg_width": 64, "extra_status": ["status_negative"], "nano_shaped": False, "extra_deps": []},
    "compare_cell":     {"cfg_width": 64, "extra_status": ["status_data_valid"], "nano_shaped": False, "extra_deps": []},
    "latch_cell":       {"cfg_width": 64, "extra_status": ["status_latched"], "nano_shaped": False, "extra_deps": []},
    "sequencer_cell":   {"cfg_width": 64, "extra_status": ["status_seq_index"], "nano_shaped": False, "extra_deps": []},
    "branch_cell":      {"cfg_width": 64, "extra_status": ["status_data_valid"], "nano_shaped": False, "extra_deps": []},
    "unicell_stripped": {"cfg_width": 128, "extra_status": [], "nano_shaped": True, "extra_deps": []},
}


def resolve_core_file(base_name, core_path):
    """points.md #567: version-agnostic file resolution -- find every
    real file matching `{base_name}_v<N>.v` in core_path, return the
    one with the highest N. Real, deliberate choice: prefers the
    newest real version automatically rather than needing every
    caller to track version numbers by hand."""
    pattern = re.compile(rf"^{re.escape(base_name)}_v(\d+)\.v$")
    candidates = []
    for fname in os.listdir(core_path):
        m = pattern.match(fname)
        if m:
            candidates.append((int(m.group(1)), fname))
    if not candidates:
        raise FileNotFoundError(f"no real file matching {base_name}_v<N>.v found in {core_path}")
    candidates.sort()
    return candidates[-1][1]  # highest version wins


def generate_single_core_top(top_name, module_name, base_name, n, rows, cols, cell_id_base=0x1000, probe_name=None):
    """points.md #567: a genuinely simpler generation mode than the
    full 8-core shell -- no core_select, no CFG_SELECT broadcast,
    since there's only ever one real core type here. Still needs the
    same real anti-pruning discipline (#554's own real lesson): a
    genuine one-shot config load from an unconstrained input, so
    Quartus can't prove every cell's own config is a known constant
    and collapse the array."""
    info = CORE_REGISTRY[base_name]
    positions = cell_positions(n, rows, cols)
    pos_set = set(positions)
    cfg_width = info["cfg_width"]

    lines = []
    lines.append(f"// {top_name}.v — points.md #567: real, generated {n}-cell array,")
    lines.append(f"// {rows}x{cols} row-major grid, SINGLE core type ({base_name}), no shell.")
    lines.append("// Generated by tools/project_assemble_v1.py -- do not hand-edit;")
    lines.append("// regenerate from the same command instead.")
    lines.append("`default_nettype none")
    lines.append("`timescale 1ns / 1ps")
    lines.append("")
    lines.append(f"module {top_name} (")
    lines.append("    input  wire CLK_100M,")
    lines.append("    input  wire ENTRY_DATA,")
    lines.append("    output wire LED0_N,")
    lines.append("    output wire LED1_N")
    lines.append(");")
    lines.append("")
    lines.append("reg [1:0] div_cnt = 2'b00;")
    lines.append("always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;")
    lines.append("wire clk = div_cnt[1];")
    lines.append("")
    lines.append("reg [3:0] rst_sr = 4'hF;")
    lines.append("always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};")
    lines.append("wire rst = rst_sr[3];")
    lines.append("")
    lines.append("reg [3:0] cfg_pulse_sr = 4'hF;")
    lines.append("always @(posedge clk) if (!rst) cfg_pulse_sr <= {cfg_pulse_sr[2:0], 1'b0};")
    lines.append("wire cfg_valid_bcast = !rst && cfg_pulse_sr[3] && !cfg_pulse_sr[2];")
    lines.append("")
    lines.append(f"// Real, genuinely unconstrained config broadcast to every cell --")
    lines.append(f"// prevents Quartus proving all {n} cells' own config is a known")
    lines.append("// constant and collapsing the array (#554's own real lesson).")
    lines.append(f"wire [{cfg_width-1}:0] cfg_data_bcast = {{{cfg_width}{{ENTRY_DATA}}}};")
    lines.append("")
    lines.append("wire [31:0] entry_data = {31'b0, ENTRY_DATA};")
    lines.append("")

    for (r, c) in positions:
        nm = inst_name(r, c)
        lines.append(f"wire [31:0] {nm}_dout_n, {nm}_dout_s, {nm}_dout_e, {nm}_dout_w;")
        lines.append(f"wire {nm}_fire_n, {nm}_fire_s, {nm}_fire_e, {nm}_fire_w;")
        lines.append(f"wire {nm}_ack_n, {nm}_ack_s, {nm}_ack_e, {nm}_ack_w;")
    lines.append("")

    for idx, (r, c) in enumerate(positions):
        nm = inst_name(r, c)
        cid = cell_id_base + idx

        def neighbor(nr, nc):
            return inst_name(nr, nc) if (nr, nc) in pos_set else None

        n_nb, s_nb, e_nb, w_nb = neighbor(r-1, c), neighbor(r+1, c), neighbor(r, c+1), neighbor(r, c-1)

        def data_in(direction, nb, opp):
            if nb is None:
                return "entry_data" if (direction == "n" and idx == 0) else "32'h0"
            return f"{nb}_dout_{opp}"

        def arrived_in(direction, nb, opp):
            if nb is None:
                return "ENTRY_DATA" if (direction == "n" and idx == 0) else "1'b0"
            return f"{nb}_fire_{opp}"

        def ack_in(nb, opp):
            return "1'b0" if nb is None else f"{nb}_ack_{opp}"

        lines.append(f"{module_name} #(.CELL_ID(16'h{cid:04X})) {nm} (")
        lines.append("    .clk(clk), .rst(rst),")
        lines.append(f"    .cfg_valid(cfg_valid_bcast), .cfg_data(cfg_data_bcast),")
        lines.append(f"    .data_in_n({data_in('n', n_nb, 's')}), .data_in_s({data_in('s', s_nb, 'n')}),")
        lines.append(f"    .data_in_e({data_in('e', e_nb, 'w')}), .data_in_w({data_in('w', w_nb, 'e')}),")
        lines.append(f"    .arrived_n({arrived_in('n', n_nb, 's')}), .arrived_s({arrived_in('s', s_nb, 'n')}),")
        lines.append(f"    .arrived_e({arrived_in('e', e_nb, 'w')}), .arrived_w({arrived_in('w', w_nb, 'e')}),")
        lines.append(f"    .data_out_n({nm}_dout_n), .data_out_s({nm}_dout_s), .data_out_e({nm}_dout_e), .data_out_w({nm}_dout_w),")
        lines.append(f"    .fire_n({nm}_fire_n), .fire_s({nm}_fire_s), .fire_e({nm}_fire_e), .fire_w({nm}_fire_w),")
        lines.append(f"    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),")
        lines.append(f"    .ack_out_n({nm}_ack_n), .ack_out_s({nm}_ack_s), .ack_out_e({nm}_ack_e), .ack_out_w({nm}_ack_w),")
        lines.append(f"    .ack_in_n({ack_in(n_nb, 's')}), .ack_in_s({ack_in(s_nb, 'n')}), .ack_in_e({ack_in(e_nb, 'w')}), .ack_in_w({ack_in(w_nb, 'e')}),")
        lines.append("    .freeze_in(1'b0),")
        if info["nano_shaped"]:
            lines.append("    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),")
            lines.append("    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),")
            lines.append("    .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),")
            lines.append("    .a_update_in(1'b0), .a_self_update_in(1'b0),")
            lines.append("    .program_in(1'b0), .program_done(),")
            lines.append("    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),")
            lines.append("    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),")
            lines.append("    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()")
        else:
            status_ports = ", ".join(f".{s}()" for s in info["extra_status"])
            lines.append(f"    {status_ports}")
        lines.append(");")
        lines.append("")

    terms = []
    for (r, c) in positions:
        nm = inst_name(r, c)
        terms.extend([f"{nm}_fire_n", f"{nm}_fire_s", f"{nm}_fire_e", f"{nm}_fire_w",
                      f"{nm}_dout_n[0]", f"{nm}_dout_s[0]", f"{nm}_dout_e[0]", f"{nm}_dout_w[0]"])
    lines.append(f"wire array_alive = {' ^ '.join(terms)};")
    lines.append("")
    lines.append("reg [23:0] hb_cnt = 0;")
    lines.append("always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;")
    lines.append("")
    lines.append("assign LED0_N = ~hb_cnt[23];")
    lines.append("assign LED1_N = ~array_alive;")
    lines.append("")
    if probe_name:
        lines.append(f"debug_issp_probe_v1 {probe_name} (")
        lines.append("    .err_sticky(array_alive),")
        lines.append("    .heartbeat(hb_cnt[23])")
        lines.append(");")
        lines.append("")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


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


def generate_logiclock_assignments(positions, fixed_alm_per_cell=None, headroom=1.25, alm_per_lab=8.484):
    """points.md #582/#583: real, per-cell LogicLock regions -- one
    region per cell, with the cell's own top-level instance (and
    everything under it: every core, every addon, the shell's own
    write-arbitration logic) assigned as that region's sole member.

    points.md #583: a real, honest finding from the FIRST real
    LogicLock build (v3, N=10, #583) forced this function to grow a
    second real mode. `LL_AUTO_SIZE ON` (the original, still the
    default when fixed_alm_per_cell is None) genuinely improved real
    Fmax (+9.7%) for near-zero real ALM cost -- but its own real,
    measured region sizes reserved 3.10x more physical die area than
    the real logic inside them needed (32,090 ALM-equivalent LAB
    capacity reserved for 10,343 real ALM used, 32.2% average real
    utilization). Since LogicLock regions cannot overlap, that's a
    real, hard area cost, not a soft one -- it dropped the real,
    area-limited max cell count from `#579`'s own ALM-only ~244 down
    to a real ~78, WORSE than no LogicLock at all for Alan's own real
    "useful area available" concern.

    When fixed_alm_per_cell is given (a real, empirically-measured
    per-cell ALM figure -- e.g. #579's own real 1030.52 for v3,
    #580's own real 1307.42 for v4), this instead emits `LL_AUTO_SIZE
    OFF` with an explicit, computed `LL_WIDTH`/`LL_HEIGHT` sized to
    `fixed_alm_per_cell * headroom` ALM, converted to LAB units via
    `alm_per_lab` -- a real, but ONLY SINGLE-DATA-POINT-CALIBRATED
    (from this same #583 real build) ALM-per-LAB density, not a
    device datasheet constant. `headroom` (default 1.25 = 25% real
    slack over the measured figure) is a real, deliberately modest
    choice compared to AUTO_SIZE's own real ~3.1x, not zero slack --
    real per-cell ALM cost genuinely varies cell-to-cell (#579's own
    real per-cell range was 900-1189 for v3), so SOME headroom over
    the average is a real, honest necessity, not padding for its own
    sake. Regions are made square (equal width/height) for simplicity,
    real, honest, not claimed optimal -- a real next real-world result
    is the only way to know if this specific choice is any good."""
    lines = []
    lines.append("")
    if fixed_alm_per_cell is not None:
        target_alm = fixed_alm_per_cell * headroom
        target_labs = target_alm / alm_per_lab
        side = max(1, math.ceil(math.sqrt(target_labs)))
        lines.append(f"# points.md #583: real, FIXED-size LogicLock regions -- {side}x{side}")
        lines.append(f"# LABs each (~{target_labs:.0f} LABs, ~{target_alm:.0f} ALM at "
                      f"~{alm_per_lab:.2f} ALM/LAB, {fixed_alm_per_cell:.2f} real measured")
        lines.append(f"# ALM/cell x {headroom:.2f} headroom) -- NOT AUTO_SIZE, which #583's own")
        lines.append("# real build showed reserves ~3.1x more physical area than needed,")
        lines.append("# a real, hard area cost since LogicLock regions cannot overlap.")
    else:
        lines.append("# points.md #582: real, per-cell LogicLock regions -- one fixed-")
        lines.append("# size, floating region per cell, forcing every real instance under")
        lines.append("# that cell (every core, every addon, the shell's own write logic)")
        lines.append("# to be placed as one contiguous block, rather than scattered across")
        lines.append("# the die the way the unconstrained baseline build showed.")
    for (r, c) in positions:
        nm = inst_name(r, c)
        region = f"LL_{nm}"
        lines.append(f"set_global_assignment -name LL_ENABLED ON -section_id {region}")
        if fixed_alm_per_cell is not None:
            lines.append(f"set_global_assignment -name LL_AUTO_SIZE OFF -section_id {region}")
            lines.append(f"set_global_assignment -name LL_WIDTH {side} -section_id {region}")
            lines.append(f"set_global_assignment -name LL_HEIGHT {side} -section_id {region}")
        else:
            lines.append(f"set_global_assignment -name LL_AUTO_SIZE ON -section_id {region}")
        lines.append(f"set_global_assignment -name LL_STATE FLOATING -section_id {region}")
        lines.append(f"set_global_assignment -name LL_RESERVED OFF -section_id {region}")
        lines.append(f"set_instance_assignment -name LL_MEMBER_OF {region} -to {nm} -section_id {region}")
    return "\n".join(lines) + "\n"


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


def generate_top(top_name, n, rows, cols, cell_id_base=0x1000, probe_name=None, shell="v3", shell_module=None):
    # points.md #590: shell_module, when given, overrides SHELL_REGISTRY's
    # own lookup -- lets --shell-module point this generator at ANY real
    # shell (e.g. unicell_super_v6/v7, #584/#587) sharing v3/v4's own
    # real port list, without adding it to the registry first.
    module_name = shell_module if shell_module else SHELL_REGISTRY[shell]["module"]
    positions = cell_positions(n, rows, cols)
    pos_set = set(positions)

    lines = []
    lines.append(f"// {top_name}.v — points.md #552/#554/#578: real, generated {n}-cell array,")
    lines.append(f"// {rows}x{cols} row-major grid, {module_name} per cell.")
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

        lines.append(f"{module_name} #(.CELL_ID(16'h{cid:04X})) {nm} (")
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
    if probe_name:
        lines.append("// Real, JTAG-readable confirmation (points.md #529/#537's own proven")
        lines.append("// pattern) -- added BEFORE the first real build, not after, so a real")
        lines.append("// silicon check doesn't need a second ~2-hour rebuild just to add it.")
        lines.append("// probe[0]=array_alive (a real snapshot of the array's own current")
        lines.append("// state), probe[1]=heartbeat (continuously toggling, proves the design")
        lines.append("// is genuinely clocking -- use debug_issp_poll.tcl, not the older fixed-")
        lines.append("// gap script, per #537's own real aliasing finding).")
        lines.append(f"debug_issp_probe_v1 {probe_name} (")
        lines.append("    .err_sticky(array_alive),")
        lines.append("    .heartbeat(hb_cnt[23])")
        lines.append(");")
        lines.append("")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def generate_top_vix(top_name, n, rows, cols, cell_id_base=0x1000, probe_name=None):
    """points.md #647/#648: real, generated N-cell array of
    `unicell_vix_carrier_v1.v` -- the 9-core VIX Carrier, a genuinely
    different real port shape from every prior shell this tool
    generates (real cardinal `active_in_x`/`freeze_in_x` instead of a
    single flat pin each, a real 160-bit VIX_LATCH instead of the old
    80-bit SUPER_LATCH, and command mode's own new drive-side
    programming-channel ports with no analogue in any prior shell) --
    kept as its own dedicated generator rather than bent into
    `generate_top()`'s own v3/v4-shaped wiring.

    Real, necessary EXTENSION of `#554`'s own anti-pruning fix, not
    just a reapplication of it: with 9 real selectable cores instead
    of the old lineage's up to 8, and a genuinely new RECEIVE-side
    programming channel PLUS command mode's own new DRIVE-side one,
    every one of `program_in`/`prog_arrived_in_x`/`prog_data_in_x`/
    `prog_ack_in_x` is ALSO broadcast from the same real, unconstrained
    ENTRY_DATA-derived signal used for `core_select`/`core_config` --
    tying any of these to a hard 0 constant would let Quartus prove
    the entire receive-side PROG_ID decode path (all 9 cores) AND
    command mode's own relay-confirmation logic permanently dead,
    the exact same real failure class `#554` already found once
    (13 ALM for 500 cells), just via a different signal this time.
    """
    module_name = SHELL_REGISTRY["vix"]["module"]
    positions = cell_positions(n, rows, cols)
    pos_set = set(positions)

    lines = []
    lines.append(f"// {top_name}.v — points.md #647/#648: real, generated {n}-cell VIX")
    lines.append(f"// Carrier array, {rows}x{cols} row-major grid, {module_name} per cell.")
    lines.append("// Generated by tools/project_assemble_v1.py --shell vix -- do not")
    lines.append("// hand-edit; regenerate from the same command instead.")
    lines.append("//")
    lines.append("// Real, necessary extension of #554's own anti-pruning fix (see this")
    lines.append("// function's own real docstring): core_select/core_config AND the")
    lines.append("// receive-side programming channel AND command mode's own new")
    lines.append("// drive-side channel are ALL broadcast from real, unconstrained")
    lines.append("// top-level inputs -- none of the 9 real cores' own PROG_ID decode")
    lines.append("// or command's own relay-confirmation logic can be proven dead.")
    lines.append("`default_nettype none")
    lines.append("`timescale 1ns / 1ps")
    lines.append("")
    lines.append(f"module {top_name} (")
    lines.append("    input  wire CLK_100M,")
    lines.append("    input  wire ENTRY_DATA,      // real, unconstrained -- feeds the array's own entry point AND every anti-pruning broadcast below")
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
    lines.append("// Real, genuinely unconstrained VIX_LATCH value broadcast to every")
    lines.append("// cell -- core_select from CFG_SELECT (real top-level input, cannot be")
    lines.append("// proven constant), core_config's full real 128 bits filled from")
    lines.append("// ENTRY_DATA repeated rather than a hardcoded, provably-known constant.")
    lines.append("wire [159:0] cfg_data_bcast = {27'b0, {128{ENTRY_DATA}}, CFG_SELECT};")
    lines.append("")
    lines.append("// Real entry point: ONE cell's own N-side arrival is driven from a")
    lines.append("// genuine, unconstrained top-level input.")
    lines.append("wire [31:0] entry_data = {31'b0, ENTRY_DATA};")
    lines.append("")
    lines.append("// Real, unconstrained broadcast covering the RECEIVE-side programming")
    lines.append("// channel (every one of the 9 cores) and command mode's own DRIVE-side")
    lines.append("// confirmation input -- see this function's own real docstring.")
    lines.append("wire [31:0] prog_data_bcast = {32{ENTRY_DATA}};")
    lines.append("")

    # Per-cell wire declarations
    for (r, c) in positions:
        nm = inst_name(r, c)
        lines.append(f"wire [31:0] {nm}_dout_n, {nm}_dout_s, {nm}_dout_e, {nm}_dout_w;")
        lines.append(f"wire {nm}_fire_n, {nm}_fire_s, {nm}_fire_e, {nm}_fire_w;")
        lines.append(f"wire {nm}_ack_n, {nm}_ack_s, {nm}_ack_e, {nm}_ack_w;")
        lines.append(f"wire {nm}_ready;")
        lines.append(f"wire {nm}_prog_done;")
        lines.append(f"wire {nm}_pack_n, {nm}_pack_s, {nm}_pack_e, {nm}_pack_w;")
        lines.append(f"wire {nm}_fzo_n, {nm}_fzo_s, {nm}_fzo_e, {nm}_fzo_w;")
        lines.append(f"wire {nm}_pon, {nm}_pos, {nm}_poe, {nm}_pow;")
        lines.append(f"wire [31:0] {nm}_pdon, {nm}_pdos, {nm}_pdoe, {nm}_pdow;")
        lines.append(f"wire {nm}_paon, {nm}_paos, {nm}_paoe, {nm}_paow;")
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

        lines.append(f"{module_name} #(.CELL_ID(16'h{cid:04X})) {nm} (")
        lines.append("    .clk(clk), .rst(rst),")
        lines.append("    .active_in_n(1'b1), .active_in_s(1'b1), .active_in_e(1'b1), .active_in_w(1'b1),")
        lines.append("    .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(1'b0),")
        lines.append(f"    .cfg_valid(cfg_valid_bcast), .cfg_data(cfg_data_bcast),")
        lines.append(f"    .data_in_n({data_in('n', n_nb, 's')}), .data_in_s({data_in('s', s_nb, 'n')}),")
        lines.append(f"    .data_in_e({data_in('e', e_nb, 'w')}), .data_in_w({data_in('w', w_nb, 'e')}),")
        lines.append(f"    .arrived_n({arrived_in('n', n_nb, 's')}), .arrived_s({arrived_in('s', s_nb, 'n')}),")
        lines.append(f"    .arrived_e({arrived_in('e', e_nb, 'w')}), .arrived_w({arrived_in('w', w_nb, 'e')}),")
        lines.append(f"    .data_out_n({nm}_dout_n), .data_out_s({nm}_dout_s), .data_out_e({nm}_dout_e), .data_out_w({nm}_dout_w),")
        lines.append(f"    .fire_n({nm}_fire_n), .fire_s({nm}_fire_s), .fire_e({nm}_fire_e), .fire_w({nm}_fire_w),")
        lines.append(f"    .ready_out({nm}_ready), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),")
        lines.append(f"    .ack_out_n({nm}_ack_n), .ack_out_s({nm}_ack_s), .ack_out_e({nm}_ack_e), .ack_out_w({nm}_ack_w),")
        lines.append(f"    .ack_in_n({ack_in('n', n_nb, 's')}), .ack_in_s({ack_in('s', s_nb, 'n')}), .ack_in_e({ack_in('e', e_nb, 'w')}), .ack_in_w({ack_in('w', w_nb, 'e')}),")
        lines.append(f"    .program_in(ENTRY_DATA), .program_done({nm}_prog_done),")
        lines.append(f"    .prog_data_in_n(prog_data_bcast), .prog_data_in_s(prog_data_bcast), .prog_data_in_e(prog_data_bcast), .prog_data_in_w(prog_data_bcast),")
        lines.append("    .prog_arrived_in_n(ENTRY_DATA), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),")
        lines.append(f"    .prog_ack_out_n({nm}_pack_n), .prog_ack_out_s({nm}_pack_s), .prog_ack_out_e({nm}_pack_e), .prog_ack_out_w({nm}_pack_w),")
        lines.append(f"    .freeze_out_n({nm}_fzo_n), .freeze_out_s({nm}_fzo_s), .freeze_out_e({nm}_fzo_e), .freeze_out_w({nm}_fzo_w),")
        lines.append(f"    .program_out_n({nm}_pon), .program_out_s({nm}_pos), .program_out_e({nm}_poe), .program_out_w({nm}_pow),")
        lines.append(f"    .prog_data_out_n({nm}_pdon), .prog_data_out_s({nm}_pdos), .prog_data_out_e({nm}_pdoe), .prog_data_out_w({nm}_pdow),")
        lines.append(f"    .prog_arrived_out_n({nm}_paon), .prog_arrived_out_s({nm}_paos), .prog_arrived_out_e({nm}_paoe), .prog_arrived_out_w({nm}_paow),")
        lines.append("    .prog_ack_in_n(ENTRY_DATA), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),")
        lines.append("    .status_core_select()")
        lines.append(");")
        lines.append("")

    lines.append("// Real anti-pruning guard: every cell's own real output -- ordinary")
    lines.append("// cardinal fire/data, ready, program_done, every real prog_ack_out,")
    lines.append("// and command mode's own new drive-side outputs -- XOR-reduced into")
    lines.append("// one real, observable signal Quartus cannot prove constant.")
    terms = []
    for (r, c) in positions:
        nm = inst_name(r, c)
        terms.extend([
            f"{nm}_fire_n", f"{nm}_fire_s", f"{nm}_fire_e", f"{nm}_fire_w",
            f"{nm}_dout_n[0]", f"{nm}_dout_s[0]", f"{nm}_dout_e[0]", f"{nm}_dout_w[0]",
            f"{nm}_ready", f"{nm}_prog_done",
            f"{nm}_pack_n", f"{nm}_pack_s", f"{nm}_pack_e", f"{nm}_pack_w",
            f"{nm}_fzo_n", f"{nm}_fzo_s", f"{nm}_fzo_e", f"{nm}_fzo_w",
            f"{nm}_pon", f"{nm}_pos", f"{nm}_poe", f"{nm}_pow",
            f"{nm}_pdon[0]", f"{nm}_pdos[0]", f"{nm}_pdoe[0]", f"{nm}_pdow[0]",
            f"{nm}_paon", f"{nm}_paos", f"{nm}_paoe", f"{nm}_paow",
        ])
    xor_expr = " ^ ".join(terms)
    lines.append(f"wire array_alive = {xor_expr};")
    lines.append("")
    lines.append("reg [23:0] hb_cnt = 0;")
    lines.append("always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;")
    lines.append("")
    lines.append("assign LED0_N = ~hb_cnt[23];")
    lines.append("assign LED1_N = ~array_alive;   // real, observable, non-prunable")
    lines.append("")
    if probe_name:
        lines.append("// Real, JTAG-readable confirmation (points.md #529/#537's own proven")
        lines.append("// pattern).")
        lines.append(f"debug_issp_probe_v1 {probe_name} (")
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


def generate_qsf(man, top_name, probe_name=None, shell="v3", logiclock=False, cell_positions_list=None,
                  ll_fixed_alm=None, ll_headroom=1.25, custom_dependencies=None):
    # points.md #590: custom_dependencies, when given, overrides
    # SHELL_REGISTRY's own registered list entirely -- see
    # resolve_dependency_list().
    dependencies = custom_dependencies if custom_dependencies is not None else SHELL_REGISTRY[shell]["dependencies"]
    out = QSF_BOILERPLATE.format(
        family=man["family"], device=man["device"], top=top_name,
        clk_pin=man["clk_pin"], led0_pin=man["led0_pin"], led1_pin=man["led1_pin"],
    )
    for dep in dependencies:
        if dep == "debug_issp_probe_v1.v" and not probe_name:
            continue
        out += f"set_global_assignment -name VERILOG_FILE {dep}\n"
    out += f"set_global_assignment -name VERILOG_FILE {top_name}.v\n"
    if probe_name:
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
    if logiclock and cell_positions_list:
        out += generate_logiclock_assignments(cell_positions_list, fixed_alm_per_cell=ll_fixed_alm, headroom=ll_headroom)
    return out


def generate_single_core_qsf(man, top_name, resolved_filename, extra_deps, probe_name=None):
    out = QSF_BOILERPLATE.format(
        family=man["family"], device=man["device"], top=top_name,
        clk_pin=man["clk_pin"], led0_pin=man["led0_pin"], led1_pin=man["led1_pin"],
    )
    out += f"set_global_assignment -name VERILOG_FILE {resolved_filename}\n"
    for dep in extra_deps:
        out += f"set_global_assignment -name VERILOG_FILE {dep}\n"
    if probe_name:
        out += "set_global_assignment -name VERILOG_FILE debug_issp_probe_v1.v\n"
    out += f"set_global_assignment -name VERILOG_FILE {top_name}.v\n"
    if probe_name:
        out += "set_global_assignment -name QSYS_FILE issp.qsys\n"
        out += (
            "\n# points.md #529/#567: needs the real, locally-generated `issp`\n"
            "# IP output added to this project before compiling -- same real,\n"
            "# already-generated issp files used for every other build this\n"
            "# session work here unmodified.\n\n"
        )
    out += f"set_global_assignment -name SDC_FILE {top_name}.sdc\n"
    return out


def assemble(man_path, cells, output, top=None, single_core=None, core_path=None, probe_name=None, shell="v3", logiclock=False, ll_fixed_alm=None, ll_headroom=1.25,
             shell_file=None, shell_module=None, file_list=None, files_string=None):
    """The real, single implementation of this tool's own job --
    both main() (CLI) and any other caller (e.g. the frontend,
    points.md #557) call this directly, so there is exactly one real
    code path, never a duplicated copy that could drift out of sync.

    points.md #567: single_core, when given a real core base name
    (e.g. "ram_cell"), switches to single-core-type generation --
    a card of just that one core, no shell, no core_select. core_path
    overrides where real source files are read from (default:
    fpga/verilog); resolve_core_file() picks the highest real version
    found there automatically, ignoring version suffixes.

    points.md #578: shell selects which real 8-core shell version the
    FULL-array path (single_core not given) generates -- "v3" (each
    core's own separate internal storage, the original default) or
    "v4" (the shared external-storage shell, #573). Ignored when
    single_core is given (that path never touches the shell at all).

    points.md #582: logiclock, when True, adds a real per-cell
    LogicLock region (fixed-membership, auto-sized, floating -- see
    generate_logiclock_assignments()) for every cell in a FULL-array
    build, forcing each cell's own logic to be placed as one
    contiguous block instead of left to the fitter's own unconstrained
    global optimization (the real cause found in #579-#581's own
    Chip Planner evidence of cross-die scattering). Ignored when
    single_core is given.

    points.md #583: ll_fixed_alm, when given alongside logiclock,
    switches region sizing from AUTO_SIZE (found to reserve a real
    ~3.1x more physical area than needed, #583's own real finding) to
    an explicit, computed fixed size based on this real, empirically-
    measured per-cell ALM figure plus ll_headroom (default 1.25 =
    25% real slack).

    points.md #590: shell_file/shell_module let this generator target
    ANY real shell file (not just the two hardcoded in SHELL_REGISTRY)
    sharing v3/v4's own real port list -- e.g. unicell_super_v6.v/v7.v
    (#584/#587), built by hand when mixing core versions. file_list/
    files_string supply a real, explicit dependency list (a text file,
    one real filename per line, or an inline comma-separated string),
    overriding SHELL_REGISTRY's own registered list entirely. Per
    Alan's own real request: this removes the separate, repeated
    chore of hand-deriving a QSF file list every time a custom shell
    or a mixed set of core versions is used in an array build. A real,
    advisory compatibility check (check_dependency_compatibility())
    runs automatically whenever shell_file is given, and its own real
    warnings (if any) are returned in the result dict rather than
    printed silently, so a caller can surface them."""
    if cells < 1:
        raise ValueError("cells must be >= 1")
    if shell_module is None and shell not in SHELL_REGISTRY:
        raise ValueError(f"unknown shell '{shell}' -- real options: {', '.join(SHELL_REGISTRY)}")

    man = load_man(man_path)
    src_dir = core_path or VERILOG_DIR
    rows, cols = grid_dims(cells)
    os.makedirs(output, exist_ok=True)

    if single_core:
        if single_core not in CORE_REGISTRY:
            raise ValueError(f"unknown core '{single_core}' -- real options: {', '.join(CORE_REGISTRY)}")
        info = CORE_REGISTRY[single_core]
        resolved = resolve_core_file(single_core, src_dir)
        top_name = top or f"top_{single_core}_{cells}cells_v1"

        shutil.copy(os.path.join(src_dir, resolved), os.path.join(output, resolved))
        for dep in info["extra_deps"]:
            dep_src = os.path.join(src_dir, dep)
            if not os.path.exists(dep_src):
                raise FileNotFoundError(f"missing real dependency {dep_src}")
            shutil.copy(dep_src, os.path.join(output, dep))
        files_written = 1 + len(info["extra_deps"])
        if probe_name:
            probe_src = os.path.join(VERILOG_DIR, "debug_issp_probe_v1.v")
            shutil.copy(probe_src, os.path.join(output, "debug_issp_probe_v1.v"))
            files_written += 1

        resolved_module_name = resolved[:-2]  # strip real ".v" -- the actual module name inside includes the version suffix
        top_rtl = generate_single_core_top(top_name, resolved_module_name, single_core, cells, rows, cols, probe_name=probe_name)
        with open(os.path.join(output, f"{top_name}.v"), "w") as f:
            f.write(top_rtl)
        with open(os.path.join(output, f"{top_name}.sdc"), "w") as f:
            f.write(generate_sdc(man))
        with open(os.path.join(output, f"{top_name}.qsf"), "w") as f:
            f.write(generate_single_core_qsf(man, top_name, resolved, info["extra_deps"], probe_name=probe_name))

        return {
            "card_id": man["card_id"], "family": man["family"], "device": man["device"],
            "cells": cells, "rows": rows, "cols": cols, "alm_total": man["alm_total"],
            "output": output, "top_name": top_name,
            "files_written": files_written + 3,
            "single_core": single_core, "resolved_file": resolved,
            "probe_name": probe_name,
        }

    ll_suffix = ""
    if logiclock:
        ll_suffix = "_llfix" if ll_fixed_alm is not None else "_ll"
    shell_tag = shell_module if shell_module else shell
    top_name = top or f"top_array_{shell_tag}_{cells}cells{ll_suffix}_v1"

    # points.md #590: resolve the real dependency list -- an explicit
    # custom list (file_list/files_string) always wins; otherwise fall
    # back to SHELL_REGISTRY's own registered default for `shell`.
    dependencies = resolve_dependency_list(file_list, files_string)
    if dependencies is None:
        dependencies = SHELL_REGISTRY[shell]["dependencies"]

    real_module_name = shell_module if shell_module else SHELL_REGISTRY[shell]["module"]

    compat_warnings = []
    if shell_file:
        # A custom shell file needs to be in the real dependency list
        # too (it's real RTL just like every other file here) -- add
        # it if the person didn't already include it themselves.
        shell_fname = os.path.basename(shell_file)
        if shell_fname not in dependencies:
            dependencies = dependencies + [shell_fname]
        # points.md #590: real, forgiving path resolution -- try the
        # given path exactly as given first (absolute, or relative to
        # the current working directory, matching how a person would
        # naturally type it on a command line), and only fall back to
        # resolving the bare filename against src_dir (this tool's own
        # established convention for every other dependency) if that
        # exact path doesn't exist. A real bug here on the first
        # attempt at this feature (a doubled fpga/verilog/fpga/verilog/
        # path) showed this ambiguity needed real, explicit handling,
        # not just documentation asking for one specific format.
        if os.path.exists(shell_file):
            shell_src_path = shell_file
        else:
            candidate = os.path.join(src_dir, shell_fname)
            if os.path.exists(candidate):
                shell_src_path = candidate
            else:
                raise FileNotFoundError(
                    f"--shell-file '{shell_file}' not found as given, and "
                    f"'{shell_fname}' not found in {src_dir} either."
                )
        compat_warnings = check_dependency_compatibility(src_dir, shell_src_path, real_module_name, dependencies)

    files_written = 0
    for dep in dependencies:
        if dep == "debug_issp_probe_v1.v" and not probe_name:
            continue
        src = os.path.join(src_dir, dep)
        if not os.path.exists(src):
            raise FileNotFoundError(f"missing real dependency {src}")
        shutil.copy(src, os.path.join(output, dep))
        files_written += 1

    if shell == "vix":
        top_rtl = generate_top_vix(top_name, cells, rows, cols, probe_name=probe_name)
    else:
        top_rtl = generate_top(top_name, cells, rows, cols, probe_name=probe_name, shell=shell, shell_module=shell_module)
    with open(os.path.join(output, f"{top_name}.v"), "w") as f:
        f.write(top_rtl)

    with open(os.path.join(output, f"{top_name}.sdc"), "w") as f:
        f.write(generate_sdc(man))

    positions = cell_positions(cells, rows, cols)
    with open(os.path.join(output, f"{top_name}.qsf"), "w") as f:
        f.write(generate_qsf(man, top_name, probe_name=probe_name, shell=shell,
                              logiclock=logiclock, cell_positions_list=positions,
                              ll_fixed_alm=ll_fixed_alm, ll_headroom=ll_headroom,
                              custom_dependencies=dependencies))

    return {
        "card_id": man["card_id"], "family": man["family"], "device": man["device"],
        "cells": cells, "rows": rows, "cols": cols, "alm_total": man["alm_total"],
        "output": output, "top_name": top_name,
        "files_written": files_written + 3,
        "probe_name": probe_name, "shell": shell_tag, "logiclock": logiclock,
        "compat_warnings": compat_warnings,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--man", required=True, help="Path to a MAN file (real card capabilities)")
    ap.add_argument("--cells", required=True, type=int, help="Number of cells to generate")
    ap.add_argument("--output", required=True, help="Output folder for the generated project (required -- prevents build artifacts landing inside the tracked repo by accident)")
    ap.add_argument("--top", default=None, help="Top-level module name (default: auto-generated)")
    ap.add_argument("-S", "--single-core", default=None,
                     help=f"Generate an array of ONE real core type instead of the full 8-core shell. Real options: {', '.join(CORE_REGISTRY)}")
    ap.add_argument("-x", "--core-path", default=None,
                     help="Real path to search for core source files (default: fpga/verilog). Files are matched by base name only, ignoring version suffixes -- the highest real version found wins.")
    ap.add_argument("-P", "--probe", nargs="?", const="DEBUG_PROBE", default=None, metavar="NAME",
                     help="points.md #569: include a real ISSP debug probe, optionally naming the instance (default name if -P given with no value: DEBUG_PROBE). Omitted by default -- the LED-based anti-pruning check works independently of the probe, so it's a real, optional extra for JTAG confirmation, not required for a pure resource/timing build.")
    ap.add_argument("--shell", default="v3", choices=sorted(SHELL_REGISTRY),
                     help="points.md #578: which real 8-core shell to array (ignored with -S). 'v3' = each core's own separate storage (the original default). 'v4' = the shared external-storage shell (#573).")
    ap.add_argument("--logiclock", action="store_true",
                     help="points.md #582: add a real per-cell LogicLock region (fixed-membership) forcing each cell's own logic to place as one contiguous block, instead of the fitter's unconstrained global optimization. Ignored with -S. Real, direct fix for the cross-die scattering Alan found in the Chip Planner on the unconstrained N=10 builds (#579-#581).")
    ap.add_argument("--ll-fixed-alm", type=float, default=None,
                     help="points.md #583: real, measured per-cell ALM figure (e.g. 1030.52 for v3 N=10, #579; 1307.42 for v4 N=10, #580) to size FIXED LogicLock regions from, instead of AUTO_SIZE -- found to reserve ~3.1x more physical area than needed (#583). Only meaningful with --logiclock.")
    ap.add_argument("--ll-headroom", type=float, default=1.25,
                     help="points.md #583: real slack multiplier over --ll-fixed-alm (default 1.25 = 25%%) -- per-cell ALM cost genuinely varies cell-to-cell, so some real headroom is needed, deliberately far less than AUTO_SIZE's own real ~3.1x.")
    ap.add_argument("--shell-file", default=None,
                     help="points.md #590: real path to a custom shell .v file (e.g. fpga/verilog/unicell_super_v7.v, #587) to array instead of a SHELL_REGISTRY entry -- must share v3/v4's own real port list. Requires --shell-module. Automatically added to the dependency list, and triggers a real, advisory compatibility check (see check_dependency_compatibility()).")
    ap.add_argument("--shell-module", default=None,
                     help="points.md #590: the real module name inside --shell-file (e.g. unicell_super_v7). Required when --shell-file is given.")
    ap.add_argument("--file-list", default=None,
                     help="points.md #590: real path to a plain text file listing dependency filenames, one real filename per line (blank lines and #-comments ignored) -- overrides SHELL_REGISTRY's own registered list entirely. Per Alan's own real request, for mixing and matching core versions without hand-writing a QSF file list each time.")
    ap.add_argument("--files", default=None,
                     help="points.md #590: real, inline comma-separated dependency list (e.g. \"compare_cell_v3.v,latch_cell_v3.v,ram_cell_v1.v,...\") -- an alternative to --file-list for a short real override. Takes precedence over --file-list if both are given.")
    args = ap.parse_args()

    if args.shell_file and not args.shell_module:
        print("error: --shell-file requires --shell-module (the real module name inside that file)", file=sys.stderr)
        sys.exit(1)

    try:
        result = assemble(args.man, args.cells, args.output, args.top, args.single_core, args.core_path, args.probe, args.shell, args.logiclock, args.ll_fixed_alm, args.ll_headroom,
                           shell_file=args.shell_file, shell_module=args.shell_module,
                           file_list=args.file_list, files_string=args.files)
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Card:   {result['card_id']} ({result['family']}, {result['device']})")
    print(f"Cells:  {result['cells']} (grid {result['rows']}x{result['cols']}, real ALM budget {result['alm_total']:,})")
    if result.get("single_core"):
        print(f"Core:   {result['single_core']} (resolved to real file: {result['resolved_file']})")
    else:
        print(f"Shell:  {result['shell']}")
        if result.get("logiclock"):
            if args.ll_fixed_alm is not None:
                print(f"LogicLock: ON -- real FIXED-size regions ({args.ll_fixed_alm:.2f} ALM/cell x {args.ll_headroom:.2f} headroom)")
            else:
                print(f"LogicLock: ON -- one real per-cell region per cell (fixed-membership, auto-sized, floating)")
        if result.get("compat_warnings"):
            print("\nCOMPATIBILITY WARNINGS (points.md #590 -- a real, advisory, heuristic scan,")
            print("NOT a substitute for a real compile; double-check, don't assume either way):")
            for w in result["compat_warnings"]:
                print(f"  - {w}")
    print(f"Output: {result['output']}")
    print(f"\nWrote {result['files_written']} real files (source + top-level RTL + .qsf + .sdc) to {result['output']}/")
    print(f"Import into Quartus using {result['top_name']}.qsf directly, matching #538's own proven flat-file template.")
    if result.get("probe_name"):
        print(f"\nReal ISSP probe included, instance name: {result['probe_name']}")
        print(f"REMINDER: generate the real issp IP in Quartus before compiling --")
        print(f"IP Catalog -> In-System Sources and Probes, probe_width=2, source_width=1,")
        print(f"no source clock (the same real configuration used throughout this project).")
        print(f"Without this step, Analysis & Synthesis will fail with 'undefined entity \"issp\"'.")
    else:
        print(f"\nNo ISSP probe included (use -P [NAME] to add one). The real LED-based")
        print(f"anti-pruning check (array_alive/heartbeat) works independently and needs")
        print(f"no extra Quartus IP generation step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
