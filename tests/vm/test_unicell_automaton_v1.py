"""
test_unicell_automaton_v1.py — basic mechanics tests for the pure
cellular-automaton model, before building anything on top of it.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from unicell_automaton_v1 import CAGrid, N, S, E, W
from unicell_gate_core import TOPO_AND, TOPO_XOR, TOPO_PASS_B

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
print("\n=== Phase 2 (2026-08-04 rebuild): pending_ack now waits for ALL targeted directions ===")
# =============================================================================
grid = CAGrid(rows=2, cols=2)
c00, c01, c10 = grid.cells[(0, 0)], grid.cells[(0, 1)], grid.cells[(1, 0)]
c00.topology, c00.start_flag, c00.routing_mask = TOPO_PASS_B, True, (1 << E) | (1 << S)
c01.topology, c01.start_flag = TOPO_AND, True    # East neighbor: free to accept immediately
c10.topology, c10.start_flag = TOPO_AND, True
c10.freeze_in = True                              # South neighbor: deliberately stalled

grid.inject(0, 0, 0x0)
grid.tick()
grid.inject(0, 0, 0xCAFEBABE)
grid.tick()   # c00 fires to BOTH E and S -- pending_ack should have both bits set
check("c00 not ready yet -- neither neighbor has consumed its copy", not c00.ready)
grid.tick()   # East neighbor (unfrozen) accepts; South neighbor (frozen) rejects/retries
check_eq("c01 (East, unfrozen) received the multicast", c01.a_data, 0xCAFEBABE)
check("c10 (South, frozen) did NOT consume its copy yet", not c10.a_arrived)
check("c00 STILL not ready -- East acked, but South has not (the real bug this phase fixes)",
      not c00.ready)
c10.freeze_in = False
grid.tick()   # South neighbor retries and now accepts
check("c10 (South, released) now received the multicast", c10.a_arrived)
check("c00 IS ready again now that BOTH targeted directions have genuinely acked",
      c00.ready)


# =============================================================================
print("\n=== Phase 2: relay_fire is now ready-gated, matching current RTL (was NOT true in the original file) ===")
# =============================================================================
grid = CAGrid(rows=1, cols=3)
c0, c1, c2 = grid.cells[(0, 0)], grid.cells[(0, 1)], grid.cells[(0, 2)]
c0.topology, c0.start_flag, c0.routing_mask = TOPO_PASS_B, True, (1 << E)
c1.topology, c1.start_flag, c1.routing_mask = TOPO_AND, True, (1 << E)
c1.cardinal_edge = (1 << W)     # West is a pure relay
c2.topology, c2.start_flag = TOPO_AND, True
c2.freeze_in = True             # deliberately stalled -- never acks c1's relay

grid.inject(0, 0, 0x0)
grid.tick()
grid.inject(0, 0, 0x11111111)
grid.tick()          # c0 fires -> queued to c1
grid.tick()          # c1 relays -> out_buffer=0x11111111, pending_ack set (East), queued to frozen c2
check_eq("c1 relayed the first value", c1.out_buffer, 0x11111111)
check("c1 not ready -- frozen c2 hasn't acked the relay yet", not c1.ready)
grid.tick()          # c2 (frozen) rejects/retries -- still doesn't ack
check("c1 STILL not ready -- c2 remains frozen", not c1.ready)

grid.inject(0, 0, 0x0)
grid.tick()
grid.inject(0, 0, 0x22222222)
grid.tick()          # c0 fires again -> queued to c1
grid.tick()          # c1 tries to relay AGAIN while still not ready -- must be rejected/retried
check_eq("c1's out_buffer STILL holds the FIRST value -- second relay correctly stalled",
         c1.out_buffer, 0x11111111)
c2.freeze_in = False
grid.run_to_quiescence()
check_eq("once c2 is released, the SECOND relay finally lands", c1.out_buffer, 0x22222222)


# =============================================================================
print("\n=== Phase 2: freeze_in fully pauses a cell -- no capture, no fire ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_AND, True
cell.freeze_in = True
grid.inject(0, 0, 0xAAAA0000)
grid.tick()
check("frozen cell never captured the arrival", not cell.a_arrived)
cell.freeze_in = False
grid.inject(0, 0, 0xAAAA0000)
grid.tick()
check("released cell captures normally", cell.a_arrived)


# =============================================================================
print("\n=== Phase 2: relay/consume mismatch -- genuine error, protective freeze ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_AND, True  # topology irrelevant here
cell.cardinal_edge = (1 << N)   # North=relay, South=consume (mismatch by construction)
# Deliver North (relay-tagged) and South (consume-tagged) in the SAME tick.
grid._pending[(0, 0)] = [(None, N, 0xDEAD0000), (None, S, 0xBEEF0000)]
grid.tick()
check("relay/consume mismatch set error_frozen", cell.error_frozen)
grid.inject(0, 0, 0x11110000)
grid.tick()
check("cell stays frozen going forward -- next arrival does not capture", not cell.a_arrived)


# =============================================================================
print("\n=== Phase 2: hold_in + a_update_in -- arriving value replaces A directly ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag, cell.hold_in = TOPO_AND, True, True
grid.inject(0, 0, 0xAAAA0000)
grid.tick()
check_eq("first arrival stored as A", cell.a_data, 0xAAAA0000)
cell.a_update_in = True
grid.inject(0, 0, 0xCAFE0000)
grid.tick()
check_eq("a_update_in REPLACED A directly, no gate computation", cell.a_data, 0xCAFE0000)
check("a_update did not touch out_buffer", cell.out_buffer is None)


# =============================================================================
print("\n=== Phase 2: hold_in + a_reemit_in -- re-emits held A unprocessed ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag, cell.hold_in = TOPO_AND, True, True
grid.inject(0, 0, 0xDEADBEEF)
grid.tick()
cell.a_reemit_in = True
grid.inject(0, 0, 0x0)   # trigger's own value is ignored entirely
grid.tick()
check_eq("re-emit pushed the HELD value, unprocessed, ignoring the trigger's own value",
         cell.out_buffer, 0xDEADBEEF)


# =============================================================================
print("\n=== Phase 2: is_command_cell -- permanent reemit, no live control wire needed ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_AND, True
cell.a_data, cell.a_arrived = 0xC0FFEE00, True   # pre-armed, as if already captured once
cell.is_command_cell = True
grid.inject(0, 0, 0x0)
grid.tick()
check_eq("command cell re-emitted its held value with zero live control wires set",
         cell.out_buffer, 0xC0FFEE00)


# =============================================================================
print("\n=== Phase 2: comparator-driven routing (dynamic_route_en) ===")
# =============================================================================
grid = CAGrid(rows=3, cols=3)
mid = grid.cells[(1, 1)]
mid.topology, mid.start_flag = TOPO_PASS_B, True
mid.routing_mask = (1 << N) | (1 << S) | (1 << E) | (1 << W)
mid.dynamic_route_en = True
mid.pattern_low, mid.pattern_equal, mid.pattern_high = (1 << N), (1 << E), (1 << S)
for pos in [(0, 1), (2, 1), (1, 0), (1, 2)]:
    grid.cells[pos].topology, grid.cells[pos].start_flag = TOPO_PASS_B, True

grid.inject(1, 1, 100)
grid.tick()
grid.inject(1, 1, 200)   # 200 > 100 -> HIGH -> pattern_high -> South only
grid.tick()
grid.tick()
check("HIGH comparator result routed South only", grid.cells[(2, 1)].a_arrived)
check("HIGH comparator result did NOT route North", not grid.cells[(0, 1)].a_arrived)

grid2 = CAGrid(rows=3, cols=3)
mid2 = grid2.cells[(1, 1)]
mid2.topology, mid2.start_flag = TOPO_PASS_B, True
mid2.routing_mask = (1 << N) | (1 << S) | (1 << E) | (1 << W)
mid2.dynamic_route_en = True
mid2.pattern_low, mid2.pattern_equal, mid2.pattern_high = (1 << N), (1 << E), (1 << S)
for pos in [(0, 1), (2, 1), (1, 0), (1, 2)]:
    grid2.cells[pos].topology, grid2.cells[pos].start_flag = TOPO_PASS_B, True
grid2.inject(1, 1, 100)
grid2.tick()
grid2.inject(1, 1, 50)   # 50 < 100 -> LOW -> pattern_low -> North only
grid2.tick()
grid2.tick()
check("LOW comparator result routed North only", grid2.cells[(0, 1)].a_arrived)
check("LOW comparator result did NOT route South", not grid2.cells[(2, 1)].a_arrived)


# =============================================================================
print("\n=== Phase 3: internal feedback -- oscillates against its own out_buffer, no arrival needed ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_XOR, True
grid.inject(0, 0, 0xAAAA0000)
grid.tick()
grid.inject(0, 0, 0x0000FFFF)
grid.tick()   # ordinary fire: data_reg=A=0xAAAA0000, out_buffer = A XOR B
first_out = cell.out_buffer
check_eq("seeded via a normal fire first", first_out, 0xAAAA0000 ^ 0x0000FFFF)

cell.hold_in = True
cell.fb_internal_in = True
before = cell.out_buffer
grid.tick()   # no injection at all -- purely internal_feedback_step
check("out_buffer changed on a tick with ZERO external arrival", cell.out_buffer != before)
check_eq("out_buffer == XOR(a_data, previous out_buffer), matching the real gate",
         cell.out_buffer, cell.a_data ^ before)
check_eq("a_data (A) stayed FIXED -- a_self_update_in is off by default", cell.a_data, 0xAAAA0000)

second = cell.out_buffer
grid.tick()
check("continues oscillating on the NEXT tick too, still with no arrival", cell.out_buffer != second)


# =============================================================================
print("\n=== Phase 3: a_self_update_in -- the threshold itself evolves instead of out_buffer ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_XOR, True
grid.inject(0, 0, 0x0F0F0F0F)
grid.tick()
grid.inject(0, 0, 0xF0F0F0F0)
grid.tick()
cell.hold_in, cell.fb_internal_in, cell.a_self_update_in = True, True, True
prev_a, prev_buf = cell.a_data, cell.out_buffer
grid.tick()
check_eq("a_data (the threshold) REPLACED by the computed result",
         cell.a_data, prev_a ^ prev_buf)
check_eq("out_buffer stays FIXED when a_self_update_in is on", cell.out_buffer, prev_buf)


# =============================================================================
print("\n=== Phase 3: internal feedback respects freeze -- stops oscillating, resumes on release ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_XOR, True
grid.inject(0, 0, 0x1)
grid.tick()
grid.inject(0, 0, 0x2)
grid.tick()
cell.hold_in, cell.fb_internal_in = True, True
grid.tick()
frozen_value = cell.out_buffer
cell.freeze_in = True
grid.tick()
grid.tick()
check_eq("frozen: out_buffer does NOT change across multiple ticks", cell.out_buffer, frozen_value)
cell.freeze_in = False
grid.tick()
check("released: oscillation resumes", cell.out_buffer != frozen_value)


# =============================================================================
print("\n=== Phase 4: wire-level programming -- COMPLETE-with-LSB arms/disarms exactly like #156 ===")
# =============================================================================
from unicell_automaton_v1 import (
    PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_CARDINAL_EDGE,
    PROG_ID_PATTERN_LOW, PROG_ID_DYN_ROUTE_EN, PROG_ID_COMPLETE,
)

grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
check("fresh cell starts disarmed (start_flag defaults False)", not cell.start_flag)

cell.program_in = True
cell.program_word(PROG_ID_TOPOLOGY, TOPO_AND)
cell.program_word(PROG_ID_ROUTING_MASK, 1 << E)
cell.program_word(PROG_ID_COMPLETE, 0)   # LSB=0: commit but stay COLD
cell.program_in = False
check_eq("topology committed even though COMPLETE's LSB was 0", cell.topology, TOPO_AND)
check_eq("routing_mask committed too", cell.routing_mask, 1 << E)
check("STILL disarmed -- COMPLETE with LSB=0 does not arm", not cell.start_flag)
check("program_done set on COMPLETE regardless of the arm bit", cell.program_done)

grid.inject(0, 0, 0xAAAA0000)
grid.tick()
check("a cold cell does not capture even a genuine arrival", not cell.a_arrived)

cell.program_in = True
cell.program_word(PROG_ID_COMPLETE, 1)   # LSB=1: arm now
cell.program_in = False
check("re-armed via COMPLETE with LSB=1", cell.start_flag)

grid.tick()   # the earlier rejected arrival is still pending -- retry now succeeds
check("now-armed cell captures the (retried) arrival", cell.a_arrived)


# =============================================================================
print("\n=== Phase 4: program_in suspends ALL ordinary operation -- arrivals rejected, not dropped ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.topology, cell.start_flag = TOPO_AND, True
cell.program_in = True
grid.inject(0, 0, 0xDEAD0000)
grid.tick()
check("arrival during programming was NOT consumed", not cell.a_arrived)
cell.program_in = False
grid.tick()
check("once program_in drops, the SAME retried arrival is finally captured", cell.a_arrived)


# =============================================================================
print("\n=== Phase 4: staged reconfiguration -- disarm, apply a field write, re-arm ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.program_in = True
cell.program_word(PROG_ID_TOPOLOGY, TOPO_AND)
cell.program_word(PROG_ID_ROUTING_MASK, 1 << N)
cell.program_word(PROG_ID_COMPLETE, 1)
cell.program_in = False
check("armed after first programming pass", cell.start_flag)

cell.program_in = True
cell.program_word(PROG_ID_COMPLETE, 0)   # explicit disarm, no field touched
cell.program_in = False
check("explicit re-disarm took effect", not cell.start_flag)

cell.program_in = True
cell.program_word(PROG_ID_ROUTING_MASK, 1 << E)   # change routing WHILE cold
cell.program_word(PROG_ID_COMPLETE, 1)            # re-arm
cell.program_in = False
check("re-armed with the new routing live", cell.start_flag)
check_eq("routing_mask genuinely changed while disarmed", cell.routing_mask, 1 << E)


# =============================================================================
print("\n=== Phase 4: cardinal_edge and comparator-pattern fields program correctly too ===")
# =============================================================================
grid = CAGrid(rows=1, cols=1)
cell = grid.cells[(0, 0)]
cell.program_in = True
cell.program_word(PROG_ID_CARDINAL_EDGE, 1 << N)
cell.program_word(PROG_ID_PATTERN_LOW, 1 << S)
cell.program_word(PROG_ID_DYN_ROUTE_EN, 1)
cell.program_word(PROG_ID_COMPLETE, 1)
cell.program_in = False
check_eq("cardinal_edge programmed", cell.cardinal_edge, 1 << N)
check_eq("pattern_low programmed", cell.pattern_low, 1 << S)
check("dynamic_route_en programmed", cell.dynamic_route_en)


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
