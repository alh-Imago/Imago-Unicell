#!/usr/bin/env python3
"""tests/test_flexsub_merge_v1.py -- gated-OR merges on the sub family (Alan #924: same-time arrivals OR together).

Run: python3 tests/test_flexsub_merge_v1.py      (needs iverilog)
Hand-built ICM v3 designs with a real merge: two source rams feed one ram (upstream faces N and W). Checks, against the REAL VM
where it can speak (one-shot items) and an explicit oracle where it cannot (back-to-back items, which the VM handshakes):
  - same-cycle arrivals OR together (RTL == VM);
  - a single active source passes straight through;
  - GATING: after both sources fired, a later item from ONE source must not pick up the other's stale value;
  - the two refusals with a definite reason (merge including a constant; merge of different latencies).
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
    cfg = {"upstream_mask": up, "downstream_mask": down}
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config=cfg, **kw)


def merge_design(extra_relay_on_n=False, const_on_w=False):
    """E1 above M (N face), E2 left of M (W face), M merges them, O is the output. Optional variants for the refusals."""
    if not extra_relay_on_n:
        recs = [ram("E1", 0, 1, [], ["s"]), ram("M", 1, 1, ["n", "w"], ["e"]), ram("O", 1, 2, ["w"], ["e"])]
        recs.append(ram("E2", 1, 0, [], ["e"], preload_value=77) if const_on_w else ram("E2", 1, 0, [], ["e"]))
    else:   # N path has one more relay than the W path -> different latencies
        recs = [ram("E1", 0, 2, [], ["s"]), ram("R", 1, 2, ["n"], ["s"]), ram("M", 2, 2, ["n", "w"], ["e"]),
                ram("E2", 2, 1, [], ["e"]), ram("O", 2, 3, ["w"], ["e"])]
    return recs


def rtl(folder, events, cycles=40):
    """events: [(cycle, {entry id: value})]; each event pulses those entries' valid for one cycle. Returns [(cycle, data)]."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    assert len(outs) == 1
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins)
    drive = "\n".join(f"      if (c == {cy}) begin " + " ".join(f"d_{n} = 32'd{val}; v_{n} = 1;" for n, val in ev.items()) + " end" for cy, ev in events)
    clear = " ".join(f"v_{n} = 0;" for n in ins)
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
{drive}
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
        raise RuntimeError(c.stderr[:300])
    out = subprocess.run(["vvp", os.path.join(folder, "tb.vvp")], capture_output=True, text=True).stdout
    return [(int(a), int(d)) for a, v, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out) if v == "1"]


def vm_out(records, inject):
    grid = vm.SuperGrid(records)
    for cid, val in inject.items():
        r = next(x for x in records if x.cell_id == cid)
        cell = grid.cells[(r.row, r.col)]
        cell.ram_data_reg, cell.ram_data_valid = val & 0xFFFFFFFF, True
    o = next(x for x in records if x.cell_id == "O")
    oc = grid.cells[(o.row, o.col)]
    for _ in range(40):
        grid.tick()
        if oc.ram_data_valid:
            return oc.ram_data_reg
    return None


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="merge_")
try:
    recs = merge_design()
    icm = os.path.join(tmp, "m.icm")
    IcmV3File(name="m", records=recs).save(icm)
    d = os.path.join(tmp, "g")
    r = cli("-s", "sub", "--icm", icm, "--output", d)
    check("a merge of two equal-latency sources generates", r.returncode == 0, r.stderr.strip()[:300])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    check("ASSEMBLY.json records the merge", rec["merges"] == {"M": ["E1", "E2"]}, str(rec["merges"]))
    lat = list(rec["output_latency_cycles"].values())[0]
    top = open(os.path.join(d, rec["top"] + ".v")).read()
    check("the glue is a GATED OR (each source masked by its own valid)", "c_E1_v ? c_E1_d" in top and "c_E2_v ? c_E2_d" in top and "c_M_mrg_v" in top)

    print("same-cycle arrivals OR together: RTL == the real VM")
    for a, b in ((0x0F0F0F0F, 0x00FF00FF), (1, 2), (0xFFFFFFFF, 0), (0x12345678, 0x12345678), (0, 0)):
        got = rtl(d, [(0, {"E1": a, "E2": b})])
        vmv = vm_out(recs, {"E1": a, "E2": b})
        check(f"E1={a:#x} E2={b:#x}: RTL {got} == VM {vmv:#x} == {a | b:#x}", got == [(lat, a | b)] and vmv == (a | b), f"rtl={got} vm={vmv}")

    print("a single active source passes straight through")
    for who, v in (("E1", 0xCAFEF00D), ("E2", 0x0BADBEEF)):
        got = rtl(d, [(0, {who: v})])
        vmv = vm_out(recs, {who: v})
        check(f"only {who} fires: RTL {got} == VM {vmv:#x} == {v:#x}", got == [(lat, v)] and vmv == v, f"rtl={got} vm={vmv}")

    print("GATING: a later item from ONE source must not pick up the other source's stale value")
    got = rtl(d, [(0, {"E1": 0x000000AA, "E2": 0x00005500}), (12, {"E1": 0x00000011})])
    check("item 1 = E1|E2, item 2 = E1 alone -> second result is 0x11, NOT 0x11 | stale E2",
          got == [(lat, 0x55AA), (12 + lat, 0x11)], str(got))
    got = rtl(d, [(0, {"E1": 0x000000AA, "E2": 0x00005500}), (12, {"E2": 0x00000022})])
    check("item 2 = E2 alone -> 0x22, NOT 0x22 | stale E1", got == [(lat, 0x55AA), (12 + lat, 0x22)], str(got))
    got = rtl(d, [(0, {"E1": 3}), (4, {"E2": 5}), (8, {"E1": 6, "E2": 9}), (12, {"E1": 1})])
    check("a mixed stream of alternating and simultaneous items comes out as the OR of each item's active sources",
          got == [(lat, 3), (4 + lat, 5), (8 + lat, 6 | 9), (12 + lat, 1)], str(got))

    print("NEGATIVE CONTROL: an UNGATED OR would fail the gating test (so the gating is doing real work)")
    dn = os.path.join(tmp, "g_ungated")
    shutil.copytree(d, dn)
    topf = os.path.join(dn, rec["top"] + ".v")
    txt = open(topf).read()
    raw = "(c_E1_v ? c_E1_d : 32'h0) | (c_E2_v ? c_E2_d : 32'h0)"
    check("the generated glue has the gated form I am about to strip", raw in txt)
    open(topf, "w").write(txt.replace(raw, "c_E1_d | c_E2_d"))
    got = rtl(dn, [(0, {"E1": 0x000000AA, "E2": 0x00005500}), (12, {"E1": 0x00000011})])
    check("ungated: the second result leaks the stale E2 value (0x5511, not 0x11)", len(got) == 2 and got[1] == (12 + lat, 0x5511), str(got))

    print("the two refusals have a definite reason")
    IcmV3File(name="c", records=merge_design(const_on_w=True)).save(os.path.join(tmp, "c.icm"))
    r = cli("-s", "sub", "--icm", os.path.join(tmp, "c.icm"), "--output", os.path.join(tmp, "gc"))
    check("a merge that includes a constant is refused (the always-valid constant would swamp the stream)",
          r.returncode != 0 and "constant" in r.stderr and "merge" in r.stderr, r.stderr.strip()[:240])
    IcmV3File(name="l", records=merge_design(extra_relay_on_n=True)).save(os.path.join(tmp, "l.icm"))
    r = cli("-s", "sub", "--icm", os.path.join(tmp, "l.icm"), "--output", os.path.join(tmp, "gl"))
    check("a merge of sources with different latencies is refused (output time would depend on which fired)",
          r.returncode != 0 and "different latencies" in r.stderr, r.stderr.strip()[:240])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
