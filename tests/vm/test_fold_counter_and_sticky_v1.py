"""
test_fold_counter_and_sticky_v1.py -- points.md #850: a real, placed
SuperGrid proving the two mechanisms an iterative/folded design (the
real, harder shape divide will eventually need, #843's own "fold an
algorithm through a small footprint" idea) actually needs -- an exit
counter and a persistent sticky-hold -- both map onto EXISTING
accumulator capability, no new core, no new mechanism.

Real topology, two independent accumulators, proven separately:

  PASS COUNTER: accumulator in pulse_mode=1, threshold=3. Confirmed
  directly against accumulator_cell_v4.v before relying on it: in
  pulse_mode, the accumulator stays SILENT (offers nothing) while
  counting, and offers EXACTLY ONCE, the instant its running total
  hits threshold, resetting itself immediately after. That single real
  offer is the "fold is complete" signal a real iterative design would
  use to stop looping and route its result onward -- proven here by
  checking it does NOT fire after 1 or 2 "pass complete" pulses, and
  DOES fire after the 3rd.

  STICKY HOLD: a second, ordinary (non-pulse) accumulator, incrementing
  whenever a given pass's own "was the discarded bit nonzero" signal
  fires. Only 1 of 3 simulated passes contributes a real increment --
  proven that the running total still correctly ends up nonzero
  (sticky was genuinely SET), matching real sticky semantics ("was
  ANYTHING ever nonzero", not an exact count) rather than a literal
  arithmetic sum being the point.

Real, honest scope: this proves the two underlying MECHANISMS work
using directly-injected "pass complete" / "sticky trigger" arrivals,
standing in for whatever real signal (#843's own still-open
drain-completion / broadcast-trigger question) would actually drive
them in a real fold. It does not build the fold/reconfigure loop
itself -- that remains blocked on #843's own open items.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _rec(cell_id, row, col, core, core_config=None, addon_config=None):
    return v3.IcmV3Record(cell_id=cell_id, row=row, col=col, core=core,
                           core_config=core_config or {}, addon_config=addon_config or {})


def _pulse(grid, cell_pos, direction_val, ticks=3):
    """Sends one real arrival by injecting directly into a cell's own
    pending queue at the given position, tagged as arriving from the
    given direction -- mirrors SuperGrid.inject()'s own real, already-
    proven convention (#692 and others), then ticks enough times for
    it to be consumed."""
    grid._pending.setdefault(cell_pos, []).append((None, direction_val, 1))
    for _ in range(ticks):
        grid.tick()


def test_pass_counter_stays_silent_until_the_real_threshold_is_hit():
    counter = _rec("counter", 0, 0, "accumulator",
                    {"downstream_mask": ["e"], "inc_dir": ["n"], "dec_dir": ["s"],
                     "step_amount": 1, "pulse_mode": 1, "threshold": 3})
    sink = _rec("sink", 0, 1, "ram", {"upstream_mask": ["w"]})
    grid = SuperGrid([counter, sink])

    from unicell_automaton_v1 import N as DIR_N  # noqa: E402

    # Pass 1
    _pulse(grid, (0, 0), DIR_N)
    assert grid.cells[(0, 1)].ram_data_valid is False, "must NOT fire after only 1 of 3 passes"

    # Pass 2
    _pulse(grid, (0, 0), DIR_N)
    assert grid.cells[(0, 1)].ram_data_valid is False, "must NOT fire after only 2 of 3 passes"

    # Pass 3 -- the real threshold
    _pulse(grid, (0, 0), DIR_N)
    assert grid.cells[(0, 1)].ram_data_valid is True, "MUST fire exactly on reaching the real threshold -- the fold-complete signal"


def test_sticky_hold_survives_across_passes_that_contribute_nothing():
    sticky = _rec("sticky", 0, 0, "accumulator",
                   {"downstream_mask": ["e"], "inc_dir": ["n"], "dec_dir": ["s"],
                    "step_amount": 1, "pulse_mode": 0, "threshold": 0})
    grid = SuperGrid([sticky])

    from unicell_automaton_v1 import N as DIR_N  # noqa: E402

    # Pass 1: no sticky contribution (discarded bit was zero this pass)
    grid.tick()
    grid.tick()
    assert grid.cells[(0, 0)].acc_total == 0, "no contribution yet -- sticky correctly still clear"

    # Pass 2: THIS pass's discarded bit was nonzero -- one real increment
    _pulse(grid, (0, 0), DIR_N)
    assert grid.cells[(0, 0)].acc_total > 0, "sticky must now be SET"

    # Pass 3: no further contribution -- sticky must STAY set, not clear itself
    grid.tick()
    grid.tick()
    assert grid.cells[(0, 0)].acc_total > 0, "sticky must remain set through a later pass that contributes nothing -- it's a HOLD, not a per-pass flag"
