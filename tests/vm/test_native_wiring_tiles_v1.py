"""tests/vm/test_native_wiring_tiles_v1.py -- ledger #1165: the cross / corner tile as a NATIVE cell in the flex (v4sa) and sub (v4s) families.
  1. each native module equals the relay slices it replaces, clock for clock on every output (random traffic; flex also on every ack), at three widths for flex; a deliberately wrong reference is caught;
  2. the generated flex design contains one native cell per tile and no slice relays, and gives the same streams as the relay version (UNICELL_NATIVE_TILES=0) under random stalls;
  3. the generated SUB design with native tiles carries two streams through a cross tile and through a corner tile (both turns), words equal, order kept.
Requires iverilog."""
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SUBV = os.path.join(ROOT, "sub", "verilog")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import test_cross_tile_v1 as xt  # noqa: E402
import test_corner_tile_v1 as ct  # noqa: E402
from fp_block_runner_v1 import run_rtl  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="nativetile_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _bench(tmp, tb, files, params):
    out = os.path.join(tmp, tb + "_" + "_".join(f"{k}{v}" for k, v in params.items()) + ".vvp")
    cmd = ["iverilog", "-g2012", "-o", out] + [f"-P{tb}.{k}={v}" for k, v in params.items()] + [os.path.join(SUBV, f) for f in [tb + ".v"] + files]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:800]
    o = subprocess.run(["vvp", out], capture_output=True, text=True).stdout
    return int(re.search(r"MISMATCHES (\d+)", o).group(1)), o


@pytest.mark.parametrize("width", [32, 18, 40])
def test_flex_native_equals_the_relays_clock_for_clock(tmp, width):
    n, o = _bench(tmp, "tb_corner_equiv_v4sa", ["corner_cell_v4sa.v", "ram_cell_v4sa.v"], {"WIDTH": width, "BREAK": 0})
    assert n == 0 and "RESULT PASS" in o
    n, o = _bench(tmp, "tb_corner_equiv_v4sa", ["corner_cell_v4sa.v", "ram_cell_v4sa.v"], {"WIDTH": width, "BREAK": 1})
    assert n > 1000 and "caught" in o                      # bite: a wrongly wired reference differs on thousands of clocks


def test_sub_native_equals_the_relays_clock_for_clock(tmp):
    n, o = _bench(tmp, "tb_corner_equiv_v4s", ["corner_cell_v4s.v", "ram_cell_v4s.v"], {"BREAK": 0})
    assert n == 0 and "RESULT PASS" in o
    n, o = _bench(tmp, "tb_corner_equiv_v4s", ["corner_cell_v4s.v", "ram_cell_v4s.v"], {"BREAK": 1})
    assert n > 1000 and "caught" in o


def _flex_build(tmp, name, recs, native):
    env = dict(os.environ, UNICELL_NATIVE_TILES="1" if native else "0")
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm, "--output", d], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[:800]
    return open(os.path.join(d, f"icm_{name}_flex.v")).read()


def test_flex_design_uses_one_native_cell_per_tile_and_no_slice_relays(tmp):
    v_nat = _flex_build(tmp, "n_nat", xt.tile("cross").records(), True)
    v_old = _flex_build(tmp, "n_old", xt.tile("cross").records(), False)
    assert len(re.findall(r"^cross_cell_v4sa ", v_nat, re.M)) == 1 and "c_X__" in v_nat
    assert not re.search(r"ram_cell_v4sa #\(.*\) c_X__", v_nat)
    assert "cross_cell_v4sa" not in v_old and len(re.findall(r"ram_cell_v4sa #\(.*\) c_X__", v_old)) == 2


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_flex_native_gives_the_relay_version_streams(tmp, mode):
    A, B = xt.streams(20, 9)
    os.environ["UNICELL_NATIVE_TILES"] = "0"
    try:
        old = run_rtl(tmp, "ab_old_" + mode, xt.tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, mode, settle=400)
    finally:
        os.environ["UNICELL_NATIVE_TILES"] = "1"
    new = run_rtl(tmp, "ab_new_" + mode, xt.tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, mode, settle=400)
    assert new == old and new["A"] == A and new["B"] == B


# ---------- the sub family, end to end ----------
def _sub_run(tmp, name, recs, ent, ex, native=True):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "s_" + name)
    env = dict(os.environ, UNICELL_NATIVE_TILES="1" if native else "0")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "sub", "--icm", icm, "--output", d], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[:800]
    top = f"icm_{name}_sub"
    text = open(os.path.join(d, top + ".v")).read()
    n = len(next(iter(ent.values())))
    L = ["`timescale 1ns/1ps", "module tb;", "reg clk=0, rst=1, cfg_valid=0; always #5 clk=~clk;", "integer cyc=0;"]
    for c in ent:
        L += [f"reg [31:0] in_{c}_data=0; reg in_{c}_valid=0;"]
    for c in ex.values():
        L += [f"wire [31:0] out_{c}_data; wire out_{c}_valid;"]
    L += [f"{top} dut(.clk(clk),.rst(rst),.cfg_valid(cfg_valid)," + ",".join([f".in_{c}_data(in_{c}_data),.in_{c}_valid(in_{c}_valid)" for c in ent] + [f".out_{c}_data(out_{c}_data),.out_{c}_valid(out_{c}_valid)" for c in ex.values()]) + ");"]
    for c, vals in ent.items():
        L += [f"reg [31:0] mem_{c} [0:{n - 1}];"] + [f"initial mem_{c}[{k}] = 32'd{v};" for k, v in enumerate(vals)]
    L += ["always @(posedge clk) begin cyc <= cyc + 1; if (cyc == 3) rst <= 0; if (cyc == 6) cfg_valid <= 1; if (cyc == 7) cfg_valid <= 0;"]
    for c in ent:
        L += [f"  if (cyc >= 12 && cyc < {12 + n}) begin in_{c}_data <= mem_{c}[cyc-12]; in_{c}_valid <= 1; end else in_{c}_valid <= 0;"]
    for k, c in ex.items():
        L += [f"  if (out_{c}_valid) $display(\"OUT {k} %0d\", out_{c}_data);"]
    L += [f"  if (cyc == {12 + n + 60}) $finish; end", "endmodule"]
    tbp = os.path.join(d, "tb.v")
    open(tbp, "w").write("\n".join(L) + "\n")
    files = [top + ".v"] + [f for f in os.listdir(d) if f.endswith(".v") and f not in (top + ".v", "tb.v")]
    vvp = os.path.join(d, "a.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-o", vvp, "tb.v"] + files, capture_output=True, text=True, cwd=d)
    assert r.returncode == 0, r.stderr[:1000]
    out = subprocess.run(["vvp", vvp], capture_output=True, text=True, cwd=d).stdout
    got = {k: [] for k in ex}
    for m in re.finditer(r"OUT (\w+) (\d+)", out):
        got[m.group(1)].append(int(m.group(2)))
    return got, text


def test_sub_cross_native_two_streams(tmp):
    A, B = xt.streams(20, 11)
    got, text = _sub_run(tmp, "sx", xt.tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"})
    assert len(re.findall(r"^cross_cell_v4s ", text, re.M)) == 1
    assert got["A"] == A and got["B"] == B


@pytest.mark.parametrize("turn,ins", [(0, ("W", "E")), (0, ("S", "N")), (1, ("W", "E")), (1, ("N", "S"))])
def test_sub_corner_native_turns(tmp, turn, ins):
    g, outs = ct.tile(turn, ins)
    S = ct.streams(16, 5)
    got, text = _sub_run(tmp, f"sc{turn}{''.join(ins)}", g.records(), {f"{a}0": S[i] for i, a in enumerate(ins)}, {f"o{i}": f"{a}0" for i, a in enumerate(outs)})
    assert len(re.findall(r"^corner_cell_v4s ", text, re.M)) == 1
    assert [got[f"o{i}"] for i in range(2)] == S


def test_sub_native_equals_relay_version_bite(tmp):
    """Bite: the relay version (UNICELL_NATIVE_TILES=0) gives the same streams, and a wrong-turn tile would deliver them swapped (corner test has the flex form of this)."""
    A, B = xt.streams(20, 12)
    new, _ = _sub_run(tmp, "sab1", xt.tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, True)
    old, t = _sub_run(tmp, "sab0", xt.tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, False)
    assert "cross_cell_v4s" not in t and new == old
