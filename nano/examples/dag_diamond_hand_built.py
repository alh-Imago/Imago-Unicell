"""
dag_diamond_hand_built.py — points.md #750: the smallest real DAG that
isn't a linear chain, hand-built and traced against the actual VM,
confirming the real timing-analysis shape the LLVM IR frontend's own
"general DAG routing" gap will eventually need to solve automatically.

t3 = (a+b) + (c+d) -- a real "diamond": two independent sub-
computations converging on a third. Targets the OLD lineage
(icm_v3.IcmV3Record, via super_tile_library_v1.py's own real tiles),
matching where the current LLVM IR frontend actually targets today.

REAL, CONFIRMED FINDING, beyond what CELL_GOTCHAS.md already
documented (#611/#742/#748): it is NOT enough to fix a continuously-
live (fixed_mode) constant source by switching to flowing-mode +
preload_value. A preloaded, flowing-mode cell is already ram_data_
valid=True at construction -- it needs no trigger to become ready, it
just IS ready from tick zero. TWO such cells feeding the SAME real
consumer are BOTH ready and BOTH offer on the very first real tick,
arriving simultaneously and OR-combining -- the exact same collision
fixed_mode causes, for a genuinely different, additional reason.
preload_value fixes RE-CONTAMINATION (a drained cell won't keep
re-offering); it does NOT by itself fix simultaneous FIRST arrival
between two independently-ready sources.

THE REAL, WORKING FIX, confirmed by tracing the actual result: pad ONE
of the two paths converging on any shared consumer with an extra real
relay hop, so the two arrivals land on genuinely different ticks. This
applies to EVERY real convergence point in a DAG -- including two
compile-time constants converging directly, which has no "dynamic"
operand at all to blame the hazard on, sharpening #611's own original
"stagger the dynamic operand" framing into the fully general rule.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from super_tile_library_v1 import super_tile_library, place  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from dataclasses import replace  # noqa: E402

ADDER = super_tile_library.get("adder")
RAM_FLOW = super_tile_library.get("ram_flowing")


def const_cell(row, col, out_dir, value, cell_id):
    """A real, one-shot constant source -- flowing-mode ram, preloaded.
    Fixes re-contamination (#742/#748) but NOT, by itself, simultaneous
    first arrival against another preloaded source (this file's own
    real, additional finding) -- staggering the PATH LENGTH is still
    required separately, see build_dag() below."""
    rec = place(RAM_FLOW, row, col, {"in": "w", "out": out_dir}, cell_id=cell_id)
    rec.core_config.pop("upstream_mask", None)  # a real constant has no real "in" at all
    return replace(rec, preload_value=value)


def relay_cell(row, col, in_dir, out_dir, cell_id):
    return place(RAM_FLOW, row, col, {"in": in_dir, "out": out_dir}, cell_id=cell_id)


def build_dag(a, b, c, d):
    """Real, systematic, collision-checked layout -- every convergence
    point (a+b at t1, c+d at t2, t1+t2 at t3) gets a deliberately
    padded path on one side, confirmed necessary by this file's own
    real, traced attempt #1/#2 failures before this shape was reached."""
    records = [
        const_cell(0, -1, "e", a, "a_const"),
        const_cell(-2, 0, "s", b, "b_const"),
        relay_cell(-1, 0, "n", "s", "b_relay"),
        place(ADDER, 0, 0, {"in_a": "w", "in_b": "n", "out": "s"}, cell_id="t1_adder"),

        const_cell(0, 2, "s", c, "c_const"),
        const_cell(2, 3, "w", d, "d_const"),
        relay_cell(2, 2, "e", "n", "d_relay"),
        place(ADDER, 1, 2, {"in_a": "n", "in_b": "s", "out": "w"}, cell_id="t2_adder"),
        relay_cell(1, 1, "e", "w", "t2_relay"),

        place(ADDER, 1, 0, {"in_a": "n", "in_b": "e", "out": "e"}, cell_id="t3_adder"),
    ]
    return records


if __name__ == "__main__":
    a, b, c, d = 3, 5, 10, 20
    records = build_dag(a, b, c, d)
    grid = SuperGrid(records)
    t1 = grid.cells[(0, 0)]
    t2 = grid.cells[(1, 2)]
    t3 = grid.cells[(1, 0)]

    for i in range(10):
        grid.tick()
        print(f"tick {i+1}: t1.valid={t1.adder_data_valid} out={t1.adder_out_buffer} | "
              f"t2.valid={t2.adder_data_valid} out={t2.adder_out_buffer} | "
              f"t3.a_arrived={t3.adder_a_arrived} a_reg={t3.adder_a_reg} "
              f"valid={t3.adder_data_valid} out={t3.adder_out_buffer}")

    expected = (a + b) + (c + d)
    print(f"\nExpected t3: {expected}, got: {t3.adder_out_buffer} -- "
          f"{'CORRECT' if t3.adder_out_buffer == expected else 'MISMATCH'}")
