"""
test_bounded_loop_ring_v1.py — points.md #649: the real VM-level
counterpart to `#638`'s own real, sim-verified RTL bounded loop ring
(`tb_nano_bounded_loop_ring_v1.v`) -- the same real 4-cell topology
(LOOPVAR --south--> LOOP_CTRL --east--> ADDER --north--> RAM_RELAY
--west--> LOOPVAR), built from the VM's own already-real, already-
proven primitives (`hold_in`/`a_reemit_in`/`a_update_in`, `#140`'s own
comparator-driven `dynamic_route_en` routing) -- none of these needed
building fresh, they already existed, predating this session.

REAL BUG FOUND AND FIXED WHILE BUILDING THIS (points.md #649): the
reset branch after a normal fire checked `self.latch_in` (this file's
own header already marks that field explicitly legacy/RTL-unconfirmed)
instead of `self.hold_in` (the real, RTL-confirmed field used
throughout this whole session's own `nano_gate_v4.v` work), and
additionally overwrote the held operand with the incoming arrival.
Confirmed directly against the real RTL's own `a_arrived <= hold_in;`
(data_reg untouched) before fixing. No existing test ever exercised a
SECOND round under `hold_in` (the only way this bug could show up) --
confirmed directly before the fix, not assumed safe.

REAL, SAME SEQUENCING LESSON as `#636`'s own RTL work, found again
here independently: `a_update_in` must be asserted BEFORE the real
value that needs to be caught by it lands, not after -- 
`SuperGrid.run_to_quiescence()` drains an entire real chain in one
call, so setting the flag afterward is always too late.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from unicell_automaton_v1 import CACell, N, S, E, W, TOPO_PASS_A
from unicell_super_automaton_v1 import SuperGrid, SuperCell

results = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")


# =============================================================================
print("=== #638's own real 4-cell bounded loop ring, built from the VM's own real primitives ===")
# =============================================================================
loopvar_ca = CACell(row=0, col=0, topology=TOPO_PASS_A, start_flag=True,
                     routing_mask=(1 << S), hold_in=True)
loopvar = SuperCell(row=0, col=0, core="nano", _nano=loopvar_ca)

loop_ctrl_ca = CACell(row=1, col=0, topology=TOPO_PASS_A, start_flag=True,
                       routing_mask=(1 << E) | (1 << S),
                       dynamic_route_en=True,
                       pattern_high=(1 << E),   # N>i (continue) -> east
                       pattern_equal=(1 << S),  # N==i (real exit) -> south
                       pattern_low=(1 << S))    # N<i (degenerate) -> south
loop_ctrl = SuperCell(row=1, col=0, core="nano", _nano=loop_ctrl_ca)

adder = SuperCell(row=1, col=1, core="adder",
                   adder_downstream_mask=(1 << N),
                   adder_upstream_mask=(1 << W) | (1 << S))

ram_relay = SuperCell(row=0, col=1, core="ram",
                       ram_downstream_mask=(1 << W),
                       ram_upstream_mask=(1 << S),
                       ram_fixed_mode=False)

grid = SuperGrid([])
grid.cells = {
    (0, 0): loopvar,
    (1, 0): loop_ctrl,
    (1, 1): adder,
    (0, 1): ram_relay,
}

# Real entry-seed: two arrivals (capture + can_fire), matching #636's
# own established real pattern -- the second (dummy) arrival is what
# produces LOOPVAR's first real offer into LOOP_CTRL.
grid.inject(0, 0, 0)
grid.run_to_quiescence()
grid.inject(0, 0, 0xDEADBEEF)
grid.run_to_quiescence()
check("entry-seed: LOOPVAR.a_data=0", loopvar_ca.a_data == 0)
check("entry-seed: LOOP_CTRL has real pending A (i=0) from LOOPVAR's own offer", loop_ctrl_ca.a_arrived)

N_BOUND = 3


def do_round(n_bound):
    """One real round: inject N into LOOP_CTRL (completing its real
    pending capture of i), let its own real comparator decide
    continue/exit. If continuing: inject the real constant B into
    ADDER, run to quiescence (the real relay through RAM_RELAY), then
    consume the real result into LOOPVAR (a_update_in) and reemit for
    the next round."""
    grid.inject(1, 0, n_bound)
    grid.run_to_quiescence()

    if not (adder.adder_a_arrived and not loop_ctrl_ca.a_arrived):
        return False

    # Real, necessary ordering, matching #636's own real fix: assert
    # a_update_in BEFORE the real value that needs to be caught by it
    # lands, not after.
    loopvar_ca.a_update_in = True

    grid.inject(1, 1, 1)   # real constant B=1, standing in for a not-yet-built source
    grid.run_to_quiescence()

    loopvar_ca.a_update_in = False

    # Real reemit: re-broadcast the now-updated value for the NEXT round.
    loopvar_ca.a_reemit_in = True
    grid.inject(0, 0, 0xFFFFFFFF)   # real "second arrival" trigger, ignored value
    grid.run_to_quiescence()
    loopvar_ca.a_reemit_in = False

    return True


cont = do_round(N_BOUND)
check("round 1: continued (0<3)", cont)
check("round 1: LOOPVAR.a_data=1 via the real VM adder+ram-relay chain", loopvar_ca.a_data == 1)

cont = do_round(N_BOUND)
check("round 2: continued (1<3)", cont)
check("round 2: LOOPVAR.a_data=2 via the real VM adder+ram-relay chain", loopvar_ca.a_data == 2)

cont = do_round(N_BOUND)
check("round 3: continued (2<3)", cont)
check("round 3: LOOPVAR.a_data=3 via the real VM adder+ram-relay chain", loopvar_ca.a_data == 3)

cont = do_round(N_BOUND)
check("round 4: real exit (3==3)", not cont)


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
    print("ALL TESTS PASSED")
