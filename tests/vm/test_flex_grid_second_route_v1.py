"""tests/vm/test_flex_grid_second_route_v1.py -- ledger #981: the SECOND word routed to its OWN faces (ICM field `second_downstream_mask`, next to `second_output`).

Three things, each run in the real generated RTL (iverilog; plain and with random stalls) and in FlexGrid, and compared with plain arithmetic:
  * the sum goes east, the carry (or the multiplier's high word) goes south, to a DIFFERENT consumer each -- no merge core is built;
  * a face in BOTH masks gets both words (first, then second) -- the merge core of #976 is still used;
  * a 64-bit add from two 32-bit limbs: limb 0's carry goes straight to the adder of limb 1 (a consumer that is NOT a ram/comparator, which the #976 same-faces rule refused).
Requires iverilog.
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


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fgroute_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def adder(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="adder", core_config=dict({"upstream_mask": up, "downstream_mask": down}, **kw))


def split_design(core, second_faces, **kw):
    """X -> P -> M <- Y ; M's first word east to S, its second word by `second_faces` (south -> C, or east too)."""
    m = IcmV3Record(cell_id="M", row=1, col=1, core=core, core_config=dict({"upstream_mask": ["n", "w"], "downstream_mask": ["e"], "second_output": 1, "second_downstream_mask": second_faces}, **kw))
    return [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), m, ram("S", 1, 2, ["w"], []), ram("C", 2, 1, ["n"], [])]


def pairs(seed, n=10):
    r = random.Random(seed)
    return [(M32, 1), (M32, M32), (0, 0), (5, 3), (0x80000000, 0x80000000)] + [(r.getrandbits(32), r.getrandbits(32)) for _ in range(n)]


def rtl_run(tmp, name, recs, streams, mode):
    d, r = h.build(tmp, name, recs)
    assert r.returncode == 0, r.stderr[:600]
    _, got = h.run_level(d, streams, mode, 5, settle=400)
    return got, d


def vm_run(recs, streams, exits, ticks_per_item=120):
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = {k: [] for k in exits}
    n_items = len(next(iter(streams.values())))
    for k in range(n_items):
        for name, vals in streams.items():
            g.inject(*pos[name], vals[k])
        for _ in range(ticks_per_item):
            g.tick()
            for e in exits:
                c = g.cells[pos[e]]
                if c.ram_data_valid:
                    seen[e].append(c.ram_data_reg)
                    c.ram_data_valid = False
    return seen


def want(core, a, b, sub=False):
    if core == "mul":
        return [(a * b) & M32, (a * b) >> 32]
    if sub:
        return [(a - b) & M32, 1 if a + ((~b) & M32) + 1 > M32 else 0]
    return [(a + b) & M32, 1 if a + b > M32 else 0]


@pytest.mark.parametrize("kind", ["add", "sub", "mul"])
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_the_two_words_go_to_different_consumers(tmp, kind, mode):
    core = "mul" if kind == "mul" else "adder"
    recs = split_design(core, ["s"], **({"subtract_mode": 1} if kind == "sub" else {}))
    ps = pairs(len(kind))
    streams = {"X": [b for _, b in ps], "Y": [a for a, _ in ps]}
    got, folder = rtl_run(tmp, f"split_{kind}_{mode}", recs, streams, mode)
    w = [want(core, a, b, kind == "sub") for a, b in ps]
    assert got["S"] == [x[0] for x in w] and got["C"] == [x[1] for x in w]
    assert vm_run(recs, streams, ["S", "C"]) == {"S": got["S"], "C": got["C"]}
    text = open(os.path.join(folder, h.json.load(open(os.path.join(folder, "ASSEMBLY.json")))["top"] + ".v")).read()
    assert ".SECOND_PORT(1)" in text and "merge_cell_v4sa" not in text           # each word has its own consumer: nothing to merge


def test_a_face_in_both_masks_gets_both_words_in_order(tmp):
    recs = split_design("adder", ["s", "e"])                                   # east in both masks; south only the carry
    ps = pairs(7, 6)
    streams = {"X": [b for _, b in ps], "Y": [a for a, _ in ps]}
    got, folder = rtl_run(tmp, "bothfaces", recs, streams, "stall")
    w = [want("adder", a, b) for a, b in ps]
    assert got["C"] == [x[1] for x in w]
    assert got["S"] == [v for x in w for v in x]                               # east: sum then carry, per pair
    assert vm_run(recs, streams, ["S", "C"], 160) == {"S": got["S"], "C": got["C"]}


def limbs_design():
    """64-bit add from two 32-bit limbs. Limb 0: X(lo of b) and Y(lo of a) -> M0; sum east to LO; carry south straight into limb 1's adder M1 (with AH); M1 -> M2 (with BH) -> HI."""
    m0 = adder("M0", 1, 1, ["n", "w"], ["e"], second_output=1, second_downstream_mask=["s"])
    return [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), m0, ram("LO", 1, 2, ["w"], []),
            ram("AH", 2, 0, [], ["e"]), adder("M1", 2, 1, ["n", "w"], ["e"]), adder("M2", 2, 2, ["w", "s"], ["e"]), ram("BH", 3, 2, [], ["n"]), ram("HI", 2, 3, ["w"], [])]


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_the_carry_feeds_the_next_limbs_adder(tmp, mode):
    r = random.Random(11)
    nums = [(M32 << 32 | M32, 1), ((1 << 64) - 1, (1 << 64) - 1), (0, 0), (M32, 1), (0xFFFFFFFF00000000, 0x00000000FFFFFFFF)] + [(r.getrandbits(64), r.getrandbits(64)) for _ in range(12)]
    streams = {"X": [b & M32 for a, b in nums], "Y": [a & M32 for a, b in nums], "AH": [a >> 32 for a, b in nums], "BH": [b >> 32 for a, b in nums]}
    recs = limbs_design()
    got, folder = rtl_run(tmp, f"limbs_{mode}", recs, streams, mode)
    for k, (a, b) in enumerate(nums):
        s = (a + b) & ((1 << 64) - 1)
        assert (got["HI"][k] << 32) | got["LO"][k] == s, (k, hex(a), hex(b))
    assert vm_run(recs, streams, ["LO", "HI"], 200) == {"LO": got["LO"], "HI": got["HI"]}


def test_set_without_the_flag_or_without_a_first_face_is_refused():
    no_flag = split_design("adder", ["s"])
    no_flag[3].core_config.pop("second_output")
    with pytest.raises(ValueError, match="second_output is off"):
        fg.FlexGrid(no_flag, width=32)
    no_first = split_design("adder", ["s"])
    no_first[3].core_config["downstream_mask"] = []
    with pytest.raises(ValueError, match="non-empty downstream_mask"):
        fg.FlexGrid(no_first, width=32)


def test_the_std_grid_routes_the_second_word_too():
    """ledger #1036: second_downstream_mask is part of the standard cells; the std grid sends the high word south and the low word east, as FlexGrid does."""
    import unicell_super_automaton_v1 as vm
    recs = split_design("mul", ["s"])
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    g = vm.SuperGrid(recs)
    g.inject(*pos["X"], 0x12345678)
    g.inject(*pos["Y"], 0x9ABCDEF0)
    s_, c_ = g.cells[pos["S"]], g.cells[pos["C"]]
    out = {}
    for _ in range(100):
        g.tick()
        for k, c in (("S", s_), ("C", c_)):
            if c.ram_data_valid:
                out[k] = c.ram_data_reg
                c.ram_data_valid = False
    full = 0x12345678 * 0x9ABCDEF0
    assert out == {"S": full & 0xFFFFFFFF, "C": full >> 32}
