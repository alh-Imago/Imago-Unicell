"""
test_fold_v1.py -- points.md #880: THE ACTUAL FOLD. The cell that the loop
reprograms is now a cell IN the data path, so each pass is genuinely processed by
the configuration loaded for it. Until now (#862..#879) the reprogrammed unit was a
separate target the items never touched, so the loop proved scheduling only.

The fold cell F is a `nano` in a 3-cell section (entry E0 -> F -> tail T). It holds
a constant K as operand A (`hold_in`) and each streamed item arrives as operand B,
so it computes f(K, item) where f is whatever topology the loop last programmed:
pass 1 runs under AND, pass 2 under XOR, the final program leaves OR. The topology
must be one where B matters (AND/OR/XOR); NOT_A would ignore the item entirely.

Three facts about the fold cell, each found by running it (not assumed):
  * A nano that has not been STARTED is effectively frozen and refuses EVERY
    arrival, including its constant. So K cannot be pre-loaded: it can only be
    captured AFTER the first program arms the cell (`start_flag`). K waits, offering
    each tick, and is taken the tick after arming.
  * K must arrive ALONE. The nano's first arrival becomes A and every later arrival
    becomes B; simultaneous arrivals OR-combine into one operand. The long transport
    line (source -> F) is what guarantees K lands first, with a wide margin.
  * With `hold_in`, A survives both firing and reprogramming: it stayed K throughout.

Layout: the reprogrammed cell must touch the programmer-mode command cell, which
touches the program store, so the fold cluster sits at the west end and the source
and drain lines run long relay paths across. That is placement doing real work as
delay AND buffer (#877): the transport line gives K its head start, the pulse path
carries the drain signal home. It costs time (~105 ticks for two passes).

REAL, HONEST SCOPE:
  * VM only. The LOADER is still a harness step (BRAM stand-in). One fold cell,
    three topologies, two passes -- not N passes, not several fold cells.
  * `hold_in` (like the per-pass start nano's `a_reemit_in`) is a nano "extra" that
    the carrier's first RTL build ties to inactive defaults (root_definition.json),
    so the fold needs standalone nano_gate_v4 or a carrier extension before RTL.
  * The function is deliberately simple (a masked AND/XOR/OR). A real fold -- e.g.
    fp32 ADD's alignment and rounding stages -- would reprogram several cells and
    fields per pass; this proves the MECHANISM, not that workload.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402
from unicell_automaton_v1 import PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE  # noqa: E402
from unicell_gate_core import TOPO_AND, TOPO_XOR, TOPO_OR, TOPO_PASS_A  # noqa: E402

TOGGLE = (PROG_ID_COMPLETE << 20) | 1
N_MASK = 0b0001                          # F routes north, into the tail
K = 0x0000FFFF
CONFIGS = [(TOPO_AND, N_MASK), (TOPO_XOR, N_MASK), (TOPO_OR, N_MASK)]
PASS1 = [0x12345678, 0xDEADBEEF]         # index 0 enters first
PASS2 = [0x00000002, 0xCAFEF00D]         # includes an even value and a value with high bits set
PASS1_B = [0xFFFFFFFF, 0x00010001]
PASS2_B = [0x0000F0F0, 0x87654321]
PL = 2


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _words(t, m):
    return [(PROG_ID_TOPOLOGY << 20) | t, (PROG_ID_ROUTING_MASK << 20) | m, TOGGLE]


def _expected(p1, p2):
    return [p1[0] & K, p1[1] & K, p2[0] ^ K, p2[1] ^ K]


def _build(src_items, configs=CONFIGS, gated=True, n_out=4, pl=PL, k_value=K, sink=False):
    seq = [w for (t, m) in configs for w in _words(t, m)]
    n = len(seq)
    top = -(n - 1)
    C = []
    for i, w in enumerate(reversed(seq)):                       # program store, column 0; head H at row 0
        r = top + i
        C.append(_rec(f"w{r}", r, 0, "ram", {
            "init_data": w, "load_data_valid": 1,
            "upstream_mask": [] if r == top else ["n"],
            "downstream_mask": ["w", "e", "s"] if r == 0 else ["s"]}))
    C += [
        _rec("CMD1", 0, -1, "command", {"mode": 1, "polarity": 0, "drive_dir": 3, "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("F", 0, -2, "nano", {"topology": 0, "ready": 0, "hold_in": 1, "routing_mask": 0}),   # THE FOLD CELL
        _rec("K", 0, -3, "ram", {"init_data": k_value, "load_data_valid": 1, "downstream_mask": ["e"]}),  # its constant
        _rec("CTL", 0, 1, "command", {"mode": 0, "polarity": 0, "drive_dir": 3, "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("MS", 0, 2, "ram", {"upstream_mask": ["n", "e"], "downstream_mask": ["w"]}),
        _rec("Q", -1, 2, "ram", {"init_data": TOGGLE, "load_data_valid": 1, "downstream_mask": ["s"]}),
        _rec("Npass", 0, 3, "nano", {"topology": TOPO_PASS_A, "ready": 1, "hold_in": 1, "a_reemit_in": 1,
                                     "routing_mask": ["w", "s"]}),
        _rec("Ppass", -1, 3, "ram", {"init_data": TOGGLE, "load_data_valid": 1, "downstream_mask": ["s"]}),
        _rec("c1", 1, 0, "ram", {"upstream_mask": ["n"], "downstream_mask": ["e"]}),
        _rec("c2", 1, 1, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("c3", 1, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("MS2", 1, 3, "ram", {"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}),
        _rec("CTL2", 1, 4, "command", {"mode": 0, "polarity": 0, "drive_dir": 1,
                                       "toggle_pattern": PROG_ID_COMPLETE if gated else 14}),
    ]
    ns = len(src_items)
    for i, v in enumerate(src_items):                           # source chain along row 2; S1 (2,4) speaks first
        C.append(_rec(f"S{i + 1}", 2, 4 - i, "ram", {
            "init_data": v, "load_data_valid": 1,
            "upstream_mask": [] if i == ns - 1 else ["w"], "downstream_mask": ["s"] if i == 0 else ["e"]}))
    # transport line: S1 -> west along row 3 -> north up column -2 -> entry cell E0 -> F
    C.append(_rec("L0", 3, 4, "ram", {"upstream_mask": ["n"], "downstream_mask": ["w"]}))
    for c in range(3, -2, -1):
        C.append(_rec(f"L{4 - c}", 3, c, "ram", {"upstream_mask": ["e"], "downstream_mask": ["w"]}))
    C += [_rec("Lturn", 3, -2, "ram", {"upstream_mask": ["e"], "downstream_mask": ["n"]}),
          _rec("Lup", 2, -2, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}),
          _rec("E0", 1, -2, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}),
          _rec("T", -1, -2, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n", "w"]})]
    for j in range(n_out):
        last = j == n_out - 1
        C.append(_rec(f"O{j + 1}", -2 - j, -2, "ram", {
            "upstream_mask": ["s"], "downstream_mask": ["n"] if (not last or sink) else []}))
    if sink:                                   # a consumer that acknowledges and discards: a real writeback port, no forced state
        C.append(_rec("SINK", -2 - n_out, -2, "accumulator", {"inc_dir": ["s"], "step_amount": 0}))
    C.append(_rec("pc", -1, -3, "accumulator", {"inc_dir": ["e"], "step_amount": 1, "pulse_mode": 1,
                                                "threshold": pl, "downstream_mask": ["w"]}))
    # drain pulse path: pc -> west -> down column -4 -> east along row 4 -> up column 5 -> Npass
    C.append(_rec("p0", -1, -4, "ram", {"upstream_mask": ["e"], "downstream_mask": ["s"]}))
    for r in range(0, 4):
        C.append(_rec(f"pd{r}", r, -4, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]}))
    C.append(_rec("pturn1", 4, -4, "ram", {"upstream_mask": ["n"], "downstream_mask": ["e"]}))
    for c in range(-3, 5):
        C.append(_rec(f"pe{c}", 4, c, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}))
    C.append(_rec("pturn2", 4, 5, "ram", {"upstream_mask": ["w"], "downstream_mask": ["n"]}))
    for r in (3, 2, 1):
        C.append(_rec(f"pu{r}", r, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]}))
    C.append(_rec("pturn3", 0, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["w"]}))
    C.append(_rec("pfin", 0, 4, "ram", {"upstream_mask": ["e"], "downstream_mask": ["w"]}))
    grid = VixCarrierGrid(C)
    if not gated:
        grid.cells[(2, 4)].freeze_in = False
    return grid


def _run(grid, passes, cap=300):
    H, S1 = grid.cells[(0, 0)], grid.cells[(2, 4)]
    F, cmd1 = grid.cells[(0, -2)], grid.cells[(0, -1)]
    n = F._nano
    src = [grid.cells[(2, 4 - i)] for i in range(PL)]
    out = [grid.cells[(-2 - j, -2)] for j in range(4)]
    ev = {"unfreeze_H": [], "refreeze_H": [], "release_src": [], "loads": [], "pulses": [],
          "a_at_done": [], "topo_at_exit": [], "arm_tick": None, "k_tick": None, "exits_at_k": None,
          "first_exit": None, "rows": []}
    prev_h, prev_s = H.freeze_in, S1.freeze_in
    pc = grid.cells[(-1, -3)]
    prev_p, prev_exits = pc.acc_pulse_pending, 0
    loaded = 1
    for t in range(cap):
        grid.tick()
        if len(passes) > loaded and S1.freeze_in and not any(c.ram_data_valid for c in src):
            for c, v in zip(src, passes[loaded]):               # THE LOADER: the only harness step
                c.program_in = True
                c.program_word(3, v & 0xFFFF)
                c.program_word(4, (v >> 16) & 0xFFFF)
                c.program_word(6, 1)
                c.program_in = False
            ev["loads"].append(t)
            loaded += 1
        exits = sum(int(c.ram_data_valid) for c in out)
        if prev_h and not H.freeze_in:
            ev["unfreeze_H"].append(t)
        if not prev_h and H.freeze_in:
            ev["refreeze_H"].append(t)
            ev["a_at_done"].append(n.a_data if n.a_arrived else None)
        if prev_s and not S1.freeze_in:
            ev["release_src"].append(t)
        if not prev_p and pc.acc_pulse_pending:
            ev["pulses"].append(t)
        if ev["arm_tick"] is None and n.start_flag:
            ev["arm_tick"] = t
        if ev["k_tick"] is None and n.a_arrived:
            ev["k_tick"], ev["exits_at_k"] = t, exits
        if exits > prev_exits:
            ev["topo_at_exit"].append(n.topology)
            if ev["first_exit"] is None:
                ev["first_exit"] = t
        prev_h, prev_s, prev_p, prev_exits = H.freeze_in, S1.freeze_in, pc.acc_pulse_pending, exits
        ev["rows"].append((t, exits))
    ev["out"] = [c.ram_data_reg for c in reversed(out) if c.ram_data_valid]     # oldest first
    ev["F"] = F
    return ev


def _standard(p1=PASS1, p2=PASS2, configs=CONFIGS):
    grid = _build(p1, configs)
    return _run(grid, [p1, p2])


def test_the_same_cell_computes_a_different_function_each_pass():
    ev = _standard()
    assert ev["out"] == _expected(PASS1, PASS2), "pass 1 under AND, pass 2 under XOR"
    all_and = [x & K for x in PASS1 + PASS2]
    all_xor = [x ^ K for x in PASS1 + PASS2]
    assert ev["out"] != all_and and ev["out"] != all_xor, "and it is neither function alone"


def test_each_item_is_processed_by_the_configuration_loaded_for_it():
    ev = _standard()
    assert ev["topo_at_exit"] == [TOPO_AND, TOPO_AND, TOPO_XOR, TOPO_XOR], \
        "the topology in force as each item left is the one programmed for its pass"


def test_the_constant_lands_alone_after_arming_before_any_item_and_survives_every_reprogram():
    ev = _standard()
    assert ev["arm_tick"] is not None and ev["k_tick"] is not None
    assert ev["k_tick"] > ev["arm_tick"], "K cannot be captured before the first program arms the cell"
    assert ev["k_tick"] - ev["arm_tick"] <= 2, "and it is taken promptly: the tick after arming"
    assert ev["exits_at_k"] == 0 and ev["k_tick"] < ev["first_exit"], "held before any item leaves"
    assert ev["a_at_done"] == [None, K, K], \
        "at the end of program 0 K has not yet landed (it arrives just AFTER arming); it is intact at the end of programs 1 and 2"
    assert ev["F"]._nano.a_data == K


def test_pass_two_cannot_reach_the_cell_before_the_reprogram_completes():
    ev = _standard()
    assert ev["refreeze_H"][1] < ev["release_src"][1], "program 1 completes, THEN the source is released"
    third_exit = [t for (t, n) in ev["rows"] if n >= 3][0]
    assert third_exit > ev["refreeze_H"][1], "no pass-2 item leaves the cell before its program is in place"


def test_each_reprogram_starts_only_after_the_drain_with_every_item_out():
    ev = _standard()
    assert len(ev["pulses"]) == 2 and len(ev["unfreeze_H"]) == 3
    for k in (1, 2):
        assert ev["pulses"][k - 1] < ev["unfreeze_H"][k]
        assert next(n for (t, n) in ev["rows"] if t == ev["unfreeze_H"][k]) == PL * k


def test_the_event_timeline_is_identical_for_different_data_and_only_the_values_differ():
    a = _standard(PASS1, PASS2)
    b = _standard(PASS1_B, PASS2_B)
    for key in ("unfreeze_H", "refreeze_H", "release_src", "loads", "pulses", "rows", "topo_at_exit"):
        assert a[key] == b[key], f"{key}: the scheduling must not depend on the data"
    assert a["out"] == _expected(PASS1, PASS2) and b["out"] == _expected(PASS1_B, PASS2_B)
    assert a["out"] != b["out"]


def test_control_reprogramming_to_the_same_function_gives_the_same_function():
    """Causality: the outputs follow the LOADED CONFIGURATION, not the position in
    the stream. Re-select AND for pass 2 and pass 2 comes out AND'ed."""
    ev = _standard(configs=[(TOPO_AND, N_MASK), (TOPO_AND, N_MASK), (TOPO_OR, N_MASK)])
    assert ev["out"] == [x & K for x in PASS1 + PASS2]
    assert ev["out"] != _expected(PASS1, PASS2)


def test_control_without_the_gate_pass_two_is_silently_processed_by_the_old_configuration():
    """Neutralise the source gate and preload all four items: they flow straight
    through behind pass 1 and pass 2 is computed under AND -- the WRONG function --
    with no error anywhere. (I predicted the constant would be corrupted by an item
    landing on the same tick; it was not -- A stayed K. The real failure is quieter
    and worse: plausible-looking wrong answers.)"""
    grid = _build(PASS1 + PASS2, gated=False)
    ev = _run(grid, [PASS1 + PASS2], cap=300)
    assert ev["out"] == [x & K for x in PASS1 + PASS2], "all four items processed under the initial AND"
    assert ev["out"] != _expected(PASS1, PASS2), "so pass 2 is wrong"
    assert ev["F"]._nano.a_data == K, "the held constant was NOT what went wrong"
