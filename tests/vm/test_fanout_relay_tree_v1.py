"""tests/vm/test_fanout_relay_tree_v1.py -- ledger #1065: a value read more than three times gets a relay tree (placer `routed_x`).

A cell has four faces and one is its input, so a value could feed at most three consumers; the `ashr` form of CORDIC reads x and y four times from the second iteration and was refused.
`fanout_relay_tree` inserts `copy` cells (one-cell pass-throughs) so every cell drives three or fewer.
Proves: the pass leaves a DAG with <=3 readers per value and does not touch the caller's list; programs that need nothing are unchanged; a value read 4, 7 and 10 times places and
computes the right answer; the ashr CORDIC (2 and 3 iterations, which v1/auto refuse) places and matches the integer model in the step simulator and in generated flex RTL.
Not covered: speed (each copy level adds a tick per item), more than 3 iterations."""
import os
import re
import shutil
import sys
import tempfile
import random

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for sub in ("nano", "tools", os.path.join("tests", "vm")):
    sys.path.insert(0, os.path.join(ROOT, sub))

import llvm_dag_frontend_v1 as F  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402
from flex_layout_view_v1 import Layout  # noqa: E402
import flex_layout_sim_v2 as S2  # noqa: E402
from test_vix_cross_router_v1 import ATAN, model, unpack  # noqa: E402

M = 0xFFFFFFFF


def cordic_ashr_ir(n):
    lines = []

    def op(t, nm):
        lines.append(f"  %{nm} = {t}")
        return "%" + nm
    x, y, z = "%x", "%y", "%z"
    for i in range(n):
        s = op(f"lshr i32 {z}, 31", f"s{i}")
        t = op(f"shl i32 {s}, 1", f"t{i}")
        m = op(f"mul i32 {t}, -1", f"m{i}")
        d = op(f"add i32 {m}, 1", f"d{i}")
        xs = op(f"ashr i32 {x}, {i}", f"xs{i}") if i else x
        ys = op(f"ashr i32 {y}, {i}", f"ys{i}") if i else y
        dy = op(f"mul i32 {d}, {ys}", f"dy{i}")
        dx = op(f"mul i32 {d}, {xs}", f"dx{i}")
        xn = op(f"sub i32 {x}, {dy}", f"xn{i}")
        yn = op(f"add i32 {y}, {dx}", f"yn{i}")
        da = op(f"mul i32 {d}, {ATAN[i]}", f"da{i}")
        zn = op(f"sub i32 {z}, {da}", f"zn{i}")
        x, y, z = xn, yn, zn
    xb = op(f"add i32 {x}, 32768", "xb")
    sh = op(f"shl i32 {y}, 16", "ysh")
    op(f"add i32 {xb}, {sh}", "r")
    return "define i32 @cordic(i32 %x, i32 %y, i32 %z) {\nentry:\n" + "\n".join(lines) + "\n  ret i32 %r\n}\n"


def input_map(src):
    m = {}
    args = set(re.findall(r"i32 %(\w+)", src.splitlines()[0]))
    for line in src.splitlines():
        mm = re.match(r"\s*%(\w+) = (\w+) i32 ([^,]+)(?:, (.+))?$", line)
        if not mm:
            continue
        res, op, a, b = mm.groups()
        isarg = lambda t: t is not None and t.strip().startswith("%") and t.strip()[1:] in args
        if op in ("shl", "lshr", "ashr"):
            if isarg(a):
                m[f"main.dynq_{res}_x"] = a.strip()[1:]
        else:
            if isarg(a):
                m[f"main.dynq_{res}_a"] = a.strip()[1:]
            if isarg(b):
                m[f"main.dynq_{res}_b"] = b.strip()[1:]
    return m


def many_readers_ir(k):
    """t = a + b is read k times: t*1+... as a sum of k different multiples so each read is a distinct cell."""
    lines = ["  %t = add i32 %a, %b"]
    acc = None
    for i in range(k):
        lines.append(f"  %m{i} = mul i32 %t, {i + 2}")
        if acc is None:
            acc = f"%m{i}"
        else:
            nm = "r" if i == k - 1 else f"s{i}"
            lines.append(f"  %{nm} = add i32 {acc}, %m{i}")
            acc = f"%{nm}"
    return "define i32 @f(i32 %a, i32 %b) {\nentry:\n" + "\n".join(lines) + f"\n  ret i32 {acc}\n}}\n"


def readers(dag):
    cnt = {}
    for i in dag:
        for o in i.operands:
            if o.kind == "ref":
                cnt[o.ref_name] = cnt.get(o.ref_name, 0) + 1
    return cnt


def final_dag(src):
    """The lowered DAG exactly as it reaches the relay-tree pass."""
    cap = {}
    orig = F.fanout_relay_tree

    def grab(final):
        cap["final"] = final
        raise ValueError("captured")
    F.fanout_relay_tree = grab
    try:
        F.compile_llvm_via_dag(src, placer="routed_x")
    finally:
        F.fanout_relay_tree = orig
    return cap["final"]


def run_items(res, its, cmap, spacing):
    tmp = tempfile.mkdtemp(prefix="fanout_")
    try:
        path = os.path.join(tmp, "d.icm")
        IcmV3File(name="d", records=res.records).save(path)
        sim = S2.StepSim(Layout.load(path), width=32)
        nxt, t = 0, 0
        while t < spacing * len(its) + 4000 and len(sim.seen["main.r"]) < len(its):
            if nxt < len(its) and t % spacing == 0:
                sim.inject({c: its[nxt][a] for c, a in cmap.items()})
                nxt += 1
            sim.step(1)
            t += 1
        return list(sim.seen["main.r"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_the_pass_leaves_three_readers_per_value_and_does_not_edit_the_callers_list():
    final = final_dag(many_readers_ir(10))
    assert max(readers(final).values()) == 10
    before = [(i.name, [(o.kind, o.ref_name) for o in i.operands]) for i in final]
    new, added = F.fanout_relay_tree(final)
    assert added > 0 and max(readers(new).values()) <= 3
    assert before == [(i.name, [(o.kind, o.ref_name) for o in i.operands]) for i in final]
    names = [i.name for i in new]
    assert len(names) == len(set(names))
    pos = {n: k for k, n in enumerate(names)}
    for i in new:                                          # every read comes after its producer
        for o in i.operands:
            if o.kind == "ref":
                assert pos[o.ref_name] < pos[i.name]


def test_a_program_that_needs_no_relays_is_left_alone():
    src = "define i32 @f(i32 %a, i32 %b) {\nentry:\n  %s = add i32 %a, %b\n  %t = mul i32 %s, 3\n  ret i32 %t\n}\n"
    final = final_dag(src)
    new, added = F.fanout_relay_tree(final)
    assert added == 0 and [i.name for i in new] == [i.name for i in final]


def test_default_placers_still_refuse_a_value_read_four_times():
    res, diags = F.compile_llvm_via_dag(many_readers_ir(4))
    assert res is None and diags


@pytest.mark.parametrize("k", [4, 7, 10])
def test_a_value_read_many_times_places_and_computes(k):
    src = many_readers_ir(k)
    res, diags = F.compile_llvm_via_dag(src, placer="routed_x")
    assert res is not None, [d.format([]) for d in diags]
    rng = random.Random(k)
    its = [{"a": rng.randint(-1000, 1000), "b": rng.randint(-1000, 1000)} for _ in range(3)]
    its = [{"a": v["a"] & M, "b": v["b"] & M} for v in its]
    got = run_items(res, its, input_map(src), spacing=400)
    want = [(((v["a"] + v["b"]) & M) * sum(range(2, k + 2))) & M for v in its]
    assert got == want


@pytest.fixture(scope="module", params=[2, 3])
def cordic(request):
    n = request.param
    src = cordic_ashr_ir(n)
    plain, _ = F.compile_llvm_via_dag(src)
    assert plain is None                                    # the default placer still refuses it
    res, diags = F.compile_llvm_via_dag(src, placer="routed_x")
    assert res is not None, [d.format([]) for d in diags]
    return n, src, res


def stim(n_items, seed=5):
    rng = random.Random(seed)
    return [(9949, 0, rng.randint(-8000, 8000)) for _ in range(n_items)]


def test_ashr_cordic_matches_the_model_in_the_step_simulator(cordic):
    n, src, res = cordic
    its = stim(3)
    got = run_items(res, [{"x": a & M, "y": b & M, "z": c & M} for a, b, c in its], input_map(src), spacing=600)
    assert [unpack(g) for g in got] == [model(a, b, c, n) for a, b, c in its]


def test_ashr_cordic_matches_the_model_in_generated_flex_rtl(cordic):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    from fp_block_runner_v1 import run_rtl
    n, src, res = cordic
    its = stim(4, seed=8)
    entries = {c: [{"x": it[0], "y": it[1], "z": it[2]}[a] & M for it in its] for c, a in input_map(src).items()}
    tmp = tempfile.mkdtemp(prefix="fanout_rtl_")
    try:
        got = run_rtl(tmp, f"cordic_ashr{n}", res.records, entries, {"r": "main.r"}, "plain", settle=9000, cycles=6000)["r"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert [unpack(g) for g in got] == [model(a, b, c, n) for a, b, c in its]
