"""
test_unicell_card_v3.py — Phase 7 tests for the card-level scheduling model.

Proves, against a real running card, exactly the properties points.md #70
derived from reading the RTL: priority (not OR) arbitration at zone
boundaries, receive/compute mutual exclusion within a zone, real
multicast fan-out kicking off several already-primed zones from one
fire, and a first real achieved-vs-ceiling measurement.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unicell_card_v3 import UniCellCardV3, N, S, E, W
from unicell_v3 import TOPO_PASS_B, TOPO_NOR

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


def arm_cell(cell, addr, out_addr, topology=TOPO_PASS_B, dynamic=False, routing_mask=0):
    cell.boot_commit(logical_addr=addr, auth_mask_bits=0)
    cell.reconfigure(topology=topology, start_flag=True)
    cell.set_output_set(True)
    cell.set_output_address(out_addr)
    if routing_mask:
        cell.set_route_latch(routing_mask=routing_mask, cardinal_edge=routing_mask)  # cardinal-only


# =============================================================================
print("=== Basic card construction ===")
# =============================================================================
card = UniCellCardV3(rows=2, cols=8, cells_per_zone=25)
check_eq("2x8 card has 16 zones", len(card.zones), 16)
check_eq("(0,0) has no North neighbor (edge)", card.neighbor(0, 0, N), None)
check_eq("(0,0) has no West neighbor (2-wide grid, always an edge)", card.neighbor(0, 0, W), None)
check_eq("(0,0) East neighbor is (0,1)", card.neighbor(0, 0, E), (0, 1))
check_eq("(0,0) South neighbor is (1,0)", card.neighbor(0, 0, S), (1, 0))
check_eq("(1,0) has no South neighbor (bottom edge)", card.neighbor(1, 0, S), None)


# =============================================================================
print("\n=== Fact 1: inbound arbitration is PRIORITY, not OR (host beats bridges) ===")
# =============================================================================
card = UniCellCardV3(rows=1, cols=1, cells_per_zone=4)
zone = card.zones[(0, 0)]
c0 = zone.array.cells[0]
arm_cell(c0, addr=0x10, out_addr=0x10)

# Queue a "bridge" pending_external AND schedule a host injection for the
# same tick -- host must win outright.
zone.pending_external.append(("bridge", 0x10, 0xBBBBBBBB))
card.schedule_host_injection(tick=0, row=0, col=0, addr=0x10, data=0xAAAAAAAA)
card.tick()
check_eq("host injection won over the queued bridge event (fact 1)", c0.a_data, 0xAAAAAAAA)
check_eq("zone recorded as 'receiving' this tick", zone.last_tick_state, "receiving")


# =============================================================================
print("\n=== Fact 1 continued: among multiple simultaneous bridges, last-declared wins, others silently dropped ===")
# =============================================================================
card = UniCellCardV3(rows=1, cols=1, cells_per_zone=4)
zone = card.zones[(0, 0)]
c0 = zone.array.cells[0]
arm_cell(c0, addr=0x10, out_addr=0x10)
zone.pending_external.append(("bridge", 0x10, 0x11111111))  # arrives "first" (declared first)
zone.pending_external.append(("bridge", 0x10, 0x22222222))  # arrives "second" (declared last -- wins)
card.tick()
check_eq("last-declared simultaneous bridge event wins, first is silently dropped",
         c0.a_data, 0x22222222)


# =============================================================================
print("\n=== Fact 2: a receiving zone cannot also advance its own internal computation ===")
# =============================================================================
card = UniCellCardV3(rows=1, cols=1, cells_per_zone=4)
zone = card.zones[(0, 0)]
c0, c1 = zone.array.cells[0], zone.array.cells[1]
arm_cell(c0, addr=0x10, out_addr=0x10)
arm_cell(c1, addr=0x11, out_addr=0x11)
zone.pending_internal = (0x11, 0x99999999)  # c1 has a queued internal continuation

# Same tick, ALSO schedule external (host) traffic for this zone.
card.schedule_host_injection(tick=0, row=0, col=0, addr=0x10, data=0x12345678)
card.tick()
check_eq("external event was applied (c0 got the host injection)", c0.a_data, 0x12345678)
check("internal continuation was SUPPRESSED this tick (c1 untouched, still no a_arrived)",
      not c1.a_arrived)
check_eq("zone recorded as 'receiving', not 'computing'", zone.last_tick_state, "receiving")

# Confirm the internal continuation is genuinely gone (consumed), not just delayed.
check("pending_internal was cleared, not deferred to next tick", card.zones[(0,0)].pending_internal is None)


# =============================================================================
print("\n=== The branch-cell scenario: one fire, multiple already-primed zones kicked off simultaneously ===")
# =============================================================================
# 1 branch zone (0,0) with a cell that fires cardinal-only toward E and S
# simultaneously (real routing_mask multicast, points.md #17 rule 2).
# Two neighboring zones (0,1) [East] and (1,0) [South] each have a
# PRE-ARMED, PRE-PRIMED cell waiting only for its second arrival.
card = UniCellCardV3(rows=2, cols=2, cells_per_zone=4)
branch_zone = card.zones[(0, 0)]
east_zone = card.zones[(0, 1)]
south_zone = card.zones[(1, 0)]

branch_cell = branch_zone.array.cells[0]
arm_cell(branch_cell, addr=0x50, out_addr=0x60, topology=TOPO_PASS_B,
         dynamic=False, routing_mask=(1 << E) | (1 << S))  # E|S multicast, cardinal-only

east_worker = east_zone.array.cells[0]
arm_cell(east_worker, addr=0x60, out_addr=0x60, topology=TOPO_NOR)
south_worker = south_zone.array.cells[0]
arm_cell(south_worker, addr=0x60, out_addr=0x60, topology=TOPO_NOR)

# Pre-prime both workers' first arrival (already "waiting for their other
# half of data", per the scenario) -- BEFORE the branch cell ever fires.
card.schedule_host_injection(tick=0, row=0, col=1, addr=0x60, data=0xFFFFFFFF)
card.schedule_host_injection(tick=1, row=1, col=0, addr=0x60, data=0xFFFFFFFF)
# (host channel is one shared resource -- can't prime both in tick 0, matches
# points.md #70's confirmed single-host-bus constraint)
card.tick()  # tick 0: prime east_worker
card.tick()  # tick 1: prime south_worker
check("east_worker primed (first arrival stored)", east_worker.a_arrived)
check("south_worker primed (first arrival stored)", south_worker.a_arrived)

# Now fire the branch cell (prime, then trigger).
card.schedule_host_injection(tick=2, row=0, col=0, addr=0x50, data=0x0)   # branch cell prime
card.tick()
card.schedule_host_injection(tick=3, row=0, col=0, addr=0x50, data=0xDEADBEEF)  # trigger
stats_fire = card.tick()  # branch cell fires, multicasts to E and S -- queued for next tick
check_eq("branch fire tick: only the branch zone was active", stats_fire.busy, 1)

stats_deliver = card.tick()  # E and S zones both RECEIVE this tick, simultaneously
check_eq("both East and South zones received in the SAME tick (real multicast parallelism)",
         stats_deliver.busy, 2)
check_eq("East worker fired (NOR of 0xDEADBEEF, 0xFFFFFFFF)",
         east_worker.data_reg, (~(0xDEADBEEF | 0xFFFFFFFF)) & 0xFFFFFFFF)
check_eq("South worker fired identically -- same multicast payload reached both",
         south_worker.data_reg, (~(0xDEADBEEF | 0xFFFFFFFF)) & 0xFFFFFFFF)


# =============================================================================
print("\n=== achieved_vs_ceiling: a first real measurement, not reasoning ===")
# =============================================================================
card = UniCellCardV3(rows=2, cols=2, cells_per_zone=4)
# Deliberately leave most zones idle for several ticks to get a clearly
# sub-1.0 achieved fraction -- proves the metric actually discriminates.
c00 = card.zones[(0,0)].array.cells[0]
arm_cell(c00, addr=0x10, out_addr=0x10)
card.schedule_host_injection(tick=0, row=0, col=0, addr=0x10, data=0x1)
card.run(5)
frac = card.achieved_vs_ceiling()
check(f"achieved fraction ({frac:.3f}) is well below 1.0 (only one zone was ever active)",
      0.0 < frac < 0.3)


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
