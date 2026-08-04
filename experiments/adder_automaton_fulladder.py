"""
adder_automaton_fulladder.py — one full-adder bit, built natively for the
pure automaton model (unicell_automaton_v1.py).

Scaled back deliberately from a full N-bit ripple chain, which turned out
to expose a real, non-trivial layout challenge worth stating honestly:
carry_out needs to reach the NEXT bit's sum-cell AND its AND-cell, and
those aren't simple one-hop neighbors of where carry_out is computed --
getting that wiring right needs careful, dedicated design, not a rushed
attempt. This file proves the actually-hard PART of a full adder works
correctly first: combining three inputs (a, b, cin) using only two-input
gates and next-hop-only wiring, with carry_in supplied externally here
rather than chained from a previous bit.

TWO REAL TECHNIQUES USED, worth naming explicitly since they're the
actual point of this experiment:

1. MULTICAST for a value needed in two places at once: p_cell computes
   p=a^b once, then fires to BOTH its sum-path neighbor and its
   carry-path neighbor in the same event (routing_mask multicast,
   points.md #17 rule 2 -- confirmed working here in the automaton model
   too, not just the zone-based one).

2. LOOP_BACK+LATCH_IN to let ONE cell hold a computed value and wait,
   armed, for a second value that arrives later (possibly much later,
   from a different source) -- avoiding the need to relay that first
   value elsewhere. The sum cell computes p=a^b, keeps it via loop_back,
   then fires XOR again the moment carry_in actually arrives, giving
   sum = p^cin using the SAME cell, no reconfiguration needed since the
   topology (XOR) is identical both times.

The carry-out cell needs to combine g=a&b with t=p&cin via OR -- since
topology only matters at FIRE time (not at storage time, when the first
arrival just gets stored), it can simply BE an OR gate throughout: g
arrives first and is stored without needing OR's logic at all, t arrives
second and triggers the actual g|t computation. No reconfiguration turned
out to be necessary once this was worked through carefully (an earlier
draft assumed it would be, and got the timing wrong -- caught and fixed
before trusting the result, not left in).

Verified against all 8 possible (a, b, cin) combinations, not just one.
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unicell_automaton_v1 import CAGrid, N, S, E, W
from unicell_gate_core import TOPO_AND, TOPO_XOR, TOPO_OR


def build_full_adder(grid: CAGrid):
    """
    Layout (every connection below is a real, single N/S/E/W hop --
    checked on paper before running, after an earlier attempt placed
    t_cell and carry_cell diagonally apart, which isn't reachable in one
    hop at all and was caught by the carry results failing):
      (0,0) p_cell   -- injected a,b (XOR). Fires E->sum_cell, S->t_cell.
      (0,1) sum_cell -- 1st arrival from W (p, via loop_back+latch_in,
                        reused as XOR). 2nd arrival from N... actually
                        injected directly here for this experiment
                        (carry_in has no prior-bit source yet).
      (1,0) t_cell   -- 1st arrival from N (p, relayed from p_cell).
                        2nd arrival: carry_in, injected directly here.
                        Fires AND -> t. Routes E->carry_cell.
      (1,1) carry_cell -- 1st arrival from W (t, from t_cell). 2nd
                        arrival from S (g, from g_cell) -> fires OR.
      (2,1) g_cell   -- injected a,b (AND). Fires N->carry_cell.
    """
    p_cell = grid.cells[(0, 0)]
    sum_cell = grid.cells[(0, 1)]
    t_cell = grid.cells[(1, 0)]
    carry_cell = grid.cells[(1, 1)]
    g_cell = grid.cells[(2, 1)]

    p_cell.topology, p_cell.start_flag = TOPO_XOR, True
    p_cell.routing_mask = (1 << E) | (1 << S)

    sum_cell.topology, sum_cell.start_flag = TOPO_XOR, True
    sum_cell.latch_in = True
    sum_cell.loop_back = True

    t_cell.topology, t_cell.start_flag = TOPO_AND, True
    t_cell.routing_mask = (1 << E)

    carry_cell.topology, carry_cell.start_flag = TOPO_OR, True
    # NOTE: topology only matters at FIRE time (the second arrival), not
    # at storage time (the first) -- t arrives first and is just stored,
    # so carry_cell can simply BE an OR gate throughout; no mid-run
    # reconfiguration is actually needed.

    g_cell.topology, g_cell.start_flag = TOPO_AND, True
    g_cell.routing_mask = (1 << N)

    return dict(p=p_cell, sum=sum_cell, t=t_cell, g=g_cell, carry=carry_cell)


def run_full_adder(a: int, b: int, cin: int) -> tuple:
    grid = CAGrid(rows=3, cols=2)
    cells = build_full_adder(grid)

    # p_cell: a, then b -- fires p east and south.
    grid.inject(0, 0, a)
    grid.tick()
    grid.inject(0, 0, b)
    grid.tick()
    grid.tick()  # deliver p to sum_cell (W) and t_cell (N)

    # g_cell (now at (2,1)): a, then b -- fires g north to carry_cell.
    grid.inject(2, 1, a)
    grid.tick()
    grid.inject(2, 1, b)
    grid.tick()

    # sum_cell now holds p (via loop_back), armed for its next arrival --
    # feed carry_in directly (this experiment's stand-in for "eventually
    # chained from a previous bit").
    grid.inject(0, 1, cin)
    grid.tick()
    sum_result = cells["sum"].data_reg

    # t_cell: cin arrives as its second arrival (p already delivered above).
    grid.inject(1, 0, cin)
    grid.tick()
    # NOTE: tick() processes ALL pending events globally, not scoped to
    # one signal -- g_cell's fire (above) actually gets delivered to
    # carry_cell during one of these ticks too, not strictly "after" t as
    # an earlier comment here assumed. Traced precisely rather than left
    # as an unchecked assumption: it doesn't affect correctness, since OR
    # is commutative -- whichever of {t, g} arrives first is just stored,
    # whichever arrives second triggers the same g|t result either way.
    grid.tick()
    carry_result = cells["carry"].data_reg

    return sum_result & 1, carry_result & 1


if __name__ == "__main__":
    print("=" * 70)
    print("One full-adder bit, built natively for the automaton model")
    print("(carry_in supplied externally -- not yet chained between bits)")
    print("=" * 70)

    all_pass = True
    for a in (0, 1):
        for b in (0, 1):
            for cin in (0, 1):
                s, c = run_full_adder(a, b, cin)
                expected_sum = a ^ b ^ cin
                expected_carry = (a & b) | (b & cin) | (a & cin)
                ok = (s == expected_sum) and (c == expected_carry)
                all_pass = all_pass and ok
                status = "PASS" if ok else "FAIL"
                print(f"  a={a} b={b} cin={cin} -> sum={s} carry={c}  "
                      f"(expected sum={expected_sum} carry={expected_carry})  {status}")

    print()
    print("ALL 8 COMBINATIONS PASS" if all_pass else "SOME FAILED")
    if not all_pass:
        sys.exit(1)
