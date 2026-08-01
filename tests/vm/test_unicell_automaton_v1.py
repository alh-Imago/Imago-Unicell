"""
test_unicell_automaton_v1.py — basic mechanics tests for the pure
cellular-automaton model, before building anything on top of it.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unicell_automaton_v1 import CAGrid, N, S, E, W
from unicell_v3 import TOPO_AND, TOPO_XOR, TOPO_PASS_B

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


# =============================================================================
print("=== Basic single-cell gate computation ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_AND, True
grid.inject(0, 0, 0xF0F0F0F0)
grid.tick()
check("first arrival stored", cell.a_arrived)
grid.inject(0, 0, 0x0F0F0F0F)
grid.tick()
check_eq("AND computed correctly", cell.data_reg, 0xF0F0F0F0 & 0x0F0F0F0F)


# =============================================================================
print("\n=== Propagation: fire reaches the correct physical neighbor ===")
# =============================================================================
grid = CAGrid(rows=1, cols=2)
c0, c1 = grid.cells[(0, 0)], grid.cells[(0, 1)]
c0.topology, c0.start_flag, c0.routing_mask = TOPO_PASS_B, True, (1 << E)
c1.topology, c1.start_flag = TOPO_AND, True

grid.inject(0, 0, 0x0)          # c0 first arrival
grid.tick()
grid.inject(0, 0, 0xABCDEF00)   # c0 trigger -> fires East to c1
grid.tick()
grid.tick()                     # deliver the queued outgoing fire to c1 (one tick latency)
check("c1 received c0's fire as its own first arrival", c1.a_arrived)
check_eq("c1's a_data == c0's fired value", c1.a_data, 0xABCDEF00)


# =============================================================================
print("\n=== Cardinal relay: a marked-cardinal incoming direction never touches a_data ===")
# =============================================================================
grid = CAGrid(rows=1, cols=3)
c0, c1, c2 = grid.cells[(0, 0)], grid.cells[(0, 1)], grid.cells[(0, 2)]
c0.topology, c0.start_flag, c0.routing_mask = TOPO_PASS_B, True, (1 << E)
c1.topology, c1.start_flag, c1.routing_mask = TOPO_AND, True, (1 << E)
c1.cardinal_edge = (1 << W)  # incoming from the West is a pure relay, not consumed
c2.topology, c2.start_flag = TOPO_AND, True

grid.inject(0, 0, 0x0)
grid.tick()
grid.inject(0, 0, 0xDEADBEEF)
grid.run_to_quiescence()
check("c1 (relay) never consumed the value -- a_arrived stays False", not c1.a_arrived)
check("c2 received the RELAYED value directly, two hops from the source", c2.a_arrived)
check_eq("c2's a_data == the original fired value, untouched by relay", c2.a_data, 0xDEADBEEF)


# =============================================================================
print("\n=== Multicast: one fire reaches multiple neighbors in the same tick ===")
# =============================================================================
grid = CAGrid(rows=2, cols=2)
branch = grid.cells[(0, 0)]
east_nb = grid.cells[(0, 1)]
south_nb = grid.cells[(1, 0)]
branch.topology, branch.start_flag, branch.routing_mask = TOPO_PASS_B, True, (1 << E) | (1 << S)
east_nb.topology, east_nb.start_flag = TOPO_AND, True
south_nb.topology, south_nb.start_flag = TOPO_AND, True

grid.inject(0, 0, 0x0)
grid.tick()
grid.inject(0, 0, 0x12345678)
active = grid.tick()
check_eq("only the branch cell was active on the firing tick", list(active.keys()), [(0, 0)])
grid.tick()  # deliver to both neighbors
check("East neighbor received the multicast", east_nb.a_arrived)
check("South neighbor received the SAME multicast, same tick", south_nb.a_arrived)


# =============================================================================
print("\n=== The core hypothesis: no shared-bus contention, multiple UNRELATED cells fire the same tick ===")
# =============================================================================
# Two completely independent 1-cell computations, on OPPOSITE corners of a
# grid, both primed and triggered to fire on the EXACT SAME ticks. Under
# the zone/card model this would be impossible (#70) -- here there's no
# shared resource for them to contend over at all.
grid = CAGrid(rows=4, cols=4)
a, b = grid.cells[(0, 0)], grid.cells[(3, 3)]
a.topology, a.start_flag = TOPO_AND, True
b.topology, b.start_flag = TOPO_XOR, True

grid.inject(0, 0, 0xFF00FF00)
grid.inject(3, 3, 0x00FF00FF)
active1 = grid.tick()
check_eq("BOTH cells received their first arrival in the SAME tick", set(active1.keys()), {(0, 0), (3, 3)})

grid.inject(0, 0, 0x0F0F0F0F)
grid.inject(3, 3, 0xF0F0F0F0)
active2 = grid.tick()
check_eq("BOTH cells fired in the SAME tick -- no contention, confirmed directly",
         set(active2.keys()), {(0, 0), (3, 3)})
check_eq("cell A computed correctly", a.data_reg, 0xFF00FF00 & 0x0F0F0F0F)
check_eq("cell B computed correctly", b.data_reg, 0x00FF00FF ^ 0xF0F0F0F0)


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
