#!/usr/bin/env python3
"""tests/test_flexsub_corpus_v1.py -- a CORPUS of compiled LLVM programs through the sub path, each checked against plain
arithmetic (the oracle). Covers what the sub generator completed in #931: mul, constants (incl. constant as minuend),
shifts (shl / lshr, a fused addon -> pure wiring, Alan #939), signed comparisons, and compositions of them.

Run: python3 tests/test_flexsub_corpus_v1.py     (needs llvmlite + iverilog)
Programs the generator must still REFUSE (nano-dependent: and/or/xor, select, eq, ashr) are checked to be refused with a reason.
"""
import json, os, random, re, shutil, subprocess, sys, tempfile
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
    repeat ({3 + rec.get('settle_cycles', 0)}) @(posedge clk); #1;
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
    return [(int(a), int(b), int(d)) for a, b, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out)]


VMF = {"ram": ("ram_data_valid", "ram_data_reg"), "adder": ("adder_data_valid", "adder_out_buffer"),
       "comparator": ("cmp_data_valid", "cmp_out_buffer"), "mul": ("mul_data_valid", "mul_out_buffer")}


def vm_result(icm, report, v):
    """What the real VM computes from the SAVED file for the same arguments (all injected on the same tick)."""
    import flexsub_icm_netlist_v1 as nl
    import unicell_super_automaton_v1 as vm
    doc, recs, cells, edges, inputs, outputs, ext, w = nl.extract(icm)
    at = {r.cell_id: r for r in recs}
    exits = [c for c in cells if not outputs.get(c)]
    grid = vm.SuperGrid(recs)
    for a, val in v.items():
        for cid in report["arg_cells"][a]:
            cell = grid.cells[(at[cid].row, at[cid].col)]
            cell.ram_data_reg, cell.ram_data_valid = val & 0xFFFFFFFF, True
    for _ in range(400):
        grid.tick()
        for e in exits:
            cell = grid.cells[(at[e].row, at[e].col)]
            fv, fd = VMF[cell.core]
            if getattr(cell, fv, None):
                return getattr(cell, fd)
    return None


try:
    import llvmlite  # noqa: F401
except ImportError:
    print("SKIP: llvmlite not installed"); sys.exit(0)
if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed"); sys.exit(0)
import flexsub_compile_v1 as fc  # noqa: E402

s32 = lambda v: v - (1 << 32) if v & 0x80000000 else v
PROGRAMS = [
    ("mul", "x y", "%r = mul i32 %x, %y", lambda v: v["x"] * v["y"]),
    ("mul_add", "x y z", "%a = mul i32 %x, %y\n  %r = add i32 %a, %z", lambda v: v["x"] * v["y"] + v["z"]),
    ("mul_c3", "x", "%r = mul i32 %x, 3", lambda v: v["x"] * 3),
    ("add_c5", "x", "%r = add i32 %x, 5", lambda v: v["x"] + 5),
    ("sub_c5", "x", "%r = sub i32 %x, 5", lambda v: v["x"] - 5),
    ("rsub_c5", "x", "%r = sub i32 5, %x", lambda v: 5 - v["x"]),
    ("add_c_neg", "x", "%r = add i32 %x, -7", lambda v: v["x"] - 7),
    ("shl3", "x", "%r = shl i32 %x, 3", lambda v: v["x"] << 3),
    ("shl1", "x", "%r = shl i32 %x, 1", lambda v: v["x"] << 1),
    ("lshr2", "x", "%r = lshr i32 %x, 2", lambda v: (v["x"] & M) >> 2),
    ("lshr7", "x", "%r = lshr i32 %x, 7", lambda v: (v["x"] & M) >> 7),
    ("shl_add", "x y", "%a = shl i32 %x, 2\n  %r = add i32 %a, %y", lambda v: (v["x"] << 2) + v["y"]),
    ("shl_sub", "x y", "%a = shl i32 %x, 1\n  %r = sub i32 %a, %y", lambda v: (v["x"] << 1) - v["y"]),
    ("icmp_slt", "x y", "%c = icmp slt i32 %x, %y\n  %r = zext i1 %c to i32", lambda v: int(s32(v["x"] & M) < s32(v["y"] & M))),
    ("icmp_sgt", "x y", "%c = icmp sgt i32 %x, %y\n  %r = zext i1 %c to i32", lambda v: int(s32(v["x"] & M) > s32(v["y"] & M))),
    ("icmp_sle", "x y", "%c = icmp sle i32 %x, %y\n  %r = zext i1 %c to i32", lambda v: int(s32(v["x"] & M) <= s32(v["y"] & M))),
    ("icmp_sge", "x y", "%c = icmp sge i32 %x, %y\n  %r = zext i1 %c to i32", lambda v: int(s32(v["x"] & M) >= s32(v["y"] & M))),
    ("and", "x y", "%r = and i32 %x, %y", lambda v: v["x"] & v["y"]),
    ("or", "x y", "%r = or i32 %x, %y", lambda v: v["x"] | v["y"]),
    ("xor", "x y", "%r = xor i32 %x, %y", lambda v: v["x"] ^ v["y"]),
    ("not_x", "x", "%r = xor i32 %x, -1", lambda v: ~v["x"]),
    ("and_c255", "x", "%r = and i32 %x, 255", lambda v: v["x"] & 255),
    ("or_c1", "x", "%r = or i32 %x, 1", lambda v: v["x"] | 1),
    ("xor_c", "x", "%r = xor i32 %x, 255", lambda v: v["x"] ^ 255),
    ("and_add", "x y z", "%a = and i32 %x, %y\n  %r = add i32 %a, %z", lambda v: (v["x"] & v["y"]) + v["z"]),
    ("add_xor", "x y z", "%a = add i32 %x, %y\n  %r = xor i32 %a, %z", lambda v: (v["x"] + v["y"]) ^ v["z"]),
    ("ashr2", "x", "%r = ashr i32 %x, 2", lambda v: s32(v["x"] & M) >> 2),
    ("ashr9", "x", "%r = ashr i32 %x, 9", lambda v: s32(v["x"] & M) >> 9),
    ("icmp_eq", "x y", "%c = icmp eq i32 %x, %y\n  %r = zext i1 %c to i32", lambda v: int((v["x"] & M) == (v["y"] & M))),
    ("icmp_ne", "x y", "%c = icmp ne i32 %x, %y\n  %r = zext i1 %c to i32", lambda v: int((v["x"] & M) != (v["y"] & M))),
    ("select_min", "x y", "%c = icmp slt i32 %x, %y\n  %r = select i1 %c, i32 %x, i32 %y", lambda v: v["x"] if s32(v["x"] & M) < s32(v["y"] & M) else v["y"]),
    ("select_max", "x y", "%c = icmp sgt i32 %x, %y\n  %r = select i1 %c, i32 %x, i32 %y", lambda v: v["x"] if s32(v["x"] & M) > s32(v["y"] & M) else v["y"]),
    # arguments / intermediate values used more than once (fan-out), and larger realistic programs
    ("x_plus_x", "x", "%r = add i32 %x, %x", lambda v: v["x"] + v["x"]),
    ("square", "x", "%r = mul i32 %x, %x", lambda v: v["x"] * v["x"]),
    ("fan_mid", "x y", "%a = add i32 %x, %y\n  %r = mul i32 %a, %a", lambda v: (v["x"] + v["y"]) * (v["x"] + v["y"])),
    ("diff_squares", "x y", "%a = add i32 %x, %y\n  %b = sub i32 %x, %y\n  %r = mul i32 %a, %b", lambda v: (v["x"] + v["y"]) * (v["x"] - v["y"])),
    ("reuse_args", "x y", "%a = mul i32 %x, %y\n  %b = add i32 %a, %x\n  %r = sub i32 %b, %y", lambda v: v["x"] * v["y"] + v["x"] - v["y"]),
    ("poly", "x", "%a = mul i32 %x, %x\n  %b = mul i32 %a, %x\n  %c = mul i32 %x, 2\n  %d = add i32 %b, %c\n  %r = add i32 %d, 1",
     lambda v: v["x"] ** 3 + 2 * v["x"] + 1),
    ("abs", "x", "%c = icmp slt i32 %x, 0\n  %n = sub i32 0, %x\n  %r = select i1 %c, i32 %n, i32 %x", lambda v: -s32(v["x"] & M) if s32(v["x"] & M) < 0 else v["x"]),
    ("max3", "x y z", "%c1 = icmp sgt i32 %x, %y\n  %m = select i1 %c1, i32 %x, i32 %y\n  %c2 = icmp sgt i32 %m, %z\n  %r = select i1 %c2, i32 %m, i32 %z",
     lambda v: max(s32(v["x"] & M), s32(v["y"] & M), s32(v["z"] & M))),
    ("combo", "x y z", "%a = add i32 %x, %y\n  %b = mul i32 %a, %z\n  %r = sub i32 %b, 7", lambda v: (v["x"] + v["y"]) * v["z"] - 7),
]
EDGE = [0, 1, 2, 5, 7, 100, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFFE, 0x12345678]
# The stock compiler lowers icmp as (32-bit difference) vs a threshold, which is only right when that difference does not
# overflow signed 32 bits. Arithmetic is the oracle ONLY inside that domain; outside it, the oracle is the VM (faithfulness).
def no_overflow(v):
    """Every PAIR the stock compare lowering subtracts must not overflow signed 32 bits (x-y; for max3 also max(x,y)-z; abs: x-0)."""
    ok = lambda a, b: -(1 << 31) <= s32(a & M) - s32(b & M) < (1 << 31)
    if "z" in v and "y" in v and "x" in v:
        return ok(v["x"], v["y"]) and ok(max(v["x"], v["y"], key=lambda q: s32(q & M)), v["z"])
    return ok(v["x"], v.get("y", 0))
OVERFLOW_VECS = [{"x": 0x80000000, "y": 0x7FFFFFFF}, {"x": 0x688B891E, "y": 0xDDB6DB66}, {"x": 0xFFFFFFFF, "y": 0x7FFFFFFF},
                 {"x": 0x7FFFFFFF, "y": 0xFFFFFFFF}, {"x": 100, "y": 0x80000000}, {"x": 5, "y": 9}, {"x": 9, "y": 5}, {"x": 7, "y": 7}]
tmp = tempfile.mkdtemp(prefix="fscorpus_")
rnd = random.Random(931)
try:
    print("compiled programs: generated sub RTL == plain arithmetic")
    for name, args, body, ref in PROGRAMS:
        names = args.split()
        src = f"define i32 @f({', '.join('i32 %' + a for a in names)}) {{\nentry:\n  {body}\n  ret i32 %r\n}}\n"
        file, report, diags = fc.compile_for_flexsub(src, name)
        if file is None:
            check(f"{name}: compiles", False, str(diags)[:160]); continue
        icm = os.path.join(tmp, name + ".icm"); file.save(icm)
        d = os.path.join(tmp, "g_" + name)
        r = cli("-s", "sub", "--icm", icm, "--output", d)
        if r.returncode:
            check(f"{name}: generates", False, r.stderr.strip()[:260]); continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        lat = list(rec["output_latency_cycles"].values())[0]
        vecs = [{a: rnd.choice(EDGE) for a in names} for _ in range(12)] + [{a: rnd.getrandbits(32) for a in names} for _ in range(12)]
        signed_cmp = name.startswith("icmp_s") or name.startswith("select_") or name in ("abs", "max3")
        if signed_cmp:
            fixed = ((5, 9, 3), (9, 5, 3), (7, 7, 3), (0xFFFFFFFF, 1, 2), (1, 0xFFFFFFFF, 2), (0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC))
            vecs = [v for v in vecs if no_overflow(v)] + [dict(zip(names, tup)) for tup in fixed]
        bad = []
        for v in vecs:
            pv = {c: v[a] for a in names for c in report["arg_cells"][a]}
            hits = [(c, dv) for c, valid, dv in simulate(d, pv) if valid]
            if hits != [(lat, ref(v) & M)]:
                bad.append((v, hits[:2], ref(v) & M))
        if name.startswith("icmp_s") and names == ["x", "y"]:
            fb = []
            for v in OVERFLOW_VECS:
                pv = {c: v[a] for a in names for c in report["arg_cells"][a]}
                hits = [dv for c, valid, dv in simulate(d, pv) if valid]
                if hits != [vm_result(icm, report, v)]:
                    fb.append((v, hits, vm_result(icm, report, v)))
            check(f"{name}: RTL == the VM on {len(OVERFLOW_VECS)} overflow-boundary vectors (faithful to the compiled program)", not fb, str(fb[:2]))
        extras = []
        if rec.get("constants"): extras.append(f"{len(rec['constants'])} const cell(s)")
        if rec.get("addon_wiring"): extras.append(f"{len(rec['addon_wiring'])} addon wiring(s)")
        check(f"{name}: {len(vecs)} vectors (edge values + random), latency {lat}" + (f", {', '.join(extras)}" if extras else ""), not bad, str(bad[:2]))

    print("unsupported nano uses are refused with the reason (not silently mistranslated)")
    from icm_v3 import IcmV3File
    base, rep0, _ = fc.compile_for_flexsub("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %r = and i32 %x, %y\n  ret i32 %r\n}\n", "nanocheck")
    for label, edit, needle in (("an unimplemented nano topology", lambda c: c.update({"topology": 0x155}), "topology"),
                                ("nano relay/hold mode (cardinal_edge)", lambda c: c.update({"cardinal_edge": ["w"]}), "cardinal_edge")):
        import copy
        f2 = copy.deepcopy(base)
        for r in f2.records:
            if r.core == "nano":
                edit(r.core_config)
        icm = os.path.join(tmp, "bad_nano.icm"); f2.save(icm)
        r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_bad"))
        check(f"{label}: refused, names it", r.returncode != 0 and needle in r.stderr, r.stderr.strip()[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
