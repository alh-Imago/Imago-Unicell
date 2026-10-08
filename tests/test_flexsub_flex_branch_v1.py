#!/usr/bin/env python3
"""tests/test_flexsub_flex_branch_v1.py -- the ICM `branch` on the FLEX family (stage 6 of the flex emitter).

Run: python3 tests/test_flexsub_flex_branch_v1.py      (needs iverilog)
branch_cell_v4sa has TWO output ports (own valid/ack, shared out_buffer), FIXED inputs that are load strobes, FLOWING inputs on valid/ready with one ack_out, and the ICM branch is a
HELD-REFERENCE comparator (the VM, #935/#936): the first arrival becomes the reference and emits nothing, each later one is compared (signed) and routed. Three input modes
(const_ref, the ENTRY variant, rolling). Checked: streams through independent stalls on the two ports against the signed-compare oracle AND the real VM; the SPURIOUS-EQUAL TRAP of a
held-valid stream in rolling mode; fixed emit value / disabled outcome; and mutation controls on the rolling glue.
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
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
passed = failed = 0
M = 0xFFFFFFFF


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
    """X --E--> M (merge) --> B ; constant Z --S--> M.  B routes low/equal -> O1 (south), high -> O2 (north)."""
    routes = bkw.pop("routes", (["s"], ["s"], ["n"]))
    return [ram("X", 2, 0, [], ["e"]), ram("Z", 1, 1, [], ["s"], preload_value=const_value & M), ram("M", 2, 1, ["n", "w"], ["e"]),
            branch_rec("B", 2, 2, "w", routes, **bkw), ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]


def entry_design(const_value):
    """The merge carries an io_name and has only the constant as an in-grid source: the branch BECOMES the entry point (cordic's z_input pattern)."""
    return [ram("Z", 1, 1, [], ["s"], preload_value=const_value & M), ram("M", 2, 1, ["n", "w"], ["e"], io_name="zin"),
            branch_rec("B", 2, 2, "w", (["s"], ["s"], ["n"])), ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]


def rolling_design(**bkw):
    return [ram("X", 2, 1, [], ["e"]), branch_rec("B", 2, 2, "w", (["s"], ["s"], ["n"]), rolling=1, **bkw), ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]


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
      if ({' && '.join(dones)}) post <= post + 1;
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


def vm_items(records, entry, items, ticks_per_item=14, settle=8):
    """Inject each item at `entry` one at a time, after a settle for constants. Returns, per item, {exit id: value} for the exits that received a NEW value."""
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
                cell.ram_data_valid = False
        out.append(got)
    return out


def lists_of(vm_res):
    return {"O1": [d["O1"] for d in vm_res if "O1" in d], "O2": [d["O2"] for d in vm_res if "O2" in d]}


def oracle_ref(items, c):
    return {"O1": [v & M for v in items if s32(v) <= s32(c)], "O2": [v & M for v in items if s32(v) > s32(c)]}


def oracle_roll(items):
    o1, o2 = [], []
    for k in range(1, len(items)):
        (o1 if s32(items[k]) <= s32(items[k - 1]) else o2).append(items[k] & M)
    return {"O1": o1, "O2": o2}


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", icm, "--output", d)


MODES = (("plain", 1), ("stall", 2), ("stall", 3), ("stall", 4))
if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)
tmp = tempfile.mkdtemp(prefix="flexbranch_")
try:
    print("const_ref (a merge of a constant and a stream, the cordic pattern): streams through INDEPENDENT stalls on the two output ports == signed compare == the real VM")
    for c in (0, 100, -50):
        recs = ref_design(c)
        d, r = build(tmp, f"ref{c}", recs)
        check(f"reference {c}: generates on flex as a const_ref branch", r.returncode == 0 and json.load(open(os.path.join(d, "ASSEMBLY.json")))["branches"]["B"]["mode"] == "const_ref", r.stderr.strip()[:240])
        if r.returncode:
            continue
        items = [c - 7, c, c + 1, c + 5000, -0x80000000, 0x7FFFFFFF, c, c - 1, c + 2, c]
        want = oracle_ref(items, c)
        vmres = lists_of(vm_items(recs, "X", items))
        bad = []
        for mode, seed in MODES:
            _, got = run_level(d, {"X": [v & M for v in items]}, mode, seed, settle=160)
            if {"O1": got["O1"], "O2": got["O2"]} != want:
                bad.append((mode, seed, got, want))
        check(f"  reference {c}: 10 items x 4 modes: low/equal -> O1, high -> O2, in order, none lost; oracle == the VM", not bad and want == vmres, f"{bad[:1]} vm={vmres}")

    print("the ENTRY variant: the branch absorbed the merge that carried the io_name, so it IS the entry point")
    recs = entry_design(100)
    d, r = build(tmp, "entry", recs)
    ok = r.returncode == 0
    check("entry-point branch generates; its top-level port is the merge's io_name", ok and "in_zin_data" in open(os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")).read(), r.stderr.strip()[:240])
    if ok:
        items = [93, 100, 101, 5000, -7, 100, 99]
        want = oracle_ref(items, 100)
        vmres = lists_of(vm_items(recs, "M", items))
        bad = []
        for mode, seed in MODES:
            _, got = run_level(d, {"zin": [v & M for v in items]}, mode, seed, settle=160)
            if {"O1": got["O1"], "O2": got["O2"]} != want:
                bad.append((mode, got, want))
        check("  7 items x 4 modes through the entry port == the signed compare == the real VM", not bad and want == vmres, f"{bad[:1]} vm={vmres}")

    print("a fixed emit value, and an outcome with emit disabled")
    recs = ref_design(10, vsrc=(1, 1, 1), fixed=(0x55, 0x55, 0x55), emit=(0, 1, 1))
    d, r = build(tmp, "fx", recs)
    check("fixed-value / emit-disabled branch generates", r.returncode == 0, r.stderr.strip()[:240])
    if r.returncode == 0:
        items = [3, 10, 11, 1000, 9, 10]
        vmres = lists_of(vm_items(recs, "X", items))
        want = {"O1": [0x55 for v in items if s32(v) == 10], "O2": [0x55 for v in items if s32(v) > 10]}
        bad = []
        for mode, seed in MODES:
            _, got = run_level(d, {"X": items}, mode, seed, settle=160)
            if {"O1": got["O1"], "O2": got["O2"]} != want:
                bad.append((mode, got, want))
        check("  value < ref emits NOTHING (consumed silently); == ref -> 0x55 on O1; > ref -> 0x55 on O2: x 4 modes == the VM", not bad and want == vmres, f"{bad[:1]} vm={vmres}")

    print("ROLLING: each value is compared with the PREVIOUS one; the first only becomes the reference -- and a HELD valid must not fire it again (the spurious-EQUAL trap)")
    recs = rolling_design()
    d, r = build(tmp, "roll", recs)
    check("rolling branch generates, planned as rolling", r.returncode == 0 and json.load(open(os.path.join(d, "ASSEMBLY.json")))["branches"]["B"]["mode"] == "rolling", r.stderr.strip()[:240])
    if r.returncode == 0:
        seq = [5, 9, 9, 3, 100, -4, -4, -9]
        vmres = lists_of(vm_items(recs, "X", seq))
        want = oracle_roll(seq)
        bad = []
        for mode, seed in MODES:
            _, got = run_level(d, {"X": [v & M for v in seq]}, mode, seed, settle=160)
            if {"O1": got["O1"], "O2": got["O2"]} != want:
                bad.append((mode, got, want))
        check("8 values x 4 modes: item 1 emits nothing; each later item is routed by its comparison with the previous: == the signed oracle == the real VM",
              not bad and want == vmres, f"{bad[:1]} vm={vmres} want={want}")
        for single, expect in (([42], {"O1": [], "O2": []}), ([7, 7], {"O1": [7], "O2": []}), ([7, 7, 7], {"O1": [7, 7], "O2": []})):
            vmx = lists_of(vm_items(recs, "X", single))
            bad = []
            for mode, seed in MODES:
                _, got = run_level(d, {"X": single}, mode, seed, settle=160)
                if {"O1": got["O1"], "O2": got["O2"]} != expect:
                    bad.append((mode, got))
            check(f"  the trap: {single} -> exactly {expect} in all 4 modes (a single item must produce NO output; a repeated item exactly one EQUAL each) == the VM {vmx}",
                  not bad and vmx == expect, f"{bad[:1]}")
        rnd = random.Random(951)
        long_seq = [rnd.choice([rnd.getrandbits(32), rnd.randrange(-5, 6) & M, 0x80000000, 0x7FFFFFFF]) for _ in range(40)]
        want = oracle_roll(long_seq)
        bad = []
        for mode, seed in MODES:
            _, got = run_level(d, {"X": long_seq}, mode, seed, settle=400, cycles=8000)
            if {"O1": got["O1"], "O2": got["O2"]} != want:
                bad.append((mode, len(got["O1"]), len(got["O2"]), len(want["O1"]), len(want["O2"])))
        check("a 40-value random sequence (incl. INT_MIN/INT_MAX and repeats) x 4 modes == the signed rolling oracle, none lost, in order", not bad, str(bad[:1]))

        print("MUTATION CONTROLS on the rolling glue")
        top = os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")
        orig = open(top).read()
        muts = [("the NAIVE rule: the stream is acknowledged only once the cell can FIRE, so the first arrival stays valid and fires against the reference it just loaded (the spurious EQUAL)",
                 r"assign (e\d+_a) = ~c_B_ld \| c_B_rdy;", r"assign \g<1> = c_B_rdy & c_B_ld;"),
                ("the reference is never reloaded after the first value (every value is compared with the FIRST)", r"wire c_B_in1v = c_B_fire, c_B_in2v = c_B_fire \| c_B_first;", r"wire c_B_in1v = c_B_fire, c_B_in2v = c_B_first;"),
                ("the stream is acknowledged before the cell is ready (items are consumed but lost)", r"assign (e\d+_a) = ~c_B_ld \| c_B_rdy;", r"assign \g<1> = 1'b1;")]
        for mi, (label, pat, rep) in enumerate(muts):
            txt = re.sub(pat, rep, orig)
            assert txt != orig, pat
            dm = os.path.join(tmp, f"mutb_{mi}")
            shutil.copytree(d, dm)
            open(os.path.join(dm, os.path.basename(top)), "w").write(txt)
            verdicts = []
            for mode, seed in MODES:
                try:
                    _, got = run_level(dm, {"X": [v & M for v in seq]}, mode, seed, settle=160)
                    verdicts.append({"O1": got["O1"], "O2": got["O2"]} == oracle_roll(seq))
                except Exception:
                    verdicts.append(False)
            check(f"  mutant caught: {label}", not all(verdicts), f"verdicts {verdicts}")

    print("refusals the lowering already makes (shared with sub), still reasoned on flex")
    nostream = [ram("X", 2, 1, [], ["e"]), branch_rec("B", 2, 2, "w", (["s"], ["s"], ["n"]), rolling=0), ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]
    d, r = build(tmp, "firstonly", nostream)
    check("a reference that is the FIRST arrival of a plain stream with rolling off (needs a 'first only' state bit = control) is refused", r.returncode != 0 and "first" in r.stderr.lower(), r.stderr.strip()[:260])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
