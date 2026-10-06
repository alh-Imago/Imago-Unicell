"""tests/vm/test_flex_grid_second_port_v1.py -- the SECOND OUTPUT PORT end to end (ledger #976): one ICM flag on the cell (adder `carry_mode`, multiplier `wide_mode`), the planner/emitter
building the port (SECOND_PORT=1, enable bit, a merge core in front of the consumer), and FlexGrid delivering the same words in the same order.

X, Y -> M (adder or mul with the flag) -> E (a relay, the design's exit). Each pair of inputs must come out as TWO words at E: the sum then the carry (0/1), or the product's low then high
word. The generated RTL is run in iverilog (plain and with random stalls) and FlexGrid must give the identical sequence. The planner must refuse the cases it does not translate. Requires iverilog.
"""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

ram = h.ram
M32 = 0xFFFFFFFF


def design(core, **cfg):
    mid = IcmV3Record(cell_id="M", row=1, col=1, core=core, core_config=dict({"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}, **cfg))
    # Y reaches M directly (hop 1) and is operand A; X goes through a relay P first (hop 2) and is operand B -- the generator needs different arrival depths to know which is which
    return [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), mid, ram("E", 1, 2, ["w"], [])]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fgsecond_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def rtl_words(tmp, name, recs, streams, mode="plain"):
    d, r = h.build(tmp, name, recs)
    assert r.returncode == 0, r.stderr[:400]
    _, got = h.run_level(d, streams, mode, 7, settle=300)
    return got["E"], d


def vm_words(recs, streams, words_per_item=2, ticks_per_item=80):
    """One item at a time: the VM pairs a two-operand cell's operands by ARRIVAL ORDER (not by face), so a fast stream could get ahead of a slow one. The generated RTL joins them with the
    handshake and is correct in any timing, so the VM is driven item by item (the next pair enters once the previous pair's words have all come out) and compared with it."""
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen, e = [], g.cells[pos["E"]]
    n_items = len(next(iter(streams.values())))
    for k in range(n_items):
        for name, vals in streams.items():
            g.inject(*pos[name], vals[k])
        start = len(seen)
        for _ in range(ticks_per_item):
            g.tick()
            if e.ram_data_valid:
                seen.append(e.ram_data_reg)
                e.ram_data_valid = False
            if len(seen) - start >= words_per_item:
                break
    return seen


def pairs(seed, n=10):
    r = random.Random(seed)
    edge = [(M32, 1), (M32, M32), (0, 0), (1 << 31, 1 << 31), (5, 3), (3, 5), (0x80000000, 0x7FFFFFFF)]
    return edge + [(r.getrandbits(32), r.getrandbits(32)) for _ in range(n)]


def expected(core, a, b, sub=0):
    if core == "mul":
        return [(a * b) & M32, (a * b) >> 32]
    if sub:
        return [(a - b) & M32, 1 if a + ((~b) & M32) + 1 > M32 else 0]
    return [(a + b) & M32, 1 if a + b > M32 else 0]


@pytest.mark.parametrize("kind", ["add", "sub", "mul"])
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_second_word_equals_the_real_generated_rtl(tmp, kind, mode):
    core = "mul" if kind == "mul" else "adder"
    cfg = {"wide_mode": 1} if kind == "mul" else {"carry_mode": 1, "subtract_mode": 1 if kind == "sub" else 0}
    ps = pairs(hash(kind) & 0xFF)
    streams = {"X": [b for _, b in ps], "Y": [a for a, _ in ps]}
    recs = design(core, **cfg)
    rtl, folder = rtl_words(tmp, f"{kind}_{mode}", recs, streams, mode)
    want = [w for a, b in ps for w in expected(core, a, b, 1 if kind == "sub" else 0)]
    assert rtl == want, f"RTL {rtl[:8]} vs arithmetic {want[:8]}"
    mine = vm_words(recs, streams)
    assert mine == rtl, f"FlexGrid {mine[:8]} vs RTL {rtl[:8]}"
    text = open(os.path.join(folder, h.json.load(open(os.path.join(folder, "ASSEMBLY.json")))["top"] + ".v")).read()
    assert ".SECOND_PORT(1)" in text and "merge_cell_v4sa" in text


def test_without_the_flag_nothing_changes(tmp):
    ps = pairs(3, 4)
    streams = {"X": [b for _, b in ps], "Y": [a for a, _ in ps]}
    recs = design("adder")
    rtl, folder = rtl_words(tmp, "noflag", recs, streams)
    assert rtl == [(a + b) & M32 for a, b in ps] == vm_words(recs, streams, words_per_item=1)
    text = open(os.path.join(folder, h.json.load(open(os.path.join(folder, "ASSEMBLY.json")))["top"] + ".v")).read()
    assert ".SECOND_PORT(1)" not in text


def test_std_grid_refuses_the_flex_only_carry_flag():
    import unicell_super_automaton_v1 as vm
    with pytest.raises(ValueError, match="flex family only"):
        vm.SuperGrid(design("adder", carry_mode=1))
    fg.FlexGrid(design("adder", carry_mode=1))          # the flex mirror accepts it


def test_planner_refusals(tmp):
    # the second-port cell as the design's exit; a pair-cell consumer; the sub family
    def gen(name, recs, *extra):
        import os
        icm = os.path.join(tmp, name + ".icm")
        h.IcmV3File(name=name, records=recs).save(icm)
        return h.cli("-s", "flex", "--icm", icm, "--output", os.path.join(tmp, "g_" + name), *extra)
    as_exit = [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]),
               IcmV3Record(cell_id="M", row=1, col=1, core="adder", core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"], "carry_mode": 1})]
    r = gen("asexit", as_exit)
    assert r.returncode != 0 and "second" in (r.stderr + r.stdout).lower()
    pair_consumer = design("adder", carry_mode=1)[:4] + [IcmV3Record(cell_id="E", row=1, col=2, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": []})]
    r = gen("pairc", pair_consumer)
    assert r.returncode != 0 and "single-input" in (r.stderr + r.stdout)
    icm = os.path.join(tmp, "subfam.icm")
    h.IcmV3File(name="subfam", records=design("adder", carry_mode=1)).save(icm)
    r = h.cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_sub"))
    assert r.returncode != 0 and "flex family only" in (r.stderr + r.stdout)
