#!/usr/bin/env python3
"""tests/test_flexsub_flex_merge_v1.py -- the MERGE CORE on the FLEX family (stage 7, ledger #954/#955): the whole hand-built CORDIC runs on flex.

Run: python3 tests/test_flexsub_flex_merge_v1.py      (needs iverilog)
A merge feeds several sources into ONE input. The VM ORs same-tick arrivals; under a handshake two sources can BOTH be valid for as long as the cell is busy, so a plain OR would FUSE two
separate items into one corrupt value. The flex MERGE is a CORE, merge_cell_v4sa (Alan's ruling: known, verified core designs, not hand-woven glue), with four selectable modes: 0 A only,
1 B only, 2 ARBITRATE (grant one, acknowledge only that one, rotate priority), 3 JOIN-OR (wait for both, then OR). The emitter inserts one in front of each ICM merge.
Checked: the actual cordic (36 cells: 4 branches, 4 merges, 8 adders, 12 constants) against the REAL VM on 12 starting angles plus the -404 anchor, one item in flight at a time, through exit
stalls; hand-built merges (no item lost, duplicated or corrupted; fairness; the same-cycle DIVERGENCE from the VM stated as a finding); streaming behaviour reported honestly; mutation controls.
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
from hierarchical_icm_prototype_loader import load_hierarchical, flatten  # noqa: E402

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


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", icm, "--output", d)


def run_level(folder, streams, mode="plain", seed=1, settle=60, cycles=3000, serial=False):
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
        gate = f"(got_n >= idx_{name})" if serial else gap                  # serial: the next item enters only once the previous RESULT has come out
        drv.append(f"      if (act_{name} && ack_{name}) begin idx_{name} <= idx_{name} + 1; act_{name} <= 1'b0; end\n"
                   f"      else if (!act_{name} && idx_{name} < {n} && {gate}) act_{name} <= 1'b1;")
        conn.append(f".in_{name}_data(d_{name}), .in_{name}_valid(act_{name}), .in_{name}_ack(ack_{name})")
        dones.append(f"idx_{name} >= {n}")
    cap = []
    for k, name in enumerate(outs):
        ready = f"lfsr[{(7 * k + 11) % 31}]" if mode == "stall" else "1'b1"
        decl.append(f"  wire [31:0] od_{name}; wire ov_{name}; wire oa_{name} = {ready};")
        cap.append(f'      $display("LV {name} %0d %0d", cyc, od_{name});\n'
                   f'      if (ov_{name} && oa_{name}) begin $display("GOT {name} %0d", od_{name}); got_n <= got_n + 1; end')
        conn.append(f".out_{name}_data(od_{name}), .out_{name}_valid(ov_{name}), .out_{name}_ack(oa_{name})")
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0;
  reg [31:0] lfsr = 32'h{(0xACE1 ^ (seed * 0x9E3779B1)) & 0xFFFFFFFF or 1:08X};
{chr(10).join(decl)}
  {top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {', '.join(conn)});
  always #5 clk = ~clk;
  integer cyc = 0, post = 0, got_n = 0; reg started = 0;
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


def vm_exit(records, injects, ticks=40):
    """Inject {cell id: value} all in the SAME tick; return the value that reached the exit ram E (or None)."""
    g_ = vm.SuperGrid(records)
    for _ in range(8):
        g_.tick()
    for cid, v in injects.items():
        r = next(x for x in records if x.cell_id == cid)
        g_.inject(r.row, r.col, v & 0xFFFFFFFF)
    ex = next(x for x in records if x.cell_id == "E")
    for _ in range(ticks):
        g_.tick()
    cell = g_.cells[(ex.row, ex.col)]
    return cell.ram_data_reg if cell.ram_data_valid else None


MODES = (("plain", 1), ("stall", 2), ("stall", 3))
if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)
tmp = tempfile.mkdtemp(prefix="flexmerge_")
try:
    print("THE WHOLE CORDIC on flex: 36 cells (4 branches, 4 merges, 8 adders, 12 constants), generated with no new cell")
    d = os.path.join(tmp, "cordic")
    r = cli("-s", "flex", "--icm", CORDIC, "--output", d)
    check("the cordic generates on flex", r.returncode == 0, r.stderr.strip()[:300])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    nm = sum(1 for j in rec["joins"] if j.get("kind", "").startswith("merge core"))
    check(f"it contains {nm} merge CORES (merge_cell_v4sa, mode arbitrate) and {len(rec['branches'])} const_ref branches (the z_input entry absorbed by the first)", nm == 4 and len(rec["branches"]) == 4 and rec["branches"]["s0.branch"].get("entry_io") == "z_input" and rec["merge_mode"] == "arbitrate" and "merge_cell_v4sa.v" in rec["files"], str(rec["branches"])[:200])
    records, _ = flatten(load_hierarchical(CORDIC))
    ic = next(x for x in records if x.io_name == "z_input")
    oc = next(x for x in records if x.io_name == "z_output")

    def vm_z(z0):
        g_ = vm.SuperGrid(records)
        for _ in range(6):
            g_.tick()
        g_.inject(ic.row, ic.col, z0 & 0xFFFFFFFF)
        for _ in range(80):
            g_.tick()
            o = g_.cells[(oc.row, oc.col)]
            if o.ram_data_valid:
                return s32(o.ram_data_reg)
        return None

    angles = (50000, -50000, 0, 1, -1, 100, -100, 12345, -12345, 90000, -90000, 200000)
    want = [vm_z(z) for z in angles]
    for mode, seed in MODES:
        _, got = run_level(d, {"z_input": [z & 0xFFFFFFFF for z in angles]}, mode, seed, settle=300, cycles=12000, serial=True)
        gv = [s32(v) for v in got["z_output"]]
        check(f"12 starting angles (both signs, 0, +-1, beyond convergence), one in flight, mode={mode}: flex == the REAL VM", gv == want, f"flex={gv} vm={want}")
    _, got = run_level(d, {"z_input": [50000]}, "plain", 1, settle=200, serial=True)
    check("the independent anchor: z0 = 50000 -> -404 (the repo's own Python-computed value, not a simulation)", [s32(v) for v in got["z_output"]] == [-404], str(got))

    print("STREAMING through the merges: reported honestly (an arbiter cannot restore ORDER between two paths)")
    stream = [12345, -12345, 90000, -90000, 100, -100, 7, -7]
    wants = {z: vm_z(z) for z in stream}
    res = []
    for mode, seed in (("plain", 4), ("stall", 5), ("stall", 6), ("stall", 7)):
        _, got = run_level(d, {"z_input": [z & 0xFFFFFFFF for z in stream]}, mode, seed, settle=400, cycles=12000)
        gv = [s32(v) for v in got["z_output"]]
        res.append((mode, sorted(gv) == sorted(wants[z] for z in stream), gv == [wants[z] for z in stream]))
    check("8 angles back-to-back x 4 modes: NO value is ever corrupted or lost (the outputs are exactly the 8 correct results, as a multiset)", all(r_[1] for r_ in res), str(res))
    print(f"        (in order: {[r_[2] for r_ in res]} -- recorded, not asserted: items on the two paths of a merge can overtake each other, so order is only guaranteed with one item in flight)")

    print("hand-built merges: two entries X, Y -> merge M -> exit E")
    two = [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]), ram("M", 1, 1, ["n", "w"], ["e"]), ram("E", 1, 2, ["w"], [])]
    d2, r = build(tmp, "two", two)
    check("a two-source merge generates on flex as a merge core", r.returncode == 0 and any(j.get("kind", "").startswith("merge core") for j in json.load(open(os.path.join(d2, "ASSEMBLY.json")))["joins"]), r.stderr.strip()[:240])
    xs, ys = [0x1000 + k for k in range(10)], [0x2000 + k for k in range(10)]
    bad = []
    for mode, seed in (("plain", 8), ("stall", 9), ("stall", 10), ("skewfirst", 11), ("skewlast", 12)):
        _, got = run_level(d2, {"X": xs, "Y": ys}, mode, seed, settle=200)
        out = got["E"]
        gx, gy = [v for v in out if v in xs], [v for v in out if v in ys]
        if sorted(out) != sorted(xs + ys) or gx != xs or gy != ys:
            bad.append((mode, out))
    check("10 + 10 items x 5 modes: every item emerges exactly once, UNCORRUPTED, and each source's own order is kept", not bad, str(bad[:1]))
    _, got = run_level(d2, {"X": xs, "Y": ys}, "plain", 13, settle=200)
    first8 = got["E"][:8]
    check(f"FAIRNESS: with both sources always valid, the first 8 outputs include BOTH sources ({sum(v in xs for v in first8)} from X, {sum(v in ys for v in first8)} from Y): no starvation",
          any(v in xs for v in first8) and any(v in ys for v in first8) and abs(sum(v in xs for v in first8) - 4) <= 2, str(first8))
    xv, yv = 0x00F0, 0x0F00
    vmv = vm_exit(two, {"X": xv, "Y": yv})
    _, got = run_level(d2, {"X": [xv], "Y": [yv]}, "plain", 14, settle=200)
    check(f"FINDING for ARBITRATE mode (stated, not hidden): two items in the SAME cycle -- the VM ORs them into ONE value {hex(vmv) if vmv is not None else None}; flex SEQUENCES them: two outputs {sorted(hex(v) for v in got['E'])}",
          vmv == (xv | yv) and sorted(got["E"]) == sorted([xv, yv]), f"vm={vmv} flex={got['E']}")

    print("JOIN-OR mode (--merge-mode join-or): two paths that are HALVES of one item, combined deterministically -- this RESOLVES the same-cycle divergence above")
    dj = os.path.join(tmp, "g_join")
    icm2 = os.path.join(tmp, "two.icm")
    rj = cli("-s", "flex", "--icm", icm2, "--output", dj, "--merge-mode", "join-or")
    recj = json.load(open(os.path.join(dj, "ASSEMBLY.json"))) if rj.returncode == 0 else {}
    check("join-or generates, and the core is configured in mode 3", rj.returncode == 0 and recj.get("merge_mode") == "join-or" and ".cfg_data(32'h3)" in open(os.path.join(dj, recj["top"] + ".v")).read(), rj.stderr.strip()[:200])
    if rj.returncode == 0:
        _, gotj = run_level(dj, {"X": [xv], "Y": [yv]}, "plain", 14, settle=200)
        check(f"the SAME-CYCLE pair now gives ONE value {[hex(v) for v in gotj['E']]} == the VM's {hex(vmv)}: the divergence is resolved by selecting the mode", gotj["E"] == [vmv], f"flex={gotj['E']} vm={vmv}")
        pairs = [(0x00F0F000 + k, 0x0000F00F << (k % 3) & 0xFFFFFFFF) for k in range(10)]
        wantp = [a_ | b_ for a_, b_ in pairs]
        bad = []
        for mode, seed in (("plain", 21), ("stall", 22), ("stall", 23), ("skewfirst", 24), ("skewlast", 25)):
            _, gj = run_level(dj, {"X": [a_ for a_, _ in pairs], "Y": [b_ for _, b_ in pairs]}, mode, seed, settle=240)
            if gj["E"] != wantp:
                bad.append((mode, gj["E"][:3], wantp[:3]))
        check("10 paired items x 5 modes (incl. X slow, Y slow): the output is x_k | y_k, IN ORDER, none lost -- the join waits for the slower side", not bad, str(bad[:1]))
        _, gj = run_level(dj, {"X": xs, "Y": ys[:6]}, "stall", 26, settle=240)
        check("lone items WAIT: 10 X items but only 6 Y items give exactly 6 outputs (the 4 surplus X items never emerge, and are never fused with anything)", gj["E"] == [a_ | b_ for a_, b_ in zip(xs[:6], ys[:6])], str(gj["E"]))

    print("MUTATION CONTROLS -- on the CORE itself (the cell's own bench must catch every one), then through a whole design")
    SUBV = os.path.join(ROOT, "sub", "verilog")
    cell_src = open(os.path.join(SUBV, "merge_cell_v4sa.v")).read()
    cmut = [("arbitration ignores the round-robin flag (A always wins)", "(valid_in_a && (!valid_in_b || !rr))", "valid_in_a"),
            ("arbitrate acknowledges B although only A is granted", "ready && (m_or ? valid_in_a : g_b)", "ready && (m_or ? valid_in_a : valid_in_b)"),
            ("join-OR does not wait: it takes either side", "m_or ? (valid_in_a && valid_in_b) : (g_a || g_b)", "m_or ? (valid_in_a || valid_in_b) : (g_a || g_b)"),
            ("join-OR computes AND instead of OR", "(in_a | in_b)", "(in_a & in_b)"),
            ("join-OR acknowledges A without B present", "ready && (m_or ? valid_in_b : g_a)", "ready"),
            ("mode 0 (A only) also accepts B", "m_b ? valid_in_b : (m_arb", "(m_b || m_a) ? valid_in_b : (m_arb"),
            ("captures when unarmed", "end else if (ready && take) begin", "end else if (take) begin"),
            ("the priority flag never rotates", "if (m_arb) rr <= g_a;", "if (m_arb) rr <= 1'b0;"),
            ("freeze does not gate the ready levels", "wire ready = armed && !pending && !freeze_in;", "wire ready = armed && !pending;"),
            ("reconfiguration does not clear a pending output", "            mode       <= cfg_data[1:0];\n            armed      <= 1'b1;\n            pending    <= 1'b0;", "            mode       <= cfg_data[1:0];\n            armed      <= 1'b1;"),
            ("the data select is swapped", "(g_a ? in_a : in_b)", "(g_a ? in_b : in_a)"),
            ("the output releases without waiting for ack_in", "if (ack_in) pending <= 1'b0;", "pending <= 1'b0;")]
    clean = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(tmp, "tbc.vvp"), os.path.join(SUBV, "tb_merge_cell_v4sa.v"), os.path.join(SUBV, "merge_cell_v4sa.v")], capture_output=True, text=True)
    cleanout = subprocess.run(["vvp", os.path.join(tmp, "tbc.vvp")], capture_output=True, text=True).stdout
    check("the cell's bench passes on the real core (37 checks, ALL PASS)", clean.returncode == 0 and "ALL PASS" in cleanout and cleanout.count("PASS:") >= 37, clean.stderr[:200])
    survivors = []
    for label, pat, rep in cmut:
        assert pat in cell_src, pat
        mc = os.path.join(tmp, "mutcell.v")
        open(mc, "w").write(cell_src.replace(pat, rep, 1))
        cc = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(tmp, "tbm.vvp"), os.path.join(SUBV, "tb_merge_cell_v4sa.v"), mc], capture_output=True, text=True)
        out = subprocess.run(["vvp", os.path.join(tmp, "tbm.vvp")], capture_output=True, text=True).stdout if cc.returncode == 0 else "ERR"
        if "ALL PASS" in out:
            survivors.append(label)
    check(f"all {len(cmut)} deliberate defects in the core are CAUGHT by its bench (survivors: {survivors or 'none'})", not survivors, str(survivors))
    for label, pat, rep, design, kind in (("arbitrate acknowledges B although only A is granted (an item consumed but lost)", "ready && (m_or ? valid_in_a : g_b)", "ready && (m_or ? valid_in_a : valid_in_b)", d2, "arb"),
                                          ("join-OR computes AND instead of OR", "(in_a | in_b)", "(in_a & in_b)", dj, "join")):
        dm = os.path.join(tmp, "mutd_" + kind)
        shutil.copytree(design, dm)
        open(os.path.join(dm, "merge_cell_v4sa.v"), "w").write(cell_src.replace(pat, rep, 1))
        if kind == "arb":
            verdicts = []
            for mode, seed in (("plain", 8), ("stall", 9), ("skewfirst", 11)):
                _, got = run_level(dm, {"X": xs, "Y": ys}, mode, seed, settle=200)
                verdicts.append(sorted(got["E"]) == sorted(xs + ys))
        else:
            _, got = run_level(dm, {"X": [a_ for a_, _ in pairs], "Y": [b_ for _, b_ in pairs]}, "plain", 21, settle=240)
            verdicts = [got["E"] == wantp]
        check(f"  through a whole design, the defect is caught: {label}", not all(verdicts), f"verdicts {verdicts}")

    print("refusals")
    three = [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]), ram("W", 2, 1, [], ["n"]), ram("M", 1, 1, ["n", "w", "s"], ["e"]), ram("E", 1, 2, ["w"], [])]
    d3, r = build(tmp, "three", three)
    check("a merge of THREE sources is refused on flex (the arbiter handles two)", r.returncode != 0 and "3 sources" in r.stderr, r.stderr.strip()[:240])
    withc = [ram("K", 0, 1, [], ["s"], preload_value=5), ram("Y", 1, 0, [], ["e"]), ram("M", 1, 1, ["n", "w"], ["e"]), ram("E", 1, 2, ["w"], [])]
    d4, r = build(tmp, "withconst", withc)
    check("a merge that includes a CONSTANT is refused (the constant is always valid and would swamp the stream)", r.returncode != 0 and "constant source" in r.stderr, r.stderr.strip()[:240])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
