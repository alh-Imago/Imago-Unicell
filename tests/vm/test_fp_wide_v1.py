"""tests/vm/test_fp_wide_v1.py -- ledger #1011: the WIDER FLEX. The ICM -> flex generator takes a cell width (`-w`), the ram's constant port scales with it (a WIDTH-bit cell has a WIDTH-bit init word), and the
fp designs take `FpFormat.word` as their parameter. Here: (1) a ram constant survives at 4/8/18/36/64 bits (RTL and FlexGrid); (2) the fp32 MULTIPLIER built for a 64-bit cell word, every rounding mode, against `mul_ref`;
(3) the fp32 COMPARATOR at a 64-bit word, against `cmp_ref`. Requires iverilog."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("", "../../tools"):
    sys.path.insert(0, os.path.join(HERE, sub))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
import fp_assembler_v1 as fa  # noqa: E402
import fp_mul_v1 as fm  # noqa: E402
import fp_compare_v1 as fc  # noqa: E402
from fp_round_ref_v1 import mul_ref, cmp_ref, MODES  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402

FP32W64 = fa.FpFormat("fp32w64", 24, 8, 64)
INF, SG = 0x7F800000, 0x80000000


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fpwide_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("w", [4, 8, 18, 36, 64])
def test_ram_constant_scales_with_the_cell(tmp, w):
    """x + K at a w-bit cell, K a full w-bit constant (high bits set: a 32-bit-wide init port would lose them at w > 32)."""
    g = Grid(rows=4, cols=6)
    g.add("E0", 0, 0)                                        # a relay ahead of the entry: the adder's two operands must not tie
    g.add("E", 0, 1)
    g.add("A", 0, 2, core="adder")
    K = (0xA5A5A5A5A5A5A5A5 | (1 << (w - 1))) & ((1 << w) - 1)
    g.add("K", 1, 2, preload=K)
    g.add("X", 0, 3)
    g.link("E0", "E")
    g.link("E", "A")
    g.link("K", "A")
    g.link("A", "X")
    assert g.problems() == []
    r = random.Random(w)
    xs = [r.getrandbits(w) for _ in range(12)] + [0, 1, (1 << w) - 1]
    want = [(x + K) & ((1 << w) - 1) for x in xs]
    got = run_rtl(tmp, f"ramw{w}", g.records(), {"E0": xs}, {"R": "X"}, "plain", settle=200, cycles=2500, width=w)["R"]
    assert got == want, (w, hex(K))
    vm = run_vm(g.records(), {"E0": xs}, {"R": "X"}, {"K": K}, ticks=60, width=w)["R"]
    assert vm == want


def mul_vectors(seed=21):
    r = random.Random(seed)
    sp = [0, SG, 1, SG | 0x7FFFFF, 0x00800000, 0x3F800000, SG | 0x3F800000, 0x7F7FFFFF, INF, SG | INF, 0x7FC00000, 0x3FC00000, 0x00400000]
    V = [(a, b) for a in sp[:7] for b in sp[:7]] + [(INF, 0), (0, INF), (0x7FC00000, 0x3F800000), (0x7F7FFFFF, 0x40000000), (0x7F7FFFFF, 0x7F7FFFFF)]
    for _ in range(40):                                      # exponents summing near underflow (e1+e2-127 ~ 0) and overflow (~255), random fractions
        for tgt in (127, 255):
            e1 = r.randrange(max(1, tgt - 254), min(254, tgt) + 1)
            e2 = tgt - e1 + r.randrange(-2, 3)
            if 1 <= e2 <= 254:
                V.append(((r.getrandbits(1) << 31) | (e1 << 23) | r.getrandbits(23), (r.getrandbits(1) << 31) | (e2 << 23) | r.getrandbits(23)))
    return V


@pytest.mark.parametrize("mode", MODES)
def test_fp32_multiplier_at_word_64_rtl(tmp, mode):
    g = Grid(rows=260, cols=900)
    ent, ex, consts, _ = fm.fp_mul(g, FP32W64, rounding=mode)
    assert g.balance(limit=500) >= 0 and g.problems() == []
    V = mul_vectors()
    A, B = zip(*V)
    got = run_rtl(tmp, f"mul32w64_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=6000, cycles=len(V) * 60 + 9000, width=64)["R"]
    nan = lambda v: (v & INF) == INF and (v & 0x7FFFFF) != 0  # noqa: E731
    bad = [(hex(a), hex(b), hex(x), hex(mul_ref(fa.FP32, a, b, mode))) for a, b, x in zip(A, B, got) if x != mul_ref(fa.FP32, a, b, mode) and not (nan(x) and nan(mul_ref(fa.FP32, a, b, mode)))]
    assert len(got) == len(V) and not bad, (mode, len(got), bad[:5])


def test_fp32_comparator_at_word_64_rtl(tmp):
    g = Grid(rows=120, cols=300)
    ent, ex, consts, _ = fc.fp_compare(g, FP32W64)
    assert g.balance(limit=300) >= 0 and g.problems() == []
    r = random.Random(8)
    base = [0, 1, 0x7FFFFF, 0x800000, 0x800001, 0x3F7FFFFF, 0x3F800000, 0x3F800001, 0x7F7FFFFF, INF, INF | 1, 0x7FC00000]
    base += [r.getrandbits(31) for _ in range(6)]
    vals = base + [SG | v for v in base]
    V = [(a, b) for a in vals for b in vals]
    r.shuffle(V)
    V = V[:300]
    A, B = zip(*V)
    got = run_rtl(tmp, "cmp32w64", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=6000, cycles=len(V) * 60 + 9000, width=64)["R"]
    want = [(1 << 64) - 1 if cmp_ref(fa.FP32, a, b) == 0xFFFFFFFF else cmp_ref(fa.FP32, a, b) for a, b in V]   # -1 is all ones in the CELL word
    bad = [(hex(a), hex(b), x, w) for a, b, x, w in zip(A, B, got, want) if x != w]
    assert len(got) == len(V) and not bad, bad[:5]


@pytest.mark.parametrize("width", [4, 18, 32, 36, 64])
@pytest.mark.parametrize("amt", [1, 3, 8, 12, 24, 28, 29, 35])
@pytest.mark.parametrize("right", [0, 1])
def test_addon_wiring_is_a_plain_logical_shift_at_any_width(width, amt, right):
    """The generator's shift add-on map is a plain logical shift of the whole cell word (a right shift by a std 'coarse' tap used to drop every lane above bit 31 at wider cells)."""
    import flexsub_icm_generate_v1 as g
    bits = g.addon_bit_map({"shift_en": 1, "direction": right, "shift_amt": amt}, free_shift=True, width=width)
    assert len(bits) == width
    M = (1 << width) - 1
    r = random.Random(width * 100 + amt)
    for _ in range(20):
        v = r.getrandbits(width)
        assert g.addon_apply(bits, v) == ((v >> amt) if right else (v << amt) & M)
