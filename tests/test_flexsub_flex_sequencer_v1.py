#!/usr/bin/env python3
"""tests/test_flexsub_flex_sequencer_v1.py -- the SEQUENCER on the FLEX family (stage 8, ledger #956): the last ICM core the planner translates.

Run: python3 tests/test_flexsub_flex_sequencer_v1.py      (needs iverilog)
Alan: the sequencer "ran on the clock signal, or the ack signal advancing each tick ... the adder cell just sends it an ack once it's cleared its internal sequence, and the sequencer sees
this and fires, switches to the next value and waits." sequencer_cell_v4sa still advances only on advance_in, so the emitter ties advance_in to the cell's own READY: it offers a new value
whenever the previous one has been taken, paced entirely by the CONSUMER's ack (the VM's "advance when drained"). The stored values are rotated one step (the cell pulses the NEXT index),
as on sub. Checked against the REAL VM: the bare sequence for every length, a comparator consumer, and the PAIRING with a stream -- where flex pairs ONE value per stream item
(item k with VALUE_(k mod n)) and the VM pairs the sequence with ITSELF (#937): a recorded, deliberate divergence. Plus the cell's armed gate, fan-out, and mutation controls.
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


def ram(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down}, **kw)


def seq(cid, r, c, values, length, down):
    cfg = {"VALUE_0": values[0], "VALUE_1": values[1], "VALUE_2": values[2], "VALUE_3": values[3], "SEQUENCE_LEN": length - 1, "downstream_mask": down}
    return IcmV3Record(cell_id=cid, row=r, col=c, core="sequencer", core_config=cfg)


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", icm, "--output", d)


def run_level(folder, streams, mode="plain", seed=1, settle=60, cycles=3000):
    """streams: {entry port suffix: [values]} (lengths may DIFFER). mode: plain (items back-to-back, exit always ready) | stall (random input gaps + random exit stalls) |
    skewfirst / skewlast (the first / last input slow, to stagger them). Returns (levels {exit: per-cycle data}, got {exit: [values captured on valid&ack]})."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = sorted(set(re.findall(r"in_(\w+)_data", text)))
    outs = sorted(set(re.findall(r"out_(\w+)_data", text)))
    assert sorted(ins) == sorted(streams), (ins, list(streams))
    decl, drv, conn, dones = [], [], [], []
    for k, name in enumerate(ins):
        vals = streams[name]
        n = len(vals)
        decl.append(f"  reg [31:0] mem_{name} [0:{n}]; integer idx_{name} = 0; reg act_{name} = 0; wire ack_{name};\n"
                    f"  wire [31:0] d_{name} = (idx_{name} < {n}) ? mem_{name}[idx_{name}] : 32'h0;")
        decl.append("  initial begin " + " ".join(f"mem_{name}[{j}] = 32'd{v};" for j, v in enumerate(vals)) + " end")
        slow3 = f"(lfsr[{(3 * k + 2) % 31}] & lfsr[{(5 * k + 7) % 31}] & lfsr[{(2 * k + 13) % 31}])"
        gap = (f"(lfsr[{(3 * k + 2) % 31}] | lfsr[{(5 * k + 7) % 31}])" if mode == "stall" else
               slow3 if (mode == "skewfirst" and k == 0) or (mode == "skewlast" and k == len(ins) - 1) else "(1'b1)")
        drv.append(f"      if (act_{name} && ack_{name}) begin idx_{name} <= idx_{name} + 1; act_{name} <= 1'b0; end\n"
                   f"      else if (!act_{name} && idx_{name} < {n} && {gap}) act_{name} <= 1'b1;")
        conn.append(f".in_{name}_data(d_{name}), .in_{name}_valid(act_{name}), .in_{name}_ack(ack_{name})")
        dones.append(f"idx_{name} >= {n}")
    cap = []
    for k, name in enumerate(outs):
        ready = f"lfsr[{(7 * k + 11) % 31}]" if mode == "stall" else "1'b1"
        decl.append(f"  wire [31:0] od_{name}; wire ov_{name}; wire oa_{name} = {ready};")
        cap.append(f'      $display("LV {name} %0d %0d", cyc, od_{name});\n'
                   f'      if (ov_{name} && oa_{name}) $display("GOT {name} %0d", od_{name});')
        conn.append(f".out_{name}_data(od_{name}), .out_{name}_valid(ov_{name}), .out_{name}_ack(oa_{name})")
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0;
  reg [31:0] lfsr = 32'h{(0xACE1 ^ (seed * 0x9E3779B1)) & 0xFFFFFFFF or 1:08X};
{chr(10).join(decl)}
  {top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {', '.join(conn)});
  always #5 clk = ~clk;
  integer cyc = 0, post = 0; reg started = 0;
  always @(posedge clk) begin
    lfsr <= {{lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]}};
    if (started) begin
      cyc <= cyc + 1;
{chr(10).join(drv)}
{chr(10).join(cap)}
      if ({' && '.join(dones) if dones else "1'b1"}) post <= post + 1;
      if (post > {settle} || cyc > {cycles}) $finish;
    end
  end
  initial begin
    repeat (4) @(posedge clk); #1 rst = 0;
    @(posedge clk); #1 cfg_valid = 1; @(posedge clk); #1 cfg_valid = 0;
    repeat (3) @(posedge clk); #1 started = 1;
  end
endmodule
"""
    open(os.path.join(folder, "tb_gen.v"), "w").write(tb)
    files = [f for f in rec["files"] if f.endswith(".v")]
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(folder, "tb.vvp"), "tb_gen.v", *files], cwd=folder, capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError(c.stderr[:400])
    out = subprocess.run(["vvp", os.path.join(folder, "tb.vvp")], capture_output=True, text=True).stdout
    levels = {o: [] for o in outs}
    got = {o: [] for o in outs}
    for o, cy, v in re.findall(r"LV (\w+) (\d+) (\d+)", out):
        levels[o].append(int(v))
    for o, v in re.findall(r"GOT (\w+) (\d+)", out):
        got[o].append(int(v))
    return levels, got


def vm_drain(records, n, exit_id="E", settle=6):
    """The values a draining consumer receives from the exit ram in the VM, in order (read each, clear it)."""
    g_ = vm.SuperGrid(records)
    for _ in range(settle):
        g_.tick()
    ex = next(r for r in records if r.cell_id == exit_id)
    cell = g_.cells[(ex.row, ex.col)]
    got = []
    for _ in range(n * 14):
        g_.tick()
        if cell.ram_data_valid:
            got.append(cell.ram_data_reg)
            cell.ram_data_valid = False
            if len(got) == n:
                break
    return got


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)
tmp = tempfile.mkdtemp(prefix="flexseq_")
try:
    print("the bare sequence: a FREE-RUNNING source paced by the consumer's ack -- S -> relay -> exit E; every length, past the wrap, == the real VM")
    for values, length in (([10, 20, 30, 40], 4), ([7, 0, 0, 0], 1), ([5, 6, 0, 0], 2), ([1, 2, 3, 0], 3), ([255, 128, 1, 0], 4)):
        recs = [seq("S", 1, 1, values, length, ["e"]), ram("R", 1, 2, ["w"], ["e"]), ram("E", 1, 3, ["w"], [])]
        d, r = build(tmp, f"bare{length}_{values[0]}", recs)
        if r.returncode:
            check(f"length {length} {values[:length]}: generates", False, r.stderr.strip()[:240])
            continue
        n = 10
        want = vm_drain(recs, n)
        expect = [values[k % length] for k in range(n)]
        bad = []
        for mode, seed in (("plain", 1), ("stall", 2), ("stall", 3)):
            _, got = run_level(d, {}, mode, seed, settle=240)
            if got["E"][:n] != expect:
                bad.append((mode, got["E"][:n]))
        check(f"length {length} {values[:length]}: the first {n} values x 3 modes (plain, two random exit stalls) == the VM {want} == VALUE_(k mod {length}), starting at VALUE_0",
              not bad and want == expect, f"{bad[:1]} vm={want}")

    print("a comparator consumer: S [10,60,49,50] -> comparator(>=50) -> E")
    recs = [seq("S", 1, 1, [10, 60, 49, 50], 4, ["e"]),
            IcmV3Record(cell_id="C", row=1, col=2, core="comparator", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": 50}), ram("E", 1, 3, ["w"], [])]
    d, r = build(tmp, "cmp", recs)
    check("sequencer -> comparator generates", r.returncode == 0, r.stderr.strip()[:200])
    want = vm_drain(recs, 8)
    _, got = run_level(d, {}, "stall", 4, settle=240)
    check(f"RTL {got['E'][:8]} == the VM {want} == [0,1,0,1,0,1,0,1]", got["E"][:8] == want == [0, 1, 0, 1, 0, 1, 0, 1], f"rtl={got['E'][:8]} vm={want}")

    print("THE PAIRING (Alan: the adder acknowledges, the sequencer switches to the next value and waits): a sequence paired with a STREAM through an adder")
    values = [100, 200, 30, 40]
    pair = [seq("S", 1, 2, values, 4, ["e"]), ram("X", 0, 1, [], ["e"]), ram("Rx1", 0, 2, ["w"], ["e"]), ram("Rx2", 0, 3, ["w"], ["s"]),
            IcmV3Record(cell_id="ADD", row=1, col=3, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}), ram("E", 1, 4, ["w"], [])]
    d, r = build(tmp, "pair", pair)
    check("a sequencer feeding a two-operand cell GENERATES on flex (it is refused on sub, #937)", r.returncode == 0, r.stderr.strip()[:240])
    xs = [3, 50, 1000, 7, 0, 99999, 12, 5, 77, 1]
    want = [(x + values[k % 4]) & 0xFFFFFFFF for k, x in enumerate(xs)]
    bad = []
    for mode, seed in (("plain", 5), ("stall", 6), ("stall", 7), ("skewfirst", 8)):
        _, got = run_level(d, {"X": xs}, mode, seed, settle=240)
        if got["E"] != want:
            bad.append((mode, got["E"][:4], want[:4]))
    check("10 stream items x 4 modes: item k + VALUE_(k mod 4), in order, none lost -- ONE sequence value per stream item", not bad, str(bad[:1]))
    vmres = []
    g_ = vm.SuperGrid(pair)
    for _ in range(8):
        g_.tick()
    ec = g_.cells[(1, 4)]
    for x in xs[:4]:
        g_.inject(0, 1, x)
        for _ in range(30):
            g_.tick()
        vmres.append(ec.ram_data_reg if ec.ram_data_valid else None)
        ec.ram_data_valid = False
    check(f"FINDING (deliberate, recorded): the VM does NOT compute that -- its arrival-paired adder pairs the sequence with ITSELF: VM {vmres} vs flex {want[:4]}",
          vmres[0] == values[0] + values[1] and vmres != want[:4], f"vm={vmres}")

    print("fan-out: one sequencer feeding TWO consumers through the usual eager fork -- both see the SAME sequence, advanced only when both have taken a value")
    fan = [seq("S", 1, 1, [11, 22, 33, 44], 4, ["n", "s"]), ram("A", 0, 1, ["s"], ["e"]), ram("EA", 0, 2, ["w"], []), ram("B", 2, 1, ["n"], ["e"]), ram("EB", 2, 2, ["w"], [])]
    d, r = build(tmp, "fan", fan)
    check("a fanned-out sequencer generates with a fork", r.returncode == 0 and len(json.load(open(os.path.join(d, "ASSEMBLY.json")))["forks"]) == 1, r.stderr.strip()[:200])
    bad = []
    for mode, seed in (("plain", 9), ("stall", 10), ("stall", 11)):
        _, got = run_level(d, {}, mode, seed, settle=300)
        ea, eb = got["EA"][:8], got["EB"][:8]
        if ea != eb or ea != [[11, 22, 33, 44][k % 4] for k in range(8)]:
            bad.append((mode, ea, eb))
    check("x 3 modes (independent exit stalls on the two branches): both exits receive 11,22,33,44,11,22,33,44 -- identical, in order", not bad, str(bad[:1]))

    print("MUTATION CONTROLS")
    recs = [seq("S", 1, 1, [10, 20, 30, 40], 4, ["e"]), ram("R", 1, 2, ["w"], ["e"]), ram("E", 1, 3, ["w"], [])]
    d, r = build(tmp, "mut_base", recs)
    top = os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")
    orig = open(top).read()
    muts = [("the values are NOT rotated (the sequence starts at VALUE_1)", r"\.cfg_data\(32'h[0-9A-F]{8}\)", ".cfg_data(32'h281E140A)"),
            ("advance_in tied low (it never advances)", r"\.advance_in\(\w+_rdy\)", ".advance_in(1'b0)")]
    for mi, (label, pat, rep) in enumerate(muts):
        txt = re.sub(pat, rep, orig, count=1)
        assert txt != orig, pat
        dm = os.path.join(tmp, f"muts_{mi}")
        shutil.copytree(d, dm)
        open(os.path.join(dm, os.path.basename(top)), "w").write(txt)
        _, got = run_level(dm, {}, "plain", 1, settle=200)
        check(f"  mutant caught: {label}", got["E"][:10] != [[10, 20, 30, 40][k % 4] for k in range(10)], str(got["E"][:6]))
    SUBV = os.path.join(ROOT, "sub", "verilog")
    cell = open(os.path.join(SUBV, "sequencer_cell_v4sa.v")).read()
    assert "advance_in && armed" in cell
    open(os.path.join(tmp, "unfixed.v"), "w").write(cell.replace("advance_in && armed", "advance_in", 1))
    ok_ = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(tmp, "a.vvp"), os.path.join(SUBV, "tb_sequencer_cell_v4sa.v"), os.path.join(SUBV, "sequencer_cell_v4sa.v")], capture_output=True, text=True)
    out_ok = subprocess.run(["vvp", os.path.join(tmp, "a.vvp")], capture_output=True, text=True).stdout
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(tmp, "b.vvp"), os.path.join(SUBV, "tb_sequencer_cell_v4sa.v"), os.path.join(tmp, "unfixed.v")], capture_output=True, text=True)
    out_bad = subprocess.run(["vvp", os.path.join(tmp, "b.vvp")], capture_output=True, text=True).stdout
    check("the CELL's armed gate: the bench passes on the fixed cell and FAILS on the unfixed one (an unconfigured cell must not offer a value)",
          "ALL PASS" in out_ok and "FAIL: unconfigured: no offer" in out_bad, out_bad[-200:])

    print("refusals")
    d, r = build(tmp, "seqmerge", [seq("S", 1, 1, [1, 2, 3, 4], 4, ["e"]), ram("N", 0, 2, [], ["s"]), ram("M", 1, 2, ["w", "n"], ["e"]), ram("E", 1, 3, ["w"], [])])
    check("a sequencer feeding a MERGE is refused on flex (which value the merge takes is ambiguous)", r.returncode != 0 and "MERGE" in r.stderr, r.stderr.strip()[:240])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
