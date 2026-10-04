#!/usr/bin/env python3
"""tests/test_flexsub_loops_v1.py -- loops on the sub family (Alan #939: "the loop and mask side").

Run: python3 tests/test_flexsub_loops_v1.py      (needs llvmlite + iverilog)
The LLVM frontend handles loops by UNROLLING them (#801-802): the trip count must be known at compile time, so a compiled loop is an ACYCLIC graph
and translates to sub like any other design. A genuine cycle in an ICM file is a hand-built ring (e.g. #638's bounded-loop ring) whose exit depends on
the data: variable latency, which fixed-latency wiring cannot align -- refused with that reason. Checked against plain arithmetic (the oracle):
counted loops with one and two carried values, a multiply-accumulate, a shift/xor recurrence; the compiler's refusal of a data-dependent exit; the
generator's refusal of a genuine cycle.
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
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    key = lambda cid: re.sub(r"[^A-Za-z0-9_]", "_", cid)  # noqa: E731
    vals = {key(c): v for c, v in port_values.items() if key(c) in ins}      # entries that only fed dead code were pruned from the design
    assert sorted(ins) == sorted(vals) and len(outs) == 1, (ins, list(vals), outs)
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins)
    drive = " ".join(f"d_{n} = 32'd{vals[n]}; v_{n} = 1;" for n in ins)
    clear = " ".join(f"v_{n} = 0; d_{n} = 0;" for n in ins)
    cycles = int(rec["settle_cycles"]) + 8 + 90
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
    repeat ({int(rec['settle_cycles']) + 3}) @(posedge clk); #1;
    for (c = 0; c < 90; c = c + 1) begin
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
    return [(int(a), int(d)) for a, v, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out) if v == "1"]


try:
    import llvmlite  # noqa: F401
except ImportError:
    print("SKIP: llvmlite not installed")
    sys.exit(0)
if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)
import flexsub_compile_v1 as fc  # noqa: E402


def loop(args, carried, body, cond_limit, ret):
    """LLVM text for a counted loop: `carried` = [(name, init, next_name)], body = instruction lines."""
    phis = "\n".join(f"  %{n} = phi i32 [ {i}, %entry ], [ %{nx}, %loop ]" for n, i, nx in carried)
    return (f"define i32 @f({', '.join('i32 %' + a for a in args)}) {{\nentry:\n  br label %loop\nloop:\n{phis}\n{body}\n"
            f"  %c = icmp slt i32 %i2, {cond_limit}\n  br i1 %c, label %loop, label %exit\nexit:\n  ret i32 %{ret}\n}}\n")


def fib(v):
    # `ret %a` in the exit block is the phi's value in the LAST executed iteration (7 iterations: i = 0..6) = a_6 -- NOT the value after the final
    # transition. (My first reference did 7 transitions and was wrong; the VM running the compiled ICM agrees with this one.)
    a, b = v["x"] & M, v["y"] & M
    last = a
    for _ in range(7):
        last = a
        a, b = b, (a + b) & M
    return last


def shiftxor(v):
    val = v["x"] & M
    for i in range(6):
        val = ((val << 1) & M) ^ i
    return val


PROGRAMS = [
    ("sum_0_to_4", ["x"], loop(["x"], [("i", 0, "i2"), ("acc", "%x", "acc2")], "  %acc2 = add i32 %acc, %i\n  %i2 = add i32 %i, 1", 5, "acc2"), lambda v: (v["x"] + 10) & M),
    ("mul_accumulate", ["x", "y"], loop(["x", "y"], [("i", 0, "i2"), ("acc", 0, "acc2")], "  %t = mul i32 %x, %y\n  %acc2 = add i32 %acc, %t\n  %i2 = add i32 %i, 1", 4, "acc2"),
     lambda v: (4 * v["x"] * v["y"]) & M),
    ("shift_xor_recurrence", ["x"], loop(["x"], [("i", 0, "i2"), ("v", "%x", "v2")], "  %s = shl i32 %v, 1\n  %v2 = xor i32 %s, %i\n  %i2 = add i32 %i, 1", 6, "v2"), shiftxor),
    ("two_carried_fibonacci", ["x", "y"], loop(["x", "y"], [("i", 0, "i2"), ("a", "%x", "b"), ("b", "%y", "bn")],
                                              "  %bn = add i32 %a, %b\n  %i2 = add i32 %i, 1", 7, "a"), fib),
]
tmp = tempfile.mkdtemp(prefix="loops_")
try:
    print("counted loops (unrolled by the frontend into acyclic graphs): generated sub RTL == plain arithmetic")
    rnd = random.Random(939)
    for name, args, src, ref in PROGRAMS:
        file, report, diags = fc.compile_for_flexsub(src, name)
        if file is None:
            check(f"{name}: compiles", False, str([d.message if hasattr(d, 'message') else str(d) for d in diags])[:240])
            continue
        icm = os.path.join(tmp, name + ".icm")
        file.save(icm)
        d = os.path.join(tmp, "g_" + name)
        r = cli("-s", "sub", "--icm", icm, "--output", d)
        if r.returncode:
            check(f"{name}: generates", False, r.stderr.strip()[:300])
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        lat = list(rec["output_latency_cycles"].values())[0]
        vecs = [dict(zip(args, t)) for t in ((0, 0), (1, 1), (7, 3), (0xFFFFFFFF, 2), (0x80000000, 0x7FFFFFFF), (123456789, 987654321))] + \
               [{a: rnd.getrandbits(32) for a in args} for _ in range(8)]
        bad = []
        for v in vecs:
            pv = {c: v[a] for a in args for c in report["arg_cells"][a]}
            hits = simulate(d, pv)
            if hits != [(lat, ref(v) & M)]:
                bad.append((v, hits[:2], ref(v) & M))
        acyclic = not re.search(r"cycle", r.stderr)
        check(f"{name}: {len(vecs)} vectors incl. 32-bit wrap; {rec['cells']} cells, latency {lat}", not bad and acyclic, str(bad[:2]))

    print("dead code is pruned and the REAL output is exported (found by the Fibonacci loop: the dead tail was exported instead)")
    src3 = loop(["x", "y"], [("i", 0, "i2"), ("a", "%x", "b"), ("b", "%y", "bn")], "  %bn = add i32 %a, %b\n  %i2 = add i32 %i, 1", 3, "a")
    file, report, _ = fc.compile_for_flexsub(src3, "fib3")
    icm = os.path.join(tmp, "fib3.icm")
    file.save(icm)
    d3 = os.path.join(tmp, "g_fib3")
    r = cli("-s", "sub", "--icm", icm, "--output", d3)
    rec3 = json.load(open(os.path.join(d3, "ASSEMBLY.json")))
    check("N=3: the returned value is just x + y, so iterations 1 and 2 are dead and pruned; the exit is the compiler's result cell main.bn__it0",
          r.returncode == 0 and rec3["pruned_dead_cells"] and list(rec3["output_latency_cycles"]) == ["main.bn__it0"], str((rec3.get("pruned_dead_cells"), rec3.get("output_latency_cycles"))))
    pv = {c: v for a, v in (("x", 7), ("y", 3)) for c in report["arg_cells"][a]}
    check("N=3 with x=7, y=3 returns 10 (= x + y), as the VM does", [v for _, v in simulate(d3, pv)] == [10], str(simulate(d3, pv)))

    print("refusals, each with its reason")
    dd = ("define i32 @f(i32 %x) {\nentry:\n  br label %loop\nloop:\n  %v = phi i32 [ %x, %entry ], [ %v2, %loop ]\n  %v2 = add i32 %v, 3\n"
          "  %c = icmp slt i32 %v2, 100\n  br i1 %c, label %loop, label %exit\nexit:\n  ret i32 %v2\n}\n")
    file, report, diags = fc.compile_for_flexsub(dd, "dd")
    check("a data-dependent loop exit is refused by the COMPILER (the trip count must be known at compile time)", file is None and diags, str(diags)[:200])
    # a genuine cycle in a hand-built ICM (a ram ring) is refused by the generator, with the variable-latency reason
    from icm_v3 import IcmV3File, IcmV3Record
    ring = [IcmV3Record(cell_id="A", row=1, col=1, core="ram", core_config={"upstream_mask": ["s"], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="B", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["s"]}),
            IcmV3Record(cell_id="C", row=2, col=2, core="ram", core_config={"upstream_mask": ["n"], "downstream_mask": ["w"]}),
            IcmV3Record(cell_id="D", row=2, col=1, core="ram", core_config={"upstream_mask": ["e"], "downstream_mask": ["n"]})]
    icm = os.path.join(tmp, "ring.icm")
    IcmV3File(name="ring", records=ring).save(icm)
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_ring"))
    check("a genuine 4-cell ring is refused by the generator, naming WHY (variable latency / collision) and what does translate",
          r.returncode != 0 and "cycle" in r.stderr and "UNROLLED" in r.stderr and "variable" in r.stderr, r.stderr.strip()[:300])
    # a MALFORMED ring: D (south of A) sends north into A's south face, but A listens only on its west face -> the edge would be silently dropped
    bad = [IcmV3Record(cell_id="A", row=1, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"]}),
           IcmV3Record(cell_id="B", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["s"]}),
           IcmV3Record(cell_id="C", row=2, col=2, core="ram", core_config={"upstream_mask": ["n"], "downstream_mask": ["w"]}),
           IcmV3Record(cell_id="D", row=2, col=1, core="ram", core_config={"upstream_mask": ["e"], "downstream_mask": ["n"]})]
    icm = os.path.join(tmp, "badring.icm")
    IcmV3File(name="badring", records=bad).save(icm)
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_badring"))
    check("a sender facing a neighbour that does not listen is refused (the VM would stall; wiring would silently drop it) -- it used to generate",
          r.returncode != 0 and "listens on no" in r.stderr and "stalls" in r.stderr, r.stderr.strip()[:300])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
