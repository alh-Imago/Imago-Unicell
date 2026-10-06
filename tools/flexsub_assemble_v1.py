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
from its own source file before being entered, and every generated instantiation is re-checked
against the cell's real parsed module header (check_ports). Any other cell is refused with a clear
message, never guessed at. Three kinds: CHAIN (one data in, one out), SOURCE (no data input,
control-pulse driven: N independent cells), SPLIT (two outputs: one chained, one observed). The generated Verilog is only as verified as the checks in
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

# One entry per supported cell. Every port name below was read from the cell's real module header,
# and EVERY generated instantiation is re-checked against that header at assembly time
# (check_ports): a name that does not exist, or an input left unconnected, is an error -- never a
# silent guess. Fields (flex-style names; the sub family is the same minus freeze/ack/WIDTH):
#   file        (stem, variant) -> {stem}_{v4sa|v4s}{variant}.v, module name = file stem
#   families    which families have the cell (default both)
#   in_data / in_valid   the chained data input (None => a SOURCE cell: no data input, driven by
#                        control pulses, so the "array" is N independent cells)
#   out         primary (data, valid) output; ack_out/ack_in the primary handshake (flex only)
#   side        extra outputs [(data, valid, ack_in)] -- observed, not chained (router b, branch 2)
#   opt_stim_data   like stim_data, but only the ports the family's real module has
#   stim_data   further W-bit inputs driven from distinct rotations of the live LFSR (#889's
#               anti-collapse rule); stim_ctrl -- 1-bit inputs driven from distinct LFSR taps
#   consts      other ports tied to a fixed value; params -- extra module parameters
#   cfg         "zero" (cfg_data = 0) or "live" (cfg_data from the LFSR -- so config-dependent logic
#               cannot be constant-folded away, the #554 lesson); cfg_or / cfg_clr pin bits so the
#               cell stays functional (e.g. keep an output enabled)
#   max_width   hard hardware ceiling (mul_dsp: 36, #916)
#   sim_stub    the repo testbench that carries the sim-only behavioural stand-in for the Gowin
#               multiplier primitive the cell instantiates (yosys ships no functional model, #901/#902);
#               recorded in ASSEMBLY.json -- synthesis uses the primitive itself
SHAPES = {
    "adder": dict(file=("adder_cell", ""), in_data="in_a", in_valid="valid_in",
                  out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in",
                  stim_data=["in_b"], cfg="zero"),
    "compare": dict(file=("compare_cell", ""), in_data="data_in", in_valid="valid_in",
                    out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in", cfg="zero",
                    opt_stim_data=["cfg_threshold"]),      # flex only: the threshold's own W-bit port (#971)
    "mask": dict(file=("mask_cell", ""), in_data="data_in", in_valid="valid_in",
                 out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in", cfg="live"),
    "ram": dict(file=("ram_cell", ""), in_data="data_in", in_valid="valid_in",
                out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in",
                consts={"cfg_fixed_mode": "1'b0"}, cfg="live"),     # flowing mode (the chainable one)
    "shift_stage": dict(file=("shift_stage", ""), in_data="data_in", in_valid="valid_in",
                        out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in",
                        params={"SHIFT_AMT": "(i % 8)", "DIRECTION": "(i % 2)"}, cfg="zero"),
    "shift": dict(file=("shift_cell", ""), families=("sub",), in_data="data_in", in_valid="valid_in",
                  out=("data_out", "valid_out"), cfg="live"),
    "mul": dict(file=("mul_cell", ""), in_data="in_a", in_valid="valid_in",
                out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in",
                stim_data=["in_b"], cfg="zero"),
    "mul_dsp": dict(file=("mul_cell", "_dsp"), in_data="in_a", in_valid="valid_in",
                    out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in",
                    stim_data=["in_b"], cfg="zero", max_width=36,
                    sim_stub="sub/verilog/tb_mul_cell_v4sa_dsp.v"),
    "mul_dsp2": dict(file=("mul_cell", "_dsp2"), families=("sub",), in_data="in_a", in_valid="valid_in",
                     out=("data_out", "valid_out"), stim_data=["in_b"], cfg="zero",
                     sim_stub="sub/verilog/tb_mul_cell_v4s_dsp2.v"),
    "mul_dsp3": dict(file=("mul_cell", "_dsp3"), families=("sub",), in_data="in_a", in_valid="valid_in",
                     out=("data_out", "valid_out"), stim_data=["in_b"], cfg="zero",
                     sim_stub="sub/verilog/tb_mul_cell_v4s_dsp3.v"),
    "nano": dict(file=("nano_cell", ""), in_data="flow_in_data", in_valid="valid_in",
                 out=("data_out", "valid_out"), ack_out="ack_out", ack_in="ack_in",
                 stim_data=["hold_in_data"], stim_ctrl=["load_hold"], cfg="live"),
    "router": dict(file=("router_cell", ""), in_data="data_in", in_valid="valid_in",
                   out=("data_out_a", "valid_out_a"), ack_out="ack_out", ack_in="ack_in_a",
                   side=[("data_out_b", "valid_out_b", "ack_in_b")],
                   cfg="live", cfg_or=0x1),                        # keep output A enabled so the chain flows
    "branch": dict(file=("branch_cell", ""), in_data="in1_data", in_valid="in1_valid",
                   out=("data_out_1", "valid_out_1"), ack_out="ack_out", ack_in="ack_in_1",
                   side=[("data_out_2", "valid_out_2", "ack_in_2")],
                   stim_data=["in2_data", "cfg_emit_fixed_value"], consts={"in2_valid": "1'b1"},
                   cfg="live", cfg_or=0x150, cfg_clr=0x3),         # both inputs flowing; every outcome -> out1
    "accumulator": dict(file=("accumulator_cell", ""), out=("data_out", "valid_out"),
                        ack_out="ack_out", ack_in="ack_in", stim_ctrl=["inc_pulse", "dec_pulse"],
                        cfg="live", cfg_or=0x1, cfg_clr=0x100),    # non-zero step; continuous mode (pulse_mode=0)
                                                                   # -- random pulse_mode left the cell silent
    "latch": dict(file=("latch_cell", ""), out=("data_out", "valid_out"),
                  ack_out="ack_out", ack_in="ack_in", stim_ctrl=["set_in", "clear_in", "toggle_in"],
                  cfg="zero"),
    "sequencer": dict(file=("sequencer_cell", ""), out=("data_out", "valid_out"),
                      ack_out="ack_out", ack_in="ack_in", stim_ctrl=["advance_in"],
                      consts={"cfg_seq_len_m1": "2'd3"}, cfg="live"),
}

MAX_WIDTH = 64   # stimulus is {lfsr, lfsr} (64 bits); a wider cell would need a wider source
STD_PORTS = ("clk", "rst", "freeze_in", "cfg_valid", "cfg_data")


def cells_for(family):
    return sorted(k for k, v in SHAPES.items() if family in v.get("families", ("flex", "sub")))


def normalise_cell_name(name):
    """`adder`, `adder_cell`, `adder_cell_v4sa`, `mul_cell_v4sa_dsp` -> `adder` / `mul_dsp`."""
    base = re.sub(r"_v4sa?(?=_|$)", "", name.strip())
    base = re.sub(r"_cell(?=_|$)", "", base)
    return base


def cell_module(base, family):
    stem, variant = SHAPES[base]["file"]
    return f"{stem}_{FAMILIES[family]['suffix']}{variant}"


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
        # resource data the assembler READS (Alan #941/#942: "the dsp type and availability and other resources have to be held in the man file ...
        # but used by the assembler"). Nothing here is assumed about a vendor.
        "synth_nowidelut_supported": ((man.get("synthesis") or {}).get("nowidelut") or {}).get("supported"),
        "synth_nowidelut_default": ((man.get("synthesis") or {}).get("nowidelut") or {}).get("default"),
        "dsp_blocks": (device.get("dsp") or {}).get("total_blocks"),
        "dsp_primitives": {pr["name"]: pr for pr in ((device.get("dsp") or {}).get("primitives") or [])},
        "dsp_abilities": list((device.get("dsp") or {}).get("abilities") or []),
        "logic_unit": logic.get("unit") or ("ALM" if device.get("alm_total") is not None else None),
        "logic_total": (logic.get("lut4_total") if logic.get("unit") == "LUT4"
                        else device.get("alm_total") if (device.get("alm_total") is not None and not logic.get("unit")) else None),
    }


def resolve_width(family, width_arg, man, max_width=MAX_WIDTH):
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
    if width > max_width:
        raise ValueError(f"width {width} exceeds this cell's hardware ceiling of {max_width}")
    return width, source


def real_ports(path, module):
    """(input names, output names, parameter names) parsed from the cell's own module header."""
    text = open(path).read()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    m = re.search(rf"\bmodule\s+{re.escape(module)}\b(.*?)\)\s*;", text, re.S)
    if not m:
        raise ValueError(f"module {module} not found in {path}")
    header = m.group(1)
    ins, outs = set(), set()
    for d, name in re.findall(r"\b(input|output|inout)\b\s+(?:wire\s+|reg\s+)?(?:signed\s+)?(?:\[[^\]]*\]\s*)?(\w+)", header):
        (ins if d == "input" else outs).add(name)
    params = set(re.findall(r"\bparameter\b\s*(?:\[[^\]]*\]\s*)?(\w+)\s*=", header))
    return ins, outs, params


def _stim_ports(sh, real_in):
    """The W-bit stimulus ports of a shape: the always-present `stim_data`, plus the `opt_stim_data` ports that THIS family's real module actually has (e.g. the flex comparator's cfg_threshold, ledger
    #971; the sub comparator has none)."""
    return list(sh.get("stim_data", [])) + [p for p in sh.get("opt_stim_data", []) if p in real_in]


def _connections(family, base, real_in):
    """Ordered [(port, expression)] for one instance. Standard ports are included only when the
    real module has them."""
    sh = SHAPES[base]
    ack = FAMILIES[family]["has_width"]
    c = []
    for p in STD_PORTS:
        if p not in real_in:
            continue
        c.append((p, {"clk": "BOARD_CLK", "rst": "rst", "freeze_in": "1'b0", "cfg_valid": "cfg_valid",
                      "cfg_data": "cfg_i" if sh.get("cfg") == "live" else "32'h0"}[p]))
    if sh.get("in_data"):
        c.append((sh["in_data"], "stage_data[i]"))
    for p in _stim_ports(sh, real_in):
        c.append((p, f"stim_{p}"))
    for k, p in enumerate(sh.get("stim_ctrl", [])):
        c.append((p, f"lfsr[(i * 3 + {k * 7 + 1}) % 32]"))
    if sh.get("in_valid"):
        c.append((sh["in_valid"], "stage_valid[i]"))
    for p, v in sh.get("consts", {}).items():
        c.append((p, v))
    if ack and sh.get("ack_out"):
        c.append((sh["ack_out"], "stage_ack[i]"))
    c.append((sh["out"][0], "stage_data[i+1]"))
    c.append((sh["out"][1], "stage_valid[i+1]"))
    if ack and sh.get("ack_in"):
        c.append((sh["ack_in"], "stage_ack[i+1]" if sh.get("in_data") else "consumer_ack"))
    for k, (d, v, a) in enumerate(sh.get("side", [])):
        c.append((d, f"side{k}_data[i]"))
        c.append((v, f"side{k}_valid[i]"))
        if ack:
            c.append((a, "consumer_ack"))
    return c


def check_ports(base, family, path, module, real=None):
    """Every connected name must exist in the real module, and every real input must be connected."""
    ins, outs, params = real or real_ports(path, module)
    conn = _connections(family, base, ins)
    names = {p for p, _ in conn}
    sh = SHAPES[base]
    bad = sorted(names - ins - outs)
    missing = sorted(ins - names)
    badparams = sorted(set(sh.get("params", {})) - params)
    problems = []
    if bad:
        problems.append(f"connects ports the cell does not have: {bad}")
    if missing:
        problems.append(f"leaves real input ports unconnected: {missing}")
    if badparams:
        problems.append(f"sets parameters the cell does not have: {badparams}")
    if problems:
        raise ValueError(f"{module}: shape table disagrees with the real module header -- " + "; ".join(problems))


def generate_top(top_name, family, base, n, width, real_in):
    sh = SHAPES[base]
    info = FAMILIES[family]
    module = cell_module(base, family)
    has_ack = info["has_width"]
    chain = bool(sh.get("in_data"))
    sides = sh.get("side", [])
    L = []
    a = L.append
    a(f"// {top_name}.v -- GENERATED by tools/flexsub_assemble_v1.py (-s {family}); do not hand-edit,")
    a(f"// regenerate from the same command instead. {n}-{'stage chain' if chain else 'cell array'} of {module}, WIDTH={width}.")
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
    if chain:
        a("assign stage_data[0]  = lfsr2[W-1:0];")
        a("assign stage_valid[0] = 1'b1;")
    else:
        a("assign stage_data[0]  = {W{1'b0}};   // source cells: no data input")
        a("assign stage_valid[0] = 1'b0;")
    if has_ack:
        a("assign stage_ack[N]   = consumer_ack;")
    for k, _ in enumerate(sides):
        a(f"wire [W-1:0] side{k}_data  [0:N-1];")
        a(f"wire         side{k}_valid [0:N-1];")
    a("")
    a("genvar i;")
    a("generate")
    a("    for (i = 0; i < N; i = i + 1) begin : STAGE")
    for k, p in enumerate(_stim_ports(sh, real_in)):
        sh_expr = f"(i + {k * 7}) % 32" if k else "i % 32"
        a(f"        wire [63:0]    rot_{p}  = (lfsr2 >> ({sh_expr}));")
        a(f"        wire [W-1:0]   stim_{p} = rot_{p}[W-1:0];")
    if sh.get("cfg") == "live" and "cfg_data" in real_in:
        a("        wire [63:0]    rot_cfg = (lfsr2 >> ((i + 11) % 32));")
        or_, clr = sh.get("cfg_or", 0), sh.get("cfg_clr", 0)
        a(f"        wire [31:0]    cfg_i   = (rot_cfg[31:0] | 32'h{or_:08X}) & ~32'h{clr:08X};")
    params = [".CELL_ID(i[15:0])"] + ([".WIDTH(W)"] if info["has_width"] else [])
    params += [f".{k}({v})" for k, v in sh.get("params", {}).items()]
    a(f"        {module} #({', '.join(params)}) U (")
    pl = _connections(family, base, real_in)
    for k, (port, expr) in enumerate(pl):
        a(f"            .{port}({expr}){',' if k < len(pl) - 1 else ''}")
    a("        );")
    a("    end")
    a("endgenerate")
    a("")
    need_red = (not chain) or bool(sides)
    if need_red:
        a("// observability reductions: every output of every cell reaches a pin")
        a("wire [W-1:0] xr_data  [0:N];")
        a("wire         or_valid [0:N];")
        a("wire         xr_ack   [0:N];")
        a("wire [W-1:0] sx_data  [0:N];")
        a("wire         sx_valid [0:N];")
        a("assign xr_data[0] = {W{1'b0}}; assign or_valid[0] = 1'b0; assign xr_ack[0] = 1'b0;")
        a("assign sx_data[0] = {W{1'b0}}; assign sx_valid[0] = 1'b0;")
        a("genvar j;")
        a("generate")
        a("    for (j = 0; j < N; j = j + 1) begin : RED")
        a("        assign xr_data[j+1]  = xr_data[j]  ^ stage_data[j+1];")
        a("        assign or_valid[j+1] = or_valid[j] | stage_valid[j+1];")
        a("        assign xr_ack[j+1]   = xr_ack[j]   ^ " + ("stage_ack[j];" if has_ack else "1'b0;"))
        sx_d = " ^ ".join(f"side{k}_data[j]" for k in range(len(sides))) or "{W{1'b0}}"
        sx_v = " | ".join(f"side{k}_valid[j]" for k in range(len(sides))) or "1'b0"
        a(f"        assign sx_data[j+1]  = sx_data[j]  ^ ({sx_d});")
        a(f"        assign sx_valid[j+1] = sx_valid[j] | ({sx_v});")
        a("    end")
        a("endgenerate")
    if chain:
        a("assign LED0_N = ~stage_valid[N];")
        base_led1 = "stage_ack[0]" if has_ack else "stage_valid[N >> 1]"
        if sides:
            a(f"assign LED1_N = ~({base_led1} ^ sx_valid[N] ^ (^sx_data[N]));")
        else:
            a(f"assign LED1_N = ~{base_led1};")
        if sides:
            a("assign LED2_N = ~((^stage_data[N]) ^ (^sx_data[N]));   // full-width reduction, #902/#908's lesson")
        else:
            a("assign LED2_N = ~(^stage_data[N]);   // full-width reduction, #902/#908's lesson")
    else:
        a("assign LED0_N = ~or_valid[N];")
        a("assign LED1_N = ~" + ("xr_ack[N];" if has_ack else "stage_valid[1];"))
        a("assign LED2_N = ~(^xr_data[N]);   // full-width reduction over every cell, #902/#908's lesson")
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


def resolve_nowidelut(request, man):
    """Should the generated `synth_gowin` script carry `-nowidelut`? (Alan, after ledger #950: it becomes the DEFAULT for the Gowin generators, but not where the card's
    toolchain does not offer it -- the Arria 10 path has no such option.) The card's own MAN says what its toolchain supports and what the default is
    (`synthesis.nowidelut.{supported,default}`); nothing about a vendor is assumed here.
      request True  (--nowidelut) : force it on; REFUSED if the MAN says the toolchain does not support it
      request False (--wide-lut)  : opt out (the historical default flow)
      request None                : the MAN's default if it states one; otherwise ON (these generators emit `synth_gowin`, which has the option)
    Returns (flag, reason)."""
    sup = man.get("synth_nowidelut_supported") if man else None
    dfl = man.get("synth_nowidelut_default") if man else None
    if request is True:
        if sup is False:
            raise ValueError("--nowidelut: this card's MAN says its synthesis toolchain does not support the option (synthesis.nowidelut.supported = false) -- "
                             "it would be silently ignored, so it is refused")
        return True, "requested (--nowidelut)"
    if request is False:
        return False, "opted out (--wide-lut): the historical default flow"
    if man is not None and sup is not None:
        on = bool(sup and dfl)
        return on, f"the card's MAN says: supported={sup}, default={dfl}"
    return True, "the default for the Gowin generators (no MAN, or a MAN with no synthesis block)"


def assemble_flexsub(family, cell, n, output, man_path=None, width_arg=None, top=None, cell_dir=None, nowidelut=None):
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; real options: {', '.join(FAMILIES)}")
    if cell is None:
        raise ValueError(f"-s {family} needs a core type via -S (supported: {', '.join(cells_for(family))})")
    base = normalise_cell_name(cell)
    if base not in SHAPES:
        raise ValueError(f"cell {cell!r} is not supported yet by -s {family}; supported: "
                         f"{', '.join(cells_for(family))}. (Each cell's port shape must be read from its "
                         f"own source and entered in SHAPES first -- never guessed.)")
    if family not in SHAPES[base].get("families", ("flex", "sub")):
        have = "/".join(SHAPES[base].get("families", ("flex", "sub")))
        raise ValueError(f"cell {base!r} does not exist in the {family} family (only in: {have}); "
                         f"{family} cells: {', '.join(cells_for(family))}")
    if n < 1:
        raise ValueError("--cells must be at least 1")
    cell_dir = cell_dir or DEFAULT_CELL_DIR
    man = load_man_flexsub(man_path) if man_path else None
    nowidelut, nowidelut_why = resolve_nowidelut(nowidelut, man)
    width, width_source = resolve_width(family, width_arg, man, SHAPES[base].get('max_width', MAX_WIDTH))

    suffix = FAMILIES[family]["suffix"]
    module = cell_module(base, family)
    cell_file = f"{module}.v"
    if not os.path.isfile(os.path.join(cell_dir, cell_file)):
        raise FileNotFoundError(f"no {cell_file} in {cell_dir}")
    real = real_ports(os.path.join(cell_dir, cell_file), module)
    check_ports(base, family, os.path.join(cell_dir, cell_file), module, real)

    top_name = top or f"flexsub_{base}_{suffix}_n{n}_w{width}"
    os.makedirs(output, exist_ok=True)
    top_path = os.path.join(output, f"{top_name}.v")
    with open(top_path, "w") as f:
        f.write(generate_top(top_name, family, base, n, width, real[0]))

    dep_pairs = _derive_deps(top_path, cell_dir)
    deps = [f for f, _ in dep_pairs]
    if cell_file not in deps:
        raise RuntimeError(f"dependency derivation did not find {cell_file} -- generated top is wrong")
    import shutil
    for fname, src in dep_pairs:
        shutil.copy2(os.path.join(src, fname), os.path.join(output, fname))

    files = [f"{top_name}.v"] + deps
    ys = [f"read_verilog -sv {' '.join(files)}", f"hierarchy -top {top_name}",
          f"synth_gowin -top {top_name}{' -nowidelut' if nowidelut else ''} -json {top_name}.json", "stat"]
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
              "cell_module": module, "cells": n, "width": width,
              "width_source": width_source, "man": man["card_id"] if man else None,
              "top": top_name, "files": files + (["build.sh"]), "pnr": have_cst,
              "synth_flags": "-nowidelut" if nowidelut else "(wide-LUT mapping)", "synth_flags_reason": nowidelut_why}
    if SHAPES[base].get("sim_stub"):
        record["sim_note"] = ("this cell instantiates a Gowin multiplier primitive; simulation needs a behavioural "
                              f"stand-in (yosys ships none) -- see the stub in {SHAPES[base]['sim_stub']}. "
                              "Synthesis uses the primitive directly.")
    with open(os.path.join(output, "ASSEMBLY.json"), "w") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    return record
