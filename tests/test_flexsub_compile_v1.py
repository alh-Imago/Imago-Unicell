#!/usr/bin/env python3
"""tests/test_flexsub_compile_v1.py -- LLVM IR compiled for the sub/flex targets (#929, option C narrowed).

Run: python3 tests/test_flexsub_compile_v1.py     (needs llvmlite + iverilog)
Non-commutative programs are compiled with tools/flexsub_compile_v1.py (mode-2 priority -> strict mode 0 + ranks),
turned into sub Verilog by `-s sub --icm`, simulated, and compared with PLAIN ARITHMETIC. Includes the case that
separates rank from arrival: (x + y) - z, where operand A is the LATER arrival.
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
M = 0xFFFFFFFF
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


def simulate(folder, port_values):
    """port_values: {input cell id: value}. One 1-cycle valid pulse on every input at cycle 0.
    Returns [(cycle, valid, data)] of the single output."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    key = lambda cid: re.sub(r"[^A-Za-z0-9_]", "_", cid)
    vals = {key(c): v for c, v in port_values.items()}
    assert sorted(ins) == sorted(vals) and len(outs) == 1, (ins, list(vals), outs)
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins)
    drive = " ".join(f"d_{n} = 32'd{vals[n]}; v_{n} = 1;" for n in ins)
    clear = " ".join(f"v_{n} = 0; d_{n} = 0;" for n in ins)
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
    for (c = 0; c < 80; c = c + 1) begin
      {clear}
      if (c == 0) begin {drive} end
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
    return [(int(a), int(b), int(d)) for a, b, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out)]


try:
    import llvmlite  # noqa: F401
except ImportError:
    print("SKIP: llvmlite not installed")
    sys.exit(0)
if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)
import flexsub_compile_v1 as fc  # noqa: E402

PROGRAMS = [
    # name, args, body, reference
    ("sub_xy", "x y", "%r = sub i32 %x, %y", lambda v: v["x"] - v["y"]),
    ("sub_yx", "x y", "%r = sub i32 %y, %x", lambda v: v["y"] - v["x"]),
    ("sub_chain", "x y z", "%a = sub i32 %x, %y\n  %r = sub i32 %a, %z", lambda v: v["x"] - v["y"] - v["z"]),
    ("add_then_sub", "x y z", "%a = add i32 %x, %y\n  %r = sub i32 %a, %z", lambda v: v["x"] + v["y"] - v["z"]),     # A is the LATER arrival
    ("sub_of_add", "x y z", "%a = add i32 %y, %z\n  %r = sub i32 %x, %a", lambda v: v["x"] - (v["y"] + v["z"])),    # B is the later arrival
    ("sub_sub_sub", "x y z w", "%a = sub i32 %x, %y\n  %b = sub i32 %a, %z\n  %r = sub i32 %b, %w", lambda v: v["x"] - v["y"] - v["z"] - v["w"]),
]
tmp = tempfile.mkdtemp(prefix="fscomp_")
recs_by_name = {}
try:
    print("retarget unit checks")
    from icm_v3 import IcmV3File
    f, rep, _ = fc.compile_for_flexsub("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %r = sub i32 %x, %y\n  ret i32 %r\n}\n", "t")
    pri = [r for r in f.records if r.core == "priority"]
    check("x - y: the priority is strict mode 0 with DIFFERENT ranks (A=0, B=1)",
          len(pri) == 1 and pri[0].core_config["scheduling_mode"] == 0
          and sorted([pri[0].core_config["priority_rank_n"], pri[0].core_config["priority_rank_s"]]) == [0, 1], str(pri[0].core_config if pri else None))
    f2, rep2, _ = fc.compile_for_flexsub("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %r = add i32 %x, %y\n  ret i32 %r\n}\n", "t")
    check("x + y (commutative): nothing to retarget", rep2["retargeted"] == [])
    import copy
    try:
        fc.retarget_records(f.records, {"nope": (0, 1)})
        check("an unknown priority label is refused", False, "no error")
    except ValueError:
        check("an unknown priority label is refused", True)
    try:
        fc.retarget_records(f.records, {"a": (0, 1)})                # already mode 0
        check("a priority that is not in mode 2 is refused", False, "no error")
    except ValueError:
        check("a priority that is not in mode 2 is refused", True)

    print("compiled non-commutative programs: generated sub RTL == plain arithmetic")
    rnd = random.Random(929)
    for name, args, body, ref in PROGRAMS:
        names = args.split()
        src = f"define i32 @f({', '.join('i32 %' + a for a in names)}) {{\nentry:\n  {body}\n  ret i32 %r\n}}\n"
        icm = os.path.join(tmp, name + ".icm")
        file, report, diags = fc.compile_for_flexsub(src, name)
        if file is None:
            check(f"{name}: compiles", False, str(diags)[:200])
            continue
        file.save(icm)
        d = os.path.join(tmp, "g_" + name)
        r = cli("-s", "sub", "--icm", icm, "--output", d)
        if r.returncode:
            check(f"{name}: generates", False, r.stderr.strip()[:300])
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        recs_by_name[name] = rec
        lat = list(rec["output_latency_cycles"].values())[0]
        vecs = [dict(zip(names, (6, 7, 3, 1))), dict(zip(names, (100, 3, 2, 5))), dict(zip(names, (0, 0, 0, 0))),
                dict(zip(names, (5, 9, 4, 8)))] + [{a: rnd.getrandbits(32) for a in names} for _ in range(6)]
        bad = []
        for v in vecs:
            pv = {}
            for a in names:
                cells = report["arg_cells"][a]
                for c in cells:
                    pv[c] = v[a]
            hits = [(c, dv) for c, valid, dv in simulate(d, pv) if valid]
            if hits != [(lat, ref(v) & M)]:
                bad.append((v, hits[:3], ref(v) & M))
        ident = sorted({x["identity_by"] for x in rec["adder_roles"].values()})
        check(f"{name}: {len(vecs)} vectors incl. 32-bit wrap; operand identity by {ident}; latency {lat}", not bad, str(bad[:2]))

    print("rank really defines identity (not coincidence): add_then_sub has A as the LATER arrival")
    roles = recs_by_name["add_then_sub"]["adder_roles"]
    sub_role = [v for v in roles.values() if v["identity_by"] == "rank"][0]
    check("the subtraction's early operand is B (z), so it is padded and A (the composed x+y) is the later arrival",
          sub_role["pad_B"] > 0 and sub_role["pad_A"] == 0, str(sub_role))
    src = "define i32 @f(i32 %x, i32 %y, i32 %z) {\nentry:\n  %a = add i32 %x, %y\n  %r = sub i32 %a, %z\n  ret i32 %r\n}\n"
    file, report, _ = fc.compile_for_flexsub(src, "ctl")
    for r in file.records:                       # NEGATIVE CONTROL: erase the identity the ranks carry
        if r.core == "priority":
            for dch in "nsew":
                r.core_config[f"priority_rank_{dch}"] = 0
    icm = os.path.join(tmp, "ctl.icm")
    file.save(icm)
    dc = os.path.join(tmp, "g_ctl")
    check("control file generates", cli("-s", "sub", "--icm", icm, "--output", dc).returncode == 0)
    v = {"x": 100, "y": 20, "z": 3}
    pv = {c: v[a] for a in v for c in report["arg_cells"][a]}
    got = [(c, dv) for c, valid, dv in simulate(dc, pv) if valid]
    right, flipped = (v["x"] + v["y"] - v["z"]) & M, (v["z"] - v["x"] - v["y"]) & M
    check("NEGATIVE CONTROL: with the ranks erased the operands come out swapped (z-(x+y)), not (x+y)-z",
          len(got) == 1 and got[0][1] == flipped and got[0][1] != right, f"got {got}, right {right}, flipped {flipped}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
