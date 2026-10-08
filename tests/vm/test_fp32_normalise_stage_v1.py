"""tests/vm/test_fp32_normalise_stage_v1.py -- ledger #984: ONE conditional-shift stage built from real flex cells, with no loop and no data-dependent routing.

    out = (v << s)  if v < 2^(24-s)  else  v          (a left-normalise step for a 24-bit significand held in a 32-bit word)

How (every cell exists today): the comparator gives r = (v >= 2^(24-s)) as a 0/1 word; the factor F = (r + 2^s) - (r << s) is 2^s when r = 0 and 1 when r = 1 (an adder, a shift add-on relay and a
subtracting adder); the multiplier's low word v * F is the result. A multiplier IS a shifter by a power of two, so the SHIFT AMOUNT comes from data without any routing -- both operands of
every cell arrive on every round, so item order can never be disturbed by two paths of different length (a branch-and-merge version could reorder items under back-pressure). r is also
delivered to its own exit: it is the stage's bit of the shift COUNT.
Run in the real generated RTL (iverilog; plain and random stalls) and in FlexGrid against the Python expression. Requires iverilog.
"""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from fp32_stage_builder_v1 import Grid  # noqa: E402

M32 = 0xFFFFFFFF


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32stage_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def stage(s):
    g = Grid()
    g.add("V", 3, 2)                                                              # the value (entry), fans out to the comparator and the multiplier
    g.add("CMP", 2, 2, "comparator", {"threshold": 1 << (24 - s)})                # r = v >= 2^(24-s)
    g.add("RX", 2, 1)                                                             # exit: r (this stage's bit of the shift count)
    g.add("K", 1, 1, preload=1 << s)                                              # the constant 2^s
    g.add("AD", 1, 2, "adder")                                                    # r + 2^s
    g.add("SUBF", 1, 3, "adder", {"subtract_mode": 1})                            # (r + 2^s) - (r << s)  = F
    g.add("RS", 2, 3, addon={"shift_en": 1, "direction": 0, "shift_amt": {1: 1, 2: 2, 4: 4, 8: 8, 16: 16}[s]})   # r << s (the add-on acts on the relay's offer)
    g.add("R1", 2, 4)
    g.add("R2", 1, 4)
    g.add("MUL", 0, 3, "mul")
    g.add("OUT", 0, 4)
    for a, b in (("V", "CMP"), ("CMP", "RX"), ("CMP", "AD"), ("K", "AD"), ("AD", "SUBF"), ("CMP", "RS"), ("RS", "R1"), ("R1", "R2"), ("R2", "SUBF"), ("SUBF", "MUL"), ("MUL", "OUT")):
        g.link(a, b)
    g.route("V", "MUL")
    return g.records()


def values(s, seed):
    r = random.Random(seed)
    top = 1 << (24 - s)
    v = [0, 1, top - 1, top, top + 1, (1 << 24) - 1, 1 << 23, 5]
    v += [r.randrange(0, top) for _ in range(6)] + [r.randrange(top, 1 << 24) for _ in range(6)]
    return v


def run_vm(recs, vals, const, ticks=300):
    """The VM offers a PRELOADED constant once, but the generated RTL's constant is always valid: so here the constant cell is an ordinary entry that is injected again with every item
    (the same stream of constants the RTL sees)."""
    import copy
    recs = [copy.replace(r, preload_value=None) if r.cell_id in const else r for r in recs] if hasattr(copy, "replace") else [
        type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config, io_name=r.io_name, preload_value=None) if r.cell_id in const else r for r in recs]
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = {"OUT": [], "RX": []}
    for v in vals:
        g.inject(*pos["V"], v)
        for k, kv in const.items():
            g.inject(*pos[k], kv)
        for _ in range(ticks):
            g.tick()
            for e in seen:
                c = g.cells[pos[e]]
                if c.ram_data_valid:
                    seen[e].append(c.ram_data_reg)
                    c.ram_data_valid = False
    return seen


@pytest.mark.parametrize("s", [16, 8, 4, 2, 1])
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_conditional_shift_stage_in_rtl_and_vm(tmp, s, mode):
    recs = stage(s)
    vals = values(s, s)
    d, r = h.build(tmp, f"stage{s}_{mode}", recs)
    assert r.returncode == 0, r.stderr[:800]
    _, got = h.run_level(d, {"V": vals}, mode, 9, settle=800)
    top = 1 << (24 - s)
    assert got["OUT"] == [((v << s) if v < top else v) & M32 for v in vals]
    assert got["RX"] == [0 if v < top else 1 for v in vals]
    assert any(v < top for v in vals) and any(v >= top for v in vals)
    assert run_vm(recs, vals, {"K": 1 << s}) == {"OUT": got["OUT"], "RX": got["RX"]}
