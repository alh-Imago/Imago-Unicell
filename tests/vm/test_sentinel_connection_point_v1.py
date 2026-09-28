"""
test_sentinel_connection_point_v1.py -- points.md #872: the drain signal is now
VALUE-INDEPENDENT. The existing `Sentinel` is attached to a real
`VixCarrierGrid` as a connection point (nano/sentinel_connection_point_v1.py);
its FEED/COLLECT counts come from accepted deliveries, never from data values,
and it prompts the reprogram and releases the next pass. See that module's
docstring for the design and its honest scope.

Grid: a serialized program store (three programs' words) feeding a
programmer-mode command cell that reprograms a target, held frozen at rest by
a trigger-mode cell; a source chain of four items feeding a two-cell section
(head, tail) into a four-cell output chain. Two passes of two items each.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402
from unicell_automaton_v1 import (  # noqa: E402
    PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE,
)
from unicell_gate_core import TOPO_NOT_A, TOPO_AND, TOPO_PASS_A  # noqa: E402
from sentinel_connection_point_v1 import SentinelConnectionPoint  # noqa: E402

TOGGLE = (PROG_ID_COMPLETE << 20) | 1
PROG0 = (TOPO_NOT_A, 0b0100)
PROG1 = (TOPO_AND, 0b0010)
PROG2 = (TOPO_PASS_A, 0b1000)
# deliberately awkward: zero, an EVEN value (the #858 latch's SET needed bit 0
# set), and the exact word #871 used as its data marker
ITEMS_A = [0x00000000, 0x00F00001, 0x00000002, 0xDEADBEEF]
ITEMS_B = [0xFFFFFFFF, 0x00000001, 0x12345678, 0x00F00001]


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _words(t, m, complete=True):
    w = [(PROG_ID_TOPOLOGY << 20) | t, (PROG_ID_ROUTING_MASK << 20) | m]
    return w + ([TOGGLE] if complete else [])


def _build(programs, items, cp_class=SentinelConnectionPoint, pass_len=2):
    seq = [w for p in programs for w in p]
    n = len(seq)
    top = -(n - 1)
    cells = []
    for i, w in enumerate(reversed(seq)):        # program store, column 0; head (row 0) speaks first
        r = top + i
        cells.append(_rec(f"w{r}", r, 0, "ram", {
            "init_data": w, "load_data_valid": 1,
            "upstream_mask": [] if r == top else ["n"],
            "downstream_mask": ["w", "e"] if r == 0 else ["s"]}))
    cells += [
        _rec("CMD1", 0, -1, "command", {"mode": 1, "polarity": 0, "drive_dir": 3,
                                        "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("TGT", 0, -2, "nano", {}),
        _rec("CTL", 0, 1, "command", {"mode": 0, "polarity": 0, "drive_dir": 3,
                                      "toggle_pattern": PROG_ID_COMPLETE}),
    ]
    k = len(items)
    for i, v in enumerate(items):                # source chain; S1 (row k-1) speaks first
        r = k - 1 - i
        cells.append(_rec(f"S{i + 1}", r, 3, "ram", {
            "init_data": v, "load_data_valid": 1,
            "upstream_mask": [] if i == k - 1 else ["n"], "downstream_mask": ["s"]}))
    cells += [_rec("head", k, 3, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]}),
              _rec("tail", k + 1, 3, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]})]
    for j in range(k):                           # output chain long enough that it never blocks
        cells.append(_rec(f"O{j + 1}", k + 2 + j, 3, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s"] if j < k - 1 else []}))
    grid = VixCarrierGrid(cells)
    cp = cp_class(grid, feed_pos=(k, 3), collect_pos=(k + 2, 3), source_pos=(k - 1, 3),
                  head_pos=(k, 3), gate_pos=(0, 1), gate_word=TOGGLE,
                  program_active_pos=(0, -1), pass_len=pass_len, chain_length=2)
    return grid, cp, k


def _kinds(cp, kind):
    return [t for (t, kd, _d) in cp.events if kd == kind]


def _sessions(cp):
    prompts, completes = _kinds(cp, "prompt"), _kinds(cp, "complete")
    return list(zip(prompts, completes))


def _full_run(items=ITEMS_A, programs=None, cp_class=SentinelConnectionPoint, ticks=160):
    programs = programs or [_words(*PROG0), _words(*PROG1), _words(*PROG2)]
    grid, cp, k = _build(programs, items, cp_class)
    cp.run(ticks)
    return grid, cp, k


def test_power_on_safe_state_prompts_the_initial_programming_before_any_data_enters():
    grid, cp, k = _full_run()
    first_prompt = cp.events[0]
    assert first_prompt[1] == "prompt" and first_prompt[2] == 0, \
        "frozen + drained at power-on IS 'safe': that edge prompts the first programming"
    assert _kinds(cp, "complete")[0] < _kinds(cp, "feed")[0], \
        "no item may enter until the initial programming has completed"


def test_each_reprogram_starts_only_when_the_section_is_completely_drained():
    grid, cp, k = _full_run()
    prompts = _kinds(cp, "prompt")
    assert len(prompts) == 3, "power-on + one after each of the two passes"
    for p in prompts[1:]:
        fed = sum(1 for (t, kd, _d) in cp.events if kd == "feed" and t <= p)
        collected = sum(1 for (t, kd, _d) in cp.events if kd == "collect" and t <= p)
        assert fed == collected, "every item fed has been collected by the time the prompt fires"
        diff_at_prompt = [d for (t, kd, d) in cp.events if kd == "prompt" and t == p][0]
        assert diff_at_prompt == 0
    wraps = [(t, d) for (t, kd, d) in cp.events if kd == "wrap"]
    assert any(d > 0 for (_t, d) in wraps), \
        "at the pass-end wrap an item is still in flight -- the wrap alone is NOT enough, the drain is what matters"


def test_the_section_is_quiescent_while_a_program_runs():
    grid, cp, k = _full_run()
    for (start, end) in _sessions(cp):
        inside = [kd for (t, kd, _d) in cp.events if start < t <= end and kd in ("feed", "collect")]
        assert inside == [], "no item may enter OR leave the section while it is being reprogrammed"


def test_each_pass_admits_exactly_pass_len_items():
    grid, cp, k = _full_run()
    completes = _kinds(cp, "complete")
    feeds = _kinds(cp, "feed")
    assert len(completes) == 3
    pass1 = [t for t in feeds if completes[0] < t < completes[1]]
    pass2 = [t for t in feeds if completes[1] < t < completes[2]]
    assert len(pass1) == 2 and len(pass2) == 2 and len(feeds) == 4


def test_the_whole_timeline_is_identical_for_completely_different_data():
    """Value independence, asserted directly: two runs with unrelated item
    values -- including zero, even values, and the old marker word -- produce
    the SAME event timeline, and every item arrives unmodified."""
    gridA, cpA, k = _full_run(ITEMS_A)
    gridB, cpB, _ = _full_run(ITEMS_B)
    assert cpA.events == cpB.events, "the sentinel's behaviour must not depend on what the data is"
    for grid, items in ((gridA, ITEMS_A), (gridB, ITEMS_B)):
        out = [grid.cells[(k + 2 + j, 3)] for j in range(k)]
        assert all(c.ram_data_valid for c in out)
        assert [c.ram_data_reg for c in out] == list(reversed(items)), "items arrive unmodified, in order"


def test_the_loop_ends_clean():
    grid, cp, k = _full_run()
    tgt, cmd1 = grid.cells[(0, -2)], grid.cells[(0, -1)]
    assert (tgt._nano.topology, tgt._nano.routing_mask, tgt._nano.start_flag) == (PROG2[0], PROG2[1], True)
    assert tgt.freeze_in is False and cmd1.command_active_r is False
    assert grid.cells[(0, 0)].freeze_in is True, "the program store ends halted"
    assert cp.sentinel.diff == 0 and cp.sentinel.err_flag is False
    assert cp.total_feeds == cp.total_collects == 4


def test_a_program_that_stops_short_stalls_safely_and_holds_back_the_next_pass():
    """Alan's caveat, demonstrated: if the program store runs out before its
    COMPLETE word, the programming never finishes, so the completion edge never
    fires, so the feed side is never released. The reprogrammed unit stays
    frozen and the next pass waits forever. It is a SAFE stall -- nothing is
    corrupted and nothing runs away -- but it is a stall."""
    programs = [_words(*PROG0), _words(*PROG1, complete=False)]
    grid, cp, k = _build(programs, ITEMS_A)
    cp.run(200)
    tgt, cmd1, S1 = grid.cells[(0, -2)], grid.cells[(0, -1)], grid.cells[(k - 1, 3)]

    assert len(_kinds(cp, "prompt")) == 2 and len(_kinds(cp, "complete")) == 1, \
        "the second programming was prompted but never completed"
    assert cp.total_feeds == 2, "pass 2 never starts: only pass 1's items were admitted"
    assert tgt.freeze_in is True and cmd1.command_active_r is True, "the reprogrammed unit is stuck frozen mid-program"
    assert cp.sentinel.out_frozen is True and S1.freeze_in is True, "the feed side is never released"
    S2, S3 = grid.cells[(k - 2, 3)], grid.cells[(k - 3, 3)]
    assert not S1.ram_data_valid, "the frozen source head is EMPTY: the freeze landed before item 3 could shift in"
    assert S2.ram_data_valid and S2.ram_data_reg == ITEMS_A[2], "item 3 is parked behind the frozen head, intact"
    assert S3.ram_data_valid and S3.ram_data_reg == ITEMS_A[3], "item 4 too"
    assert cp.sentinel.err_flag is False, "a stall is not an error state -- the sentinel just never sees completion"

    snapshot = (cp.total_feeds, cp.total_collects, tgt.freeze_in, cmd1.command_active_r, len(cp.events))
    cp.run(80)
    assert (cp.total_feeds, cp.total_collects, tgt.freeze_in, cmd1.command_active_r, len(cp.events)) == snapshot, \
        "and it stays exactly stalled -- no runaway, no drift"


def test_prompting_on_the_out_freeze_alone_would_reprogram_with_items_still_moving():
    """Negative control, from the RTL header's own reasoning (#279): 'OUT
    freezing alone doesn't prove the pipeline is drained, only that no NEW data
    is entering.' Prompt on out_frozen instead of safe_to_intervene and the
    reprogram starts while an item is still in flight, and the section is
    moving DURING programming."""
    class EarlyPrompt(SentinelConnectionPoint):
        def _maybe_prompt(self):
            flag = self.sentinel.need_data_flag          # out_frozen only -- ignores the drain
            if flag and not self._prev_safe and not self._prog_running:
                self.grid.inject(self.gate_pos[0], self.gate_pos[1], self.gate_word)
                self._prog_running = True
                self._prog_seen_active = False
                self._log("prompt")
            self._prev_safe = flag

    grid, cp, k = _full_run(cp_class=EarlyPrompt)
    prompts_with_items_in_flight = [d for (t, kd, d) in cp.events if kd == "prompt" and d > 0]
    assert prompts_with_items_in_flight, "the early prompt fires while diff > 0"
    moving_during_program = any(
        kd in ("feed", "collect") and start < t <= end
        for (start, end) in _sessions(cp) for (t, kd, _d) in cp.events)
    assert moving_during_program, "and items move through the section while it is being reprogrammed"
