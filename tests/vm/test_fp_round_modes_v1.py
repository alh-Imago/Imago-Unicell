"""tests/vm/test_fp_round_modes_v1.py -- ledger #1007: ROUNDING MODES from cells. Part 1: the rounding block alone (`fp_assembler_v1.round_mode`) in all five IEEE modes against a Python rule, in
the generated RTL (plain + random stalls) and FlexGrid. Part 2 (below, added with the adder): the whole adder per mode against `fp_round_ref_v1.add_ref`. Requires iverilog."""
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
import fp_add_v1 as fadd  # noqa: E402
from fp_round_ref_v1 import add_ref, MODES  # noqa: E402
import test_fp_special_v1 as sp  # noqa: E402

FMT = fa.FP32
LOW = 4


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fpround_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def block(mode):
    g = Grid(rows=20, cols=40)
    b = fa.round_mode(g, FMT, mode, "RN", 4, 4, low=LOW)
    g.balance()
    assert g.problems() == []
    return g, b


def rule(mode, x, sgn):
    sig, low = x >> LOW, x & ((1 << LOW) - 1)
    guard, sticky = (low >> (LOW - 1)) & 1, int((low & ((1 << (LOW - 1)) - 1)) != 0)
    if mode == "rne":
        up = guard and (sticky or sig & 1)
    elif mode == "rna":
        up = guard
    elif mode == "rtz":
        up = 0
    elif mode == "rup":
        up = (guard or sticky) and not sgn
    else:
        up = (guard or sticky) and sgn
    return sig + int(bool(up))


def vecs():
    r = random.Random(4)
    X = [r.getrandbits(r.randrange(5, 29)) for _ in range(60)] + [0, 0xF, 0x8, 0x18, 0x1, 0x7, 0xFFFFFFF, 0x80, 0x88, 0x98]
    return X, [r.getrandbits(1) for _ in X]


@pytest.mark.parametrize("mode", fa.ROUND_MODES)
def test_round_block_rtl(tmp, mode):
    g, b = block(mode)
    X, SG = vecs()
    ent = {b.entries["X"]: X}
    if "SGN" in b.entries:
        ent[b.entries["SGN"]] = SG
    for rmode in ("plain", "stall"):
        got = run_rtl(tmp, f"rm_{mode}", g.records(), ent, b.exits, rmode, settle=20000)["OUT"]
        bad = [(hex(x), s, got[i], rule(mode, x, s)) for i, (x, s) in enumerate(zip(X, SG)) if got[i] != rule(mode, x, s)]
        assert not bad, bad[:4]


@pytest.mark.parametrize("mode", ["rna", "rup", "rdn", "rtz"])
def test_round_block_flexgrid(mode):
    g, b = block(mode)
    X, SG = vecs()
    X, SG = X[-10:], SG[-10:]
    ent = {b.entries["X"]: X}
    if "SGN" in b.entries:
        ent[b.entries["SGN"]] = SG
    got = run_vm(g.records(), ent, b.exits, b.consts, ticks=500)["OUT"]
    assert got == [rule(mode, x, s) for x, s in zip(X, SG)]


def test_modes_differ_on_the_vectors():
    """The vectors have teeth: every pair of modes disagrees somewhere."""
    X, SG = vecs()
    outs = {m: [rule(m, x, s) for x, s in zip(X, SG)] for m in fa.ROUND_MODES}
    for a in fa.ROUND_MODES:
        for b_ in fa.ROUND_MODES:
            if a < b_:
                assert outs[a] != outs[b_], (a, b_)


# ---- part 2: the WHOLE adder in each rounding mode --------------------------------------------------------------------------------------------------------------------------------------
_ADDERS = {}


def adder(key, mode):
    if (key, mode) not in _ADDERS:
        g, ent, ex, consts = fadd.fp_add_grid(sp.FORMATS[key][0], rounding=mode)
        assert g.balance(limit=300) >= 0 and g.problems() == []
        _ADDERS[(key, mode)] = (g, ent, ex, consts)
    return _ADDERS[(key, mode)]


def mode_vectors(key, seed=9):
    """The special / subnormal vectors plus rounding-heavy ones: exact ties, just-above and just-below ties, opposite signs, signed zeros, results near the overflow threshold."""
    fmt = sp.FORMATS[key][0]
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    emax = (1 << E) - 1
    SG = 1 << (m + E)
    r = random.Random(seed)
    V = [(a, b) for a, b, _ in sp.vectors(key)]
    one = ((emax // 2)) << m
    for _ in range(14):                                       # a number plus a power-of-two fraction of it: guard set, sticky clear (tie) or set (above)
        e = r.randrange(3, emax - 3)
        x = (e << m) | r.getrandbits(m)
        sh = r.randrange(m - 1, m + 3)
        y = (max(e - sh, 1) << m) | r.choice([0, r.getrandbits(m)])
        sx, sy = r.choice([0, SG]), r.choice([0, SG])
        V.append((x | sx, y | sy))
    V += [(SG, SG), (SG, 0), (0, SG), (0, 0), (one, one | SG), (one | SG, one), ((emax - 1) << m | ((1 << m) - 1), (emax - 1) << m | ((1 << m) - 1)),
          (SG | (emax - 1) << m | ((1 << m) - 1), SG | (emax - 1) << m | ((1 << m) - 1)), ((emax - 1) << m | ((1 << m) - 1), 1 << (m - 24 if m > 24 else 0)),
          (SG | 1, SG | 1), (1, SG | 1), (SG | 1, 1)]
    for k in range(4):                                        # exact half-ulp ties with an EVEN lsb (rne stays, rna goes away from zero), both signs
        e = emax // 2 + 2 * k
        V += [(e << m, (e - m - 1) << m), (SG | (e << m), SG | ((e - m - 1) << m))]
    W = 1 << (m + E + 1)
    V = [(a & (W - 1), b & (W - 1)) for a, b in V]
    assert all(0 <= a < W and 0 <= b < W for a, b in V)
    return V


def same(fmt, got, want):
    return sp.same(fmt, got, want)


@pytest.mark.parametrize("mode", MODES)
def test_adder_in_each_mode_rtl_fp32(tmp, mode):
    fmt = fa.FP32
    g, ent, ex, _ = adder("fp32", mode)
    V = mode_vectors("fp32")
    A, B = zip(*V)
    W = [add_ref(fmt, a, b, mode) for a, b in V]
    got = run_rtl(tmp, f"add_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=120000)["R"]
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if not same(fmt, x, w)]
    assert not bad, (mode, bad[:5])


def test_adder_modes_differ_on_the_vectors():
    """The vectors have teeth: every pair of modes disagrees on several of them, and the RNE reference is numpy's."""
    fmt = fa.FP32
    V = mode_vectors("fp32")
    outs = {m_: [add_ref(fmt, a, b, m_) for a, b in V] for m_ in MODES}
    for a in MODES:
        for b in MODES:
            if a < b:
                assert sum(x != y for x, y in zip(outs[a], outs[b])) >= 3, (a, b)
    rne = [sp.reference("fp32", a, b) for a, b in V]
    assert all(sp.same(fmt, x, y) for x, y in zip(outs["rne"], rne))


@pytest.mark.parametrize("mode", ["rtz", "rdn"])
def test_adder_in_each_mode_rtl_fp16(tmp, mode):
    fmt = fa.FP16
    g, ent, ex, _ = adder("fp16", mode)
    V = mode_vectors("fp16")
    A, B = zip(*V)
    W = [add_ref(fmt, a, b, mode) for a, b in V]
    got = run_rtl(tmp, f"add16_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=120000)["R"]
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if not same(fmt, x, w)]
    assert not bad, (mode, bad[:5])
