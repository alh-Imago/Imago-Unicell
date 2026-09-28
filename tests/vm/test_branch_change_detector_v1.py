"""
test_branch_change_detector_v1.py -- points.md #875: the `branch` core in
ROLLING mode is a genuine CHANGE DETECTOR, and it is the answer to the
"continuously re-offered level" problem that #858/#863 kept hitting.

Found by running an experiment after Alan asked whether the comparator was the
cell that "sees the matching value ... and sends either the value or a 1/0".
By its fields that description is the `branch` core (3-outcome compare against
a held reference; per outcome: emit or stay SILENT, pass the input value or a
FIXED value, and a route), not `compare` (`>=` against a threshold, and it
answers 0 or 1 for EVERY arrival). In rolling mode each arrival is compared
with the PREVIOUS arrival, so "equal" means "nothing changed": configure it
silent and only changes come out -- one value per change, however many times a
continuous source (latch, accumulator) re-offers the same level.

This corrects a claim of mine: at #863 I told Alan no edge-detector primitive
existed ready-made in the project. It did; I had not looked at rolling mode.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _collectors():
    return [_rec("k1", 0, 3, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
            _rec("k2", 0, 4, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
            _rec("k3", 0, 5, "ram", {"upstream_mask": ["w"], "downstream_mask": []})]


def _latch_source(with_clear=True):
    """A latch (a continuously re-offered level) SET early by `setter` and,
    if asked, CLEARed later through a short relay chain from the north."""
    cells = [_rec("setter", 0, 0, "ram", {"init_data": 1, "load_data_valid": 1, "downstream_mask": ["e"]}),
             _rec("latch", 0, 1, "latch", {"set_dir": ["w"], "clear_dir": ["n"], "downstream_mask": ["e"]})]
    if with_clear:
        cells.append(_rec("clr0", -4, 1, "ram", {"init_data": 1, "load_data_valid": 1, "downstream_mask": ["s"]}))
        cells += [_rec(f"clr{r}", r, 1, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]})
                  for r in (-3, -2, -1)]
    return cells


def _rolling_branch(**over):
    cfg = {"upstream_dir": ["w"], "rolling_mode": 1,
           "emit_low": 1, "value_source_low": 1, "fixed_value_low": 2, "route_low": ["e"],
           "emit_equal": 0,
           "emit_high": 1, "value_source_high": 1, "fixed_value_high": 1, "route_high": ["e"]}
    cfg.update(over)
    return _rec("branch", 0, 2, "branch", cfg)


def _received(grid):
    """Emissions that reached the collector chain, in ARRIVAL order (deepest cell first)."""
    return [grid.cells[(0, c)].ram_data_reg for c in (5, 4, 3) if grid.cells[(0, c)].ram_data_valid]


def test_rolling_branch_emits_exactly_once_per_change_of_a_reoffered_latch():
    grid = VixCarrierGrid(_latch_source() + [_rolling_branch()] + _collectors())
    latch = grid.cells[(0, 1)]
    ticks_high = 0
    for _ in range(30):
        grid.tick()
        ticks_high += bool(latch.latch_state)
    assert ticks_high >= 2, "the latch stayed high across several ticks, re-offering its level each time"
    assert _received(grid) == [1, 2], \
        "exactly two emissions -- a fixed 1 on the RISE, a fixed 2 on the FALL -- and nothing while the level held"


def test_the_first_arrival_is_only_a_baseline_and_is_never_emitted():
    grid = VixCarrierGrid(_latch_source(with_clear=False)[1:] + [_rolling_branch()] + _collectors())
    # no setter: the latch just sits at 0 and re-offers it forever
    for _ in range(25):
        grid.tick()
    br = grid.cells[(0, 2)]
    assert br.br_ref_valid is True and br.br_ref_value == 0, "the first arrival became the baseline"
    assert _received(grid) == [], "an unchanging level produces no emissions at all"


def test_contrast_non_rolling_mode_is_not_a_change_detector():
    """Same latch, but the branch compares against a FIXED baseline (0) instead
    of the previous arrival: every re-offer of the held 1 is 'high' again, so
    ONE change produces a stream of emissions and fills the collector."""
    grid = VixCarrierGrid(_latch_source(with_clear=False) + [_rolling_branch(rolling_mode=0)] + _collectors())
    for _ in range(30):
        grid.tick()
    assert _received(grid) == [1, 1, 1], "one SET, yet the collector filled: a level source re-triggers every time"


def test_contrast_the_compare_core_always_answers_and_cannot_stay_silent():
    """`comparator` (the `compare` core) is `>=` against a threshold and offers a 0 or 1 for EVERY
    arrival -- it has no 'emit only on a match' option, so it cannot be a
    one-shot trigger on its own. Nothing has happened here (the latch just
    sits at 0), yet it answers repeatedly."""
    cmp_cell = _rec("cmp", 0, 2, "comparator", {"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": 1})
    grid = VixCarrierGrid(_latch_source(with_clear=False)[1:] + [cmp_cell] + _collectors())
    for _ in range(30):
        grid.tick()
    got = _received(grid)
    assert got == [0, 0, 0], "it answered 0 again and again although nothing ever changed"


def test_a_change_to_a_second_value_is_also_detected_on_a_counter_style_stream():
    """The detector is about VALUE changes, not just a latch's 0/1: a stream
    arriving as 1,1,1,2,2,3 through a rolling branch that passes the INPUT
    value (not a fixed one) on a rise emits 2 then 3 only. The chain cell
    nearest the branch speaks first, so it is loaded in REVERSE."""
    arrival_order = [1, 1, 1, 2, 2, 3]
    n = len(arrival_order)
    cells = []
    for i, v in enumerate(reversed(arrival_order)):          # i = 0 is the farthest, speaks last
        cells.append(_rec(f"s{i}", 0, -n + i, "ram", {
            "init_data": v, "load_data_valid": 1,
            "upstream_mask": [] if i == 0 else ["w"], "downstream_mask": ["e"]}))
    branch = _rec("branch", 0, 0, "branch", {"upstream_dir": ["w"], "rolling_mode": 1,
                                             "emit_high": 1, "value_source_high": 0, "route_high": ["e"],
                                             "emit_low": 0, "emit_equal": 0})
    sink = [_rec(f"k{j}", 0, 1 + j, "ram", {"upstream_mask": ["w"],
                                             "downstream_mask": ["e"] if j < 3 else []}) for j in range(4)]
    grid = VixCarrierGrid(cells + [branch] + sink)
    for _ in range(40):
        grid.tick()
    got = [grid.cells[(0, 1 + j)].ram_data_reg for j in (3, 2, 1, 0) if grid.cells[(0, 1 + j)].ram_data_valid]
    assert got == [2, 3], "1 = baseline, 1,1 equal (silent), 2 rise (emit), 2 equal (silent), 3 rise (emit)"
