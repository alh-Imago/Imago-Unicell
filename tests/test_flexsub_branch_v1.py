#!/usr/bin/env python3
"""tests/test_flexsub_branch_v1.py -- the ICM `branch` lowered onto branch_cell_v4s (Alan #935: "complete the branch lowering").

Run: python3 tests/test_flexsub_branch_v1.py      (needs iverilog)
The ICM branch is a HELD-REFERENCE comparator (VM _deliver_branch): the first arrival on its one upstream face becomes the reference
and emits nothing; each later arrival is compared (signed) with it; the outcome picks value source / emit / route faces; with
rolling_mode the compared value becomes the new reference. Lowered as:
  const_ref -- fed by a merge of a constant and a stream (cordic's pattern): in1 = stream, in2 = the constant, the merge is removed;
  rolling   -- the stream feeds both inputs with in2 held (the first arrival finds nothing loaded -> it becomes the reference).
Checked against the REAL VM: the hand-built cordic z-convergence design (36 cells, 12 starting angles + the independent -404 anchor)
and hand-built branch designs; plus the refusals that carry a definite reason.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "nano/examples", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
CORDIC = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json")
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


def branch_rec(cid, r, c, up, routes, rolling=0, vsrc=(0, 0, 0), fixed=(0, 0, 0), emit=(1, 1, 1)):
    cfg = {"upstream_dir": {"n": 0, "s": 1, "e": 2, "w": 3}[up], "rolling_mode": rolling}     # ICM v3: a single direction CODE, not a mask
    for k, n in enumerate(("low", "equal", "high")):
        cfg[f"value_source_{n}"], cfg[f"fixed_value_{n}"], cfg[f"emit_{n}"], cfg[f"route_{n}"] = vsrc[k], fixed[k], emit[k], routes[k]
    return IcmV3Record(cell_id=cid, row=r, col=c, core="branch", core_config=cfg)


def ref_design(const_value, **bkw):
    """X --W--> M (merge) --> B ; constant Z --N--> M.  B routes low/equal -> O1 (south), high -> O2 (north)."""
    routes = bkw.pop("routes", (["s"], ["s"], ["n"]))
    return [ram("X", 2, 0, [], ["e"]), ram("Z", 1, 1, [], ["s"], preload_value=const_value & 0xFFFFFFFF),
            ram("M", 2, 1, ["n", "w"], ["e"]), branch_rec("B", 2, 2, "w", routes, **bkw),
            ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]


def rolling_design(**bkw):
    return [ram("X", 2, 1, [], ["e"]), branch_rec("B", 2, 2, "w", (["s"], ["s"], ["n"]), rolling=1, **bkw),
            ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]


def rtl(folder, events, cycles):
    """events: [(cycle, {entry port suffix: value})]. Returns {exit port suffix: [(cycle, value)]}."""
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


def vm_items(records, entry, items, ticks_per_item=14, settle=8):
    """Inject each item at `entry` one at a time (letting it propagate), after a settle for constants. Returns, per item,
    {exit cell id: value} for the exits that received a NEW value (exit rams are cleared between items, as a consumer would)."""
    grid = vm.SuperGrid(records)
    for _ in range(settle):
        grid.tick()
    er = next(r for r in records if r.cell_id == entry)
    exits = [r for r in records if r.core == "ram" and not (r.core_config or {}).get("downstream_mask")]
    out = []
    for v in items:
        grid.inject(er.row, er.col, v & 0xFFFFFFFF)
        for _ in range(ticks_per_item):
            grid.tick()
        got = {}
        for x in exits:
            cell = grid.cells[(x.row, x.col)]
            if cell.ram_data_valid:
                got[x.cell_id] = cell.ram_data_reg
                cell.ram_data_valid = False          # consumed
        out.append(got)
    return out


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="branch_")
try:
    print("CORDIC z-convergence: 36 cells (4 branches, merges, 12 constants, 8 adders) as generated sub Verilog vs the real VM")
    d = os.path.join(tmp, "cordic")
    r = cli("-s", "sub", "--icm", CORDIC, "--output", d)
    check("cordic generates on the sub family", r.returncode == 0, r.stderr.strip()[:300])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    check("4 branches lowered (all const_ref: three reading a graph stream, the first absorbing the merge that carried the z_input entry)",
          len(rec["branches"]) == 4 and all(b["mode"] == "const_ref" for b in rec["branches"].values())
          and rec["branches"]["s0.branch"].get("entry_io") == "z_input", str({k: v["mode"] for k, v in rec["branches"].items()}))
    from hierarchical_icm_prototype_loader import load_hierarchical, flatten
    records, _ = flatten(load_hierarchical(CORDIC))
    ic = next(x for x in records if x.io_name == "z_input")
    oc = next(x for x in records if x.io_name == "z_output")
    settle = (rec.get("settle_cycles") or 6) + 6

    def vm_z(z0):
        g = vm.SuperGrid(records)
        for _ in range(6):
            g.tick()
        g.inject(ic.row, ic.col, z0 & 0xFFFFFFFF)
        for _ in range(80):
            g.tick()
            o = g.cells[(oc.row, oc.col)]
            if o.ram_data_valid:
                return s32(o.ram_data_reg)
        return None
    anchor = s32(rtl(d, [(settle, {"z_input": 50000})], settle + 40)["z_output"][0][1])
    check("independent anchor: z0 = 50000 -> -404 (computed in Python in the repo's own harness, not from a simulation)", anchor == -404, str(anchor))
    bad = []
    for z0 in (50000, -50000, 0, 1, -1, 100, -100, 12345, -12345, 90000, -90000, 200000):
        hits = rtl(d, [(settle, {"z_input": z0 & 0xFFFFFFFF})], settle + 40)["z_output"]
        got = [(c - settle, s32(v)) for c, v in hits]
        want = vm_z(z0)
        if got != [(16, want)]:
            bad.append((z0, got, want))
    check("12 starting angles (both signs, 0, +-1, beyond convergence): generated RTL == the real VM, one pulse at the predicted cycle 16", not bad, str(bad[:2]))

    print("a hand-built branch: constant reference (merge of a constant and a stream, the cordic pattern) vs the real VM")
    for const_value in (0, 100, -50):
        recs = ref_design(const_value)
        icm = os.path.join(tmp, f"ref{const_value}.icm")
        IcmV3File(name="ref", records=recs).save(icm)
        dd = os.path.join(tmp, f"g_ref{const_value}")
        r = cli("-s", "sub", "--icm", icm, "--output", dd)
        ok = r.returncode == 0
        check(f"reference {const_value}: generates", ok, r.stderr.strip()[:300])
        if not ok:
            continue
        rr = json.load(open(os.path.join(dd, "ASSEMBLY.json")))
        vals = [const_value - 7, const_value, const_value + 1, const_value + 5000, -0x80000000, 0x7FFFFFFF]
        bad = []
        vmres = vm_items(recs, "X", vals)
        for v, vmr in zip(vals, vmres):
            hits = rtl(dd, [(rr["settle_cycles"] + 8, {"X": v & 0xFFFFFFFF})], rr["settle_cycles"] + 30)
            got = {n: s32(h[0][1]) for n, h in hits.items() if h}
            want = {k: s32(x) for k, x in vmr.items()}
            if got != want:
                bad.append((v, got, want))
        check(f"reference {const_value}: low/equal -> O1, high -> O2 for 6 values incl. the signed extremes: RTL == VM", not bad, str(bad[:2]))

    print("fixed emit value, and an outcome with emit disabled")
    recs = ref_design(10, vsrc=(1, 1, 1), fixed=(0x55, 0x55, 0x55), emit=(0, 1, 1))
    icm = os.path.join(tmp, "fx.icm")
    IcmV3File(name="fx", records=recs).save(icm)
    dd = os.path.join(tmp, "g_fx")
    r = cli("-s", "sub", "--icm", icm, "--output", dd)
    check("fixed-value / emit-disabled branch generates", r.returncode == 0, r.stderr.strip()[:300])
    rr = json.load(open(os.path.join(dd, "ASSEMBLY.json")))
    vals = [3, 10, 11, 1000]
    bad = []
    for v, vmr in zip(vals, vm_items(recs, "X", vals)):
        hits = rtl(dd, [(rr["settle_cycles"] + 8, {"X": v})], rr["settle_cycles"] + 30)
        got = {n: h[0][1] for n, h in hits.items() if h}
        if got != vmr:
            bad.append((v, got, vmr))
    check("value < ref emits NOTHING (emit_low = 0); == ref and > ref emit the fixed 0x55 on O1 / O2: RTL == VM", not bad, str(bad[:2]))

    print("rolling mode: each value is compared with the PREVIOUS one; the first only becomes the reference")
    recs = rolling_design()
    icm = os.path.join(tmp, "roll.icm")
    IcmV3File(name="roll", records=recs).save(icm)
    dd = os.path.join(tmp, "g_roll")
    r = cli("-s", "sub", "--icm", icm, "--output", dd)
    check("rolling branch generates", r.returncode == 0, r.stderr.strip()[:300])
    rr = json.load(open(os.path.join(dd, "ASSEMBLY.json")))
    check("planned as rolling (stream on both inputs, in2 held)", rr["branches"]["B"]["mode"] == "rolling")
    seq = [5, 9, 9, 3, 100, -4, -4, -9]
    vmseq = vm_items(recs, "X", seq)
    gap, base = 12, rr["settle_cycles"] + 8
    hits = rtl(dd, [(base + k * gap, {"X": v & 0xFFFFFFFF}) for k, v in enumerate(seq)], base + len(seq) * gap + 10)
    per_item = []
    for k in range(len(seq)):
        lo, hi = base + k * gap, base + (k + 1) * gap
        per_item.append({n: s32(v) for n, hs in hits.items() for c, v in hs if lo <= c < hi})
    want = [{k: s32(x) for k, x in m.items()} for m in vmseq]
    check("8 successive values: item 1 emits nothing; each later item is routed by its comparison with the previous: RTL == VM",
          per_item == want and per_item[0] == {}, f"rtl={per_item} vm={want}")

    print("refusals, each with a definite reason")
    # a plain stream into a non-rolling branch: the reference would be its FIRST ARRIVAL -> needs a 'first only' state bit
    plain = [ram("X", 2, 1, [], ["e"]), branch_rec("B", 2, 2, "w", (["s"], ["s"], ["n"])), ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]
    for label, recs, needle in (
            ("a non-rolling branch whose reference is the first arrival of a plain stream", plain, "FIRST ARRIVAL"),
            ("value sources that differ among the emitting outcomes", ref_design(0, vsrc=(0, 1, 0)), "value_source"),
            ("three routed faces", ref_design(0, routes=(["s"], ["n"], ["e"])), "distinct faces"),
            ("a routed face with no cell on it (two faces, S has a cell, E has none)", ref_design(0, routes=(["s"], ["s"], ["e"])), "no cell listens")):
        icm = os.path.join(tmp, "bad.icm")
        IcmV3File(name="bad", records=recs).save(icm)
        r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_bad"))
        check(f"refused: {label}", r.returncode != 0 and needle in r.stderr, r.stderr.strip()[:260])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
