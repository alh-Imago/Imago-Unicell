"""tests/vm/test_flex_grid_v1.py -- FlexGrid, step 1: the skeleton must be INDISTINGUISHABLE from SuperGrid (ledger #965).

Before any flex behaviour is added, FlexGrid (FlexCell + an empty flex handler table) has to behave exactly like the std VM. Proved by a differential run: the same ICM, the same
injections, both grids, and the COMPLETE observable state of every cell compared after every tick (every attribute, not just outputs). Also: the handler hook really is consulted
(a registered flex handler takes over; the std registry is untouched), duplicates are refused, and a width passes through.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_grid_v1 as fg  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402
from icm_vix_v1 import IcmVixFile  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples")


def snapshot(grid):
    """Everything observable: every attribute of every cell (and of a delegated nano), the pending queue, the tick counter."""
    out = {"tick": grid.tick_count, "pending": repr(sorted(grid._pending.items(), key=repr))}
    for pos, c in sorted(grid.cells.items()):
        d = {k: v for k, v in vars(c).items() if k not in ("_nano", "merge_mode", "_merge_order", "_merge_rr", "adder_carry_mode", "adder_captured_carry", "adder_delivering_carry")}   # the flex-only merge and adder-carry bookkeeping is not behaviour while the flex table is empty
        if getattr(c, "_nano", None) is not None:
            d["_nano"] = {k: v for k, v in vars(c._nano).items()}
        out[pos] = repr(sorted(d.items(), key=lambda kv: kv[0]))
    return out


def ram(cid, r, c, up, down, **cfg):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down, **cfg})


def drive(records, injections, ticks, make):
    g = make(records)
    snaps = []
    for t in range(ticks):
        for at, (row, col, value) in injections:
            if at == t:
                g.inject(row, col, value)
        g.tick()
        snaps.append(snapshot(g))
    return snaps


def hand_designs():
    chain = [ram("A", 0, 0, [], ["e"]), ram("B", 0, 1, ["w"], ["e"]), ram("C", 0, 2, ["w"], [])]
    pair = [ram("X", 0, 0, [], ["e"]), ram("Y", 1, 1, [], ["n"]),
            IcmV3Record(cell_id="ADD", row=0, col=1, core="adder", core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"]}), ram("E", 0, 2, ["w"], [])]
    mul = [ram("X", 0, 0, [], ["e"]), ram("Y", 1, 1, [], ["n"]),
           IcmV3Record(cell_id="M", row=0, col=1, core="mul", core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"]}), ram("E", 0, 2, ["w"], [])]
    cmpd = [ram("X", 0, 0, [], ["e"]), IcmV3Record(cell_id="C", row=0, col=1, core="comparator", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": 5}), ram("E", 0, 2, ["w"], [])]
    return {"relay chain": (chain, [(3, (0, 0, 7)), (9, (0, 0, 8))]),
            "adder": (pair, [(3, (0, 0, 40)), (12, (1, 1, 2))]),
            "multiplier": (mul, [(3, (0, 0, 6)), (12, (1, 1, 7))]),
            "comparator": (cmpd, [(3, (0, 0, 9)), (10, (0, 0, 1))])}


@pytest.fixture
def empty_flex_table(monkeypatch):
    """The skeleton proof (step 1) needs the flex handler table EMPTY: since #968+ the table holds the real flex relay/merge, so tests that prove 'FlexGrid with nothing flex-specific == SuperGrid' clear it."""
    monkeypatch.setattr(fg, "_FLEX_HANDLERS", {})


def test_flex_cell_and_grid_are_real_subclasses():
    assert issubclass(fg.FlexCell, vm.SuperCell) and issubclass(fg.FlexGrid, vm.SuperGrid)
    g = fg.FlexGrid([ram("A", 0, 0, [], [])])
    assert all(type(c) is fg.FlexCell for c in g.cells.values()) and g.family == "flex"


@pytest.mark.parametrize("name", list(hand_designs()))
def test_empty_flexgrid_equals_supergrid_on_hand_built_designs(name, empty_flex_table):
    records, inj = hand_designs()[name]
    a = drive(records, inj, 40, vm.SuperGrid)
    b = drive(records, inj, 40, fg.FlexGrid)
    assert a == b


@pytest.mark.parametrize("example", ["small_relay_chain", "parallel_reduction_tree", "cordic_z_convergence"])
def test_empty_flexgrid_equals_supergrid_on_the_example_designs(example, empty_flex_table):
    x = IcmVixFile.load(os.path.join(EX, example + ".icm-hier.json"))
    records, _ = x.flatten()
    entries = [r for r in records if r.io_name and not r.core_config.get("upstream_mask")] or records[:1]
    inj = [(3 + 5 * k, (r.row, r.col, 3 + k)) for k, r in enumerate(entries[:4])]
    a = drive(records, inj, 120, vm.SuperGrid)
    b = drive(records, inj, 120, fg.FlexGrid)
    assert a == b


def test_width_passes_through_the_flex_grid(empty_flex_table):
    records, inj = hand_designs()["adder"]
    a = drive(records, inj, 40, lambda r: vm.SuperGrid(r, width=18))
    b = drive(records, inj, 40, lambda r: fg.FlexGrid(r, width=18))
    assert a == b and fg.FlexGrid(records, width=18).width == 18


def test_a_registered_flex_handler_takes_over_and_the_std_registry_is_untouched(empty_flex_table):
    std_before = dict(vm._CORE_HANDLERS)
    marker = []
    def deliver(cell, arrivals, injected):
        marker.append(cell.core)
        return (False, None)
    handler = vm.CoreHandler(deliver=deliver, offer_state=vm._CORE_HANDLERS["ram"].offer_state)   # a handler needs an offer_state too; borrow the std one
    fg.register_flex_handler("ram", handler)
    try:
        records, inj = hand_designs()["relay chain"]
        std = vm.SuperGrid(records)
        flex = fg.FlexGrid(records)
        for g in (std, flex):
            g.inject(0, 0, 7)
            for _ in range(6):
                g.tick()
        assert marker, "the flex handler was never consulted"
        assert vm._CORE_HANDLERS == std_before                        # the std registry is untouched
        assert std.cells[(0, 2)].ram_data_valid and std.cells[(0, 2)].ram_data_reg == 7        # std: the value travelled to the last cell
        assert not flex.cells[(0, 2)].ram_data_valid                                           # flex: its handler refused every delivery, so nothing moved
        with pytest.raises(ValueError, match="already registered"):
            fg.register_flex_handler("ram", handler)
    finally:
        fg._FLEX_HANDLERS.pop("ram", None)
