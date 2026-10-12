"""tests/vm/test_division_loop_v1.py -- ledger #1068: division as a runtime loop, in the VM (repeated subtraction, #518's shape).

Three cells: SUB (accumulator, step = divisor), BR (branch, held reference = A-B, continue while SUB <= A-B, route to SUB and Q), Q (accumulator, step 1).
Harness steps, stated plainly: the branch's held reference is set on the cell directly (A-B worked out by the harness, as #518 did in RTL), and SUB's
freeze_in is driven each tick as 'frozen unless BR holds a continue', with one unfrozen tick at start (#518's freeze fix; without it the quotient is +1).
Limits shown here: divisor must fit the accumulator's 8-bit step; ticks grow with the quotient; divide by zero never halts."""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "nano"))

import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def build(a, b):
    cells = [
        vix.HierCell(cell_id="SUB", rel_row=1, rel_col=0, core="accumulator",
                     core_config={"inc_dir": ["e"], "downstream_mask": ["e"], "step_amount": b}),
        vix.HierCell(cell_id="BR", rel_row=1, rel_col=1, core="branch",
                     core_config={"upstream_dir": ["w"], "emit_low": 1, "emit_equal": 1, "emit_high": 0,
                                  "route_low": ["w", "e"], "route_equal": ["w", "e"], "route_high": []}),
        vix.HierCell(cell_id="Q", rel_row=1, rel_col=2, core="accumulator",
                     core_config={"inc_dir": ["w"], "step_amount": 1}),
    ]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                         placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="d")
    g = SuperGrid(icm.flatten()[0])
    br = g.cells[(1, 1)]
    br.br_ref_value, br.br_ref_valid = a - b, True
    return g


def run(a, b, freeze=True, ticks=None, settle=30):
    g = build(a, b)
    sub, br, q = g.cells[(1, 0)], g.cells[(1, 1)], g.cells[(1, 2)]
    last, prev, t = 0, None, 0
    while t < (ticks or 4 * (a // max(b, 1)) + 200):
        sub.freeze_in = freeze and t >= 1 and not br.br_data_valid
        g.tick()
        cur = (sub.acc_total, q.acc_total)
        if cur != prev:
            last, prev = t, cur
        t += 1
        if ticks is None and t - last > settle:
            break
    return q.acc_total, a - sub.acc_total, last


def test_known_cases_match_python():
    for a, b in [(23, 7), (21, 7), (3, 7), (100, 9), (0, 5), (255, 1), (255, 255), (256, 255), (1, 1), (96, 80)]:
        assert run(a, b)[:2] == (a // b, a % b), (a, b)


def test_random_cases_match_python():
    rnd = random.Random(1)
    for _ in range(60):
        a, b = rnd.randint(0, 3000), rnd.randint(1, 255)
        assert run(a, b)[:2] == (a // b, a % b), (a, b)


def test_without_the_freeze_gate_the_quotient_is_one_too_many():
    """The race #518 found in RTL appears in the VM too: a stale value is offered twice."""
    for a, b in [(23, 7), (21, 7), (100, 9)]:
        q, r, _ = run(a, b, freeze=False)
        assert (q, r) == (a // b + 1, a % b - b), (a, b, q, r)


def test_two_ticks_per_quotient_step():
    for a, b in [(100, 1), (1000, 10), (500, 5)]:
        assert run(a, b)[2] == 2 * (a // b), (a, b)


def test_divide_by_zero_never_halts():
    g = build(5, 0)
    sub, br, q = g.cells[(1, 0)], g.cells[(1, 1)], g.cells[(1, 2)]
    counts = []
    for t in range(600):
        sub.freeze_in = t >= 1 and not br.br_data_valid
        g.tick()
        if t in (299, 599):
            counts.append(q.acc_total)
    assert counts[1] > counts[0] > 0
