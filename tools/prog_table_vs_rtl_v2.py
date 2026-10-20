#!/usr/bin/env python3
"""tools/prog_table_vs_rtl_v2.py -- ledger #1305, a clone of prog_table_vs_rtl_v1.py (#1284; v1 untouched): now also mul (mul_cell_v5.v, the wide-mode mul the VM models), div, priority and merge, and command (whose table lives in vix_carrier_automaton_v1.py, #868, which #1284 did not look at). Original text: ledger #1284: compare the VM's per-core programming tables (nano/unicell_super_automaton_v1._PROG_TABLES, PROG_ID -> field) with the
PROG_ID_* localparams the standard-family RTL (fpga/verilog/<core>_cell_v4.v) really declares. It lists, per core, ids the RTL has that the VM table lacks, ids the VM table has
that the RTL lacks, and the (RTL name, VM field) pair for every id both have so a person can see whether they mean the same thing. Names are NOT matched automatically beyond that.
Scope: the standard family (fpga/verilog) only; widths are not compared here. Usage: python3 tools/prog_table_vs_rtl_v1.py [--json]"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import unicell_super_automaton_v1 as sa  # noqa: E402
import vix_carrier_automaton_v1 as vc  # noqa: E402   # command's table (ledger #868)

FILES = {"adder": "adder_cell_v4.v", "ram": "ram_cell_v4.v", "comparator": "compare_cell_v4.v", "accumulator": "accumulator_cell_v4.v", "latch": "latch_cell_v4.v",
         "sequencer": "sequencer_cell_v4.v", "branch": "branch_cell_v4.v", "mul": "mul_cell_v5.v", "div": "div_cell_v4.v", "priority": "priority_cell_v4.v", "merge": "merge_cell_v4.v",
         "command": "command_cell_v4.v"}


def rtl_ids(path):
    out = {}
    for m in re.finditer(r"localparam\s*(?:\[[^\]]*\])?\s*PROG_ID_(\w+)\s*=\s*\d+'d(\d+)", open(path).read()):
        out[int(m.group(2))] = m.group(1)
    return out


def main():
    res = {}
    for core, fn in FILES.items():
        rtl = rtl_ids(os.path.join(ROOT, "fpga", "verilog", fn))
        vm = {k: v[1] for k, v in (vc._COMMAND_PROG_TABLE if core == "command" else sa._PROG_TABLES[core]).items()}
        res[core] = {"rtl_only": {k: rtl[k] for k in sorted(set(rtl) - set(vm))},
                     "vm_only": {k: vm[k] for k in sorted(set(vm) - set(rtl))},
                     "both": {k: [rtl[k], vm[k]] for k in sorted(set(rtl) & set(vm))}}
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1))
    else:
        for core, r in res.items():
            print(f"{core}: RTL-only ids {r['rtl_only'] or '-'} | VM-only ids {r['vm_only'] or '-'}")
            for k, (a, b) in r["both"].items():
                print(f"    id {k}: RTL {a:<26} VM {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
