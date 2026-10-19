#!/usr/bin/env python3
"""cell_debug_clone_v1.py -- ledger #1247. Clones four PROVEN cell files into debug versions that bring out the cell's hidden registers on one extra output
port, `dbg_state[127:0]` (four 32-bit words). Nothing else changes: the original files are not touched (rule: clone and increment the version),
and the clones' only differences are the added port, its connection in the shell, and one `assign` (check with diff; the script prints the diff size).

  adder_cell_v4e  -> adder_cell_v4f      adder_shell_v1e -> adder_shell_v1f
  ram_cell_v4     -> ram_cell_v4d        ram_shell_v1    -> ram_shell_v1d

dbg_state, ADDER (word 0 is the lowest 32 bits):
  w0 a_reg (the waiting first operand)   w1 out_buffer
  w2 [5:0] downstream_mask  [11:6] upstream_mask  [17:12] second_downstream_mask  [21:18] pending_ack
  w3 bit0 a_arrived 1 data_valid 2 subtract_mode 3 join_mode 4 second_output 5 captured_carry 6 delivering_carry 7 phase1_offered 8 armed 9 program_done_r
dbg_state, RAM:
  w0 data_reg (the stored word)   w1 init_data   w2 [19:0] addon_config
  w3 [5:0] downstream_mask  [11:6] upstream_mask  [15:12] pending_ack  bit16 data_valid 17 fixed_mode 18 armed 19 program_done_r
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VDIR = os.path.join(ROOT, "fpga", "verilog")

ADDER_ASSIGN = ("    // ledger #1247: debug view of the hidden registers (see tools/cell_debug_clone_v1.py for the layout)\n"
                "    assign dbg_state = { {22'b0, program_done_r, armed, phase1_offered, delivering_carry, captured_carry, second_output, join_mode, subtract_mode, data_valid, a_arrived},\n"
                "                         {10'b0, pending_ack, second_downstream_mask, upstream_mask, downstream_mask},\n"
                "                         out_buffer, a_reg };\n")
RAM_ASSIGN = ("    // ledger #1247: debug view of the hidden registers (see tools/cell_debug_clone_v1.py for the layout)\n"
              "    assign dbg_state = { {12'b0, program_done_r, armed, fixed_mode, data_valid, pending_ack, upstream_mask, downstream_mask},\n"
              "                         {12'b0, addon_config}, init_data, data_reg };\n")


def sub1(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


def clone(name_old, name_new, edits, note):
    src = open(os.path.join(VDIR, name_old + ".v")).read()
    out = src
    for old, new in edits:
        out = sub1(out, old, new)
    out = sub1(out, "`default_nettype none", "// ledger #1247: DEBUG CLONE of %s -- %s Identical in behaviour; the only additions are the dbg_state port and its wiring.\n`default_nettype none" % (name_old, note))
    path = os.path.join(VDIR, name_new + ".v")
    open(path, "w").write(out)
    d = subprocess.run(["diff", os.path.join(VDIR, name_old + ".v"), path], capture_output=True, text=True).stdout
    added = [l for l in d.splitlines() if l.startswith("> ")]
    removed = [l for l in d.splitlines() if l.startswith("< ")]
    print("%-16s -> %-16s  lines added %d, removed/changed %d" % (name_old, name_new, len(added), len(removed)))
    return path


def main():
    clone("adder_cell_v4e", "adder_cell_v4f", [
        ("module adder_cell_v4e #(", "module adder_cell_v4f #("),
        ("    output wire         status_a_arrived\n);", "    output wire         status_a_arrived,\n    output wire [127:0] dbg_state\n);"),
        ("\nendmodule", "\n" + ADDER_ASSIGN + "endmodule"),            # at the end: program_done_r is declared late in the file
    ], "adds the dbg_state port.")
    clone("adder_shell_v1e", "adder_shell_v1f", [
        ("module adder_shell_v1e #(", "module adder_shell_v1f #("),
        ("    output wire         status_a_arrived\n);", "    output wire         status_a_arrived,\n    output wire [127:0] dbg_state\n);"),
        ("    adder_cell_v4e #(.CELL_ID(CELL_ID)) CORE (", "    adder_cell_v4f #(.CELL_ID(CELL_ID)) CORE ("),
        (".status_data_valid(status_data_valid), .status_a_arrived(status_a_arrived)\n", ".status_data_valid(status_data_valid), .status_a_arrived(status_a_arrived),\n        .dbg_state(dbg_state)\n"),
    ], "wraps adder_cell_v4f.")
    clone("ram_cell_v4", "ram_cell_v4d", [
        ("module ram_cell_v4 #(", "module ram_cell_v4d #("),
        ("    output wire         status_data_valid\n);", "    output wire         status_data_valid,\n    output wire [127:0] dbg_state\n);"),
        ("\nendmodule", "\n" + RAM_ASSIGN + "endmodule"),
    ], "adds the dbg_state port.")
    clone("ram_shell_v1", "ram_shell_v1d", [
        ("module ram_shell_v1 #(", "module ram_shell_v1d #("),
        ("    output wire         status_data_valid\n);", "    output wire         status_data_valid,\n    output wire [127:0] dbg_state\n);"),
        ("    ram_cell_v4 #(.CELL_ID(CELL_ID)) CORE (", "    ram_cell_v4d #(.CELL_ID(CELL_ID)) CORE ("),
        ("        .status_data_valid(status_data_valid)\n", "        .status_data_valid(status_data_valid),\n        .dbg_state(dbg_state)\n"),
    ], "wraps ram_cell_v4d.")


if __name__ == "__main__":
    main()
