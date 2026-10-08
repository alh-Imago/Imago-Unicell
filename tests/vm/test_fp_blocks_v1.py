"""tests/vm/test_fp_blocks_v1.py -- ledger #989: the PARAMETRIC fp blocks of tools/fp_assembler_v1.py (normalise chain + exponent adjust, align with sticky, round-to-nearest-even), each for fp32 AND a smaller
format (fp16: 11-bit significand), in the generated RTL (plain + random stalls) and in FlexGrid, against plain Python. Timing ties are removed by the layout engine (`Grid.balance`), not by hand.
Also the COMPOSITION align -> round (the sticky flag and the guard bits cross the block boundary): OUT = round-half-even(sig / 2^d). Requires iverilog."""
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
from fp32_stage_builder_v1 import Grid  # noqa: E402,F401
from flex_layout_v1 import Grid as LGrid  # noqa: E402
from fp32_boundary_v1 import round_to_nearest_even  # noqa: E402

M32 = 0xFFFFFFFF
FORMATS = [fa.FP32, fa.FP16]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fpblocks_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def ids(f):
    return f.name


def both(tmp, name, g, entries, exits, consts, want):
    recs = g.records()
    for mode in ("plain", "stall"):
        got = run_rtl(tmp, name, recs, entries, exits, mode)
        assert got == want, (mode, {k: [(i, a, b) for i, (a, b) in enumerate(zip(got[k], want[k])) if a != b][:3] for k in want})
    assert run_vm(recs, entries, exits, consts) == want


@pytest.mark.parametrize("fmt", FORMATS, ids=ids)
def test_normalise_chain_parametric(tmp, fmt):
    g = LGrid(rows=16, cols=100)
    b = fa.normalise_chain(g, fmt)
    assert g.balance() >= 0 and not g.problems()
    S = fmt.sig_bits
    r = random.Random(3)
    vs = [(1 << S) - 1, 1 << (S - 1), 1, 2, 3, 5, 0x55 & ((1 << S) - 1) or 1] + [r.getrandbits(r.randrange(1, S + 1)) or 1 for _ in range(18)]
    es = [r.randrange(40, 200) for _ in vs]
    lz = [S - v.bit_length() for v in vs]
    want = {"NORM": [v << z for v, z in zip(vs, lz)], "EXPOUT": [(e - z) & M32 for e, z in zip(es, lz)]}
    both(tmp, f"norm_{fmt.name}", g, {b.entries["V"]: vs, b.entries["EXPIN"]: es}, b.exits, b.consts, want)


@pytest.mark.parametrize("fmt", FORMATS, ids=ids)
def test_align_sticky_parametric(tmp, fmt):
    g = LGrid(rows=16, cols=120)
    b = fa.align_sticky(g, fmt)
    assert g.balance() >= 0 and not g.problems()
    S, W = fmt.sig_bits, fmt.word
    r = random.Random(8)
    ws = [((1 << S) - 1) << (W - S), 1 << (W - 1), 1 << (W - S), 0] + [r.getrandbits(S) << (W - S) for _ in range(20)]
    ds = [0, 1, 2, S - 1, S, S + 1, (1 << fmt.Ka) - 1, 1 << fmt.Ka, (1 << fmt.Ka) + 3, 100, 3, 8] + [r.randrange(0, 70) for _ in range(12)]
    ts = [fa.align_total_shift(fmt, d) for d in ds]
    want = {"OUT": [w >> t for w, t in zip(ws, ts)], "STK": [1 if w & ((1 << t) - 1) else 0 for w, t in zip(ws, ts)]}
    both(tmp, f"align_{fmt.name}", g, {b.entries["V"]: ws, b.entries["D"]: ds}, b.exits, b.consts, want)


def rne_ref(x, low, ext=0):
    return round_to_nearest_even(x >> low, (x >> (low - 1)) & 1, 1 if ((x & ((1 << (low - 1)) - 1)) or ext) else 0)


@pytest.mark.parametrize("fmt", FORMATS, ids=ids)
@pytest.mark.parametrize("ext", [False, True], ids=["noext", "ext"])
def test_round_rne_parametric(tmp, fmt, ext):
    low = 8 if fmt is fa.FP32 else 12
    g = LGrid(rows=14, cols=40)
    b = fa.round_rne(g, fmt, low=low, ext_sticky=ext)
    assert g.balance() >= 0 and not g.problems()
    S = fmt.sig_bits
    r = random.Random(11)
    sigs = (0x800000 >> (24 - S), (1 << S) - 1, 0x2AAAAA >> (24 - S) | 1 << (S - 1))
    xs = [(s << low) | lo for s in sigs for lo in (0, 1, (1 << (low - 1)) - 1, 1 << (low - 1), (1 << (low - 1)) | 1, (1 << low) - 1)] + [(r.getrandbits(S) << low) | r.getrandbits(low) for _ in range(30)]
    ents = {b.entries["X"]: xs}
    es = [r.getrandbits(1) for _ in xs]
    if ext:
        ents[b.entries["STK"]] = es
    want = {"OUT": [rne_ref(x, low, e if ext else 0) for x, e in zip(xs, es)]}
    assert any(w != x >> low for w, x in zip(want["OUT"], xs))
    both(tmp, f"round_{fmt.name}_{ext}", g, ents, b.exits, b.consts, want)


@pytest.mark.parametrize("fmt", FORMATS, ids=ids)
def test_compose_align_then_round(tmp, fmt):
    """OUT = round-half-even(sig / 2^d): the aligned word's guard bits and the sticky flag cross from one block to the next."""
    g = LGrid(rows=16, cols=180)
    a = fa.align_sticky(g, fmt, "AL", 0, 0)
    low = fmt.word - fmt.sig_bits - (fmt.Ka + 1)
    rr = fa.round_rne(g, fmt, "RN", 0, a.extent[1] + 3, low=low, ext_sticky=True)
    g.route(a.exits["OUT"], rr.entries["X"])
    g.route(a.exits["STK"], rr.entries["STK"])
    assert g.balance() >= 0 and not g.problems()
    S, W = fmt.sig_bits, fmt.word
    r = random.Random(5)
    sigs = [(1 << S) - 1, 1 << (S - 1), 1, 3, 5] + [r.getrandbits(S) or 1 for _ in range(14)]
    ds = [0, 1, 2, 3, S - 2, S - 1, S, S + 1, 40] + [r.randrange(0, S + 4) for _ in range(10)]
    pairs = list(zip(sigs, ds))
    assert len(pairs) >= 14

    def ref(sig, d):
        if d == 0:
            return sig
        q = sig >> d
        rem = sig - (q << d)
        half = 1 << (d - 1)
        return q + (1 if (rem > half or (rem == half and q & 1)) else 0)
    sigs, ds = zip(*pairs)
    want = {"OUT": [ref(s, d) for s, d in pairs]}
    ents = {a.entries["V"]: [s << (W - S) for s in sigs], a.entries["D"]: list(ds)}
    both(tmp, f"compose_{fmt.name}", g, ents, rr.exits, {**a.consts, **rr.consts}, want)
