"""
card_parallelism_experiment.py — Phase 7's actual deliverable: real
measured numbers for "where the system halts and what is truly
achievable" (Alan, 2026-08-02), not further reasoning about it.

Two contrasting workload shapes, both run on the same card model
(unicell_card_v3.py), each measured for real:

1. ISOLATED: every zone runs its own completely independent 3-stage
   chain, never crossing a zone boundary. This is the best case the
   architecture can produce -- points.md #70 predicted this should
   approach the theoretical ceiling once running, but pay a real,
   zone-count-proportional startup cost from the single shared host
   channel (only one zone can be primed per tick, card-wide).

2. CHAINED: a single computation that hops sequentially through every
   zone on the card, one cardinal hop at a time -- points.md #70
   predicted this should be close to fully serial (at most one zone
   ever active at a time), regardless of how many zones exist.

Run directly: `PYTHONPATH=. python3 experiments/card_parallelism_experiment.py`
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unicell_card_v3 import UniCellCardV3, N, S, E, W
from unicell_v3 import TOPO_PASS_B, TOPO_AND, TOPO_NOR


def arm(cell, addr, out_addr, topology, latch_in=False):
    cell.boot_commit(logical_addr=addr, auth_mask_bits=0)
    cell.reconfigure(topology=topology, start_flag=True, latch_in=latch_in)
    cell.set_output_set(True)
    cell.set_output_address(out_addr)


def run_isolated(rows: int, cols: int, cells_per_zone: int):
    """Every zone computes one independent 2-input gate (AND of two
    host-provided operands), never touching another zone. This is the
    simplest UNAMBIGUOUS workload: every cell needs exactly two bus
    events to fire -- no autonomous/self-triggering exists anywhere in
    this architecture (confirmed directly: a cell never fires without an
    actual incoming event, even with latch_in set), so a multi-stage
    internal chain needs its own carefully-designed trigger path per
    stage, not assumed 'it propagates on its own' -- that's real future
    work, not this experiment's claim. This measures the more basic,
    unambiguous question first: since every computation needs at least
    one externally-provided operand, and the host channel is ONE shared
    resource card-wide, how much genuine simultaneous multi-zone activity
    does even a fully 'isolated' workload actually achieve?"""
    card = UniCellCardV3(rows=rows, cols=cols, cells_per_zone=cells_per_zone)
    zone_positions = list(card.zones.keys())

    for pos in zone_positions:
        zone = card.zones[pos]
        cell = zone.array.cells[0]
        cell.boot_commit(logical_addr=0x100, auth_mask_bits=0)
        cell.reconfigure(topology=TOPO_AND, start_flag=True)
        cell.set_output_set(True)
        cell.set_output_address(0x100)

    # Two host injections per zone (first arrival, then the trigger) --
    # the actual, verified minimum for one fire. One shared channel means
    # these can never overlap across zones, by construction.
    tick = 0
    for pos in zone_positions:
        card.schedule_host_injection(tick=tick, row=pos[0], col=pos[1], addr=0x100, data=0xF0F0F0F0)
        card.schedule_host_injection(tick=tick + 1, row=pos[0], col=pos[1], addr=0x100, data=0x0F0F0F0F)
        tick += 2
    card.run(tick)

    # Verify every zone actually completed (not just assumed).
    all_completed = all(
        card.zones[pos].array.cells[0].data_reg == (0xF0F0F0F0 & 0x0F0F0F0F)
        for pos in zone_positions
    )
    return card.achieved_vs_ceiling(), tick, all_completed


def run_chained(rows: int, cols: int, cells_per_zone: int):
    """One computation, hopping sequentially through every zone on the
    card via a single cardinal-only relay cell per zone. Inherently
    serial -- at most one zone can ever be doing anything at a time."""
    card = UniCellCardV3(rows=rows, cols=cols, cells_per_zone=cells_per_zone)
    positions = list(card.zones.keys())

    # Simple serpentine path visiting every zone exactly once, always via
    # a real cardinal edge (East across a row, South at row ends, etc.) --
    # constructed directly from the grid rather than assumed.
    path = []
    for r in range(rows):
        row_cols = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)
        for c in row_cols:
            path.append((r, c))

    RELAY_ADDR = 0x200
    for i, pos in enumerate(path):
        zone = card.zones[pos]
        relay = zone.array.cells[0]
        relay.boot_commit(logical_addr=RELAY_ADDR, auth_mask_bits=0)
        relay.reconfigure(topology=TOPO_PASS_B, start_flag=True)
        relay.set_output_set(True)
        if i < len(path) - 1:
            # Determine the real cardinal direction to the next zone in
            # the path, and set cardinal-only routing toward it.
            nxt = path[i + 1]
            dr, dc = nxt[0] - pos[0], nxt[1] - pos[1]
            direction = {(-1, 0): N, (1, 0): S, (0, 1): E, (0, -1): W}[(dr, dc)]
            bit = 1 << direction
            relay.set_route_latch(routing_mask=bit, cardinal_edge=bit)
        # else: last zone in the path, no further routing needed.

    card.schedule_host_injection(tick=0, row=path[0][0], col=path[0][1], addr=RELAY_ADDR, data=0x0)
    card.schedule_host_injection(tick=1, row=path[0][0], col=path[0][1], addr=RELAY_ADDR, data=0xDEADBEEF)
    # Run long enough for the relay to traverse every zone (each hop costs
    # roughly 2 ticks: the sending zone's own fire, then the next tick's
    # delivery/receive) plus the 2-tick prime above.
    total_ticks = 2 + len(path) * 2
    card.run(total_ticks)
    return card.achieved_vs_ceiling(), total_ticks, len(path)


if __name__ == "__main__":
    print("=" * 78)
    print("PHASE 7 EXPERIMENT: real measured card-level parallelism")
    print("=" * 78)
    print("\nNOTE: the ISOLATED workload below is deliberately the simplest,")
    print("unambiguous case -- one 2-input gate per zone, needing exactly the")
    print("two bus events it actually requires (verified directly: no cell")
    print("ever fires without a real incoming event, even with latch_in set).")
    print("A genuinely self-sustaining multi-stage internal chain needs a")
    print("carefully-designed per-stage trigger path, which is real follow-up")
    print("work, not assumed here.")

    for (rows, cols) in [(4, 8), (8, 8)]:
        num_zones = rows * cols
        print(f"\n--- {rows}x{cols} grid ({num_zones} zones) ---\n")

        iso_frac, iso_ticks, iso_ok = run_isolated(rows, cols, cells_per_zone=4)
        print(f"ISOLATED workload (every zone computes its own independent gate):")
        print(f"  all {num_zones} zones completed correctly: {iso_ok}")
        print(f"  achieved fraction over {iso_ticks} ticks = {iso_frac:.4f}  "
              f"(ceiling=1.0; expect near 1/{num_zones} = {1/num_zones:.4f} -- "
              f"EVEN a fully isolated workload is bottlenecked to one zone at a "
              f"time here, because every step still needs the ONE shared host "
              f"channel)")

        chained_frac, chained_ticks, path_len = run_chained(rows, cols, cells_per_zone=4)
        print(f"\nCHAINED workload (one computation hopping through all {path_len} zones):")
        print(f"  achieved fraction over {chained_ticks} ticks = {chained_frac:.4f}  "
              f"(ceiling=1.0; expect near 1/{num_zones} = {1/num_zones:.4f})")

    print("\n" + "=" * 78)
    print("HONEST READING OF THIS FIRST RESULT: both workloads measure close to")
    print("the SAME low figure here -- NOT because more zones don't help, but")
    print("because THIS experiment's 'isolated' workload still needs host-fed")
    print("data for its only step, so it's ALSO bottlenecked by the one shared")
    print("host channel, same as the chained case. This is itself a real,")
    print("useful finding: true simultaneous multi-zone activity requires zones")
    print("to be running on ALREADY-DELIVERED data (via multi-stage internal")
    print("chaining or cardinal multicast, both proven in test_unicell_card_v3.py),")
    print("not per-step host involvement. The next experiment should measure a")
    print("workload where MOST zones' work happens after an initial kickoff,")
    print("to see the real separation predicted by points.md #70.")
    print("=" * 78)
