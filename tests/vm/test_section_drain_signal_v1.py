"""
test_section_drain_signal_v1.py -- points.md #858: a real, placed
SuperGrid proving `#843`'s own drain-completion-signal question has a
real, working answer -- not the big, host-level `#257` "empty/full"
system (a different, larger design for a different problem), but a
genuinely local, per-section signal built from cores already proven
tonight.

Real design history, kept honest rather than presenting only the
final answer:

  Attempt 1 (accumulator + comparator): inc/dec fed an accumulator
  (mirroring #850's own exit-counter mechanism, aimed differently --
  occupancy instead of pass-count), a comparator read "total >= 1" as
  "still occupied". Built and traced: the accumulator's own count
  correctly hit exactly zero the instant the value fully drained,
  proving the core idea sound. But the comparator (a real, single-shot
  core -- captures once, then refuses to capture again until drained)
  froze on its very first reading (0) and never updated again, since
  nothing was consuming its own output to re-arm it. A real, genuine
  finding, not a dead end: it named exactly what a "live boolean off a
  continuously-refreshing source" needs.

  Attempt 2 (a single latch, Alan's own real correction): `latch` is
  continuously-live (confirmed directly, CELL_CHEATSHEET.md's own
  entry) -- SET on the section's real head-arrival, CLEAR on the
  section's real tail-drain, no comparator, no accumulator, no re-arm
  problem at all, since latch never needs re-arming to react to a new
  arrival. Simpler AND correct where attempt 1 needed more machinery
  to reach the same live-signal property.

  A real, precise detail found while wiring this, not assumed: SET
  requires the arriving VALUE's own bit0=1 (confirmed directly in
  `_deliver_latch`); CLEAR fires on any arrival regardless of value.
  In a genuine, later implementation this argues for a real, dedicated
  marker value (not real chain data, whose LSB is arbitrary) feeding
  SET -- this test uses an odd preload value as a legitimate
  simplification for proving the mechanism, not the final wiring
  discipline a real fold/section design should use.

Real, honest scope, named directly rather than glossed over: this
latch-based signal is correct specifically for "at most one item in
the section at a time" -- which matches #843's own original framing
(fold an algorithm through a small footprint, one value per pass, not
a pipeline of overlapping values). If a section could ever hold
MULTIPLE simultaneously in-flight items, this signal is WRONG (a
second item's own entry could be masked by CLEAR firing for the FIRST
item's own exit while the second is still present) -- the accumulator-
based COUNT from attempt 1 remains the correct, general mechanism for
that case, with its own comparator-freezing problem still needing a
real solution if a live boolean is required from it specifically.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _build_grid(preload_value):
    """Real topology: a 2-cell 'section' (head, tail) with a real
    upstream (src) and downstream (sink), plus a latch tracking real
    occupancy via a wrapped-around relay from the tail back to the
    latch's own CLEAR input -- the same real 'wrap it around' routing
    Alan named directly."""
    src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="src", rel_row=0, rel_col=-1,
                     preload_value=preload_value)
    head = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": ["e", "s"]}, cell_id="head", rel_row=0, rel_col=0)
    tail = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": ["e", "s"]}, cell_id="tail", rel_row=0, rel_col=1)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=2)
    relay_r = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "n", "out": "w"}, cell_id="relay_r", rel_row=1, rel_col=1)
    lat = vtl.place(vtl.TILE_LATCH, {"set": "n", "clear": "e", "toggle": "w", "out": "s"},
                     cell_id="lat", rel_row=1, rel_col=0)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[src, head, tail, sink, relay_r, lat])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="section_drain_signal")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    return SuperGrid(records)


def test_latch_correctly_signals_occupied_while_a_value_is_in_transit():
    grid = _build_grid(preload_value=43)   # odd -- satisfies latch's own real SET requirement (bit0=1)
    for _ in range(3):
        grid.tick()
    assert grid.cells[(0, 1)].ram_data_valid is True, "sanity: the value should be at tail by now"
    assert grid.cells[(1, 0)].latch_state is True, "occupied: a real value is still mid-transit through the section"


def test_latch_correctly_clears_the_real_instant_the_section_genuinely_drains():
    """The real claim this entry exists to prove, per Alan's own
    'it should clear hopefully': confirmed directly, not hoped for."""
    grid = _build_grid(preload_value=43)
    for _ in range(4):
        grid.tick()
    assert grid.cells[(0, 2)].ram_data_valid is True, "sanity: the value should have reached sink by now"
    assert grid.cells[(1, 0)].latch_state is True, "still occupied -- the drain hasn't reached the latch's own CLEAR input yet (one more real hop through relay_r)"
    grid.tick()
    assert grid.cells[(1, 0)].latch_state is False, "drained -- exactly the tick the wrapped-around CLEAR signal arrives"


def test_latch_stays_drained_with_nothing_further_happening():
    """A real, necessary check: the signal doesn't spuriously flip back
    to occupied once genuinely drained and nothing more is moving."""
    grid = _build_grid(preload_value=43)
    for _ in range(10):
        grid.tick()
    assert grid.cells[(1, 0)].latch_state is False
