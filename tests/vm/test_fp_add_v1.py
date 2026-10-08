"""tests/vm/test_fp_add_v1.py -- ledger #990: the WHOLE floating-point ADDER built from flex cells (tools/fp_add_v1.py), parametric in the format: fp32, bfloat16, fp16.
Normal numbers and zero, round-to-nearest-even; no subnormal / overflow / inf / nan (the scope of nano/fp32_add_v1.py). Compared with a generic exact reference (an independent
integer implementation: exact sum, then one rounding) in the generated RTL (plain, plus random stalls for fp32) and in FlexGrid (a few items: the VM is slow on 1700 cells).
The generic reference is first checked against fp32_add_v1 (3000 pairs), so the oracle is itself anchored. Vectors include same-exponent opposite signs (cancellation), exponent gaps
beyond the significand, zeros, and rounding ties. Results whose exponent would leave the normal range are excluded (out of scope). Requires iverilog."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
import fp_assembler_v1 as fa  # noqa: E402
import fp_add_v1 as fadd  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
from fp32_add_v1 import fp32_add  # noqa: E402

FORMATS = {"fp32": fa.FP32, "bf16": fa.BF16, "fp16": fa.FP16}


def ref_add(fmt, x, y, rne=True):
    """Exact sum of two normal-or-zero numbers, rounded ONCE to the format (half to even). Returns (bits, biased exponent of the result); exponent is None for an exact zero."""
    S, E = fmt.sig_bits, fmt.exp_bits
    m = S - 1

    def dec(v):
        e = (v >> m) & ((1 << E) - 1)
        s = v >> (m + E)
        M = ((v & ((1 << m) - 1)) | (1 << m)) if e else 0
        return (-1 if s else 1) * M, e
    a, ea = dec(x)
    b, eb = dec(y)
    emin = min(ea, eb)
    T = a * (1 << (ea - emin)) + b * (1 << (eb - emin))
    if T == 0:
        return 0, None
    s = 1 if T < 0 else 0
    T = abs(T)
    k = T.bit_length() - S
    if k > 0:
        q, rem, half = T >> k, T & ((1 << k) - 1), 1 << (k - 1)
        if rne and (rem > half or (rem == half and (q & 1))):
            q += 1
        M = q
    else:
        M = T << (-k)
    er = emin + k
    if M == 1 << S:
        M >>= 1
        er += 1
    return (s << (m + E)) | ((er & ((1 << E) - 1)) << m) | (M - (1 << m)), er


def vectors(fmt, seed=5):
    S, E = fmt.sig_bits, fmt.exp_bits
    m = S - 1
    bias = (1 << (E - 1)) - 1
    r = random.Random(seed)
    sgn = lambda: r.getrandbits(1) << (m + E)
    rnd = lambda: sgn() | (r.randrange(bias - 6, bias + 7) << m) | r.getrandbits(m)
    A = [rnd() for _ in range(20)]
    B = [rnd() for _ in range(20)]
    for _ in range(8):                                        # same exponent, opposite sign, nearly equal: cancellation
        x = rnd()
        A.append(x)
        B.append((x ^ (1 << (m + E))) ^ r.getrandbits(r.randrange(1, 6)))
    for _ in range(6):                                        # neighbouring exponents, opposite sign
        x = rnd()
        ee = ((x >> m) & ((1 << E) - 1)) + r.choice([-1, 0, 1])
        A.append(x)
        B.append(((x ^ (1 << (m + E))) & ~(((1 << E) - 1) << m)) | (ee << m))
    one = bias << m
    A += [one, 0, one + (1 << m), one, 0, one, one, one]
    B += [one, one + (5 << (m - 3)), 0, one | (1 << (m + E)), 0, (bias - m - 1) << m, (bias - m) << m, (bias - m + 1) << m | 1]
    keep = [(x, y) for x, y in zip(A, B) if (lambda e: e is None or 1 <= e <= (1 << E) - 2)(ref_add(fmt, x, y)[1])]
    return [x for x, _ in keep], [y for _, y in keep]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fpadd_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_generic_reference_is_anchored_to_fp32_add_v1():
    r = random.Random(9)
    for _ in range(3000):
        x = (r.getrandbits(1) << 31) | (r.randrange(100, 160) << 23) | r.getrandbits(23)
        y = (r.getrandbits(1) << 31) | (r.randrange(100, 160) << 23) | r.getrandbits(23)
        assert ref_add(fa.FP32, x, y)[0] == fp32_add(x, y), (hex(x), hex(y))


@pytest.mark.parametrize("name", list(FORMATS))
def test_vectors_exercise_rounding_cancellation_and_zero(name):
    fmt = FORMATS[name]
    A, B = vectors(fmt)
    assert len(A) >= 36
    differs = sum(ref_add(fmt, x, y)[0] != ref_add(fmt, x, y, rne=False)[0] for x, y in zip(A, B))
    assert differs >= 3, "the vectors must contain rounding cases (truncation would differ)"
    m = fmt.sig_bits - 1
    cancel = sum(1 for x, y in zip(A, B) if ref_add(fmt, x, y)[1] is not None and ref_add(fmt, x, y)[1] < max((x >> m) & ((1 << fmt.exp_bits) - 1), (y >> m) & ((1 << fmt.exp_bits) - 1)))
    assert cancel >= 3 and any(x == 0 or y == 0 for x, y in zip(A, B))


def build(fmt):
    g = Grid(rows=34, cols=330)
    ent, ex, consts = fadd.fp_add(g, fmt)
    assert g.balance() >= 0 and g.problems() == []
    return g, ent, ex, consts


@pytest.mark.parametrize("name", list(FORMATS))
def test_adder_in_rtl(tmp, name):
    fmt = FORMATS[name]
    g, ent, ex, _ = build(fmt)
    A, B = vectors(fmt)
    want = [ref_add(fmt, x, y)[0] for x, y in zip(A, B)]
    modes = ("plain", "stall") if name == "fp32" else ("plain",)
    for mode in modes:
        got = run_rtl(tmp, f"add_{name}_{mode}", g.records(), {ent["a"]: A, ent["b"]: B}, ex, mode, settle=60000)["R"]
        assert got == want, [(i, hex(A[i]), hex(B[i]), hex(a), hex(b)) for i, (a, b) in enumerate(zip(got, want)) if a != b][:4]


@pytest.mark.parametrize("name", ["fp32", "fp16"])
def test_adder_in_flexgrid(name):
    fmt = FORMATS[name]
    g, ent, ex, consts = build(fmt)
    A, B = vectors(fmt)
    n = 5
    want = [ref_add(fmt, x, y)[0] for x, y in zip(A[:n], B[:n])]
    vm = run_vm(g.records(), {ent["a"]: A[:n], ent["b"]: B[:n]}, ex, consts, ticks=900)["R"]
    assert vm == want


def test_bite_the_checker_sees_a_wrong_result(tmp):
    """A deliberately wrong expectation (truncation instead of round-half-even) must NOT match the hardware on the same vectors."""
    fmt = fa.FP16
    g, ent, ex, _ = build(fmt)
    A, B = vectors(fmt)
    got = run_rtl(tmp, "add_bite", g.records(), {ent["a"]: A, ent["b"]: B}, ex, "plain", settle=60000)["R"]
    assert got != [ref_add(fmt, x, y, rne=False)[0] for x, y in zip(A, B)]
