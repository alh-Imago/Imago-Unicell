"""
adder_automaton_ripple.py — a genuine N-bit ripple-carry adder for the
pure automaton model, resolving the layout difficulty from points.md #74
using Alan's suggestion directly: lean on cardinality -- one cell
receiving on one direction, firing out on two or three.

THE KEY MOVE: carry_out[i] doesn't need to reach two different cells in
bit i+1 directly. It only needs to reach ONE cell -- p_cell[i+1] -- which
already multicasts to its own two destinations (sum_cell[i], t_cell[i])
for its OWN p[i]=a[i]^b[i] value. Since a direct injection (a[i], b[i])
bypasses cardinal_edge entirely (it never arrives "from a direction"),
p_cell can mark its west-incoming direction as CARDINAL (pure relay) for
carry_in specifically, without that touching its own a/b-driven
computation at all -- then relay carry_in using the exact same
routing_mask it already uses for its own fire. One relayed value, reused
routing, no separate fan-out logic needed for carry at all.

This turns "carry needs to reach two non-adjacent cells" (points.md #74's
actual difficulty) into "carry needs to reach one adjacent cell, which
already knows how to fan out" -- solved by cardinality, not by more
relay cells.

Tile layout per bit i (base column = 3*i), every connection verified as
a genuine single hop before writing any code:
  sum_cell[i]   = (0, 3i)     -- north of p_cell[i]
  p_cell[i]     = (1, 3i)
  t_cell[i]     = (1, 3i+1)   -- east of p_cell[i]
  carry_cell[i] = (1, 3i+2)   -- east of t_cell[i]
  g_cell[i]     = (2, 3i+2)   -- south of carry_cell[i]
  carry_cell[i] fires EAST -> lands exactly on p_cell[i+1] = (1, 3(i+1))
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unicell_automaton_v1 import CAGrid, N, S, E, W
from unicell_gate_core import TOPO_AND, TOPO_XOR, TOPO_OR


def build_adder(grid: CAGrid, num_bits: int):
    cells = []
    for i in range(num_bits):
        base = 3 * i
        p = grid.cells[(1, base)]
        s = grid.cells[(0, base)]
        t = grid.cells[(1, base + 1)]
        c = grid.cells[(1, base + 2)]
        g = grid.cells[(2, base + 2)]

        p.topology, p.start_flag = TOPO_XOR, True
        p.routing_mask = (1 << N) | (1 << E)
        if i > 0:
            p.cardinal_edge = (1 << W)  # relay carry_in through, never consume it here

        s.topology, s.start_flag = TOPO_XOR, True
        t.topology, t.start_flag = TOPO_AND, True
        t.routing_mask = (1 << E)

        c.topology, c.start_flag = TOPO_OR, True
        if i < num_bits - 1:
            c.routing_mask = (1 << E)

        g.topology, g.start_flag = TOPO_AND, True
        g.routing_mask = (1 << N)

        cells.append(dict(p=p, sum=s, t=t, carry=c, g=g))
    return cells


def run_adder(a: int, b: int, num_bits: int) -> int:
    grid = CAGrid(rows=3, cols=3 * num_bits)
    cells = build_adder(grid, num_bits)

    for i in range(num_bits):
        ai, bi = (a >> i) & 1, (b >> i) & 1
        base = 3 * i
        grid.inject(1, base, ai)      # p_cell[i]: a
        grid.inject(2, base + 2, ai)  # g_cell[i]: a
        grid.tick()
        grid.inject(1, base, bi)      # p_cell[i]: b -- fires p north+east
        grid.inject(2, base + 2, bi)  # g_cell[i]: b -- fires g north
        grid.tick()

    # Bit 0 has no previous bit to relay carry_in=0 through p_cell -- the
    # real bug this fix addresses: without this, sum_cell[0]/t_cell[0]
    # never get a second arrival at all and simply never fire, which
    # silently produced sum=0 for every non-trivial case (caught by
    # actual test failures, not assumed correct).
    grid.inject(0, 0, 0)   # sum_cell[0]'s own second arrival: cin=0
    grid.inject(1, 1, 0)   # t_cell[0]'s own second arrival: cin=0
    grid.tick()

    # Drive enough further ticks for the carry chain to fully ripple
    # through every remaining bit (t_cell needs carry_in to fire, which
    # only arrives once the previous bit's carry_cell has fired, which
    # only happens once ITS t_cell has fired... genuinely sequential,
    # exactly as expected for ripple-carry).
    grid.run_to_quiescence(max_ticks=10 * num_bits + 20)

    sum_value = 0
    for i in range(num_bits):
        sum_value |= (cells[i]["sum"].data_reg & 1) << i
    return sum_value


if __name__ == "__main__":
    print("=" * 74)
    print("Genuine N-bit ripple-carry adder, pure automaton model")
    print("Carry resolved via cardinality (relay through p_cell), not extra fan-out")
    print("=" * 74)

    test_cases = [
        (0, 0, 4), (1, 1, 4), (7, 1, 4), (15, 1, 4), (5, 10, 4), (15, 15, 4),
        (0, 0, 8), (255, 1, 8), (170, 85, 8), (200, 100, 8),
    ]
    all_pass = True
    for a, b, n in test_cases:
        mask = (1 << n) - 1
        result = run_adder(a, b, n)
        expected = (a + b) & mask
        ok = result == expected
        all_pass = all_pass and ok
        print(f"  {n}-bit: {a:#0{n//4+2}x} + {b:#0{n//4+2}x} = {result:#0{n//4+2}x}  "
              f"expected={expected:#0{n//4+2}x}  {'PASS' if ok else 'FAIL'}")

    print()
    print("ALL PASS" if all_pass else "SOME FAILED")
    if not all_pass:
        sys.exit(1)
