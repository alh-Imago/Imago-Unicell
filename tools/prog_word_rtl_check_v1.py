#!/usr/bin/env python3
"""tools/prog_word_rtl_check_v1.py -- ledger #1305: the VM's word-programming tables against the REAL RTL, by simulation.
For each of adder, mul (mul_cell_v5), div, priority, merge: the standard-family cell is simulated in iverilog, every PROG_ID (0-7, including ids the cell does not have) is written through the
cell's real programming channel with random 20-bit words, and after every write the cell's own programmed registers are read (hierarchically) and compared with the fields of a VM cell that
received the same words through SuperCell.program_word(). Prints one line per core and exits 1 on any difference. Needs iverilog. Usage: python3 tools/prog_word_rtl_check_v1.py [--writes N] [--seed S]"""
import os, random, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperCell  # noqa: E402

V = os.path.join(ROOT, "fpga", "verilog")
# core -> (module, source files, [(RTL register, width, VM field)], first write that must come before the credits are meaningful)
CORES = {
    "adder": ("adder_cell_v4", ["adder_cell_v4.v"], [("downstream_mask", 6, "adder_downstream_mask"), ("upstream_mask", 6, "adder_upstream_mask"), ("subtract_mode", 1, "adder_subtract_mode"),
              ("second_output", 1, "adder_carry_mode"), ("second_downstream_mask", 6, "second_mask"), ("addon_config", 20, "addon_config")]),
    "mul": ("mul_cell_v5", ["mul_cell_v5.v"], [("downstream_mask", 6, "mul_downstream_mask"), ("upstream_mask", 6, "mul_upstream_mask"), ("wide_mode", 1, "mul_wide_mode"),
            ("second_downstream_mask", 6, "second_mask"), ("addon_config", 20, "addon_config")]),
    "div": ("div_cell_v4", ["div_cell_v4.v"], [("downstream_mask", 6, "div_downstream_mask"), ("upstream_mask", 6, "div_upstream_mask"), ("rem_primary", 1, "div_remainder_primary"),
            ("second_output", 1, "div_second_output"), ("second_downstream_mask", 6, "second_mask"), ("addon_config", 20, "addon_config")]),
    "priority": ("priority_cell_v4", ["priority_cell_v4.v"], [("upstream_mask", 6, "pri_upstream_mask"), ("downstream_mask", 6, "pri_downstream_mask"), ("priority_rank_n", 2, "pri_rank_n"),
                ("priority_rank_s", 2, "pri_rank_s"), ("priority_rank_e", 2, "pri_rank_e"), ("priority_rank_w", 2, "pri_rank_w"), ("scheduling_mode", 1, "pri_scheduling_mode"),
                ("credit_n", 8, "pri_credit_n"), ("credit_s", 8, "pri_credit_s"), ("credit_e", 8, "pri_credit_e"), ("credit_w", 8, "pri_credit_w"), ("addon_config", 20, "addon_config")]),
    "merge": ("merge_cell_v4", ["merge_cell_v4.v"], [("downstream_mask", 6, "mrg_downstream_mask"), ("upstream_mask", 6, "mrg_upstream_mask"), ("mode", 2, "mrg_mode"), ("addon_config", 20, "addon_config")]),
}
# ids that exist per core (written once each, in this order, before the random writes, so every register has a defined value; priority's ranks word also defines its credits)
IDS = {"adder": [0, 1, 2, 3, 4, 5], "mul": [0, 1, 2, 3, 4], "div": [0, 1, 2, 3, 4, 5], "priority": [2, 0, 1, 3], "merge": [0, 1, 2, 5]}


def make_tb(core, writes):
    mod, _, regs = CORES[core]
    lines = ["`timescale 1ns/1ps", "module tb;", " reg clk=0; always #5 clk=~clk;", " reg rst=1, active=1, program_in=0, arr=0; reg [31:0] pd=0;",
             f" {mod} DUT(.clk(clk), .rst(rst), .active(active), .program_in(program_in), .prog_arrived_in_n(arr), .prog_data_in_n(pd));",
             " task wr(input [2:0] id, input [19:0] w); begin @(negedge clk); pd={9'h0,id,w}; arr=1; program_in=1; @(negedge clk); arr=0; @(negedge clk);"]
    fmt = " ".join(["%0d" if False else "%h"] * len(regs))
    lines.append(f"   $display(\"R {core} %0d %h {fmt}\", id, w, " + ", ".join(f"DUT.{r}" for r, _, _ in regs) + "); end endtask")
    lines += [" initial begin repeat(3) @(negedge clk); rst=0;"]
    lines += [f"  wr(3'd{i}, 20'h{w:05x});" for i, w in writes]
    lines += [" $finish; end", "endmodule"]
    return "\n".join(lines)


def main():
    n = int(sys.argv[sys.argv.index("--writes") + 1]) if "--writes" in sys.argv else 80
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 1305
    if not shutil.which("iverilog"):
        print("iverilog not found: this check cannot run"); return 2
    rnd = random.Random(seed)
    bad = 0
    for core, (mod, files, regs) in CORES.items():
        writes = [(i, rnd.getrandbits(20)) for i in IDS[core]] + [(rnd.randrange(8), rnd.getrandbits(20)) for _ in range(n)]
        d = tempfile.mkdtemp(prefix="pwrtl_")
        open(os.path.join(d, "tb.v"), "w").write(make_tb(core, writes))
        out = os.path.join(d, "sim.vvp")
        r = subprocess.run(["iverilog", "-g2012", "-y", V, "-Y", ".v", "-o", out, os.path.join(d, "tb.v")] + [os.path.join(V, f) for f in files], capture_output=True, text=True)
        if r.returncode:
            print(core, "iverilog failed:", r.stderr[:300]); bad += 1; continue
        sim = subprocess.run(["vvp", out], capture_output=True, text=True).stdout.splitlines()
        rows = [l.split() for l in sim if l.startswith("R ")]
        cell = SuperCell.from_record(v3.IcmV3Record(cell_id="c", row=0, col=0, core=core, core_config={}, addon_config={}))
        diffs = 0
        for (i, w), row in zip(writes, rows):
            cell.program_word(i, w)
            if i == 7:
                continue
            vals = [int(x, 16) if re.fullmatch(r"[0-9a-f]+", x) else None for x in row[4:]]
            for (rname, width, vmf), rv in zip(regs, vals):
                vv = getattr(cell, vmf)
                vv = int(vv) if not isinstance(vv, dict) else (0 if not vv else None)     # addon_config is {} until a word writes it; the RTL reads 0
                if rv is None or vv is None or rv != vv:
                    # a register not yet written reads x in the RTL: not compared until it has been written (the first writes cover every id)
                    if rv is None and (i, w) in writes[:len(IDS[core])]:
                        continue
                    diffs += 1
                    if diffs <= 3:
                        print(f"  {core}: after id {i} word {w:05x}: RTL {rname}={row[4 + [r_[0] for r_ in regs].index(rname)]} VM {vmf}={getattr(cell, vmf)}")
        print(f"{core:9s} {len(rows)} writes simulated, {len(regs)} registers compared after each: {'IDENTICAL' if not diffs and len(rows) == len(writes) else 'DIFFERENT (%d)' % diffs}")
        bad += 1 if (diffs or len(rows) != len(writes)) else 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
