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
    slow (output ready only 1 cycle in 8). Returns {exit suffix: [values captured in order]}."""
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
        gap = f"(1'b1)" if mode != "stall" else f"(lfsr[{(3 * k + 2) % 31}] | lfsr[{(5 * k + 7) % 31}])"
        drv.append(f"      if (act_{name} && ack_{name}) begin idx_{name} <= idx_{name} + 1; act_{name} <= 1'b0; end\n"
                   f"      else if (!act_{name} && idx_{name} < {n} && {gap}) act_{name} <= 1'b1;")
        conn.append(f".in_{name}_data(d_{name}), .in_{name}_valid(act_{name}), .in_{name}_ack(ack_{name})")
    for k, name in enumerate(outs):
        ready = {"plain": "1'b1", "stall": f"lfsr[{(7 * k + 11) % 31}]", "slow": f"(lfsr[{(7 * k + 11) % 31}] & lfsr[{(7 * k + 12) % 31}] & lfsr[{(7 * k + 13) % 31}])"}[mode]
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
    check("cordic (branch, constants) is refused on flex with the reasons", r.returncode != 0 and "not yet translated on flex" in r.stderr and "branch" in r.stderr, r.stderr.strip()[:200])
    file, report, _ = fc.compile_for_flexsub("define i32 @f(i32 %x) {\nentry:\n  %r = add i32 %x, 5\n  ret i32 %r\n}\n", "k")
    file.save(os.path.join(tmp, "k.icm"))
    r = cli("-s", "flex", "--icm", os.path.join(tmp, "k.icm"), "--output", os.path.join(tmp, "g_k"))
    check("a program with a constant (x + 5) is refused on flex (stage 1)", r.returncode != 0 and "constant" in r.stderr, r.stderr.strip()[:200])
    mrg = [IcmV3Record(cell_id=n_, row=rr, col=cc, core="ram", core_config={"upstream_mask": up, "downstream_mask": dn})
           for n_, rr, cc, up, dn in (("E1", 0, 1, [], ["s"]), ("E2", 1, 0, [], ["e"]), ("M", 1, 1, ["n", "w"], ["e"]), ("O", 1, 2, ["w"], []))]
    IcmV3File(name="m", records=mrg).save(os.path.join(tmp, "m.icm"))
    r = cli("-s", "flex", "--icm", os.path.join(tmp, "m.icm"), "--output", os.path.join(tmp, "g_m"))
    check("a merge is refused on flex (stage 1) -- under a handshake an OR-merge must decide which source to acknowledge", r.returncode != 0 and "merges" in r.stderr, r.stderr.strip()[:200])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
