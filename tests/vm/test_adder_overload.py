"""
test_adder_overload.py — the overload test Alan asked for directly:
feed the ripple-carry adder (points.md #75) a SECOND round of input data
before the FIRST round's chain-end results have been confirmed read,
and verify the new ready-flag/output-buffer mechanism (points.md #77)
correctly stalls rather than silently losing or corrupting data --
exactly the gap confirmed to exist (and now closed) in both cell types.

This directly exercises the backward cascade: the sum cells (chain-ends,
holding round 1's unconfirmed results) block round 2's carry chain from
completing, which in turn blocks the p_cell/g_cell/t_cell/carry_cell
stages further back, purely as a consequence of the same ready gate
applying uniformly at every cell -- no separate stall signal needed.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.adder_automaton_ripple import build_adder
from unicell_automaton_v1 import CAGrid

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if ok:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")


NUM_BITS = 4
grid = CAGrid(rows=3, cols=3 * NUM_BITS)
cells = build_adder(grid, NUM_BITS)


def inject_round(a: int, b: int):
    for i in range(NUM_BITS):
        ai, bi = (a >> i) & 1, (b >> i) & 1
        base = 3 * i
        grid.inject(1, base, ai)
        grid.inject(2, base + 2, ai)
        grid.tick()
        grid.inject(1, base, bi)
        grid.inject(2, base + 2, bi)
        grid.tick()
    grid.inject(0, 0, 0)
    grid.inject(1, 1, 0)
    grid.tick()


def read_sum() -> int:
    value = 0
    for i in range(NUM_BITS):
        value |= (cells[i]["sum"].out_buffer & 1) << i
    return value


# =============================================================================
print("=== ROUND 1: normal computation, 5 + 3, drain fully to quiescence ===")
# =============================================================================
inject_round(5, 3)
grid.run_to_quiescence(max_ticks=100)
round1_sum = read_sum()
check_eq("round 1 result correct (5+3=8)", round1_sum, 8)
check("sum cells are NOT ready (holding unconfirmed round-1 output)",
      all(not cells[i]["sum"].ready for i in range(NUM_BITS)))


# =============================================================================
print("\n=== ROUND 2: inject 9 + 1 WITHOUT confirming round 1's reads ===")
# =============================================================================
inject_round(9, 1)
# Run a bounded number of ticks (NOT to quiescence, since it genuinely
# should never quiesce while round 1 remains unconfirmed -- the whole
# point of this test) and verify it's actually stalled, not silently
# completed with wrong data.
for _ in range(50):
    grid.tick()

check_eq("round 1's result is STILL intact -- untouched by round 2's attempt",
         read_sum(), 8)
check("the pipeline is still stalled (pending events still queued, "
      "confirming it's genuinely blocked, not just slow)",
      len(grid._pending) > 0)


# =============================================================================
print("\n=== CONFIRM round 1's reads -- the 'memory-reading top command layer' ===")
# =============================================================================
for i in range(NUM_BITS):
    grid.confirm_read(0, 3 * i)  # sum_cell[i] position, per the ripple adder's own layout
# The final bit's carry_cell has no outgoing routing at all (there's no
# bit num_bits to receive it -- it's the adder's overflow output) --
# genuinely another unread output needing confirmation, correctly caught
# by the mechanism itself: the first version of this test forgot it, and
# the pipeline correctly stayed stuck until this was added, rather than
# silently completing with a bug hidden in it.
grid.confirm_read(1, 3 * (NUM_BITS - 1) + 2)  # carry_cell[last] position

check("sum cells are ready again immediately after confirmation",
      all(cells[i]["sum"].ready for i in range(NUM_BITS)))


# =============================================================================
print("\n=== Round 2 now flows through correctly, no data loss/corruption ===")
# =============================================================================
grid.run_to_quiescence(max_ticks=100)
round2_sum = read_sum()
check_eq("round 2 result correct (9+1=10), NOT corrupted by the earlier stall",
         round2_sum, 10)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED -- backward stall cascade confirmed, zero data loss/corruption")
