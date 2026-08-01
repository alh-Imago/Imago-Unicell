"""
card_ram_loop.py — the full operational loop Alan described: RAM staging
-> command zones (shells) reading their own operands -> chain zones
(interiors) computing -> results written to per-command-zone output RAM
-> completion signal.

Directly tests the thing the conversation actually turned on: whether
multiple command zones reading RAM simultaneously collide depends
entirely on real port count, not on the architecture in the abstract.
Modeled explicitly rather than assumed either way -- a SharedRAM with a
configurable number of ports, where using a port more than once in the
same tick is a genuine, measured contention event, not hand-waved.

Two scenarios, both run and compared:
  1. DUAL-PORT RAM, one port per command zone -- matches real Arria 10
     BRAM's genuine dual-port capability. Expect zero contention.
  2. SINGLE-PORT RAM, multiple command zones sharing it -- expect real,
     measured contention, reintroducing the #69/#70 bottleneck at the
     RAM level instead of the host-channel level.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from hybrid_card_v1 import HybridCard


class SharedRAM:
    """A RAM with a configurable number of real ports. Using the same
    port twice in one tick is a genuine contention event -- the second
    user must wait, exactly matching how a real single/dual-port BRAM
    behaves, not an idealized always-available resource."""

    def __init__(self, num_ports: int, size: int = 256):
        self.num_ports = num_ports
        self.data = [0] * size
        self._used_this_tick = set()
        self.contention_events = 0  # measured, not assumed

    def tick_reset(self):
        self._used_this_tick = set()

    def try_read(self, port: int, addr: int):
        """Returns (success, value). success=False means this port is
        already in use this tick -- caller must retry next tick."""
        if port in self._used_this_tick:
            self.contention_events += 1
            return (False, None)
        self._used_this_tick.add(port)
        return (True, self.data[addr])

    def try_write(self, port: int, addr: int, value: int):
        if port in self._used_this_tick:
            self.contention_events += 1
            return False
        self._used_this_tick.add(port)
        self.data[addr] = value
        return True


class CommandZone:
    """One command zone: reads its own operand pair from a specific RAM
    port/address, drives its own HybridCard (shell + chain interior),
    writes the result back to its own output RAM address, then signals
    completion. Explicitly stateful/steppable so multiple zones can be
    genuinely interleaved tick-by-tick, not run to completion in turn."""

    def __init__(self, zone_id: int, ram: SharedRAM, port: int,
                 in_addr: int, out_addr: int, num_bits: int = 4):
        self.zone_id = zone_id
        self.ram = ram
        self.port = port
        self.in_addr = in_addr
        self.out_addr = out_addr
        self.card = HybridCard(num_bits=num_bits)
        self.state = "READ_RAM"
        self.completed = False
        self.stall_ticks = 0  # measured contention wait, per zone

    def step(self):
        if self.state == "READ_RAM":
            ok, packed = self.ram.try_read(self.port, self.in_addr)
            if not ok:
                self.stall_ticks += 1
                return
            a, b = packed & 0xF, (packed >> 4) & 0xF
            self.card.feed_adder(a, b)
            self.state = "COMPUTE"
        elif self.state == "COMPUTE":
            if self.card.interior._pending:
                self.card.interior.tick()
            else:
                self.state = "WRITE_RAM"
        elif self.state == "WRITE_RAM":
            value = 0
            for i in range(self.card.num_bits):
                value |= (self.card.adder_cells[i]["sum"].out_buffer & 1) << i
            ok = self.ram.try_write(self.port, self.out_addr, value)
            if not ok:
                self.stall_ticks += 1
                return
            for i in range(self.card.num_bits):
                self.card.interior.confirm_read(0, 3 * i)
            self.card.interior.confirm_read(1, 3 * (self.card.num_bits - 1) + 2)
            self.state = "DONE"
            self.completed = True


def run_scenario(num_ports: int, zone_ports: list, pairs: list, num_bits: int = 4) -> dict:
    """zone_ports[i] = which RAM port command zone i uses. pairs[i] =
    (a, b) for zone i, pre-loaded into RAM at that zone's input address."""
    ram = SharedRAM(num_ports=num_ports)
    zones = []
    for i, (port, (a, b)) in enumerate(zip(zone_ports, pairs)):
        in_addr, out_addr = 10 + i, 50 + i
        ram.data[in_addr] = a | (b << 4)
        zones.append(CommandZone(i, ram, port, in_addr, out_addr, num_bits))

    max_ticks = 500
    for _ in range(max_ticks):
        ram.tick_reset()
        if all(z.completed for z in zones):
            break
        for z in zones:
            if not z.completed:
                z.step()

    results = []
    for i, (z, (a, b)) in enumerate(zip(zones, pairs)):
        expected = (a + b) & ((1 << num_bits) - 1)
        got = ram.data[z.out_addr]
        results.append((got, expected, got == expected))

    return dict(
        all_completed=all(z.completed for z in zones),
        results=results,
        total_contention=ram.contention_events,
        stall_ticks=[z.stall_ticks for z in zones],
    )


if __name__ == "__main__":
    pairs = [(5, 3), (9, 1)]

    print("=" * 78)
    print("SCENARIO 1: DUAL-PORT RAM, one port per command zone (matches real BRAM)")
    print("=" * 78)
    dual = run_scenario(num_ports=2, zone_ports=[0, 1], pairs=pairs)
    for i, (got, expected, ok) in enumerate(dual["results"]):
        print(f"  zone {i}: got={got} expected={expected} {'PASS' if ok else 'FAIL'}")
    print(f"  contention events: {dual['total_contention']}")
    print(f"  per-zone stall ticks: {dual['stall_ticks']}")

    print()
    print("=" * 78)
    print("SCENARIO 2: SINGLE-PORT RAM, both command zones sharing it")
    print("=" * 78)
    single = run_scenario(num_ports=1, zone_ports=[0, 0], pairs=pairs)
    for i, (got, expected, ok) in enumerate(single["results"]):
        print(f"  zone {i}: got={got} expected={expected} {'PASS' if ok else 'FAIL'}")
    print(f"  contention events: {single['total_contention']}")
    print(f"  per-zone stall ticks: {single['stall_ticks']}")

    print()
    print("=" * 78)
    dual_ok = dual["all_completed"] and all(ok for _, _, ok in dual["results"])
    single_ok = single["all_completed"] and all(ok for _, _, ok in single["results"])
    print(f"Both scenarios computed correctly: {dual_ok and single_ok}")
    print(f"Dual-port had ZERO contention: {dual['total_contention'] == 0}")
    print(f"Single-port had REAL, measured contention: {single['total_contention'] > 0}")
    print("=" * 78)

    if not (dual_ok and single_ok and dual["total_contention"] == 0 and single["total_contention"] > 0):
        sys.exit(1)
