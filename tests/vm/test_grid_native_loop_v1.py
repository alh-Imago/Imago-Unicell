"""
test_grid_native_loop_v1.py -- points.md #879: the reconfiguration loop with NO
harness glue and NO data-valued marker anywhere. Replaces #872's connection-point
glue (feed/collect counting, pass counter, start-word injection, completion edge)
with cells, and #871's data-as-marker placeholders.

Every piece is a cell:
  * START WORD = a preloaded constant, never data. Power-on: a one-shot `ram`
    holding the word. Per pass: a hold-and-reemit `nano` (#382) pre-armed with the
    word; ANY arrival releases it, so the trigger's own value is irrelevant.
  * DRAIN = #878's pass-aware exit counter: an `accumulator` in pulse mode with
    threshold = the pass length, counting the section's exits. Fires once after the
    N-th item has left and resets itself. Its pulse reaches the nano through a
    3-cell relay path (delay AND buffer, #877).
  * PROGRAM RUN = a trigger-mode command cell holding the program store's head
    frozen; the start word unfreezes it, the program's own final word halts it
    (#870); a programmer-mode cell relays the words to the target.
  * SOURCE GATE = a second trigger-mode command cell holding the source head
    frozen. It sees only two events, which strictly alternate: the START word
    (freeze) and a copy of the program's FINAL word (release).
  * THE CHAIN IS ITS OWN COUNTER. The source holds exactly one pass of items, so
    nothing has to count admissions. I first considered counting admissions and
    freezing on the pulse; that has a race (the pulse path is >= 3 ticks, the
    source releases an item every 2) and was not built.

The ONLY thing the test does is the LOADER: when the source is frozen and empty it
puts the next pass into it -- standing in for the host loading BRAM in the real
protocol ("host loads N inputs, unfreezes"). It touches nothing else.

REAL, HONEST SCOPE:
  * VM only. The loader is a harness step. The reprogrammed unit is still a
    separate target, NOT a cell of the drained section -- the actual fold.
  * A hold-and-reemit nano is one of nano's "extras". The carrier's first RTL build
    ties those inputs to inactive defaults (root_definition.json), so this needs
    standalone nano_gate_v4 or a carrier extension before it can run in RTL.
  * Two passes of two items and three programs; N passes is not demonstrated.
  * Whether the relay delays are needed at all is an RTL-timing question (#876).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402
from unicell_automaton_v1 import PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE  # noqa: E402
from unicell_gate_core import TOPO_NOT_A, TOPO_AND, TOPO_PASS_A  # noqa: E402

TOGGLE = (PROG_ID_COMPLETE << 20) | 1
PROG_CONFIGS = [(TOPO_NOT_A, 0b0100), (TOPO_AND, 0b0010), (TOPO_PASS_A, 0b1000)]
PASSES_A = [[0x11111111, 0x00F00001], [0x00000002, 0xDEADBEEF]]     # incl. the old marker word and an even value
PASSES_B = [[0xFFFFFFFF, 0x00000001], [0x12345678, 0x00000000]]
L = 4


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _words(t, m):
    return [(PROG_ID_TOPOLOGY << 20) | t, (PROG_ID_ROUTING_MASK << 20) | m, TOGGLE]


def _build(first_pass, gated=True):
    pl = len(first_pass)
    seq = [w for (t, m) in PROG_CONFIGS for w in _words(t, m)]
    n = len(seq)
    top = -(n - 1)
    cells = []
    for i, w in enumerate(reversed(seq)):              # program store, column 0; head H at row 0 speaks first
        r = top + i
        cells.append(_rec(f"w{r}", r, 0, "ram", {
            "init_data": w, "load_data_valid": 1,
            "upstream_mask": [] if r == top else ["n"],
            "downstream_mask": ["w", "e", "s"] if r == 0 else ["s"]}))
    cells += [
        _rec("CMD1", 0, -1, "command", {"mode": 1, "polarity": 0, "drive_dir": 3, "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("TGT", 0, -2, "nano", {}),
        _rec("CTL", 0, 1, "command", {"mode": 0, "polarity": 0, "drive_dir": 3, "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("MS", 0, 2, "ram", {"upstream_mask": ["n", "e"], "downstream_mask": ["w"]}),
        _rec("Q", -1, 2, "ram", {"init_data": TOGGLE, "load_data_valid": 1, "downstream_mask": ["s"]}),   # power-on start
        _rec("Npass", 0, 3, "nano", {"topology": TOPO_PASS_A, "ready": 1, "hold_in": 1, "a_reemit_in": 1,
                                     "routing_mask": ["w", "s"]}),                                       # per-pass start
        _rec("Ppass", -1, 3, "ram", {"init_data": TOGGLE, "load_data_valid": 1, "downstream_mask": ["s"]}),  # arms Npass
        # copy of the program's final word travels to the source gate
        _rec("c1", 1, 0, "ram", {"upstream_mask": ["n"], "downstream_mask": ["e"]}),
        _rec("c2", 1, 1, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("c3", 1, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("MS2", 1, 3, "ram", {"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}),
        _rec("CTL2", 1, 4, "command", {"mode": 0, "polarity": 0, "drive_dir": 1,
                                       "toggle_pattern": PROG_ID_COMPLETE if gated else 14}),
    ]
    for i, v in enumerate(first_pass):                 # source chain: S1 (2,4) speaks first, S2 (2,3), ...
        cells.append(_rec(f"S{i + 1}", 2, 4 - i, "ram", {
            "init_data": v, "load_data_valid": 1,
            "upstream_mask": [] if i == pl - 1 else ["w"], "downstream_mask": ["s"] if i == 0 else ["e"]}))
    for j in range(L):                                 # the drained section
        cells.append(_rec(f"sec{j}", 3 + j, 4, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s", "e"] if j == L - 1 else ["s"]}))
    n_out = pl * 2
    for j in range(n_out):
        cells.append(_rec(f"O{j + 1}", 3 + L + j, 4, "ram", {
            "upstream_mask": ["n"], "downstream_mask": ["s"] if j < n_out - 1 else []}))
    # exit tap -> pulse-mode counter -> 3-cell relay path -> Npass
    cells.append(_rec("ro", 2 + L, 5, "ram", {"upstream_mask": ["w"], "downstream_mask": ["n"]}))
    for r in range(1 + L, 2, -1):
        cells.append(_rec(f"ro{r}", r, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}))
    cells.append(_rec("pc", 2, 5, "accumulator", {"inc_dir": ["s"], "step_amount": 1, "pulse_mode": 1,
                                                  "threshold": pl, "downstream_mask": ["n"]}))
    cells += [_rec("u1", 1, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}),
              _rec("u2", 0, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["w"]}),
              _rec("u3", 0, 4, "ram", {"upstream_mask": ["e"], "downstream_mask": ["w"]})]
    grid = VixCarrierGrid(cells)
    if not gated:
        grid.cells[(2, 4)].freeze_in = False           # the ungated control: source never held
    return grid, pl


def _run(grid, pl, passes, cap=140):
    H, CTL2 = grid.cells[(0, 0)], grid.cells[(1, 4)]
    S1, cmd1, tgt, pc = grid.cells[(2, 4)], grid.cells[(0, -1)], grid.cells[(0, -2)], grid.cells[(2, 5)]
    src = [grid.cells[(2, 4 - i)] for i in range(pl)]
    out = [grid.cells[(3 + L + j, 4)] for j in range(pl * 2)]
    ev = {"unfreeze_H": [], "refreeze_H": [], "release_src": [], "hold_src": [], "pulses": [],
          "loads": [], "snap_at_done": [], "rows": []}
    prev_h, prev_s, prev_p = H.freeze_in, S1.freeze_in, pc.acc_pulse_pending
    loaded = 1
    for t in range(cap):
        grid.tick()
        if loaded < len(passes) and S1.freeze_in and not any(c.ram_data_valid for c in src):
            for c, v in zip(src, passes[loaded]):      # THE LOADER: the only harness step
                c.program_in = True
                c.program_word(3, v & 0xFFFF)
                c.program_word(4, (v >> 16) & 0xFFFF)
                c.program_word(6, 1)
                c.program_in = False
            ev["loads"].append(t)
            loaded += 1
        if prev_h and not H.freeze_in:
            ev["unfreeze_H"].append(t)
        if not prev_h and H.freeze_in:
            ev["refreeze_H"].append(t)
            ev["snap_at_done"].append((tgt._nano.topology, tgt._nano.routing_mask, tgt._nano.start_flag))
        if prev_s and not S1.freeze_in:
            ev["release_src"].append(t)
        if not prev_s and S1.freeze_in:
            ev["hold_src"].append(t)
        if not prev_p and pc.acc_pulse_pending:
            ev["pulses"].append(t)
        prev_h, prev_s, prev_p = H.freeze_in, S1.freeze_in, pc.acc_pulse_pending
        ev["rows"].append((t, int(S1.freeze_in), sum(int(c.ram_data_valid) for c in out)))
    ev["out_cells"] = out
    ev["tgt"] = tgt
    return ev


def _items_out_at(ev, t):
    return next(n for (tt, _s, n) in ev["rows"] if tt == t)


def test_two_passes_and_three_programs_run_with_no_host_action_except_the_loader():
    grid, pl = _build(PASSES_A[0])
    ev = _run(grid, pl, PASSES_A)
    assert len(ev["unfreeze_H"]) == 3 and len(ev["refreeze_H"]) == 3, "three programs ran and each halted itself"
    assert [(t, m) for (t, m, _s) in ev["snap_at_done"]] == PROG_CONFIGS, \
        "the target was reprogrammed to each configuration, in order"
    assert all(s for (_t, _m, s) in ev["snap_at_done"]), "each program ended with the target started"
    assert ev["loads"] and len(ev["loads"]) == 1, "the loader fired exactly once, for pass 2"


def test_the_initial_programming_precedes_every_item_and_the_source_is_released_only_after_it():
    grid, pl = _build(PASSES_A[0])
    ev = _run(grid, pl, PASSES_A)
    assert ev["unfreeze_H"][0] < ev["refreeze_H"][0] < ev["release_src"][0], \
        "power-on start, program 0 completes, THEN the source is released"
    assert _items_out_at(ev, ev["release_src"][0]) == 0, "nothing had entered before the release"


def test_the_source_is_held_and_the_section_quiet_throughout_every_program():
    grid, pl = _build(PASSES_A[0])
    ev = _run(grid, pl, PASSES_A)
    for k in range(3):
        start, end = ev["unfreeze_H"][k], ev["refreeze_H"][k]
        window = [(s, n) for (t, s, n) in ev["rows"] if start < t <= end]
        assert all(s == 1 for (s, _n) in window), f"program {k}: the source is frozen for the whole run"
        assert len({n for (_s, n) in window}) == 1, f"program {k}: no item enters or leaves the section meanwhile"


def test_each_reprogram_is_prompted_only_by_the_pass_aware_drain():
    grid, pl = _build(PASSES_A[0])
    ev = _run(grid, pl, PASSES_A)
    assert len(ev["pulses"]) == 2, "exactly one drain pulse per pass"
    for k in (1, 2):
        assert ev["pulses"][k - 1] < ev["unfreeze_H"][k], "the reprogram follows the drain pulse"
        assert _items_out_at(ev, ev["unfreeze_H"][k]) == pl * k, \
            "and starts only after EVERY item of the pass has left the section"


def test_exactly_one_pass_of_items_is_admitted_before_each_reprogram_completes():
    grid, pl = _build(PASSES_A[0])
    ev = _run(grid, pl, PASSES_A)
    for (t, _s, n) in ev["rows"]:
        releases_so_far = sum(1 for r in ev["release_src"] if r <= t)
        assert n <= pl * releases_so_far, "never more than one pass per release"
    assert _items_out_at(ev, ev["release_src"][1]) == pl, "pass 2 waits for program 1 to complete"


def test_the_timeline_is_identical_for_completely_different_data():
    gA, pl = _build(PASSES_A[0])
    gB, _ = _build(PASSES_B[0])
    evA, evB = _run(gA, pl, PASSES_A), _run(gB, pl, PASSES_B)
    keys = ("unfreeze_H", "refreeze_H", "release_src", "hold_src", "pulses", "loads", "snap_at_done", "rows")
    assert all(evA[k] == evB[k] for k in keys), \
        "nothing depends on the data: no data-valued marker exists anywhere in the loop"


def test_the_loop_ends_clean_and_every_item_arrives_unmodified_in_order():
    grid, pl = _build(PASSES_A[0])
    ev = _run(grid, pl, PASSES_A)
    tgt = ev["tgt"]
    assert (tgt._nano.topology, tgt._nano.routing_mask, tgt._nano.start_flag) == (*PROG_CONFIGS[2], True)
    assert grid.cells[(0, 0)].freeze_in is True, "the program store ends halted"
    assert all(c.ram_data_valid for c in ev["out_cells"])
    assert [c.ram_data_reg for c in ev["out_cells"]] == list(reversed(PASSES_A[0] + PASSES_A[1]))


def test_control_without_the_source_gate_items_race_ahead_of_the_initial_programming():
    """Negative control: neutralise CTL2 (a toggle pattern that never matches) and
    release the source at power-on. The first pass then enters the section BEFORE
    the initial programming has completed -- the exact hazard the gate exists for."""
    grid, pl = _build(PASSES_A[0], gated=False)
    ev = _run(grid, pl, PASSES_A, cap=40)
    first_exit = next(t for (t, _s, n) in ev["rows"] if n > 0)
    assert first_exit < ev["refreeze_H"][0], \
        "ungated: an item has already left the section before program 0 finished"
