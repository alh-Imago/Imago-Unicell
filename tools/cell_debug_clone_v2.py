#!/usr/bin/env python3
"""cell_debug_clone_v2.py -- ledger #1250. Clones the DEBUG cells of #1247 (adder_cell_v4f, ram_cell_v4d and their shells) into LOAD-CAPABLE debug cells:

  adder_cell_v4f -> adder_cell_v4g      adder_shell_v1f -> adder_shell_v1g
  ram_cell_v4d   -> ram_cell_v4g        ram_shell_v1d   -> ram_shell_v1g

Two added inputs, dbg_load_en and dbg_load_state[127:0] (the SAME layout as the dbg_state output, see cell_debug_clone_v1.py). While dbg_load_en is 1 at a clock edge
(and rst is 0) the cell's registers are overwritten with the fields of dbg_load_state; nothing else changes, and with dbg_load_en = 0 the behaviour is that of v4f / v4d.
The load branch sits ahead of cfg_valid in the register block: reset wins over load, load wins over everything else.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VDIR = os.path.join(ROOT, "fpga", "verilog")

ADDER_LOAD = """        end else if (dbg_load_en) begin       // ledger #1250: overwrite every register from dbg_load_state (layout = dbg_state)
            a_reg           <= dbg_load_state[31:0];
            out_buffer      <= dbg_load_state[63:32];
            downstream_mask <= dbg_load_state[69:64];
            upstream_mask   <= dbg_load_state[75:70];
            second_downstream_mask <= dbg_load_state[81:76];
            pending_ack     <= dbg_load_state[85:82];
            a_arrived       <= dbg_load_state[96];
            data_valid      <= dbg_load_state[97];
            subtract_mode   <= dbg_load_state[98];
            join_mode       <= dbg_load_state[99];
            second_output   <= dbg_load_state[100];
            captured_carry  <= dbg_load_state[101];
            delivering_carry <= dbg_load_state[102];
            phase1_offered  <= dbg_load_state[103];
            armed           <= dbg_load_state[104];
            program_done_r  <= dbg_load_state[105];
"""
RAM_LOAD = """        end else if (dbg_load_en) begin       // ledger #1250: overwrite every register from dbg_load_state (layout = dbg_state)
            data_reg        <= dbg_load_state[31:0];
            init_data       <= dbg_load_state[63:32];
            addon_config    <= dbg_load_state[83:64];
            downstream_mask <= dbg_load_state[101:96];
            upstream_mask   <= dbg_load_state[107:102];
            pending_ack     <= dbg_load_state[111:108];
            data_valid      <= dbg_load_state[112];
            fixed_mode      <= dbg_load_state[113];
            armed           <= dbg_load_state[114];
            program_done_r  <= dbg_load_state[115];
"""
PORTS_OLD = "    output wire [127:0] dbg_state\n);"
PORTS_NEW = "    output wire [127:0] dbg_state,\n    input  wire         dbg_load_en,\n    input  wire [127:0] dbg_load_state\n);"


def sub1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def clone(name_old, name_new, edits, note):
    out = open(os.path.join(VDIR, name_old + ".v")).read()
    for old, new in edits:
        out = sub1(out, old, new)
    out = sub1(out, "`default_nettype none", "// ledger #1250: LOAD-CAPABLE DEBUG CLONE of %s -- %s Identical in behaviour while dbg_load_en = 0.\n`default_nettype none" % (name_old, note))
    path = os.path.join(VDIR, name_new + ".v")
    open(path, "w").write(out)
    d = subprocess.run(["diff", os.path.join(VDIR, name_old + ".v"), path], capture_output=True, text=True).stdout.splitlines()
    print("%-16s -> %-16s  lines added %d, removed/changed %d" % (name_old, name_new, sum(l.startswith("> ") for l in d), sum(l.startswith("< ") for l in d)))


def main():
    clone("adder_cell_v4f", "adder_cell_v4g", [
        ("module adder_cell_v4f #(", "module adder_cell_v4g #("),
        (PORTS_OLD, PORTS_NEW),
        ("        end else if (cfg_valid) begin\n", ADDER_LOAD + "        end else if (cfg_valid) begin\n"),
    ], "adds the load inputs.")
    clone("adder_shell_v1f", "adder_shell_v1g", [
        ("module adder_shell_v1f #(", "module adder_shell_v1g #("),
        (PORTS_OLD, PORTS_NEW),
        ("    adder_cell_v4f #(.CELL_ID(CELL_ID)) CORE (", "    adder_cell_v4g #(.CELL_ID(CELL_ID)) CORE ("),
        (".dbg_state(dbg_state)\n", ".dbg_state(dbg_state),\n        .dbg_load_en(dbg_load_en), .dbg_load_state(dbg_load_state)\n"),
    ], "wraps adder_cell_v4g.")
    clone("ram_cell_v4d", "ram_cell_v4g", [
        ("module ram_cell_v4d #(", "module ram_cell_v4g #("),
        (PORTS_OLD, PORTS_NEW),
        ("        end else if (cfg_valid) begin\n", RAM_LOAD + "        end else if (cfg_valid) begin\n"),
    ], "adds the load inputs.")
    clone("ram_shell_v1d", "ram_shell_v1g", [
        ("module ram_shell_v1d #(", "module ram_shell_v1g #("),
        (PORTS_OLD, PORTS_NEW),
        ("    ram_cell_v4d #(.CELL_ID(CELL_ID)) CORE (", "    ram_cell_v4g #(.CELL_ID(CELL_ID)) CORE ("),
        (".dbg_state(dbg_state)\n", ".dbg_state(dbg_state),\n        .dbg_load_en(dbg_load_en), .dbg_load_state(dbg_load_state)\n"),
    ], "wraps ram_cell_v4g.")


if __name__ == "__main__":
    main()
