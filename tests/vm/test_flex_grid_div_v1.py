"""tests/vm/test_flex_grid_div_v1.py -- ledger #1070: FlexGrid's division core against the REAL generated flex RTL (div_cell_v4sa) at several widths.

Y (the dividend, operand A: it reaches the cell first) and X (the divisor, via a relay) feed the divider M, whose results go to the exit E. For each pair the exit must receive, in order, the words the
flags ask for (quotient; quotient then remainder; remainder then quotient; remainder alone). The generated RTL is run in iverilog (plain, and with random stalls) and checked against plain arithmetic
first; FlexGrid must then give the identical sequence. Requires iverilog."""
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


def design(**cfg):
    mid = IcmV3Record(cell_id="M", row=1, col=1, core="div", core_config=dict({"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}, **cfg))
    # Y reaches M directly (hop 1) and is operand A, the dividend; X goes through a relay P first (hop 2) and is operand B, the divisor
    return [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), mid, ram("E", 1, 2, ["w"], [])]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fgdiv_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def pairs(width, seed, n=10):
    m = (1 << width) - 1
    r = random.Random(seed)
    edge = [(m, 1), (m, m), (0, 0), (5, 0), (m, 0), (0, 7), (1, 2), (m - 1, m), (1 << (width - 1), 3), (23 & m, 7 & m)]
    return [(a & m, b & m) for a, b in edge] + [(r.getrandbits(width), r.getrandbits(width) >> r.randrange(width)) for _ in range(n)]


def expected(width, a, b, second, rem_first):
    m = (1 << width) - 1
    q, r = (m, a) if b == 0 else (a // b, a % b)
    words = [r, q] if rem_first else [q, r]
    return words if second else words[:1]


def vm_words(recs, streams, width, words_per_item, ticks_per_item=300):
    """One item at a time (the VM pairs a two-operand cell's operands by arrival order; the generated RTL joins them with the handshake and is correct in any timing)."""
    g = fg.FlexGrid(recs, width=width)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen, e = [], g.cells[pos["E"]]
    for k in range(len(streams["X"])):
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


COMBOS = [(0, 0), (1, 0), (1, 1), (0, 1)]       # (second_output, remainder_primary)


@pytest.mark.parametrize("width", [32, 18, 8, 4, 36])
@pytest.mark.parametrize("second,rem_first", COMBOS)
def test_flexgrid_division_equals_the_generated_rtl(tmp, width, second, rem_first):
    ps = pairs(width, width * 7 + second * 2 + rem_first)
    streams = {"X": [b for _, b in ps], "Y": [a for a, _ in ps]}
    recs = design(second_output=second, remainder_primary=rem_first)
    name = f"w{width}_s{second}_r{rem_first}"
    d, r = h.build(tmp, name, recs, width)
    assert r.returncode == 0, (r.stderr or r.stdout)[:500]
    modes = ["plain", "stall"] if width == 32 else ["plain"]
    want = [w for a, b in ps for w in expected(width, a, b, second, rem_first)]
    for mode in modes:
        _, got = h.run_level(d, streams, mode, 7, settle=400, cycles=20000, width=width)
        assert got["E"] == want, f"RTL ({mode}) {got['E'][:8]} vs arithmetic {want[:8]}"
    mine = vm_words(recs, streams, width, 2 if second else 1)
    assert mine == want, f"FlexGrid {mine[:8]} vs arithmetic {want[:8]}"
    text = open(os.path.join(d, h.json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")).read()
    assert "div_cell_v4sa" in text and (".SECOND_PORT(1)" in text) == bool(second)


def test_a_same_tick_pair_has_no_dividend_order_and_is_refused():
    """Both operands arriving in the same tick have no order, so FlexGrid refuses (the real cell would order them by arrival)."""
    recs = [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]),
            IcmV3Record(cell_id="M", row=1, col=1, core="div", core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}), ram("E", 1, 2, ["w"], [])]
    g = fg.FlexGrid(recs, width=32)
    g.inject(0, 1, 100)
    g.inject(1, 0, 7)
    with pytest.raises(ValueError, match="same tick"):
        for _ in range(10):
            g.tick()


def test_the_sub_family_now_builds_division(tmp):
    """Ledger #1071 asserted here that the sub family REFUSES division; ledger #1072 enabled it (div_cell_v4s, instantiated at STEPS = 32), which made that assertion stale.
    The RTL-vs-VM proof for sub is tests/vm/test_sub_div_v1.py; this only pins that the build now succeeds and uses the sub cell."""
    recs = design()
    icm = os.path.join(tmp, "subbuild.icm")
    from icm_v3 import IcmV3File
    IcmV3File(name="subbuild", records=recs).save(icm)
    out = os.path.join(tmp, "g_subbuild")
    r = h.cli("-s", "sub", "--icm", icm, "--output", out)
    assert r.returncode == 0, (r.stderr or r.stdout)[:500]
    rec = h.json.load(open(os.path.join(out, "ASSEMBLY.json")))
    text = open(os.path.join(out, rec["top"] + ".v")).read()
    assert "div_cell_v4s" in text
