"""
test_stage_pipeline_vs_fold_v1.py -- points.md #885: the MEASURED comparison Alan asked
for. The same 4-stage function over the same 8 items, built two ways, both checked
against a Python reference:

  STATIC : four `nano` op-cells in series, each holding the constant K as operand A
           and taking the item as operand B, each with its own topology. A stage
           pipeline: once full it yields a result every 2 ticks whatever its depth.
  FOLD   : ONE `nano` reprogrammed between four passes by the grid-native loop of
           #879/#880, its outputs written back as the next pass's inputs (the
           iterative use the fold exists for -- #880 processed different items).

The function is XOR -> NAND -> AND -> XNOR with K = 0x9C3E5A17. It was CHOSEN by
search, not assumed: four different gates (so every pass boundary is a genuine
reconfiguration), 8 distinct outputs, ~99% information-preserving over random inputs,
every stage needed, order-sensitive. My first attempt (XOR, AND, OR, XNOR) produced
0xFFFFFFFF for every item -- AND-then-OR collapses to K -- and could not have caught a
mixed-up item or a wrong stage.

WRITEBACK is a real port, not forced state: the tail feeds a sink that acknowledges and
discards, and the loader reads each result as it arrives. My first loader cleared the
output chain by forcing `valid` to 0; that left stale pending acks which re-fired and
corrupted the chain. Forcing a cell's state from outside interferes with the grid's own
bookkeeping, so the harness does not do it.

REAL, HONEST SCOPE: VM only; ticks are protocol rounds, not clock cycles. The loader
(a BRAM stand-in) is a harness step. The static pipeline's storage cells are only a
modelling artifact (a BRAM in reality), so the comparison is on MACHINERY cells, with
storage reported separately. 8 items per pass is small: the fold's boundary overhead
amortises with larger passes (#883), but its serial structure means it can never beat
the static pipeline on time -- see the structural test.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))
sys.path.insert(0, os.path.dirname(__file__))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402
from unicell_gate_core import TOPO_XOR, TOPO_AND, TOPO_XNOR, TOPO_NAND, compute_gate  # noqa: E402
import test_fold_v1 as F  # noqa: E402

K = 0x9C3E5A17
STAGES = [TOPO_XOR, TOPO_NAND, TOPO_AND, TOPO_XNOR]
ITEMS = [0x12345678, 0xDEADBEEF, 0x00000002, 0xCAFEF00D, 0x0F0F0F0F, 0xFFFFFFFF, 0x00000000, 0x87654321]
M32 = 0xFFFFFFFF
N_ITEMS, N_STAGES = len(ITEMS), len(STAGES)


def _ref(x, stages=STAGES, upto=None):
    for t in (stages if upto is None else stages[:upto]):
        x = compute_gate(t, K, x) & M32
    return x


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


# ------------------------------------------------------------------ static
def _run_static(stages=STAGES, items=ITEMS):
    n_st, n = len(stages), len(items)
    C = []
    for i, t in enumerate(stages):
        C.append(_rec(f"F{i}", i, 0, "nano", {"topology": t, "ready": 1, "hold_in": 1, "routing_mask": ["s"]}))
        C.append(_rec(f"K{i}", i, -1, "ram", {"init_data": K, "load_data_valid": 1, "downstream_mask": ["e"]}))
    for i, v in enumerate(items):
        C.append(_rec(f"S{i}", -1 - i, 0, "ram", {"init_data": v, "load_data_valid": 1,
                                                  "upstream_mask": [] if i == n - 1 else ["n"], "downstream_mask": ["s"]}))
    for j in range(n):
        C.append(_rec(f"O{j}", n_st + j, 0, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"] if j < n - 1 else []}))
    g = VixCarrierGrid(C)
    g.cells[(-1, 0)].freeze_in = True                       # let every constant land alone first
    arrivals, prev, release = [], 0, 6
    for t in range(300):
        if t == release:
            g.cells[(-1, 0)].freeze_in = False
        g.tick()
        c = sum(int(g.cells[(n_st + j, 0)].ram_data_valid) for j in range(n))
        arrivals += [t] * (c - prev) if c > prev else []
        prev = c
    out = [g.cells[(n_st + j, 0)].ram_data_reg for j in reversed(range(n))]
    return {"out": out, "cells": len(g.cells), "machinery": 2 * n_st, "first": arrivals[0] - release,
            "total": arrivals[-1] - release, "gaps": sorted({b - a for a, b in zip(arrivals, arrivals[1:])})}


# -------------------------------------------------------------------- fold
def _is_storage(cid):
    return (cid[0] in "SO" and cid[1:].isdigit()) or cid == "SINK"


def _run_fold(stages=STAGES, items=ITEMS, wait_for_gate=True, cap=1500):
    n, n_st = len(items), len(stages)
    grid = F._build(items[:2], configs=[(t, F.N_MASK) for t in stages], n_out=1, pl=n, k_value=K, sink=True)
    S1, S2, H, pc = grid.cells[(2, 4)], grid.cells[(2, 3)], grid.cells[(0, 0)], grid.cells[(-1, -3)]
    sink = grid.cells[(-3, -2)]
    got = []
    orig = sink.deliver

    def tap(arrivals, injected=None, **kw):
        res = orig(arrivals, injected=injected, **kw)
        if res[0] and arrivals:
            got.append(list(arrivals.values())[0])
        return res
    sink.deliver = tap

    def load(c, v):
        c.program_in = True
        c.program_word(3, v & 0xFFFF)
        c.program_word(4, (v >> 16) & 0xFFFF)
        c.program_word(6, 1)
        c.program_in = False

    pending, passes = list(items[2:]), []
    ev = {"pulses": [], "unfreeze": [], "refreeze": [], "release": []}
    ph, ps, pp = H.freeze_in, S1.freeze_in, pc.acc_pulse_pending
    t_first = t_done = None
    for t in range(cap):
        grid.tick()
        if pending and not S2.ram_data_valid:
            load(S2, pending.pop(0))
        if len(got) == n and len(passes) == n_st - 1:
            passes.append(list(got))
            got.clear()
            t_done = t
            break
        gate_ok = (S1.freeze_in and not S1.ram_data_valid and not S2.ram_data_valid and not pending) if wait_for_gate \
            else (not pending)
        if len(got) == n and gate_ok:
            passes.append(list(got))
            got.clear()
            nxt = passes[-1]
            load(S1, nxt[0])
            load(S2, nxt[1])
            pending = nxt[2:]
        if ph and not H.freeze_in:
            ev["unfreeze"].append(t)
        if not ph and H.freeze_in:
            ev["refreeze"].append(t)
        if ps and not S1.freeze_in:
            ev["release"].append(t)
            t_first = t if t_first is None else t_first
        if not pp and pc.acc_pulse_pending:
            ev["pulses"].append(t)
        ph, ps, pp = H.freeze_in, S1.freeze_in, pc.acc_pulse_pending
    cells = len(grid.cells)
    storage = sum(1 for c in grid.cells.values() if _is_storage(c.cell_id))
    return {"passes": passes, "ev": ev, "t_first": t_first, "t_done": t_done, "cells": cells,
            "machinery": cells - storage, "storage": storage,
            "total": None if t_done is None else t_done - t_first}


# ------------------------------------------------------------------- tests
def test_the_static_pipeline_computes_the_reference_at_two_ticks_per_item():
    r = _run_static()
    assert r["out"] == [_ref(x) for x in ITEMS], "every item through all four stages"
    assert r["gaps"] == [2], "a steady 2.0 ticks per item"
    assert r["machinery"] == 8 and r["cells"] == 24


def test_the_fold_computes_the_same_function_and_is_correct_after_every_pass():
    r = _run_fold()
    assert len(r["passes"]) == N_STAGES
    for k, out in enumerate(r["passes"], start=1):
        assert out == [_ref(x, upto=k) for x in ITEMS], f"after pass {k} every item has had exactly {k} stage(s)"
    assert len(r["ev"]["refreeze"]) == N_STAGES and len(r["ev"]["pulses"]) == N_STAGES, \
        "four programs, four drain pulses"


def test_both_designs_produce_identical_final_values():
    s, f = _run_static(), _run_fold()
    assert s["out"] == f["passes"][-1] == [_ref(x) for x in ITEMS]


def test_static_is_much_faster_and_the_fold_can_never_beat_it():
    s, f = _run_static(), _run_fold()
    ratio = f["total"] / s["total"]
    assert ratio >= 8, f"measured ~10.7x slower at 8 items per pass (got {ratio:.1f}x)"
    assert f["total"] > N_STAGES * s["total"], \
        "structurally: the fold runs every stage serially on one datapath, so it is more than N_STAGES times slower"


def test_static_needs_far_fewer_machinery_cells():
    s, f = _run_static(), _run_fold()
    assert f["machinery"] >= 6 * s["machinery"], \
        f"fold {f['machinery']} vs static {s['machinery']} machinery cells (measured 56 vs 8)"


def test_the_fold_time_is_dominated_by_the_pass_boundary_not_the_work():
    f = _run_fold()
    period = f["ev"]["pulses"][1] - f["ev"]["pulses"][0]                 # one full pass, drain to drain
    useful = 2 * N_ITEMS                                                 # 8 items at the measured 2 ticks each
    assert period >= 3 * useful, f"a {period}-tick pass carries only {useful} ticks of useful work"


def test_the_marginal_cost_of_a_stage_the_fold_store_costs_more_than_a_static_stage():
    """Each extra stage adds 3 cells to the fold's serial program store (topology, mask,
    COMPLETE words) but only 2 to a static pipeline (an op-cell and its constant). So as
    built the fold never wins on CELLS however many stages there are; only a compact
    program store (BRAM, or a sequencer holding several words per cell, #873/#874) would
    change that. Derived from counting cells at 3 and 4 stages."""
    fold3 = len(F._build(ITEMS[:2], configs=[(t, F.N_MASK) for t in STAGES[:3]], n_out=1, pl=N_ITEMS, k_value=K, sink=True).cells)
    fold4 = len(F._build(ITEMS[:2], configs=[(t, F.N_MASK) for t in STAGES], n_out=1, pl=N_ITEMS, k_value=K, sink=True).cells)
    st3, st4 = _run_static(STAGES[:3])["cells"], _run_static(STAGES)["cells"]
    assert fold4 - fold3 == 3, "3 program-store cells per extra stage"
    assert st4 - st3 == 2, "2 cells per extra static stage"
    assert fold4 - fold3 > st4 - st3


def test_control_staging_the_next_pass_before_the_gate_freezes_splits_a_pass_across_two_configurations():
    """The loader-before-gate mistake I made, kept as a control: stage the next pass as soon
    as the last result is back. The source is not yet frozen, so pass 2 starts flowing under
    the OLD configuration; the reprogram then lands MID-PASS (the fold cell is frozen while
    items are in flight). Observed: the first 7 items were processed by stage 1 (XOR) AGAIN,
    which cancels back to the original value, and only the 8th got the new stage (NAND). I
    first predicted 'all 8 under the old configuration'; the truth is worse -- one pass split
    between two functions -- with wrong answers and no error anywhere."""
    f = _run_fold(wait_for_gate=False)
    assert f["passes"][0] == [_ref(x, upto=1) for x in ITEMS], "pass 1 is unaffected"
    correct2 = [_ref(x, upto=2) for x in ITEMS]
    assert f["passes"][1] != correct2, "pass 2 is wrong"
    assert f["passes"][1][:7] == [_ref(_ref(x, upto=1), upto=1) for x in ITEMS][:7], \
        "items 0-6 had stage 1 applied a SECOND time (XOR twice = the original value)"
    assert f["passes"][1][7] == correct2[7], "and item 7 alone got the reprogrammed stage"
