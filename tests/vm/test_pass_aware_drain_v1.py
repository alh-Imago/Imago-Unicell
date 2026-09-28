"""
test_pass_aware_drain_v1.py -- points.md #878: a PASS-AWARE drain signal.

#876's grid-native detector means "the count became zero" and fires at EVERY
zero crossing, so a bubble in the middle of a pass (the section briefly empties,
then more items of the same pass arrive) fires it early. The sentinel avoids this
with `safe_to_intervene` = pass-ended AND count-zero.

The simple grid-native answer is #850's exit counter, aimed at the section's
exits: an `accumulator` in PULSE MODE with threshold = the pass length. It stays
silent while counting, offers EXACTLY ONCE when the N-th item has left, and
resets itself for the next pass. One cell, no zero-reference, no change filter.
A bubble cannot fool it because it never looks at emptiness -- only at how many
items have EXITED.

What it costs, said plainly: it TRUSTS the configured pass length. The compiler
knows how many items a pass carries (the same knowledge as the RTL's address-
counter wrap), but if more or fewer items are actually fed the counter is wrong:
too few -> it never fires (a safe stall, like a truncated program); too many ->
it fires while an item is still in flight. #876's detector needs no pass length
but is not pass-aware. They are complementary; combining them is the robust form.

RETRACTION recorded here: #877 suggested ANDing a pass-end pulse with the drain
event through a `nano` rendezvous. Reasoned (NOT run) to be flawed: a nano holds
its first operand until the second arrives, so a stale bubble event would satisfy
the AND early at the pass-end pulse. Replaced by the exit counter, which is tested.

REAL, HONEST SCOPE: VM only; the pass length is a compile-time constant here; the
drain->command-cell wiring and source gating for this variant are not built.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))
sys.path.insert(0, os.path.dirname(__file__))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402
import test_grid_native_drain_event_v1 as zc  # noqa: E402  (#876's zero-crossing detector, for comparison)

ITEMS_A = [0x00000000, 0x00F00001, 0x00000002, 0xDEADBEEF]
ITEMS_B = [0xFFFFFFFF, 0x00000001, 0x12345678, 0x00F00001]
COLLECTORS = 3


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _build(items, pass_len=None, L=4, delay=1, n_out=None):
    """Same section as #876; the exit tap feeds a pulse-mode accumulator. Returns (grid, k, first_collector_col)."""
    k = len(items)
    pass_len = pass_len or k
    n_out = n_out or k
    cells = []
    for i, v in enumerate(items):
        cells.append(_rec(f"S{i + 1}", k - 1 - i, 3, "ram", {
            "init_data": v, "load_data_valid": 1,
            "upstream_mask": [] if i == k - 1 else ["n"], "downstream_mask": ["s"]}))
    for j in range(L):
        cells.append(_rec(f"sec{j}", k + j, 3, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s", "e"] if j == L - 1 else ["s"]}))
    for j in range(n_out):
        cells.append(_rec(f"O{j + 1}", k + L + j, 3, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s"] if j < n_out - 1 else []}))
    cells.append(_rec(f"r_out{L - 1}", k + L - 1, 4, "ram", {"upstream_mask": ["w"], "downstream_mask": ["n"]}))
    for j in range(L - 2, 0, -1):
        cells.append(_rec(f"r_out{j}", k + j, 4, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}))
    cells.append(_rec("pc", k, 4, "accumulator", {"inc_dir": ["s"], "step_amount": 1, "pulse_mode": 1,
                                                  "threshold": pass_len, "downstream_mask": ["e"]}))
    col = 5
    for d in range(delay):
        cells.append(_rec(f"D{d}", k, col, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}))
        col += 1
    for j in range(COLLECTORS):
        cells.append(_rec(f"K{j}", k, col + j, "ram", {
            "upstream_mask": ["w"], "downstream_mask": ["e"] if j < COLLECTORS - 1 else []}))
    return VixCarrierGrid(cells), k, col


def _events(grid, k, kc):
    return sum(int(grid.cells[(k, kc + j)].ram_data_valid) for j in range(COLLECTORS))


def _run(grid, k, kc, items=None, bubble_wait=None, ticks=140):
    """Tick, optionally creating a mid-pass bubble: freeze the source head the
    moment item 3 arrives in it, and release it `bubble_wait` ticks later."""
    s1 = grid.cells[(k - 1, 3)]
    frozen_at = released = None
    first_event, at_first_event = None, None
    for t in range(ticks):
        grid.tick()
        if bubble_wait is not None:
            if frozen_at is None and s1.ram_data_valid and s1.ram_data_reg == items[2]:
                s1.freeze_in, frozen_at = True, t
            if frozen_at is not None and released is None and t - frozen_at >= bubble_wait:
                s1.freeze_in, released = False, t
        if first_event is None and _events(grid, k, kc):
            first_event = t
            # what is still upstream of the section when the first event appears?
            at_first_event = {"source_items": sum(int(grid.cells[(r, 3)].ram_data_valid) for r in range(k))}
    return first_event, at_first_event


def test_the_exit_counter_fires_exactly_once_after_the_pass_length_th_exit():
    grid, k, kc = _build(ITEMS_A)
    pc = grid.cells[(k, 4)]
    pulse_tick = None
    for t in range(80):
        grid.tick()
        if pc.acc_pulse_pending and pulse_tick is None:
            pulse_tick = t
            assert all(grid.cells[(k + 4 + j, 3)].ram_data_valid for j in range(4)), \
                "when the pulse fires all four items have already reached the output chain"
        if pulse_tick is None:
            assert _events(grid, k, kc) == 0, "silent while counting"
    assert pulse_tick is not None and _events(grid, k, kc) == 1, "exactly one event for the whole pass"


def test_a_mid_pass_bubble_fools_the_zero_crossing_detector_but_not_the_exit_counter():
    """The same bubble script on both: items 1-2 flow, the source is held until
    the section has fully emptied, then items 3-4 follow."""
    g_zero, k, kc_zero = zc._build(ITEMS_A, delay=1)
    fe_zero, at_zero = _run(g_zero, k, kc_zero, ITEMS_A, bubble_wait=30)
    n_zero = zc._events(g_zero, k, kc_zero)

    g_exit, k2, kc_exit = _build(ITEMS_A)
    fe_exit, _ = _run(g_exit, k2, kc_exit, ITEMS_A, bubble_wait=30)
    n_exit = _events(g_exit, k2, kc_exit)

    assert n_zero == 2, "#876's detector fires at the bubble AND at the end -- two events for one pass"
    assert at_zero["source_items"] >= 1, "its first event fires while items of the pass are still parked upstream"
    assert n_exit == 1, "the exit counter fires once, only after the 4th item has left"
    assert fe_exit > fe_zero, "and later than the bubble's false event"


def test_the_counter_rearms_itself_for_the_next_pass():
    items = ITEMS_A + [0x0A0A0A0A, 0x0B0B0B0B, 0x0C0C0C0C, 0x0D0D0D0D]
    grid, k, kc = _build(items, pass_len=4)
    for _ in range(140):
        grid.tick()
    assert _events(grid, k, kc) == 2, "one event per pass of four: pulse mode resets itself after each"


def test_the_timeline_is_identical_for_completely_different_data():
    ga, k, kc = _build(ITEMS_A)
    gb, _, _ = _build(ITEMS_B)
    ta, tb = [], []
    for _ in range(60):
        ga.tick()
        gb.tick()
        ta.append(_events(ga, k, kc))
        tb.append(_events(gb, k, kc))
    assert ta == tb and ta[-1] == 1


def test_control_too_few_items_it_never_fires_a_safe_stall():
    grid, k, kc = _build(ITEMS_A[:3], pass_len=4)
    for _ in range(80):
        grid.tick()
    assert _events(grid, k, kc) == 0, "a short pass never reaches its threshold -- nothing fires, nothing is corrupted"


def test_known_limit_too_many_items_leave_a_residual_count_that_skews_every_later_pass():
    """It trusts the configured pass length, and over-feeding it fails in a way I
    first predicted WRONGLY. I expected 'it fires while the extra item is still in
    flight'. The trace shows otherwise: the exit tap lags the real exits by about
    three ticks, so by the time the pulse fires (the 4th exit COUNTED) all five
    items have already left -- it is not early. The damage is afterwards: the 5th
    item's exit copy is counted AFTER the reset, leaving a residual count of 1 that
    carries into the next pass, which will then fire one item early, and every
    pass after it. Pinned so it cannot change silently; the guard is the
    zero-crossing detector or the sentinel's diff, which count emptiness, not items."""
    items = ITEMS_A + [0x55555555]
    grid, k, kc = _build(items, pass_len=4, n_out=5)
    pc = grid.cells[(k, 4)]
    at_pulse = None
    for t in range(60):
        grid.tick()
        if pc.acc_pulse_pending and at_pulse is None:
            at_pulse = (sum(int(grid.cells[(k + 4 + j, 3)].ram_data_valid) for j in range(5)),
                        sum(int(grid.cells[(k + j, 3)].ram_data_valid) for j in range(4)))
    assert at_pulse == (5, 0), "the pulse is NOT early here: all five items had already exited (tap lag)"
    assert pc.acc_total == 1, "but the fifth exit was counted after the reset: a residual count of 1 skews the next pass"
