#!/usr/bin/env python3
"""tests/test_flexsub_flex_level_v1.py -- the flex LEVEL SOURCES (accumulator, latch), stage 5 of the flex emitter.

Run: python3 tests/test_flexsub_flex_level_v1.py      (needs iverilog)
A level source offers its state ALWAYS VALID (the VM, #938), so a stream test (items out) is the wrong observation: the right one is to SAMPLE the level every cycle and
compare the SEQUENCE OF DISTINCT VALUES it passes through, which exposes a dropped or duplicated event whatever the timing -- against the real VM's per-item totals/states.
The flex cells' pulse inputs have NO handshake and the snapshot (`out_buffer`) is only taken when the cell is not pending, so the emitter gates every pulse by the cell's ready:
that is what is verified here, with input gaps, back-to-back items, forced simultaneity (priority clear > set > toggle) and MUTATION CONTROLS on the gating.
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
    return IcmV3Record(cell_id=cid, row=r, col=c, core="accumulator", core_config={"inc_dir": inc, "dec_dir": dec, "downstream_mask": down, "step_amount": step,
                                                                                 "pulse_mode": pulse, "threshold": thr})


def latch(cid, r, c, setd, clr, tog, down):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="latch", core_config={"set_dir": setd, "clear_dir": clr, "toggle_dir": tog, "downstream_mask": down})


def cmp_(cid, r, c, up, down, thr):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="comparator", core_config={"upstream_mask": up, "downstream_mask": down, "threshold": thr})


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


def comp(seq):
    out = []
    for v in seq:
        if not out or out[-1] != v:
            out.append(v)
    return out


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", icm, "--output", d)


def vm_level(records, items, probe_id, getter, settle=8):
    g_ = vm.SuperGrid(records)
    for _ in range(settle):
        g_.tick()
    pr = next(r for r in records if r.cell_id == probe_id)
    cell = g_.cells[(pr.row, pr.col)]
    out = []
    for it in items:
        for cid, v in it.items():
            r = next(x for x in records if x.cell_id == cid)
            g_.inject(r.row, r.col, v & 0xFFFFFFFF)
        for _ in range(24):
            g_.tick()
        out.append(getter(cell))
    return out


def vm_events(records, items, exit_id, settle=8):
    g_ = vm.SuperGrid(records)
    for _ in range(settle):
        g_.tick()
    ex = next(r for r in records if r.cell_id == exit_id)
    cell = g_.cells[(ex.row, ex.col)]
    out = []
    for it in items:
        for cid, v in it.items():
            r = next(x for x in records if x.cell_id == cid)
            g_.inject(r.row, r.col, v & 0xFFFFFFFF)
        for _ in range(20):
            g_.tick()
        if cell.ram_data_valid:
            out.append(cell.ram_data_reg)
            cell.ram_data_valid = False
    return out


ACC_TOTAL = lambda c: c.acc_total & 0xFFFFFFFF          # noqa: E731
LATCH_STATE = lambda c: 1 if c.latch_state else 0       # noqa: E731

if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="flexlevel_")
try:
    print("accumulator, continuous mode -- a LEVEL source: the sequence of totals it passes through == the real VM's, under gaps and back-to-back items")
    recs = [ram("XI", 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"], [], [], step=3)]
    d, r = build(tmp, "counter", recs)
    check("counter generates on flex (the accumulator is a level source AND the exit)", r.returncode == 0 and json.load(open(os.path.join(d, "ASSEMBLY.json")))["level_sources"] == ["ACC"], r.stderr.strip()[:240])
    n = 9
    want = [0] + vm_level(recs, [{"XI": 0xDEAD}] * n, "ACC", ACC_TOTAL)
    for mode, seed in (("plain", 1), ("stall", 2), ("stall", 3)):
        lv, _ = run_level(d, {"XI": [0xDEAD] * n}, mode, seed)
        got = comp(lv["ACC"])
        check(f"9 increments of 3, mode={mode}: levels {got} == [0] + the VM's totals", got == want == [3 * k for k in range(n + 1)], f"got={got} vm={want}")

    print("up/down with TWO sources (their arrivals interleave differently under every mode): the final level and every intermediate level are right")
    recs2 = [ram("XI", 0, 1, [], ["s"]), ram("XD", 2, 1, [], ["n"]), acc("ACC", 1, 1, ["n"], ["s"], [], step=5)]
    d2, r = build(tmp, "updown", recs2)
    check("up/down generates", r.returncode == 0, r.stderr.strip()[:240])
    ninc, ndec = 8, 3
    reach = {5 * (a_ - b_) & 0xFFFFFFFF for a_ in range(ninc + 1) for b_ in range(ndec + 1)}
    for mode, seed in (("plain", 4), ("stall", 5), ("stall", 6), ("skewfirst", 7), ("skewlast", 8)):
        lv, _ = run_level(d2, {"XI": [1] * ninc, "XD": [1] * ndec}, mode, seed)
        seq = comp(lv["ACC"])
        check(f"{ninc} inc + {ndec} dec of 5, mode={mode}: final level {s32(seq[-1])} == {5 * (ninc - ndec)}; every level visited is a reachable partial sum",
              seq[-1] == (5 * (ninc - ndec)) & 0xFFFFFFFF and all(v in reach for v in seq), f"seq={[s32(v) for v in seq]}")

    print("accumulator in PULSE mode: a discrete event on each threshold crossing (resets to 0) == the real VM's events, through exit stalls")
    for label, entry, items, want_sign in (("inc", "XI", ["XI"] * 9, 30), ("dec", "XD", ["XD"] * 9, -30)):
        recs3 = [ram(entry, 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"] if entry == "XI" else [], ["w"] if entry == "XD" else [], ["e"], step=10, pulse=1, thr=25), ram("E", 1, 2, ["w"], [])]
        d3, r = build(tmp, "pulse_" + label, recs3)
        check(f"pulse-mode accumulator ({label}) generates and is NOT a level source", r.returncode == 0 and json.load(open(os.path.join(d3, "ASSEMBLY.json")))["level_sources"] == [], r.stderr.strip()[:200])
        wantv = [s32(v) for v in vm_events(recs3, [{entry: 1}] * 9, "E")]
        for mode, seed in (("plain", 9), ("stall", 10), ("stall", 11)):
            _, got = run_level(d3, {entry: [1] * 9}, mode, seed, settle=120)
            gv = [s32(v) for v in got["E"]]
            check(f"  {label}, mode={mode}: events {gv} == the VM's {wantv} (= {want_sign} every 3rd item)", gv == wantv == [want_sign] * 3, f"got={gv} vm={wantv}")

    print("latch -- a LEVEL source: toggle, set (needs bit 0), and the priority clear > set > toggle when two events arrive in the SAME cycle")
    recs4 = [ram("XT", 1, 0, [], ["e"]), latch("L", 1, 1, [], [], ["w"], [])]
    d4, r = build(tmp, "toggle", recs4)
    check("latch (toggle) generates", r.returncode == 0, r.stderr.strip()[:200])
    wantt = [0] + vm_level(recs4, [{"XT": 1}] * 6, "L", LATCH_STATE)
    for mode, seed in (("plain", 12), ("stall", 13)):
        lv, _ = run_level(d4, {"XT": [1] * 6}, mode, seed)
        check(f"6 toggles, mode={mode}: states {comp(lv['L'])} == [0] + the VM's {wantt[1:]}", comp(lv["L"]) == wantt == [0, 1, 0, 1, 0, 1, 0], f"got={comp(lv['L'])} vm={wantt}")
    recs5 = [ram("XS", 1, 0, [], ["e"]), latch("L", 1, 1, ["w"], [], [], [])]
    d5, r = build(tmp, "setonly", recs5)
    vals = [0, 2, 1, 3, 0, 5]
    wants = [0] + vm_level(recs5, [{"XS": v} for v in vals], "L", LATCH_STATE)
    for mode, seed in (("plain", 14), ("stall", 15)):
        lv, _ = run_level(d5, {"XS": vals}, mode, seed)
        check(f"set with values {vals} (only an odd value sets, the others are consumed with no effect), mode={mode}: states {comp(lv['L'])} == the VM's, final 1",
              comp(lv["L"]) == comp(wants) == [0, 1], f"got={comp(lv['L'])} vm={comp(wants)}")
    even = [0, 2, 4, 6, 8]
    wante = vm_level(recs5, [{"XS": v} for v in even], "L", LATCH_STATE)
    lv, _ = run_level(d5, {"XS": even}, "plain", 14)
    check(f"set with ALL-EVEN values {even}: bit 0 is never 1, so the latch must NEVER set: flex {comp(lv['L'])} == the VM's {comp(wante)} == [0]", comp(lv["L"]) == comp(wante) == [0], f"flex={comp(lv['L'])} vm={wante}")
    # forced simultaneity: both entries present their single item in the SAME cycle
    pri = [("set(1)+clear", {"XS": 1, "XC": 1}, [ram("XS", 0, 1, [], ["s"]), ram("XC", 1, 0, [], ["e"]), latch("L", 1, 1, ["n"], ["w"], [], [])], 0),
           ("set(1)+toggle", {"XS": 1, "XT": 1}, [ram("XS", 0, 1, [], ["s"]), ram("XT", 2, 1, [], ["n"]), latch("L", 1, 1, ["n"], [], ["s"], [])], 1),
           ("toggle+clear", {"XT": 1, "XC": 1}, [ram("XT", 2, 1, [], ["n"]), ram("XC", 1, 0, [], ["e"]), latch("L", 1, 1, [], ["w"], ["s"], [])], 0)]
    for label, ev, recs6, expect in pri:
        d6, r = build(tmp, "pri_" + re.sub(r"\W+", "_", label), recs6)
        vmv = vm_level(recs6, [ev], "L", LATCH_STATE)[0]
        lv, _ = run_level(d6, {k: [v] for k, v in ev.items()}, "plain", 16)
        check(f"simultaneous {label}: final state {comp(lv['L'])[-1]} == the VM's {vmv} == {expect}", comp(lv["L"])[-1] == vmv == expect, f"flex={comp(lv['L'])} vm={vmv}")

    print("a sentinel chain: accumulator (level) -> comparator -> latch SET (a level driving a level), count to 9 with the sentinel at >= 5")
    recs7 = [ram("XI", 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"], [], ["e"], step=1), cmp_("CMP", 1, 2, ["w"], ["e"], 5), latch("L", 1, 3, ["w"], [], [], [])]
    d7, r = build(tmp, "sentinel", recs7)
    check("sentinel chain generates on flex", r.returncode == 0, r.stderr.strip()[:240])
    wantc = comp([0] + vm_level(recs7, [{"XI": 1}] * 9, "L", LATCH_STATE))
    for mode, seed in (("plain", 17), ("stall", 18), ("stall", 19)):
        lv, _ = run_level(d7, {"XI": [1] * 9}, mode, seed, settle=120)
        check(f"mode={mode}: the latch reads {comp(lv['L'])} == the VM's {wantc} (0 until the count reaches 5, then 1)", comp(lv["L"]) == wantc == [0, 1], f"flex={comp(lv['L'])} vm={wantc}")

    print("MUTATION CONTROLS on the pulse gating: break it on purpose; the order-forcing / back-to-back modes must catch it")
    top2 = os.path.join(d2, json.load(open(os.path.join(d2, "ASSEMBLY.json")))["top"] + ".v")
    orig2 = open(top2).read()
    muts = [("the pulse is NOT gated by ready (a pulse can land while the cell is pending: counted, snapshot LOST)",
             r"(wire c_ACC_p_(?:inc|dec) = \([^;]*\)) & c_ACC_rdy;", r"\g<1>;"),
            ("the sources are acknowledged even when the cell is NOT ready (items consumed but lost)", r"assign (e\d+_a) = c_ACC_rdy;", r"assign \g<1> = 1'b1;")]
    for mi, (label, pat, rep) in enumerate(muts):
        txt = re.sub(pat, rep, orig2)
        assert txt != orig2, pat
        dm = os.path.join(tmp, f"mutl_{mi}")
        shutil.copytree(d2, dm)
        open(os.path.join(dm, os.path.basename(top2)), "w").write(txt)
        verdicts = []
        for mode, seed in (("plain", 4), ("stall", 5), ("stall", 6), ("skewfirst", 7), ("skewlast", 8)):
            lv, _ = run_level(dm, {"XI": [1] * ninc, "XD": [1] * ndec}, mode, seed)
            seq = comp(lv["ACC"])
            verdicts.append(seq[-1] == (5 * (ninc - ndec)) & 0xFFFFFFFF and all(v in reach for v in seq))
        check(f"mutant caught: {label}", not all(verdicts), f"verdicts {verdicts}")
    tops = os.path.join(d5, json.load(open(os.path.join(d5, "ASSEMBLY.json")))["top"] + ".v")
    origs = open(tops).read()
    txt = re.sub(r"\(e(\d+)_v & [A-Za-z0-9_]+\[0\]\)", r"e\1_v", origs)
    assert txt != origs
    dm = os.path.join(tmp, "mutl_set")
    shutil.copytree(d5, dm)
    open(os.path.join(dm, os.path.basename(tops)), "w").write(txt)
    lv, _ = run_level(dm, {"XS": even}, "plain", 14)
    check("mutant caught: a latch `set` that ignores bit 0 sets on an all-even stream (the correct latch stays 0)", comp(lv["L"]) != [0], f"mutant levels {comp(lv['L'])}")

    print("refusals: a constant or level source into a COUNTING / TOGGLING input is rate-dependent (the same rule as sub)")
    cases = (("a constant feeding an accumulator's inc", [ram("K", 1, 0, [], ["e"], preload_value=1), acc("ACC", 1, 1, ["w"], [], [])], "inc"),
             ("an accumulator (level) feeding another accumulator's inc", [ram("XI", 1, 0, [], ["e"]), acc("A1", 1, 1, ["w"], [], ["e"]), acc("A2", 1, 2, ["w"], [], [])], "inc"),
             ("a comparator-of-a-level feeding a latch's toggle", [ram("XI", 1, 0, [], ["e"]), acc("ACC", 1, 1, ["w"], [], ["e"]), cmp_("CMP", 1, 2, ["w"], ["e"], 3), latch("L", 1, 3, [], [], ["w"], [])], "toggle"))
    for label, recs8, role in cases:
        d8, r = build(tmp, "bad", recs8)
        check(f"refused on flex: {label}", r.returncode != 0 and "RATE" in r.stderr.upper() and role in r.stderr, r.stderr.strip()[:260])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
