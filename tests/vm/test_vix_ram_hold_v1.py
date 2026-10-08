"""tests/vm/test_vix_ram_hold_v1.py -- ledger #1035: the VIX / super-cell ram (SuperGrid, the std VM) absorbs the flex ram's HOLD behaviour WITHOUT a new config bit: a FIXED ram that has an upstream face is a HOLD ram
(the rule the flex generator already uses). It offers its stored word again and again (never used up), any word arriving REPLACES the stored one, and it offers nothing until a word has been written (or preloaded).
A fixed ram with NO upstream is still the plain constant, and a flowing ram is unchanged (the existing ram tests cover those)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def design(preload=None, fixed_up=("w",)):
    cfg = {"upstream_mask": list(fixed_up), "downstream_mask": ["e"], "fixed_mode": 1}
    if preload is not None:
        cfg.update({"load_data_valid": 1, "init_data": preload})
    return [v3.IcmV3Record(cell_id="W", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            v3.IcmV3Record(cell_id="H", row=1, col=1, core="ram", core_config=cfg),
            v3.IcmV3Record(cell_id="O", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]


def run(records, writes, ticks=60):
    """writes: {tick: value} injected into W. Returns the words the sink O received, in order (O is emptied after every tick)."""
    g = SuperGrid(records)
    o, seen = g.cells[(1, 2)], []
    for t in range(ticks):
        if t in writes:
            g.inject(1, 0, writes[t])
        g.tick()
        if o.ram_data_valid:
            seen.append(o.ram_data_reg)
            o.ram_data_valid = False
    return seen


def test_hold_offers_nothing_until_written_then_the_same_word_again_and_again():
    seen = run(design(), {20: 7})
    assert seen and set(seen) == {7} and len(seen) >= 5          # re-offered, never used up
    assert run(design(), {}) == []                                # empty until a word is written


def test_a_later_write_replaces_the_held_word():
    seen = run(design(), {10: 7, 40: 100}, ticks=90)
    assert seen[0] == 7 and seen[-1] == 100 and set(seen) == {7, 100}
    first100 = seen.index(100)
    assert all(x == 7 for x in seen[:first100]) and all(x == 100 for x in seen[first100:])      # one clean switch


def test_hold_with_a_starting_value_offers_it_at_once():
    seen = run(design(preload=5), {})
    assert seen and set(seen) == {5}
    seen = run(design(preload=5), {25: 9}, ticks=80)
    assert seen[0] == 5 and seen[-1] == 9


def test_fixed_without_an_upstream_is_still_the_plain_constant_and_refuses_writes():
    recs = design(preload=5, fixed_up=())
    seen = run(recs, {10: 99})
    assert seen and set(seen) == {5}                             # the write is not taken: a constant is a constant
