"""tests/vm/test_mixed_grid_checkpoint_v2.py -- ledger #1036 addendum 60: a whole-grid checkpoint (cells + the grid's in-flight words), checked on the CORDIC in both VM modes.
  1. cut the run at every tick (with TWO items in flight), save to a file, reload into a fresh grid: from that tick on, EVERY cell's state and the grid's pending words equal the
     uninterrupted run's, tick by tick for 40 ticks (a stronger check than the final answer).
  2. the v1 file (cells only) fails the same check at every cut where words are in flight (the finding of addendum 59).
  3. tampering with the saved pending words is caught by the hash; a v1 file is refused; a grid of the other class is refused."""
import copy
import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for p in (os.path.join(ROOT, "nano"), os.path.join(ROOT, "nano", "examples"), os.path.join(ROOT, "tools")):
    sys.path.insert(0, p)
from hierarchical_icm_prototype_loader import load_hierarchical, flatten  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
import cordic_baseline_v1 as cb  # noqa: E402
import mixed_grid_checkpoint_v1 as v1  # noqa: E402
import mixed_grid_checkpoint_v2 as v2  # noqa: E402

RECORDS, _ = flatten(load_hierarchical(cb.ICM))
IC = next(x for x in RECORDS if x.io_name == "z_input")
MODES = (("SuperGrid", vm.SuperGrid, 6), ("FlexGrid", fg.FlexGrid, 20))


def state(g):
    return ({pos: c.checkpoint() for pos, c in g.cells.items()}, copy.deepcopy(g._pending), g.tick_count)


def start(cls, settle):
    g = cls(RECORDS)
    for _ in range(settle):
        g.tick()
    g.inject(IC.row, IC.col, 50000)
    return g


def second_item(g, t):
    if t == 5:
        g.inject(IC.row, IC.col, (-123456) & 0xFFFFFFFF)


@pytest.fixture(scope="module")
def tmp():
    d = tempfile.mkdtemp(prefix="ck2_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def reference(cls, settle, total=60):
    g = start(cls, settle)
    trace = []
    for t in range(total):
        second_item(g, t)
        g.tick()
        trace.append(state(g))
    return trace


@pytest.mark.parametrize("name,cls,settle", MODES)
def test_every_cut_resumes_identically(tmp, name, cls, settle):
    ref = reference(cls, settle)
    checked = in_flight = 0
    for cut in range(0, 21):
        g = start(cls, settle)
        for t in range(cut):
            second_item(g, t)
            g.tick()
        in_flight += bool(g._pending)
        path = os.path.join(tmp, f"{name}_{cut}.json")
        v2.save_grid(g, path, name="cordic cut")
        del g
        g2 = cls(RECORDS)
        v2.restore_into(g2, path)
        for t in range(cut, cut + 40):
            second_item(g2, t)
            g2.tick()
            assert state(g2) == ref[t], (name, cut, t)
        checked += 1
    assert checked == 21 and in_flight >= 15       # most cuts really had words in flight between cells


@pytest.mark.parametrize("name,cls,settle", MODES)
def test_v1_cells_only_fails_where_words_are_in_flight(tmp, name, cls, settle):
    ref = reference(cls, settle)
    failed = tested = 0
    for cut in range(0, 21):
        g = start(cls, settle)
        for t in range(cut):
            second_item(g, t)
            g.tick()
        if not g._pending:
            continue
        tested += 1
        path = os.path.join(tmp, f"v1_{name}_{cut}.json")
        v1.save_mixed_model(dict(g.cells), path)
        cells, w, m, tc = v1.load_mixed_model(path), g.width, g.mask, g.tick_count
        g2 = cls(RECORDS)
        for k, c in cells.items():
            c.width, c.mask = w, m
            g2.cells[k] = c
        g2.tick_count = tc                          # everything v1 saved, nothing the grid held
        ok = True
        for t in range(cut, cut + 40):
            second_item(g2, t)
            g2.tick()
            ok &= (state(g2) == ref[t])
        failed += (not ok)
    assert tested >= 15 and failed == tested


def test_tamper_wrong_format_and_wrong_class_are_refused(tmp):
    g = start(vm.SuperGrid, 6)
    for _ in range(3):
        g.tick()
    assert g._pending
    path = os.path.join(tmp, "t.json")
    v2.save_grid(g, path)
    raw = json.load(open(path))
    raw["grid"]["pending"][0][2][0][3] += 1                       # change one in-flight word
    bad = os.path.join(tmp, "bad.json")
    json.dump(raw, open(bad, "w"))
    with pytest.raises(ValueError, match="hash mismatch"):
        v2.load_grid(bad)
    v1path = os.path.join(tmp, "v1.json")
    v1.save_mixed_model(dict(g.cells), v1path)
    with pytest.raises(ValueError, match="not a mixed-grid-checkpoint-v2"):
        v2.load_grid(v1path)
    with pytest.raises(ValueError, match="not a FlexGrid"):
        v2.restore_into(fg.FlexGrid(RECORDS), path)
