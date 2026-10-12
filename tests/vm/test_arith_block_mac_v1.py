"""Ledger #1080: the stored, pre-laid-out multiply-accumulate block (arith_blocks_v1.mac_chain) for dot products.

Cells are exactly 7n - 1 for n terms (measured against what is built); results equal the general placer's and Python's on random words incl. wrap-around; formulas that are not
exactly a dot product are untouched; the block runs as real generated flex RTL and sub RTL."""
import json
import os
import random
import re
import shutil
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "nano"), os.path.join(_HERE, "..", "..", "tools")):
    sys.path.insert(0, _p)

import arith_blocks_v1 as AB  # noqa: E402
import latex_frontend_v1 as L  # noqa: E402
import flex_rtl_harness_v1 as _h  # noqa: E402
import test_sub_div_v1 as _sub  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

M = 0xFFFFFFFF


def _dot(n):
    return r"y = \sum_{i=1}^{%d} a_i b_i" % n


@pytest.mark.parametrize("n", range(2, 11))
def test_cell_count_is_exactly_7n_minus_1(n):
    pairs = [(f"v_a_{k}", f"v_b_{k}", f"_t{k}") for k in range(1, n + 1)]
    recs, inj, rc = AB.mac_chain(pairs)
    assert len(recs) == AB.mac_chain_cell_count(n) == 7 * n - 1
    assert len({(r.row, r.col) for r in recs}) == len(recs) and len({r.cell_id for r in recs}) == len(recs)       # no two cells on one square, unique names
    assert recs[-1].cell_id == "main.r" or any(r.cell_id == "main.r" and (r.row, r.col) == rc for r in recs)
    assert sorted(inj) == sorted([p[0] for p in pairs] + [p[1] for p in pairs])


@pytest.mark.parametrize("n", [2, 3, 4, 6])
def test_block_equals_python_and_the_general_placer(n):
    rng = random.Random(1080 + n)
    blk, gen = L.compile_latex(_dot(n)), L.compile_latex(_dot(n), blocks="off")
    assert blk.result.placer == "stored_block:mac_chain" and blk.cells == 7 * n - 1 and gen.cells > blk.cells
    assert blk.checked > 0
    names = [f"{p}_{k}" for k in range(1, n + 1) for p in "ab"]
    for _ in range(4):
        v = {nm: rng.choice([0, 1, M, rng.randint(0, M)]) for nm in names}
        want = sum(v[f"a_{k}"] * v[f"b_{k}"] for k in range(1, n + 1)) & M
        assert blk.run(v) == want == blk.reference(v)
    if n <= 3:
        v = {nm: rng.randint(0, M) for nm in names}
        assert gen.run(v) == blk.run(v)


def test_only_a_pure_dot_product_uses_the_block():
    for src in ["y = a b + c d + e", "y = a a + b c", "y = a b", "y = a b + a c", "y = a b - c d", "y = 2 a b + c d", "y = a b c + d e", "y = a b + c d x"]:
        r = L.compile_latex(src)
        assert r.result.placer != "stored_block:mac_chain", src
    assert L.compile_latex("y = a b + c d").result.placer == "stored_block:mac_chain"
    assert L.compile_latex("y = a b + c d + e f").result.placer == "stored_block:mac_chain"


def test_blocks_option_validated_and_off_gives_the_general_layout():
    with pytest.raises(L.LatexError):
        L.compile_latex(_dot(2), blocks="yes")
    assert L.compile_latex(_dot(2), blocks="off").cells == 29            # measured in #1079
    assert L.compile_latex(_dot(2)).cells == 13


def test_a_one_term_sum_is_not_a_dot_product():
    assert L.compile_latex(r"y = \sum_{i=1}^{1} a_i b_i").result.placer != "stored_block:mac_chain"


_VECS = None


def _vecs(n):
    rng = random.Random(7)
    names = [f"{p}_{k}" for k in range(1, n + 1) for p in "ab"]
    first = [{nm: 0 for nm in names}, {nm: 1 for nm in names}, {nm: M for nm in names}]
    return first + [{nm: rng.randint(0, M) for nm in names} for _ in range(5)]


def test_block_as_generated_flex_rtl():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    r = L.compile_latex(_dot(3))
    vecs = _vecs(3)
    tmp = tempfile.mkdtemp(prefix="mac_")
    try:
        d, res = _h.build(tmp, "lx", r.result.records, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(d, top + ".v")).read()
        cmap = L._input_cells(r)
        streams = {}
        for name in sorted(set(re.findall(r"\bin_(\w+)_data", text))):
            cid = [c for c in cmap if c.replace(".", "_") == name]
            assert len(cid) == 1, (name, list(cmap))
            streams[name] = [v[cmap[cid[0]]] & M for v in vecs]
        _, got = _h.run_level(d, streams, "plain", 3, settle=600, cycles=60000, width=32)
        (out,) = got.values()
        assert out == [r.reference(v) for v in vecs], out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_block_as_generated_sub_rtl():
    assert shutil.which("iverilog") and shutil.which("vvp")
    r = L.compile_latex(_dot(3))
    vecs = _vecs(3)
    tmp = tempfile.mkdtemp(prefix="macsub_")
    try:
        icm = os.path.join(tmp, "x.icm")
        IcmV3File(name="x", records=r.result.records).save(icm)
        out = os.path.join(tmp, "g")
        p = _h.cli("-s", "sub", "--icm", icm, "--output", out)
        assert p.returncode == 0, (p.stderr or p.stdout)[:500]
        top = json.load(open(os.path.join(out, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(out, top + ".v")).read()
        cmap = L._input_cells(r)
        ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
        items = []
        for v in vecs:
            it = {}
            for n_ in ins:
                cid = [c for c in cmap if c.replace(".", "_") == n_]
                assert len(cid) == 1
                it[n_] = v[cmap[cid[0]]] & M
            items.append(it)
        got, _ = _sub.simulate(out, items)
        assert [g[1] for g in got] == [r.reference(v) for v in vecs], got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
