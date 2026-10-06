"""tests/vm/test_fp32_stage_map_cells_v1.py -- ledger #982: the fp32 pipeline stages that now map onto REAL flex cells, run in the generated RTL (iverilog) and in FlexGrid and compared with the
Python models (nano/fp32_boundary_v1.py, fp32_add_v1.py, fp32_mul_v1.py). The map and the stages still without cells: docs/stripped-cell/design-notes/fp32_stage_map_second_ports.md.

Significands are LEFT-ALIGNED in the 32-bit word (sig << 8, what a shift-left-8 add-on gives): then the 32-bit cells see the 24-bit significand's own carries --
  * ADD: the adder's carry out of bit 31 IS the significand overflow of fp32_add (`raw_sum & (1 << 24)`): the carry word goes straight into an exponent adder (exp + carry) = the normalise step;
  * MUL: the 64-bit product of two left-aligned significands is P48 << 16, so its HIGH word's top bit IS fp32_mul's normalise test (`product & (1 << 47)`): an add-on shifts it down to 0/1 and an
    exponent adder adds it = the exponent bump; the low word and the high word are both delivered (second_output, routed to their own consumers).
  * UNPACK: a relay ram with the shift add-on (fp32_boundary_v1's own addon config).
Requires iverilog.
"""
import os
import random
import shutil
import struct
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402
from fp32_boundary_v1 import extract_sign_exp, unpack, restore_implicit_one  # noqa: E402

ram = h.ram
M32 = 0xFFFFFFFF


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32map_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def cell(cid, r, c, core, up, down, **cfg):
    return IcmV3Record(cell_id=cid, row=r, col=c, core=core, core_config=dict({"upstream_mask": up, "downstream_mask": down}, **cfg))


def rtl_run(tmp, name, recs, streams, mode):
    d, r = h.build(tmp, name, recs)
    assert r.returncode == 0, r.stderr[:600]
    return h.run_level(d, streams, mode, 3, settle=500)[1]


def vm_run(recs, streams, exits, ticks_per_item=250):
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = {k: [] for k in exits}
    for k in range(len(next(iter(streams.values())))):
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


def f32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def finite_floats(seed, n):
    r = random.Random(seed)
    out = []
    while len(out) < n:
        b = r.getrandbits(32)
        if 1 <= (b >> 23) & 0xFF <= 254:
            out.append(b)
    return out


def fields(bits):
    se, m = unpack(bits)
    e = se & 0xFF
    return e, restore_implicit_one(e, m)


# ── UNPACK: sign + exponent ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_unpack_sign_exp_is_a_relay_with_the_shift_addon(tmp, mode):
    # (the add-on acts when the cell OFFERS its value to a neighbour, so the result is read from the cell after it, not from the add-on cell itself)
    recs = [ram("IN", 0, 0, [], ["e"]), ram("SE", 0, 1, ["w"], ["e"], addon_config={"shift_en": 1, "direction": 1, "shift_amt": 20, "shift_fine": 3}), ram("OUT", 0, 2, ["w"], [])]
    vals = finite_floats(1, 14) + [0, f32(1.0), f32(-2.5), M32]
    got = rtl_run(tmp, f"unpack_{mode}", recs, {"IN": vals}, mode)
    assert got["OUT"] == [extract_sign_exp(v) for v in vals]
    assert vm_run(recs, {"IN": vals}, ["OUT"], 60)["OUT"] == got["OUT"]


# ── ADD: carry = the significand overflow = the exponent bump ──────────────────────────────────────────────────────────────────────────────────
def add_design():
    """Y (big sig) + X (aligned small sig, via a relay) -> M with second_output: sum east to SUM, CARRY south into the exponent adder together with EXP -> EXPOUT."""
    m = cell("M", 1, 1, "adder", ["n", "w"], ["e"], second_output=1, second_downstream_mask=["s"])
    return [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), m, ram("SUM", 1, 2, ["w"], []),
            ram("EXP", 2, 0, [], ["e"]), cell("EA", 2, 1, "adder", ["n", "w"], ["e"]), ram("EXPOUT", 2, 2, ["w"], [])]


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_add_carry_is_the_normalise_trigger_and_bumps_the_exponent(tmp, mode):
    r = random.Random(5)
    rows = []
    for _ in range(18):
        big = (1 << 23) | r.getrandbits(23)
        small = ((1 << 23) | r.getrandbits(23)) >> r.randrange(0, 3)       # the aligned integer part of the smaller significand
        rows.append((big, small, r.randrange(1, 254)))
    rows += [((1 << 24) - 1, (1 << 24) - 1, 100), (1 << 23, 1 << 23, 7), (1 << 23, 0, 9)]
    streams = {"Y": [b << 8 for b, s, e in rows], "X": [s << 8 for b, s, e in rows], "EXP": [e for b, s, e in rows]}
    recs = add_design()
    got = rtl_run(tmp, f"addnorm_{mode}", recs, streams, mode)
    for k, (big, small, e) in enumerate(rows):
        overflow = 1 if (big + small) & (1 << 24) else 0                    # fp32_add: `(raw_sum_wide >> _EXTRA) & (1 << 24)` -> out_exp += 1
        assert got["SUM"][k] == ((big + small) << 8) & M32
        assert got["EXPOUT"][k] == e + overflow
    assert any(((b + s) & (1 << 24)) for b, s, e in rows) and any(not ((b + s) & (1 << 24)) for b, s, e in rows)
    assert vm_run(recs, streams, ["SUM", "EXPOUT"]) == {"SUM": got["SUM"], "EXPOUT": got["EXPOUT"]}


# ── MUL: the high word's top bit = the normalise test = the exponent bump ───────────────────────────────────────────────────────────────────────
def mul_design():
    """Y x X -> M (second_output): LOW word east to LO; HIGH word south to H, which fans out to HIX (exit) and to NB (shift add-on: bit 31 -> 0/1) -> exponent adder with EXP -> EXPOUT."""
    m = cell("M", 1, 1, "mul", ["n", "w"], ["e"], second_output=1, second_downstream_mask=["s"])
    return [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), m, ram("LO", 1, 2, ["w"], []),
            ram("H", 2, 1, ["n"], ["e", "s"]), ram("HIX", 2, 2, ["w"], []),
            ram("NB", 3, 1, ["n"], ["e"], addon_config={"shift_en": 1, "direction": 1, "shift_amt": 28, "shift_fine": 3}),
            ram("EXP", 4, 2, [], ["n"]), cell("EA", 3, 2, "adder", ["w", "s"], ["e"]), ram("EXPOUT", 3, 3, ["w"], [])]


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_mul_high_word_top_bit_is_the_normalise_test_and_bumps_the_exponent(tmp, mode):
    fl = finite_floats(8, 20)
    rows = []
    for k in range(0, len(fl), 2):
        (ea, sa), (eb, sb) = fields(fl[k]), fields(fl[k + 1])
        rows.append((sa, sb, ea + eb - 127 + 200))                           # +200 keeps the test exponent positive; the bump is what is being checked
    rows += [((1 << 24) - 1, (1 << 24) - 1, 300), (1 << 23, 1 << 23, 300), (1 << 23, (1 << 24) - 1, 300)]
    streams = {"Y": [a << 8 for a, b, e in rows], "X": [b << 8 for a, b, e in rows], "EXP": [e for a, b, e in rows]}
    recs = mul_design()
    got = rtl_run(tmp, f"mulnorm_{mode}", recs, streams, mode)
    for k, (a, b, e) in enumerate(rows):
        p64 = (a << 8) * (b << 8)
        p48 = a * b
        assert got["LO"][k] == p64 & M32 and got["HIX"][k] == p64 >> 32
        assert got["EXPOUT"][k] == e + (1 if p48 & (1 << 47) else 0)        # fp32_mul: `if product & (1 << 47): exp_sum += 1`
    bumps = [1 if a * b & (1 << 47) else 0 for a, b, e in rows]
    assert 0 < sum(bumps) < len(bumps)
    assert vm_run(recs, streams, ["LO", "HIX", "EXPOUT"]) == {k: got[k] for k in ("LO", "HIX", "EXPOUT")}
