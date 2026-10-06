"""tests/vm/test_fp32_normalise_chain_v1.py -- ledger #984: the full LEFT-NORMALISE of a 24-bit significand from real flex cells: five conditional-shift stages (16, 8, 4, 2, 1; see
test_fp32_normalise_stage_v1.py) in a row, plus the EXPONENT ADJUSTMENT: each stage's 0/1 word r_s is shifted left by log2(s) and the five are added (S = sum r_s * s), so
the shift count is lz = 31 - S and  exp_out = exp_in - lz = exp_in + S - 31  (two more adders, the constant added as 2^32 - 31).

Compared (generated RTL, plain and random stalls; and FlexGrid) with the Python reference: leading-zero count of the 24-bit significand, normalised significand, adjusted exponent.
(A significand of 0 has no leading one: it passes through every stage unchanged and the count is 31 -- the same input is excluded from the exponent check, as fp32 zero is handled before this.)
Requires iverilog.
"""
import copy
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from fp32_stage_builder_v1 import Grid  # noqa: E402

M32 = 0xFFFFFFFF
STAGES = (16, 8, 4, 2, 1)
LOG2 = {16: 4, 8: 3, 4: 2, 2: 1, 1: 0}
PITCH = 9
TAP = {16: (12, 0), 8: (4, 1), 4: (2, 0), 2: (1, 0), 1: (1, 0)}      # (coarse tap, fine) of the right shift s - log2(s) = 12, 5, 2, 1, 1


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32chain_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def build():
    g = Grid(rows=14, cols=PITCH * 5 + 14)
    consts, prev_mul = {}, None
    for k, s in enumerate(STAGES):
        c0, p = PITCH * k, f"S{s}."
        g.add(p + "V", 3, 2 + c0)
        g.add(p + "CMP", 2, 2 + c0, "comparator", {"threshold": 1 << (24 - s)})
        g.add(p + "T", 3, 4 + c0, addon={"shift_en": 1, "direction": 1, "shift_amt": TAP[s][0], "shift_fine": TAP[s][1]})   # (r_s << s) >> (s - log2 s) = r_s << log2(s): this stage's share of the count; fed from R1 (CMP's four faces are full)
        g.add(p + "K", 1, 1 + c0, preload=1 << s)
        g.add(p + "AD", 1, 2 + c0, "adder")
        g.add(p + "SUBF", 1, 3 + c0, "adder", {"subtract_mode": 1})
        g.add(p + "RS", 2, 3 + c0, addon={"shift_en": 1, "direction": 0, "shift_amt": s})
        g.add(p + "R1", 2, 4 + c0)
        g.add(p + "R2", 1, 4 + c0)
        g.add(p + "MUL", 0, 3 + c0, "mul")
        consts[p + "K"] = 1 << s
        for a, b in (("V", "CMP"), ("CMP", "AD"), ("K", "AD"), ("AD", "SUBF"), ("CMP", "RS"), ("RS", "R1"), ("R1", "R2"), ("R1", "T"), ("R2", "SUBF"), ("SUBF", "MUL")):
            g.link(p + a, p + b)
    # the exponent adjustment runs along row 5 under the stages: A_k (k = 1..4, under stage k) adds stage k's T to the running sum from the stage before; T leaves its stage straight DOWN
    for k in range(1, 5):
        g.add(f"A{k}", 5, 4 + PITCH * k, "adder")
    for k, s in enumerate(STAGES):
        if k:
            g.route(f"S{s}.T", f"A{k}")
    g.route(f"S{STAGES[0]}.T", "A1")
    for k in range(1, 4):
        g.route(f"A{k}", f"A{k + 1}")
    X = PITCH * 4 + 4
    g.add("E1", 5, X + 2, "adder")
    g.route("A4", "E1")
    g.add("EXPIN", 6, X + 2)
    g.link("EXPIN", "E1")
    g.add("E2", 5, X + 4, "adder")
    g.route("E1", "E2")
    g.add("C31", 6, X + 4, preload=(1 << 32) - 31)
    g.link("C31", "E2")
    g.add("EXPOUT", 5, X + 5)
    g.link("E2", "EXPOUT")
    # the value chain: stage k's multiplier -> stage k+1's V
    for k, s in enumerate(STAGES):
        g.route(f"S{s}.V", f"S{s}.MUL", avoid=[(0, 4 + PITCH * k)])
    for k in range(4):
        g.route(f"S{STAGES[k]}.MUL", f"S{STAGES[k + 1]}.V")
    g.add("NORM", 0, PITCH * 4 + 6)
    g.route("S1.MUL", "NORM")
    consts["C31"] = (1 << 32) - 31
    return g, consts


def lz24(v):
    return 24 - v.bit_length() if v else 24


def normalise(v):
    s = 0
    for st in STAGES:
        if v < (1 << (24 - st)):
            v <<= st
            s += st
    return v, s


def run_vm(recs, streams, consts, exits, ticks=900):
    recs = [type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config, io_name=r.io_name, preload_value=None) if r.cell_id in consts else r for r in recs]
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = {k: [] for k in exits}
    for i in range(len(next(iter(streams.values())))):
        for name, vals in streams.items():
            g.inject(*pos[name], vals[i])
        for k, kv in consts.items():
            g.inject(*pos[k], kv)
        for _ in range(ticks):
            g.tick()
            for e in exits:
                c = g.cells[pos[e]]
                if c.ram_data_valid:
                    seen[e].append(c.ram_data_reg)
                    c.ram_data_valid = False
    return seen


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_left_normalise_and_exponent_adjust(tmp, mode):
    g, consts = build()
    recs = g.records()
    r = random.Random(3)
    sigs = [(1 << 24) - 1, 1 << 23, 1, 2, 3, 0xFF, 0x100, 0x1234, 0x80, 0x7FFF, 0xABCDE] + [r.getrandbits(r.randrange(1, 25)) or 1 for _ in range(20)]
    exps = [r.randrange(40, 200) for _ in sigs]
    d, res = h.build(tmp, f"chain_{mode}", recs)
    assert res.returncode == 0, res.stderr[:1500]
    # the entries are the first stage's V and EXPIN
    _, got = h.run_level(d, {"S16_V": sigs, "EXPIN": exps}, mode, 4, settle=3000)
    for k, (v, e) in enumerate(zip(sigs, exps)):
        nv, s_total = normalise(v)
        assert nv == v << lz24(v) and s_total == lz24(v)
        assert got["NORM"][k] == nv, (k, hex(v))
        assert got["EXPOUT"][k] == (e - s_total) & M32, (k, hex(v), e)
    vm = run_vm(recs, {"S16.V": sigs, "EXPIN": exps}, consts, ["NORM", "EXPOUT"])
    assert vm == {"NORM": got["NORM"], "EXPOUT": got["EXPOUT"]}
