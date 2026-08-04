"""
adder_repeatable_unit.py — rebuilding the 32-bit Kogge-Stone adder's
stage 1 (the g[i]/p[i] generate/propagate computation) from a small,
REUSED unit fed serially by the loader, replacing the flawed 64-cell
dedicated version (points.md #72).

The compiler's existing make_int32_add() output assumes multiple cells
can share one trigger and fire simultaneously to distinct output
addresses -- confirmed invalid (points.md #72): different-address
simultaneous fires collide on the real wired-OR bus (#32/#70). So even
the "dedicated" 64-cell version could never actually fire all 64 cells
together; it would need to service them one at a time regardless. Given
that, this rebuild uses just 2 cells -- one AND, one XOR -- fed all 32
bit positions in sequence via the SAME loader-injection pattern
(unicell_card_v3.py's schedule_host_injection), at the SAME cycle cost
the dedicated version was always actually going to pay, using a tiny
fraction of the cells.

CRITICAL SEQUENCING DETAIL, worth being explicit about since it's exactly
the mistake points.md #72 identifies: the AND cell and the XOR cell must
NOT be triggered in the same tick, even though they compute from the
same (a[i], b[i]) pair -- they fire to DIFFERENT output addresses (g[i]
vs p[i]), which is precisely the collision scenario that's invalid. Each
gets its own full prime+trigger pair, strictly sequential.

Verified against Python's own bitwise AND/XOR for a real 32-bit value
pair -- not just "it runs for some number of cycles", but "it computes
the actually-correct answer, checked bit by bit".
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nano"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "archeology", "full-cell", "python"))

from unicell_card_v3 import UniCellCardV3
from unicell_gate_core import TOPO_AND, TOPO_XOR


def build_and_run(a: int, b: int):
    """One zone, two reused cells (AND, XOR), fed all 32 bit positions
    of a and b in sequence. Returns (g_bits, p_bits, total_ticks)."""
    card = UniCellCardV3(rows=1, cols=1, cells_per_zone=2)
    zone = card.zones[(0, 0)]
    and_cell, xor_cell = zone.array.cells[0], zone.array.cells[1]

    AND_ADDR, XOR_ADDR = 0x300, 0x301
    G_OUT, P_OUT = 0x310, 0x311  # results read back from these, not chained further here

    and_cell.boot_commit(logical_addr=AND_ADDR, auth_mask_bits=0)
    and_cell.reconfigure(topology=TOPO_AND, start_flag=True)
    and_cell.set_output_set(True)
    and_cell.set_output_address(G_OUT)

    xor_cell.boot_commit(logical_addr=XOR_ADDR, auth_mask_bits=0)
    xor_cell.reconfigure(topology=TOPO_XOR, start_flag=True)
    xor_cell.set_output_set(True)
    xor_cell.set_output_address(P_OUT)

    g_bits = [0] * 32
    p_bits = [0] * 32
    tick = 0

    for i in range(32):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        # AND cell: prime, then trigger -- fully sequential, own two ticks.
        card.schedule_host_injection(tick=tick,     row=0, col=0, addr=AND_ADDR, data=ai)
        card.schedule_host_injection(tick=tick + 1, row=0, col=0, addr=AND_ADDR, data=bi)
        card.run(2)
        g_bits[i] = and_cell.data_reg & 1
        tick += 2

        # XOR cell: separate prime+trigger pair -- never overlaps the AND
        # cell's own events, exactly the sequencing #72 identifies as
        # necessary (different output addresses, never the same tick).
        card.schedule_host_injection(tick=tick,     row=0, col=0, addr=XOR_ADDR, data=ai)
        card.schedule_host_injection(tick=tick + 1, row=0, col=0, addr=XOR_ADDR, data=bi)
        card.run(2)
        p_bits[i] = xor_cell.data_reg & 1
        tick += 2

    return g_bits, p_bits, tick


if __name__ == "__main__":
    A = 0x12345678
    B = 0x9ABCDEF0

    print("=" * 78)
    print("Stage 1 rebuilt from a 2-cell reused unit, loader-fed --")
    print("replacing the flawed 64-cell dedicated version (points.md #72)")
    print("=" * 78)
    print(f"\nA = {A:#010x}")
    print(f"B = {B:#010x}")

    g_bits, p_bits, total_ticks = build_and_run(A, B)

    g_computed = sum(bit << i for i, bit in enumerate(g_bits))
    p_computed = sum(bit << i for i, bit in enumerate(p_bits))
    g_expected = A & B
    p_expected = A ^ B

    print(f"\ng[] (AND) computed = {g_computed:#010x}")
    print(f"g[] (AND) expected = {g_expected:#010x}  (Python A & B)")
    print(f"MATCH: {g_computed == g_expected}")

    print(f"\np[] (XOR) computed = {p_computed:#010x}")
    print(f"p[] (XOR) expected = {p_expected:#010x}  (Python A ^ B)")
    print(f"MATCH: {p_computed == p_expected}")

    print(f"\nTotal ticks: {total_ticks}  (32 positions x 2 gates x 2 events/gate = 128, as expected)")
    print(f"Cells used: 2  (vs 64 in the existing compiled tile's stage 1)")
    print(f"Cycle cost: IDENTICAL to what the 64-cell version was always actually")
    print(f"going to pay, once #72's correction is applied -- it could never fire")
    print(f"all 64 simultaneously either. The only thing the 64-cell version spent")
    print(f"that this doesn't: 62 cells' worth of silicon, for zero cycle benefit.")
    print("=" * 78)

    if g_computed != g_expected or p_computed != p_expected:
        sys.exit(1)
