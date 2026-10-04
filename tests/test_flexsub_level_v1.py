#!/usr/bin/env python3
"""tests/test_flexsub_level_v1.py -- accumulator and latch on the sub family (Alan #938: "Yes, start with those").

Run: python3 tests/test_flexsub_level_v1.py      (needs iverilog)
In the VM a CONTINUOUS accumulator offers its running total, and a latch its 0/1 state, ALWAYS VALID (a level source); the v4s cells pulse
valid_out only on an update. Rule under test: a level source's valid is held high (its own pulse unused) and it counts as constant-like for
timing. A PULSE-MODE accumulator already matches the VM (a discrete event on the threshold crossing) and stays an ordinary timed source.
Checked against the REAL VM: the value a consumer sees after every input item, for a counter, up/down (incl. simultaneous), a pulse-mode
accumulator crossing in both directions, a latch's set/clear/toggle and their priority, and a sentinel chain accumulator -> comparator -> latch.
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


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v


def ram(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down}, **kw)


def acc(cid, r, c, inc, dec, down, step=1, pulse=0, thr=0):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="accumulator", core_config={
        "inc_dir": inc, "dec_dir": dec, "downstream_mask": down, "step_amount": step, "pulse_mode": pulse, "threshold": thr})


def latch(cid, r, c, setd, clr, tog, down):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="latch", core_config={
        "set_dir": setd, "clear_dir": clr, "toggle_dir": tog, "downstream_mask": down})


def cmp_(cid, r, c, up, down, thr):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="comparator", core_config={"upstream_mask": up, "downstream_mask": down, "threshold": thr})


def rtl(folder, events, cycles):
    """events: [(cycle, {entry suffix: value})]. Returns {exit suffix: [(cycle, value)]} (valid cycles only)."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{n}_data(od_{n}), .out_{n}_valid(ov_{n})" for n in outs])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins) + "\n" + "\n".join(f"  wire [31:0] od_{n}; wire ov_{n};" for n in outs)
    drive = "\n".join(f"      if (c == {cy}) begin " + " ".join(f"d_{n} = 32'd{val}; v_{n} = 1;" for n, val in ev.items()) + " end" for cy, ev in events)
    clear = " ".join(f"v_{n} = 0;" for n in ins)
    show = "\n".join(f'      $display("OUT {n} %0d %0d %0d", c, ov_{n}, od_{n});' for n in outs)
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0;
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
{drive}
      #3
{show}
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
    res = {n: [] for n in outs}
    for n, cy, v, d in re.findall(r"OUT (\w+) (\d+) (\d+) (\d+)", out):
        if v == "1":
            res[n].append((int(cy), int(d)))
    return res


def vm_level(records, items, probe_id, getter, settle=8):
    """Per item: inject the entries that fire, run, then read the level source's OWN state in the VM (acc_total / latch_state).
    (Reading it through a manually-cleared exit cell is NOT a valid probe: the VM refreshes an accumulator's offered snapshot only while its
    destination is empty, so the first recapture after a clear is one item stale -- see ledger #938.)"""
    grid = vm.SuperGrid(records)
    for _ in range(settle):
        grid.tick()
    pr = next(r for r in records if r.cell_id == probe_id)
    cell = grid.cells[(pr.row, pr.col)]
    out = []
    for it in items:
        for cid, v in it.items():
            r = next(x for x in records if x.cell_id == cid)
            grid.inject(r.row, r.col, v & 0xFFFFFFFF)
        for _ in range(24):
            grid.tick()
        out.append(getter(cell))
    return out


ACC_TOTAL = lambda c: c.acc_total & 0xFFFFFFFF          # noqa: E731
LATCH_STATE = lambda c: 1 if c.latch_state else 0       # noqa: E731


def vm_events(records, items, exit_id, settle=8):
    """Per item: the discrete event (if any) that reached the exit."""
    grid = vm.SuperGrid(records)
    for _ in range(settle):
        grid.tick()
    ex = next(r for r in records if r.cell_id == exit_id)
    cell = grid.cells[(ex.row, ex.col)]
    out = []
    for it in items:
        for cid, v in it.items():
            r = next(x for x in records if x.cell_id == cid)
            grid.inject(r.row, r.col, v & 0xFFFFFFFF)
        for _ in range(20):
            grid.tick()
        if cell.ram_data_valid:
            out.append(cell.ram_data_reg)
            cell.ram_data_valid = False
        else:
            out.append(None)
    return out


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    r = cli("-s", "sub", "--icm", icm, "--output", d)
    return d, r


def level_rtl(d, items, exit_suffix, gap=24):
    ev = [(k * gap, {cid: v & 0xFFFFFFFF for cid, v in it.items()}) for k, it in enumerate(items)]
    res = rtl(d, ev, len(items) * gap + 6)[exit_suffix]
    byc = dict(res)
    return [byc.get(k * gap + gap - 1) for k in range(len(items))]            # the level just before the next item


def event_rtl(d, items, exit_suffix, gap=24):
    ev = [(k * gap, {cid: v & 0xFFFFFFFF for cid, v in it.items()}) for k, it in enumerate(items)]
    res = rtl(d, ev, len(items) * gap + 6)[exit_suffix]
    out = []
    for k in range(len(items)):
        w = [v for c, v in res if k * gap <= c < (k + 1) * gap]
        out.append(w[0] if w else None)
    return out


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="level_")
try:
    print("accumulator, continuous mode -- a LEVEL source: the running total, after every item (RTL == the real VM)")
    recs = [ram("XI", 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"], [], ["e"], step=3), ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "cnt", recs)
    check("counter generates", r.returncode == 0, r.stderr.strip()[:300])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    check("ASSEMBLY.json records the level source", rec["level_sources"] == ["ACC"], str(rec.get("level_sources")))
    items = [{"XI": 0xDEAD}] * 9
    want, got = vm_level(recs, items, "ACC", ACC_TOTAL), level_rtl(d, items, "E")
    check(f"9 increments of 3 (the arriving value is ignored): RTL {got} == VM {want} == 3,6,..,27",
          got == want == [3 * (k + 1) for k in range(9)], f"rtl={got} vm={want}")

    print("up/down, including a simultaneous inc + dec (net zero), negative totals")
    recs = [ram("XI", 0, 1, [], ["s"]), ram("XD", 2, 1, [], ["n"]), acc("ACC", 1, 1, ["n"], ["s"], ["e"], step=5), ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "ud", recs)
    check("up/down generates", r.returncode == 0, r.stderr.strip()[:300])
    items = [{"XI": 1}, {"XI": 1}, {"XD": 1}, {"XI": 1, "XD": 1}, {"XD": 1}, {"XD": 1}, {"XD": 1}, {"XI": 1}]
    want, got = vm_level(recs, items, "ACC", ACC_TOTAL), level_rtl(d, items, "E")
    sw, sg = [s32(x) if x is not None else None for x in want], [s32(x) if x is not None else None for x in got]
    check(f"inc,inc,dec,(inc+dec),dec,dec,dec,inc with step 5: RTL {sg} == VM {sw} == 5,10,5,5,0,-5,-10,-5",
          sg == sw == [5, 10, 5, 5, 0, -5, -10, -5], f"rtl={sg} vm={sw}")

    print("accumulator, PULSE mode -- a discrete event on the threshold crossing, resets to 0, crosses in both directions")
    recs = [ram("XI", 0, 1, [], ["s"]), ram("XD", 2, 1, [], ["n"]), acc("ACC", 1, 1, ["n"], ["s"], ["e"], step=10, pulse=1, thr=25), ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "pulse", recs)
    check("pulse-mode accumulator generates", r.returncode == 0, r.stderr.strip()[:300])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    check("a pulse-mode accumulator is NOT a level source (it is a timed event source)", rec["level_sources"] == [], str(rec["level_sources"]))
    items = [{"XI": 1}] * 3 + [{"XD": 1}] * 3 + [{"XI": 1}, {"XD": 1}] * 2 + [{"XI": 1}] * 3
    want, got = vm_events(recs, items, "E"), event_rtl(d, items, "E")
    sw, sg = [s32(x) if x is not None else None for x in want], [s32(x) if x is not None else None for x in got]
    check(f"events RTL {sg} == VM {sw}  (30 at the 3rd inc, -30 at the 3rd dec, none between)", sg == sw and 30 in sg and -30 in sg, f"rtl={sg} vm={sw}")

    print("latch -- a LEVEL source: set needs bit 0 of the arriving value; priority clear > set > toggle")
    recs = [ram("XS", 0, 1, [], ["s"]), ram("XC", 1, 0, [], ["e"]), ram("XT", 2, 1, [], ["n"]),
            latch("L", 1, 1, ["n"], ["w"], ["s"], ["e"]), ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "latch", recs)
    check("latch generates", r.returncode == 0, r.stderr.strip()[:300])
    items = [{"XS": 1}, {"XS": 0}, {"XT": 1}, {"XT": 1}, {"XS": 3}, {"XC": 1}, {"XS": 1, "XC": 1}, {"XT": 1, "XS": 1}, {"XT": 1}, {"XT": 1, "XC": 1}]
    want, got = vm_level(recs, items, "L", LATCH_STATE), level_rtl(d, items, "E")
    check(f"set(1), set(0:no-op), toggle, toggle, set(3), clear, set+clear, toggle+set, toggle, toggle+clear: RTL {got} == VM {want}",
          got == want, f"rtl={got} vm={want}")

    print("a sentinel chain: accumulator (level) -> comparator -> latch SET (level driving a level)")
    recs = [ram("XI", 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"], [], ["e"], step=1), cmp_("CMP", 1, 2, ["w"], ["e"], 5),
            latch("L", 1, 3, ["w"], [], [], ["e"]), ram("E", 1, 4, ["w"], [])]
    d, r = build(tmp, "sentinel", recs)
    check("sentinel chain generates", r.returncode == 0, r.stderr.strip()[:300])
    items = [{"XI": 1}] * 9
    want, got = vm_level(recs, items, "L", LATCH_STATE), level_rtl(d, items, "E")
    check(f"count to 9 with the sentinel at >= 5: the latch reads RTL {got} == VM {want} == 0,0,0,0,1,1,1,1,1",
          got == want == [0, 0, 0, 0, 1, 1, 1, 1, 1], f"rtl={got} vm={want}")

    print("refusals: a level/constant source into a COUNTING or TOGGLING input is rate-dependent")
    cases = (
        ("a constant feeding an accumulator's inc", [ram("K", 1, 0, [], ["e"], preload_value=1), acc("ACC", 1, 1, ["w"], [], ["e"]), ram("E", 1, 2, ["w"], [])], "inc"),
        ("an accumulator (level) feeding another accumulator's inc",
         [ram("XI", 1, 0, [], ["e"]), acc("A1", 1, 1, ["w"], [], ["e"]), acc("A2", 1, 2, ["w"], [], ["e"]), ram("E", 1, 3, ["w"], [])], "inc"),
        ("a comparator-of-a-level feeding a latch's toggle",
         [ram("XI", 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"], [], ["e"]), cmp_("CMP", 1, 2, ["w"], ["e"], 3),
          latch("L", 1, 3, [], [], ["w"], ["e"]), ram("E", 1, 4, ["w"], [])], "toggle"))
    for label, recs, role in cases:
        d, r = build(tmp, "bad", recs)
        check(f"refused: {label}", r.returncode != 0 and "RATE" in r.stderr.upper() and role in r.stderr, r.stderr.strip()[:260])
    d, r = build(tmp, "unconn", [acc("ACC", 1, 1, [], [], ["e"]), ram("E", 1, 2, ["w"], [])])
    check("refused: an accumulator with no pulse input connected", r.returncode != 0 and "no pulse input" in r.stderr, r.stderr.strip()[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
