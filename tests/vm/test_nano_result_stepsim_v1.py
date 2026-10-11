"""tests/vm/test_nano_result_stepsim_v1.py -- ledger #1065: a design whose RESULT is a nano (and / or / xor) is now visible in the step simulator.

Before: StepSim (v1) skipped a nano output ("unsupported core 'nano'"), so `or` looked broken. It was not: the nano computed the right value. `flex_layout_sim_v2.StepSim` reads it.
Proves: and/or/xor of two variables and of a variable with a constant, several items, equal the Python result in the step simulator AND in generated flex RTL (needs iverilog);
a nano in the MIDDLE of a chain (or, then add) also works; v1 still shows nothing (so the fix is what changed the answer)."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for sub in ("nano", "tools", os.path.join("tests", "vm")):
    sys.path.insert(0, os.path.join(ROOT, sub))

import llvm_dag_frontend_v1 as F  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402
from flex_layout_view_v1 import Layout  # noqa: E402
import flex_layout_sim_v1 as S1  # noqa: E402
import flex_layout_sim_v2 as S2  # noqa: E402

OPS = {"and": lambda a, b: a & b, "or": lambda a, b: a | b, "xor": lambda a, b: a ^ b}
M = 0xFFFFFFFF


def ir_var(op):
    return f"define i32 @f(i32 %a, i32 %b) {{\nentry:\n  %r = {op} i32 %a, %b\n  ret i32 %r\n}}\n"


def ir_const(op, k):
    return f"define i32 @f(i32 %a) {{\nentry:\n  %r = {op} i32 %a, {k}\n  ret i32 %r\n}}\n"


def ir_mid():
    return "define i32 @f(i32 %a, i32 %b) {\nentry:\n  %t = or i32 %a, %b\n  %r = add i32 %t, 5\n  ret i32 %r\n}\n"


def compile_(src):
    res, diags = F.compile_llvm_via_dag(src, placer="routed_x")
    assert res is not None, [d.format([]) for d in diags]
    return res


def items(n, seed=3):
    rng = random.Random(seed)
    return [(rng.getrandbits(32), rng.getrandbits(32)) for _ in range(n)]


def run_step(res, sim_mod, its, cellmap, spacing=150):
    tmp = tempfile.mkdtemp(prefix="nanores_")
    try:
        path = os.path.join(tmp, "d.icm")
        IcmV3File(name="d", records=res.records).save(path)
        sim = sim_mod.StepSim(Layout.load(path), width=32)
        nxt, t = 0, 0
        while t < spacing * len(its) + 1500 and len(sim.seen["main.r"]) < len(its):
            if nxt < len(its) and t % spacing == 0:
                a, b = its[nxt]
                sim.inject({c: {"a": a, "b": b}[v] for c, v in cellmap.items()})
                nxt += 1
            sim.step(1)
            t += 1
        return list(sim.seen["main.r"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("op", sorted(OPS))
def test_nano_result_of_two_variables_in_the_step_simulator(op):
    res = compile_(ir_var(op))
    its = items(5)
    got = run_step(res, S2, its, {"main.dynq_r_a": "a", "main.dynq_r_b": "b"})
    assert got == [OPS[op](a, b) for a, b in its]


@pytest.mark.parametrize("op", sorted(OPS))
def test_nano_result_with_a_constant_in_the_step_simulator(op):
    k = 0x00FF00FF
    res = compile_(ir_const(op, k))
    its = items(5, seed=4)
    got = run_step(res, S2, its, {"main.dynq_r_x": "a"})
    assert got == [OPS[op](a, k) for a, _ in its]


def test_a_nano_in_the_middle_of_a_chain():
    res = compile_(ir_mid())
    its = items(4, seed=5)
    got = run_step(res, S2, its, {"main.dynq_t_a": "a", "main.dynq_t_b": "b"})
    assert got == [((a | b) + 5) & M for a, b in its]


def test_v1_simulator_still_shows_nothing_so_the_fix_is_what_changed_it():
    res = compile_(ir_var("or"))
    assert run_step(res, S1, items(2), {"main.dynq_r_a": "a", "main.dynq_r_b": "b"}) == []


@pytest.mark.parametrize("op", sorted(OPS))
def test_nano_result_matches_in_generated_flex_rtl(op):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    from fp_block_runner_v1 import run_rtl
    res = compile_(ir_var(op))
    its = items(6, seed=9)
    entries = {"main.dynq_r_a": [a for a, _ in its], "main.dynq_r_b": [b for _, b in its]}
    tmp = tempfile.mkdtemp(prefix="nanores_rtl_")
    try:
        got = run_rtl(tmp, "nano_" + op, res.records, entries, {"r": "main.r"}, "plain", settle=3000, cycles=3000)["r"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert [g & M for g in got] == [OPS[op](a, b) for a, b in its]
