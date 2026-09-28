"""
test_grid_native_drain_event_v1.py -- points.md #876: the drain event built
ENTIRELY from grid cells, with no connection-point harness and no data values.

  counter  : an `accumulator` counting occupancy by ARRIVAL DIRECTION (+1 for a
             copy of each item entering, -1 for a copy of each item leaving; it
             ignores values and nets a simultaneous +1/-1 to zero).
  stage A  : a `branch` in ROLLING mode, silent on "equal", passing the INPUT
             value on any change -- so the counter's continuous re-offers of an
             unchanged total vanish and only CHANGES come through (#875).
  stage B  : a `branch` with a FIXED baseline of 0 that fires a fixed 1 only when
             a changed value equals 0 -- "the count became zero". Its reference
             is always its FIRST arrival (no config key preloads it), so a
             preloaded 0 is delivered first on the same face via a merge cell.
  delay    : one relay cell after stage B (Alan: "add a delay on the branch
             dispatch side ... so even if the trigger is on the actual arrival,
             this ensures the branch is clear completely").

Unlike #858's latch this handles SEVERAL items in flight: with a 4-cell section
the count peaks at 3 and the event fires exactly once, at the final drain.

REAL, HONEST SCOPE:
  * VM only; the VM is round-stepped, not cycle-accurate. In this VM the trigger
    ALREADY reaches its consumer one tick after stage B has cleared (offer/ack
    pipelining), so the delay cell is a MARGIN here, not a fix. Whether it is
    needed is a question for RTL timing, which this does not answer.
  * The delay is a RELAY CELL in the path (one extra cell), not a delay
    parameter inside the branch core; the latter would be a core change.
  * The exit copy travels a relay path as long as the section, so the count
    reaches zero slightly AFTER the last item really leaves: a conservative lag
    (never early), which is the safe direction for a drain signal.
  * The zero-reference stage needs its baseline delivered first; a 0 arriving
    late would leave it wrong (see the no-zero-reference control).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid, PROG_ID_MODE  # noqa: E402,F401

ITEMS_A = [0x00000000, 0x00F00001, 0x00000002, 0xDEADBEEF]
ITEMS_B = [0xFFFFFFFF, 0x00000001, 0x12345678, 0x00F00001]
COLLECTORS = 3


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _build(items, L=4, delay=True, stage_a="branch", zero_ref=True, n_out=None):
    """Returns (grid, k, first_collector_col)."""
    k = len(items)
    n_out = n_out or k
    cells = []
    for i, v in enumerate(items):                         # source chain; S1 (row k-1) speaks first
        cells.append(_rec(f"S{i + 1}", k - 1 - i, 3, "ram", {
            "init_data": v, "load_data_valid": 1,
            "upstream_mask": [] if i == k - 1 else ["n"],
            "downstream_mask": ["s", "e"] if i == 0 else ["s"]}))
    for j in range(L):                                    # the drained section
        cells.append(_rec(f"sec{j}", k + j, 3, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s", "e"] if j == L - 1 else ["s"]}))
    for j in range(n_out):                                # output chain, sized never to block
        cells.append(_rec(f"O{j + 1}", k + L + j, 3, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s"] if j < n_out - 1 else []}))
    # taps: a copy of each item entering (from S1) and leaving (from the tail)
    cells.append(_rec("r_in", k - 1, 4, "ram", {"upstream_mask": ["w"], "downstream_mask": ["s"]}))
    cells.append(_rec(f"r_out{L - 1}", k + L - 1, 4, "ram", {"upstream_mask": ["w"], "downstream_mask": ["n"]}))
    for j in range(L - 2, 0, -1):
        cells.append(_rec(f"r_out{j}", k + j, 4, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}))
    cells.append(_rec("acc", k, 4, "accumulator", {"inc_dir": ["n"], "dec_dir": ["s"],
                                                   "step_amount": 1, "downstream_mask": ["e"]}))
    if stage_a == "branch":
        cells.append(_rec("A", k, 5, "branch", {
            "upstream_dir": ["w"], "rolling_mode": 1,
            "emit_high": 1, "value_source_high": 0, "route_high": ["e"],
            "emit_low": 1, "value_source_low": 0, "route_low": ["e"], "emit_equal": 0}))
    else:                                                 # negative control: no change filter at all
        cells.append(_rec("A", k, 5, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}))
    cells.append(_rec("M", k, 6, "ram", {"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}))
    if zero_ref:
        cells.append(_rec("P", k - 1, 6, "ram", {"init_data": 0, "load_data_valid": 1, "downstream_mask": ["s"]}))
    cells.append(_rec("B", k, 7, "branch", {
        "upstream_dir": ["w"], "rolling_mode": 0,
        "emit_equal": 1, "value_source_equal": 1, "fixed_value_equal": 1, "route_equal": ["e"],
        "emit_low": 0, "emit_high": 0}))
    col = 8
    if delay:
        cells.append(_rec("D", k, col, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}))
        col += 1
    for j in range(COLLECTORS):
        cells.append(_rec(f"K{j}", k, col + j, "ram", {
            "upstream_mask": ["w"], "downstream_mask": ["e"] if j < COLLECTORS - 1 else []}))
    return VixCarrierGrid(cells), k, col


def _events(grid, k, kc):
    return sum(int(grid.cells[(k, kc + j)].ram_data_valid) for j in range(COLLECTORS))


def _trace(grid, k, kc, ticks=90):
    """Per-tick (count, events) plus the first-occurrence ticks that matter."""
    acc, A, B = grid.cells[(k, 4)], grid.cells[(k, 5)], grid.cells[(k, 7)]
    rows, tl = [], {"peak": 0, "t_zero": None, "t_B": None, "t_arrive": None, "t_A_zero": None}
    for t in range(ticks):
        grid.tick()
        c, e = acc.acc_total, _events(grid, k, kc)
        rows.append((c, e))
        tl["peak"] = max(tl["peak"], c)
        if tl["peak"] > 0 and c == 0 and tl["t_zero"] is None:
            tl["t_zero"] = t
        if A.br_data_valid and A.br_out_buffer == 0 and tl["peak"] > 0 and tl["t_A_zero"] is None:
            tl["t_A_zero"] = t
        if B.br_data_valid and tl["t_B"] is None:
            tl["t_B"] = t
        if e and tl["t_arrive"] is None:
            tl["t_arrive"] = t
    return rows, tl


def test_several_items_are_genuinely_in_flight_and_the_count_returns_to_zero():
    grid, k, kc = _build(ITEMS_A)
    rows, tl = _trace(grid, k, kc)
    assert tl["peak"] >= 2, "more than one item in flight at once -- the case #858's latch got wrong"
    assert rows[-1][0] == 0, "the count returns to exactly zero once everything has drained"


def test_exactly_one_drain_event_and_none_while_items_remain():
    grid, k, kc = _build(ITEMS_A)
    rows, tl = _trace(grid, k, kc)
    assert rows[-1][1] == 1, "exactly one drain event for the whole stream"
    assert all(e == 0 for (_c, e) in rows[:tl["t_zero"] + 1]), \
        "no event while the count is still above zero, however many times it changed on the way"
    assert tl["t_zero"] < tl["t_A_zero"] < tl["t_B"] < tl["t_arrive"], "strictly ordered pipeline"


def test_two_separate_bursts_give_two_events_so_the_detector_rearms():
    """Burst 1 drains; the HOST then reloads the source head (a harness step,
    like the next pass in the loop) and burst 2 must fire a second event."""
    grid, k, kc = _build([0x11111111], n_out=2)
    _trace(grid, k, kc, ticks=60)
    assert _events(grid, k, kc) == 1, "burst 1: one event"
    s1 = grid.cells[(k - 1, 3)]
    s1.program_in = True
    s1.program_word(3, 0x2222)        # init_data low half
    s1.program_word(4, 0x0000)        # init_data high half
    s1.program_word(6, 1)             # data_valid: a fresh item is offered
    s1.program_in = False
    for _ in range(60):
        grid.tick()
    assert _events(grid, k, kc) == 2, "burst 2: a second, separate event -- the baseline-0 stage stays armed"


def test_the_timeline_is_identical_for_completely_different_data():
    gA, k, kc = _build(ITEMS_A)
    gB, _, _ = _build(ITEMS_B)
    rowsA, tlA = _trace(gA, k, kc)
    rowsB, tlB = _trace(gB, k, kc)
    assert rowsA == rowsB and tlA == tlB, "the counter never reads a value, so nothing depends on the data"


def test_the_delay_adds_exactly_one_tick_and_the_branch_is_completely_clear_on_arrival():
    """Alan's spec: the trigger lands one tick later so the branch is clear."""
    g_no, k, kc_no = _build(ITEMS_A, delay=False)
    g_de, _, kc_de = _build(ITEMS_A, delay=True)
    _, tl_no = _trace(g_no, k, kc_no)
    _, tl_de = _trace(g_de, k, kc_de)
    assert tl_de["t_B"] == tl_no["t_B"], "the detector itself is unchanged by the delay cell"
    assert tl_de["t_arrive"] - tl_no["t_arrive"] == 1, "the delay makes the trigger land exactly ONE tick later"

    # at the moment the delayed trigger has landed, everything upstream is completely clear
    g, k, kc = _build(ITEMS_A, delay=True)
    for t in range(tl_de["t_arrive"] + 1):
        g.tick()
    assert g.cells[(k, 5)].br_data_valid is False, "stage A holds nothing"
    assert g.cells[(k, 7)].br_data_valid is False, "stage B holds nothing -- the branch is clear completely"
    assert g.cells[(k, 4)].acc_total == 0
    assert not any(g.cells[(k + j, 3)].ram_data_valid for j in range(4)), "and the whole section is empty"


def test_in_this_vm_the_trigger_already_lands_one_tick_after_the_branch_clears_without_the_delay():
    """Honest note, pinned: the VM's offer/ack pipelining already gives one tick
    between stage B's output and its consumer, so here the delay is MARGIN, not a
    fix. Cycle-accurate RTL timing is what would show whether it is needed."""
    g, k, kc = _build(ITEMS_A, delay=False)
    _, tl = _trace(g, k, kc)
    assert tl["t_arrive"] - tl["t_B"] == 1


def test_control_without_the_change_filter_the_level_source_fires_false_events():
    """Replace stage A with a plain relay: stage B now sees the counter's
    continuous re-offers and compares every one against its baseline of 0, so it
    fires REPEATEDLY -- including while items are still in the section (observed:
    the first false event at t6 with the count at 3, three events for one drain).
    (I first predicted 'before any item enters'; the trace showed otherwise.)"""
    grid, k, kc = _build(ITEMS_A, stage_a="relay")
    rows, tl = _trace(grid, k, kc)
    assert any(c > 0 and e > 0 for (c, e) in rows), \
        "an event appears while items are STILL in the section: a false, early drain signal"
    assert rows[-1][1] > 1, "and it fires more than once for a single drain -- not a one-shot"


def test_control_without_the_zero_reference_the_detector_fires_at_the_wrong_count():
    """Drop the preloaded 0: stage B's baseline becomes its first arrival, the
    first CHANGED count (1). The real drain (0) is then merely 'below baseline'
    and produces NO event; instead the detector fires whenever the count returns
    to 1 -- while an item is still in flight. (I first predicted 'never fires';
    the trace showed it fires, for the wrong reason, at the wrong moment.)"""
    grid, k, kc = _build([0x11111111], n_out=2, zero_ref=False)
    acc, B = grid.cells[(k, 4)], grid.cells[(k, 7)]
    for _ in range(60):
        grid.tick()
    assert acc.acc_total == 0 and B.br_ref_value == 1, "the baseline is 1, not 0"
    assert _events(grid, k, kc) == 0, "burst 1's REAL drain produced no event at all"

    s1 = grid.cells[(k - 1, 3)]
    s1.program_in = True
    s1.program_word(3, 0x2222)
    s1.program_word(4, 0x0000)
    s1.program_word(6, 1)
    s1.program_in = False
    count_when_it_fired = None
    for _ in range(60):
        grid.tick()
        if _events(grid, k, kc) >= 1 and count_when_it_fired is None:
            count_when_it_fired = acc.acc_total
    assert count_when_it_fired == 1, "burst 2: it fired at count 1 -- an item still in flight -- not at the drain"
