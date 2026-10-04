#!/usr/bin/env python3
"""
flexsub_assemble_v1.py -- STEP 1 of the two-step Flex-Sub assembler plan (Alan, 2026-10-04,
following points.md #903-#905/#914/#919): the assembler can now be told to build from the
stripped cell families in sub/verilog/ instead of the carrier/shell lineage.

Reached through tools/project_assemble_v1.py's own `-s/--family` flag. That file is untouched
apart from the flag plumbing + one dispatch line; with the flag absent (or `-s nano`) every
existing mode runs exactly as before (verified byte-for-byte against pre-change output).

  -s flex   the Flex-Sub family (`*_cell_v4sa.v`): WIDTH-parameterised, ack+freeze handshake.
            WIDTH comes from  -w N  if given, else the MAN file's `device.logic.native_width`
            (#914's contract), else -- only when a MAN exists but lacks the field -- 32, the
            Verilog default (#914: "fall back to 32 only when the target's MAN file has no such
            field"). With NO MAN and no -w there is nothing to read, so this is an error.
  -s sub    the fixed-32 family (`*_cell_v4s.v`): no WIDTH parameter, no ack. -w is rejected.
  -s nano   explicit name for the existing/default behaviour (carrier/shell lineage); handled
            entirely by project_assemble_v1.py, never reaches this module.

The core type is chosen with the existing  -S/--single-core  flag (e.g. `-s flex -S adder`), the
count with --cells, the card with --man (optional here -- see above).

WHAT STEP 1 BUILDS: an N-cell CHAIN of one cell type with a pin-bound top (LFSR stimulus,
full-width XOR observability -- the same anti-pruning discipline as sub/verilog/
adder_chain_v4sa_top100_width18.v and tools/gowin_sizing/), written to --output as a flat,
self-contained folder: top .v, every dependency copied from the cell source dir, a yosys
`synth_gowin` script, build.sh, an ASSEMBLY.json record, and -- when a Gowin MAN is given -- a
real .cst built from that MAN's own pin table. STEP 2 (reading an ICM-VIX file's design_map as
the netlist instead of generating a uniform chain) is NOT in this file.

HONEST SCOPE: only the cells in SHAPES below are supported -- each one's real port list was read
from its own source file before being entered. Any other cell is refused with a clear message,
never guessed at. The generated Verilog is only as verified as the checks in
tests/test_flexsub_assemble_v1.py (compile + synthesis); nothing here has run on silicon.
"""
import json
import os
import re
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TOOLS_DIR)
DEFAULT_CELL_DIR = os.path.join(REPO_ROOT, "sub", "verilog")

FAMILIES = {
    "flex": {"suffix": "v4sa", "has_width": True},
    "sub": {"suffix": "v4s", "has_width": False},
}

# Port roles per supported cell, read from each cell's real module header (not from docs):
#   chain_in -- the port the previous stage's data_out feeds
#   stim     -- further data inputs, driven from rotated slices of the live LFSR (distinct per
#               stage, so no two ports are provably related -- #889's anti-collapse rule)
SHAPES = {
    "adder": {"chain_in": "in_a", "stim": ["in_b"]},
    "compare": {"chain_in": "data_in", "stim": []},
}

MAX_WIDTH = 64   # stimulus is {lfsr, lfsr} (64 bits); a wider cell would need a wider source


def normalise_cell_name(name):
    """`adder`, `adder_cell`, `adder_cell_v4sa` -> `adder`."""
    base = name.strip()
    base = re.sub(r"_v4sa?$", "", base)
    base = re.sub(r"_cell$", "", base)
    return base


def load_man_flexsub(path):
    """Vendor-neutral reader for exactly what this module needs. Deliberately NOT
    project_assemble_v1.load_man(), which refuses non-Intel MAN files by design (#887)."""
    with open(path) as f:
        man = json.load(f)
    device = man["device"]
    logic = device.get("logic", {})
    return {
        "card_id": man["card_id"],
        "vendor": man.get("vendor", "intel"),
        "part": device["part"],
        "pnr_family": (device.get("apicula") or {}).get("family"),
        "native_width": logic.get("native_width"),
        "board": man.get("board", {}),
    }


def resolve_width(family, width_arg, man):
    """Returns (width, source). Raises ValueError with a clear message on a bad combination."""
    info = FAMILIES[family]
    if not info["has_width"]:
        if width_arg is not None:
            raise ValueError(
                f"-w/--width is not valid with -s {family}: the {info['suffix']} cells have no WIDTH "
                f"parameter (fixed 32 bits). Use -s flex for a width-parameterised build.")
        return 32, f"fixed (-s {family} cells are 32-bit)"
    if width_arg is not None:
        width, source = width_arg, "-w"
    elif man is not None and man.get("native_width") is not None:
        width, source = int(man["native_width"]), f"MAN {man['card_id']} device.logic.native_width"
    elif man is not None:
        width, source = 32, (f"fallback to the Verilog default (MAN {man['card_id']} records no "
                             f"native_width, #914)")
    else:
        raise ValueError("-s flex needs either --man (its native_width sets WIDTH) or -w N "
                         "(e.g. -w 18) -- there is nothing else to take a width from.")
    if not (1 <= width <= MAX_WIDTH):
        raise ValueError(f"width {width} out of range 1..{MAX_WIDTH}")
    return width, source


def _port_lines(family, base):
    shape = SHAPES[base]
    ports = [".clk(BOARD_CLK)", ".rst(rst)"]
    if FAMILIES[family]["has_width"]:
        ports.append(".freeze_in(1'b0)")
    ports += [".cfg_valid(cfg_valid)", ".cfg_data(32'h0)"]
    ports.append(f".{shape['chain_in']}(stage_data[i])")
    for p in shape["stim"]:
        ports.append(f".{p}(stim_{p})")
    ports.append(".valid_in(stage_valid[i])")
    if FAMILIES[family]["has_width"]:
        ports.append(".ack_out(stage_ack[i])")
    ports += [".data_out(stage_data[i+1])", ".valid_out(stage_valid[i+1])"]
    if FAMILIES[family]["has_width"]:
        ports.append(".ack_in(stage_ack[i+1])")
    return ports


def generate_top(top_name, family, base, n, width):
    info = FAMILIES[family]
    module = f"{base}_cell_{info['suffix']}"
    has_ack = info["has_width"]
    L = []
    a = L.append
    a(f"// {top_name}.v -- GENERATED by tools/flexsub_assemble_v1.py (-s {family}); do not hand-edit,")
    a(f"// regenerate from the same command instead. {n}-stage chain of {module}, WIDTH={width}.")
    a("// Anti-pruning: live LFSR stimulus, full-width XOR observability (#902/#908/#889).")
    a("`default_nettype none")
    a("`timescale 1ns / 1ps")
    a("")
    a(f"module {top_name} (")
    a("    input  wire BOARD_CLK,")
    a("    input  wire BTN_RST_N,")
    a("    input  wire BTN_ENTRY,")
    a("    output wire LED0_N,")
    a("    output wire LED1_N,")
    a("    output wire LED2_N")
    a(");")
    a(f"localparam W = {width};")
    a(f"localparam N = {n};")
    a("reg [3:0] rst_sr = 4'hF;")
    a("always @(posedge BOARD_CLK) rst_sr <= {rst_sr[2:0], ~BTN_RST_N};")
    a("wire rst = rst_sr[3] | ~BTN_RST_N;")
    a("")
    a("reg [3:0] cfg_sr = 4'hF;")
    a("always @(posedge BOARD_CLK) if (!rst) cfg_sr <= {cfg_sr[2:0], 1'b0};")
    a("wire cfg_valid = !rst && cfg_sr[3] && !cfg_sr[2];")
    a("")
    a("reg [31:0] lfsr = 32'hACE1_1234;")
    a("always @(posedge BOARD_CLK) lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]^BTN_ENTRY};")
    a("wire [63:0] lfsr2 = {lfsr, lfsr};")
    if has_ack:
        a("")
        a("reg [4:0] tick_cnt = 0;")
        a("always @(posedge BOARD_CLK) tick_cnt <= tick_cnt + 5'd1;")
        a("wire consumer_ack = (tick_cnt == 5'h1F);")
    a("")
    a("wire [W-1:0] stage_data  [0:N];")
    a("wire         stage_valid [0:N];")
    if has_ack:
        a("wire         stage_ack   [0:N];")
    a("assign stage_data[0]  = lfsr2[W-1:0];")
    a("assign stage_valid[0] = 1'b1;")
    if has_ack:
        a("assign stage_ack[N]   = consumer_ack;")
    a("")
    a("genvar i;")
    a("generate")
    a("    for (i = 0; i < N; i = i + 1) begin : STAGE")
    for p in SHAPES[base]["stim"]:
        a(f"        wire [63:0]    rot_{p}  = (lfsr2 >> (i % 32));")
        a(f"        wire [W-1:0]   stim_{p} = rot_{p}[W-1:0];")
    params = ".CELL_ID(i[15:0])" + (", .WIDTH(W)" if info["has_width"] else "")
    a(f"        {module} #({params}) U (")
    pl = _port_lines(family, base)
    for k, line in enumerate(pl):
        a(f"            {line}{',' if k < len(pl) - 1 else ''}")
    a("        );")
    a("    end")
    a("endgenerate")
    a("")
    a("assign LED0_N = ~stage_valid[N];")
    if has_ack:
        a("assign LED1_N = ~stage_ack[0];")
    else:
        a("assign LED1_N = ~stage_valid[N >> 1];")
    a("assign LED2_N = ~(^stage_data[N]);   // full-width reduction, #902/#908's lesson")
    a("endmodule")
    return "\n".join(L) + "\n"


def generate_cst(man):
    """A real .cst from the MAN's own board table. Same five/six pins and reset pull-up as the
    proven sub/verilog hand-built tops; only emitted for a Gowin MAN with the pins present."""
    board = man["board"]
    try:
        clk = board["clock"]["CLK_27M"]["pin"]
        rst = board["buttons"]["S1"]["pin"]
        entry = board["buttons"]["S2"]["pin"]
        leds = [board["leds"][f"LED{i}_N"] for i in range(3)]
    except KeyError as e:
        raise ValueError(f"MAN {man['card_id']} board table is missing {e} -- cannot build a .cst") from e
    L = [f'IO_LOC "BOARD_CLK" {clk};', 'IO_PORT "BOARD_CLK" IO_TYPE=LVCMOS33;',
         f'IO_LOC "BTN_RST_N" {rst};', 'IO_PORT "BTN_RST_N" IO_TYPE=LVCMOS33 PULL_MODE=UP;',
         f'IO_LOC "BTN_ENTRY" {entry};', 'IO_PORT "BTN_ENTRY" IO_TYPE=LVCMOS33;']
    for i, pin in enumerate(leds):
        L += [f'IO_LOC "LED{i}_N" {pin};', f'IO_PORT "LED{i}_N" IO_TYPE=LVCMOS33 DRIVE=8;']
    return "\n".join(L) + "\n"


def _derive_deps(top_path, cell_dir):
    """Transitive dependency walk over the real sources, reusing project_assemble_v1's own regex
    machinery (discover_instantiated_modules / build_module_index). The cell dir is searched FIRST,
    then fpga/verilog: the Flex-Sub cells still instantiate shared primitives that live there
    (adder_v1.v, found the hard way -- the first generated folder failed to elaborate without it).
    Returns [(filename, source_dir), ...], top excluded. A module found in neither dir is skipped
    (the heuristic's known false-positive case) -- the iverilog compile in the test suite is what
    actually proves the folder is complete."""
    sys.path.insert(0, TOOLS_DIR)
    import project_assemble_v1 as pa
    search_dirs = [cell_dir]
    shared = os.path.join(REPO_ROOT, "fpga", "verilog")
    if os.path.isdir(shared) and os.path.abspath(shared) != os.path.abspath(cell_dir):
        search_dirs.append(shared)
    index = {}   # module name -> (filename, dir); earlier dirs win
    for d in search_dirs:
        for mod, fname in pa.build_module_index(d).items():
            index.setdefault(mod, (fname, d))
    found, to_scan = {}, [top_path]
    while to_scan:
        current = to_scan.pop()
        for mod in pa.discover_instantiated_modules(current):
            hit = index.get(mod)
            if hit is None or hit[0] in found:
                continue
            found[hit[0]] = hit[1]
            to_scan.append(os.path.join(hit[1], hit[0]))
    return sorted(found.items())


def assemble_flexsub(family, cell, n, output, man_path=None, width_arg=None, top=None, cell_dir=None):
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; real options: {', '.join(FAMILIES)}")
    if cell is None:
        raise ValueError(f"-s {family} needs a core type via -S (supported: {', '.join(sorted(SHAPES))})")
    base = normalise_cell_name(cell)
    if base not in SHAPES:
        raise ValueError(f"cell {cell!r} is not supported yet by -s {family}; supported: "
                         f"{', '.join(sorted(SHAPES))}. (Each cell's port shape must be read from its "
                         f"own source and entered in SHAPES first -- never guessed.)")
    if n < 1:
        raise ValueError("--cells must be at least 1")
    cell_dir = cell_dir or DEFAULT_CELL_DIR
    man = load_man_flexsub(man_path) if man_path else None
    width, width_source = resolve_width(family, width_arg, man)

    suffix = FAMILIES[family]["suffix"]
    cell_file = f"{base}_cell_{suffix}.v"
    if not os.path.isfile(os.path.join(cell_dir, cell_file)):
        raise FileNotFoundError(f"no {cell_file} in {cell_dir}")

    top_name = top or f"flexsub_{base}_{suffix}_n{n}_w{width}"
    os.makedirs(output, exist_ok=True)
    top_path = os.path.join(output, f"{top_name}.v")
    with open(top_path, "w") as f:
        f.write(generate_top(top_name, family, base, n, width))

    dep_pairs = _derive_deps(top_path, cell_dir)
    deps = [f for f, _ in dep_pairs]
    if cell_file not in deps:
        raise RuntimeError(f"dependency derivation did not find {cell_file} -- generated top is wrong")
    import shutil
    for fname, src in dep_pairs:
        shutil.copy2(os.path.join(src, fname), os.path.join(output, fname))

    files = [f"{top_name}.v"] + deps
    ys = [f"read_verilog -sv {' '.join(files)}", f"hierarchy -top {top_name}",
          f"synth_gowin -top {top_name} -json {top_name}.json", "stat"]
    with open(os.path.join(output, f"{top_name}.ys"), "w") as f:
        f.write("\n".join(ys) + "\n")

    have_cst = bool(man and man["vendor"] == "gowin")
    sh = ["#!/bin/bash", f"# GENERATED by tools/flexsub_assemble_v1.py -- {top_name}",
          "set -euo pipefail", 'cd "$(dirname "$0")"', f"yosys -s {top_name}.ys"]
    if have_cst:
        with open(os.path.join(output, f"{top_name}.cst"), "w") as f:
            f.write(generate_cst(man))
        sh += [f"yowasp-nextpnr-himbaechel-gowin --device \"{man['part']}\" "
               f"--vopt family={man['pnr_family']} --vopt cst={top_name}.cst "
               f"--json {top_name}.json --write {top_name}_routed.json "
               f"--report {top_name}_report.json --freq 27 --timing-allow-fail"]
    else:
        sh.append("# no Gowin MAN given -> synthesis only (no pin constraints, no place-and-route)")
    with open(os.path.join(output, "build.sh"), "w") as f:
        f.write("\n".join(sh) + "\n")
    os.chmod(os.path.join(output, "build.sh"), 0o755)

    record = {"generator": "tools/flexsub_assemble_v1.py", "family": family, "cell": base,
              "cell_module": f"{base}_cell_{suffix}", "cells": n, "width": width,
              "width_source": width_source, "man": man["card_id"] if man else None,
              "top": top_name, "files": files + (["build.sh"]), "pnr": have_cst}
    with open(os.path.join(output, "ASSEMBLY.json"), "w") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return record
