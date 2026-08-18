"""
chaos_topology_v1.py — genuine random-topology exploration, per Alan's
own real proposal (points.md, day 3): random core assignment, random
valid wiring, feed known data in, watch what actually happens using the
real VM -- not a generated narrative about what might happen.

Every core's own required fields (per icm_v3.py's own real
CORE_FIELD_TABLES) are always populated with SOME valid random value --
this guarantees every cell LOADS successfully into a real SuperGrid, but
says nothing about whether any given cell's neighbors exist or whether
its wiring "makes sense" -- that's the whole point of chaos testing:
some cells will offer into empty space, some will never fire, some will
form real chains by pure chance. All of that is real, observed
behavior, not designed.
"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nano"))

from icm_v3 import IcmV3Record, SEL_NANO, SEL_RAM, SEL_ADDER, SEL_ACC, SEL_CMP, SEL_LATCH
from unicell_super_automaton_v1 import SuperGrid

DIRS = ["n", "s", "e", "w"]
CORE_NAMES = ["nano", "ram", "adder", "accumulator", "comparator", "latch"]


def _rand_dirs(rng, min_n=0, max_n=4):
    """A random, possibly-empty subset of cardinal directions."""
    n = rng.randint(min_n, max_n)
    return rng.sample(DIRS, n)


def random_core_config(core, rng):
    if core == "nano":
        return {
            "topology": rng.randint(0, 1023),
            "ready": rng.randint(0, 1),
            "routing_mask": rng.randint(0, 63),
            "cardinal_edge": rng.randint(0, 63),
        }
    if core == "ram":
        return {
            "downstream_mask": _rand_dirs(rng),
            "upstream_mask": _rand_dirs(rng),
            "fixed_mode": rng.randint(0, 1),
            "load_data_valid": rng.randint(0, 1),
            "init_data": rng.randint(0, 2**32 - 1),
        }
    if core == "adder":
        return {
            "downstream_mask": _rand_dirs(rng),
            "upstream_mask": _rand_dirs(rng),
        }
    if core == "accumulator":
        return {
            "inc_dir": _rand_dirs(rng),
            "dec_dir": _rand_dirs(rng),
            "downstream_mask": _rand_dirs(rng),
        }
    if core == "comparator":
        return {
            "downstream_mask": _rand_dirs(rng),
            "upstream_mask": _rand_dirs(rng),
            "threshold": rng.randint(0, 2**32 - 1),
        }
    if core == "latch":
        return {
            "set_dir": _rand_dirs(rng),
            "clear_dir": _rand_dirs(rng),
            "downstream_mask": _rand_dirs(rng),
        }
    raise ValueError(core)


def random_topology(rows, cols, seed):
    """A real, valid, fully-random grid -- every cell loads, wiring is genuinely random."""
    rng = random.Random(seed)
    records = []
    for r in range(rows):
        for c in range(cols):
            core = rng.choice(CORE_NAMES)
            cfg = random_core_config(core, rng)
            records.append(IcmV3Record(
                cell_id=f"chaos_{r}_{c}", row=r, col=c, core=core,
                core_config=cfg, addon_config={},
            ))
    return records


def summarize(grid, rows, cols):
    """Real, observed state -- counts of what's actually happening, not narrative."""
    core_counts = {}
    for (r, c), cell in grid.cells.items():
        core_counts[cell.core] = core_counts.get(cell.core, 0) + 1
    pending_targets = {pos for pos in grid._pending.keys()}
    return {
        "total_cells": rows * cols,
        "core_counts": core_counts,
        "pending_events": len(grid._pending),
        "distinct_cells_with_pending_events": len(pending_targets),
    }


if __name__ == "__main__":
    ROWS, COLS, SEED = 10, 10, 42
    records = random_topology(ROWS, COLS, SEED)
    grid = SuperGrid(records)

    print(f"=== chaos topology: {ROWS}x{COLS}, seed={SEED} ===")
    print(summarize(grid, ROWS, COLS))

    # feed known data at a few known points, then observe real behavior
    injection_points = [(0, 0), (0, COLS // 2), (ROWS // 2, 0), (ROWS - 1, COLS - 1)]
    for (r, c) in injection_points:
        grid.inject(r, c, 12345)
    print(f"\ninjected known value 12345 into {len(injection_points)} cells")

    try:
        ticks = grid.run_to_quiescence(max_ticks=200)
        print(f"\nreached quiescence after {ticks} ticks")
    except TimeoutError:
        print(f"\ndid NOT reach quiescence within 200 ticks -- genuinely live/oscillating topology")

    print(summarize(grid, ROWS, COLS))
