#!/usr/bin/env python3
"""tests/test_flexsub_flex_v1.py -- the FLEX family `--icm` emitter, STAGE 1 (ram, adder, mul).

Run: python3 tests/test_flexsub_flex_v1.py      (needs llvmlite + iverilog)
Alan: "the flex side ... hopefully slightly easier as it has the ack side." The flex cells are valid/ready cells (capture when valid_in and not pending; offer held
until ack_in), so a design needs NO latency alignment: fan-out is an EAGER FORK (a `taken` flop per consumer), a two-operand cell is a JOIN. What this checks, and
why it is the right test for a handshake design: STREAMS of items pushed through random INPUT GAPS and random OUTPUT STALLS (and a heavy-stall mode), asserting
nothing is lost, nothing is duplicated and ORDER is kept -- results compared with plain arithmetic -- plus a DIAMOND (two sources each feeding two adders, the
combinational-loop trap), the shipped relay chain and reduction tree (also against the real VM), and the stage-1 refusals.
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
import unicell_super_automaton_v1 as vm  # noqa: E402
import flexsub_icm_netlist_v1 as nl  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples")
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


def run_stream(folder, streams, mode="plain", seed=1, cycles=6000):
    """streams: {entry port suffix: [values]} (equal length N). mode: plain (always ready, no gaps) | stall (random output stalls + random input gaps) |
    slow (output ready only 1 cycle in 8) | skewfirst / skewlast (the first / last INPUT is slow, forcing one operand order: for a nano, B-before-A or A-before-B). Returns {exit suffix: [values captured in order]}."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    assert sorted(ins) == sorted(streams), (ins, list(streams))
    n = len(next(iter(streams.values())))
    decl, drv, cap, conn = [], [], [], []
    for k, name in enumerate(ins):
        vals = streams[name]
        decl.append(f"  reg [31:0] mem_{name} [0:{n}];\n  integer idx_{name} = 0; reg act_{name} = 0;\n  wire ack_{name};\n"
                    f"  wire [31:0] d_{name} = (idx_{name} < {n}) ? mem_{name}[idx_{name}] : 32'h0;")
        decl.append("  initial begin " + " ".join(f"mem_{name}[{j}] = 32'd{v};" for j, v in enumerate(vals)) + " end")
        slow3 = f"(lfsr[{(3 * k + 2) % 31}] & lfsr[{(5 * k + 7) % 31}] & lfsr[{(2 * k + 13) % 31}])"
        gap = (f"(lfsr[{(3 * k + 2) % 31}] | lfsr[{(5 * k + 7) % 31}])" if mode == "stall" else
               slow3 if (mode == "skewfirst" and k == 0) or (mode == "skewlast" and k == len(ins) - 1) else "(1'b1)")
        drv.append(f"      if (act_{name} && ack_{name}) begin idx_{name} <= idx_{name} + 1; act_{name} <= 1'b0; end\n"
                   f"      else if (!act_{name} && idx_{name} < {n} && {gap}) act_{name} <= 1'b1;")
        conn.append(f".in_{name}_data(d_{name}), .in_{name}_valid(act_{name}), .in_{name}_ack(ack_{name})")
    for k, name in enumerate(outs):
        ready = {"plain": "1'b1", "skewfirst": "1'b1", "skewlast": "1'b1", "stall": f"lfsr[{(7 * k + 11) % 31}]", "slow": f"(lfsr[{(7 * k + 11) % 31}] & lfsr[{(7 * k + 12) % 31}] & lfsr[{(7 * k + 13) % 31}])"}[mode]
        decl.append(f"  wire [31:0] od_{name}; wire ov_{name}; wire oa_{name} = {ready};\n  integer cnt_{name} = 0;")
        cap.append(f"      if (ov_{name} && oa_{name} && cnt_{name} < {n}) begin $display(\"GOT {name} %0d %0d\", cnt_{name}, od_{name}); cnt_{name} <= cnt_{name} + 1; end")
        conn.append(f".out_{name}_data(od_{name}), .out_{name}_valid(ov_{name}), .out_{name}_ack(oa_{name})")
    done = " && ".join(f"cnt_{o} >= {n}" for o in outs)
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0;
  reg [31:0] lfsr = 32'h{(0xACE1 ^ (seed * 0x9E3779B1)) & 0xFFFFFFFF or 1:08X};
{chr(10).join(decl)}
  {top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {', '.join(conn)});
  always #5 clk = ~clk;
  integer cyc = 0; reg started = 0;
  always @(posedge clk) begin
    lfsr <= {{lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]}};
    if (started) begin
      cyc <= cyc + 1;
{chr(10).join(drv)}
{chr(10).join(cap)}
      if ({done} || cyc > {cycles}) begin $display("DONE %0d", cyc); $finish; end
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
    res = {o: [] for o in outs}
    for o, i, v in re.findall(r"GOT (\w+) (\d+) (\d+)", out):
        res[o].append(int(v))
    done = re.search(r"DONE (\d+)", out)
    return res, int(done.group(1)) if done else None


def build(tmp, name, path):
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", path, "--output", d)


try:
    import llvmlite  # noqa: F401
except ImportError:
    print("SKIP: llvmlite not installed")
    sys.exit(0)
if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)
import flexsub_compile_v1 as fc  # noqa: E402

rnd = random.Random(944)
EDGE = [0, 1, M, 0x80000000, 0x7FFFFFFF, 2, 3, 12345, 0xDEADBEEF, 7]


def items(n):
    return [EDGE[k % len(EDGE)] if k < len(EDGE) else rnd.getrandbits(32) for k in range(n)]


tmp = tempfile.mkdtemp(prefix="flex_")
try:
    print("the shipped relay chain (8 ram cells): a stream through gaps and stalls loses nothing and keeps order")
    d, r = build(tmp, "relay", os.path.join(EX, "small_relay_chain.icm-hier.json"))
    check("generates on flex", r.returncode == 0, r.stderr.strip()[:200])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    ent = re.findall(r"in_(\w+)_data", open(os.path.join(d, rec["top"] + ".v")).read())[0]
    vals = items(24)
    for mode, seed in (("plain", 1), ("stall", 2), ("stall", 3), ("slow", 4)):
        res, cyc = run_stream(d, {ent: vals}, mode, seed)
        got = list(res.values())[0]
        check(f"24 items, mode={mode} seed={seed}: all out, in order, none lost or duplicated ({cyc} cycles)", got == vals, f"got {len(got)}: {got[:4]}")

    print("the shipped parallel reduction tree (4 inputs, 3 joins): streams == per-item sums, and one item == the real VM")
    path = os.path.join(EX, "parallel_reduction_tree.icm-hier.json")
    d, r = build(tmp, "tree", path)
    check("generates on flex (3 joins, no forks)", r.returncode == 0 and len(json.load(open(os.path.join(d, "ASSEMBLY.json")))["joins"]) == 3, r.stderr.strip()[:200])
    names = sorted(set(re.findall(r"in_(\w+)_data", open(os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")).read())))   # a SET: each port is mentioned several times
    n = 20
    streams = {nm: [rnd.getrandbits(32) for _ in range(n)] for nm in names}
    want = [sum(streams[nm][k] for nm in names) & M for k in range(n)]
    for mode, seed in (("plain", 5), ("stall", 6), ("slow", 7)):
        res, cyc = run_stream(d, streams, mode, seed)
        check(f"20 items x 4 inputs, mode={mode}: each output is the sum of its own four inputs, in order ({cyc} cycles)", list(res.values())[0] == want, f"got {list(res.values())[0][:3]} want {want[:3]}")
    one = {nm: [k + 1] for k, nm in enumerate(sorted(names))}
    res, _ = run_stream(d, one, "plain", 1)
    doc, recs, cells, edges, inputs, outputs, ext, w = nl.extract(path)
    grid = vm.SuperGrid(recs)
    byname = {r_.io_name: r_ for r_ in recs if r_.io_name}
    for k in range(4):
        grid.inject(byname[f"input_{k}"].row, byname[f"input_{k}"].col, k + 1)
    for _ in range(80):
        grid.tick()
    oc = byname["output"]
    check(f"one item (1,2,3,4): flex RTL {list(res.values())[0]} == the real VM {grid.cells[(oc.row, oc.col)].adder_out_buffer} == 10",
          list(res.values())[0] == [10] and grid.cells[(oc.row, oc.col)].adder_out_buffer == 10)

    print("compiled programs with FAN-OUT and operand joins (incl. a DIAMOND), streams through gaps and stalls vs plain arithmetic")
    progs = [
        ("add", "x y", "%r = add i32 %x, %y", lambda v: v["x"] + v["y"]),
        ("sub", "x y", "%r = sub i32 %x, %y", lambda v: v["x"] - v["y"]),
        ("square_fanout_same_source", "x", "%r = mul i32 %x, %x", lambda v: v["x"] * v["x"]),
        ("mul_add", "x y z", "%a = mul i32 %x, %y\n  %r = add i32 %a, %z", lambda v: v["x"] * v["y"] + v["z"]),
        ("diff_of_squares_(separate injection cells: joins, NO fork)", "x y", "%s = add i32 %x, %y\n  %d = sub i32 %x, %y\n  %r = mul i32 %s, %d", lambda v: (v["x"] + v["y"]) * (v["x"] - v["y"])),
        ("TRUE_DIAMOND", "x y", "%a = add i32 %x, %y\n  %b = sub i32 %x, %y\n  %s = add i32 %a, %b\n  %d = sub i32 %a, %b\n  %r = mul i32 %s, %d",
         lambda v: ((v["x"] + v["y"]) + (v["x"] - v["y"])) * ((v["x"] + v["y"]) - (v["x"] - v["y"]))),
        ("fanout_three", "x y", "%a = add i32 %x, %y\n  %b = mul i32 %a, %x\n  %c = sub i32 %b, %a\n  %r = add i32 %c, %x", lambda v: ((v["x"] + v["y"]) * v["x"] - (v["x"] + v["y"])) + v["x"]),
    ]
    for name, args, body, ref in progs:
        a_list = args.split()
        src = f"define i32 @f({', '.join('i32 %' + a for a in a_list)}) {{\nentry:\n  {body}\n  ret i32 %r\n}}\n"
        file, report, diags = fc.compile_for_flexsub(src, name)
        if file is None:
            check(f"{name}: compiles", False, str(diags)[:200])
            continue
        icm = os.path.join(tmp, name + ".icm")
        file.save(icm)
        d, r = build(tmp, name, icm)
        if r.returncode:
            check(f"{name}: generates on flex", False, r.stderr.strip()[:300])
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        n = 16
        vals = {a: items(n) if k == 0 else [rnd.getrandbits(32) for _ in range(n)] for k, a in enumerate(a_list)}
        streams = {}
        for a in a_list:
            for c in report["arg_cells"][a]:
                key = re.sub(r"[^A-Za-z0-9_]", "_", c)
                if key in re.findall(r"in_(\w+)_data", open(os.path.join(d, rec["top"] + ".v")).read()):
                    streams[key] = vals[a]
        want = [ref({a: vals[a][k] for a in a_list}) & M for k in range(n)]
        bad = []
        for mode, seed in (("plain", 11), ("stall", 12), ("stall", 13), ("slow", 14)):
            res, cyc = run_stream(d, streams, mode, seed)
            got = list(res.values())[0]
            if got != want:
                bad.append((mode, seed, len(got), got[:3], want[:3]))
        check(f"{name}: forks {len(rec['forks'])}, joins {len(rec['joins'])}; 16 items x 4 modes (plain, 2 stalls, slow): all correct, in order, none lost", not bad, str(bad[:1]))
        if name == "TRUE_DIAMOND":
            check("TRUE_DIAMOND really has a diamond: a and b each fan out to two joins (2 forks, 5 joins)", len(rec["forks"]) == 2 and len(rec["joins"]) == 5, str((rec["forks"], rec["joins"])))
            diamond = (d, rec, streams, want)

    print("CONSTANTS (stage 2): a constant is a fixed-mode ram (always valid, always ready, never used up) -- no fork, no ack")
    import ast
    csrc = open(os.path.join(ROOT, "tests", "test_flexsub_corpus_v1.py")).read()
    node = next(n_ for n_ in ast.parse(csrc).body if isinstance(n_, ast.Assign) and getattr(n_.targets[0], "id", "") == "PROGRAMS")
    cns = {"M": M}
    s32node = next(n_ for n_ in ast.parse(csrc).body if isinstance(n_, ast.Assign) and getattr(n_.targets[0], "id", "") == "s32")   # the reference lambdas call it
    exec(ast.get_source_segment(csrc, s32node), cns)
    exec(ast.get_source_segment(csrc, node), cns)
    for nm in ("VMF", "EDGE", "OVERFLOW_VECS", "no_overflow", "vm_result"):          # the corpus's own rules for compare-based programs
        nd = next(n_ for n_ in ast.parse(csrc).body if (isinstance(n_, ast.Assign) and getattr(n_.targets[0], "id", "") == nm) or (isinstance(n_, ast.FunctionDef) and n_.name == nm))
        exec(ast.get_source_segment(csrc, nd), cns)
    no_overflow, vm_result, OVERFLOW_VECS = cns["no_overflow"], cns["vm_result"], cns["OVERFLOW_VECS"]
    CORPUS = cns["PROGRAMS"]
    accepted, refused, bad_programs, with_const, overflow_checked = [], [], [], [], []
    for name, args, body, ref in CORPUS:
        a_list = args.split()
        src = f"define i32 @f({', '.join('i32 %' + a for a in a_list)}) {{\nentry:\n  {body}\n  ret i32 %r\n}}\n"
        file, report, diags = fc.compile_for_flexsub(src, name)
        if file is None:
            continue
        icm = os.path.join(tmp, "c_" + name + ".icm")
        file.save(icm)
        d, r = build(tmp, "c_" + name, icm)
        if r.returncode:
            refused.append((name, "not yet translated on flex" in r.stderr))
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        top_text = open(os.path.join(d, rec["top"] + ".v")).read()
        ports = set(re.findall(r"in_(\w+)_data", top_text))
        n = 12
        signed_cmp = name.startswith("icmp_s") or name.startswith("select_") or name in ("abs", "max3")
        if signed_cmp:
            fixed = ((5, 9, 3), (9, 5, 3), (7, 7, 3), (0xFFFFFFFF, 1, 2), (1, 0xFFFFFFFF, 2), (0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC))
            cand = [{a: rnd.choice(cns["EDGE"]) for a in a_list} for _ in range(60)] + [{a: rnd.getrandbits(32) for a in a_list} for _ in range(60)]
            vecs = [v for v in cand if no_overflow(v)][:n - len(fixed)] + [dict(zip(a_list, tup)) for tup in fixed]
            vals = {a: [v[a] for v in vecs] for a in a_list}
        else:
            vals = {a: items(n) if k == 0 else [rnd.getrandbits(32) for _ in range(n)] for k, a in enumerate(a_list)}
        streams = {re.sub(r"[^A-Za-z0-9_]", "_", c): vals[a] for a in a_list for c in report["arg_cells"][a] if re.sub(r"[^A-Za-z0-9_]", "_", c) in ports}
        want = [ref({a: vals[a][k] for a in a_list}) & M for k in range(n)]
        ok = True
        if name.startswith("icmp_s") and a_list == ["x", "y"]:                  # outside the arithmetic domain the oracle is the VM: faithful to the compiled program
            fb = []
            for v in OVERFLOW_VECS:
                res1, _ = run_stream(d, {k_: [v[a_] for a_ in a_list for c_ in report["arg_cells"][a_] if re.sub(r"[^A-Za-z0-9_]", "_", c_) == k_][0:1] for k_ in streams}, "plain", 5, cycles=1500)
                if list(res1.values())[0] != [vm_result(icm, report, v)]:
                    fb.append((v, list(res1.values())[0], vm_result(icm, report, v)))
            overflow_checked.append((name, len(OVERFLOW_VECS), not fb))
            ok = ok and not fb
        for mode, seed in (("plain", 21), ("stall", 22), ("slow", 23)):
            res, _ = run_stream(d, streams, mode, seed)
            ok = ok and list(res.values())[0] == want
        accepted.append(name)
        if rec["constants"]:
            with_const.append(name)
        if not ok:
            bad_programs.append(name)
    check(f"corpus programs flex accepts: {len(accepted)} of {len(CORPUS)}, each 12 items x 3 modes (plain, stall, slow) == plain arithmetic ({len(with_const)} of them use constants)",
          accepted and not bad_programs and len(with_const) >= 6, f"wrong: {bad_programs}; accepted {accepted}")
    check(f"every corpus program flex does not accept is REFUSED with a flex reason ({len(refused)}: {sorted(n_ for n_, _ in refused)}), none silently dropped",
          all(flag for _, flag in refused), str([n_ for n_, flag in refused if not flag]))
    check(f"the signed-compare programs (icmp_slt/sgt/sle/sge) are also faithful to the VM on the 8 overflow-boundary vectors where arithmetic is NOT the oracle: {overflow_checked}",
          len(overflow_checked) >= 3 and all(o for _, _, o in overflow_checked), str(overflow_checked))
    check("the corpus programs that were blocked by nano ALONE are now accepted (and, and_add, and_c255, ashr2, add_xor)",
          {"and", "and_add", "and_c255", "ashr2", "add_xor"} <= set(accepted), str(sorted(set(["and", "and_add", "and_c255", "ashr2", "add_xor"]) - set(accepted))))
    check("constants really are in play: the accepted set includes x+5, x-5, 5-x, x*3 and a negative constant",
          {"add_c5", "sub_c5", "rsub_c5", "mul_c3", "add_c_neg"} <= set(with_const), str(sorted(with_const)))

    # one constant feeding TWO consumers (no fork, no ack): K -> ADD1 and ADD2, each also fed by its own stream
    def rr(cid, r_, c_, up, dn, **kw):
        return IcmV3Record(cell_id=cid, row=r_, col=c_, core="ram", core_config={"upstream_mask": up, "downstream_mask": dn}, **kw)
    two = [rr("K", 1, 3, [], ["n", "s"], preload_value=7), rr("X1", 0, 1, [], ["e"]), rr("R1", 0, 2, ["w"], ["e"]),
           IcmV3Record(cell_id="A1", row=0, col=3, core="adder", core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"]}), rr("E1", 0, 4, ["w"], []),
           rr("X2", 2, 1, [], ["e"]), rr("R2", 2, 2, ["w"], ["e"]),
           IcmV3Record(cell_id="A2", row=2, col=3, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}), rr("E2", 2, 4, ["w"], [])]
    IcmV3File(name="two", records=two).save(os.path.join(tmp, "two.icm"))
    d2, r2 = build(tmp, "two_consumers", os.path.join(tmp, "two.icm"))
    check("one constant feeding two adders generates with NO fork (a constant is never used up)", r2.returncode == 0 and json.load(open(os.path.join(d2, "ASSEMBLY.json")))["forks"] == [], r2.stderr.strip()[:200])
    if r2.returncode == 0:
        sx = {"X1": items(14), "X2": [rnd.getrandbits(32) for _ in range(14)]}
        wx = {"E1": [(v + 7) & M for v in sx["X1"]], "E2": [(v + 7) & M for v in sx["X2"]]}
        bad = []
        for mode, seed in (("plain", 31), ("stall", 32), ("slow", 33)):
            res, _ = run_stream(d2, sx, mode, seed)
            if res != wx:
                bad.append((mode, {k: v[:2] for k, v in res.items()}))
        check("both consumers get the constant on every item: E1 = X1 + 7, E2 = X2 + 7, 14 items x 3 modes", not bad, str(bad[:1]))
        top2 = os.path.join(d2, json.load(open(os.path.join(d2, "ASSEMBLY.json")))["top"] + ".v")
        orig2 = open(top2).read()
        for mi, (label, pat, rep) in enumerate((("the constant is made FLOWING (nothing is ever offered): the design must not produce results", r"\.cfg_fixed_mode\(1'b1\)", ".cfg_fixed_mode(1'b0)"),
                                ("the constant's VALUE is zeroed: wrong results", r"\.cfg_data\(32'h00000007\)", ".cfg_data(32'h00000000)"))):
            txt = re.sub(pat, rep, orig2)
            assert txt != orig2, pat
            dm = os.path.join(tmp, f"mutc_{mi}")
            shutil.copytree(d2, dm)
            open(os.path.join(dm, os.path.basename(top2)), "w").write(txt)
            res, _ = run_stream(dm, sx, "plain", 41, cycles=800)
            check(f"mutant caught: {label}", res != wx, str({k: v[:2] for k, v in res.items()}))

    # a constant with an addon (5 shifted left 2 = 20) added to a stream: flex stream vs the real VM, one call per VM grid (the VM's constant is single-shot)
    sh = [rr("K", 0, 1, [], ["s"], addon_config={"shift_en": 1, "direction": 0, "shift_amt": 2}, preload_value=5),
          rr("X", 2, 0, [], ["n"]), rr("Rx", 1, 0, ["s"], ["e"]),
          IcmV3Record(cell_id="ADD", row=1, col=1, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}), rr("E", 1, 2, ["w"], [])]
    IcmV3File(name="sh", records=sh).save(os.path.join(tmp, "sh.icm"))
    d3, r3 = build(tmp, "const_shift", os.path.join(tmp, "sh.icm"))
    check("a constant source with an addon generates on flex", r3.returncode == 0, r3.stderr.strip()[:200])
    if r3.returncode == 0:
        xs = items(14)
        res, _ = run_stream(d3, {"X": xs}, "stall", 51)
        vmv = []
        for x in xs[:6]:
            g_ = vm.SuperGrid(sh)
            for _ in range(8):
                g_.tick()
            g_.inject(2, 0, x)
            for _ in range(40):
                g_.tick()
            vmv.append(g_.cells[(1, 2)].ram_data_reg if g_.cells[(1, 2)].ram_data_valid else None)
        check(f"constant 5 << 2 = 20 plus a stream: flex stream == X + 20 for 14 items; the first 6 also == the real VM (a fresh grid per item)",
              list(res.values())[0] == [(x + 20) & M for x in xs] and vmv == [(x + 20) & M for x in xs[:6]], f"flex={list(res.values())[0][:3]} vm={vmv[:3]}")

    print("NANO (stage 3): a HELD operand A that is only a load strobe + a FLOWING operand B on valid/ready; one `aload` flag per nano")
    nprogs = [
        ("and", "x y", "%r = and i32 %x, %y", lambda v: v["x"] & v["y"]),
        ("or", "x y", "%r = or i32 %x, %y", lambda v: v["x"] | v["y"]),
        ("xor", "x y", "%r = xor i32 %x, %y", lambda v: v["x"] ^ v["y"]),
        ("and_c255_(constant operand)", "x", "%r = and i32 %x, 255", lambda v: v["x"] & 255),
        ("xor_then_and_then_or", "x y z", "%a = xor i32 %x, %y\n  %b = and i32 %a, %z\n  %r = or i32 %b, %x", lambda v: ((v["x"] ^ v["y"]) & v["z"]) | v["x"]),
        ("FORK_into_a_nano", "x y", "%a = add i32 %x, %y\n  %b = xor i32 %a, %x\n  %r = and i32 %a, %b", lambda v: (v["x"] + v["y"]) & ((v["x"] + v["y"]) ^ v["x"])),
        ("add_then_xor", "x y z", "%a = add i32 %x, %y\n  %r = xor i32 %a, %z", lambda v: (v["x"] + v["y"]) ^ v["z"]),
    ]
    nano_dir = None
    for name, args, body, ref in nprogs:
        a_list = args.split()
        src = f"define i32 @f({', '.join('i32 %' + a for a in a_list)}) {{\nentry:\n  {body}\n  ret i32 %r\n}}\n"
        file, report, diags = fc.compile_for_flexsub(src, name)
        if file is None:
            check(f"{name}: compiles", False, str(diags)[:200])
            continue
        icm = os.path.join(tmp, "n_" + re.sub(r"\W+", "_", name) + ".icm")
        file.save(icm)
        d, r = build(tmp, "n_" + re.sub(r"\W+", "_", name), icm)
        if r.returncode:
            check(f"{name}: generates on flex", False, r.stderr.strip()[:300])
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        n = 16
        vals = {a: items(n) if k == 0 else [rnd.getrandbits(32) for _ in range(n)] for k, a in enumerate(a_list)}
        ports = set(re.findall(r"in_(\w+)_data", open(os.path.join(d, rec["top"] + ".v")).read()))
        streams = {re.sub(r"[^A-Za-z0-9_]", "_", c): vals[a] for a in a_list for c in report["arg_cells"][a] if re.sub(r"[^A-Za-z0-9_]", "_", c) in ports}
        want = [ref({a: vals[a][k] for a in a_list}) & M for k in range(n)]
        bad = []
        for mode, seed in (("plain", 61), ("stall", 62), ("stall", 63), ("slow", 64), ("skewfirst", 65), ("skewlast", 66)):
            res, cyc = run_stream(d, streams, mode, seed, cycles=9000)
            if list(res.values())[0] != want:
                bad.append((mode, seed, list(res.values())[0][:3], want[:3]))
        nn = sum(1 for j in rec["joins"] if j.get("kind") == "nano hold/flow")
        check(f"{name}: {nn} nano, forks {len(rec['forks'])}; 16 items x 6 modes (plain, 2 stalls, slow, B-before-A, A-before-B): all correct, in order", not bad and nn >= 1, str(bad[:1]))
        if name == "and":
            nano_dir = (d, rec, streams, want)
        if name == "FORK_into_a_nano":
            check("a real FORK feeds a nano (the source is released only after the hold load AND the flow capture, which happen at different times)", len(rec["forks"]) >= 1, str(rec["forks"]))

    print("   MUTATION CONTROLS on the nano glue: break the `aload` logic; the order-forcing modes must catch each one")
    dn, recn, streamsn, wantn = nano_dir
    topn = os.path.join(dn, recn["top"] + ".v")
    orign = open(topn).read()
    for mi, (label, pat, rep) in enumerate((
            ("B is captured WITHOUT waiting for A to be loaded (a stale hold is read)", r"(assign c_\w+_vin) = (e\d+_v) & c_\w+_aload;", r"\g<1> = \g<2>;"),
            ("A is re-loaded even when it is already loaded (the hold is overwritten before B)", r"(wire c_\w+_ldA = e\d+_v) & ~c_\w+_aload & (c_\w+_armed;)", r"\g<1> & \g<2>"),
            ("the capture never clears `aload` (the hold is never re-armed for the next pair)", r"else if \(c_\w+_cap\) c_\w+_aload <= 1'b0; ", ""))):
        txt = re.sub(pat, rep, orign)
        assert txt != orign, pat
        dm = os.path.join(tmp, f"mutn_{mi}")
        shutil.copytree(dn, dm)
        open(os.path.join(dm, recn["top"] + ".v"), "w").write(txt)
        verdicts = []
        for mode, seed in (("plain", 71), ("stall", 72), ("skewfirst", 73), ("skewlast", 74)):
            try:
                res, _ = run_stream(dm, streamsn, mode, seed, cycles=2500)
                verdicts.append(list(res.values())[0] == wantn)
            except Exception:
                verdicts.append(False)
        check(f"mutant caught: {label}", not all(verdicts), f"verdicts {verdicts}")

    print("COMPARATOR (stage 4): signed(data) >= threshold -> 0/1, a single-input cell -- a hand-built relay -> comparator -> exit at several thresholds vs the real VM")
    s32 = lambda v: v - (1 << 32) if v & 0x80000000 else v   # noqa: E731
    probe = [0x80000000, 0xFFFFFFF0, 0xFFFFFFFA, 0xFFFFFFFB, 0xFFFFFFFC, 0xFFFFFFFF, 0, 1, 4, 5, 6, 0x7FFFFFFF]
    cmp_dirs = {}
    for thr in (0, 5, 0xFFFFFFFB):
        crecs = [IcmV3Record(cell_id="X", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
                 IcmV3Record(cell_id="C", row=1, col=1, core="comparator", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": thr}),
                 IcmV3Record(cell_id="E", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
        try:
            IcmV3File(name="cmp", records=crecs).save(os.path.join(tmp, f"cmp_{thr}.icm"))
        except Exception as e_:
            check(f"threshold {s32(thr)}: the ICM can hold it", False, str(e_)[:160])
            continue
        dc, rc = build(tmp, f"cmp_{thr}", os.path.join(tmp, f"cmp_{thr}.icm"))
        if rc.returncode:
            check(f"threshold {s32(thr)}: generates on flex", False, rc.stderr.strip()[:200])
            continue
        wantc = [int(s32(v) >= s32(thr)) for v in probe]
        bad = []
        for mode, seed in (("plain", 81), ("stall", 82), ("slow", 83)):
            res, _ = run_stream(dc, {"X": probe}, mode, seed)
            if list(res.values())[0] != wantc:
                bad.append((mode, list(res.values())[0][:4], wantc[:4]))
        vmc = []
        frecs = nl.extract(os.path.join(tmp, f"cmp_{thr}.icm"))[1]            # the VM runs the DECODED FILE, as the real pipeline does
        for v in probe:
            g_ = vm.SuperGrid(frecs)
            for _ in range(8):
                g_.tick()
            g_.inject(1, 0, v)
            for _ in range(40):
                g_.tick()
            vmc.append(g_.cells[(1, 2)].ram_data_reg if g_.cells[(1, 2)].ram_data_valid else None)
        if thr < (1 << 31):
            check(f"threshold {s32(thr)}: {len(probe)} values incl. INT_MIN/INT_MAX around it x 3 modes == signed compare == the real VM ({vmc[:6]}...)", not bad and vmc == wantc, f"{bad[:1]} vm={vmc}")
        else:
            check(f"threshold {s32(thr)} (bit 31 set): the flex RTL == a true SIGNED compare on all {len(probe)} values x 3 modes (the cell declares its threshold signed)", not bad, str(bad[:1]))
            check("FINDING (a VM cascade item, not patched): the VM declares cmp_threshold signed but loads the unsigned 32-bit ICM field RAW, so a bit-31 threshold is read as a "
                  "huge positive and the VM returns 0 for EVERY value; the RTL (both families) reads it as negative. The compiler only emits non-negative thresholds, so nothing in the corpus hits it",
                  vmc == [0] * len(probe) and vmc != wantc, f"vm={vmc} signed-want={wantc}")
        cmp_dirs[thr] = dc
    if 5 in cmp_dirs:
        dz = cmp_dirs[5]
        topz = os.path.join(dz, json.load(open(os.path.join(dz, "ASSEMBLY.json")))["top"] + ".v")
        txt = re.sub(r"\.cfg_data\(32'h00000005\)", ".cfg_data(32'h00000000)", open(topz).read())
        dmz = os.path.join(tmp, "mutcmp")
        shutil.copytree(dz, dmz)
        open(os.path.join(dmz, os.path.basename(topz)), "w").write(txt)
        res, _ = run_stream(dmz, {"X": probe}, "plain", 84)
        check("mutant caught: the comparator's threshold zeroed (5 -> 0)", list(res.values())[0] != [int(s32(v) >= 5) for v in probe])

    print("MUTATION CONTROLS on the true diamond: break the fork / the join on purpose; the stall tests must catch each one")
    d0, rec0, streams0, want0 = diamond
    top0 = os.path.join(d0, rec0["top"] + ".v")
    orig = open(top0).read()

    def mutant(label, pat, rep):
        txt = re.sub(pat, rep, orig)
        assert txt != orig, f"mutation pattern not found: {pat}"
        dm = os.path.join(tmp, "mut_" + re.sub(r"\W+", "_", label)[:20])
        shutil.copytree(d0, dm)
        open(os.path.join(dm, rec0["top"] + ".v"), "w").write(txt)
        verdicts = []
        for mode, seed in (("plain", 11), ("stall", 12), ("stall", 13), ("slow", 14)):
            try:
                res, cyc = run_stream(dm, streams0, mode, seed)
                verdicts.append(list(res.values())[0] == want0)
            except Exception:
                verdicts.append(False)
        check(f"mutant caught: {label}", not all(verdicts), f"verdicts {verdicts}")
    mutant("the fork FORGETS who has taken the item (taken never set)", r"(\be\d+_t <= )e\d+_t \| e\d+_acc;", r"\g<1>1'b0;")
    mutant("valid is NOT masked by `taken` (a consumer is re-offered an item it already took)", r"assign (e\d+_v) = (c_\w+_v) & ~e\d+_t;", r"assign \g<1> = \g<2>;")
    mutant("the join acknowledges operand A even when B is not present", r"(assign e\d+_a = c_\w+_rdy) & e\d+_v;", r"\g<1>;")

    print("stage-1 refusals, each with its reason (never a silent mistranslation)")
    r = cli("-s", "flex", "--icm", os.path.join(EX, "cordic_z_convergence.icm-hier.json"), "--output", os.path.join(tmp, "g_c"))
    check("the hand-built cordic is refused on flex for its BRANCH and merges (constants are translated now, so they are NOT a reason)",
          r.returncode != 0 and "not yet translated on flex" in r.stderr and "branch" in r.stderr and "constant source" not in r.stderr, r.stderr.strip()[:260])
    kconst = [IcmV3Record(cell_id="K", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}, preload_value=9),
              IcmV3Record(cell_id="R", row=1, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"]}),
              IcmV3Record(cell_id="E", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
    IcmV3File(name="k", records=kconst).save(os.path.join(tmp, "k.icm"))
    r = cli("-s", "flex", "--icm", os.path.join(tmp, "k.icm"), "--output", os.path.join(tmp, "g_k"))
    check("an output that depends ONLY on constants is refused on flex (nothing live would pace it)", r.returncode != 0 and "only on constants" in r.stderr, r.stderr.strip()[:200])
    mrg = [IcmV3Record(cell_id=n_, row=rr, col=cc, core="ram", core_config={"upstream_mask": up, "downstream_mask": dn})
           for n_, rr, cc, up, dn in (("E1", 0, 1, [], ["s"]), ("E2", 1, 0, [], ["e"]), ("M", 1, 1, ["n", "w"], ["e"]), ("O", 1, 2, ["w"], []))]
    IcmV3File(name="m", records=mrg).save(os.path.join(tmp, "m.icm"))
    r = cli("-s", "flex", "--icm", os.path.join(tmp, "m.icm"), "--output", os.path.join(tmp, "g_m"))
    check("a merge is refused on flex (stage 1) -- under a handshake an OR-merge must decide which source to acknowledge", r.returncode != 0 and "merges" in r.stderr, r.stderr.strip()[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
