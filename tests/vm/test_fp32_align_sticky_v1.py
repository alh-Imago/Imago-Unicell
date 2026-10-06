"""tests/vm/test_fp32_align_sticky_v1.py -- ledger #988: ALIGN WITH STICKY from real flex cells, using the multiplier's TWO output words (second port).

Each stage is ONE multiplier:  P = v * F  with  F = 2^(31 - s*b)   (b = 0/1: bit k of the exponent difference d; s = 1,2,4,8,16; a sixth stage has s = 31 and b = (d >= 32)).
HIGH word of P = v >> (1 + s*b)  -> the next stage's value (second port, routed with second_downstream_mask);  LOW word = the bits shifted out -> the sticky collector (first port).
Each stage shifts by one bit MORE than asked (b = 0 would need F = 2^32, which does not fit a word), six stages -> a fixed extra shift of 6: the aligned word is  w >> (6 + d)  (w = significand << 8 in the
32-bit word => the aligned significand with TWO guard bits below its lsb), and nothing is lost: every bit shifted out lands in some stage's low word.
F comes from b without any branch:  F = b*Kc + 2^31  with  Kc = 2^(31-s) - 2^31 (mod 2^32)  (a multiplier and an adder, two constants).  b = bit k of d: relay << (31-k), relay >> 1 (the comparator
is SIGNED), comparator >= 2^30 (the sixth stage: comparator d >= 32).  Sticky: each low word >> 1 (sign) -> comparator >= 1 -> added along a lane; at the end a comparator >= 1.
Outputs compared with a plain Python shift: ALIGNED = w >> T and STICKY = (w mod 2^T != 0), T = 6 + (d mod 32) + (31 if d >= 32).  Real generated RTL (plain + stalls) == FlexGrid. Requires iverilog.
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
SHIFTS = (1, 2, 4, 8, 16, 31)
P = 7
NS = int(os.environ.get('ALIGN_NS', '0'))


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32alignst_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def build(ns=0):
    """ns = number of spacer relays on each stage's low-word path (a knob that only exists to keep the two operands of the sticky adders from arriving in the same hop)."""
    R = 5 + ns                                                                     # the sticky lane's row
    g = Grid(rows=R + 4, cols=P * 6 + 12)
    consts = {}
    for k, s in enumerate(SHIFTS):
        c, p = P * k, f"A{k}."
        last = k == 5
        g.add(f"P{k}", 0, 1 + c)                                                   # the d bus
        g.add(p + "E", 1, 1 + c)
        g.add(p + "B1", 1, 2 + c, addon=None if last else {"shift_en": 1, "direction": 0, "shift_amt": 31 - k})
        g.add(p + "B2", 1, 3 + c, addon=None if last else {"shift_en": 1, "direction": 1, "shift_amt": 1})
        g.add(p + "BC", 1, 4 + c, "comparator", {"threshold": 32 if last else 1 << 30})
        g.add(p + "BX", 1, 5 + c)                                                  # one spare relay: staggers the two operands of MUL (the generator refuses equal arrival hops)
        kc = ((1 << (31 - s)) - (1 << 31)) & M32
        g.add(p + "K", 2, 4 + c, preload=kc)
        g.add(p + "KM", 2, 5 + c, "mul")                                           # b * Kc
        g.add(p + "C", 1, 6 + c, preload=1 << 31)
        g.add(p + "ADF", 2, 6 + c, "adder")                                        # + 2^31 = F
        g.add(p + "V", 3, 5 + c)
        g.add(p + "MUL", 3, 6 + c, "mul", {"second_output": 1})
        nk = ns if k else 0                                                        # spacers only on stages 1..5: SA_1's two operands then differ in length
        Rk = 5 + nk
        g.add(p + "LS", 4, 6 + c, addon={"shift_en": 1, "direction": 1, "shift_amt": 1})
        for i in range(nk):
            g.add(p + f"Q{i}", 5 + i, 6 + c)
        g.add(p + "LC", Rk, 6 + c, "comparator", {"threshold": 1})
        g.add(p + "SA", Rk, 7 + c, "adder")
        consts[p + "K"], consts[p + "C"] = kc, 1 << 31
        if k == 0:
            g.add(p + "Z", Rk - 1, 7 + c, preload=0)                                # SA_0 = LC_0 + 0 keeps every stage's sum alike
            consts[p + "Z"] = 0
        g.link(f"P{k}", p + "E")
        chain = ["E", "B1", "B2", "BC", "BX", "KM"]
        pairs = list(zip(chain, chain[1:])) + [("K", "KM"), ("KM", "ADF"), ("C", "ADF"), ("ADF", "MUL"), ("V", "MUL"), ("MUL", "LS")]
        lo = ["LS"] + [f"Q{i}" for i in range(nk)] + ["LC"]
        pairs += list(zip(lo, lo[1:])) + [("LC", "SA")] + ([("Z", "SA")] if k == 0 else [])
        for a, b in pairs:
            g.link(p + a, p + b)
    g.add("OUT", 3, 7 + P * 5)
    g.add("FIN", R, 8 + P * 5, "comparator", {"threshold": 1})
    g.add("STK", R, 9 + P * 5)
    for k in range(1, 6):
        g.route(f"P{k - 1}", f"P{k}")
    for k in range(5):
        g.add(f"A{k}.SP", 3, 7 + P * k)                                            # a spacer relay on the value lane
        g.link(f"A{k}.MUL", f"A{k}.SP", second=True)                               # the HIGH word (second port) is the next value
        g.route(f"A{k}.SP", f"A{k + 1}.V", avoid=[(3, 10 + P * k)])               # a detour of two extra hops
    g.route("A5.MUL", "OUT", second=True)
    for k in range(1, 6):
        g.route_via(f"A{k - 1}.SA", f"A{k}.SA", (R + 3, 4 + P * k))                    # deliberately long: the sum's two operands must not arrive in the same hop
    g.link("A5.SA", "FIN")
    g.link("FIN", "STK")
    return g, consts


def expected(w, d):
    t = 6 + (d & 31) + (31 if d >= 32 else 0)
    return w >> t, 1 if w & ((1 << t) - 1) else 0


def run_vm(recs, consts, ws, ds, ticks=1500):
    recs = [type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config, io_name=r.io_name, preload_value=None) if r.cell_id in consts else r for r in recs]
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = {"OUT": [], "STK": []}
    for w, d in zip(ws, ds):
        g.inject(*pos["A0.V"], w)
        g.inject(*pos["P0"], d)
        for k, kv in consts.items():
            g.inject(*pos[k], kv)
        for _ in range(ticks):
            g.tick()
            for e in seen:
                c = g.cells[pos[e]]
                if c.ram_data_valid:
                    seen[e].append(c.ram_data_reg)
                    c.ram_data_valid = False
    return seen


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_align_with_sticky(tmp, mode):
    g, consts = build(NS)
    recs = g.records()
    r = random.Random(8)
    ws = [M32, 0xFFFFFF00, 0x80000000, 0x12345600, 0x00000100, 0] + [r.getrandbits(24) << 8 for _ in range(24)]
    ds = [0, 1, 2, 7, 26, 31, 32, 33, 5, 8, 16, 24, 40, 100] + [r.randrange(0, 60) for _ in range(16)]
    d, res = h.build(tmp, f"alst_{mode}", recs)
    assert res.returncode == 0, res.stderr[:1500]
    _, got = h.run_level(d, {"A0_V": ws, "P0": ds}, mode, 4, settle=6000)
    want = [expected(w, dd) for w, dd in zip(ws, ds)]
    assert got["OUT"] == [a for a, _ in want], [(hex(w), dd, hex(x), hex(a)) for w, dd, x, (a, _) in zip(ws, ds, got["OUT"], want) if x != a][:3]
    assert got["STK"] == [b for _, b in want], [(hex(w), dd, x, b) for w, dd, x, (_, b) in zip(ws, ds, got["STK"], want) if x != b][:3]
    assert run_vm(recs, consts, ws, ds) == {"OUT": got["OUT"], "STK": got["STK"]}
