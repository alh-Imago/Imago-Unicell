"""tests/vm/test_fp_normalise_clamp_v1.py -- ledger #1005: the CLAMPED left-normalise (`fp_assembler_v1.normalise_chain_clamped`), the block that makes subnormal RESULTS possible. The total
shift is min(leading zeros, EXPIN - 1), so the exponent that comes out is never below 1 (a result that would go lower stays unnormalised: a subnormal). Five stages (16, 8, 4, 2, 1), each with
its own exponent-budget test; every connection a direct neighbour link, no router. Checked against the Python rule in the generated RTL (plain and random stalls) and in FlexGrid.
The window is the adder's (28 bits). Requires iverilog."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
import fp_assembler_v1 as fa  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402

WIDE = fa.FpFormat("wide28", 28, 8, 32)
S = 28


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="nrmclamp_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def build():
    g = Grid(rows=20, cols=70)
    b = fa.normalise_chain_clamped(g, WIDE, "N", 4, 4)
    r, c = g.pos(b.entries["EXPIN"])
    g.add("E0", r, c - 1)                                  # a one-relay entry for EXPIN: in the adder the two entries arrive at different times; standing alone they would tie at the first stage
    g.link("E0", b.entries["EXPIN"])
    assert g.problems() == []
    return g, b


def want(v, e):
    lz = S - v.bit_length() if v else S + 10
    sh = min(lz, e - 1, 31)
    return (v << sh) & 0xFFFFFFFF, (e - sh) & 0xFFFFFFFF


def vectors():
    r = random.Random(11)
    vs, es = [], []
    for e in (1, 2, 3, 5, 17, 18, 24, 25, 29, 30, 31, 32, 33, 40, 100, 255):
        for v in (1, 2, 3, 0x1234, 1 << 27, (1 << 28) - 1, 0, 1 << 11, 1 << 12, 1 << 20):
            vs.append(v)
            es.append(e)
    for _ in range(40):
        vs.append(r.getrandbits(r.randrange(0, S + 1)))
        es.append(r.choice([1, 2, r.randrange(1, 40), r.randrange(1, 300)]))
    return vs, es


def test_the_clamp_really_bites():
    """The vectors include cases where the exponent budget, not the leading zeros, decides the shift."""
    vs, es = vectors()
    n = sum(1 for v, e in zip(vs, es) if v and e - 1 < S - v.bit_length())
    assert n >= 25


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_clamped_normalise_rtl(tmp, mode):
    g, b = build()
    vs, es = vectors()
    got = run_rtl(tmp, "nrmclamp", g.records(), {b.entries["V"]: vs, "E0": es}, b.exits, mode, settle=40000)
    bad = [(hex(v), e, got["NORM"][i], got["EXPOUT"][i], want(v, e)) for i, (v, e) in enumerate(zip(vs, es)) if (got["NORM"][i], got["EXPOUT"][i]) != want(v, e)]
    assert not bad, bad[:4]


def test_clamped_normalise_flexgrid():
    g, b = build()
    vs = [3, 0x1234, 1, 1 << 27, 0xFF]
    es = [2, 30, 5, 1, 9]
    consts = b.consts
    got = run_vm(g.records(), {b.entries["V"]: vs, "E0": es}, b.exits, consts, ticks=900)
    for i, (v, e) in enumerate(zip(vs, es)):
        assert (got["NORM"][i], got["EXPOUT"][i]) == want(v, e), (hex(v), e)
