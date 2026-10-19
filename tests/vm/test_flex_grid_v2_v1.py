"""tests/vm/test_flex_grid_v2_v1.py -- FlexGrid v2, held constants (ledger #1271).
1. The CORDIC z-convergence streams give, word for word, what the Kintex card delivered (#1266) and what an independent four-step CORDIC computation gives.
2. FlexGrid v1 is unchanged: it still delivers only the first word of a stream (the behaviour v2 exists to fix), so nothing was edited under it.
3. v2 changes NOTHING for the 25 example designs: tools/vm_baseline_v1.py --check against the record taken before v2 existed (tests/baselines/vm_flexgrid_before_v2.json).
4. The rule is narrow: exactly the 8 constants of the CORDIC (the ones that feed adders) are held; the 4 zero references (they feed a merge) are not.
"""
import os
import subprocess
import sys
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import flex_grid_v1 as fg1  # noqa: E402
import flex_grid_v2 as fg2  # noqa: E402

CORDIC = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json")
ATAN = [45000, 26565, 14036, 7125]


def _cordic(z):
    # the design's branch routes `equal` the same way as `low` (route_equal = S), so z == 0 ADDS: positive subtracts, zero and negative add
    for a in ATAN:
        z = z - a if z > 0 else z + a
    return z


def _run(G, words, settle=12):
    doc, recs, *_ = nl.extract(CORDIC)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = G(recs)
    for _ in range(settle):
        g.tick()
    zi, zo = pos["s0.merge"], pos["s3.gather"]
    c, e = g.cells[zi], g.cells[zo]
    e.ram_data_valid = False
    todo, seen = list(words), []
    for _ in range(2500):
        if todo and not c.ram_data_valid and not g._pending.get(zi):
            g.inject(*zi, todo.pop(0))
        g.tick()
        if e.ram_data_valid:
            v = e.ram_data_reg
            seen.append(v - (1 << 32) if v >= 1 << 31 else v)
            e.ram_data_valid = False
    return seen, g


def test_cordic_streams_equal_the_card_and_the_independent_computation():
    assert _run(fg2.FlexGrid2, [10, 1, 2])[0] == [2736, 2727, 2728]          # the card, ledger #1266
    assert _run(fg2.FlexGrid2, [14, 100, 3])[0] == [2740, 2826, 2729]
    words = [50000, 10, 1, 100, 4294967291, 7, 30000, 0]
    assert _run(fg2.FlexGrid2, words)[0] == [_cordic(w - (1 << 32) if w >= 1 << 31 else w) for w in words]
    assert _run(fg2.FlexGrid2, [50000])[0] == [-404]                          # the value of the original test (#742)


def test_v1_is_unchanged():
    assert _run(fg1.FlexGrid, [10, 1, 2])[0] == [2736]                        # one word only: the behaviour v2 fixes
    assert _run(fg1.FlexGrid, [14, 100, 3])[0] == [2740]


def test_the_rule_is_narrow():
    held = _run(fg2.FlexGrid2, [10])[1]._held
    assert len(held) == 8
    names = {(r.row, r.col): r.cell_id for r in nl.extract(CORDIC)[1]}
    assert sorted(names[p].split(".")[1] for p in held) == ["const_neg"] * 4 + ["const_pos"] * 4
    assert not any(names[p].endswith("zero_source") for p in held)


def test_nothing_else_changes():
    base = os.path.join(ROOT, "tests", "baselines", "vm_flexgrid_before_v2.json")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "vm_baseline_v1.py"), "--check", base, "--grid", "flex2"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:]
