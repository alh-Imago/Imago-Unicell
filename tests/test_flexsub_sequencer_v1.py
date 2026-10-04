#!/usr/bin/env python3
"""tests/test_flexsub_sequencer_v1.py -- the sequencer on the sub family (Alan #937: on sub it "loses the ack side and goes back to just
the clock pulse side"; the ack is the flex side's).

Run: python3 tests/test_flexsub_sequencer_v1.py      (needs iverilog)
The VM's sequencer is perpetually live: it offers VALUE_0 first and advances each time a consumer drains its offer (a backward ack),
wrapping after SEQUENCE_LEN+1 values. sequencer_cell_v4s has no ack: it takes an external `advance_in` PULSE and emits the value at the NEXT
index, so its first pulsed value is VALUE_1. The generator therefore (a) rotates the stored values one step so the pulsed sequence starts at
VALUE_0, and (b) exposes the pulse as a top-level adv_<name> input, presented on the same cycle as the other arguments.
Checked against the REAL VM: the bare sequence for every length, and the case that matters -- the sequence paired with a data stream.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def cli(*a):
    return subprocess.run(CLI + list(a), capture_output=True, text=True)


def ram(cid, r, c, up, down):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down})


def seq(cid, r, c, values, length, down):
    cfg = {"VALUE_0": values[0], "VALUE_1": values[1], "VALUE_2": values[2], "VALUE_3": values[3], "SEQUENCE_LEN": length - 1, "downstream_mask": down}
    return IcmV3Record(cell_id=cid, row=r, col=c, core="sequencer", core_config=cfg)


def adder(cid, r, c, up, down):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="adder", core_config={"upstream_mask": up, "downstream_mask": down})


def bare_design(values, length):          # S -> R -> E
    return [seq("S", 1, 1, values, length, ["e"]), ram("R", 1, 2, ["w"], ["e"]), ram("E", 1, 3, ["w"], [])]


def paired_design(values, length):        # S (west of ADD) and X -> Rx1 -> Rx2 (north of ADD) -> ADD -> E
    return [seq("S", 1, 2, values, length, ["e"]), ram("X", 0, 1, [], ["e"]), ram("Rx1", 0, 2, ["w"], ["e"]), ram("Rx2", 0, 3, ["w"], ["s"]),
            adder("ADD", 1, 3, ["w", "n"], ["e"]), ram("E", 1, 4, ["w"], [])]


def rtl(folder, events, cycles):
    """events: [(cycle, {'in:NAME': value} and/or {'adv:NAME': 1})]. Returns [(cycle, value)] of the single output."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    advs = re.findall(r"input\s+wire\s+adv_(\w+)\s*[,)\n]", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    assert len(outs) == 1
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".adv_{n}(a_{n})" for n in advs] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join([f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins] + [f"  reg a_{n} = 0;" for n in advs])
    lines = []
    for cy, ev in events:
        body = " ".join((f"d_{k[3:]} = 32'd{v}; v_{k[3:]} = 1;" if k.startswith("in:") else f"a_{k[4:]} = 1;") for k, v in ev.items())
        lines.append(f"      if (c == {cy}) begin {body} end")
    clear = " ".join([f"v_{n} = 0;" for n in ins] + [f"a_{n} = 0;" for n in advs])
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0; wire [31:0] od; wire ov;
{decl}
  {top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {conn});
  always #5 clk = ~clk;
  integer c;
  initial begin
    repeat (4) @(posedge clk); #1 rst = 0;
    @(posedge clk); #1 cfg_valid = 1; @(posedge clk); #1 cfg_valid = 0;
    repeat (3) @(posedge clk); #1;
    for (c = 0; c < {cycles}; c = c + 1) begin
      {clear}
{chr(10).join(lines)}
      #3 $display("OUT %0d %0d %0d", c, ov, od);
      @(posedge clk); #1;
    end
    $finish;
  end
endmodule
"""
    open(os.path.join(folder, "tb_gen.v"), "w").write(tb)
    files = [f for f in rec["files"] if f.endswith(".v")]
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(folder, "tb.vvp"), "tb_gen.v", *files], cwd=folder, capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError(c.stderr[:400])
    out = subprocess.run(["vvp", os.path.join(folder, "tb.vvp")], capture_output=True, text=True).stdout
    return [(int(a), int(d)) for a, v, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out) if v == "1"]


def vm_drain(records, n, ticks=4, settle=6):
    """The values a draining consumer receives from the exit ram, in order: read each, clear it (as a consumer would)."""
    grid = vm.SuperGrid(records)
    for _ in range(settle):
        grid.tick()
    ex = next(r for r in records if r.cell_id == "E")
    cell = grid.cells[(ex.row, ex.col)]
    got = []
    for _ in range(n * 12):
        grid.tick()
        if cell.ram_data_valid:
            got.append(cell.ram_data_reg)
            cell.ram_data_valid = False
            if len(got) == n:
                break
    return got


def vm_paired(records, xs, settle=6, ticks=30):
    grid = vm.SuperGrid(records)
    for _ in range(settle):
        grid.tick()
    xr = next(r for r in records if r.cell_id == "X")
    ex = next(r for r in records if r.cell_id == "E")
    cell = grid.cells[(ex.row, ex.col)]
    out = []
    for x in xs:
        grid.inject(xr.row, xr.col, x & 0xFFFFFFFF)
        got = None
        for _ in range(ticks):
            grid.tick()
            if cell.ram_data_valid:
                got = cell.ram_data_reg
                cell.ram_data_valid = False
                break
        out.append(got)
    return out


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="seq_")
try:
    print("the bare sequence a consumer sees: RTL (external advance pulses) == the real VM, for every length, past the wrap")
    for values, length in (([10, 20, 30, 40], 4), ([7, 0, 0, 0], 1), ([5, 6, 0, 0], 2), ([1, 2, 3, 0], 3), ([255, 128, 1, 0], 4)):
        recs = bare_design(values, length)
        icm = os.path.join(tmp, f"s{length}.icm")
        IcmV3File(name="s", records=recs).save(icm)
        d = os.path.join(tmp, f"g_s{length}_{values[0]}")
        r = cli("-s", "sub", "--icm", icm, "--output", d)
        ok = r.returncode == 0
        check(f"length {length} {values[:length]}: generates", ok, r.stderr.strip()[:300])
        if not ok:
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        port = rec["sequencers"]["S"]["advance_port"]
        check(f"length {length}: the host contract is recorded (advance port {port}, length {rec['sequencers']['S']['length']})",
              port == "adv_S" and rec["sequencers"]["S"]["length"] == length)
        n = 10
        want = vm_drain(recs, n)
        gap = 6
        hits = rtl(d, [(k * gap, {"adv:S": 1}) for k in range(n)], n * gap + 10)
        got = [v for _, v in hits]
        expect = [values[k % length] for k in range(n)]
        check(f"length {length}: the first {n} values RTL {got} == VM {want} == VALUE_(k mod {length}), starting at VALUE_0",
              got == want == expect, f"rtl={got} vm={want} expect={expect}")

    print("a sequencer feeding a SINGLE-INPUT consumer other than a relay (a comparator): RTL == the real VM")
    recs = [seq("S", 1, 1, [10, 60, 49, 50], 4, ["e"]),
            IcmV3Record(cell_id="C", row=1, col=2, core="comparator", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": 50}),
            ram("E", 1, 3, ["w"], [])]
    icm = os.path.join(tmp, "cmp.icm")
    IcmV3File(name="c", records=recs).save(icm)
    d = os.path.join(tmp, "g_cmp")
    r = cli("-s", "sub", "--icm", icm, "--output", d)
    check("sequencer -> comparator generates", r.returncode == 0, r.stderr.strip()[:300])
    want = vm_drain(recs, 8)
    hits = rtl(d, [(k * 6, {"adv:S": 1}) for k in range(8)], 8 * 6 + 10)
    got = [v for _, v in hits]
    check(f"sequencer [10,60,49,50] -> comparator(>=50): RTL {got} == VM {want} == [0,1,0,1,0,1,0,1]", got == want == [0, 1, 0, 1, 0, 1, 0, 1], f"rtl={got} vm={want}")

    print("a sequencer feeding a TWO-OPERAND cell is refused -- and the reason is a finding about the VM, recorded here")
    recs = paired_design([100, 200, 30, 40], 4)
    icm = os.path.join(tmp, "pair.icm")
    IcmV3File(name="p", records=recs).save(icm)
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_pair"))
    check("refused, naming the arrival-pairing reason", r.returncode != 0 and "ARRIVAL" in r.stderr and "sequencer" in r.stderr, r.stderr.strip()[:300])
    xs = [3, 50, 1000, 7, 0, 99999, 12, 5]
    vmres = vm_paired(recs, xs)
    intended = [(x + [100, 200, 30, 40][k % 4]) & 0xFFFFFFFF for k, x in enumerate(xs)]
    check("FINDING: the VM does NOT compute X_k + VALUE_(k mod n) here (the sequence values pair with each other: first result 100+200 = 300)",
          vmres != intended and vmres[0] == 300, f"vm={vmres} intended={intended}")

    print("an addon on a sequencer is refused")
    recs = bare_design([1, 2, 3, 4], 4)
    recs[0].addon_config = {"shift_en": 1, "shift_amt": 4}
    IcmV3File(name="b", records=recs).save(os.path.join(tmp, "b.icm"))
    r = cli("-s", "sub", "--icm", os.path.join(tmp, "b.icm"), "--output", os.path.join(tmp, "gb"))
    check("addon_config on a sequencer: refused with the reason", r.returncode != 0 and "sequencer" in r.stderr and "addon" in r.stderr, r.stderr.strip()[:240])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
