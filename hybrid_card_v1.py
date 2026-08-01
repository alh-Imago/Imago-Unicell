"""
hybrid_card_v1.py — realizing the #76/#79 hybrid architecture concretely:
one ADDRESSED zone (UniCellArrayV3, matching the real card's actual
25-cell zone size) acting as the shell, bridging data into a STRIPPED,
next-hop-only interior (CAGrid, running the #75 ripple adder) and reading
results back out through the addressed side.

This is the direct test of #79's stated next step: does the synthesis
still hold together once it's built as one working system, not just two
separately-proven halves.

THE BRIDGE, stated precisely: the shell (addressed) and interior
(stripped) have completely different APIs -- deliver(bus_addr, bus_data)
vs. inject(row, col, value) -- there's no hardware-level unification
attempted here, this is Python code standing in for what a real bilingual
boundary cell (#76's "next concrete step") would eventually be in
silicon: it reads a FireResult off the shell and translates it into an
injection on the interior side, and vice versa for the return path. Each
bit of the adder gets its own dedicated shell cell acting as a "loader
tap" feeding that bit's entry point directly -- this session doesn't yet
attempt collapsing that down to a single serial entry point with
internal fan-out (a bigger, separate piece of work), but every connection
used here is a genuine, addressed-to-stripped bridge, not a shortcut.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from unicell_array_v3 import UniCellArrayV3
from unicell_automaton_v1 import CAGrid
from unicell_v3 import TOPO_PASS_B
from experiments.adder_automaton_ripple import build_adder


class HybridCard:
    def __init__(self, num_bits: int):
        self.num_bits = num_bits
        # Shell: one real addressed zone, 25 cells -- matches the actual
        # target card's zone size, not an arbitrary number.
        self.shell = UniCellArrayV3(num_cells=25, cell_base=0)
        # Interior: the stripped region running the #75 ripple adder.
        self.interior = CAGrid(rows=3, cols=3 * num_bits)
        self.adder_cells = build_adder(self.interior, num_bits)

        # One shell cell per bit, per operand (a, b) -- 2*num_bits shell
        # cells act as addressed "loader taps", each bridging directly to
        # one interior entry point (p_cell[i] or g_cell[i]).
        self.a_taps = []
        self.b_taps = []
        for i in range(num_bits):
            addr_a = 0x100 + 2 * i
            addr_b = 0x100 + 2 * i + 1
            cell_a = self.shell.cells[2 * i]
            cell_b = self.shell.cells[2 * i + 1]
            cell_a.boot_commit(logical_addr=addr_a, auth_mask_bits=0)
            cell_a.reconfigure(topology=TOPO_PASS_B, start_flag=True)
            cell_a.set_output_set(True)
            cell_b.boot_commit(logical_addr=addr_b, auth_mask_bits=0)
            cell_b.reconfigure(topology=TOPO_PASS_B, start_flag=True)
            cell_b.set_output_set(True)
            self.a_taps.append((addr_a, cell_a))
            self.b_taps.append((addr_b, cell_b))

    def load_operand_bit(self, tap_addr: int, bit_value: int) -> int:
        """Fire a shell tap cell with a bit value (needs 2 addressed
        events -- prime then trigger, PASS_B just relays the trigger's
        own value through as this tap's output)."""
        self.shell.deliver(tap_addr, 0)
        result = self.shell.deliver(tap_addr, bit_value)
        return result.data if result.valid else None

    def feed_adder(self, a: int, b: int):
        """Bridge: read each shell tap's fired output and inject it
        directly at the corresponding interior entry point -- the
        addressed-to-stripped translation, done explicitly, not hidden."""
        for i in range(self.num_bits):
            base = 3 * i
            ai_addr, _ = self.a_taps[i]
            bi_addr, _ = self.b_taps[i]
            ai = self.load_operand_bit(ai_addr, (a >> i) & 1)
            self.interior.inject(1, base, ai & 1)      # p_cell[i]
            self.interior.inject(2, base + 2, ai & 1)  # g_cell[i]
            self.interior.tick()
            bi = self.load_operand_bit(bi_addr, (b >> i) & 1)
            self.interior.inject(1, base, bi & 1)
            self.interior.inject(2, base + 2, bi & 1)
            self.interior.tick()
        self.interior.inject(0, 0, 0)
        self.interior.inject(1, 1, 0)
        self.interior.tick()

    def run_and_read_back(self, max_ticks: int = 200) -> int:
        """Drain the interior to quiescence, then bridge each sum bit's
        confirmed output back out (the addressed side reading the
        stripped side's result -- the return half of the boundary)."""
        self.interior.run_to_quiescence(max_ticks=max_ticks)
        value = 0
        for i in range(self.num_bits):
            bit = self.adder_cells[i]["sum"].out_buffer & 1
            value |= bit << i
            self.interior.confirm_read(0, 3 * i)
        # also confirm the final overflow carry, exactly as #78 established is necessary
        self.interior.confirm_read(1, 3 * (self.num_bits - 1) + 2)
        return value


if __name__ == "__main__":
    print("=" * 78)
    print("HYBRID CARD: addressed shell (real 25-cell zone) bridging into")
    print("a stripped, next-hop interior running the ripple adder")
    print("=" * 78)

    test_cases = [(0, 0), (5, 3), (15, 1), (9, 1), (170 & 0xF, 85 & 0xF)]
    all_pass = True
    for a, b in test_cases:
        card = HybridCard(num_bits=4)
        card.feed_adder(a, b)
        result = card.run_and_read_back()
        expected = (a + b) & 0xF
        ok = result == expected
        all_pass = all_pass and ok
        print(f"  {a:#06b} + {b:#06b} = {result:#06b}  expected={expected:#06b}  "
              f"{'PASS' if ok else 'FAIL'}")

    print()
    print("ALL PASS -- the hybrid synthesis holds together end to end"
          if all_pass else "SOME FAILED")
    if not all_pass:
        sys.exit(1)
