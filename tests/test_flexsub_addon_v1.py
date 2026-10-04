#!/usr/bin/env python3
"""tests/test_flexsub_addon_v1.py -- the addon chain (mask / shift / lane-cut / invert) as pure WIRING on the sub family (Alan #939).

Run: python3 tests/test_flexsub_addon_v1.py      (needs iverilog)
Alan: "now the sub variant is fully fixed so the mask like the shift just becomes wiring, same for the invert."
The VM applies apply_addons(value, addon_config) to EVERY core's offered value except nano (nibble_mask -> fine shift -> coarse lane shift
(+ lane_cut on right shifts) -> invert), a pure function of 32 bits with constant config -- so each output bit is a constant, an input bit or its
inverse: no cell and no latency. Checked three ways: (1) the symbolic wiring map == the VM's own apply_addons over every mask pattern, every shift
amount, both directions, all fine/lane-cut values, invert and random configs; (2) generated RTL == the real VM for each addon on a relay, and on an
adder, a constant source and a branch; (3) the refusals (a nano, an unknown field).
"""
import json
import os
import random
import re
import itertools
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
import unicell_super_automaton_v1 as vm  # noqa: E402
import flexsub_icm_generate_v1 as gen  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
passed = failed = 0
VALUES = [0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0xDEADBEEF, 0x12345678, 0xA5A5A5A5, 0x0F0F0F0F, 0xF0F0F0F0]


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


def ram(cid, r, c, up, down, addon=None, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down},
                       addon_config=dict(addon or {}), **kw)


def rtl(folder, events, cycles):
    """events: [(cycle, {entry suffix: value})] -> {exit suffix: [(cycle, value)]} (valid cycles)."""
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


def vm_each(records, entry, values, exits, settle=8, run=26):
    """For each value: inject, run, read every exit that received something (clear it). Returns [{exit: value}]."""
    grid = vm.SuperGrid(records)
    for _ in range(settle):
        grid.tick()
    er = next(r for r in records if r.cell_id == entry)
    xs = {x: grid.cells[(next(r for r in records if r.cell_id == x).row, next(r for r in records if r.cell_id == x).col)] for x in exits}
    out = []
    for v in values:
        grid.inject(er.row, er.col, v & 0xFFFFFFFF)
        for _ in range(run):
            grid.tick()
        got = {}
        for x, cell in xs.items():
            if cell.ram_data_valid:
                got[x] = cell.ram_data_reg
                cell.ram_data_valid = False
        out.append(got)
    return out


def rtl_each(d, entry, values, gap=24):
    res = rtl(d, [(k * gap, {entry: v}) for k, v in enumerate(values)], len(values) * gap + 8)
    out = []
    for k in range(len(values)):
        out.append({n: next(v for c, v in hs if k * gap <= c < (k + 1) * gap) for n, hs in res.items() if any(k * gap <= c < (k + 1) * gap for c, _ in hs)})
    return out


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "sub", "--icm", icm, "--output", d)


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

print("1. the wiring map IS the VM's addon chain (apply_addons), over a large structured + random config space")
rnd = random.Random(939)
vals = VALUES + [rnd.getrandbits(32) for _ in range(30)]
bad, n = [], 0
def same(cfg):
    bm = gen.addon_bit_map(cfg)
    return all(gen.addon_apply(bm, v) == vm.apply_addons(v, cfg) for v in vals)
for nm, me in itertools.product(range(256), (0, 1)):
    n += 1
    if not same({"mask_en": me, "nibble_mask": nm}):
        bad.append(("mask", nm, me))
for en, dr, fine, amt, lc, inv in itertools.product((0, 1), (0, 1), range(4), range(32), range(8), (0, 1)):
    n += 1
    cfg = {"shift_en": en, "direction": dr, "shift_fine": fine, "shift_amt": amt, "lane_cut": lc, "invert_en": inv}
    if not same(cfg):
        bad.append(cfg)
for _ in range(2000):
    cfg = {"mask_en": rnd.getrandbits(1), "nibble_mask": rnd.getrandbits(8), "shift_en": rnd.getrandbits(1), "direction": rnd.getrandbits(1),
           "shift_fine": rnd.getrandbits(2), "shift_amt": rnd.choice([0, 1, 2, 4, 8, 12, 16, 20, 24, 28, rnd.getrandbits(5)]),
           "lane_cut": rnd.getrandbits(3), "invert_en": rnd.getrandbits(1)}
    n += 1
    if not same(cfg):
        bad.append(cfg)
check(f"{n} configurations x {len(vals)} values: the wiring map equals the VM's apply_addons (all 256 nibble masks, every shift amount incl. the "
      f"unsupported ones, both directions, every fine/lane-cut value, invert, random mixes)", not bad, str(bad[:2]))
check("a config that does nothing (unsupported shift amount, nothing else) is the identity map", gen.addon_is_identity(gen.addon_bit_map({"shift_en": 1, "shift_amt": 3})))
check("a config with the shift disabled ignores its amount/direction", gen.addon_is_identity(gen.addon_bit_map({"shift_en": 0, "shift_amt": 8, "direction": 1, "lane_cut": 7})))

tmp = tempfile.mkdtemp(prefix="addon_")
try:
    print("2. generated RTL == the real VM: each addon on a ram relay (X -> R[addon] -> E), 10 edge/random values each")
    configs = {
        "mask": {"mask_en": 1, "nibble_mask": 0b10100101},
        "invert": {"invert_en": 1},
        "shift_left": {"shift_en": 1, "direction": 0, "shift_amt": 8},
        "shift_right": {"shift_en": 1, "direction": 1, "shift_amt": 4},
        "fine_only": {"shift_en": 1, "direction": 0, "shift_fine": 3},
        "lane_cut": {"shift_en": 1, "direction": 1, "shift_amt": 8, "lane_cut": 5},
        "everything": {"mask_en": 1, "nibble_mask": 0x18, "shift_en": 1, "direction": 1, "shift_fine": 2, "shift_amt": 12, "lane_cut": 2, "invert_en": 1},
        "unsupported_amount": {"shift_en": 1, "shift_amt": 3},
    }
    for name, ad in configs.items():
        recs = [ram("X", 1, 0, [], ["e"]), ram("R", 1, 1, ["w"], ["e"], addon=ad), ram("E", 1, 2, ["w"], [])]
        d, r = build(tmp, name, recs)
        if r.returncode:
            check(f"{name}: generates", False, r.stderr.strip()[:300])
            continue
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        no_cells = not any("shift_stage" in f for f in rec["files"])
        want = [g.get("E") for g in vm_each(recs, "X", VALUES, ["E"])]
        got = [g.get("E") for g in rtl_each(d, "X", VALUES)]
        wired = "R" in rec["addon_wiring"]
        exp_wired = not gen.addon_is_identity(gen.addon_bit_map(ad))
        check(f"{name}: RTL == VM on all {len(VALUES)} values; no extra cell ({'wiring' if wired else 'identity: nothing emitted'}); latency {list(rec['output_latency_cycles'].values())[0]}",
              got == want and None not in got and no_cells and wired == exp_wired, f"rtl={[hex(x) for x in got if x is not None][:4]} vm={[hex(x) for x in want if x is not None][:4]} wired={wired}")

    print("   the addon adds NO latency (wiring): a relay with an addon has the same latency as one without")
    d0, _ = build(tmp, "plain", [ram("X", 1, 0, [], ["e"]), ram("R", 1, 1, ["w"], ["e"]), ram("E", 1, 2, ["w"], [])])
    dA, _ = build(tmp, "wired", [ram("X", 1, 0, [], ["e"]), ram("R", 1, 1, ["w"], ["e"], addon=configs["everything"]), ram("E", 1, 2, ["w"], [])])
    l0 = list(json.load(open(os.path.join(d0, "ASSEMBLY.json")))["output_latency_cycles"].values())
    lA = list(json.load(open(os.path.join(dA, "ASSEMBLY.json")))["output_latency_cycles"].values())
    check(f"latency with the full addon chain {lA} == latency without {l0}", l0 == lA)

    print("   addons on OTHER cores: an adder (invert), a constant source (shift left 2), a branch (invert on both outputs)")
    # adder: XB -> ADD (west); XA -> RA -> ADD (north). commutative, so the order tie-break is irrelevant; output inverted
    recs = [ram("XB", 1, 0, [], ["e"]), ram("XA", 0, 0, [], ["e"]), ram("RA", 0, 1, ["w"], ["s"]),
            IcmV3Record(cell_id="ADD", row=1, col=1, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}, addon_config={"invert_en": 1}),
            ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "add_inv", recs)
    check("adder with invert generates", r.returncode == 0, r.stderr.strip()[:300])
    if r.returncode == 0:
        vals = [(3, 4), (0, 0), (0xFFFFFFFF, 1), (100, 200)]
        want, got = [], []
        grid = vm.SuperGrid(recs)
        for _ in range(8):
            grid.tick()
        ec = grid.cells[(1, 2)]
        for xa, xb in vals:
            grid.inject(0, 0, xa)
            grid.inject(1, 0, xb)
            for _ in range(30):
                grid.tick()
            want.append(ec.ram_data_reg if ec.ram_data_valid else None)
            ec.ram_data_valid = False
        res = rtl(d, [(k * 24, {"XA": xa, "XB": xb}) for k, (xa, xb) in enumerate(vals)], len(vals) * 24 + 8)["E"]
        got = [next((v for c, v in res if k * 24 <= c < (k + 1) * 24), None) for k in range(len(vals))]
        exp = [(~(xa + xb)) & 0xFFFFFFFF for xa, xb in vals]
        check(f"adder + invert: ~(a+b): RTL == VM == arithmetic", got == want == exp, f"rtl={got} vm={want} exp={exp}")
    # constant with a shift: K (5, <<2 = 20) at the north of ADD, X -> Rx -> ADD (west)
    recs = [ram("K", 0, 1, [], ["s"], addon={"shift_en": 1, "direction": 0, "shift_amt": 2}, preload_value=5),
            ram("X", 1, -1, [], ["e"]) if False else ram("X", 2, 0, [], ["n"]), ram("Rx", 1, 0, ["s"], ["e"]),
            IcmV3Record(cell_id="ADD", row=1, col=1, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}),
            ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "const_shift", recs)
    check("a constant source with an addon generates", r.returncode == 0, r.stderr.strip()[:300])
    if r.returncode == 0:
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        xs = [0, 1, 1000, 0xFFFFFFF0]
        # A FRESH VM grid per item: in the VM a preloaded ram that is not fixed_mode is SINGLE-SHOT -- it offers its constant once, so within one
        # run only the first item would see it (a stream shows [20, None, 1001, None]). The generator reads a preload_value source as an always-valid
        # constant (#931), which is what a per-call constant means; the two agree for one call per grid.
        want = [vm_each(recs, "X", [x], ["E"])[0].get("E") for x in xs]
        got = [g.get("E") for g in rtl_each(d, "X", xs)]
        stream = [g.get("E") for g in vm_each(recs, "X", xs, ["E"])]
        check(f"constant 5 shifted left 2 (= 20) + X, one call per VM grid: RTL {got} == VM {want} == X + 20", got == want == [(x + 20) & 0xFFFFFFFF for x in xs], f"rtl={got} vm={want}")
        check("FINDING: within ONE VM run a non-fixed preloaded ram feeds only the first item (the VM's constant is single-shot)", stream[0] == 20 and stream != got, f"vm stream={stream}")

    # branch: constant reference 10 (merge of a constant and a stream, the cordic pattern); an invert addon on BOTH output ports
    def bcfg(**kw):
        cfg = {"upstream_dir": 3, "rolling_mode": 0}
        for n, rt in (("low", ["s"]), ("equal", ["s"]), ("high", ["n"])):
            cfg.update({f"value_source_{n}": 0, f"fixed_value_{n}": 0, f"emit_{n}": 1, f"route_{n}": rt})
        return cfg
    recs = [ram("X", 2, 0, [], ["e"]), ram("Z", 1, 1, [], ["s"], preload_value=10), ram("M", 2, 1, ["n", "w"], ["e"]),
            IcmV3Record(cell_id="B", row=2, col=2, core="branch", core_config=bcfg(), addon_config={"invert_en": 1}),
            ram("O1", 3, 2, ["n"], []), ram("O2", 1, 2, ["s"], [])]
    d, r = build(tmp, "br_inv", recs)
    check("a branch with an invert addon generates", r.returncode == 0, r.stderr.strip()[:300])
    if r.returncode == 0:
        xs = [3, 10, 11, 0xFFFFFFFB, 0x7FFFFFFF]
        want = [vm_each(recs, "X", [x], ["O1", "O2"])[0] for x in xs]          # a fresh grid per item (the constant reference is single-shot in the VM)
        got = rtl_each(d, "X", xs)
        check(f"branch(ref 10) + invert on both output ports: low/equal -> ~x on O1, high -> ~x on O2: RTL == VM",
              got == want and got[0] == {"O1": (~3) & 0xFFFFFFFF} and got[2] == {"O2": (~11) & 0xFFFFFFFF}, f"rtl={got} vm={want}")

    print("3. refusals")
    recs = [ram("X", 1, 0, [], ["e"]), ram("R", 1, 1, ["w"], ["e"], addon={"mask_en": 1, "nibble_mask": 1}), ram("E", 1, 2, ["w"], [])]
    recs[1].addon_config["bogus"] = 1
    icm = os.path.join(tmp, "bogus.icm")
    try:
        IcmV3File(name="b", records=recs).save(icm)
        r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_bogus"))
        check("an unknown addon field is refused (by the format or the generator)", r.returncode != 0, r.stderr.strip()[:200])
    except ValueError as e:
        check("an unknown addon field is refused (by the ICM format itself, before it reaches the generator)", "bogus" in str(e) or "unknown" in str(e).lower(), str(e)[:200])
    nano = IcmV3Record(cell_id="N", row=1, col=1, core="nano", core_config={"routing_mask": ["e"], "topology": 0x2C}, addon_config={"invert_en": 1})
    recs = [ram("A", 1, 0, [], ["e"]), nano, ram("E", 1, 2, ["w"], [])]
    d, r = build(tmp, "nano_addon", recs)
    check("an addon on a nano is refused with the reason (the VM's offer pass skips nano)", r.returncode != 0 and "nano" in r.stderr and "addon" in r.stderr, r.stderr.strip()[:240])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
