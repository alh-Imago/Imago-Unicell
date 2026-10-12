"""Ledger #1082: matrices on the LaTeX side -- a rule for the entries and a size, applied to a run-time vector (y = A x), built as the stored block `matvec`."""
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

M = 0xFFFFFFFF


@pytest.mark.parametrize("m,n", [(1, 2), (1, 5), (2, 2), (2, 3), (3, 3), (4, 4), (5, 2)])
def test_cell_count_formula_and_distinct_squares(m, n):
    recs, inj, exits = AB.matvec([[1] * n for _ in range(m)], [f"x_{j}" for j in range(n)])
    assert len(recs) == AB.matvec_cell_count(m, n) == 8 * n * (m - 1) + 7 * n - 1
    assert len({(r.row, r.col) for r in recs}) == len(recs) and len({r.cell_id for r in recs}) == len(recs)
    assert len(exits) == m and all(len(v) == 1 for v in inj.values())


def test_entries_count_from_one_and_follow_the_rule():
    r = L.compile_matrix_latex("A_{ij} = i j", 2, 3)
    assert r.matrix == [[1, 2, 3], [2, 4, 6]]
    assert L.compile_matrix_latex("A_{ij} = i + j", 3, 2).matrix == [[2, 3], [3, 4], [4, 5]]
    assert L.compile_matrix_latex("A_{ij} = i^2 j^2", 3, 3).matrix == [[1, 4, 9], [4, 16, 36], [9, 36, 81]]       # a product of squares
    assert L.compile_matrix_latex("A_{ij} = 2 i - j", 2, 2).matrix == [[1, 0], [3, 2]]
    assert L.compile_matrix_latex("A_{i,j} = i j", 2, 2).matrix == [[1, 2], [2, 4]]
    assert L.compile_matrix_latex("B_{kl} = k l + 1", 2, 2).matrix == [[2, 3], [3, 5]]
    assert L.compile_matrix_latex("A_{ij} = i - j", 2, 2).matrix == [[0, M], [1, 0]]                                 # wraps like the cells
    assert L.compile_matrix_latex("A_{ij} = j / i", 2, 2).matrix == [[1, 2], [0, 1]]                                 # division works in the rule
    assert L.compile_matrix_latex("A_{ij} = j \\bmod i", 2, 3).matrix == [[0, 0, 0], [1, 0, 1]]


@pytest.mark.parametrize("rule,m,n", [("A_{ij} = i j", 3, 3), ("A_{ij} = i + j", 2, 4), ("A_{ij} = i^2 j^2", 3, 2), ("A_{ij} = 3 i - 7 j + 5", 4, 3)])
def test_the_design_equals_the_product_on_random_vectors(rule, m, n):
    rng = random.Random(1082)
    r = L.compile_matrix_latex(rule, m, n)
    assert r.checked == 7 and r.cells == AB.matvec_cell_count(m, n)
    for _ in range(3):
        v = {a: rng.choice([0, 1, M, rng.randint(0, M)]) for a in r.args}
        assert r.run(v) == r.reference(v)


def test_refusals_say_why():
    bad = [("A_{ij} = i j", 2, 1, "columns"), ("A_{ij} = i j", 0, 3, "rows"), ("A_{ij} = i j", 17, 3, "rows"), ("A_{ii} = i", 2, 2, "differ"), ("A = i j", 2, 2, "must read"),
           ("A_{ij} = i j k", 2, 2, "not an index"), ("A_{ij} = ", 2, 2, "empty"), ("A_{ij} = i j", 2, 3.5, "size")]
    for rule, m, n, why in bad:
        with pytest.raises(L.LatexError) as e:
            L.compile_matrix_latex(rule, m, n)
        assert why in str(e.value), (rule, str(e.value))
    for vec in ("i", "A", "xy", "3"):
        with pytest.raises(L.LatexError):
            L.compile_matrix_latex("A_{ij} = i j", 2, 2, vector=vec)


def test_cli_matrix_mode():
    import subprocess
    tmp = tempfile.mkdtemp(prefix="mx_")
    try:
        o = os.path.join(tmp, "m.icm")
        p = subprocess.run([sys.executable, os.path.join(_HERE, "..", "..", "nano", "latex_cli_v1.py"), "A_{ij} = i j", "--matrix", "3x3", "--set", "x_1=1", "--set", "x_2=2", "--set", "x_3=3", "-o", o],
                           capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        assert "y_1 = 14, y_2 = 28, y_3 = 42" in p.stdout and os.path.exists(o) and "matrix A (3x3): 1 2 3; 2 4 6; 3 6 9" in p.stdout
        bad = subprocess.run([sys.executable, os.path.join(_HERE, "..", "..", "nano", "latex_cli_v1.py"), "A_{ij} = i j", "--matrix", "3by3"], capture_output=True, text=True)
        assert bad.returncode == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_X = [{1: 0, 2: 0, 3: 0}, {1: 1, 2: 1, 3: 1}, {1: M, 2: M, 3: M}, {1: 5, 2: 7, 3: 11}, {1: 123456789, 2: 987654321, 3: 4000000000}]


def test_two_by_three_as_generated_flex_rtl_two_outputs():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    r = L.compile_matrix_latex("A_{ij} = i j", 2, 3)
    tmp = tempfile.mkdtemp(prefix="mxf_")
    try:
        d, res = _h.build(tmp, "mx", r.records, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(d, top + ".v")).read()
        ins = sorted(set(re.findall(r"\bin_(\w+)_data", text)))
        assert len(ins) == 3
        # input cell names are main_mv0_<j>_a (chain 0, stage j): x_{j+1}
        streams = {n_: [vec[int(re.search(r"mv0_(\d)_a", n_).group(1)) + 1] for vec in _X] for n_ in ins}
        _, got = _h.run_level(d, streams, "plain", 3, settle=600, cycles=80000, width=32)
        assert sorted(got) == ["main_y1", "main_y2"], sorted(got)
        want = [r.reference({f"x_{j}": vec[j] for j in (1, 2, 3)}) for vec in _X]
        assert got["main_y1"] == [w[0] for w in want] and got["main_y2"] == [w[1] for w in want], (got, want)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_one_by_three_as_generated_sub_rtl():
    assert shutil.which("iverilog") and shutil.which("vvp")
    r = L.compile_matrix_latex("A_{ij} = 2 i + j", 1, 3)
    tmp = tempfile.mkdtemp(prefix="mxs_")
    try:
        icm = os.path.join(tmp, "m.icm")
        r.save(icm)
        out = os.path.join(tmp, "g")
        p = _h.cli("-s", "sub", "--icm", icm, "--output", out)
        assert p.returncode == 0, (p.stderr or p.stdout)[:500]
        top = json.load(open(os.path.join(out, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(out, top + ".v")).read()
        ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
        items = [{n_: vec[int(re.search(r"mv0_(\d)_a", n_).group(1)) + 1] for n_ in ins} for vec in _X]
        got, _ = _sub.simulate(out, items)
        assert [g[1] for g in got] == [r.reference({f"x_{j}": vec[j] for j in (1, 2, 3)})[0] for vec in _X], got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- ledger #1083: run-time matrices, chaining, matrix times matrix by streaming ----

def _mv(A, x):
    return [sum(a * b for a, b in zip(row, x)) & M for row in A]


def test_a_runtime_matrix_takes_its_entries_as_inputs():
    rng = random.Random(1083)
    r = L.compile_matrix_latex("A_{ij}", 2, 3)
    assert r.args == ["x_1", "x_2", "x_3"] + [f"A_{i}_{j}" for i in (1, 2) for j in (1, 2, 3)]
    assert r.matrix is None and r.cells == AB.matvec_cell_count(2, 3)          # same size as the constant form: an input cell where the constant was
    for _ in range(4):
        v = {a: rng.choice([0, 1, M, rng.randint(0, M)]) for a in r.args}
        assert r.run(v) == r.reference(v) == _mv([[v[f"A_{i}_{j}"] for j in (1, 2, 3)] for i in (1, 2)], [v["x_1"], v["x_2"], v["x_3"]])


@pytest.mark.parametrize("specs", [
    [("A_{ij} = i j", 2, 3), ("B_{ij} = i + j", 3, 2)],
    [("A_{ij} = i j", 3, 3), ("B_{ij}", 2, 3), ("C_{ij} = 2 i - j", 2, 2)],
    [("A_{ij} = i + j", 2, 2), ("B_{ij} = i j", 3, 2), ("C_{ij} = j", 2, 3), ("D_{ij} = i", 1, 2)],
])
def test_chained_matrices_equal_applying_them_in_turn(specs):
    rng = random.Random(1083)
    first, rest = specs[0], specs[1:]
    r = L.compile_matrix_latex(first[0], first[1], first[2], then=rest)
    squares = [(c.row, c.col) for c in r.records]
    assert len(set(squares)) == len(squares), "two cells on one square"
    assert r.checked == 7 and len(r.layers) == len(specs)
    v = {a: rng.randint(0, M) for a in r.args}
    x = [v[f"x_{j}"] for j in range(1, first[2] + 1)]
    want = x
    for lay in r.layers:
        mat = lay["matrix"] or [[v[nm] for nm in row] for row in lay["entry_names"]]
        want = _mv(mat, want)
    assert r.run(v) == r.reference(v) == want


def test_chain_refusals():
    with pytest.raises(L.LatexError) as e:
        L.compile_matrix_latex("A_{ij} = i j", 2, 3, then=[("B_{ij} = i", 2, 4)])
    assert "4 columns" in str(e.value) and "2 results" in str(e.value)
    with pytest.raises(L.LatexError) as e:
        L.compile_matrix_latex("A_{ij} = i j", 2, 3, then=[("A_{ij} = i", 2, 2)])
    assert "already used" in str(e.value)
    with pytest.raises(L.LatexError):
        L.compile_matrix_latex("A_{ij} = i j", 2, 3, vector="A")
    with pytest.raises(L.LatexError):
        L.compile_matrix_latex("A_{ij} = i j", 1, 3, then=[("B_{ij} = i", 2, 1)])            # the middle result is a single value: the next block needs two columns
    with pytest.raises(L.LatexError) as e:
        L.compile_matrix_latex("A_{ij} = i + k", 2, 2)
    assert "run time" in str(e.value) and "A_{ij}" in str(e.value)


def test_matrix_times_matrix_by_streaming_the_columns_through_one_block_on_flex_rtl():
    """C = A B with A a constant 2x3 block and B's three columns streamed through it one after another: the same hardware, no copies. Output streams are the columns of C."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    r = L.compile_matrix_latex("A_{ij} = i j + 1", 2, 3)
    rng = random.Random(1083)
    Bcols = [[rng.randint(0, M) for _ in range(3)] for _ in range(4)]               # four columns of B (3 rows each)
    tmp = tempfile.mkdtemp(prefix="mxm_")
    try:
        d, res = _h.build(tmp, "mx", r.records, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(d, top + ".v")).read()
        ins = sorted(set(re.findall(r"\bin_(\w+)_data", text)))
        streams = {n_: [col[int(re.search(r"mv0_(\d)_a", n_).group(1))] for col in Bcols] for n_ in ins}
        _, got = _h.run_level(d, streams, "plain", 3, settle=600, cycles=120000, width=32)
        for i in (1, 2):
            assert got[f"main_y{i}"] == [_mv(r.matrix, col)[i - 1] for col in Bcols], (i, got)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_two_matrix_chain_as_generated_flex_rtl_and_a_final_single_row_as_sub_rtl():
    assert shutil.which("iverilog") and shutil.which("vvp")
    r = L.compile_matrix_latex("A_{ij} = i + j", 2, 3, then=[("B_{ij} = i j", 2, 2)])
    tmp = tempfile.mkdtemp(prefix="mxc_")
    try:
        d, res = _h.build(tmp, "mx", r.records, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(d, top + ".v")).read()
        ins = sorted(set(re.findall(r"\bin_(\w+)_data", text)))
        assert len(ins) == 3
        streams = {n_: [vec[int(re.search(r"mv0_(\d)_a", n_).group(1)) + 1] for vec in _X] for n_ in ins}
        _, got = _h.run_level(d, streams, "plain", 3, settle=900, cycles=120000, width=32)
        want = [r.reference({f"x_{j}": vec[j] for j in (1, 2, 3)}) for vec in _X]
        assert got["main_b1_y1"] == [w[0] for w in want] and got["main_b1_y2"] == [w[1] for w in want], (got, want)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    r1 = L.compile_matrix_latex("A_{ij} = i + j", 2, 3, then=[("B_{ij} = j", 1, 2)])
    tmp = tempfile.mkdtemp(prefix="mxcs_")
    try:
        icm = os.path.join(tmp, "m.icm")
        r1.save(icm)
        out = os.path.join(tmp, "g")
        p = _h.cli("-s", "sub", "--icm", icm, "--output", out)
        assert p.returncode == 0, (p.stderr or p.stdout)[:500]
        top = json.load(open(os.path.join(out, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(out, top + ".v")).read()
        ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
        items = [{n_: vec[int(re.search(r"mv0_(\d)_a", n_).group(1)) + 1] for n_ in ins} for vec in _X]
        got, _ = _sub.simulate(out, items)
        assert [g[1] for g in got] == [r1.reference({f"x_{j}": vec[j] for j in (1, 2, 3)})[0] for vec in _X], got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cli_then_and_runtime_matrix():
    import subprocess
    cli = os.path.join(_HERE, "..", "..", "nano", "latex_cli_v1.py")
    p = subprocess.run([sys.executable, cli, "A_{ij} = i j", "--matrix", "2x3", "--then", "B_{ij} = i + j @ 3x2", "--set", "x_1=1", "--set", "x_2=2", "--set", "x_3=3"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "y_1 = 112, y_2 = 154, y_3 = 196" in p.stdout and "matrix B (3x2): 2 3; 3 4; 4 5" in p.stdout
    p = subprocess.run([sys.executable, cli, "A_{ij}", "--matrix", "2x2", "--set", "x_1=1", "--set", "x_2=1", "--set", "A_1_1=1", "--set", "A_1_2=2", "--set", "A_2_1=3", "--set", "A_2_2=4"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "y_1 = 3, y_2 = 7" in p.stdout
    bad = subprocess.run([sys.executable, cli, "A_{ij} = i j", "--matrix", "2x3", "--then", "B_{ij} = i"], capture_output=True, text=True)
    assert bad.returncode == 1
