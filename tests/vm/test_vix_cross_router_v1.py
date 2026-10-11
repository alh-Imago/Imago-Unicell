"""tests/vm/test_vix_cross_router_v1.py -- ledger #1064: the LLVM compiler's routed placer can now use the CROSSING TILE.

Until now `vix_virtual_layout_v1.compile_dag_routed` refused any program whose routes must cross ("a non-planar program cannot be routed on a plane with no crossover cell"). A CORDIC
needs it from the SECOND iteration: x and y feed each other every stage. `vix_virtual_layout_v2.compile_dag_routed` (placer name `routed_x` in `compile_llvm_via_dag`) lets two routes pass
straight through one cell at right angles and lowers that cell to ONE `cross` tile (core_select 10), which the netlist step, FlexGrid and the flex generator already supported (#999).

What this proves (a 2-iteration 32-bit CORDIC written as LLVM IR, the multiply-by-d form):
  * v1 refuses it; v2 with allow_cross=False refuses it the same way (so the switch is the only difference); v2 places it, with `cross` tiles in the result;
  * the placed design computes the integer CORDIC model exactly: in the step simulator (every item) and in the GENERATED flex RTL, items back to back (needs iverilog);
  * for a program that needs no crossing, v2 gives the SAME cells as v1 (no behaviour change when nothing crosses);
  * `auto` (the default placer) is unchanged: it still refuses the 2-iteration program.
Not covered: more than 2 iterations in the suite (10 iterations were run by hand: bit-exact in the VM and in the generated RTL, see the ledger entry), the select form beyond 2 iterations, timing."""
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
import vix_virtual_layout_v1 as V1  # noqa: E402
import vix_virtual_layout_v2 as V2  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402
from flex_layout_view_v1 import Layout  # noqa: E402
from flex_layout_sim_v1 import StepSim  # noqa: E402

ATAN = [6434, 3798, 2007, 1019, 511, 256, 128, 64, 32, 16]


def cordic_ir(n):
    """n CORDIC rotation iterations; the conditional add/subtract is d*(shifted) with d = +-1 (a multiplier), the arithmetic shift is a biased logical shift."""
    lines = []

    def op(text, name):
        lines.append(f"  %{name} = {text}")
        return "%" + name

    def asr(v, i, tag):
        if i == 0:
            return v
        u = op(f"add i32 {v}, -2147483648", f"u{tag}{i}")
        s = op(f"lshr i32 {u}, {i}", f"l{tag}{i}")
        return op(f"sub i32 {s}, {1 << (31 - i)}", f"a{tag}{i}")

    x, y, z = "%x", "%y", "%z"
    for i in range(n):
        s = op(f"lshr i32 {z}, 31", f"s{i}")
        t = op(f"shl i32 {s}, 1", f"t{i}")
        m = op(f"mul i32 {t}, -1", f"m{i}")
        d = op(f"add i32 {m}, 1", f"d{i}")
        xs, ys = asr(x, i, "x"), asr(y, i, "y")
        dys = op(f"mul i32 {d}, {ys}", f"dy{i}")
        dxs = op(f"mul i32 {d}, {xs}", f"dx{i}")
        xn = op(f"sub i32 {x}, {dys}", f"xn{i}")
        yn = op(f"add i32 {y}, {dxs}", f"yn{i}")
        da = op(f"mul i32 {d}, {ATAN[i]}", f"da{i}")
        zn = op(f"sub i32 {z}, {da}", f"zn{i}")
        x, y, z = xn, yn, zn
    xb = op(f"add i32 {x}, 32768", "xb")
    sh = op(f"shl i32 {y}, 16", "ysh")
    r = op(f"add i32 {xb}, {sh}", "r")
    return "define i32 @cordic(i32 %x, i32 %y, i32 %z) {\nentry:\n" + "\n".join(lines) + f"\n  ret i32 {r}\n}}\n"


def input_map(n):
    """compiled input cell -> function argument (one input cell per USE of an argument)."""
    import re
    m = {}
    for line in cordic_ir(n).splitlines():
        mm = re.match(r"\s*%(\w+) = (\w+) i32 ([^,]+)(?:, (.+))?$", line)
        if not mm:
            continue
        res, op, a, b = mm.groups()
        isarg = lambda t: t is not None and t.strip().startswith("%") and t.strip()[1:] in ("x", "y", "z")
        if op in ("shl", "lshr"):
            if isarg(a):
                m[f"main.dynq_{res}_x"] = a.strip()[1:]
        else:
            if isarg(a):
                m[f"main.dynq_{res}_a"] = a.strip()[1:]
            if isarg(b):
                m[f"main.dynq_{res}_b"] = b.strip()[1:]
    return m


def model(x, y, z, n):
    for i in range(n):
        d = -1 if z < 0 else 1
        x, y, z = x - d * (y >> i), y + d * (x >> i), z - d * ATAN[i]
    return x, y


def unpack(r):
    lo = (r & 0xFFFF) - 32768
    hi = (r >> 16) & 0xFFFF
    return lo, (hi - 65536 if hi >= 32768 else hi)


def stimulus(n_items, seed=5):
    rng = random.Random(seed)
    return [(9949, 0, rng.randint(-8000, 8000)) for _ in range(n_items)]


@pytest.fixture(scope="module")
def placed():
    result, diags = F.compile_llvm_via_dag(cordic_ir(2), placer="routed_x")
    assert result is not None, [d.format([]) for d in diags]
    return result


def _dag_instrs(src):
    cap = {}
    orig = F.compile_dag_routed_x

    def grab(final, **kw):
        cap["final"] = final
        raise V2.RouteFailure("captured")
    F.compile_dag_routed_x = grab
    try:
        F.compile_llvm_via_dag(src, placer="routed_x")
    finally:
        F.compile_dag_routed_x = orig
    return cap["final"]


def test_v1_refuses_the_two_iteration_cordic_and_v2_without_crossing_refuses_it_the_same_way():
    final = _dag_instrs(cordic_ir(2))
    with pytest.raises(V1.RouteFailure):
        V1.compile_dag_routed(final, attempts=2, spacings=(6,))
    with pytest.raises(V2.RouteFailure):
        V2.compile_dag_routed(final, attempts=2, spacings=(6,), allow_cross=False)


def test_auto_placer_is_unchanged_and_still_refuses():
    result, diags = F.compile_llvm_via_dag(cordic_ir(2))
    assert result is None and any("place" in d.format(cordic_ir(2).splitlines()) for d in diags)


def test_v2_places_it_with_cross_tiles(placed):
    cores = {}
    for r in placed.records:
        cores[r.core] = cores.get(r.core, 0) + 1
    assert placed.placer == "routed_x"
    assert cores.get("cross", 0) >= 4, cores
    for r in placed.records:                                   # every cross tile has its two straight pairs recorded
        if r.core == "cross":
            up, down = r.core_config["upstream_mask"], r.core_config["downstream_mask"]
            assert len(up) == 2 and len(down) == 2


def test_the_placed_design_matches_the_integer_model_in_the_step_simulator(placed):
    tmp = tempfile.mkdtemp(prefix="crossrouter_")
    try:
        path = os.path.join(tmp, "cordic2.icm")
        IcmV3File(name="cordic2", records=placed.records).save(path)
        layout = Layout.load(path)
        sim = StepSim(layout, width=32)
        imap = input_map(2)
        items = stimulus(6)
        spacing, nxt, t = 120, 0, 0                                # the input cells take a value only when free: one item per `spacing` ticks
        while t < spacing * len(items) + 1500 and len(sim.seen["main.r"]) < len(items):
            if nxt < len(items) and t % spacing == 0:
                x, y, z = items[nxt]
                sim.inject({c: {"x": x, "y": y, "z": z}[a] for c, a in imap.items()})
                nxt += 1
            sim.step(1)
            t += 1
        outs = sim.seen["main.r"]
        assert len(outs) == len(items)
        assert [unpack(o) for o in outs] == [model(*it, 2) for it in items]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_the_placed_design_matches_the_model_in_generated_flex_rtl_back_to_back(placed):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    from fp_block_runner_v1 import run_rtl
    imap = input_map(2)
    items = stimulus(8, seed=7)
    entries = {c: [{"x": it[0], "y": it[1], "z": it[2]}[a] & 0xFFFFFFFF for it in items] for c, a in imap.items()}
    tmp = tempfile.mkdtemp(prefix="crossrouter_rtl_")
    try:
        got = run_rtl(tmp, "cordic2x", placed.records, entries, {"r": "main.r"}, "plain", settle=7000, cycles=4000)["r"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert len(got) == len(items)
    assert [unpack(g) for g in got] == [model(*it, 2) for it in items]


def test_a_program_that_needs_no_crossing_places_identically_in_v1_and_v2():
    src = ("define i32 @f(i32 %a, i32 %b) {\nentry:\n  %s = add i32 %a, %b\n  %t = mul i32 %s, 3\n  %u = sub i32 %t, 7\n  ret i32 %u\n}\n")
    final = _dag_instrs(src)
    a = V1.compile_dag_routed(final)[0].flatten()[0]
    b = V2.compile_dag_routed(final)[0].flatten()[0]
    key = lambda cells: sorted((c.cell_id, c.row, c.col, c.core, str(sorted(c.core_config.items(), key=str))) for c in cells)
    assert key(a) == key(b)
    assert not any(c.core == "cross" for c in b)


def test_legal_crossing_rule_unit():
    class E:
        def __init__(self, name):
            self.name = name
            self.src_face = "e"
            self.dst_face = "w"
    ew, ns = E("ew"), E("ns")
    # ew runs W->E through (5,5); ns runs N->S through (5,5): a crossing
    p_ew = [(5, 3), (5, 4), (5, 5), (5, 6), (5, 7)]
    p_ns = [(3, 5), (4, 5), (5, 5), (6, 5), (7, 5)]
    assert (5, 5) in V2._legal_crossings([(ew, p_ew), (ns, p_ns)])
    # two routes running the SAME way through a cell are a conflict, not a crossing
    p_ew2 = [(5, 4), (5, 5), (5, 6)]
    assert (5, 5) not in V2._legal_crossings([(ew, p_ew), (E("b"), p_ew2)])
    # a route that TURNS at the cell is not a crossing
    p_turn = [(4, 5), (5, 5), (5, 6)]
    assert (5, 5) not in V2._legal_crossings([(ew, p_ew), (E("t"), p_turn)])
    # a route end (touching a node pin) is never a crossing
    p_end = [(5, 5), (6, 5), (7, 5)]
    assert (5, 5) not in V2._legal_crossings([(ew, p_ew), (E("e"), p_end)])
