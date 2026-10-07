"""tests/vm/test_priority_flex_v1.py -- ledger #1017: the PRIORITY core in a generated flex design (generator -> Verilog -> iverilog). Three source streams feed one priority cell (faces N, W, S), its
output goes to an exit ram. Checked: one item from each source offered at the same moment is served in RANK order (strict); in a long stream nothing is lost, duplicated or corrupted and every
source's own order is kept, through random input gaps and exit stalls, in both modes; weighted mode shares the output between the sources; the refusals (sequenced mode 2, the sub family, a constant
source) with their reasons. Requires iverilog."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]


def cli(*a):
    return subprocess.run(CLI + list(a), capture_output=True, text=True)


def ram(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down}, **kw)


def pri(mode=0, ranks=(1, 0, 2), faces=("n", "w", "s")):
    """P at (1,1): sources above (N), left (W) and below (S); ranks for n, w, s; output to the east."""
    cfg = {"upstream_mask": list(faces), "downstream_mask": ["e"], "scheduling_mode": mode}
    for f, rk in zip(("n", "w", "s"), ranks):
        cfg[f"priority_rank_{f}"] = rk
    return IcmV3Record(cell_id="P", row=1, col=1, core="priority", core_config=cfg)


def design(mode=0, ranks=(1, 0, 2), sources=("n", "w", "s")):
    recs = [pri(mode, ranks, tuple(sources)), ram("O", 1, 2, ["w"], ["e"])]
    if "n" in sources:
        recs.append(ram("E1", 0, 1, [], ["s"]))
    if "w" in sources:
        recs.append(ram("E2", 1, 0, [], ["e"]))
    if "s" in sources:
        recs.append(ram("E3", 2, 1, [], ["n"]))
    return recs


def build(tmp, name, recs, *extra):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", icm, "--output", d, *extra)


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




def streams_for(n, sources=("E1", "E2", "E3")):
    return {nm: [100 * (k + 1) + j for j in range(n)] for k, nm in enumerate(sources)}


def test_strict_rank_order_for_simultaneous_offers():
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, "pri_strict", design(0, (1, 0, 2)))
    assert r.returncode == 0, r.stderr[-600:] + r.stdout[-600:]
    _, got = run_level(d, {"E1": [11], "E2": [22], "E3": [33]}, "plain", settle=80)
    assert got["O"] == [22, 11, 33], got        # W (rank 0), then N (rank 1), then S (rank 2)


@pytest.mark.parametrize("mode,seed", [("plain", 1), ("stall", 2), ("stall", 3), ("skewfirst", 4)])
@pytest.mark.parametrize("pmode", (0, 1))
def test_stream_nothing_lost_duplicated_or_reordered(pmode, mode, seed):
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, f"pri_s{pmode}", design(pmode, (1, 3, 2)))
    assert r.returncode == 0, r.stderr[-600:] + r.stdout[-600:]
    S = streams_for(12)
    _, got = run_level(d, S, mode, seed=seed, settle=200, cycles=12000)
    out = got["O"]
    allv = sorted(v for s in S.values() for v in s)
    assert sorted(out) == allv, (len(out), len(allv))
    for nm, vals in S.items():                                   # every source's own order is kept
        assert [v for v in out if v in vals] == vals, nm


def test_weighted_shares_the_output():
    """Weighted (surplus round robin): north weight 3, west weight 1, both long streams: the north's items come out about three times as often while both still offer."""
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, "pri_w", design(1, (3, 1, 0), ("n", "w")))
    assert r.returncode == 0, r.stderr[-600:] + r.stdout[-600:]
    S = {"E1": [1000 + j for j in range(24)], "E2": [2000 + j for j in range(24)]}
    _, got = run_level(d, S, "plain", settle=200, cycles=8000)
    first = got["O"][:16]
    n_first = sum(1 for v in first if v < 2000)
    assert 10 <= n_first <= 13, (n_first, first)


def test_refusals_have_reasons():
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, "pri_seq", design(2, (0, 1, 2)))
    assert r.returncode != 0 and "sequenced channel" in (r.stderr + r.stdout)
    d, r = build(tmp, "pri_sub", design(0, (1, 0, 2)), )
    assert r.returncode == 0
    icm = os.path.join(tmp, "pri_strict_sub.icm")
    IcmV3File(name="x", records=design(0, (1, 0, 2))).save(icm)
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_sub"))
    assert r.returncode != 0 and "priority" in (r.stderr + r.stdout)
    recs = design(0, (1, 0, 2))
    recs = [x for x in recs if x.cell_id != "E1"] + [ram("E1", 0, 1, [], ["s"], preload_value=5)]
    d, r = build(tmp, "pri_const", recs)
    assert r.returncode != 0 and "constant" in (r.stderr + r.stdout)


def test_generated_design_uses_the_core_and_the_test_bites():
    """The generated top instantiates priority_cell_v4sa with the configuration word built from the ICM, the weighted sequence is exactly 3:1 (n n n w), and a defective copy of the core in the
    generated folder changes the result (so the integration tests above can fail)."""
    tmp = tempfile.mkdtemp()
    d, r = build(tmp, "pri_bite", design(1, (3, 1, 0), ("n", "w")))
    assert r.returncode == 0
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    top = open(os.path.join(d, rec["top"] + ".v")).read()
    inst = [l for l in top.splitlines() if "priority_cell_v4sa #" in l]
    assert len(inst) == 1 and "cfg_data(32'h00001439)" in inst[0], inst   # mask n (bit 0) + w (bit 3) = 0x9; rank_n = 3 at [5:4] = 0x30; rank_w = 1 at [11:10] = 0x400; mode 1 at bit 12 = 0x1000
    S = {"E1": [1000 + j for j in range(24)], "E2": [2000 + j for j in range(24)]}
    _, good = run_level(d, S, "plain", settle=200, cycles=8000)
    exp = []
    n_i = w_i = 0
    for k in range(48):
        if k % 4 == 3 and w_i < 24:
            exp.append(2000 + w_i); w_i += 1
        elif n_i < 24:
            exp.append(1000 + n_i); n_i += 1
        else:
            exp.append(2000 + w_i); w_i += 1
    assert good["O"][:16] == exp[:16], good["O"][:16]
    f = os.path.join(d, "priority_cell_v4sa.v")
    src = open(f).read()
    assert "scheduling_mode <= cfg_data[12];" in src
    open(f, "w").write(src.replace("scheduling_mode <= cfg_data[12];", "scheduling_mode <= 1'b0;"))
    _, bad = run_level(d, S, "plain", settle=200, cycles=8000)
    assert bad["O"][:16] != good["O"][:16]
